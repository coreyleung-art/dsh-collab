#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route-feedback-replay.py v1.0 — 判定反馈回放器（纯规则，零 LLM）

职责：从历史数据批量生成「判定训练对」，解决 route-feedback 冷启动慢（500 条要值班慢慢攒）的问题。

数据源 → 标签规则（关键：不把 agent-bus 一刀切标 skip）：
  ① resource-registry 变更日志（338 条）→ deposit（已登记=该沉淀，强正样本）
  ② agent-bus 实质消息（迭代报告/交付/登记/决策/脚本/文档等实质词）→ deposit（强正样本）
  ③ agent-bus 真·纯回执（回执/收悉/保持协作，且【无】实质词）→ skip（负样本）
  ④ 其余无信号 → review（留人工，不进训练）

⚠️ 教训（2026-08-22 用户纠偏）：agent-bus 20570 消息里 51% 是纯回执，但其中 36%
  混有「迭代报告/交付/登记」实质词——绝不能按「agent-bus=skip」一刀切，会污染训练样本。

用法：
  python3 route-feedback-replay.py --dry-run     # 只看统计不落盘
  python3 route-feedback-replay.py               # 生成 route-feedback-train.jsonl
  python3 route-feedback-replay.py --balance      # 正负样本均衡采样（deposit/skip 等比）
"""
import argparse, json, os, re, random, datetime

COLLAB = os.path.expanduser("~/dsh-collab")
REGISTRY = os.path.join(COLLAB, "resource-registry.md")
BUS = os.path.expanduser("~/.dsh/agent-bus.json")
OUT = os.path.join(COLLAB, "token-monitor", "route-feedback-train.jsonl")

# 实质信号（含这些 = 该沉淀 deposit，即使开头是回执 emoji）
# ⚠️ 校准（2026-08-22 实测）：单宽泛词（闭/裁决/登记/验收）在普通协作消息里命中过多，
#   导致 deposit 误判 14511 条 vs skip 611 条（24:1 失衡）。
#   收窄为「强产出信号」——只有明确产出物/动作才 deposit。
DEPOSIT_PATTERNS = [
    r'迭代报告', r'交付', r'脚本', r'插件', r'文档', r'规范', r'纪律', r'沉淀',
    r'向量化', r'根因', r'复用', r'SOP', r'PoC', r'poc', r'新建', r'新增',
    r'工具化', r'插件化', r'架构', r'bug', r'上线', r'落地', r'方案',
]
# 纯回执信号（含这些且无实质信号 = 该 skip）
ACK_PATTERNS = [
    r'^(🤝|✅|🎉|👌|👍)\s*$',  # 纯 emoji
    r'^收到\s*[✅✓]?$', r'^收悉', r'^保持协作', r'^保持联动', r'^回执',
    r'确认收悉', r'收到测试', r'测试消息',
]

def has_deposit(text):
    return any(re.search(p, text) for p in DEPOSIT_PATTERNS)

def is_pure_ack(text):
    """真·纯回执：回执信号 且 无实质内容（极短/纯 emoji/纯「收到」无后续）"""
    t = text.strip()
    # 纯 emoji 或极短回执
    if re.match(r'^(🤝|✅|🎉|👌|👍|🚀|🎯)\s*$', t):
        return True
    # 短回执（≤12 字）且无实质信号：如「收到」「收悉」「保持协作」「确认收悉」
    if len(t) <= 12 and re.match(r'^(收到|收悉|保持协作|保持联动|回执|确认收悉)', t) and not has_deposit(t):
        return True
    return False

def load_registry_tasks():
    """resource-registry 变更日志 → deposit 正样本"""
    tasks = []
    for ln in open(REGISTRY, encoding="utf-8"):
        ln = ln.strip()
        if ln.startswith('| 20') and '| v1.0.' in ln:
            parts = [p.strip() for p in ln.split('|')]
            if len(parts) >= 4:
                title = parts[3].replace('**', '')
                tasks.append(title)
    return tasks

def load_bus_messages():
    """agent-bus 全部消息文本"""
    d = json.load(open(BUS, encoding="utf-8"))
    msgs = []
    for t in d.get('threads', []):
        for m in t.get('messages', []):
            txt = (m.get('text') or '').strip()
            if txt:
                msgs.append(txt)
    return msgs

def load_bus_reports():
    """agent-bus 中的「迭代报告」消息（明确的任务交付报告 = 强正样本）"""
    d = json.load(open(BUS, encoding="utf-8"))
    reports = []
    for t in d.get('threads', []):
        for m in t.get('messages', []):
            txt = (m.get('text') or '').strip()
            if '迭代报告' in txt:
                reports.append(txt)
    return reports

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只看统计不落盘")
    ap.add_argument("--balance", action="store_true", help="正负样本均衡采样")
    args = ap.parse_args()

    # ① registry 变更日志 = deposit 正样本（最干净）
    reg_tasks = load_registry_tasks()
    # ② agent-bus 迭代报告 = deposit 正样本（明确任务交付）
    bus_reports = load_bus_reports()
    # ③ agent-bus 真·纯回执 = skip 负样本
    bus_msgs = load_bus_messages()
    bus_ack = [m for m in bus_msgs if is_pure_ack(m)]

    print("=== 判定反馈回放 · 历史数据盘点 ===")
    print(f"① registry 变更日志: {len(reg_tasks)} 条 → deposit 正样本")
    print(f"② agent-bus 迭代报告: {len(bus_reports)} 条 → deposit 正样本")
    print(f"③ agent-bus 真·纯回执: {len(bus_ack)} 条 → skip 负样本")
    print()

    # 构建训练对
    train = []
    for t in reg_tasks:
        train.append({"summary": t[:200], "scanned": "deposit", "actual": "deposit", "source": "registry"})
    for t in bus_reports:
        train.append({"summary": t[:200], "scanned": "deposit", "actual": "deposit", "source": "bus-report"})
    for t in bus_ack:
        train.append({"summary": t[:200], "scanned": "skip", "actual": "skip", "source": "bus-ack"})

    n_pos = len(reg_tasks) + len(bus_reports)
    n_neg = len(bus_ack)
    print(f"训练对: 正样本(deposit) {n_pos} · 负样本(skip) {n_neg} · 合计 {len(train)}")

    if args.balance and n_neg > n_pos:
        # 负样本远多于正样本 → 随机等量采样
        random.seed(42)
        sampled_neg = random.sample([t for t in train if t["actual"] == "skip"], n_pos)
        train = [t for t in train if t["actual"] != "skip"] + sampled_neg
        print(f"均衡采样后: 正 {n_pos} · 负 {len(sampled_neg)} · 合计 {len(train)}")

    if not args.dry_run:
        with open(OUT, "w", encoding="utf-8") as f:
            for r in train:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n✅ 训练数据落盘: {OUT}（{len(train)} 条）")
        print("   下一步：喂给 v1.2 学习型路由（本地 qwen/gemma4 学判定器）")
    else:
        print(f"\n(dry-run) 未落盘，训练对 {len(train)} 条已生成")

if __name__ == "__main__":
    main()
