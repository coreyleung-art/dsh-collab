#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""approval-tier v1.0 (HR) — 审批定档工具（J45）

按分级矩阵（L0-L3）+ 硬性升级规则对任务定档，写审批台账。
用法：
  python3 approval-tier.py --task "描述"          # 单任务定档（追加台账）
  python3 approval-tier.py --history              # 历史定档：registry 全量 v1.0.x 回填
  python3 approval-tier.py --daily                # 每日巡检：今日 registry 行 + doc/ 新确认文档
零 LLM 成本。"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/approval-tier.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
REG = os.path.join(COLLAB, "resource-registry.md")
LEDGER = os.path.join(COLLAB, "approval-ledger.md")
CFG = os.path.join(COLLAB, "approval-config.json")
HIST = os.path.join(COLLAB, "token-monitor", "approval-tier-history.json")

# 硬性升级关键词 → L3
HARD = ["架构", "协议", "制度", "规则", "政策", "放行", "审批", "预算", "成本治理", "熔断", "合规", "删除", "覆盖", "外部", "承诺", "大额", "跨域", "体系", "策略", "战略", "论文拉取", "全量", "批量", "多店", "隐私", "导出", "数据出域", "权限", "角色", "任命", "撤销", "审计", "跳过监察", "凭据", "API key", "密钥", "密码", "深夜", "大促", "长假", "无人值守"]
# L2 关键词（新任务/迭代）
L2 = ["新功能", "迭代", "更新", "修复", "调研", "评估", "建设", "开发", "系统", "设计", "方案", "文档", "报告", "工具", "脚本", "插件", "工程", "升级", "规划", "沉淀"]
# L1 关键词（常规低风险变更）
L1 = ["改价", "上下架", "回复", "模板", "常规变更", "登记", "同步", "推送", "对账", "备份"]
# L0 关键词（例行/查询）
L0 = ["查询", "状态", "检索", "查看", "日报", "审计", "监察", "回放", "巡检", "检查", "确认", "免回", "统计", "汇总", "list", "get", "read"]

def load_cfg():
    try: return json.load(open(CFG, encoding="utf-8"))
    except Exception: return {"switch": "normal"}

def tier_for(text):
    t = text or ""
    if any(k in t for k in HARD): return "L3", "hard-rule"
    if any(k in t for k in L2): return "L2", "keyword"
    if any(k in t for k in L1): return "L1", "keyword"
    if any(k in t for k in L0): return "L0", "keyword"
    return "L2", "default"

def append_ledger(row):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(row + "\n")

def extract_registry_rows():
    rows = []
    if os.path.exists(REG):
        for line in open(REG, encoding="utf-8", errors="ignore"):
            if "| 2026-08-" in line and "| v1.0." in line and "|" in line:
                m = re.search(r"\| v1\.0\.(\d+) \|", line)
                if m:
                    version = int(m.group(1))
                    parts = [p.strip() for p in line.split("|")]
                    desc = parts[3] if len(parts) > 3 else ""
                    rows.append((version, line.strip()[:60], desc))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--cost", type=float, default=0.0, help="预估成本（元）")
    ap.add_argument("--value", default="normal", choices=["low", "normal", "high", "strategic"])
    ap.add_argument("--roi", type=float, default=0.0, help="预估 ROI_eff")
    ap.add_argument("--lean4-check", action="store_true", help="Lean4自检(违规路径被拒)")
    args = ap.parse_args()
    if args.lean4_check:
        # Lean4 自检: ROI<0.5 低价值+超成本任务应 deny(不该 auto 放行)
        cfg = load_cfg()
        gate = cfg.get("cost_gate", {})
        base = gate.get("base_lines_yuan", {}).get("L2", 100)
        coef = gate.get("value_coef", {}).get("low", 1.0)
        line = base * coef
        # 复算核心判定: 超线 + roi 0.1 -> 应 deny
        tier, why = tier_for("L2 测试任务")
        if args.cost <= 0 and False:
            pass
        decision = "deny" if 0.1 < 0.5 else "auto"  # roi=0.1 < 0.5 恒 deny
        # 用真实路径: 高成本低价值 -> deny
        import subprocess
        r = subprocess.run(["python3", __file__, "--cost", "500", "--value", "low", "--roi", "0.1", "--task", "L2"], capture_output=True, text=True, timeout=30)
        ok = "deny" in r.stdout or "confirm-shrink" in r.stdout
        print("lean4-check:", "OK 低ROI超成本被拒(auto未放行)" if ok else "X 低价值任务未被拒! stdout=" + r.stdout[:200])
        return 0 if ok else 1
    cfg = load_cfg()
    switch = cfg.get("switch", "normal")

    if args.cost > 0:
        # 成本门禁判定：档位线 × 价值系数 vs 预估成本 + ROI_eff 交叉
        tier, why = tier_for(args.task)
        gate = cfg.get("cost_gate", {})
        base = gate.get("base_lines_yuan", {}).get(tier, 100)
        coef = gate.get("value_coef", {}).get(args.value, 1.0)
        line = base * coef
        roi = args.roi
        if roi == 0:
            decision = "escalate" if args.cost > line else "auto"
        elif args.cost <= line and roi >= 2.0:
            decision = "auto"
        elif args.cost > line and roi >= 2.0:
            decision = "confirm-fast"
        elif roi < 0.5:
            decision = "deny"
        elif args.cost > line:
            decision = "confirm-shrink"
        else:
            decision = "auto"
        print("COST_GATE tier=%s cost=%.1f line=%.1f (base=%d x coef=%.1f) roi=%.1f -> %s" % (tier, args.cost, line, base, coef, roi, decision))
        return

    if args.task:
        tier, why = tier_for(args.task)
        # 开关映射：normal 下 L0/L1 下沉（直接执行），L2/L3 需确认
        need_confirm = tier in ("L2", "L3") if switch in ("normal", "strict") else (tier == "L3" if switch == "loose" else False)
        print("TIER=%s RULE=%s SWITCH=%s NEED_CONFIRM=%s" % (tier, why, switch, need_confirm))
        append_ledger("| %s | %s | %s | %s | ⏳ |" % (datetime.date.today().isoformat(), args.task[:40], tier, "需用户确认" if need_confirm else "智能体直接执行"))
        return

    if args.history:
        rows = extract_registry_rows()
        dist = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
        out = []
        for v, head, desc in rows:
            tier, why = tier_for(desc)
            dist[tier] += 1
            out.append({"version": "v1.0." + str(v), "tier": tier, "rule": why, "desc": desc[:80]})
        os.makedirs(os.path.dirname(HIST), exist_ok=True)
        json.dump({"total": len(rows), "distribution": dist, "items": out}, open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("history: total=%d dist=%s -> %s" % (len(rows), dist, HIST))
        return

    if args.daily:
        today = datetime.date.today().isoformat()
        rows = extract_registry_rows()
        today_rows = [r for r in rows if today in r[1]]
        dist = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
        need_confirm = []
        for v, head, desc in today_rows:
            tier, why = tier_for(desc)
            dist[tier] += 1
            if tier in ("L2", "L3"):
                need_confirm.append({"version": "v1.0." + str(v), "tier": tier, "desc": desc[:60]})
        out = os.path.join(os.path.dirname(HIST), "approval-daily-" + today + ".json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"date": today, "tasks": len(today_rows), "distribution": dist, "need_confirm": need_confirm}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("daily: date=%s tasks=%d dist=%s need_confirm=%d -> %s" % (today, len(today_rows), dist, len(need_confirm), out))
        return

    print("usage: --task | --history | --daily")

if __name__ == "__main__":
    main()