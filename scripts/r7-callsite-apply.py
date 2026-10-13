#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r7-callsite-apply.py — 给脚本补 R006 ⑦ 的 log() 调用点 v1.0.0

★★ 为什么（实据 · 2026-10-13 独立考古）：
  R006 ⑦「统一日志」由 `r006-retrofit-apply.py` 机械补课，而它
  **只注入 `LOG` 常量与 `log()` 函数定义、从不注入【调用点】**；
  其判据 `needs_r7` 只查「日志路径的**形状**」⇒ ★ **门与对象同形 = 自证通过**。
  实测：含 `def log(` 的脚本里 **232 个（81%）零调用** ⇒ **声明的日志文件永不产生**。
  ★ 本件就是补上【调用点】。判据也已同步改为【行为】（本线同日修）。

★★★ 四条前置（★ 试点实测得出，缺一即会破坏脚本）：
  ① 文件有 `def log(` 定义
  ② 有 `main()`，且其内有 `argparse.ArgumentParser(`
  ③ ★★ **文件已 `import sys`** —— ★ 否则插入的 `sys.argv` 会 NameError
     （`approval-tier.py` 就是这样被试点抓到的）
  ④ ★★ **必须用【纯行插入】，不得用正则重组多行** ——
     ★ 第一版用正则重组 ⇒ **3 个文件全部 IndentationError**（缩进被打乱）

★ 用法：
    r7-callsite-apply.py                 # ★ dry-run（默认，零写入）
    r7-callsite-apply.py --apply --limit 10
    r7-callsite-apply.py --json
    r7-callsite-apply.py --tool-version
"""
__version__ = "1.0.0"

import argparse, ast, datetime, json, os, re, shutil, subprocess, sys

SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
LOGS = os.path.expanduser("~/dsh-collab/logs")
LOG = os.path.join(LOGS, "r7-callsite-apply.log")
MARK = "★ r7-callsite-inserted"          # ★ 幂等标记（已插过就跳过）

INSERT_LINES = [
    "# ★★ r7-callsite-inserted 2026-10-13：R006 ⑦【统一日志】的【调用点】。",
    "#   背景：本文件此前【只有 LOG 常量与 log() 定义、零调用】⇒ 声明的日志文件永不产生；",
    "#   根因是补课器只注入【形状】不注入【调用点】，其判据只查【路径形状】⇒ 门与对象同形=自证通过。",
    "#   ★ 本行【不改任何业务逻辑】，只记「被调用 + 参数」。",
    'log("invoked argv=%s" % " ".join(sys.argv[1:]))',
]


def log(msg):
    try:
        os.makedirs(LOGS, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def candidates():
    """★ 找出【同时满足 4 条前置】的候选。"""
    out = []
    for f in sorted(os.listdir(SCRIPTS)):
        if not f.endswith(".py"):
            continue
        p = os.path.join(SCRIPTS, f)
        try:
            s = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if MARK in s:
            continue                                             # ③ 幂等
        if not re.search(r"(?m)^\s*def log\(", s):
            continue                                             # ① 有定义
        body = re.sub(r"(?m)^\s*def log\([^)]*\):\s*$", "", s)
        if "log(" in body:
            continue                                             # ① 确实零调用
        if not re.search(r"(?m)^import sys|^import .*\bsys\b", s):
            continue                                             # ③ ★ 必须已 import sys
        mi = next((i for i, l in enumerate(s.split("\n")) if re.match(r"def main\(", l)), None)
        if mi is None:
            continue                                             # ② 有 main
        lines = s.split("\n")
        ai = next((i for i in range(mi + 1, min(mi + 15, len(lines)))
                   if "argparse.ArgumentParser(" in lines[i]), None)
        if ai is None:
            continue                                             # ② main 内有 argparse
        out.append({"file": f, "path": p, "insertBefore": ai + 1,
                    "indent": re.match(r"(\s*)", lines[ai]).group(1)})
    return out


def apply_one(c):
    """★ 纯【行插入】（★ 不重组任何既有行 —— 第一版教训）。"""
    p = c["path"]
    shutil.copy2(p, p + ".r7bak")
    lines = open(p, encoding="utf-8").read().split("\n")
    ind = c["indent"]
    ins = [ind + x for x in INSERT_LINES]
    lines[c["insertBefore"] - 1:c["insertBefore"] - 1] = ins
    open(p, "w", encoding="utf-8").write("\n".join(lines))
    # ★★ 结果态验证：语法必须仍可解析（★ 不信「写成功」）
    try:
        ast.parse(open(p, encoding="utf-8").read())
    except SyntaxError as e:
        shutil.copy2(p + ".r7bak", p)                             # ★ 立即回滚
        os.remove(p + ".r7bak")
        return {"file": c["file"], "ok": False, "verdict": "★ 语法坏 ⇒ 已回滚: %s" % str(e)[:60]}
    os.remove(p + ".r7bak")
    return {"file": c["file"], "ok": True, "verdict": "✓ 已插入（语法自验通过）"}


def main():
    ap = argparse.ArgumentParser(description="补 R006 ⑦ log() 调用点（★ 默认 dry-run）")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    a = ap.parse_args()
    if a.tool_version:
        print(__version__); return 0
    cand = candidates()
    if a.limit:
        cand = cand[:a.limit]
    res = ([apply_one(c) for c in cand] if a.apply
           else [{"file": c["file"], "ok": True, "verdict": "★ dry-run（将插入于第 %d 行前）" % c["insertBefore"]}
                 for c in cand])
    out = {"tool": "r7-callsite-apply", "version": __version__, "dryRun": not a.apply,
           "at": datetime.datetime.now().isoformat(), "candidateCount": len(cand),
           "results": res, "ok": sum(1 for r in res if r["ok"]),
           "failed": sum(1 for r in res if not r["ok"])}
    log("run dry=%s n=%d ok=%d failed=%d" % (out["dryRun"], len(cand), out["ok"], out["failed"]))
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("══ R006 ⑦ 调用点补齐 v%s ══ [%s]" % (__version__, "真插" if a.apply else "★ dry-run"))
        print("  候选（★ 满足 4 条前置）: %d 个" % len(cand))
        for r in res[:20]:
            print("    %-36s %s" % (r["file"], r["verdict"]))
        if len(res) > 20:
            print("    …（另 %d 个）" % (len(res) - 20))
        print("\n  ⇒ 处理 %d · 成功 %d · 失败 %d" % (len(cand), out["ok"], out["failed"]))
        if not a.apply:
            print("  ★ dry-run：零写入。真插请加 --apply")
    return 0 if out["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
