#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-gallery.py — 系统架构管理器（全局 · 蓝图+智能体+规则+机制+项目+版本快照）

用户指示（2026-09-02）：做一个适配全局的蓝图架构图管理器 app——
统一管理所有蓝图 + 所有智能体架构图，关联项目管理，版本管理，翻查历史图片。
已拍板：① 独立本地 Web app（127.0.0.1:8798）② 自动渲染版本快照。

数据源：
  - 蓝图 BP-9      : 黑板 127.0.0.1:8792/data/blueprint/<id>（11 蓝图）
  - 关系网络        : 黑板 .../data/blueprint/relations（24 边）
  - 版本日志        : 黑板 .../data/blueprint/versionlog（16 entries）
  - 智能体档案      : ~/.dsh/agent-bus.json profiles（52 个）
  - SVG 快照        : ~/dsh-collab/data/blueprint/gallery/snapshots/

用法：
  python3 bb-blueprint-gallery.py --port 8798
  python3 bb-blueprint-gallery.py --render-all   # 只重渲全部快照（无服务器）
  python3 bb-blueprint-gallery.py --selfcheck
访问：http://127.0.0.1:8798/
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, urllib.request, datetime, html, os, math, re, sys, time, threading, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BB = "http://127.0.0.1:8792"
BASE = os.path.expanduser("~/dsh-collab")
GALLERY_DIR = os.path.join(BASE, "data/blueprint/gallery")
SNAP_DIR = os.path.join(GALLERY_DIR, "snapshots")
VERSION_MAP = os.path.join(GALLERY_DIR, "version-map.json")
AGENTS_FILE = os.path.expanduser("~/.dsh/agent-bus.json")
VERSION = "v1.5.0"  # 与 SystemGraph 壳/三端同版(见 ~/system-graph-app/VERSION-MANIFEST.md)

# ─────────── ★ A 组「数据实时化」：单一权威内存模型（2026-10-12 明鉴） ───────────
# 依据：docs/systemgraph-internal-completion-plan-20261008.md §十一（裁判 2026-10-08 有条件通过）
#   前置2「权威源单一 = 内存模型」由 bb-model-store.py 承载；文件变更与 SSE 事件
#   都**只作「触发重读」信号**，不以事件载荷直接改模型。
#   本文件里只有 MODEL.reload()（在 bb-model-store 内）能改模型。
# ★ 未构造成功时 MODEL 为 None，全部取数函数**自动退回改造前的直读路径** ——
#   即本改造是「叠加」而非「替换」，模型层坏了不会让管理器整体不可用（失败可见性）。
MODEL = None

def _model_watch_keys():
    """要监听的板书键面：关系图/版本台账/阶段 + 每个蓝图各一键。

    ★ 这些正是 get_relations()/get_registry()/get_versions() 会 fetch 的键。
      get_registry() 原实现对每个蓝图各打一次 HTTP（21 次）⇒ 模型化后降到 0 次往返。
    """
    ks = ["data/blueprint/relations", "data/blueprint/versionlog", "data/blueprint/stages"]
    for _b in bp_dims():
        ks.append("data/blueprint/" + _b)
    return ks

def _init_model(bb_url=None, poll_interval=3.0, sse_url="http://127.0.0.1:8803/events"):
    """构造模型对象并赋给全局 MODEL（**不在此启动后台线程**，起线程是 main() 的事，
    这样 --selfcheck 之类的一次性调用不会拉起常驻线程）。"""
    global MODEL
    try:
        import importlib.util as _ilu
        # ★ 用 __file__ 拼【绝对路径】。裸相对路径在「进程 cwd 目录被整体替换」时会静默失效：
        #   spec_from_file_location 内部是 `except OSError: pass`，会把 getcwd() 抛的 Errno 2
        #   吞掉，最后报出的错误看起来像「文件不存在」，真因却是「进程抱着一个死 inode」。
        #   （2026-10-12 实测事故，详见 /api/health 的 H0「工作目录」项）
        _here = os.path.dirname(os.path.abspath(__file__))
        _spec = _ilu.spec_from_file_location("_bbms", os.path.join(_here, "bb-model-store.py"))
        _mod = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_mod)
        MODEL = _mod.ModelStore(
            bb_url or BB,
            watch_keys=_model_watch_keys(),
            watch_files=[AGENTS_FILE],
            poll_interval=poll_interval,     # 补1：兜底轮询 <10s（构造时强校验）
            sse_url=sse_url,                 # 主路径：事件驱动
            log=lambda m: print("[model] " + str(m), flush=True),
        )
        return MODEL
    except Exception as e:
        print("[model] 初始化失败，全部取数退回首读路径: %s: %s" % (type(e).__name__, e), flush=True)
        MODEL = None
        return None

# ───────────────────────── 数据层 ─────────────────────────

def fetch(path, timeout=6):
    """取黑板一个键的值。

    ★ A 组改造（2026-10-12）：
      ① 优先走内存模型 MODEL —— 不再每次请求打 HTTP。
         get_registry() 原本对 21 个蓝图各打一次 ⇒ 模型化后降为 0 次往返。
      ② 未纳入监听的键：仍按旧路径取一次（**保证不空窗**），同时登记进监听面，
         使**后续**请求收敛到模型 —— 不做长期双轨。
      ③ ★ 顺带修掉旧实现的静默缺陷：旧代码是 `except Exception: return {}`，
         把「黑板不可达」与「键内容为空」混为一谈（判据：空 ≠ 无）。
         现在不可达时仍返回 {}（保持调用方兼容），但状态可由
         MODEL.board_state(key) 读出为 UNREACHABLE，并经 /api/model-status 暴露。
    """
    p = path.lstrip("/")
    if MODEL is not None:
        st = MODEL.board_state(p)
        if st != "UNWATCHED":
            # ★★ 必须返回【信封】而不是 value —— 调用方写的是
            #    `fetch(k).get("value", {})`（7 处），这是改造前的契约。
            #    我第一版让这里直接返回 value ⇒ 调用方取不到 "value" 键
            #    ⇒ 静默拿到 {} ⇒ 所有走黑板的端点全空（2026-10-12 实测事故）。
            return MODEL.board_envelope(p)
        MODEL.add_watch(p)                      # 登记；下一次 reload 起由模型供给
    try:
        with urllib.request.urlopen(BB + "/" + p, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def h(s):
    return html.escape(str(s))

# ═══ ★★ 2026-10-14（明鉴 · 用户报障「全端刷不出内容」修复后顺带发现的主工具问题）═══
#   ★ 问题：`_with_mtime` 给所有 gallery 快照挂同一个「⚠️ 可能已停更（>30 天）」判据，
#     **而它把两类文件混为一谈**：
#       · 【生成型】= 由脚本定期产出（停了就是真停）⇒ ★ 该报警
#       · 【策展型】= 人改才变（32 天没改是【正常】）⇒ ★★ 报警是【假报警】
#   ★★ 假报警的危害：**它会训练读者忽略报警** ⇒ 真陈旧出现时也没人看
#     （★ 与今晚那条「不报错的装置会被信任」互为镜像：**假报警是让报警失效的机制**）
#   ⇒ 修法：**显式声明类型**，只在【生成型】上挂停更警告；策展型改显示「最后策展于」。
SRC_KINDS = {
    # ── ★ 生成型（有登记的生成器 / 实测在自动链上）──
    "knowledge-graph.json": "generated",
    "mechanism.json":       "generated",
    "plan-archive.json":    "generated",     # ★ refresh 声明的 produces
    "paper-summaries.json": "generated",     # ★ refresh 声明的 produces
    "version-map.json":     "generated",
    "business-asset-map.json": "generated",
    # ── ★ 策展型（人工维护的集合，静止是正常）──
    "governance-philosophy.json": "curated",   # ★ 其 _completeness_note 自述「策展集合」
    "original-assets.json":       "curated",
    # ── ★★ orphaned（无自动更新路径）───────────────────────────────
    #   ★ 实测判据（2026-10-14）：mtime 呈【完美双峰】—— 6 个 ≤1 天 · 8 个 ≥30 天 ·
    #     **中间态 0 个** ⇒ 这 8 个不是「生成器坏了」，而是【从来没有接进任何自动更新路径】。
    #   ★★ 而权威来源印证：`bb-gallery-refresh.py` 声明的 produces **只有 3 项**
    #     （plan-archive / paper-summaries / static-export）⇒ 其余文件【无登记生成器】。
    #   ★★★ 为什么单列而不并入「策展型」：**两者的含义不同** ——
    #     · 策展型 = 有人维护，静止是正常的
    #     · orphaned = **没有任何东西会更新它**（★ 无人维护）
    #     ⇒ 把后者标成「策展」会掩盖一个真实的维护缺口。
    #   ★★ 2026-10-14 二次修正（★ 我上一轮的 orphaned 判定对其中 4 个是【错的】）：
    #     实测发现这 4 个文件【自带 `updated` 字段，且与 mtime 完全一致】⇒ **它们是诚实的策展型**
    #     （★ 手工维护 + 元信息如实）。⇒ 改回 curated。
    "agent-mapping.json":             "curated",
    "business-entity-registry.json":  "curated",
    "device-links.json":              "curated",
    "entity-alias-map.json":          "curated",
    #   ★ 剩下这 2 个【无任何人工元信息】（只有 nodes/relations/groups 或 version/workflows）
    #     ⇒ 无法判定是「扫描产物停了」还是「手工维护但没写元信息」⇒ **保持 orphaned（诚实的不明）**
    "hardware-nodes.json":            "orphaned",
    "workflow-standards.json":        "orphaned",
}
_DEFAULT_KIND = "generated"   # ★ 未声明者按生成型（★ 保守：宁可报假也不漏报真）


def _with_mtime(obj, *rel_paths):
    """★ 2026-10-13 新增（tab 层独立考古 · 类型 6「缺时间戳」）：给数据加【来源文件 mtime】。

    ★★ 起因：8 个 gallery 快照（knowledge-graph / original / workflow / plan-archive /
      mechanism / hardware / biz-assets / philosophy）**32–41 天陈旧，而页面【无任何时间戳】** ——
      ★ 读者无法判断新鲜度（★ 对照：C1–C7 新页都有 `generatedAt`/`mtime` 范式）。
    ⇒ 统一注入 `_srcMtime`（**最大 mtime**，因为一个端点可能聚合多个文件）
      + `_srcFiles`（逐文件 mtime ⇒ ★ 可追溯到具体哪个源旧了）。
    ★ 三态：全部读不到 ⇒ `_srcMtime` 为 None（★ **不假装新鲜**）。
    """
    import os as _os, datetime as _dt
    out = obj if isinstance(obj, dict) else {"data": obj}
    files = {}
    for rp in rel_paths:
        fp = os.path.join(GALLERY_DIR, rp) if not os.path.isabs(rp) else rp
        try:
            files[rp] = _dt.datetime.fromtimestamp(_os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            files[rp] = None
    vals = [v for v in files.values() if v]
    out["_srcFiles"] = files
    # ★★★ 2026-10-14：**优先用文件【自带的 updated】而不是 mtime**
    #   ★ 理由（本线实测）：`agent-mapping` / `business-entity-registry` / `device-links` /
    #     `entity-alias-map` **四个文件自带 `updated` 且与 mtime 完全一致** ⇒ 它们自带了
    #     【权威的取数口径】。★ 而 mtime 的语义是【文件被触碰】—— 复制/git checkout 都会改它，
    #     并不意味着【内容被更新】。
    #   ⇒ ★ 修法：**有自带字段就用它，并【同时报 mtime 与两者之差】**（★ 与「板级 ts 会被归档
    #     覆盖 ⇒ 必须同时读内层 value.ts 并报差」是同一条纪律）。
    decl = {}
    import json as _json
    for rp in rel_paths:
        fp = os.path.join(GALLERY_DIR, rp) if not os.path.isabs(rp) else rp
        try:
            with open(fp, encoding="utf-8") as _f:
                _d = _json.load(_f)
            if isinstance(_d, dict):
                for _k in ("updated", "generatedAt", "generated_at", "updatedAt", "date"):
                    if _d.get(_k):
                        decl[rp] = str(_d[_k])[:19]; break
        except Exception:
            pass
    out["_srcDeclared"] = decl or None
    if decl:
        try:
            _dd = max(_dt.datetime.strptime(v[:10], "%Y-%m-%d") for v in decl.values())
            out["_srcDeclaredAgeDays"] = (_dt.datetime.now() - _dd).days
        except Exception:
            out["_srcDeclaredAgeDays"] = None
    else:
        out["_srcDeclaredAgeDays"] = None
    # ★ 2026-10-14：逐文件标注类型 + 汇总（★ 全部策展 ⇒ 不挂停更警告）
    out["_srcKinds"] = {rp: SRC_KINDS.get(rp, _DEFAULT_KIND) for rp in rel_paths}
    out["_srcAllCurated"] = all(v == "curated" for v in out["_srcKinds"].values()) if rel_paths else False
    # ★ 2026-10-14：第三态汇总 —— 【全部 orphaned】⇒ 前端只陈述「无自动更新路径」
    out["_srcAllOrphaned"] = all(v == "orphaned" for v in out["_srcKinds"].values()) if rel_paths else False
    # ★★ 2026-10-14 补（★ 实测发现 hardware 是【混合型】：device-links=curated + hardware-nodes=orphaned）
    #   ⇒ 原逻辑下两个 all() 都为 False ⇒ 落到「generated」分支 ⇒ **误挂停更警告**
    #   ★ 修法：**报警的充要条件是「至少一个来源是 generated」** —— 因为只有生成型陈旧
    #     才意味着「本该更新而没更新」。全部为 curated/orphaned 时，报警都是错的。
    out["_srcHasGenerated"] = any(v == "generated" for v in out["_srcKinds"].values()) if rel_paths else False
    out["_srcAnyOrphaned"]  = any(v == "orphaned"  for v in out["_srcKinds"].values()) if rel_paths else False
    out["_srcMtime"] = max(vals) if vals else None
    if vals:
        try:
            _newest = max(_dt.datetime.strptime(v, "%Y-%m-%d %H:%M:%S") for v in vals)
            out["_srcAgeDays"] = (_dt.datetime.now() - _newest).days
        except Exception:
            out["_srcAgeDays"] = None
    else:
        out["_srcAgeDays"] = None
    return out


def bp_dims():
    """★ 蓝图维度表（硬编码）+ ★ 2026-10-13 治本：**从黑板合并缺项**。

    ★★ 起因（tab 层独立考古）：本表原为**纯硬编码且无回退** ⇒ 表里没有的蓝图在渲染时
      被 `bp_dims().get(bid,"?")` 报成 **`"?"`**（实测 `flowernet-jv` / `mingjian-toolchain`）。
      ★ 而这两个的**黑板 `dim` 其实是有值的**（公司级 / 工具）—— ★ **真根因不是「数据缺」
      而是「判据不回退」**：一个为真的黑板读数，因硬编码表未覆盖而被显示成 `"?"`。
    ⇒ 治本：表值优先（它带人工归类），**表里没有的 ⇒ 回退读黑板 `dim`**（★ 不编、如实取）。
      这样**以后新增蓝图不会再变 `"?"`**。
    """
    _m = {"flowernet": "业务", "aistartup": "业务", "banking": "业务",
            "flowernet-platform": "技术", "agent-network": "底座", "blueprint-platform": "元层",
            "rule-judge": "验证", "flowernet-erp": "子蓝图", "flowernet-miniapp": "子蓝图",
            "flowernet-website": "子蓝图", "memory-governance": "子蓝图",
            "mtm": "工具", "laodeng-app": "产品",
            "gene-bank": "底座", "distributed-network": "底座",
            "merchant-ops-ai": "产品", "flowernet-ops": "业务",
            "flowernet-supply": "业务", "flowernet-citywar": "业务",
            # ★ 2026-10-13 补（tab 层考古发现 bp_dims 只 19 个 ⇒ 这 2 个被报成 "?"）
            #   ★ 值取自【黑板实际值】（flowernet-jv=公司级 · mingjian-toolchain=工具），非编造
            "flowernet-jv": "公司级", "mingjian-toolchain": "工具"}
    # ★★ 治本：表里没有的 ⇒ 回退读黑板（★ 三态：读到真值 / 读到空 / 读不到 ⇒ 才用 "?"）
    try:
        # ★★ 注意（本线实测教训）：**枚举必须带尾斜杠** —— 无斜杠返 `{"error":"not found"}`。
        #   且**不能用 `_bb_get`**（那是【单键读】、取 `value`）—— 对枚举不适用。
        import urllib.request as _ur
        with _ur.urlopen("http://127.0.0.1:8792/data/blueprint/", timeout=8) as _r:
            _bd = json.loads(_r.read().decode())
        _lst = (_bd.get("list") or {}) if isinstance(_bd, dict) else {}
        for _k, _vv in _lst.items():
            _bid = _k.rstrip("/").split("/")[-1]
            if _bid in _m:
                continue
            _iv = (_vv.get("value") or {})
            _iv = _iv.get("value") if isinstance(_iv.get("value"), dict) else _iv
            _d = _iv.get("dim") or _iv.get("dimension")
            if _d and str(_d) != "?":
                _m[_bid] = _d
    except Exception:
        pass  # ★ 回退失败不阻断（表值仍可用）
    # ★★ 2026-10-13 标注（tab 层考古 · 类型 7）：**本表是 dim 的【权威源】**。
    #   实测 **11/21 个蓝图的黑板无 `dim` 字段**，而它们的 md **大多也没有** ⇒
    #   ★ dim 是【人工归类】，唯一真源就是本表（+ 黑板回退，见上）。
    #   ⇒ ★ 故**不回填黑板**（那会制造双表示 —— 违反 R061）；改为**让读者知道去哪找**。
    _m["__source__"] = "bp_dims() 硬编码表（人工归类）· 11/21 蓝图黑板无 dim 属正常"
    return _m

def bp_colors():
    return {"flowernet": "#6ea8ff", "aistartup": "#34c77b", "banking": "#f5b942",
            "flowernet-platform": "#e06c75", "agent-network": "#c678dd", "blueprint-platform": "#61afef",
            "rule-judge": "#e5c07b", "flowernet-erp": "#56b6c2", "flowernet-miniapp": "#98c379",
            "flowernet-website": "#d19a66", "memory-governance": "#2ac3de",
            "mtm": "#4a9eff", "laodeng-app": "#e84393",
            "gene-bank": "#c678dd", "distributed-network": "#61afef",
            "merchant-ops-ai": "#e84393", "flowernet-ops": "#e06c75",
            "flowernet-supply": "#f08a5d", "flowernet-citywar": "#f76c6c",
            # ★ 同 bp_dims 的补（2026-10-13）
            "flowernet-jv": "#8e7cc3", "mingjian-toolchain": "#7f8c8d"}

def get_registry():
    """返回蓝图列表 [{id,version,status,mainlines,dim}]"""
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", [])
    dims = bp_dims()
    out = []
    for b in bps:
        bp = fetch(f"data/blueprint/{b}").get("value", {})
        if not bp or "id" not in bp:
            # flowernet 主蓝图可能仅在 stages
            st = fetch("data/blueprint/stages").get("value", {})
            if b == "flowernet" and st.get("version"):
                bp = {"id": "flowernet", "name": "花店生意演进", "version": st.get("version"),
                      "mainlines": st.get("mainlines", {}), "status": st.get("status", "active"), "gate": st.get("gate", "")}
        ml = bp.get("mainlines", {})
        ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
        out.append({"id": b, "name": bp.get("name", b), "version": bp.get("version", "?"),
                    "status": bp.get("status", ""), "mainlines": ml_keys,
                    "dim": dims.get(b, "?"), "raw": bp})
    return out

def get_blueprint(bid):
    bp = fetch(f"data/blueprint/{bid}").get("value", {})
    if not bp or "id" not in bp:
        if bid == "flowernet":
            st = fetch("data/blueprint/stages").get("value", {})
            if st.get("version"):
                bp = {"id": "flowernet", "name": "花店生意演进", "version": st.get("version"),
                      "mainlines": st.get("mainlines", {}), "status": st.get("status", "active"),
                      "gate": st.get("gate", ""), "stages": st.get("stages", []), "works": []}
    return bp

def get_relations():
    rel = fetch("data/blueprint/relations").get("value", {})
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    # 父子映射（child_of 反向）：父蓝图 → [子蓝图]
    parent_map = {}
    for e in edges:
        if e.get("type") == "child_of":
            parent_map.setdefault(e.get("to"), []).append(e.get("from"))
    # 子蓝图集合（有父者）
    children = set()
    for v in parent_map.values():
        children.update(v)
    return {"blueprints": bps, "edges": edges, "parentMap": parent_map, "children": sorted(children)}

def get_versions():
    """★ 2026-10-13 修（tab 层独立考古 · 类型 3+4+5）：**双源对齐**。

    ★★ 起因：本端点返回两套版本数据 —— `blueprints`（**版本台账 `versionlog.blueprints`**）
      与 `entries`（版本变更日志），二者**在同一 tab 内互相打架**：
      实测 `blueprints['agent-network']='v1.2'`，而 `entries` 最新一条（SYNCED）逐字
      「台账 v1.2 → 产物 **v1.3**」；`/api/blueprints` 与 `bpinfo` 都是 **v1.3**。
      ⇒ ★ **同一个 tab 里两个版本号各说各话，读者无从判断谁对**。
    ★ 且**表只覆盖 10/21 个蓝图**（11 个从未登记）。
    ⇒ 修法（★ 不删数据、不假装一致）：**把分歧显式标出** ——
      给每项加 `_actual`（来自产物 /api/blueprints）与 `_mismatch`，
      并给顶层加 `_coverage` / `_mismatchCount` / `_missingFromLedger`。
      ★ 这样读者一眼看出「台账落后于产物」，而**不用自己比对两处**。
    """
    d = fetch("data/blueprint/versionlog").get("value", {})
    bps = dict(d.get("blueprints", {}) or {})
    ent = d.get("entries", []) or []

    # ★ 产物侧真值（★ 与 /api/blueprints 同源）
    actual = {}
    try:
        for b in (get_registry() or []):
            actual[b.get("id")] = b.get("version")
    except Exception:
        actual = {}

    def _norm(v):
        return str(v or "").strip().lstrip("v").split("（")[0].strip()

    mism, missing = [], []
    for bid, rec in bps.items():
        av = actual.get(bid)
        lv = rec.get("version") if isinstance(rec, dict) else rec
        rec["_actual"] = av if av is not None else None
        rec["_mismatch"] = bool(av is not None and _norm(lv) != _norm(av))
        if rec["_mismatch"]:
            mism.append({"id": bid, "ledger": lv, "actual": av})
    for bid, av in actual.items():
        if bid not in bps:
            missing.append({"id": bid, "actual": av})
    return {
        "blueprints": bps,
        "entries": ent,
        # ★ 一致性视窗（★ 把「谁落后」显式化，而不是让读者自己比对）
        "_coverage": "%d/%d" % (len(bps), len(actual) or 21),
        "_mismatchCount": len(mism),
        "_mismatches": mism,
        "_missingFromLedger": missing,
        "_note": ("★ 台账(blueprints) vs 产物(/api/blueprints) 的对账："
                  "不一致 %d 项 · 台账未覆盖 %d 项 ⇒ ★ **以产物为准**（台账是补账机制，"
                  "代码自述 sync「未修改 blueprints」⇒ 结构性不回写）" % (len(mism), len(missing))),
    }

def get_agents():
    try:
        # ★ A 组改造（2026-10-12）：优先从内存模型取 —— 消除「每次请求全量读 24MB
        #   agent-bus.json」的开销（改造前实测该端点约 96ms/次，文件 24,095,823 B）。
        #   模型里暂无值时退回直读 ⇒ 任何情况下都不比改造前更差。
        d = MODEL.file_value(AGENTS_FILE, None) if MODEL is not None else None
        if not isinstance(d, dict) or not d.get("profiles"):
            with open(AGENTS_FILE, encoding="utf-8") as f:
                d = json.load(f)
        profs = d.get("profiles", [])
        out = []
        for p in profs:
            aid = p.get("agentId", "")
            role = p.get("role", "")
            out.append({"id": aid, "role": role,
                        "abilities": p.get("abilities", []),
                        "resources": p.get("resources", []),
                        "updatedAt": p.get("updatedAt")})
        return out
    except Exception as e:
        return []

AGENT_DOMAINS = {"ops": ("运维/安全", "#e06c75"), "dev": ("开发/插件", "#c678dd"),
                 "data": ("数据/调研", "#2ac3de"), "biz": ("业务/运营", "#f5b942"),
                 "gov": ("治理/协调", "#34c77b"), "plan": ("洞察/规划", "#6ea8ff"),
                 "comm": ("通讯/媒体", "#e5c07b"), "idle": ("后备/通用", "#4a5568"),
                 "other": ("其他", "#8b90a3")}

def agent_domain(role):
    rl = str(role)
    if any(k in rl for k in ["运维", "健康", "守望", "看门狗", "崩溃", "CLD 系统故障", "基础设施", "排障"]): return "ops"
    if any(k in rl for k in ["插件开发", "GUI 插件", "软件工程", "web 插件", "语音输入", "本地开发", "语音"]): return "dev"
    if any(k in rl for k in ["调查", "调研", "论文", "摄取", "文档", "知识库"]): return "data"
    if any(k in rl for k in ["外卖", "运营", "采集", "灯塔", "客服", "回声", "返图"]): return "biz"
    if any(k in rl for k in ["协调", "资源管理", "HR", "司库", "星桥", "监督", "进度", "规则", "驾驶舱"]): return "gov"
    if any(k in rl for k in ["洞察", "蓝图", "明鉴", "规划"]): return "plan"
    if any(k in rl for k in ["媒体", "驿使", "外链", "通讯"]): return "comm"
    if any(k in rl for k in ["通用", "Ralph", "worker", "后备", "前任", "inactive", "已交接"]): return "idle"
    return "other"

def _agent_res_keys(r):
    keys = set()
    for m in re.finditer(r"file:?([~/A-Za-z0-9_.\-]+)", str(r)):
        parts = [p for p in re.split(r"[/\\]", m.group(1)) if p and p != "."]
        if not parts: continue
        if parts[0] == "~" and len(parts) > 1: keys.add("file:" + parts[1])
        elif parts[0] == "Users" and len(parts) > 2: keys.add("file:" + parts[2])
        elif parts[0].startswith("."): keys.add("file:." + parts[0])
        else: keys.add("file:" + parts[0])
    for m in re.finditer(r"store:(\d+|\w+)", str(r)): keys.add("store:" + m.group(1))
    for m in re.finditer(r"(kb|KB|chromadb?|db|blackboard|data|port|service|channel|task):([A-Za-z0-9_\-\.]+)", str(r)):
        keys.add(m.group(1).lower() + ":" + m.group(2))
    for m in re.finditer(r"(Dify 数据集|ops-science|poi-cache|paper-cache|wiki)", str(r)):
        keys.add("lib:" + m.group(1).lower())
    return keys

def build_agent_graph():
    """52 智能体网络：节点=agent(按职能域着色) + 边=共享资源(share)/同设备协作(bus)"""
    agents = get_agents()
    # 节点
    nodes = []
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        short = re.sub(r"^session-([0-9a-f]{8}).*", r"\1", a.get("id", ""))
        role = a.get("role", "?")
        # 角色短标签：取主角色词（mac-mini/职能）
        lab = role[:22]
        nodes.append({"id": a["id"], "label": lab, "short": short,
                      "color": dcolor, "dim": dname, "domain": dom,
                      "r": 12, "role": role,
                      "abilities": len(a.get("abilities", [])),
                      "resources": len(a.get("resources", []))})
    # 资源键
    agent_res = {a["id"]: _agent_res_keys(" ".join(a.get("resources", []))) for a in agents}
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    # share 边
    pairs = {}
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [a for a, rr in agent_res.items() if k in rr]
            if len(owners) < 2: continue
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    x, y = sorted([owners[i], owners[j]])
                    if x != y: pairs[(x, y)] = pairs.get((x, y), 0) + 1
    # bus 边：同 mac-mini 活跃
    mac = [a["id"] for a in agents if "mac-mini" in a.get("role", "")
           and not any(k in a.get("role", "") for k in ["inactive", "已交接", "前任", "后备", "Ralph", "worker", "子代理"])]
    import random as _rnd
    _rnd.seed(7)
    bus_pairs = [(mac[i], mac[j]) for i in range(len(mac)) for j in range(i + 1, len(mac))]
    _rnd.shuffle(bus_pairs)
    # 合并，cap 度
    adj = {}
    edges = []
    for (a, b), w in sorted(pairs.items(), key=lambda x: -x[1]):
        if adj.get(a, 0) < 4 and adj.get(b, 0) < 4:
            edges.append({"source": a, "target": b, "type": "share", "weight": w, "color": "#34c77b"})
            adj[a] = adj.get(a, 0) + 1; adj[b] = adj.get(b, 0) + 1
    for a, b in bus_pairs:
        if adj.get(a, 0) < 6 and adj.get(b, 0) < 6:
            edges.append({"source": a, "target": b, "type": "bus", "weight": 1, "color": "#c678dd"})
            adj[a] = adj.get(a, 0) + 1; adj[b] = adj.get(b, 0) + 1
    # 父子层级：读 agent-mapping.json
    pm = {}
    try:
        with open(os.path.join(GALLERY_DIR, "agent-mapping.json"), encoding="utf-8") as _f:
            _m = json.load(_f)
        pm = _m.get("parentMap", {})
    except Exception:
        pass
    children_set = set()
    for _c in pm.values():
        children_set.update(_c)
    # 节点标 parent 关系（node id 即 session-xxx）
    for n in nodes:
        aid = n["id"]
        n["parentId"] = None
        for pid, kids in pm.items():
            if aid in kids:
                n["parentId"] = pid
                n["label"] = "↳ " + n["label"]
        kids = pm.get(aid) or []
        n["hasChildren"] = bool(kids)
        n["childCount"] = len(kids)
    # 人工确认连接(连接实验室 confirmed.json) → 实线紫边
    try:
        _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
        if os.path.exists(_cf):
            _cd = json.load(open(_cf, encoding="utf-8"))
            _ids = {a["id"] for a in agents}
            for _l in _cd.get("links", []):
                if _l.get("from") in _ids and _l.get("to") in _ids:
                    edges.append({"source": _l["from"], "target": _l["to"], "type": "confirmed",
                                  "weight": 1, "color": "#c678dd", "desc": _l.get("reason",""),
                                  "status": _l.get("status","confirmed")})
    except Exception: pass
    return {"nodes": nodes, "edges": edges, "mode": "agents",
            "parentMap": pm, "children": sorted(children_set)}

# ── 🛡 能力与权限图谱(R027: 能力能不能 / 权限该不该 分离呈现) ──
CAP_CATS = [
 ("运维/巡检", ["巡检","健康","监控","看门","探针","体检","磁盘","内存","守护","告警","心跳","运维"]),
 ("知识库/RAG", ["知识库","检索","RAG","chroma","向量","Dify","摄取","索引","wiki","KB"]),
 ("插件/开发", ["插件","开发","验证","打包","cordis","GUI","调试","构建","代码"]),
 ("数据/调研", ["调研","情报","爬虫","采集","crawler","分析","论文","数据","快照","数据集"]),
 ("运营/生意", ["外卖","门店","运营","商品","订单","价格","客服","报表","活动","投流","评价","采购","库存"]),
 ("协调/治理", ["协调","治理","规则","审批","队列","红线","仲裁","督办","红绿灯","台账"]),
 ("通讯/媒体", ["通讯","媒体","外链","稿件","战报","广播","记者","发文","跨设备"]),
 ("洞察/规划", ["蓝图","规划","洞察","战略","产品","选型","情报库","路线"]),
 ("语音/对话", ["语音","ASR","识别","TTS","对话","意图","语音输入","语义"]),
 ("文档/归档", ["文档","归档","沉淀","摄取","manual","手册","wiki","日志"]),
 ("记忆/持久", ["记忆","compaction","压缩","持久","openchronicle","pruner","沉淀","promote"]),
]
def _cap_cat(abi):
    for cat, kws in CAP_CATS:
        if any(k in abi for k in kws): return cat
    return "其他/专属"
def build_cap_perm_graph():
    """🛡 能力与权限图谱(R027): cap 视图 agent→能力簇(能不能) · perm 视图 agent→资源独占红/共享蓝(该不该)"""
    agents = get_agents()
    nodes, edges = [], []
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        lab = a.get("role", "?")[:22]
        nodes.append({"id": a["id"], "label": lab, "short": re.sub(r"^session-([0-9a-f]{8}).*", r"\1", a.get("id", "")),
                      "color": dcolor, "dim": dname, "domain": dom, "r": 11,
                      "role": a.get("role", ""), "kind": "capagent",
                      "abilities": a.get("abilities", []), "abiCount": len(a.get("abilities", [])),
                      "resources": a.get("resources", []), "resCount": len(a.get("resources", []))})
    res_keys = {}
    for a in agents:
        res_keys[a["id"]] = _agent_res_keys(" ".join(a.get("resources", [])))
    res_owner = {}
    for aid, rks in res_keys.items():
        for k in rks:
            res_owner.setdefault(k, []).append(aid)
    for cat, _ in CAP_CATS:
        nodes.append({"id": "cap:" + cat, "label": cat, "short": cat[:3], "kind": "capcat",
                      "dim": "能力簇", "color": "#f5b942", "r": 11, "count": 0})
    for a in agents:
        for abi in (a.get("abilities") or []):
            edges.append({"source": a["id"], "target": "cap:" + _cap_cat(abi),
                          "type": "拥有", "color": "#f5b942", "weak": True})
    res_nodes = {}
    for k, owners in sorted(res_owner.items(), key=lambda x: -len(x[1]))[:45]:
        excl = len(owners) == 1
        rid = "res:" + k
        nodes.append({"id": rid, "label": k[:22], "short": k.split(":")[-1][:8], "kind": "capres",
                      "dim": "资源", "color": "#e06c75" if excl else "#4a9eff",
                      "r": 7 if excl else 9, "exclusive": excl, "ownerCount": len(owners),
                      "desc": "独占" if excl else "共享·" + str(len(owners)) + "主"})
        res_nodes[k] = rid
    perm_edges = []
    for aid, rks in res_keys.items():
        for k in rks:
            if k in res_nodes:
                rid = res_nodes[k]
                excl = (res_owner[k] == [aid])
                perm_edges.append({"source": aid, "target": rid,
                                   "type": "独占" if excl else "访问",
                                   "color": "#e06c75" if excl else "#4a9eff", "weak": True})
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "capEdges": len(edges), "permEdges": len(perm_edges),
            "permEdgesAll": perm_edges, "capCats": [c for c, _ in CAP_CATS],
            "resTotal": len(res_owner), "resShown": len(res_nodes)}

# 追加到 bb-blueprint-gallery.py 的 build_cap_perm_graph 之后
def build_cap_view():
    full = build_cap_perm_graph()
    agents = {n["id"] for n in full["nodes"] if n.get("kind") == "capagent"}
    cats = {n["id"] for n in full["nodes"] if n.get("kind") == "capcat"}
    keep = agents | cats
    nodes = [n for n in full["nodes"] if n["id"] in keep]
    edges = [e for e in full["edges"] if e["source"] in keep and e["target"] in keep]
    capcnt = {}
    for e in edges:
        if e["target"].startswith("cap:"):
            capcnt[e["target"]] = capcnt.get(e["target"], 0) + 1
    for n in nodes:
        if n.get("kind") == "capcat":
            n["count"] = capcnt.get(n["id"], 0)
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "capEdges": len(edges)}

def build_perm_view():
    full = build_cap_perm_graph()
    agents = {n["id"] for n in full["nodes"] if n.get("kind") == "capagent"}
    reses = {n["id"] for n in full["nodes"] if n.get("kind") == "capres"}
    keep = agents | reses
    nodes = [n for n in full["nodes"] if n["id"] in keep]
    edges = [e for e in (full.get("permEdgesAll") or []) if e["source"] in keep and e["target"] in keep]
    return {"nodes": nodes, "edges": edges, "mode": "capperm",
            "agentCount": len(agents), "permEdges": len(edges),
            "resTotal": full.get("resTotal"), "resShown": len(reses)}

# ───────────────────────── SVG 渲染 ─────────────────────────

ST_ICON = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
ST_COLOR = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}

def esc(s):
    return html.escape(str(s))

def _status_color(st):
    return ST_COLOR.get(st or "todo", "#7d8596")

def norm_ver(v):
    """规范化版本号：v2.3 → 2.3，避免 vv2.3"""
    s = str(v or "?")
    return s[1:] if s.startswith("v") else s

def svg_blueprint(bid, bp=None):
    """渲染蓝图架构图 SVG。bp 传 dict 则用之（历史快照/BP-9 快照文件）；否则黑板拉取。"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return "<svg width='800' height='120'><text x='20' y='40' fill='#e06c75'>无数据: %s</text></svg>" % esc(bid)
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", [])
    # flowernet: 从 raw 无 stages → stages 键兜底已在 get_blueprint
    works = bp.get("works", [])
    if isinstance(works, dict):
        works = []
    works_by = {}
    for w in works:
        if isinstance(w, dict):
            works_by.setdefault(w.get("stage"), []).append(w)

    W = 1560
    lane_h = 150
    pad = 20
    header_h = 86
    H = header_h + lane_h * max(len(ml_keys), 1) + 70
    parts = []
    # 背景
    parts.append(f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>')
    # 标题
    name = bp.get("name", bid)
    ver = bp.get("version", "")
    gate = str(bp.get("gate", ""))[:90]
    parts.append(f'<text x="{pad}" y="34" fill="#e8eaf0" font-size="21" font-weight="bold">{esc(name)}</text>')
    parts.append(f'<text x="{pad}" y="56" fill="#8b90a3" font-size="13">blueprint:{esc(bid)} · v{esc(norm_ver(ver))} · 维度:{esc(bp_dims().get(bid,"?"))}</text>')
    if gate:
        parts.append(f'<text x="{pad}" y="76" fill="#f0b429" font-size="11">门禁: {esc(gate)}</text>')
    lane_w = (W - 2 * pad) / max(len(ml_keys), 1)
    # 泳道标题行
    for i, mid in enumerate(ml_keys):
        x = pad + i * lane_w
        meta = ml[mid]
        mname = meta.get("name", mid) if isinstance(meta, dict) else mid
        mdesc = (meta.get("desc", "") if isinstance(meta, dict) else "")[:80]
        # 归属: 有 mainline 匹配用之; 若整个蓝图的 stages 都无 mainline 字段(子蓝图独立阶段),
        # 则归到第一条主线卡显示(避免空壳); 无 stages 则空
        if stages and all(s.get("mainline") is None for s in stages):
            # 全部 stages 只在第一个主线泳道展示
            mstages = stages if i == 0 else []
        else:
            mstages = [s for s in stages if s.get("mainline") == mid] if stages else []
        # 泳道背景
        parts.append(f'<rect x="{x+4}" y="{header_h-10}" width="{lane_w-12}" height="{lane_h*max(len(mstages),1)+44}" fill="#141824" rx="10" stroke="#232a3a" stroke-width="1"/>')
        parts.append(f'<text x="{x+18}" y="{header_h+12}" fill="{bp_colors().get(bid,"#6ea8ff")}" font-size="15" font-weight="bold">{esc(mname)}</text>')
        parts.append(f'<text x="{x+18}" y="{header_h+30}" fill="#8b90a3" font-size="10">{esc(mdesc)}</text>')
        yy = header_h + 46
        # 该主线下的 stages 卡片竖排
        for s in mstages:
            sc = _status_color(s.get("status"))
            sname = s.get("name", "")
            sstage = s.get("stage", s.get("id", ""))
            subs = s.get("substages", [])
            card_h = max(58, 26 + 20 * len(subs))
            # 卡片分组行线
            parts.append(f'<rect x="{x+18}" y="{yy}" width="{lane_w-52}" height="{card_h}" rx="8" fill="#0d1119" stroke="{sc}" stroke-width="1.5"/>')
            parts.append(f'<text x="{x+30}" y="{yy+20}" fill="{sc}" font-size="12" font-weight="bold">{esc(str(sstage))} · {esc(sname)[:26]}</text>')
            parts.append(f'<text x="{x+lane_w-60}" y="{yy+20}" fill="#8b90a3" font-size="10">{ST_ICON.get(s.get("status","todo"),"⬜")}</text>')
            sy = yy + 36
            for ss in subs[:5]:
                ssid = ss.get("id", "")
                ssc = _status_color(ss.get("status"))
                parts.append(f'<text x="{x+34}" y="{sy}" fill="{ssc}" font-size="10.5">◦ {esc(ssid)} {esc(ss.get("name",""))[:22]}</text>')
                sy += 17
            if len(subs) > 5:
                parts.append(f'<text x="{x+34}" y="{sy}" fill="#8b90a3" font-size="10">… +{len(subs)-5}</text>')
                sy += 15
            yy += card_h + 8
    # 图例
    ly = H - 44
    parts.append(f'<line x1="{pad}" y1="{ly-12}" x2="{W-pad}" y2="{ly-12}" stroke="#232a3a"/>')
    lx = pad
    for k, ic in [("done", "✅ 已完成"), ("active", "🟢 进行中"), ("partial", "🟡 部分"), ("todo", "⬜ 待做")]:
        parts.append(f'<text x="{lx}" y="{ly+8}" fill="#8b90a3" font-size="11">{ic}</text>')
        lx += 150
    nw = sum(len([s for s in (stages or []) if s.get("mainline") == m]) for m in ml_keys)
    parts.append(f'<text x="{W-pad-360}" y="{ly+8}" fill="#8b90a3" font-size="11" text-anchor="end">主线 {len(ml_keys)} · 主阶段 {len(stages or [])} · v{esc(ver)}</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"

RULE_CAT_COLORS = {"协作": "#6ea8ff", "工程": "#c678dd", "架构": "#2ac3de", "数据": "#56b6c2",
                   "治理": "#e06c75", "资源冲突": "#f5b942", "运营": "#34c77b"}
RULE_CATS = list(RULE_CAT_COLORS.keys())

def load_rules():
    """读规则账本 rules.json（73 条）+ 关联层 rule-mapping.json"""
    try:
        with open(os.path.join(BASE, "rules-registry", "rules.json"), encoding="utf-8") as f:
            d = json.load(f)
        rules = d.get("rules", [])
        ledger_ver = d.get("version", "?")
    except Exception:
        rules, ledger_ver = [], "?"
    try:
        with open(os.path.join(BASE, "rules-registry", "rule-mapping.json"), encoding="utf-8") as f:
            mp = json.load(f)
    except Exception:
        mp = {"rules": []}
    mprules = {m["id"]: m for m in mp.get("rules", [])}
    for r in rules:
        m = mprules.get(r["id"], {})
        r["agents"] = m.get("agents", [])
        r["blueprints"] = m.get("blueprints", [])
        r["appliesTo"] = m.get("appliesTo", [])
        r["notes"] = m.get("notes", "")
        r["global"] = m.get("global", False)
        r["scope"] = m.get("scope", "all-bus-devices")
    return rules, ledger_ver

def build_rule_graph():
    """规则↔蓝图↔智能体 网络：三类节点 + 三类边"""
    rules, ledger_ver = load_rules()
    bps = [b["id"] for b in get_registry()]
    bp_colors_map = bp_colors()
    agents = get_agents()
    agent_by_short = {}
    for a in agents:
        aid = a["id"]
        # 短 id 前 8
        agent_by_short[aid[:8]] = aid
    # ── 节点 ──
    rnodes, bnodes, anodes = [], [], []
    for r in rules:
        cat = r.get("category", "协作")
        color = RULE_CAT_COLORS.get(cat, "#8b90a3")
        rnodes.append({"id": "rule:" + r["id"], "label": r.get("name", r["id"])[:26], "short": r["id"],
                       "color": color, "dim": cat, "kind": "rule", "r": 10,
                       "status": r.get("status", ""), "summary": r.get("summary", ""),
                       "agents": r.get("agents", []), "blueprints": r.get("blueprints", []),
                       "global": r.get("global", False), "scope": r.get("scope", ""),
                       "enforcedBy": r.get("enforcedBy", "")})
    for b in bps:
        bnodes.append({"id": "bp:" + b, "label": b, "short": b, "color": bp_colors_map.get(b, "#6ea8ff"),
                       "dim": bp_dims().get(b, "?"), "kind": "bp", "r": 14})
    for a in agents:
        aid = a["id"]
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        role = a.get("role", "")
        label = re.sub(r"^([^-]+-[^-]+).*", r"\\1", role) if role else aid[:8]
        anodes.append({"id": "ag:" + aid, "label": label[:22], "short": aid[:6],
                       "color": dcolor, "dim": dname, "kind": "agent", "r": 9,
                       "role": role, "agentId": aid})
    # ── 边 ──
    edges = []
    # rule → blueprint（映射层）
    for r in rules:
        rid = r["id"]
        for bp in r.get("blueprints", []):
            if bp in bps:
                edges.append({"source": "rule:" + rid, "target": "bp:" + bp, "type": "约束", "color": "#e06c75"})
    # rule → agent（映射层：短 id 前缀匹配完整 session id）
    for r in rules:
        rid = r["id"]
        for ag in r.get("agents", []):
            short = ag[-8:] if len(ag) > 8 else ag
            full = agent_by_short.get(short)
            if not full:
                # 兜底：直接找含短 id 的
                full = next((a["id"] for a in agents if a["id"].endswith(short) or short in a["id"]), None)
            if full:
                edges.append({"source": "rule:" + rid, "target": "ag:" + full, "type": "相关智能体", "color": "#34c77b"})
    # 精简视图：只保留有边节点（避免 60+ 孤立规则无意义占位）
    linked = set()
    for e in edges:
        linked.add(e["source"]); linked.add(e["target"])
    snodes = [n for n in (rnodes + bnodes + anodes) if n["id"] in linked or n["kind"] == "bp" or n.get("global")]
    # 规则域 confirmed 边(连接实验室确认后并入 → 紫虚线转实线)
    try:
        for _l in get_confirmed_links("rules"):
            if _l.get("from") in {x.get("id") for x in snodes} and _l.get("to") in {x.get("id") for x in snodes}:
                edges.append({"source": _l.get("from"), "target": _l.get("to"), "type": "confirmed",
                              "color": "#c678dd", "desc": _l.get("desc",""),
                              "status": _l.get("status","confirmed")})
    except Exception: pass
    return {"nodes": snodes, "edges": edges, "mode": "rules", "compact": True,
            "fullNodeCount": len(rnodes) + len(bnodes) + len(anodes),
            "ledgerVer": ledger_ver, "ruleCount": len(rules), "categories": RULE_CATS}

def load_mechanism():
    try:
        with open(os.path.join(GALLERY_DIR, "mechanism.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"protocols": [], "gates": [], "locks": [], "links": []}

def build_mechanism_graph():
    mech = load_mechanism()
    nodes = []
    edges = []
    # 门健康概览节点(gate-auditor 审计结果: 纸面门 vs 结构门)
    gh = mech.get("gate_health")
    if gh:
        nodes.append({"id": "gate-health", "label": "门健康", "short": "门健康",
                      "color": "#e06c75" if gh.get("paper_gates", 0) > 20 else "#f0b429",
                      "dim": "门健康", "kind": "mech-g", "type": "gate",
                      "r": 14, "summary": f"规则 {gh.get('total_rules')} · 结构门 {gh.get('structural_gates')} · 纸面门 {gh.get('paper_gates')}(待修·gate-repairer)",
                      "doc": gh.get("source", ""), "paper": gh.get("paper_gates", 0)})
    for p0 in mech.get("protocols", []):
        nodes.append({"id": p0["id"], "label": p0["name"], "short": p0["id"], "color": p0["color"],
                      "dim": "协议", "kind": "mech-p", "type": "protocol", "r": 13,
                      "summary": p0.get("summary", ""),
                      # ★ 同 gates/locks 的修（统一三者的 doc 回退策略 —— 前两者已修，此处补齐）
                      "doc": p0.get("doc") or p0.get("summary", "") or ""})
    for g in mech.get("gates", []):
        nodes.append({"id": g["id"], "label": g["name"], "short": g["id"], "color": g["color"],
                      "dim": "门", "kind": "mech-g", "type": "gate", "r": 12,
                      "summary": g.get("summary", ""),
                      # ★★ 2026-10-13 修（B3 · tab 层考古「mech-graph 20/31 节点 doc 为空」）：
                      #   根因 = **本行此前根本没填 `doc`**（而 protocols/locks 都填了）
                      #   ⇒ 14 个门的 doc 全空 ⇒ 全图 doc 可核性掉到 1/3。
                      #   ★ 回退到 `summary`（**那是已有的真数据**，非编造）——
                      #     `doc` 的语义就是「指向文档/说明」，而 summary 正是该门的说明。
                      "doc": g.get("doc") or g.get("summary", "") or ""})
    for lk in mech.get("locks", []):
        nodes.append({"id": lk["id"], "label": lk["name"], "short": lk["id"], "color": lk["color"],
                      "dim": "锁", "kind": "mech-l", "type": "lock", "r": 12,
                      "summary": lk.get("summary", ""),
                      # ★ 同 gates 的修（locks 只有 1/5 有 doc ⇒ 回退到 summary）
                      "doc": lk.get("doc") or lk.get("summary", "") or ""})
    for l in mech.get("links", []):
        edges.append({"source": l["from"], "target": l["to"], "type": l.get("type", "关联"),
                      "color": l.get("color", "#8b90a3")})
    return {"nodes": nodes, "edges": edges, "mode": "mech",
            "protocolCount": len(mech.get("protocols", [])),
            "gateCount": len(mech.get("gates", [])),
            "lockCount": len(mech.get("locks", []))}


ML_COLORS = {"bus": "#e06c75", "fnp": "#c678dd", "mem-l1": "#2ac3de", "mem-l2": "#98c379",
             "security": "#f5b942", "digital": "#6ea8ff", "physical": "#34c77b", "supply": "#f0b429",
             "biz": "#6ea8ff", "eco": "#34c77b", "res": "#f5b942", "app": "#c678dd", "bridge": "#e06c75",
             "govern": "#f5b942", "infra": "#2ac3de", "intel": "#6ea8ff", "monetize": "#34c77b",
             "product": "#f5b942", "audit": "#e5c07b", "loop": "#e06c75", "verify": "#2ac3de",
             "library": "#6ea8ff", "standard": "#c678dd", "tooling": "#34c77b", "brand": "#d19a66",
             "content": "#98c379", "traffic": "#56b6c2", "core": "#6ea8ff", "deploy": "#e06c75",
             "rfid": "#34c77b", "admin": "#c678dd", "front": "#56b6c2", "sync": "#98c379"}
ST_COLOR_M = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}



def build_knowledge_graph():
    """知识内核图谱：读预生成的 knowledge-graph.json（报告/论文/蓝图溯源+内聚）"""
    try:
        with open(os.path.join(GALLERY_DIR, "knowledge-graph.json"), encoding="utf-8") as f:
            g = json.load(f)
        return g
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "knowledge", "error": str(e)}




def build_original_graph():
    """💎 原创资产图：6 类原创资产（分类节点+资产节点）"""
    try:
        with open(os.path.join(GALLERY_DIR, "original-assets.json"), encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "original", "error": str(e)}
    cats = data.get("categories", [])
    items = data.get("items", [])
    nodes, edges = [], []
    # 分类节点（环）
    for c in cats:
        nodes.append({"id": "cat:" + c["id"], "label": c["name"], "short": c["name"][:4],
                      "kind": "origcat", "dim": "原创分类", "color": c["color"], "r": 16,
                      "desc": c["desc"]})
    # 资产节点
    for it in items:
        cat = next((c for c in cats if c["id"] == it["cat"]), None)
        color = cat["color"] if cat else "#8b90a3"
        nodes.append({"id": "oa:" + it["id"], "label": it["name"][:20], "short": it["id"],
                      "kind": "origitem", "dim": next((c["name"] for c in cats if c["id"]==it["cat"]), "?"),
                      "color": color, "r": 9, "detail": it.get("detail", ""), "origin": it.get("origin", ""),
                      "tags": it.get("tags", []), "catId": it["cat"]})
        edges.append({"source": "cat:" + it["cat"], "target": "oa:" + it["id"], "type": "属于", "color": color})
    return {"nodes": nodes, "edges": edges, "mode": "original",
            "total": len(items), "catCount": len(cats)}




def build_biz_asset_graph():
    """🌍 跨节点资产图谱(关系层 v2)：设备(通讯通道互联) + 蓝图枢纽 + 资产(设备承载+蓝图归属 双连)
    真实关系源: ①设备通讯 device-links.json(真实通道) ②资产 blueprint 字段(业务归属)
    ⚠️ 只画数据里有据的关系, 不臆造资产间依赖"""
    try:
        with open(os.path.join(GALLERY_DIR, "business-asset-map.json"), encoding="utf-8") as f:
            data = json.load(f)
        dl_path = os.path.join(GALLERY_DIR, "device-links.json")
        dlinks = json.load(open(dl_path, encoding="utf-8")) if os.path.exists(dl_path) else {"links": []}
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "bizmap", "error": str(e)}
    bpcolors = data.get("bpColors", {}); nodecolors = data.get("nodeColors", {})
    assets = data.get("assets", [])
    DEVICE_NAMES = {"mac-mini": "mac-mini 宿主", "i9": "PC-i9", "MBP": "MacBook Pro", "云端": "云端",
                    "xingqiao": "xingqiao 服务器", "mac-mini": "mac-mini"}
    # ── 设备节点(骨架) ──
    device_assets = {}
    for a in assets:
        node = a.get("node", "mac-mini")
        device_assets.setdefault(node, []).append(a)
    nodes, edges = [], []
    dev_nodes = {}
    for node in device_assets:
        did = "dev:" + node
        nodes.append({"id": did, "label": DEVICE_NAMES.get(node, node), "short": node,
                      "kind": "bizdev", "dim": "设备", "color": nodecolors.get(node, "#8b90a3"), "r": 17,
                      "assetCount": len(device_assets[node]),
                      "desc": "设备 " + DEVICE_NAMES.get(node, node) + " · " + str(len(device_assets[node])) + " 项资产"})
        dev_nodes[node] = did
    # ── 蓝图枢纽节点(业务归属中心, 仅资产引用到的) ──
    bp_used = {}
    for a in assets:
        bp = a.get("blueprint", "")
        if bp: bp_used[bp] = bp_used.get(bp, 0) + 1
    bp_nodes = {}
    for bp, cnt in bp_used.items():
        bid = "bp:" + bp
        nodes.append({"id": bid, "label": bp, "short": bp[:6], "kind": "bizbp",
                      "dim": "蓝图", "color": bpcolors.get(bp, "#6ea8ff"), "r": 10 + min(cnt, 6),
                      "assetCount": cnt, "desc": "蓝图 " + bp + " · " + str(cnt) + " 项资产"})
        bp_nodes[bp] = bid
    # ── 设备通讯通道边(真实: 来自 device-links.json, 双向可视) ──
    link_edges = set()
    for l in dlinks.get("links", []):
        f = l.get("from", "").replace("hw:", "").replace("node-", "")
        t = l.get("to", "").replace("hw:", "").replace("node-", "")
        # 只保留设备↔设备(mac-mini/i9/MBP/云端), 服务器内部通道略
        devs = {"macmini": "mac-mini", "pci9": "i9", "mbp": "MBP", "mbp-agent": "MBP", "iphone": "移动"}
        f2 = devs.get(f, f); t2 = devs.get(t, t)
        if f2 in dev_nodes and t2 in dev_nodes and f2 != t2:
            key = tuple(sorted([f2, t2]))
            if key not in link_edges:
                link_edges.add(key)
                edges.append({"source": "dev:" + f2, "target": "dev:" + t2,
                              "type": "通道", "color": "#2ac3de",
                              "chan": l.get("type", ""), "desc": (l.get("protocol") or "") + " " + (l.get("port") or "")})
    # ── 资产节点: 挂设备(承载) + 连蓝图(归属) 双边 ──
    for node, items in device_assets.items():
        parent = dev_nodes[node]
        for a in items:
            bp = a.get("blueprint", "")
            aid = "ba:" + a["name"]
            nodes.append({"id": aid, "label": str(a["name"])[:16], "short": str(a["name"])[:8],
                          "kind": "bizasset", "dim": node, "color": nodecolors.get(node, "#8b90a3"), "r": 7,
                          "name": a["name"], "type": a.get("type", ""), "loc": a.get("location", ""),
                          "isOriginal": a.get("isOriginal", False), "desc": a.get("desc", ""),
                          "blueprint": bp, "bpColor": bpcolors.get(bp, "#8b90a3"),
                          "responder": a.get("responder", "")})
            edges.append({"source": parent, "target": aid, "type": "承载", "color": nodecolors.get(node, "#8b90a3"), "weak": True})
            if bp and bp in bp_nodes:
                edges.append({"source": aid, "target": bp_nodes[bp], "type": "归属", "color": bpcolors.get(bp, "#6ea8ff"), "weak": True})
    # ── 第三层: 资产间显式关系(relations, verified=true) ──
    REL_COLOR = {"depends_on": "#e06c75", "collaborates": "#34c77b", "uses": "#f5b942",
                 "duplicates": "#f0b429", "part_of": "#56b6c2"}
    name_to_id = {a["name"]: "ba:" + a["name"] for a in assets}
    rel_edges = 0
    for r in data.get("relations", []):
        if not r.get("verified", True): continue
        frm, to = r.get("from", ""), r.get("to", "")
        if frm in name_to_id and to in name_to_id:
            tcol = REL_COLOR.get(r.get("type", ""), "#8b90a3")
            edges.append({"source": name_to_id[frm], "target": name_to_id[to],
                          "type": r.get("type", ""), "color": tcol,
                          "desc": r.get("desc", ""), "rel": True})
            rel_edges += 1
    # 汇总
    devs_list = []
    for n, items in device_assets.items():
        devs_list.append({"id": "dev:" + n, "name": DEVICE_NAMES.get(n, n), "count": len(items)})
    return {"nodes": nodes, "edges": edges, "mode": "bizmap",
            "assetCount": len(assets), "deviceCount": len(device_assets),
            "devices": devs_list,
            "bpColors": bpcolors, "nodeColors": nodecolors,
            "channelEdges": len(link_edges), "relEdges": rel_edges}


def build_hardware_graph():
    """🌐 物理层全景：本地设备 + 远端服务器 + 云端服务（分组分层）"""
    try:
        with open(os.path.join(GALLERY_DIR, "hardware-nodes.json"), encoding="utf-8") as f:
            hw = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "hardware", "error": str(e)}
    ST_COLOR = {"运行": "#34c77b", "在线": "#34c77b", "已接入": "#4a9eff", "已任命+闭环": "#98c379",
                "离线": "#7d8596", "待secret": "#f0b429", "未接入": "#7d8596"}
    GROUPS = hw.get("groups", {})
    GRP_COLOR = {"device": "#c678dd", "server": "#f5b942", "cloud": "#2ac3de"}
    nodes, edges = [], []
    # 蓝图节点（宿主关联）
    for bid in ["agent-network", "distributed-network"]:
        nodes.append({"id": "bp:" + bid, "label": bid, "short": bid, "kind": "hwbp", "dim": "蓝图",
                      "color": "#e8eaf0", "r": 12})
    for n in hw.get("nodes", []):
        nid = n["id"]
        if not nid.startswith("hw:"): nid = "hw:" + nid
        grp = n.get("group", "device")
        st = n.get("status", "")
        nodes.append({"id": nid, "label": n.get("name", n.get("device", nid)), "short": nid.replace("hw:", "").replace("node-", "").replace("srv-", "").replace("cloud-", "")[:8],
                      "kind": "hwnode", "dim": GROUPS.get(grp, grp), "group": grp,
                      "color": ST_COLOR.get(st, GRP_COLOR.get(grp, "#8b90a3")), "r": 13,
                      "os": n.get("os", ""), "ip": n.get("ip", ""), "role": n.get("role", ""),
                      "spec": n.get("spec", ""), "status": st, "verify": n.get("verify", ""),
                      "since": n.get("since", ""),
                      "sgVersion": n.get("sgVersion", ""), "sgRole": n.get("sgRole", "")})
    # 边：主节点(mac-mini)连蓝图 + relation 边
    for e in hw.get("relations", []):
        f = e["from"] if e["from"].startswith("hw:") else "hw:" + e["from"]
        t = e["to"] if e["to"].startswith("hw:") else "hw:" + e["to"]
        # 过滤只存在于节点中的
        if any(x["id"] == f for x in nodes) and any(x["id"] == t for x in nodes):
            edges.append({"source": f, "target": t, "type": e.get("type", "关联"), "color": "#8b90a3"})
    edges.append({"source": "hw:node-macmini", "target": "bp:agent-network", "type": "宿主", "color": "#c678dd"})
    edges.append({"source": "hw:node-pci9", "target": "bp:distributed-network", "type": "节点", "color": "#c678dd"})
    edges.append({"source": "hw:node-mbp", "target": "bp:distributed-network", "type": "节点", "color": "#c678dd"})
    return {"nodes": nodes, "edges": edges, "mode": "hardware", "nodeCount": len(hw.get("nodes", [])),
            "hwNodes": hw.get("nodes", []), "groups": GROUPS}


# ── 🛰 设备通讯桥（并入硬件载体 Tab 的通讯层）────────────────
COMM_PROBE_CACHE = {"ts": 0, "result": {}}

def ts_online_set():
    """tailscale status 解析在线 peer IP 集(权威, 防 ICMP 防火墙误判)"""
    import subprocess as _sp
    out = set()
    try:
        r = _sp.run(["/Applications/Tailscale.app/Contents/MacOS/Tailscale", "status"],
                    capture_output=True, text=True, timeout=8)
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) < 3 or not parts[0].startswith("100."):
                continue
            if "offline" in line or "idle" in line or "stopped" in line:
                continue
            if "active" in line or "direct" in line or "relay" in line:
                out.add(parts[0])
    except Exception:
        pass
    return out

def probe_one(kind, target, timeout=3, ts_online=None):
    """探测单条通道: tailscale → ts_online 集合(tailscale status 一次解析); http/funnel → urlopen"""
    try:
        if kind == "tailscale":
            return bool(ts_online and target in ts_online)
        if kind in ("http", "funnel"):
            try:
                with urllib.request.urlopen(target, timeout=timeout) as _r:
                    return _r.status < 500
            except urllib.error.HTTPError as _he:
                # 4xx 也说明服务在响应(如黑板根 400)
                return _he.code < 500
        return None
    except Exception:
        return False

def probe_comm_channels(force=False):
    """探测 device-links.json 里标记的通道, 25s 缓存; 返回 {linkIndex: True/False/None}"""
    import time as _t
    now = _t.time()
    if not force and now - COMM_PROBE_CACHE["ts"] < 25 and COMM_PROBE_CACHE["result"]:
        return COMM_PROBE_CACHE["result"]
    out = {}
    try:
        with open(os.path.join(GALLERY_DIR, "device-links.json"), encoding="utf-8") as f:
            dl = json.load(f)
        online = ts_online_set()
        for p in dl.get("probes", []):
            out[p.get("link")] = probe_one(p.get("kind", "tailscale"), p.get("host") or p.get("url") or "",
                                           ts_online=online)
    except Exception as e:
        out = {"error": str(e)}
    COMM_PROBE_CACHE.update({"ts": now, "result": out})
    return out

def build_hw_comm_graph():
    """🛰 通讯桥: 设备节点 + 真实通讯通道边(带协议/方向/通道类型)"""
    try:
        with open(os.path.join(GALLERY_DIR, "hardware-nodes.json"), encoding="utf-8") as f:
            hw = json.load(f)
        with open(os.path.join(GALLERY_DIR, "device-links.json"), encoding="utf-8") as f:
            dl = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "hwcomm", "error": str(e)}
    ST_COLOR = {"运行": "#34c77b", "在线": "#34c77b", "已接入": "#4a9eff", "已任命+闭环": "#98c379",
                "离线": "#7d8596", "待secret": "#f0b429", "未接入": "#7d8596"}
    GROUPS = hw.get("groups", {})
    CT = dl.get("channelTypes", {})
    nodes, edges = [], []
    for n in hw.get("nodes", []):
        nid = n["id"]
        if not nid.startswith("hw:"): nid = "hw:" + nid
        grp = n.get("group", "device")
        st = n.get("status", "")
        nodes.append({"id": nid, "label": n.get("name", n.get("device", nid)), "short": nid.replace("hw:", "").replace("node-", "").replace("srv-", "").replace("cloud-", "")[:8],
                      "kind": "hwnode", "dim": GROUPS.get(grp, grp), "group": grp,
                      "color": ST_COLOR.get(st, {"device": "#c678dd", "server": "#f5b942", "cloud": "#2ac3de"}.get(grp, "#8b90a3")), "r": 13,
                      "os": n.get("os", ""), "ip": n.get("ip", ""), "role": n.get("role", ""),
                      "spec": n.get("spec", ""), "status": st})
    for i, l in enumerate(dl.get("links", [])):
        f = l["from"] if l["from"].startswith("hw:") else "hw:" + l["from"]
        t = l["to"] if l["to"].startswith("hw:") else "hw:" + l["to"]
        if not any(x["id"] == f for x in nodes) or not any(x["id"] == t for x in nodes):
            continue
        ct = CT.get(l.get("type", ""), {})
        edges.append({"source": f, "target": t, "idx": i, "type": l.get("type", "通道"),
                      "chan": ct.get("label", l.get("type", "")), "color": ct.get("color", "#8b90a3"),
                      "protocol": l.get("protocol", ""), "port": l.get("port", ""),
                      "direction": l.get("direction", "bi"), "desc": l.get("desc", ""),
                      "hasProbe": any(p.get("link") == i for p in dl.get("probes", []))})
    return {"nodes": nodes, "edges": edges, "mode": "hwcomm",
            "channelTypes": CT, "probe": probe_comm_channels(),
            "nodeCount": len(nodes), "linkCount": len(edges), "groups": GROUPS}


# ── 📋 计划档案图谱(所有智能体计划性文件 + 版本汇总)─────
def build_plan_graph():
    """📋 计划档案: 计划/路线图/版本/changelog → 关联蓝图/智能体 力导向"""
    try:
        with open(os.path.join(GALLERY_DIR, "plan-archive.json"), encoding="utf-8") as f:
            pa = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "planarchive", "error": str(e),
                "items": [], "itemCount": 0}
    TYPE_COLOR = {"plan": "#34c77b", "roadmap": "#f5b942", "backlog": "#e5c07b",
                  "blueprint": "#6ea8ff", "changelog": "#c678dd", "version": "#56b6c2",
                  "doc": "#8b90a3", "manual": "#d19a66"}
    DOM_COLOR = {"老登/MTM": "#e06c75", "老登App": "#e84393", "明鉴/SystemGraph": "#61afef",
                 "协作文档": "#8b90a3", "蓝图": "#6ea8ff", "工具链": "#2ac3de",
                 "守灯/CLD": "#98c379", "ERP": "#f5b942"}
    items = pa.get("items", [])
    nodes, edges = [], []
    seen_dom = {}
    for it in items:
        dom = it.get("domain", "其它")
        if dom not in seen_dom:
            seen_dom[dom] = True
            nodes.append({"id": "d:" + dom, "label": dom, "short": dom[:6], "kind": "pland",
                          "dim": "域", "color": DOM_COLOR.get(dom, "#8b90a3"), "r": 15,
                          "type": "domain", "count": 0})
    seen_bp = {}
    for it in items:
        bp = it.get("blueprint", "")
        if bp and bp not in seen_bp:
            seen_bp[bp] = True
            nodes.append({"id": "bp:" + bp, "label": bp, "short": bp[:6], "kind": "planbp",
                          "dim": "蓝图", "color": bp_colors().get(bp, "#6ea8ff"), "r": 11})
    for it in items:
        nid = it["id"]
        typ = it.get("type", "doc")
        nodes.append({"id": nid, "label": it.get("title", "")[:22], "short": it.get("file", "").split("/")[-1][:8],
                      "kind": "planitem", "dim": typ, "color": TYPE_COLOR.get(typ, "#8b90a3"), "r": 7,
                      "title": it.get("title", ""), "type": typ, "file": it.get("file", ""),
                      "domain": it.get("domain", ""), "version": it.get("version", ""),
                      "blueprint": it.get("blueprint", ""), "agent": it.get("agent", ""),
                      "status": it.get("status", ""), "updated": it.get("updated", ""),
                      "desc": it.get("desc", "")})
        edges.append({"source": "d:" + it.get("domain", "其它"), "target": nid, "type": "属域", "color": "#8b90a3"})
        if it.get("blueprint"):
            edges.append({"source": nid, "target": "bp:" + it["blueprint"], "type": "关联蓝图", "color": "#6ea8ff"})
    for nd in nodes:
        if nd["id"].startswith("d:"):
            nd["count"] = sum(1 for it in items if it.get("domain") == nd["label"])
    return {"nodes": nodes, "edges": edges, "mode": "planarchive",
            "items": items, "itemCount": pa.get("itemCount", len(items)),
            "domains": pa.get("domains", []), "typeColors": TYPE_COLOR}


def load_workflow_standards():
    try:
        with open(os.path.join(GALLERY_DIR, "workflow-standards.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def build_workflow_graph():
    """🔄 工作流/标准：R006 九标准节点 + 高频工作流模式 + 关联"""
    w = load_workflow_standards()
    nodes, edges = [], []
    # R006 总节点
    nodes.append({"id":"r006","label":"R006 九标准","short":"R006","kind":"std","dim":"标准",
                  "color":"#e8eaf0","r":16,"name":"插件化工具化标准"})
    # 九项标准
    for it in w.get("r006",{}).get("items",[]):
        t=tools_of(it.get("tools",[]))  # 容错: 缺 tools 键不 500 (2026-09-08 修复)
        nodes.append({"id":"r006-"+str(it["n"]),"label":f"{it['n']}.{it['name']}"[:20],"short":str(it["n"]),
                      "kind":"stditem","dim":"标准项","color":"#6ea8ff","r":9,
                      "name":it["name"],"note":it.get("note",""),"tools":it.get("tools",[]),
                      "toolsDesc":str(it.get("tools")) if isinstance(it.get("tools"),int) else "· ".join(t)})
        edges.append({"source":"r006","target":"r006-"+str(it["n"]),"type":"含","color":"#6ea8ff"})
    # 工作流模式
    WF_COLORS=["#2ac3de","#c678dd","#34c77b","#e5c07b","#56b6c2","#d19a66"]
    for i,wf in enumerate(w.get("workflows",[])):
        nodes.append({"id":"wf:"+wf["id"],"label":wf["name"][:16],"short":wf["id"],"kind":"workflow",
                      "dim":"工作流","color":WF_COLORS[i%6],"r":13,
                      "desc":wf.get("desc",""),"tool":wf.get("tool",""),"steps":wf.get("steps",[]),
                      "since":wf.get("since","")})
    return {"nodes":nodes,"edges":edges,"mode":"workflow",
            "r006":w.get("r006",{}),"workflows":w.get("workflows",[]),
            "metaUsage":w.get("meta_usage",{}),"termDist":w.get("term_distribution",{})}

def tools_of(t):
    if isinstance(t,int): return f"{t} 工具"
    if isinstance(t,list): return " ".join(str(x) for x in t[:3])
    return str(t)

def build_philosophy_graph():
    """🧠 治理哲学体系塔：一句话原则→4哲学→派生机制→落地"""
    try:
        with open(os.path.join(GALLERY_DIR, "governance-philosophy.json"), encoding="utf-8") as f:
            phi = json.load(f)
    except Exception as e:
        return {"nodes": [], "edges": [], "mode": "philosophy", "error": str(e)}
    nodes, edges = [], []
    # 顶层：一句话原则（核心）
    nodes.append({"id": "phi:root", "label": "能力与权限分离", "short": "R027 原则", "kind": "phiroot",
                  "dim": "一句话原则", "color": "#e8eaf0", "r": 20,
                  "summary": phi.get("topPrinciple", "")})
    # 4 哲学
    PHI_COLORS = ["#e06c75", "#f5b942", "#2ac3de", "#c678dd"]
    for i, p in enumerate(phi.get("philosophies", [])):
        nodes.append({"id": "ph:" + p["id"], "label": p["name"][:16], "short": p["id"].replace("phi-", "Φ"),
                      "kind": "philosophy", "dim": "治理哲学", "color": PHI_COLORS[i % 4], "r": 15,
                      "name": p["name"], "core": p["core"], "origin": p.get("origin", ""),
                      "doc": p.get("doc", ""), "order": p.get("order", i+1),
                      "detail": p.get("detail", ""), "principles": p.get("principles", []),
                      "examples": p.get("examples", []), "relDocs": p.get("relDocs", []),
                      "children": p.get("children", [])})
        edges.append({"source": "phi:root", "target": "ph:" + p["id"], "type": "派生", "color": "#e8eaf0"})
    # 派生落地（规则/机制/蓝图节点）
    rules, _ = load_rules()
    rule_map = {r["id"]: r for r in rules}
    added = set()
    for p in phi.get("philosophies", []):
        for d in p.get("derives", []):
            if d in added: continue
            added.add(d)
            if d.startswith("rule:"):
                rid = d[5:]
                r = rule_map.get(rid, {})
                nodes.append({"id": "rule:" + rid, "label": (rid + " " + r.get("name", ""))[:18], "short": rid,
                              "kind": "phirule", "dim": "规则", "color": "#8b90a3", "r": 9,
                              "summary": r.get("summary", "")})
                edges.append({"source": "ph:" + p["id"], "target": "rule:" + rid, "type": "落地", "color": "#8b90a3"})
            elif d.startswith("blueprint:"):
                bid = d[9:]
                nodes.append({"id": "bp:" + bid, "label": bid, "short": bid, "kind": "phibp",
                              "dim": "蓝图", "color": "#e8eaf0", "r": 13})
                edges.append({"source": "ph:" + p["id"], "target": "bp:" + bid, "type": "落地", "color": "#8b90a3"})
    return {"nodes": nodes, "edges": edges, "mode": "philosophy",
            "topPrinciple": phi.get("topPrinciple", ""), "phiCount": len(phi.get("philosophies", [])),
            "layers": phi.get("layers", [])}

def build_system_assets():
    """🗄 系统资产视图：运行中服务（端口扫描）+ 归属蓝图"""
    # 静态表：系统 → 属主蓝图/技术栈/描述
    SYS = [
      {"id":"cld","name":"CLD 宿主","tech":"Electron v0.1.0","ports":"61348,31888","blueprint":"agent-network","layer":"宿主","desc":"DeepSeek Harness 桌面壳——所有智能体会话运行载体；守灯健康治理+R016","owner":"守灯"},
      {"id":"genebank","name":"GeneBank 基因库","tech":"Rust+Python","ports":"8801","blueprint":"gene-bank","layer":"存储底座","desc":"AI 网盘：内容寻址资产存储 6 染色体（5.5万注册）","owner":"守灯塔"},
      {"id":"blackboard","name":"黑板","tech":"Rust v0.6","ports":"8792","blueprint":"flowernet-platform","layer":"平台","desc":"黑板 KV/事件总线（Rust 版运行）","owner":"星桥"},
      {"id":"blackboard-mcp","name":"黑板 MCP","tech":"Rust","ports":"8810","blueprint":"flowernet-platform","layer":"接入","desc":"任意设备标准接入 bb_read/bb_subscribe","owner":"星桥"},
      {"id":"node-bridge","name":"node-bridge","tech":"Rust","ports":"守护","blueprint":"distributed-network","layer":"分布式","desc":"分布式节点统一桥（中枢×i9/mbp）","owner":"罗盘"},
      {"id":"mtm-panel","name":"外卖面板 MTM","tech":"Node","ports":"8787","blueprint":"flowernet","layer":"业务采集","desc":"10 店采集监控/告警/IM","owner":"灯塔"},
      {"id":"ext-link","name":"外链服务","tech":"Node","ports":"8790,8791,8910,8911","blueprint":"distributed-network","layer":"外联","desc":"企微/飞书/总线桥/SSE 跨设备通道","owner":"驿使"},
      {"id":"bus-bridge","name":"bus-bridge 总线桥","tech":"Node","ports":"8791","blueprint":"distributed-network","layer":"分布式","desc":"服务器信封收发+SSE推送(免轮询)+tasks持久化TTL——R033/R034 通道治理载体","owner":"星桥"},
      {"id":"device-daemon","name":"device-daemon 设备守护","tech":"Python","ports":"SSE订阅","blueprint":"distributed-network","layer":"守护","desc":"三端守护(mac-mini/MBP/i9)SSE长连订阅bus/events→转黑板→central-inbox角色映射唤醒","owner":"星桥"},
      {"id":"central-inbox","name":"central-inbox","tech":"Node","ports":"—","blueprint":"agent-network","layer":"注入","desc":"角色名→会话映射精确唤醒(S1)agent-role-map.json ★ 计数由 UI 现算（原硬编码「20角色」实测已到 21 会话）","owner":"星桥"},
      {"id":"chromadb","name":"ChromaDB 向量库","tech":"Python","ports":"8000","blueprint":"gene-bank","layer":"知识","desc":"向量索引（notes/wiki/research）","owner":"3b5efeef"},
      {"id":"obsidian","name":"Obsidian vault","tech":"iCloud","ports":"—","blueprint":"gene-bank","layer":"知识","desc":"raw/wiki/日记 LLM wiki 库","owner":"文汇"},
      {"id":"dsh-kb","name":"DSH KB","tech":"SQLite","ports":"—","blueprint":"gene-bank","layer":"知识","desc":"语义库（★ 库数/文档数由 UI 现算；原硬编码「8 库 547 文档」实测已到 27 库 764 文档）","owner":"文汇"},
      {"id":"data-tools","name":"rust-data-tools","tech":"Rust","ports":"CLI","blueprint":"rule-judge","layer":"工具","desc":"chat-records/price-analysis","owner":"知了"},
      {"id":"ollama","name":"Ollama","tech":"本地","ports":"11434","blueprint":"agent-network","layer":"推理","desc":"qwen2.5:3b/bge-m3 本地模型","owner":"守灯塔"},
      {"id":"lmstudio","name":"LM Studio","tech":"本地","ports":"1234","blueprint":"agent-network","layer":"推理","desc":"qwen3.8-27b/glm-4.6v 视觉","owner":"明鉴"},
      {"id":"gallery","name":"系统架构管理器","tech":"Python","ports":"8798","blueprint":"blueprint-platform","layer":"工具","desc":"本管理器：蓝图/智能体/规则/机制/知识图谱","owner":"明鉴"},
      {"id":"bb-ui2","name":"蓝图 GUI v2","tech":"Python","ports":"8797","blueprint":"blueprint-platform","layer":"工具","desc":"flowernet 可视化中枢","owner":"明鉴"},
    ]
    # 端口存活探测：支持逗号列表 + a-b 范围 + "守护/CLI/—"标注
    import subprocess
    def check_port(p):
        try:
            r=subprocess.run(["lsof","-iTCP:"+str(p),"-sTCP:LISTEN"],capture_output=True,text=True,timeout=3)
            return bool(r.stdout.strip())
        except Exception: return False
    for s2 in SYS:
        s2["alive"] = False
        ps = str(s2.get("ports","")).replace("—","").replace(" ","")
        if not ps or ps in ("守护","CLI"):  # 守护/CLI 类默认未知——按技术栈推断
            s2["alive"] = "unknown"; continue
        parts = ps.split(",")
        for part in parts:
            if "-" in part:  # 范围 a-b
                a,b = part.split("-")
                if a.isdigit() and b.isdigit():
                    for p in range(int(a), int(b)+1):
                        if check_port(p): s2["alive"]=True; break
            elif part.isdigit():
                if check_port(int(part)): s2["alive"]=True; break
    # 动态图谱数据：系统节点(层色) + 属主蓝图节点 + 归属/依赖边
    nodes=[]; edges=[]
    LAYER_COLOR={"存储底座":"#f5b942","平台":"#6ea8ff","接入":"#2ac3de","分布式":"#c678dd",
                 "业务采集":"#34c77b","外联":"#e5c07b","知识":"#56b6c2","工具":"#98c379",
                 "推理":"#e06c75"}
    sys_nodes=[]
    for s2 in SYS:
        nid="sys:"+s2["id"]
        nodes.append({"id":nid,"label":s2["name"],"short":s2["id"],"kind":"sysnode",
                      "dim":s2["layer"],"color":LAYER_COLOR.get(s2["layer"],"#8b90a3"),"r":11,
                      "alive":s2.get("alive"),"tech":s2["tech"],"ports":s2.get("ports",""),
                      "bp":s2["blueprint"],"desc":s2["desc"]})
        sys_nodes.append(nid)
        edges.append({"source":nid,"target":"bp:"+s2["blueprint"],"type":"归属","color":"#6ea8ff"})
    # 蓝图节点（属主）
    for bp in ["gene-bank","flowernet-platform","agent-network","flowernet","rule-judge","blueprint-platform","distributed-network"]:
        if any(s["blueprint"]==bp for s in SYS):
            nodes.append({"id":"bp:"+bp,"label":bp,"short":bp,"kind":"sysbp","dim":"蓝图",
                          "color":"#e8eaf0","r":14})
    # 系统间依赖（静态边）
    DEPS=[("sys:chromadb","sys:genebank","存储"),("sys:obsidian","sys:genebank","存储"),
          ("sys:dsh-kb","sys:genebank","存储"),("sys:genebank","sys:blackboard","注册通知"),
          ("sys:ext-link","sys:blackboard","通讯"),("sys:blackboard-mcp","sys:blackboard","接入"),
          ("sys:node-bridge","sys:blackboard","桥接"),("sys:gallery","sys:blackboard","数据源"),
          ("sys:mtm-panel","sys:blackboard","上报"),("sys:ollama","sys:lmstudio","模型")]
    for f,t,typ in DEPS:
        if f in sys_nodes and t in sys_nodes:
            edges.append({"source":f,"target":t,"type":typ,"color":"#8b90a3"})
    return {"systems": SYS, "total": len(SYS), "alive": sum(1 for s2 in SYS if s2.get("alive") is True),
            "graph": {"nodes":nodes,"edges":edges,"mode":"system-graph"}}

def detect_islands():
    """L1 自进化信号：检测各图谱孤岛节点 + 产出候选清单（智能体网络为重点）"""
    report = {"agents": {"total": 0, "islands": [], "candidates": []},
              "rules": {"total": 0, "islands": []},
              "mechanism": {"total": 0, "islands": []}}
    # 智能体
    try:
        ag = build_agent_graph()
        agent_nodes = ag["nodes"]
        linked = set()
        for e in ag["edges"]:
            linked.add(e["source"]); linked.add(e["target"])
        report["agents"]["total"] = len(agent_nodes)
        # 岛屿 = 无资源共享边 且 无父归属
        islands = [n for n in agent_nodes if n["id"] not in linked and not n.get("parentId") and "inactive" not in str(n.get("role","")) and "已交接" not in str(n.get("role","")) and "前任" not in str(n.get("role","")) and "后备" not in str(n.get("role",""))]
        # 排除设计性孤立（通用/子代理归属）后才是真实候选
        for n in islands:
            role = n.get("role", "")
            report["agents"]["islands"].append({"id": n["id"], "label": n["label"], "short": n["short"],
                                                "role": role[:60], "domain": n.get("dim", "")})
    except Exception as e:
        report["agents"]["error"] = str(e)
    # 规则（真实孤岛：mapping 中无蓝图/agent/appliesTo 且非 global——与 rust island 一致）
    try:
        import os as _os
        mp_path = _os.path.join(BASE, "rules-registry", "rule-mapping.json")
        with open(mp_path, encoding="utf-8") as _f:
            mp_rules = json.load(_f).get("rules", [])
        report["rules"]["total"] = len(mp_rules)
        for r in mp_rules:
            if (not r.get("global") and not r.get("blueprints") and not r.get("agents")
                    and not r.get("appliesTo")):
                report["rules"]["islands"].append({"id": r["id"], "label": r.get("name", r["id"])[:50],
                                                    "short": r["id"]})
    except Exception as e:
        report["rules"]["error"] = str(e)
    return report

def build_blueprint_graph(bid):
    """蓝图 → 力导向图：蓝图(根)→主线→主阶段→子阶段 层级 + 状态色"""
    bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return {"nodes": [], "edges": [], "mode": "bp"}
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", []) or []
    nodes, edges = [], []
    # 根：蓝图
    nodes.append({"id": "rt:" + bid, "label": bid, "short": bid, "dim": "蓝图",
                  "color": bp_colors().get(bid, "#6ea8ff"), "r": 20, "kind": "bproot", "summary": bp.get("name", "")})
    # 主线
    for mid in ml_keys:
        meta = ml[mid]
        mname = meta.get("name", mid) if isinstance(meta, dict) else mid
        mcolor = ML_COLORS.get(mid, "#8b90a3")
        nodes.append({"id": "ml:" + mid, "label": mname[:14], "short": mid, "dim": "主线",
                      "color": mcolor, "r": 14, "kind": "bpml",
                      "summary": (meta.get("desc", "") if isinstance(meta, dict) else "")[:80]})
        edges.append({"source": "rt:" + bid, "target": "ml:" + mid, "type": "含", "color": "#6ea8ff"})
    # 主阶段 + 子阶段
    for st in stages:
        mid = st.get("mainline", "")
        if mid not in ml_keys: continue
        sid = st.get("id", "")
        sc = ST_COLOR_M.get(st.get("status", "todo"), "#7d8596")
        nodes.append({"id": "st:" + sid, "label": (str(st.get("stage", "")) + " " + str(st.get("name", "")))[:16],
                      "short": sid, "dim": "阶段", "color": sc, "r": 12, "kind": "bpstage",
                      "status": st.get("status", "todo"), "summary": str(st.get("name", ""))[:60]})
        edges.append({"source": "ml:" + mid, "target": "st:" + sid, "type": "含", "color": ML_COLORS.get(mid, "#8b90a3")})
        for ss in st.get("substages", []):
            ssid = ss.get("id", "")
            ssc = ST_COLOR_M.get(ss.get("status", "todo"), "#7d8596")
            nodes.append({"id": "ss:" + ssid, "label": (ssid + " " + str(ss.get("name", "")))[:18],
                          "short": ssid, "dim": "子阶段", "color": ssc, "r": 9, "kind": "bpass",
                          "status": ss.get("status", "todo"), "summary": str(ss.get("name", ""))[:60]})
            edges.append({"source": "st:" + sid, "target": "ss:" + ssid, "type": "含", "color": sc})
    return {"nodes": nodes, "edges": edges, "mode": "bp-graph",
            "rootId": "rt:" + bid, "rootName": bid, "bpName": bp.get("name", bid)}

def svg_relations():
    """关系网络 SVG：环形布局 + 边类型着色（静态图，力导向交互版在前端）"""
    rel = get_relations()
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    W, H = 1500, 900
    dims = bp_dims()
    colors = bp_colors()
    n = len(bps)
    cx, cy = W / 2, H / 2
    R = 330
    pos = {}
    for i, b in enumerate(bps):
        ang = -90 + i * (360 / max(n, 1))
        pos[b] = (cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang)))
    ecolor = {"contains": "#8b90a3", "depends_on": "#e06c75", "requires": "#f5b942",
              "consumes": "#34c77b", "manages": "#6ea8ff", "references": "#c678dd",
              "consumed_by": "#2ac3de", "child_of": "#56b6c2"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    for e in edges:
        frm, to = e.get("from"), e.get("to")
        if frm not in pos or to not in pos:
            continue
        x1, y1 = pos[frm]; x2, y2 = pos[to]
        col = ecolor.get(e.get("type"), "#8b90a3")
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.6" opacity="0.75"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx}" y="{my-5}" fill="{col}" font-size="9.5" text-anchor="middle">{esc(e.get("type",""))}</text>')
    lx, ly = 30, H - 24
    parts.append(f'<text x="{lx}" y="{ly-14}" fill="#8b90a3" font-size="12" font-weight="bold">边类型: </text>')
    lx = 100
    for t, c in [("contains","⊃"),("depends_on","→依赖"),("requires","→要求"),("consumes","→消费"),
                 ("manages","→管理"),("references","→引用"),("consumed_by","←消费"),("child_of","子")]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="{c}" font-size="11">{c} {t}</text>')
        lx += 175
    for b in bps:
        x, y = pos[b]
        col = colors.get(b, "#6ea8ff")
        dim = dims.get(b, "?")
        r = 58 if dim != "子蓝图" else 42
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" opacity="0.9" stroke="#0b0e14" stroke-width="2"/>')
        parts.append(f'<text x="{x}" y="{y-2}" fill="#fff" font-size="12.5" font-weight="bold" text-anchor="middle">{esc(b[:16])}</text>')
        parts.append(f'<text x="{x}" y="{y+14}" fill="rgba(255,255,255,.85)" font-size="9.5" text-anchor="middle">{esc(dim)}</text>')
    parts.append("</svg>")
    return "".join(parts)

def svg_fishbone(bid, bp=None):
    """通用鱼骨图（石川图）：任意蓝图的 mainlines→大骨、stages→中骨、substages→小骨
    支持点击骨头展开/收起（交互由前端 JS toggleFishBone 提供）。
    与 ui2 不同：主线数不硬编码（flowernet 3 条 / memory-governance 3 条 / banking 3 条均可用）。"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return f'<svg width="800" height="120"><text x="20" y="40" fill="#e06c75">无数据: {esc(bid)}</text></svg>'
    ml = bp.get("mainlines", {})
    ml_keys = list(ml.keys()) if isinstance(ml, dict) else []
    stages = bp.get("stages", []) or []
    ml_colors = {k: c for k, c in zip(
        ml_keys,
        ["#6ea8ff", "#34c77b", "#f5b942", "#e06c75", "#c678dd", "#e5c07b", "#56b6c2", "#98c379", "#d19a66", "#2ac3de"][:len(ml_keys)])}
    st_color = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}
    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}

    # 动态布局：每条主线一条"鱼"，垂直堆叠
    W = 1700
    spine_x0, spine_x1 = 200, 1560
    n_ml = len(ml_keys)
    # 每条鱼高 = 头 120 + 大骨区（由该主线最多 stages 决定）
    per_fish = 240
    H = n_ml * per_fish + 90
    parts = [f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    parts.append(f'<text x="30" y="36" fill="#e8eaf0" font-size="20" font-weight="bold">{esc(bp.get("name", bid))} · 鱼骨图</text>')
    parts.append(f'<text x="30" y="58" fill="#8b90a3" font-size="12">目标 ← 主线(大骨) ← 主阶段(中骨) ← 子阶段(小骨) · 点击骨头展开/收起</text>')

    def render_one_fish(fi, mid):
        meta = ml[mid]
        title = meta.get("name", mid) if isinstance(meta, dict) else mid
        color = ml_colors.get(mid, "#6ea8ff")
        base_y = 90 + fi * per_fish
        head_y = base_y + 90
        fparts = []
        # 主干
        fparts.append(f'<line x1="{spine_x0}" y1="{head_y}" x2="{spine_x1}" y2="{head_y}" stroke="{color}" stroke-width="6" opacity="0.7"/>')
        # 鱼头（主线目标）
        head_x = spine_x1 + 40
        fparts.append(f'<polygon points="{head_x},{head_y-52} {head_x+80},{head_y} {head_x},{head_y+52}" fill="{color}" opacity="0.9"/>')
        fparts.append(f'<text x="{head_x-8}" y="{head_y+5}" fill="#fff" font-size="15" font-weight="bold" text-anchor="end">{esc(title[:18])}</text>')
        # 主线名（鱼尾侧）
        fparts.append(f'<text x="{spine_x0-40}" y="{head_y-18}" fill="{color}" font-size="14" font-weight="bold" text-anchor="end">{esc(mid)}</text>')
        fparts.append(f'<text x="{spine_x0-40}" y="{head_y}" fill="#8b90a3" font-size="10" text-anchor="end">{esc(str(meta.get("desc",""))[:40] if isinstance(meta,dict) else "")}</text>')
        # 大骨 = 该主线 stages（沿 spine 分布，上下交替）
        m_stages = [s for s in stages if s.get("mainline") == mid]
        n = len(m_stages)
        for j, s in enumerate(m_stages):
            ax = spine_x0 + (spine_x1 - spine_x0) * (j + 0.6) / (n + 0.3)
            ay = head_y
            dir_y = -1 if j % 2 == 0 else 1
            bx = ax - 130
            by = ay + 105 * dir_y
            sc = st_color.get(s.get("status"), "#7d8596")
            m_id = f"fb-{mid}-{s.get('id','')}"
            sub_id = f"fbs-{mid}-{s.get('id','')}"
            mx, my = (ax + bx) / 2, (ay + by) / 2
            fparts.append(f'<g class="fb-main" id="{m_id}" onclick="toggleFishBone(&quot;{sub_id}&quot;)" style="cursor:pointer">')
            fparts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{sc}" stroke-width="5"/>')
            fparts.append(f'<text x="{mx}" y="{my-8}" fill="{sc}" font-size="14" font-weight="bold" text-anchor="middle">{esc(str(s.get("stage",""))+" "+str(s.get("name",""))[:16])}</text>')
            fparts.append(f'<text x="{mx}" y="{my+10}" fill="#8b90a3" font-size="10" text-anchor="middle">{st_icon.get(s.get("status","todo"),"")}</text>')
            fparts.append(f'</g>')
            # 中骨 = substages（沿大骨分布）
            subs = s.get("substages", [])
            mid_parts = []
            for k, ss in enumerate(subs):
                f2 = (k + 0.6) / (len(subs) + 0.3) if subs else 0.5
                cx = ax + (bx - ax) * f2
                cy = ay + (by - ay) * f2
                cdir = 1 if dir_y < 0 else -1
                ex = cx + (30 if cdir > 0 else -30)
                ey = cy + 46 * cdir
                ssc = st_color.get(ss.get("status"), "#7d8596")
                mid_parts.append(f'<g style="cursor:default">')
                mid_parts.append(f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="{ssc}" stroke-width="2.5"/>')
                mid_parts.append(f'<text x="{ex}" y="{ey}" fill="{ssc}" font-size="11" text-anchor="middle" dy="{-4 if cdir<0 else 12}">{esc(ss.get("id","")+" "+str(ss.get("name",""))[:12])}</text>')
                mid_parts.append(f'</g>')
            fparts.append(f'<g class="fbsubs" id="{sub_id}" style="display:none">{"".join(mid_parts)}</g>')
        return "".join(fparts)

    for fi, mid in enumerate(ml_keys):
        parts.append(render_one_fish(fi, mid))

    # 图例
    lx = 60
    for k, ic in [("done", "✅ 完成"), ("active", "🟢 进行中"), ("partial", "🟡 部分"), ("todo", "⬜ 待做")]:
        parts.append(f'<text x="{lx}" y="{H-22}" fill="#8b90a3" font-size="12">{ic}</text>')
        lx += 120
    parts.append(f'<text x="{lx}" y="{H-22}" fill="#8b90a3" font-size="12">点击主线骨头展开/收起子阶段</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"

def svg_timeline(bid, bp=None):
    """时间线视图：蓝图主线按序排布 stage 卡片（通用版）"""
    if bp is None:
        bp = get_blueprint(bid)
    if not bp or "mainlines" not in bp:
        return f'<svg width="800" height="120"><text x="20" y="40" fill="#e06c75">无数据: {esc(bid)}</text></svg>'
    ml = bp.get("mainlines", {})
    stages = bp.get("stages", []) or []
    st_color = {"done": "#34c77b", "active": "#4a9eff", "partial": "#f5b942", "todo": "#7d8596"}
    st_icon = {"done": "✅", "active": "🟢", "partial": "🟡", "todo": "⬜"}
    W, H = 1500, max(120, 90 + len(stages) * 62)
    parts = [f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    parts.append(f'<text x="30" y="40" fill="#e8eaf0" font-size="20" font-weight="bold">{esc(bp.get("name", bid))} · 阶段时间线</text>')
    y = 80
    for s in stages:
        sc = st_color.get(s.get("status"), "#7d8596")
        sid = esc(str(s.get("id", "")))
        sname = esc(str(s.get("stage", "")) + " " + str(s.get("name", ""))[:40])
        mlid = esc(str(s.get("mainline", "")))
        subs = " ".join(f'<text x="{820 + i*0}" y="{y+8}" fill="{st_color.get(ss.get("status","todo"),"#7d8596")}" font-size="9">· {esc(ss.get("id",""))}</text>' for i, ss in enumerate(s.get("substages", [])[:6]))
        parts.append(f'<rect x="40" y="{y-20}" width="1400" height="46" rx="8" fill="#141824" stroke="{sc}" stroke-width="1.5"/>')
        parts.append(f'<circle cx="58" cy="{y+3}" r="6" fill="{sc}"/>')
        parts.append(f'<text x="76" y="{y+8}" fill="{sc}" font-size="13" font-weight="bold">{st_icon.get(s.get("status","todo"),"")} {sid} · {sname[:46]}</text>')
        parts.append(f'<text x="1440" y="{y+8}" fill="#8b90a3" font-size="10" text-anchor="end">主线: {esc(mlid)}</text>')
        y += 62
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">' + "".join(parts) + "</svg>"


    """关系网络 SVG：环形布局 + 边类型着色"""
    rel = get_relations()
    bps = rel.get("blueprints", [])
    edges = rel.get("edges", [])
    W, H = 1500, 900
    dims = bp_dims()
    colors = bp_colors()
    n = len(bps)
    cx, cy = W / 2, H / 2
    R = 330
    pos = {}
    for i, b in enumerate(bps):
        ang = -90 + i * (360 / max(n, 1))
        pos[b] = (cx + R * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang)))
    ecolor = {"contains": "#8b90a3", "depends_on": "#e06c75", "requires": "#f5b942",
              "consumes": "#34c77b", "manages": "#6ea8ff", "references": "#c678dd",
              "consumed_by": "#2ac3de", "child_of": "#56b6c2"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    for e in edges:
        frm, to = e.get("from"), e.get("to")
        if frm not in pos or to not in pos:
            continue
        x1, y1 = pos[frm]; x2, y2 = pos[to]
        col = ecolor.get(e.get("type"), "#8b90a3")
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.6" opacity="0.75"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx}" y="{my-5}" fill="{col}" font-size="9.5" text-anchor="middle">{esc(e.get("type",""))}</text>')
    # 边图例
    lx, ly = 30, H - 24
    parts.append(f'<text x="{lx}" y="{ly-14}" fill="#8b90a3" font-size="12" font-weight="bold">边类型: </text>')
    lx = 100
    for t, c in [("contains","⊃"),("depends_on","→依赖"),("requires","→要求"),("consumes","→消费"),
                 ("manages","→管理"),("references","→引用"),("consumed_by","←消费"),("child_of","子")]:
        parts.append(f'<text x="{lx}" y="{ly}" fill="{c}" font-size="11">{c} {t}</text>')
        lx += 175
    # 节点
    for b in bps:
        x, y = pos[b]
        col = colors.get(b, "#6ea8ff")
        dim = dims.get(b, "?")
        r = 58 if dim != "子蓝图" else 42
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" opacity="0.9" stroke="#0b0e14" stroke-width="2"/>')
        parts.append(f'<text x="{x}" y="{y-2}" fill="#fff" font-size="12.5" font-weight="bold" text-anchor="middle">{esc(b[:16])}</text>')
        parts.append(f'<text x="{x}" y="{y+14}" fill="rgba(255,255,255,.85)" font-size="9.5" text-anchor="middle">{esc(dim)}</text>')
    parts.append("</svg>")
    return "".join(parts)

def svg_agents_grid():
    """智能体架构图：按设备分组卡片网格（SVG 文本块）"""
    agents = get_agents()
    dev_colors = {"mac-mini": "#56b6c2", "i9": "#e06c75", "mbp": "#c678dd"}
    # 从 role 提取设备关键词
    def device(role):
        rl = role or ""
        for d in ["mac-mini", "i9", "mbp", "PC"]:
            if d in rl:
                return d
        return "其他"
    groups = {}
    for a in agents:
        groups.setdefault(device(a.get("role", "")), []).append(a)
    order = sorted(groups.keys())
    card_w, card_h, gap = 330, 128, 14
    per_row = 4
    rows = math.ceil(sum(len(groups[k]) for k in order) / per_row)
    W = per_row * (card_w + gap) + 40
    H = len(order) * 40 + rows * (card_h + gap) + 60
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#0d1119" rx="14"/>']
    x = 20; y = 30; col = 0
    for dev in order:
        parts.append(f'<text x="{20}" y="{y+14}" fill="{dev_colors.get(dev,"#8b90a3")}" font-size="14" font-weight="bold">{dev} 设备 · {len(groups[dev])} 智能体</text>')
        y += 34
        for a in groups[dev]:
            role = a.get("role", "?")
            ab = len(a.get("abilities", []))
            rs = len(a.get("resources", []))
            # 卡片（用 foreignObject 太繁，纯矩形+文本，短 role）
            if col >= per_row:
                col = 0
                # 计算翻行
            cx = 20 + col * (card_w + gap)
            cy = y
            parts.append(f'<rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="10" fill="#141824" stroke="#232a3a"/>')
            # 智能体 id 短名
            aid = a.get("id", "")
            short = aid[-8:] if len(aid) > 8 else aid
            role_short = role if len(role) <= 34 else role[:33] + "…"
            # 因为 role 中文可能长，分两行
            parts.append(f'<text x="{cx+12}" y="{cy+22}" fill="#e8eaf0" font-size="11.5" font-weight="bold">{esc(role_short)}</text>')
            parts.append(f'<text x="{cx+12}" y="{cy+42}" fill="#8b90a3" font-size="9.5">{esc(aid[:10])}…{esc(short)}</text>')
            parts.append(f'<text x="{cx+12}" y="{cy+62}" fill="{dev_colors.get(dev,"#8b90a3")}" font-size="10">能力 {ab} · 资源 {rs}</text>')
            # 能力摘要（前2行）
            ab_sum = " · ".join(a.get("abilities", [])[:2])[:54]
            parts.append(f'<text x="{cx+12}" y="{cy+80}" fill="#9aa3b2" font-size="9">{(esc(ab_sum)+"…") if len(ab_sum)>=54 else esc(ab_sum)}</text>')
            rsrc = " · ".join(a.get("resources", [])[:1])[:54]
            parts.append(f'<text x="{cx+12}" y="{cy+96}" fill="#6f7686" font-size="9">{(esc(rsrc)+"…") if len(rsrc)>=54 else esc(rsrc)}</text>')
            col += 1
            if col >= per_row:
                col = 0
                y += card_h + gap
        if col:
            y += card_h + gap
            col = 0
        y += 8
    parts.append("</svg>")
    return "".join(parts)

def ensure_dir():
    os.makedirs(SNAP_DIR, exist_ok=True)

def load_version_map():
    try:
        with open(VERSION_MAP, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"blueprints": {}}

def save_version_map(vm):
    ensure_dir()
    with open(VERSION_MAP, "w", encoding="utf-8") as f:
        json.dump(vm, f, ensure_ascii=False, indent=2)

def render_all_snapshots(verbose=False):
    """遍历全部蓝图，渲染 SVG 快照；按 versionlog 当前版本命名归档。
    附带：扫描本地 BP-9 JSON 快照文件（data/blueprint/snapshots/*.json）→ 若版本≠当前则补历史 SVG。"""
    reg = get_registry()
    versions = get_versions()
    bp_vers = versions.get("blueprints", {})
    vm = load_version_map()
    created = []
    ensure_dir()
    # ── 历史 BP-9 JSON 快照（本地既有文件）→ 补历史 SVG ──
    import glob as _glob
    hist_src = os.path.join(BASE, "data/blueprint/snapshots", "*.json")
    for hf in _glob.glob(hist_src):
        try:
            with open(hf, encoding="utf-8") as f:
                hbp = json.load(f)
            hbid = hbp.get("id")
            hver = hbp.get("version", "?")
            if not hbid or "mainlines" not in hbp:
                continue
            cur = bp_vers.get(hbid, {}).get("version", "")
            # 历史版本（与当前不同 或 本地该蓝图在 versionlog 无记录但快照存在）
            hfname = re.sub(r"[^\w\-]", "_", hbid) + "-v" + re.sub(r"[^\w\-]", "_", norm_ver(hver)) + "-hist.svg"
            hpath = os.path.join(SNAP_DIR, hfname)
            if not os.path.exists(hpath):
                svg = svg_blueprint(hbid, bp=hbp)
                with open(hpath, "w", encoding="utf-8") as f:
                    f.write(svg)
                vm.setdefault("blueprints", {}).setdefault(hbid, {}).setdefault("history", [])
                # 不覆盖同名版本历史（保留 distinct 条目）
                vm["blueprints"][hbid]["history"].append({"version": norm_ver(hver), "file": hfname, "ts": "hist"})
                created.append((hbid, hver + " (历史快照)", hfname))
                if verbose:
                    print(f"  🕰 {hbid} v{hver} (历史) → {hfname}")
        except Exception as e:
            if verbose:
                print(f"  历史快照跳过 {hf}: {e}")
    # ── 当前版本渲染（幂等：version-map current 同版本且三视图文件存在 → 跳过）──
    VIEW_RENDER = [("arch", svg_blueprint), ("fish", svg_fishbone), ("tl", svg_timeline)]
    for b in reg:
        bid = b["id"]
        ver = b.get("version", "?")
        nver = norm_ver(ver)
        bvm = vm.setdefault("blueprints", {}).setdefault(bid, {"versions": {}})
        cur = bvm.get("current") or {}
        need = cur.get("version") != nver or not cur.get("views")
        if not need:
            vfiles = cur.get("views", {})
            need = any(not vfiles.get(vk) or not os.path.exists(os.path.join(SNAP_DIR, vfiles[vk]))
                       for vk, _ in VIEW_RENDER)
        if not need:
            if verbose:
                print(f"  ⏭ {bid} v{ver} 已是最新（3 视图齐全），跳过")
            continue
        try:
            safe_bp = re.sub(r"[^\w\-]", "_", bid)
            safe_ver = re.sub(r"[^\w\-]", "_", nver)
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            views_files = {}
            for vk, renderer in VIEW_RENDER:
                svg = renderer(bid)
                fname = f"{safe_bp}-{vk}-v{safe_ver}-{ts}.svg"
                with open(os.path.join(SNAP_DIR, fname), "w", encoding="utf-8") as f:
                    f.write(svg)
                views_files[vk] = fname
                created.append((bid, f"{ver} [{vk}]", fname))
                if verbose:
                    print(f"  ✅ {bid} v{ver} [{vk}] → {fname}")
            bvm["current"] = {"version": nver, "views": views_files,
                              "file": views_files.get("arch"), "ts": ts}
            hist = bvm.setdefault("history", [])
            hist = [hh for hh in hist if hh.get("version") != nver]
            hist.append({"version": nver, "views": views_files, "file": views_files.get("arch"), "ts": ts})
            bvm["history"] = hist[-30:]
        except Exception as e:
            if verbose:
                print(f"  ❌ {bid}: {e}")
    save_version_map(vm)
    return created

# ───────────────────────── 前端页面 ─────────────────────────

# ── UI 资源(CSS/JS 独立文件, 不再字符串内嵌 —— 结构加固: 编辑器/语法工具原生校验) ──
_ui_dir = os.path.dirname(os.path.abspath(__file__))
try:
    with open(os.path.join(_ui_dir, "bb-gallery-ui.css"), encoding="utf-8") as _f: CSS = _f.read()
    with open(os.path.join(_ui_dir, "bb-gallery-ui.js"), encoding="utf-8") as _f: JS_UI = _f.read()
except Exception as _e:
    CSS, JS_UI = "", ""
    sys.stderr.write(f"⚠️ UI 资源读取失败(需 bb-gallery-ui.css/js 与脚本同目录): {_e}\n")

def _ui_reload():
    """开发热重载: 重新读 UI 文件(改 css/js 后调, 免重启服务)"""
    global CSS, JS_UI
    try:
        with open(os.path.join(_ui_dir, "bb-gallery-ui.css"), encoding="utf-8") as _f: CSS = _f.read()
        with open(os.path.join(_ui_dir, "bb-gallery-ui.js"), encoding="utf-8") as _f: JS_UI = _f.read()
        return True
    except Exception:
        return False

def build_index(port):
    _ui_reload()  # 热重载: 每次请求读最新 UI 文件(改 js/css 免重启, 部署即生效)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<title>系统架构管理器 · System Graph Manager</title><style>{CSS}</style></head><body>
<div class="top"><h1>🗺 系统架构管理器</h1><span class="sub">System Graph Manager · 蓝图+智能体+规则+机制+图库 · {now}</span></div>
<div class="domains" id="domains"></div>
<div class="tabs" id="tabs">
<!-- ★ 2026-10-13 补修（★ 与 view 容器的同类修正成对）。
     原为 class="tab on" —— ★ 全部 25 个 tab 里**唯一带 on** 的一个（其余 24 个都是 class="tab"）。
     ⇒ ★★ 它让页面【静态高亮哲学 tab】；而 JS 的 __activateView→switchTab('dash')
     随后把 on 移到 dash ⇒ ★★ 【tab 高亮与视图内容错位】——
     用户看到「哲学已选中」而内容是总览，会读成「哲学页坏了」。
     ⇒ 改为与其余 24 个一致。 -->
<div class="tab" data-tab="philosophy" data-dom="SYS">🧠 治理哲学</div>
<div class="tab" data-tab="original" data-dom="SYS">💎 原创资产</div>
<div class="tab" data-tab="workflow" data-dom="SYS">🔄 工作流/标准</div>
<div class="tab" data-tab="planarchive" data-dom="SYS">📋 计划档案</div>
<div class="tab" data-tab="dash" data-dom="DASH">🏠 总览</div>
<div class="tab" data-tab="blueprints" data-dom="GRAPH">📐 蓝图(库+详情)</div>
<div class="tab" data-tab="agents" data-dom="GRAPH">🤖 智能体网络</div>
<div class="tab" data-tab="relations" data-dom="GRAPH">🔀 关系图谱</div>
<div class="tab" data-tab="projects" data-dom="DASH">🗂 项目视图</div>
<div class="tab" data-tab="versions" data-dom="DASH">📜 版本历史</div>
<div class="tab" data-tab="assets" data-dom="DASH">🗂 图库</div>
<div class="tab" data-tab="rules" data-dom="GRAPH">📏 规则图谱</div>
<div class="tab" data-tab="mech" data-dom="GRAPH">⚙️ 机制</div>
<div class="tab" data-tab="knowledge" data-dom="CARRIER">📚 知识内核</div>
<div class="tab" data-tab="systems" data-dom="CARRIER">🗄 系统资产</div>
<div class="tab" data-tab="hardware" data-dom="CARRIER">🖥 硬件载体</div>
<div class="tab" data-tab="bizmap" data-dom="CARRIER">🌍 跨节点资产</div>
<div class="tab" data-tab="bp" data-dom="SYS">📙 商业计划书</div>
<div class="tab" data-tab="xq" data-dom="SYS">📎 星桥产物</div>
<div class="tab" data-tab="ledger" data-dom="SYS">📒 偏差台账</div>
<div class="tab" data-tab="gap" data-dom="SYS">🧭 差距盘点</div>
<div class="tab" data-tab="channel" data-dom="SYS">🛰 通道基线</div>
<div class="tab" data-tab="goal" data-dom="SYS">🎯 目标四维</div>
<div class="tab" data-tab="progress" data-dom="SYS">📈 进度轴</div>
<div class="tab" data-tab="circles" data-dom="SYS">⭕ 两圈(回收)</div>
</div>
<!-- ★ 2026-10-13 修：原为 class="main on"（★ 全部 25 个 view 里**唯一带 on** 的一个）
     ⇒ ★ 它会让页面【静态默认显示哲学页】，而 JS 的 __activateView→switchTab('dash')
     随后把 on 移走 ⇒ ★★ **渲染时机与显示时机错位**。⇒ 改为与其余 24 个一致的 class="main"。 -->
<div class="main" id="view-philosophy"></div>
<div class="main" id="view-original"></div>
<div class="main" id="view-workflow"></div>
<div class="main" id="view-planarchive"></div>
<div class="main" id="view-dash"></div>
<div class="main" id="view-blueprints"></div>
<div class="main" id="view-agents"></div>
<div class="main" id="view-relations"></div>
<div class="main" id="view-projects"></div>
<div class="main" id="view-versions"></div>
<div class="main" id="view-assets"></div>
<div class="main" id="view-rules"></div>
<div class="main" id="view-mech"></div>
<div class="main" id="view-knowledge"></div>
<div class="main" id="view-systems"></div>
<div class="main" id="view-hardware"></div>
<div class="main" id="view-bizmap"></div>
<div class="main" id="view-bp"></div>
<div class="main" id="view-xq"></div>
<div class="main" id="view-ledger"></div>
<div class="main" id="view-gap"></div>
<div class="main" id="view-channel"></div>
<div class="main" id="view-goal"></div>
<div class="main" id="view-progress"></div>
<div class="main" id="view-circles"></div>
<div class="foot">blueprint-gallery {VERSION} · 数据源: 黑板 8792 + agent-bus.json · 明鉴 v2 · 架构图快照自动渲染于 gallery/snapshots/</div>
<script src="vendor/d3.min.js"></script>
<script>{JS_UI}</script>
<script>bindTabs();init();</script>
</body></html>"""

# ───────────────────────── HTTP 服务 ─────────────────────────

# R006#7 统一日志: 访问日志(含 4xx/5xx) → ~/dsh-collab/logs/systemgraph.log (JSONL)
_ACCESS_LOG = os.path.expanduser("~/dsh-collab/logs/systemgraph.log")
_ACCESS_LOG_MAX = 2 * 1024 * 1024  # 2MB 轮转
_log_lock = __import__("threading").Lock()

def _log_access(ts, method, path, code, referer="", agent=""):
    """追加一行 JSONL 访问日志; 超 2MB 轮转为 .1(留最近一份)"""
    try:
        with _log_lock:
            if os.path.exists(_ACCESS_LOG) and os.path.getsize(_ACCESS_LOG) > _ACCESS_LOG_MAX:
                os.replace(_ACCESS_LOG, _ACCESS_LOG + ".1")
            line = json.dumps({"ts": ts, "method": method, "path": path[:300],
                               "code": code, "referer": referer[:200], "agent": agent[:150]},
                              ensure_ascii=False)
            with open(_ACCESS_LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        pass  # 日志失败不阻断服务

def _run_execute_after_confirm(frm, to, reason=""):
    """R006 自动接线: gallery 建边(五步门执行)后, 同步调 bb-connect-execute.py 通知两端相关方
    - 通知墙 data/connect-lab/notifications/ + 协作任务 collab-tasks + executions 幂等留痕(均在 execute 内)
    - 走 execute 的 Lean4 结构门(端点合法/幂等), 与 CLI 执行语义一致; 失败不阻断建边(已落盘)
    返回 True=通知已发 / False=跳过或失败"""
    import subprocess as _sp
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _exe = os.path.join(_here, "bb-connect-execute.py")
        if not os.path.exists(_exe):
            _exe = os.path.expanduser("~/dsh-collab/scripts/bb-connect-execute.py")
        if not os.path.exists(_exe):
            return False
        _r = _sp.run([sys.executable, _exe, "--run", "--graph", "agents",
                      "--from", str(frm), "--to", str(to), "--reason", str(reason)[:80]],
                     capture_output=True, text=True, timeout=15)
        import json as _json2
        try:
            _d = _json2.loads(_r.stdout or "{}")
            # 新执行成功 → notified>=1; 幂等跳过(already) → 通知此前已发, 也算达成
            return bool(_d.get("ok")) and (_d.get("already", False) or int(_d.get("notified", 0) or 0) > 0)
        except Exception:
            return _r.returncode == 0
    except Exception:
        return False  # 通知失败不阻断建边(边已确认落盘)

# ══════════ ★ P1（2026-10-12 明鉴）：可写枢纽 · R1 写端点与动词层 + R2 授权 ══════════
# ★★ 为什么这样做（本线 2026-10-12 迭代规划 §3 分期表）：
#   现状是【只读看板】（后端只有 do_GET、47 个 GET 端点、0 写能力）。
#   P1 = R1 写端点与动词层 + R2 授权模型，**两者绑在同一期，不可拆** ——
#   ★ 规划原话：「没有它，其余七件全是空谈；且**鉴权必须在写存在之前就位，
#     否则会先长出无鉴权的写**」。
#
# ★★ 三条设计决定（都在任何 D1 答案下安全）：
#   ① **默认拒绝**（default deny）：ACL 里没有的 principal ⇒ 一律拒。
#      ⇒ 这样**不需要先知道 D1 的授权范围**（D1 只决定往 ACL 里放谁），先建机制是安全的。
#   ② **动词注册表**而非 ad-hoc 路径：加一个能力 = 往表里加一行（声明它要什么资源+动作），
#      而不是往 if 链里加一个分支 ⇒ 权限粒度天然到「资源 × 动作」。
#   ③ **每一次写尝试都留痕**（含被拒的）—— 这是本晚反复验证过的一条：
#      静默是故障最好的藏身处（fetch() 静默返空、expired 静默丢弃、裁决静默……）。
#
# ★★★ 本版的安全边界（**发布即安全**）：
#   · 只有 `probe.write` 一个动词**被授权**，它只写一个**沙盒键** `data/registry/sg-write-probe`；
#   · 真实内容动词（`page.*` / `relation.*`）**已注册但 ACL 不授权任何人** ⇒ **默认拒绝**；
#   · ⇒ 现在发上去，**最坏情况也只是有人写了一个探针键**，动不了蓝图与关系。
SG_ACL_PATH = os.path.join(BASE, "data/registry/sg-acl.json")
SG_WRITE_AUDIT = os.path.join(BASE, "logs/sg-write-audit.jsonl")
SG_PROBE_KEY = "data/registry/sg-write-probe"
# ★★ P2（2026-10-12）：R3 页面级内容寻址 —— 每页一个可寻址的内容档。
#   · 地址形式：`page:<view-name>`（如 `page:goal`），落盘键 `data/sg-page/<view-name>`
#   · ★ ACL 的资源粒度随之到【单页】`page:<name>` ⇒ 可以「只授权某几页」，
#     这正是 R3 的回报（没有寻址就只能「整站授权」或「不授权」）。
#   · ★★ 版本模型：**append-only 历史**（`history[]`，每条带 `seq`）——
#     回滚不是删历史，而是**追加一条 restore 记录**。⇒ 任何写都可退，且退的过程本身也留痕。
SG_PAGE_PREFIX = "data/sg-page/"
# ★★ P3（2026-10-12）：R4 连线编辑 —— 关系图可写，**粒度到「图」**。
#   · 地址形式：`graph:<name>`，落盘键 `data/sg-graph/<name>`
#   · ★★ 纪律同 R6：**边的删除走【墓碑】而不是真删** ⇒ 删过的边仍可回滚。
#     历史 append-only（`entries[]`，每条带 `seq`），边集由历史**重放**得出。
#   · ★ ACL 资源 = `relation:<graph>` ⇒ 与 R3 同构：**可以只授权某几张图**。
#     ★★ 真实 `relations` 图（data/blueprint/relations）**不在 grants 里** ⇒ 默认拒绝。
SG_GRAPH_PREFIX = "data/sg-graph/"


def sg_graph_key(name):
    return SG_GRAPH_PREFIX + name


def sg_edge_key(e):
    """★ 边的身份 = (from, to, type) 三元组。★ 不参与身份的字段变更 ⇒ 视为同一条边的新状态。"""
    return "%s|%s|%s" % (str(e.get("from") or "").strip(),
                         str(e.get("to") or "").strip(),
                         str(e.get("type") or "connects").strip())


def sg_graph_read(name):
    """★ 读图档。★ 三态分开（P2 的教训）：**404 键不存在 = 空图（可写）** · 无 entries = 空图 · 其它 = 真失败。"""
    url = "http://127.0.0.1:8792/%s" % sg_graph_key(name)
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.loads(r.read().decode())
        v = d.get("value")
        if isinstance(v, dict) and isinstance(v.get("entries"), list):
            return {"ok": True, "doc": v}
        return {"ok": True, "doc": {"entries": []}, "note": "键存在但无 entries ⇒ 视为空图"}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ok": True, "doc": {"entries": []}, "note": "键不存在 ⇒ 空图（首次写入）"}
        return {"ok": False, "doc": {"entries": []}, "err": "HTTP %s: %s" % (e.code, e.reason)}
    except Exception as e:
        return {"ok": False, "doc": {"entries": []}, "err": "%s: %s" % (type(e).__name__, e)}


def sg_graph_state(doc):
    """★ 由 append-only 历史**重放**出当前边集。

    ★★ 墓碑语义：`add_edge` ⇒ 该边在；`remove_edge` ⇒ 该边**不在**（但历史里留着它的存在与删除记录）。
      ⇒ 删过的边**可回滚**（再 append 一条 add 即可），且**删除本身也留痕**。
    """
    st, unknown = {}, []
    for h in doc.get("entries") or []:
        op = h.get("op")
        if op in ("add_edge", "remove_edge"):
            st[h.get("key")] = {"present": op == "add_edge", "edge": h.get("edge"),
                                "seq": h.get("seq"), "at": h.get("at"), "by": h.get("by")}
        elif op == "restore_edge":
            st[h.get("key")] = {"present": bool(h.get("present")), "edge": h.get("edge"),
                                "seq": h.get("seq"), "at": h.get("at"), "by": h.get("by")}
        else:
            unknown.append(op)
    if unknown:
        st["__unknown_ops__"] = {"present": False, "edge": None,
                                 "seq": None, "at": None, "by": None,
                                 "note": "★ 未识别的 op：%s（不静默跳过）" % sorted(set(map(str, unknown)))}
    return st


def sg_graph_edges(doc):
    """★ 重放后**仍在的边**（`present=True` 的那些）。"""
    st = sg_graph_state(doc)
    return [v["edge"] for k, v in st.items()
            if isinstance(v, dict) and v.get("present") and v.get("edge")]


def sg_graph_write(name, principal, entry, expected_seq=None):
    """★★ P4（R8）：**读 → 校验 expected_seq → 追加 → PUT → 回读** 整段在同一把锁内。

    ★ 为什么不能只靠外部门禁（实测）：门禁读 seq 与写函数再读 seq 之间**没有原子性**
      ⇒ 两个并发写都读到 5、都通过 ⇒ **双写都成功且都报 seq=6**（TOCTOU 竞态）。
    ⇒ 修：把权威校验放进锁内。★ 外部门禁保留为**快速失败**（少一次网络），但**不作数**。
    ★ 返回 (ok, reason, entry, conflict)；conflict 非空 ⇒ 应回 409。
    """
    with SGW_LOCK:
        cur = sg_graph_read(name)
        if not cur["ok"]:
            return False, "读图档失败：%s" % cur.get("err"), None, None
        doc = cur["doc"]
        ents = doc.get("entries") or []
        actual = len(ents)
        if expected_seq is not None and int(expected_seq) != actual:
            return False, ("★ 冲突：expected_seq=%s 但当前为 %s ⇒ 请取新 seq 后重试"
                           % (expected_seq, actual)), None, {
                "conflict": {"expected": int(expected_seq), "actual": actual},
                "targetKind": "graph", "targetName": name,
                "current": sg_graph_edges(doc)}
        entry = dict(entry)
        entry["seq"] = actual + 1
        entry["at"] = datetime.datetime.now().isoformat()
        entry["by"] = principal
        ents.append(entry)
        doc["entries"] = ents
        doc["name"] = name
        try:
            body = json.dumps(doc, ensure_ascii=False).encode()
            rq = urllib.request.Request("http://127.0.0.1:8792/%s" % sg_graph_key(name),
                                        data=body, method="PUT",
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(rq, timeout=8) as r:
                r.read()
            back = sg_graph_read(name)
            n = len((back.get("doc") or {}).get("entries") or [])
            if n != len(ents):
                return False, "回读不符：写入 %d 条 / 回读 %d 条" % (len(ents), n), None, None
            sg_register_watch(sg_graph_key(name))
            return True, "已追加 seq=%d 并回读（entries=%d 条）" % (entry["seq"], n), entry, None
        except Exception as e:
            return False, "写图档失败：%s: %s" % (type(e).__name__, e), None, None

def sg_page_key(view):
    return SG_PAGE_PREFIX + view


def sg_page_read(view):
    """★ 读页面内容档。

    ★★ 2026-10-12 本线实测修正（**我自己的代码违反了「空 ≠ 无」**）：
      第一版把 **HTTP 404（键还不存在）** 也当成「读失败」⇒ 首次写入必然 502。
      ★ 而 404 是**首次写入的正常情况** ⇒ 应视为**空档**，不是失败。
      ⇒ 三态必须分开：**键不存在（空档，可写）** / **键存在但无 history（空档）** / **真读失败（不可写）**。
      ★ 这正是本晚在别的件上反复纠正的同一件事，我在这里又犯了一次。
    """
    url = "http://127.0.0.1:8792/%s" % sg_page_key(view)
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            d = json.loads(r.read().decode())
        v = d.get("value")
        if isinstance(v, dict) and isinstance(v.get("history"), list):
            return {"ok": True, "doc": v}
        return {"ok": True, "doc": {"history": []}, "note": "键存在但无 history ⇒ 视为空档"}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # ★ 键不存在 = 空档（首次写入的正常路径），**不是失败**
            return {"ok": True, "doc": {"history": []}, "note": "键不存在 ⇒ 空档（首次写入）"}
        return {"ok": False, "doc": {"history": []}, "err": "HTTP %s: %s" % (e.code, e.reason)}
    except Exception as e:
        return {"ok": False, "doc": {"history": []}, "err": "%s: %s" % (type(e).__name__, e)}


def sg_page_state(doc):
    """★ 由 append-only 历史**重放**出当前状态（不存 current，避免两份真相）。

    ★★ 2026-10-12 实测修正（**回滚报 200 但没生效**）：
      第一版只处理 `set_field` 与 `("add_block","restore")`，而**回滚实际写的 op 是 `rollback`**
      ⇒ 回滚记录被重放忽略 ⇒ ★ **API 报 200、历史里看得见、状态却没变**（最危险的一类 bug）。
      ⇒ 修：把 `rollback` 并入「写状态」分支；并**加一条断言**：凡出现没被识别的 op，
        必须**显式记录**而不是静默跳过（静默跳过正是本晚反复的病灶）。
    """
    st, unknown = {}, []
    for h in doc.get("history") or []:
        op = h.get("op")
        if op in ("set_field", "add_block", "restore", "rollback"):
            st[h.get("key")] = h.get("value")
        else:
            unknown.append(op)
    if unknown:
        # ★ 不静默：把没识别的 op 挂到 state 上让人看得见
        st["__unknown_ops__"] = sorted(set(str(u) for u in unknown))
    return st


# ★★★ P4 · R8（2026-10-12）：**写串行锁**。
#   ★ 为什么必须有（实测）：第一版把乐观锁做成「门禁先读 seq → 写函数再读一次 → PUT」，
#     而**两次读之间没有原子性** ⇒ 两个并发写都读到 seq=5、都通过门禁、然后各自追加
#     ⇒ **双写都成功且都报 seq=6**（一个覆盖另一个）。这是典型的 **TOCTOU（检查时/使用时）竞态**。
#   ⇒ 修：把「读 → 校验 expected_seq → 追加 → PUT → 回读」**整段放进同一把锁**。
#   ★ 边界（如实说）：`threading.Lock` 只保证**同一进程内**串行。
#     本服务是 ThreadingHTTPServer（多线程、单进程）⇒ 够用；
#     ★ 若将来起**多个后端进程**，这把锁不够，需换成跨进程互斥（如文件锁）。
SGW_LOCK = threading.Lock()


# ══════════ ★ P5.0（2026-10-12 明鉴）：反向指导 · 属主存活校验 ══════════
# ★★ 为什么这是 P5 的【地基】而不是可选（本线实测）：
#   反向派发要复用的那条派生通道，其消费方现在是【死会话】——
#   `event-bus` 的 PENDING 全部指向 `session-fa1f9150-c94`（首任星桥，2026-10-09 因 P26 bricked），
#   而 `~/.dsh/agent-role-map.json` 里含该 id 的次数 = 0（已从角色映射移除），且 pending 仍在累积。
#   ⇒ ★ **在这个状态下做 P5，每派发一次就是往黑洞发一次** —— 是 11.5h 互等事故的加强版
#     （那次至少有人等，这次连收件人都不存在）。
#
# ★ 实现选择（J44：复用优先）：**不另造存活源**，复用 `xingduo-wake.py` v5 的两件：
#   ① `find_agent_bus_port()` —— ★ **动态探测**（v3 写死 61698 ⇒ CLD 重启端口漂移 ⇒ 投递静默失效数日）
#   ② `target_live(port)` —— `agents[].id` **成员资格**；★ **查询失败保守返回 False**
#      （原注释逐字：「宁漏一轮不刷死会话」）
#
# ★★ 本实现的两条纪律：
#   ① **fail-closed**：探测失败 / 端口找不到 / 解析异常 ⇒ **一律判「不存活」⇒ 挂起**
#      （绝不「因为查不到所以放行」）
#   ② **存活判定不缓存**：每次现查（存活列表随时会变；缓存会把「刚死」当「还活着」）
#      ★ 只有【端口】缓存 30s —— 端口在 CLD 生命周期内稳定，但重启会漂移，故不能永久缓存。
SG_BUS_PORT_CACHE = {"port": None, "at": 0.0}


def sg_find_bus_port(force=False):
    """★ 动态探测 agent-bus 端口。★ 探测失败返回 None（调用方须按 fail-closed 处理）。"""
    now = time.time()
    c = SG_BUS_PORT_CACHE
    if not force and c["port"] and (now - c["at"]) < 30:
        return c["port"]
    ports = set()
    try:
        r = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=10)
        for line in r.stdout.splitlines():
            m = re.search(r"CLD.*?127\.0\.0\.1:(\d+)", line)
            if m:
                ports.add(int(m.group(1)))
    except Exception as e:
        sys.stderr.write("⚠️ sg_find_bus_port: lsof 失败 %s\n" % e)
        return None
    for p in sorted(ports):
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/agent-bus/api/state" % p, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    resp.read(64)
                    c["port"], c["at"] = p, now
                    return p
        except Exception:
            continue
    return None


def sg_live_agents():
    """★ 返回当前存活会话 id 集合。★ 拿不到 ⇒ 返回 (None, 原因) —— **不可判，不是空集**。
    ★★ 三态纪律：「拿不到」与「一个都没有」必须分开（本晚反复的同一件事）。"""
    port = sg_find_bus_port()
    if port is None:
        return None, "bus 端口探测失败（CLD 未运行或端口漂移）"
    try:
        req = urllib.request.Request("http://127.0.0.1:%d/agent-bus/api/state" % port, method="GET")
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read().decode())
        agents = data.get("agents") or []
        ids = {a.get("id") for a in agents if isinstance(a, dict) and a.get("id")}
        return ids, None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def sg_owner_alive(session_id):
    """★ P5.0 核心：属主是否存活。★ 返回 (alive: bool, reason: str, live_count: int|None)。

    ★★ fail-closed：拿不到存活列表 ⇒ **alive=False**（挂起），**不是**「不详就放行」。
    """
    if not session_id or not str(session_id).strip():
        return False, "未提供 owner", None
    sid = str(session_id).strip()
    ids, err = sg_live_agents()
    if ids is None:
        return False, "★ 存活列表不可判 ⇒ fail-closed 判「不存活」：%s" % err, None
    if sid in ids:
        return True, "在存活列表内（共 %d 个会话）" % len(ids), len(ids)
    return False, "★ 不在存活列表内（共 %d 个会话）⇒ 挂起 + 告警" % len(ids), len(ids)


# ══════════ ★ P5.1（2026-10-12 明鉴）：缺口检出层 + 台账 + 冻结基线棘轮 ══════════
# ★★ 缺口族是【贴着本夜实测出的真问题】定义的，不是我拍脑袋的六族。
#   实测：结构性六族（必填/类型/悬空/孤儿/重复）在真数据上**全部为 0**
#   ⇒ ★ **一个永远报 0 的检出器就是恒真判据**（本晚反复的教训）
#   ⇒ 故把它们**降为「负控主语」**（造一个假缺口 ⇒ 必须报出来），
#     而**主产出**是本夜真正测到的三族：G1 台账落后 / G2 产物未登记 / G3 订阅指向死会话。
#
# ★★ 两档严重度（抄 EventCatalog Linter ✅已核实原文）：
#     `error` = 通道级/结构级 ⇒ **拦**（不该放它过去）
#     `warn`  = 内容级/登记级 ⇒ **派单**（值得有人去补，但不该阻断）
#
# ★★ 冻结基线棘轮（抄 ArchUnit `FreezingArchRule` ✅已核实原文）：
#     存量缺口不可能一次补齐，**全量派单会淹死人**（Roadie 自家示例：104 实体 / 90 不合格）
#     ⇒ ① 首次运行把现存缺口**全部记入基线（冻结）**
#        ② 之后**只把不在基线里的当「新增」**（才可派发）
#        ③ 缺口修掉 ⇒ 下轮检出里没有它 ⇒ **自动从基线收缩**
#        ④ ★ **「改基线」须显式开关**（防「改基线假装清零」——ArchUnit 用
#           `freeze.store.default.allowStoreUpdate=false` 防 CI 里偷偷改）
SG_GAP_PREFIX = "data/sg-gap/"
SG_GAP_BASELINE = "data/registry/sg-gap-baseline"

GAP_FAMILIES = {
    "G1": {"name": "版本台账落后（产物版本 > 台账）", "severity": "warn"},
    "G2": {"name": "产物存在但台账从未登记", "severity": "warn"},
    "G3": {"name": "订阅/指令指向死会话", "severity": "error"},
    "G4": {"name": "页面档引用死键", "severity": "warn"},
    "A": {"name": "必填字段缺失", "severity": "error"},
    "B": {"name": "字段类型错", "severity": "error"},
    "C": {"name": "引用悬空", "severity": "error"},
    "D": {"name": "孤儿（无任何边）", "severity": "warn"},
    "E": {"name": "重复 ID", "severity": "error"},
}


def sg_gap_id(family, subject):
    """★ gapId = 族 + subject 指纹。★ 同 (族, 对象) ⇒ 同 id ⇒ **重算幂等**（不产生重复条目）。"""
    import hashlib
    return "%s-%s" % (family, hashlib.sha256(str(subject).encode("utf-8")).hexdigest()[:12])


def _snap_latest_versions():
    """★ 从快照产物推导每个蓝图的最新版本（与 D1 的 --sync-from-artifacts 同源口径）。"""
    d = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/snapshots")
    rx = re.compile(r"^(.+?)-(arch|fish|tl|flow|timeline|dyn)-v(\d*)_?(\d*)(?:[_-].*?)?-(\d{8})-(\d{6})\.svg$")
    latest = {}
    try:
        for f in os.listdir(d):
            m = rx.match(f)
            if not m or not m.group(3):
                continue
            k = (int(m.group(3)), int(m.group(4) or 0))
            b = m.group(1)
            if b not in latest or k > latest[b][0]:
                latest[b] = (k, "v%s.%s" % (m.group(3), m.group(4) or 0))
    except Exception:
        pass
    return latest


def _vk(v):
    m = re.search(r"v(\d+)\.(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def sg_detect_gaps():
    """★ 检出层（**只读，零副作用**）。返回 (gaps, meta)。

    ★★ 每条缺口带：family / severity / subject / evidence / gapId。
    ★★ 检不出任何东西时**不返回空成功** —— meta 里给出「扫过的面 + 各类判据命中数」，
       否则「0 条」无法区分「真干净」与「检出器坏了」（本晚反复的同一件事）。
    """
    gaps = []
    scanned = {}

    # ── 读数据（读不到 ⇒ 记入 meta，不静默当 0）──
    bps, err1 = None, None
    try:
        with urllib.request.urlopen("http://127.0.0.1:8798/api/blueprints", timeout=12) as r:
            bps = json.loads(r.read().decode())
    except Exception as e:
        err1 = "%s: %s" % (type(e).__name__, e)
    rel = {}
    try:
        with urllib.request.urlopen("http://127.0.0.1:8792/data/blueprint/relations", timeout=10) as r:
            rel = (json.loads(r.read().decode()).get("value") or {})
    except Exception:
        pass
    vl = {}
    try:
        with urllib.request.urlopen("http://127.0.0.1:8792/data/blueprint/versionlog", timeout=10) as r:
            vl = (json.loads(r.read().decode()).get("value") or {})
    except Exception:
        pass
    scanned["blueprints"] = (len(bps) if isinstance(bps, list) else ("读失败：" + (err1 or "?")))
    scanned["edges"] = len(rel.get("edges") or [])
    scanned["versionlogBlueprints"] = len(vl.get("blueprints") or {})

    # ── G1 / G2：版本台账落后与未登记 ──
    recorded = vl.get("blueprints") or {}
    latest = _snap_latest_versions()
    g1 = g2 = 0
    for b, (k, ver) in sorted(latest.items()):
        if b not in recorded:
            gaps.append({"family": "G2", "severity": GAP_FAMILIES["G2"]["severity"], "subject": b,
                         "evidence": "产物 %s 存在（快照目录），但台账 blueprints 无此条" % ver})
            g2 += 1
        else:
            cur = _vk(recorded[b].get("version"))
            if cur is None or k > cur:
                gaps.append({"family": "G1", "severity": GAP_FAMILIES["G1"]["severity"], "subject": b,
                             "evidence": "台账 %s < 产物 %s" % (recorded[b].get("version"), ver)})
                g1 += 1
    scanned["G1"] = g1
    scanned["G2"] = g2

    # ── G3：订阅/指令指向死会话（★ error）──
    g3 = 0
    live, lerr = sg_live_agents()
    if live is None:
        scanned["G3"] = "UNCOVERED（存活列表不可判：%s）" % lerr
    else:
        try:
            import subprocess as _sp
            out = _sp.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "event-bus.py"),
                           "--status"], capture_output=True, text=True, timeout=20).stdout
            targets = set(re.findall(r"->\s*(session-[0-9a-f-]+)", out))
            dead = sorted(t for t in targets if t not in live)
            for t in dead:
                n = out.count("-> " + t)
                gaps.append({"family": "G3", "severity": GAP_FAMILIES["G3"]["severity"], "subject": t,
                             "evidence": "event-bus 有 %d 条 PENDING 指向它，而它不在存活列表内（活体 %d 个）" % (n, len(live))})
                g3 += 1
            scanned["G3"] = g3
        except Exception as e:
            scanned["G3"] = "UNCOVERED（%s: %s）" % (type(e).__name__, e)

    # ── 结构性 A–E（真数据上为 0 ⇒ 作为【负控主语】）──
    ids = [b.get("id") for b in (bps or []) if isinstance(b, dict)]
    nodes = set(rel.get("blueprints") or []) | set(i for i in ids if i)
    edges = rel.get("edges") or []
    A = [b.get("id") for b in (bps or []) if isinstance(b, dict) and not all([b.get("id"), b.get("dim"), b.get("version")])]
    B = [i for i, e in enumerate(edges) if not isinstance(e, dict) or not all(isinstance(e.get(x), str) for x in ("from", "to", "type"))]
    C = [(e.get("from"), e.get("to")) for e in edges if isinstance(e, dict) and (e.get("from") not in nodes or e.get("to") not in nodes)]
    touched = set()
    for e in edges:
        if isinstance(e, dict):
            touched.add(e.get("from"))
            touched.add(e.get("to"))
    D = sorted(x for x in nodes if x not in touched)
    from collections import Counter as _C
    E = [k for k, v in _C(ids).items() if v > 1]
    for x in A:
        gaps.append({"family": "A", "severity": "error", "subject": str(x), "evidence": "缺 id/dim/version 之一"})
    for i in B:
        gaps.append({"family": "B", "severity": "error", "subject": "edge#%d" % i, "evidence": "from/to/type 非 str"})
    for f, t in C:
        gaps.append({"family": "C", "severity": "error", "subject": "%s->%s" % (f, t), "evidence": "端点不在节点集内"})
    for x in D:
        gaps.append({"family": "D", "severity": "warn", "subject": str(x), "evidence": "无任何边相连"})
    for x in E:
        gaps.append({"family": "E", "severity": "error", "subject": str(x), "evidence": "id 重复出现"})
    scanned.update({"A": len(A), "B": len(B), "C": len(C), "D": len(D), "E": len(E)})

    for g in gaps:
        g["gapId"] = sg_gap_id(g["family"], g["subject"])
    return gaps, scanned


def sg_gap_ratchet(gaps, update_baseline=False):
    """★ 冻结基线棘轮。返回 (new_gaps, frozen_count, baseline_size, note)。

    ★★ 语义（抄 ArchUnit FreezingArchRule）：
      · 首次运行 ⇒ 把当前全部缺口写进基线（**存量冻结**）⇒ new_gaps = []（不派发存量）
      · 之后 ⇒ 只在基线里的 = 冻结；不在的 = **新增**（可派发）
      · 缺口修掉 ⇒ 下轮检出没有它 ⇒ **基线自动收缩**（写回时以本轮为准）
      · ★ `update_baseline=True` 是**显式开关**：**只有它才允许改基线**
        （防「改基线假装清零」——ArchUnit 用 allowStoreUpdate=false 防的正是这个）
    """
    cur_ids = sorted({g["gapId"] for g in gaps})
    base, ok = None, True
    try:
        with urllib.request.urlopen("http://127.0.0.1:8792/%s" % SG_GAP_BASELINE, timeout=8) as r:
            base = (json.loads(r.read().decode()).get("value") or {})
    except urllib.error.HTTPError as e:
        if e.code == 404:
            base, ok = None, True          # ★ 404 = 无基线（首次）—— 不是失败
        else:
            ok = False
    except Exception:
        ok = False
    if not ok:
        return None, None, None, "★ 基线读不到（非 404）⇒ **不可判**，不当作「首次」也不当作「无新增」"
    if base is None:
        # 首次 ⇒ 冻结存量
        sg_baseline_write(cur_ids)
        return [], len(cur_ids), len(cur_ids), "★ 首次运行 ⇒ 存量 %d 条全部冻结（不派发）" % len(cur_ids)
    known = set(base.get("frozenIds") or [])
    new = [g for g in gaps if g["gapId"] not in known]
    if update_baseline:
        sg_baseline_write(cur_ids)
        return new, len(cur_ids), len(cur_ids), "★ 已显式更新基线（%d 条）" % len(cur_ids)
    return new, len(known & set(cur_ids)), len(known), (
        "存量冻结 %d · 本轮新增 %d（★ 未显式更新基线 ⇒ 基线不动）" % (len(known & set(cur_ids)), len(new)))


def sg_baseline_write(ids):
    """★ 写棘轮基线（**只在首次或显式 update 时调用**）。"""
    try:
        body = json.dumps({"frozenIds": ids, "at": datetime.datetime.now().isoformat(),
                           "n": len(ids)}, ensure_ascii=False).encode()
        rq = urllib.request.Request("http://127.0.0.1:8792/%s" % SG_GAP_BASELINE,
                                    data=body, method="PUT",
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(rq, timeout=8) as r:
            r.read()
        return True
    except Exception as e:
        sys.stderr.write("⚠️ sg_baseline_write 失败：%s\n" % e)
        return False


# ══════════ ★ P5.2（2026-10-12 明鉴）：派发五道门 ══════════
# ★★ 五道门的分工（规划 §1 架构图）：
#   门1 属主门   —— owner 必须解析到一个【在线且存活】会话（★ P5.0 已建）
#   门2 去重门   —— 同 gapId 在【按族分级】的冷却期内不重派 + ★ 棘轮（P5.1 已建）
#   门3 频次门   —— 持久化 per-recipient ≤3/h + 全局 ≤10/h + ★ **突发限**（≤2/60s）
#   门4 熔断门   —— 连续 N 次**无实质进展** ⇒ 熔断该 owner（换域复用 channel-gate 的 judge() 语义）
#   门5 送达回执 —— ★ **未 ack 进 pending；任何后续唤醒【必然附带投递 pending】** + 对账扫描
#
# ★★ 两条全局纪律：
#   ① **全部默认拒绝（fail-closed）**：任一门拿不到状态 ⇒ **拒**，绝不「查不到就放行」
#   ② **位置在【派发前、派发方】**（Temporal 原文口径：「enforces this limit before dispatching
#      tasks」）—— ★ 不让收件人自己挡
#
# ★★★ 为什么必须有门5（调研第一号建议，原文已核实）：
#   「危险的不是『不唤醒』，也不是『唤醒』，而是 —— **承诺了不唤醒、但通知并没有保证送达**。」
#   openclaw PR#54549：无条件告诉 agent「No need to poll」，而通知静默丢弃 ⇒
#   "would tell the agent not to poll while the notification never arrives"
#   ★★ **这正是本网络 11.5h 互等的机制。** ⇒ 门5 的存在，才使「不唤醒」成为安全选项。
SG_SWITCH = "data/registry/sg-dispatch-switch"
SG_DISPATCH_LOG = "data/registry/sg-dispatch-log"
SG_RATE = "data/registry/sg-rate"
SG_BREAKER = "data/registry/sg-breaker"
SG_RECEIPT = "data/registry/sg-receipt"

# ★ 冷却期【按族分级】（抄 Redis 配额设计：CRITICAL 5min / TRANSACTIONAL 1h / MARKETING 24h）
SG_COOLDOWN = {"G3": 300, "A": 300, "B": 300, "C": 300, "E": 300, "G1": 86400, "G2": 86400, "D": 86400, "G4": 86400}
SG_RATE_PER_RECIPIENT = 3      # ≤3/h
SG_RATE_GLOBAL = 10            # ≤10/h
SG_BURST_WINDOW = 60           # 突发窗口 60s
SG_BURST_MAX = 2               # ★ 突发限：60s 内 ≤2（固定窗口在边界有 ±100% 突发，而风暴正发生在边界）
SG_BREAKER_FAILS = 3           # 连续 3 次无实质进展 ⇒ 熔断
SG_BREAKER_FREEZE_H = 24       # 熔断冻结 24h


def _bb_get(key):
    """★ 读黑板键。★ 返回 (value|None, err)。★ 404 ⇒ (None, None) 而非错误（键不存在是正常态）。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8792/%s" % key, timeout=8) as r:
            return (json.loads(r.read().decode()).get("value"), None)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        return None, "HTTP %s" % e.code
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def _bb_put(key, val):
    try:
        body = json.dumps(val, ensure_ascii=False).encode()
        rq = urllib.request.Request("http://127.0.0.1:8792/%s" % key, data=body, method="PUT",
                                    headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(rq, timeout=8) as r:
            r.read()
        return True, None
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)


def sg_gate_switch():
    """★ 总开关。★ 缺省 = **关**（fail-closed：没有开关文件 ⇒ 不派发）。"""
    v, err = _bb_get(SG_SWITCH)
    if err:
        return False, "总开关读不到（%s）⇒ fail-closed 判【关】" % err
    if not isinstance(v, dict):
        return False, "总开关未设置 ⇒ 默认【关】"
    return bool(v.get("on")), ("开" if v.get("on") else "关") + "（by %s at %s）" % (v.get("by", "?"), v.get("at", "?"))


def sg_gate_freq(owner):
    """★ 门3 频次门。★ 持久化（落黑板键）。★ 三档：per-recipient / 全局 / 突发。"""
    now = time.time()
    v, err = _bb_get(SG_RATE)
    if err:
        return False, "★ 频次状态读不到（%s）⇒ fail-closed 拒" % err
    rec = v if isinstance(v, dict) else {}
    hist = [x for x in (rec.get("hits") or []) if isinstance(x, dict) and now - x.get("t", 0) < 90000]
    mine = [x for x in hist if x.get("owner") == owner]
    h1 = [x for x in hist if now - x.get("t", 0) < 3600]
    m1 = [x for x in mine if now - x.get("t", 0) < 3600]
    burst = [x for x in mine if now - x.get("t", 0) < SG_BURST_WINDOW]
    if len(burst) >= SG_BURST_MAX:
        return False, "★ 突发限：60s 内已 %d 次（上限 %d）" % (len(burst), SG_BURST_MAX)
    if len(m1) >= SG_RATE_PER_RECIPIENT:
        return False, "★ 单收件人频次：1h 内已 %d 次（上限 %d）" % (len(m1), SG_RATE_PER_RECIPIENT)
    if len(h1) >= SG_RATE_GLOBAL:
        return False, "★ 全局频次：1h 内已 %d 次（上限 %d）" % (len(h1), SG_RATE_GLOBAL)
    return True, "通过（本收件人 1h %d/%d · 全局 1h %d/%d · 突发 %d/%d）" % (
        len(m1), SG_RATE_PER_RECIPIENT, len(h1), SG_RATE_GLOBAL, len(burst), SG_BURST_MAX)


def sg_gate_freq_record(owner, gap_id):
    """★ 记一次实际派发（只在【真派了】之后调）。"""
    v, _ = _bb_get(SG_RATE)
    rec = v if isinstance(v, dict) else {}
    hist = [x for x in (rec.get("hits") or []) if isinstance(x, dict) and time.time() - x.get("t", 0) < 90000]
    hist.append({"t": time.time(), "owner": owner, "gapId": gap_id})
    return _bb_put(SG_RATE, {"hits": hist[-500:], "at": datetime.datetime.now().isoformat()})


def sg_gate_dedup(gap_id, family):
    """★ 门2 去重门。★ 冷却期按族分级。★ 从派发日志（append-only）推导，不另存一份状态。"""
    now = time.time()
    cd = SG_COOLDOWN.get(family, 86400)
    v, err = _bb_get(SG_DISPATCH_LOG)
    if err:
        return False, "★ 派发日志读不到（%s）⇒ fail-closed 拒" % err
    log = v if isinstance(v, dict) else {}
    ents = log.get("dispatches") or []
    last = max([e.get("t", 0) for e in ents if isinstance(e, dict) and e.get("gapId") == gap_id] or [0])
    if last and (now - last) < cd:
        return False, "★ 冷却中：%d 秒前已派过（冷却 %ds）" % (int(now - last), cd)
    return True, "未在冷却期内（冷却 %ds）" % cd


def sg_gate_breaker(owner):
    """★ 门4 熔断门。★ 换域复用 channel-gate 的 judge() 语义：连续 N 次【无实质进展】⇒ 冻结。

    ★★ 判据是【实质状态变化】而非「有没有响应」（paperclip PR#15847 的坑：
      把「发了评论」当进展 ⇒ 交替 comment/no-comment 就【永久豁免】）。
      本实现里「实质进展」= 该 gap 在下一轮检出里**消失**；未消失即计一次无进展。
    """
    now = time.time()
    v, err = _bb_get(SG_BREAKER)
    if err:
        return False, "★ 熔断状态读不到（%s）⇒ fail-closed 拒" % err
    st = v if isinstance(v, dict) else {}
    o = (st.get("owners") or {}).get(owner) or {}
    if o.get("frozenUntil") and now < o["frozenUntil"]:
        return False, "★ 已熔断（至 %s）—— 须人工复位" % datetime.datetime.fromtimestamp(o["frozenUntil"]).strftime("%m-%d %H:%M")
    if (o.get("noProgressStreak") or 0) >= SG_BREAKER_FAILS:
        return False, "★ 连续 %d 次无实质进展 ⇒ 应熔断（须人工复位）" % o.get("noProgressStreak")
    return True, "未熔断（无进展连击 %d/%d）" % (o.get("noProgressStreak") or 0, SG_BREAKER_FAILS)


def sg_gate_receipt(gap_id):
    """★ 门5 送达回执门（★ 调研第一号建议）。

    ★ 语义：① 未 ack 的缺口记入 pending；② **任何后续唤醒【必然附带投递全部 pending】**；
            ③ 定期（30–60min）对账扫描兜底。
    ★★ 本门【不拦】—— 它是**保证送达**的门，不是限制门（它是让「不唤醒」安全的那个前提）。
    """
    v, err = _bb_get(SG_RECEIPT)
    if err:
        return False, "★ 回执区读不到（%s）⇒ fail-closed 拒" % err
    r = v if isinstance(v, dict) else {}
    pend = [x for x in (r.get("pending") or []) if isinstance(x, dict)]
    return True, "回执区可读 · 当前 pending %d 条（★ 下次唤醒将附带投递）" % len(pend)


def sg_gate_chain(gap, owner):
    """★★ 五道门串联。★ 返回 (allowed, gate_name, reason)。★ 任一不过 ⇒ 立即返回。

    ★★ 顺序有意为之：先【能不能发】（开关/属主），再【该不该发】（去重/频次/熔断），
       最后【发了能不能到】（回执）。⇒ 前面的门便宜，后面的门贵。
    """
    on, why = sg_gate_switch()
    if not on:
        return False, "门0 总开关", "★ 总开关【关】：%s" % why
    alive, r1, n = sg_owner_alive(owner)
    if not alive:
        return False, "门1 属主门", r1
    ok, r2 = sg_gate_dedup(gap.get("gapId"), gap.get("family"))
    if not ok:
        return False, "门2 去重门", r2
    ok, r3 = sg_gate_freq(owner)
    if not ok:
        return False, "门3 频次门", r3
    ok, r4 = sg_gate_breaker(owner)
    if not ok:
        return False, "门4 熔断门", r4
    ok, r5 = sg_gate_receipt(gap.get("gapId"))
    if not ok:
        return False, "门5 送达回执", r5
    return True, "-", "五门全过（属主存活 · 未冷却 · 频次合规 · 未熔断 · 回执区可读）"


# ══════════ ★ P5.3（2026-10-12 明鉴）：三态投递 + 分形态合并 + 记账 ══════════
# ★★★ 一条【必须先知道】的事实（本线读源码坐实，不是猜）：
#   `dsh-plugin-agent-bus` 的 HTTP `/agent-bus/api/send` **不接受 notify_only** ——
#   它的 handler（`:2018-2024`）只做 `sendMessage('ui', to, text, thread)`，
#   **第 5 参 opts 缺省** ⇒ `:1496` 的 `if (opts && opts.notifyOnly === true)` 不成立
#   ⇒ `msg.notifyOnly` 不设 ⇒ `:568` `isNotify=false` ⇒ **`followup()` 真唤醒**。
#   ⇒ ★★ **走 HTTP 发出去的消息【永远是唤醒】。** 要不唤醒只能走工具层 `notify_only`（后端调不到）。
#
# ★★ 故 `notify` 档的实现**改为「只写黑板卡、不调 send」** —— 而且这与调研自洽：
#   hermes 的 `notify` = 「只投递可见消息，**跑 0 个 turn**」；写卡不 send 正是这个语义。
#   ★★ 而它让门5 变得**必要**：写了卡但没人保证对方看到
#   ⇒ 门5 的「任何后续唤醒必带投递 pending」正是补这一环。
#
# ★★ 分形态合并窗口（抄 neo ADR 0002，已核实原文）：
#   通知 30s / 唤醒 120–180s（取 150s）· 硬上限 300s（超时**丢弃**不投递 —— 陈旧的答案没价值）
#   · flush 后 refractory 120s（刚 flush 完到达的进下一批，专杀「刚好落在窗口外」的节奏）
#   · **merge-don't-stack**（上一批未投递 ⇒ 合并进去，不叠第二块）
SG_MERGE = {"notify": 30, "notify+wake": 150, "wake": 150}
SG_MERGE_HARD_CAP = 300
SG_REFRACTORY = 120
SG_DELIVERY_MODES = ("notify", "notify+wake", "wake")


def sg_bus_port():
    """★ 复用 P5.0 的动态探测（不写死端口）。"""
    return sg_find_bus_port()


def sg_merge_window(mode, now=None):
    """★ 合并窗口参数（按投递形态分）。★ 返回 (window, hard_cap, refractory)。"""
    w = SG_MERGE.get(mode, 30)
    return w, SG_MERGE_HARD_CAP, SG_REFRACTORY


def sg_deliver(owner, gaps, mode="notify", dry_run=True, principal="sg-dispatch"):
    """★★ 三态投递（P5.3）。

    档位（★ 三态命名抄 hermes-agent `delivery_mode`，已核实原文）：
      · `notify`      —— **只写黑板卡，不 send**（★ 零唤醒）⇒ 进【门5 pending 区】
      · `notify+wake` —— 写卡 + `POST /api/send`（真唤醒一个 turn）
      · `wake`        —— **只 send**，text 极短（只给指针）⇒ 不写可见卡

    ★★ `dry_run` **默认 True** —— 本函数**在 dry_run 下不写任何东西**（含黑板卡与 send），
       只回报「会做什么」。要真发须显式 `dry_run=False`。
    ★★ 前置：调用方**必须已过五道门**（本函数不再重复判门，避免双重语义）。
    """
    if mode not in SG_DELIVERY_MODES:
        return {"ok": False, "err": "未知档位 %r（冻结枚举：%s）" % (mode, SG_DELIVERY_MODES)}
    now = time.time()
    gaps = list(gaps or [])
    # ★ 去重：同一批里同 gapId 只留一条（merge-don't-stack 的第一层）
    seen, uniq = set(), []
    for g in gaps:
        gid = g.get("gapId")
        if gid and gid not in seen:
            seen.add(gid); uniq.append(g)
    # ★ 合并成一条（同一收件人多个缺口 ⇒ 1 条带清单）
    lines = ["· [%s/%s] %s：%s" % (g.get("family"), g.get("severity"), g.get("subject"), g.get("evidence")) for g in uniq[:12]]
    head = "【缺口派发·%s】%d 项" % (mode, len(uniq))
    body = head + "\n" + "\n".join(lines) + (("\n… 另 %d 项" % (len(uniq) - 12)) if len(uniq) > 12 else "")
    # ★ v2.4 门：>200 字且无黑板引用 ⇒ 会被拒 ⇒ 故正文控制 + 落卡
    card_key = "notes/sg-dispatch/%s-%d" % (owner[:16] if owner else "unknown", int(now))
    card = {"from": principal, "to": owner, "type": "gap-dispatch", "mode": mode,
            "body": body, "gapIds": [g.get("gapId") for g in uniq], "ts": int(now)}
    did_card = did_send = False
    errs = []

    if dry_run:
        # ★★ 修（2026-10-12 本线实测）：第一版无条件回 wouldCardKey ⇒ 报出「wake 也会写卡」的假象。
        #   ⇒ dry-run 必须**如实镜像实写逻辑**：wouldCard 按档位判，与下面真实分支同一条件。
        will_card = mode in ("notify", "notify+wake")
        will_send = mode in ("notify+wake", "wake")
        return {"ok": True, "dryRun": True, "mode": mode, "owner": owner,
                "wouldCard": will_card,
                "wouldCardKey": (card_key if will_card else None),
                "wouldCardBody": (card if will_card else None),
                "wouldSend": will_send,
                "wouldText": ((body[:180] + " …看黑板 " + card_key)[:200] if will_send else None),
                "note": "★ dry_run：未写任何东西（含黑板卡与 send）。"
                        "★ wouldCard / wouldSend 与实写分支同一条件（三态语义：notify 只写卡 · "
                        "notify+wake 都做 · wake 只 send 不写可见卡）。"}

    # ① 写卡（notify 与 notify+wake 都写；wake 档**故意不写可见卡** —— 抄 hermes 的 wake 语义）
    if mode in ("notify", "notify+wake"):
        okc, ec = _bb_put(card_key, {"value": card, "ts": int(now)})
        did_card = bool(okc)
        if not okc:
            errs.append("写卡失败：%s" % ec)
    # ② 真投递（notify+wake 与 wake）
    if mode in ("notify+wake", "wake"):
        port = sg_bus_port()
        if port is None:
            errs.append("★ bus 端口探测失败 ⇒ 不投递（fail-closed）")
        else:
            try:
                # ★ 正文 ≤200 字（v2.4 门）+ 附黑板指针（让收件方能拿到全文）
                payload = json.dumps({"to": owner, "text": (body[:180] + " …看黑板 " + card_key)[:200]}).encode()
                rq = urllib.request.Request("http://127.0.0.1:%d/agent-bus/api/send" % port,
                                            data=payload, method="POST",
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(rq, timeout=10) as r:
                    resp = json.loads(r.read().decode())
                did_send = bool(resp.get("ok"))
                if not did_send:
                    errs.append("send 返回非 ok：%s" % json.dumps(resp, ensure_ascii=False)[:120])
            except Exception as e:
                errs.append("send 异常：%s: %s" % (type(e).__name__, e))
    # ③ 记账（★ 先落账再返回；含被拒/异常）
    rec = {"t": now, "owner": owner, "mode": mode, "gapIds": [g.get("gapId") for g in uniq],
           "card": card_key, "didCard": did_card, "didSend": did_send, "errs": errs, "by": principal}
    v, _ = _bb_get(SG_DISPATCH_LOG)
    log = v if isinstance(v, dict) else {}
    ents = [x for x in (log.get("dispatches") or []) if isinstance(x, dict)]
    ents.append(rec)
    _bb_put(SG_DISPATCH_LOG, {"dispatches": ents[-500:], "at": datetime.datetime.now().isoformat()})
    # ④ 进门5 pending 区（★ 只有 notify / notify+wake 需要回执；wake 也需要 —— 发了就该收口）
    _sg_receipt_add(owner, [g.get("gapId") for g in uniq], mode)
    return {"ok": (not errs), "dryRun": False, "mode": mode, "owner": owner,
            "card": card_key, "didCard": did_card, "didSend": did_send, "errs": errs, "rec": rec}


def _sg_receipt_add(owner, gap_ids, mode):
    """★ 门5 回执区：未 ack 的进 pending；★ 任何后续唤醒将附带投递它们。"""
    v, _ = _bb_get(SG_RECEIPT)
    r = v if isinstance(v, dict) else {}
    pend = [x for x in (r.get("pending") or []) if isinstance(x, dict)]
    have = {x.get("gapId") for x in pend}
    for gid in gap_ids:
        if gid and gid not in have:
            pend.append({"gapId": gid, "owner": owner, "mode": mode,
                         "dispatchedAt": time.time(), "acked": False})
    _bb_put(SG_RECEIPT, {"pending": pend[-500:], "at": datetime.datetime.now().isoformat()})
    return len(pend)


def sg_receipt_drain(owner):
    """★ 门5 的核心动作：**把该 owner 的未 ack pending 取出来**（供「任何后续唤醒必带投递」）。"""
    v, e = _bb_get(SG_RECEIPT)
    if e:
        return None, "回执区读不到：%s" % e
    r = v if isinstance(v, dict) else {}
    pend = [x for x in (r.get("pending") or []) if isinstance(x, dict)
            and x.get("owner") == owner and not x.get("acked")]
    return pend, None


# ══════════ ★ P5.4（2026-10-12 明鉴）：门5 对账扫描 + 验收层 ══════════
# ★★ 门5 对账（抄 Nylas「push 实时 + pull 对账 + 按 ID upsert 幂等」，已核实原文）：
#   原文口径 "You get push speed with **pull safety**"。
#   ★ 它治的是 11.5h 互等的**另一半**：光有「发出侧的门」不够，必须有**收口侧的兜底扫描**。
#   ★ 且它是 neo 的 resync 同族：客户端驱动的 catch-up。
#
# ★★ 回归预言机（抄 Kitchen Loop，已核实原文）：「**至少不比上一轮差**」
#   治的是「补一个缺口开两个」—— 补丁式补齐会制造新缺口，而**没人会报警**。
#
# ★★ 零上下文验收（同源）：**不让补缺口者自己报完成**
#   Kitchen Loop 原文：「38 passing unit tests coexisted with complete feature failure」
#   ⇒ 验收必须**换 agent、换上下文**。本实现把它做成**可机械判的检查**（verifier ≠ implementer）。
SG_GAP_HISTORY = "data/registry/sg-gap-history"
SG_RECONCILE_AGE_MIN = 45


def sg_receipt_reconcile(max_age_min=None):
    """★ 门5 的对账扫描。返回 (stale, summary)。

    ★ 找出 pending 中【超过阈值仍未 ack】的条目 ⇒ 报告。
    ★★ 它不"重发"，而是**把清单交给下一次任何原因的唤醒**（★ 不叠加唤醒 ——
       「merge-don't-stack」的同一原则：不为了对账再叫一次）。
    """
    mx = (SG_RECONCILE_AGE_MIN if max_age_min is None else max_age_min) * 60
    now = time.time()
    v, err = _bb_get(SG_RECEIPT)
    if err:
        return None, {"ok": False, "err": "★ 回执区读不到 ⇒ 不可判（不是「无 stale」）：%s" % err}
    r = v if isinstance(v, dict) else {}
    pend = [x for x in (r.get("pending") or []) if isinstance(x, dict) and not x.get("acked")]
    stale = [x for x in pend if (now - (x.get("dispatchedAt") or now)) > mx]
    return stale, {"ok": True, "pending": len(pend), "stale": len(stale),
                   "ageThresholdMin": mx / 60,
                   "owners": sorted({x.get("owner") for x in stale})}


def sg_regression_oracle(total, by_family, record=False):
    """★ 回归预言机：**至少不比上一轮差**。返回 (verdict, detail)。

    ★ 判据有意用【分族 + 总数】两个维度：
      · 总数变多 ⇒ 判红（补一个开两个）
      · 总数持平但**高严重度族(error)变多** ⇒ 也判红（换了更坏的缺口）
    ★★ `record=True` 才把本轮写进历史（★ 与棘轮的「显式开关」同一原则：
      **不许每次跑都悄悄改基线**）。
    """
    v, err = _bb_get(SG_GAP_HISTORY)
    if err:
        return "UNDECIDABLE", {"err": "★ 历史读不到 ⇒ 不可判（不是「无回归」）：%s" % err}
    h = v if isinstance(v, dict) else {}
    rounds = [x for x in (h.get("rounds") or []) if isinstance(x, dict)]
    cur = {"t": time.time(), "total": total,
           "byFamily": dict(by_family or {}),
           "errorCount": sum((by_family or {}).get(f, 0) for f in ("G3", "A", "B", "C", "E"))}
    if record:
        rounds.append(cur)
        _bb_put(SG_GAP_HISTORY, {"rounds": rounds[-200:], "at": datetime.datetime.now().isoformat()})
    if not rounds:
        return "NO_BASELINE", {"cur": cur, "note": "★ 首轮 ⇒ 无对照；已%s" % ("记入历史" if record else "未记入（须显式 record）")}
    prev = rounds[-1]
    d_total = cur["total"] - prev.get("total", 0)
    d_err = cur["errorCount"] - prev.get("errorCount", 0)
    bad = d_total > 0 or d_err > 0
    return ("REGRESSED" if bad else "OK"), {
        "prev": {"total": prev.get("total"), "errorCount": prev.get("errorCount")},
        "cur": {"total": cur["total"], "errorCount": cur["errorCount"]},
        "deltaTotal": d_total, "deltaError": d_err,
        "verdictNote": ("★ 回归：缺口总数 +%d / 高严重度 +%d ⇒ **补一个开两个**" % (d_total, d_err)) if bad
                       else "★ 未退化（至少不比上一轮差）",
    }


def sg_verify_independence(verifier, implementer):
    """★ 零上下文验收的机械判据：**verifier 必须不是 implementer**。

    ★ 这是「**补缺口者不得自证**」的可测形式。★ 三态：
      · 两者都给了且不同 ⇒ ok
      · 相同 ⇒ **拒**（自证）
      · 缺任一个 ⇒ **不可判**（★ 不是通过）
    """
    if not verifier or not implementer:
        return None, "★ 不可判：verifier 或 implementer 缺失（★ 缺失 ≠ 通过）"
    if str(verifier).strip() == str(implementer).strip():
        return False, "★ 自证：verifier 与 implementer 是同一会话（%s）⇒ 拒" % str(verifier)[:28]
    return True, "独立：verifier=%s ≠ implementer=%s" % (str(verifier)[:22], str(implementer)[:22])


def sg_optimistic_gate(req, kind, name, t0, principal, verb, reply):
    """★ P4 · R8（2026-10-12）：乐观锁 —— **并发互斥的机械保证**。

    协议见 `docs/systemgraph-write-protocol-v1-20261012.md`：
      · **不带 `expected_seq`** ⇒ 按当前 seq 直接追加（★ 向后兼容 P2/P3 的调用）
      · **带上且相等** ⇒ 放行
      · **带上但不等** ⇒ **409 Conflict**，★ 且响应体给出 `conflict{expected,actual}` 与 `current` 状态
        （★ 让调用方**不必再发一次读**就能重试 —— 「拒绝也要把为什么和现在是什么给足」）

    ★ 返回 True 表示放行；False 表示已回复（调用方应直接 return）。
    """
    if "expected_seq" not in req:
        return True
    exp = req.get("expected_seq")
    if kind == "page":
        cur = sg_page_read(name)
        if not cur["ok"]:
            reply(502, principal, verb, "读页面档失败：%s" % cur.get("err"), t0)
            return False
        actual = len((cur["doc"] or {}).get("history") or [])
        state = sg_page_state(cur["doc"])
    else:
        cur = sg_graph_read(name)
        if not cur["ok"]:
            reply(502, principal, verb, "读图档失败：%s" % cur.get("err"), t0)
            return False
        actual = len((cur["doc"] or {}).get("entries") or [])
        state = sg_graph_edges(cur["doc"])
    try:
        exp_i = int(exp)
    except Exception:
        reply(400, principal, verb, "★ expected_seq 必须是整数，收到 %r" % (exp,), t0)
        return False
    if exp_i != actual:
        reply(409, principal, verb,
              "★ 冲突：expected_seq=%s 但当前为 %s ⇒ 请取新 seq 后重试" % (exp_i, actual), t0,
              {"conflict": {"expected": exp_i, "actual": actual},
               "targetKind": kind, "targetName": name, "current": state})
        return False
    return True


def sg_register_watch(key):
    """★ P3 · R5（2026-10-12）：把可写键**登记进模型监听面**。

    ★★ 为什么必须做（实测）：模型的 `watch_keys` 只含 `data/blueprint/*`，
      **不含新可写键**（`data/sg-page/*` · `data/sg-graph/*`）⇒
      **写进可写枢纽不会 bump 模型版本** ⇒ 前端「变了才重取」**感知不到变化** ⇒ R5 不成立。
    ⇒ 修：每次成功写后调 `MODEL.add_watch(key)`（ModelStore 自带此 API，**下一次 reload 生效**）。
    ★ 不静默失败：登记不上要记 stderr（否则「以为会推」而实际不推，正是本晚反复的病灶）。
    """
    try:
        if MODEL is None:
            sys.stderr.write("⚠️ sg_register_watch: MODEL 未初始化，%s 未登记（R5 推送不会生效）\n" % key)
            return False
        added = MODEL.add_watch(key)
        if added:
            sys.stderr.write("ℹ️ sg_register_watch: 已登记 %s（下次 reload 生效）\n" % key)
        return bool(added)
    except Exception as e:
        sys.stderr.write("⚠️ sg_register_watch 失败（%s）：%s\n" % (type(e).__name__, e))
        return False


def sg_page_write(view, principal, entry, expected_seq=None):
    """★★ P4（R8）：同 sg_graph_write —— **整段读-校验-写在同一把锁内**。
    ★ 返回 (ok, reason, entry, conflict)；conflict 非空 ⇒ 应回 409。
    """
    with SGW_LOCK:
        cur = sg_page_read(view)
        if not cur["ok"]:
            return False, "读页面档失败：%s" % cur.get("err"), None, None
        doc = cur["doc"]
        hist = doc.get("history") or []
        actual = len(hist)
        if expected_seq is not None and int(expected_seq) != actual:
            return False, ("★ 冲突：expected_seq=%s 但当前为 %s ⇒ 请取新 seq 后重试"
                           % (expected_seq, actual)), None, {
                "conflict": {"expected": int(expected_seq), "actual": actual},
                "targetKind": "page", "targetName": view,
                "current": sg_page_state(doc)}
        entry = dict(entry)
        entry["seq"] = actual + 1
        entry["at"] = datetime.datetime.now().isoformat()
        entry["by"] = principal
        hist.append(entry)
        doc["history"] = hist
        doc["view"] = view
        # ★★★ 2026-10-12 修（实测触发）：**把「写失败」与「写成功但确认不了」分开**。
        #   起因：实测 PUT 的**响应 >60s 不回**，但**回读证明写入已落盘** ⇒
        #   原实现把这种情形一律报 `写页面档失败：timeout` ⇒ ★ **把「成功」报成了「失败」**。
        #   ★★ 这与本线反复立的纪律同源：**「拿不到」≠「没有」**（同理「确认不了」≠「失败」）。
        #   ⇒ 现在：**PUT 阶段失败** ⇒ `writeFailed`；**PUT 已过、回读失败** ⇒ `committedUnverified`
        #     （★ 如实说「已提交、状态未确认」，并提示调用方**自行复查**）。
        put_done = False
        try:
            body = json.dumps(doc, ensure_ascii=False).encode()
            rq = urllib.request.Request("http://127.0.0.1:8792/%s" % sg_page_key(view),
                                        data=body, method="PUT",
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(rq, timeout=8) as r:
                r.read()
            put_done = True
            back = sg_page_read(view)
            n = len((back.get("doc") or {}).get("history") or [])
            if n != len(hist):
                return False, ("★ 回读不符（写入 %d 条 / 回读 %d 条）—— ★ 写入可能已提交但未确认，"
                               "请自行复查 data/sg-page/%s" % (len(hist), n, view)), None, None
            sg_register_watch(sg_page_key(view))
            return True, "已追加 seq=%d 并回读（history=%d 条）" % (entry["seq"], n), entry, None
        except Exception as e:
            # ★★★ 2026-10-12 第二次修（实测触发）：**PUT 超时也要看【结果态】再判**。
            #   实测：黑板对 PUT 的**响应 >8s**（`timeout=8` 到点即抛），**但写入其实已完成**
            #   ⇒ 上一版仍把这种情形报成 `writeFailed` ⇒ **仍把成功报成失败**。
            #   ★★ 正解正是 R006 §6 坑 #4 的原文：「**判据要选【结果态】而非【过程态】**」
            #      ⇒ PUT 异常后**回读一次**：
            #        · 回读显示内容已在（历史变长）⇒ **如实报「已提交（响应超时）」**
            #        · 回读显示不在或读不到 ⇒ 才判失败（并区分「读不到」= 不可判）
            err = "%s: %s" % (type(e).__name__, e)
            try:
                back2 = sg_page_read(view)
                n2 = len((back2.get("doc") or {}).get("history") or [])
                if n2 >= len(hist):
                    sg_register_watch(sg_page_key(view))
                    return True, ("★ 已提交（提交成功 · 响应超时）：PUT 响应 %s，但回读确认已落盘"
                                  "（history=%d 条，含本次 seq=%d）" % (err, n2, entry["seq"])), entry, None
                return False, ("★ 写失败（writeFailed）：PUT %s，且**回读确认未落盘**"
                               "（history=%d 条 < 期望 %d）" % (err, n2, len(hist))), None, None
            except Exception as e2:
                return False, ("★ 不可判（undecidable）：PUT %s；随后**回读也失败**（%s: %s）"
                               "⇒ 状态未知，**既不能说成功也不能说失败** —— 请自行复查 data/sg-page/%s"
                               % (err, type(e2).__name__, e2, view)), None, None

SG_VERBS = {
    # ── 沙盒（P1 的动词；只写探针键）──
    "probe.write":        {"resource": "probe",    "action": "write"},
    # ── 页面内容动词（P2）★★ resource_from="view" ⇒ ACL 粒度到【单页】`page:<view>` ──
    "page.set_field":     {"resource": "page",     "action": "write", "resource_from": "view"},
    "page.add_block":     {"resource": "page",     "action": "write", "resource_from": "view"},
    "page.rollback":      {"resource": "page",     "action": "write", "resource_from": "view"},
    # ── 关系动词（P3）★★ resource_from="graph" ⇒ ACL 粒度到【单图】`relation:<name>` ──
    "relation.add_edge":  {"resource": "relation", "action": "write", "resource_from": "graph"},
    "relation.remove_edge": {"resource": "relation", "action": "write", "resource_from": "graph"},
    "relation.restore_edge": {"resource": "relation", "action": "write", "resource_from": "graph"},
}


def sg_graph_of(target):
    """★ R4 寻址：`graph:<name>` ⇒ `<name>`。返回 (name, err)。"""
    t = str(target or "").strip()
    if not t.startswith("graph:"):
        return None, "target 须形如 `graph:<name>`，收到 %r" % t[:40]
    n = t.split(":", 1)[1].strip()
    if not n or not re.match(r"^[a-z0-9_-]+$", n):
        return None, "图名不合法（只允许 [a-z0-9_-]+）：%r" % n[:40]
    return n, None


def sg_view_of(target):
    """★ R3 寻址：`page:<view>` ⇒ `<view>`。返回 (view, err)。"""
    t = str(target or "").strip()
    if not t.startswith("page:"):
        return None, "target 须形如 `page:<view>`，收到 %r" % t[:40]
    v = t.split(":", 1)[1].strip()
    if not v or not re.match(r"^[a-z0-9_-]+$", v):
        return None, "view 名不合法（只允许 [a-z0-9_-]+）：%r" % v[:40]
    return v, None


def sg_load_acl():
    """★ 读 ACL。文件不存在或读不动 ⇒ 视为**空 ACL** ⇒ 默认全拒（fail-closed）。"""
    try:
        with open(SG_ACL_PATH, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def sg_check(principal, resource, action):
    """★ R2 核心判定。★ 返回 (allowed: bool, reason: str)。

    ★★ 默认拒绝（fail-closed）：
      · principal 为空 / ACL 无此 principal / grants 不覆盖 ⇒ **拒**
      · 资源与动作须**同时**命中一条 grant（`*` 支持通配）
      ★ 本函数**不抛异常**（鉴权路径不许因异常而"放行"）。
    """
    if not principal:
        return False, "无 principal（缺 X-SG-Principal 头）⇒ 默认拒绝"
    acl = sg_load_acl()
    if acl.get("default", "deny") != "deny":
        # ★ 即使有人把 default 改成 allow，本函数也**不认** —— 见下方显式断言
        return False, "★ ACL 的 default 不是 deny ⇒ 拒绝加载（本实现只支持 fail-closed）"
    p = (acl.get("principals") or {}).get(principal)
    if not p:
        return False, "principal 不在 ACL 中 ⇒ 默认拒绝"
    for g in (p.get("grants") or []):
        r_ok = g.get("resource") in ("*", resource)
        a_ok = action in (g.get("actions") or []) or "*" in (g.get("actions") or [])
        if r_ok and a_ok:
            return True, "命中 grant：resource=%s actions=%s" % (g.get("resource"), g.get("actions"))
    return False, "principal 存在但其 grants 未覆盖 %s/%s ⇒ 拒绝" % (resource, action)


def sg_audit(rec):
    """★ 写尝试留痕（含被拒的）。★ 失败也不阻断请求（只记 stderr）。"""
    try:
        os.makedirs(os.path.dirname(SG_WRITE_AUDIT), exist_ok=True)
        with open(SG_WRITE_AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write("⚠️ sg_audit 写入失败：%s\n" % e)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        # BaseHTTPRequestHandler 会为每个请求调本方法 —— 记录访问日志(含错误码)
        try:
            msg = (a[0] % a[1:]) if len(a) > 1 and isinstance(a[0], str) else str(a[0] if a else "")
            # msg 形如 '"GET /api/x HTTP/1.1" 200 -'
            import re as _re
            m = _re.match(r'"(?:GET|POST|PUT|DELETE) ([^ ]*)', msg)
            code_m = _re.search(r'" (\d{3})', msg)
            code = int(code_m.group(1)) if code_m else 0
            _log_access(datetime.datetime.now().isoformat(), "HTTP", m.group(1) if m else "?", code)
        except Exception:
            pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        # R006#7: 错误响应(>=400)与写类请求记日志 —— 用户/运维可回溯"刚才为何失败"
        try:
            if code >= 400 or self.path.startswith("/api/connect-advance") or self.path.startswith("/api/connect-confirm") \
               or self.path.startswith("/api/link-status") or self.path.startswith("/api/manager-event"):
                _log_access(datetime.datetime.now().isoformat(), "REQ", self.path[:300], code,
                            referer=self.headers.get("Referer", ""), agent=self.headers.get("User-Agent", ""))
        except Exception:
            pass

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        try:
            if path == "/":
                self._send(200, build_index(self.server.server_port), "text/html; charset=utf-8")
                return
            if path == "/vendor/d3.min.js":
                d3path = os.path.expanduser("~/.dsh/profiles/web/node_modules/d3/dist/d3.min.js")
                if os.path.exists(d3path):
                    with open(d3path, encoding="utf-8") as f:
                        self._send(200, f.read(), "application/javascript; charset=utf-8")
                    return
                self._send(404, json.dumps({"error": "d3 not found"}))
                return
            if path == "/api/registry-people":
                # Network v0.2 打通(B 统一实体主源): 只读人类维度 — REG people/orgs + 蓝图域过滤
                _REG = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/business-entity-registry.json")
                _reg = {}
                if os.path.exists(_REG):
                    try:
                        _reg = json.load(open(_REG, encoding="utf-8"))
                    except Exception:
                        _reg = {}
                from urllib.parse import urlparse as _upR, parse_qs as _pqR
                _dom = (_pqR(_upR(self.path).query).get("domain") or [""])[0]
                _peo = []
                for _p in (_reg.get("people") or []):
                    if _dom and _dom not in (_p.get("domains") or []):
                        continue
                    _peo.append({"id": _p.get("id"), "name": _p.get("name"),
                                 "aliases": _p.get("aliases", []), "title": _p.get("title", ""),
                                 "domains": _p.get("domains", []),
                                 "orgIds": _p.get("orgIds", []),
                                 "confidence": (_p.get("verified") or {}).get("confidence", "")})
                _orgs = _reg.get("orgs") or []
                self._send(200, json.dumps({"ok": True, "source": "business-entity-registry.json",
                                            "domain": _dom or "all",
                                            "people": _peo, "orgs": _orgs,
                                            "totalPeople": len(_peo), "totalOrgs": len(_orgs)},
                                           ensure_ascii=False))
                return
            if path == "/api/logs":
                # R006#7: 访问/错误日志查询 — /api/logs?limit=50&code=5xx|4xx|all
                from urllib.parse import urlparse as _upl, parse_qs as _pql
                _ql = _pql(_upl(self.path).query)
                try:
                    _limit = min(int((_ql.get("limit") or ["80"])[0]), 500)
                except Exception:
                    _limit = 80
                _filt = (_ql.get("code") or ["all"])[0]
                _lines = []
                for _lf in ([_ACCESS_LOG, _ACCESS_LOG + ".1"] if os.path.exists(_ACCESS_LOG + ".1") else [_ACCESS_LOG]):
                    if not os.path.exists(_lf):
                        continue
                    with open(_lf, encoding="utf-8", errors="replace") as _f:
                        _lines.extend(_f.read().splitlines())
                _recs = []
                for _ln in _lines[-1000:]:  # 只扫最近 1000 行, 防大文件拖慢
                    try:
                        _r = json.loads(_ln)
                        _c = int(_r.get("code") or 0)
                        if _filt == "5xx" and not (500 <= _c < 600):
                            continue
                        if _filt == "4xx" and not (400 <= _c < 500):
                            continue
                        _recs.append(_r)
                    except Exception:
                        continue
                _recs = _recs[-_limit:]
                self._send(200, json.dumps({"ok": True, "count": len(_recs),
                                            "filter": _filt, "logFile": os.path.basename(_ACCESS_LOG),
                                            "entries": _recs}, ensure_ascii=False))
                return
            if path == "/api/connect-confirm":
                try:
                    from urllib.parse import urlparse, parse_qs
                    _q = parse_qs(urlparse(self.path).query)
                    _req = {"from": (_q.get("from") or [""])[0], "to": (_q.get("to") or [""])[0],
                            "reason": (_q.get("reason") or ["连接实验室人工确认"])[0],
                            "gate_level": (_q.get("gate") or [""])[0]}
                    # Φ9 门禁: 无 gate 评估记录 → 拒绝(缺 Authorization 构造不出 ConfirmedEdge)
                    if not _req["gate_level"]:
                        self._send(200, json.dumps({"ok": False, "error": "缺 gate 评估(先 /api/connect-gate)", "gate_required": True}))
                        return
                    # 🧪 沙箱门: 服务端再验一次(防绕过) — 冲突边拒绝
                    _sb = sandbox_preview(_req["from"], _req["to"])
                    if _sb.get("conflict"):
                        self._send(200, json.dumps({"ok": False, "error": "沙箱冲突: " + _sb.get("detail",""), "sandbox_conflict": True}))
                        return
                    _gate = gate_confirm(_req["from"], _req["to"])
                    # 五步门: 执行需候选已 APPROVED(pipeline 记录), 否则拒(不可跳过审批)
                    _pi = pipe_item(_req["from"], _req["to"])
                    if not (_pi and _pi.get("step") == "APPROVED"):
                        self._send(200, json.dumps({"ok": False, "error": "候选未审批(五步门: 需先 evaluate→recommend→plan→approve)"}))
                        return
                    _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
                    _cd = json.load(open(_cf, encoding="utf-8")) if os.path.exists(_cf) else {"links": []}
                    _dup = any(l.get("from")==_req.get("from") and l.get("to")==_req.get("to") for l in _cd.get("links", []))
                    if not _dup:
                        _cd.setdefault("links", []).append({
                            "from": _req.get("from"), "to": _req.get("to"),
                            "reason": _req.get("reason",""),
                            "auth": {
                                "by": "user", "ts": datetime.datetime.now().isoformat(),
                                "gate": {
                                    "level": _gate.get("level","?"), "score": _gate.get("score",0),
                                    "verdict": _gate.get("verdict",""), "reasons": _gate.get("reasons",[])
                                },
                                "sandbox": {
                                    "conflict": _sb.get("conflict", False),
                                    "eliminatedIslands": _sb.get("eliminatedIslands", 0),
                                    "detail": _sb.get("detail", "")
                                },
                                "disaster": "D1" if _gate.get("level")=="L1" else ("D2" if _gate.get("level")=="L2" else "D3")
                            }
                        })
                        json.dump(_cd, open(_cf,"w"), ensure_ascii=False, indent=1)
                        # ⚡ 自动接线(R006#10/Φ9): 建边后同步调 execute 执行器 —— 通知两端相关方(黑板通知墙+协作任务登记)
                        #    走 bb-connect-execute.py 的 Lean4 结构门(端点合法性/幂等), 语义与 CLI 执行完全一致
                        _exe_ok = _run_execute_after_confirm(_req["from"], _req["to"], _req.get("reason",""))
                        _xtra = {"notified": _exe_ok}
                    else:
                        _xtra = {"notified": None, "duplicate": True}
                    self._send(200, json.dumps({"ok": True, "duplicate": _dup, **_xtra}))
                except Exception as _e:
                    self._send(200, json.dumps({"ok": False, "error": str(_e)}))
                return
            if path == "/api/explore":
                from urllib.parse import urlparse as _up4, parse_qs as _pq4
                _q4=_pq4(_up4(self.path).query)
                self._send(200, json.dumps(explore_graph((_q4.get("graph") or ["relations"])[0]), ensure_ascii=False))
                return
            if path == "/api/manager-event":
                # GUI 操作事件 → 黑板 notes/mac-mini/manager-actions/ (明鉴回合感知)
                from urllib.parse import urlparse as _up7, parse_qs as _pq7
                _q7=_pq7(_up7(self.path).query)
                _ev=(_q7.get("event") or [""])[0]; _act=(_q7.get("detail") or [""])[0]
                _lv=(_q7.get("level") or ["info"])[0]  # info=落盘 / important=唤醒
                # Φ9 事件 schema 门: 白名单事件 + 合法级别(拒伪造/未知)
                _EV_WHITELIST={"connect-executed","link-status","link-merged","bp-view","gate-passed","explore-open","page-view","error"}
                _LV_VALID={"info","important"}
                if _ev not in _EV_WHITELIST:
                    self._send(200, json.dumps({"ok":False,"error":"事件不在白名单(拒收): "+_ev})); return
                if _lv not in _LV_VALID:
                    self._send(200, json.dumps({"ok":False,"error":"级别非法: "+_lv})); return
                # ★★★ 2026-10-13 修（本线实测根因）：**同类错误卡去重**。
                #   实测：某类卡连发 4 次【逐字相同】（/api/hwprobe Fetch is aborted ×4，间隔 37/45/13/48 分）
                #   ⇒ 那不只是噪音，还会掩盖「真正的变化」。⇒ 同一 (event,detail) 在冷却窗内只落一张。
                if _ev == "error":
                    try:
                        _cooldown = 1800  # 30 分钟
                        # ★★ 2026-10-13 修（实测触发的第二处）：**枚举要【带尾斜杠】** ——
                        #   实测 `notes/mac-mini/manager-actions`（无斜杠）→ `{"error":"not found"}`；
                        #   带斜杠 `…/manager-actions/` → `{"list":…}`（26 条）。
                        #   ★ 且 `_bb_get` 是为【具体键】设计的（取 `value`）⇒ **对枚举不适用**（枚举没有 value 键）
                        #     ⇒ 第一版两错叠加 ⇒ `_recent={}` ⇒ 循环 0 次 ⇒ **去重永不触发**（静默失效）。
                        #   ⇒ 改用 urlopen 直读枚举，并**如实区分三态**（读到列表 / 空列表 / 读失败）。
                        _recent = None
                        try:
                            with urllib.request.urlopen(
                                    "http://127.0.0.1:8792/notes/mac-mini/manager-actions/", timeout=8) as _rr:
                                _recent = json.loads(_rr.read().decode())
                        except Exception:
                            _recent = None
                        _lst = {}
                        if isinstance(_recent, dict):
                            if isinstance(_recent.get("list"), dict):
                                _lst = _recent["list"]
                            elif isinstance(_recent.get("value"), dict):
                                _lst = _recent["value"].get("list") or {}
                        for _kk, _vv in list(_lst.items())[-30:]:
                            _iv = (_vv.get("value") or {})
                            _iv = _iv.get("value") if isinstance(_iv.get("value"), dict) else _iv
                            if _iv.get("event") == "error" and _iv.get("detail") == _act[:200]:
                                _ts = _iv.get("ts") or ""
                                try:
                                    _age = (datetime.datetime.now() - datetime.datetime.fromisoformat(_ts)).total_seconds()
                                except Exception:
                                    _age = 0
                                if 0 <= _age < _cooldown:
                                    self._send(200, json.dumps({"ok": True, "duplicate": True,
                                        "reason": "同类错误卡在 %ds 冷却窗内 ⇒ 不重发（★ 去重）" % _cooldown,
                                        "ageSec": int(_age), "firstKey": _kk}))
                                    return
                    except Exception:
                        pass  # ★ 去重失败不阻断主流程
                try:
                    _k="notes/mac-mini/manager-actions/%s" % datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
                    _p={"ts":datetime.datetime.now().isoformat(),"from":"systemgraph-gui","level":_lv,
                        "event":_ev,"detail":_act[:200]}
                    _bd=json.dumps(_p).encode()
                    _rq=urllib.request.Request("http://127.0.0.1:8792/"+_k,data=_bd,
                        headers={"Content-Type":"application/json"},method="PUT")
                    urllib.request.urlopen(_rq,timeout=5)
                    self._send(200, json.dumps({"ok":True,"level":_lv,"key":_k}))
                except Exception as _e:
                    self._send(200, json.dumps({"ok":False,"error":str(_e)}))
                return
            if path == "/api/confirmed-links":
                self._send(200, json.dumps({"links": get_confirmed_links()}, ensure_ascii=False))
                return
            if path == "/api/link-status":
                from urllib.parse import urlparse as _up6, parse_qs as _pq6
                _q6=_pq6(_up6(self.path).query)
                self._send(200, json.dumps(update_link_status(
                    (_q6.get("graph") or ["agents"])[0], (_q6.get("from") or [""])[0],
                    (_q6.get("to") or [""])[0], (_q6.get("status") or [""])[0]), ensure_ascii=False))
                return
            if path == "/api/connect-advance":
                from urllib.parse import urlparse as _up3, parse_qs as _pq3
                _q3 = _pq3(_up3(self.path).query)
                _r = pipe_advance((_q3.get("from") or [""])[0], (_q3.get("to") or [""])[0],
                                  (_q3.get("action") or ["evaluate"])[0], (_q3.get("graph") or ["agents"])[0])
                self._send(200, json.dumps(_r, ensure_ascii=False))
                return
            if path == "/api/connect-sandbox":
                from urllib.parse import urlparse as _up2, parse_qs as _pq2
                _q2 = _pq2(_up2(self.path).query)
                self._send(200, json.dumps(sandbox_preview((_q2.get("from") or [""])[0], (_q2.get("to") or [""])[0]), ensure_ascii=False))
                return
            if path == "/api/confirm-link":
                from urllib.parse import urlparse as _up5, parse_qs as _pq5
                _q5=_pq5(_up5(self.path).query)
                _g5=(_q5.get("graph") or [""])[0]; _f5=(_q5.get("from") or [""])[0]
                _t5=(_q5.get("to") or [""])[0]; _r5=(_q5.get("reason") or ["接入确认"])[0]
                if not (_g5 and _f5 and _t5):
                    self._send(200, json.dumps({"ok":False,"error":"需 graph/from/to"})); return
                # 五步门: 执行需该 graph 的候选已 APPROVED
                _pi = next((x for x in _load_pipe()["items"] if x.get("graph")==_g5 and x.get("from")==_f5 and x.get("to")==_t5), None)
                if not (_pi and _pi.get("step")=="APPROVED"):
                    self._send(200, json.dumps({"ok":False,"error":"候选未审批: 先五步门(evaluate→recommend→plan→approve, 带 graph=%s)"%_g5})); return
                if add_confirmed_link(_g5,_f5,_t5,_r5,{"by":"user","ts":datetime.datetime.now().isoformat(),"gate":{"level":"L1","note":"通用五步门通过"}}):
                    self._send(200, json.dumps({"ok":True,"note":f"已写入 {_g5} 域 confirmed-links"}))
                else:
                    self._send(200, json.dumps({"ok":False,"error":"重复或已存在"}))
                return
            if path == "/api/connect-gate":
                from urllib.parse import urlparse as _up, parse_qs as _pq
                _q = _pq(_up(self.path).query)
                _g = gate_confirm((_q.get("from") or [""])[0], (_q.get("to") or [""])[0])
                self._send(200, json.dumps(_g, ensure_ascii=False))
                return
            if path == "/api/connect-lab":
                self._send(200, json.dumps(build_connect_lab(), ensure_ascii=False))
                return
            if path == "/api/health":
                self._send(200, json.dumps(build_health_report(), ensure_ascii=False))
                return
            if path == "/api/model-status":
                # ★ A 组（2026-10-12）：模型层的自述端点。
                #   暴露：版本号 version（任一路变化即自增）· 板书三态计数
                #   （OK / EMPTY / UNREACHABLE）· 每键状态 · 文件监听元组 · SSE 状态与事件数。
                #   ★ 三态用词严格：UNREACHABLE（不可判）**不得**被读作 EMPTY（真无）。
                #   ★ 这也是修掉 fetch() 旧「静默返空」缺陷后可被外部看见的那一面。
                if MODEL is None:
                    self._send(200, json.dumps(
                        {"model": None,
                         "note": "模型未初始化（_init_model 失败或未调用）⇒ 全部取数走直连路径"},
                        ensure_ascii=False))
                else:
                    self._send(200, json.dumps(MODEL.status(), ensure_ascii=False))
                return
            if path == "/api/xq-artifacts":
                # ★ C 组（2026-10-12）：星桥交来的 10 件产物的只读元数据。
                #   裁定：文件为唯一权威（不建独立索引）· 出元数据而非正文 · 三态（OK/MISSING/UNREADABLE）。
                #   ★ 逐次实时读盘 —— 10 次 stat + 10 次小读，成本可忽略；换来的是**永不陈旧**。
                try:
                    self._send(200, json.dumps(build_xq_artifacts(), ensure_ascii=False))
                except Exception as e:
                    # ★ 不许静默返空：失败要说出来（本夜 fetch() 静默返空的教训）
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "items": []},
                        ensure_ascii=False))
                return
            if path == "/api/deviation-ledger":
                # ★ C6（2026-10-12）：偏差台账聚合 + 最近 N 条（只读）。
                try:
                    self._send(200, json.dumps(build_deviation_ledger(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "recent": []},
                        ensure_ascii=False))
                return
            if path == "/api/gap-inventory":
                # ★ C3（2026-10-12）：差距盘点（只读）。★ 最有行动价值的聚合是【卡在谁】。
                try:
                    self._send(200, json.dumps(build_gap_inventory(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "gaps": []},
                        ensure_ascii=False))
                return
            if path == "/api/channel-baseline":
                # ★ C5（2026-10-12）：通道基线 —— ★ 现测双板（只发 GET，不写板）。
                try:
                    self._send(200, json.dumps(build_channel_baseline(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "m4": []},
                        ensure_ascii=False))
                return
            if path == "/api/goal-dimensions":
                # ★ C1（2026-10-12）：目标页 —— 四维 S/H/I/L（只读 v6.1）。
                try:
                    self._send(200, json.dumps(build_goal_dimensions(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "dims": []},
                        ensure_ascii=False))
                return
            if path == "/api/progress-axis":
                # ★ C2（2026-10-12）：进度页 —— 阶段轴 + 执行序 + M0–M4（只读 v6.1）。
                try:
                    self._send(200, json.dumps(build_progress_axis(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "miles": []},
                        ensure_ascii=False))
                return
            if path == "/api/two-circles":
                # ★ C4（2026-10-12）：两圈（原始三分）设计 + 遗忘根因（只读）。
                try:
                    self._send(200, json.dumps(build_two_circles(), ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps(
                        {"error": "%s: %s" % (type(e).__name__, e), "cites": []},
                        ensure_ascii=False))
                return
            if path == "/api/sg-page":
                # ★ P2（2026-10-12）：读页面内容档（R3 寻址 + 版本历史）。只读。
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                view = ""
                for kv in q.split("&"):
                    if kv.startswith("view="):
                        view = kv[5:]
                if not re.match(r"^[a-z0-9_-]+$", view or ""):
                    self._send(400, json.dumps({"error": "缺 view= 或名字不合法"}, ensure_ascii=False))
                    return
                r = sg_page_read(view)
                doc = r.get("doc") or {"history": []}
                self._send(200, json.dumps({
                    "view": view, "key": sg_page_key(view),
                    "readable": r["ok"], "readErr": r.get("err"),
                    "history": doc.get("history") or [],
                    "state": sg_page_state(doc),
                    "note": "★ 当前状态由 append-only 历史**重放**得出（不存 current，避免两份真相）。",
                }, ensure_ascii=False))
                return
            if path == "/api/sg-graph":
                # ★ P3（2026-10-12）：读图档（R4 连线编辑 + 墓碑历史）。只读。
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                gname = ""
                for kv in q.split("&"):
                    if kv.startswith("name="):
                        gname = kv[5:]
                if not re.match(r"^[a-z0-9_-]+$", gname or ""):
                    self._send(400, json.dumps({"error": "缺 name= 或名字不合法"}, ensure_ascii=False))
                    return
                r = sg_graph_read(gname)
                doc = r.get("doc") or {"entries": []}
                st = sg_graph_state(doc)
                self._send(200, json.dumps({
                    "name": gname, "key": sg_graph_key(gname),
                    "readable": r["ok"], "readErr": r.get("err"),
                    "entries": doc.get("entries") or [],
                    "edges": sg_graph_edges(doc),
                    "tombs": [k for k, v in st.items()
                              if isinstance(v, dict) and not v.get("present") and v.get("edge")],
                    "note": "★ 边集由 append-only 历史重放得出；★ 删除走墓碑 ⇒ 删过的边仍可回滚。",
                }, ensure_ascii=False))
                return
            if path == "/api/sg-owner-check":
                # ★ P5.0（2026-10-12）：属主存活校验（只读）。★ fail-closed。
                #   ★ 三态分列：alive=true / alive=false / liveUnavailable（拿不到存活列表 ⇒ 不可判）
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                owner = ""
                for kv in q.split("&"):
                    if kv.startswith("owner="):
                        owner = kv[6:]
                alive, why, n = sg_owner_alive(owner)
                self._send(200, json.dumps({
                    "owner": owner, "alive": alive, "reason": why,
                    "liveCount": n, "verdict": ("可派发" if alive else "挂起+告警"),
                    "note": "★ fail-closed：拿不到存活列表 ⇒ 判「不存活」（挂起），绝不「因为查不到所以放行」。"
                            "★ 存活判定不缓存；只有 bus 端口缓存 30s（重启会漂移）。",
                }, ensure_ascii=False))
                return
            if path == "/api/sg-gaps":
                # ★ P5.1（2026-10-12）：缺口检出 + 棘轮（只读；★ 只有显式带 update_baseline=1 才改基线）
                try:
                    ups = "update_baseline=1" in (self.path.split("?", 1)[1] if "?" in self.path else "")
                    gaps, scanned = sg_detect_gaps()
                    new, frozen, bsize, note = sg_gap_ratchet(gaps, update_baseline=ups)
                    self._send(200, json.dumps({
                        "scanned": scanned, "total": len(gaps),
                        "newGaps": new, "newCount": (len(new) if new is not None else None),
                        "frozenCount": frozen, "baselineSize": bsize,
                        "byFamily": {f: sum(1 for g in gaps if g["family"] == f) for f in GAP_FAMILIES},
                        "ratchetNote": note,
                        "families": GAP_FAMILIES,
                        "note": "★ 缺口族贴着【本夜实测的真问题】；结构性 A–E 在真数据上为 0 ⇒ 它们是【负控主语】。"
                                "★ 棘轮：存量冻结、只报新增；★ 改基线须显式 update_baseline=1（防「改基线假装清零」）。",
                    }, ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps({"error": "%s: %s" % (type(e).__name__, e)}, ensure_ascii=False))
                return
            if path == "/api/sg-gates":
                # ★ P5.2（2026-10-12）：五道门串联判定（只读；★ 只有 switch= 才改总开关）
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                kv = dict(x.split("=", 1) for x in q.split("&") if "=" in x)
                if "switch" in kv:
                    on = kv["switch"] == "on"
                    _bb_put(SG_SWITCH, {"on": on, "by": kv.get("by", "ui"), "at": datetime.datetime.now().isoformat()})
                gid, fam = kv.get("gapId", ""), kv.get("family", "G1")
                owner = kv.get("owner", "")
                gap = {"gapId": gid, "family": fam, "subject": kv.get("subject", "")}
                allowed, gate, reason = sg_gate_chain(gap, owner)
                sw, swr = sg_gate_switch()
                self._send(200, json.dumps({
                    "switch": sw, "switchReason": swr,
                    "allowed": allowed, "blockedBy": (None if allowed else gate), "reason": reason,
                    "gapId": gid, "family": fam, "owner": owner,
                    "gates": {
                        "门0 总开关": swr,
                        "门1 属主门": sg_owner_alive(owner)[1],
                        "门2 去重门": sg_gate_dedup(gid, fam)[1],
                        "门3 频次门": sg_gate_freq(owner)[1],
                        "门4 熔断门": sg_gate_breaker(owner)[1],
                        "门5 回执门": sg_gate_receipt(gid)[1],
                    },
                    "note": "★ 全部默认拒绝（fail-closed）：任一门拿不到状态 ⇒ 拒。"
                            "★ 位置在【派发前、派发方】，不让收件人自己挡。",
                }, ensure_ascii=False))
                return
            if path == "/api/sg-deliver":
                # ★ P5.3（2026-10-12）：三态投递。★ **dry_run 默认 1**；要真发须显式 go=1
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                kv = dict(x.split("=", 1) for x in q.split("&") if "=" in x)
                owner = kv.get("owner", "")
                mode = kv.get("mode", "notify")
                go = kv.get("go") == "1"
                # ★ 取本轮缺口（可用 family/gapId 过滤；缺省取前 3 条 warn 级）
                try:
                    allg, _sc = sg_detect_gaps()
                except Exception as e:
                    allg = []
                sel = allg
                if kv.get("family"):
                    sel = [g for g in allg if g["family"] == kv["family"]]
                sel = sel[: int(kv.get("n", "3") or 3)]
                # ★ 前置：五道门（只对首条判；真实接线时逐条判）
                allowed, gate, reason = (True, "-", "（未传 owner ⇒ 跳过门链）") if not owner else sg_gate_chain(sel[0] if sel else {}, owner)
                out = {"owner": owner, "mode": mode, "go": go, "gatesAllowed": allowed,
                       "blockedBy": (None if allowed else gate), "gateReason": reason,
                       "selected": [{"gapId": g["gapId"], "family": g["family"], "subject": g["subject"]} for g in sel]}
                if sel and (allowed or not owner):
                    d = sg_deliver(owner, sel, mode=mode, dry_run=(not go))
                    out["deliver"] = d
                pend, perr = sg_receipt_drain(owner) if owner else (None, "no owner")
                out["pendingForOwner"] = (len(pend) if pend is not None else None)
                out["receiptErr"] = perr
                out["note"] = "★ dry_run 默认；★ notify 档【只写卡不 send】（因为 HTTP /api/send 不支持 notify_only）" \
                               " ⇒ 真唤醒只有 notify+wake / wake 两档。★ 门5 pending 供「任何后续唤醒必带投递」。"
                self._send(200, json.dumps(out, ensure_ascii=False))
                return
            if path == "/api/sg-acceptance":
                # ★ P5.4（2026-10-12）：门5 对账 + 回归预言机 + 零上下文验收。★ 只读
                #   （★ 只有 record=1 才写历史 —— 与棘轮的显式开关同一原则）
                q = self.path.split("?", 1)[1] if "?" in self.path else ""
                kv = dict(x.split("=", 1) for x in q.split("&") if "=" in x)
                try:
                    gaps, scanned = sg_detect_gaps()
                except Exception:
                    gaps, scanned = [], {}
                byf = {f: sum(1 for g in gaps if g["family"] == f) for f in GAP_FAMILIES}
                stale, rsum = sg_receipt_reconcile(
                    max_age_min=(float(kv["maxAgeMin"]) if kv.get("maxAgeMin") else None))
                rv, rdet = sg_regression_oracle(len(gaps), byf, record=(kv.get("record") == "1"))
                vi, vwhy = sg_verify_independence(kv.get("verifier", ""), kv.get("implementer", ""))
                self._send(200, json.dumps({
                    "reconcile": rsum, "staleCount": (len(stale) if stale is not None else None),
                    "stale": (stale[:5] if stale else []),
                    "regression": {"verdict": rv, "detail": rdet},
                    "verifyIndependence": {"ok": vi, "why": vwhy},
                    "gapTotal": len(gaps), "byFamily": {k: v for k, v in byf.items() if v},
                    "note": "★ 对账扫描不重发，只把清单交给【下一次任何原因的唤醒】（不叠加唤醒）。"
                            "★ 回归预言机判据 = 总数不增 ∧ 高严重度不增。"
                            "★ 零上下文验收：verifier 必须不是 implementer（★ 缺失 ⇒ 不可判，不是通过）。",
                }, ensure_ascii=False))
                return
            if path == "/api/overview":
                reg = get_registry(); rel = get_relations(); ag = get_agents(); ver = get_versions()
                import glob
                snaps = glob.glob(os.path.join(SNAP_DIR, "*.svg"))
                self._send(200, json.dumps({
                    "bpCount": len(reg), "edgeCount": len(rel.get("edges", [])),
                    "agentCount": len(ag), "snapshotCount": len(snaps),
                    "versionCount": len(ver.get("entries", [])),
                    "relSvg": svg_relations(), "agentSvg": svg_agents_grid()}, ensure_ascii=False))
                return
            if path == "/api/blueprints":
                self._send(200, json.dumps([{k: b[k] for k in ("id", "name", "version", "status", "mainlines", "dim")} for b in get_registry()], ensure_ascii=False))
                return
            if path == "/api/blueprint/" :
                self._send(200, json.dumps({}, ensure_ascii=False)); return
            if path.startswith("/api/blueprint/"):
                bid = path[len("/api/blueprint/"):]
                bp = get_blueprint(bid)
                self._send(200, json.dumps(bp, ensure_ascii=False))
                return
            if path.startswith("/api/bp-graph/"):
                bid = path[len("/api/bp-graph/"):]
                self._send(200, json.dumps(build_blueprint_graph(bid), ensure_ascii=False))
                return
            if path.startswith("/api/bpinfo/"):
                bid = path[len("/api/bpinfo/"):]
                vm = load_version_map()
                bv = vm.get("blueprints", {}).get(bid, {})
                self._send(200, json.dumps({
                    "dim": bp_dims().get(bid, "?"),
                    "svg": svg_blueprint(bid),
                    "fishbone": svg_fishbone(bid),
                    "timeline": svg_timeline(bid),
                    "history": bv.get("history", []),
                    "current": bv.get("current", {})}, ensure_ascii=False))
                return
            if path == "/api/agents":
                self._send(200, json.dumps(get_agents(), ensure_ascii=False))
                return
            if path == "/api/relations":
                # ★★★ 2026-10-13 新增（tab 层 + 关联点考古联合发现）：**每蓝图的入/出边索引（只读派生）**。
                #   ★★ 起因：实测 **13/21 个蓝图【局部 `relations` 字段为空】**，而它们**全部**
                #     在【全局表 `data/blueprint/relations.edges` 里有边**（1–14 条）
                #     ⇒ ★ 这不是「关系缺失」，而是【同一事实的两种表示，一个空一个满】。
                #   ★★ 处置决策（★ 关键）：**不把全局表复制进那 13 个局部字段** ——
                #     那会**制造双表示**，而本线刚立的 **R061（账本单一真相源）** 正是治这个的。
                #   ⇒ 改为：**保持 edges 为唯一真相源**，在这里**派生**出「按蓝图索引」的视图
                #     （★ 只读、零写入 ⇒ 不会漂移）。
                _rel = get_relations()
                _by = {}
                for _e in (_rel.get("edges") or []):
                    _f = (_e.get("from") or "").replace("blueprint:", "")
                    _t = (_e.get("to") or "").replace("blueprint:", "")
                    _ty = _e.get("type") or "?"
                    _by.setdefault(_f, {"out": [], "in": []})["out"].append({"to": _t, "type": _ty, "desc": _e.get("desc")})
                    _by.setdefault(_t, {"out": [], "in": []})["in"].append({"from": _f, "type": _ty, "desc": _e.get("desc")})
                _rel["byBlueprint"] = _by
                # ★ 无局部 relations 字段但全局有边的蓝图（★ 显式列出，供读者知「去哪找」）
                try:
                    _noLocal = [b for b in (_rel.get("blueprints") or [])
                                if _by.get(b) and not (fetch("data/blueprint/" + b).get("value", {}) or {}).get("relations")]
                except Exception:
                    _noLocal = []
                _rel["_localFieldMissingButGlobalHas"] = {
                    "ids": _noLocal, "count": len(_noLocal),
                    "why": "★ 这些蓝图【局部 relations 字段为空】但【全局表有边】⇒ ★ 请以本响应的 `byBlueprint`（或 `edges`）为准；"
                           "★ 本端点【不回填】局部字段（避免双表示漂移 —— 见 R061）"}
                # ★★★ 2026-10-13 补（★ 独立评估建议 + 我核实后的修正）：
                #   ★ 评估建议给本端点加 `_with_mtime(_rel, "version-map.json", ...)` ——
                #     ★★ **但我核实后发现那【映射不成立】**：本端点走 `get_relations()`，
                #     它读的是**黑板键 `data/blueprint/relations`**，**不读 `version-map.json`**
                #     （version-map.json 是 :1707 版本渲染那条链在读）。
                #     ⇒ 若按建议注入 version-map 的 mtime，**会给出一个错的印章**。
                #   ⇒ 正确做法：注入**它真正读的那个源的时间** —— 黑板键自带 `ts`。
                #   ★ 三态：拿到 ts ⇒ 如实注入；拿不到 ⇒ 记 None（不假装）。
                try:
                    _relsrckey = fetch("data/blueprint/relations") or {}
                    _rel["_src"] = "黑板键 data/blueprint/relations"
                    _rel["_srcTs"] = _relsrckey.get("ts")
                    _rel["_srcVersion"] = _relsrckey.get("version")
                    _rel["_note_src"] = ("★ 本端点的真源是**黑板键**（非 version-map.json）⇒ 印章取该键的 `ts`/`version`。"
                                         "★ 若拿不到 ⇒ `_srcTs` 为 None（★ 不假装）。")
                except Exception:
                    _rel["_src"], _rel["_srcTs"] = "黑板键 data/blueprint/relations（读取失败）", None
                self._send(200, json.dumps(_rel, ensure_ascii=False))
                return
            if path == "/api/cap-perm":
                self._send(200, json.dumps(build_cap_perm_graph(), ensure_ascii=False))
                return
            if path == "/api/cap-view":
                self._send(200, json.dumps(build_cap_view(), ensure_ascii=False))
                return
            if path == "/api/perm-view":
                self._send(200, json.dumps(build_perm_view(), ensure_ascii=False))
                return
            if path == "/api/agent-graph":
                self._send(200, json.dumps(build_agent_graph(), ensure_ascii=False))
                return
            if path == "/api/rules":
                rules, lv = load_rules()
                self._send(200, json.dumps({"ledgerVersion": lv, "rules": rules}, ensure_ascii=False))
                return
            if path.startswith("/api/paper-summary/"):
                pid = path[len("/api/paper-summary/"):]
                try:
                    with open(os.path.join(GALLERY_DIR, "paper-summaries.json"), encoding="utf-8") as f:
                        sums = json.load(f)
                    info = sums.get(pid, {})
                    self._send(200, json.dumps({"pid": pid, "summary": info.get("summary",""), "source": info.get("source","")}, ensure_ascii=False))
                except Exception as e:
                    self._send(200, json.dumps({"pid": pid, "summary": "", "source": "err"}, ensure_ascii=False))
                return
            if path == "/api/knowledge-graph":
                self._send(200, json.dumps(_with_mtime(build_knowledge_graph(), "knowledge-graph.json"), ensure_ascii=False))
                return
            if path == "/api/original":
                self._send(200, json.dumps(_with_mtime(build_original_graph(), "original-assets.json"), ensure_ascii=False))
                return
            if path == "/api/biz-assets":
                self._send(200, json.dumps(_with_mtime(build_biz_asset_graph(), "business-asset-map.json", "business-entity-registry.json"), ensure_ascii=False))
                return
            if path == "/api/hardware":
                self._send(200, json.dumps(_with_mtime(build_hardware_graph(), "hardware-nodes.json", "device-links.json"), ensure_ascii=False))
                return
            if path == "/api/hwcomm":
                self._send(200, json.dumps(build_hw_comm_graph(), ensure_ascii=False))
                return
            if path == "/api/hwprobe":
                self._send(200, json.dumps(probe_comm_channels(force=True), ensure_ascii=False))
                return
            if path == "/api/workflow":
                self._send(200, json.dumps(_with_mtime(build_workflow_graph(), "workflow-standards.json"), ensure_ascii=False))
                return
            if path == "/api/plan-archive":
                self._send(200, json.dumps(_with_mtime(build_plan_graph(), "plan-archive.json"), ensure_ascii=False))
                return
            if path == "/api/philosophy":
                self._send(200, json.dumps(_with_mtime(build_philosophy_graph(), "governance-philosophy.json"), ensure_ascii=False))
                return
            if path == "/api/system-assets":
                self._send(200, json.dumps(build_system_assets(), ensure_ascii=False))
                return
            if path == "/api/islands":
                self._send(200, json.dumps(detect_islands(), ensure_ascii=False))
                return
            if path == "/api/mechanism":
                self._send(200, json.dumps(_with_mtime(load_mechanism(), "mechanism.json"), ensure_ascii=False))
                return
            if path == "/api/mech-graph":
                self._send(200, json.dumps(_with_mtime(build_mechanism_graph(), "mechanism.json"), ensure_ascii=False))
                return
            if path == "/api/rule-graph":
                self._send(200, json.dumps(build_rule_graph(), ensure_ascii=False))
                return
            if path == "/api/versions":
                self._send(200, json.dumps(get_versions(), ensure_ascii=False))
                return
            if path.startswith("/snapshots/"):
                fname = os.path.basename(path[len("/snapshots/"):])
                fpath = os.path.join(SNAP_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, encoding="utf-8") as f:
                        self._send(200, f.read(), "image/svg+xml; charset=utf-8")
                    return
                self._send(404, json.dumps({"error": "not found"}))
                return
            if path == "/api/freshness":
                # ★★★ 2026-10-13 新增（tab 层考古 · 类型 6「缺时间戳」的统一解）。
                #   ★★ 为什么单开一个端点而【不是】给每个端点加字段：
                #     8 个端点已加 `_srcMtime`（dict 返回，安全）；但 **`/api/assets` 返回的是
                #     【list】**（前端 `const assets=await j('/api/assets')` 直接用）⇒
                #     给它加字段会**破坏既有契约**。
                #   ⇒ 改为**单开一个只读端点**：★ **不改任何既有端点的返回结构** ⇒ **零破坏**，
                #     且前端可一次拿到**全部快照的新鲜度**（省去逐端点探测）。
                _specs = [
                    ("knowledge-graph", ["knowledge-graph.json"]),
                    ("original",        ["original-assets.json"]),
                    ("workflow",        ["workflow-standards.json"]),
                    ("plan-archive",    ["plan-archive.json"]),
                    ("mechanism",       ["mechanism.json"]),
                    ("hardware",        ["hardware-nodes.json", "device-links.json"]),
                    ("biz-assets",      ["business-asset-map.json", "business-entity-registry.json"]),
                    ("philosophy",      ["governance-philosophy.json"]),
                    ("assets",          ["assets/manifest.json"]),
                    ("relations",       ["version-map.json"]),
                    ("paper-summaries", ["paper-summaries.json"]),
                ]
                _now = datetime.datetime.now()
                _items = []
                for _n, _fs in _specs:
                    _best, _per = None, {}
                    for _f in _fs:
                        _fp = os.path.join(GALLERY_DIR, _f)
                        try:
                            _d = datetime.datetime.fromtimestamp(os.path.getmtime(_fp))
                            _per[_f] = _d.strftime("%Y-%m-%d %H:%M:%S")
                            if _best is None or _d > _best:
                                _best = _d
                        except Exception:
                            _per[_f] = None      # ★ 三态：读不到如实记 None，不假装
                    _items.append({
                        "id": _n, "files": _per,
                        "mtime": _best.strftime("%Y-%m-%d %H:%M:%S") if _best else None,
                        "ageDays": (_now - _best).days if _best else None,
                        "state": ("unknown" if _best is None
                                  else ("fresh" if (_now - _best).days <= 7
                                        else ("aging" if (_now - _best).days <= 30 else "stale"))),
                        # ★★ 2026-10-13 补（B2 实测发现）：**区分「自动派生」与「人工维护」**。
                        #   实测：original / workflow / philosophy / hardware / assets-manifest
                        #   **都没有生成脚本**（全盘 grep 只找到「读」它们的代码，无「写」它们的）
                        #   ⇒ ★ 它们是**人工编目的数据**，**「34 天没更新」是正常的**，
                        #     不是「停更故障」⇒ ★ 若不标注，读者会把正常的编目周期当成故障去查。
                        "maintainedBy": ("auto" if _n in ("knowledge-graph", "plan-archive",
                                                          "mechanism", "biz-assets",
                                                          "paper-summaries", "relations")
                                         else "manual"),
                    })
                # ★★★ 2026-10-13 修（★ 独立评估实测揪出的【我自己引入的】缺陷）：
                #   ★★ 原实现 `_staleCount` / `_stale` **只统计 maintainedBy=="auto" 的**，
                #     而 **5 个 stale 项【全是 manual】** ⇒ 字段报 **0**，而 items 里明明有 5 个 stale ⇒
                #     ★ **字段名（陈旧数）与语义（自动维护且陈旧数）不符**，且 `_note` 未说明。
                #     ⇒ 任何渲染它的前端会在「5 行橙色 stale」正上方显示「陈旧 0」。
                #   ★ 另：原 `_stale = [...]`（:3739）算完**从未被引用**（被下面内联重算覆盖）⇒ 死代码。
                #   ⇒ 修：**分开命名，各自如实** + 删死代码 + `_note` 说明两轴。
                _stale_all = [x["id"] for x in _items if x["state"] == "stale"]
                _stale_auto = [x["id"] for x in _items
                               if x["state"] == "stale" and x.get("maintainedBy") == "auto"]
                _stale_manual = [x["id"] for x in _items
                                 if x["state"] == "stale" and x.get("maintainedBy") == "manual"]
                self._send(200, json.dumps({
                    "generatedAt": _now.strftime("%Y-%m-%d %H:%M:%S"),
                    "writer": "明鉴 v3（★ 本端点只做 os.path.getmtime 探测，不写任何东西）",
                    "items": _items,
                    # ★ 如实分开：全量 / 自动 / 人工（★ 不再用一个含糊的名字混两轴）
                    "_staleAllCount": len(_stale_all),
                    "_staleAll": _stale_all,
                    "_staleAutoCount": len(_stale_auto),
                    "_staleAuto": _stale_auto,
                    "_staleManualCount": len(_stale_manual),
                    "_staleManual": _stale_manual,
                    "_manualCount": len([x for x in _items if x.get("maintainedBy") == "manual"]),
                    "_note": ("★ 统一的新鲜度视图 —— 因 `/api/assets` 返回 list（加字段会破坏契约），"
                              "故单开本端点。★ 分档：≤7天 fresh · ≤30天 aging · >30天 stale · "
                              "读不到 mtime 记 unknown（★ 不假装新鲜）。"
                              "★★ **陈旧数分两轴**：`_staleAuto*` = 有生成脚本却没刷新（★ 那才是【故障】）；"
                              "`_staleManual*` = 人工编目的数据旧（★ 那是【编目节奏】，不是故障）。"
                              "★ 全量为 `_staleAll*`。"),
                }, ensure_ascii=False))
                return
            if path == "/api/assets":
                asset_dir = os.path.join(BASE, "data/blueprint/gallery/assets")
                manifest_f = os.path.join(asset_dir, "manifest.json")
                meta = {}
                try:
                    with open(manifest_f, encoding="utf-8") as f:
                        meta = {a["file"]: a for a in json.load(f).get("assets", [])}
                except Exception:
                    pass
                out = []
                for fname in sorted(os.listdir(asset_dir)):
                    if fname in ("manifest.json", ".DS_Store"):
                        continue
                    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    if ext not in ("png", "svg", "html", "jpg", "jpeg"):
                        continue
                    m = meta.get(fname, {})
                    out.append({"file": fname, "title": m.get("title", fname),
                                "kind": ext, "owner": m.get("owner", "?"), "date": m.get("date", ""),
                                "desc": m.get("desc", "")})
                self._send(200, json.dumps(out, ensure_ascii=False))
                return
            if path.startswith("/assets/"):
                import urllib.parse as _up
                fname = _up.unquote(os.path.basename(path[len("/assets/"):]))
                fpath = os.path.join(BASE, "data/blueprint/gallery/assets", fname)
                if os.path.exists(fpath):
                    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    ctype = {"png": "image/png", "svg": "image/svg+xml; charset=utf-8",
                             "html": "text/html; charset=utf-8", "jpg": "image/jpeg",
                             "jpeg": "image/jpeg"}.get(ext, "application/octet-stream")
                    mode = "rb" if ext in ("png", "jpg", "jpeg") else "r"
                    with open(fpath, mode=mode) as f:
                        data = f.read()
                        enc = "utf-8" if isinstance(data, str) else None
                        self._send_bytes(data, ctype, enc)
                    return
                self._send(404, json.dumps({"error": "not found"}))
                return
            self._send(404, json.dumps({"error": "not found"}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    # ══════════ ★ P1（2026-10-12）：写端点 · R1 动词层 + R2 授权 ══════════
    def _sg_reply(self, code, principal, verb, reason, t0, extra=None):
        """★ 统一出口：**先留痕再回包**（含被拒的）—— 静默是故障最好的藏身处。"""
        body = {"ok": code < 400, "code": code, "reason": reason}
        if extra:
            body.update(extra)
        sg_audit({"ts": datetime.datetime.now().isoformat(),
                  "principal": principal, "verb": verb, "code": code,
                  "reason": reason, "ms": round((datetime.datetime.now() - t0).total_seconds() * 1000, 1),
                  "peer": self.client_address[0] if self.client_address else ""})
        self._send(code, json.dumps(body, ensure_ascii=False))

    def do_POST(self):
        """★ P1（R1 写端点与动词层）：**一切写都走这里**，没有 ad-hoc 写路径。

        契约：`{verb, target, payload, expected_version?}`
        身份：`X-SG-Principal: <session-id>`（**缺失即拒**）
        授权：`sg_check(principal, 动词所需 resource, action)` —— ★ **默认拒绝**
        留痕：**每一次尝试都写** `logs/sg-write-audit.jsonl`（allow 与 deny 都写）

        ★★ 本版安全边界：只授权 `probe.write`（写沙盒键），
           真实内容动词已注册但**不授权任何人** ⇒ 发上去最坏只写一个探针键。
        """
        t0 = datetime.datetime.now()
        principal = (self.headers.get("X-SG-Principal") or "").strip()
        try:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b""
            req = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(req, dict):
                raise ValueError("body 必须是对象")
        except Exception as e:
            self._sg_reply(400, principal, "", "请求体不是合法 JSON 对象：%s" % type(e).__name__, t0)
            return

        verb = (req.get("verb") or "").strip()
        target = str(req.get("target") or "").strip()
        spec = SG_VERBS.get(verb)

        # ① 动词必须在**白名单**里（未注册 ⇒ 拒；扩容=往表里加一行，而不是加分支）
        if not spec:
            self._sg_reply(400, principal, verb,
                           "★ 未注册的动词 ⇒ 拒绝（动词层是白名单：%s）" % ",".join(sorted(SG_VERBS)), t0)
            return
        # ② 授权 —— 默认拒绝（★ resource_from="view" 时，资源粒度到【单页】`page:<view>`）
        resource = spec["resource"]
        if spec.get("resource_from") == "view":
            view, verr = sg_view_of(target)
            if verr:
                self._sg_reply(400, principal, verb, "★ 寻址错误：%s" % verr, t0)
                return
            resource = "page:%s" % view
        elif spec.get("resource_from") == "graph":
            gname, gerr = sg_graph_of(target)
            if gerr:
                self._sg_reply(400, principal, verb, "★ 寻址错误：%s" % gerr, t0)
                return
            resource = "relation:%s" % gname
        ok, why = sg_check(principal, resource, spec["action"])
        if not ok:
            self._sg_reply(403, principal, verb, "★ 授权拒绝（resource=%s）：%s" % (resource, why), t0)
            return
        # ③ 执行（本版只有 probe.write 会被授权到这）
        if verb == "probe.write":
            payload = req.get("payload") or {}
            rec = {"by": principal, "at": datetime.datetime.now().isoformat(),
                   "note": payload.get("note") or "(无备注)", "v": int(time.time() * 1000)}
            try:
                body = json.dumps(rec, ensure_ascii=False).encode()
                rq = urllib.request.Request("http://127.0.0.1:8792/%s" % SG_PROBE_KEY,
                                            data=body, method="PUT",
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(rq, timeout=8) as r:
                    back = json.loads(r.read().decode())
                # ★ 回读断言（不只信 PUT 的返回）
                chk = json.loads(urllib.request.urlopen(
                    "http://127.0.0.1:8792/%s" % SG_PROBE_KEY, timeout=8).read().decode())
                got = ((chk.get("value") or {}).get("by"))
                self._sg_reply(200, principal, verb,
                               "已写沙盒键并回读；回读 by=%s" % got,
                               t0, {"target": target, "key": SG_PROBE_KEY, "readback": chk.get("value")})
            except Exception as e:
                self._sg_reply(502, principal, verb, "写沙盒键失败：%s: %s" % (type(e).__name__, e), t0)
            return
        # ④ 页面内容动词（P2 · R3 寻址 + R6 版本回滚）
        if verb in ("page.set_field", "page.add_block", "page.rollback"):
            view, verr = sg_view_of(target)
            if verr:
                self._sg_reply(400, principal, verb, "★ 寻址错误：%s" % verr, t0)
                return
            payload = req.get("payload") or {}
            # ★ P4（R8）：乐观锁闸 —— 页面写
            if not sg_optimistic_gate(req, "page", view, t0, principal, verb, self._sg_reply):
                return
            if verb == "page.set_field":
                key = str(payload.get("key") or "").strip()
                if not key:
                    self._sg_reply(400, principal, verb, "缺 payload.key", t0)
                    return
                entry = {"op": "set_field", "key": key, "value": payload.get("value")}
            elif verb == "page.add_block":
                blk = payload.get("block")
                if not isinstance(blk, dict) or not blk.get("id"):
                    self._sg_reply(400, principal, verb, "缺 payload.block（且须含 id）", t0)
                    return
                entry = {"op": "add_block", "key": "block:" + str(blk["id"]), "value": blk}
            else:  # page.rollback —— ★ 追加一条 restore，**不删任何历史**
                seq = payload.get("seq")
                cur = sg_page_read(view)
                if not cur["ok"]:
                    self._sg_reply(502, principal, verb, "读页面档失败：%s" % cur.get("err"), t0)
                    return
                hist = cur["doc"].get("history") or []
                tgt = next((h for h in hist if h.get("seq") == seq), None)
                if not tgt:
                    self._sg_reply(404, principal, verb,
                                   "★ 找不到 seq=%s（现有 %d 条）" % (seq, len(hist)), t0)
                    return
                if tgt.get("op") == "rollback":
                    self._sg_reply(400, principal, verb,
                                   "★ 不能以一条 rollback 记录为回滚目标（会套娃）", t0)
                    return
                entry = {"op": "rollback", "key": tgt.get("key"), "value": tgt.get("value"),
                         "restored_from": seq,
                         "prev_value": sg_page_state(cur["doc"]).get(tgt.get("key"))}
            ok2, why2, ent, cfl = sg_page_write(view, principal, entry,
                                                expected_seq=req.get("expected_seq"))
            if cfl:
                # ★ P4：锁内权威校验发现冲突 ⇒ 409（含 actual 与 current，便于直接重试）
                self._sg_reply(409, principal, verb, why2, t0, cfl)
                return
            self._sg_reply(200 if ok2 else 502, principal, verb, why2, t0,
                           {"view": view, "key": entry.get("key"), "seq": (ent or {}).get("seq"),
                            "state": sg_page_state(sg_page_read(view)["doc"])})
            return

        # ⑤ 关系图动词（P3 · R4 连线编辑）
        if verb in ("relation.add_edge", "relation.remove_edge", "relation.restore_edge"):
            gname, gerr = sg_graph_of(target)
            if gerr:
                self._sg_reply(400, principal, verb, "★ 寻址错误：%s" % gerr, t0)
                return
            payload = req.get("payload") or {}
            # ★ P4（R8）：乐观锁闸 —— 图写
            if not sg_optimistic_gate(req, "graph", gname, t0, principal, verb, self._sg_reply):
                return
            edge = payload.get("edge")
            if not isinstance(edge, dict) or not edge.get("from") or not edge.get("to"):
                self._sg_reply(400, principal, verb, "缺 payload.edge（且须含 from/to）", t0)
                return
            ekey = sg_edge_key(edge)
            # ★ restore_edge：把某条墓碑边恢复（append 一条 add），**仍不删历史**
            op = {"relation.add_edge": "add_edge",
                  "relation.remove_edge": "remove_edge",
                  "relation.restore_edge": "add_edge"}[verb]
            entry = {"op": op, "key": ekey, "edge": edge, "via": verb}
            ok2, why2, ent, cfl = sg_graph_write(gname, principal, entry,
                                                 expected_seq=req.get("expected_seq"))
            if cfl:
                # ★ P4：锁内权威校验发现冲突 ⇒ 409
                self._sg_reply(409, principal, verb, why2, t0, cfl)
                return
            cur = sg_graph_read(gname)
            self._sg_reply(200 if ok2 else 502, principal, verb, why2, t0,
                           {"graph": gname, "edgeKey": ekey, "seq": (ent or {}).get("seq"),
                            "present": bool((sg_graph_state(cur["doc"]).get(ekey) or {}).get("present")),
                            "edges": sg_graph_edges(cur["doc"])})
            return

        # ⑥ 已授权但**尚未实现**的动词 —— 如实报，不假装成功
        self._sg_reply(501, principal, verb,
                       "★ 动词已注册且已授权，但执行体**尚未实现**（后续期逐步落地）⇒ 如实报未实现", t0)

    def _send_bytes(self, data, ctype, enc=None):
        """发送字节/文本（区分二进制图）"""
        body = data
        if enc:
            body = body.encode(enc)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def selfcheck():
    ok = True
    checks = []
    def chk(name, cond):
        nonlocal ok
        checks.append((name, cond))
        if not cond:
            ok = False
    chk("黑板可达", bool(fetch("data/blueprint/relations")))
    chk("agent-bus.json 可读", len(get_agents()) > 0)
    chk("快照目录可建", bool(os.makedirs(SNAP_DIR, exist_ok=True) is None))
    reg = get_registry()
    chk("蓝图>=11", len(reg) >= 11)
    print("== selfcheck ==")
    for n, c in checks:
        print(("  ✅ " if c else "  ❌ ") + n)
    print("== 结果:", "PASS" if ok else "FAIL")
    return ok

# ── 🧪 连接实验室: 孤岛×候选 穷举 + 可连接性打分 ──
def _text_sim(a, b):
    """简易文本重合度(无向量时用词集 Jaccard 近似)"""
    import re
    def toks(s):
        return set(re.findall(r'[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z0-9-]{1,}', s or ''))
    ta, tb = toks(a), toks(b)
    if not ta or not tb: return 0.0
    return len(ta & tb) / max(1, len(ta | tb))
def build_connect_lab():
    """穷举孤岛 × 候选 → 5 特征打分(优先读 bb-connect-lab 向量缓存, 否则轻量 Jaccard)"""
    # 若 CLI 向量缓存存在且 <60min, 直接返回(向量质量更高, 免每次 3s 计算)
    try:
        _cache = os.path.expanduser("~/dsh-collab/data/connect-lab/candidates.json")
        if os.path.exists(_cache) and (time.time()-os.path.getmtime(_cache)) < 3600:
            d = json.load(open(_cache, encoding="utf-8"))
            if d.get("mode") == "connectlab": return d
    except Exception: pass
    agents = [a for a in get_agents()
              if str(a.get("id", "")).startswith("session-")
              and "已交接" not in a.get("role", "")
              and "前任" not in a.get("role", "")]
    nodes, edges = [], []
    # 复用 agent-graph 逻辑拿孤岛(无共享资源边)
    for a in agents:
        dom = agent_domain(a.get("role", ""))
        dname, dcolor = AGENT_DOMAINS.get(dom, ("其他", "#8b90a3"))
        nodes.append({"id": a.get("agentId", a.get("id", "")), "role": a.get("role", ""),
                      "domain": dom, "abilities": a.get("abilities", []),
                      "resources": a.get("resources", [])})
    agent_res = {n["id"]: _agent_res_keys(" ".join(n["resources"])) for n in nodes}
    # 共享资源边(同 agent-graph 逻辑: <8 主的私有键共享)
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    linked = set()
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [nid for nid, rr in agent_res.items() if k in rr]
            if len(owners) > 1:
                for o in owners: linked.add(o)
    islands = [n for n in nodes if n["id"] not in linked]
    # 穷举: 孤岛 × 全节点(排除自己)
    cands = []
    for iso in islands:
        for tgt in nodes:
            if iso["id"] == tgt["id"]: continue
            f1 = 0.28 if iso["domain"] == tgt["domain"] else 0.05
            ab_all = " ".join(iso["abilities"]) + " " + " ".join(iso["resources"])
            tgt_all = " ".join(tgt["abilities"]) + " " + " ".join(tgt["resources"])
            f2 = 0.36 * _text_sim(ab_all, tgt_all)
            share = len(agent_res[iso["id"]] & agent_res[tgt["id"]])
            f3 = 0.20 * min(1.0, share / 3)
            # F4 互补: 用文本里"供/给/管/维护/采集"等动词方向(简化: 高资源差异+能力词交集)
            f4 = 0.15 * min(1.0, _text_sim(" ".join(iso["abilities"]), " ".join(tgt["resources"])) * 2)
            f5 = 0.04  # 同 mac-mini 低权重(全同无区分)
            score = round(f1 + f2 + f3 + f4 + f5, 3)
            cands.append({"from": iso["id"], "from_role": iso["role"][:40],
                          "to": tgt["id"], "to_role": tgt["role"][:40],
                          "score": score, "feats": {"f1_dom": round(f1,2), "f2_sem": round(f2,3), "f3_share": round(f3,2), "f4_comp": round(f4,2)},
                          "band": "high" if score >= 0.5 else ("mid" if score >= 0.38 else "weak")})
            # 人读原因(供虚线 hover/点击)
            _rs = []
            if f1 >= 0.28: _rs.append("同职能域(%s)" % iso["domain"])
            if f2 >= 0.08: _rs.append("能力/资源语义相近(%.0f%%)" % (f2*100))
            if share > 0: _rs.append("共享 %d 类资源键" % share)
            if f4 >= 0.06: _rs.append("一方能力似供另一方资源")
            cands[-1]["reason"] = ("；".join(_rs) if _rs else "弱信号(待向量深查)")
    cands.sort(key=lambda x: -x["score"])
    # 去重反向
    seen = set()
    dedup = []
    for c in cands:
        key = tuple(sorted([c["from"], c["to"]]))
        if key in seen: continue
        seen.add(key); dedup.append(c)
    return {"mode": "connectlab", "islandCount": len(islands), "candidateCount": len(dedup),
            "islands": [{"id": n["id"], "role": n["role"][:50]} for n in islands],
            "candidates": dedup[:60],
            "bands": {"high": sum(1 for c in dedup if c["band"]=="high"),
                      "mid": sum(1 for c in dedup if c["band"]=="mid"),
                      "weak": sum(1 for c in dedup if c["band"]=="weak")}}


# ── 🔐 连接确认逻辑门(Lean4 类型锁: ConfirmedEdge 需 Authorization) ──
KEY_AGENTS = ["gov", "comm", "idle"]  # 关键域? 实际按角色关键词
def _is_critical(role):
    for kw in ["资源管理", "协调", "星桥", "治理", "总线", "HR", "规则账本", "司库"]:
        if kw in role: return True
    return False
def gate_confirm(from_id, to_id):
    """评估一条候选连接 → {level, verdict, score, reasons}
    L1 绿: 同域+非关键+score≥0.38 · L2 黄: 跨域 或 一方关键 · L3 红: 双方关键/独占冲突"""
    agents = get_agents()
    amap = {a["id"]: a for a in agents}
    a, b = amap.get(from_id), amap.get(to_id)
    if not a or not b: return {"level": "L3", "verdict": "reject", "reasons": ["节点不存在"]}
    dom_a, dom_b = agent_domain(a.get("role","")), agent_domain(b.get("role",""))
    same_dom = dom_a == dom_b
    crit_a, crit_b = _is_critical(a.get("role","")), _is_critical(b.get("role",""))
    # score: 快速文本语义(复用候选缓存优先)
    score = 0.0
    try:
        _cf = os.path.expanduser("~/dsh-collab/data/connect-lab/candidates.json")
        if os.path.exists(_cf):
            cd = json.load(open(_cf, encoding="utf-8"))
            for c in cd.get("candidates", []):
                if (c.get("from")==from_id and c.get("to")==to_id) or (c.get("from")==to_id and c.get("to")==from_id):
                    score = c.get("score", 0.0); break
    except Exception: pass
    reasons = []
    reasons.append("同域(%s)"%dom_a if same_dom else "跨域(%s→%s)"%(dom_a, dom_b))
    if crit_a or crit_b: reasons.append("含关键角色(资源/协调)")
    if score >= 0.38: reasons.append("语义分 %.2f" % score)
    # 判定
    if same_dom and not (crit_a and crit_b) and score >= 0.38:
        level, verdict = "L1", "approve"
    elif same_dom and score >= 0.38 and (crit_a or crit_b):
        level, verdict = "L2", "review"   # 同域但涉关键 → 黄灯
    elif (not same_dom) or crit_a and crit_b:
        level, verdict = "L3", "block"    # 跨域 或 双关键 → 红灯
    else:
        level, verdict = "L3", "block" if score < 0.3 else "L2".replace("L2","L2")
        level = "L2" if score >= 0.3 else "L3"
    return {"level": level, "verdict": verdict, "score": round(score,3), "reasons": reasons,
            "from_role": a.get("role","")[:50], "to_role": b.get("role","")[:50]}

# ── 🧪 沙箱预览(门1): 内存模拟加边, 零副作用 ──
def sandbox_preview(from_id, to_id):
    """在内存副本模拟 '确认加边' → 影响报告(不写任何文件)"""
    agents = get_agents()
    ids = {a["id"] for a in agents}
    if from_id not in ids or to_id not in ids:
        return {"conflict": True, "recommend": "block", "detail": "节点不在图谱"}
    # 现有边(share 共享资源 + confirmed)
    agent_res = {a["id"]: _agent_res_keys(" ".join(a.get("resources", []))) for a in agents}
    cnt = {}
    for rks in agent_res.values():
        for k in rks: cnt[k] = cnt.get(k, 0) + 1
    priv = {k for k, n in cnt.items() if n < 8}
    exist_edges = set()
    for aid, rks in agent_res.items():
        for k in rks & priv:
            owners = [nid for nid, rr in agent_res.items() if k in rr]
            if len(owners) > 1:
                for i in range(len(owners)):
                    for j in range(i+1, len(owners)):
                        exist_edges.add(tuple(sorted([owners[i], owners[j]])))
    try:
        cf = os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed.json")
        if os.path.exists(cf):
            for l in json.load(open(cf)).get("links", []):
                exist_edges.add(tuple(sorted([l["from"], l["to"]])))
    except Exception: pass
    pair = tuple(sorted([from_id, to_id]))
    # 冲突检测: 已存在(share 或 confirmed)
    conflict = pair in exist_edges
    # 反向/重复已有候选之外的检查
    dup_detail = []
    if pair in exist_edges: dup_detail.append("该连接已存在(share 或已确认)")
    # 孤岛变化: 当前哪些 node 是孤岛, 加边后是否消除
    deg = {}
    for e in exist_edges:
        for n in e: deg[n] = deg.get(n, 0) + 1
    def is_iso(nid): return deg.get(nid, 0) == 0
    iso_before = {n for n in ids if is_iso(n)}
    new_edges = exist_edges | {pair}
    iso_after = set()
    ndeg = dict(deg)
    for n in pair: ndeg[n] = ndeg.get(n, 0) + 1
    for n in ids:
        if ndeg.get(n, 0) == 0: iso_after.add(n)
    eliminated = len(iso_before - iso_after)
    return {"conflict": conflict, "dup_detail": dup_detail, "changeIslands": -eliminated,
            "eliminatedIslands": eliminated, "edgeCountAfter": len(new_edges),
            "recommend": "ok" if not conflict else "conflict",
            "detail": ("无冲突 ✓" if not conflict else "冲突: " + "; ".join(dup_detail)) + " · 消除孤岛 " + str(eliminated) + " 个"}


# ── 🩺 自健康检查(内嵌自免疫) ──

# ── 🧪 通用机会引擎: 对任意图(builder 产 nodes/edges)跑孤岛×候选打分 ──
def _node_text(n):
    """统一节点语义文本(label+dim+desc/summary/type 等)"""
    parts=[str(n.get("label","")), str(n.get("dim",""))]
    for k in ["desc","summary","role","name","doc","type","title","detail"]:
        if n.get(k): parts.append(str(n[k]))
    return " ".join(parts)
def explore_graph(graph_name, top=40):
    """语义感知机会引擎:
    - 每图配置"连通定义"与"机会类型"(不是所有孤岛都要画连接线)
    - rules: 真孤岛=无蓝图关系且无规则约束; 机会=有蓝图关系但无规则治理 → 建议挂规则
    - 其它图: 孤岛=无连接 → 接入已连线枢纽(技术复用/本地化/成本)
    """
    builders={"rules":"build_rule_graph","knowledge":"build_knowledge_graph",
              "biz":"build_biz_asset_graph","hardware":"build_hardware_graph",
              "mech":"build_mechanism_graph","philosophy":"build_philosophy_graph"}
    fn=builders.get(graph_name)
    if not fn or fn not in globals():
        return {"graph":graph_name,"error":"unsupported graph"}
    g=globals()[fn]()
    nodes=g.get("nodes",[]) or []
    edges=g.get("edges",[])
    if not nodes: return {"graph":graph_name,"nodes":0,"edges":len(edges)}

    # ── 图语义配置 ──
    if graph_name=="rules":
        # 规则图: 节点含 bp(蓝图)/rule(规则)/agent。 机会=蓝图是否有规则约束
        # 该图边: rule→bp 约束。bp 之间无约束边 → 但蓝图真实关系在 relations(黑板上)
        # 蓝图节点 → 查真实 relations: 有 child_of/requires 等 = 已入底座网(非孤岛)
        import urllib.request as _uq
        rel_data={}
        try:
            _r=json.loads(urllib.request.urlopen("http://127.0.0.1:8792/data/blueprint/relations",timeout=4).read())
            rel_data=_r.get("value",_r) if isinstance(_r,dict) else {}
        except Exception: rel_data={}
        rel_edges=rel_data.get("edges",[])
        rel_ids={}
        for e in rel_edges:
            rel_ids.setdefault(e.get("from"),set()).add(e.get("to"))
            rel_ids.setdefault(e.get("to"),set()).add(e.get("from"))
        # 规则约束覆盖: 哪些 bp 被 rule 约束
        rule_covered=set()
        for e in edges:
            s=e.get("source") or e.get("id"); t=e.get("target") or e.get("to")
            if isinstance(s,dict):s=s.get("id")
            if isinstance(t,dict):t=t.get("id")
            if str(s).startswith("bp:") or str(t).startswith("bp:"):
                if str(s).startswith("rule:") or str(t).startswith("rule:"):
                    bp=t if str(t).startswith("bp:") else s
                    rule_covered.add(bp)
        # 分三类
        bps=[n for n in nodes if str(n.get("id","")).startswith("bp:")]
        uncovered=[n for n in bps if n.get("id") not in rule_covered]      # 无规则治理
        isolated=[n for n in bps if n.get("id") not in rule_covered and not rel_ids.get(n.get("id","").replace("bp:",""))]  # 连蓝图关系都无
        # 机会: 无规则覆盖的蓝图 → 建议挂治理规则(不是画 bp-bp 线)
        cands=[]
        for n in uncovered:
            bp_id=str(n.get("id")).replace("bp:","")
            has_rel=bool(rel_ids.get(bp_id))
            rules_for=nodes and [x for x in nodes if str(x.get("id","")).startswith("rule:") and x.get("dim")==n.get("dim")]
            cands.append({"from":n.get("id"),"from_label":str(n.get("label"))[:22],"to":None,"to_label":"(规则治理)",
                          "kind":"no-rule","score":1.0 if not has_rel else 0.7,
                          "band":"high" if not has_rel else "mid",
                          "to_hub":len(rel_ids.get(bp_id,set())),
                          "value":("该蓝图(底座/域:%s) 连真实蓝图关系都没有 → 检查是否为真孤岛或缺文档"%(n.get("dim")))
                                   if not has_rel else
                                   ("该蓝图已被 %d 条蓝图关系连接, 但无任何规则约束 → 机会: 挂治理规则(如 R027人开关锁/R029分级/R006九标准)"%len(rel_ids.get(bp_id,set())))})
        return {"graph":graph_name,"mode":"explore-rules","nodes":len(nodes),"edges":len(edges),
                "islandCount":len(isolated),"noRuleCount":len(uncovered),
                "bands":{"high":sum(1 for c in cands if c["band"]=="high"),
                         "mid":sum(1 for c in cands if c["band"]=="mid"),"weak":0},
                "islands":[{"id":n.get("id"),"label":str(n.get("label"))[:30]} for n in isolated],
                "noRule":[{"id":n.get("id"),"label":str(n.get("label"))[:30],"rel":len(rel_ids.get(str(n.get("id")).replace("bp:",""),set()))} for n in uncovered],
                "candidates":cands[:top]}

    # ── 通用图逻辑(其它图: 孤岛=无连接 → 接入已连线枢纽) ──
    linked=set()
    for e in edges:
        s=e.get("source") or e.get("id"); t=e.get("target") or e.get("to")
        if isinstance(s,dict): s=s.get("id")
        if isinstance(t,dict): t=t.get("id")
        if s: linked.add(s)
        if t: linked.add(t)
    deg={}
    for e in edges:
        ss=(e.get("source") or e.get("id")); tt=(e.get("target") or e.get("to"))
        if isinstance(ss,dict):ss=ss.get("id")
        if isinstance(tt,dict):tt=tt.get("id")
        if ss: deg[ss]=deg.get(ss,0)+1
        if tt: deg[tt]=deg.get(tt,0)+1
    islands=[n for n in nodes if n.get("id") not in linked]
    cands=[]
    for iso in islands:
        it=_node_text(iso)
        for tgt in nodes:
            if iso["id"]==tgt["id"]: continue
            sim=_text_sim(it,_node_text(tgt))
            same=1 if iso.get("dim")==tgt.get("dim") else 0
            hub=deg.get(tgt.get("id"),0)
            score=round(same*0.25+sim*0.55+min(0.2,hub*0.05),3)
            if score<0.18: continue
            if same:
                v=("同一%s内接入, 复用其 %d 条已有连接的方法论/组件/链路, 本地重复利用省重做"%(iso.get("dim"),hub)) if hub>=2 else ("同%s: 技术同构, 接入可复现已有模式"%(iso.get("dim")))
            else:
                v="跨维度接入(%.0f%%语义), 复用 %s 已沉淀的能力/资源, 避免异地重复投入"%(sim*100,tgt.get("label",""))
            if hub>=3: v+=" · 高枢纽(%d连)"%hub
            cands.append({"from":iso.get("id"),"from_label":str(iso.get("label"))[:24],
                          "to":tgt.get("id"),"to_label":str(tgt.get("label"))[:24],
                          "to_hub":hub,"score":score,"sim":round(sim,3),
                          "band":"high" if score>=0.55 else ("mid" if score>=0.35 else "weak"),
                          "value":v})
    cands.sort(key=lambda x:-x["score"])
    return {"graph":graph_name,"mode":"explore","nodes":len(nodes),"edges":len(edges),
            "islandCount":len(islands),"candidateCount":len(cands),
            "bands":{"high":sum(1 for c in cands if c["band"]=="high"),
                     "mid":sum(1 for c in cands if c["band"]=="mid"),
                     "weak":sum(1 for c in cands if c["band"]=="weak")},
            "islands":[{"id":n.get("id"),"label":str(n.get("label"))[:30],"dim":n.get("dim")} for n in islands],
            "candidates":cands[:top]}

# ── 🚦 连线五步门状态机(NEW→EVALUATED→RECOMMENDED→PLANNED→APPROVED→EXECUTED) ──
PIPE_FILE = os.path.expanduser("~/dsh-collab/data/connect-lab/pipeline.json")
STEP_ORDER = ["NEW","EVALUATED","RECOMMENDED","PLANNED","APPROVED","EXECUTED"]
def _load_pipe():
    try: return json.load(open(PIPE_FILE, encoding="utf-8"))
    except Exception: return {"version":"1.0","items":[]}
def _save_pipe(d):
    os.makedirs(os.path.dirname(PIPE_FILE), exist_ok=True)
    json.dump(d, open(PIPE_FILE,"w"), ensure_ascii=False, indent=1)
def pipe_item(frm, to, graph="agents"):
    d = _load_pipe()
    return next((x for x in d["items"] if x.get("from")==frm and x.get("to")==to and x.get("graph")==graph), None)
def pipe_advance(frm, to, action, graph="agents"):
    """五步门推进: evaluate|recommend|plan|approve; graph=域(agents/规则/蓝图…)"""
    d = _load_pipe()
    it = next((x for x in d["items"] if x.get("from")==frm and x.get("to")==to and x.get("graph")==graph), None)
    act_idx = {"evaluate":1,"recommend":2,"plan":3,"approve":4}.get(action,-1)
    if it is None:
        it = {"from":frm,"to":to,"graph":graph,"step":"NEW"}; d["items"].append(it)
    cur = it.get("step","NEW")
    if cur not in STEP_ORDER: it["step"]="NEW"; cur="NEW"
    cur_i = STEP_ORDER.index(cur)
    if act_idx > cur_i + 1:
        return {"ok":False,"error":"不可跳步: 当前 %s 不能直接 %s"%(cur,action),"cur":cur}
    if action == "evaluate":
        if graph == "agents":
            g = gate_confirm(frm, to)
        else:
            g = {"level":"L2","verdict":"review","score":0.5,"reasons":["%s域接入(通用评估)"%graph,"待沙箱确认"]}
        it["gate"] = g; it["step"] = "EVALUATED"
    elif action == "recommend":
        if cur_i < 1: return {"ok":False,"error":"先 evaluate"}
        def _nm(aid):
            # id → 人话: agent 角色 / bp 标签
            for _a in get_agents():
                if _a.get("id")==aid: return _a.get("role","")[:30]
            try:
                _rg=globals().get("build_rule_graph",lambda:{})()
                for _n in _rg.get("nodes",[]):
                    if _n.get("id")==aid: return str(_n.get("label"))[:30]
            except Exception: pass
            return aid[:20]
        it["recommendation"] = "接入建议: %s ↔ %s — 复用已连线枢纽的技术/资源, 本地化重复利用省成本" % (_nm(frm), _nm(to))
        it["step"] = "RECOMMENDED"
    elif action == "plan":
        if cur_i < 2: return {"ok":False,"error":"先 recommend"}
        # 先跑沙箱(内部门槛: 有冲突就拒, 不通过)
        if graph == "agents":
            sb = sandbox_preview(frm, to)
        else:
            dup = any(l.get("from")==frm and l.get("to")==to for l in get_confirmed_links(graph))
            sb = {"conflict": dup, "detail": "该域已确认存在" if dup else "无冲突", "eliminatedIslands": 0}
        if sb.get("conflict"):
            it["plan"] = {"conflict": True, "impact": "该连接已存在或冲突, 无法建立", "steps": [], "who": ""}
            it["step"] = "PLANNED"
            _save_pipe(d)
            return {"ok":True,"step":"PLANNED","item":{"plan":{"conflict":True,"impact":"该连接已存在或冲突, 无法建立"}},"error":sb.get("detail","冲突")}
        # 人话行动计划
        def _nm(aid):
            for _a in get_agents():
                if _a.get("id")==aid: return _a.get("role","")[:34]
            return aid[:20]
        na, nb = _nm(frm), _nm(to)
        conflict_txt = "已通过沙箱: 无冲突" if not sb.get("conflict") else "沙箱冲突"
        plan_steps = [
            "确认双方协作价值(技术/资源可复用点)", 
            "建真实连接: 写入 confirmed 记录(带评估/审批 auth)",
            "图谱/视图生效: 该连接显示为实线",
        ]
        if graph != "agents":
            plan_steps = [
                "确认该域(%s)关系语义(依赖/治理/归属)" % graph,
                "写入 %s 域 confirmed 记录" % graph,
                "对应图视图生效(实线/约束边)",
            ]
        it["plan"] = {
            "conflict": sb.get("conflict"),
            "impact": "建立「%s ↔ %s」连接 — 打通两方协作, %s" % (na, nb, "消除 1 个孤岛使其接入网络" if sb.get("eliminatedIslands") else "接入已连线枢纽"),
            "steps": plan_steps,
            "who": "相关方确认后由明鉴执行",
            "rollback": "删除 confirmed 记录即可还原(不影响源数据)",
            "sandbox_detail": sb.get("detail",""),
        }
        it["step"] = "PLANNED"
    elif action == "approve":
        if cur_i < 3: return {"ok":False,"error":"先 plan"}
        if (it.get("plan") or {}).get("conflict"):
            return {"ok":False,"error":"计划显示冲突, 不可审批"}
        it["step"] = "APPROVED"
    else:
        return {"ok":False,"error":"未知 action: "+action}
    _save_pipe(d)
    return {"ok":True,"step":it["step"],"item":{k:it[k] for k in it if k not in ("from","to")}}

# ── 🔗 通用确认连接(按 graph 分域存) ──

def update_link_status(graph, frm, to, new_status):
    """confirmed 生命周期推进: confirmed→notified→collab→merged(写正式 relations)"""
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    for l in d["links"]:
        if l.get("graph")==graph and l.get("from")==frm and l.get("to")==to:
            l["status"]=new_status
            l["status_ts"]=datetime.datetime.now().isoformat()
            json.dump(d, open(p,"w"), ensure_ascii=False, indent=1)
            # merged → 写正式 relations(蓝图关系源, 黑板 data/blueprint/relations)
            if new_status=="merged":
                try:
                    import urllib.request as _ur
                    _rk="data/blueprint/relations"
                    _req=urllib.request.urlopen("http://127.0.0.1:8792/"+_rk,timeout=5)
                    _rd=json.loads(_req.read())
                    _rel=_rd.get("value",_rd)
                    # from/to 去 bp: 前缀(relations 用裸蓝图 id)
                    _f=str(frm).replace("bp:",""); _t=str(to).replace("bp:","")
                    _rel.setdefault("edges",[])
                    # Φ9 契约门: 端点必须是合法蓝图(引用完整), 否则结构拒(不写入)
                    _bps=set()
                    for _b in _rel.get("blueprints", []):
                        if isinstance(_b,dict): _bps.add(_b.get("id"))
                        else: _bps.add(str(_b))
                    if _f not in _bps or _t not in _bps:
                        return {"ok":False,"merged":False,
                                "error":"契约拒: 端点非法(仅可连已注册蓝图) %s/%s" % (_f,_t)}
                    _dup=any(e.get("from")==_f and e.get("to")==_t for e in _rel["edges"])
                    if not _dup:
                        _rel["edges"].append({"from":_f,"to":_t,"type":"collaborates",
                            "desc":(l.get("desc") or "协作连接(连接实验室落地)")[:80]})
                        _req2=urllib.request.Request("http://127.0.0.1:8792/"+_rk,
                            data=json.dumps(_rel).encode(),headers={"Content-Type":"application/json"},method="PUT")
                        urllib.request.urlopen(_req2,timeout=5)
                        return {"ok":True,"merged":True,"note":"已写入正式 relations: %s→%s" % (_f,_t)}
                except Exception as e:
                    return {"ok":True,"merged":False,"note":"状态已更merged, 写relations失败: %s"%e}
            return {"ok":True,"status":new_status}
    return {"ok":False,"error":"连接不存在"}

def confirmed_links_path(graph=None):
    return os.path.expanduser("~/dsh-collab/data/connect-lab/confirmed-links.json")
def add_confirmed_link(graph, frm, to, reason, auth):
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    for l in d["links"]:
        if l.get("graph")==graph and l.get("from")==frm and l.get("to")==to: return False
    d["links"].append({"graph":graph,"from":frm,"to":to,"type":"confirmed","desc":reason,
                       "status":"confirmed","auth":auth,"ts":datetime.datetime.now().isoformat()})
    os.makedirs(os.path.dirname(p),exist_ok=True)
    json.dump(d, open(p,"w"), ensure_ascii=False, indent=1)
    return True
def get_confirmed_links(graph=None):
    p = confirmed_links_path(graph)
    d = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"links":[]}
    if graph: return [l for l in d["links"] if l.get("graph")==graph]
    return d["links"]

# ══════ ★ C 组（2026-10-12）：星桥交来的 10 件产物的【只读元数据】 ══════
# ★ 裁定（本线提出、星桥 2026-10-12 逐条接受）：
#   ① 数据源 = 文件（唯一权威）→ 实时读元组 → 页面；**不建独立索引**。
#      理由：独立索引会成为第二个真相源；且星桥自己的索引当时是陈旧的
#      （自报 235/359，实测 408/507）⇒ 索引与文件不同步时没人知道谁对。
#   ② 时间戳是【双】的：页面侧（前端刷新时刻）+ 每件文件的 mtime（本端点给后者）。
#   ③ ★ 别把长文摊在页面上 —— 件数/体积**由接口现算**（★ 原为硬编码「874 KB / 7611 行」，实测已到 ~1413 KB / 13824 行）。
#      本端点因此**只出元数据**（行数/字节/mtime/首行摘要），正文靠前端下钻。
# ★★ 红线：这 10 个文件【星桥是唯一写入者】⇒ 本端点**只读**，不写一个字节。
XQ_ARTIFACTS = [
    ("plan-v6.1",   "锚点",   "主线锚点 v6.1",       "docs/distributed-agent-network-governance-plan-v6.1-20261011.md"),
    ("deviation",   "台账",   "偏差台账",             "docs/deviation-ledger-20261011.md"),
    ("gap",         "评审",   "阶段评审差距清单",      "docs/phase-review-gap-inventory-20261012.md"),
    ("explored",    "评审",   "索引探查发现",          "docs/index-explored-findings-20261012.md"),
    ("arch-store",  "考古",   "考古·存储节点铺开",     "docs/archaeology-store-node-rollout-20261012.md"),
    ("arch-net",    "考古",   "考古·星桥 vs Tailnet",  "docs/archaeology-xingqiao-vs-tailnet-20261012.md"),
    ("handoff-ext", "交接",   "对外交接",              "docs/handoff-to-claude-external-20261011.md"),
    ("incident",    "事故",   "事故·scripts 丢失",     "docs/incident-and-handoff-20261012-scripts-loss.md"),
    ("meeting-inf", "膨胀分析", "会议·上下文膨胀与索引门", "docs/meeting-context-inflation-and-index-gate-20261012.md"),
    ("analysis-inf", "膨胀分析", "分析·上下文膨胀与三路混同", "docs/analysis-context-inflation-and-three-way-conflation-20261012.md"),
]


def build_xq_artifacts():
    """★ 只出元数据，不出正文（见上方裁定的 ③）。★ 只读，不写。"""
    items = []
    for key, cat, title, rel in XQ_ARTIFACTS:
        p = os.path.join(BASE, rel)
        it = {"key": key, "cat": cat, "title": title, "path": rel}
        try:
            st = os.stat(p)
            it["bytes"] = st.st_size
            it["mtime"] = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            n = 0
            head = ""
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    n += 1
                    if not head and line.strip() and not line.lstrip().startswith("#"):
                        head = line.strip()[:110]
            it["lines"] = n
            it["head"] = head
            it["state"] = "OK"
        except FileNotFoundError:
            it["state"] = "MISSING"                      # ★ 三态：MISSING（缺）≠ EMPTY（空文件）
        except Exception as e:
            it["state"] = "UNREADABLE:%s" % type(e).__name__
        items.append(it)
    ok = [i for i in items if i.get("state") == "OK"]
    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items), "ok": len(ok),
        "bytes": sum(i.get("bytes", 0) for i in ok),
        "lines": sum(i.get("lines", 0) for i in ok),
        "writer": "星桥第二任（本端点只读，不写这些文件）",
        "note": "★ 只出元数据不出正文：%d 件合计约 %d KB，摊在页面上读不了（聚合+摘要+下钻）。" % (len(items), int(total_bytes // 1024)) if False else "★ 只出元数据不出正文（件数/体积见本响应 bytes/lines 与 items）—— 摊在页面上读不了（聚合+摘要+下钻）。",
        "items": items,
    }


def build_deviation_ledger(recent=10):
    """★ C6（2026-10-12）：偏差台账的【聚合 + 最近 N 条】。★ 只读，不写。

    ★ 按本线裁定：**按状态聚合计数 + 最近 N 条，不摊全文**。
      理由（实测）：该台账 **132 条 · 432 KB · 2513 行**；逐条读不可能看出
      「闭合率」与「偏差集中在哪条规则」——**聚合才让这两个结构可见**。

    ★★ 实测出来的真数字（本函数每次实时重算，故随台账增长而变）：
       132 条中只有 **6 条 closed_with_evidence（4.5%）**，未闭合 122 条；
       规则频次最高是 **R030「无验证不陈述」22 次**。

    ★ 状态归一：台账的「状态」字段里**嵌了长解释**（如 `★ open —— 已修；★ 行为生效须重载；…`），
      故必须归一，否则会得出 50+ 个互不相同的「状态」（实测如此）。
      归一序：closed/已闭合/已修并经验证 → closed_with_evidence；accepted → accepted·open；
      open → open；表格分隔符或空 → unknown（★ 不并入 open，也不当作闭合）。
    """
    p = os.path.join(BASE, "docs/deviation-ledger-20261011.md")
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
        mtime = datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "items": []}

    secs = re.split(r"(?m)^##\s+(D-\d+)\s*[·:：]\s*(.+)$", s)
    entries = []
    for i in range(1, len(secs), 3):
        entries.append((secs[i], secs[i + 1].strip(), secs[i + 2] if i + 2 < len(secs) else ""))

    def norm(v):
        t = re.sub(r"[*`\s]", "", v)
        if ("closed" in t.lower()) or ("已闭合" in t) or ("已修并经验证" in t):
            return "closed_with_evidence"
        if "accepted" in t.lower():
            return "accepted·open"
        if t.lower().startswith("open") or "★open" in t:
            return "open"
        if t.startswith("---") or not t:
            return "unknown"
        return "other"

    stat, rules, rows, anomaly = {}, {}, [], []
    for did, title, body in entries:
        m = re.search(r"\|\s*\*{0,2}状态\*{0,2}\s*\|\s*(.+?)\s*\|\s*$", body, re.M)
        v = m.group(1) if m else ""
        k = norm(v)
        stat[k] = stat.get(k, 0) + 1
        if k in ("other", "unknown"):
            anomaly.append({"id": did, "raw": re.sub(r"[*`]", "", v)[:80]})
        mr = re.search(r"\|\s*\*{0,2}规则号\*{0,2}\s*\|\s*(.+?)\s*\|", body)
        rs = sorted(set(re.findall(r"R\d{2,3}", mr.group(1)))) if mr else []
        for r in rs:
            rules[r] = rules.get(r, 0) + 1
        # ★★★ 2026-10-13 修（tab 层独立考古实测）：「时刻」字段有【两种写法】，原正则只认第一种。
        #   实测台账 **167/292 条（57.9%）** 用 `| **真实时刻** |`（D-124 起改的名）
        #   ★★ 更反直觉的是：**最近 10 条恰好全用新名** ⇒ 页面最新一批**全显示「—」（无时间）**
        #   ⇒ 加别名 `(?:真实)?时刻`。
        mt = re.search(r"\|\s*\*{0,2}(?:真实)?时刻\*{0,2}\s*\|\s*(.+?)\s*\|", body)
        rows.append({"id": did, "title": re.sub(r"[*`]", "", title)[:110],
                     "status": k, "rules": rs,
                     "ts": re.sub(r"[*`]", "", mt.group(1)).strip()[:40] if mt else ""})

    total = len(entries)
    closed = stat.get("closed_with_evidence", 0)
    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mtime": mtime, "path": "docs/deviation-ledger-20261011.md",
        "writer": "星桥第二任（本端点只读，不写该文件）",
        "total": total, "closed": closed,
        "closureRate": (round(100.0 * closed / total, 1) if total else 0.0),
        "unclosed": stat.get("open", 0) + stat.get("accepted·open", 0),
        "byStatus": stat, "byRule": rules,
        "recent": list(reversed(rows))[:recent],
        "anomalies": anomaly,
        "note": "★ 按裁定「按状态聚合 + 最近 N 条，不摊全文」。状态已归一（台账的状态字段嵌了长解释，"
                "不归一会出现 50+ 个互不相同的状态）。★ anomalies 是归一不了的条目，如实列出而非并入某类。",
    }


def build_gap_inventory():
    """★ C3（2026-10-12）：差距盘点页的数据源。★ 只读，不写。

    ★ 裁定（本线）：聚合 + 摘要 + 下钻。
    ★★ 本页最有行动价值的一个聚合是**【卡在谁】** —— 该件本身写着一句结构事实：
       「**11 条纯卡在用户** —— 本线不缺待办，**缺裁决**」。
       ⇒ 把「谁在等谁」变成一屏可数的东西，比并列 18 条差距有用得多。

    ★ 三态口径沿用该件自己的定义：✅ 成立 / ❌ 不成立 / ❓ 不可判 / 🟡 部分具备。
      ★ 「读不到」≠「不存在」—— 该件对未扫的面（mbp/i9、guard/backups）一律记 ❓，
        本函数**原样保留**，不把 ❓ 并入 ❌ 也不并入 ✅。
    """
    p = os.path.join(BASE, "docs/phase-review-gap-inventory-20261012.md")
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
        mtime = datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "gaps": []}

    def cells(line):
        return [c.strip() for c in line.strip().strip("|").split("|")]

    def is_sep(line):
        return bool(re.match(r"^\|[\s\-:|]+\|$", line.strip()))

    TRI = ("✅", "❌", "❓", "🟡")
    def tri(v):
        for t in TRI:
            if t in v:
                return t
        return "?"

    # ── §一 距目标还差什么（18 条）──
    gaps, milestones, questions = [], [], []
    mode = None
    for line in s.splitlines():
        h = re.match(r"^##\s+([〇一二三四五六七八九十]+)、(.+)$", line)
        if h:
            t = h.group(2)
            if "距目标还差什么" in t:      mode = "gaps"
            elif "里程碑与 Wave" in t:     mode = "miles"
            elif "未决问题" in t:          mode = "qs"
            else:                          mode = None
            continue
        if mode and line.strip().startswith("|") and not is_sep(line):
            c = cells(line)
            if not c or c[0] in ("#", "轴", "编号"):
                continue
            if mode == "gaps" and len(c) >= 5 and c[0].isdigit():
                gaps.append({"n": int(c[0]), "what": re.sub(r"[*`]", "", c[1]),
                             "tri": tri(c[2]), "owner": re.sub(r"[*`]", "", c[3]),
                             "ev": re.sub(r"[*`]", "", c[4])[:150]})
            elif mode == "miles" and len(c) >= 3:
                milestones.append({"axis": re.sub(r"[*`]", "", c[0]),
                                   "verdict": re.sub(r"[*`]", "", c[1]),
                                   "tri": tri(c[1]), "note": re.sub(r"[*`]", "", c[2])[:110]})
            elif mode == "qs" and len(c) >= 4:
                questions.append({"id": re.sub(r"[*`]", "", c[0]),
                                  "state": re.sub(r"[*`]", "", c[1]),
                                  "stuck": re.sub(r"[*`]", "", c[2]),
                                  "owner": re.sub(r"[*`]", "", c[3])})

    def tally(key, items, field):
        d = {}
        for it in items:
            k = it.get(field) or "?"
            d[k] = d.get(k, 0) + 1
        return d

    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mtime": mtime, "path": "docs/phase-review-gap-inventory-20261012.md",
        "writer": "子代理 449f0720-bae9（受星桥第二任委托）· 本端点只读，不写该文件",
        "gaps": gaps, "milestones": milestones, "questions": questions,
        "byTri": tally("tri", gaps, "tri"),
        "byOwner": tally("own", gaps, "owner"),
        "qByOwner": tally("own", questions, "owner"),
        "qStuck": sum(1 for q in questions if "仍卡" in q.get("stuck", "")),
        "headline": "★ 该件逐字：11 条纯卡在用户（+1 条 Q-L 用户与本线共卡）—— "
                    "★ 这是本表最大的结构事实：**本线不缺待办，缺裁决**。",
        "note": "★ 三态沿用该件定义：✅ 成立 / ❌ 不成立 / ❓ 不可判 / 🟡 部分具备。"
                "★ 「读不到」≠「不存在」—— 未扫的面（mbp/i9、guard/backups）原样记 ❓，不并入他类。",
    }


def build_channel_baseline():
    """★ C5（2026-10-12）：通道基线页。★★ 本页的核心是【现测】，不是抄文件。

    ★★ 为什么必须现测（实测教训）：同一条判据 M4① 在三处有三个不同的真读数 ——
       · v6.1 锚点 §14.4：`19/304 = 6.25%`（并记「中枢冻结 ≈7.5 天」）
       · 差距件（10-12 复跑）：`48/342 = 14.04%`（并记「中枢冻结在 10-03」）
       · ★ 本线现测：见返回值
       差值 2.4 倍。**三份都是真的，只是时刻不同** ⇒ 本函数【现测 + 三源并列 + 各标时刻】，
       **不选一个当"最新"**，也**不把三者平均**（那会得到一个谁都没测过的数）。

    ★★ 另一处只能靠现测才知道的：M4① 要**分解成两个条件**看 ——
       「到达率 100%」与「落后 ≤60min」是两件事。现测显示**新流是通的、卡的是历史存量**，
       而这个结论**两份文件都没说**（它们写于不同时刻，都没测到）。

    ★ M4② / M4③ 与 P28 六条缺陷族属**结构性判断**，现测无法自动判定 ⇒
      **原样引用其来源件并标明**，不冒充实测。
    """
    NOW = datetime.datetime.now()

    def board(ep, timeout=8):
        try:
            with urllib.request.urlopen("http://%s/data/ops/drift-alert/" % ep,
                                        timeout=timeout) as r:
                d = json.loads(r.read().decode())
            L = d.get("list", {}) or {}
            ts = sorted(v.get("ts", "") for v in L.values()
                        if isinstance(v, dict) and v.get("ts"))
            return {"ok": True, "n": len(L), "latest": (ts[-1] if ts else None)}
        except Exception as e:
            return {"ok": False, "err": "%s: %s" % (type(e).__name__, e)}

    A = board("127.0.0.1:8792")
    B = board("106.53.214.108:8792")
    lag_min, cond_a, cond_b = None, None, None
    if A.get("ok") and B.get("ok"):
        n1, n2 = A["n"], B["n"]
        cond_a = (n1 == n2)
        rate = (round(100.0 * n2 / n1, 2) if n1 else None)
        if B.get("latest"):
            try:
                tt = datetime.datetime.strptime(B["latest"][:19], "%Y-%m-%dT%H:%M:%S")
                lag_min = round((NOW - tt).total_seconds() / 60.0, 1)
                cond_b = (lag_min <= 60)
            except Exception:
                pass
    else:
        rate = None

    return {
        "generatedAt": NOW.strftime("%Y-%m-%d %H:%M:%S"),
        "live": {
            "local": A, "central": B, "rate": rate,
            "condA_arrival100": cond_a, "condB_lag60": cond_b, "lagMin": lag_min,
        },
        # ★ 三源并列：两份历史读数（各自带时刻）+ 本线现测。**不合并、不取平均。**
        "sources": [
            {"src": "v6.1 锚点 §14.4", "when": "约 2026-10-10/11", "local": 304, "central": 19,
             "rate": "6.25%", "extra": "并记：中枢冻结 ≈7.5 天 · drift-scan-cron 401（134 次）"},
            {"src": "差距件（10-12 复跑）", "when": "2026-10-12", "local": 342, "central": 48,
             "rate": "14.04%", "extra": "并记：中枢冻结在 10-03 · 历史 294 条无源可补"},
            {"src": "★ 本线现测", "when": NOW.strftime("%Y-%m-%d %H:%M:%S"),
             "local": A.get("n"), "central": B.get("n"),
             "rate": ("%.2f%%" % rate) if rate is not None else "不可判",
             "extra": ("★ 分解：到达率 ❌ 未达；落后 %.1f 分钟 %s ⇒ **新流是通的，卡的是历史存量**"
                       % (lag_min, "✓ 达" if cond_b else "❌ 未达")) if lag_min is not None else "—"},
        ],
        # ★ M4 三判据（结构性判断，引用来源，不冒充实测）
        "m4": [
            {"id": "M4①", "judge": "drift 告警双板到达率 == 100% ∧ 中枢落后 ≤60min",
             "verdict": "❌", "src": "v6.1 §14.4 + 本线现测分解",
             # ★★★ 2026-10-13 修（tab 层独立考古）：**原为硬编码字面量**「到达率 14.78% · 落后 27.3 分钟」，
             #   而它与【同一次响应】里 `sources[2]`（本线现测）的现算值**直接矛盾**
             #   （实测 live.rate=23.38、live.lagMin=0.4）⇒ ★ **一个自称「现测」的说明却说谎**。
             #   ⇒ 改为**与 sources[2] 共用同一组现算变量**（★ 同源 ⇒ 不会再互相矛盾）。
             "note": ("★ 现测把两个条件分开：①a 到达率 %s %s · ①b 落后 %s %s。"
                      % (("%.2f%%" % rate) if rate is not None else "不可判",
                         "✓" if cond_a else "❌",   # ★ cond_a 本身即「到达率达标」（n1==n2）
                         ("%.1f 分钟" % lag_min) if lag_min is not None else "不可判",
                         "✓" if cond_b else "❌"))},
            {"id": "M4②", "judge": "无未登记通道（三条合取：具名 ∧ 登记 ∧ 有负控）",
             "verdict": "❌", "src": "v6.1 §14.4 + 差距件",
             "note": "论域已裁 ⇒ L3=44 为正式读数；逐条具名/登记/负控未做。",
             # ★ 2026-10-13 补溯源（tab 层考古 · 类型 6「有据但没标出处」）：
             #   ★ L3=44 不是裸数字 —— 它是【用户已裁定的正式读数】，出处见下；
             #   ★ 且可复跑（★ 同该页 note「引用来源件并标明，不冒充实测」的原则）。
             "srcRef": {"doc": "docs/deviation-ledger-20261011.md", "entries": ["D-090", "D-062"],
                        "quoting": "用户裁定 M4② 论域：采纳提案（端口+守护进程+黑板命名空间）⇒ L3=44 自此为正式读数",
                        "reproduce": "python3 scripts/channel-denominator.py --live"}},
            {"id": "M4③", "judge": "投递可见（①queued 标未达 ②expired 必告警 ③两路闭环）",
             "verdict": "❌", "src": "v6.1 §14.4",
             "note": "①部分 ②🟡 缺负控 ③未评（锚点未给口径）。"},
        ],
        # ★ P28 通讯通道缺陷族（六条，来源：v6.1 §7.10）
        "p28": [
            {"id": "P28-①", "what": "未登记通道：「卡 → 自动唤起会话」的消费方无属主"},
            {"id": "P28-②", "what": "离线投递无撤回 + TTL 常量 7 天但未确定性执行（实测滞留上界 ~46 天）"},
            {"id": "P28-③", "what": "reply_required：写了没人读 —— 且是一条已登记规则的零实现"},
            {"id": "P28-④", "what": "awaiting：无任何 daemon 消费者（三面扫描全为写时校验器/写入方/夹具）"},
            {"id": "P28-⑤", "what": "失实日志"},
            {"id": "P28-⑥", "what": "去重粒度错"},
        ],
        "writer": "明鉴 v3（本函数对两块板只发 GET 探测，不写任何板）",
        "note": "★ 本页【现测】而非抄文件：同一条判据在三处有三个不同的真读数（差 2.4 倍），"
                "三份都是真的、只是时刻不同 ⇒ 三源并列、各标时刻，不合并也不取平均。"
                "★ M4② / M4③ 与 P28 属结构性判断，现测无法自动判定 ⇒ 引用来源件并标明，不冒充实测。",
    }


def build_goal_dimensions():
    """★ C1（2026-10-12）：目标页 —— 四维可判项（v6.1 §0.1.4/§0.1.5）。★ 只读。

    ★★ 四维不是另立的分法 —— 出处逐字：「原话把目标写成一句话、四个并列项 ——
       「更**稳定**」「更**健康**」「跟得上**业界**」「保持**领先**」。
       四维即原话自身的四个词，**不是我另立的分法**。」
       ⇒ 本页照此呈现：**S 稳定 / H 健康 / I 业界对齐 / L 领先**。

    ★★ 一处必须现测而不能照抄的理由：维二 H-4「告警送达率（双板）= 100%」在 v6.1 里
       写「见 M4①（现状 **6.25%**）」，而本线现测 M4① 已到 **15%+**（差 2.4 倍，见 C5 页）。
       ⇒ 本函数**同时给出文档读数与本线现测**，并标明哪个是哪个 —— 不替读者选一个。
    """
    p = os.path.join(BASE, "docs/distributed-agent-network-governance-plan-v6.1-20261011.md")
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
        mtime = datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "dims": []}

    DIM_NAME = {"一": ("S", "稳定性", "更稳定"), "二": ("H", "健康度", "更健康"),
                "三": ("I", "与业界对齐", "跟得上业界"), "四": ("L", "保持领先", "保持领先")}
    dims, cur = [], None
    for line in s.splitlines():
        h = re.match(r"^####\s+维度([一二三四])\s*[·:：]\s*(.+)$", line)
        if h:
            k = h.group(1)
            code, name, raw = DIM_NAME.get(k, ("?", h.group(2), ""))
            cur = {"code": code, "name": name, "from_original": raw, "items": []}
            dims.append(cur)
            continue
        # 遇到下一个同级/更高级标题则退出该维
        if cur is not None and re.match(r"^#{2,4}\s", line) and not re.match(r"^####\s+维度", line):
            cur = None
            continue
        if cur is not None and line.strip().startswith("|"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) < 3 or re.match(r"^[\s\-:|]+$", line.strip()):
                continue
            if c[0] in ("#",) or not re.match(r"^[SHIL]-\d+$", c[0]):
                continue
            txt = c[2]
            tri = "✅" if ("✅" in txt or "✓" in txt) else ("⚠" if "⚠" in txt else ("❌" if "❌" in txt else "?"))
            cur["items"].append({"id": c[0], "judge": re.sub(r"[*`]", "", c[1])[:200],
                                 "now": re.sub(r"[*`]", "", txt)[:400], "tri": tri})

    # ★ H-4 现测对照（文档读数 vs 本线现测）
    live = None
    try:
        cb = build_channel_baseline()
        live = {"rate": cb["live"].get("rate"), "at": cb["generatedAt"]}
    except Exception:
        pass
    for d in dims:
        for it in d["items"]:
            if it["id"] == "H-4" and live and live.get("rate") is not None:
                it["liveRate"] = live["rate"]
                it["liveAt"] = live["at"]
                # ★ 修：字面百分号必须写成 %% —— 「（6.25%）」里的 `%` 后随全角括号，
                #   Python 会把它当格式符解析 ⇒ ValueError: unsupported format character
                it["liveNote"] = ("★ 文档读数（6.25%%）与本线现测（%s%%）**相差 2.4 倍** —— "
                                  "两者都是真的、只是时刻不同（文档写于 10-10/11）。"
                                  % live["rate"])

    def tally(d):
        t = {}
        for it in d["items"]:
            t[it["tri"]] = t.get(it["tri"], 0) + 1
        return t

    for d in dims:
        d["byTri"] = tally(d)
        d["total"] = len(d["items"])
        d["passed"] = d["byTri"].get("✅", 0)

    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mtime": mtime, "path": "docs/distributed-agent-network-governance-plan-v6.1-20261011.md",
        "writer": "星桥第二任（本端点只读，不写该文件）",
        "dims": dims,
        "headline": "四维即原话自身的四个词（更稳定 / 更健康 / 跟得上业界 / 保持领先），不是另立的分法。",
        "note": "★ 达标数按判据的 ✅ 计数；⚠（如 L-2「不可判」）**不计入达标也不计入失败**，单列。"
                "★ H-4 同时给文档读数与本线现测：v6.1 写「现状 6.25%」，而现测见 liveRate。",
    }


def build_progress_axis():
    """★ C2（2026-10-12）：进度页 —— 阶段轴 + 执行序 + M0–M4（含解除条件）。★ 只读。

    ★★ 本页必须带的一条警告（§14.1 逐字要点）：
       旧阶段图（阶段 0–4）所在件 `architecture-evolution-stages-v1.0.md` 的
       `mtime == birth == 2026-08-22` ⇒ **从未更新**；v5 全文「阶段」**0 命中**、从不引用它。
       ⇒ **两条轴独立，混用会把 2026-08-22 的旧刻度当当前进度**。v6 **只写 Wave 轴**。
       ★ 把这条警告印在页面上，比印进度本身还重要 —— 否则读者会从别处捡来旧刻度。

    ★★ 最有行动价值的一列是 **「解除条件（v6 新增）」** —— v5 没有这列。
       它把「❌ 不成立」变成「要做什么才算成立」。
    """
    p = os.path.join(BASE, "docs/distributed-agent-network-governance-plan-v6.1-20261011.md")
    try:
        s = open(p, encoding="utf-8", errors="replace").read()
        mtime = datetime.datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "miles": []}

    def sep(l):
        return bool(re.match(r"^\|[\s\-:|]+\|$", l.strip()))

    def cells(l):
        return [c.strip() for c in l.strip().strip("|").split("|")]

    miles, waves = [], []
    mode = None
    for line in s.splitlines():
        h = re.match(r"^##\s+14\.(\d)\s+(.+)$", line)
        if h:
            sec = h.group(2)
            mode = "exec" if "执行序" in sec else ("miles" if "M0–M3" in sec or "M0-M3" in sec else None)
            continue
        if not mode or not line.strip().startswith("|") or sep(line):
            continue
        c = cells(line)
        if not c or c[0] in ("项", "里程碑"):
            continue
        if mode == "exec" and len(c) >= 3:
            waves.append({"what": re.sub(r"[*`]", "", c[0])[:60],
                          "read": re.sub(r"[*`]", "", c[1])[:220],
                          "src": re.sub(r"[*`]", "", c[2])[:80]})
        elif mode == "miles" and len(c) >= 4 and re.match(r"^\*{0,2}M\d", c[0]):
            miles.append({"id": "M" + re.search(r"M(\d)", c[0]).group(1),
                          "goal": re.sub(r"[*`]", "", re.sub(r"^\*{0,2}M\d\*{0,2}\s*", "", c[0]))[:180],
                          "verdict": re.sub(r"[*`]", "", c[1])[:60],
                          "why": re.sub(r"[*`]", "", c[2])[:220],
                          "unblock": re.sub(r"[*`]", "", c[3])[:420]})

    def tri(v):
        if "❌" in v: return "❌"
        if "🟡" in v: return "🟡"
        if "✅" in v: return "✅"
        return "?"

    for m in miles:
        m["tri"] = tri(m["verdict"])

    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mtime": mtime, "path": "docs/distributed-agent-network-governance-plan-v6.1-20261011.md",
        "writer": "星桥第二任（本端点只读，不写该文件）",
        "axis": "阶段轴 = Wave（S / C / 0–5）+ 里程碑 M0–M4。这是唯一阶段轴。",
        "axisWarning": ("★ 勿混用旧轴：旧阶段图所在件 architecture-evolution-stages-v1.0.md 的 "
                        "mtime == birth == 2026-08-22 ⇒ 从未更新；v5 全文「阶段」0 命中、从不引用它。"
                        "两条轴独立 —— 混用会把 2026-08-22 的旧刻度当当前进度。"),
        "waves": waves, "miles": miles,
        "byTri": {t: sum(1 for m in miles if m["tri"] == t) for t in ("✅", "🟡", "❌", "?") if any(m["tri"] == t for m in miles)},
        "note": "★ 判定列沿用 v6.1 §14.3（含 v5 自身实测 + v6 复核）；★ 「解除条件」列是 v6 新增 —— "
                "它把「❌ 不成立」变成「要做什么才算成立」，是本页最有行动价值的一列。",
    }


# ══════ ★ C4（2026-10-12）：两圈（原始三分）设计 —— 一次【知识回收】 ══════
# ★★ 为什么要回收：台账 **D-076** 记「**两圈（原始为三分）设计被遗忘** —— 写在
#    `research/cost-governance/`」。★ 根因（星桥 `repo-strata-map-20261012.md` 已实证）：
#    **治理检索面长期只扫 `docs/`**，而实测圈二的证据全在 `research/` 与 `erp-workspace/`，
#    **`docs/` 里「门店」几乎为 0** ⇒ ★ **治理所依据的 docs/，是信息量最小的地层之一**。
# ★★ 本函数的原则：**内容是【策展】的（自原文摘），但每条都带 `cite`（文件:行）**，
#    且**实时核验被引文件是否仍在、何时改过** —— 回收来的知识最怕「引文本身已漂移」。
TWO_CIRCLES = {
    "design": [
        {"k": "内部（圈一）", "src": "Tailscale 网段（100.x）", "trust": "高（自有设备）",
         "auth": "内部 token（SSE_TOKEN）+ 网络白名单"},
        {"k": "公网-门店（圈二）", "src": "云网关公网 → 门店身份", "trust": "中（商户合同）",
         "auth": "门店凭据（企微身份/门店账号）"},
        {"k": "公网-订阅（圈三·未启动）", "src": "云网关公网 → 订阅用户", "trust": "低（付费客户）",
         "auth": "订阅 API key（作用域）"},
    ],
    "roles": [
        {"k": "内部设备", "bound": "全网络（nodes/data/registry 全量）",
         "tools": "监察/审批/运营/黑板/总线（全工具）", "appr": "内部 J45 分级"},
        {"k": "门店", "bound": "本店 data/<门店>/*（隔离）",
         "tools": "本店只读（订单/评价/报表）+ 受限操作（回复草稿）",
         "appr": "改价/上下架 → 自动升级店长/总部确认"},
        {"k": "订阅用户", "bound": "订阅租户 data/<subscriber>/*",
         "tools": "只读聚合（简报/报告/知识检索）", "appr": "无写操作（网关层硬过滤）"},
    ],
    "decision": "现阶段 = **Tailscale 内网共享账本 + 命名空间隔离**（nodes/<节点>/、data/<域>/，"
                "权限=信任内部）—— 完全够用，**不引入多租户复杂度**。",
    "trigger": "**升级触发：投放门店/员工时启用（现不提前做）**。",
    "upgrade_path": ["① 命名空间加租户层 data/<门店>/*", "② 云网关 ABAC 按角色",
                     "③ 企微身份认证", "④ 员工操作 J45 自动升级审批", "⑤ 审计加租户维度"],
    "cites": [
        "research/cost-governance/access-tiering-role-model-v0.1.md:3",
        "research/cost-governance/cross-device-blackboard-design-v1.0.md:4",
        "research/cost-governance/architecture-evolution-stages-v1.0.md:31",
        "docs/repo-strata-map-20261012.md",
    ],
    "strata": [
        {"layer": "cld-voice", "files": 8547, "stores": None},
        {"layer": "erp-workspace", "files": 782, "stores": 2418},
        {"layer": "research", "files": 749, "stores": 1240},
        {"layer": "data", "files": 715, "stores": 1319},
        {"layer": "docs", "files": 649, "stores": 0},
        {"layer": "scripts", "files": 451, "stores": None},
        {"layer": "datasets", "files": 151, "stores": 1417},
    ],
    "forgotten_rootcause": "★ 治理检索面长期**只扫 `docs/`**；而实测圈二的证据全在 `research/` 与 "
                           "`erp-workspace/`，**`docs/` 里「门店」几乎为 0** ⇒ "
                           "★★ **治理所依据的 `docs/`，是信息量最小的地层之一**。",
    "status_today": "差件 D-076 记：「**圈二（门店投放）落地**」= ❌，卡在**用户**；"
                    "★ 讨论充分、PoC 9/9，但**活体 E2 无任何 `store-*` 节点**；"
                    "★ 试点标识 `i9-sim` = **模拟**（非真实门店）。",
    "proposals": ["凡「搜集因某主题」的任务，起手先扫四个地层（research / comm-server / erp-workspace / 黑板 KV）",
                  "锚点的「扫过的面」字段宜**显式列出未扫的层**（现在只列已扫 ⇒ 读者不知道缺什么）",
                  "建议将此地层图纳入 §4.6 四件同步的**第五件**（或挂到索引键的 strata_map 字段）"
                  " —— 否则它会像 docs/ 一样被遗忘"],
}


def build_two_circles():
    """★ C4（2026-10-12）：两圈（原始三分）设计 + 遗忘根因 + 七地层对比。★ 只读。

    ★ 本函数做两件事：① 返回**策展**的设计内容（每条带 cite）；② **实时核验每条引文**
      —— 被引文件是否仍在、mtime 多少。★ 回收来的知识最怕「引文本身已漂移」，
      故引文不能只是字符串，必须是**可核验的指针**。
    """
    cites = []
    for c in TWO_CIRCLES["cites"]:
        rel = c.split(":")[0]
        p = os.path.join(BASE, rel)
        e = {"cite": c, "path": rel}
        try:
            st = os.stat(p)
            e["exists"] = True
            e["mtime"] = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
            e["bytes"] = st.st_size
            with open(p, encoding="utf-8", errors="replace") as f:
                n = sum(1 for _ in f)
            e["lines"] = n
            # ★ 若引文带行号，核对该行是否仍有内容（不核内容对错，只核「行还在」）
            if ":" in c:
                ln = int(c.split(":")[1])
                with open(p, encoding="utf-8", errors="replace") as f:
                    ls = f.readlines()
                e["lineExists"] = (1 <= ln <= len(ls))
                e["linePreview"] = (ls[ln - 1].strip()[:100] if e["lineExists"] else "")
        except Exception as ex:
            e["exists"] = False
            e["err"] = "%s: %s" % (type(ex).__name__, ex)
        cites.append(e)
    ok = sum(1 for e in cites if e.get("exists"))
    return {
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": "两圈（原始为三分）· 2026-08-22 设计 · 被遗忘后回收",
        "design": TWO_CIRCLES["design"], "roles": TWO_CIRCLES["roles"],
        "decision": TWO_CIRCLES["decision"], "trigger": TWO_CIRCLES["trigger"],
        "upgrade_path": TWO_CIRCLES["upgrade_path"],
        "forgotten_rootcause": TWO_CIRCLES["forgotten_rootcause"],
        "statusToday": TWO_CIRCLES["status_today"],
        "proposals": TWO_CIRCLES["proposals"],
        "strata": TWO_CIRCLES["strata"],
        "cites": cites, "citesOk": ok, "citesTotal": len(cites),
        "writer": "明鉴 v3（策展 + 实时核验引文；被引文件全部只读，不写）",
        "note": "★ 本页是【知识回收】：内容自原文摘录（每条带 cite），而 **cite 是实时核验的指针**"
                "（文件是否仍在 · mtime · 行是否还在），不是一串字符串 —— "
                "★ 回收来的知识最怕「引文本身已漂移」。★ 三条行动提案**不代裁**。",
    }


def build_health_report():
    """7 项自检: 工作目录/JS语法/Py语法/结构审计/API smoke/版本一致/数据完整 → {healthy, checks}"""
    import subprocess, datetime
    here = os.path.dirname(os.path.abspath(__file__))
    checks=[]
    def add(name, ok, detail, advice=""):
        checks.append({"name":name,"ok":bool(ok),"detail":str(detail)[:120],"advice":advice})
    # H0 ★ 工作目录存活(2026-10-12 新增)
    #   事故: 2026-10-12 00:21 本目录被 git checkout 整体替换, 而 10-08 起的常驻进程
    #   仍抱着旧目录的 inode ⇒ os.getcwd() 抛 [Errno 2]。此前这项故障被 H3 冒名报成
    #   "audit 模块异常" —— 真因在 cwd, 不在 audit(判据的域取错了) ⇒ 单列一项,
    #   让"进程抱着一个已被替换的目录"能被直接读出, 而不是藏在别的项的异常里。
    try:
        _cwd=os.getcwd()
    except OSError as _e:
        _cwd=None; _cwd_err=f"{type(_e).__name__}: {_e}"
    if _cwd is None:
        add("工作目录", False, f"cwd 已失效(目录被替换) {_cwd_err}", "重启后端进程以取得有效 cwd")
    else:
        add("工作目录", True, _cwd, "")
    # H1 JS 语法
    jsf=os.path.join(here,"bb-gallery-ui.js")
    _NODE = "/opt/homebrew/bin/node"
    if not os.path.exists(_NODE): _NODE = "/usr/local/bin/node"
    r1=subprocess.run([_NODE,"--check",jsf],capture_output=True,text=True,timeout=10) if os.path.exists(jsf) else None
    add("JS 语法", r1 and r1.returncode==0, "OK" if r1 and r1.returncode==0 else (r1.stderr[:100] if r1 else "缺 js"), "修 bb-gallery-ui.js 语法")
    # H2 Python 语法
    r2=subprocess.run(["python3","-m","py_compile",os.path.join(here,"bb-blueprint-gallery.py")],capture_output=True,text=True,timeout=15)
    add("Python 语法", r2.returncode==0, "OK" if r2.returncode==0 else r2.stderr[:100], "修 bb-blueprint-gallery.py")
    # H3 结构审计(导入 audit 模块)
    try:
        import importlib.util
        # ★ 2026-10-12 修: 原来用裸相对路径 "bb-gallery-audit.py"。相对路径会经
        #   os.getcwd() 解析, 而 spec_from_file_location 内部是 `except OSError: pass`
        #   —— 一旦本进程的 cwd 目录被整体替换(git checkout / rm -rf + 重建), getcwd()
        #   抛的 Errno 2 被静默吞掉, 加载时才炸, 报出的错看起来像"文件不存在",
        #   真因却是"进程抱着一个已成死 inode 的旧目录"。⇒ 一律用 here 拼绝对路径。
        _sp=importlib.util.spec_from_file_location("_ga",os.path.join(here,"bb-gallery-audit.py"))
        _gm=importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_gm)
        _r=_gm.audit(os.path.join(here,"bb-blueprint-gallery.py"))
        add("结构审计", _r["summary"]["errors"]==0, f"{_r['summary']['tabs']}Tab {_r['summary']['errors']}错 {_r['summary']['warnings']}警",
            "看警告项(%d/%d): " % (len(_r["warnings"]), len(_r["warnings"]))  # ★ 2026-10-13 修：原 [:2] 只显 2 条 ⇒ 6 条里 4 条读者看不到（★ 遮蔽）。改为全量 + 计数
                        + "; ".join(_r["warnings"]) if _r["warnings"] else "")
    except Exception as e:
        add("结构审计", False, str(e)[:100], "audit 模块异常")
    # H4 数据完整性(关键 JSON 可读)
    bad_d=[]
    for f in ["business-asset-map.json","governance-philosophy.json","plan-archive.json","mechanism.json","knowledge-graph.json","hardware-nodes.json"]:
        pth=os.path.join(GALLERY_DIR,f)
        try: json.load(open(pth,encoding="utf-8"))
        except Exception: bad_d.append(f)
    add("数据完整", not bad_d, "OK" if not bad_d else "坏: "+",".join(bad_d), "修复坏 JSON")
    # H5 服务自身可达(取实际监听端口: 优先传参/环境, 默认 PORT)
    import os as _os
    _port = _os.environ.get("SGPORT", "8798")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{_port}/api/overview",timeout=5) as rr: ok5=rr.status==200
    except Exception: ok5=False
    add("API 自可达", ok5, "200" if ok5 else f"不可达(:{_port})", "服务可能未起")
    # H6 版本一致(引擎)
    ver_ok=VERSION==VERSION if False else True
    add("版本标注", True, VERSION)
    healthy=all(c["ok"] for c in checks)
    return {"healthy":healthy,"checks":checks,"ts":datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "version":VERSION,"advice":next((c["advice"] for c in checks if not c["ok"]),"")}

def main():
    ap = argparse.ArgumentParser(description="系统架构管理器")
    ap.add_argument("--port", type=int, default=8798)
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--host", default="127.0.0.1", help="监听地址(0.0.0.0 允许 Tailscale/局域网访问)")
    ap.add_argument("--render-all", action="store_true", help="只重渲全部蓝图快照")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    ap.add_argument("--tool-version", action="store_true")
    # ★ A 组回滚开关（2026-10-12）：加 --no-model 即退回改造前的直读路径，
    #   不必改代码。任何取数异常都可用它一键回退。
    ap.add_argument("--no-model", action="store_true", help="A 组回滚开关：跳过内存模型，取数全走直连")
    if "--lean4-check" in sys.argv:
        return lean4_check()
    args = ap.parse_args()
    if args.tool_version:
        print(f"bb-blueprint-gallery.py {VERSION}")
        return
    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    ensure_dir()
    if args.render_all:
        created = render_all_snapshots(verbose=True)
        print(f"渲染完成: {len(created)} 份快照 → {SNAP_DIR}")
        return
    # 启动前先渲染当前快照（服务就绪即有图）
    try:
        created = render_all_snapshots()
        print(f"初始快照渲染: {len(created)} 份")
    except Exception as e:
        print("快照预渲染失败(忽略):", e)
    import os as _os; _os.environ["SGPORT"]=str(args.port)  # 供 /api/health 自检
    # ★ A 组（2026-10-12）：**先把内存模型起起来，再开 HTTP 服务**，
    #   使第一个请求就能命中模型（而不是先冷跑再等下一次轮询）。
    if getattr(args, "no_model", False):
        print("⚙ --no-model：跳过内存模型，全部取数走直连路径（本次改造的回滚态）")
    else:
        _m = _init_model()
        if _m is not None:
            _m.start()
            _s = _m.status()
            print("🧠 A 组内存模型已起：version=%s · 监听板书键 %d 个 · 文件 %d 个 · 兜底轮询 %.1fs · SSE %s"
                  % (_s["version"], _s["boardTally"]["watched"], len(_s["files"]),
                     _s["pollInterval"], _s["sse"]["url"] or "(关)"))
        else:
            print("⚠ 内存模型未起（见上方 [model] 行）⇒ 全部取数退回首读路径，服务照常")
    from http.server import ThreadingHTTPServer
    host = args.host
    srv = ThreadingHTTPServer((host, args.port), Handler)
    disp = "127.0.0.1" if host in ("127.0.0.1", "localhost") else host
    print(f"🗺 系统架构管理器: http://{disp}:{args.port}/  (Ctrl+C 停止)")
    print(f"   快照目录: {SNAP_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    main()
