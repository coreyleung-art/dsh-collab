#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waimai-erp-import.py — 外卖商品订单 → ERP 导入执行（蓝图 2.5-3）

读取外卖商品销售 CSV（GBK 编码，43 列），提取商品维度数据，为 ERP product/variety
upsert 准备。蓝图 2.5 数据打通核心（数据已就绪：commodityData 17,426 行回溯完成）。

用法：
  python3 waimai-erp-import.py --csv '<导出CSV路径>'          # 提取商品汇总
  python3 waimai-erp-import.py --csv '<路径>' --out map.json   # 输出映射
  python3 waimai-erp-import.py --list-exports                  # 列出现有导出
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import csv, json, sys, glob, os, argparse, datetime
from collections import defaultdict


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/waimai-erp-import.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def load_csv(path):
    """读取外卖导出 CSV（GBK 编码，环境自适配）"""
    # 编码探测：UTF-8 严格优先（外卖导出现为 UTF-8），失败再回退 GBK 系
    # （2026-08-31 修复：此前 GBK 优先会把 UTF-8 中文解码成乱码表头，导致必需列匹配失败）
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            rows = list(csv.reader(open(path, encoding=enc, errors="strict" if enc == "utf-8" else "replace")))
            # 首行表头含必需列才算成功（防乱码误判）
            if rows and any(k in "".join(rows[0]) for k in ("商品", "日期", "订单")):
                return rows
        except Exception:
            continue
    return []

def extract_products(rows):
    """提取商品维度汇总（名称/UPC/SKU/数量/实付/补贴）"""
    if not rows:
        return []
    hdr = rows[0]
    idx = {c: i for i, c in enumerate(hdr)}
    # 必需列
    # 列名兼容新旧两种导出格式（2026-08-31 适配 order_sales_full 新 30 列格式）
    col_aliases = {
        "日期": ["日期"],
        "店铺名称": ["店铺名称"],
        "商品分类": ["商品分类", "分类"],
        "商品名称": ["商品名称", "产品名称"],
        "UPC": ["UPC", "UPC码"],
        "SKU": ["SKU", "商品SKU码", "SKU码"],
        "数量": ["数量", "商品销售数量", "销售数量"],
        "实付销售额": ["实付销售额", "商品实付销售额"],
        "总补贴": ["总补贴", "商品总补贴金额", "补贴金额"],
    }
    resolved = {}
    for key, aliases in col_aliases.items():
        found = next((a for a in aliases if a in idx), None)
        if found is None:
            return {"error": f"缺必需列: {key}", "have": list(idx.keys())[:10]}
        resolved[key] = found
    req = list(resolved.values())
    products = defaultdict(lambda: {"name": "", "category": "", "upc": "", "sku": "",
                                    "qty": 0, "sales": 0.0, "subsidy": 0.0, "dates": set()})
    for row in rows[1:]:
        if len(row) <= max(idx.values()):
            continue
        name = row[idx["商品名称"]].strip()
        if not name:
            continue
        p = products[name]
        p["name"] = name
        p["category"] = row[idx["商品分类"]].strip()
        p["upc"] = row[idx["UPC"]].strip()
        p["sku"] = row[idx["SKU"]].strip()
        try: p["qty"] += int(float(row[idx["数量"]]))
        except: pass
        try: p["sales"] += float(row[idx["实付销售额"]])
        except: pass
        try: p["subsidy"] += float(row[idx["总补贴"]])
        except: pass
        p["dates"].add(row[idx["日期"]].strip())
    result = []
    for name, p in products.items():
        p["dates"] = sorted(p["dates"])
        result.append(p)
    # 按销售额降序
    result.sort(key=lambda x: -x["sales"])
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="导出 CSV 路径")
    ap.add_argument("--out", help="输出 JSON 路径")
    ap.add_argument("--list-exports", action="store_true")
    args = ap.parse_args()

    if args.list_exports:
        exps = glob.glob(os.path.expanduser("~/meituan-multi/data/exports/*.csv"))
        print("现有导出 (%d 个):" % len(exps))
        for e in exps[:10]:
            print("  ", os.path.basename(e))
        sys.exit(0)

    if not args.csv:
        print("需 --csv <路径> 或 --list-exports"); sys.exit(1)

    path = os.path.expanduser(args.csv)
    rows = load_csv(path)
    products = extract_products(rows)
    if isinstance(products, dict) and "error" in products:
        print("❌", products); sys.exit(1)

    total_qty = sum(p["qty"] for p in products)
    total_sales = sum(p["sales"] for p in products)
    print("== 商品提取汇总 ==")
    print("商品种类: %d | 总销量: %d | 总实付: ¥%.2f" % (len(products), total_qty, total_sales))
    print("\nTop 10 商品（按实付销售额）:")
    for p in products[:10]:
        print("  %s | %s | 销量%d | ¥%.2f" % (p["name"][:25], p["category"][:8], p["qty"], p["sales"]))

    if args.out:
        out = {"source": path, "generated": datetime.datetime.now().isoformat(),
               "product_count": len(products), "products": products}
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("\n✅ 映射已输出: %s" % args.out)

if __name__ == "__main__":
    main()
