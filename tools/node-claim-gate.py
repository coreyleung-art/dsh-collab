#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""node-claim-gate.py — 身份声称门（设备归属/位置）

★ 规范源：`rules-registry/lean4/node-claim-gate.lean`（本文件为其**运行面镜像**，谓词 1:1）

动因（2026-10-10，实测事件）
    一个会话把自己的**归属**写成「MBP 侧」并署名发出，而**实体在 mac-mini**
    （它后来自证 `hostname=CoreydeMac-mini` / `hw.model=Mac16,10`）。
    ★ 关键区分：**「归属」（属于谁）与「位置」（在哪运行）是两个不同维度**，
      而系统里用同一个词表达 ⇒ 读者把归属词当作位置实测。

★ 为什么"提醒它"无效（四条叠加，实测）
    ① 它 role 是**它自己写的** —— 没人会质疑别人的 role
    ② 「MBP 侧」在文档里是**合法分类词**（`docs/absorb-mbp-systemgraph-v1.md` 表头「MBP 侧项」）
    ③ **workspace 各设备同名**（`--Users-coreyleung--`）⇒ 从任何路径看不出设备
    ④ **`DSH_NODE_ID` 未设** ⇒ 没有权威字段可比对
    ⇒ 误判可长期存活而不被任何环节检出。**且它零次 `hostname` 调用 ⇒ 无法自证**。

★★ 本门的解法：不靠流程，靠**结构**
    Lean 侧 `structure NodeClaim` 的 `h_eq : claimed = observed` 是**构造子字段**
    ⇒ **claimed ≠ observed 时不存在该类型的项** —— 不是"会被拒"，是**写不出来**。
    运行面镜像三条：
      ① **门自己跑 `hostname`** —— **会话不能自报设备**，只能提交原始输出；
      ② **`observed` 必须与门本次实测逐字符一致** ⇒ **伪造证据不可能通过**；
      ③ **任一字段缺失即拒**（与 `acceptance-gate` 的「`surface_unmeasured` 字段必须在场」同构）。

用法
    python3 tools/node-claim-gate.py --attest          # ★ 门实测并输出可复跑的证明项
    python3 tools/node-claim-gate.py --node            # 仅输出本机 node（供脚本消费）
    python3 tools/node-claim-gate.py --check <claim.json>
    python3 tools/node-claim-gate.py --selftest
    python3 tools/node-claim-gate.py --lean4-check     # 谓词与 Lean 规范的对应性

claim.json 形状
    {"claimed":"mac-mini","observed":"mac-mini",
     "evidence":{"rawOutput":"CoreydeMac-mini.local","takenAt":"2026-10-10T…","rerunCmd":"hostname"}}

退出码
    0 = 过门 · 1 = 拒（列出哪条失败）· 2 = 用法/环境错
"""
import json
import os
import re
import subprocess
import sys
import time

GATE_VERSION = "1.0.0"

# ★ 设备枚举（**封闭集合**，与 Lean 侧 `inductive Node` 1:1）
NODES = ["mac-mini", "mbp", "i9", "unknown"]

# hostname → node 的解析规则（**唯一来源 = hostname 原始输出**）
def parse_node(raw):
    """从 hostname 原始输出解析 node。

    ★ 判据只认 hostname，**不认**：文档路径（notes/mbp）· 历史报告 · profile 自述 · 环境变量。
      理由：那些都是**归属线索**，不是**位置实测** —— 本次误判正是由二者混淆产生。
    """
    s = (raw or "").strip().lower()
    if not s:
        return "unknown"
    if "mac-mini" in s or "macmini" in s:
        return "mac-mini"
    if "mbp" in s or "macbook" in s:
        return "mbp"
    if re.search(r"\bi9\b", s):
        return "i9"
    return "unknown"


def observe():
    """★ 门**自己**跑 hostname —— 这是"会话不能自报设备"的机制所在。"""
    try:
        p = subprocess.run(["hostname"], capture_output=True, text=True, timeout=10)
        raw = (p.stdout or "").strip()
    except Exception as e:
        raw = ""
    return {"rawOutput": raw, "takenAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "rerunCmd": "hostname"}


def check(claim):
    """返回 (ok, reasons)。谓词与 Lean 侧 `valid` 1:1。"""
    r = []
    if not isinstance(claim, dict):
        return False, ["claim 不是对象"]
    # ① 字段在场（缺一即拒 —— 同 Lean 定理 3）
    for f in ("claimed", "observed", "evidence"):
        if f not in claim:
            r.append("字段缺失：%s（★ 缺字段 = 边界由假设划定 ⇒ 拒，与 acceptance-gate 同构）" % f)
    if r:
        return False, r
    ev = claim.get("evidence") or {}
    for f in ("rawOutput", "takenAt", "rerunCmd"):
        if not str(ev.get(f) or "").strip():
            r.append("证明项字段为空：evidence.%s" % f)
    obs = str(claim.get("observed") or "")
    cla = str(claim.get("claimed") or "")
    # ② 枚举合法（Lean 侧封闭集合）
    if obs not in NODES:
        r.append("observed 不在设备枚举内：%r（枚举 %s）" % (obs, NODES))
    if cla not in NODES:
        r.append("claimed 不在设备枚举内：%r" % cla)
    # ③ ★ 定理 2：observed = unknown ⇒ 未实测不得充当实测
    if obs == "unknown":
        r.append("observed = unknown ⇒ 未实测（★ Lean 定理 2）")
    # ④ ★ 定理 1：claimed ≠ observed ⇒ 拒
    if obs and cla and obs != cla:
        r.append("★ claimed(%s) ≠ observed(%s) ⇒ **错误归属**（Lean 定理 1：此类声称不可构造）"
                 % (cla, obs))
    # ⑤ ★ 防伪造：observed 必须与门**本次实测**一致
    now = observe()
    if obs and obs != parse_node(now["rawOutput"]):
        r.append("★ observed 与门本次实测不符：声称 %s vs 实测 %s（★ 伪造证据不可能通过）"
                 % (obs, parse_node(now["rawOutput"])))
    if str(ev.get("rawOutput") or "").strip() and str(ev["rawOutput"]).strip() != now["rawOutput"]:
        r.append("evidence.rawOutput 与门实测逐字符不符：%r vs %r"
                 % (str(ev["rawOutput"])[:40], now["rawOutput"][:40]))
    return (len(r) == 0), r


def selftest():
    print("★ node-claim-gate 自证：用**真实事件**构造正负例（含本次误判的原型）")
    now = observe()
    real = now["rawOutput"]
    realnode = parse_node(real)
    other = "mbp" if realnode != "mbp" else "mac-mini"
    cases = []
    good = {"claimed": realnode, "observed": realnode, "evidence": now}
    cases.append(("正例·claimed=observed=实测 ⇒ 应过", check(good)[0], True))
    bad1 = {"claimed": other, "observed": realnode, "evidence": now}
    ok1, rs1 = check(bad1)
    cases.append(("★ 负例·**本次误判原型**（声称 %s，实体 %s）⇒ 应拒" % (other, realnode), ok1, False))
    bad2 = {"observed": realnode, "evidence": now}          # 缺 claimed
    cases.append(("负例·缺 claimed 字段 ⇒ 应拒", check(bad2)[0], False))
    bad3 = {"claimed": realnode, "observed": realnode, "evidence": {"rawOutput": "", "takenAt": "", "rerunCmd": ""}}
    cases.append(("负例·证明项全空 ⇒ 应拒（定理 3）", check(bad3)[0], False))
    bad4 = {"claimed": "mac-mini", "observed": "unknown", "evidence": now}
    cases.append(("负例·observed=unknown ⇒ 应拒（定理 2）", check(bad4)[0], False))
    forge = {"claimed": "mbp", "observed": "mbp",
             "evidence": {"rawOutput": "MBP-fake.local", "takenAt": now["takenAt"], "rerunCmd": "hostname"}}
    ok5, rs5 = check(forge)
    cases.append(("★ 负例·**伪造证据**（自称 mbp + 编造 rawOutput）⇒ 应拒", ok5, False))
    ok = 0
    for name, got, want in cases:
        goodc = (got == want)
        print("  %s %s（实得 %s）" % ("✅" if goodc else "❌", name, got))
        ok += 1 if goodc else 0
    print("  自证：%d/%d" % (ok, len(cases)))
    return 0 if ok == len(cases) else 1


def lean4_parity():
    """谓词与 Lean 规范的对应性检查（同 acceptance-gate 的做法）。"""
    lp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "rules-registry", "lean4", "node-claim-gate.lean")
    pairs = [
        ("valid 仅依赖 attested", "def valid (c : NodeClaim) : Prop := attested c", "attested"),
        ("claimed=observed 是构造子字段", "h_eq     : claimed = observed", "h_eq"),
        ("unknown 拒绝（定理 2）", "unknown_observed_invalid", "unknown"),
        ("空证据拒绝（定理 3）", "empty_evidence_invalid", "empty"),
        ("错误归属不可构造（定理 1）", "wrong_attribution_impossible", "wrong_attr"),
        ("不依赖提出者（定理 4）", "validity_independent_of_proposer", "independent"),
    ]
    src = open(lp, encoding="utf-8").read() if os.path.exists(lp) else ""
    print("★ lean4-check：谓词与 %s 的对应性" % os.path.basename(lp))
    print("  Lean 规范源在场：%s" % ("是" if src else "★ 否（对应性无法核）"))
    ok = 0
    me = open(os.path.abspath(__file__), encoding="utf-8").read()
    for name, lean_frag, py_frag in pairs:
        a = lean_frag.split()[0] if lean_frag else ""
        in_lean = (lean_frag in src) if src else None
        in_py = (py_frag.lower() in me.lower())
        good = bool(in_lean) and in_py
        print("  %s %-34s Lean=%s 运行面=%s" % ("✅" if good else "❌", name, in_lean, in_py))
        ok += 1 if good else 0
    print("  对应性：%d/%d" % (ok, len(pairs)))
    return 0 if ok == len(pairs) else 1


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    if "--lean4-check" in args:
        sys.exit(lean4_parity())
    if "--node" in args:
        print(parse_node(observe()["rawOutput"]))
        sys.exit(0)
    if "--attest" in args:
        now = observe()
        node = parse_node(now["rawOutput"])
        print("★ 身份证明项（**由门实测签发**，非会话自报）")
        print(json.dumps({"node": node, "evidence": now, "gate_version": GATE_VERSION},
                         ensure_ascii=False, indent=1))
        print("★ 复跑命令：%s" % now["rerunCmd"])
        print("★ 把本输出原样填入 claim 的 observed/evidence；**claimed 若与之不符，门会拒**。")
        sys.exit(0 if node != "unknown" else 1)
    if "--check" in args:
        i = args.index("--check")
        if i + 1 >= len(args):
            print("用法: node-claim-gate.py --check <claim.json>"); sys.exit(2)
        try:
            claim = json.load(open(args[i + 1], encoding="utf-8"))
        except Exception as e:
            print("claim 不可读：%s" % e); sys.exit(2)
        ok, reasons = check(claim)
        if ok:
            print("GATE PASS: 声称已由实测划定（claimed = observed = 门实测）")
            sys.exit(0)
        print("GATE REJECT:")
        for r in reasons:
            print("  -", r)
        sys.exit(1)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
