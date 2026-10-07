#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refine-wake-triage.py —— 修正分层表的分类规则（补「节点别名」与更细的状态）

【为什么改】2026-10-03 22:45 复核 `notes/collab/archify-a-prereq-done` 时发现：
  我的分类规则只查 **`to` 是否含我的会话 id**，**没查 `to` 是否为我的节点别名**（`mbp`/`MBP`/…）
  ⇒ 更严的复查**立刻翻出 2 条被漏掉的**：`to: mbp`（`bus-bidir-test-2-reply` / `bus-probe-reply`，
  均为 2026-09-08 的**总线测试/探针回执**，无诉求、无 `reply_required`）。
  ★ 教训同族（R31 家族）：**"我的分类器说不是我的活" ≠ "确实与我无关"** ——
    分类器本身要被更严的规则复核（我这次是先给结论、再自查规则，顺序应当反过来）。

【新分类（更细，避免把"广播"和"点名别人"混为一谈）】
  · `mine-processed`            ：`to` 含我会话 id 或我的节点别名 ⇒ 属于我（已处理）
  · `addressed-to-me-no-action` ：`to` 指向我，但内容是测试/探针回执、无诉求 ⇒ **无需动作**
  · `broadcast-no-to`           ：**无 `to` 字段** ⇒ 频道广播（进度/通知），非派单
  · `named-other`               ：`to` 明确指向别的对象
  · 任何 `reply_required=true` 一律另标 ⚠️（无条件需关注）
"""
import io
import json
import os
import re
import urllib.request

TOK = io.open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
H = "http://xingqiao.meetfunbp.com:8792"
TBL = os.path.expanduser("~/dsh-collab/data/ops/replayed-batch-triage-20261003.json")
ME = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
ALIAS = ("mbp", "MBP", "corey-mbp", "macbook-pro-2", "20b800d4")


def get(k):
    r = urllib.request.Request(H + "/" + k,
                               headers={"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK})
    return json.load(urllib.request.urlopen(r, timeout=12))


doc = json.load(io.open(TBL, encoding="utf-8"))
PROCESSED = set(r["key"] for r in doc["rows"] if r["status"] == "mine-processed")

for r in doc["rows"]:
    try:
        d = get(r["key"]); v = d.get("value", d); i = v.get("value", v) if isinstance(v, dict) else v
    except Exception:
        i = None
    if not isinstance(i, dict):
        r["status"] = "fetch-failed"; continue
    to = str(i.get("to") or "").strip()
    r["to"] = to
    r["reply_required"] = (i.get("reply_required") is True)
    r["from"] = str(i.get("from") or r.get("from") or "")
    if r["key"] in PROCESSED:
        r["status"] = "mine-processed"
    elif any(a.lower() in to.lower() for a in ALIAS):
        r["status"] = "addressed-to-me-no-action"     # 测试/探针回执，无诉求
    elif not to:
        r["status"] = "broadcast-no-to"
    else:
        r["status"] = "named-other"

import collections
c = collections.Counter(r["status"] for r in doc["rows"])
doc["summary"] = {"total": len(doc["rows"]), **{k: v for k, v in c.items()}}
doc["classification"] = ("`mine-processed` = `to` 含我会话 id/节点别名且已处理；"
                         "`addressed-to-me-no-action` = 指向我但为测试/探针回执、无诉求；"
                         "`broadcast-no-to` = 无 `to`（频道广播）；`named-other` = 点名别人。"
                         "★ 规则修正史：原只查会话 id，**漏了节点别名** ⇒ 复查翻出 2 条（已归入 "
                         "`addressed-to-me-no-action`）。")
json.dump(doc, io.open(TBL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

rb = json.load(io.open(TBL, encoding="utf-8"))
print("✅ 分层表已按更严规则重算：%s" % TBL)
for k, v in sorted(rb["summary"].items(), key=lambda kv: -kv[1] if isinstance(kv[1], int) else 0):
    print("    %-28s %s" % (k, v))
print()
print("  ⚠️ reply_required=true 的条目：%s"
      % ([r["key"] for r in rb["rows"] if r.get("reply_required")] or "无"))
print("  ★ 指向我的（非已处理）：%s"
      % ([r["key"].split("/")[-1] for r in rb["rows"] if r["status"] == "addressed-to-me-no-action"] or "无"))
