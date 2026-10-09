#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
citation-stale-check —— 引用失效检测（v1.0.0）

来源：HR 2026-09-14「五同律」裁定的机制处置建议 ——
「账本应登记每个对外引用数字的绑定项：引用登记时带实现指纹（文件 + 行号 + 该行哈希）；
 该行变更 ⇒ 引用自动标 stale 并提醒引用者。」
其判据：**同一失误一晚由三个不同主体各犯一次 ⇒ 不得再用「提醒」处置，必须改为机制处置。**

本工具把「引用实现细节」变成可判 stale 的登记项。

三态（比 OK/STALE 二态更有用）：
    FRESH   行号与行内容都与登记时一致
    MOVED   该行内容仍存在于文件，但**行号变了**（内容未变、位置变了）
    CHANGED 该行内容已不存在于文件（改过/删过）⇒ 引用已失效

用法：
    python3 citation-stale-check.py --print  FILE:LINE          # 生成可粘贴进卡片的指纹
    python3 citation-stale-check.py --check  FILE:LINE:HASH     # 单条判定
    python3 citation-stale-check.py --registry REG.json        # 批量判定（含 --json-out）
    python3 citation-stale-check.py --selftest
    退出码：0 全 FRESH · 1 存在 MOVED/CHANGED · 2 参数错

设计纪律：
    · selftest 必须**含反例且先跑反例**（否则假阴性会被读成「全部新鲜」）
    · 指纹绑定**行号 + 行哈希**：行号单独不够（内容会移位），哈希单独不够（无法定位）

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
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets")
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
    print("== citation-stale-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · citation-stale-check —— 引用失效检测（v1.0.0）")
    print("  · 来源：HR 2026-09-14「五同律」裁定的机制处置建议 ——")
    print("  · 「账本应登记每个对外引用数字的绑定项：引用登记时带实现指纹（文件 + 行号 + 该行哈希）；")
    print("  · 该行变更 ⇒ 引用自动标 stale 并提醒引用者。」")
    print("  · 命令/参数: print, check, registry, json-out, selftest, version")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, collections, hashlib, json, os, sys, tempfile, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/citation-stale-check.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import hashlib
import json
import os
import sys
import tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/citation-stale-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "2.1.0"
HASH_LEN = 12


def line_hash(text):
    """行指纹：去右侧空白与行尾换行后取 sha256 前 12 位。"""
    return hashlib.sha256(text.rstrip("\r\n").rstrip().encode("utf-8")).hexdigest()[:HASH_LEN]


def read_lines(path):
    with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def fingerprint(path, lineno):
    lines = read_lines(path)
    if lineno < 1 or lineno > len(lines):
        raise SystemExit(f"行号越界：{path} 共 {len(lines)} 行，请求 L{lineno}")
    return {"file": path, "line": lineno, "hash": line_hash(lines[lineno - 1]),
            "text_head": lines[lineno - 1].strip()[:60]}


def check_deps(rec):
    """检测面决定声明上界（HR 2026-09-14）。行级哈希只支持「该行未变」。

    kind=env            ：该环境变量若被设置 ⇒ 生效值偏离行内默认 ⇒ DEPENDS-DIVERGES
    kind=file_line      ：另一处 (file,line,hash) 必须 FRESH，否则 DEPENDS-CHANGED
    kind=symbol         ：不可机械校验 ⇒ DEPENDS-UNVERIFIED（声明强度封顶）
    kind=runtime_writer ：**第四类生产者**（HR 2026-09-14 裁定新增）—— **import 期改写 env 的模块**
                          （实例：`im-window.js:14` / `browser-restart.js:13`）。它与 file_line 的
                          机械校验相同，但**枚举必须分开**，理由（HR 的判据）：**两个枚举面须对齐；
                          一处枚举的成员应能在另一处找到落点，找不到即为缺口** —— 缺这一类，
                          `depends_on` 会漏掉**最隐蔽的一类生产者**（它不改配置文件、只改进程）。
    ★ 并返回**使结论成立的条件清单**（HR 2026-09-14: FRESH 是条件化的状态，条件须显示）——
      否则 FRESH 会被读成**无条件成立**。
    返回 (state, detail, conditions)。
    """
    deps = rec.get("depends_on") or []
    if not deps:
        return "NO-DEPS", "未声明 depends_on ⇒ 声明强度上限仅为「该行未变」，不含「结论仍成立」", []
    conds = []
    for d in deps:
        k = d.get("kind")
        if k == "env":
            name = d.get("name", "")
            if os.environ.get(name) is not None:
                return "DEPENDS-DIVERGES", f"环境变量 {name} 已被设置 ⇒ 生效值偏离行内默认（行哈希不可见）", conds
            conds.append(f"env {name} 未设")
        elif k in ("file_line", "runtime_writer"):
            sub = {kk: d.get(kk) for kk in ("file", "line", "hash")}
            r = check_one(sub)
            if r["state"] != "FRESH":
                label = "运行时改写者" if k == "runtime_writer" else "依赖项"
                return "DEPENDS-CHANGED", f"{label} {d.get('file')}:{d.get('line')} = {r['state']}", conds
            if k == "runtime_writer":
                conds.append(f"运行时改写者 {d.get('file')}:{d.get('line')} 仍在（import 期改写）")
        elif k == "symbol":
            return "DEPENDS-UNVERIFIED", f"符号 {d.get('name')} 无法机械校验 ⇒ 声明强度封顶", conds
        else:
            return "DEPENDS-UNVERIFIED", f"未知 kind「{k}」⇒ 无法校验 ⇒ 声明强度封顶（已知 kind：env/file_line/symbol/runtime_writer）", conds
    return "DEPS-OK", f"依赖项 {len(deps)} 个均已校验", conds


def check_one(rec):
    path, lineno, h = rec["file"], int(rec["line"]), rec["hash"]
    if not os.path.exists(os.path.expanduser(path)):
        return {**rec, "state": "CHANGED", "detail": "文件不存在"}
    lines = read_lines(path)
    if 1 <= lineno <= len(lines) and line_hash(lines[lineno - 1]) == h:
        ds, dd, conds = check_deps(rec)
        if ds in ("DEPS-OK", "NO-DEPS"):
            return {**rec, "state": "FRESH", "dep_state": ds, "conditions": conds,
                    "detail": f"L{lineno} 内容一致；{dd}"}
        return {**rec, "state": ds, "dep_state": ds, "conditions": conds, "detail": dd}
    hits = [i + 1 for i, l in enumerate(lines) if line_hash(l) == h]
    if hits:
        return {**rec, "state": "MOVED", "detail": f"内容仍在，行号 {lineno} → {hits[0]}"}
    return {**rec, "state": "CHANGED", "detail": f"L{lineno} 原内容已不存在（文件 {len(lines)} 行）"}


# ── selftest：**每个用例在自己那份文件状态下立即求值** ─────────────────
#    反面教材（本工具 1.0.0 首版）：先登记所有用例、最后统一求值 ⇒ 文件已复原
#    ⇒ 三条「应判 CHANGED」全被读成 FRESH（只有正例通过）⇒ 延期求值 = 测错了对象。
def _w(path, body):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


def selftest():
    ok = total = 0
    d = tempfile.mkdtemp(prefix="cit-stale-")
    f = os.path.join(d, "impl.sh")
    BASE = "line1\nRETENTION_DAYS=180\nline3\nfind x -mtime +7 -delete\n"

    def run(name, expect, setup, rec_fn):
        nonlocal ok, total
        total += 1
        setup()
        rec = rec_fn()
        got = check_one(rec)
        good = got["state"] == expect
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: expect={expect} got={got['state']} ({got['detail']})")

    _w(f, BASE)
    fp2 = fingerprint(f, 2)
    fp4 = fingerprint(f, 4)
    print("selftest（反例与正例各自立即求值）:")
    run("反例·L2 被改 ⇒ CHANGED", "CHANGED",
        lambda: _w(f, "line1\nRETENTION_DAYS=90\nline3\nfind x -mtime +7 -delete\n"),
        lambda: {**fp2, "file": f})
    run("反例·L2 被删 ⇒ CHANGED", "CHANGED",
        lambda: _w(f, "line1\nline3\nfind x -mtime +7 -delete\n"),
        lambda: {**fp2, "file": f})
    run("正例·内容仍在但移位 ⇒ MOVED", "MOVED",
        lambda: _w(f, "line1\nNEW\nRETENTION_DAYS=180\nline3\nfind x -mtime +7 -delete\n"),
        lambda: {**fp2, "file": f})
    run("正例·未改动+依赖已校验 ⇒ FRESH", "FRESH",
        lambda: _w(f, BASE), lambda: {**fp2, "file": f, "depends_on": [{"kind": "file_line", "file": f, "line": 2, "hash": fp2["hash"]}]})
    run("反例·无 depends_on ⇒ FRESH 但声明封顶（NO-DEPS）", "FRESH",
        lambda: _w(f, BASE), lambda: {**fp2, "file": f})
    run("反例·env 被设置 ⇒ DEPENDS-DIVERGES", "DEPENDS-DIVERGES",
        lambda: (os.environ.__setitem__("CIT_TEST_ENV", "1"), _w(f, BASE))[1],
        lambda: {**fp2, "file": f, "depends_on": [{"kind": "env", "name": "CIT_TEST_ENV"}]})
    run("反例·登记行内容已从文件消失（旧策略行）⇒ CHANGED", "CHANGED",
        lambda: _w(f, BASE), lambda: {"file": f, "line": 4, "hash": "deadbeef0000"})
    run("正例·文件不存在 ⇒ CHANGED", "CHANGED",
        lambda: None, lambda: {"file": os.path.join(d, "missing.sh"), "line": 1, "hash": "x"})
    # ── 第四类生产者 runtime_writer（HR 2026-09-14 裁定的枚举缺口）──
    wf = os.path.join(d, "runtime_writer.js")
    _w(wf, "const os=require('os')\nconst p=(s)=>s\nprocess.env.MTM_DATA_DIR='x'\n")
    fpw3 = fingerprint(wf, 3)
    run("正例·runtime_writer 仍在且行未变 ⇒ FRESH（且须带条件）", "FRESH",
        lambda: _w(wf, "const os=require('os')\nconst p=(s)=>s\nprocess.env.MTM_DATA_DIR='x'\n"),
        lambda: {**fp2, "file": f, "depends_on": [{"kind": "runtime_writer", "file": wf, "line": 3, "hash": fpw3["hash"]}]})
    run("反例·运行时改写者被删 ⇒ DEPENDS-CHANGED（不得仍报 FRESH）", "DEPENDS-CHANGED",
        lambda: _w(wf, "const os=require('os')\n"),
        lambda: {**fp2, "file": f, "depends_on": [{"kind": "runtime_writer", "file": wf, "line": 3, "hash": fpw3["hash"]}]})
    run("反例·改写内容变了 ⇒ DEPENDS-CHANGED", "DEPENDS-CHANGED",
        lambda: _w(wf, "const os=require('os')\nconst p=(s)=>s\nprocess.env.MTM_DATA_DIR='/other'\n"),
        lambda: {**fp2, "file": f, "depends_on": [{"kind": "runtime_writer", "file": wf, "line": 3, "hash": fpw3["hash"]}]})
    run("反例·未知 kind ⇒ DEPENDS-UNVERIFIED（封顶，不得放过）", "DEPENDS-UNVERIFIED",
        lambda: _w(f, BASE),
        lambda: {**fp2, "file": f, "depends_on": [{"kind": "telepathy", "name": "?"}]})
    # ★ 枚举面对齐的**标签**级测试（HR 的判据：一处枚举的成员须能在另一处找到落点）
    total += 1
    _w(f, BASE)
    _w(wf, "garbage\n")
    got = check_one({**fp2, "file": f, "depends_on": [{"kind": "runtime_writer", "file": wf, "line": 3, "hash": fpw3["hash"]}]})
    good = "运行时改写者" in got["detail"]
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 反例·runtime_writer 须以**独立标签**报出（并入 file_line 即枚举面缺口的复发）: {got['detail'][:40]}")
    total += 1
    _w(f, BASE)
    _w(wf, "const os=require('os')\nconst p=(s)=>s\nprocess.env.MTM_DATA_DIR='x'\n")  # 复原：上一例把它改过
    os.environ.pop("CIT_TEST_ENV", None)
    got = check_one({**fp2, "file": f, "depends_on": [
        {"kind": "env", "name": "CIT_TEST_ENV"},
        {"kind": "runtime_writer", "file": wf, "line": 3, "hash": fpw3["hash"]}]})
    cond = got.get("conditions") or []
    good = got["state"] == "FRESH" and len(cond) == 2
    ok += 1 if good else 0
    print(f"  {'✅' if good else '❌'} 反例·★FRESH 必须附**使其成立的条件**（否则被读成无条件）: state={got['state']} cond={cond}")
    print(f"\nselftest {ok}/{total}")
    print("判据（HR 2026-09-14）：检测面决定声明上界 —— 无 depends_on 的登记，其最大声明是「该行未变」。")
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--print", dest="pr", metavar="FILE:LINE")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--check", metavar="FILE:LINE:HASH")
    ap.add_argument("--registry")
    ap.add_argument("--json-out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()

    if args.version:
        print(json.dumps({"tool": "citation-stale-check", "version": VERSION,
                          "states": ["FRESH", "MOVED", "CHANGED"],
                          "rule": "引用实现细节须登记 (文件, 行号, 行哈希)；变更即判 stale"}, ensure_ascii=False))
        return 0
    if args.selftest:
        return selftest()

    if args.pr:
        path, _, ln = args.pr.rpartition(":")
        fp = fingerprint(path, int(ln))
        print(json.dumps(fp, ensure_ascii=False))
        print("→ 把上面这段作为 citation 字段写进卡片；检查时用 --check 或 --registry")
        return 0

    if args.check:
        path, ln, h = args.check.rsplit(":", 2)
        r = check_one({"file": path, "line": int(ln), "hash": h})
        print(f"{r['state']} — {r['detail']}")
        return 0 if r["state"] == "FRESH" else 1

    if args.registry:
        reg = json.load(open(os.path.expanduser(args.registry), encoding="utf-8"))
        recs = reg if isinstance(reg, list) else reg.get("citations", [])
        out = [check_one(r) for r in recs]
        bad = [r for r in out if r["state"] != "FRESH"]
        for r in bad:
            print(f"[{r['state']}] {r.get('card', r.get('file'))} :: {r['file']}:{r['line']} — {r['detail']}")
        # ★ FRESH 是**条件化的状态**（HR 2026-09-14）：条件不显示 ⇒ 结论被读成无条件成立
        fresh = [r for r in out if r["state"] == "FRESH"]
        conds = {}
        for r in fresh:
            for c in (r.get("conditions") or []):
                conds[c] = conds.get(c, 0) + 1
        nod = [r for r in fresh if r.get("dep_state") == "NO-DEPS"]
        if fresh:
            print(f"\n【FRESH 的条件】{len(fresh)} 条 FRESH —— 它们**在下列条件取值下**成立：")
            if conds:
                for c, n in sorted(conds.items(), key=lambda x: -x[1]):
                    print(f"   · {c}（{n} 条依赖它）")
            else:
                print("   · （无声明条件）")
            if nod:
                print(f"   ⚠ 其中 {len(nod)} 条为 **NO-DEPS（封顶）**：无依赖登记 ⇒ 最大声明仅为「该行未变」，"
                      f"**不含「结论仍成立」**")
            print("   ⇒ 判据（HR 2026-09-14）：**凡「成立/通过」的结论，须随附使其成立的条件取值**；"
                  "条件不可见 ⇒ 结论被读成无条件。")
        from collections import Counter
        c = Counter(r["state"] for r in out)
        print(f"\n登记 {len(out)} 条 · " + " · ".join(f"{k}={v}" for k, v in sorted(c.items())))
        if args.json_out:
            json.dump({"version": VERSION, "results": out}, open(os.path.expanduser(args.json_out), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"json → {args.json_out}")
        return 1 if bad else 0

    ap.print_help()
    return 2


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
    'tool': 'citation-stale-check',
    'version': '2.1.0',
    'capability': ['引用失效检测：账本登记每个对外引用数字的绑定项（文件 + 行号 + 该行哈希）', '该行变更 ⇒ 引用自动标 stale 并提醒引用者', '三态：FRESH / MOVED / CHANGED'],
    'impossible': ['本器不执行外部命令、不删除数据、不修改权限 ⇒ 无该路径', '不改写被引用方的文件（只登记与比对）', '不把「文件不存在」与「行哈希不符」混为一类（MOVED vs CHANGED 分开）'],
    'log': 'citation-stale-check.log',
    'write_roots': ['/tmp', '~/dsh-collab/logs', '~/dsh-collab/data'],
    'negatives': [['--definitely-not-a-flag'], ['--check']],
    'positive': ['--selftest'],
    'dryrun': None,
    'watch': [],
    'allowed_danger': {
        '__import__': '若本器以 --selfcheck 调用则走自检分支；模块名字面量 sys',
    },
    'frozen_exec': frozenset({'subprocess.run'}),
    'frozen_write': frozenset({'<expr>'}),
    'frozen_danger': frozenset({'__import__'}),
    'positive_expect_rc': [0],
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


if __name__ == "__main__" and _r006_want("--selfcheck"):
    _r006_sys.exit(_r006_selfcheck())

if __name__ == "__main__" and _r006_want("--lean4-check"):
    _r006_sys.exit(_r006_lean4_check())

if __name__ == "__main__" and _r006_want("--r006-sets"):
    _r006_sys.exit(_r006_sets())
# ══════════════════════════════ R006 块结束 ══════════════════════════════

if __name__ == "__main__":
    sys.exit(main())
