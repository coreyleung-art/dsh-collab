#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pitfalls-cli.py — 踩坑档案 CLI（对齐 i9 pitfall-archive.py 结构，跨端统一）

整合：i9 dsh-plugin-health-check 的 pitfalls.json 结构（id/级别/日期/迭代/正文头）
     + mac-mini error-to-sop-feedback-loop 机制（记录→归档→更新SOP→验证→同步）

用法:
  pitfalls.py add <id> <severity> <title>    # 新增（P0/P1/P2/P3，交互补字段）
  pitfalls.py list [--severity P1]           # 列出（过滤级别）
  pitfalls.py query <关键词>                  # 检索（title/根因/修复/教训）
  pitfalls.py stats                          # 统计（级别/日期分布）
  pitfalls.py export                         # 导出 markdown 到 docs/pitfalls/
  pitfalls.py sync                           # 同步黑板 data/ops/pitfalls/
  pitfalls.py import <json-file>             # 从 i9 pitfalls.json 导入（跨端整合）

存储:
  本地: ~/dsh-collab/docs/pitfalls/pitfalls.json（单一事实源）
  黑板: data/ops/pitfalls/（同步）
  markdown: docs/pitfalls/YYYY-MM-DD-<slug>.md（人类可读）

依赖: 纯 stdlib（json/os/sys/argparse/urllib）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, urllib.request

PITFALLS_FILE = os.path.expanduser("~/dsh-collab/docs/pitfalls/pitfalls.json")
MD_DIR = os.path.expanduser("~/dsh-collab/docs/pitfalls/")
BB = "http://127.0.0.1:8792"
BB_KEY = "data/ops/pitfalls"

def load():
    try:
        return json.load(open(PITFALLS_FILE))
    except Exception:
        return {"version": 1, "items": []}

def save(data):
    os.makedirs(os.path.dirname(PITFALLS_FILE), exist_ok=True)
    json.dump(data, open(PITFALLS_FILE, "w"), ensure_ascii=False, indent=2)
    print(f"✅ 已保存 {PITFALLS_FILE}（{len(data['items'])} 条）")

def put_bb(path, value):
    try:
        req = urllib.request.Request(BB + "/" + path.lstrip("/"),
            data=json.dumps(value, ensure_ascii=False).encode(), method="PUT")
        with urllib.request.urlopen(req, timeout=8) as r:
            print(f"✅ 已同步黑板 {BB}/{path} → HTTP {r.status}")
    except Exception as e:
        print(f"⚠️ 黑板同步失败: {e}")

def cmd_add(args):
    data = load()
    # 查重
    if any(i["id"] == args.id for i in data["items"]):
        print(f"⚠️ 已存在 {args.id}（用 query 查看）")
        return
    item = {
        "id": args.id,
        "severity": args.severity.upper(),
        "date": datetime.date.today().isoformat(),
        "title": args.title,
        "phenomenon": input("现象: ").strip(),
        "root_cause": input("根因: ").strip(),
        "fix": input("修复: ").strip(),
        "lesson": input("教训: ").strip(),
        "sop_update": input("SOP 更新点: ").strip(),
    }
    data["items"].append(item)
    save(data)
    # 同时生成 markdown
    cmd_export(None)

def cmd_list(args):
    data = load()
    items = data["items"]
    if args.severity:
        items = [i for i in items if i["severity"] == args.severity.upper()]
    print(f"共 {len(items)} 条踩坑档案：")
    for i in items:
        print(f"  [{i['severity']}] {i['id']} · {i['title']}")

def cmd_query(args):
    data = load()
    kw = args.keyword.lower()
    hits = [i for i in data["items"] if kw in json.dumps(i, ensure_ascii=False).lower()]
    print(f"命中 {len(hits)} 条（关键词: {args.keyword}）：")
    for i in hits:
        print(f"  [{i['severity']}] {i['id']} · {i['title']}")
        print(f"    教训: {i.get('lesson','')[:80]}")

def cmd_stats(args):
    data = load()
    items = data["items"]
    from collections import Counter
    by_sev = Counter(i["severity"] for i in items)
    by_date = Counter(i["date"] for i in items)
    print(f"总条数: {len(items)}")
    print(f"按级别: {dict(by_sev)}")
    print(f"按日期: {dict(sorted(by_date.items()))}")

def cmd_export(args):
    data = load()
    os.makedirs(MD_DIR, exist_ok=True)
    for i in data["items"]:
        slug = i["id"]
        md = f"""# {i['id']} {i['title']}

> 级别: {i['severity']} · 日期: {i['date']}

## 现象
{i.get('phenomenon','')}

## 根因
{i.get('root_cause','')}

## 修复
{i.get('fix','')}

## 教训（→ SOP 更新点）
{i.get('lesson','')}

## SOP 更新
{i.get('sop_update','')}
"""
        path = os.path.join(MD_DIR, f"{slug}.md")
        with open(path, "w") as f:
            f.write(md)
    print(f"✅ 已导出 {len(data['items'])} 条 markdown → {MD_DIR}")

def cmd_sync(args):
    data = load()
    put_bb(BB_KEY, {"ts": datetime.datetime.now().isoformat(), "items": data["items"]})

def cmd_import(args):
    """从 i9 pitfalls.json 导入（跨端整合）"""
    src = json.load(open(args.file))
    items = src if isinstance(src, list) else src.get("items", src.get("pitfalls", []))
    data = load()
    existing = {i["id"] for i in data["items"]}
    added = 0
    for it in items:
        if isinstance(it, dict) and it.get("id") and it["id"] not in existing:
            data["items"].append(it)
            added += 1
    save(data)
    print(f"导入 {added} 条新档案（跳过 {len(items)-added} 条已存在）")

def main():
    ap = argparse.ArgumentParser(description="踩坑档案 CLI（跨端统一）")
    sub = ap.add_subparsers(dest="cmd")
    p_add = sub.add_parser("add"); p_add.add_argument("id"); p_add.add_argument("severity"); p_add.add_argument("title")
    p_list = sub.add_parser("list"); p_list.add_argument("--severity", default="")
    p_query = sub.add_parser("query"); p_query.add_argument("keyword")
    sub.add_parser("stats")
    sub.add_parser("export")
    sub.add_parser("sync")
    p_import = sub.add_parser("import"); p_import.add_argument("file")
    args = ap.parse_args()
    if args.cmd == "add": cmd_add(args)
    elif args.cmd == "list": cmd_list(args)
    elif args.cmd == "query": cmd_query(args)
    elif args.cmd == "stats": cmd_stats(args)
    elif args.cmd == "export": cmd_export(args)
    elif args.cmd == "sync": cmd_sync(args)
    elif args.cmd == "import": cmd_import(args)
    else: ap.print_help()

if __name__ == "__main__":
    main()
