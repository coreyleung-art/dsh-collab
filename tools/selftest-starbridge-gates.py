#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星桥判据门 · 自证矩阵（正例 + 负例）

为什么需要它
    裁判 addendum-3 指出我的层错：
      · 我做的负控问的是「**不用 --check 时它会不会写盘**」—— 那是**手段层**（工程）
      · §11 要的负控问的是「**给一条不合规数据，判据会不会红**」—— 那是**目的层**（验收）
    ⇒ 无本矩阵时，三个判据只**记录**不合规而不**失败** ⇒ 判据等于不会红（半修形态①的变体）。

本矩阵测什么（逐条对应 §11 的「负控（必须能红）」）
    正例 1  三个脚本正常跑 ⇒ **必须 exit 0** 且输出 "✓ 判据通过"
    负例 2  索引 + 不可解指针      ⇒ **必须 exit 4**
    负例 3  索引 + superseded 缺 superseded_by ⇒ **必须非 0**（add() 内断言）
    负例 4  状态机 + closed_with_evidence 三要素不齐 ⇒ **必须 exit 5**

安全
    全部用例走 `--check` + `STARBRIDGE_OUT=/tmp/...` ⇒ **不写任何生产文件**。
    本脚本自身只写 /tmp，并在结束时清理。

用法
    python3 tools/selftest-starbridge-gates.py
    退出码：0 = 全部符合预期；1 = 有不符合
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# 归属说明（2026-10-09）：**方法属审查方（T6），用例属我方自证**。
#   可移交：负例必红的结构、正例/响应性用例的命名纪律；
#   保留理由：其用例绑定我方三条判据（STARBRIDGE_INJECT_BAD），交掉即失去自证手段（R046 要求自证+第三方两者在场）。
#   登记：blackboard:data/registry/audit-tool-handover

COLLAB = Path.home() / "dsh-collab"
IDX = "tools/build-starbridge-index.py"
STA = "tools/build-state-registry.py"
tmpdir = tempfile.mkdtemp(prefix="sb-gates-")

CASES = [
    # (名称, 脚本, 注入值, 期望退出码集合, 期望输出包含, 是否「响应性」用例)
    #
    # ★ 命名修正（采纳裁判 addendum-5 的 🟡 意见）：
    #   原「正例2 状态机(真数据)」期望 rc ∈ {0,5} ⇒ 严格意义上**正例被放宽**。
    #   裁判判语：「真正的正例只有『正例1 rc=0』；『正例2』实为**响应性用例**。」
    #   ⇒ 更名并降级为「响应性用例」：它测的是**判据在响应**（rc 与裁决文本自洽），
    #     而非「数据合规」。数据合规性由单独一行报告，不混进通过/不通过。
    #   注：待 P0 修好 continuity-index（C1/C2/C3/C5 三要素补齐）后，
    #       本用例会自然转为 rc=0 的真正例 —— 届时可再更名回「正例2」。
    ("正例1 索引",            IDX, "",             {0},    "✓ 判据通过",        False),
    ("响应性用例2 状态机(真数据)", STA, "",           {0, 5}, None,               True),
    ("负例1 索引·指针不可解",  IDX, "unresolvable", {4},    "✗ 判据未通过",      False),
    ("负例2 索引·superseded缺字段", IDX, "superseded", None, "superseded 缺 superseded_by", False),
    ("负例3 状态机·三要素不齐", STA, "closure",    {5},    "✗ 判据未通过",      False),
]

results = []
data_findings = []
for name, script, inject, expect_codes, expect_text, is_data_case in CASES:
    env = dict(os.environ)
    env.pop("STARBRIDGE_INJECT_BAD", None)
    if inject:
        env["STARBRIDGE_INJECT_BAD"] = inject
    env["STARBRIDGE_OUT"] = str(Path(tmpdir) / ("out-%s.json" % abs(hash(name))))
    p = subprocess.run([sys.executable, script, "--check"], cwd=str(COLLAB),
                       capture_output=True, text=True, env=env, timeout=120)
    out = (p.stdout or "") + (p.stderr or "")
    rc = p.returncode
    if expect_codes is None:
        ok_rc = rc != 0
        rc_desc = "非 0"
    else:
        ok_rc = rc in expect_codes
        rc_desc = "或".join(str(c) for c in sorted(expect_codes))
    if is_data_case:
        # 测「判据在响应」：rc 与裁决文本必须自洽
        verdict = ("✓ 判据通过" in out) or ("✗ 判据未通过" in out)
        ok_txt = verdict and ((rc == 0) == ("✓ 判据通过" in out))
        if rc == 5:
            for l in out.splitlines():
                if "缺:" in l:
                    data_findings.append(l.strip())
    else:
        ok_txt = expect_text in out
    ok = ok_rc and ok_txt
    results.append((name, ok, rc, rc_desc, ok_txt))
    print("%s %-28s rc=%-3s (期望 %-6s) 裁决文本自洽=%s"
          % ("✅" if ok else "❌", name, rc, rc_desc, "是" if ok_txt else "否"))
    if not ok:
        tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
        for l in tail:
            print("        | %s" % l[:150])

# 清理
for f in Path(tmpdir).glob("*"):
    f.unlink()
os.rmdir(tmpdir)

print()
n_ok = sum(1 for _, ok, *_ in results if ok)
print("自证矩阵：%d/%d 符合预期" % (n_ok, len(results)))
if data_findings:
    print()
    print("★ 另发现**数据合规性问题**（非判据问题，判据正确地红了）：")
    for d in data_findings:
        print("   %s" % d)
    print("   ⇒ 这些项在 continuity-index 记 closed_with_evidence，但按锚点 §11 六者规则**不够格**。")
    print("   ⇒ 修改 continuity-index 须随 P0（升锚点 state_version），本会话不擅动。")
if n_ok == len(results):
    print()
    print("⇒ 三条判据**均能被不合规数据触发**（负控成立，非空转）")
    sys.exit(0)
print("⇒ ✗ 有判据不会红或正例误红 —— 判据不可信")
sys.exit(1)
