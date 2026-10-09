#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""intent-outcome-pairing-check.py — 两段式留痕的配对不变量检查（v1.0.0）

依据（PSTD 2026-10-08）：配合两段式留痕，**不变量 = 每条 intent 必有配对 outcome**，
验证退化为**差集统计**（不需等运气触发超时）。

配对键：key（同键的 intent 与其后最近的 outcome 视为一对；同键多轮按时间顺序配对）。
判定：
  ✅ paired      — intent 有其后 outcome
  ⚠️ dangling    — intent 之后无 outcome（说明调用未走到落痕点：正是要抓的病象）
  ℹ️ orphan      — outcome 无前置 intent（旧版本日志，正常历史）
用法: python3 intent-outcome-pairing-check.py [--log <path>] [--json] [--selftest]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import argparse, json, os, sys, urllib.request

VERSION = "1.1.0"
__version__ = VERSION


def load(path):
    rows = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            rows.append(d)
    return rows


def board_has(key, base="http://127.0.0.1:8792", timeout=10):
    """读板判断该键是否已落（区分「超时已落」与「超时未落」）"""
    try:
        with urllib.request.urlopen(f"{base}/{key}", timeout=timeout) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:
        return None   # 不可达 ⇒ 未证，不判


def analyze(rows, base=None):
    """★ 2026-10-08 修正（PSTD）：`orphan` 类别须按**时界 t0**（首个 intent 的时刻）切成两类：
         · orphan(pre-t0)  ⇒ 历史遗留（intent 机制上线前写入），不计
         · orphan(post-t0) ⇒ **覆盖缺口，必须报**（一个类别两种成因，标签不得预先归为无害那种）
       同族：① 一个字段两个爆炸半径（N3 的 id vs name）② 一个标签两种射程（「首行」）。"""
    pend = {}
    intent_total = outcome_total = paired = 0
    dangling_keys = []
    t0 = None
    for r in rows:
        if r.get("phase") == "intent":
            t = r.get("at")
            if t and (t0 is None or t < t0):
                t0 = t
    orphan_pre = orphan_post = 0
    pend2 = {}
    for r in rows:
        k = r.get("key")
        ph = r.get("phase")
        res = r.get("result")
        if ph == "intent":
            intent_total += 1
            pend[k] = pend.get(k, 0) + 1
        elif res in ("OK", "OK-WITH-TIMEOUT", "FAIL"):
            outcome_total += 1
            if pend.get(k, 0) > 0:
                pend[k] -= 1
                paired += 1
            else:
                # 无前置 intent 的 outcome ⇒ 按 t0 切成历史 / 缺口
                t = r.get("at") or ""
                if t0 is None or (t and t < t0):
                    orphan_pre += 1
                else:
                    orphan_post += 1
    dangling_keys = [k for k, v in pend.items() if v > 0]
    dangling = sum(pend.values())
    # ★ 2026-10-08：dangling 有两种成因，必须分开 —— 挂起 intent 的卡**可能已落板**（超时逃逸）。
    dangling_detail = []
    if base:
        for k in dangling_keys:
            dangling_detail.append({"key": k, "board_has_key": board_has(k, base)})
    landed = sum(1 for x in dangling_detail if x["board_has_key"] is True)
    not_landed = sum(1 for x in dangling_detail if x["board_has_key"] is False)
    unverified = sum(1 for x in dangling_detail if x["board_has_key"] is None)
    return {
        "intent_total": intent_total, "outcome_total": outcome_total,
        "paired": paired, "dangling": dangling,
        "t0_first_intent": t0,
        "orphan_pre_t0_historical": orphan_pre,
        "orphan_post_t0_coverage_gap": orphan_post,
        "dangling_keys": dangling_keys[:20],
        "dangling_detail": dangling_detail,
        "dangling_landed_escape": landed if base else "（未查板：请传 --board）",
        "dangling_not_landed": not_landed if base else "（未查板）",
        "dangling_unverified": unverified if base else "（未查板）",
        "invariant": ("dangling == 0 ∧ orphan_post_t0 == 0 ∧ **无「挂起且未落板」**"
                      "（挂起但已落板 = 超时逃逸，属日志不完整而非写失败）"),
        "verdict": ("pass" if (dangling == 0 and orphan_post == 0)
                    else ("fail(挂起且未落板)" if base and not_landed > 0
                          else ("warn(挂起但均已落板=超时逃逸)" if base and landed > 0 else "fail"))),
    }


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    # 正例：intent + outcome 配对
    r = analyze([{"key": "a", "phase": "intent"}, {"key": "a", "result": "OK"}])
    chk(r["dangling"] == 0 and r["paired"] == 1, "正例·配对成立")
    # 负控①：只有 intent ⇒ dangling=1（能红）
    r = analyze([{"key": "b", "phase": "intent"}])
    chk(r["dangling"] == 1 and r["verdict"] == "fail", "负控·悬空 intent 必红")
    # 负控②：旧日志（只有 outcome）⇒ orphan，不算 dangling（不误报新病象）
    r = analyze([{"key": "c", "result": "OK"}])
    chk(r["dangling"] == 0 and r["orphan_pre_t0_historical"] == 1, "负控·历史 orphan（无 t0）归 pre-t0 不误判")
    # 负控④：t0 之后的无 intent outcome ⇒ 覆盖缺口必红
    r = analyze([{"key": "i", "phase": "intent", "at": "2026-10-08T00:30:00"},
                 {"key": "i", "result": "OK", "at": "2026-10-08T00:31:00"},
                 {"key": "x", "result": "OK", "at": "2026-10-08T00:40:00"}])
    chk(r["orphan_post_t0_coverage_gap"] == 1 and r["verdict"] == "fail", "负控·post-t0 orphan 判覆盖缺口并红")
    # 负控③：同键两轮，只配上一轮 ⇒ dangling=1
    r = analyze([{"key": "d", "phase": "intent"}, {"key": "d", "phase": "intent"}, {"key": "d", "result": "OK"}])
    chk(r["dangling"] == 1, "负控·同键多轮部分配对被抓出")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=os.path.expanduser("~/dsh-collab/logs/bb-card-send.log"))
    ap.add_argument("--board", default="http://127.0.0.1:8792", help="查板以区分「挂起已落/未落」；传 '' 跳过")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(json.dumps({"tool": "intent-outcome-pairing-check", "version": VERSION})); return 0
    if a.selftest:
        return selftest()
    r = analyze(load(a.log), base=(a.board or None))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"intent={r['intent_total']} outcome={r['outcome_total']} paired={r['paired']} dangling={r['dangling']}")
        print(f"t0={r['t0_first_intent']} | orphan(pre-t0 历史)={r['orphan_pre_t0_historical']} "
              f"| orphan(post-t0 **覆盖缺口**)={r['orphan_post_t0_coverage_gap']}")
        if r["dangling_keys"]:
            print("悬空键:", ", ".join(r["dangling_keys"]))
        print("verdict:", r["verdict"], "|", r["invariant"])
    return 0 if str(r["verdict"]).startswith("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
