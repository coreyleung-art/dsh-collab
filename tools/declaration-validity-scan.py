#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨库「声明物是否仍指向有效对象」扫描器 · v1.0

规格:  data/registry/declaration-validity-scanner-spec（v0.1 + §十一实证）
裁定:  data/registry/dvs-spec-ruling-five-adopted-plus-five-amendments
       ①–⑤ 采纳 + 五处增补；⑥ 升格为通用判据
执行方: session-a072636f（用户 2026-10-10 临时授权）
验证方: session-1ffded95（独立复核）

家族不变式：**声明物与实际脱节，且不报错、无症状。**

判定三态（裁定 ②③）
    VALID         被指对象存在，状态与声明一致      —— 且**判据的真值源可显式给出**
    STALE         被指对象不存在 / 状态与声明不符
    UNJUDGEABLE   真值源给不出 ⇒ **必须独立报出**，不得并入 VALID/STALE

退出码契约（裁定 ④：exit 3 必须报在【第一行】）
    0  扫描完成，无 STALE
    2  扫描完成，存在 STALE
    3  判据没跑起来（空集 / 扫描面解析失败）—— ★ 打印在第一行
    4  内部错误

门脚本纪律（裁定 ⑥ · 通用判据）
    凡门脚本里有【预期会失败】的命令，`set -e` 都会跳过其后的断言
    ⇒ 任何门脚本必须先证明【自己的断言跑了】。
    本脚本用两种修法并用：① 断言自报  ③ entered/asserted 成对标记。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

VERSION = "1.0"
GATE = "DVSCAN"

# ── 门①：entered/asserted 成对标记（裁定 ⑥ 修法③）────────────────
_ASSERT = []
_ENTERED = []


_CUR = {"gate": None}


def gate_enter(name):
    """门进入标记（裁定⑥修法③）。★ 与 asserted 成对，且【末行由数据算出】。"""
    _ENTERED.append(name)
    _CUR["gate"] = name
    print(f"  → [entered] {name}")


def gate_assert(name, ok, detail=""):
    """断言自报（修法①）：无论通过与否都打印，使「通过」与「没跑」可区分。"""
    _ASSERT.append((name, ok, detail, _CUR["gate"]))
    mark = "✅" if ok else "❌"
    print(f"  {mark} [asserted] {name}" + (f" — {detail}" if detail else ""))
    return ok


# ── 真值源（裁定 ②：真值源给不出 ⇒ UNJUDGEABLE）──────────────────
def truth_source_exists(path):
    """真值源 = 文件系统存在性。给出即返回 (True, val)，给不出返回 (False, None)。"""
    if not path or not isinstance(path, str):
        return False, None
    p = os.path.expanduser(path)
    if not p.startswith("/"):
        return False, None
    return True, os.path.exists(p)


def truth_source_code_writes(code_files, declared):
    """真值源 = 代码是否真的写到 declared 路径（用于「统一日志」类声明）。

    为何需要（本扫描器发现的关键点）：
        日志文件「不存在」有两种成因，真值源不同 ——
          (a) 工具从没跑过  ⇒ 非缺陷
          (b) 代码根本不写这个路径（声明与实际脱节）⇒ 缺陷
        只看文件存在性会把 (a) 误判为 STALE。故须回到代码这个真值源。
    返回 (True, bool_ok, code_file) 或 (False, None, None)。
    """
    base = os.path.basename(declared)
    for cf in code_files:
        try:
            txt = open(cf, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if base in txt:
            return True, True, cf
    if code_files:
        return True, False, code_files[0]
    return False, None, None


# ── 扫描面 D：工具/插件声明的「统一日志」──────────────────────────
LOG_DECL_RE = re.compile(r'[`"\']((?:~|/Users/[A-Za-z0-9_.-]+)[^`"\'\s]*?/logs/[A-Za-z0-9._-]+\.log)[`"\']')
CODE_EXT = (".py", ".js", ".ts", ".sh")
# 代码级日志声明：容忍单/双引号与路径前缀（★ 双引号专匹配会漏掉单引号声明）
LOG_PATH_LITERAL_RE = re.compile(r'[\"\']((?:~|/Users/[A-Za-z0-9_.-]+)[^\"\'\s]*?\.log)[\"\']')


def find_code_files(start_dir, max_up=3):
    """从声明所在目录向上找到【包根】的代码文件（真值源解析）。

    为何必须向上找（本扫描器 v1.0 首次运行的自证）：
        声明常写在 `docs/README.md`，而代码在包根的 `lib/`。
        只查同目录 ⇒ 真值源给不出 ⇒ 整批落 UNJUDGEABLE。
        v1.0 实测 UNJUDGEABLE 占 87.5% —— 按裁定 ③，这判的是
        【扫描面可检性不足】，不是「库很干净」。本函数即为该修正。
    """
    d = os.path.abspath(start_dir)
    for _ in range(max_up + 1):
        found = []
        for dp, dn, fn in os.walk(d):
            dn[:] = [x for x in dn if x not in ("node_modules", ".git", "__pycache__")]
            found += [os.path.join(dp, f) for f in fn if f.endswith(CODE_EXT)]
            if dp != d and len(found) > 400:
                break
        if found:
            return sorted(found)
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    return []


def scan_surface_d(roots):
    """声明物 = 「统一日志 = P」（R006 ⑦）。真值源 = 包内代码是否写到 P。"""
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "__pycache__")]
            docs = [f for f in filenames if f.endswith(".md")]
            codes = find_code_files(dirpath) if docs else []
            for d in docs:
                fp = os.path.join(dirpath, d)
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for m in LOG_DECL_RE.finditer(txt):
                    declared = m.group(1)
                    have_code, writes, codefile = truth_source_code_writes(codes, declared)
                    # ★ 判据优先级（v1.0 首次运行自证修正）：
                    #   存在性 = 直接证据，必须先看。先前把「代码引用」置于其上，
                    #   导致 【文件明明存在】却被判 STALE（实测误报 3 条：
                    #   gate-canfail / bus-queue-triage / silent-truncation-lint）。
                    has, exists = truth_source_exists(declared)
                    if not has:
                        state, reason = "UNJUDGEABLE", "路径不可解析为绝对路径"
                    elif exists:
                        state, reason = "VALID", "文件已在（存在性即直接证据）"
                    elif not have_code:
                        state, reason = "UNJUDGEABLE", "文件未生成且包内无代码可判真值源"
                    elif writes:
                        state, reason = "VALID", "代码写到该路径（文件未生成：工具未跑过，非缺陷）"
                    else:
                        state, reason = "STALE", "代码未引用该路径且文件不存在（声明与实际脱节）"
                    out.append({
                        "surface": "D",
                        "declared": declared,
                        "source_file": fp,
                        "truth_source": codefile or "(无)",
                        "state": state,
                        "reason": reason,
                    })

            # ★ v1.0 修订：面 D 必须【同时】覆盖【代码内声明】。
            #   缘起：v1 首版只读 .md ⇒ 对代码级声明结构性失明；而裁决方实测
            #   命中率最高的一批（9 工具中 5 个声明了不存在的日志）**正是代码级**。
            #   ⇒ 漏这一半，扫描器会把 5 条真命中读成 0 条，且输出上看不出来。
            for cf in codes:
                try:
                    ctxt = open(cf, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for m in LOG_PATH_LITERAL_RE.finditer(ctxt):
                    declared = m.group(1)
                    has, exists = truth_source_exists(declared)
                    if not has:
                        state, reason = "UNJUDGEABLE", "路径不可解析为绝对路径"
                    elif exists:
                        state, reason = "VALID", "文件已在（存在性即直接证据）"
                    else:
                        state, reason = "STALE", "代码声明的日志文件不存在"
                    out.append({
                        "surface": "D",
                        "declared": declared,
                        "source_file": cf,
                        "truth_source": cf,
                        "state": state,
                        "reason": reason,
                    })
    return out


# ── 扫描面 B：索引表里的 SOURCE_AVAILABLE: yes ────────────────────
IDX_ROW_RE = re.compile(r'\|\s*`([^`]+)`\s*\|[^|]*\|\s*\**\s*(yes|no)\s*\**\s*\|(.*)')
SRC_PATH_RE = re.compile(r'`((?:~|/)[^`\s]+)`')


def scan_surface_b(roots):
    """声明物 = 索引表行 SOURCE_AVAILABLE=yes。真值源 = 该行写明的源路径。"""
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
            for f in filenames:
                if not f.endswith(".md"):
                    continue
                fp = os.path.join(dirpath, f)
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for line in txt.splitlines():
                    m = IDX_ROW_RE.search(line)
                    if not m:
                        continue
                    name, avail, rest = m.group(1), m.group(2), m.group(3)
                    if avail.lower() != "yes":
                        continue
                    srcs = [s for s in SRC_PATH_RE.findall(rest) if "/logs/" in s or "/tmp/" in s or "/" in s]
                    if not srcs:
                        out.append({"surface": "B", "declared": name, "source_file": fp,
                                    "truth_source": "(未写明源)", "state": "STALE",
                                    "reason": "标 yes 却指不出源（形态④）"})
                        continue
                    for s in srcs:
                        has, exists = truth_source_exists(s)
                        if not has:
                            state, reason = "UNJUDGEABLE", "源路径不可解析"
                        elif exists:
                            state, reason = "VALID", f"源在位 {s}"
                        else:
                            state, reason = "STALE", f"源不存在 {s}"
                        out.append({"surface": "B", "declared": name, "source_file": fp,
                                    "truth_source": s, "state": state, "reason": reason})
    return out


def main():
    ap = argparse.ArgumentParser(description="跨库声明物有效性扫描（只读 · 三态）")
    ap.add_argument("--root", action="append", default=None,
                    help="扫描根（可多次）；默认 dsh-collab/devices + dsh-collab/docs + dsh-collab/tools")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--selfcheck", action="store_true", help="运行自身四道门并退出")
    args = ap.parse_args()

    home = os.path.expanduser("~")
    roots = args.root or [
        os.path.join(home, "dsh-collab", "devices"),
        os.path.join(home, "dsh-collab", "docs"),
        os.path.join(home, "dsh-collab", "tools"),
        # ★ v1.0 修订：补 scripts/ —— 默认根曾漏掉它，而裁决方实测命中率最高的一批
        #   （9 工具中 5 个声明了不存在的日志）**全部位于此目录**。
        #   漏根 ⇒ 扫描器对最高价值的面【结构性失明】，且输出上看不出来。
        os.path.join(home, "dsh-collab", "scripts"),
    ]

    t0 = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    if args.selfcheck:
        return selfcheck(roots)

    items = scan_surface_d(roots) + scan_surface_b(roots)

    # ── 门① 空集守卫：0 条 ⇒ 判据没跑起来（★ 第一行，裁定 ④）──
    if not items:
        print("❌ 判据没跑起来（DVSCAN-EMPTY）：扫描面解析出 0 条声明物。")
        print("   ★ 空输入不是「全部合规」，是【判据没跑起来】。拒绝输出通过。")
        print(f"   范围: {len(roots)} 个根 · 时刻: {t0}")
        return 3

    n = {"VALID": 0, "STALE": 0, "UNJUDGEABLE": 0}
    for it in items:
        n[it["state"]] = n.get(it["state"], 0) + 1
    total = len(items)
    unj_pct = n["UNJUDGEABLE"] / total * 100.0

    if args.json:
        print(json.dumps({
            "version": VERSION, "scanned_at": t0, "roots": roots,
            "range": {"declarations_total": total, "by_surface": {
                s: sum(1 for i in items if i["surface"] == s) for s in ("A", "B", "C", "D")}},
            "unit": "一条声明物（指向 + 断言 + 可检 · 真值源可显式给出）",
            "counts": n, "unjugeable_pct": round(unj_pct, 1),
            "items": items}, ensure_ascii=False, indent=1))
    else:
        print("=" * 74)
        print(f"声明物有效性扫描 v{VERSION}（只读 · 三态）")
        print(f"时刻: {t0}")
        print(f"范围: 声明物 {total} 条 · 面 A/B/C/D 分别 "
              f"{sum(1 for i in items if i['surface']=='D')}/"
              f"{sum(1 for i in items if i['surface']=='B')}/0/0 · 根 {len(roots)} 个")
        print(f"单位: 一条声明物（指向 + 断言 + 可检 · 真值源可显式给出）")
        print("=" * 74)
        for st in ("STALE", "UNJUDGEABLE", "VALID"):
            sel = [i for i in items if i["state"] == st]
            if not sel:
                continue
            icon = {"STALE": "❌", "UNJUDGEABLE": "⚠️", "VALID": "✅"}[st]
            print(f"\n{icon} {st} × {len(sel)}")
            for i in sel[:12]:
                print(f"   [{i['surface']}] {i['declared']}")
                print(f"        {i['reason']}")
                print(f"        声明于 {i['source_file'].replace(home, '~')}")
            if len(sel) > 12:
                print(f"   … 另有 {len(sel)-12} 条")
        print("-" * 74)
        print(f"合计: VALID {n['VALID']} · STALE {n['STALE']} · UNJUDGEABLE {n['UNJUDGEABLE']}"
              f"（{unj_pct:.1f}%）")
        if unj_pct >= 90:
            print("★ UNJUDGEABLE ≥90% ⇒ 【扫描面可检性不足】，不是「库很干净」（裁定 ③）。")

    if n["STALE"] > 0:
        return 2
    return 0


def selfcheck(roots):
    """自身四道门（裁定 ⑤：必须）。只读：全程不修改被扫对象。"""
    print(f"=== {GATE} --selfcheck（四道门）===")
    ok = True
    # 门③ 基线先绿
    gate_enter("gate3-baseline")
    items = scan_surface_d(roots) + scan_surface_b(roots)
    ok &= gate_assert("基线：真库解析出 >0 条声明物", len(items) > 0, f"n={len(items)}")

    # 门④ 零接触：跑前跑后整树 sha
    def tree_sha(paths):
        h = hashlib.sha256()
        for r in paths:
            for dp, dn, fn in os.walk(r):
                dn[:] = [d for d in dn if d not in ("node_modules", ".git")]
                for f in sorted(fn):
                    fp = os.path.join(dp, f)
                    try:
                        h.update(fp.encode())
                        h.update(str(os.path.getsize(fp)).encode())
                    except Exception:
                        pass
        return h.hexdigest()

    gate_enter("gate4-zero-touch")
    before = tree_sha(roots)
    scan_surface_d(roots); scan_surface_b(roots)
    after = tree_sha(roots)
    ok &= gate_assert("门④ 零接触：整树 sha 前后一致", before == after,
                      f"{before[:16]}…=={after[:16]}…")

    # 门② 反向对照（在副本上；本处只验证真值源判据是否可失败）
    gate_enter("gate2-negative-control")
    ok &= gate_assert("门② 反向对照：不存在的源被判 STALE",
                      truth_source_exists("/definitely/not/here.log") == (True, False))
    ok &= gate_assert("门② 反向对照：不可解析路径被判 UNJUDGEABLE",
                      truth_source_exists("relative.log")[0] is False)

    # 门① 空集守卫：0 条 ⇒ 必须非零退出
    gate_enter("gate1-empty-guard")
    ok &= gate_assert("门① 空集守卫：空输入走非零分支", _empty_returns_nonzero())

    ne, na = len(_ENTERED), len(_ASSERT)
    npass = sum(1 for a in _ASSERT if a[1])
    # ★ 配对语义：每个 entered 门至少有一条 asserted；且不存在【无主断言】
    #   （原按 1:1 计数会把「一门多断言」误判为不配对——实测 entered=4/asserted=5 时误报）
    orphans = sum(1 for a in _ASSERT if a[3] is None)
    silent = [g for g in _ENTERED if not any(a[3] == g for a in _ASSERT)]
    paired = (orphans == 0 and not silent)
    line = (f"entered={ne} asserted={na} paired={'true' if paired else 'false'} "
            f"pass={npass}/{na} orphans={orphans} silent_gates={len(silent)}")
    if not paired:
        # ★ 修法第三条：缺 asserted 时【拒绝】报「成对」——把自称降级为需条件
        print(f"\n❌ assertion-pairing 不成立：{line} ⇒ 拒绝报「成对」")
        return 4
    print(f"\n=== {GATE} --selfcheck {line} ===")
    return 0 if ok else 4


def _empty_returns_nonzero():
    """用空根跑一次，断言返回 3（判据没跑起来）。"""
    empty = "/tmp/__dvscan_empty__"
    os.makedirs(empty, exist_ok=True)
    old = sys.argv
    try:
        sys.argv = ["x", "--root", empty]
        return _run_main_silent() == 3
    finally:
        sys.argv = old


def _run_main_silent():
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main()
    first = buf.getvalue().splitlines()[0] if buf.getvalue() else ""
    # 裁定 ④：exit 3 必须报在第一行
    if rc == 3 and not first.startswith("❌ 判据没跑起来"):
        return -1
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ DVSCAN-INTERNAL: {e}")
        sys.exit(4)
