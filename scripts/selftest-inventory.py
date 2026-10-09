#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具族自测入口盘点 —— 把「盘点」从一次性手工探针，变成一次调用产出的读数。

由来（2026-09-28）：
  我做过一次手工盘点，量出「5/10 有可达的 --selftest 入口」，其中把 `dup-skeleton.py` 判为
  「✅ 有入口且跑通」—— **判错了**。它的首行是「扫描 1 个文件 · 0 个函数（≥3 行）」，
  即它把 `--selftest` 当成**文件路径**、照常跑了默认扫描并 exit=0。
  ⇒ 证据就在我自己的探针输出里，**我读的是 exit 码，没读输出**。

★ 本工具用的判据（与那次手探的区别就在这里）：
  1. **不用 exit 码分态** —— `exit=0` 对「真通过」与「静默跑默认动作」**同痕**。
  2. 判「--selftest 有没有真跑」看**输出里有没有工具自报的自测标识/断言**
     （grep 计 `selftest|自测|must_pass|must_reject|期望|PASS|✅` 的行数，>0 才算跑了自测）。
  3. 判「怎么处理不认识的输入」用**伪造旗标** `--zzz-bogus-flag`（老登的那条一般化：
     特定参数是实例，不认识的参数是类别）⇒ 看它有没有**说出那个旗标**。

五态（① ④ 为合格，② ③ ⑤ 为缺口）：
  ① 有自测入口且真跑 ｜ ② 静默跑默认动作（输出像正常报告）｜ ③ 崩（Traceback）
  ④ 干净报用法/不认识的参数 ｜ ⑤ = ② 的体面版：把旗标当对象、错误消息指向另一个原因

用法：python3 selftest-inventory.py [--tools a,b,c]
退出码：0 = 全部合格；1 = 有缺口（逐条列出）。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, re, subprocess, sys, time



# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/selftest-inventory.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

_KNOWN = {"--tools", "--dir", "-h", "--help"}
_unknown = [a for a in sys.argv[1:] if a.startswith("-") and a not in _KNOWN]
if _unknown:
    print(f"❌ 不认识的参数: {' '.join(_unknown)}")
    print(f"   本工具接受的参数: {' '.join(sorted(_KNOWN))}")
    print("   ★ 加这道检查的起因：本工具自己曾把伪造旗标【静默忽略】、照常跑默认动作")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
BOGUS = "--zzz-bogus-flag"
CRASH = "Traceback (most recent call last)"
# ★ R1 的判据被改了四次，每次都因为「同痕」（这是本工具最该记住的一件事）：
#   第 1 版 exit 码        ⇒ exit=0 对「真通过」与「静默跑默认动作」同痕（dup-skeleton 被我判成①）
#   第 2 版 宽标记集(✅/PASS)⇒ dup-skeleton 的【默认动作输出】里也有 ✅ ⇒ 又中了（假阳性）
#   第 3 版 窄标记(自测/selftest)⇒ card-json-check 的崩溃消息 `FileNotFoundError: '--selftest'`
#                             回显了旗标名 ⇒ 假阳性；加「排除旗标回显行」堵住
#   第 4 版 窄标记+排除回显  ⇒ ts-not-future-check 根本不印「自测」二字、只打断言行 ⇒ 假阴性
#   ⇒ ★ 结论：任何「找输出里的某个字面」的判据都同时有假阳性与假阴性两侧。
#     正解与我给老登那条建议**同构**：不要把「识别」做成扫字串，要做成【必填字段】——
#     让每个工具在自测输出里打一行固定形态的机器可读标识：`SELFTEST <工具名> <通过>/<总数>`。
#     这一行在默认动作里不可能出现（默认动作不知道总数）⇒ 二值、不撞车。
SELFTEST_LINE = re.compile(r"^SELFTEST\s+\S+\s+\S+", re.M)
DEFAULT_TOOLS = ["verification-level-lint", "inplace-pointer-audit", "absence-claim-lint",
                 "ts-not-future-check", "thread-fork-audit", "card-json-check", "dup-skeleton",
                 "msg-count-lint", "bb-put-both", "put-card"]


def ran_selftest(out, out_default):
    """工具是否真的声明自己在跑自测。

    ★ 判据最终定为【两段】—— 第二段是被老登现场逼出来的：
      他只写 `SELFTEST OK`（无数字）时，**默认动作可能顺手把这行也打了** ⇒ 那一行不携带信息。
      ⇒ 所以判据是：㈠`--selftest` 的输出里有 SELFTEST 标识行 **且** ㈡**默认动作的输出里没有**。
      第二段等价于「这里有一个只有真跑了自测才会出现的量」——但它**不查格式**，
      所以不用管各工具是写 `6/6` 还是 `16 PASS / 0 FAIL`（格式不统一正是找字面判据必然漏的原因）。
    """
    if CRASH in out:
        return 0, "崩溃（不是自测）"
    m = SELFTEST_LINE.search(out)
    if not m:
        return 0, "没有 SELFTEST 标识行 ⇒ 无法证明它跑的是自测（未申报）"
    if SELFTEST_LINE.search(out_default):
        return 0, "★ 该标识行在【默认动作】的输出里也出现 ⇒ 它不携带信息（可被伪造）"
    return 1, f"有 SELFTEST 行，且默认动作不打它：{m.group(0).strip()}"


def run(path, args, timeout=12):
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, path] + args, capture_output=True, text=True, timeout=timeout)
        code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        code, out = "timeout", ""
    return code, out, time.time() - t0


def _discover(here):
    """★ 名单从【目录枚举】得来，不手写。

    起因（2026-09-28，当天）：`DEFAULT_TOOLS` 原本是**手写的 10 个名字**，于是
    **我当天新建的两个工具（catchall-scan.py · selftest-inventory.py 自己）从未进过盘点** ——
    而它们恰好带着我花一整天编目的那个缺陷（伪造旗标 ⇒ 静默跑默认动作）。
    ⇒ 这暴露了我上一卡那条「把判别对象换到我这一侧就安全」的一个反例：
      **世界侧 = 无法枚举 · 我这一侧 = 可以枚举、但名单可能不完整。**
    ⇒ 修法：名单由 `*.py` 枚举产生 ⇒ 那一刻「漏」变成不可能；`--tools` 只用于收窄。
    """
    out = sorted(f[:-3] for f in os.listdir(here) if f.endswith(".py"))
    return out


def main():
    here = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else HERE
    all_py = _discover(here)
    tools = all_py
    if "--tools" in sys.argv:
        tools = sys.argv[sys.argv.index("--tools") + 1].split(",")
    elif "--exhaustive" not in sys.argv:
        # ★ 预筛（默认开）：只动态跑「文件里出现过 SELFTEST 字面」的那些。
        #   起因：名录改成目录枚举后是 218 个文件 × 2 次子进程 ⇒ 跑不动（实测超时）。
        #   ★ 预筛的代价必须写出来：**它是一道【找字面】的闸** ⇒ 会漏掉「不写字面
        #     但真跑自测」的工具 ⇒ 所以报出跳过了几个，并给 --exhaustive 兜底。
        keep = []
        for t in all_py:
            try:
                if "SELFTEST" in open(os.path.join(here, t + ".py"), encoding="utf-8", errors="replace").read():
                    keep.append(t)
            except OSError:
                pass
        skipped = [t for t in all_py if t not in keep]
        print(f"  （预筛：{len(all_py)} 个 .py 里，{len(keep)} 个含 SELFTEST 字面 ⇒ 只动态跑这些）")
        # ★ 被跳过的名字要列出来，不能只报个数。
        #   实测假阴性一例：`put-card` —— 它的 SELFTEST 字面在【兄弟文件】 put-card-selftest.py 里，
        #   不在 put-card.py 里 ⇒ 预筛把它跳过了，而它恰好是当时【唯一】合格的一个。
        #   ⇒ 只报「跳过 N 个」时那个 N 里藏着「唯一合格的那个」；列出名字才可发现。
        print(f"   ★ 未动态测的 {len(skipped)} 个（已知假阴性：put-card，其标识在兄弟文件里）：")
        print("     " + " ".join(skipped[:40]) + (" …" if len(skipped) > 40 else ""))
        print("     ⇒ 要全跑用 --exhaustive（代价：会执行 218 个工具，慢且有副作用风险）")
        tools = keep
    tools = [t[:-3] if t.endswith(".py") else t for t in tools]

    print("工具族自测入口盘点（判据：①自报 SELFTEST 行 ②该行在默认动作里不出现）")
    print(f"被测目录: {here}")
    print()
    print(f"  {'工具':26s} {'selftest态':10s} {'伪造旗标态':12s} 证据")
    gaps = []
    for t in tools:
        f = os.path.join(here, t + ".py")
        if not os.path.exists(f):
            print(f"  {t:26s} {'文件不存在':10s} {'—':12s} （我档案里可能登记过一个不存在的工具）")
            gaps.append((t, "MISSING", "文件不存在"))
            continue
        c1, o1, _ = run(f, ["--selftest"])
        c0, o0, _ = run(f, [])
        marks, why1 = ran_selftest(o1, o0)
        st1 = "①真跑" if marks > 0 else ("③自测崩" if CRASH in o1 else "②没跑自测")
        c2, o2, _ = run(f, [BOGUS])
        named = "bogus" in o2
        crashed = CRASH in o2
        usage = bool(re.search(r"usage:|用法", o2))
        if crashed:
            st2 = "③崩"
        elif named:
            st2 = "④报出旗标"
        elif usage:
            st2 = "④报用法"
        else:
            st2 = "⑤默默当成对象"
        ev = f"自测标识行={marks}（{why1}）· 旗标 exit={c2} · 说出旗标={named}"
        print(f"  {t:26s} {st1:10s} {st2:12s} {ev}")
        if st1.startswith(("②", "③")):
            gaps.append((t, "NO_SELFTEST_ENTRY", f"selftest 态={st1}（exit={c1}，{why1}）"))
        if st2.startswith(("③", "⑤")):
            gaps.append((t, "BAD_UNKNOWN_INPUT", f"伪造旗标的处理={st2}（exit={c2}）"))

    print()
    if not gaps:
        print("★ 全部合格：每个工具都有真跑的自测入口，且对不认识的输入有声。")
        return 0
    print(f"缺口 {len(gaps)} 项：")
    for t, kind, why in gaps:
        print(f"  ✗ {t:26s} {kind:22s} {why}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
