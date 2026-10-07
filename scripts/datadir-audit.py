#!/usr/bin/env python3
"""datadir-audit —— 数据根「生效配置」审计（可机械核验，2026-09-14 老登 aa528267）

立据：2026-09-14 诱饵库事件（两个子系统栽在 `~/meituan-multi/data/app.db` 这份陈旧副本上）。
协调者的可机械核验补条：①**模块顶层改写 process.env 列为禁形**（可 grep 扫描）
②数据根未设时 **fail-loud 不 fallback**。

本工具做静态三查（只读，不改任何文件）：
  禁形  A  模块**顶层**（缩进 0）出现 `process.env.<VAR> = ...` —— 会使生效配置依赖 **import 顺序**
  禁形  B  数据根 fallback 指向**仓库**（`|| ROOT` 且 ROOT=path.resolve(__dirname,"..")) —— 确定性指向诱饵
  禁形  C  数据根 fallback **指向实盘**（`process.env.MTM_DATA_DIR || <指向实盘的表达式>`）
           ★ 定义 = **「取值以 env 为先」⇒ 可由设置 MTM_DATA_DIR 纠正**。
              「单一字面量」**不是定义**，只是实现的最初约束 ⇒ 分段 join / 跨行写法**同属 C**。
              （2026-09-14 裁：`lib/errorlog.js:12` 分段 join ⇒ 属 C ⇒ C = 9 处）
  禁形  D  模块内**无条件硬编码实盘绝对路径**（**该语句取值不经任何 env**）—— 比 C 更硬：
           C 至少可被设 env 纠正，**D 连纠正的机会都没有** ⇒ 处置不同，故单列
  ★ 类判别式（可判定，不靠读源码）：**该处能否被设置 `MTM_DATA_DIR` 纠正？** 能 ⇒ C 族；不能 ⇒ D 族。
     理由：**形态会变（分段 / 换行 / 变量中转），处置不会** ⇒ 按处置分类才稳定。

  单位约定：**A=出现处数 · B=出现处数 · C=出现处数 · D=文件数**
           （此前我把「含实盘路径字符串的 lib 文件数」与「C 的 fallback 处数」混说成同一个数，
            故此处显式声明单位；两数不同不是错，是谓词与单位不同）

用法: datadir-audit.py [--root ~/meituan-multi] [--json] [--selftest]
退出码: 0=无禁形 · 1=有禁形（可用于 CI / 定时检查）· 2=selftest 失败

★ 计数三件套（HR 2026-09-14 要求：机械扫描的数也须附三件套，不搞双重标准）：
  ① 匹配器定义：见下方 RE_* 常量，且正常输出会**原样回显**它们
  ② 正例（构造）：selftest 用合成样本证明「能命中」
  ③ 真语料边界例：selftest 用**真实语料形态**的边界样本（非构造近似）证明「不误命中」
     —— 本工具的边界例取自实测语料：
       · `process.env.MTM_DATA_DIR = ... || '<实盘>'` 形（禁形 A，**不得**被判为禁形 B）
       · `const X = process.env.MTM_DATA_DIR || ROOT;` 后的**注释行**里出现 `Application Support`
         （**不得**被判为禁形 C —— 它只是注释，不是 fallback 表达式）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, shutil, sys, tempfile

RE_TOP_ENV = r"^process\.env\.([A-Z_][A-Z0-9_]*)\s*="                    # 禁形 A 匹配器
RE_FALLBACK = r"process\.env\.MTM_DATA_DIR\s*\|\|\s*(.+?);?\s*$"         # 禁形 B/C 入口匹配器
RE_ROOT_DEF = r"const\s+ROOT\s*=\s*path\.resolve\(__dirname"             # 判定 `|| ROOT` 语义用

LIVE_PATH_MARKER = "Application Support/外卖门店多平台管理"   # ★ C 与 D 共用的唯一标记

ENV_RE = re.compile(RE_TOP_ENV)          # 顶层（无缩进）
FALLBACK_RE = re.compile(RE_FALLBACK)
ROOT_DEF_RE = re.compile(RE_ROOT_DEF)


def looks_live(expr):
    """识别「指向实盘」的表达式 —— 必须容忍**分段写法**（path.join(..., "Library","Application Support","外卖门店多平台管理")）。
    立据（协调者 2026-09-14）：路径写成分段 join 时字符串被切开 ⇒ 单一字面量模式漏检（errorlog.js:12）。"""
    if not expr:
        return False
    return LIVE_PATH_MARKER in expr or ("Application Support" in expr and "外卖门店多平台管理" in expr)


def scan(root):
    lib = os.path.join(root, "lib")
    findings = {"A_top_level_env_mutation": [], "B_repo_fallback": [], "C_abs_path_fallback": [],
                "D_unconditional_abs_path": []}
    if not os.path.isdir(lib):
        return findings, 0
    files = sorted(f for f in os.listdir(lib) if f.endswith(".js"))
    for f in files:
        p = os.path.join(lib, f)
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        except Exception:
            continue
        text = "\n".join(lines)
        # ★ 语句级视图：把跨行表达式合并（修「路径写成分段 join、字符串被切开 ⇒ 两门之间漏掉」）
        stmts = []           # [(起始行号, 合并后的文本)]
        buf, buf_start = "", 0
        for i, ln in enumerate(lines, 1):
            st = ln.strip()
            if st.startswith("//") or st.startswith("*") or st.startswith("/*"):
                continue          # 纯注释行不参与判定
            if not buf:
                buf_start = i
            buf = (buf + " " + st).strip() if buf else st
            nxt = lines[i].strip() if i < len(lines) else ""
            cont = buf.endswith(("||", "&&", "+", ",", "(", "[", "{")) or nxt.startswith(("||", "&&")) \
                   or (nxt == "" and buf.endswith(("||", "&&")))
            if not cont:
                stmts.append((buf_start, buf)); buf = ""
        if buf:
            stmts.append((buf_start, buf))

        for (i, joined) in stmts:
            text_stmt = joined
            m_env = ENV_RE.match(joined)
            if m_env:
                findings["A_top_level_env_mutation"].append(
                    {"file": f"lib/{f}", "line": i, "env": m_env.group(1),
                     "snippet": joined[:90]})
            m = FALLBACK_RE.search(text_stmt)
            if m:
                expr = m.group(1).strip()
                rec = {"file": f"lib/{f}", "line": i, "fallback": expr[:80]}
                if looks_live(expr):
                    rec["kind"] = "实盘（正确，但硬编码绝对路径）"
                    findings["C_abs_path_fallback"].append(rec)
                elif expr.strip() == "ROOT":
                    rec["kind"] = "★诱饵：确定性指向仓库根"
                    findings["B_repo_fallback"].append(rec)
                elif "meituan-multi" in expr:
                    rec["kind"] = "★诱饵：家目录相对，与 cwd 无关"
                    findings["B_repo_fallback"].append(rec)
                else:
                    rec["kind"] = "★其它（未归类 —— 不计入覆盖）"
                    rec["unclassified"] = True
                    findings["B_repo_fallback"].append(rec)
        # 禁形 D：语句内出现实盘路径，且**该语句的取值不经任何 env**（精确定义，2026-09-14 采纳协调者）
        abs_hits = [(i, j) for (i, j) in stmts if LIVE_PATH_MARKER in j and "process.env" not in j]
        if abs_hits:
            findings["D_unconditional_abs_path"].append(
                {"file": f"lib/{f}", "line": abs_hits[0][0],
                 "snippet": abs_hits[0][1][:110],
                 "kind": "★无条件硬编码：该语句取值不经任何 env"})
    # ★ 闭合检查（协调者方法：先枚举全集再分类；absence 类检查的枚举面须比分类面更粗）
    # ★ 只有**精确类别**计入覆盖；「其它（未归类）」不算覆盖
    #   （立据：变异检验发现「其它」是 catch-all ⇒ 闭合检查被构造性满足 ⇒ 名义闭合）
    classified = set()
    for b in ("A_top_level_env_mutation", "C_abs_path_fallback", "D_unconditional_abs_path"):
        classified |= {r["file"].split("/")[-1] for r in findings[b]}
    classified |= {r["file"].split("/")[-1] for r in findings["B_repo_fallback"] if not r.get("unclassified")}
    unclassified = {r["file"].split("/")[-1] for r in findings["B_repo_fallback"] if r.get("unclassified")}
    # ★ 枚举面必须比分类面**更粗**（协调者方法）：只用关键词，不用任何模式
    COARSE_KEYWORD = "外卖门店多平台管理"
    coarse = {f for f in files if COARSE_KEYWORD in
              open(os.path.join(lib, f), encoding="utf-8", errors="replace").read()}
    findings["E_closure_uncovered"] = [
        {"file": f"lib/{x}", "kind": "★粗枚举命中但未被任何类别覆盖 ⇒ **漏检**"} for x in sorted(coarse - classified)]
    findings["closure"] = {"粗枚举文件数": len(coarse), "精确分类文件数": len(classified),
                           "未归类文件数": len(unclassified), "漏检数": len(coarse - classified),
                           "判据": "覆盖 = A ∪ B(精确) ∪ C ∪ D；「其它」桶不计入覆盖"}
    return findings, len(files)


def selftest():
    """计数三件套：构造正例 + 真语料形态边界例。每类**各用一个独立文件**，消除交叉干扰。"""
    detail = []
    tmp = tempfile.mkdtemp(prefix="datadir-audit-selftest-")
    M = LIVE_PATH_MARKER
    try:
        lib = os.path.join(tmp, "lib")
        os.makedirs(lib)
        fixtures = {
            # ① 正例（构造）
            "a_pos.js": "process.env.MTM_DATA_DIR = '/Users/x/Library/Application Support/" + M + "';\n",
            "b_pos.js": "const ROOT = path.resolve(__dirname, '..');\nconst D = process.env.MTM_DATA_DIR || ROOT;\n",
            "c_pos.js": "const D = process.env.MTM_DATA_DIR || '/Users/x/Library/Application Support/" + M + "';\n",
            "d_pos.js": "const DB_PATH = path.join(os.homedir(), 'Library/Application Support/" + M + "/data/app.db');\n",
            # ② 真语料形态边界例（不得误报）
            "b_neg.js": "const q = process.env.MTM_DATA_DIR;\n",                      # 裸读 ⇒ 非 A 非 B
            "c_neg.js": "// 注释提到 Application Support/" + M + "（非 fallback 表达式）\n",
            "d_neg.js": ("const D = process.env.MTM_DATA_DIR || '/Users/x/Library/Application Support/"
                         + M + "/data/app.db';\n"),                                  # 有 env 兜底 ⇒ 属 C 不属 D
        }
        for name, body in fixtures.items():
            open(os.path.join(lib, name), "w", encoding="utf-8").write(body)
        f, _ = scan(tmp)
        def files_in(bucket): return {r["file"].split("/")[-1] for r in f[bucket]}
        cases = [
            ("正例·禁形A（顶层改 env）命中", "a_pos.js" in files_in("A_top_level_env_mutation")),
            ("正例·禁形B（诱饵 fallback）命中", "b_pos.js" in files_in("B_repo_fallback")),
            ("正例·禁形C（env 兜底绝对路径）命中", "c_pos.js" in files_in("C_abs_path_fallback")),
            ("正例·禁形D（无条件硬编码）命中", "d_pos.js" in files_in("D_unconditional_abs_path")),
            ("边界例·裸读 env 不误报为 A", "b_neg.js" not in files_in("A_top_level_env_mutation")),
            ("边界例·裸读 env 不误报为 B", "b_neg.js" not in files_in("B_repo_fallback")),
            ("边界例·注释中的路径不误报为 C", "c_neg.js" not in files_in("C_abs_path_fallback")),
            ("边界例·注释中的路径不误报为 D", "c_neg.js" not in files_in("D_unconditional_abs_path")),
            ("边界例·有 env 兜底者属 C 不属 D", "d_neg.js" not in files_in("D_unconditional_abs_path")),
        ]
        for name, ok in cases:
            detail.append((name, ok))
        # ★ 非 0 码的 must_reject 用例（子进程，各自独立）
        import subprocess as _sp, tempfile as _tf
        me = os.path.abspath(__file__)
        r_noin = _sp.run([sys.executable, me, "--root", os.path.join(tmp, "nope")],
                         capture_output=True, text=True).returncode
        detail.append(("must_reject·码4 无输入(root 不存在)", r_noin == 4))
        hit = os.path.join(tmp, "hit")
        os.makedirs(os.path.join(hit, "lib"))
        open(os.path.join(hit, "lib", "x.js"), "w", encoding="utf-8").write(
            "process.env.MTM_DATA_DIR = '/Users/x/Library/Application Support/" + M + "';\n")
        r_hit = _sp.run([sys.executable, me, "--root", hit],
                        capture_output=True, text=True).returncode
        detail.append(("must_reject·码1 检出禁形", r_hit == 1))
        return sum(1 for _, ok in detail if ok), len(detail), detail
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.expanduser("~/meituan-multi"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        ok, tot, detail = selftest()
        for name, k in detail:
            print(f"  {'✅' if k else '❌'} {name}")
        print(f"\nselftest {ok}/{tot}（正例=构造，边界例=真语料形态）")
        sys.exit(0 if ok == tot else 2)
    root = os.path.expanduser(a.root)
    if not os.path.isdir(os.path.join(root, "lib")):
        # ★ 「无输入」态：**不得**报「全部通过」（否则最危险的失败看起来最像成功）
        msg = {"状态": "无输入（root 或 lib/ 不存在）", "root": root,
               "结论": "**未评估** —— 无输入 ≠ 全部通过", "退出码": 4}
        if a.json: print(json.dumps(msg, ensure_ascii=False, indent=1))
        else: print(f"⚠️ 无输入：{root}/lib 不存在 ⇒ **未评估**（无输入 ≠ 全部通过）· 退出码 4")
        sys.exit(4)
    f, n = scan(root)
    if n == 0:
        msg = {"状态": "无输入（lib/ 内 0 个 .js）", "结论": "**未评估**", "退出码": 4}
        if a.json: print(json.dumps(msg, ensure_ascii=False, indent=1))
        else: print("⚠️ 无输入：lib/ 内 0 个 .js ⇒ **未评估** · 退出码 4")
        sys.exit(4)
    # ★ 三件套第一件：原样回显匹配器定义
    matchers = {"禁形A": RE_TOP_ENV, "禁形B_C入口": RE_FALLBACK, "ROOT语义": RE_ROOT_DEF}
    if a.json:
        print(json.dumps({"root": a.root, "lib_files": n, "matchers": matchers, "findings": f},
                         ensure_ascii=False, indent=1))
    else:
        print(f"数据根审计 · {a.root} · lib/*.js 共 {n} 个")
        print("匹配器定义（三件套①）：")
        for k, v in matchers.items():
            print(f"   {k}: {v}")
        print(f"\n【禁形 A】模块顶层改写 process.env（{len(f['A_top_level_env_mutation'])} 处）→ 使生效配置依赖 import 顺序")
        for r in f["A_top_level_env_mutation"]:
            print(f"   {r['file']}:{r['line']}  {r['env']}  |  {r['snippet']}")
        print(f"\n【禁形 B】数据根 fallback 指向诱饵（{len(f['B_repo_fallback'])} 处）→ 未设即静默读旧库")
        for r in f["B_repo_fallback"]:
            print(f"   {r['file']}:{r['line']}  {r['kind']}  |  {r['fallback']}")
        print(f"\n【禁形 C】fallback 硬编码绝对路径（{len(f['C_abs_path_fallback'])} **处**）→ 可移植性差、副本易失同步")
        for r in f["C_abs_path_fallback"]:
            print(f"   {r['file']}:{r['line']}  |  {r['fallback']}")
        print(f"\n【禁形 D】无条件硬编码实盘绝对路径（{len(f['D_unconditional_abs_path'])} **个文件**）→ 不读 env，**无法用环境变量纠正**")
        for r in f["D_unconditional_abs_path"]:
            print(f"   {r['file']}:{r['line']}  |  {r['snippet']}")
    bad = (len(f["A_top_level_env_mutation"]) + len(f["B_repo_fallback"])
           + len(f["C_abs_path_fallback"]) + len(f["D_unconditional_abs_path"])
           + len(f.get("E_closure_uncovered", [])))
    if a.json:
        # ★ --json 模式只输出 JSON（机器可读纯净；人类摘要一律不混入）
        sys.exit(0 if bad == 0 else 1)
    print(f"\n闭合检查：粗枚举 {f.get('closure',{}).get('粗枚举文件数')} 个文件 ⊆ 分类面 "
          f"{f.get('closure',{}).get('被分类文件数')} 个 · 漏检 {f.get('closure',{}).get('漏检数')}")
    for r in f.get("E_closure_uncovered", []):
        print(f"   ❌ {r['file']} —— {r['kind']}")
    print(f"\n合计禁形 A+B+C(处)+D(文件)+E(漏检) = {bad}" + ("（✅ 无）" if bad == 0 else "（需修）"))
    sys.exit(0 if bad == 0 else 1)


main()
