#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deposit-reflow.py v1.0 — 数据沉淀回流：scan 结果 → 结构化清单文档

读黑板 tasks/<node>/result（scan/数据沉淀 回报）→ 生成 markdown 清单 → 落盘。
让「i9 项目沉淀 → mac 侧可检索」自动化、可复用（不只是手工一次）。

用法:
  python3 deposit-reflow.py                          # 回流最近一次 scan 回报（默认 i9）
  python3 deposit-reflow.py --node i9                # 指定节点
  python3 deposit-reflow.py --out ~/dsh-collab/research/cost-governance
  python3 deposit-reflow.py --dry-run                # 只打印清单不落盘

输出: 生成的清单文档路径（落盘后由协调者/HR 入库 KB）
"""
import argparse, json, os, sys, datetime, urllib.request

BLACKBOARD = "http://127.0.0.1:8792"
NODE = "i9"
DEFAULT_OUT = os.path.expanduser("~/dsh-collab/research/cost-governance")

def _get(path):
    req = urllib.request.Request(BLACKBOARD + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as ex:
        return {"error": str(ex)[:80]}

def _fmt_size(b):
    try:
        b = int(b)
    except (TypeError, ValueError):
        return str(b)
    if b < 1024: return "%d B" % b
    if b < 1024**2: return "%.1f KB" % (b/1024)
    if b < 1024**3: return "%.1f MB" % (b/1024**2)
    return "%.2f GB" % (b/1024**3)

SAFE_OUT_DIRS = (os.path.expanduser('~/dsh-collab'), os.path.expanduser('~/Desktop'), os.path.expanduser('~/Documents'))

def reflow(node, dry_run=False, out_dir=None):
    """读最近 scan 回报 → 生成清单文档，返回 (doc_path, item_count)"""
    if out_dir:
        real = os.path.realpath(os.path.abspath(out_dir))
        if not any(real.startswith(os.path.realpath(b)) for b in SAFE_OUT_DIRS):
            return None, '路径越权拒绝: ' + out_dir + ' (仅允许 ~/dsh-collab, ~/Desktop, ~/Documents)'
    r = _get("/tasks/%s/result" % node)
    if "error" in r:
        return None, "黑板不可达: %s" % r["error"]
    v = r.get("value", {})
    if not v:
        return None, "无回报记录（%s 从未回报过任务）" % node
    task_id = v.get("task_id", "?")
    ts = v.get("ts", "?")
    output = v.get("output", "") or ""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None, "回报不是 JSON（task_id=%s，可能是非 scan 任务）" % task_id
    # 支持 scan 结果（root/items）或任意含 items 的结构
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return None, "回报无 items 清单（task_id=%s 非 scan 结果）" % task_id
    root = data.get("root", "?")
    item_count = data.get("item_count", len(items))
    date = datetime.date.today().isoformat()

    lines = []
    lines.append("# %s 项目资产清单（数据沉淀回流 · %s）" % (node.upper(), date))
    lines.append("")
    lines.append("> 来源：mac总线 → %s总线 任务卡 %s（scan %s）" % (node, task_id, root))
    lines.append("> 沉淀：%s · 数据沉淀回流脚本 deposit-reflow.py" % ts)
    lines.append("> 协议：黑板任务卡协议 v1.1（blackboard-task-card-protocol-v1.1）")
    lines.append("")
    lines.append("## 一、资产全景（%d 项，root=%s）" % (item_count, root))
    lines.append("")
    lines.append("| 资产 | 类型 | 大小 | 可复用性 |")
    lines.append("|---|---|---|---|")
    reusable_high = []
    for it in items:
        name = it.get("name", "?")
        kind = it.get("type", it.get("kind", "?"))
        size_hr = it.get("size_hr") or _fmt_size(it.get("size_bytes", 0))
        reusable = it.get("reusable", "n/a")
        path = it.get("path", "")
        lines.append("| %s | %s | %s | %s |" % (name, kind, size_hr, reusable))
        if reusable == "high":
            reusable_high.append((name, kind, size_hr, path))
    lines.append("")
    lines.append("## 二、高可复用资产（重点）")
    lines.append("")
    if reusable_high:
        for name, kind, size_hr, path in reusable_high:
            lines.append("1. **%s**（%s）— %s" % (name, size_hr, path))
    else:
        lines.append("（无 high 标记资产）")
    lines.append("")
    lines.append("## 三、沉淀意义")
    lines.append("")
    lines.append("1. %s 项目资产全景可检索（mac 侧随时查询）" % node.upper())
    lines.append("2. 高可复用项目优先接入算力调度（GPU 训练/推理分派）")
    lines.append("3. 可按「数据沉淀」action 深度扫描单个项目")
    lines.append("")
    lines.append("---")
    lines.append("*%s 项目资产清单 · 数据沉淀回流 · %s*" % (node.upper(), date))

    doc = "\n".join(lines)
    if dry_run:
        print(doc)
        return "(dry-run)", item_count
    out_dir = out_dir or DEFAULT_OUT
    os.makedirs(out_dir, exist_ok=True)
    fname = "%s-project-assets-%s.md" % (node, date)
    fpath = os.path.join(out_dir, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(doc)
    return fpath, item_count

def main():
    ap = argparse.ArgumentParser(description="数据沉淀回流：scan 结果 → 清单文档")
    ap.add_argument("--node", default=NODE, help="目标节点（默认 i9）")
    ap.add_argument("--out", default=None, help="输出目录（默认 research/cost-governance）")
    ap.add_argument("--dry-run", action="store_true", help="只打印清单不落盘")
    ap.add_argument("--lean4-check", action="store_true", help="Lean4自检(越权路径被拒)")
    args = ap.parse_args()
    if args.lean4_check:
        # Lean4 自检: 越权输出目录应被拒
        fpath, info = reflow(args.node, True, "/etc")  # /etc 越权
        ok = isinstance(info, str) and "越权" in info
        print("lean4-check:", "OK 越权输出路径被拒" if ok else "X 越权路径未拦截! info=" + str(info)[:100])
        return 0 if ok else 1
    fpath, info = reflow(args.node, args.dry_run, args.out)
    if isinstance(info, str):  # 错误
        print("❌ %s" % info)
        sys.exit(1)
    print("✅ 数据沉淀回流完成: %d 项资产" % info)
    if not args.dry_run:
        print("   文档: %s" % fpath)
        print("   入库 KB 提示: 用 knowledge_add_document 将上述文档入库（baseId=ops-science-research）")

if __name__ == "__main__":
    main()
