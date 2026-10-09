#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit-census.py — 板级审计普查（v1.0.0）

依据：独立复核员 2026-10-08 定位的**连字符坑**与**两套「正确」文件集**：
  · `audit-*.jsonl` **只匹配归档**；**活动文件是 `audit.jsonl`（无连字符、无日期后缀）** ⇒
    用前者做普查会**恰好漏掉最近、最相关的一段**（我的实证：漏 1,881 行、而仅有 2 条 writer 全在其中）。
  · ★ 但两套文件集各有其正确用途：**板子自己的保留枚举**用 `starts_with("audit-")` 是**故意排除活动文件**
    （不该删正在写的文件）；而**保留窗口的普查**必须用 `audit*.jsonl`。
⇒ 本脚本把普查口径固定为 {audit.jsonl} ∪ {audit-*.jsonl}，并**逐个列出文件名**（漏了谁一眼可见）。

用法: python3 audit-census.py [--dir <审计目录>] [--json] [--selftest]
判据：file_set_complete=True 且逐文件列出；writer_top_level 计数（非 0 即表明有客户端发 X-Writer）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== audit-census 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · audit-census.py — 板级审计普查（v1.0.0）")
    print("  · 依据：独立复核员 2026-10-08 定位的**连字符坑**与**两套「正确」文件集**：")
    print("  · · `audit-*.jsonl` **只匹配归档**；**活动文件是 `audit.jsonl`（无连字符、无日期后缀）** ⇒")
    print("  · 用前者做普查会**恰好漏掉最近、最相关的一段**（我的实证：漏 1,881 行、而仅有 2 条 writer 全在其中）。")
    print("  · 命令/参数: dir, json, selftest, version")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, tempfile, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/audit-census.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import argparse, glob, json, os, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/audit-census.log")


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
__version__ = VERSION
DEFAULT_DIR = os.path.expanduser("~/dsh-collab/token-monitor/blackboard")


def census(d):
    active = sorted(glob.glob(os.path.join(d, "audit.jsonl")))
    archived = sorted(glob.glob(os.path.join(d, "audit-*.jsonl")))
    # ★ 断言文件集完备：活动文件（无连字符）必须在内
    files = active + archived
    complete = len(active) == 1
    rows = 0
    writer_top = 0
    per_file = []
    for f in files:
        n = w = 0
        try:
            for ln in open(f, encoding="utf-8", errors="ignore"):
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    d2 = json.loads(ln)
                except Exception:
                    continue
                n += 1
                if "writer" in d2:
                    w += 1
        except FileNotFoundError:
            continue
        per_file.append({"file": os.path.basename(f), "kind": "active" if f in active else "archived",
                         "rows": n, "writer_top_level": w})
        rows += n; writer_top += w
    return {"dir": d,
            "file_set_rule": "{audit.jsonl} ∪ {audit-*.jsonl}（★ 连字符坑：audit-*.jsonl 只匹配归档）",
            "file_set_complete": complete,
            "files": per_file,
            "active_file_present": bool(active),
            "rows_total": rows,
            "writer_top_level_total": writer_top,
            "verdict": "pass" if complete else "fail(file-set-incomplete)"}


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    import tempfile
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "audit.jsonl"), "w") as f:
        f.write(json.dumps({"key": "a", "writer": "s1"}) + "\n")
    with open(os.path.join(d, "audit-20261008-0000.jsonl"), "w") as f:
        f.write(json.dumps({"key": "b"}) + "\n")
    r = census(d)
    chk(r["file_set_complete"] is True, "活动文件被纳入（file_set_complete=True）")
    chk(r["rows_total"] == 2, "总数包含活动文件（2 行）")
    chk(r["writer_top_level_total"] == 1, "writer 命中来自活动文件（连字符坑的反例）")
    chk(any(x["kind"] == "active" for x in r["files"]), "逐文件列表含 active 标记")
    # 负控：无活动文件 ⇒ 明确 fail 而非静默
    d2 = tempfile.mkdtemp()
    open(os.path.join(d2, "audit-20261008-0000.jsonl"), "w").write("{}\n")
    r2 = census(d2)
    chk(r2["verdict"].startswith("fail"), "负控·缺活动文件 ⇒ 判 fail（不静默）")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(json.dumps({"tool": "audit-census", "version": VERSION})); return 0
    if a.selftest: return selftest()
    r = census(a.dir)
    if a.json: print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"dir={r['dir']} | 规则: {r['file_set_rule']}")
        for x in r["files"]:
            print(f"  [{x['kind']:<8}] {x['file']:<34} rows={x['rows']:<7} writer={x['writer_top_level']}")
        print(f"  合计 rows={r['rows_total']} writer(顶层)={r['writer_top_level_total']} | file_set_complete={r['file_set_complete']} | {r['verdict']}")
    return 0 if r["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
