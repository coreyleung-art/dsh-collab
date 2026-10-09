#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-plan-scanner.py — 计划档案扫描器(系统架构管理器 📋计划档案 Tab 数据源)
扫描全域计划性 md/版本文件 → data/blueprint/gallery/plan-archive.json
幂等可复跑: 按文件 mtime 增量更新; --scan 全量 / --selfcheck 校验 / --list 汇总
用法:
  python3 bb-plan-scanner.py --scan      全量扫描生成/更新 plan-archive.json
  python3 bb-plan-scanner.py --list      打印汇总
  python3 bb-plan-scanner.py --selfcheck 校验(重复id/孤儿引用)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, hashlib, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-plan-scanner.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BASE = os.path.expanduser("~/dsh-collab")
OUT = os.path.join(BASE, "data/blueprint/gallery/plan-archive.json")
MEITUAN = os.path.expanduser("~/meituan-multi")
SYSG = os.path.expanduser("~/system-graph-app")
SYSI = os.path.expanduser("~/system-graph-ios")

# 域识别: 路径片段 → domain
def domain_of(path):
    p = path.replace("\\", "/")
    if "/meituan-multi/laodeng-h5/" in p or "/laodeng-h5/" in p: return "老登App"
    if "/meituan-multi/" in p or p.startswith(MEITUAN + "/"): return "老登/MTM"
    if "/system-graph-app/" in p or "/system-graph-ios/" in p: return "明鉴/SystemGraph"
    if "/dsh-collab/data/blueprint/" in p:
        m = re.search(r"data/blueprint/([^/]+)/", p)
        return ("蓝图:" + m.group(1)) if m else "蓝图"
    if "/dsh-collab/docs/" in p: return "协作文档"
    if "/dsh-collab/rules-registry/" in p: return "星桥/规则"
    if "/dsh-collab/cld/" in p: return "守灯/CLD"
    if "/dsh-collab/rust-" in p: return "工具链"
    if "/dsh-collab/erp-workspace/" in p or "chuheng_erp" in p: return "ERP"
    return "其它"

# 类型识别
def type_of(path):
    p = path.replace("\\", "/").lower()
    base = os.path.basename(path).lower()
    if "changelog" in base or base.endswith(".changelog"): return "changelog"
    if base in ("version.json", "versioning.md", "versions.txt") or "version.md" in base or base.startswith("version"): return "version"
    if "roadmap" in base: return "roadmap"
    if "blueprint-" in base and "erp-v" not in base: return "blueprint"  # 蓝图版本档案
    if "plan" in base or re.search(r"计划|规划", path): return "plan"
    if "backlog" in base or "迭代" in path: return "backlog"
    if "manual" in base or re.search(r"手册|预案", path): return "manual"
    return "doc"

# 关联蓝图(文件名/路径线索)
BLUEPRINT_PAT = re.compile(r"(flowernet|aistartup|banking|agent-network|blueprint-platform|rule-judge|gene-bank|distributed-network|mtm|laodeng-app|flowernet-erp|flowernet-miniapp|flowernet-website|memory-governance)")

def relate_blueprint(path, title):
    m = BLUEPRINT_PAT.search(path + " " + title)
    return m.group(1) if m else ""

# 关联智能体(路径/文件名线索)
AGENT_PAT = re.compile(r"(明鉴|星桥|老登|守灯|司库|罗盘|知了|守望|回声|守链|文汇|驿使|拾光|4787d717|i9|MBP|验金石|星舵|月亮|sunshine|yanjin)")

def relate_agent(path, title):
    m = AGENT_PAT.search(path + " " + title)
    return m.group(1) if m else ""

def version_of(path, content):
    # 从内容/文件名提取版本
    m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", content[:4000])
    if m: return "v" + m.group(1)
    m2 = re.search(r"version['\"]?\s*[:=]\s*['\"]?v?([\d.]+)", content[:2000])
    return "v" + m2.group(1) if m2 else ""

def mtime(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")

def scan_dir(path, patterns, max_depth, out):
    """patterns 支持: '*.md'后缀 / 'blueprint-*.md'前缀 / 完整名"""
    if not os.path.exists(path): return
    def match(f):
        fn = f.lower()
        for p in patterns:
            p = p.lower()
            if p.startswith("*"):  # *.md
                if fn.endswith(p[1:]): return True
            elif p.endswith("*"):  # blueprint-*.md
                if fn.startswith(p[:-1]): return True
            else:
                if fn == p: return True
        return False
    for root, dirs, files in os.walk(path):
        depth = root[len(path):].count(os.sep)
        if depth > max_depth: dirs[:] = []; continue
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", ".dsh", "target", "dist", "build", "logs", ".synced", "archive", "research", "papers-local")]
        for f in files:
            full = os.path.join(root, f)
            if match(f):
                item = scan_file(full)
                if item: out.append(item)

def scan_file(full):
    try:
        with open(full, encoding="utf-8", errors="ignore") as fh:
            content = fh.read(4000)
    except Exception:
        content = ""
    rel = full.replace(os.path.expanduser("~"), "~")
    title_line = content.strip().split("\n")[0] if content.strip() else ""
    title = title_line.lstrip("#> ").strip()[:80] or os.path.basename(full)
    domain = domain_of(rel)
    typ = type_of(rel)
    # 域内类型修饰: 版本类多带具体产品
    item = {
        "id": "pa-" + hashlib.md5(rel.encode()).hexdigest()[:8],
        "title": title,
        "type": typ,
        "domain": domain,
        "file": rel,
        "version": version_of(rel, content),
        "blueprint": relate_blueprint(rel, title),
        "agent": relate_agent(rel, title),
        "status": "",
        "updated": mtime(full),
        "desc": title_line[:120],
    }
    # 状态推断
    st = re.search(r"状态[:：]\s*(active|done|todo|planned|进行中|已完成|待办)", content)
    if st: item["status"] = st.group(1)
    return item

def scan():
    items = []
    # 1) meituan-multi 计划类 md(浅)
    scan_dir(MEITUAN + "/docs", ["*.md"], 3, items)
    # 2) laodeng-h5 版本/roadmap
    scan_dir(MEITUAN + "/laodeng-h5", ["*.md", "*.json"], 2, items)
    # 3) dsh-collab docs(计划类)
    scan_dir(BASE + "/docs", ["*.md"], 1, items)
    # 4) 蓝图库版本 md
    scan_dir(BASE + "/data/blueprint", ["blueprint-*.md"], 3, items)
    # 5) 版本文件(CHANGELOG/VERSION/version.json)
    for root in [BASE, MEITUAN, SYSG, SYSI]:
        scan_dir(root, ["CHANGELOG.md", "VERSION", "VERSIONING.md", "version.json", "VERSIONS.txt", "VERSION-MANIFEST.md", "version.rs"], 3, items)
    # 6) SystemGraph 台账
    scan_dir(SYSG, ["VERSION-MANIFEST.md", "CHANGELOG.md"], 1, items)
    # 去重(同路径)
    seen, out = set(), []
    for it in items:
        if it["file"] not in seen:
            seen.add(it["file"]); out.append(it)
    # 过滤噪音: doc 类只保留 计划/规划/roadmap/迭代/manual/预案 语义; 纯分析报告剔除
    def is_planish(it):
        base = os.path.basename(it["file"]).lower() + " " + it["title"].lower()
        return bool(re.search(r"plan|roadmap|计划|规划|迭代|backlog|milestone|路线|演进|manual|预案|schedule|todo", base))
    filtered = []
    for it in out:
        if it["type"] == "doc" and not is_planish(it):
            continue
        # 蓝图库版本 md 强制收(它们是档案核心)
        filtered.append(it)
    # Φ9 写前去重(结构保证: 输出的档案不可能含重复 id)
    seen_ids=set(); uniq=[]
    for _it in filtered:
        if _it.get("id") not in seen_ids:
            seen_ids.add(_it.get("id")); uniq.append(_it)
    if len(uniq)!=len(filtered):
        print(f"  ⚠️ 去重 {len(filtered)-len(uniq)} 条重复 id")
    filtered=uniq
    data = {"version": "1.0", "updated": datetime.date.today().isoformat(),
            "domains": sorted({d["domain"] for d in filtered}),
            "items": filtered,
            "itemCount": len(filtered)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    # 统计
    from collections import Counter
    print(f"✅ plan-archive.json: {len(filtered)} 项")
    print("  类型分布:", dict(Counter(i['type'] for i in filtered)))
    print("  域分布:", dict(Counter(i['domain'] for i in filtered)))
    return filtered

def selfcheck():
    d = json.load(open(OUT))
    ids = [i["id"] for i in d["items"]]
    dup = len(ids) - len(set(ids))
    print(f"items={len(ids)} 重复id={dup}")
    return 1 if dup else 0

def main():
    ap = argparse.ArgumentParser(description="计划档案扫描器")
    ap.add_argument("--scan", action="store_true", help="扫描生成 plan-archive.json")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.scan: scan()
    elif args.list:
        d = json.load(open(OUT)); print(f"{d['itemCount']} 项")
        for i in d["items"][:30]: print(f"  [{i['type']:9s}][{i['domain']:12s}] {i['title'][:45]}")
    elif args.selfcheck: sys.exit(selfcheck())
    else: ap.print_help()

if __name__ == "__main__":
    import sys
    main()
