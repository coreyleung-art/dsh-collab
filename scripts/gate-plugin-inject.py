#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-plugin-inject —— 插件 inject 声明门（宿主/客户端边界 + 源/产物一致）

由来：2026-10-09 CLD 崩溃风暴。dsh-plugin-excalidraw 在**宿主平面**的 inject 里写了
`slots`，而 slots 只在**客户端平面**存在（dsh-client-runtime/lib/client.js:35
`super(ctx, "slots")`）⇒ 该条永久 pending ⇒ 官方 `assertEntriesActivated`
（dsh-app-boot/lib/index.js:1125 `missing = Object.keys(fiber.inject).filter(
s => fiber.ctx.get(s) === void 0)`）判定整棵插件树加载失败 ⇒ 子进程 exit 1 ⇒
33 分钟内约 800 次崩溃重启。

本门复刻那条判据，但**离线静态**跑。它不修 bug，它让这一类进不来。

两条规则：
  a  宿主/客户端边界：宿主入口（package.json `main`）的 inject 里，
     凡 `仅由客户端入口提供` 的服务名 ⇒ RED。
  b  源/产物一致：同一插件 src 与 lib 的宿主入口 inject 声明必须相等 ⇒ 不等 RED。
     （8月22 只从 lib/ 删了 slots、src/ 没删，10-09 迁移从 src 重编译 lib ⇒ 复活）

诚实边界（R030）：RED 需要**正面证据**——该服务名在客户端入口被 provide、且在任何
宿主入口都没被 provide。证据不足只报 WARN（unknown），绝不静默通过。

用法：
  python3 -I gate-plugin-inject.py                 # 两条规则都跑
  python3 -I gate-plugin-inject.py --rule a
  python3 -I gate-plugin-inject.py --json
  python3 -I gate-plugin-inject.py --strict        # WARN 也算失败
退出码：0 无 RED；1 有 RED（或 --strict 下有 WARN）；2 用法错。
"""
import argparse
import json
import os
import re
import sys

RUNTIME = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules"
PROFILE = os.path.expanduser("~/.dsh/profiles/web")
PROFILE_NM = os.path.join(PROFILE, "node_modules")

SKIP_DIR = ("node_modules", "types", ".git", "dist")


def _prune(dirs):
    """跳过非挂载目录：已知工具目录**与一切点开头目录**。

    点目录判据来自实测：`~/.dsh/profiles/web/node_modules/.@linxin666.disabled/` 是
    **已停用**的包，扫它会把两个早已不在档里的服务（`none`、`webUiSettings`）算进清单
    ——`none` 更糟：它根本是 minified 代码里的构造器调用被误读。停用的东西不该参与判定。
    """
    return [d for d in dirs if d not in SKIP_DIR and not d.startswith(".")]
SKIP_EXT = (".d.ts", ".map", ".json", ".md", ".tsbuildinfo")

# 服务提供点的两种写法（实测：官方运行时只用这两种）
RE_PROVIDE = re.compile(r"""provide\(\s*["'`]([A-Za-z0-9_$@/.\-]+)["'`]""")
RE_SUPER = re.compile(r"""super\(\s*[A-Za-z_$][\w$]*\s*,\s*["'`]([A-Za-z0-9_$@/.\-]+)["'`]""", re.S)
# 形态 ③：服务名先存进常量，再 `provide(标识符)`。
# **只做 provide，不做 `super(标识符)`**：实测（第四版）`super(ident)` 在运行时/档里
# 新增 7 个条目、**真服务 0 个**，全是 vendored bundle 里的普通构造器调用
# （mermaid.js / three.js / pdfjs 的 `super(x, y)`，恰好 `y` 是个字符串常量）。
# 而 `provide(ident)` 新增 4 个，**全是官方真服务**
# （webRuntime / webStartup / headlessStartup / configuredAgentIdentities）⇒ 留一删一，有实测依据。
RE_STR_CONST = re.compile(
    r"""\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*["'`]([A-Za-z0-9_$@/.\-]+)["'`]""")
RE_PROVIDE_IDENT = re.compile(r"""provide\(\s*([A-Za-z_$][\w$]*)\s*[,)]""")


# ---------------------------------------------------------------- 文件工具
def read(p):
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def walk_js(root, limit=4000):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = _prune(dirnames)
        for fn in filenames:
            if not fn.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx")):
                continue
            if fn.endswith(SKIP_EXT):
                continue
            out.append(os.path.join(dirpath, fn))
            if len(out) >= limit:
                return out
    return out


def provides_in(path):
    """返回 {serviceName: 行号}

    认三种 provide 形态（第三种是实测补上的）：
      ① `ctx.provide("x")` / `ctx.reflect.provide("x")`
      ② Service 子类构造器里的 `super(ctx, "x")`
      ③ **常量间接**：`const SVC = "x"` 后 `ctx.provide(SVC, …)`
         —— 运行时 bundle 就这么写（`@deepseek-ai/dsh-web-app/lib/index.js:28` +
         `:175` 提供 `webRuntime`）。只认前两种会把**已存在的宿主服务**当成未知，
         于是规则 a 把合法的 `inject` 报成「无法证明可满足」的假黄（第三版实测）。
         该形态另补上 `webStartup` / `headlessStartup` / `configuredAgentIdentities`
         三个真服务。查不到值的标识符**不猜**，跳过即可（宁缺勿造）。
    """
    t = read(path)
    if not t:
        return {}
    found = {}
    consts = {m.group(1): m.group(2) for m in RE_STR_CONST.finditer(t)}
    for m in RE_PROVIDE.finditer(t):
        found.setdefault(m.group(1), t.count("\n", 0, m.start()) + 1)
    for m in RE_SUPER.finditer(t):
        found.setdefault(m.group(1), t.count("\n", 0, m.start()) + 1)
    for m in RE_PROVIDE_IDENT.finditer(t):
        name = consts.get(m.group(1))
        if name:
            found.setdefault(name, t.count("\n", 0, m.start()) + 1)
    return found


def is_client_file(pkgdir, pkgname, relpath):
    """文件是否属于客户端平面。判据：包名含 client 段，或文件名为 client.*"""
    if "client" in pkgname.split("-"):
        return True
    base = os.path.basename(relpath)
    if base.startswith("client."):
        return True
    return False


# ---------------------------------------------------------------- inject 抽取
def _match_bracket(text, start):
    """从 text[start] 的 [ 或 { 起，返回配对闭合处的下标；失败返 -1。"""
    if start >= len(text) or text[start] not in "[{":
        return -1
    stack = []
    i = start
    while i < len(text):
        c = text[i]
        if c in "[{":
            stack.append(c)
        elif c in "]}":
            if not stack:
                return -1
            stack.pop()
            if not stack:
                return i
        i += 1
    return -1


def _names_in(text):
    return set(re.findall(r"""["'`]([A-Za-z0-9_$@/.\-]+)["'`]""", text))


def _sub_block(text, key):
    """在对象字面量 text 里取 key 后的数组块文本。"""
    m = re.search(r"""\b%s\s*:""" % re.escape(key), text)
    if not m:
        return None
    k = m.end()
    while k < len(text) and text[k] in " \t\r\n":
        k += 1
    end = _match_bracket(text, k)
    return text[k:end + 1] if end != -1 else None


# 顶层声明形态。**必须同时接受 `export const inject` 与裸 `const inject`**：
# 打包器（esbuild/rollup）把 `export const inject = [...]` 改写成
# `const inject = [...];` + 末尾 `export { ..., inject, ... };`。
# 只认 export 形态会对**每一个打包产物**报假红（本门第一版实测 5 个假红，全是这个原因）。
RE_INJECT_DECL = re.compile(r"^[ \t]{0,2}(?:export\s+)?(?:const|let|var)\s+inject\b", re.M)

# 打包产物的第二种形态：客户端 bundle 把模块导出写成**成员赋值**，且被 minify 成一行，
# 例如 `…,n.inject=[`slots`,`sessions`],…`。只认 `const inject` 会对这类产物报假红
# （第二版实测：@omdsh-dev/dsh-genui 的 lib/client.js 正是这个形态）。
# 判据是 `=`：`ctx.inject([...])` / `slots.inject(name, fn)` 都是**调用**，不匹配。
RE_INJECT_MEMBER = re.compile(r"\b[A-Za-z_$][\w$]*\.inject\s*=\s*")


def _parse_inject_rhs(text, k, line):
    """从 text[k] 起解析 inject 右值：数组，或 { required: [...], optional: [...] }。"""
    while k < len(text) and text[k] in " \t\r\n":
        k += 1
    if k >= len(text) or text[k] not in "[{":
        return None
    end = _match_bracket(text, k)
    if end == -1:
        return None
    raw = text[k:end + 1]
    if text[k] == "[":
        return {"found": True, "required": _names_in(raw), "optional": set(),
                "form": "array", "raw": raw, "line": line}
    req = _sub_block(raw, "required")
    opt = _sub_block(raw, "optional")
    if req is None and opt is None:
        return None
    return {"found": True,
            "required": _names_in(req) if req else set(),
            "optional": _names_in(opt) if opt else set(),
            "form": "object", "raw": raw, "line": line}


def extract_inject(text):
    """返回 dict(found, required, optional, form, raw, line)。

    认三种形态：`[export] const|let|var inject = …`、成员赋值 `X.inject = …`、
    以及对象 `{ required: [...], optional: [...] }`（数组与对象皆可）。
    """
    empty = {"found": False, "required": set(), "optional": set(),
             "form": None, "raw": "", "line": None}
    if not text:
        return empty
    for m in RE_INJECT_DECL.finditer(text):
        eq = text.find("=", m.end())
        if eq == -1:
            continue
        head = text[m.end():eq]
        if ";" in head or "}" in head:
            continue          # '=' 属于后一条语句，不是本声明
        r = _parse_inject_rhs(text, eq + 1, text.count("\n", 0, m.start()) + 1)
        if r:
            return r
    for m in RE_INJECT_MEMBER.finditer(text):
        r = _parse_inject_rhs(text, m.end(), text.count("\n", 0, m.start()) + 1)
        if r:
            return r
    return empty


def entry_of(pkg):
    """(hostEntry relative, clientEntry relative)，相对包目录；无则 None。

    宿主入口不只看 `main`：包可以只声明 `exports["."]`（实测 `@liustack/modlens`
    `main` 为空、宿主入口在 `exports["."] = ./dsh/index.js`）。只看 `main` 会让
    **整个包被静默跳过**——那是「没检查」冒充「通过」，比报错更坏。
    """
    ex = pkg.get("exports") or {}
    host = pkg.get("main")
    if not host and isinstance(ex, dict):
        dot = ex.get(".")
        if isinstance(dot, str):
            host = dot
        elif isinstance(dot, dict):
            host = dot.get("default") or dot.get("import") or dot.get("require")
    c = (ex.get("./client") or {}) if isinstance(ex, dict) else {}
    if isinstance(c, str):
        client = c
    elif isinstance(c, dict):
        client = c.get("default") or c.get("import") or c.get("require")
    else:
        client = None
    if not client:
        dc = pkg.get("dsh", {}).get("client")
        if isinstance(dc, str):
            client = dc
    return host, client


# ---------------------------------------------------------------- 清单
def service_inventory():
    """扫运行时 + 挂载插件的 `.js`，按平面归集 provide 出的服务名。"""
    host, client = {}, {}   # name -> "文件:行"
    roots = []
    if os.path.isdir(RUNTIME):
        roots.append(("runtime", RUNTIME))
    if os.path.isdir(PROFILE_NM):
        roots.append(("profile", PROFILE_NM))

    seen = set()
    for _, root in roots:
        # followlinks=True：profile/node_modules 下的插件全是符号链接，不跟随就整批漏掉
        for dirpath, dirnames, _f in os.walk(root, followlinks=True):
            dirnames[:] = _prune(dirnames)
            pj = os.path.join(dirpath, "package.json")
            if not os.path.isfile(pj):
                continue
            real = os.path.realpath(dirpath)
            if real in seen:
                dirnames[:] = []
                continue
            seen.add(real)
            pkg = json.loads(read(pj) or "{}")
            pkgname = pkg.get("name") or os.path.basename(dirpath)
            for f in walk_js(dirpath, limit=800):
                rel = os.path.relpath(f, dirpath)
                if rel.startswith("lib/types/"):
                    continue
                prov = provides_in(f)
                if not prov:
                    continue
                bucket = client if is_client_file(dirpath, pkgname,
                                                  rel.replace(os.sep, "/")) else host
                for name, ln in prov.items():
                    bucket.setdefault(name, "%s:%d" % (f, ln))
            dirnames[:] = []
    return host, client


def resolve_mounts(extra_dirs=()):
    """返回 [(logicalName, dir, 来源)]。

    挂载点判据 = **profile 声明的 bundle** 或 **包自带 `dsh.bundle`**。
    只按"在 node_modules 里"会把 @aws-sdk / @codemirror 这类传递依赖当成挂载点
    （实测 756 个假挂载点）——那是噪声，不是门要管的东西。
    """
    out, seen = [], set()
    pkg = json.loads(read(os.path.join(PROFILE, "package.json")) or "{}")
    bundles = (pkg.get("dsh", {}).get("profile", {}) or {}).get("bundles", []) or []
    bundle_set = set(bundles)

    def add(name, src, must_be_bundle):
        d = os.path.join(PROFILE_NM, *name.split("/")) if name.startswith("@") \
            else os.path.join(PROFILE_NM, name)
        if not os.path.isdir(d):
            if must_be_bundle:
                out.append((name, None, src + "·未解析"))
            return
        real = os.path.realpath(d)
        if real in seen:
            return
        pj = os.path.join(real, "package.json")
        if not os.path.isfile(pj):
            return
        p = json.loads(read(pj) or "{}")
        nm = p.get("name") or name
        has_bundle = bool((p.get("dsh") or {}).get("bundle"))
        # 声明为 bundle 的必须收；其余只有自带 dsh.bundle 才算挂载点
        if not must_be_bundle and not has_bundle and nm not in bundle_set:
            return
        seen.add(real)
        out.append((nm, real, src))

    for b in bundles:
        add(b, "bundles", True)
    if os.path.isdir(PROFILE_NM):
        for n in sorted(os.listdir(PROFILE_NM)):
            if n.startswith("."):
                continue
            p = os.path.join(PROFILE_NM, n)
            if n.startswith("@") and os.path.isdir(p):
                for m in sorted(os.listdir(p)):
                    add(n + "/" + m, "node_modules", False)
            else:
                add(n, "node_modules", False)
    for d in extra_dirs:
        d = os.path.realpath(d)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            sub = os.path.join(d, n)
            if not os.path.isfile(os.path.join(sub, "package.json")):
                continue
            real = os.path.realpath(sub)
            if real in seen:
                continue
            seen.add(real)
            out.append((n, real, "extra"))
    return out


# ---------------------------------------------------------------- 规则
def rule_a(mounts, host_svc, client_svc):
    """宿主入口 inject 里的、仅存在于客户端平面的服务名 ⇒ RED。"""
    client_only = {k: v for k, v in client_svc.items() if k not in host_svc}
    rows = []
    for name, d, src in mounts:
        if not d:
            continue
        pj = os.path.join(d, "package.json")
        pkg = json.loads(read(pj) or "{}")
        host_entry, _client_entry = entry_of(pkg)
        if not host_entry:
            rows.append({"pkg": name, "verdict": "SKIP", "why": "package.json 无 main"})
            continue
        hp = os.path.join(d, host_entry)
        if not os.path.isfile(hp):
            rows.append({"pkg": name, "verdict": "SKIP",
                         "why": "main 指向不存在: %s" % host_entry})
            continue
        inj = extract_inject(read(hp) or "")
        if not inj["found"]:
            rows.append({"pkg": name, "verdict": "OK", "why": "宿主入口未声明 inject（= 无强依赖）",
                         "entry": host_entry})
            continue
        red, warn, ok = [], [], []
        for s in sorted(inj["required"]):
            if s in client_only:
                red.append((s, client_only[s]))
            elif s in host_svc:
                ok.append(s)
            else:
                warn.append(s)
        opt_red = [(s, client_only[s]) for s in sorted(inj["optional"]) if s in client_only]
        v = "RED" if red else ("WARN" if warn or opt_red else "OK")
        rows.append({"pkg": name, "verdict": v, "entry": host_entry, "form": inj["form"],
                     "required": sorted(inj["required"]), "optional": sorted(inj["optional"]),
                     "red": red, "unknown": warn, "optional_client": opt_red,
                     "host_provided": ok})
    return rows


def rule_b(mounts):
    """src 与 lib 的宿主入口 inject 必须相等。"""
    rows = []
    for name, d, src in mounts:
        if not d:
            continue
        pkg = json.loads(read(os.path.join(d, "package.json")) or "{}")
        host_entry, client_entry = entry_of(pkg)
        pairs = [("host", host_entry, _src_candidates(d, "index")),
                 ("client", client_entry, _src_candidates(d, "client"))]
        for kind, built, srcs in pairs:
            if not built:
                continue
            bp = os.path.join(d, built)
            if not os.path.isfile(bp):
                continue
            sp = next((s for s in srcs if os.path.isfile(s)), None)
            if not sp:
                rows.append({"pkg": name, "kind": kind, "verdict": "SKIP",
                             "why": "无对应源文件（%s）" % built, "built": built})
                continue
            # 入口源可能只是 barrel ⇒ 沿 re-export 下探到真声明处（见 _src_inject）。
            res = _src_inject(d, sp)
            if res is not None and "ambiguous" in res:
                rows.append({"pkg": name, "kind": kind, "verdict": "SKIP",
                             "why": "源侧多个子模块都声明 inject（%s），入口语义不明确"
                                    % ", ".join(os.path.relpath(p, d) for p in res["ambiguous"]),
                             "built": built})
                continue
            si = res["inject"] if res else {"found": False, "required": set(), "optional": set()}
            if res:
                sp = res["from"]
            bi = extract_inject(read(bp) or "")
            b_req, s_req = bi["required"], si["required"]
            b_opt, s_opt = bi["optional"], si["optional"]
            if not si["found"] and bi["found"]:
                v, why = "RED", "源未声明 inject，而产物声明了 %s" % sorted(b_req)
            elif si["found"] and not bi["found"]:
                v, why = "RED", "源声明了 %s，而产物未声明" % sorted(s_req)
            elif b_req == s_req and b_opt == s_opt:
                v, why = "OK", ""
            else:
                v = "RED"
                parts = []
                if b_req != s_req:
                    parts.append("required 仅产物有 %s / 仅源有 %s"
                                 % (sorted(b_req - s_req), sorted(s_req - b_req)))
                if b_opt != s_opt:
                    parts.append("optional 仅产物有 %s / 仅源有 %s"
                                 % (sorted(b_opt - s_opt), sorted(s_opt - b_opt)))
                why = "；".join(parts)
            rows.append({"pkg": name, "kind": kind, "verdict": v, "why": why,
                         "src": os.path.relpath(sp, d), "built": built,
                         "src_required": sorted(s_req), "built_required": sorted(b_req),
                         "src_optional": sorted(s_opt), "built_optional": sorted(b_opt)})
    return rows


def _src_candidates(d, stem):
    base = os.path.join(d, "src")
    out = []
    for ext in (".ts", ".tsx", ".js", ".mjs"):
        out.append(os.path.join(base, stem + ext))
        out.append(os.path.join(base, stem, "index" + ext))
    return out


# 源侧下探用的相对说明符。**只跟 `export … from`**——inject 必须被入口**再导出**才有意义；
# 若把裸 `import` 也算进来，一个副作用引入的子模块会把它的 inject 冒充成入口的
# （那会**掩盖**真差异，把红判成绿，比假红更坏）。
RE_REEXPORT = re.compile(r"""export\s+(?:\*|\{[^}]*\})\s*from\s*["'](\.[^"']*)["']""")
# 例外：`import { inject } from './x'; export { inject }` 这种先引后导的写法，
# 入口只有裸 `export { … inject … }`。**仅在这种形态出现时**才把相对 import 也纳入下探。
RE_IMPORT_FROM = re.compile(r"""import\s[^;]*?from\s*["'](\.[^"']*)["']""")
RE_BARE_EXPORT_INJECT = re.compile(r"""export\s*\{[^}]*\binject\b[^}]*\}""")


def _resolve_spec(pkgdir, fromfile, spec):
    """把相对模块说明符解析成包内真实文件候选（有界，不出包目录）。"""
    p = os.path.normpath(os.path.join(os.path.dirname(fromfile), spec))
    if not (p == pkgdir or p.startswith(pkgdir + os.sep)):
        return []
    cands = []
    if os.path.splitext(p)[1] in (".ts", ".tsx", ".js", ".mjs", ".cjs"):
        cands.append(p)          # 说明符自带扩展名（如 './fence-render.tsx'）
    for ext in (".ts", ".tsx", ".js", ".mjs"):
        cands.append(p + ext)
        cands.append(os.path.join(p, "index" + ext))
    return cands


def _src_inject(pkgdir, path, seen=None, depth=0):
    """在源文件里找 inject 声明；自身没有就沿相对 `export … from` 下探（有界）。

    入口常是 **barrel**（`src/index.ts` 只 `export * from './plugin/index'`），真声明在子模块。
    只读入口会得到「源未声明」的**假红**（第二版实测：@omdsh-dev/dsh-genui 宿主入口如此）。

    返回 {"inject":…, "from":…} / {"ambiguous": [路径…]} / None（确实没有）。
    """
    seen = set() if seen is None else seen
    if depth > 3 or path in seen or not os.path.isfile(path):
        return None
    seen.add(path)
    txt = read(path) or ""
    r = extract_inject(txt)
    if r["found"]:
        return {"inject": r, "from": path}
    specs = [m.group(1) for m in RE_REEXPORT.finditer(txt)]
    if RE_BARE_EXPORT_INJECT.search(txt):
        specs += [m.group(1) for m in RE_IMPORT_FROM.finditer(txt)]
    kids = {}
    for spec in specs:
        for cand in _resolve_spec(pkgdir, path, spec):
            got = _src_inject(pkgdir, cand, seen, depth + 1)
            if got and got.get("inject", {}).get("found"):
                kids[got["from"]] = got
    if not kids:
        return None
    if len(kids) > 1:
        return {"ambiguous": sorted(kids)}
    return next(iter(kids.values()))


# ---------------------------------------------------------------- 自证（正控）
def selftest():
    """造已知坏/好夹具，证明门会红也会绿。

    没有这一步，一个从未触发过的门和一个永远绿的门无法区分——那本身就是 R030 违规。
    """
    import shutil
    import tempfile

    root = tempfile.mkdtemp(prefix="gate-inject-selftest-")
    made = []

    def mk(name, lib_js, src_ts=None, src_extra=None, client_js=None):
        d = os.path.join(root, name)
        os.makedirs(os.path.join(d, "lib"))
        pkg = {"name": name, "version": "0.0.0", "main": "lib/index.js",
               "exports": {".": {"default": "./lib/index.js"}},
               "dsh": {"bundle": {"patch": "./cordis.patch.yml"}}}
        if client_js is not None:
            pkg["exports"]["./client"] = {"default": "./lib/client.js"}
        with open(os.path.join(d, "package.json"), "w") as f:
            f.write(json.dumps(pkg))
        with open(os.path.join(d, "lib", "index.js"), "w") as f:
            f.write(lib_js)
        if client_js is not None:
            with open(os.path.join(d, "lib", "client.js"), "w") as f:
                f.write(client_js)
        if src_ts is not None:
            os.makedirs(os.path.join(d, "src"))
            with open(os.path.join(d, "src", "index.ts"), "w") as f:
                f.write(src_ts)
        for rel, body in (src_extra or {}).items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(body)
        made.append(name)
        return d

    # 复刻事故形态：宿主入口 inject 了只在客户端平面存在的 slots
    mk("fx-boundary", 'export const inject = ["slots"];\nexport function apply() {}\n',
       'export const inject: string[] = ["slots"];\n')
    # 复刻"只修产物未修源"：src 有 slots、lib 没有
    mk("fx-parity", 'export const inject = ["tools"];\nexport function apply() {}\n',
       'export const inject: string[] = ["tools", "slots"];\n')
    # 干净
    mk("fx-clean", 'export const inject = [];\nexport function apply() {}\n',
       'export const inject: string[] = [];\n')
    # 打包器形态：`const inject = [...]` + 末尾 `export { inject }`。
    # 两侧语义相同（都是 tools）⇒ 规则 b 必须判 OK，不许报假红。
    mk("fx-bundled", 'const inject = ["tools"];\nexport function apply() {}\n'
                     'export { inject };\n',
       'export const inject: string[] = ["tools"];\n')
    # 打包器形态之二：客户端 bundle minify 成成员赋值 `n.inject=[...]`（全一行）。
    # 第二版实测 dsh-genui 的 lib/client.js 就是这个形态 ⇒ 不许报假红。
    mk("fx-member", 'export const inject = [];\nexport function apply() {}\n',
       client_js='window.__ModuleLoader__.load({id:"fx-member",factory:()=>{let n={};'
                 'n.apply=e=>{};n.inject=[`slots`,`sessions`];return n}});\n',
       src_extra={"src/client/index.tsx":
                  "export const inject = ['slots', 'sessions'];\nexport function apply() {}\n"})
    # 源侧 barrel：`src/index.ts` 只 re-export，真声明在 `src/plugin/index.ts`。
    # 第二版实测 dsh-genui 宿主如此 ⇒ 必须找到子模块的声明，不许报假红。
    mk("fx-barrel", 'const inject = ["systemPrompt"];\nexport function apply() {}\n'
                    'export { inject };\n',
       src_ts="import type {} from '@x/y'\nexport * from './plugin/index'\n",
       src_extra={"src/plugin/index.ts":
                  "export const inject = ['systemPrompt'];\nexport function apply() {}\n"})
    # 反向正控：源侧 barrel 的子模块真有 slots、产物没有 ⇒ 仍必须红（下探不能把红洗成绿）
    mk("fx-barrel-stale", 'export const inject = ["tools"];\nexport function apply() {}\n',
       src_ts="export * from './plugin/index'\n",
       src_extra={"src/plugin/index.ts":
                  "export const inject = ['tools', 'slots'];\nexport function apply() {}\n"})

    mounts = resolve_mounts([root])
    host_svc, client_svc = service_inventory()
    client_only = {k: v for k, v in client_svc.items() if k not in host_svc}

    ra = {r["pkg"]: r for r in rule_a(mounts, host_svc, client_svc) if r["pkg"] in made}
    rb = {(r["pkg"], r["kind"]): r for r in rule_b(mounts) if r["pkg"] in made}

    checks = [
        ("清单纯粹性：`slots` 必须被判为仅客户端", "slots" in client_only, client_only.get("slots")),
        # 回归：常量间接形态 `ctx.provide(WEB_RUNTIME_SERVICE, …)`
        # （@deepseek-ai/dsh-web-app 就这么提供 webRuntime）⇒ 必须被归为**宿主**服务
        ("服务清单认得常量间接形态：webRuntime 必须归为宿主",
         "webRuntime" in host_svc and "webRuntime" not in client_only,
         host_svc.get("webRuntime")),
        ("规则 a 抓得住事故形态 fx-boundary", ra.get("fx-boundary", {}).get("verdict") == "RED",
         ra.get("fx-boundary", {}).get("verdict")),
        ("规则 a 不冤枉干净的 fx-clean", ra.get("fx-clean", {}).get("verdict") != "RED",
         ra.get("fx-clean", {}).get("verdict")),
        ("规则 b 抓得住只修产物未修源 fx-parity",
         rb.get(("fx-parity", "host"), {}).get("verdict") == "RED",
         rb.get(("fx-parity", "host"), {}).get("verdict")),
        ("规则 b 不冤枉干净的 fx-clean",
         rb.get(("fx-clean", "host"), {}).get("verdict") != "RED",
         rb.get(("fx-clean", "host"), {}).get("verdict")),
        # 回归：打包器改写 `export const inject` → `const inject` + `export { inject }`
        ("规则 b 认得打包器形态 fx-bundled（两侧语义相同 ⇒ 不许假红）",
         rb.get("fx-bundled", {}).get("verdict") != "RED",
         rb.get("fx-bundled", {}).get("verdict")),
        # 回归：客户端 bundle minify 成 `n.inject=[...]`
        ("规则 b 认得成员赋值形态 fx-member[client]（不许假红）",
         rb.get(("fx-member", "client"), {}).get("verdict") != "RED",
         rb.get(("fx-member", "client"), {}).get("verdict")),
        # 回归：源侧入口是 barrel，真声明在子模块
        ("规则 b 认得源侧 barrel fx-barrel[host]（下探到子模块 ⇒ 不许假红）",
         rb.get(("fx-barrel", "host"), {}).get("verdict") != "RED",
         rb.get(("fx-barrel", "host"), {}).get("verdict")),
        # **反向正控**：下探不能让真差异漏网（barrel 子模块有 slots、产物没有 ⇒ 必须红）
        ("规则 b 下探后仍抓得住 fx-barrel-stale（不许把红洗成绿）",
         rb.get(("fx-barrel-stale", "host"), {}).get("verdict") == "RED",
         rb.get(("fx-barrel-stale", "host"), {}).get("verdict")),
    ]
    print("gate-plugin-inject --selftest（正控）")
    ok = True
    for label, passed, got in checks:
        ok &= bool(passed)
        print("  %s %s%s" % ("✅" if passed else "🔴", label,
                             "" if passed else "  ⇒ 实得: %r" % (got,)))
    shutil.rmtree(root, ignore_errors=True)
    print("== 自证 %s ==" % ("通过" if ok else "失败"))
    return 0 if ok else 1


# ---------------------------------------------------------------- 呈现
ICON = {"OK": "✅", "RED": "🔴", "WARN": "🟡", "SKIP": "·"}


def main():
    ap = argparse.ArgumentParser(add_help=True, description="插件 inject 声明门")
    ap.add_argument("--rule", choices=["a", "b", "all"], default="all")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    ap.add_argument("--show-skip", action="store_true")
    ap.add_argument("--all", action="store_true", help="连 OK 行一起打（默认只打红/黄）")
    ap.add_argument("--mounts-dir", action="append", default=[],
                    help="额外挂载根目录（自证用）")
    ap.add_argument("--selftest", action="store_true",
                    help="正控：造已知坏/好夹具，证明门会红也会绿")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    mounts = resolve_mounts(args.mounts_dir)
    host_svc, client_svc = service_inventory()
    client_only = {k: v for k, v in client_svc.items() if k not in host_svc}

    report = {"runtime": RUNTIME, "profile": PROFILE,
              "mounts": len(mounts), "resolved": sum(1 for _, d, _ in mounts if d),
              "host_services": len(host_svc), "client_services": len(client_svc),
              "client_only": sorted(client_only.keys()), "rules": {}}
    bad = warn = 0

    if args.rule in ("a", "all"):
        rows = rule_a(mounts, host_svc, client_svc)
        report["rules"]["a"] = rows
        bad += sum(1 for r in rows if r["verdict"] == "RED")
        warn += sum(1 for r in rows if r["verdict"] == "WARN")
    if args.rule in ("b", "all"):
        rows = rule_b(mounts)
        report["rules"]["b"] = rows
        bad += sum(1 for r in rows if r["verdict"] == "RED")
        warn += sum(1 for r in rows if r["verdict"] == "WARN")

    report["red"] = bad
    report["warn"] = warn
    report["verdict"] = "FAIL" if (bad or (args.strict and warn)) else "PASS"

    if args.json:
        # --json 是机读出口：stdout 上**只能**有 JSON（此前尾部还打了一行「== 结论 ==」
        # ⇒ 下游 `json.load` 报 Extra data。人读的结论走 stderr，不污染机读流。）
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("== 结论：%s（RED %d，WARN %d）==" % (report["verdict"], bad, warn),
              file=sys.stderr)
    else:
        print("gate-plugin-inject")
        print("  运行时 = %s" % RUNTIME)
        print("  挂载点 = %d 个（解析到 %d）" % (report["mounts"], report["resolved"]))
        print("  服务清单 = 宿主 %d / 客户端 %d ⇒ 仅客户端 %d"
              % (len(host_svc), len(client_svc), len(client_only)))
        if client_only:
            print("    仅客户端(节选) = %s" % ", ".join(sorted(client_only)[:12]))
        print()
        for rule in ("a", "b"):
            if rule not in report["rules"]:
                continue
            title = ("a 宿主/客户端边界" if rule == "a" else "b 源/产物一致")
            rows = report["rules"][rule]
            nb = sum(1 for r in rows if r["verdict"] == "RED")
            nw = sum(1 for r in rows if r["verdict"] == "WARN")
            ns = sum(1 for r in rows if r["verdict"] == "SKIP")
            print("── 规则 %s ── %d 红 / %d 黄 / %d 跳过（共 %d 个挂载点）"
                  % (title, nb, nw, ns, len(rows)))
            for r in rows:
                v = r["verdict"]
                if v == "SKIP" and not args.show_skip:
                    continue
                if v == "OK" and not args.all:
                    continue
                print("  %s %s%s" % (ICON.get(v, "?"), r["pkg"],
                                     (" [%s]" % r["kind"]) if r.get("kind") else ""))
                if v == "RED":
                    for s, where in r.get("red", []):
                        print("       inject 里的 `%s` 只在客户端平面被提供 → %s" % (s, where))
                    if r.get("why"):
                        print("       %s" % r["why"])
                elif v == "WARN":
                    if r.get("unknown"):
                        print("       证据不足（无法证明可满足）: %s" % ", ".join(r["unknown"]))
                    for s, where in r.get("optional_client", []):
                        print("       optional 里含客户端服务 `%s` → %s" % (s, where))
                elif r.get("why"):
                    print("       %s" % r["why"])
            print()

    if not args.json:
        print("== 结论：%s（RED %d，WARN %d）==" % (report["verdict"], bad, warn))
    return 1 if report["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
