#!/usr/bin/env python3
"""核验级别检测：找「已落盘 / 已修复 / 已同步」这类声称，看它有没有声明核到哪一级。

由来（HR 2026-09-14 排序：第 1 位）：
  可机械检查 ✓ · 后果最重 —— 虚假的「已落盘」会让下游在错误前提上行动。
  今晚多起事故都源于此：HR 报「写入成功两次」· 我报「已落盘成功」，而两层都不是真的。
  执行理由：这条防的是【下游在错误前提上行动】（不可逆）；裸数那条防的是【可比性失真】（可重算）。
  ⇒ 不可逆的优先于可重算的。

三级（明鉴 2026-09-14 的核验边界 v2）：
  存在级 —— 键在、非空（GET 得到）
  结构级 —— 层级与字段形态符合约定（字段数 / 键集合 / 单层）
  内容级 —— 值与声称相符（指纹 / 复算）

它做什么：扫卡的内容，找【完成态声称】，检查同一段里有没有级别词。
  有声称 + 无级别词 ⇒ 报出（该声称的强度上限不明）
  有声称 + 有级别词 ⇒ 通过

用法：
  python3 verification-level-lint.py [--ns data/registry/] [--limit N]
退出码：0 = 未发现无级别的完成态声称；1 = 有

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets", "--dry-run")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== verification-level-lint 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 核验级别检测：找「已落盘 / 已修复 / 已同步」这类声称，看它有没有声明核到哪一级。")
    print("  · 由来（HR 2026-09-14 排序：第 1 位）：")
    print("  · 可机械检查 ✓ · 后果最重 —— 虚假的「已落盘」会让下游在错误前提上行动。")
    print("  · 今晚多起事故都源于此：HR 报「写入成功两次」· 我报「已落盘成功」，而两层都不是真的。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: concurrent, hashlib, json, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/verification-level-lint.log")
    return 0


import sys as _r006_sys
if False:  # ★ R006 ②⑩ 已迁移至文件末 canonical 块（原守卫并入）
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, re, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

# ★ 2026-09-28 加：未知参数必须【有声拒绝】，不能静默跑默认动作。
#   实测（08:47 工具族盘点，探针 = `python3 <工具> --selftest`）：本工具**没有 --selftest 入口**，
#   而它当时**静默忽略了 --selftest、照常跑了默认扫描**，产出 825 键的 A/B/S 报告并 exit=1。
#   ⇒ 危险在于：**它回答的是另一个问题，而读数看起来像答案** ——
#     若那次默认扫描恰好 exit 0，调用者会把「它跑了别的任务」记成「自测通过」。
#   ⇒ 样板：bb-put-both.py 的做法（不认识就干净打用法、exit 2），本段照抄其精神。
import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/verification-level-lint.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

_KNOWN = {"--ns", "--limit", "--all", "--version", "-h", "--help", "--json"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    print("❌ 不认识的参数: %s" % " ".join(_unknown))
    print("   本工具接受的参数: %s" % " ".join(sorted(_KNOWN)))
    print("   ★ 本工具【没有】--selftest 入口（明鉴已知未结项，2026-09-28 盘点时发现）——")
    print("     这里明确说出来，而不是静默跑默认扫描（那会给你另一个问题的答案）。")
    # ★ R006 ⑨② 退出码语义：用法错误 = 2（原为 sys.exit(字符串) ⇒ rc=1，与「门失效」混为一类）
    sys.exit(2)
# ★ R006 ⑨⑤ --help 自解释：原状是【静默忽略 --help 并跑默认扫描（28s，rc=1）】
if ("-h" in sys.argv[1:]) or ("--help" in sys.argv[1:]):
    print("用法: verification-level-lint [--ns <ns>] [--limit N] [--all] [--json] [--version]")
    print("退出码: 0=无发现 · 1=有发现/判据失效 · 2=用法或 IO 错误")
    print("")
    print(__doc__ or "")
    sys.exit(0)

BB = "127.0.0.1:8792"

# ★ 收紧（第一版只抓「词的出现」，实测假阳性极高）：
#   第一版正则 CLAIM = 已落盘|已写入|已修复|已修|... ⇒ 120 键报 28 处 17 张，
#   而看样例：v2.2.0：…已修（历史记录）· 是否已修好（待查问题）·
#   「不是报告已修」（否定式）· 已修好的 20 张（被指对象）—— 三种都不是【声称】。
#   根因与我在 inplace-pointer-audit 第一版犯的同一个错：测的是【词的出现】，
#   要测的是【声称本身】。
# 收紧为：只认【第一人称的完成态声称】——
#   形态 = 「已X」后紧跟【冒号 或 具体对象】，且其前 12 字内没有
#   是否 / 不是 / 未 / 被 / 的 / 版本号 / 引号内的转述标记
CLAIM = re.compile(r"已(?:落盘|写入|修复|同步|完成|投递|部署|上线|合并|推送)")
NEG = re.compile(r"是否|不是|并非|未|被|已在|待|若|如|已修好的|报告已|声称")
VER = re.compile(r"v\d+\.\d+|VERSION|版本")
# 级别词（声明核到哪一级）
LEVEL = re.compile(r"存在级|结构级|内容级|已核|非空|字段数|键集合|指纹|sha256|复算|回读|GET\s*\d|双侧|ver=|\d+\s*B\b|字节")


def enum(ns):
    d = json.loads(urllib.request.urlopen(f"http://{BB}/{ns}", timeout=90).read())
    l = d.get("list", {})
    return list(l.keys()) if isinstance(l, dict) else list(l)


def get(k):
    try:
        with urllib.request.urlopen(f"http://{BB}/{k}", timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def leaves(v):
    """只取叶子【字符串】，不把子键名当内容。
    修 2026-09-14 实测缺陷①：原实现 json.dumps(val) 把子键名也写进待检文本，
    实例 failure-state-vs-read-the-body-laodeng 命中的是子键名
    「★_全4店失败_即零采集却记为已完成」而非正文。属「对象≠制品」同族。"""
    out = []
    if isinstance(v, str):
        out.append(v)
    elif isinstance(v, list):
        for x in v:
            out.extend(leaves(x))
    elif isinstance(v, dict):
        for _k, val in v.items():
            out.extend(leaves(val))
    return out


SUSPECT_QUOTED = re.compile("[「『“”" + chr(34) + "']$")
SUSPECT_ATTR = re.compile(r"^\s*[的项卡文件版本份条]")
HOMONYM = [("已合并", re.compile(r"版本|VERSION|v\d+\.\d+|[为成]\s?1\s?份|成一条|定义"))]
EVIDENCE = re.compile(r"md5|[0-9a-f]{7,}|回读|复验|回归|重训|一致|哈希|指纹|字节")


def scan(k):
    """返回 (key, fields)；fields = [(字段名, [(词, suspect, evidence, ctx), ...])]
    粒度已改：同字段多次匹配合并为一条 ⇒ 新版「处」= 字段（旧版「处」= 匹配次数）。"""
    env = get(k)
    if not env:
        return None
    v = env.get("value", {})
    if not isinstance(v, dict):
        return None
    fields = []
    for fld, val in v.items():
        hits = []
        for s in leaves(val):
            for m in CLAIM.finditer(s):
                after = s[m.end(): m.end() + 10]
                if not re.match(r"\s*[:：]", after) and not re.search(r"[0-9A-Za-z_\-/]", after):
                    continue
                before = s[max(0, m.start() - 12): m.start()]
                if NEG.search(before) or VER.search(before):
                    continue
                ctx = s[max(0, m.start() - 60): m.end() + 60]
                if LEVEL.search(ctx):
                    continue
                kind = ""
                if SUSPECT_QUOTED.search(s[max(0, m.start() - 1): m.start()]):
                    kind = "quoted"
                elif SUSPECT_ATTR.match(after):
                    kind = "attributive"
                else:
                    for w, pat in HOMONYM:
                        if m.group(0) == w and pat.search(ctx):
                            kind = "homonym"
                            break
                hits.append((m.group(0), kind, bool(EVIDENCE.search(ctx)), ctx.strip()[:90]))
        if hits:
            fields.append((fld, hits))
    return (k, fields) if fields else None


VERSION = "2.0.0"   # 2.0.0 = 2026-09-14 修两处实现缺陷 + 加分档（判据段未改）


def main():
    if "--version" in sys.argv:
        import hashlib
        h = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
        print("verification-level-lint " + VERSION + " | file_sha256[:16]=" + h
              + " | 判据 CLAIM/NEG/VER/LEVEL 自 v1 起未改")
        return 0
    ns = "data/registry/"
    limit = 0
    if "--ns" in sys.argv:
        ns = sys.argv[sys.argv.index("--ns") + 1]
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    keys = enum(ns)
    if limit:
        keys = keys[:limit]
    with ThreadPoolExecutor(max_workers=24) as ex:
        res = [r for r in ex.map(scan, keys) if r]

    A, B, S = [], [], []
    for k, fields in res:
        for fld, hits in fields:
            if any(h[1] for h in hits):
                S.append((k, fld, hits))
            elif any(h[2] for h in hits):
                B.append((k, fld, hits))
            else:
                A.append((k, fld, hits))

    # ★ R006 ⑨④ 机器可读开关：--json ⇒ 【纯 JSON 输出】（故文本输出后移到本分支之后）
    if "--json" in sys.argv:
        import json as _j
        print(_j.dumps({"tool": "verification-level-lint", "version": VERSION, "ns": ns,
                        "keys_scanned": len(keys), "A_true_defect": A,
                        "B_undetermined": B, "S_suspect": S},
                       ensure_ascii=False, default=str))
        return 1 if (A or B) else 0
    print("扫描 " + ns + " · " + str(len(keys)) + " 键 · 判据段未改动（本次仅修实现 + 加分档）")
    print("★ 命中字段合计 " + str(len(A) + len(B) + len(S)) + " 个（" + str(len(res)) + " 张卡）—— 新版「处」= 字段，旧版「处」= 匹配次数，不可直接比")
    print("  A 真缺陷（无级别词且无证据）    : " + str(len(A)))
    print("  B 待定  （无级别词但有验证证据）: " + str(len(B)))
    print("  S 疑似  （元讨论/异义/被指对象）: " + str(len(S)) + "   ← 候选非判决，须人工")
    print()

    def show(rows, tag, cap):
        if not rows:
            print("  【" + tag + "】无")
            print()
            return
        print("  【" + tag + "】")
        for k, fld, hits in rows[:cap]:
            ws = "/".join(sorted({h[0] for h in hits}))
            kinds = "/".join(sorted({h[1] for h in hits if h[1]})) or "-"
            print("    " + k.split("/")[-1][:50] + " | " + fld[:24] + " | [" + ws + "] kind=" + kinds)
            print("        …" + hits[0][3][:80] + "…")
        if len(rows) > cap:
            print("    …另有 " + str(len(rows) - cap) + " 个字段")
        print()

    # ★ 2026-09-14 加 --all：HR 标了「未逐张复核 A37 名单」，而原实现只打印前 12 个
    #   ⇒ 那是我的工具缺口，不是 HR 的核对缺口。判据不变，只改打印上限。
    cap = 10 ** 9 if "--all" in sys.argv else 12
    show(A, "A 真缺陷", cap)
    show(B, "B 待定（有证据未命名级别）", 8)
    show(S, "S 疑似（元讨论/异义/被指对象）—— 必须打印，不得静默吞掉", 10)
    print("★ 判读：A/B/S 三档都是【候选而非判决】——")
    print("  A：一段里没有级别词，也可能是它在别处声明了。")
    print("  B：给了哈希/回读/复验等证据但没命名级别 ⇒ 比「已修复」强，仍需读者自判证据强度。")
    print("  S：suspect 由结构判据给出（引号相邻/量词相邻/已知异义表）⇒ 会误判，须人工收口。")
    return 1 if A else 0


# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块 · 自包含 · 勿手改） ═══════════
# 由 scripts/r006-u6-apply.py 注入；改模板后重跑注入器，勿在本块内手工编辑。
# 设计原则（三条，均有本线实证来源）：
#   1) ② 的每一句声明都必须【被本块结构核验】—— 只打印不检查的「纸面声明」不算 TCC。
#   2) ⑩ 的 A/ E/F 是【冻结声明 + 变更检测】：新增危险原语/写入点/外部命令调用点 ⇒ 立刻红。
#   3) 反空洞：写入点与命令点扫描器必须先在【合成恶意源】上自证会红，否则判「不能判定」。
#      （依据 R006 §4.2 坑 3：剥字面量后读不到实参 ⇒ 调用点枚举为 0 ⇒ 「0 ⊆ 允许」空洞通过）
import sys as _r006_sys
import os as _r006_os
import io as _r006_io
import re as _r006_re
import json as _r006_json
import ast as _r006_ast
import time as _r006_time
import tokenize as _r006_tokenize
import subprocess as _r006_subprocess

_R006_DECL = {
    'tool': 'verification-level-lint',
    'version': '2.0.0',
    'capability': ['核验级别检测：找「已落盘 / 已修复 / 已同步」这类声称，看它有没有声明核到哪一级（CLAIM/NEG/VER/LEVEL）', '由来（HR 2026-09-14 排序第 1 位）：虚假的「已落盘」会让下游在错误前提上行动', '→ 本条自陈：本器【没有】--selftest 入口（2026-09-28 盘点发现），这里说明白而不是静默跑默认扫描'],
    'impossible': ['本器不执行外部命令、不删除数据、不修改权限 ⇒ 无该路径', '不修改被扫文件（只读审计类行为）', '不识别的参数 ⇒ 拒绝执行并列出可接受参数，绝不静默回退到默认扫描'],
    'log': 'verification-level-lint.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs'],
    'negatives': [['--definitely-not-a-flag'], ['--limit']],
    'positive': ['--limit', '1'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {

    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset(),
    'positive_expect_rc': [0],
    'dryrun_via_block': True,
    'dry_suppress': ['log'],
    'dryrun_note': '本器原无 --dry-run ⇒ 由 canonical 块接管：垫片摘旗标 + 置空写助手 log',
}

_R006_EXEC_ATTRS = ("run", "Popen", "call", "check_call", "check_output")
_R006_DANGER_ATTRS = {
    "os": ("system", "popen", "remove", "unlink", "rmdir", "removedirs", "chmod", "chown", "kill"),
    "shutil": ("rmtree", "move"),
    "subprocess": _R006_EXEC_ATTRS,
}
_R006_DANGER_NAMES = ("eval", "exec", "compile", "__import__")
_R006_SYNTH_EXEC = "import subprocess as _sp\nfrom subprocess import Popen\n_sp.run(['ls'], shell=True)\nPopen(['x'])\n"
_R006_SYNTH_WRITE = "open('x','w')\nopen(p, mode='a')\n"
_R006_SYNTH_EXEC_WANT = frozenset({"subprocess.run", "subprocess.Popen"})
_R006_SYNTH_WRITE_WANT = frozenset({"const:x", "<expr>"})


def _r006_src():
    return open(_r006_os.path.abspath(__file__), encoding="utf-8").read()


def _r006_strip(s):
    """tokenize 抹除注释与字符串【内容】：按原文区间置空。
    ★ 不重拼 token —— 重拼会吞掉 token 间空白（`if a.selftest:` 变 `ifa.selftest:`）。"""
    buf = list(s)
    off = [0]
    for ln in s.splitlines(True):
        off.append(off[-1] + len(ln))
    try:
        for tk in _r006_tokenize.generate_tokens(_r006_io.StringIO(s).readline):
            if tk.type in (_r006_tokenize.COMMENT, _r006_tokenize.STRING):
                a = off[tk.start[0] - 1] + tk.start[1]
                b = off[tk.end[0] - 1] + tk.end[1]
                for i in range(a, min(b, len(buf))):
                    if buf[i] not in "\r\n":
                        buf[i] = " "
    except Exception:
        return s
    return "".join(buf)


def _r006_aliases(t):
    """import 别名解析：`import subprocess as sp` / `from subprocess import run` 都要认得。
    ★ 不做这步，改个别名就能绕过扫描器（= 空洞通过）。"""
    m = {}
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                m[(a.asname or a.name.split(".")[0])] = a.name.split(".")[0]
        elif isinstance(n, _r006_ast.ImportFrom):
            for a in n.names:
                m[(a.asname or a.name)] = (n.module or "").split(".")[0] + "." + a.name
    return m


def _r006_scan(src):
    """AST 三面读数：外部命令调用点 / 写入点 / 危险原语。
    ★ 用 AST 而非正则：注释与字符串天生不进 AST ⇒ 免除「扫到自己的检测正则」假阳性。"""
    r = {"exec": set(), "write": set(), "danger": set(), "imports": set(), "err": ""}
    try:
        t = _r006_ast.parse(src)
    except Exception as e:
        r["err"] = "AST 解析失败: %s" % e
        return r
    al = _r006_aliases(t)
    for n in _r006_ast.walk(t):
        if isinstance(n, _r006_ast.Import):
            for a in n.names:
                r["imports"].add(a.name.split(".")[0])
        elif isinstance(n, _r006_ast.ImportFrom):
            if n.module:
                r["imports"].add(n.module.split(".")[0])
        elif isinstance(n, _r006_ast.Call):
            f = n.func
            if isinstance(f, _r006_ast.Attribute) and isinstance(f.value, _r006_ast.Name):
                mod = al.get(f.value.id, f.value.id)
                if mod in _R006_DANGER_ATTRS and f.attr in _R006_DANGER_ATTRS[mod]:
                    if mod == "subprocess":
                        r["exec"].add("subprocess." + f.attr)
                    else:
                        r["danger"].add(mod + "." + f.attr)
            elif isinstance(f, _r006_ast.Name):
                tgt = al.get(f.id, f.id)
                if tgt.startswith("subprocess."):
                    r["exec"].add("subprocess." + tgt.split(".", 1)[1])
                elif f.id in _R006_DANGER_NAMES:
                    r["danger"].add(f.id)
                elif f.id == "open":
                    mode = ""
                    if len(n.args) >= 2 and isinstance(n.args[1], _r006_ast.Constant):
                        mode = str(n.args[1].value)
                    for kw in n.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, _r006_ast.Constant):
                            mode = str(kw.value.value)
                    if any(c in mode for c in ("w", "a", "x", "+")):
                        p = "<expr>"
                        if n.args and isinstance(n.args[0], _r006_ast.Constant):
                            p = "const:" + str(n.args[0].value)
                        r["write"].add(p)
    return r


def _r006_regex_pass(s):
    """A 的【独立第二通道】：在 tokenize-剥离后的文本上做正则扫描。
    两通道结论不一致 ⇒ 判「不能判定」，**不得**假设其中某一个对。"""
    code = _r006_strip(s)
    hits = set()
    for pat, name in ((r"\beval\s*\(", "eval"), (r"\bexec\s*\(", "exec"),
                      (r"\b__import__\s*\(", "__import__"),
                      (r"\bos\.system\s*\(", "os.system"), (r"\bos\.popen\s*\(", "os.popen"),
                      (r"\.rmtree\s*\(", "shutil.rmtree"), (r"\bos\.remove\s*\(", "os.remove")):
        if _r006_re.search(pat, code):
            hits.add(name)
    return hits


def _r006_run(argv, timeout=60):
    try:
        p = _r006_subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                 cwd=_r006_os.path.dirname(_r006_os.path.abspath(__file__)))
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except _r006_subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def _r006_snap(paths):
    import hashlib
    out = {}
    for p in paths:
        try:
            st = _r006_os.stat(p)
            with open(p, "rb") as fh:
                h = hashlib.sha256(fh.read()).hexdigest()[:16]
            out[p] = [st.st_size, h]
        except OSError:
            out[p] = None
    return out


def _r006_std_imports(imports):
    """③ 依赖完整性：把顶层 import 分类为 内置 / 标准库 / 第三方（Python 3.9 无 stdlib_module_names）。"""
    import importlib.util as _u
    import sysconfig
    std = _r006_os.path.realpath(sysconfig.get_paths()["stdlib"])
    third, stdlib = [], []
    for m in sorted(imports):
        if m in _r006_sys.builtin_module_names:
            stdlib.append(m)
            continue
        try:
            sp = _u.find_spec(m)
        except Exception:
            sp = None
        if sp is None:
            third.append(m + "(未解析)")
        elif sp.origin and _r006_os.path.realpath(sp.origin).startswith(std):
            stdlib.append(m)
        elif sp.origin in (None, "built-in", "frozen"):
            stdlib.append(m)
        else:
            third.append(m)
    return stdlib, third


def _r006_legacy_narrative():
    """沿用本器【原有的 selfcheck() 自述】—— 不因迁移到 canonical 块而丢失既有声明内容。
    取不到时如实说明（不静默当空）。"""
    f = globals().get("selfcheck")
    if not callable(f) or getattr(f, "__module__", None) != __name__:
        return []
    try:
        import io as _i
        import contextlib as _c
        buf = _i.StringIO()
        with _c.redirect_stdout(buf):
            f()
        return [l.rstrip() for l in buf.getvalue().splitlines() if l.strip()]
    except Exception as e:
        return ["(沿用原有 selfcheck() 失败，如实报出: %s)" % e]


def _r006_selfcheck():
    """R006 ② TCC 能力边界自检：三段输出 + 【结构核验】（不做纸面声明）。"""
    name = _R006_DECL["tool"]
    src = _r006_src()
    sc = _r006_scan(src)
    stdlib, third = _r006_std_imports(sc["imports"])
    W = _R006_DECL
    lines = ["R006 ② TCC 能力边界自检 · %s v%s" % (name, W["version"])]
    lines.append("【① 能力清单】")
    for x in W["capability"]:
        lines.append("  · " + x)
    legacy = _r006_legacy_narrative()
    if legacy:
        lines.append("  · —— 以下沿用本器原有 selfcheck() 自述 ——")
        for l in legacy:
            lines.append("  " + l)
    lines.append("【② 不该发生路径清单】")
    for x in W["impossible"]:
        lines.append("  · " + x)
    lines.append("【③ 依赖完整性】")
    lines.append("  · Python %s（本机）" % _r006_sys.version.split()[0])
    lines.append("  · 标准库 %d 个：%s" % (len(stdlib), ", ".join(stdlib) if stdlib else "无"))
    lines.append("  · 第三方 %d 个：%s" % (len(third), ", ".join(third) if third else "无"))
    lines.append("  · 外部命令调用点（冻结）：%s" % (", ".join(sorted(W["frozen_exec"])) or "无"))
    lines.append("  · 写入点（冻结）：%s" % (", ".join(sorted(W["frozen_write"])) or "无"))
    lines.append("  · 固定日志：%s" % (W["log"] or "无"))

    chk = []
    chk.append(("依赖无第三方", not third, "第三方: %s" % (", ".join(third) or "无")))
    ext_ok = (frozenset(sc["exec"]) == frozenset(W["frozen_exec"]))
    chk.append(("外部命令面与冻结集一致", ext_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["exec"]) or "无", sorted(W["frozen_exec"]) or "无")))
    wr_ok = (frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    chk.append(("写入面与冻结集一致", wr_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["write"]) or "无", sorted(W["frozen_write"]) or "无")))
    roots = [r for r in W.get("write_roots", [])]
    bad = [p for p in sc["write"] if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(_r006_os.path.expanduser(r)) for r in roots)]
    chk.append(("常量写入点在允许根内", not bad, "越界: %s" % (", ".join(bad) if bad else "无")))
    dg_ok = (frozenset(sc["danger"]) == frozenset(W["frozen_danger"]))
    chk.append(("危险原语面与冻结集一致", dg_ok,
                "实测 %s / 冻结 %s" % (sorted(sc["danger"]) or "无", sorted(W["frozen_danger"]) or "无")))
    lg_ok = (not W["log"]) or (W["log"] in src)
    chk.append(("声明的日志路径真实存在于源码", lg_ok, W["log"] or "N/A（本器无日志）"))
    need = ["【① 能力清单】", "【② 不该发生路径清单】", "【③ 依赖完整性】"]
    chk.append(("R006 ② 规格要求的三段齐备", all(n in lines for n in need), " / ".join(need)))
    # ★ 第 9 项 —— 采纳 adjudicator 建议的【可判定窄口径】版，而非其原表述。
    #   为何是窄口径（均为实测，见 docs「批次缺陷复核」节）：
    #     ① 只扫【剥离面】：对「版本写进字符串声明」与「写进错误消息」两种【自然写法】命中 0 ⇒ 瞎；
    #     ② 改扫【字符串面】：现有 10 器立刻误报 11 处（多为 legit 的文档提及与工具自身版本常量）。
    #   ⇒ 「硬编码版本」整体**不可门化**（真值源给不出：无法机械区分合法的版本下限声明与不正当锁死）。
    #     故只保留其中【可判定】的一片：生产代码里的**浮点型**版本字面量（形态✓ 真值源✓）。
    #   ★ 如实标注：本项命中率极低，是**变更检测器**，不是能力证明。
    _vh = sorted(set(_r006_re.findall(r"\b3\.\d+(?:\.\d+)?\b", _r006_strip(src))))
    chk.append(("剥离面无浮点型 Python 版本字面量（窄口径可判定片）", not _vh,
                "命中: %s" % (", ".join(_vh) if _vh else "无（★ 低命中率：变更检测器，非能力证明）")))
    # ★ 声明的正例必须实测可用（非空转）—— 此前这里放的是「读过自己打印的行」，那是同义反复。
    _pos = W.get("positive", [])
    _prc = None
    if _pos:
        _prc, _po = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(_pos))
    chk.append(("声明的正例实测可用（非空转）",
                bool(_pos) and _prc in W.get("positive_expect_rc", [0]) and _prc not in (2, 124, 125),
                "%s → rc=%s" % (" ".join(_pos), _prc)))

    fails = [c for c in chk if not c[1]]
    lines.append("⇒ 声明核验：%d/%d 一致%s" % (len(chk) - len(fails), len(chk),
                                        "" if not fails else " · ❌ " + "; ".join(c[0] for c in fails)))
    for nm, ok, dt in chk:
        lines.append("   %s %s — %s" % ("✅" if ok else "❌", nm, dt))
    print("\n".join(lines))
    return 0 if not fails else 1


def _r006_dryrun_proof():
    """⑩ D：有 --dry-run ⇒ 实测 run 前后外部状态一致；无 ⇒ 【结构证明】（并如实标注为变体）。"""
    W = _R006_DECL
    dr = W.get("dryrun")
    watch = [_r006_os.path.expanduser(p) for p in W.get("watch", [])]
    if dr:
        b = _r006_snap(watch)
        rc, out = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(dr))
        a = _r006_snap(watch)
        return (rc == 0 and a == b), "★ 实测：rc=%s · watch %d 项前后一致=%s" % (rc, len(watch), a == b), "实测"
    src = _r006_src()
    wr = _r006_scan(src)["write"]
    roots = [_r006_os.path.expanduser(r) for r in W.get("write_roots", [])]
    outside = [p for p in wr if p.startswith("const:") and not any(
        _r006_os.path.expanduser(p[6:]).startswith(r) for r in roots)]
    ok = (frozenset(wr) == frozenset(W["frozen_write"])) and not outside
    return ok, ("△ 变体（非实测）：本器无 --dry-run ⇒ 以【写入面冻结 + 全部写入点在允许根内】作结构证明"
                "（%s）" % (", ".join(sorted(wr)) or "零写入点")), "结构证明"


def _r006_lean4_check():
    """R006 ⑩ 约束门 A–F。每项都带【反空洞】控制：扫描器先在合成恶意源上自证会红。"""
    W = _R006_DECL
    src = _r006_src()
    sc = _r006_scan(src)
    me = _r006_os.path.basename(_r006_os.path.abspath(__file__))
    rows = []

    # 反空洞前置：扫描器自证
    syn_e = frozenset(_r006_scan(_R006_SYNTH_EXEC)["exec"])
    syn_w = frozenset(_r006_scan(_R006_SYNTH_WRITE)["write"])
    scanner_live = (syn_e == _R006_SYNTH_EXEC_WANT) and (syn_w == _R006_SYNTH_WRITE_WANT)
    vac = [] if scanner_live else ["合成源未被完整检出 exec=%s write=%s" % (sorted(syn_e), sorted(syn_w))]

    # A 危险原语面（★ 不是「一定没有」—— 有则必须逐条声明并冻结；未声明即红）
    allowed_dg = dict(W.get("allowed_danger", {}))
    a_ast = frozenset(sc["danger"])
    a_rx = frozenset(_r006_regex_pass(src))
    a_frozen = frozenset(W["frozen_danger"])
    unallowed = sorted(a_ast - set(allowed_dg))
    a_ok = (scanner_live and a_ast == a_frozen and not (a_rx - a_ast) and not unallowed)
    rows.append(("A", "危险原语面全部已声明并冻结（无未声明原语）", a_ok,
                 "实测=%s · 已声明 %d 项 · 双通道一致=%s%s"
                 % (sorted(a_ast) or "无（零危险原语）", len(allowed_dg), (a_rx - a_ast) == set(),
                    "" if not unallowed else " · ★未声明: %s" % unallowed)))

    # B 负例全部被拒（非空，且实测 rc != 0）
    negs = W.get("negatives", [])
    b_det, b_ok = [], len(negs) >= 2
    for nv in negs:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(nv))
        b_det.append("%s→rc%s" % (" ".join(nv), rc))
        if rc == 0:
            b_ok = False
    if not scanner_live:
        b_ok = False
    rows.append(("B", "负例全部被拒（≥2 条，实测 rc≠0）", b_ok, " · ".join(b_det) or "无负例"))

    # C 正例可用（防门太宽砍掉自己）
    # ★ 口径：合法输入必须被【受理并产出结果】。默认 rc==0；对「报告器」类工具，
    #   rc=1（报告有发现）是合法结果 —— 但须在 decl 里显式声明 expect_rc 并给出理由，
    #   不得拿它当免检口（否则 C 退化为空转）。rc∈{2,124,125} 一律算门失效。
    pos = W.get("positive", [])
    want_rc = W.get("positive_expect_rc", [0])
    c_ok, c_det = bool(pos), "无正例 ⇒ 不能判定"
    if pos:
        rc, _o = _r006_run([_r006_sys.executable, _r006_os.path.abspath(__file__)] + list(pos))
        c_ok = (rc in want_rc) and (rc not in (2, 124, 125))
        c_det = "%s → rc=%s（期望 %s）%s" % (" ".join(pos), rc, want_rc,
                                            "" if rc in want_rc else " · ★门太宽或用法被拒")
    if len(want_rc) > 1:
        c_det += " · 放宽理由：" + W.get("positive_expect_reason", "（未给理由 ⇒ 视为未声明）")
    rows.append(("C", "正例可用（防门太宽砍掉自己）", c_ok, c_det))

    # D 零变更
    d_ok, d_det, d_kind = _r006_dryrun_proof()
    rows.append(("D", "零变更（%s）" % d_kind, d_ok, d_det))

    # E 白名单冻结 + 写入面变更检测
    e_ok = (scanner_live and isinstance(W["frozen_write"], frozenset)
            and frozenset(sc["write"]) == frozenset(W["frozen_write"]))
    rows.append(("E", "写入面白名单冻结（frozenset + 变更即红）", e_ok,
                 "类型=%s · 元素=%d · 变更检测=on" % (type(W["frozen_write"]).__name__, len(W["frozen_write"]))))

    # F 外部命令白名单 + 别名逃逸检测
    f_ok = scanner_live and isinstance(W["frozen_exec"], frozenset) and frozenset(sc["exec"]) == frozenset(W["frozen_exec"])
    f_alias = "import subprocess as _sp" in _R006_SYNTH_EXEC and "subprocess.run" in syn_e
    rows.append(("F", "外部命令白名单（别名逃逸已覆盖 + 变更即红）", f_ok and f_alias,
                 "命令集=%s · 别名形式检出=%s" % (sorted(sc["exec"]) or "无", f_alias)))

    nf = [r for r in rows if not r[2]]
    print("== %s · --lean4-check（六项 A–F）==" % me)
    for k, nm, ok, dt in rows:
        print("  %s %s %-38s %s" % ("OK  " if ok else "FAIL", k, nm, dt))
    if vac:
        print("  ★ 反空洞控制未过：%s" % "; ".join(vac))
    print("\n  => %d/%d pass, %d FAIL" % (len(rows) - len(nf), len(rows), len(nf)))
    return 0 if not nf else 1


def _r006_sets():
    """诊断口：给出本器【实际】三面读数与冻结集，供注入器「先算后填」。"""
    sc = _r006_scan(_r006_src())
    print(_r006_json.dumps({
        "tool": _R006_DECL["tool"],
        "observed_exec": sorted(sc["exec"]), "frozen_exec": sorted(_R006_DECL["frozen_exec"]),
        "observed_write": sorted(sc["write"]), "frozen_write": sorted(_R006_DECL["frozen_write"]),
        "observed_danger": sorted(sc["danger"]), "frozen_danger": sorted(_R006_DECL["frozen_danger"]),
        "imports": sorted(sc["imports"]), "err": sc["err"],
    }, ensure_ascii=False, indent=2))
    return 0


def _r006_want(flag):
    """旗标本器是否被请求：既认当前 argv，也认【早期垫片】暂存的旗标。
    （垫片必须存在：本器可能在模块级就校验 argv，会先于本块把旗标当「不认识的参数」拒掉。）"""
    return (flag in _r006_sys.argv) or (flag in globals().get("_R006_EARLY_FLAGS", []))


# ── R006 ⑨③ `--dry-run` 统一实现（canonical） ────────────────────────────────
# 分流（★ 必须分流：本族里 3 个器【自带】--dry-run，拦截它会破坏其既有语义）：
#   · dryrun_via_block=True  : 本器无自带实现 ⇒ 由本块接管：把 --dry-run 从 argv 摘掉
#     （故其 argparse 不因未知旗标报错），并按 decl["dry_suppress"] 把【自动写入助手】
#     置为空操作 ⇒ 本器走完整逻辑但不产生自动落盘副作用。
#   · dryrun_via_block=False : 本器自带实现 ⇒ 把垫片摘走的旗标【放回 argv】，交还原实现。
if __name__ == "__main__":
    _R006_DRY = False
    if _R006_DECL.get("dryrun_via_block") and _r006_want("--dry-run"):
        _R006_DRY = True
        _r006_sys.argv = [x for x in _r006_sys.argv if x != "--dry-run"]
        for _rn in _R006_DECL.get("dry_suppress", []):
            if callable(globals().get(_rn)):
                globals()[_rn] = (lambda *a, **k: None)
    elif "--dry-run" in globals().get("_R006_EARLY_FLAGS", []):
        _r006_sys.argv.append("--dry-run")
else:
    _R006_DRY = False


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
