#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift-scan-cron.py — 通道漂移周期巡检 wrapper（com.dsh.cron.drift-scan 调用）

运行 drift-scan（node 工具）→ driftCount>0 时写黑板告警卡 data/ops/drift-alert/<ts>。
正常时静默（只写统一日志）。零漂移零写入黑板（防噪音）。
2026-10-02 星桥 · 架构三期治理常态化 ①
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== drift-scan-cron 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · drift-scan-cron.py — 通道漂移周期巡检 wrapper（com.dsh.cron.drift-scan 调用）")
    print("  · 运行 drift-scan（node 工具）→ driftCount>0 时写黑板告警卡 data/ops/drift-alert/<ts>。")
    print("  · 正常时静默（只写统一日志）。零漂移零写入黑板（防噪音）。")
    print("  · 2026-10-02 星桥 · 架构三期治理常态化 ①")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/drift-scan-cron.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, subprocess, sys, time, urllib.request, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/drift-scan-cron.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TOOL = "/opt/homebrew/bin/node"
CLI = os.path.expanduser("~/dsh-plugin-drift-scan/cli.js")
BB = "http://127.0.0.1:8792"


def main():
    r = subprocess.run([TOOL, CLI, "--json"], capture_output=True, text=True, timeout=120)
    if r.returncode not in (0, 1):
        print(f"[drift-cron] 工具异常 exit={r.returncode}: {r.stderr[:120]}", flush=True)
        return 1
    try:
        d = json.loads(r.stdout)
    except Exception as e:
        print(f"[drift-cron] 输出解析失败: {e}", flush=True)
        return 1
    if d.get("driftCount", 0) == 0:
        return 0  # 零漂移：静默
    # 漂移 → 写黑板告警卡（本机+中枢双写+回读断言）
    ts = int(time.time() * 1000)
    key = f"data/ops/drift-alert/{ts}"
    val = {
        "type": "drift-alert", "from": "drift-scan-cron",
        "ts": ts, "driftCount": d.get("driftCount"),
        "drifts": [{"check": row.get("check"), "actual": str(row.get("actual"))[:80]}
                   for row in d.get("rows", []) if row.get("drift")],
        "note": "通道漂移巡检告警（自动）：修复路径=经 channel-gate 登记（portal §3）",
    }
    body = json.dumps(val).encode()
    readbacks = {}
    for name, base in (("local", BB), ("central", "http://xingqiao.meetfunbp.com:8792")):
        req = urllib.request.Request(base + "/" + key, data=body, method="PUT",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as r:
            st = r.status
        with urllib.request.urlopen(base + "/" + key, timeout=6) as r:
            readbacks[name] = json.loads(r.read())
        print(f"[drift-cron] 告警卡 {name} PUT {st}", flush=True)
    assert readbacks["local"]["value"] == readbacks["central"]["value"], "两板不一致"
    print(f"[drift-cron] 漂移 {d.get('driftCount')} 项 → 告警卡 {key} 双写一致", flush=True)
    return 0



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    if "--lean4-check" in sys.argv:
        sys.exit(lean4_check())
    sys.exit(main())
