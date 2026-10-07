#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""restart-audit.py — 重启前插件兼容性审查（2026-10-03 CLD 崩溃事故后建立）

**为什么存在**：重启是唯一会暴露「apply 期问题」的时刻。当天两次事故都在这条缝里：
  · central-inbox 0.2.8：`os.homedir()` 裸用（ESM）⇒ apply 抛 ReferenceError ⇒ **CLD 启动崩溃**
  · agent-way 1.5.9：`readFileSync`/`existsSync` 未导入 ⇒ 在 try 内 ⇒ **不崩，但静默降级**
    ⇒ 而且它**不在 apply 期**，所以「真 apply 冒烟」对它**零判别力**

**审查六项**（每项都对应一次真实事故）：
  ① 语法        node --check                        （基础；拦不住 ESM 裸全局）
  ② 依赖可达    解析每个 import，检查目标是否存在      （拦 ERR_MODULE_NOT_FOUND：历史事故「漏装 12 包」）
  ③ 静态符号    裸用的 fs/os/path 符号是否已绑定       （拦 agent-way 那类**函数体内**的裸用）
  ④ 真 apply    真挂载冒烟（stub ctx + 沙箱 HOME）    （拦 0.2.8 那类 **apply 期**崩溃）
  ⑤ .bak 残留   规范 §4.2「禁带旧副本」               （拦多副本漂移）
  ⑥ 版本一致    package.json vs 目录名                 （基础卫生）

**后续增补（每项同样对应一次真实事故，勿删）**：
  ⑧ bundles ↔ dependencies 一致性（潜伏：一次 `npm install` 会剪包/回退版本）
  ⑨ / ⑨b 唤醒消息「回复指路」死前缀（文本扫描 + 行为断言，两节点同款中招）
  ⑩ 档案自洽（`~/dsh-collab/hazards` 内部不变量）
  ⑪ **投递去重键必须「成功发出之后」才写**（失败即记号 ⇒ **永久吞卡**；2026-10-04 G28）

**用法**：
  python3 restart-audit.py                    # 审 web profile 全部插件
  python3 restart-audit.py --json             # 机器可读
退出码：0 = 全绿可重启 / 1 = 有阻断项（**不建议重启**）
"""
import glob as glob_mod
import json, os, re, subprocess, sys, shutil

NM = os.path.expanduser("~/.dsh/profiles/web/node_modules")
SMOKE = os.path.expanduser("~/dsh-collab/tools/plugin-apply-smoke.mjs")
NODE = shutil.which("node") or "/opt/homebrew/bin/node"

# 需要检查「是否已绑定」的常见裸用符号（来自 node:fs / node:os / node:path 等）
WATCH_SYMS = [
    "readFileSync", "writeFileSync", "existsSync", "mkdirSync", "statSync", "readdirSync",
    "readFile", "writeFile", "mkdir", "readdir", "unlink", "rm",
    "homedir", "hostname", "tmpdir", "platform",
    "join", "dirname", "basename", "resolve", "extname",
    "spawn", "exec", "execSync", "createHash", "randomBytes", "randomUUID",
]
# JS 运行时全局（不算裸用）
GLOBALS = {
    "JSON", "Math", "Object", "Array", "String", "Number", "Boolean", "Date", "RegExp",
    "Promise", "Error", "TypeError", "RangeError", "Map", "Set", "WeakMap", "Symbol",
    "Buffer", "process", "console", "globalThis", "structuredClone", "URL", "URLSearchParams",
    "TextEncoder", "TextDecoder", "fetch", "setTimeout", "setInterval",
    "clearTimeout", "clearInterval", "setImmediate", "queueMicrotask", "AbortController",
    "parseInt", "parseFloat", "isNaN", "encodeURIComponent", "decodeURIComponent", "require",
}

RE_IMPORT = re.compile(
    r"""import\s+(?:([\w$]+)\s*,?\s*)?(?:\{([^}]*)\})?\s*(?:\*\s*as\s+([\w$]+)\s*)?from\s*['"]([^'"]+)['"]""")
RE_DYN_IMPORT = re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)""")
RE_TOP_DECL = re.compile(r"^\s*(?:export\s+)?(?:const|let|var|function|class)\s+([\w$]+)", re.M)
# ★ `const { a, b } = require('fs')` 也是绑定（函数内 require 曾被误报「未导入」）
RE_REQUIRE_DECL = re.compile(r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\s*\(")

# ★ Node 内置模块：**不是外部依赖**，第一版漏了这个判据 ⇒ 10 个插件全部误报「依赖缺失」。
#   （2026-10-03：审查脚本首跑即误报 10/13 —— 又一次「判据未验证」）
NODE_BUILTINS = {
    "fs", "fs/promises", "os", "path", "url", "http", "https", "http2", "child_process",
    "crypto", "util", "events", "stream", "net", "tls", "zlib", "assert", "buffer",
    "querystring", "readline", "worker_threads", "perf_hooks", "async_hooks", "v8", "vm",
    "module", "process", "timers", "tty", "dns", "cluster", "constants", "string_decoder",
    "diagnostics_channel", "inspector", "repl", "sea", "test", "trace_events", "wasi",
}
# 宿主 runtime 的 profile（@deepseek-ai/* 等由 CLD 提供）
RUNTIME_NM = "/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules"


def _is_builtin(mod):
    return mod.startswith("node:") or mod.split("/")[0] in NODE_BUILTINS



def js_files(pkg_dir):
    out = []
    for root, dirs, files in os.walk(pkg_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
        for f in files:
            # ★ 排除 macOS AppleDouble（`._` 前缀）—— 它们不是真 JS 文件，
            #   首版把 `lib/._adapt.js` 当语法失败报 ⇒ 假阳性（2026-10-03 实测）。
            if (f.endswith((".js", ".mjs")) and ".bak" not in f
                    and not f.startswith("._")):
                out.append(os.path.join(root, f))
    return out


def check_syntax(f):
    r = subprocess.run([NODE, "--check", f], capture_output=True, text=True)
    return (r.returncode == 0), (r.stderr or "").strip().split("\n")[0][:160]


def check_deps(files, pkg_dir):
    """解析所有 import 目标，检查是否存在（相对路径 + 兄弟包）。"""
    missing = []
    for f in files:
        raw = open(f, encoding="utf-8", errors="replace").read()
        # ★ 先去掉注释（等长替换，保持行号）：否则**注释里**的 `import('./index.js')`
        #   会被当成真实依赖 ⇒ 假阳性（2026-10-03 实测：restart-audit 自己的文档注释中招）。
        src = strip_comments_safe(raw)   # ★ 见 strip_comments_safe：块注释正则曾吞 196 行 ⇒ 假阴性
        src = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), src)
        for spec in RE_IMPORT.findall(src):
            mod = spec[3]
        # 上面 findall 只取最后一组，改用逐条扫描
        for m in RE_IMPORT.finditer(src):
            mod = m.group(4)
            if mod.startswith("."):
                base = os.path.normpath(os.path.join(os.path.dirname(f), mod))
                if not (os.path.isfile(base) or os.path.isfile(base + ".js")
                        or os.path.isfile(base + ".mjs")
                        or os.path.isfile(os.path.join(base, "index.js"))
                        or os.path.isdir(base)):
                    missing.append((os.path.relpath(f, pkg_dir), mod))
            elif _is_builtin(mod):
                continue                      # ★ Node 内置模块不是"缺失依赖"
            else:
                # 包名（含 scoped）⇒ 在 profile node_modules / runtime / 一级父目录找
                name = "/".join(mod.split("/")[:2]) if mod.startswith("@") else mod.split("/")[0]
                cands = [os.path.join(NM, name),
                         os.path.join(RUNTIME_NM, name),
                         os.path.normpath(os.path.join(pkg_dir, "..", name)),
                         os.path.normpath(os.path.join(pkg_dir, "..", "..", name))]
                if not any(os.path.exists(c) for c in cands):
                    missing.append((os.path.relpath(f, pkg_dir), mod))
        for m in RE_DYN_IMPORT.finditer(src):
            mod = m.group(1)
            if mod.startswith("."):
                base = os.path.normpath(os.path.join(os.path.dirname(f), mod))
                if not os.path.exists(base):
                    missing.append((os.path.relpath(f, pkg_dir), mod + " (dynamic)"))
    return missing


def check_bare_symbols(files, pkg_dir):
    """★ 静态符号门：裸用但未绑定的 fs/os/path 符号（agent-way 隐患所属类别）。

    三处曾误报的坑（2026-10-03 首跑实录，均已修）：
      1. 未排除 Node 内置模块 ⇒ `node:fs` 被当成「缺失依赖」
      2. 未解析 `const { x } = require('fs')` 解构 ⇒ 函数内 require 的符号被误报「未导入」
      3. 在「去注释后的文本」上算行号 ⇒ **行号错位**（现改为等长替换，行号与原文件一致）
    """
    hits = []
    for f in files:
        src = open(f, encoding="utf-8", errors="replace").read()
        # ★ 等长替换（不改变长度）⇒ 行号与原文件严格一致
        code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), src, flags=re.S)
        code = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), code)
        code = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", lambda m: " " * len(m.group(0)), code)
        bound = set()
        for m in RE_IMPORT.finditer(src):
            if m.group(1): bound.add(m.group(1))
            if m.group(3): bound.add(m.group(3))
            if m.group(2):
                for part in m.group(2).split(","):
                    part = part.strip()
                    if part: bound.add(part.split(" as ")[-1].strip())
        # ★ 函数内/顶层的 `const { a, b } = require('...')` 也是绑定
        for m in RE_REQUIRE_DECL.finditer(code):
            for part in m.group(1).split(","):
                part = part.strip()
                if part: bound.add(part.split(":")[-1].strip())
        # ★ 函数参数也是绑定：`(resolve) => …` / `function (a, b) { … }`。
        #   曾把 `new Promise((resolve) => …)` 里的 `resolve` 误报为裸用（agent-way L1789）。
        #   注：这属于**放宽**（不做作用域分析）⇒ 可能漏报，但换来误报率可接受。
        for m in re.finditer(r"(?:function\s*[\w$]*\s*)?\(([^)]*)\)\s*(?:=>|\{)", code):
            for part in m.group(1).split(","):
                nm = part.strip().split("=")[0].strip().split(":")[-1].strip().rstrip("?")
                # ★ 嵌套括号：`new Promise((resolve) => {` ⇒ 上面正则取到的是 "(resolve"，
                #   必须先清掉非标识符字符再判定（否则 fullmatch 失败、绑定丢失 ⇒ 误报）。
                nm = re.sub(r"[^\w$]", "", nm)
                if re.fullmatch(r"[\w$]+", nm or ""):
                    bound.add(nm)
        bound |= set(RE_TOP_DECL.findall(src))
        for sym in WATCH_SYMS:
            for m in re.finditer(r"(?<![\w$.])" + sym + r"\s*\(", code):
                if sym not in bound and sym not in GLOBALS:
                    ln = code[:m.start()].count("\n") + 1
                    line_txt = src.split("\n")[ln - 1].strip()[:90] if ln <= len(src.split("\n")) else ""
                    hits.append((os.path.relpath(f, pkg_dir), ln, sym, line_txt))
    return hits


def check_smoke(pkg_dir):
    if not os.path.isfile(SMOKE):
        return None, "冒烟工具缺失"
    try:
        r = subprocess.run([NODE, SMOKE, pkg_dir], capture_output=True, text=True, timeout=180)
    except Exception as e:
        return False, str(e)[:80]
    txt = (r.stdout or "") + (r.stderr or "")
    if "非插件包" in txt or "不适用" in txt:
        return None, "非插件包（不适用）"
    if "PASS" in txt and "拦住" not in txt:
        return True, "PASS"
    tail = " | ".join([l for l in txt.strip().split("\n") if l.strip()][-2:])[:200]
    # ★ 区分「真缺陷」与「stub 局限」：冒烟工具只提供最小 stub ctx（get/effect/on/inject），
    #   需要宿主配置（ctx.xxx.baseDir / .roots / .dataDir / .trustedHosts）的插件会在 apply 里
    #   读到 undefined ⇒ 报 TypeError。**单看这条无法判定**，故结合「该插件当前是否真在运行」
    #   （自查日志有 ✅）作佐证：在跑 ⇒ 说明宿主环境下 apply 是成功的 ⇒ 判为 stub 局限。
    if "Cannot read properties of undefined" in tail or "undefined (reading" in tail:
        # ★ 精确判定：报错的属性名若在源码里以 `config.<prop>` 形式出现 ⇒ 是 cordis 注入的配置，
        #   而冒烟 stub ctx 只提供 get/effect/on/inject（无 config）⇒ **stub 局限，非插件缺陷**。
        #   实证（2026-10-03）：compliance(baseDir) / local-projects(roots) /
        #   market(dataDir) / sandbox-policy-ui(trustedHosts) 四个插件的报错属性**全部**如此。
        m = re.search(r"reading '([^']+)'", tail)
        prop = m.group(1) if m else ""
        if prop:
            for f in js_files(pkg_dir):
                try:
                    s = open(f, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                if ("config.%s" % prop) in s or ('config["%s"]' % prop) in s:
                    return "stub-limited", "%s（属性 `%s` 来自 config.*，stub 未提供 config）" % (tail[:120], prop)
        return "stub-limited", tail
    return False, tail


def _selfcheck_passed(name):
    """佐证：该插件在最近一次真启动里是否自查通过（在跑 ⇒ apply 在宿主下成功）。"""
    p = os.path.expanduser("~/.dsh/plugin-selfcheck/selfcheck.log")
    try:
        tail = open(p, encoding="utf-8", errors="replace").read()[-20000:]
        return ("✅ %s 自查通过" % name.replace("dsh-plugin-", "")) in tail
    except Exception:
        return False


def check_self_recursion(pkg_dir):
    """★ 自指检测（2026-10-03 CLD「刷屏死循环」事故后新增）。

    事故形态：`apply()` → `runSelfCheck()` → 冒烟 `await import('./index.js')` 后 `mod.apply(stubCtx)`
    → 又回到 `apply()` ⇒ **环**。因为是 async/await，每层 `await` 把同步栈卸掉、状态挂到堆上，
    **栈深度恒定、永不 RangeError** ⇒ 不报错、不退出，只烧 100% CPU 且每层 `console.log` 一行。

    ⇒ 这一项**正是「真 apply 冒烟」拦不住的**：冒烟只调一次 `apply` 就返回 PASS，
       而真实 boot 会递归进去。（2026-10-03 我的部署门当时就是 PASS 的 —— 这是审查的缺口。）
    ⇒ 判据：**检查模块（selfcheck/selftest/smoke）是否 import 自身入口并调用其 `apply`**。
    """
    hits = []
    for f in js_files(pkg_dir):
        base = os.path.basename(f)
        if not any(k in base for k in ("selfcheck", "selftest", "smoke")):
            continue
        try:
            src = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        code = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), src, flags=re.S)
        code = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), code)
        if not (re.search(r"""import\s*\(\s*['"][^'"]*index\.js['"]\s*\)""", code)
                or re.search(r"""from\s*['"][^'"]*index\.js['"]""", code)):
            continue
        # ★ 重入守卫识别（首版判据漏了这一步 ⇒ 把「已修版」误报成「含环」，2026-10-03 实测）：
        #   若检查模块里有 `_inSmoke`/`inSmoke` 这类标志或明确写了「重入」，
        #   说明环在深度 2 处已被切断 ⇒ 视为已防护，不再报。
        #   实测依据：修好的 0.2.9 有 `let _inSmoke = false;` + `if (_inSmoke) { 重入跳过 }`；
        #   而 0.2.9 原始包（/tmp/ci029）这两样都没有 ⇒ 那才是真含环。
        if re.search(r"_in\w*[Ss]moke|inSmoke|重入|reentran", src):
            continue
        for m in re.finditer(r"(?<![\w$.])apply\s*\(", code):
            ln = code[:m.start()].count("\n") + 1
            hits.append((os.path.relpath(f, pkg_dir), ln,
                         "自指：检查模块 import 自身入口后又调 apply() ⇒ apply⇄selfcheck 环"))
    return hits


def check_apply_settle(pkg_dir, settle_ms=3000):
    """★「apply 后沉降观测」门 —— 补「真 apply 冒烟」的盲区。

    为什么必须有这一道（2026-10-03 实测）：
      `apply` 内部对 `runSelfCheck` 是 **fire-and-forget（不 await）** ⇒ `apply` 同步返回
      ⇒ 冒烟拿到结果就**退出进程** ⇒ **后台那条递归链被进程退出带走** ⇒ 冒烟原理上看不见它。
      ⇒ 必须在**同一进程内**调完 apply 后**不退出**，继续看事件循环与输出。

    ★★ **超时判定是这道门的核心**（不是兜底）：
      含环包会让观察器**永不返回** —— 事件循环被递归占满，连 `setTimeout` 回调都排不上队，
      所以子进程**无法自己报错退出**，只能由**父进程超时**来判定。
      实测：含环的 0.2.9 原始包让观测进程跑满 180s 被外部 SIGTERM 杀掉。
    """
    import subprocess
    import shutil as _shutil
    settle = os.path.expanduser("~/dsh-plugin-restart-audit/scripts/plugin-apply-settle.mjs")
    node = _shutil.which("node") or "/opt/homebrew/bin/node"
    if not os.path.isfile(settle):
        return None, "沉降观测器缺失（未随插件分发）"
    timeout = (settle_ms / 1000.0) + 15
    try:
        p = subprocess.run([node, settle, pkg_dir, "--settle-ms", str(settle_ms)],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, ("沉降观测**超时**（>%.0fs）⇒ 事件循环被阻塞 ⇒ 疑 apply 后后台链失控"
                       "（自递归的最强特征：连 setTimeout 都排不上队）" % timeout)
    txt = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode == 3 or "不适用" in txt:
        return None, "非插件包（不适用）"
    if p.returncode == 0 and "PASS" in txt:
        return True, (txt.split("\n")[0][:130] if txt else "PASS")
    return False, (txt.split("\n")[0][:200] if txt else "沉降异常（未输出原因）")


def check_boot_sandbox(profile="web"):
    """★★ 「可观察 boot 沙箱」——本审查的**最强判据**，按真实 bundles 顺序全量跑一遍。

    为什么它比前几项都强（2026-10-03 用户提出方案 + 实测验证）：
      · 前面的检查要么是**静态**（语法/依赖/裸符号，看不到运行时），
        要么是**单插件 + stub 环境**（环境不真 ⇒ 假阳性，且 `apply` 同步返回 ⇒ 看不见后台链）
      · 本沙箱：**真实 bundles 顺序 + 真实 config（含 Config schema default）+ 完整 ctx 面
        （含 cordis 的 `ctx.fiber`）+ 隔离（HOME 沙箱 / 掐网络）+ 逐项可观测（耗时/输出/漂移）**
      · **判别力实测**：含环的 0.2.9 原始包 ⇒ **卡住（事件循环被占满）**；
        已修版 ⇒ 正常放行。**前六项检查对含环版全部放行，只有本项抓住。**
    """
    import subprocess
    import shutil as _shutil
    sb = os.path.expanduser("~/dsh-plugin-restart-audit/scripts/plugin-boot-sandbox.mjs")
    node = _shutil.which("node") or "/opt/homebrew/bin/node"
    if not os.path.isfile(sb):
        return None, "boot 沙箱缺失（未随插件分发）"
    try:
        p = subprocess.run([node, sb, "--profile", profile], capture_output=True,
                           text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return False, ("boot 沙箱**超时**（>240s）⇒ 真实环境下有插件卡住"
                       "（事件循环被占满 = 自递归/刷屏的形态）")
    txt = ((p.stdout or "") + (p.stderr or "")).strip()
    if p.returncode == 0:
        n = len([l for l in txt.split("\n") if l.strip().startswith("✅")])
        return True, "全 profile（%s）真实顺序沉降正常，%d 项通过" % (profile, n)
    bad = [l.strip() for l in txt.split("\n") if l.strip().startswith("❌")]
    tail = txt.split("\n")[-1][:160] if txt else "无输出"
    return False, ("；".join(bad[:3])[:220] or tail)


def check_bundle_patch(pkg_dir):
    """★★ 「发布完整性」门（R17）—— 检查 `dsh.bundle.patch` 指向的文件是否存在。

    **为什么必须有这一项**（2026-10-03 事故 #4；根因 = **我自己的部署命令**）：
      发布包（星桥的 tgz）**不含 `cordis.patch.yml`** —— 它只有 `lib/`、`package.json`、`cli.js`。
      而我的部署命令是 `rsync -a --delete --exclude='.bak*' --exclude='node_modules'`，
      **`--delete` 会删掉目标里「源没有」的文件** ⇒ **把 `cordis.patch.yml` 删了**。
      该文件是 `dsh.bundle.patch` 指向的声明，boot 时缺它 ⇒ **插件树加载失败 ⇒ 整机 exit 1**
      （在插件树加载前抛错，**没有单插件降级余地**）。
      ⇒ 且热替换是**静默**的：删完进程照常跑（插件早在内存）⇒ **代价延迟到下次重启才爆发**，
        实测潜伏 **56 分钟**，期间系统"看起来完全健康"。

    ★ 教训（同一天我犯了两次同型）：`--delete` 的风险对象**不只有目录**，
      还有「**源包里没有、目标必须有**」的**单文件** —— `cordis.patch.yml` 就是。
      我当天只排除了 `node_modules`，**漏掉的那个才是致命的**。
    """
    pj = os.path.join(pkg_dir, "package.json")
    if not os.path.isfile(pj):
        return None, "无 package.json（非插件目录）"
    try:
        j = json.load(open(pj, encoding="utf-8"))
    except Exception as e:
        return False, "package.json 解析失败: %s" % str(e)[:60]
    pt = ((j.get("dsh") or {}).get("bundle") or {}).get("patch")
    if not pt:
        return None, "未声明 dsh.bundle.patch（非 bundle 形态）"
    f = os.path.join(pkg_dir, pt.replace("./", ""))
    if os.path.isfile(f):
        return True, "patch 在位（%s）" % pt
    return False, ("**缺少 %s**（dsh.bundle.patch 指向的文件不存在）"
                   "⇒ boot 时插件树加载失败 ⇒ **整机 fatal，不是单插件降级**" % pt)


def check_bundle_deps(profile="web"):
    """★ ⑧ profile `dsh.profile.bundles` ↔ `dependencies` 一致性（2026-10-03 完整审查 T6 新增）。

    **为什么必须有这一项**（实测发现，非推理）：
      `~/.dsh/profiles/web/package.json` 里 `dsh.profile.bundles` 列了 13 项，
      而 `dependencies` 只列了 8 项。实测两处具体问题：
        ① **3 个 bundle 根本不在 dependencies**：`dsh-plugin-central-inbox`、
           `dsh-plugin-compliance`、`dsh-plugin-restart-audit`
           ⇒ 它们只靠"手工放进 node_modules"存在。**任何人跑一次 `npm install`**，
             npm 会把它们当 **extraneous（多余包）剪掉** ⇒ next boot 插件树加载失败 ⇒ 整机 fatal。
        ② **`dsh-plugin-agent-way` 版本漂移**：dependencies 写死 `1.5.8`，实际部署 `1.5.11`
           ⇒ `npm install` 会把**热修回退**成 1.5.8。

    **它属于哪一类**：与事故 #3/#4 同族 ——「**源里没有、目标必须有**」（类别 A），
      只是这次的"源"是 `dependencies`、"目标"是 `node_modules`+bundles。
      ★ 与 `check_bundle_patch`（R17）的区别：R17 管**单文件声明**（patch），
        本项管**依赖表与装载表的一致性**。**两个判据各管一层，互不替代。**

    **判定**：**⚠️ 警告级**（不阻断重启）——
      当前 node_modules 是完整的，重启不会因此失败；
      但它是**潜伏项**：风险在"下次有人跑 npm install"时兑现。
      ⇒ 只报告、不拦，避免用假阻断制造噪音（恒报警的判据会被忽略）。

    ★ 判据边界：本项**只查 bundles↔dependencies 的声明一致性**，
      不验证 registry 可达性，也不验证 `link:` 目标的内容正确性。
    """
    prof_dir = os.path.expanduser("~/.dsh/profiles/%s" % profile)
    pj = os.path.join(prof_dir, "package.json")
    if not os.path.isfile(pj):
        return None, "profile package.json 不存在: %s" % pj
    try:
        j = json.load(open(pj, encoding="utf-8"))
    except Exception as e:
        return None, "解析失败: %s" % str(e)[:60]
    bundles = ((j.get("dsh") or {}).get("profile") or {}).get("bundles") or []
    deps = j.get("dependencies") or {}
    nm = os.path.join(prof_dir, "node_modules")
    missing_dep, drift, absent = [], [], []
    for b in bundles:
        if b.startswith("@deepseek-ai/"):
            continue                      # 宿主层，由 runtime 提供
        d = os.path.join(nm, b)
        if not os.path.isdir(d):
            absent.append(b)
            continue
        inst = None
        bpj = os.path.join(d, "package.json")
        if os.path.isfile(bpj):
            try:
                inst = json.load(open(bpj, encoding="utf-8")).get("version")
            except Exception:
                pass
        dep = deps.get(b)
        if dep is None:
            missing_dep.append(b)
        elif not str(dep).startswith("link:") and inst and dep != inst:
            drift.append((b, dep, inst))
    if not (missing_dep or drift or absent):
        return True, "bundles(%d) ↔ dependencies 一致" % len([b for b in bundles if not b.startswith("@deepseek-ai/")])
    parts = []
    if missing_dep:
        parts.append("**不在 dependencies**（npm install 会当多余包剪掉 ⇒ boot 整机 fatal）: %s"
                     % "、".join(missing_dep))
    if drift:
        parts.append("**版本漂移**（npm install 会回退）: %s"
                     % "、".join("%s 依赖=%s 实际=%s" % t for t in drift))
    if absent:
        parts.append("**bundles 声明但 node_modules 无此包**: %s" % "、".join(absent))
    return False, "；".join(parts)


def _reply_hint_probe(rh_path):
    """⑨b 行为探针（抽出以便自证）：对给定 reply-hint.js 真跑，返回 (ok|None, msg)。"""
    probe = (
        "import('%s').then(m=>{const a=m.peerNodeHint('session-abc12345');"
        "const b=m.peerNodeHint('bus:mac-mini');"
        "if(a!==null){console.log('FAIL session->'+JSON.stringify(a));process.exit(1);}"
        "if(b!=='mac-mini'){console.log('FAIL bus->'+JSON.stringify(b));process.exit(1);}"
        "const h1=String(m.replyCardHint('ui')||'');"
        "const h2=String(m.replyCardHint('unknown-thing')||'');"
        "if(h1.includes('notes/ui/')){console.log('FAIL ui 死前缀: '+h1.slice(0,60));process.exit(1);}"
        "if(h2.includes('notes/unknown-thing/')){console.log('FAIL 未知标签死前缀: '+h2.slice(0,60));process.exit(1);}"
        "console.log('PASS');}).catch(e=>{console.log('ERR '+e.message);process.exit(1);});"
        % rh_path.replace("'", "\\'")
    )
    try:
        r = subprocess.run([NODE, "-e", probe], capture_output=True, text=True, timeout=30)
        outp = ((r.stdout or "") + (r.stderr or "")).strip()
        if r.returncode == 0 and "PASS" in outp:
            return True, "行为判据通过：session-id→null / bus:别名→节点名（绝不拼死前缀）"
        return False, "**行为判据失败**（reply-hint.js 存在但输出不符）：%s" % outp[:120]
    except Exception as e:
        return None, "行为判据无法执行（%s）—— 回退文本扫描" % str(e)[:50]


def check_reply_hints(pkg_dir, pkg_name=""):
    """★ ⑨ 唤醒/通知消息里的「回复指路」是否指向**会被监听的**前缀（2026-10-03 新增）。

    **为什么必须有**（实测，两个节点同时中招）：
      agent-way 在跨机唤醒消息里拼回复指路：
        `'— 跨机回复请写黑板卡 notes/' + String(msg.from).replace(/^bus:/, '') + '/ 键（…）'`
      而 `msg.from` 在跨机场景下是**会话 id**（`session-fa1f9150-…`）
      ⇒ 拼出 `notes/session-fa1f9150-…/` —— **死前缀**：接收端只监听
        `notes/<节点>/` 与 `notes/collab/`，**该前缀无人监听**。
      ⇒ 后果：**对端照着这句指路回复 ⇒ 卡写进无人监听的前缀 ⇒ 静默丢失**。
        这解释了历史上"对方没回"的一部分（不是对方不理，是**我们的指路把对方带进了死胡同**）。
    **实测证据**：我侧与对端（mac-mini）的 agent-way **1.5.11 同族同版本，502/511/518 三处一致**；
      对端日志 `notes/session-*` 前缀被注入次数 = **0**。

    **判据**：在部署插件的 `lib/*.js` 里找「拼 `notes/` + 来自 `from`/`sender` 的变量 + `/`」这类
      指路拼接；若**没有**把它映射成节点名（即可能直接落成 session-id 前缀），则**报警**。
    ★ 判据边界：启发式扫描，**可能漏报**（若拼接被拆散在多个变量里）；报出即需人工确认。
      **它不判断运行期实际拼出什么** —— 那是 `comm-preflight` B7（发端可解析性）的职责。
    ★ 级别：**⚠️ 警告**（不阻断重启）—— 启发式判据不该有阻断权（否则误报会挡住重启）。

    ★★ ⑨b **行为判据（比文本扫描强）**：若存在 `lib/reply-hint.js`（1.5.12 起的纯函数模块），
      就**直接 node 跑它**，喂两个已知输入断言输出 —— 这是"**执行而不是阅读**"：
        · `peerNodeHint('session-abc12345')` 必须 **null**（绝不拼 session-id 键）
        · `peerNodeHint('bus:mac-mini')` 必须 **'mac-mini'**
      依据（同日实测）：对端 1.5.12 已落此模块；文本扫描只能看"有没有可疑拼接"，
      **行为断言能直接证明"它会不会拼出死前缀"**。⇒ 有该模块时以行为判据为准。
    """
    d = os.path.join(pkg_dir, "lib")
    if not os.path.isdir(d):
        return None, "无 lib/"
    # ── ⑨b 行为判据（优先）─────────────────────────────────────────────
    rh = os.path.join(d, "reply-hint.js")
    if os.path.isfile(rh):
        # ★ 2026-10-04 扩充（发现 1.5.12 的修复**只堵了 session-*、没堵任意标签**）：
        #   实测 `replyCardHint('ui')` ⇒ 提示写 `notes/ui/`（**无人监听的死前缀**）；
        #   `replyNodeHint` 把任何匹配 /^[a-z][a-z0-9-]{0,15}$/i 的短标签都当"合法节点别名"。
        #   ⇒ 判据必须含**未知标签**形态（否则与故障不同层 —— 这正是它逃过双方判据的原因）。
        return _reply_hint_probe(rh)
    hits = []
    pat = re.compile(r"""notes/\s*['"]?\s*\+[^;\n]{0,120}?(from|sender|msg\.from)""")
    for f in sorted(glob_mod.glob(os.path.join(d, "**", "*.js"), recursive=True)):
        try:
            src = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for i, ln in enumerate(src.splitlines(), 1):
            if ln.lstrip().startswith("//"):
                continue
            if pat.search(ln):
                # 已含节点名映射（如 replace(/^session-[0-9a-f]+/, '') 或 nodeOf(...)）⇒ 视为已修
                fixed = ("session-" in ln and ("replace" in ln and "bus:" not in ln)) or "nodeOf" in ln or "nodeAlias" in ln
                if not fixed:
                    hits.append((os.path.relpath(f, pkg_dir), i, ln.strip()[:120]))
    if not hits:
        return True, "回复指路未发现死前缀拼接"
    return False, ("**回复指路可能拼出 session-id 死前缀** %d 处（对端照做即丢卡）："
                   % len(hits) + "；".join("%s:%d" % (f, i) for f, i, _ in hits[:4]))


def check_seen_after_inject(pkg_dir, pkg_name=""):
    """★ ⑪ 投递去重键必须「**成功发出之后**」才写（2026-10-04 新增，hazards G28 / 类别 B）。

    **为什么必须有**（实测：一张卡被静默吞掉，**两端同款代码**）：
      `central-inbox` 原实现先 `_remember(_seen, …)`（写去重键），**之后**才判
      `if (!target) { …; return; }`（目标解析失败 / centralAgent 未就绪），
      注入抛错也被 `catch` 吞掉 ⇒ **投递失败照样写 seen** ⇒ 该键永久命中去重
      ⇒ **不重试、双方无感**（我侧零信号，最后靠**对端日志考古**才发现）。
    **实证**：星桥一张卡（我一直以为送到的 **0.6.4 接口卡+包**）因此**从未送达** ——
      它日志 `14:02:31 注入目标为 null，跳过` 后再无成功行；它 `seen` 表该键只有 **1** 个指纹
      （正常投递的卡各有 **2** 个）；它侧这种 `null 跳过` 共 **10 条**。
    **修法**：把 seen 写入移进 `try`、放在 `agentBus.send(...)` **之后**。

    **判据（结构断言，不是文本相似）**：
      · 定位去重键写入行 `_remember(_seen` / `remember(_seen`
      · 定位目标守卫行 `if (!target)`
      · 断言 **seen 行 > 守卫行**（在守卫之后 ⇒ 失败路径不会写 seen）
    ★ **fail-closed**：若代码形态已变、两个锚点找不齐 ⇒ 判「**无法判定**」并**阻断**，
      逼人重看一眼（判据没测到 ≠ 没问题 —— H31 家族）。
    ★ 唯一不适用情形：该插件**根本没有去重机制**（无 `_seen`/`dedupKey`）⇒ None。

    ★★ **管辖边界（2026-10-04 首跑即出的假阳性，已修）**：
      首版把「含 `dedupKey` 字样」当作「有去重机制」 ⇒ **agent-way 中招**（它有个**同名函数
      `dedupKey()`**、还有 `if (!target || …) return false` 的别处守卫），
      seen 锚点找不到 ⇒ 走 fail-closed ⇒ **把整机判成「不建议重启」**。
      ⇒ 修法两条：① 管辖范围按**形态**界定（必须有 `_remember(_seen` 这类 seen 写入调用）；
        ② fail-closed **只对确知契约的插件**（`central-inbox`）生效，其余形态回 None（不适用）。
      ⇒ 教训（与 H31/H37 同族）：**新判据不仅要验"能抓坏样本"，还要跑全量验"不误伤别人"**。
    """
    d = os.path.join(pkg_dir, "lib")
    if not os.path.isdir(d):
        return None, "无 lib/"
    _is_inbox = ("central-inbox" in (pkg_name or "")) or ("central-inbox" in pkg_dir)
    src = ""
    main = os.path.join(d, "index.js")
    if os.path.isfile(main):
        try:
            src = open(main, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            return False, "读 lib/index.js 失败：%s" % str(e)[:60]
    else:
        for f in sorted(glob_mod.glob(os.path.join(d, "**", "*.js"), recursive=True)):
            try:
                src += open(f, encoding="utf-8", errors="ignore").read() + "\n"
            except Exception:
                continue
    lines = src.splitlines()
    seen_ln = [i for i, l in enumerate(lines, 1)
               if re.search(r"_remember\(\s*_seen|remember\(\s*_seen", l)]
    guard_ln = [i for i, l in enumerate(lines, 1) if re.search(r"if\s*\(\s*!target\s*\)", l)]
    send_ln = [i for i, l in enumerate(lines, 1) if re.search(r"agentBus\.send\s*\(", l)]
    # ① 管辖范围 = 形态：没有 seen 写入调用 ⇒ 不是本判据管的形态
    if not seen_ln:
        if _is_inbox:
            return False, ("**无法判定**（central-inbox 里找不到 `_remember(_seen`）"
                           "⇒ 判据失效，必须人工确认 seen 是否仍在「成功之后」写（G28）")
        return None, "非本判据管辖（无 `_remember(_seen` 形态）"
    if not guard_ln or not send_ln:
        if _is_inbox:
            return False, ("**无法判定**（central-inbox 缺 `if (!target)` 守卫或 `agentBus.send(` 锚点）"
                           "⇒ 判据失效，必须人工确认（G28）")
        return None, "非本判据管辖（无 target 守卫/发送锚点形态）"
    gl, sl = max(guard_ln), max(send_ln)
    # ② 合法形态 A：**成功路径**必须在 `agentBus.send` 之后写 seen（至少一处）
    post = [l for l in seen_ln if l > sl]
    # ③ 合法形态 B：`send` 之前的 seen 写入 = **有意丢弃分支**，必须紧跟 `return`
    #    （★ 2026-10-04 第二轮：我加的「超龄卡丢弃」分支就是这种 —— 它先记号后 return，
    #      语义正确。首版判据用 `min(seen) > guard` 一刀切 ⇒ **误判我自己的正确补丁**。
    #      ⇒ 判据改为表达**真不变量**：不许存在「写了 seen 却不返回、继续走到注入」的路径。）
    orphan = []
    for l in seen_ln:
        if l > sl:
            continue
        window = " ".join(lines[l:l + 6])          # 其后 6 行内必须出现 return
        if not re.search(r"\breturn\b", window):
            orphan.append(l)
    if not post:
        return False, ("**成功路径没有 seen 写入**（seen 只在 `agentBus.send` 之前写 %s / send 在 L%d）"
                       "⇒ 失败与成功无法区分（G28）" % (seen_ln, sl))
    if orphan:
        return False, ("**投递失败仍写去重键 ⇒ 永久吞卡**（L%s 写了 seen 却未 return，"
                       "会继续走到注入/守卫）—— 修法：移进 try 放 `agentBus.send()` 之后，"
                       "或做成「有意丢弃、写完立即 return」（G28）" % (orphan,))
    return True, ("成功路径 seen 在 send 之后（L%s > L%d）；send 前的 seen 均属"
                  "「有意丢弃 + return」分支 ⇒ 失败路径不记号" % (post, sl))


def check_ghost_copies(profile="web"):
    """★ ⑤b 幽灵副本（2026-10-04 新增 —— 补 ⑤ 的**盲区**）。

    **为什么必须有**：⑤ 只扫「**包内**」的 `.bak` 文件。而实际存在的形态是
    **`node_modules/` 顶层的兄弟目录**（`dsh-plugin-xxx.bak-upgrade-20261003-010507/` 等）
    —— 实测 **12 个目录 / 25 个条目 / 5.7 MB**，⑤ **一个都没报**（门显示「包内 .bak = 0」，pass）。
    ⇒ 这正是 hazards 的 **H6「清理 `node_modules` 里的 `.bak-*` 幽灵包」** 所针对的形态，
    却因为**判据扫描范围不全**而长期静默（类别 C：判据无判别力 / 范围不全）。

    范围：① `NM` 顶层名字含 `.bak` 的目录（幽灵**包**）② profile 根目录名字含 `.bak` 的文件
      （`cordis.yml.bak-cld` 等；这类**可能**被 glob 式加载器扫到，且会让人误以为配置有多份真相）。
    级别：**⚠️ 信息级、不阻断**（当前系统能正常 boot ⇒ 不构成阻断），但必须**可见**。
    """
    prof = os.path.expanduser("~/.dsh/profiles/" + profile)
    ghosts = []
    try:
        for n in sorted(os.listdir(NM)):
            p = os.path.join(NM, n)
            if ".bak" in n and os.path.isdir(p):
                ghosts.append(("node_modules/", n, "ghost-pkg"))
    except Exception:
        pass
    try:
        for n in sorted(os.listdir(prof)):
            p = os.path.join(prof, n)
            if ".bak" in n and os.path.isfile(p):
                ghosts.append(("profile根/", n, "ref-copy"))
    except Exception:
        pass
    return ghosts


def strip_comments_safe(src):
    """★ 安全的注释剥离（2026-10-04 修**假阴性**事故）。

    **事故**：原实现用 `re.sub(r"/\\*.*?\\*/", …, flags=S)` 全局剥块注释。
    而 agent-way 里有**行注释文本含 `/*`**（`//   webServer API（/agent-bus/api/*）+ agentBus 服务…`）
    ⇒ 正则把它当块注释起点，**一口吞掉 pos 613→8267（约 196 行）**
    ⇒ 里面的 `import … dsh-comm-shared/identity.js` 被抹掉
    ⇒ **②依赖检查对 agent-way 完全失明**（"依赖缺=[]"是**瞎报的绿**，属类别 C 假阴性）。
    ⇒ 改为**只剥「整行注释」**：行首（去空白后）以 `//` 或 `*` 或 `/*` 开头的行整行置空。
    不做块注释正则 ⇒ 不会再有吞掉整段的风险；代价是**行内**注释里的 `import(` 可能假阳性（可见、非静默）。
    """
    out = []
    for l in src.split("\n"):
        t = l.lstrip()
        if t.startswith("//") or t.startswith("*") or t.startswith("/*"):
            out.append("")
        else:
            out.append(l)
    return "\n".join(out)


def check_reexport_bindings(files, pkg_dir):
    """★ ③b **再导出 ≠ 本地绑定**（2026-10-04 实测事故：静默 16 小时投递全挂）。

    **缺陷形态**：文件里写
        `export { peerNodeHint, replyCardHint } from './reply-hint.js';`
    该语句**只建立"导出"，不在本模块作用域建立绑定** ⇒ 同文件里调用 `replyCardHint(...)`
    抛 `ReferenceError: … is not defined`；若该调用在 `try` 内（本例在 `deliver()` 里）
    会被 `catch { return false }` **静默吞掉** ⇒ 表现成"消息 `queued` 收不到"。
    ★ **两端判据全都没抓到**：他们的 selfcheck 与我的 ⑨b 都只 `import reply-hint.js` 直接调函数，
      **从不经过本文件的作用域** ⇒ 判据与故障不同层（类别 C 的又一形态）。

    **判据**：取 `export { X } from '…'` 的名字集合，减去本文件真正的本地绑定
    （`import { X } from …` / `function X` / `const|let|var X`）；剩下的若**在本文件里被调用**（`X(`）
    ⇒ 「只有再导出、没有绑定却被调用」= **必然 ReferenceError**，且极易被 try 吞掉。
    级别：**阻断**（不是风格问题，是运行期必错）。
    ★ 边界：先等长剥掉块注释、跳过 `//` 行（避免注释里的 `X(` 假阳性）；成员调用 `a.X(` 不算。
    """
    import re as _re
    reexp_re = _re.compile(r"export\s*\{([^}]+)\}\s*from\s*['\"][^'\"]+['\"]")
    imp_re = _re.compile(r"import\s*\{([^}]+)\}\s*from")
    decl_re = _re.compile(r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"
                          r"|(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
    hits = []
    for f in files:
        raw = open(f, encoding="utf-8", errors="replace").read()
        src = strip_comments_safe(raw)
        reexported = set()
        for m in reexp_re.finditer(src):
            for part in m.group(1).split(","):
                nm = part.split(" as ")[-1].strip()
                if nm:
                    reexported.add(nm)
        if not reexported:
            continue
        bound = set()
        for m in imp_re.finditer(src):
            for part in m.group(1).split(","):
                nm = part.split(" as ")[-1].strip()
                if nm:
                    bound.add(nm)
        for m in decl_re.finditer(src):
            for g in m.groups():
                if g:
                    bound.add(g)
        for nm in sorted(reexported - bound):
            if _re.search(r"(?<![\w.$])" + _re.escape(nm) + r"\s*\(", src):
                hits.append((os.path.relpath(f, pkg_dir), nm))
    return hits


def audit():
    pkgs = sorted([d for d in os.listdir(NM)
                   if (d.startswith("dsh-plugin-") or d.startswith("dsh-comm-"))
                   and ".bak" not in d and os.path.isdir(os.path.join(NM, d))])
    report = []
    for name in pkgs:
        pkg_dir = os.path.join(NM, name)
        pj = os.path.join(pkg_dir, "package.json")
        ver = None
        try:
            ver = json.load(open(pj, encoding="utf-8")).get("version")
        except Exception:
            pass
        files = js_files(pkg_dir)
        # ①②
        syn, syn_err = [], []
        for f in files:
            ok, err = check_syntax(f)
            (syn if ok else syn_err).append((os.path.relpath(f, pkg_dir), err))
        # ②依赖
        deps = check_deps(files, pkg_dir)
        # ③静态符号
        syms = check_bare_symbols(files, pkg_dir)
        # ④冒烟
        smoke_ok, smoke_msg = check_smoke(pkg_dir)
        # ④b 自指检测（冒烟门拦不住的那一类：环只在真实 boot 展开）
        selfrec = check_self_recursion(pkg_dir)
        # ④d ★ 发布完整性（R17）：`dsh.bundle.patch` 指向的文件必须在位
        patch_ok, patch_msg = check_bundle_patch(pkg_dir)
        # ⑨ 回复指路死前缀（2026-10-03：两节点同族同版本同时中招）
        hint_ok, hint_msg = check_reply_hints(pkg_dir, name)
        # ③b 再导出≠本地绑定（2026-10-04：静默 16 小时投递全挂的根因）
        reexp = check_reexport_bindings(files, pkg_dir)
        # ⑪ 投递去重键「成功后才写」（2026-10-04：失败即记号 ⇒ 永久吞卡；两端同款代码）
        seen_ok, seen_msg = check_seen_after_inject(pkg_dir, name)
        # ④c 单插件沉降 —— **已退役，不再纳入判定**。
        #   理由（2026-10-03 实测）：它用 stub ctx，环境不真 ⇒ 4 个假阳性
        #   （无 lib/index.js 的非标准包、缺 config 的插件、自身注释里的 import…）；
        #   而全 profile「boot 沙箱」（真实 ctx + 真实 bundles 顺序 + 真实 config）已覆盖同一目的
        #   且实测 12/12 无误报，并**能抓住含环版**。
        #   ★ 保留 check_apply_settle 定义，供**单插件手工排查**时调用；自动判定一律以沙箱为准。
        settle_ok, settle_msg = None, "已由 boot 沙箱取代（见报告末尾）"
        # ⑤.bak 残留（包内）
        baks = [os.path.relpath(os.path.join(r, f), pkg_dir)
                for r, _, fs in os.walk(pkg_dir) for f in fs
                if ".bak" in f and not f.startswith("._")]   # 同样排除 AppleDouble
        # ⑥版本
        ver_ok = bool(ver)
        report.append(dict(name=name, version=ver, files=len(files),
                           syntax_fail=syn_err, deps_missing=deps, bare_syms=syms,
                           self_recursion=selfrec,
                           settle=settle_ok, settle_msg=settle_msg,
                           patch=patch_ok, patch_msg=patch_msg,
                           hint=hint_ok, hint_msg=hint_msg,
                           seen_order=seen_ok, seen_msg=seen_msg,
                           reexport=reexp,
                           smoke=smoke_ok, smoke_msg=smoke_msg, bak_files=baks, ver_ok=ver_ok))
    return report


def compute_blockers(rep, sandbox_ok):
    """★ 单一真相源（2026-10-03 修「两分支判定相反」缺陷）。

    背景：`--json` 分支原先把 `smoke == "stub-limited"` 一律当阻断（exit 1），
    而人读分支对**有自查证据**的 stub-limited **降级为 ⚠️ 不阻断**（exit 0）
    ⇒ 插件工具只看退出码 ⇒ **工具报"未通过"、手跑脚本报"可以重启"**（同一份数据两个结论）。
    ⇒ 抽到这里，两分支共用，杜绝再次分叉。
    """
    blockers = []                                   # ← 修：原被补丁误改成自我递归（RecursionError）
    for r in rep:
        if (r["syntax_fail"] or r["deps_missing"] or r["bare_syms"]
                or r.get("self_recursion") or r.get("settle") is False
                or r.get("patch") is False or r["smoke"] is False
                or r.get("seen_order") is False or r.get("reexport")):
            blockers.append(r["name"])
        elif (r["smoke"] == "stub-limited"
              and "来自 config.*" not in str(r["smoke_msg"])
              and not _selfcheck_passed(r["name"])):
            blockers.append(r["name"] + "(apply 需人工确认)")
    return blockers


def _selftest():
    """★ 判据自证（铁律 1：**负控是判据有效性的唯一证明**；铁律 2：**期望值先行**）。

    覆盖本工具新增且易腐坏的两条判据：
      · **③b 再导出≠本地绑定** —— 坏（再导出+调用且无 import）应命中；好（另有 import）0 命中；无关（再导出不调用）0 命中
      · **⑨b 回复指路** —— 故意写成**宽松正则**的坏模块（`ui` ⇒ `notes/ui/`）应判失败；白名单好模块应判通过
    动机（2026-10-04）：这两条判据当天都只有"我手工跑过一次"的负控 ⇒ 属"会悄悄腐坏"的形态。
    """
    import tempfile, shutil as _sh
    ok = True
    tmp = tempfile.mkdtemp(prefix="ra-selftest-")
    print("restart-audit · 判据自证（正负样本）")
    try:
        for name, src, expect_hit in [
            ("坏：再导出+调用、无 import", "export { foo } from './m.js';\nfoo(1);\n", True),
            ("好：另有 import { foo }", "import { foo } from './m.js';\nexport { foo } from './m.js';\nfoo(1);\n", False),
            ("无关：再导出但不调用", "export { foo } from './m.js';\n", False),
        ]:
            d = tempfile.mkdtemp(dir=tmp); os.makedirs(os.path.join(d, "lib"))
            open(os.path.join(d, "lib/index.js"), "w", encoding="utf-8").write(src)
            hits = check_reexport_bindings(js_files(d), d)
            good = bool(hits) == expect_hit
            ok = ok and good
            print("  %s ③b %-28s 期望命中=%-5s 实际=%s" % ("✅" if good else "❌", name, expect_hit, bool(hits)))
        bad_mod = ("export function peerNodeHint(f){f=String(f||'');if(f.startsWith('bus:'))return f.slice(4)||null;"
                   "if(/^session-/.test(f))return null;if(/^[a-z][a-z0-9-]{0,15}$/i.test(f))return f;return null;}\n"
                   "export function replyCardHint(from){const n=peerNodeHint(from);"
                   "return n?('\u2014 notes/'+n+'/ \u952e'):'\u2014 \u901a\u7528\u6307\u5f15 notes/<\u5bf9\u7aef\u8282\u70b9>/';}\n")
        good_mod = ("export function peerNodeHint(f){f=String(f||'');const WL=['mac-mini','macmini','mbp','mbp-bus','i9'];"
                    "const lab=f.startsWith('bus:')?f.slice(4):f;return WL.includes(lab)?lab:null;}\n"
                    "export function replyCardHint(from){const n=peerNodeHint(from);"
                    "return n?('\u2014 notes/'+n+'/ \u952e'):'\u2014 \u901a\u7528\u6307\u5f15 notes/<\u5bf9\u7aef\u8282\u70b9>/';}\n")
        for name, src, expect_ok in [("坏模块（任意标签⇒死前缀）", bad_mod, False),
                                     ("好模块（白名单）", good_mod, True)]:
            d = tempfile.mkdtemp(dir=tmp); os.makedirs(os.path.join(d, "lib"))
            pth = os.path.join(d, "lib/reply-hint.js"); open(pth, "w", encoding="utf-8").write(src)
            got, msg = _reply_hint_probe(pth)
            good = (got is expect_ok)
            ok = ok and good
            print("  %s ⑨b %-28s 期望=%-5s 实际=%-5s | %s" % ("✅" if good else "❌", name, expect_ok, got, str(msg)[:60]))
    finally:
        _sh.rmtree(tmp, ignore_errors=True)
    print("\n  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    rep = audit()
    # ★★ 全 profile boot 沙箱 —— 本审查的最强判据（真实顺序 + 真实 config + 隔离 + 可观测）
    sandbox_ok, sandbox_msg = check_boot_sandbox("web")
    # ★ ⑧ bundles ↔ dependencies 一致性（潜伏项：不阻断重启，但必须可见）
    deps_ok, deps_msg = check_bundle_deps("web")
    # ★ ⑤b 幽灵副本（补 ⑤ 的盲区：node_modules 顶层兄弟目录 / profile 根 .bak 文件）
    ghosts = check_ghost_copies("web")
    as_json = "--json" in sys.argv
    if as_json:
        # ★ 与人读分支**同一判定**（compute_blockers）；顺带把结论写进 JSON，
        #   调用方不必再从退出码反推（退出码语义保留：0=通过 / 1=有阻断）。
        _blk = compute_blockers(rep, sandbox_ok)
        print(json.dumps({"_verdict": "blocked" if _blk else "pass",
                          "_blockers": _blk,
                          "_sandbox_ok": sandbox_ok,
                          "_deps_ok": deps_ok,
                          "_ghosts": ghosts,
                          "plugins": rep}, ensure_ascii=False, indent=2))
        return 1 if _blk else 0

    print("═" * 76)
    print("重启前插件兼容性审查 · %s" % __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("═" * 76)
    # ★ 单一真相源：阻断判定只在这里算一次（与 --json 分支同源）
    #   修史：2026-10-03 我曾用 replace(...,1) 打补丁，误命中 compute_blockers 函数体
    #   （先改成自我递归 ⇒ RecursionError），又误删本分支的内联阻断逻辑
    #   ⇒ 那一版**人读分支只剩 boot-sandbox 一项阻断 = 重启门自身假绿**（真跳过了插件阻断）。
    #   ⇒ 教训：**盲目的首次匹配替换会打到别处**；改完必须两分支对跑 + 用已知阻断样本验。
    blockers = compute_blockers(rep, sandbox_ok)
    for r in rep:
        flags = []
        if r["syntax_fail"]: flags.append("❌语法")
        if r["deps_missing"]: flags.append("❌依赖")
        if r["bare_syms"]: flags.append("❌裸符号")
        if r.get("self_recursion"): flags.append("❌自指环")
        if r.get("settle") is False: flags.append("❌沉降")
        if r.get("patch") is False: flags.append("❌patch缺失")
        if r["smoke"] is False: flags.append("❌apply冒烟")
        if r["smoke"] == "stub-limited": flags.append("⚠️apply需人工判断")
        if r["smoke"] is None: flags.append("—不适用")
        if r["bak_files"]: flags.append("⚠️.bak")
        if r.get("hint") is False: flags.append("⚠️回复指路死前缀")
        if r.get("seen_order") is False: flags.append("❌投递去重键过早")
        if r.get("reexport"): flags.append("❌再导出当本地用")
        print("\n▸ %-32s v%s   %s" % (r["name"], r["version"], " ".join(flags) or "✅ 全绿"))
        if r["syntax_fail"]:
            for f, e in r["syntax_fail"][:3]: print("    语法: %s  %s" % (f, e))
        if r["deps_missing"]:
            seen = set()
            for f, m in r["deps_missing"]:
                if (f, m) in seen: continue
                seen.add((f, m)); print("    依赖缺失: %s → %s" % (f, m))
                if len(seen) >= 5: print("    …（共 %d 处）" % len(r["deps_missing"])); break
        if r["bare_syms"]:
            for f, ln, s, txt in r["bare_syms"][:5]:
                print("    ★裸符号: %s:%d  `%s` 未绑定" % (f, ln, s))
                print("        该行: %s" % txt)
        if r.get("self_recursion"):
            for f, ln, msg in r["self_recursion"][:3]:
                print("    ★自指环: %s:%d  %s" % (f, ln, msg))
                print("        后果：async 下栈不增长 ⇒ 不报错、不退出、烧满 CPU + 无限刷屏")
        if r["smoke"] is False:
            print("    apply 冒烟: %s" % r["smoke_msg"])
        if r.get("patch") is False:
            print("    ★发布完整性(R17): %s" % r.get("patch_msg"))
            print("        这是**热替换静默期**看不出来的一类：现在进程照跑，下次 boot 才整机 fatal")
        if r.get("settle") is False:
            print("    ★沉降观测: %s" % str(r.get("settle_msg"))[:170])
            print("        这是 apply 冒烟**看不见**的一类：apply 同步返回，但后台链失控")
        if r["smoke"] == "stub-limited":
            # 若 msg 已含「来自 config.*」⇒ 判据已定位到根因（stub 未提供 config），无需人工；
            # 否则才是真的需人工判断（stub 与缺陷无法区分）。
            _root = "来自 config.*" in str(r["smoke_msg"])
            print("    apply 冒烟: %s — %s" % ("⚠️ stub 局限（已定位）" if _root else "⚠️ **需人工判断**",
                                              str(r["smoke_msg"])[:110]))
            if not _root:
                sc = _selfcheck_passed(r["name"])
                print("        佐证：自查日志 %s ⇒ %s"
                      % ("✅ 有该插件通过记录" if sc else "未找到通过记录",
                         "判为 **stub 局限**（宿主下 apply 成功）" if sc
                         else "**无法排除真缺陷**，请人工核 apply 内对 ctx 的读取"))
        if r["bak_files"]:
            print("    .bak 残留 %d 个（规范 §4.2 禁带旧副本）" % len(r["bak_files"]))
        if r.get("hint") is False:
            print("    ★回复指路: %s" % r.get("hint_msg"))
            print("        后果：**对端照着这句指路回复 ⇒ 写进无人监听的前缀 ⇒ 静默丢失**")
            print("        （接收端只监听 notes/<节点>/ 与 notes/collab/）")
        if r.get("reexport"):
            for f, nm in r["reexport"][:4]:
                print("    ★再导出当本地用: %s  `%s` 只有 `export {…} from`、本文件无绑定却被调用" % (f, nm))
            print("        后果：**必然 ReferenceError**；若在 try 内会被静默吞掉（实测：投递全挂 16 小时）")
        if r.get("seen_order") is False:
            print("    ★投递去重键: %s" % r.get("seen_msg"))
            print("        后果：**对端注入失败（目标 null / 未就绪）也写去重键 ⇒ 该卡永久不再投递**")
            print("        （双方都看不见：我侧零信号，只能靠对端日志考古 —— 2026-10-04 实际发生）")
    print("\n" + "═" * 76)
    print("【boot 沙箱】%s %s" % ("✅" if sandbox_ok else ("—" if sandbox_ok is None else "❌"), sandbox_msg))
    print("  （真实 bundles 顺序 + 真实 config + 隔离 HOME/网络；唯一能抓「apply 后台链失控」的判据）")
    # ★ ⑧ 潜伏项：bundles ↔ dependencies（**不阻断重启**，但必须可见）
    print("─" * 76)
    # ★ ⑩ 档案自洽（2026-10-03 新增 · **信息级，不阻断**）
    #   动机：我在同一天四次把 hazards 里的"规则区间声明"改漏（R1–R24/R28/R30/R35）。
    #   ⇒ 建 `check-hazards-consistency.py` 并在此给它一个**触发点**（G1 教训：没人调用的门=纪律）。
    #   边界：它校验的是 `~/dsh-collab/hazards` 的**内部自洽**，与本次重启无关 ⇒ 只报不改判定。
    try:
        _hg = os.path.expanduser("~/dsh-collab/tools/check-hazards-consistency.py")
        if os.path.isfile(_hg):
            _r = subprocess.run([sys.executable, _hg], capture_output=True, text=True, timeout=60)
            _msg = ((_r.stdout or "") + (_r.stderr or "")).strip().splitlines()
            print("【档案自洽】%s" % ((_msg[0].split("·")[-1].strip() if _msg else "✅ 通过")
                                     if _r.returncode == 0 else "❌ 有漂移（不阻断重启）"))
            if _r.returncode != 0:
                for _l in _msg[1:6]:
                    print("  %s" % _l.strip())
        else:
            print("【档案自洽】— 未安装 check-hazards-consistency.py")
    except Exception as _e:
        print("【档案自洽】— 无法执行（%s）" % str(_e)[:60])
    print("─" * 76)
    # ★ ⑤b 幽灵副本（信息级，不阻断）—— 补 ⑤「只扫包内」的盲区。★ 分级：
    #   · ghost-pkg = `node_modules/` 顶层 `.bak*` **目录** ⇒ hazards **H6**「禁带旧副本」的正面形态，**应清**
    #   · ref-copy  = profile 根 `.bak*` **文件** ⇒ 多为「回滚参考副本」；实测 boot 日志 **0 行**加载过它们
    #     （`cordis.patch.yml` 的注释还把它们写成回滚路径）⇒ **留档可接受**，但必须可见
    gp = [g for g in ghosts if g[2] == "ghost-pkg"]
    rc = [g for g in ghosts if g[2] == "ref-copy"]
    if gp or rc:
        print("【幽灵副本】%s **node_modules 幽灵包 %d 个（H6 应清）** ／ 根目录参考副本 %d 个（留档可接受）"
              % ("⚠️" if gp else "ℹ️", len(gp), len(rc)))
        for where, n, _ in gp[:6]:
            print("  · [应清] %s%s" % (where, n))
        if len(gp) > 6:
            print("  …（幽灵包共 %d 个）" % len(gp))
        for where, n, _ in rc[:4]:
            print("  · [留档] %s%s" % (where, n))
        if len(rc) > 4:
            print("  …（参考副本共 %d 个）" % len(rc))
        print("  ⇒ 处置：幽灵包**搬出**（不是删）到 `~/dsh-collab/data/backups/`；参考副本保持现状即可")
    else:
        print("【幽灵副本】✅ 无（node_modules 顶层与 profile 根均干净）")
    print("─" * 76)
    if deps_ok is None:
        print("【依赖表一致性】— %s" % deps_msg)
    elif deps_ok:
        print("【依赖表一致性】✅ %s" % deps_msg)
    else:
        print("【依赖表一致性】⚠️ **潜伏项（不阻断本次重启）**")
        print("  %s" % deps_msg)
        print("  ⇒ 当前 node_modules 完整，**重启不会因此失败**；风险在「下次有人跑 npm install」时兑现。")
        print("  ⇒ 处理：把缺的 bundle 补进 dependencies（link: 或正确版本），并把版本漂移改齐。")
    print("─" * 76)
    if blockers:
        print("⛔ 有阻断项：%s ⇒ **不建议重启**（先修再启）" % ", ".join(blockers))
        return 1
    print("✅ 全部通过 ⇒ 可以重启")
    return 0


if __name__ == "__main__":
    sys.exit(main())
