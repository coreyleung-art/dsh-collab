#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""常量变异面扩大：**自动**找出各纯核导出常量里的每个值，逐个变异，看断言集会不会红。

★ 为什么做（裁判确认的行动）：
  M1/M2 只是**两个实例**，而「参照系共用」是**模式** ⇒ 按「按判据修不按实例修」，
  必须把变异面**从手挑**扩成**穷举**。★ 与上一轮「交叉核对从 1 个粒度扩到 7 个」是同一个动作。

★ 不预设结论：可能不止两处未被杀，也可能只有两处。**两种结果都如实报。**

★ 安全：每个变异前备份、finally 还原并逐字节校验；任一还原失败立即中止。
"""
import hashlib
import os
import re
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

# ★★ 内部枚举白名单（**判定「未杀是否算缺口」的判据**）
#   分类依据（见 CHANGELOG 0.10.0 与 Z1 组注释）：
#     外部事实 —— 必须与外部来源逐字一致（官方运行时 / 立项书原文 / 持久化格式）⇒ 改了**静默失效且无症状** ⇒ 必须钉
#     内部枚举 —— 用到的地方都用同一常量 ⇒ 改了是自洽的 ⇒ **不必钉**，但**必须如实报出**
#   ★ 本白名单即「内部枚举」那一侧；未杀项若**不在**本表 ⇒ 判为真缺口 ⇒ exit 1。
INTERNAL_ENUM_KEYS = {
    # budget.js —— 决策/原因码（包内自洽；不改对外语义的只有这几个）
    "COMPRESS", "SKIP_BELOW_THRESHOLD", "SKIP_COMPACTION_IN_PROGRESS",
    "NO_TOKEN_METER", "NO_SESSION", "NO_TARGET", "NO_LLM", "NO_CONTEXT_WINDOW",
    "OK", "IMPOSSIBLE", "NOTHING_TO_SHADOW",
    # checkpoint.js —— 阶梯档位与计划结论
    "L1_TRIM", "L2_DROP_TOOL_RESULTS", "L3_DROP_REST",
    # pairing.js / ledger？—— 见下方注释：这三类**不**在白名单
}

# ★ 另两类「正确地未杀」（不是缺口，但**理由与内部枚举不同**）：
#   · 非行为字段 —— 引文串（source/judge 等）。判据只查**子串包含**，追加字符不破坏包含关系
#     ⇒ 未杀是**判据口径本来就对**，不是漏。★ 但若某天断言改成**全等**，这里就不再正确。
#   · 被支配常量 —— 取值在该上下文中被另一个更大的量支配，改它**无行为差异**。
#     实证 `neededSavingsTokens: 0→1` 未杀，因为下游取 `max(minSavingsTokens=32, needed)` ⇒ 32 支配 1。
#     ★ **它的安全是「有条件的」**：条件 = 被支配方仍小于支配方 ⇒ 若 `minSavingsTokens` 被改小，本项即刻变成真缺口。
NON_BEHAVIORAL_KEYS = {"source", "judge"}            # 引文串（子串包含式判据）
DOMINATED_KEYS = {"neededSavingsTokens"}             # 被 minSavingsTokens 支配（有条件的无害）

CORES = [
    "lib/budget.js", "lib/checkpoint.js", "lib/events.js", "lib/pairing.js",
    "lib/ledger.js", "lib/ledger-io.js", "lib/calibration.js", "lib/notice.js",
]

# 抓 const 对象里的 `KEY: 值,`；值限数字/字符串/布尔（不抓嵌套对象，避免改坏结构）
KV = re.compile(r"^(\s+)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(-?\d+(?:\.\d+)?|'[^']*'|true|false)\s*(,?)\s*$")


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


def suites_ok():
    a = sh(f"{NODE} cli.js --checkpoint-check")
    b = sh(f"{NODE} cli.js --recall-check")
    return a.returncode == 0 and b.returncode == 0


def mutate_value(v):
    """产生一个**行为不同**的值（不是格式变化）。"""
    if v.startswith("'"):
        inner = v[1:-1]
        return "'" + (inner + '-X' if inner else 'X') + "'"
    if v == "true":
        return "false"
    if v == "false":
        return "true"
    if "." in v:
        f = float(v)
        return repr(f + 1.0) if f < 1000 else repr(f / 2)
    n = int(v)
    if n == 0:
        return "1"
    if n < 10:
        return str(n + 1)
    if n < 10000:
        return str(n + 1)
    return str(n // 2)


def collect(path):
    """返回 [(行号, 原值串, KEY)]，只收 const 对象块内的 KV。"""
    out = []
    depth = 0
    in_block = False
    for i, line in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        if re.match(r"^export const [A-Z_][A-Z0-9_]* = Object\.freeze\(\{", line):
            in_block = True
            depth = 1
            continue
        if in_block:
            depth += line.count("{") - line.count("}")
            if depth <= 0:
                in_block = False
                continue
            m = KV.match(line)
            if m:
                out.append((i, m.group(3), m.group(2)))
    return out


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
    if not suites_ok():
        print("❌ 基线不绿 ⇒ 变异无意义")
        return 2
    print("基线：✅ 两套断言集全绿")
    print()

    killed, notkilled, skipped = [], [], []
    total = 0
    for rel in CORES:
        path = os.path.join(P, rel)
        items = collect(path)
        if not items:
            continue
        src0 = open(path, encoding="utf-8").read()
        lines0 = src0.split("\n")
        bk = os.path.join(TMP, rel.replace("/", "_"))
        shutil.copy2(path, bk)
        h0 = sha(path)
        for lineno, val, key in items:
            total += 1
            newval = mutate_value(val)
            lines = src0.split("\n")
            # 保持缩进与尾随逗号
            indent = re.match(r"^(\s*)", lines[lineno - 1]).group(1)
            lines[lineno - 1] = f"{indent}{key}: {newval},"
            try:
                open(path, "w", encoding="utf-8").write("\n".join(lines))
                ok = suites_ok()
                tag = f"{rel}  {key}: {val} \u2192 {newval}"
                if ok:
                    notkilled.append(tag)
                else:
                    killed.append(tag)
            finally:
                shutil.copy2(bk, path)
                if sha(path) != h0:
                    print(f"  ⚠️ 还原校验失败：{rel}")
                    return 2
    # ★★ 假通过防护（0637278c 的「空集通过」同族）：**零常量被收集 ⇒ 判据不可用 ⇒ exit 2**
    #   实证：把 collect() 判据改坏后，本工具印的是「✅ 全部被杀 ⇒ 不存在未看守的常量」+「✅ 无真缺口」+ **exit 0**
    #   —— 在**一个空集上**说「全部被杀」。★ 这比漏报更误导：它**主动断言**了一件没检查过的事。
    if total == 0:
        print("环境错误：**一个常量都没被收集到** ⇒ 判据**不可用**（解析判据可能已失效）", file=sys.stderr)
        print("★ 这是「空集通过」防护：**零输入不是「全部被杀」**，是判据没跑起来。", file=sys.stderr)
        return 2

    print(f"共变异 {total} 个常量值：✅ 被杀 {len(killed)} · ❌ 未杀 {len(notkilled)}")
    print()
    # ★★ 判定分两类（而不是"有未杀就红"）—— 未杀 ∩ 外部事实 = 真缺口；未杀 ∩ 内部枚举 = 预期内
    real_gaps, expected = [], []
    for t in notkilled:
        key = t.split()[-4].rstrip(":") if len(t.split()) >= 4 else t
        # 从 "rel  KEY: old → new" 里取 KEY
        import re as _re
        m = _re.search(r"\s([A-Za-z_][A-Za-z0-9_]*):\s", t)
        key = m.group(1) if m else ""
        if key in INTERNAL_ENUM_KEYS or key in NON_BEHAVIORAL_KEYS or key in DOMINATED_KEYS:
            expected.append(t)
        else:
            real_gaps.append(t)

    if expected:
        print(f"★ 未杀但**属内部枚举**（{len(expected)} 条）—— 按分类**不必钉**，如实报出：")
        for t in expected:
            print("  ·", t)
        print()
    if real_gaps:
        print(f"★★ 未杀且**不属内部枚举**（{len(real_gaps)} 条）—— 这些是**真缺口**（参照系共用或覆盖缺口）：")
        for t in real_gaps:
            print("  ·", t)
        print()
    if not notkilled:
        print("✅ 全部被杀 ⇒ 在本轮变异面上不存在未看守的常量")
    print()
    if real_gaps:
        print(f"❌ 真缺口 {len(real_gaps)} 处 ⇒ 须补钉")
        return 1
    print(f"✅ 无真缺口（未杀 {len(expected)} 条全属内部枚举，已在上面如实列出）")
    _orig_sha_after = _tree_sha(ORIG)
    if _orig_sha_after != _orig_sha_before:
        print("\n❌ **原件被触碰了**（sha 变化）—— 零接触设计失效，须立即排查")
        return 2
    print(f"\n✅ 原件未被触碰（整树 sha 前后一致：{_orig_sha_before[:16]}…）")

    return 0


if __name__ == "__main__":
    sys.exit(main())
