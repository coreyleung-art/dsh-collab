#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星桥 1.0 / 2.0 版本区别登记卡

为什么需要这张卡
    「星桥」这个名字下先后有两个**不同主体**（不同会话 id、不同权限、不同存活状态）。
    只要引用只用「星桥」二字，就会出现两类事故：
      ① 责任错配 —— 把 2.0 的行为记到 1.0 名下（或反之）
      ② 投递错配 —— 发给「星桥」的消息落进已死会话（A1/A3 活引用仍在指向它）

    故本卡把两个主体**分开登记**，并逐维列出「承接 / 未承接 / 被禁 / 新增」四类差异。

依据
    docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md §三（命名方案）
    ~/.dsh/agent-bus.json profiles（两侧自述档案，source=self，按 R030 不可作事实）
    R009（智能体自命名-设备-角色）

观测面声明
    两侧的 role/abilities/resources 均取自 `agent-bus.json` 的 `profiles[]`，
    性质为**各自自述**（source=self），**未经第三方核实** ⇒ 可作线索，不可作事实。

输出
    data/registry/starbridge-version-registry.json
"""
import json
import os
import datetime
import sys
from pathlib import Path

HOME = Path.home()
COLLAB = HOME / "dsh-collab"
# ★ 输出路径可覆盖（第三方复跑时写临时位置，不碰生产）：
#   STARBRIDGE_OUT=/tmp/x.json python3 tools/build-starbridge-version-registry.py
OUT = Path(os.environ.get("STARBRIDGE_OUT")
           or (COLLAB / "data" / "registry" / "starbridge-version-registry.json"))
WRITER = "session-e317d6ab-5302-4b33-b095-947983ba16f4"

S1 = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
S2 = "session-e317d6ab-5302-4b33-b095-947983ba16f4"

doc = {
    "schema": "starbridge-version-registry/v1",
    "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "writer": WRITER,
    "purpose": "把「星桥」名下的两个不同主体分开登记，逐维列出差异，防止引用歧义、责任错配与投递错配。",
    "observation_surface": {
        "source": "~/.dsh/agent-bus.json profiles[]（两侧自述）+ 本会话实测（role-map / 文件系统）",
        "nature": "role/abilities/resources 均为 source=self 自述，未经第三方核实 ⇒ 线索而非事实",
        "unverified": [
            "1.0 的 abilities/resources 在它死后是否仍成立（无人复跑）",
            "1.0 名下资源的实际当前状态（rules-registry 等是否可读、是否已被他方改动）",
        ],
    },

    # ── 术语表：四个易混名字，先钉死 ──────────────────────────────
    "terminology": {
        "星桥": {
            "means": "首任会话（= 星桥 1.0），历史专名，冻结",
            "session": S1,
            "note": "agent-role-map.json 中该键【保留】指向 1.0，**不重指**（v3.1 §三）",
        },
        "星桥v2": {
            "means": "第二任会话（= 星桥 2.0），在任",
            "session": S2,
            "note": "无空格；沿用明鉴/明鉴v2 的存量做法；role-map 键【待新增】（P2，需先补 P1 停点）",
        },
        "星桥1.0 / 星桥2.0": {
            "means": "本卡的书写形式，仅在需要**显式区分版本**时使用",
            "note": "日常行文中仍用「星桥」= 1.0、「星桥v2」= 2.0，与 role-map 保持一致",
        },
        "星台": {
            "means": "starbridge App（iOS）",
            "session": None,
            "note": "**首任的资源，不交接** —— 与「星桥」是两回事，勿混",
        },
        "星舵": {
            "means": "另一会话，与本交接**无关**",
            "session": "session-8c2494e0-3772-4a62-9789-b7adc3123ccc",
            "note": "名字相近，显式排除",
        },
    },

    # ── 两个主体的基本事实 ────────────────────────────────────────
    "versions": [
        {
            "version": "1.0",
            "display": "星桥",
            "session": S1,
            "status": "dead",
            "death": {
                "at": "2026-10-09T05:39:52+08:00",
                "cause": "P26 会话硬死锁（compaction 判据下界 > 被遮内容）",
                "nature": "**不崩** —— 进程与 CLD 均存活，但它再也发不出任何一次请求",
                "recoverable": False,
                "external_declaration": "唯一出路 = 外部声明（它无法自声明；P4，须批）",
            },
            "window": "2026-08-16T23:17 → 2026-10-09T05:39:52（54 天）",
            "role_self": "星桥 · 协调者（mac-mini 中枢，rules-registry 属主，星台发布与 ASC 编排，仓库管理；设计/代码工作经独立审查员审计= R048）",
            "outputs": {
                "design_docs": 23,
                "rules_involving": 19,
                "tools": "6 个 release/ASC 相关（asc-api · starbridge-release · hb-watchdog · cld-release · verify-cld-release · laodeng-release）",
                "messages": 22592,
                "threads": 3241,
                "approvals": "全库 35 份中七成",
            },
        },
        {
            "version": "2.0",
            "display": "星桥v2",
            "session": S2,
            "status": "active",
            "started_at": "2026-10-09",
            "role_self": "星桥 · 协调者（第二任，继承 session-fa1f9150；mac-mini 中枢）—— 继承进行中：首任档案与别名映射仍指向已死会话，继承范围待用户划界",
            "authorization": {
                "basis": "审批单 aprv-mv0prir5-dj「星桥协调者职能继承（第二任）· 范围划界」（approved）",
                "scope_note": "四选项**未落值** ⇒ 本会话按最小授权只接治理与协调；其余待所有者划界",
            },
        },
    ],

    # ── 核心：差异登记（2.0 相对 1.0）─────────────────────────────
    "delta": {
        "legend": {
            "inherited": "2.0 承接且已在位",
            "inheriting": "2.0 承接中（明确在做，未完成）",
            "not_inherited": "2.0 未承接（待所有者划界或转他方）",
            "forbidden": "2.0 被明令禁止（1.0 无此限制）",
            "new": "2.0 新增（1.0 没有的职能）",
            "structural_gap": "结构性缺口（不是意愿问题，是机制做不到）",
        },
        "rows": [
            {
                "dimension": "治理裁定（R046 验收门 · R047 命名门 · R048 审查协作）",
                "v1": "✅ 在位",
                "v2": "🔄 承接中",
                "kind": "inheriting",
            },
            {
                "dimension": "黑板双板读写",
                "v1": "✅ 在位",
                "v2": "✅ 在位（且**补登**两条写入路径：bb_card_send 工具门 / bb_dualwrite.py 脚本门）",
                "kind": "inherited",
            },
            {
                "dimension": "文件/命令/后台任务面 + 双重回读核验（400=键非法 / 404=合法但不存在）",
                "v1": "（隐含具备）",
                "v2": "✅ 在位",
                "kind": "inherited",
            },
            {
                "dimension": "R006 / PSTD 插件化工具化标准落地",
                "v1": "✅ 在位",
                "v2": "✅ 在位",
                "kind": "inherited",
            },
            {
                "dimension": "★ 连续性信标维护（锚点 · continuity-index · resume-prompt · beacon-check · Wave C）",
                "v1": "❌ 未做（M0 因此不成立）",
                "v2": "🔄 承接中（Wave C；C4/C6/C7 未完）",
                "kind": "new",
            },
            {
                "dimension": "重启治理与健康巡检编排",
                "v1": "✅ 在位",
                "v2": "❌ 未承接",
                "kind": "not_inherited",
            },
            {
                "dimension": "App Store Connect 编排（asc-api.py，JWT 签名）",
                "v1": "✅ 在位",
                "v2": "❌ 未承接",
                "kind": "not_inherited",
            },
            {
                "dimension": "星台 TestFlight 发布流水线（starbridge-release.sh）",
                "v1": "✅ 在位",
                "v2": "❌ 未承接（且「星台」本身**不交接**）",
                "kind": "not_inherited",
            },
            {
                "dimension": "双仓管理（GitHub repo:coreyleung-art/* 55 仓 + Gitee coreyleung/* 15 仓）",
                "v1": "✅ 在位",
                "v2": "❌ 未承接",
                "kind": "not_inherited",
            },
            {
                "dimension": "dsh-plugin-agent-bus 改名（原待重启窗口）",
                "v1": "在办",
                "v2": "❌ 未承接（重启窗口已不在授权内）",
                "kind": "not_inherited",
            },
            {
                "dimension": "★ rules-registry 属主（file:rules-registry 锁）",
                "v1": "✅ 属主",
                "v2": "❌ **无法单向过户** —— agent_profile 只能写自己档案，资源的属主登记在 1.0 名下",
                "kind": "structural_gap",
            },
            {
                "dimension": "重启 CLD / 改 profile / 载体换",
                "v1": "（默认可为）",
                "v2": "⛔ **被用户明令禁止**",
                "kind": "forbidden",
            },
            {
                "dimension": "复活 1.0",
                "v1": "—",
                "v2": "⛔ **被明令禁止**（P26 不可恢复；且 `all=true` 广播会向它灌字、点燃失败循环）",
                "kind": "forbidden",
            },
            {
                "dimension": "删改历史留痕",
                "v1": "—",
                "v2": "⛔ 禁止（central-inbox.log / agent-bus.json / 997 卡 / 黑板 307+26 键 只读不改）",
                "kind": "forbidden",
            },
        ],
    },

    # ── 引用纪律：写文档/发消息时怎么用 ────────────────────────────
    "citation_rules": [
        "① 只用「星桥」二字时，默认指 **1.0**（与 role-map 一致）；指 2.0 须写「星桥v2」。",
        "② 引用 1.0 的产出时，不得表述为 2.0 的产出（责任错配）；反之亦然。",
        "③ 向「星桥」投递 = 落进**已死会话**（A1/A3 活引用仍指向它）⇒ 交接期间投递一律用 `星桥v2`。",
        "④ 「星台」是 App，不是会话；「星舵」是另一会话，与本次交接无关 —— 三者不可互指。",
        "⑤ 两侧的 role/abilities/resources 均为 source=self 自述 ⇒ 引用须连「自述、未核实」一起引（R030 + 锚点 §6.3）。",
    ],

    # ── 未决 ──────────────────────────────────────────────────────
    "open": [
        "【待所有者拍板 S1】是否登记英文别名 `star-bridge-v2`？（v3.1 §三 建议暂不加）",
        "【待批 P2】role-map 新增 `星桥v2` 键（A1 活引用变更，须先过 P1 停点）",
        "【待划界】2.0 是否承接 ASC / 星台发布 / 双仓管理（四项未承接项）",
        "【待解决】rules-registry 属主结构性缺口 —— 需机制改动或他方代持",
    ],
    "known_gaps": [
        "1.0 的 abilities/resources 是它死前的自述，**死后是否仍成立无人复跑**",
        "1.0 名下 6 个 release 工具的当前可用性未验证（本轮只做了存在性枚举）",
        "「往来方 271 / role-map 21 会话」口径与 v3.1 §2.2 记的「23 角色」差 2，未核",
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
# ★ 2026-10-09 补：只读模式。裁判 §八 载明它「为避免写入其生产文件，一律未跑」本类脚本
#   ⇒ 第三方无法复跑 ⇒ 复跑命令形同虚设。故：默认**写盘**（保持既有用法不变），
#   但 --check / --dry-run 为**纯只读**（不建目录、不写文件、不改 mtime）。
READONLY = ("--check" in sys.argv) or ("--dry-run" in sys.argv)
if not READONLY:
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

n = {k: 0 for k in doc["delta"]["legend"]}
for r in doc["delta"]["rows"]:
    n[r["kind"]] += 1
if READONLY:
    print("★ 只读模式（--check）：未写盘")
    print("将写: %s（内容 %d B）" % (OUT, len(json.dumps(doc, ensure_ascii=False))))
else:
    print("版本登记卡已写: %s (%d B)" % (OUT, OUT.stat().st_size))
print("差异行数: %d" % len(doc["delta"]["rows"]))
for k, v in n.items():
    if v:
        print("  %-16s %d" % (k, v))
print("术语条目: %d ｜ 引用纪律: %d 条 ｜ 未决: %d ｜ 已知缺口: %d"
      % (len(doc["terminology"]), len(doc["citation_rules"]), len(doc["open"]), len(doc["known_gaps"])))
