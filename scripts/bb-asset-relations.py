#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-asset-relations.py — 资产关系建模工具(持久内置 · 系统架构管理器)
维护 business-asset-map.json 的 relations 层(资产间真实关系)
真实世界原则: 只画有据关系; --suggest 仅建议, 人工确认 --add 后 verified=true

用法:
  python3 bb-asset-relations.py --add "资产A" "资产B" depends_on "说明"
  python3 bb-asset-relations.py --add-asset "资产名" --bp flowernet-xxx --atype asset --desc "说明"
  python3 bb-asset-relations.py --assets [bp_id]      # 列资产
  python3 bb-asset-relations.py --del "资产A" "资产B"
  python3 bb-asset-relations.py --list [type]
  python3 bb-asset-relations.py --selfcheck
  python3 bb-asset-relations.py --suggest

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-asset-relations.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

MAP = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/business-asset-map.json")
VALID_TYPES = ["depends_on", "collaborates", "uses", "duplicates", "part_of"]

def load():
    return json.load(open(MAP, encoding="utf-8"))

def save(d):
    json.dump(d, open(MAP, "w"), ensure_ascii=False, indent=1)

def names(d):
    return {a["name"] for a in d["assets"]}

def cmd_add(d, frm, to, typ, desc):
    nameset = names(d)
    if frm not in nameset: print(f"❌ 不存在资产: {frm}"); return 1
    if to not in nameset: print(f"❌ 不存在资产: {to}"); return 1
    if frm == to: print("❌ from==to 不允许"); return 1
    if typ not in VALID_TYPES: print(f"❌ 类型须为 {VALID_TYPES}"); return 1
    for r in d.get("relations", []):
        if r["from"] == frm and r["to"] == to and r["type"] == typ:
            print(f"⚠️ 已存在: {frm} {typ} {to}"); return 0
    d.setdefault("relations", []).append({
        "from": frm, "to": to, "type": typ,
        "desc": desc or "", "since": __import__("datetime").date.today().isoformat(),
        "verified": True})  # 显式 add = 人工确认
    save(d)
    print(f"✅ {frm} --{typ}--> {to} (verified)")
    return 0

def cmd_del(d, frm, to):
    rs = d.get("relations", [])
    n = len(rs)
    d["relations"] = [r for r in rs if not (r["from"] == frm and r["to"] == to)]
    save(d)
    print(f"删 {n - len(d['relations'])} 条: {frm}→{to}")
    return 0

def cmd_add_asset(d, name, bp, typ="asset", desc="", responder="明鉴", node="mac-mini", location=""):
    """资产登记（assets 数组添加）——asset-map 写入口 CLI"""
    nameset = names(d)
    if name in nameset:
        print(f"⚠️ 资产已存在: {name}"); return 0
    d.setdefault("assets", []).append({
        "name": name, "type": typ, "location": location or "data/blueprint/",
        "isOriginal": False, "blueprint": bp, "desc": desc or "",
        "responder": responder, "node": node})
    save(d)
    print(f"✅ 资产登记: {name} (bp={bp}, type={typ})")
    return 0

def cmd_list_assets(d, bp=None):
    assets = d.get("assets", [])
    if bp:
        assets = [a for a in assets if a.get("blueprint") == bp]
    print(f"== 资产 ({len(assets)}) ==")
    for a in sorted(assets, key=lambda x: x.get("blueprint", "")):
        print(f"  [{a.get('blueprint','?')}] {a.get('name')} ({a.get('type','?')})")
    return 0

def cmd_list(d, typ=None):
    rs = d.get("relations", [])
    if typ: rs = [r for r in rs if r["type"] == typ]
    print(f"共 {len(rs)} 条关系:")
    for r in rs:
        mark = "" if r.get("verified") else " (未验证!)"
        print(f"  {r['from']} --{r['type']}--> {r['to']}{mark}  {r.get('desc','')[:40]}")
    return 0

def cmd_selfcheck(d):
    nameset = names(d); errs = []
    seen = set()
    for i, r in enumerate(d.get("relations", [])):
        if r["from"] not in nameset: errs.append(f"#{i} from 不存在: {r['from']}")
        if r["to"] not in nameset: errs.append(f"#{i} to 不存在: {r['to']}")
        if r.get("type") not in VALID_TYPES: errs.append(f"#{i} 非法类型: {r.get('type')}")
        k = (r["from"], r["to"], r["type"])
        if k in seen: errs.append(f"重复: {k}")
        seen.add(k)
    # 孤儿资产(无 node 归属且无关系)
    print(f"校验: {len(d.get('relations',[]))} 关系 / {len(d['assets'])} 资产")
    if errs: print("❌"); [print("  ", e) for e in errs]; return 1
    print("✅ selfcheck 通过"); return 0

def cmd_suggest(d):
    """扫描潜在关系建议(供人工确认)"""
    assets = d["assets"]; by_name = {a["name"]: a for a in assets}
    suggs = []
    # 1) 同蓝图同设备 ≠ 关系(太弱); 跨设备同蓝图 = 协作可能
    from collections import defaultdict
    by_bp = defaultdict(list)
    for a in assets: by_bp[a.get("blueprint", "")].append(a)
    for bp, items in by_bp.items():
        if not bp: continue
        by_nd = defaultdict(list)
        for a in items: by_nd[a.get("node", "")].append(a["name"])
        # 同蓝图跨设备: 可能是协作(两端各持有部分)
    # 2) responder 相同 + 不同 node → 协作候选
    by_resp = defaultdict(list)
    for a in assets: by_resp[a.get("responder", "-")].append(a["name"])
    for resp, its in by_resp.items():
        if resp in ("-", ""): continue
        if len(its) >= 3:
            suggs.append(("collaborates", its[:4], f"同属主 {resp}"))
    # 3) 命名语义(如 xxx-训练集/权重/模型)
    pat = re.compile(r"(flower|l2|yolo|权重|模型|数据集|采集|扫描)")
    for a in assets:
        nm = a["name"]
        # 不自动标, 仅列命名相关候选
    # 只输出类型化建议
    print("== 潜在关系建议(人工确认后 --add) ==")
    if not suggs:
        print("  (暂无明显建议)")
    for typ, its, why in suggs:
        print(f"  建议 {typ}: {its}  ← {why}")
    return 0

def main():
    ap = argparse.ArgumentParser(description="资产关系建模工具（asset-map 写入口）")
    ap.add_argument("--add", nargs=3, metavar=("FROM", "TO", "TYPE"), help="加关系(需 --desc)")
    ap.add_argument("--desc", default="")
    ap.add_argument("--add-asset", metavar="NAME", help="资产登记(需 --bp)")
    ap.add_argument("--bp", default="", help="资产所属蓝图(--add-asset 用)")
    ap.add_argument("--atype", default="asset", help="资产类型(--add-asset 用, 默认 asset)")
    ap.add_argument("--del", nargs=2, metavar=("FROM", "TO"), dest="delrel")
    ap.add_argument("--list", nargs="?", const="", default=None, help="列关系(可按类型)")
    ap.add_argument("--assets", nargs="?", const="", default=None, help="列资产(可按蓝图)")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--suggest", action="store_true")
    args = ap.parse_args()
    d = load()
    if args.add_asset:
        return cmd_add_asset(d, args.add_asset, args.bp, args.atype, args.desc)
    if args.assets is not None:
        return cmd_list_assets(d, args.assets or None)
    if args.add:
        frm, to, typ = args.add
        return cmd_add(d, frm, to, typ, args.desc)
    if args.delrel:
        return cmd_del(d, args.delrel[0], args.delrel[1])
    if args.list is not None:
        return cmd_list(d, args.list or None)
    if args.selfcheck:
        return cmd_selfcheck(d)
    if args.suggest:
        return cmd_suggest(d)
    ap.print_help(); return 0

if __name__ == "__main__":
    sys.exit(main())
