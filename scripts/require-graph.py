#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""require-graph v1.0.0 — CommonJS require() 图静态解析 + 遮蔽（shadowing）判定
作者: 老登 session-aa528267 (mac-mini) · 2026-09-14

用途
  从入口文件出发静态解析 require() 图，逐条回答：
    · 每个 bare specifier 实际解析到哪个物理副本（winner）
    · 沿途还有哪些同名副本被它遮蔽（shadowed）  ← 这正是 pnpm 遮蔽事故的根因形态
  并给出**可核验的完整度声明**：哪些 require 没解析出来、为什么、影响了什么结论。

输出契约（与星桥议定格式一致）
  entrypoints / resolved / unresolved(expr_class) / coverage_declaration / shadowing / fail_closed

退出码（六态）
  0 通过     图闭合（unresolved==0）且 ≥1 个 bare specifier 被解析（遮蔽分析有材料）
  1 失败     unresolved>0 或 max-files 截断 ⇒ **fail-closed**：遮蔽结论降格为「已解析子图内成立」
  2 未发现  图闭合但**零 bare specifier**（无可分析对象；如自包含文件）
  3 无法判定 require 实参语法不在可判定闭集内 / 可疑正则形态 ⇒ 不猜，停
  4 无输入   未给入口 / 入口不存在或不可读
  5 调用错   未知选项 / 选项取值非法 ⇒ **不复用 4**
            理由（2026-09-28 修）：原实现把 `--任意未知` 走 `entries.append()` 当成入口文件，
            于是「调用方式错」被报成「入口不存在或不可读」+ 码 4 —— 把**两种不同语义**
            压进同一个读数。这正是我自己编目的那族错误（把「未声明」说成「不可用」）。
            码 5 ≠ 码 4：前者指**我的调用错**，后者指**被调对象缺失**，处置方不同。

── 计数三件套（匹配器 / 正例 / 真语料边界例）────────────────────────
匹配器定义（写在这里就是为了被复用，不是注释）：
  左边界断言 (?<![A-Za-z0-9_$.])require\\s*\\(
  ★ 左边界断言是必需的：没有它，`mtujuapp-` 式的粘连会把 "require" 认成 "myrequire" 的后缀。
抑制审计（不靠信任剥离器，靠可核验差量）：
  suppressed = 原文命中数 − 剥离后命中数  ⇒ **剥离掉的是什么，逐文件可查、可抽样**
真语料边界例（全部实测存在，见 --selftest 的 real-corpus 组）：
  ① 注释内        pako/dist/pako_inflate.es5.js:3660  `* const pako = require('pako')`      必须不命中
  ② 模板串内      dsh-better-sidebar/lib/client.js:1960 ``require('${spec}') missed...``   必须不命中
  ③ require.apply @excalidraw/excalidraw/dist/prod/chunk-SRAX5OIU.js:1                    必须不命中
  ④ require.resolve node-addon-api/tools/clang-format.js:22                               必须不命中（非加载）
  ⑤ 真正例        d3-contour/dist/d3-contour.js:3 `require('d3-array')`（UMD 分支）        必须命中
  ⑥ 一行 20KB+ 的压缩文件（d3-*.min.js）必须不崩、且边界判定与多行一致
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys
import tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/require-graph.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"

# ── 匹配器（唯一权威定义；selftest 直接 import 同一个常量，杜绝两份写法漂移） ──
REQUIRE_RE = re.compile(r"(?<![A-Za-z0-9_$.])require\s*\(")
# 可疑正则形态：紧邻 / 或 + 的 require( —— 不判定，仅上抛供人工复核
REGEX_SUSPECT_RE = re.compile(r"[/+]require\s*\(")

NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster", "console", "constants",
    "crypto", "dgram", "diagnostics_channel", "dns", "domain", "events", "fs", "http",
    "http2", "https", "inspector", "module", "net", "os", "path", "perf_hooks", "process",
    "punycode", "querystring", "readline", "repl", "stream", "string_decoder", "sys",
    "timers", "tls", "trace_events", "tty", "url", "util", "v8", "vm", "wasi", "worker_threads",
    "zlib", "sqlite", "test",
}

# 可判定实参形态闭集（**不设 catch-all**：不在闭集内 ⇒ 退出码 3，而不是塞进「其它」桶）
EXPR_CLASSES = ("literal", "template-static", "template-dynamic", "concat",
                "conditional", "identifier", "call")

EXT_CANDIDATES = ("", ".js", ".cjs", ".mjs", ".json", ".node")
INDEX_CANDIDATES = ("index.js", "index.cjs", "index.mjs", "index.json", "index.node")


# ───────────────────────────── 剥离器（可审计） ─────────────────────────────
def mask_js(src):
    """把注释内容串内容替换为空格（**长度严格保持**），保留引号与 ${} 内的表达式。
    返回 (masked, stats)。同一长度是硬约束：偏移量即原文偏移量。"""
    n = len(src)
    out = list(src)
    i = 0
    stats = {"line_comment": 0, "block_comment": 0, "string": 0, "template": 0}
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = i
            while j < n and src[j] != "\n":
                out[j] = " "
                j += 1
            stats["line_comment"] += 1
            i = j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = i + 2
            while j < n and not (src[j] == "*" and j + 1 < n and src[j + 1] == "/"):
                out[j] = " "
                j += 1
            for k in range(i, min(j + 2, n)):
                out[k] = " "
            stats["block_comment"] += 1
            i = j + 2
        elif c in ("'", '"'):
            q = c
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    out[j] = " "
                    if j + 1 < n:
                        out[j + 1] = " "
                    j += 2
                    continue
                if src[j] == q:
                    break
                if src[j] == "\n":      # 未闭合字串：不越界猜，直接停
                    break
                out[j] = " "
                j += 1
            stats["string"] += 1
            i = j + 1 if j < n and src[j] == q else j
        elif c == "`":
            j = i + 1
            depth = 0
            while j < n:
                if src[j] == "\\":
                    out[j] = " "
                    if j + 1 < n:
                        out[j + 1] = " "
                    j += 2
                    continue
                if src[j] == "$" and j + 1 < n and src[j + 1] == "{":
                    depth += 1
                    j += 1
                    j += 1
                    continue
                if src[j] == "}" and depth > 0:
                    depth -= 1
                    j += 1
                    continue
                if src[j] == "`" and depth == 0:
                    break
                if depth == 0:
                    out[j] = " "
                j += 1
            stats["template"] += 1
            i = j + 1
        else:
            i += 1
    return "".join(out), stats


def match_paren(masked, open_idx):
    """在 masked 上做括号配平，返回 (argstart, argend)；不成立返回 (None, None)"""
    depth = 0
    j = open_idx
    n = len(masked)
    while j < n:
        if masked[j] == "(":
            depth += 1
        elif masked[j] == ")":
            depth -= 1
            if depth == 0:
                return open_idx + 1, j
        j += 1
    return None, None


def split_top(text, sep):
    """按顶层分隔符切分（跳过括号/方括号/花括号内的分隔符）"""
    parts, depth, cur = [], 0, []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if depth == 0 and text.startswith(sep, i):
            parts.append("".join(cur))
            cur = []
            i += len(sep)
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def classify(arg):
    """对**原文实参**分类。返回 (expr_class, value_or_None)。闭集外返回 (None, None)"""
    a = arg.strip()
    if a == "":
        return None, None
    # 单/双引号字面量
    m = re.fullmatch(r"'([^'\\]|\\.)*'", a, re.S) or re.fullmatch(r'"([^"\\]|\\.)*"', a, re.S)
    if m:
        return "literal", a[1:-1]
    # 模板字面量
    if a.startswith("`") and a.endswith("`") and len(a) >= 2:
        body = a[1:-1]
        if "${" in body:
            return "template-dynamic", None
        return "template-static", body
    # 拼接：全为字面量则可解析，否则动态
    if "+" in a:
        parts = split_top(a, "+")
        if len(parts) > 1:
            vals, ok = [], True
            for p in parts:
                c, v = classify(p)
                if c in ("literal", "template-static") and v is not None:
                    vals.append(v)
                else:
                    ok = False
                    break
            if ok:
                return "literal", "".join(vals)
            return "concat", None
    # 三元
    if "?" in a and ":" in a:
        return "conditional", None
    # 调用：**必须是被调方形态**，不能只看「以 ) 结尾」
    # （只看结尾会把 `await import('x')` 误判成 call —— 那是一条真实的 selftest FAIL）
    if a.endswith(")") and re.match(r"^[A-Za-z_$][A-Za-z0-9_$.]*\s*\(", a):
        return "call", None
    # 标识符 / 成员访问（计算型）
    if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*(\.[A-Za-z_$][A-Za-z0-9_$]*)*", a):
        return "identifier", None
    return None, None


# ───────────────────────────── 解析器 ─────────────────────────────
def is_file(p):
    return os.path.isfile(p)


def resolve_relative(base_dir, spec):
    raw = os.path.normpath(os.path.join(base_dir, spec))
    for ext in EXT_CANDIDATES:
        if is_file(raw + ext):
            return raw + ext
    if os.path.isdir(raw):
        for idx in INDEX_CANDIDATES:
            if is_file(os.path.join(raw, idx)):
                return os.path.join(raw, idx)
        pj = os.path.join(raw, "package.json")
        if is_file(pj):
            try:
                with open(pj) as f:
                    m = json.load(f).get("main")
                if m:
                    return resolve_relative(raw, m)
            except Exception:
                pass
    return None


def bare_to_dir(spec):
    seg = spec.split("/")
    if spec.startswith("@"):
        return "/".join(seg[:2]), "/".join(seg[2:])
    return seg[0], "/".join(seg[1:])


def resolve_bare(start_dir, spec):
    """返回 (winner_or_None, [shadowed...])。winner = 最近的 node_modules 命中（Node 语义）"""
    pkg, sub = bare_to_dir(spec)
    hits = []
    d = os.path.abspath(start_dir)
    while True:
        nm = os.path.join(d, "node_modules", pkg)
        if os.path.isdir(nm) or is_file(nm):
            if sub:
                r = resolve_relative(nm, "./" + sub)
            else:
                r = resolve_relative(nm, ".")
                if r is None and is_file(nm):
                    r = nm
            if r:
                hits.append(r)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    if not hits:
        return None, []
    return hits[0], hits[1:]


def walk(entries, max_files, do_mask_stats=True):
    rep = {
        "entrypoints": [],
        "resolved": [],
        "unresolved": [],
        "shadowing": [],
        "suppressed_detail": [],
        "truncated": False,
        "hard_stop": False,
        "hard_stop_reason": None,
        "regex_suspects": [],
        "files_scanned": 0,
        "raw_require_hits": 0,
        "kept_require_hits": 0,
        "mask_stats": {},
    }
    queue = []
    seen = set()
    for e in entries:
        p = os.path.abspath(e)
        if is_file(p):
            rep["entrypoints"].append(p)
            if p not in seen:
                seen.add(p)
                queue.append(p)
        else:
            rep["entrypoints"].append({"path": p, "error": "not-a-readable-file"})

    while queue:
        f = queue.pop(0)
        if rep["files_scanned"] >= max_files:
            rep["truncated"] = True
            break
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except Exception as ex:
            rep["unresolved"].append({"from": f, "request": None,
                                      "expr_class": None, "reason": "unreadable:%s" % ex})
            continue
        rep["files_scanned"] += 1
        masked, st = mask_js(src)
        for k, v in st.items():
            rep["mask_stats"][k] = rep["mask_stats"].get(k, 0) + v
        # 抑制审计：原文 vs 剥离后
        raw_hits = list(REQUIRE_RE.finditer(src))
        kept_hits = list(REQUIRE_RE.finditer(masked))
        rep["raw_require_hits"] += len(raw_hits)
        rep["kept_require_hits"] += len(kept_hits)
        if do_mask_stats and len(raw_hits) > len(kept_hits):
            kept_at = {m.start() for m in kept_hits}
            samples = []
            for m in raw_hits:
                if m.start() not in kept_at:
                    ln = src.count("\n", 0, m.start()) + 1
                    samples.append({"line": ln, "snippet": src[m.start():m.start() + 44]
                                    .replace("\n", "\\n")})
                    if len(samples) >= 3:
                        break
            rep["suppressed_detail"].append({"file": f, "suppressed": len(raw_hits) - len(kept_hits),
                                             "samples": samples})
        for rs in REGEX_SUSPECT_RE.finditer(masked):
            ln = masked.count("\n", 0, rs.start()) + 1
            rep["regex_suspects"].append({"file": f, "line": ln,
                                          "snippet": src[rs.start():rs.start() + 40]})

        base = os.path.dirname(f)
        for m in kept_hits:
            open_idx = masked.index("(", m.start())
            a0, a1 = match_paren(masked, open_idx)
            if a0 is None:
                rep["hard_stop"] = True
                rep["hard_stop_reason"] = "unbalanced-paren at %s" % f
                break
            arg_src = src[a0:a1]
            ec, val = classify(arg_src)
            if ec is None:
                rep["hard_stop"] = True
                rep["hard_stop_reason"] = ("unclassified require argument at %s: %r"
                                           % (f, arg_src.strip()[:60]))
                break
            ln = src.count("\n", 0, m.start()) + 1
            if ec != "literal" and ec != "template-static":
                rep["unresolved"].append({"from": f, "line": ln, "request": arg_src.strip()[:80],
                                          "expr_class": ec, "reason": "non-static-specifier"})
                continue
            spec = val
            if spec in NODE_BUILTINS or spec.startswith("node:"):
                rep["resolved"].append({"from": f, "line": ln, "request": spec,
                                        "to": None, "how": "builtin"})
                continue
            if spec.startswith(".") or spec.startswith("/"):
                tgt = resolve_relative(base, spec)
                if tgt:
                    rep["resolved"].append({"from": f, "line": ln, "request": spec,
                                            "to": tgt, "how": "relative"})
                    if tgt not in seen and os.path.splitext(tgt)[1] in (".js", ".cjs", ".mjs"):
                        seen.add(tgt)
                        queue.append(tgt)
                else:
                    rep["unresolved"].append({"from": f, "line": ln, "request": spec,
                                              "expr_class": "literal", "reason": "relative-not-found"})
                continue
            winner, shadowed = resolve_bare(base, spec)
            if winner:
                rep["resolved"].append({"from": f, "line": ln, "request": spec,
                                        "to": winner, "how": "node_modules"})
                if shadowed:
                    rep["shadowing"].append({"request": spec, "winner": winner,
                                             "shadowed": shadowed, "required_from": f})
                if winner not in seen and os.path.splitext(winner)[1] in (".js", ".cjs", ".mjs"):
                    seen.add(winner)
                    queue.append(winner)
            else:
                rep["unresolved"].append({"from": f, "line": ln, "request": spec,
                                          "expr_class": "literal", "reason": "bare-not-found"})
    return rep


# ───────────────────────────── 报告 ─────────────────────────────
def coverage_declaration(corpus):
    return {
        "机制": "CommonJS require() 静态解析；ESM import 不覆盖",
        "可判定实参闭集": list(EXPR_CLASSES),
        "catch-all桶": "无（闭集外 ⇒ 退出码 3，不塞进「其它」桶）",
        "匹配器定义": REQUIRE_RE.pattern,
        "抑制审计": "suppressed = 原文命中数 − 剥离后命中数，逐文件可抽样核验",
        "含项": ["项目内 .js/.cjs/.mjs 的相对与 bare require",
                 "node 内建模块名（不视为文件）",
                 "node_modules 逐级上溯（记录 winner 与全部被遮蔽副本）"],
        "排除项": [
            "ESM `import ... from`（另一套机制，本工具不解析）",
            "`createRequire(...)` 产出的 require（实参不是标识符 require ⇒ **本工具看不见**）",
            "打包器（webpack/vite/esbuild）产出的内联模块表",
            "exports/imports 字段的条件导出与 package self-reference",
            "Yarn PnP / pnpm 虚拟 store 的符号链接语义",
            ".json/.node 之外的资源加载（fs.readFile 等）",
        ],
        "已知未测量项": ["正则字面量内 require( —— 已用 regex_suspects 上抛可疑形态，但未做全量判定"],
        "语料根": corpus,
        "计数单位": "文件数 / require 调用点数 / specifier 数",
    }


def run(entries, max_files=500, corpus=None):
    rep = walk(entries, max_files)
    valid_entries = [e for e in rep["entrypoints"] if isinstance(e, str)]
    if not valid_entries:
        rep["verdict"] = "无输入：入口不存在或不可读"
        rep["exit"] = 4
        rep["coverage_declaration"] = coverage_declaration(corpus)
        rep["fail_closed"] = True
        return rep
    bare = [r for r in rep["resolved"] if r["how"] == "node_modules"]
    rep["coverage_declaration"] = coverage_declaration(corpus)
    rep["coverage_declaration"]["已扫文件数"] = rep["files_scanned"]
    rep["coverage_declaration"]["截断"] = rep["truncated"]

    if rep["hard_stop"]:
        rep["verdict"] = "无法判定：%s" % rep["hard_stop_reason"]
        rep["exit"] = 3
    elif rep["truncated"] or rep["unresolved"]:
        rep["verdict"] = ("失败：图未闭合（unresolved=%d, truncated=%s）"
                          % (len(rep["unresolved"]), rep["truncated"]))
        rep["exit"] = 1
    elif not bare:
        rep["verdict"] = "未发现：图闭合但零 bare specifier，无遮蔽分析对象"
        rep["exit"] = 2
    else:
        rep["verdict"] = "通过：图闭合，%d 个 bare specifier 已解析" % len(bare)
        rep["exit"] = 0

    rep["fail_closed"] = rep["exit"] != 0
    if rep["fail_closed"]:
        rep["降格声明"] = ("遮蔽与副本数结论**仅在已解析子图内成立**；未闭合部分可能另含解析路径差异。")
    # 遮蔽汇总（按 specifier 归并）
    agg = {}
    for s in rep["shadowing"]:
        k = s["request"]
        e = agg.setdefault(k, {"request": k, "winner": s["winner"], "shadowed": set(),
                               "sites": 0})
        e["shadowed"].update(s["shadowed"])
        e["sites"] += 1
    rep["shadowing_summary"] = [
        {"request": v["request"], "winner": v["winner"],
         "shadowed_count": len(v["shadowed"]), "shadowed": sorted(v["shadowed"]),
         "sites": v["sites"]}
        for v in sorted(agg.values(), key=lambda x: -len(x["shadowed"]))
    ]
    return rep


def print_text(rep):
    print("require-graph v%s" % VERSION)
    print("入口: %s" % ", ".join(str(e) for e in rep["entrypoints"]))
    print("文件数: %s · require 原文命中 %s · 剥离后保留 %s（抑制 %s）"
          % (rep["files_scanned"], rep["raw_require_hits"], rep["kept_require_hits"],
             rep["raw_require_hits"] - rep["kept_require_hits"]))
    kinds = {}
    for r in rep["resolved"]:
        kinds[r["how"]] = kinds.get(r["how"], 0) + 1
    print("resolved: %s" % (kinds or "无"))
    if rep["unresolved"]:
        uc, ur = {}, {}
        for u in rep["unresolved"]:
            k = u.get("expr_class") or "?"
            uc[k] = uc.get(k, 0) + 1
            rr = u.get("reason") or "?"
            ur[rr] = ur.get(rr, 0) + 1
        print("unresolved: %d 按实参类=%s" % (len(rep["unresolved"]), uc))
        print("            按原因=%s" % ur)
        print("            ★ 提示：bare-not-found 常见于**可选/平台专用依赖**"
              "（如 NAPI 预编译包在这台机器上本就不存在），"
              "与「动态 require」性质不同，但两者都使图未闭合、结论同等降格")
    ss = rep.get("shadowing_summary", [])
    if ss:
        print("★ 遮蔽（%d 个 specifier）:" % len(ss))
        for s in ss[:15]:
            print("  %-40s winner=%s" % (s["request"], s["winner"]))
            for sh in s["shadowed"][:4]:
                print("      被遮蔽 → %s" % sh)
            if s["shadowed_count"] > 4:
                print("      … 另 %d 个" % (s["shadowed_count"] - 4))
    else:
        print("遮蔽: 未发现同名多副本")
    if rep["suppressed_detail"]:
        print("抑制审计样本: %d 个文件存在被剥离的 require 形态" % len(rep["suppressed_detail"]))
    if rep.get("fail_closed"):
        print("★ 降格声明: %s" % rep.get("降格声明"))
    print("结论: %s" % rep["verdict"])
    print("退出码: %d" % rep["exit"])


# ───────────────────────────── 自检 ─────────────────────────────
CORPUS = os.path.expanduser("~/.dsh/profiles/web")
CASE_FILES = {}


def _mk(tmpdir, name, body):
    """★ 每个用例**唯一文件名**（老登第 3 次共享可变状态缺陷的堵法：同文件名会让 A 用例跑成 B 用例）"""
    p = os.path.join(tmpdir, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    CASE_FILES[name] = p
    return p


def selftest():
    tmpdir = tempfile.mkdtemp(prefix="reqgraph-st-")
    cases = []      # (期望退出码, 说明, 入口列表, must_reject)
    passed = failed = 0
    log = []

    # ── 构造用例：每个非零退出码都有 must_reject ──
    # case0 同时充当**遮蔽见证**：内层 node_modules 必须赢、外层必须被记为 shadowed
    _mk(tmpdir, "lib_a.js", "module.exports = 1;\n")
    _mk(tmpdir, "node_modules/shadowpkg/index.js", "module.exports = 'outer';\n")
    _mk(tmpdir, "node_modules/shadowpkg/package.json", '{"name":"shadowpkg","main":"index.js"}\n')
    _mk(tmpdir, "sub/node_modules/shadowpkg/index.js", "module.exports = 'inner';\n")
    _mk(tmpdir, "sub/node_modules/shadowpkg/package.json",
        '{"name":"shadowpkg","main":"index.js"}\n')
    ok_f = _mk(tmpdir, "case0_closed.js",
               "const a = require('./lib_a.js');\nconst b = require('path');\n"
               "const c = require('shadowpkg');\n")
    # 注意 case0 的入口在 tmpdir 根 ⇒ 外层副本胜出、内层**不是** shadowed（内层在更深层未被上溯）
    sub_f = _mk(tmpdir, "sub/case0b_inner.js", "const c = require('shadowpkg');\n")
    cases.append((0, "图闭合 + bare→node_modules（外层副本胜出）", [ok_f], False))
    cases.append((0, "遮蔽见证：内层入口 ⇒ 内层胜、外层被遮蔽", [sub_f], False))

    dyn_f = _mk(tmpdir, "case1_dynamic.js", "const p = 'x';\nconst m = require(p);\n")
    cases.append((1, "动态 require ⇒ 图未闭合", [dyn_f], True))

    self_f = _mk(tmpdir, "case2_nobare.js", "const a = require('./lib_a.js');\n")
    cases.append((2, "零 bare specifier ⇒ 无可分析对象", [self_f], True))

    unk_f = _mk(tmpdir, "case3_unknown.js", "const m = require(await import('x'));\n")
    cases.append((3, "实参语法在闭集外 ⇒ 不猜，停", [unk_f], True))

    cases.append((4, "入口不存在 ⇒ 无输入", [os.path.join(tmpdir, "nope_never_exists.js")], True))

    # ── ★ 新增：拼接字面量分支（这是 `split_top` **唯一**的到达路径）──────────
    # 立据（2026-09-28 入口覆盖审计实测）：`split_top`（18 行）**零被经过**，
    #   而它**有调用点**（第 200 行 `parts = split_top(a, "+")`）⇒ 成因是
    #   **「可达但未被测试」**（另一种成因是「本文件内无调用点=死代码」，二者处置相反）。
    # ⇒ 故补一条真正走过该分支的用例。覆盖它的是**拼接字面量**这一形态：
    #   classify("'d3'+'-array'") ⇒ ('literal','d3-array')，即拼出来仍可解析。
    # ★ 端到端而非直接调 classify：直接调只能证明函数本身对，证明不了它**被接上**。
    _mk(tmpdir, "node_modules/concatmod/index.js", "module.exports = 'c';\n")
    _mk(tmpdir, "node_modules/concatmod/package.json",
        '{"name":"concatmod","main":"index.js"}\n')
    concat_f = _mk(tmpdir, "case6_concat.js",
                   "const a = require('concat' + 'mod');\n")
    cases.append((0, "拼接字面量 ⇒ split_top 分支（唯一到达路径）", [concat_f], False))

    # 退出码 1 的**第二条守卫分支**：截断（不只是动态 require）
    # 闭合门纪律：覆盖面按守卫分支算，不按退出码值算 ⇒ 同一个 1 也要两条分支
    _mk(tmpdir, "chain_b.js", "const c = require('./chain_c.js');\n")
    _mk(tmpdir, "chain_c.js", "module.exports = 3;\n")
    chain_a = _mk(tmpdir, "case1b_truncated.js",
                  "const b = require('./chain_b.js');\nconst x = require('shadowpkg');\n")
    cases.append((1, "max-files 截断 ⇒ 未闭合（守卫分支2）", [chain_a], True, 1))

    results = {}
    for tup in cases:
        exp, desc, ents, reject = tup[0], tup[1], tup[2], tup[3]
        mf = tup[4] if len(tup) > 4 else 500
        r = run(ents, max_files=mf, corpus=CORPUS)
        got = r["exit"]
        results[desc] = r
        if got == exp:
            passed += 1
            log.append("  [PASS] 构造·%s → 退出码 %d" % (desc, got))
        else:
            failed += 1
            log.append("  [FAIL] 构造·%s → 期望 %d 实得 %d（%s）"
                       % (desc, exp, got, r.get("verdict")))

    # 遮蔽见证的方向性断言（不只是退出码对）
    r = results.get("遮蔽见证：内层入口 ⇒ 内层胜、外层被遮蔽", {})
    ss = r.get("shadowing_summary", [])
    if ss and "sub/node_modules" in ss[0]["winner"] and ss[0]["shadowed_count"] >= 1 \
            and any("shadowpkg" in x for x in ss[0]["shadowed"]):
        passed += 1
        log.append("  [PASS] 遮蔽·winner=内层且外层被记为 shadowed（%d 个）"
                   % ss[0]["shadowed_count"])
    else:
        failed += 1
        log.append("  [FAIL] 遮蔽·未产出正确 winner/shadowed：%s" % (ss or "空"))

    # ★ 共享可变状态护栏：用例文件名必须互不相同
    if len(set(CASE_FILES.values())) == len(CASE_FILES):
        passed += 1
        log.append("  [PASS] 护栏·%d 个用例文件名互不相同" % len(CASE_FILES))
    else:
        failed += 1
        log.append("  [FAIL] 护栏·用例文件名发生碰撞 ⇒ 用例会互相顶替")

    # ── 真语料边界例：**逐构造**方向性断言（不是粗粒度 raw/kept 比较）──
    # 每项 (相对路径, 断言构造, 该构造是否应被抑制: True/False/None=形态本身不该被命中, 说明)
    REAL_CASES = [
        ("pako/dist/pako_inflate.es5.js", "require('pako')", True,
         "注释内 require( 必须被剥离"),
        ("dsh-better-sidebar/lib/client.js", "require('${spec}')", True,
         "模板串内 require( 必须被剥离"),
        ("dsh-better-sidebar/lib/client.js", 'require("react")', False,
         "同文件真调用必须保留（防过度剥离）"),
        ("d3-contour/dist/d3-contour.js", "require('d3-array')", False,
         "真正例：UMD 分支调用必须命中"),
        ("d3-shape/dist/d3-shape.min.js", 'require("d3-path")', False,
         "压缩单行文件（20KB+ 一行）不崩且命中"),
        ("@excalidraw/excalidraw/dist/prod/chunk-SRAX5OIU.js", "require.apply(", None,
         "非调用形态 require.apply( 不得被当作 require("),
        ("node-addon-api/tools/clang-format.js", "require.resolve(", None,
         "非加载形态 require.resolve( 不得被当作 require("),
    ]
    for rel, construct, suppressed, desc in REAL_CASES:
        p = os.path.join(CORPUS, "node_modules", rel)
        if not is_file(p):
            failed += 1
            log.append("  [FAIL] 真语料·边界例缺失：%s（%s）" % (rel, desc))
            continue
        with open(p, encoding="utf-8", errors="replace") as f:
            src = f.read()
        masked, _ = mask_js(src)
        raw_at = {m.start() for m in REQUIRE_RE.finditer(src)}
        kept_at = {m.start() for m in REQUIRE_RE.finditer(masked)}
        offsets = [i for i in range(len(src)) if src.startswith(construct, i)]
        if not offsets:
            failed += 1
            log.append("  [FAIL] 真语料·%s 构造 %r 未在文件里出现（语料已变，断言失效）"
                       % (desc, construct))
            continue
        o = offsets[0]
        hit_raw, hit_kept = o in raw_at, o in kept_at
        if suppressed is True:
            good = hit_raw and not hit_kept
        elif suppressed is False:
            good = hit_raw and hit_kept
        else:
            good = not hit_raw and not hit_kept
        detail = "raw=%s kept=%s（出现 %d 次）" % (hit_raw, hit_kept, len(offsets))
        if good:
            passed += 1
            log.append("  [PASS] 真语料·%s → %s" % (desc, detail))
        else:
            failed += 1
            log.append("  [FAIL] 真语料·%s → %s" % (desc, detail))

    # ── ★ 新增：main() 的参数解析路径 ──────────────────────────────
    # 为什么单列一组：上面所有构造用例都直接调 run()，**从未经过 main()**。
    # 于是「未知选项被当成入口文件」这个缺陷能在 12+ 个用例全绿的情况下存活。
    # 纪律：一个没有被任何用例经过的代码路径 = 一条**没被检查过**的宣称。
    # 判据：每个非 0 退出码都须有 must_reject 用例 ⇒ 码 5 在此补。
    # 反向用例（must_pass）：合法调用必须仍成功，防「把一切都拒了」冒充覆盖。
    import subprocess
    me = os.path.abspath(__file__)
    ok_entry = _mk(tmpdir, "case5_main_closed.js",
                   "const a = require('./lib_a.js');\nconst b = require('path');\nconst c = require('shadowpkg');\n")
    main_cases = [
        (["--zzz-bogus-flag"],                  5, "must_reject·码5 未知选项"),
        (["--zzz-bogus-flag", ok_entry],        5, "must_reject·码5 未知选项+合法入口（不得因有入口就放行）"),
        (["--max-files"],                       5, "must_reject·码5 --max-files 缺值"),
        (["--max-files", "abc", ok_entry],      5, "must_reject·码5 --max-files 非整数"),
        ([],                                    4, "must_reject·码4 无入口（与码5须可区分）"),
        ([ok_entry],                            0, "must_pass·合法调用仍成功"),
        ([ok_entry, "--max-files", "500"],      0, "must_pass·合法选项仍成功"),
    ]
    n_rej = n_rej_ok = n_pas = n_pas_ok = 0
    for args, exp, desc in main_cases:
        p = subprocess.run([sys.executable, me] + args,
                           capture_output=True, text=True)
        got = p.returncode
        if exp == 0:
            n_pas += 1; n_pas_ok += (got == 0)
        else:
            n_rej += 1; n_rej_ok += (got == exp)
        if got == exp:
            passed += 1
            log.append("  [PASS] main·%s → 退出码 %d" % (desc, got))
        else:
            failed += 1
            log.append("  [FAIL] main·%s → 期望 %d 实得 %d（stdout 首行：%s）"
                       % (desc, exp, got, (p.stdout or "").strip().splitlines()[:1]))
    # ★ 差分断言：码 5 与码 4 的**输出必须可区分** —— 否则加了码值也只是换了个数字
    a5 = subprocess.run([sys.executable, me, "--zzz-bogus-flag"], capture_output=True, text=True)
    a4 = subprocess.run([sys.executable, me, os.path.join(tmpdir, "nope_never_exists.js")],
                        capture_output=True, text=True)
    if a5.returncode != a4.returncode and "未知选项" in a5.stdout \
            and "入口不存在或不可读" in a4.stdout:
        passed += 1
        log.append("  [PASS] main·码5 与码4 既不同码也不同文（可区分）")
    else:
        failed += 1
        log.append("  [FAIL] main·码5/码4 不可区分：rc=%s/%s"
                   % (a5.returncode, a4.returncode))

    print("require-graph v%s --selftest" % VERSION)
    print("匹配器定义: %s" % REQUIRE_RE.pattern)
    print("正例: d3-contour 的 UMD require('d3-array') 必须命中")
    print("真语料边界例: %d 项，逐构造断言（按守卫分支覆盖，非按形态覆盖）" % len(REAL_CASES))
    print("-" * 72)
    for line in log:
        print(line)
    print("-" * 72)
    print("合计: %d PASS / %d FAIL" % (passed, failed))
    # ★ 覆盖形态（不是总数）：**只报总数会掩盖不对称**
    #   我自己的写卡门曾出现 5/5 全 must_reject、0 must_pass ⇒ 一个「什么都拒绝」
    #   的实现与正确实现**读数完全相同**。故此处分开报，且当一侧为 0 时明确点出。
    print("覆盖形态: main 组 must_reject %d/%d · must_pass %d/%d"
          % (n_rej_ok, n_rej, n_pas_ok, n_pas))
    if n_pas == 0:
        print("  ⚠️ must_pass 用例数=0 ⇒ 本组**无法区分**「正确实现」与「一律拒绝的实现」")
    if n_rej == 0:
        print("  ⚠️ must_reject 用例数=0 ⇒ 本组**无法区分**「正确实现」与「一律放行的实现」")
    return 0 if failed == 0 else 1


def main(argv):
    if "--version" in argv:
        print("require-graph %s" % VERSION)
        return 0
    if "--selftest" in argv:
        return selftest()
    entries, max_files, as_json = [], 500, "--json" in argv
    unknown, bad_value = [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--max-files":
            # ★ 缺值/非整数：原实现直接 int(argv[i+1]) ⇒ IndexError 裸崩。
            #   这与「未知选项」同族：把「调用方式错」当成别的东西。
            if i + 1 >= len(argv):
                bad_value.append("--max-files 缺值")
                i += 1; continue
            try:
                max_files = int(argv[i + 1])
            except ValueError:
                bad_value.append("--max-files 的值不是整数：%r" % argv[i + 1])
                i += 2; continue
            i += 2; continue
        if a in ("--json",):
            i += 1; continue
        # ★ 未知选项：原实现 entries.append(a) ⇒ 被当成入口文件 → 「入口不存在或不可读」+ 码 4。
        #   那是**把「调用方式错」报成「内容缺失」**（同族：把未声明说成不可用）。
        #   故单列一码 5，不复用 4（复用即再次混淆两种语义）。
        if a.startswith("-") and a != "-":
            unknown.append(a)
            i += 1; continue
        entries.append(a); i += 1
    if unknown or bad_value:
        for u in unknown:
            print("未知选项: %s" % u)
        for b in bad_value:
            print("选项取值错: %s" % b)
        print("用法: require-graph.py <入口.js ...> [--max-files N] [--json] [--selftest]")
        print("（码 5 = 调用方式错；码 4 = 入口不存在或不可读 —— 二者语义不同，不共用）")
        return 5
    if not entries:
        print("用法: require-graph.py <入口.js ...> [--max-files N] [--json] [--selftest]")
        return 4
    rep = run(entries, max_files=max_files, corpus=CORPUS)
    if as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2, default=str))
    else:
        print_text(rep)
    return rep["exit"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
