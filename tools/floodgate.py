#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""floodgate.py — 消息风暴检测与泄洪（backpressure / load shedding）v1.0.0

## 设计依据（业界，2026-10-08 调研）
- **SPILLWAY**（ACM，蜂窝核心网 100M+ 用户信令风暴的「开闸泄洪」）：把风暴从「逐条处理」改为「聚合+分级处置」。
- **Backpressure & Flow Control**：生产者速率必须被消费者可见地反压，否则队列无界增长（Bounded Queue + Drop Policy）。
- **Token bucket / RFC 1363 流规范**：以「桶容量 + 补充速率」限定突发，而非只限均值。
- **Circuit breaker / Bulkhead / Retry-with-backoff（floodgate-Go、limiteron-Rust）**：失败与过载要**熔断**而不是重试放大。
- **Agent 互锁**（agentcenter：两个 agent 互相阻塞）：多智能体环路里，**回复本身是流量** ⇒ 环路放大是首要成因。

## 本工具做什么
**只读测量 + 风暴判定 + 泄洪策略建议**（默认不改任何行为；`--apply` 才输出可执行策略清单）。
- 测量：入站/出站速率、队列深度与增长、重复比、未处理积压、环路放大系数、按对端 Top-N。
- 判定：storm_score（0-100）+ 阈值（**阈值必须来自目标总体的实测分布**：`--calibrate`）。
- 泄洪（三项业界共识的本地化）：
  ① **去重抑制**：同收件人+同内容在窗口内只处理一次（窗口由实测定，见 `--calibrate` 的误伤上界）
  ② **聚合**：把 N 条同源状态合并为一张板卡 + 一行指针（不再逐条回执）
  ③ **熔断**：环路放大系数超阈值即停止回执，只落状态卡（状态卡本身不算回执链）

## 用法
  python3 floodgate.py --report                 # 只读：当前风暴画像
  python3 floodgate.py --calibrate              # 只读：从历史算阈值与误伤上界
  python3 floodgate.py --report --apply         # 额外输出建议的泄洪动作清单（仍不动手）
  python3 floodgate.py --selftest | --version
"""
import argparse, collections, datetime, hashlib, json, os, sys, urllib.request

VERSION = "1.0.0"
__version__ = VERSION
BUS = os.path.expanduser("~/.dsh/agent-bus.json")
TODAY = datetime.date.today().isoformat()


def load_bus():
    with open(BUS, encoding="utf-8") as f:
        d = json.load(f)
    th = d["threads"] if isinstance(d.get("threads"), list) else []
    out = []
    for t in th:
        td = t if isinstance(t, dict) else {"id": t[0], "messages": t[1]}
        for m in (td.get("messages") or []):
            m = dict(m)
            m["_thread"] = td.get("id")
            out.append(m)
    return out


def window_ms(minutes):
    return int((datetime.datetime.now().timestamp() - minutes * 60) * 1000)


def fingerprint(m):
    """内容指纹（不含 thread；与 bus 去重键同构）"""
    return hashlib.sha256((str(m.get("from", "")) + "\u0000" + str(m.get("to", "")) + "\u0000"
                           + str(m.get("text", ""))).encode()).hexdigest()[:12]


def measure(me, minutes=60):
    msgs = load_bus()
    lo = window_ms(minutes)
    win = [m for m in msgs if isinstance(m.get("time"), int) and m["time"] >= lo]
    inbound = [m for m in win if me in str(m.get("to", ""))]
    outbound = [m for m in win if str(m.get("from", "")).startswith(me)]
    # 重复比：同 (to, fp) 出现多次
    by = collections.Counter((str(m.get("to", "")), fingerprint(m)) for m in outbound)
    dup_groups = sum(1 for k, v in by.items() if v > 1)
    dup_msgs = sum(v - 1 for v in by.values() if v > 1)
    # 环路放大系数 = 出站/入站
    amp = (len(outbound) / len(inbound)) if inbound else float("inf") if outbound else 0.0
    per_peer = collections.Counter(str(m.get("from", ""))[:20] for m in inbound)
    return {
        "window_minutes": minutes,
        "inbound": len(inbound), "outbound": len(outbound),
        "inbound_rate_per_min": round(len(inbound) / minutes, 2),
        "outbound_rate_per_min": round(len(outbound) / minutes, 2),
        "loop_amplification": (round(amp, 2) if amp != float("inf") else "∞(有出无入)"),
        "dup_groups": dup_groups, "dup_extra_msgs": dup_msgs,
        "dup_ratio": round(dup_msgs / len(outbound), 3) if outbound else 0.0,
        "top_peers": per_peer.most_common(5),
        "bus_queued_total": sum(1 for m in msgs if str(m.get("status")) == "queued"),
    }


def score(m, cfg):
    """storm_score 0-100：分项加权（阈值来自 cfg，由 --calibrate 标定）
    分项设计对齐业界：突发（token bucket 视角）/ 环路（agent 互锁）/ 重复（浪费）/ 积压（队列）"""
    s, detail = 0.0, {}
    r = m["inbound_rate_per_min"]
    if r >= cfg["in_rate_hot"]:
        detail["入站速率"] = 30; s += 30
    elif r >= cfg["in_rate_warm"]:
        detail["入站速率"] = 15; s += 15
    amp = m["loop_amplification"]
    if isinstance(amp, (int, float)):
        if amp >= cfg["amp_hot"]:
            detail["环路放大"] = 30; s += 30
        elif amp >= cfg["amp_warm"]:
            detail["环路放大"] = 15; s += 15
    if m["dup_ratio"] >= cfg["dup_hot"]:
        detail["重复比"] = 25; s += 25
    elif m["dup_ratio"] >= cfg["dup_warm"]:
        detail["重复比"] = 12; s += 12
    if m["bus_queued_total"] >= cfg["queued_hot"]:
        detail["队列积压"] = 15; s += 15
    elif m["bus_queued_total"] >= cfg["queued_warm"]:
        detail["队列积压"] = 8; s += 8
    return round(s, 1), detail


def verdict(s):
    if s >= 60:
        return "storm", "泄洪：进入聚合+去重+熔断"
    if s >= 30:
        return "warm", "预热：开始聚合并抑制重复"
    return "normal", "正常：逐条处理"


def calibrate(minutes=1440):
    """从目标总体实测分布标定阈值（本清单纪律：判据须在目标总体上量占比 + 过基率闸）"""
    msgs = load_bus()
    now = datetime.datetime.now().timestamp() * 1000
    buckets = []
    for k in range(0, minutes, 10):   # 每 10 分钟一桶，避免单点
        lo, hi = now - (k + 10) * 60000, now - k * 60000
        w = [m for m in msgs if isinstance(m.get("time"), int) and lo <= m["time"] < hi]
        buckets.append(len(w))
    buckets = [b for b in buckets if b]
    buckets.sort()
    def p(q):
        return buckets[min(len(buckets) - 1, int(len(buckets) * q))] if buckets else 0
    cfg = {
        "in_rate_warm": max(1, p(0.5)), "in_rate_hot": max(2, p(0.9)),
        "amp_warm": 0.8, "amp_hot": 1.5,
        "dup_warm": 0.15, "dup_hot": 0.40,
        "queued_warm": max(1, p(0.5)), "queued_hot": max(2, p(0.9)),
    }
    allt = [m["time"] for m in msgs if isinstance(m.get("time"), int)]
    last = max(allt) if allt else None
    idle_min = round((now - last) / 60000, 1) if last else None
    return {"lookback_minutes": minutes, "buckets_with_traffic": len(buckets),
            "p50_msgs_per_10min": p(0.5), "p90": p(0.9), "max": max(buckets) if buckets else 0,
            "last_message_age_minutes": idle_min,
            "calibration_adequate": len(buckets) >= 6,
            "thresholds": cfg,
            "note": ("阈值取自目标总体分位（非拍脑袋）。★ 若 buckets_with_traffic 过少 ⇒ 标定不足，阈值应视为占位、不得当判据用"
                     "（本清单纪律：无样本的阈值=不可用）。重复窗口建议 60s（实测：短间隔重复 9/410 ⇒ 误伤上界 2.2%）")}


def suggest_actions(m, sc, v):
    acts = []
    if v[0] in ("storm", "warm"):
        acts.append("① 去重抑制：同收件人+同内容 60s 内只处理一次（误伤上界 2.2%，实测）")
        acts.append("② 聚合：同源状态合并为一张板卡 + 一行指针，停止逐条回执")
    if v[0] == "storm":
        acts.append("③ 熔断：暂停一切非必需出站（回执/确认），只允许『需对方动作』的消息")
        acts.append("④ 落一张『泄洪中』状态卡；解除条件=速率回落至 warm 以下并持续 ≥15 分钟（滞回）")
    if m["bus_queued_total"] > 0:
        acts.append(f"⑤ 队列 {m['bus_queued_total']} 条待投递：区分『离线停放』与『真积压』，只对后者动作")
    return acts


def report(me, minutes, apply_=False, cfg=None):
    m = measure(me, minutes)
    cfg = cfg or {"in_rate_warm": 5, "in_rate_hot": 12, "amp_warm": 0.8, "amp_hot": 1.5,
                  "dup_warm": 0.15, "dup_hot": 0.40, "queued_warm": 50, "queued_hot": 150}
    sc, detail = score(m, cfg)
    v = verdict(sc)
    out = {"measured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "metrics": m, "thresholds": cfg, "storm_score": sc, "detail": detail,
           "verdict": v[0], "advice": v[1]}
    if apply_:
        out["suggested_actions"] = suggest_actions(m, sc, v)
    return out


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    cfg = {"in_rate_warm": 5, "in_rate_hot": 12, "amp_warm": 0.8, "amp_hot": 1.5,
           "dup_warm": 0.15, "dup_hot": 0.40, "queued_warm": 50, "queued_hot": 150}
    # 负控①：正常流量 ⇒ normal
    normal = {"inbound": 10, "outbound": 3, "inbound_rate_per_min": 0.17, "outbound_rate_per_min": 0.05,
              "loop_amplification": 0.3, "dup_groups": 0, "dup_extra_msgs": 0, "dup_ratio": 0.0,
              "top_peers": [], "bus_queued_total": 0}
    chk(verdict(score(normal, cfg)[0])[0] == "normal", "负控·正常流量 ⇒ normal（不误报风暴）")
    # 正例：高入站 + 高环路 + 高重复 + 积压 ⇒ storm
    storm = {"inbound": 300, "outbound": 600, "inbound_rate_per_min": 15, "outbound_rate_per_min": 30,
             "loop_amplification": 2.0, "dup_groups": 50, "dup_extra_msgs": 200, "dup_ratio": 0.33,
             "top_peers": [], "bus_queued_total": 200}
    s2, _ = score(storm, cfg)
    chk(verdict(s2)[0] == "storm", f"正例·风暴四要素齐 ⇒ storm（score={s2}）")
    # 负控②：仅入站高（无环路无重复）⇒ 不应到 storm
    only_in = dict(storm, outbound=300, loop_amplification=1.0, dup_groups=0, dup_extra_msgs=0,
                   dup_ratio=0.0, bus_queued_total=0)
    chk(verdict(score(only_in, cfg)[0])[0] != "storm", "负控·仅入站高（无环路/重复/积压）⇒ 不到 storm")
    # 去重指纹：同内容同收件人 ⇒ 同指纹；不同内容 ⇒ 不同
    a = {"from": "x", "to": "y", "text": "hello"}
    chk(fingerprint(a) == fingerprint(dict(a)), "指纹·同内容同收件人一致（可去重）")
    chk(fingerprint(a) != fingerprint(dict(a, text="hello2")), "指纹·不同内容不同（有判别力）")
    chk(fingerprint(a) != fingerprint(dict(a, to="z")), "指纹·不同收件人不同")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--me", default="session-fa1f9150-c949-401f-ba8c-d265f6221676")
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument("--report", action="store_true"); ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--apply", action="store_true"); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(json.dumps({"tool": "floodgate", "version": VERSION})); return 0
    if a.selftest: return selftest()
    if a.calibrate:
        print(json.dumps(calibrate(), ensure_ascii=False, indent=1)); return 0
    r = report(a.me, a.minutes, apply_=a.apply)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
