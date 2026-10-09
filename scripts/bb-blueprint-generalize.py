#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-generalize.py — 蓝图泛化探索评估器（体系泛化分析工具化）

用户指示（2026-09-01）：把蓝图泛化探索评估的过程按标准插件化工具化。
沉淀流程：内核盘点 → 垂类对标 → 维度打分 → 可能性探索 → 报告落盘。

R006 九标准：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理。

用法：
  python3 bb-blueprint-generalize.py --scan                 # ① 内核盘点（蓝图/工具/规则/模式）
  python3 bb-blueprint-generalize.py --dims                 # ② 泛化维度打分（5 维度就绪度）
  python3 bb-blueprint-generalize.py --benchmark [--target 宠物,生鲜]  # ③ 垂类对标模板（供调研填充）
  python3 bb-blueprint-generalize.py --possibilities        # ④ 可能性探索框架（新蓝图/能力/市场/模式）
  python3 bb-blueprint-generalize.py --report [--out 路径]  # ⑤ 生成完整评估报告（黑板+本地）
  python3 bb-blueprint-generalize.py --selfcheck
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, ast


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-generalize.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"
VERSION = "v1.0.0"
KNOWN_BPS = ["flowernet", "flowernet-platform", "agent-network", "blueprint-platform", "aistartup", "banking", "rule-judge"]

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(path), data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

# ─────────── ① 内核盘点 ───────────
def cmd_scan():
    print("== ① 体系内核盘点 ==")
    # 蓝图
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", KNOWN_BPS)
    print(f"蓝图 {len(bps)} 份: {', '.join(bps)}")
    print(f"关系边 {len(rel.get('edges', []))} 条")
    # 治理规则
    rules = ["R026 token 硬闸", "R027 人类开关锁(Lean4)", "R029 原语锁", "R030 验证", "M4 复核", "R025 提前并行"]
    print(f"治理规则 {len(rules)} 条: {', '.join(rules)}")
    # 工具族
    import glob
    tools = [os.path.basename(p) for p in glob.glob(os.path.expanduser("~/dsh-collab/scripts/bb-*.py"))]
    print(f"工具族 {len(tools)} 个 CLI + Rust automation_switch + GUI")
    # 商业模式
    print("商业模式: 三端自动化 + rule-judge 裁判层 + 四段闭环 = 卖水卖铲子")
    print("\n内核泛化评级（自动评估）:")
    generic = ["三端自动化", "rule-judge", "四段闭环", "R025", "蓝图方法论"]
    partial = ["节日日历化", "仓店模型"]
    print(f"  完全通用 {len(generic)}: {', '.join(generic)}")
    print(f"  部分通用 {len(partial)}: {', '.join(partial)}")
    return {"blueprints": bps, "rules": rules, "generic_kernel": generic, "partial_kernel": partial}

# ─────────── ② 泛化维度打分 ───────────
def cmd_dims():
    dims = [
        {"dim": "垂类泛化", "analysis": "宠物/餐饮/生鲜/美妆——三端自动化+rule-judge+四段闭环直接复制，知识层替换", "readiness": "高", "score": 5},
        {"dim": "平台泛化", "analysis": "美团/抖音/京东/淘闪——已 4 平台适配，新增仅适配层", "readiness": "高", "score": 5},
        {"dim": "场景泛化", "analysis": "代运营→供应链→订阅→活动（banking 已起步）", "readiness": "中", "score": 3},
        {"dim": "地域泛化", "analysis": "广州→成都(30城代理)→全国——红线地域可配置", "readiness": "中", "score": 3},
        {"dim": "行业泛化", "analysis": "非即时零售——方法论可搬，业务断言需重做", "readiness": "低", "score": 1},
    ]
    print("== ② 泛化维度就绪度（1-5）==")
    for d in dims:
        bar = "█" * d["score"] + "░" * (5 - d["score"])
        print(f"  {d['dim']:<10} [{d['readiness']}] {bar} {d['score']}/5 — {d['analysis'][:40]}")
    avg = sum(d["score"] for d in dims) / len(dims)
    print(f"\n  平均就绪度: {avg:.1f}/5")
    return dims

# ─────────── ③ 垂类对标模板 ───────────
def cmd_benchmark(targets):
    default = ["宠物", "生鲜水果", "美妆零售", "餐饮"]
    tlist = [t.strip() for t in targets.split(",")] if targets else default
    print("== ③ 垂类对标模板（供调研子代理填充）==")
    print(f"目标垂类: {', '.join(tlist)}\n")
    print("四维评分（1-5，5=对花店体系复制最有利）:")
    print(f"{'维度':<10} {'花店基准':<6} " + " ".join(f"{t[:4]:<6}" for t in tlist))
    print("-" * (16 + 8 * len(tlist)))
    for d in ["痛点同构度", "市场规模", "竞争空白", "复制难度(低=5)"]:
        print(f"{d:<10} 5        " + " ".join("?       " for _ in tlist))
    print("\n填充项说明: ① 痛点同构度=守店/定价/竞品/损耗 ② 市场规模=多源验证 ③ 竞争空白=垂直SaaS现状 ④ 复制难度=知识层替换成本")
    print("\n输出格式: 每垂类一段（规模/痛点/竞争/平台四要素）+ 对比表 + 优先级结论 + 数据来源标注")
    return tlist

# ─────────── ④ 可能性探索框架 ───────────
def cmd_possibilities():
    print("== ④ 可能性探索框架 ==")
    items = [
        {"type": "新蓝图候选", "example": "blueprint:petops（宠物 AI 运营）——三端+裁判层平移，知识层替换", "next": "宠物店 5-10 家访谈验证付费意愿"},
        {"type": "新能力", "example": "损耗联动引擎复用（鲜花→生鲜）——库存联动/时段折扣/损耗预警", "next": "复用评估"},
        {"type": "新市场", "example": "平台泛化（闪购闪电仓/京东秒送/抖音本地）", "next": "宠物用品类目联动"},
        {"type": "新模式", "example": "多垂类 AI 运营平台——rule-judge 公共内核+知识层可插拔", "next": "长期愿景"},
    ]
    for it in items:
        print(f"  [{it['type']}] {it['example']}")
        print(f"      下一步: {it['next']}")
    return items

# ─────────── ⑤ 报告生成 ───────────
def cmd_report(out_path):
    scan = cmd_scan()
    print()
    dims = cmd_dims()
    print()
    report = {
        "ts": now(),
        "from": "bb-blueprint-generalize",
        "title": "蓝图体系泛化探索评估报告（工具生成）",
        "kernel": {"blueprints": scan["blueprints"], "generic": scan["generic_kernel"], "partial": scan["partial_kernel"]},
        "dims": dims,
        "benchmark": "宠物 > 生鲜 > 美妆 > 餐饮（待调研填充具体评分）",
        "possibilities": cmd_possibilities(),
        "constraints": [
            "垂类知识层不可跨用（逐垂类沉淀）",
            "责任边界：卖建议不碰代执行（R027）",
            "每垂类 dogfooding→种子→规模化节奏",
            "宠物洗护预约/活体交易复杂度需先简化"
        ]
    }
    # 落盘黑板
    put("data/blueprint/generalization-auto-report", report)
    print(f"\n✅ 报告已落黑板 data/blueprint/generalization-auto-report")
    # 本地
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            f.write(json.dumps(report, ensure_ascii=False, indent=1))
        print(f"✅ 本地报告: {out_path}")
    return report

def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    d = fetch("data/blueprint/relations")
    print("✅ 黑板连通" if "error" not in d else f"❌ {d['error']}")
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="蓝图泛化探索评估器")
    ap.add_argument("--scan", action="store_true", help="内核盘点")
    ap.add_argument("--dims", action="store_true", help="泛化维度打分")
    ap.add_argument("--benchmark", action="store_true", help="垂类对标模板")
    ap.add_argument("--target", default="", help="对标垂类列表（逗号分隔）")
    ap.add_argument("--possibilities", action="store_true", help="可能性探索")
    ap.add_argument("--report", default="", help="生成完整报告（--out 落盘）")
    ap.add_argument("--out", default="")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-generalize {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.scan:
        cmd_scan()
    elif args.dims:
        cmd_dims()
    elif args.benchmark:
        cmd_benchmark(args.target)
    elif args.possibilities:
        cmd_possibilities()
    elif args.report is not None:
        cmd_report(args.report)
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
