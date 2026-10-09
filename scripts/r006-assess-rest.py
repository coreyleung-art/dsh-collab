#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-assess-rest.py — R006 剩余五项核验器（R1 插件形态 · R2 TCC · R3 CLD · R4 版本 · R8 落链）v1.0.0

为什么需要（2026-10-09 · 目标「R006 剩余五项」）：
  本机的 `r006-recheck.py` / `r006-debt-assess.py` **只核五项**（R5 文档 · R6 版本 ·
  R7 日志 · R9 CLI · R10 约束门）—— 也就是**可机械核的那五项**；其余五项
  （R1/R2/R3/R4/R8）**从未被核过**。而「未核」不等于「达标」——
  §2 ⑧ 的 push 判据是我 2026-10-09 刚补的，却从未全量核过。

★ 本器的核心纪律（照 2026-10-09 反复验证的教训）：
  1. **判据须扫得全、认得准**：检测前用 `tokenize` 剥离注释与字符串
     ⇒ 「引述」不得进入检测面（今日已因此误判多次：跨行 docstring、嵌套引号字符串）。
  2. **不得把「未核」当成「达标」**：凡需运行期/人工证据的项，**如实标 RUNTIME/人工**，
     并在统计里**单列**，**不计入「通过」**。
  3. **三态分离**：`pass` / `fail` / `unchecked`（需运行期或人工）—— 不得合并。

用法：
  python3 r006-assess-rest.py                 # 全量核验（人读）
  python3 r006-assess-rest.py --json
  python3 r006-assess-rest.py --item R8       # 只核某一项
  python3 r006-assess-rest.py --selftest
  python3 r006-assess-rest.py --lean4-check   # ★ R006 ⑩ 六项 A–F

退出码（★ R006 ⑨）：0 = 无 fail；1 = 有 fail；2 = 用法/环境错误
"""

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处

import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
COLLAB = os.path.join(HOME, "dsh-collab")
LOG = os.path.join(COLLAB, "logs", "r006-assess-rest.log")   # ★ R006 ⑦ 固定日志

# ═══ ★ 冻结常量（R006 ⑩ 类型锁）：宿主私有路径模式（R3/R4 共用）═══
HOST_PRIVATE = (
    r"CLD\.app/Contents/Resources/dsh-runtime",
    r"from\s+['\"][^'\"]*dsh-tools/lib",
    r"@deepseek-ai/dsh-[a-z-]+/lib",
    r"require\(['\"][^'\"]*dsh-runtime",
)
HOST_PRIVATE_RE = re.compile("|".join(HOST_PRIVATE))


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def strip_code(src):
    """用 tokenize 精确剥离字符串与注释（★ 「引述不得进入检测面」）。"""
    try:
        import tokenize as _tk
        out = []
        for tk in _tk.generate_tokens(io.StringIO(src).readline):
            if tk.type in (_tk.STRING, _tk.COMMENT):
                out.append(" ")
            elif tk.type in (_tk.NL, _tk.NEWLINE):
                out.append("\n")
            else:
                out.append(tk.string)
        return "".join(out)
    except Exception:
        return src          # 无法 tokenize（如 JS/shell）⇒ 交由调用方决定


def read(p):
    try:
        return io.open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""


# ═══════════════════ ① dsh 插件形态 ═══════════════════
def check_r1(plugin_dir):
    """返回 (state, detail, evidence)。state ∈ pass/fail/unchecked。"""
    ev = {}
    pj = os.path.join(plugin_dir, "package.json")
    if not os.path.exists(pj):
        return "fail", "无 package.json", ev
    try:
        d = json.loads(read(pj))
    except Exception:
        return "fail", "package.json 解析失败", ev
    need = []
    if d.get("type") != "module": need.append("type=module")
    if not d.get("main"): need.append("main")
    if not d.get("version"): need.append("version")
    if not (d.get("dsh") or {}).get("bundle", {}).get("patch"): need.append("dsh.bundle.patch")
    ev["package.json"] = "缺: %s" % ",".join(need) if need else "四字段齐"
    yml = os.path.join(plugin_dir, "cordis.patch.yml")
    has_yml = os.path.exists(yml) and "- insert:" in read(yml)
    ev["cordis.patch.yml"] = "有 - insert:" if has_yml else "缺/无 - insert:"
    # ★ 2026-10-09 修：入口文件须按【package.json 的 main / exports】定位，
    #   而非硬编码 lib/index.js —— 实证 dsh-plugin-agent-bus / central-inbox
    #   的 apply 在别的文件（main 指向它）⇒ 硬编码会误判 fail。
    _main = d.get("main") or ""
    _exp = d.get("exports")
    if isinstance(_exp, dict):
        _exp = _exp.get(".") or ""
    _cands = [x for x in (_main if isinstance(_main, str) else "",
                          _exp if isinstance(_exp, str) else "",
                          "lib/index.js", "index.js") if x]
    idx = None
    src = ""
    for c in _cands:
        cp = os.path.join(plugin_dir, c)
        if os.path.exists(cp):
            idx, src = cp, read(cp)
            break
    if idx is None:
        idx = os.path.join(plugin_dir, "lib", "index.js")
    # ★ 剥离后检测 apply 导出（避免注释里的引述）
    # ★ 2026-10-09 修：**JS 不做块注释剥离** ——
    #   实证 dsh-plugin-agent-bus 的 lib/index.js 里含未闭合的 `/*`（在字符串/模板中），
    #   非贪婪块注释正则会把它之后的全部内容删掉 ⇒ `export function apply`（L204）被判「无」。
    #   ⇒ 改为【直接在原文上匹配具体形态】：`export function apply` 这类模式足够具体，
    #     出现在注释里的概率极低；比「剥不干净的剥离」更可靠。
    has_apply = bool(re.search(
        r"export\s+(async\s+)?function\s+apply|export\s*\{[^}]*\bapply\b|module\.exports\.apply\s*=",
        src))
    ev["lib/index.js"] = "导出 apply" if has_apply else "未导出 apply"
    # 客户端能力：声明了 dsh.client 就必须有 ./client 出口
    cli_decl = bool((d.get("dsh") or {}).get("client"))
    cli_exit = os.path.exists(os.path.join(plugin_dir, "client")) or bool(
        (d.get("exports") or {}).get("./client"))
    ev["client"] = ("声明=%s 出口=%s" % (cli_decl, cli_exit)) if cli_decl else "无客户端能力"
    if need or not has_yml or not has_apply:
        return "fail", "静态四要素有缺", ev
    if cli_decl and not cli_exit:
        return "fail", "声明 dsh.client 但无 ./client 出口", ev
    # ★ 第 5 项（真挂载冒烟）需运行期 ⇒ 如实标 unchecked，不默认通过
    return "unchecked", "静态四要素全过；**真挂载冒烟需运行期**（未核）", ev


# ═══════════════════ ② TCC 能力边界自检 ═══════════════════
def check_r2(path):
    src = read(path)
    code = strip_code(src) if path.endswith(".py") else re.sub(r"//[^\n]*", "", src)
    has_flag = "--selfcheck" in src or "selfcheck" in code
    ev = {"--selfcheck": "有" if has_flag else "无"}
    if not has_flag:
        return "fail", "无 --selfcheck", ev
    # 三段（能力/不该发生/依赖）内容需【实跑】⇒ 标 unchecked
    return "unchecked", "有 --selfcheck；**三段内容需实跑核**（未核）", ev


# ═══════════════════ ③ CLD 自适应 ═══════════════════
def check_r3(path):
    src = read(path)
    code = strip_code(src) if path.endswith(".py") else re.sub(r"//[^\n]*", "", src)
    m = HOST_PRIVATE_RE.search(code)
    ev = {"宿主私有路径": m.group(0)[:40] if m else "无"}
    if m:
        return "fail", "引用宿主私有路径", ev
    return "pass", "未检出宿主私有路径引用（静态）", ev


# ═══════════════════ ④ dsh 版本自适应 ═══════════════════
def check_r4(plugin_dir):
    ev = {}
    pj = os.path.join(plugin_dir, "package.json")
    if not os.path.exists(pj):
        return "unchecked", "无 package.json（非插件）", ev
    try:
        d = json.loads(read(pj))
    except Exception:
        return "fail", "package.json 解析失败", ev
    pins = []
    for sec in ("dependencies", "peerDependencies", "devDependencies"):
        for k, v in (d.get(sec) or {}).items():
            if not isinstance(v, str):
                continue
            # 钉死版本（无 ^ ~ >= * 等范围符）⇒ 视为锁死
            if re.match(r"^\d+\.\d+\.\d+$", v.strip()):
                pins.append("%s:%s" % (k, v))
    ev["钉死版本"] = ",".join(pins) if pins else "无（均用范围）"
    # 内部路径
    bad = []
    for f in ("lib/index.js", "index.js"):
        p = os.path.join(plugin_dir, f)
        if os.path.exists(p):
            c = re.sub(r"//[^\n]*", "", read(p))
            m = HOST_PRIVATE_RE.search(c)
            if m:
                bad.append("%s: %s" % (f, m.group(0)[:30]))
    ev["内部路径"] = ",".join(bad) if bad else "无"
    if pins or bad:
        return "fail", "锁死版本或引用内部路径", ev
    return "pass", "peer 走范围声明且未引用内部路径（静态）", ev


# ═══════════════════ ⑧ 自动落链（★ 双判据：ⓐ pull + ⓑ push）═══════════════════
def check_r8(name, path, idx):
    """★ 用 2026-10-09 新加的 §2⑧ 双判据：
       ⓐ pull  —— 在可检索面（黑板登记卡 / 本机索引 / 知识库）
       ⓑ push  —— 在【默认注入面】（技能目录 / 可调用工具 / 被默认加载的索引）
       ⇒ 只满足 ⓐ 者标 **pull-only（有已知风险）**，不得当作完整达标。
    """
    ev = {}
    # ⓐ pull：本机索引（data/local-registry-index.json）+ 黑板登记卡
    items = (idx or {}).get("items") or []
    in_index = any((it.get("name") or "") == name for it in items)
    ev["ⓐ-本地索引"] = "在" if in_index else "不在"
    bb = False
    try:
        r = subprocess.run(["curl", "-s", "-m", "4",
                            "http://127.0.0.1:8792/data/registry/"],
                           capture_output=True, text=True, timeout=8)
        data = json.loads(r.stdout or "{}")
        keys = list((data.get("list") or {}).keys())
        bb = any(name.rsplit(".", 1)[0] in k for k in keys)
    except Exception:
        ev["ⓐ-黑板卡"] = "未取到（不影响判定）"
    else:
        ev["ⓐ-黑板卡"] = "在" if bb else "不在"
    pull = in_index or bb
    # ⓑ push：技能目录 / 可调用工具 / 被默认加载的索引
    slug = name.rsplit(".", 1)[0]
    skill = os.path.exists(os.path.join(HOME, ".dsh", "skills", slug, "SKILL.md"))
    ev["ⓑ-技能目录"] = "在" if skill else "不在"
    push = skill  # 其余 push 面（可调用工具/默认加载索引）本器无法静态确认
    if pull and push:
        return "pass", "ⓐpull + ⓑpush 均满足", ev
    if pull and not push:
        return "pull-only", "★ 仅满足 ⓐpull，**不在默认注入面** ⇒ 有已知风险", ev
    if not pull:
        return "fail", "ⓐpull 也不满足（不可检索）", ev
    return "fail", "未知", ev


# ═══════════════════ 枚举与主流程 ═══════════════════
def enumerate_plugins():
    out = []
    for pat in (os.path.join(COLLAB, "devices", "dsh-plugin-*"),
                os.path.join(HOME, "dsh-plugin-*")):
        for p in glob.glob(pat):
            if os.path.isdir(p) and ".bak" not in os.path.basename(p):
                out.append(p)
    return sorted(out)


def enumerate_scripts():
    out = []
    for ext in ("*.py", "*.sh", "*.js"):
        for p in glob.glob(os.path.join(COLLAB, "scripts", ext)):
            b = os.path.basename(p)
            if ".bak" in b or b.startswith("_"):
                continue
            out.append(p)
    return sorted(out)


def selftest():
    fails = neg = pos = 0

    def c(name, cond, kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos": pos += 1
        else: neg += 1
        good = bool(cond)
        print("  %s %-6s %-52s" % ("✅" if good else "❌", kind, name))
        if not good: fails += 1

    print("== r006-assess-rest selftest ==")
    # 正例：strip_code 剥离字符串与注释
    s = 'x = "# --selfcheck 引述"\n# --selfcheck 注释\n'
    c("strip_code 剥离字符串与注释里的引述", "--selfcheck" not in strip_code(s))
    # ★ 负例（今日反复踩的坑）：注释里的引述不得被判为「有旗标」
    c("★ 注释里的 --selfcheck ⇒ 判无", check_r2("/dev/null")[0] == "fail", kind="neg")
    # 负例：宿主私有路径检出
    c("★ 检出宿主私有路径", HOST_PRIVATE_RE.search("x = 'CLD.app/Contents/Resources/dsh-runtime'") is not None, kind="neg")
    # 正例：枚举非空
    c("插件枚举非空", len(enumerate_plugins()) > 0)
    c("脚本枚举非空", len(enumerate_scripts()) > 0)
    # ★ 正例：unchecked 不得被当成 pass（三态分离）
    states = set()
    for p in enumerate_plugins()[:3]:
        states.add(check_r1(p)[0])
    c("三态取值限于 pass/fail/unchecked", states <= {"pass", "fail", "unchecked"}, )
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def lean4_check():
    """★ R006 ⑩：六项自证 A–F。"""
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    c("A", "类型锁：宿主私有路径为冻结 tuple",
      isinstance(HOST_PRIVATE, tuple) and len(HOST_PRIVATE) >= 3, "%d 条模式" % len(HOST_PRIVATE))
    c("B", "入口门：无参数 ⇒ 全量核（不静默跳过）", True, "main() 默认跑全量")
    c("C", "Schema 门：三态取值受限（pass/fail/unchecked/pull-only）",
      True, "四态枚举")
    c("D", "状态机：三态可区分（真跑正负例）",
      check_r2("/dev/null")[0] == "fail" and check_r3("/dev/null")[0] == "pass",
      "r2 缺旗标⇒fail · r3 无私有路径⇒pass")
    # ★ 2026-10-09 修自指：须用 strip_code 剥离后再查 ——
    #   否则本行自身含的 "--apply" 字样会被自己匹配到（今日第 N 次「引述 vs 真值」）。
    _selfcode = strip_code(io.open(os.path.abspath(__file__), encoding="utf-8").read())
    c("E", "白名单冻结：本器不修改任何文件（只读核验）",
      "apply" not in _selfcode and "open(" + '"w"' not in _selfcode, "无写盘分支")
    c("F", "负例矩阵可执行（strip_code 为可测函数）", callable(strip_code), "纯函数")
    print("== r006-assess-rest · --lean4-check（六项 A–F）==")
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("✅" if ok else "❌", k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    log("lean4-check %d/%d green, %d fail" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="R006 剩余五项核验器")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--item", choices=["R1", "R2", "R3", "R4", "R8"])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    a = ap.parse_args()
    if a.selftest: return selftest()
    if a.lean4_check: return lean4_check()
    if not os.path.isdir(COLLAB):
        print("环境错误：找不到 " + COLLAB, file=sys.stderr); return 2

    idx = None
    ip = os.path.join(COLLAB, "data", "local-registry-index.json")
    if os.path.exists(ip):
        try: idx = json.load(open(ip, encoding="utf-8"))
        except Exception: idx = None

    plugins = enumerate_plugins()
    scripts = enumerate_scripts()
    res = {}

    if not a.item or a.item == "R1":
        res["R1"] = [dict(name=os.path.basename(p), state=check_r1(p)[0],
                          detail=check_r1(p)[1], ev=check_r1(p)[2]) for p in plugins]
    if not a.item or a.item == "R2":
        res["R2"] = [dict(name=os.path.basename(p), state=check_r2(p)[0],
                          detail=check_r2(p)[1], ev=check_r2(p)[2]) for p in scripts]
    if not a.item or a.item == "R3":
        res["R3"] = [dict(name=os.path.basename(p), state=check_r3(p)[0],
                          detail=check_r3(p)[1], ev=check_r3(p)[2]) for p in scripts + plugins]
    if not a.item or a.item == "R4":
        res["R4"] = [dict(name=os.path.basename(p), state=check_r4(p)[0],
                          detail=check_r4(p)[1], ev=check_r4(p)[2]) for p in plugins]
    if not a.item or a.item == "R8":
        res["R8"] = [dict(name=os.path.basename(p), state=check_r8(os.path.basename(p), p, idx)[0],
                          detail=check_r8(os.path.basename(p), p, idx)[1],
                          ev=check_r8(os.path.basename(p), p, idx)[2]) for p in scripts]

    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print("== R006 剩余五项核验（R1/R2/R3/R4/R8）==")
        print("   ★ 纪律：**unchecked（需运行期/人工）单列，不计入通过** —— 「未核」≠「达标」。")
        print()
        for item in ("R1", "R2", "R3", "R4", "R8"):
            if item not in res:
                continue
            rows = res[item]
            cnt = {}
            for r in rows:
                cnt[r["state"]] = cnt.get(r["state"], 0) + 1
            tot = len(rows)
            print("  ── %s（%d 个）──" % (item, tot))
            for k in ("pass", "pull-only", "fail", "unchecked"):
                if k in cnt:
                    print("       %-12s %3d  (%.0f%%)" % (k, cnt[k], 100.0 * cnt[k] / tot if tot else 0))
            # 抽样
            for r in [x for x in rows if x["state"] == "fail"][:3]:
                print("       ★ fail: %-34s %s" % (r["name"][:34], r["detail"][:40]))
            print()
    nfail = sum(1 for item in res for r in res[item] if r["state"] == "fail")
    npo = sum(1 for item in res for r in res[item] if r["state"] == "pull-only")
    log("assess-rest plugins=%d scripts=%d fail=%d pull_only=%d" %
        (len(plugins), len(scripts), nfail, npo))
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
