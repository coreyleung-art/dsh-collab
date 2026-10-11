#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live-role-resolve-harness.py — INC-08 的**现场 harness**（跑用户会走的那条命令，而非自证夹具）。

★ 立据（短判决位 2026-10-10 判决 B 逐字）：
  「INC-08 的 harness 是 `--selftest`（我实跑绿），而**同一文件默认路径 `--role 裁判` 100% 崩溃** ⇒
    **INC-08 PASS 是关于 selftest 的，不是「这工具能用」**；harness 未覆盖事故现场。
    ★ 与 INC-07 **完全同形**（harness 路径 ≠ 实际路径）—— 中间只隔了刚加的「口径≠在役」声明
    ⇒ **「原则不跨门传导」第五次**」
  ★ 通用形态（判决给的）：**入册须断言「harness 走的是用户会走的那条命令」**。

本 harness 就做两件**现场动作**（都是用户会做的）：
  S1 **不带 `--peers`**（默认路径）⇒ 必须**干净报用法错**：exit 非 0 且**输出里不得有 Traceback**（判决 B 那个崩溃点）
  S2 **带 `--peers`**（真实用法）⇒ 必须 exit 0 且判为 `unique_live_candidate`
  ★ 两者都不调用 `--selftest` —— 自证夹具**不能**替代现场。

退出码：0 = 现场两步都达预期 · 1 = 有一步未达 · 2 = 环境错误
用法：python3 tools/live-role-resolve-harness.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.expanduser("~/dsh-collab")
PY = sys.executable or "python3"
TOOL = os.path.join(HERE, "tools/live-role-resolve.py")
USER_CMD = [PY, "tools/live-role-resolve.py", "--role", "裁判"]      # ← 用户会走的那条命令（不带 --peers）
WITH_PEERS = USER_CMD + ["--peers", "<snapshot>"]


def run(args, cwd=HERE):
    r = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    if not os.path.isfile(TOOL):
        print(f"环境错误：找不到 {TOOL}")
        return 2
    # ★ 观测面六要素（含第六项「补偿控制」）
    import datetime as _dt3
    _t = _dt3.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"); _t = _t[:-2] + ":" + _t[-2:]
    print("  观测面（六要素）：**含项** = 本 harness **真正执行**的两条用户命令（S1 默认路径 / S2 带快照）"
          "；**排除项** = ① 不跑 `--selftest`（夹具不替代现场）② 不测**其它**入口/参数组合 "
          "③ 不测在役宿主内的行为（那是宿主面）；"
          "**补偿控制** = ① S1 断「干净失败」（非 0 · **无栈** · 有用法提示）② S2 断「真解析出结论」"
          "③ **反控**：带 `--peers` 时不得报用法错（防「一律报错」的恒红）④ 退出码经 `$?` 直取、**不经管道**；"
          f"**工具** = subprocess（真跑）；**单位** = 条命令；**时刻** = {_t}")
    bad = []

    # ── S1 现场之一：默认路径（不带 --peers）——判据是「干净失败」，不是「不崩就行」 ──
    rc, out = run(USER_CMD)
    has_tb = "Traceback (most recent call last)" in out
    print(f"[S1·正控] 现场命令（默认路径**必须干净失败**）：{' '.join(str(a) for a in USER_CMD)}")
    print(f"     exit={rc} · Traceback={'有（★ 缺陷）' if has_tb else '无（✓）'}")
    if has_tb:
        bad.append("S1 默认路径抛栈（用户看到的是崩溃而非用法提示）")
    if rc == 0:
        bad.append("S1 默认路径居然 exit 0 —— 缺 --peers 时无法判活体，不该算成功")
    if "用法错误" not in out:
        bad.append("S1 默认路径未给出「用法错误」提示（用户无从知道缺什么）")

    # ── S2 现场之二：真实用法（带 --peers 快照）——须真解析出结论 ──
    _work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(_work, exist_ok=True)   # ★ 本目录在沙箱/新机上可能不存在（实测教训）
    sb = tempfile.mkdtemp(prefix="lrr-harness-", dir=_work)
    snap = os.path.join(sb, "peers.json")
    # 快照形态与 `agent_peers` 输出一致；这里用**自造的确定输入**，故判据可复算
    json.dump({"agents": [{"id": "judge-live", "status": "running"}], "self": "me"}, open(snap, "w", encoding="utf-8"))
    prof = os.path.join(sb, "profiles.json")
    json.dump({"profiles": [{"agentId": "ghost-1", "role": "裁判 · 独立审查员"},
                            {"agentId": "judge-live", "role": "裁判 · 独立审查员"}]}, open(prof, "w", encoding="utf-8"))
    cmd2 = [PY, "tools/live-role-resolve.py", "--role", "裁判", "--peers", snap, "--profiles", prof]
    rc2, out2 = run(cmd2)
    print(f"[S2·正控] 真实用法（**必须真解析出结论**）：{' '.join(str(a) for a in cmd2[:4])} …（快照为自造确定输入）")
    print(f"     exit={rc2} · 状态命中={'unique_live_candidate' if 'unique_live_candidate' in out2 else '否（★）'}")
    if rc2 != 0 or "unique_live_candidate" not in out2:
        bad.append(f"S2 真实用法未得到唯一活体候选（exit={rc2}）")
    # ★ 反控：带上 `--peers` 时**不得**再报用法错（该绿必须绿）——与 S1 互补，防"一律报错"的恒红
    rc3, out3 = run([PY, "tools/live-role-resolve.py", "--role", "裁判", "--peers", snap, "--profiles", prof])
    rev_ok = (rc3 == 0) and ("用法错误" not in out3)
    print(f"  {'✅' if rev_ok else '❌'} 【反控】带 `--peers` 时**不得**报用法错（exit={rc3}）")
    if not rev_ok:
        bad.append("反控失败：带快照时仍报用法错（判据可能恒红）")
    try:
        import shutil
        shutil.rmtree(sb, ignore_errors=True)
    except Exception:
        pass

    if bad:
        print("\n❌ 现场 harness 未通过：")
        for b in bad:
            print("  " + b)
        return 1
    print("\n✅ 【正控】现场两步通过：默认路径**干净失败**（非 0 · 无栈 · 有用法提示）· 真实用法**真解析出结论**")
    print("  ★ 本 harness **不跑 --selftest** —— 自证夹具不能替代现场（判决 B 的教训）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
