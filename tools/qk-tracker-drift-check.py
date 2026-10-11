#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qk-tracker-drift-check.py — Q-K 台账 §1 与连续性索引 Q-K 条目的**漂移判据**（只读）。

★ 为什么需要它（2026-10-10 实测教训）：
  Q-K 目标明写「两处不许漂，写完独立回读比 payload sha」。
  而我做了 K3/K4/K5/K6 四轮工作，**每轮都往台账 §5 追加日志**（看起来像完成了同步），
  却**从没更新 §1 的里程碑摘要表** ⇒ §1 一直把 K3/K4/K5 标为 ⬜（未开始）。
  ★ 病根与今天反复出现的一族同形：**§5 有更新 ≠ §1 有更新** ——
    「我改了这个文件」不等于「我改了这份文件里该改的那一处」。

判据（机械、只读、可复跑）：
  §1 表里标 ⬜（未开始）的阶段，**不得**在索引里有实质 state。
  反之亦然：索引里有 state 的阶段，§1 不得标 ⬜。

退出码：0 = 无漂移 · 1 = 有漂移（逐条列出）· 2 = 用法/环境错误
"""
import json
import re
import sys
import urllib.request

TRACKER = "/Users/coreyleung/dsh-collab/docs/context-survival-tracker.md"
BB = "http://127.0.0.1:8792"
KEY = "data/registry/continuity-index"
QK_INDEX = 10          # open_questions[10] = Q-K
STAGES = ("k1", "k2", "k21", "k3", "k4", "k5", "k6", "k7")


def index_states():
    try:
        raw = urllib.request.urlopen(f"{BB}/{KEY}", timeout=10).read().decode()
    except Exception as e:
        print(f"环境错误：读不到连续性索引（{e}）", file=sys.stderr)
        sys.exit(2)
    q = json.loads(raw)["value"]["open_questions"][QK_INDEX]
    out = {}
    for k in STAGES:
        v = q.get(k)
        if isinstance(v, dict) and isinstance(v.get("state"), str):
            out[k] = v["state"]
    return out


def tracker_marks():
    try:
        body = open(TRACKER, encoding="utf-8").read()
    except Exception as e:
        print(f"环境错误：读不到台账（{e}）", file=sys.stderr)
        sys.exit(2)
    if "## 1 · 里程碑状态" not in body:
        print("环境错误：台账里找不到 §1 里程碑表", file=sys.stderr)
        sys.exit(2)
    sec = body.split("## 1 · 里程碑状态")[1].split("## 2")[0]
    out = {}
    for line in sec.split("\n"):
        m = re.match(r"\|\s*\*{0,2}(K[\d.]+)\*{0,2}\s*\|", line)
        if m:
            out[m.group(1)] = {"undecided": "⬜" in line, "done": "✅" in line, "partial": "◐" in line}
    return out


def main():
    idx = index_states()
    marks = tracker_marks()

    # ★★ 假通过防护（0637278c 的 zip 漏配同族）：**输入为空 ⇒ 判据不可用 ⇒ 报错，不报通过**
    #   理由：若解析失败返回空集，下面的循环一次都不执行 ⇒ drift 为空 ⇒ 会打印「✅ 无漂移」——
    #   而那是「**我什么都没检查**」，不是「没有问题」。★ 无人会去查一个 ✅。
    if not marks:
        print("环境错误：台账 §1 解析出 **0 个阶段** ⇒ 判据**不可用**（表格格式可能已变）", file=sys.stderr)
        print("★ 这是「空集通过」防护：**空输入不是「无漂移」**，是判据没跑起来。", file=sys.stderr)
        sys.exit(2)
    if not idx:
        print("环境错误：索引解析出 **0 个 state** ⇒ 判据**不可用**", file=sys.stderr)
        sys.exit(2)

    drift = []

    for k, v in marks.items():
        key = k.lower().replace(".", "")
        has_state = key in idx
        if v["undecided"] and has_state:
            drift.append(f"{k}: 台账 §1 标 ⬜（未开始），而索引有实质 state = {idx[key]}")
        if not v["undecided"] and not has_state and key not in ("k0",):
            drift.append(f"{k}: 台账 §1 已标进展（{'✅' if v['done'] else '◐' if v['partial'] else '?'}），"
                         f"而索引**没有**对应 state 块")

    print("qk-tracker-drift-check · 台账 §1 ⨯ 索引 Q-K 条目")
    print(f"  台账阶段: {sorted(marks.keys())}")
    print(f"  索引 state: {sorted(idx.keys())}")
    if drift:
        print()
        for d in drift:
            print(f"  ❌ {d}")
        print(f"\n❌ 检出错位 {len(drift)} 处 —— 按目标要求「两处不许漂」，须先同步再推进")
        return 1
    print(f"\n✅ 无漂移 —— ★ 本次**实际核对 {len(marks)} 个阶段**（索引有 state 的 {len(idx)} 个）；空输入已在入口拦截，故此处 len 必 > 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
