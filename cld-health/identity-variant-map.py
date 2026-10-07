#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identity-variant-map.py — 黑板 `from` 变体 → 规范身份 映射表（只读）
守灯 2026-09-11 · 依 HR 指示：**先只交映射表，不重聚合、不改卡、零风险**
输出：
  ① 框声明（文件清单/记录数/时点）
  ② 变体清单（含出现次数）
  ③ 映射结果：变体 → {类型: agent|service|unknown, 规范 id, 依据, 置信度}
  ④ 未确认清单（需人核）
不做什么：**不做任何覆盖率/参与面的重新聚合**（那涉及重算已公布数，属需裁定动作）
"""
import json, glob, re, os, datetime
from collections import Counter

AUDIT = sorted(glob.glob(os.path.expanduser('~/dsh-collab/token-monitor/blackboard/audit*.jsonl')))

# 已知 agent：规范 id ↔ 角色名/别名（来源：agent_profiles 登记 + 会话面板）
AGENTS = {
    "session-fa1f9150-c949-401f-ba8c-d265f6221676": ["星桥", "coordinator", "mac-mini:星桥", "mac-mini 星桥", "star-bridge", "mac-mini-coordinator", "bus:server:coordinator"],
    "session-a190c54c-ca73-4845-9a65-9dc002d45044": ["明鉴", "明鉴 v3", "mingjian-v3", "a190c54c"],
    "session-f38244df-9225-42ba-ba33-91d1e689edcf": ["明鉴 v2"],
    "session-2a15e6b1-32a9-48b3-a167-8fe0a28e8d82": ["HR", "司库", "HR 司库", "mac HR 司库"],
    "session-9910d4b2-80ff-4437-afed-c848dbda22d1": ["守灯"],
    "session-0e84e65c-d932-43d0-ac36-cb92cb6925c0": ["守链"],
    "session-4787d717-d243-403e-9880-f1a83e65e004": ["4787d717", "数据调查"],
    "session-aa528267-0434-4bf5-87c5-d5a61f8215b2": ["老登"],
    "session-a3bc8cba-714e-446a-900a-b924f111edc7": ["知了", "a3bc8cba"],
    "session-de7b29de-3a65-4f45-911c-e5ef410a5d4b": ["灯塔"],
    "session-54e809ed-452e-47d3-ab7f-d17a6f1b4943": ["媒体", "54e809ed-media"],
    "session-55d4d1bd-bb6d-4c5e-a887-f71eb64c8a3a": ["文汇"],
    "session-92623479-a990-4f32-bb6c-ffa688d64294": ["驿使", "external-link-agent"],
    "session-ffb7c3ab-e722-4ac2-8ee5-0309bc9bb1ea": ["验金石", "QA"],
    "session-6ed4daf2-d00e-4498-9a3f-44fd1b0ed2e2": ["守望"],
    "session-5a5368af-8234-48a5-8e91-1fc64f9902b7": ["罗盘"],
    "session-8c2494e0-3772-4a62-9789-b7adc3123ccc": ["星舵"],
    "session-b193c782-f56a-4b1e-b943-f7a05dcbc853": ["回声"],
    "session-b241741f-820e-4453-83d4-4ebfc8cd48a3": ["守灯塔"],
    "session-1467a7e2": ["i9 设计师"],
}
# 服务/工具写者（**不是 agent 身份**，如实单列，不强行并入某人）
SERVICES = ["cld-monitor", "bb-milestone-report", "pollution-scanner", "sb-mobile",
            "bus:mbp", "bus:i9", "i9", "i9-coordinator", "mbp-bus", "mbp-ops", "device-daemon",
            "central-wake", "node-join-notify", "blackboard-mcp"]

SESS_RE = re.compile(r'(session-[a-f0-9]{8}[a-f0-9-]*|(?<![a-z0-9])[a-f0-9]{8}(?![a-z0-9]))')

def classify(raw):
    s = (raw or '').strip()
    if s in ('None', '', 'null'):
        return ("missing", None, "字段缺失（未写 from）", "已验")
    low = s.lower()
    # 1) 含会话 id（完整或 8 位短式）
    m = SESS_RE.search(s)
    if m:
        frag = m.group(1)
        for cid in AGENTS:
            if cid.startswith(frag[:len('session-')+8]) or cid.replace('session-','').startswith(frag):
                return ("agent", cid, "内嵌会话 id 命中登记表", "已验")
        return ("agent?", frag, "内嵌会话 id 但未匹配登记表", "待核")
    # 2) 服务/工具写者
    for sv in SERVICES:
        if low == sv.lower() or low.startswith(sv.lower()):
            return ("service", sv, "服务/工具名（非 agent）", "已验")
    # 3) 已知角色别名 —— ★ v0.2 修复：按**别名长度降序**匹配
    #    首版按 dict 顺序匹配 ⇒ 「明鉴 v2」被『明鉴』(a190c54c/v3 的别名) 抢先命中，
    #    误配到 v3 桶（真值应为 session-f38244df）。**最长别名优先**才对。
    pairs = []
    for cid, aliases in AGENTS.items():
        for a in aliases:
            pairs.append((a, cid))
    for a, cid in sorted(pairs, key=lambda x: -len(x[0])):
        if a.lower() in low:
            conf = "已验" if low == a.lower() else "高可能"
            return ("agent", cid, f"命别名『{a}』(最长优先)", conf)
    # 4) 设备/系统/测试类（命名为线索，标高可能而非确证）
    if low in ('mac-mini', 'mbp', 'i9') or low.startswith('bus:'):
        return ("device/system", s, "命名即设备/总线标识（非 agent 会话）", "高可能")
    if low in ('ui', 'systemgraph-gui', 'sb-reg'):
        return ("system/ui", s, "UI/注册系统写者", "高可能")
    if 'test' in low or 'probe' in low:
        return ("test/probe", s, "测试或探针写者", "高可能")
    return ("unknown", s, "无会话 id、无服务名、无已知别名", "待核")

def main():
    cnt = Counter(); ns = Counter(); span = [None, None]
    for f in AUDIT:
        for line in open(f, encoding='utf-8'):
            try: d = json.loads(line)
            except Exception: continue
            if d.get('op') != 'PUT': continue
            v = d.get('value') or {}
            cnt[str(v.get('from') if isinstance(v, dict) else None)] += 1
            ns[(d.get('key') or '').split('/')[0]] += 1
            t = d.get('ts') or ''
            span[0] = t if (t and (not span[0] or t < span[0])) else span[0]
            span[1] = t if (t and (not span[1] or t > span[1])) else span[1]

    out = {
        "框声明": {
            "文件清单": [os.path.basename(f) for f in AUDIT],
            "记录数": sum(cnt.values()),
            "时段": span,
            "命名空间分布": dict(ns),
            "取样时点": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "说明": "log 轮转窗，**非全历史**（保留策略会从旧端缩短）",
        },
        "映射": [], "未确认": [],
    }
    for raw, n in cnt.most_common():
        typ, cid, basis, conf = classify(raw)
        rec = {"变体": raw, "次数": n, "类型": typ, "规范": cid, "依据": basis, "置信度": conf}
        out["映射"].append(rec)
        if conf == "待核":
            out["未确认"].append(rec)

    p = os.path.expanduser('~/dsh-collab/cld-health/identity-variant-map-20260911.json')
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print("=== ① 框声明 ===")
    print(f"  文件 {len(AUDIT)} · 记录 {out['框声明']['记录数']} · 时段 {span[0]} → {span[1]}")
    print(f"\n=== ② 映射结果（按次数）===")
    print(f"{'变体':<38}{'次数':>8}{'类型':>10}{'规范':>14}  置信")
    for r in out["映射"][:28]:
        cid = (r["规范"] or "")[:12]
        print(f"  {str(r['变体'])[:36]:<36}{r['次数']:>8}{r['类型']:>10}{cid:>14}  {r['置信度']}")
    print(f"\n  变体总数 {len(out['映射'])} ｜ 待核 {len(out['未确认'])}")
    print(f"\n=== ③ 待核清单（需人确认，不强行归类）===")
    for r in out["未确认"][:15]:
        print(f"  {r['次数']:>6}  {r['变体']!r}  → {r['依据']}")
    print(f"\n映射表已落盘: {p}")
    print("★ 本次**未做任何重新聚合**（未重算参与面/覆盖率）—— 按你的指示，重聚合属需裁定动作")

if __name__ == "__main__":
    main()
