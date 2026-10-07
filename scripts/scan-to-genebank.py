#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan-to-genebank.py v1.0 — 数据沉淀衔接：i9 scan 结果 → 自动注册为基因

读黑板 tasks/<node>/result 的 scan 回报 → 为每个资产生成 manifest → 注册到 GeneBank。
打通「i9 项目沉淀 → GeneBank 基因库」（provenance=i9-scan-*）。

用法:
  python3 scan-to-genebank.py                    # 读最近 scan 回报 → 注册基因
  python3 scan-to-genebank.py --node i9          # 指定节点
  python3 scan-to-genebank.py --genebank http://127.0.0.1:8801
  python3 scan-to-genebank.py --dry-run          # 只生成 manifest 不注册
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, hashlib, urllib.request

BLACKBOARD = "http://127.0.0.1:8792"
GENEBANK = "http://127.0.0.1:8801"
NODE = "i9"

# scan item 类型 → 染色体映射
CHROM_MAP = {
    "代码项目": "artifacts",
    "备份/回收": "artifacts",
    "应用/游戏": "artifacts",
    "文档": "knowledge",
    "其他": "artifacts",
    "file": "knowledge",
    "dir": "artifacts",
}

def _get(url):
    try:
        return json.loads(urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "ignore"))
    except Exception as ex:
        return {"error": str(ex)[:80]}

def _bb_put(path, data):
    import http.client, urllib.parse
    u = urllib.parse.urlparse(GENEBANK)
    body = json.dumps(data, ensure_ascii=False).encode()
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=8)
    conn.request("PUT", path, body=body, headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", "ignore")
    conn.close()
    return json.loads(raw) if raw else {}

def make_manifest(item, root, provenance):
    """由 scan item 生成 manifest（gene_id 由路径内容寻址）"""
    name = item.get("name", "asset")
    path = item.get("path", root)
    kind = item.get("type", item.get("kind", "其他"))
    chromosome = CHROM_MAP.get(kind, "artifacts")
    size = item.get("size_bytes", 0)
    # 内容寻址：由路径+名称+大小 哈希（实际文件哈希由 i9 侧可补）
    h = hashlib.sha256(("%s|%s|%s" % (name, path, size)).encode()).hexdigest()
    return {
        "gene_id": "sha256:" + h,
        "name": name,
        "chromosome": chromosome,
        "body": {"path": path, "size_bytes": size, "format": "dir" if item.get("kind") == "dir" else "file", "checksum": h[:16]},
        "expression": {"trainable": None, "inferable": False, "retrievable": False, "composable": []},
        "heredity": {"parent_genes": [], "mutation": "1.0.0", "provenance": provenance},
        "phenotype": {"reusable": item.get("reusable", "n/a")},
    }

def main():
    ap = argparse.ArgumentParser(description="scan 结果 → GeneBank 基因注册")
    ap.add_argument("--node", default=NODE)
    ap.add_argument("--genebank", default=GENEBANK)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--file", default=None, help="从 scan JSON 文件读（黑板 result 被覆盖时用）")
    args = ap.parse_args()

    if args.file:
        data = json.load(open(args.file, encoding="utf-8"))
        v = {"ts": "2026-08-23T00:00:00"}
    else:
        # 读黑板 scan 回报
        r = _get("%s/tasks/%s/result" % (BLACKBOARD, args.node))
        if "error" in r:
            print("❌ 黑板不可达: %s" % r["error"]); sys.exit(1)
        v = r.get("value", {})
        output = v.get("output", "") or ""
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            print("❌ 回报非 JSON（可能是非 scan 任务，或用 --file 从文件读）"); sys.exit(1)
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        print("⚠️ 无资产清单（scan 回报为空）"); sys.exit(1)

    root = data.get("root", "?")
    provenance = "%s-scan-%s" % (args.node, v.get("ts", "?")[:10].replace("-", ""))
    registered = 0
    skipped = 0
    for it in items:
        if it.get("kind") != "dir" and it.get("size_bytes", 0) == 0:
            skipped += 1
            continue
        m = make_manifest(it, root, provenance)
        if args.dry_run:
            print("  [%s] %s (%s)" % (m["chromosome"], m["name"], m["body"]["size_bytes"]))
            continue
        resp = _bb_put("/api/v1/genes", m)
        if resp.get("ok"):
            registered += 1
        else:
            print("  ⚠️ 注册失败 %s: %s" % (m["name"], resp.get("errors")))
    if args.dry_run:
        print("dry-run：共 %d 项，可注册 %d 基因（已跳过 %d 空文件）" % (len(items), len(items) - skipped, skipped))
    else:
        print("✅ 已注册 %d 个基因到 GeneBank（%s，来源 %s）" % (registered, args.genebank, provenance))

if __name__ == "__main__":
    main()
