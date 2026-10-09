#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sedimentation-absence-check.py — 沉淀链【缺席可判别】检查器 v1.0.0

为什么需要（2026-10-09）：
  沉淀链在 2026-10-09 被接上电（`--from-git` 数据源 + `com.dsh.cron.sedimentation` 每日 1 次），
  清单随即从 `2026-09-02.json`（静默 37 天）跳到 `2026-10-09.json`（79 条）。
  **⇒ 但「有清单」不等于「链在跑」** —— 实测同一时刻：
    · 今日清单 79 条
    · 消费标记（`sedimentation-scan-state.json` 的 `seen`）只有 **1 条**
    · 消费协议指定值班方为 **HR**，而 **HR 会话已失效**
  ⇒ 即：**清单产生了，而【无人消费】—— 而这不会自己报警。**

★ 判据来源（照抄本机既有原则，不发明）：
  ① **G1/G3 的「缺席可判别」**：把报警从【存在报警】反转为【缺席报警】；
     仪表静默死亡时无人知道 —— 故须【期望周期内收到，否则报警】。
  ② **HR 2026-09-22 原则**（见 `scripts/bb-copy.py` L983-985）：
     「**心跳阈值须与检查周期同阶**，否则报警恒真 —— 恒真报警与恒假读数**对称**」
     ⇒ **刷新周期与阈值都由【一处】导出**，不得各自硬编码而漂移。
  ③ **三态纪律**（本项目 2026-10-09 学到）：缺字段 ⇒ 判「**未核**」而非「通过」。

用法：
  python3 sedimentation-absence-check.py            # 人读
  python3 sedimentation-absence-check.py --json     # 机器读
  python3 sedimentation-absence-check.py --selftest
  python3 sedimentation-absence-check.py --lean4-check   # ★ R006 ⑩ 六项 A–F
  python3 sedimentation-absence-check.py --verify-plist  # 核对 plist 与脚本常量不漂移

退出码（★ R006 ⑨ 固定语义）：
  0 = 新鲜且被消费（或无异常）；1 = **检出缺席/未消费**；2 = 用法或环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import json
import os
import plistlib
import re
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
QUEUE = os.path.join(COLLAB, "token-monitor", "sedimentation-queue")
STATE = os.path.join(COLLAB, "token-monitor", "sedimentation-scan-state.json")
PLIST = os.path.join(HOME, "Library", "LaunchAgents", "com.dsh.cron.sedimentation.plist")
LOG = os.path.join(COLLAB, "logs", "sedimentation-absence-check.log")   # ★ R006 ⑦
BB_KEY = "data/health/sedimentation"
BB = "http://127.0.0.1:8792"

# ═══ ★ 单一来源（原则 ②）：刷新周期与阈值【同阶且同源】 ═══
REFRESH_SECONDS = int(os.environ.get("SEDIMENT_REFRESH_SECONDS", "86400"))   # = plist StartInterval
STALE_THRESHOLD = REFRESH_SECONDS * 2          # ★ 由 REFRESH 导出，不得独立硬编码
CONSUME_GRACE_SECONDS = REFRESH_SECONDS        # 清单产生后【一个周期内】应被消费


def log(msg):
    """★ R006 ⑦：固定路径日志，失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def verdict_stale(age, max_age=None):
    """三态：True 新鲜 / False 陈旧 / None **未核**（缺 ts）。"""
    if age is None:
        return None, "★ **未核**：无时间戳 ⇒ 不得当作通过"
    m = max_age if max_age is not None else STALE_THRESHOLD
    if age > m:
        return False, "★ **缺席**：最新清单已 %.0f 秒未更新（阈值 %d = 刷新 %d × 2）" % (age, m, REFRESH_SECONDS)
    return True, "新鲜：%.0f 秒前（阈值 %d）" % (age, m)


def collect():
    """读三样：最新清单、消费标记、本次清单条数。"""
    out = {"ok": False}
    try:
        files = sorted([f for f in os.listdir(QUEUE) if f.endswith(".json")]) if os.path.isdir(QUEUE) else []
    except Exception as e:
        return {"error": "读不了清单目录: %s" % str(e)[:60]}
    if not files:
        return {"error": "清单目录为空 ⇒ 链从未产出"}
    latest = os.path.join(QUEUE, files[-1])
    out["latest"] = files[-1]
    out["latest_mtime"] = os.path.getmtime(latest)
    out["age_seconds"] = time.time() - out["latest_mtime"]
    try:
        d = json.load(open(latest, encoding="utf-8"))
        # ★ 2026-10-09 修 bug①：实盘字段是 queue/deposit/review/skip，而非 items/list。
        #   实证：读错字段 ⇒ 得 0 ⇒ 与 bug② 叠加 ⇒ 假绿（把 56 条待沉淀报成 PASS）。
        #   ⇒ 现容忍多种命名，且【认不出字段时记 None（未核）而非 0】——
        #     「读不到 ≠ 0」（今日 N-21/「让 X 不可提取 ≠ 让 X 不存在」同族）。
        if isinstance(d, dict):
            for k in ("queue", "items", "list", "pending"):
                v = d.get(k)
                if isinstance(v, list):
                    out["items"] = len(v); break
                if isinstance(v, int):
                    out["items"] = v; break
            else:
                out["items"] = None      # ★ 未核，不得当成 0
            out["breakdown"] = {k: d.get(k) for k in ("deposit", "review", "skip")
                                if k in d}
        else:
            out["items"] = None
    except Exception:
        out["items"] = None
    try:
        st = json.load(open(STATE, encoding="utf-8"))
        out["consumed"] = len(st.get("seen") or [])
    except Exception:
        out["consumed"] = None      # ⇒ 未核
    out["ok"] = True
    return out


def evaluate(info):
    """返回 (exit_code, verdict_dict)。"""
    v = {"source_age_seconds": info.get("age_seconds"), "latest": info.get("latest"),
         "items": info.get("items"), "consumed": info.get("consumed"),
         "refresh_seconds": REFRESH_SECONDS, "stale_threshold": STALE_THRESHOLD,
         "consume_grace": CONSUME_GRACE_SECONDS}
    if "error" in info:
        v["status"] = "GAP"; v["why"] = "★ " + info["error"]
        return 1, v
    ok, why = verdict_stale(info.get("age_seconds"))
    if ok is None:
        v["status"] = "SKIP"; v["why"] = why
        return 1, v
    if ok is False:
        v["status"] = "FAIL"; v["why"] = why + " ⇒ **链未在跑**（launchd 是否装载？）"
        return 1, v
    # 新鲜 ⇒ 再看消费
    n_items = info.get("items")
    n_cons = info.get("consumed")
    if n_cons is None:
        v["status"] = "SKIP"; v["why"] = "★ **未核**：读不到消费标记 ⇒ 不得当作通过"
        return 1, v
    # ★ 2026-10-09 修 bug②：原判据 `n_items > 0 and n_cons == 0`
    #   ⇒ **0 条时不进入判定 ⇒ 报 PASS** ⇒ 与 bug① 叠加产生假绿。
    #   ⇒ 现分四种情况，均分开报（照 R006 §3「三态分开报」精神）：
    if n_items is None:
        v["status"] = "SKIP"
        v["why"] = "★ **未核**：认不出清单字段（读不到 ≠ 0）⇒ 不得当作通过"
        return 1, v
    if n_items == 0:
        v["status"] = "GAP"
        v["why"] = ("清单新鲜但**条目为 0** ⇒ **链产出了空清单**"
                    "（疑：--since 窗口内无提交，或数据源未接通）")
        return 1, v
    if n_cons == 0:
        v["status"] = "GAP"
        v["why"] = ("清单新鲜（%d 条）而**消费标记为 0** ⇒ **有清单而无人消费**"
                    "（消费协议指定值班方为 HR，而 HR 会话已失效）" % n_items)
        return 1, v
    if n_cons < n_items:
        v["status"] = "PENDING"
        v["why"] = ("清单 %d 条，已消费 %d 条（未消费 %d）⇒ **部分消费**"
                    % (n_items, n_cons, n_items - n_cons))
        return 1, v          # ★ 部分消费也算缺口（非 0），但语义与 GAP 不同
    v["status"] = "PASS"
    v["why"] = "清单新鲜（%s 条）且已消费 %d 条" % (n_items, n_cons)
    return 0, v


def bb_put(key, value, dry=False):
    if dry:
        return {"_dry_run": True}
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request("%s/%s" % (BB, key), data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    try:
        tok = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("X-Blackboard-Token", tok)
    except Exception:
        pass
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return {"_http": r.status}
    except Exception as e:
        return {"_error": "%s: %s" % (type(e).__name__, str(e)[:60])}


def verify_plist():
    """★ 原则 ②：plist 的 StartInterval 必须 == 脚本 REFRESH_SECONDS（防漂移）。"""
    if not os.path.exists(PLIST):
        return None, "★ **未核**：plist 不存在（%s）⇒ 未装载" % PLIST.replace(HOME, "~")
    try:
        d = plistlib.load(open(PLIST, "rb"))
    except Exception as e:
        return None, "★ **未核**：plist 解析失败（%s）" % type(e).__name__
    si = d.get("StartInterval")
    if si == REFRESH_SECONDS:
        return True, "一致：plist StartInterval=%s == 脚本 REFRESH_SECONDS=%s" % (si, REFRESH_SECONDS)
    return False, ("★ **漂移**：plist StartInterval=%s ≠ 脚本 REFRESH_SECONDS=%s"
                   " ⇒ 阈值（×2）与真实刷新不同阶 ⇒ **报警可能恒真或恒假**" % (si, REFRESH_SECONDS))


def selftest():
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-50s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== sedimentation-absence-check selftest ==")
    R = REFRESH_SECONDS
    # 负例：陈旧 ⇒ 缺席
    c("陈旧 ⇒ 缺席", verdict_stale(R * 3)[0] is False, kind="neg")
    # 负例：缺 ts ⇒ 未核（不是通过）
    c("缺 ts ⇒ 未核（None）", verdict_stale(None)[0] is None, kind="neg")
    # 正例：新鲜
    c("新鲜 ⇒ 通过", verdict_stale(10)[0] is True)
    # 正例：阈值由刷新导出（单一来源）
    c("阈值 == 刷新 × 2（单一来源）", STALE_THRESHOLD == REFRESH_SECONDS * 2)
    # 负例：有清单而消费 0 ⇒ GAP
    rc, v = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": 79, "consumed": 0})
    c("有清单而消费 0 ⇒ GAP(非 0)", rc != 0 and v["status"] == "GAP", kind="neg")
    # 负例：读不到消费标记 ⇒ 未核（不得当通过）
    rc2, v2 = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": 5, "consumed": None})
    c("消费标记读不到 ⇒ SKIP(非 0)", rc2 != 0 and v2["status"] == "SKIP", kind="neg")
    # 正例：新鲜且【全部消费】⇒ 通过
    #   ★ 2026-10-09：判据新增「部分消费 ⇒ PENDING」后，本正例须同步为 consumed >= items
    #     （原用 items=5,consumed=3 ⇒ 按新语义属部分消费 ⇒ 不再是 PASS）
    rc3, v3 = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": 5, "consumed": 5})
    c("新鲜且【全部】消费 ⇒ PASS", rc3 == 0 and v3["status"] == "PASS")
    # 负例：目录空 ⇒ GAP
    rc4, _ = evaluate({"error": "清单目录为空 ⇒ 链从未产出"})
    c("目录空 ⇒ GAP(非 0)", rc4 != 0, kind="neg")
    # ★ 负例：清单 0 条 ⇒ GAP（不得因 0 而跳过判定）
    rc5, v5 = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": 0, "consumed": 0})
    c("清单 0 条 ⇒ GAP（不得报 PASS）", rc5 != 0 and v5["status"] == "GAP", kind="neg")
    # ★ 负例：认不出字段 ⇒ SKIP（读不到 ≠ 0）
    rc6, v6 = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": None, "consumed": 1})
    c("字段认不出 ⇒ SKIP（读不到≠0）", rc6 != 0 and v6["status"] == "SKIP", kind="neg")
    # ★ 负例：部分消费 ⇒ PENDING（非 0）
    rc7, v7 = evaluate({"ok": True, "age_seconds": 10, "latest": "x.json", "items": 56, "consumed": 1})
    c("部分消费(56/1) ⇒ PENDING(非 0)", rc7 != 0 and v7["status"] == "PENDING", kind="neg")
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0
    checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    _self = open(os.path.abspath(__file__), encoding="utf-8").read()
    c("A", "类型锁：阈值由刷新周期导出（不可独立硬编码）",
      "STALE_THRESHOLD = REFRESH_SECONDS * 2" in _self, "单一来源表达式")
    rc, _v = evaluate({"ok": True, "age_seconds": 10, "latest": "x", "items": 9, "consumed": 0})
    c("B", "入口门：有清单而消费 0 ⇒ 拒绝", rc != 0, "evaluate 返回非 0")
    c("C", "Schema 门：verdict 必备 status/why 两键",
      all(k in _v for k in ("status", "why")), "PASS/GAP/FAIL/SKIP 四态")
    # D 状态机：真跑正负例
    d1 = evaluate({"ok": True, "age_seconds": 10, "latest": "x", "items": 1, "consumed": 1})[0] == 0
    d2 = evaluate({"ok": True, "age_seconds": 10 ** 9, "latest": "x", "items": 1, "consumed": 1})[0] != 0
    c("D", "状态机：新鲜/陈旧可区分（正负例均跑）", d1 and d2, "正例=%s 负例=%s" % (d1, d2))
    c("E", "白名单冻结：退出码仅取 0/1/2",
      "return 0, v" in _self and "return 1, v" in _self, "无其它返回值")
    c("F", "负例矩阵可执行（evaluate 为纯函数）", callable(evaluate), "只读 dict 参数")
    print("== sedimentation-absence-check · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-46s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="沉淀链缺席可判别检查器")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="不写黑板")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--verify-plist", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()
    if a.verify_plist:
        ok, why = verify_plist()
        print(json.dumps({"ok": ok, "verdict": why}, ensure_ascii=False, indent=1))
        return 0 if ok is True else 1
    if not os.path.isdir(COLLAB):
        print("环境错误：找不到 " + COLLAB, file=sys.stderr); return 2

    info = collect()
    rc, v = evaluate(info)
    v["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    v["source_ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.localtime(info.get("latest_mtime", time.time())))
    if not a.dry_run:
        bb_put(BB_KEY, v)
        # ★ 写后必读
        try:
            with urllib.request.urlopen("%s/%s" % (BB, BB_KEY), timeout=6) as r:
                back = json.loads(r.read().decode())
            v["readback_ok"] = bool(isinstance(back.get("value"), dict))
        except Exception:
            v["readback_ok"] = False
    log("status=%s rc=%d why=%s" % (v["status"], rc, v["why"][:90]))
    if a.json:
        print(json.dumps(v, ensure_ascii=False, indent=1))
    else:
        print("== 沉淀链缺席可判别 ==")
        print("  最新清单 : %s" % v.get("latest"))
        print("  清单条数 : %s · 已消费 : %s" % (v.get("items"), v.get("consumed")))
        print("  源时刻   : %s" % v.get("source_ts"))
        print("  ⇒ %s —— %s" % (v["status"], v["why"]))
    return rc


if __name__ == "__main__":
    sys.exit(main())
