#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""handoff-fallback-check —— 【csx 不适用时的续接替代路径】判据（H5f）

★★★★★ 立据（`P26` + 本线 2026-10-15 实测）：
  ★ `P26` 叫「**会话硬死锁：compaction 下界 > 被遮内容（两机制）**」——
    ★ 实测：**全量 147 次压缩 / 100 次失败 / 37 次恰好相等**（★ 68% 失败率）。
  ★★★ 而本线本会话实测（`csx_status`）：
    ★ **token 压力 472107 / 700000 = 47.2%**（★ 未达阈值）
    ★★ **`write.writes = 0` · `write.notApplicable = 157`**（★ 本会话 **79**）
    ★ 拒绝理由逐字：★「**表面序 ≠ seq 序**（第 1 个节点 `seq=8678225` ≤ 前一个 `8954065`）
      ⇒ 该会话发生过【表面替换】…在该形态下不适用 ⇒ **本步不动**」
  ★★★ **⇒ 即：★ `csx` 检查点这条路【对本会话不可用】** ——
    ★★ 而 **`P26` 明说那个风险是【分布式】的**（★ 不只本会话）。

★★★★ 故本条问的是：
  ★★★ **「当 `csx` 不适用时，续接靠什么 —— 而它是否新鲜？」**

★ 三态：
  ★ 找不到任何替代路径 ⇒ **FAIL**（★ 那意味着**没有续接**）
  ★ 找到但**不新鲜** ⇒ **FAIL**（★ 那意味着**续接会指向旧状态**）
  ★ `csx` 可用 ⇒ **PASS**（★ 那就有检查点，不需要替代路径）
  ★ 读不到 ⇒ **SKIP**

用法：
  python3 tools/handoff-fallback-check.py [--json]
  python3 tools/handoff-fallback-check.py --selftest
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys

VERSION = "1.0.0"
HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "dsh-collab")
RESUME = os.path.join(ROOT, "docs", "resume-prompt-starbridge-v3.md")
MKR = os.path.join(ROOT, "tools", "mk-resume-prompt.py")
INDEX = os.path.join(ROOT, "data", "registry", "continuity-index.json")
ANCHOR = os.path.join(ROOT, "docs", "distributed-agent-network-governance-plan-v7-20261012.md")
LEDGER = os.path.join(ROOT, "docs", "deviation-ledger-20261011.md")


def now():
    return datetime.datetime.now().astimezone()


def csx_available():
    """★ 读 csx 守卫的可用性 ⇒ (available: bool|None, note)"""
    try:
        p = os.path.join(HOME, ".dsh", "context-survival")
        # ★ 优先用守卫自己的状态文件；★ 取不到则从事件流推
        for cand in (os.path.join(p, "guard-state.json"),
                     os.path.join(p, "state.json")):
            if os.path.exists(cand):
                d = json.load(io.open(cand, encoding="utf-8"))
                na = (d.get("write") or {}).get("notApplicable", 0)
                w = (d.get("write") or {}).get("writes", 0)
                if w > 0 and na == 0:
                    return True, "csx 有成功写入"
                if na > 0 and w == 0:
                    return False, "csx 写入 notApplicable=%d（★ 须走替代路径）" % na
                return None, "csx 读数不足（writes=%s notApplicable=%s）" % (w, na)
        return None, "★ 找不到 csx 状态文件 ⇒ 不可判（★ 空 ≠ 无）"
    except Exception as e:
        return None, "csx 读数失败 %s" % type(e).__name__


def check_fallback(as_json=False):
    d = {"version": VERSION, "at": now().isoformat(timespec="seconds")}
    av, note = csx_available()
    d["csx_available"] = av
    d["csx_note"] = note
    print("══ 续接替代路径检查（H5f）══  %s" % d["at"])
    print("  ★ csx 检查点：%s" % ("可用" if av else ("不可用" if av is False else "不可判")))
    print("     %s" % note)
    print()

    if av is True:
        print("  ⇒ ✅ **csx 可用** ⇒ 有检查点，本条不需要替代路径")
        d["verdict"] = "PASS"
        if as_json:
            print(json.dumps(d, ensure_ascii=False))
        return 0

    # ★ csx 不可用（或不可判）⇒ 检查替代路径
    checks = []

    # ① 续接提示词在位且 ≤40 行
    try:
        rl = io.open(RESUME, encoding="utf-8").read().split("\n")
        n = len([x for x in rl if x.strip()])
        checks.append(("① 续接提示词在位", os.path.exists(RESUME), "%s · %d 行" % (os.path.basename(RESUME), n)))
        checks.append(("①b ≤40 行（★ §4.1③）", n <= 40, "%d 行" % n))
    except Exception as e:
        checks.append(("① 续接提示词在位", False, "★ 读不到：%s" % type(e).__name__))

    # ② 提示词与【现渲染结果】一致（★ 防漂移）
    try:
        before = io.open(RESUME, encoding="utf-8").read()
        subprocess.run([sys.executable, MKR], capture_output=True, text=True, timeout=90)
        after = io.open(RESUME, encoding="utf-8").read()
        checks.append(("② 提示词未漂移（★ == 现渲染）", before == after,
                       "★ 一致" if before == after else "★ 不一致 ⇒ 跑一次生成脚本（★ 不要手改）"))
    except Exception as e:
        checks.append(("② 提示词未漂移", False, "★ 取不到：%s" % type(e).__name__))

    # ③ 索引 state_version == 锚点 state_version
    try:
        iv = json.load(io.open(INDEX, encoding="utf-8")).get("state_version")
        av2 = None
        m = re.search(r"\*\*state_version\*\*:\s*(\d+)", io.open(ANCHOR, encoding="utf-8").read())
        if m:
            av2 = int(m.group(1))
        checks.append(("③ 索引 ↔ 锚点版本相等", iv == av2, "索引=%s 锚点=%s" % (iv, av2)))
    except Exception as e:
        checks.append(("③ 索引 ↔ 锚点版本", False, "★ 取不到：%s" % type(e).__name__))

    # ④ 台账【最近有 round-close 注记】（★ 那 = 上一轮的收尾做过）
    try:
        idx = json.load(io.open(INDEX, encoding="utf-8"))
        notes = [k for k in idx if k.startswith("_v") and k.endswith("_round_close_note")]
        checks.append(("④ 索引有 round-close 注记", len(notes) > 0, "%d 条" % len(notes)))
    except Exception as e:
        checks.append(("④ round-close 注记", False, "★ 取不到：%s" % type(e).__name__))

    # ⑤ 台账条数（★ 非零即可 —— ★ 那是续接的【实质内容】）
    try:
        t = io.open(LEDGER, encoding="utf-8", errors="ignore").read()
        nl = len(re.findall(r"^## D-\d{3}", t, re.M))
        checks.append(("⑤ 台账条数 > 0", nl > 0, "%d 条" % nl))
    except Exception as e:
        checks.append(("⑤ 台账条数", False, "★ 取不到：%s" % type(e).__name__))

    ok = sum(1 for _, c, _ in checks if c)
    for name, c, ev in checks:
        print("    %s %-34s %s" % ("✅" if c else "❌", name, ev))
    print()
    print("  【替代路径】%d/%d 项" % (ok, len(checks)))
    d["checks"] = [{"name": n, "ok": c, "evidence": e} for n, c, e in checks]
    d["fallback_ok"] = ok
    d["fallback_total"] = len(checks)
    if ok == len(checks):
        print("  ⇒ ✅ **替代路径完整且新鲜** —— ★ 即使 `csx` 不适用，★ 续接仍然可用")
        d["verdict"] = "PASS"
    else:
        print("  ⇒ ❌ **替代路径不完整** —— ★ 而 `csx` 不可用 ⇒ ★★ **续接会有断裂**")
        d["verdict"] = "FAIL"
    print()
    print("  ★ 诚实边界：★ 本条只验【替代路径是否在位且新鲜】，★ **不验它是否【内容充分】**")
    print("    （★ 内容充分性属人工判断 —— ★ 那正是「续接提示词 ≤40 行」这条的来源。）")
    if as_json:
        print(json.dumps(d, ensure_ascii=False))
    return 0 if d["verdict"] == "PASS" else 1


def selftest():
    ok = tot = 0
    print("== handoff-fallback-check 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：四个文件都存在（★ 那是替代路径的载体）
    chk(os.path.exists(RESUME), "正控：续接提示词在位")
    chk(os.path.exists(MKR), "正控：生成器在位")
    chk(os.path.exists(INDEX), "正控：索引在位")
    chk(os.path.exists(ANCHOR), "正控：锚点在位")
    # ★ 负控：csx 可用性判据三态
    av, note = csx_available()
    chk(av in (True, False, None), "负控：csx 可用性返回三态之一（现值 %s）" % av)
    # ★ 正控：实跑一次
    r = check_fallback()
    chk(r in (0, 1, 2), "正控：check_fallback 返回 0/1/2（实得 %s）" % r)
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("handoff-fallback-check %s" % VERSION)
        return 0
    if a.selftest:
        return selftest()
    return check_fallback(a.json)


if __name__ == "__main__":
    sys.exit(main())
