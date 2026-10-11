#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""直测：本插件的七道门**各自能不能红**。

★ 判据来自裁判交接的 `gate-canfail.py`：
  「一个判据若没有能让它失败的输入，**它就不是判据，是日志**。」
★ 我的可疑对象：`--lean4-check`（A–F）—— 我**从没见它红过**。
★ 做法：对每道门施加一个「应当使它失败」的输入，看它退不退非零；finally 还原并逐字节校验。
"""
import hashlib
import os
import shutil
import subprocess
import sys

P = os.path.expanduser("~/dsh-collab/devices/dsh-plugin-context-survival")
NODE = "/opt/homebrew/bin/node"
TMP = "/tmp/csx-canfail-backup"


def sh(cmd, cwd=P):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180, cwd=cwd)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


BASE = {
    "lean4-check": f"{NODE} cli.js --lean4-check",
    "contract-check": f"{NODE} cli.js --contract-check",
    "checkpoint-check": f"{NODE} cli.js --checkpoint-check",
    "recall-check": f"{NODE} cli.js --recall-check",
    "budget-check": f"{NODE} cli.js --budget-check",
    "calibration": f"{NODE} cli.js --calibration",
    "selfcheck(默认)": f"{NODE} cli.js --selfcheck",
}

# 每个门一个「应当使它失败」的注入：(标签, [(文件, 原文, 替换文)...], 门)
INJECTIONS = [
    ("A 源码里出现执行点（A 项判据）", [("lib/gate.js", "export function stripLiterals(src) {", "export function stripLiterals(src) {\n  // inject\n  require('node:child_process').exec('true');\n")], "lean4-check"),
    ("lib/index.js 写死宿主路径（R3/③ 判据）", [("cli.js", "const HERE = path.dirname(fileURLToPath(import.meta.url));", "const HERE = path.dirname(fileURLToPath(import.meta.url));\nconst _BAD = '/Applications/CLD.app/x';\n")], "lean4-check"),
    ("inject 写进禁集（D 项判据）", [("lib/index.js", "export const inject = ['tools'];", "export const inject = ['tools', 'slots'];\n")], "lean4-check"),
    ("工具契约滞留（contract-check 判据）", [("lib/index.js", "const STAGE = 'K5-r006-7of10';", "const STAGE = 'K5-r006-7of10'; // 尚未实现 K1 骨架\n")], "contract-check"),
    ("白名单不再冻结（E 项判据）", [("lib/gate.js", "export const ALLOWED_INJECT = Object.freeze(['tools']);", "export const ALLOWED_INJECT = ['tools'];\n")], "lean4-check"),
]


def main():
    os.makedirs(TMP, exist_ok=True)
    print("csx-canfail · 本插件七道门各自能不能红")
    print()
    base = {}
    for name, cmd in BASE.items():
        r = sh(cmd)
        base[name] = r.returncode
        print(f"  基线 {name:18s} exit={r.returncode}")
    print()

    results = []
    for label, edits, gate in INJECTIONS:
        backs = []
        hashes = {}
        ok_apply = True
        for rel, old, new in edits:
            path = os.path.join(P, rel)
            bk = os.path.join(TMP, rel.replace("/", "_"))
            shutil.copy2(path, bk)
            backs.append((path, bk))
            hashes[path] = sha(path)
            src = open(path, encoding="utf-8").read()
            if src.count(old) != 1:
                print(f"  ⚠️ {label} —— 锚点 {src.count(old)} 次（未施加）")
                ok_apply = False
                break
            open(path, "w", encoding="utf-8").write(src.replace(old, new))
        try:
            if not ok_apply:
                results.append((label, gate, "锚点不中", None))
                continue
            r = sh(BASE[gate])
            rc = r.returncode
            killed = rc != 0
            out = (r.stdout + r.stderr)
            # 抽出被红的那一项（若有）
            reds = [l.strip() for l in out.split("\n") if "❌" in l][:2]
            results.append((label, gate, "✅ 被杀" if killed else "❌ 未杀", reds))
            print(f"  {'✅' if killed else '❌'} {label}")
            print(f"       门={gate} exit={rc} {'（变红）' if killed else '**（仍绿 ⇒ 该判据无失败路径）**'}")
            if reds:
                for x in reds:
                    print(f"       {x[:100]}")
        finally:
            bad = False
            for path, bk in backs:
                shutil.copy2(bk, path)
                if sha(path) != hashes[path]:
                    bad = True
            if bad:
                print(f"     ⚠️ 还原校验失败！{label}")
                return 2
    print()
    end_bad = []
    for name, cmd in BASE.items():
        r = sh(cmd)
        if r.returncode != base[name]:
            end_bad.append(f"{name}: {base[name]} -> {r.returncode}")
    print(f"还原后：{'✅ 各门回到基线' if not end_bad else '❌ ' + '; '.join(end_bad)}")
    print()
    killed = [r for r in results if r[2] == "✅ 被杀"]
    notkilled = [r for r in results if r[2] == "❌ 未杀"]
    skipped = [r for r in results if r[2] == "锚点不中"]
    print(f"注入 {len(INJECTIONS)} 个：✅ 被杀 {len(killed)} · ❌ 未杀 {len(notkilled)} · ⚠️ 未施加 {len(skipped)}")
    if notkilled:
        print()
        print("★★ 未被杀 —— 这些门在对应输入上**不会红**（= 日志，不是判据）：")
        for label, gate, _, _ in notkilled:
            print(f"  · [{gate}] {label}")
    seen = sorted({r[1] for r in results})
    print()
    print(f"本次覆盖到的门：{seen}")
    missing = [g for g in BASE if g not in seen]
    print(f"★ 未被任何注入覆盖的门（仍需负控）：{missing}")
    return 1 if (notkilled or skipped or end_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
