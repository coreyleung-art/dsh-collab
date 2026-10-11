#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
acceptance-gate.py — 验收门（版本单一来源 GATE_VERSION，--tool-version 查询）（老板 2026-10-04 22:5x：自审无效、第三方必须在场）
运行面镜像；谓词与 rules-registry/lean4/acceptance-gate.lean 1:1：
  valid(c) := adjudicator ∉ {proposer, executor} ∧ surfaceDeclared ∧ surfaceMeasured ∧ 证据在场且全部可解
v1.1（MBP 负控复现后）：证据引用必须**可解**——board:<key> 双板 HTTP 200（G37 逐板）；
  board-local:/board-central: 单板 200；file:/log:/marker:<path> 文件存在（可选 ::contains:<子串>）。
  任何一条不可解 ⇒ 拒（列明哪条失败）。拒绝「凭空证据」（负控 #5/#6）。
v1.1.4（2026-10-06 PSTD v5 教训「范围必须由实测划定、不能由假设划定」正式化，用户点头）：
  新增 surfaceMeasured 判据——裁定面必须附实测边界：
    · surface_measured：非空且全部可解的引用列表（条目级实测清单/复现证据）
    · surface_unmeasured：字段必须在场（可为空数组）——显式声明「没有未测项」；
      字段缺失 = 边界由假设划定 = 拒（负控 #8/#9/#10）
用法：
  acceptance-gate.py --check <claim.json>   # 校验一张验收声明（exit 0=过门 / 1=拒 / 2=用法错）
  acceptance-gate.py --selftest             # 正/负样本自测（门必须有判别力，防假绿）
  acceptance-gate.py --lean4-check          # 谓词与 Lean4 规范的对应性检查
  acceptance-gate.py --tool-version         # 机器可读版本（GATE_VERSION 单一来源）
环境：BB_LOCAL（默认 http://127.0.0.1:8792）、BB_CENTRAL（默认 http://xingqiao.meetfunbp.com:8792）
"""
import json, os, sys, urllib.request

GATE_VERSION = "1.1.4"
LEAN4_SPEC = "rules-registry/lean4/acceptance-gate.lean"
BB_LOCAL = os.environ.get("BB_LOCAL", "http://127.0.0.1:8792")
BB_CENTRAL = os.environ.get("BB_CENTRAL", "http://xingqiao.meetfunbp.com:8792")


def third_party_present(c):
    return c.get("adjudicator") and c["adjudicator"] not in (c.get("proposer"), c.get("executor"))


def surface_declared(c):
    s = c.get("surface", "")
    return isinstance(s, str) and len(s.strip()) > 0


def surface_measured(c):
    """v1.1.4：裁定面必须由实测划定——surface_measured 非空且全部可解，surface_unmeasured 字段必须在场。"""
    measured = c.get("surface_measured")
    if not measured or not isinstance(measured, (list, str)):
        return False, ["surface_measured 必须为非空引用列表（条目级实测清单/复现证据，格式同 evidence_refs）"]
    if isinstance(measured, str):
        measured = [measured]
    if "surface_unmeasured" not in c:
        return False, ["surface_unmeasured 字段必须在场（可为空数组）：缺字段 = 未测边界由假设划定"]
    failed = []
    for ref in measured:
        ok, detail = _resolve_one(ref)
        if not ok:
            failed.append(detail)
    if failed:
        return False, ["surface_measured 引用不可解: " + f for f in failed]
    return True, []


def evidence_present(c):
    # v1.1.1（裁判 preset 首审发现）：只认 evidence_refs（可解引用）。
    # 内联 evidence 自由文本不构成可解证据——只写内联曾让门 PASS 且打印「证据在场且全部可解」假话。
    refs = c.get("evidence_refs")
    return bool(refs) and isinstance(refs, (list, str))


def _board_get(url, key):
    try:
        with urllib.request.urlopen(url + "/" + key, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def _resolve_one(ref):
    """单条证据引用解析：返回 (ok, detail)。不可解/格式未知 = fail-closed。"""
    if not isinstance(ref, str) or not ref.strip():
        return False, "空引用"
    contains = None
    if "::contains:" in ref:
        ref, contains = ref.split("::contains:", 1)
    if ref.startswith("board:"):
        key = ref[len("board:"):].strip()
        if not key:
            return False, "board: 缺键名"
        ok_l = _board_get(BB_LOCAL, key)
        ok_c = _board_get(BB_CENTRAL, key)
        if ok_l and ok_c:
            return True, f"board 双板 200: {key}"
        return False, f"board 双板 200 失败: {key}（local={ok_l}, central={ok_c}）"
    if ref.startswith("board-local:"):
        key = ref[len("board-local:"):].strip()
        ok = _board_get(BB_LOCAL, key)
        return (ok, f"board-local 200: {key}") if ok else (False, f"board-local 404/失败: {key}")
    if ref.startswith("board-central:"):
        key = ref[len("board-central:"):].strip()
        ok = _board_get(BB_CENTRAL, key)
        return (ok, f"board-central 200: {key}") if ok else (False, f"board-central 404/失败: {key}")
    if ref.startswith(("file:", "log:", "marker:")):
        path = ref.split(":", 1)[1].strip()
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return False, f"文件不存在: {path}"
        if contains is not None and contains == "":
            return False, f"contains: 空 needle 是空断言（声明体错，exit 1 属预期）: {path}"
        if contains is not None:
            try:
                data = open(path, encoding="utf-8", errors="ignore").read(200000)
            except Exception:
                return False, f"文件不可读: {path}"
            if contains not in data:
                return False, f"文件不含指定行: {path} ::contains:{contains}"
        return True, f"文件存在: {path}"
    return False, f"未知引用格式（须 board:/board-local:/board-central:/file:/log:/marker: 前缀）: {ref[:60]}"


def valid(c):
    """valid(c) := 第三方在场 ∧ 声明裁定面 ∧ 裁定面由实测划定 ∧ 证据在场且全部可解"""
    if not (third_party_present(c) and surface_declared(c) and evidence_present(c)):
        return False, []
    ok_m, failed_m = surface_measured(c)
    if not ok_m:
        return False, failed_m
    refs = c.get("evidence_refs") or []
    if isinstance(refs, str):
        refs = [refs]
    failed = []
    for ref in refs:
        ok, detail = _resolve_one(ref)
        if not ok:
            failed.append(detail)
    return (not failed), failed


def check(claim):
    reasons = []
    if not third_party_present(claim):
        reasons.append("adjudicator 必须是第三方（≠ proposer 且 ≠ executor）")
    if not surface_declared(claim):
        reasons.append("必须显式声明裁定面 surface（只审了 X 面）")
    if not evidence_present(claim):
        reasons.append("必须附可解 evidence_refs（board:/file: 等）")
    if reasons:
        return False, reasons
    ok_m, reasons_m = surface_measured(claim)
    if not ok_m:
        return False, reasons_m
    ok, failed = valid(claim)
    if not ok:
        reasons = ["证据引用不可解: " + f for f in failed]
    return ok, reasons


def selftest():
    _m = ["file:" + os.path.abspath(__file__)]
    pos = {"proposer": "i9", "executor": "i9", "adjudicator": "xq",
           "surface": "板上可见面",
           "surface_measured": _m,
           "surface_unmeasured": [],
           "evidence_refs": ["file:" + os.path.abspath(__file__)],
           "verdict": "pass"}
    negs = [
        ({"proposer": "i9", "executor": "i9", "adjudicator": "i9", "surface": "全量",
          "surface_measured": _m, "surface_unmeasured": [], "evidence_refs": ["file:/tmp/x"]},
         "负1：提出=裁定（自审）必须拒"),
        ({"proposer": "i9", "executor": "xq", "adjudicator": "xq", "surface": "全量",
          "surface_measured": _m, "surface_unmeasured": [], "evidence_refs": ["file:/tmp/x"]},
         "负2：执行=裁定必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "",
          "surface_measured": _m, "surface_unmeasured": [], "evidence_refs": ["file:/tmp/x"]},
         "负3：未声明裁定面必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "板上可见面",
          "surface_measured": _m, "surface_unmeasured": []},
         "负4：无原始证据必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "板上可见面",
          "surface_measured": _m, "surface_unmeasured": [],
          "evidence": "只写内联不写 evidence_refs"}, "负7：仅内联 evidence 无 evidence_refs 必须拒（裁判首审旁路）"),
        ({"proposer": "mbp", "executor": "mbp", "adjudicator": "xq", "surface": "换代+结票双板可读",
          "surface_measured": _m, "surface_unmeasured": [],
          "evidence_refs": ["board:notes/mac-mini/restart-closed-rn-test-xq-1791093027"]},
         "负5：证据引用不可解（伪造 board 键 404）必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "本地文件",
          "surface_measured": _m, "surface_unmeasured": [],
          "evidence_refs": ["file:/tmp/acceptance-gate-nonexistent-xyz"]},
         "负6：文件证据不存在必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "全量",
          "surface_unmeasured": [], "evidence_refs": _m},
         "负8：无 surface_measured 必须拒（v1.1.4 面由实测划定）"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "全量",
          "surface_measured": ["board:notes/__nonexistent-surface-measured-xyz__"],
          "surface_unmeasured": [], "evidence_refs": _m},
         "负9：surface_measured 引用不可解必须拒"),
        ({"proposer": "i9", "executor": "i9", "adjudicator": "xq", "surface": "全量",
          "surface_measured": _m, "evidence_refs": _m},
         "负10：缺 surface_unmeasured 字段必须拒（未测边界不得由假设划定）"),
    ]
    fails = 0
    ok, _ = check(pos)
    print("正样本（三方分明+声明面+面由实测划定+可解证据）:", "✅ 通过" if ok else "❌ 误拒（门坏了）")
    if not ok: fails += 1
    for i, (c, label) in enumerate(negs, 1):
        ok, reasons = check(c)
        mark = "✅ 已拒" if not ok else "❌ 误放行"
        print(f"{label}:", mark, ("| " + ";".join(reasons[:2])) if not ok else "")
        if ok: fails += 1
    print(f"selftest: {'0 FAIL' if fails == 0 else str(fails) + ' FAIL'}（1 正 10 负）")
    return fails


def lean4_parity():
    print("Lean4 镜像声明（门版本 v" + GATE_VERSION + "）：")
    print("  Lean4:  valid(c) := thirdPartyPresent(c) ∧ c.surfaceDeclared = true ∧ c.surfaceMeasured = true")
    print("  本门:   valid(c) := third_party_present(c) ∧ surface_declared(c) ∧ surface_measured(c) ∧ 证据在场且全部可解")
    print("  注：surfaceMeasured（v1.1.4）= 面由实测划定：surface_measured 非空且可解 ∧ surface_unmeasured 字段在场。")
    print("  规范源:", LEAN4_SPEC, "（lean 可用时以 lean 编译为准）")
    return 0


def main():
    args = sys.argv[1:]
    if "--tool-version" in args:
        print(GATE_VERSION); sys.exit(0)
    if "--selftest" in args:
        sys.exit(1 if selftest() else 0)
    if "--lean4-check" in args:
        sys.exit(lean4_parity())
    if "--check" in args:
        i = args.index("--check")
        if i + 1 >= len(args):
            print("用法: acceptance-gate.py --check <claim.json>"); sys.exit(2)
        with open(args[i + 1], encoding="utf-8") as f:
            claim = json.load(f)
        ok, reasons = check(claim)
        if ok:
            print("GATE PASS: 第三方在场 ∧ 已声明裁定面 ∧ 裁定面由实测划定 ∧ 证据在场且全部可解")
            sys.exit(0)
        print("GATE REJECT:")
        for r in reasons: print("  -", r)
        sys.exit(1)
    print(__doc__); sys.exit(2)


if __name__ == "__main__":
    main()
