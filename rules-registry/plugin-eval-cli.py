#!/usr/bin/env python3
"""plugin-eval-cli.py — 新插件定位评估工具（独立 vs 纳入已有 vs 复用）
用法:
  plugin-eval-cli.py <新插件名或需求描述>
  plugin-eval-cli.py --list          # 列出现有插件目录
  plugin-eval-cli.py --scan <关键词> # 扫描现有插件中与关键词相关的

判定逻辑（规则 R009）：
  功能唯一（无重叠）→ 独立插件
  同一领域能力补充 → 纳入已有（子插件）
  功能重叠 → 复用已有
"""
import os, sys, json, re

PLUGIN_DIRS = [
    os.path.expanduser("~/dsh-plugin-agent-bus"),
    os.path.expanduser("~/dsh-plugin-central-inbox"),
    os.path.expanduser("~/dsh-plugin-openchronicle"),
    os.path.expanduser("~/dsh-plugin-flower-cockpit"),
    os.path.expanduser("~/dsh-plugin-hr"),
    os.path.expanduser("~/dsh-plugin-waimai"),
    os.path.expanduser("~/dsh-plugin-repo-pipeline"),
    os.path.expanduser("~/dsh-plugin-local-projects/bus-bridge"),
    os.path.expanduser("~/dsh-plugin-local-projects/external-link-policy"),
]

# 现有插件能力索引（name → domain/keywords）
PLUGIN_INDEX = {
    "dsh-plugin-agent-way": {"domain": "协作总线", "kw": ["agent", "消息", "总线", "红绿灯", "互斥"]},
    "dsh-plugin-central-inbox": {"domain": "协作注入", "kw": ["注入", "inbox", "黑板", "SSE", "通知"]},
    "dsh-plugin-openchronicle": {"domain": "感知记忆", "kw": ["感知", "记忆", "捕获", "屏幕", "上下文"]},
    "dsh-plugin-flower-cockpit": {"domain": "花店驾驶舱", "kw": ["花店", "驾驶舱", "周报", "促销"]},
    "dsh-plugin-hr": {"domain": "资源管理", "kw": ["资源", "HR", "成本", "审批", "监察"]},
    "dsh-plugin-waimai": {"domain": "外卖运营", "kw": ["外卖", "订单", "店铺", "运营", "评价"]},
    "dsh-plugin-repo-pipeline": {"domain": "双仓 CI/CD", "kw": ["git", "仓库", "CI", "CD", "同步"]},
    "dsh-plugin-bus-bridge": {"domain": "总线桥", "kw": ["桥", "总线", "跨设备", "转发"]},
    "dsh-plugin-external-link-policy": {"domain": "外链策略", "kw": ["外链", "企微", "通道", "分级"]},
}

def list_plugins():
    print("═══ 现有插件目录 ═══")
    for d in PLUGIN_DIRS:
        name = os.path.basename(d)
        if os.path.isdir(d):
            ver = "?"
            try:
                pkg = json.load(open(os.path.join(d, "package.json")))
                ver = pkg.get("version", "?")
            except: pass
            domain = PLUGIN_INDEX.get(name, {}).get("domain", "?")
            print(f"  {name} v{ver} [{domain}]")

def scan(keyword):
    print(f"═══ 扫描与「{keyword}」相关的现有插件 ═══")
    results = []
    for name, meta in PLUGIN_INDEX.items():
        overlap = 0
        for kw in meta["kw"]:
            if kw in keyword:
                overlap += 1
        if overlap > 0:
            results.append((name, meta["domain"], overlap))
    if not results:
        print("  无直接重叠（可能功能唯一 → 独立插件）")
        return []
    for name, domain, score in sorted(results, key=lambda x: -x[2]):
        print(f"  [{score}重叠] {name} [{domain}]")
    return results

def evaluate(new_name, keyword):
    print(f"═══ 插件定位评估: {new_name} ═══")
    print(f"  需求: {keyword}")
    print()
    # 1. 扫描现有
    related = scan(keyword)
    print()
    # 2. 判定
    if not related:
        verdict = "独立插件"
        reason = "现有插件无功能重叠，领域唯一"
    else:
        top = related[0]
        score = top[2]
        if score >= 2:
            verdict = f"纳入/复用 {top[0]}"
            reason = f"与 {top[0]}（{top[1]}）高度重叠（{score} 项关键词），应纳入或复用，避免重复"
        else:
            verdict = f"独立插件（参考 {top[0]}）"
            reason = f"与 {top[0]}（{top[1]}）仅轻微相关（{score} 项），可独立但需规划依赖"
    print(f"  【判定】{verdict}")
    print(f"  【理由】{reason}")
    print()
    print("  【请用户决策】")
    print(f"    选项 A: {verdict}（推荐）")
    print("    选项 B: 其他（说明理由）")

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return
    if args[0] == "--list":
        list_plugins()
    elif args[0] == "--scan" and len(args) > 1:
        scan(args[1])
    else:
        # 新插件评估：第一个参数是名字，其余是需求
        name = args[0]
        keyword = " ".join(args[1:]) if len(args) > 1 else name
        evaluate(name, keyword)

if __name__ == "__main__":
    main()
