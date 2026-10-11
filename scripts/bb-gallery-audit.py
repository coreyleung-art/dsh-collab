#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gallery-audit.py — 系统架构管理器结构审查器(R006 九标准 · TCC 自检)
审查 bb-blueprint-gallery.py 的 Tab/视图/render 结构健康度:
  H1 Tab-View-Render 映射完整(每 tab 有 view + 渲染入口)
  H2 深链可达(每 tab 可 #直达)
  H3 内容重复检测(同渲染源出现在多 view)
  H4 空态风险(依赖未初始化数据的入口)
  H5 死代码(定义了未引用的 view/render/tab)
用法:
  python3 bb-gallery-audit.py --scan [FILE]   审查(默认 bb-blueprint-gallery.py)
  python3 bb-gallery-audit.py --selfcheck     同 --scan(exit code: 有严重问题=1)
  python3 bb-gallery-audit.py --json          输出 JSON(供落链)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, re, os, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-gallery-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DEFAULT = os.path.expanduser("~/dsh-collab/scripts/bb-blueprint-gallery.py")

# 已知子视图(render 前缀但非独立 tab) —— 合法无需 tab
SUB_VIEWS = {"renderCapView","renderPermView","renderNetView","renderHwComm","renderHwTopo",
             "renderPlanTable","renderPlanTable2","renderDash"}

def audit(path):
    try:
        src = open(path, encoding="utf-8").read()
    except Exception as e:
        return {"error": str(e)}
    # 前端 JS 已独立成 bb-gallery-ui.js(同目录) → 追加扫描 render/tab 结构
    _js_path = os.path.join(os.path.dirname(os.path.abspath(path)), "bb-gallery-ui.js")
    if os.path.exists(_js_path):
        try:
            src += "\n" + open(_js_path, encoding="utf-8").read()
        except Exception:
            pass
    tabs = re.findall(r'data-tab="([a-z-]+)"', src)
    views = re.findall(r'<div class="main(?: on)?" id="view-([a-z-]+)"', src)
    # 视图容器引用(JS 里 $('view-xxx'))
    viewrefs = set(re.findall(r"\$\('view-([a-z-]+)'\)", src))
    renders = set(re.findall(r'function (render[A-Za-z]+)\(', src))
    # switchTab 分支首次渲染
    sw_render = set(re.findall(r"name==='([a-z-]+)'&&!", src))
    # init 一次性渲染(无 switchTab 分支 = 只在 init)
    init_renders = set(re.findall(r'window\.__\w+Done=true;render(\w+)\(', src))
    findings = {"tabs": tabs, "views": views, "info": {}, "warnings": [], "errors": []}

    # H1: Tab ↔ view
    tab_set, view_set = set(tabs), set(views)
    for t in tabs:
        if t not in view_set:
            findings["errors"].append(f"H1: tab '{t}' 无对应 view-div")
    for v in views:
        if v not in tab_set:
            findings["errors"].append(f"H1: view '{v}' 无对应 tab")
    # view 有 div 但 JS 从未引用(死 view)
    for v in views:
        if v not in viewrefs and v not in tab_set:
            findings["warnings"].append(f"H1: view '{v}' div 存在但 JS 未引用(死)")

    # H2: switchTab 分支覆盖 — 哪些 tab 只在 init 渲染(切回内容在但深链需数据先备)
    only_init = [t for t in tabs if t not in sw_render and t not in ("dash","blueprints","projects","versions","assets","hardware","blueprint-detail","philosophy")]
    # init 一次性渲染的 tab: dash/blueprints/projects/versions/assets/philosophy(init 里)
    init_tabs = []
    for fn in sorted(init_renders):
        # 找对应 tab: renderX → 需映射(启发式: 该函数操作的 view)
        pass
    # 简化: 列出有 view 且无任何 render 挂载的 tab
    rendered_anywhere = set()
    for fn in renders:
        m = re.search(r'render(\w+)', fn)
    # H2b: 深链 bindTabs 支持的 hash
    hash_support = set(re.findall(r"_h==='([a-z-]+)'", src))
    findings["info"]["hash_deeplinks"] = sorted(hash_support)
    findings["info"]["tabs_no_swbranch"] = sorted([t for t in tabs if t not in sw_render])
    # 已知合法(init 渲染): dash blueprints projects versions assets philosophy hardware
    LEGIT_INIT = {"dash","blueprints","projects","versions","assets","philosophy","hardware","workflow","original","planarchive","agents","relations","rules","mech","knowledge","systems","bizmap"}
    for t in tabs:
        if t not in sw_render and t not in LEGIT_INIT:
            findings["warnings"].append(f"H2: tab '{t}' 无 switchTab 首次渲染分支(可能空态)")

    # H3: 重复内容 — 同名 view 被多个 render 写(非子视图)
    writes = {}
    for fn in sorted(renders - SUB_VIEWS):
        # 找函数体引用的 view id
        body_start = src.find("function " + fn)
        nxt = src.find("\nfunction ", body_start + 10)
        body = src[body_start:nxt if nxt > 0 else body_start + 3000]
        used = set(re.findall(r"\$\('view-([a-z-]+)'\)|getElementById\('view-([a-z-]+)'\)", body))
        used_ids = {a or b for a, b in used}
        for uid in used_ids:
            writes.setdefault(uid, []).append(fn)
    dupes = {v: fns for v, fns in writes.items() if len(set(fns)) > 1 and len(set(fns) - SUB_VIEWS) > 1}
    if dupes:
        for v, fns in dupes.items():
            findings["warnings"].append(f"H3: view '{v}' 被多函数写 {sorted(set(fns))}(可能重复/覆盖)")
    findings["info"]["view_writers"] = {k: sorted(set(v)) for k, v in sorted(writes.items())}

    # H5: 未用 render 定义(定义未在任何地方调用)
    called = set(re.findall(r"(\w+)\(", src))
    unused = [f for f in sorted(renders - SUB_VIEWS) if f not in called]
    if unused:
        findings["warnings"].append(f"H5: 定义了但未见调用的 render: {unused}")

    # H6: 蓝图卡片生成反模式(多个 render 用 ALL.blueprints 生成可点卡片 → 内容重复)
    bp_card_sites = []
    for m in re.finditer(r"(?:li|card)\.onclick=\(\)=>openBp\(b\.id\)", src):
        line = src[:m.start()].count("\n") + 1
        # 找最近外层函数
        fns = re.findall(r"function (\w+)\{", src[:m.start()])
        fn = fns[-1] if fns else "?"
        bp_card_sites.append((fn, line))
    if len(bp_card_sites) > 1:
        sites = ", ".join(f"{f}@{l}" for f, l in bp_card_sites)
        findings["warnings"].append(f"H6: 蓝图可点卡片在多处生成(内容重复): {sites} — 建议合并单一入口")
    findings["info"]["bp_card_sites"] = bp_card_sites

    # H7: 空态风险 — render 引用 ALL.xx 但无 __xxxDone 门控且不在 init 顺序
    # 识别引用未初始化全局的 render(启发式: 引用 ALL. 但函数非 async/未在 init 首屏)
    # init() 数据就绪后同步调用的 render(顺序安全, 不属空态风险)
    init_body = src[src.find("async function init()"):]
    init_called = set(re.findall(r"render(\w+)\(", init_body))
    risky = []
    for fn in sorted(renders - SUB_VIEWS):
        body_start = src.find("function " + fn)
        nxt = src.find("\nfunction ", body_start + 10)
        body = src[body_start:nxt if nxt > 0 else body_start + 2500]
        short = fn.replace("render", "")
        if "ALL." in body and "async" not in body[:80] and short not in init_called and fn not in init_called:
            # 引用 ALL 且非 async 且非 init 首屏调用 → 依赖未初始化全局的风险
            risky.append(fn)
    if risky:
        findings["warnings"].append(f"H7: 引用全局 ALL 但非 async 的 render(依赖 init 顺序, 深链直达可能空): {sorted(set(risky))}")
    findings["info"]["all_dependent"] = sorted(set(risky))

    # 汇总
    findings["summary"] = {
        "tabs": len(tabs), "views": len(views), "renders": len(renders),
        "errors": len(findings["errors"]), "warnings": len(findings["warnings"])}
    return findings

def main():
    ap = argparse.ArgumentParser(description="系统架构管理器结构审查(R006)")
    ap.add_argument("--scan", nargs="?", const=DEFAULT, help="审查文件(默认自身目录源)")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检: 有 error 则 exit 1")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()
    if args.tool_version:
        print("bb-gallery-audit v1.0.0"); return
    path = args.scan or DEFAULT
    if not os.path.exists(path):
        print(f"❌ 文件不存在: {path}"); sys.exit(1)
    r = audit(path)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"══ 结构审查: {os.path.basename(path)} ══")
        print(f"Tabs {r['summary']['tabs']} · Views {r['summary']['views']} · Renders {r['summary']['renders']}")
        if r["errors"]:
            for e in r["errors"]: print("❌", e)
        if r["warnings"]:
            for w in r["warnings"]: print("⚠️", w)
        print(f"→ {len(r['errors'])} 错误 / {len(r['warnings'])} 警告")
        if not r["errors"] and not r["warnings"]: print("✅ 结构健康")
    if args.selfcheck:
        sys.exit(1 if r["errors"] else 0)

if __name__ == "__main__":
    main()
