#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix-g23-addendum-quoting.py —— 修复被 shell 命令替换改坏的归档条目

【事故】（2026-10-03 22:36）
  我用 `python3 -c "…"`（**双引号**）写这条归档，正文里含**反引号**包裹的标识符：
    `session-ab866871` / `RULES.md` / `precedence` / `ledgerIndex`
  ⇒ **bash 把反引号内容当命令替换**（stderr 可见 `session-ab866871: command not found`）
  ⇒ 写入的文本里这些标识符**被替换成空串**，条目**静默残缺**。

【为什么值得单独记】
  这正是同日立下的 **R36**（多行/复杂脚本落文件，不用内联）要防的事，而我又犯了 ——
  且**后果是静默的**：脚本没报错、退出码 0，只是内容少了几个词；
  若不做**读回核对**，我会以为条目已写好。⇒ **写完必须读回**（R030）。
"""
import io
import os

p = os.path.expanduser("~/dsh-collab/hazards/INDEX.md")
s = io.open(p, encoding="utf-8").read()

broken = "| **G23-追** | **重放批已整批处理完毕（2026-10-03 22:35）**：本批含  **7 张旧卡**（10-02 内容）。我**一次读完并逐条核完**，用**它推荐的「逐条对账」格式**发收口卡：**收到 7 → 已处理 7 → 剩余 0**。其两条核心要求均已落地：① **R037 前置声明写在对的位置**（ L267-272 + json  fail-closed）；② **禁令独立约束表**（RC-001 + ）。★ 过程副产品：补了 **3 条自证/规则缺口**（R27 两条延伸、R40/R41）与**摘要漂移检查** | ✅ 已收口 |"

fixed = ("| **G23-追** | **重放批已整批处理完毕（2026-10-03 22:35）**：本批含 `session-ab866871` 的 **7 张旧卡**"
         "（内容属 10-02）。我**一次读完并逐条核完**，并以**它推荐的「逐条对账」格式**发收口卡："
         "**收到 7 → 已处理 7 → 剩余 0**。其两条核心要求均已落地："
         "① **R037 前置声明写在对的位置**（`RULES.md` L267-272 + json `precedence` 结构化：约束表优先／降级为只读告警／fail-closed）；"
         "② **禁令独立约束表**（RC-001 + `ledgerIndex` 31 键）。"
         "★ 过程副产品：补了 **3 处自证/规则缺口**（R27 两条延伸、R40/R41）与新增**摘要漂移检查**。"
         "★ 本条自身也踩了坑：我用 `python3 -c \"…\"` 双引号内联写它，"
         "**反引号被 bash 命令替换** ⇒ 标识符被替换成空串、条目静默残缺（已按 R36 用文件改回） | ✅ 已收口 |")

assert broken in s, "未找到待修条目（可能已被改过）"
io.open(p, "w", encoding="utf-8").write(s.replace(broken, fixed, 1))

# ★ 写后读回断言（R030）
rb = io.open(p, encoding="utf-8").read()
must = ["session-ab866871", "RULES.md", "precedence", "ledgerIndex", "收到 7 → 已处理 7 → 剩余 0"]
missing = [m for m in must if m not in rb]
print("✅ 已修复 G23-追 条目")
print("   读回校验：%s" % ("全部关键标识符在位" if not missing else "❌ 仍缺 %s" % missing))
