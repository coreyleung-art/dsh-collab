#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-wake-triage.py —— 查「这条唤醒是不是我的活、处理过没有」（读固定分层表）

用法: python3 check-wake-triage.py <黑板键|键的片段>
退出码: 0=属于我且已处理 ／ 1=非我的活 ／ 2=表中无此键 ／ 3=参数错
★ 目的：**重复唤醒一查即答**，不靠记忆、不重复分析。
"""
import json, os, sys

TBL = os.path.expanduser("~/dsh-collab/data/ops/replayed-batch-triage-20261003.json")


def main():
    if len(sys.argv) < 2:
        print("用法: check-wake-triage.py <黑板键|片段>"); return 3
    q = sys.argv[1]
    # ★ 允许**直接粘贴整条唤醒消息**：自动抽取 notes/… 键
    #   （动机：用户要转发 ~100 条排空唤醒，每次手抄键太费；粘贴全文即可）
    if "notes/" in q or " " in q:
        import re as _re
        m = _re.search(r"notes/[A-Za-z0-9_\-./]+", q)
        if m:
            q = m.group(0).rstrip(".,;")
    d = json.load(open(TBL, encoding="utf-8"))
    hit = [r for r in d["rows"] if q in r["key"]]
    if not hit:
        print("表中无此键（可能不是本次重放批的卡）⇒ 需按常规判断")
        return 2
    for r in hit:
        print("键  : %s" % r["key"])
        print("来源: %s ｜ to=%s" % (r["from"] or "?", r.get("to") or "（无 to）"))
        print("标题: %s" % (r["title"] or "?"))
        st = r["status"]
        if st == "mine-processed":
            print("⇒ ★ **属于我，且已处理**（本批 7 张已整批收口，剩余 0）—— **无需再处理**")
            return 0
        if st == "addressed-to-me-no-action":
            print("⇒ **指向我，但内容是测试/探针回执、无诉求** —— **无需处理**")
            return 1
        if st == "broadcast-no-to":
            print("⇒ **频道广播**（无 `to`、非派单）—— 无需处理")
            return 1
        print("⇒ **点名别人**（to=%s）—— 非我的活" % (r.get("to") or "?"))
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
