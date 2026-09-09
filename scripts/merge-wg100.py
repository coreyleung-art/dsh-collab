#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge-wg100.py — 合并 10 主题×10轮 推演结果
读: /tmp/wg100/T*.json → 汇总分析 + 生成可入引擎的 simulation 轮次
写: docs/flowernet-wargame-100-master-v1.md + data/wargame/flowernet/simulation.json 追加(模拟域)
"""
import json, glob, os, sys, datetime, re

OUT_MD = "/Users/coreyleung/dsh-collab/docs/flowernet-wargame-100-master-v1.md"
SIM = "/Users/coreyleung/dsh-collab/data/wargame/flowernet/simulation.json"


def load_all():
    results = {}
    for f in sorted(glob.glob("/tmp/wg100/T*.json")):
        topic = os.path.basename(f).replace(".json", "")
        try:
            d = json.load(open(f, encoding="utf-8"))
            results[topic] = d
        except Exception as e:
            print("⚠️ 加载失败", topic, e)
    return results


def merge_into_simulation(results):
    """把每轮转成 simulation 的三方轮次(追加为独立轮, 避免与 R2 冲突)"""
    sim = json.load(open(SIM, encoding="utf-8")) if os.path.exists(SIM) else {"objective": "", "rounds": [], "pending": None}
    existing = {r.get("issue", "")[:40] for r in sim.get("rounds", [])}
    base = max([r.get("round", 0) for r in sim.get("rounds", [])] + [0])
    added = 0
    for topic, d in results.items():
        for r in d.get("rounds", []):
            issue = str(r.get("issue", ""))[:120]
            if issue[:40] in existing:
                continue
            base += 1
            sim["rounds"].append({
                "round": base, "topic": topic, "issue": issue,
                "stances": {"正方": {"arg": r.get("zheng", "")[:600]},
                            "反方": {"arg": r.get("fan", "")[:600]},
                            "中立方": {"arg": r.get("verdict", "")[:600]}},
                "verdict": r.get("verdict", "")[:600],
                "actions": r.get("actions", []),
            })
            existing.add(issue[:40])
            added += 1
    sim["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    json.dump(sim, open(SIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return added


def analyze(results):
    """统计: 高频行动优先级/高频主题词/风险收敛"""
    all_actions = []
    topic_insight = {}
    risk_words = ["买断", "合规", "平台", "资金", "团队", "数据", "授权", "紫阳", "返佣", "窗口", "竞对", "稀释"]
    risk_count = {w: 0 for w in risk_words}
    for topic, d in results.items():
        acts = []
        for r in d.get("rounds", []):
            for a in r.get("actions", []):
                acts.append(a)
            text = (str(r.get("verdict", "")) + str(r.get("zheng", "")) + str(r.get("fan", "")))
            for w in risk_words:
                if w in text:
                    risk_count[w] += 1
        topic_insight[topic] = acts
        all_actions += acts
    # P0 级行动(含 P0 标记)
    p0 = [a for a in all_actions if re.search(r"P0", a)]
    return {"total_actions": len(all_actions), "p0": p0[:20],
            "risk_top": sorted(risk_count.items(), key=lambda x: -x[1])[:8],
            "topic_actions": {t: len(v) for t, v in topic_insight.items()}}


def gen_report(results, stats):
    lines = [
        "# Flowernet 100 轮沙盘推演 · 汇总报告",
        "",
        f"> 明鉴 · 2026-09-09 · 10 主题 × 10 轮三方对抗(正方→反方→中立裁决) · 目标: 垂直鲜花全国第一",
        f"> 总行动项: {stats['total_actions']} 条 · 引擎: wargame :8813",
        "",
        "## 〇、主题覆盖与行动密度",
        "",
        "| 主题 | 行动项 |",
        "|---|---|",
    ]
    for t, n in stats["topic_actions"].items():
        lines.append(f"| {t} | {n} |")
    lines += ["", "## 一、高频风险词(100轮提及频次, 风险收敛信号)", ""]
    lines.append("| 风险词 | 提及 | 含义 |")
    lines.append("|---|---|---|")
    for w, c in stats["risk_top"]:
        meaning = {"买断": "授权买回是最高频议题", "合规": "数据/合同合规持续警报", "平台": "平台政策主导性",
                   "资金": "现金/融资纪律", "团队": "组织与激励", "数据": "数据端口护城河",
                   "授权": "授权可持续性", "紫阳": "声通合作主体确证", "返佣": "现金流结构", "窗口": "时间窗压力",
                   "竞对": "竞争对抗", "稀释": "股权稀释控制"}.get(w, "")
        lines.append(f"| {w} | {c} | {meaning} |")
    lines += ["", "## 二、P0 级行动(跨主题收敛的高优先项)", ""]
    for a in stats["p0"]:
        lines.append(f"- {a}")
    lines += ["", "## 三、逐主题 Top 裁决洞察", ""]
    for topic, d in results.items():
        lines.append(f"### {topic}")
        for r in d.get("rounds", [])[:3]:
            v = str(r.get("verdict", ""))[:150]
            lines.append(f"- **{r.get('issue','')[:60]}** → {v}")
        lines.append("")
    lines.append("---")
    lines.append("*100轮推演 · 明鉴 · 2026-09-09*")
    return "\n".join(lines)


def main():
    results = load_all()
    if not results:
        print("❌ 无结果文件(子代理可能未完成)"); return 1
    stats = analyze(results)
    added = merge_into_simulation(results)
    report = gen_report(results, stats)
    open(OUT_MD, "w", encoding="utf-8").write(report)
    print(f"✅ 合并 {len(results)} 主题 / {added} 轮入 simulation.json")
    print(f"✅ 报告: {OUT_MD}")
    print(f"   总行动项: {stats['total_actions']} | P0: {len(stats['p0'])} | 风险Top: {stats['risk_top'][:4]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
