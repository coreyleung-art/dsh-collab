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
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import hashlib
import json
import os
import sys
import tempfile

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
    ap.add_argument("--check", metavar="FILE:LINE:HASH")
    ap.add_argument("--registry")
    ap.add_argument("--json-out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
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


if __name__ == "__main__":
    sys.exit(main())
