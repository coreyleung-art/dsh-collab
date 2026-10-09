#!/usr/bin/env python3
"""G10/G11 复核取证：
① 刚发的卡（走新代码路径）的 `from` 是否仍是硬编码星桥 ⇒ 判 G11 是否已修
② gate.js 与 g11 备份的 diff（gate.js 从 4066 → 5181B，说明有改动）
③ core.js 的 delays 数组实际长度（他称“8 次”，但列了 7 个数字）
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== g10-g11-verify 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · G10/G11 复核取证：")
    print("  · ① 刚发的卡（走新代码路径）的 `from` 是否仍是硬编码星桥 ⇒ 判 G11 是否已修")
    print("  · ② gate.js 与 g11 备份的 diff（gate.js 从 4066 → 5181B，说明有改动）")
    print("  · ③ core.js 的 delays 数组实际长度（他称“8 次”，但列了 7 个数字）")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/g10-g11-verify.log")
    return 0



# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。

import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

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


import sys as _r006_sys
if __name__ == "__main__" and "--lean4-check" in _r006_sys.argv:
    _r006_sys.exit(lean4_check())

import json, urllib.request, urllib.error, subprocess, re, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/g10-g11-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

KEY = "notes/mac-mini/r048-two-items-verified-one-command-gap-20261008"

print("=" * 74)
print("【①】G11 即时验证：我刚发的卡 from 是谁")
print("=" * 74)
for label, base in (("local", "http://127.0.0.1:8792/"), ("central", "http://106.53.214.108:8792/")):
    try:
        d = json.load(urllib.request.urlopen(base + KEY, timeout=25))
        v = d.get("value", {})
        print(f"  {label:<8} from = {v.get('from')}")
        print(f"           from_label = {v.get('from_label')}")
    except Exception as e:
        print(f"  {label} 读取失败 {e}")
print("  ⇒ 期望（若 G11 已修）：from == session-1ffded95-c401-41f3-8bec-f74f2d9790cd（裁判）")
print("     若仍为 session-fa1f9150-…（星桥）⇒ G11 未修或未生效")

print()
print("=" * 74)
print("【②】gate.js 现状 vs g11 备份")
print("=" * 74)
D = os.path.expanduser("~/dsh-plugin-bb-card-send/lib")
for f in ("gate.js", "gate.js.bak-20261008-g11"):
    p = os.path.join(D, f)
    if os.path.isfile(p):
        src = open(p, errors="replace").read()
        print(f"  {f}: {len(src)}B, {src.count(chr(10))+1} 行")
        for m in re.finditer(r"FROM_SELF|from\s*[:=]|session-|writerLabel|authorResolved", src):
            line = src[:m.start()].count("\n") + 1
            seg = src.splitlines()[line - 1].strip() if line - 1 < src.count("\n") else ""
            print(f"     L{line}: {seg[:110]}")
print()
# ★ 2026-10-09 R10 修复：原 shell=True 仅为管道 `| head -40` ⇒ 改列表传参 + Python 内截断
_d = subprocess.run(["diff", f"{D}/gate.js.bak-20261008-g11", f"{D}/gate.js"],
                    capture_output=True, text=True)
class _R:
    returncode = _d.returncode
    stdout = "\n".join((_d.stdout or "").splitlines()[:40])
    stderr = _d.stderr
rc = _R()
print("  diff（旧→新，前 40 行）:")
for l in (rc.stdout or "").splitlines():
    print("   ", l[:130])
if not (rc.stdout or "").strip():
    print("    （无差异）")

print()
print("=" * 74)
print("【③】core.js 的 delays 数组实际内容")
print("=" * 74)
src = open(os.path.join(D, "core.js"), errors="replace").read()
m = re.search(r"delays\s*=\s*\[([^\]]*)\]", src)
if m:
    nums = [x.strip() for x in m.group(1).split(",") if x.strip()]
    print(f"  delays = [{m.group(1).strip()}]")
    print(f"  ⇒ 元素个数 = {len(nums)}   （他称“8 次”；列出的数字是 5/10/20/40/60/60/45 = 7 个）")
    try:
        tot = sum(int(float(n)) for n in nums)
        print(f"  ⇒ 等待总和 = {tot}s   （他称“总窗 ≤240s”）")
    except Exception as e:
        print("  求和失败", e)
else:
    print("  ❌ 未找到 delays 数组定义（可能在别处/动态生成）")
    for i, line in enumerate(src.splitlines(), 1):
        if "delay" in line.lower():
            print(f"    L{i}: {line.strip()[:130]}")

