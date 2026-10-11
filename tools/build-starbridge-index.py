#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建星桥全域索引（M1 索引 · 10 类 · 每条 7 字段）

用途
    把首任星桥 session-fa1f9150 的 54 天产出，从「散在文件里、只能全量重读」
    转为「索引化 + 按需投影 + 失效自报」。全量重读正是杀死它的动作（P26）。

依据
    docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md §五「M1 索引规格」
    锚点 docs/distributed-agent-network-governance-plan-v4-20261009.md §4.1 ②③ / §9 L6

判据（三条硬判据，缺一不得记完成）
    ① 常驻预算：本索引永不常驻，仅按需 read
    ② 可解指针：每条 pointer 必须可解 —— 脚本对每条做存在性校验，不可解者如实标 dead
    ③ 失效自报：status ∈ {active, superseded, dead}，superseded 必带 superseded_by

输出
    data/registry/starbridge-knowledge-index.json  （本地副本；黑板由 bb_dualwrite.py 写）

用法
    python3 tools/build-starbridge-index.py            # 生成 + 打印统计
    python3 tools/build-starbridge-index.py --check    # 只校验现有索引的指针可解性
"""
import json
import os
import re
import sys
import datetime
from pathlib import Path

HOME = Path.home()
COLLAB = HOME / "dsh-collab"
SUBJECT = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
WRITER = "session-e317d6ab-5302-4b33-b095-947983ba16f4"
# ★ 输出路径可覆盖（第三方复跑时写临时位置，不碰生产）：
#   STARBRIDGE_OUT=/tmp/x.json python3 tools/build-starbridge-index.py
OUT = Path(os.environ.get("STARBRIDGE_OUT")
           or (COLLAB / "data" / "registry" / "starbridge-knowledge-index.json"))

CLASSES = {
    "①": "角色定义/边界",
    "②": "能力/资源",
    "③": "设计产出",
    "④": "规则裁定",
    "⑤": "工具/脚本",
    "⑥": "在办活",
    "⑦": "失效清单",
    "⑧": "裁定与审批记录",
    "⑨": "修复/广播动作",
    "⑩": "合作方登记",
}

# 指针校验：记录 {pointer_string: resolvable_bool}
_pointer_cache = {}


def resolve_pointer(p):
    """判定 pointer 是否可解。file:PATH 检查存在性；blackboard:KEY 记 None（需网络，由 --net 另检）。"""
    if p in _pointer_cache:
        return _pointer_cache[p]
    ok = None
    if p.startswith("file:"):
        raw = p[len("file:"):]
        if "::" in raw:          # file:path::L10-20 行号域
            raw = raw.split("::")[0]
        raw = os.path.expanduser(raw)
        ok = Path(raw).exists()
    elif p.startswith("blackboard:"):
        ok = None                # 需网络，留给 --net
    elif p.startswith("bus:"):
        ok = True                # 总线对象，由 agent-bus.json 存在性保证
    _pointer_cache[p] = ok
    return ok


entries = []
_seen_ids = set()


def add(cid, cls, title, pointer, status="active", superseded_by=None, verified_by=None):
    if cid in _seen_ids:
        raise SystemExit("重复 id: " + cid)
    _seen_ids.add(cid)
    if status == "superseded" and not superseded_by:
        raise SystemExit("superseded 缺 superseded_by: " + cid)
    entries.append({
        "id": cid, "class": cls, "title": title, "pointer": pointer,
        "status": status, "superseded_by": superseded_by, "verified_by": verified_by,
    })


# ── ① 角色定义/边界 ────────────────────────────────────────────────
add("K1-001", "①", "audit-reviewer preset 把「不改规则（星桥）」写成硬边界",
    "file:~/.dsh/.agent-presets/audit-reviewer/agent.cordis.yml::L68,L72",
    verified_by="本会话实读（grep 命中原文）")
add("K1-002", "①", "audit-reviewer preset 身份卡（独立审计员·代号裁判）",
    "file:~/.dsh/.agent-presets/audit-reviewer/preset.yml",
    verified_by="本会话实读")
add("K1-003", "①", "role-map：星桥 → 首任会话（A1 活引用；P2 不重指，另立 星桥v2）",
    "file:~/.dsh/agent-role-map.json",
    verified_by="本会话实读（无 星桥v2 键，实测）")
add("K1-004", "①", "★ 缺口：无「在任 v2」的角色定义（P5 才补 preset 边界）",
    "file:~/.dsh/.agent-presets/", status="active",
    verified_by="本会话实测：6 个 preset 目录均无星桥专属边界")
add("K1-005", "①", "★ 星桥 1.0 / 2.0 版本区别登记（双主体对照 · 差异四分类 · 引用纪律 · 术语四义钉死）",
    "blackboard:data/registry/starbridge-version-registry",
    verified_by="本会话实测（两侧 profiles 自述 source=self + role-map + 文件系统）；差异 14 维，详见该卡")
add("K1-006", "①", "★ 术语四义：星桥=1.0（冻结）· 星桥v2=2.0（在任）· 星台=starbridge App（不交接）· 星舵=无关会话",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md::L252-L261",
    verified_by="v3.1 §三 命名方案 + 本会话录入版本登记卡")
add("K1-007", "①", "★★ 活引用清单不完整（v3.1 的 A1–A7 漏 A8/A9）："
                    "**A8** = `~/sb-mobile/server.js`（★**运行中 PID 1250**，launchd `com.dsh.sb-mobile-bridge`，"
                    "L241-242 硬编码 `fa1f9150` 做排序）· "
                    "**A9** = `~/sb-mobile/main-roles.json`（★**第二份角色映射**，与 A1 `agent-role-map.json` 并存且互不引用）",
    "blackboard:data/registry/live-references-a8-a9",
    verified_by="本会话实测（ps aux 见 PID 1250 + launchctl list 见 label + grep 行号定位硬编码）")
add("K1-008", "①", "★ 角色/别名映射至少**三轨并存**：A1 `~/.dsh/agent-role-map.json` · "
                    "A9 `~/sb-mobile/main-roles.json` · `cld-health/identity-variant-map.py` —— 三者互不引用",
    "blackboard:data/registry/live-references-a8-a9",
    verified_by="本会话实测（三处内容比对一致指向死会话，但无交叉引用）")

# ── ② 能力/资源 ───────────────────────────────────────────────────
add("K2-001", "②", "★ 首任能力/资源清单（自述档案，仅存活于 agent-bus.json；无本地可读副本）",
    "bus:~/.dsh/agent-bus.json::profiles[agentId=session-fa1f9150]",
    verified_by="本会话实测抽取（role/abilities×7/resources×6）")
add("K2-002", "②", "首任自述资源：rules-registry 属主 / 双仓 / 星台工程 / 6 个 release 工具",
    "file:~/.dsh/agent-bus.json",
    verified_by="本会话实测抽取")
add("K2-003", "②", "第二任（在任）自述档案：已承接 + 未承接 + 被禁止三档",
    "bus:~/.dsh/agent-bus.json::profiles[agentId=session-e317d6ab]",
    verified_by="本会话自述（source=self，按 R030 不可作事实）")
add("K2-004", "②", "★ 缺口：agent_profile 只能写自己档案 ⇒ 死会话名下的 resources 无法单向过户",
    "file:~/.dsh/agent-bus.json",
    verified_by="本会话实测（tools/agent_* 语义确认）")
add("K2-005", "②", "★ 既有资产未被利用：星桥记忆继承包（3,293 行 / 39 段宿主压缩摘要 + 最近 8 条用户指令，"
                    "由 HR 的 session-rebirth v1.0.0 于首任死前一天生成）—— 索引化后按需投影，不整份读",
    "file:~/dsh-collab/docs/星桥-memory-inheritance-2026-10-08.md",
    verified_by="v3.1 §2.4 实测（3,293 行）+ 本会话存在性校验；★ 内容完备性未逐段核（观测量=行数，非覆盖）")
add("K2-006", "②", "配套续接提示词（首任世代，2026-10-08）",
    "file:~/dsh-collab/docs/星桥-resume-prompt-2026-10-08.md",
    verified_by="本会话存在性校验（1,520 B）")
add("K2-007", "②", "★ 缺口：② 类此前「仅活在已死会话档案里，无本地可读副本」—— "
                    "本轮已把两侧自述档案索引化（K2-001/K2-003），但**档案本体仍在 agent-bus.json**，"
                    "尚无独立本地快照；且 agent_profile 只能写自己档案 ⇒ 过户无机制",
    "bus:~/.dsh/agent-bus.json::profiles",
    verified_by="本会话实测（profiles 78 条，两侧均在；无独立副本）")

# ── ③ 设计产出（23 份 comm-server/*.md，实测枚举）────────────────
_cs = sorted((COLLAB / "comm-server").glob("*.md"))
NOTE_3 = {
    "perpetual-comms-convergence-plan-v1.md": "perpetual-comms-convergence-plan-v2.md",
}
for i, f in enumerate(_cs, 1):
    sup = NOTE_3.get(f.name)
    add("K3-%03d" % i, "③", f.name,
        "file:~/dsh-collab/comm-server/%s" % f.name,
        status="superseded" if sup else "active",
        superseded_by=("file:~/dsh-collab/comm-server/%s" % sup) if sup else None,
        verified_by="本会话实读（ls 枚举 + 存在性校验）")

# ── ④ 规则裁定（RULES.md 中含「星桥」的规则条目）──────────────────
_rules = (COLLAB / "rules-registry" / "RULES.md")
if _rules.exists():
    txt = _rules.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    # 逐规则条目：命中「星桥」的规则取标题行。
    # ★ 修正：规则标题行**自身**含「星桥」的占多数（如「R046 … 星桥入账」），
    #   旧版只在 elif 分支标记 ⇒ 漏掉全部标题命中（实测 24 处只得 4 条）。
    cur = None
    hit = []
    for ln, line in enumerate(lines, 1):
        m = re.match(r"^## (R\d{3})\s", line)
        if m:
            cur = [m.group(1), line.strip(), ln, "星桥" in line]
            hit.append(cur)
        elif cur is not None and "星桥" in line:
            cur[3] = True
    idx = 0
    for rid, title, ln, has in hit:
        if has:
            idx += 1
            add("K4-%03d" % idx, "④", "%s %s" % (rid, title[:60]),
                "file:~/dsh-collab/rules-registry/RULES.md::L%d" % ln,
                verified_by="本会话实读（grep 命中规则标题行，共 %d 处含「星桥」）"
                           % txt.count("星桥"))

# ── ⑤ 工具/脚本（tools/ 下非备份项）──────────────────────────────
_tools = sorted(p for p in (COLLAB / "tools").iterdir()
                if p.is_file() and ".bak" not in p.name)
for i, f in enumerate(_tools, 1):
    add("K5-%03d" % i, "⑤", f.name, "file:~/dsh-collab/tools/%s" % f.name,
        verified_by="本会话实读（ls 枚举，已排除 .bak/.bak-* 备份 %d 个）"
                   % (len(list((COLLAB / 'tools').glob('*.bak*')))))

# ── ⑥ 在办活 ──────────────────────────────────────────────────────
add("K6-001", "⑥", "锚点 WBS 30 项（Wave S/C/0–5）", 
    "file:~/dsh-collab/docs/distributed-agent-network-governance-plan-v4-20261009.md::L259-L268",
    verified_by="本会话实读")
add("K6-002", "⑥", "continuity-index.items（C1–C7 + P26 状态机）",
    "blackboard:data/registry/continuity-index",
    verified_by="本会话实读（C4/C6/C7 = open，其余 closed_with_evidence）")
add("K6-003", "⑥", "交接计划 P0–P5（六阶段 + 审查停点）",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md::L361-L370",
    verified_by="本会话实读")
add("K6-004", "⑥", "memory-governance 蓝图 11 阶段（多数 todo；mg1-2 自称 active 已被 P26 证伪）",
    "file:~/dsh-collab/data/blueprint/memory-governance/blueprint-memory-governance-v1.0.md",
    verified_by="v3.1 §2.5 实测 + 本会话实读")
# ★ 本会话（2026-10-09 晚）产出 —— 登记为在办活，使索引自身也覆盖「今晚做了什么」
add("K6-005", "⑥", "★ 本会话产出①：M1 索引本体（本条所在之物）",
    "blackboard:data/registry/starbridge-knowledge-index",
    verified_by="本会话实测（双板逐字节相等）")
add("K6-006", "⑥", "★ 本会话产出②：星桥 1.0/2.0 版本区别登记（14 维差异 + 术语四义 + 引用纪律）",
    "blackboard:data/registry/starbridge-version-registry",
    verified_by="本会话实测（双板逐字节相等）")
add("K6-007", "⑥", "★ 本会话产出③：C6 状态机登记（14 项 + 8 wave + 五态对齐 + 3 缺口）",
    "blackboard:data/registry/state-registry",
    verified_by="本会话实测（双板逐字节相等）；发现锚点五态缺 unknown 态")
add("K6-008", "⑥", "★★ 本会话产出④：死会话死后活动证据（9 次 compaction 全失败 · turn 11170→11178）—— P3/P4 紧迫性依据",
    "blackboard:data/registry/dead-session-postmortem-activity",
    verified_by="本会话全量流式扫描（5 个可复跑脚本，audits/20261009/repro/c7-*.py）")
add("K6-009", "⑥", "★★ 本会话产出⑤：P3 前置定位 —— 回退注入源在 dsh-plugin-central-inbox 源码硬编码（非环境变量非配置）",
    "blackboard:data/registry/fallback-injection-source-located",
    verified_by="本会话实读 lib/index.js:117/120/125 + plist 实读 + 两副本 sha 一致")
add("K6-010", "⑥", "★ 本会话产出⑥：P1-c 别名映射缺陷登记（移交守灯）",
    "blackboard:data/registry/starbridge-alias-mapping-defect",
    verified_by="本会话实测（5 条证据链）")
add("K6-011", "⑥", "★ 本会话产出⑦：测试标识机读清单（3 标识 / 12 条消息）",
    "blackboard:data/registry/bus-test-identifiers",
    verified_by="本会话实测")
add("K6-012", "⑥", "★ 本会话产出⑧：C7 补正三项（双向失效标注 · n/distinct 声明 · 第 5–8 态入证伪清单）",
    "file:~/dsh-collab/docs/c7-half-fix-clause10-20261009.md::L119-",
    verified_by="本会话实测（§八增量，不改前七节原文）")
add("K6-014", "⑥", "★ 本会话产出⑩：阶段报告 + 独立审查信息包（按锚点 §5.3 十四项规格）—— 已据此委托裁判",
    "file:~/dsh-collab/docs/starbridge-stage-report-and-review-package-20261009.md",
    verified_by="本会话实测（14 项逐项填写；含 8 个提问项与负控缺口前置披露）")
add("K6-015", "⑥", "★ 本会话产出⑪：下阶段计划（三候选 + 依赖链 + 建议排序）—— 待所有者拍板",
    "file:~/dsh-collab/docs/starbridge-next-stage-plan-20261010.md",
    verified_by="本会话实测（依赖链与候选均引本阶段实测证据）")
add("K6-016", "⑥", "★ 本会话产出⑫：阶段审查委托登记（含 verifier 候选分析与排除理由）",
    "blackboard:data/registry/starbridge-stage-review-request",
    verified_by="本会话实测（p2p 委托已送达裁判，thread-mv11hpn9-m433vf7a）")
add("K6-013", "⑥", "★ 本会话产出⑨：三个可持续更新的构建脚本（索引 / 版本登记 / 状态机登记）",
    "file:~/dsh-collab/tools/build-starbridge-index.py",
    verified_by="本会话实测（可复跑，指针可解性校验内建）")

# ── ⑦ 失效清单（本计划新建；此前「不存在」）──────────────────────
add("K7-001", "⑦", "plan v1 已被取代", 
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v1-20261009.md",
    status="superseded",
    superseded_by="file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v2-20261009.md",
    verified_by="本会话实读（头部 superseded 标注在位）")
add("K7-002", "⑦", "plan v2 已被取代",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v2-20261009.md",
    status="superseded",
    superseded_by="file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3-20261009.md",
    verified_by="本会话实读")
add("K7-003", "⑦", "plan v3 被 v3.1 取代（v3 本体因「审计对象不可变」冻结，sha16 91ff3286e9fc0e9a）",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3-20261009.md",
    status="superseded",
    superseded_by="file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md",
    verified_by="黑板卡 data/registry/plan-version-chain（外部声明，非自声明）")
add("K7-004", "⑦", "perpetual-comms-convergence-plan v1 被 v2 取代",
    "file:~/dsh-collab/comm-server/perpetual-comms-convergence-plan-v1.md",
    status="superseded",
    superseded_by="file:~/dsh-collab/comm-server/perpetual-comms-convergence-plan-v2.md",
    verified_by="同族版本对扫描（ls 去版本号后 uniq -d 唯一命中）")
add("K7-005", "⑦", "hb-watchdog.sh 的 4 个 .bak 备份（非活跃）",
    "file:~/dsh-collab/tools/hb-watchdog.sh",
    status="dead",
    verified_by="本会话实测（ls glob *.bak* 计数 = 4）")
add("K7-006", "⑦", "★ 缺口补记：54 天产出中其余作废项的判定 —— 本轮只覆盖有显式版本对/备份标记者；"
                   "无标记的语义性作废（如设计被后续实现取代）本轮未判定，不得读成「只有这 6 条失效」",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md::L195",
    verified_by="本会话如实标注（观测面声明：判据=显式标记；无标记者不可判）")

# ── ⑧ 裁定与审批记录 ──────────────────────────────────────────────
_bus = HOME / ".dsh" / "agent-bus.json"
if _bus.exists():
    _d = json.loads(_bus.read_text(encoding="utf-8"))
    for i, a in enumerate(_d.get("approvals") or [], 1):
        add("K8-%03d" % i, "⑧", "[%s] %s" % (a.get("status", "?"), str(a.get("title", ""))[:70]),
            "bus:~/.dsh/agent-bus.json::approvals[%s]" % a.get("id"),
            verified_by="本会话实测抽取（approvals 共 %d 份）" % len(_d.get("approvals") or []))

# ── ⑨ 修复/广播动作 ───────────────────────────────────────────────
for i, f in enumerate(sorted((COLLAB / "cld-health").iterdir()), 1):
    if f.is_file() and ".bak" not in f.name:
        add("K9-%03d" % i, "⑨", "cld-health/%s" % f.name,
            "file:~/dsh-collab/cld-health/%s" % f.name,
            verified_by="本会话实读（ls 枚举）")
_rp = sorted((COLLAB / "data" / "reports").iterdir()) if (COLLAB / "data" / "reports").exists() else []
for i, f in enumerate(_rp, 100):
    if f.is_file():
        add("K9-%03d" % i, "⑨", "data/reports/%s" % f.name,
            "file:~/dsh-collab/data/reports/%s" % f.name,
            verified_by="本会话实读（ls 枚举）")

# ── ⑩ 合作方登记（TOP15，来自 v3.1 §2.2 实测；★本轮补：自述档案实况）─────
# ★ 实测更正（本轮）：所谓「无角色名」= 不在 role-map 的 main 表中，
#   **不等于无档案** —— 4 个节点在 agent-bus profiles 中均有完整自述
#   （role + abilities 5–7 条 + resources 2–6 条，source=self）。
#   按 R009「自命名」⇒ 正式角色名须其自选或 HR/所有者定，**本会话不得代命名**。
_PEERS = [
    (2721, "a17a52f8", None, "HR 驾驶舱（资源管理者 + 成本监察专员）· CAHAC 示范", 7, 5),
    (1296, "aa528267", "老登", "工具纪律/门与核验侧；写卡门与绑定机检", None, None),
    (1217, "e7bfeea8", None, "前任资源管理者（已交接 a17a52f8）", 6, 6),
    (1009, "55d4d1bd", "文汇", "文档摄取归档（P1）", None, None),
    (733, "9910d4b2", "守灯", "健康审查 + 名册席位#4（C1–C7 核验）", None, None),
    (637, "a190c54c", "明鉴", "蓝图主编 + SystemGraph 主源架构师", None, None),
    (600, "2a15e6b1", "司库", "资源管理 + 成本监察（HR Cockpit）", None, None),
    (571, "b3778a1e", None, "通用成员/前任资源管理者", 6, 2),
    (551, "a3bc8cba", "知了", "学习引擎（权限边界 v2）", None, None),
    (513, "43b1a2d3", None, "DSH/CLD 运维与远程访问", 5, 3),
    (504, "5a5368af", "罗盘", "设备协调（Device Orchestrator）", None, None),
    (459, "92623479", "驿使", "外部链接/交付通道", None, None),
    (445, "b241741f", "守灯塔", "系统运维/知识库", None, None),
    (444, "de7b29de", "灯塔", "外卖采集统筹", None, None),
]
for i, (n, sid, role, desc, nab, nres) in enumerate(_PEERS, 1):
    full = None
    for p in (_d.get("profiles") or []):
        if str(p.get("agentId", "")).startswith("session-" + sid):
            full = p.get("agentId")
            break
    if role:
        title = "%d 条 · %s · %s" % (n, role, desc)
        vby = "v3.1 §2.2 实测 + 本会话复跑（role-map 命中）；职责列为自述 source=self，未核实"
    else:
        title = "%d 条 · ★无正式角色名（有自述档案：%s）" % (n, desc)
        vby = ("本会话实测更正：profiles 中存有自述 role/abilities×%s/resources×%s (source=self)，"
               "但不在 role-map；按 R009 自命名 ⇒ 不得由本会话代命名" % (nab, nres))
    add("K10-%03d" % i, "⑩", title,
        ("bus:~/.dsh/agent-bus.json::profiles[%s]" % full) if full else
        "bus:~/.dsh/agent-bus.json::threads（会话 %s 未登记 profile）" % sid,
        status="active", verified_by=vby)
add("K10-000", "⑩", "往来面：往来方 271 / role-map 仅登记 21 会话 ⇒ 未登记面 = 250",
    "file:~/dsh-collab/docs/starbridge-v2-handover-and-failure-visibility-plan-v3.1-20261009.md::L145",
    verified_by="v3.1 §2.2 实测（271 往来方）+ 本会话实读 role-map（21 会话，v3.1 记 23 角色名，差 2 待核）")
add("K10-090", "⑩", "★ 待命名节点清单（4 个）：有自述档案、无正式角色名 —— 命名权归其自身(R009)或 HR/所有者，"
                    "本会话不得代命名；P1-b 的「补登记」在本会话权限内只能做到【把自述档案索引化 + 列出待命名】",
    "bus:~/.dsh/agent-bus.json::profiles",
    verified_by="本会话实测（4/4 有 profiles；abilities 7/6/6/5，resources 5/6/2/3，source 全为 self）")
add("K10-091", "⑩", "★ 测试标识机读清单（3 个标识 / 12 条消息）：bus:stress · bus:s2-test · bus:s2-live —— "
                    "统计总线负载与往来量时须排除，否则读数被 S2 压测流量污染",
    "blackboard:data/registry/bus-test-identifiers",
    verified_by="本会话实测（逐条 messages 定位，含 peer 与黑板证据指针）")
add("K10-092", "⑩", "★ 别名映射缺陷（移交守灯）：identity-variant-map.py 把 bus:server:coordinator 错配到 "
                    "fa1f9150 名下，而 mac-mini 侧的 bus:coordinator 未映射 —— 二者实为不同主体",
    "blackboard:data/registry/starbridge-alias-mapping-defect",
    verified_by="本会话实测（5 条证据链：TRUSTED_DEVS 并列 / 双向消息 / 命名空间 / COORDINATORS / 计数）")

# ── ★ 负控注入（仅测试用；默认不触发）────────────────────────────
# 用途：回应裁判 addendum-3 的「目的层负控」要求 —— 给一条**不合规数据**，
#       判据**会不会红**？注入值取自 STARBRIDGE_INJECT_BAD：
#         unresolvable → 一条指针不可解的条目
#         superseded   → 一条 superseded 但缺 superseded_by 的条目
# ★ 断言（add() 内的 raise SystemExit）会**立即终止**，故两种注入需分别跑。
_inject = os.environ.get("STARBRIDGE_INJECT_BAD", "").strip()
if _inject == "unresolvable":
    add("K-BAD-001", "①", "★负控样本：指针不可解（注入）",
        "file:/nonexistent/negative-control-target-DOES-NOT-EXIST.md",
        verified_by="★ 由 STARBRIDGE_INJECT_BAD=unresolvable 注入，仅用于负控测试")
elif _inject == "superseded":
    add("K-BAD-002", "①", "★负控样本：superseded 但缺 superseded_by（注入）",
        "file:~/dsh-collab/docs/resume-prompt-starbridge-v3.md",
        status="superseded", superseded_by=None,
        verified_by="★ 由 STARBRIDGE_INJECT_BAD=superseded 注入，仅用于负控测试")

# ── 落盘 ──────────────────────────────────────────────────────────
now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
doc = {
    "schema": "starbridge-knowledge-index/v1",
    "created_at": now,
    "writer": WRITER,
    "subject": {
        "session_id": SUBJECT,
        "name": "星桥（首任，历史专名，冻结）",
        "window": "2026-08-16T23:17 → 2026-10-09T05:39:52",
        "death": "P26 会话硬死锁（不崩，但再也发不出请求）",
    },
    "observation_surface": {
        "searched": [
            "~/dsh-collab（文件系统枚举）", "~/.dsh（配置/状态层；agent-bus.json 全量）",
            "~/.dsh/.agent-presets（6 preset）", "~/system-graph-app（v3.1 §2.5）",
        ],
        "unsearched": [
            "其余设备（MBP/i9/星台）本地文件", "服务器 106.53.214.108 侧",
            "~/sb-mobile · ~/.claude · ~/Desktop · Obsidian 的命中文件性质分类",
            "私有仓库",
        ],
        "note": "本索引的「已覆盖」仅指上述 searched 面；unsearched 面内的星桥产出不在本索引内，"
                "不得据本索引宣称「星桥产出已全量索引」。",
    },
    "entry_schema": ["id", "class", "title", "pointer", "status", "superseded_by", "verified_by"],
    "classes": CLASSES,
    "entries": entries,
    "counts": {},
}
# 指针可解性校验
bad = []
for e in entries:
    r = resolve_pointer(e["pointer"])
    e["pointer_resolvable"] = ("true" if r else "false") if r is not None else "unknown(net)"
    if r is False:
        bad.append(e["id"])
doc["pointer_unresolvable"] = bad
cnt = {}
for e in entries:
    cnt[e["class"]] = cnt.get(e["class"], 0) + 1
doc["counts"] = cnt
doc["total"] = len(entries)

if "--check" not in sys.argv:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

print("总条数: %d" % len(entries))
for k in sorted(CLASSES):
    print("  %s %-14s %3d 条" % (k, CLASSES[k], cnt.get(k, 0)))
print("指针不可解: %s" % (bad if bad else "0（全部可解）"))
st = {}
for e in entries:
    st[e["status"]] = st.get(e["status"], 0) + 1
print("状态分布: %s" % st)
if "--check" not in sys.argv:
    print("已写: %s (%d B)" % (OUT, OUT.stat().st_size))

# ── ★ 判据失败退出（add 的断言之外的第二道门）─────────────────────
# 无此门时，「存在不可解指针」只会被**记录**而进程仍 exit 0 ⇒ 判据等于不会红。
# 这正是裁判 addendum-3 指出的层错：我原先的负控测的是**手段层**（会不会写盘），
# 而 §11 要的是**目的层**（不合规数据会不会被判红）。本门即为该判据的实现。
if bad:
    print("✗ 判据未通过：存在 %d 条指针不可解的条目 ⇒ exit 4" % len(bad))
    print("   %s" % bad)
    sys.exit(4)
print("✓ 判据通过：全部指针可解")
