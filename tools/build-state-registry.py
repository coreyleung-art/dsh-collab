#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C6 · 状态机登记（对齐 item-validity-review-check 五态）

任务来源
    锚点 §10 Wave C：**C6 状态机登记（对齐 item-validity-review-check 五态）** —— 未做
    锚点 §4.2：`open → in_flight → closed_with_evidence →(回归) regressed → in_flight`；
             旁支 `blocked(reason, owner, next_action)`；closure 三要素 = DoD · evidence · verifier

本脚本做什么
    ① 从 continuity-index（items + waves）汇总全部项
    ② 把每项映射到统一五态
    ③ **机械校验** closure 三要素是否齐（不齐的如实标出，不补全）
    ④ 与 item-validity-review-check 的五态建立**显式映射**，并指出**我方缺失的态**
    ⑤ 输出 data/registry/state-registry.json

本脚本不做什么
    不改任何被登记项的状态；不为任何项出具裁定；不凭空补 evidence（R030）。
"""
import json
import os
import sys
import datetime
from pathlib import Path

HOME = Path.home()
COLLAB = HOME / "dsh-collab"
CINDEX = COLLAB / "data" / "registry" / "continuity-index.json"
# ★ 输出路径可覆盖（第三方复跑时写临时位置，不碰生产）：
#   STARBRIDGE_OUT=/tmp/x.json python3 tools/build-state-registry.py
OUT = Path(os.environ.get("STARBRIDGE_OUT")
           or (COLLAB / "data" / "registry" / "state-registry.json"))
WRITER = "session-e317d6ab-5302-4b33-b095-947983ba16f4"

# ── 锚点 §4.2 的五态（权威定义）────────────────────────────────
STATES = {
    "open": "已登记、未开始。无阻塞原因。",
    "in_flight": "进行中（有人在做，或已部分落地）。",
    "closed_with_evidence": "已关闭**且有证据**。closure 三要素必须齐：DoD（含边界+负控）· evidence（可解指针）· verifier（第三方，禁自证）。",
    "regressed": "曾 closed_with_evidence，后回归（原判据不再成立）。须重新走 in_flight。",
    "blocked": "旁支状态：明确阻塞。必须带 blocked_reason + owner + next_action 三字段。",
}

# ── 与 item-validity-review-check 的五态映射 ─────────────────────
IV_STATES = {
    "closed": "显式关闭声明或已见回复（通道 A/B）",
    "stale": "超窗/已被取代（疑似过期，须核依赖后才能关闭）",
    "open": "未关闭",
    "unknown": "★ 判不了（缺字段/缺时刻/通道不可见）⇒ 须补字段",
    "n/a": "不适用",
}

MAPPING = [
    {"ours": "open", "theirs": "open", "relation": "同义直接对应",
     "check": "一致"},
    {"ours": "in_flight", "theirs": "（无）", "relation": "★ item-validity 无「进行中」概念 —— "
     "它把条目当作待办二值（开/关），不区分「有人在做」",
     "check": "我方多一态；无冲突"},
    {"ours": "closed_with_evidence", "theirs": "closed", "relation": "★ **判据强度差距**："
     "item-validity 的 closed = 「状态类字段命中关闭词」（作者已声明不必再管）；"
     "我方要求三要素齐（DoD + 可解 evidence + 第三方 verifier）⇒ **同名的 closed 不是同一件事**",
     "check": "★ 须标注：不可跨表直接比较闭环率"},
    {"ours": "regressed", "theirs": "stale", "relation": "近似：都是「原以为关闭，实际失效」。"
     "差别：stale 的原因是「超窗/被取代」（时间/版本维），regressed 的原因是「原判据不再成立」（判据维）",
     "check": "近似但不等价"},
    {"ours": "blocked", "theirs": "unknown", "relation": "★★ **关键差异**："
     "item-validity 的 unknown =「**判不了**」（缺字段/缺时刻/通道不可见）；"
     "我方的 blocked =「**明确知道原因，但做不了**」（有 reason/owner/next_action）。"
     "⇒ 两者是**不同的东西**：一个是信息不足，一个是能力/授权不足",
     "check": "★ 不同义，不可互替"},
    {"ours": "（无）", "theirs": "unknown", "relation": "★★ **我方缺失此态**："
     "锚点五态里没有「判不了」。后果：一个「我判不了它是否完成」的项，会被迫二选一 —— "
     "记 open（谎称未开始）或记 blocked（谎称知道原因）。**两者都不准**。",
     "check": "★ **缺口**"},
    {"ours": "（无）", "theirs": "n/a", "relation": "我方缺失（不适用）。"
     "影响较轻：不适用项可归入 open 并被排除，但缺少显式标记",
     "check": "缺口（轻）"},
]

doc = {
    "schema": "state-registry/v1",
    "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "writer": WRITER,
    "item": "C6",
    "subject": "状态机登记（对齐 item-validity-review-check 五态）",
    "authority": "锚点 docs/distributed-agent-network-governance-plan-v4-20261009.md §4.2 / §10 Wave C",
    "states": STATES,
    "closure_rule": "六者齐备（§11）：正向 ∧ 负控红 ∧ 边界不崩 ∧ 阈值达标 ∧ 沙箱复跑一致 ∧ 官方条款无未声明差异 "
                    "⇒ 缺一不得记 closed_with_evidence",
    "alignment_with_item_validity": {
        "their_source": "docs/item-validity-index.json（2,642 条，generated_at 2026-10-08T18:49:19Z）"
                        " + devices/dsh-plugin-item-validity-review-check",
        "their_states": IV_STATES,
        "mapping": MAPPING,
        "conclusion": "★ 两套五态**不是同一套**：3 组可对齐（open / closed≈ / regressed≈stale）、"
                      "1 组不同义（blocked ≠ unknown）、1 组我方缺失（unknown = 判不了）。"
                      "⇒ 「对齐」的正确做法不是改名，而是**建立显式映射并标注不可比处**。"
                      "本条即该映射。",
    },
    "items": [],
    "waves": [],
    "gaps": [],
}

# ── 汇总 items ────────────────────────────────────────────────
if not CINDEX.exists():
    print("找不到 %s" % CINDEX)
    sys.exit(1)
ci = json.loads(CINDEX.read_text(encoding="utf-8"))
ANCHOR_SV = ci.get("state_version")

# 我方权限内可证的「已落」项（本轮实测产生）
LOCAL_DONE = {
    "M1-INDEX": {
        "name": "M1 索引（星桥全域索引 10 类）",
        "state": "in_flight",
        "note": "★ 本轮新建：data/registry/starbridge-knowledge-index（169 条 / 10 类 / 指针全可解 / 双板相等）。"
                "未记 closed_with_evidence：verifier 未指派（第三方禁自证）。",
        "evidence": ["blackboard:data/registry/starbridge-knowledge-index"],
        "dod": "10 类各 ≥1 且指针可解（已达标 10/10）；★ 负控未构造；verifier 未指派 ⇒ 三要素缺二",
        "verifier": None,
    },
    "P1-f": {
        "name": "星桥 1.0 / 2.0 版本区别登记",
        "state": "in_flight",
        "note": "★ 本轮新建：data/registry/starbridge-version-registry（14 维差异 + 术语四义 + 引用纪律）",
        "evidence": ["blackboard:data/registry/starbridge-version-registry"],
        "dod": "两主体分列 + 差异逐维 + 引用纪律（已达标）；★ 负控未构造；verifier 未指派",
        "verifier": None,
    },
    "P1-c-defect": {
        "name": "别名映射缺陷登记（移交守灯）",
        "state": "in_flight",
        "note": "★ 本轮新建：data/registry/starbridge-alias-mapping-defect。"
                "**待守灯裁决**（其属主），本会话不改他人文件。",
        "evidence": ["blackboard:data/registry/starbridge-alias-mapping-defect"],
        "dod": "证据链 5 条；★ 须守灯裁定 3 问 ⇒ 未闭环",
        "verifier": "守灯 session-9910d4b2-80ff-4437-afed-c848dbda22d1（属主，待其出证）",
    },
    "P1-d": {
        "name": "测试标识机读清单",
        "state": "in_flight",
        "note": "★ 本轮新建：data/registry/bus-test-identifiers（3 标识 / 12 条消息）",
        "evidence": ["blackboard:data/registry/bus-test-identifiers"],
        "dod": "机读清单已在位；★ 负控（验证排除规则真的生效）未构造",
        "verifier": None,
    },
    "U5": {
        "name": "P-7 实例登记增字段「该写入是否外部可见」",
        "state": "in_flight",
        "note": "★ 本轮落：p5-intent-vs-landing 增补 visibility_ledger（3 实例 + 结构发现："
                "外部可见是必要条件非充分条件）",
        "evidence": ["blackboard:data/registry/p5-intent-vs-landing"],
        "dod": "字段已在位；★ 未构造负控；verifier 未指派",
        "verifier": None,
    },
    "DEAD-ACTIVITY": {
        "name": "★ 死会话死后活动证据",
        "state": "in_flight",
        "note": "★ 本轮新建：data/registry/dead-session-postmortem-activity —— "
                "死后 9 次 compaction 全失败，turn 11170→11178。**这是 P3/P4 的紧迫性证据。**",
        "evidence": ["blackboard:data/registry/dead-session-postmortem-activity",
                     "file:~/dsh-collab/audits/20261009/repro/c7-postmortem-activity.py"],
        "dod": "全量流式扫描 + 逐条明细；★ verifier 未指派（须第三方复跑）",
        "verifier": None,
    },
}

def elem_check(e):
    """closure 三要素齐备性机械校验。"""
    has_dod = bool(e.get("dod"))
    has_ev = bool(e.get("evidence"))
    has_vf = bool(e.get("verifier"))
    missing = []
    if not has_dod:
        missing.append("DoD")
    if not has_ev:
        missing.append("evidence")
    if not has_vf:
        missing.append("verifier")
    return missing

# ── ★ 本地推进：不动 continuity-index，但登记必须反映**真实**状态 ──────
# 缺陷修正（本轮自查发现）：原版无条件照搬 continuity-index 的 state，
# 导致 C6/C7 明明已推进却仍显示 open —— 这正是第 5 态（合法但已失效）的
# **登记层**实例：读者据登记表读到的是一个不再为真的状态。
# 处置：本地推进如实登记为 in_flight，同时保留 continuity_index_state 作为基线，
# 并置 sync_pending=true 说明「同步须随 P0（升锚点 state_version）一并做」——
# 因为单独改 continuity-index 会使两件 state_version 不等 ⇒ beacon-check 红。
LOCAL_ADVANCE = {
    "C6": {
        "state": "in_flight",
        "evidence": ["blackboard:data/registry/state-registry",
                     "file:~/dsh-collab/tools/build-state-registry.py"],
        "note": "★ 本轮推进：状态机登记已建（14 项 + 8 wave + 五态对齐 + 3 条缺口标注）。"
                "未记 closed_with_evidence —— verifier 未指派（第三方禁自证）。",
        "dod": "五态定义 + 与 item-validity 的显式映射 + 不可比处标注（已达标）；"
               "★ 负控未构造；verifier 未指派 ⇒ 三要素缺二",
        "verifier": None,
    },
    "C7": {
        "state": "in_flight",
        "evidence": ["file:~/dsh-collab/docs/c7-half-fix-clause10-20261009.md",
                     "blackboard:data/registry/c7-half-fix-clause10",
                     "blackboard:data/registry/c7-half-fix-clause10-v2"],
        "note": "★ 本轮推进：v3.1 附一待落盘清单第 3 项（C7 补正三项）**已全落** —— "
                "① v1 卡双向失效标注 ② n/distinct 观测面声明 ③ 第 5–8 态入证伪清单（§八）。"
                "★ 证伪条 8–11 入锚点须随 P0 待批（锚点是唯一权威件）。",
        "dod": "交付物在位 + 补正三项全落（已达标）；★ 证伪条 8–11 未入锚点（待 P0）；verifier 未指派",
        "verifier": None,
    },
    "P26": {
        "state": "in_flight",
        "evidence": ["file:~/dsh-collab/docs/compaction-lowerbound-crash-20261009.md",
                     "blackboard:data/registry/dead-session-postmortem-activity"],
        "note": "★ 本轮推进（**诊断侧**）：全量流式扫描确认 —— 死后 9 次 compaction 全失败 · "
                "turn 11170→11178 · 105/105 样本 `framed−shadowed ≥ 0`（无一为负）。"
                "**修复侧（G-CR16 请求前预算门 / G-CR17 压缩有效性门）仍未建。**",
        "dod": "诊断充分（全量扫描 + 逐条明细 + 5 个可复跑脚本）；★ 修复未做 ⇒ 不得记 closed",
        "verifier": None,
    },
}

for it in (ci.get("items") or []):
    adv = LOCAL_ADVANCE.get(it.get("id"))
    row = {
        "id": it.get("id"),
        "name": it.get("name"),
        "state": (adv or {}).get("state") or it.get("state"),
        "continuity_index_state": it.get("state"),
        "sync_pending": bool(adv),
        "local_advance": bool(adv),
        "source": "blackboard:data/registry/continuity-index",
        "blocked_reason": it.get("blocked_reason"),
        "note": (adv or {}).get("note") or it.get("note"),
        "evidence": (adv or {}).get("evidence") or it.get("evidence") or [],
        "verifier": (adv or {}).get("verifier") if adv else it.get("verifier"),
        "dod": (adv or {}).get("dod") if adv
               else (it.get("note") if it.get("state") == "closed_with_evidence" else None),
    }
    row["closure_missing"] = elem_check(row) if row["state"] == "closed_with_evidence" else None
    doc["items"].append(row)

for w in (ci.get("waves") or []):
    doc["waves"].append({
        "id": w.get("id"), "name": w.get("name"), "state": w.get("state"),
        "owner": w.get("owner"), "blocked_reason": w.get("blocked_reason"), "note": w.get("note"),
        "source": "blackboard:data/registry/continuity-index",
    })

for k, v in LOCAL_DONE.items():
    v2 = dict(v)
    v2["id"] = k
    v2["source"] = "本会话本轮（session-e317d6ab）"
    v2["closure_missing"] = elem_check(v2) if v2["state"] == "closed_with_evidence" else None
    doc["items"].append(v2)

# ── ★ 负控注入（仅测试用；默认不触发）────────────────────────────
# 用途：回应裁判 addendum-3 —— 构造一个 `closed_with_evidence` 但**三要素不齐**的项，
#       判据（closure_missing）会不会把它标出来、判据门会不会红。
if os.environ.get("STARBRIDGE_INJECT_BAD") == "closure":
    _bad = {
        "id": "K-BAD-CLOSURE",
        "name": "★负控样本：closed_with_evidence 但三要素不齐（注入）",
        "state": "closed_with_evidence",
        "evidence": [],            # 缺 evidence
        "dod": None,               # 缺 DoD
        "verifier": None,          # 缺 verifier
        "source": "★ 由 STARBRIDGE_INJECT_BAD=closure 注入，仅用于负控测试",
    }
    _bad["closure_missing"] = elem_check(_bad)
    doc["items"].append(_bad)

# ── 缺口汇总 ──────────────────────────────────────────────────
doc["gaps"] = [
    {"gap": "★ 锚点五态缺 `unknown`（判不了）", "severity": "中高",
     "why": "「判不了它是否完成」的项被迫二选一：记 open（谎称未开始）或记 blocked（谎称知道原因）。"
            "这正是失败可见性体系要治的『不可知被回落成某个已知值』（第 7 态：默认值被读成事实）",
     "suggest": "向所有者提请：为锚点 §4.2 增补第 6 态 `unknown`（或把 blocked 拆为 blocked/unknown 两支）。"
                "**本会话不擅改权威件。**"},
    {"gap": "★ closed 的判据强度两表不同", "severity": "中",
     "why": "item-validity 的 closed = 状态字段命中关闭词；我方的 closed_with_evidence 要求三要素齐。"
            "⇒ 闭环率**不可跨表比较**",
     "suggest": "任何引用闭环率的地方须注明出自哪套判据"},
    {"gap": "closure 三要素的实际齐备率", "severity": "低（本轮已量化）",
     "why": "见 items[].closure_missing", "suggest": "—"},
]

# ── 统计 ──────────────────────────────────────────────────────
st = {}
for r in doc["items"]:
    st[r["state"]] = st.get(r["state"], 0) + 1
doc["tally"] = st
doc["total_items"] = len(doc["items"])

OUT.parent.mkdir(parents=True, exist_ok=True)
# ★ 2026-10-09 补：只读模式（同 build-starbridge-version-registry.py 的理由）
READONLY = ("--check" in sys.argv) or ("--dry-run" in sys.argv)
if not READONLY:
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

if READONLY:
    print("★ 只读模式（--check）：未写盘")
    print("将写: %s（内容 %d B）" % (OUT, len(json.dumps(doc, ensure_ascii=False))))
else:
    print("已写: %s (%d B)" % (OUT, OUT.stat().st_size))
print("项数: %d（continuity-index %d + 本轮新增 %d）"
      % (len(doc["items"]), len(ci.get("items") or []), len(LOCAL_DONE)))
print("wave 数: %d" % len(doc["waves"]))
print("状态分布: %s" % st)
print()
print("★ 五态对齐结论:")
for m in MAPPING:
    if "缺口" in m["check"] or "不可比" in m["check"] or "不同义" in m["check"]:
        print("  %-22s ←→ %-10s | %s" % (m["ours"], m["theirs"], m["check"]))
print()
print("★ 缺口 %d 条:" % len(doc["gaps"]))
for g in doc["gaps"]:
    print("  [%s] %s" % (g["severity"], g["gap"]))

# ── ★ 判据失败退出（回应裁判 addendum-3 的「目的层」负控）──────────
# 无此门时，「closed_with_evidence 但三要素不齐」只会被**记录**在 closure_missing 字段，
# 进程仍 exit 0 ⇒ 判据等于不会红。本门即为该判据的实现：有则必须 exit 5。
_unsound = [it["id"] for it in doc["items"]
            if it.get("state") == "closed_with_evidence" and it.get("closure_missing")]
if _unsound:
    print()
    print("✗ 判据未通过：%d 项记 closed_with_evidence 但三要素不齐 ⇒ exit 5" % len(_unsound))
    for it in doc["items"]:
        if it.get("state") == "closed_with_evidence" and it.get("closure_missing"):
            print("   %s 缺: %s" % (it["id"], it["closure_missing"]))
    sys.exit(5)
print()
print("✓ 判据通过：所有 closed_with_evidence 项三要素齐备")
