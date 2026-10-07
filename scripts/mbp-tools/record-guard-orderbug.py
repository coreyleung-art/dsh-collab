#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record-guard-orderbug.py —— 归档「守卫顺序缺陷 ⇒ 崩溃伪装成生效」这条发现

★ 本脚本**故意落文件**而不是 heredoc（遵守同日新立的 R36）：
  heredoc 里中文夹英文引号会反复导致解析期 SyntaxError，同日已踩 4 次；
  落文件则一次通过、可复查、可复用。
"""
import io
import os

H = os.path.expanduser("~/dsh-collab/hazards")

# ── ① rules.md：新增 R37 ────────────────────────────────────────────────
p = os.path.join(H, "rules.md")
s = io.open(p, encoding="utf-8").read()
s = s.replace("R1–R36 + R025", "R1–R37 + R025", 1)
s = s.replace(
    "## R27–R36（2026-10-03 建立 · 工具契约 + 判据有效性 + 跨端投递 + 结构式删除 + 约定守卫 + 判据强度 + 脚本载体）",
    "## R27–R37（2026-10-03 建立 · 工具契约 + 判据有效性 + 跨端投递 + 结构式删除 + 约定守卫 + 判据强度 + 脚本载体 + 退出码语义）", 1)

row = ("| R37 | **门的「拒绝」与「崩溃」必须用不同退出码/标记区分** —— 否则任何 `NameError/ImportError` "
       "都会被读成「守卫拦住了」。约定：`0`=通过 ／ `1`=用例失败 ／ `2`=环境错 ／ **`3`=守卫主动拒绝**"
       "（或打印唯一标记行）。**另：守卫所依赖的常量必须在守卫之前定义** |\n")
s = s.replace('| R31 | **判据"什么都没测到"必须报失败，不得报成功**',
              row + '| R31 | **判据"什么都没测到"必须报失败，不得报成功**', 1)

inst = '''
> **R37 实例**（2026-10-03 · 对端照我建议加守卫后引入，我在它机器上实跑抓到）：
> ```
> $ python3 put-card-selftest.py
>   exit=1
>   Traceback ... line 33, in <module>
>     if any(KEY.startswith(p) for p in _LISTENED):
>   NameError: name 'KEY' is not defined
> ```
> `KEY` 在第 33 行被引用、第 36 行才赋值 ⇒ **模块加载期 NameError** ⇒ 自测的 8 个用例（85–96 行）
> **一条都没跑**，而**退出码也是 1** —— 与它声称的"守卫当场拒绝 exit 1"**完全无法区分**。
> ⇒ **「判据崩了」被读成「判据生效了」**：比"判据没跑"更危险，因为它还给出一个看起来正确的信号。
> **修法**：① 常量先于守卫定义；② **拒绝用独立退出码（3）或唯一标记行**。
> ★ **我的责任**：这条守卫是照我"在约定发生点断言"的建议加的 —— 建议成立，但我没提醒
>   ① 顺序（守卫必须在被断言常量之后）② 拒绝要可区分。**属于我的建议不完整**，一并记档。
'''
s = s.replace("\n## R025（本目录的规则来源", inst + "\n## R025（本目录的规则来源", 1)
io.open(p, "w", encoding="utf-8").write(s)
print("✅ rules.md: R37 入册，条目 %d" % len([l for l in s.splitlines() if l.startswith("| R")]))

# ── ② patterns/00-总表.md：类别 C 增补子形态 C″（崩溃伪装成拒绝）──────────
p2 = os.path.join(H, "patterns/00-总表.md")
u = io.open(p2, encoding="utf-8").read()
anchor = "**判据（可执行，**新增判据时的强制流程**）**："
add = '''**★ 子形态 C″ · 崩溃伪装成拒绝（2026-10-03 新识别）**：
判据**自身崩掉**（NameError / ImportError / 路径不存在）时，退出码往往**与"主动拒绝"相同**（都是非 0）
⇒ 观测者看到"非 0"，会读成「门拦住了」，**而实际上门根本没运行**。
实例：对端 `put-card-selftest.py` 守卫里 `KEY` 先用后定义 ⇒ 加载期 `NameError` ⇒ **exit 1**，
而它声称的守卫拒绝**也是 exit 1** ⇒ 无法区分；8 个用例全部从未执行。
**判据（可执行）**：
> ① **退出码必须语义化**：`0` 通过 ／ `1` 用例失败 ／ `2` 环境错 ／ **`3` 守卫主动拒绝**；
> ② 守卫**不得**与"崩溃"共用退出码，也**不得**只靠非零值表达；
> ③ **守卫所依赖的常量必须在守卫之前定义**（先用后定义 = 必崩）；
> ④ 加了守卫之后**必须实跑一次自测**：若连自测都进不去，说明守卫本身把门砸了。

'''
if "C″" in u or "崩溃伪装成拒绝" in u:
    print("⚠️ patterns 已有 C″，跳过")
elif anchor in u:
    u = u.replace(anchor, add + anchor, 1)
    io.open(p2, "w", encoding="utf-8").write(u)
    print("✅ patterns: 类别 C 增补子形态 C″")
else:
    print("❌ patterns 锚点未命中，需人工处理")

# ── ③ INDEX.md：标题 + 新条目 ──────────────────────────────────────────
p3 = os.path.join(H, "INDEX.md")
t = io.open(p3, encoding="utf-8").read()
t = t.replace("R1–R36 + R025", "R1–R37 + R025", 1)
a2 = "| **G8b** | **SSE 断连频率**"
add2 = ("| **G15** | ★ **对端自测守卫顺序缺陷 ⇒ 自测整体失效**（2026-10-03 实跑抓到）："
        "`put-card-selftest.py` 里 `KEY` 第 33 行被引用、第 36 行才赋值 ⇒ 加载期 `NameError`；"
        "8 个用例从未执行，而**退出码同为 1** ⇒ **崩溃伪装成「守卫生效」**。"
        "**已回报并给出修法**（常量前置 + 拒绝用 exit 3/唯一标记）。**含我的责任**：守卫是我建议加的，"
        "未提醒顺序与可区分性。→ 立 **R37**、类别 C 增子形态 **C″** | ⚠️ 已回报；对端待修 |\n")
assert a2 in t
io.open(p3, "w", encoding="utf-8").write(t.replace(a2, add2 + a2, 1))
print("✅ INDEX: G15 入册，标题→R1–R37")
