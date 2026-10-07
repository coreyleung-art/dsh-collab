#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把我在 MBP 侧的**两处改进**合并进星桥的 v1.5.8 / v0.2.2（在 staging 目录打补丁）。

对比结论（已在 mac-mini 侧实测确认）：
  · 自回声短标识守卫 —— **它已覆盖且更完整**（route.js L57-59 有 session-XXXXXXXX 对称处理）
    ⇒ 我的 caShort **弃用，不合并**。
  · 内容指纹去抖 —— **它未覆盖**：route.js 用 `key + '@' + version`，
    而「重建卡片」会改 version ⇒ **仍会重复注入**（正是我 10-02 实测到的问题）
    ⇒ **合并我的内容指纹**。
  · 思考链中文门 —— 它无 ⇒ **合并**。

★ 关键设计：内容指纹去重键**不得含 version**。
    含 version ⇒ 重建（ver 变、内容同）生成新键 ⇒ 照样注入（等于没修）。
    去 version、只留指纹 ⇒ 内容同即同键（不注入）、内容变即新键（注入）。
"""
import io, os, re, sys

ST = os.path.expanduser("~/upgrade-staging")
CL = os.path.join(ST, "dsh-plugin-central-inbox")
AW = os.path.join(ST, "dsh-plugin-agent-bus")
fail = []

# ---------------- 补丁 1：route.js 内容指纹去重 ----------------
RJ = os.path.join(CL, "lib", "route.js")
s = io.open(RJ, encoding="utf-8").read()
OLD = """  // ★ 修缺陷1：真去重 —— `<key>@<version>` 成员资格，而非单槽
  const ver = value.version === undefined ? (d.version === undefined ? '' : d.version) : value.version;
  const dk = key + '@' + ver;"""
NEW = """  // ★ 修缺陷1：真去重 —— 成员资格，而非单槽
  // ★★ 2026-10-02 MBP(session-20b800d4) 合并：去重键**改用内容指纹、且不含 version**。
  //   理由（实测）：上游用 `key@version`，而**重建卡片会改 version、内容却完全一致**
  //   （星桥「批量补 to → 误覆盖 → 按历史重建」即此形态）⇒ 每次重建都被当新卡注入，
  //   接收方被反复唤醒（实测同一张卡连推 3 次）。
  //   ⇒ 含 version 的键解决不了这个问题；**去 version、只留内容指纹**才对：
  //      内容同 ⇒ 同键 ⇒ 不注入；内容变（如追加新回复）⇒ 新键 ⇒ 照常注入。
  const ver = value.version === undefined ? (d.version === undefined ? '' : d.version) : d.version;
  const fp = contentFingerprint(JSON.stringify(value));
  const dk = key + '#' + fp;"""
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    # 补 import
    if "contentFingerprint" not in s.split("\n")[0]:
        s = s.replace("import { normalizeTo } from '../../dsh-comm-shared/identity.js';",
                      "import { normalizeTo, contentFingerprint } from '../../dsh-comm-shared/identity.js';", 1)
    io.open(RJ, "w", encoding="utf-8").write(s)
    print("✅ route.js：去重键已改为内容指纹（不含 version）")
else:
    fail.append("route.js 未匹配到原去重段（结构可能已变，需人工看）")

# 校验 import 到位
s2 = io.open(RJ, encoding="utf-8").read()
if "contentFingerprint" not in s2:
    fail.append("route.js 缺 contentFingerprint import")
if "key + '#' + fp" not in s2:
    fail.append("route.js 去重键未生效")

# ---------------- 补丁 2：agent-way 思考链中文门 ----------------
AI = os.path.join(AW, "lib", "index.js")
a = io.open(AI, encoding="utf-8").read()
LANG = '''
const LANG_PROMPT = `【思考链语言纪律 · 中文】
推理/思考（thinking）内容一律用【中文】书写。这是硬约束，任何会话、任何智能体都适用。
1. 叙述、判断、权衡、结论、自述、给用户的解释——一律中文。
2. 技术标识符保持原样、不翻译：代码、文件路径、API/函数名、命令、报错原文、
   协议字段（如 approval/asked、turn/start、limit=500、sp.section）。
3. 中英混排时不要整段滑向英文；英文只用于上述标识符与原文引用。
4. 本条是既有「正文本就要求中文」的**延伸**：此前思考链无任何约束，会自然漂移成英文。
   若你发现自己在用英文推理，立即切回中文。`;

'''
if "LANG_PROMPT" not in a:
    # 插在 REPORT_PROMPT 定义之后（找其结尾反引号行）
    m = re.search(r"(const REPORT_PROMPT = `.*?`;\n)", a, re.S)
    if m:
        a = a[:m.end()] + LANG + a[m.end():]
        print("✅ agent-way：LANG_PROMPT 已插入")
    else:
        fail.append("agent-way 未找到 REPORT_PROMPT 定义")
    # 注册 sp.section
    m2 = re.search(r"(ctx\.effect\(\(\) => sp\.section\(\{ name: 'agent-bus:iteration-report', order: 117, text: REPORT_PROMPT \}\)\);\n)", a)
    if m2:
        a = a[:m2.end()] + "    ctx.effect(() => sp.section({ name: 'agent-bus:lang-zh', order: 118, text: LANG_PROMPT }));\n" + a[m2.end():]
        print("✅ agent-way：sp.section(lang-zh, order 118) 已注册")
    else:
        fail.append("agent-way 未找到 iteration-report 注入行（v1.5.8 结构可能与 v1.4.x 不同）")
    io.open(AI, "w", encoding="utf-8").write(a)
else:
    print("（agent-way 已含 LANG_PROMPT，跳过）")

# ---------------- 校验 ----------------
a2 = io.open(AI, encoding="utf-8").read()
if "LANG_PROMPT" not in a2: fail.append("agent-way LANG_PROMPT 未落地")
if "agent-bus:lang-zh" not in a2: fail.append("agent-way lang-zh section 未落地")

print("\n=== 补丁结果 ===")
print("  route.js  : 内容指纹去重 =", "key + '#' + fp" in s2)
print("  agent-way : LANG_PROMPT =", "LANG_PROMPT" in a2, "· lang-zh =", "agent-bus:lang-zh" in a2)
if fail:
    print("\n  ❌ 待处理:")
    for f in fail: print("     -", f)
    sys.exit(1)
print("\n  ✅ 两处补丁均已落地")
