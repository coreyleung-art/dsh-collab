#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变异检验：核对了的断言集**真的会红吗**？

★ 判据思路来自 `scripts/assertion-set-consistency.py`：
  「断言集是工具，不是文档；**审它的正确方式是执行它，而不是阅读它**」
  「**不一致只存在于两条之间的关系里**」
⇒ 本脚本把该哲学用在**本插件自己的断言集**上：
  改动**纯核**里一处真实行为 ⇒ 断言集**必须变红**。
  若某处改动**不导致变红** ⇒ 那片区域**无人看守**（可能是恒真断言、也可能是覆盖缺口）。

★ 为什么这正好治本会话的病：
  我今天的事故全是「**读不出来、只能跑出来**」—— `err()` 绑错异常类致 5 条恒假红 ·
  落链断言 5 次查错字段 · 交叉核对只覆盖 1/4 粒度 · 恒真断言。**通读全都能过。**

★ 安全：每次改动前备份到 /tmp，finally 里还原并**逐字节校验**。
"""
import hashlib
import os
import shutil
import subprocess
import sys

P = os.path.expanduser("~/dsh-collab/devices/dsh-plugin-context-survival")
NODE = "/opt/homebrew/bin/node"
# ★★ 工作副本与还原备份**必须移出 /tmp**（2026-10-10 · 0637278c 指出的复合缺陷）：
#   形态3 的判据不是「是不是证据」，而是「**它丢了会不会让某机制失效**」。
#   此处有复合：**启动自愈依赖本目录的备份 ⇒ /tmp 被清理 ⇒ 自愈本身失效。**
#   ⇒ 移到 guard 下的持久路径。★ 注：零接触改造后，本目录的备份**已非承重**
#   （原件不再被写），保留仅作历史残留兜底。
TMP = os.path.expanduser("~/dsh-collab/guard/mutation-work")

# (标签, 文件, 原文, 替换文, 期望被哪套杀掉)
MUTATIONS = [
    ("M1 官方阈值比率 80→79",
     "lib/budget.js", "export const OFFICIAL_THRESHOLD_PCT = 80;",
     "export const OFFICIAL_THRESHOLD_PCT = 79;"),
    ("M2 抢先上限默认 70→75",
     "lib/budget.js", "preemptPct: 70,", "preemptPct: 75,"),
    ("M3 L1 引文预算 32→64",
     "lib/checkpoint.js", "l1QuoteTokens: 32,", "l1QuoteTokens: 64,"),
    ("M4 ★ end-seed 陈旧豁免去掉（承重性）",
     "lib/events.js", "if (seedSeq !== null && seedSeq > startSeq) {",
     "if (false) {"),
    ("M5 配对 fold 首切口由 true 改 false",
     "lib/pairing.js", "const cutBalanced = [true];", "const cutBalanced = [false];"),
    ("M6 召回 MISS 冒充 HIT",
     "lib/ledger.js", "status: RECALL_STATUS.MISS,", "status: RECALL_STATUS.HIT,"),
    ("M7 落盘：空文件不再判 DEGRADED",
     "lib/ledger-io.js", "if (text.trim() === '') {", "if (false) {"),
]


# ★★ 默认参数**在 def 时求值一次** ⇒ `cwd=P` 会把工作目录**永久绑定到调用时的 P**，
#   而零接触改造是**运行时**把 P 重指到副本 ⇒ 默认参数**不会跟着变** ⇒
#   变异施加在副本上、断言集却在原件上跑 ⇒ **全变异都测不到（实测 7/7 变 0/7）**。
#   ⇒ 改为在**调用时**解析 P（`cwd=None → cwd = P`）。★ 这是「静默失去判定力」的一个实例。
def sh(cmd, cwd=None):
    if cwd is None:
        cwd = P
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180, cwd=cwd)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_suites():
    """跑两套断言集，返回 (通过?, 摘要)。"""
    r1 = sh(f"{NODE} cli.js --checkpoint-check")
    r2 = sh(f"{NODE} cli.js --recall-check")
    ok = (r1.returncode == 0) and (r2.returncode == 0)
    brief = []
    for name, r in (("K3", r1), ("K4", r2)):
        line = ""
        for l in r.stdout.split("\n"):
            if "断言" in l and "通过" in l:
                line = l.strip()
                break
        if not line:
            line = (r.stderr or r.stdout).strip().split("\n")[0][:80]
        brief.append(f"{name}:{line}")
    return ok, " | ".join(brief)


# ★★ SIGTERM/SIGKILL 防护（2026-10-10 实测事故）：
#   本脚本靠 `finally` 还原 —— 而**超时被 SIGTERM 杀掉时 finally 不执行**。
#   实证后果：一次超时的运行把 `lib/ledger-io.js` 留在变异态（`schema: '…-X'`），
#   使 `--recall-check` 变 155/156 —— **工作区被静默腐蚀，而本脚本的"还原逐字节校验"根本没跑。**
#   ⇒ 修法：**启动时先无条件还原所有遗留备份**。
#     完整运行结束时文件与备份相同 ⇒ 还原是 no-op；被打断的运行 ⇒ 当场修复。
#     这比信号处理器更稳（信号处理挡不住 SIGKILL；启动自愈挡得住任何死法）。
# ★★ 零接触原件（2026-10-10 · 采纳 0637278c 的修法）
#
# 原设计：改**原件** + `finally` 还原 + 启动自愈兜底。
# 实证缺陷：SIGTERM **绕过 finally** ⇒ 原件被留在变异态 ⇒ 工作区静默腐蚀；
#          启动自愈只能「下次运行时」修 ⇒ **被杀后到下次运行之间原件是坏的**。
# ⇒ 改为：**整棵树复制到临时工作区，一切变异与断言集都在副本上跑，原件零接触。**
#    ⇒ 无「还原」这一步 ⇒ **「还原失败」这个失效面根本不存在**（不是修好了，是消掉了）。
def _make_work_copy():
    """把插件整树复制到临时工作区；返回副本路径（原件此行之后永不写入）。"""
    work = os.path.join(TMP, "work")
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(P, work, ignore=shutil.ignore_patterns(".git", "node_modules"))
    return work


def _tree_sha(root):
    """整树内容 sha（用于证明原件未被触碰）——只算源码与配置，跳过 .git/node_modules。"""
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            h.update(os.path.relpath(fp, root).encode())
            try:
                h.update(open(fp, "rb").read())
            except Exception:
                pass
    return h.hexdigest()


def _heal_leftovers():
    import glob as _glob
    healed = []
    for bk in _glob.glob(os.path.join(TMP, "lib_*")):
        rel = os.path.basename(bk).replace("_", "/", 1).replace("lib_", "lib/", 1)
        # 备份名为 lib_xxx.js -> 目标 lib/xxx.js
        rel = "lib/" + os.path.basename(bk)[len("lib_"):]
        dst = os.path.join(P, rel)
        if os.path.exists(dst) and os.path.exists(bk):
            if hashlib.sha256(open(dst, "rb").read()).hexdigest() != hashlib.sha256(open(bk, "rb").read()).hexdigest():
                shutil.copy2(bk, dst)
                healed.append(rel)
    return healed


def main():
    global P
    os.makedirs(TMP, exist_ok=True)
    _healed = _heal_leftovers()
    _orig_sha_before = _tree_sha(P)
    WORK = _make_work_copy()
    # ★ 把 P 重指到副本 ⇒ 下游所有 `sh(..., cwd=P)` 与 `os.path.join(P, rel)` **自动**落在副本上，
    #   原件路径另存 ORIG（仅用于最后证明"原件未被触碰"）。★ 这是最小改动面：不逐处改写路径。
    ORIG = P
    P = WORK
    print(f"  零接触：变异与断言集均在副本上进行，原件只读（原树 sha 已记）；**不改被核对象**，临时写面 = `guard/mutation-work/`")
    if _healed:
        print(f"  ⚠️ 启动自愈：还原了上次遗留的变异 {_healed}")
    print("csx-mutation-check · 断言集到底会不会红")
    print()

    # 基线：全绿才谈得上"杀掉"
    base_ok, base_brief = run_suites()
    print(f"基线：{'✅ 全绿' if base_ok else '❌ 已红（先修基线）'}")
    print(f"      {base_brief}")
    if not base_ok:
        print("\n❌ 基线不绿 ⇒ 变异检验无意义")
        return 2
    print()

    results = []
    for label, rel, old, new in MUTATIONS:
        path = os.path.join(P, rel)
        backup = os.path.join(TMP, rel.replace("/", "_"))
        shutil.copy2(path, backup)
        before = sha(path)
        src = open(path, encoding="utf-8").read()
        if src.count(old) != 1:
            results.append((label, "锚点不中", f"{src.count(old)} 次 ⇒ 未测", before))
            print(f"  ⚠️ {label} —— 锚点命中 {src.count(old)} 次（未施加）")
            continue
        try:
            open(path, "w", encoding="utf-8").write(src.replace(old, new))
            ok, brief = run_suites()
            killed = not ok
            results.append((label, "✅ 被杀" if killed else "❌ 未杀", brief, before))
            print(f"  {'✅' if killed else '❌'} {label} —— {'被杀（断言集变红）' if killed else '**未被杀**（该处无人看守）'}")
        finally:
            shutil.copy2(backup, path)
            after = sha(path)
            if after != before:
                print(f"     ⚠️ 还原校验失败！{rel} 与备份不一致")
                return 2
    print()

    # 终局：确认还原后仍全绿
    end_ok, end_brief = run_suites()
    print(f"还原后：{'✅ 全绿' if end_ok else '❌ 未还原干净'}")
    print(f"      {end_brief}")
    print()

    killed = [r for r in results if r[1] == "✅ 被杀"]
    notkilled = [r for r in results if r[1] == "❌ 未杀"]
    skipped = [r for r in results if r[1] == "锚点不中"]
    print(f"变异 {len(MUTATIONS)} 个：✅ 被杀 {len(killed)} · ❌ 未杀 {len(notkilled)} · ⚠️ 未施加 {len(skipped)}")
    if notkilled:
        print()
        print("★ 未被杀的变异 —— 这些区域**没有断言在看守**：")
        for label, _, brief, _ in notkilled:
            print(f"  · {label}")
            print(f"      {brief}")
    print()
    if notkilled or skipped or not end_ok:
        return 1
    print("✅ 全部变异被杀 ⇒ 断言集在这些点上**真的会红**（不是恒真）")
    _orig_sha_after = _tree_sha(ORIG)
    if _orig_sha_after != _orig_sha_before:
        print("\n❌ **原件被触碰了**（sha 变化）—— 零接触设计失效，须立即排查")
        return 2
    print(f"\n✅ 原件未被触碰（整树 sha 前后一致：{_orig_sha_before[:16]}…）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
