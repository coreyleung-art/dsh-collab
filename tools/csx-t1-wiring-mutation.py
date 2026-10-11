#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csx-t1-wiring-mutation.py — T1 负控：`--contract-check ④`（阶段串 + 接线状态）**能不能红**。

★ 判据来源（裁判交接）：「一个判据若没有能让它失败的输入，**它就不是判据，是日志**。」
★ 本脚本的存在理由：T1 的 DoD 明写负控必须是「在 `csx_checkpoint` 里故意写死一处 `persistWired: false`
  ⇒ `--contract-check` **必须变红**；改回 ⇒ 变绿」——而**光跑正例不算证据**（正例只证明它不误报）。

★★ 零接触（任务书 §2 T1「沙箱复跑」逐字：在**整目录副本**上跑，原件永不写）：
  做法参考既有 `tools/csx-mutation-check.py` 的复制式改造（整树 copytree 到工作区，
  之后一切变异与跑门都落在副本上）。工作区**不放 /tmp**（本机约定：/tmp 会被清理）。

★ 如实边界：本脚本只证明「门对**这两类**输入会红」，不证明它覆盖全部滞留形态；
  也不证明在役面（在役需 CLD 重启，见任务书 T3）。

退出码：0 = 两条变异**都红**且原件零接触 · 1 = 有变异**没红**（判据空转）或原件被动过 · 2 = 环境/用法错误
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time

SRC = os.path.expanduser("~/dsh-collab/devices/dsh-plugin-context-survival")
NODE = "/opt/homebrew/bin/node"
WORKROOT = os.path.expanduser("~/dsh-collab/guard/mutation-work")
GUARDED = ["lib/index.js", "cli.js", "lib/meta.js"]  # 原件零接触的核对面（含被变异文件本身）

# 两条变异：M1 = 写死布尔（P2 的原形）；M2 = 描述里手写旧措辞（非派生行）
M1 = ("coreStatus: { writeWired: WIRING.write, persistWired: WIRING.persist, recallWired: WIRING.recall },",
      "coreStatus: { writeWired: true, persistWired: false, recallWired: false },")
M2 = ("        + `★ 产出核（lib/checkpoint.js）已实现并全绿，条数由调用时实时读回。逐件状态：${wiringText()}。`,",
      "        + '★ 产出核已实现并全绿；② 落盘 / ③ 召回尚未接线。',")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_contract_check(root):
    r = subprocess.run([NODE, "cli.js", "--contract-check"], cwd=root, capture_output=True, text=True, timeout=180)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    if not os.path.isdir(SRC):
        print("环境错误：插件目录不存在", SRC)
        return 2
    before = {rel: (sha(os.path.join(SRC, rel)), os.stat(os.path.join(SRC, rel)).st_mtime_ns) for rel in GUARDED}

    ts = time.strftime("%Y%m%d-%H%M%S")
    work = os.path.join(WORKROOT, f"t1-{ts}")
    os.makedirs(WORKROOT, exist_ok=True)
    shutil.copytree(SRC, work, ignore=shutil.ignore_patterns(".git", "node_modules"))
    print(f"# 工作副本（原件零接触）：{work}\n")

    # ── 基线：副本上未变异 ⇒ 必须绿 ──
    code0, out0 = run_contract_check(work)
    print("=== [基线·副本未变异] node cli.js --contract-check ===")
    print(out0.rstrip())
    print(f"[exit:{code0}]\n")

    failures = []
    if code0 != 0:
        failures.append("基线本应 exit 0（副本未变异却已红）")

    results = {}
    for name, (old, new) in (("M1 写死 persistWired:false", M1), ("M2 描述手写旧措辞", M2)):
        target = os.path.join(work, "lib/index.js")
        src = open(target, encoding="utf-8").read()
        if old not in src:
            print(f"!! {name}：锚点未命中（源码已演进）⇒ 本变异**未施加**，如实报 not-applied")
            failures.append(f"{name} 锚点未命中（not-applied）")
            continue
        open(target, "w", encoding="utf-8").write(src.replace(old, new, 1))
        code, out = run_contract_check(work)
        print(f"=== [{name}] node cli.js --contract-check ===")
        print(out.rstrip())
        print(f"[exit:{code}]\n")
        red = code != 0 and "④" in out
        results[name] = red
        if not red:
            failures.append(f"{name} **没有变红** ⇒ ④ 对该形态空转")
        # 还原副本，为下一条变异复位
        shutil.copy2(os.path.join(SRC, "lib/index.js"), target)

    # ── 原件零接触核对 ──
    after = {rel: (sha(os.path.join(SRC, rel)), os.stat(os.path.join(SRC, rel)).st_mtime_ns) for rel in GUARDED}
    touched = [rel for rel in GUARDED if before[rel] != after[rel]]
    print("=== 原件零接触核对 ===")
    for rel in GUARDED:
        print(f"  {rel}: sha {before[rel][0][:16]} → {after[rel][0][:16]} · mtime {'同' if before[rel][1] == after[rel][1] else '变了'}")
    print("  ⇒ " + ("零接触 ✓（sha 与 mtime 均未变）" if not touched else f"★ 原件被改动：{touched}"))
    if touched:
        failures.append(f"原件被改动：{touched}")

    # 副本用毕即删（结论已落 stdout；不留在工作区里冒充"实验残留"）
    shutil.rmtree(work, ignore_errors=True)

    print("\n=== 判定 ===")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}：{'变红' if v else '未红'}")
    if failures:
        print("  ❌ 负控未通过：" + " ｜ ".join(failures))
        return 1
    print("  ✅ 两条变异均使 ④ 变红，且原件零接触")
    return 0


if __name__ == "__main__":
    sys.exit(main())
