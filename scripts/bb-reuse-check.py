#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-reuse-check.py — 底座能力复用性评估器（进化循环第 3 步）

每次底座升级/新增能力时运行：判定该能力「是否适合复用到分布式节点侧（i9/MBP）」。
输出：复用分级（reusable / needs-adaptation / hub-only）+ 节点接入建议。

用法：
  python3 bb-reuse-check.py --capability "事件桥异步通知" --deps "threading,8803端口"
  python3 bb-reuse-check.py --capability "result 自动镜像" --hub-dependent "黑板server核心" --node-side "无需改造"
  python3 bb-reuse-check.py --list-known        # 列出已知能力分级

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime

# 已知能力分级库（每次评估后沉淀，供后续复用）
import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-reuse-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

KNOWN = [
    # 节点可复用：i9/MBP 可直接跑或轻微适配
    {"cap": "事件桥 SSE(8803)", "grade": "reusable", "node": "i9/MBP", "why": "纯 Python 标准库，无中枢依赖", "adapt": "配置黑板地址即可"},
    {"cap": "事件驱动订阅(sse-sub)", "grade": "reusable", "node": "i9/MBP", "why": "HTTP SSE 客户端，跨平台", "adapt": "装 python3 即可"},
    {"cap": "任务卡队列协议", "grade": "reusable", "node": "i9(已用)", "why": "黑板 HTTP API，节点轮询/订阅皆可", "adapt": "已落地 i9-executor"},
    {"cap": "全局时间轴/seq", "grade": "reusable", "node": "i9/MBP", "why": "客户端只需 GET /clock + /timeline", "adapt": "节点侧接入对时即可"},
    {"cap": "genebank 扫描注册", "grade": "reusable", "node": "i9(已用)", "why": "scan-to-genebank 已在 i9 侧", "adapt": "无需改造"},
    # 需适配：节点可跑但需改造
    {"cap": "落链 5 步制度", "grade": "needs-adaptation", "node": "i9", "why": "KB/向量化在中枢，节点只落盘+回报", "adapt": "i9 已接 data/i9/sediment-rules"},
    {"cap": "项目族智能体", "grade": "needs-adaptation", "node": "i9", "why": "模型混合(v4-flash/Ollama)，回报走 notes", "adapt": "按 data/i9/family-agents-plan 建立"},
    {"cap": "职责命名空间", "grade": "needs-adaptation", "node": "i9/MBP", "why": "命名空间映射中枢维护，节点按约定写", "adapt": "GET /ns-registry 自查"},
    # 中枢独占：不适合节点
    {"cap": "黑板 server 本身", "grade": "hub-only", "node": "—", "why": "全局状态权威，单点", "adapt": "中枢唯一"},
    {"cap": "registry/资源登记", "grade": "hub-only", "node": "—", "why": "HR 中枢职责", "adapt": "节点只读/回报"},
    {"cap": "audit 轮转/快照", "grade": "hub-only", "node": "—", "why": "存储管理中枢专属", "adapt": "节点不涉及"},
    {"cap": "订阅持久化", "grade": "hub-only", "node": "—", "why": "黑板进程内", "adapt": "节点不涉及"},
]

def evaluate(capability, deps, hub_dep, node_side, env_notes=""):
    """基于规则判定复用分级（含环境自适配维度）"""
    score = 0
    reasons = []
    # 依赖中枢资源？
    hub_keywords = ["黑板server", "registry", "audit", "存储", "HR", "全局权威", "快照"]
    node_keywords = ["HTTP", "SSE", "标准库", "纯Python", "客户端", "轮询", "订阅", "GET", "POST"]
    for kw in hub_keywords:
        if kw in (hub_dep + capability):
            score -= 2; reasons.append("依赖中枢: %s" % kw)
    for kw in node_keywords:
        if kw in (deps + node_side + capability):
            score += 1; reasons.append("节点友好: %s" % kw)
    if "无中枢依赖" in node_side or "纯标准库" in node_side:
        score += 3; reasons.append("无中枢依赖声明")
    # 环境自适配维度（v1.1：吸收循环强制检查）
    env_ok_keywords = ["编码", "平台", "路径", "GBK", "跨平台", "自适配", "platform", "locale"]
    env_bad_keywords = ["硬编码", "utf-8写死", "windows-only", "mac-only", "无适配"]
    for kw in env_ok_keywords:
        if kw in env_notes:
            score += 1; reasons.append("环境自适配: %s" % kw)
    for kw in env_bad_keywords:
        if kw in env_notes:
            score -= 2; reasons.append("环境缺口: %s" % kw)
    if not env_notes:
        reasons.append("⚠️ 未声明环境适配性（建议补充：编码/平台/路径差异）")
    if score >= 3:
        grade = "reusable"
    elif score >= 0:
        grade = "needs-adaptation"
    else:
        grade = "hub-only"
    return grade, reasons

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capability", help="能力名称/描述")
    ap.add_argument("--deps", default="", help="依赖（如 threading,8803端口）")
    ap.add_argument("--hub-dependent", default="", help="中枢依赖描述（若无写'无'）")
    ap.add_argument("--node-side", default="", help="节点侧情况（是否需要改造）")
    ap.add_argument("--env-notes", default="", help="环境自适配说明（编码/平台/路径差异，v1.1 强制维度）")
    ap.add_argument("--list-known", action="store_true", help="列出已知能力分级")
    args = ap.parse_args()

    if args.list_known:
        print("== 已知能力复用分级 ==")
        for k in KNOWN:
            print("  [%s] %s → %s" % (k["grade"], k["cap"], k["node"]))
            print("      为什么: %s | 适配: %s" % (k["why"], k["adapt"]))
        sys.exit(0)

    if not args.capability:
        print(ap.format_help()); sys.exit(1)

    grade, reasons = evaluate(args.capability, args.deps,
                              args.hub_dependent, args.node_side, args.env_notes)
    result = {
        "capability": args.capability,
        "grade": grade,
        "reasons": reasons,
        "ts": datetime.datetime.now().isoformat(timespec="seconds")
    }
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print("\n分级说明:")
    print("  reusable        → 可直接复用到 i9/MBP（零改造或配置即可）")
    print("  needs-adaptation→ 节点可跑但需适配（见建议）")
    print("  hub-only        → 中枢独占，不适合节点")

if __name__ == "__main__":
    main()
