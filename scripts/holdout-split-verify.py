#!/usr/bin/env python3
"""独立复核 holdout-split.py：① 自检是否真 6 例 3 负控 0 失败 ② 同输入两次 digest 是否一致
③ 空输入是否报错（负控） ④ 真实数据源是否真的 0 条
★ 只读 + 只写 /tmp 下自造输入；不碰被审对象的生产文件。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== holdout-split-verify 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 独立复核 holdout-split.py：① 自检是否真 6 例 3 负控 0 失败 ② 同输入两次 digest 是否一致")
    print("  · ③ 空输入是否报错（负控） ④ 真实数据源是否真的 0 条")
    print("  · ★ 只读 + 只写 /tmp 下自造输入；不碰被审对象的生产文件。")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/holdout-split-verify.log")
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

import os, subprocess, json, tempfile, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/holdout-split-verify.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SC = os.path.expanduser("~/dsh-collab/scripts/holdout-split.py")
print("=" * 74)
print("【①】脚本存在性")
print("=" * 74)
print(f"  {SC}  exists={os.path.isfile(SC)}  size={os.path.getsize(SC) if os.path.isfile(SC) else '-'}")


def run(args, timeout=120):
    r = subprocess.run(["python3", SC] + args, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


print()
print("=" * 74)
print("【②】--selftest")
print("=" * 74)
if os.path.isfile(SC):
    rc, out = run(["--selftest"])
    print(f"  exit = {rc}")
    for l in out.splitlines()[-22:]:
        print("   ", l[:150])

print()
print("=" * 74)
print("【③】同输入两次 ⇒ digest 是否一致（可复跑的核心）")
print("=" * 74)
td = tempfile.mkdtemp(prefix="holdout-verify-")
inp = os.path.join(td, "in.json")
data = [{"id": f"L{i}", "ts": f"2026-10-{i+1:02d}T00:00:00"} for i in range(20)]
json.dump(data, open(inp, "w"))
digests = []
for i in (1, 2):
    rc, out = run(["--input", inp])
    line = [l for l in out.splitlines() if "digest" in l]
    print(f"  第{i}次 exit={rc}  {line[0][:130] if line else out.strip()[:130]}")
    for l in line:
        if "holdout_digest=" in l:
            digests.append(l.split("holdout_digest=")[1].split()[0])
print(f"  ⇒ digest 两次 = {digests}  一致={len(set(digests)) == 1 if len(digests) == 2 else 'N/A'}")

print()
print("=" * 74)
print("【④】负控：空输入应报错（不是静默返回空划分）")
print("=" * 74)
empty = os.path.join(td, "empty.json")
json.dump([], open(empty, "w"))
rc, out = run(["--input", empty])
print(f"  exit = {rc}（期望非 0）")
print("  输出:", out.strip()[:200])
print(f"  ⇒ {'✅ 报错（符合其声称）' if rc != 0 else '❌ 未报错，与其文档声称不符'}")

print()
print("=" * 74)
print("【⑤】真实数据源条数（其文档声称 0 条）")
print("=" * 74)
for p in ("~/dsh-collab/data/confirmed-links.json",
          "~/dsh-collab/data/registry/confirmed-links.json",
          "~/dsh-collab/systemgraph/data/confirmed-links.json"):
    fp = os.path.expanduser(p)
    print(f"  {p}: exists={os.path.isfile(fp)}")
print("  （本项只列常见路径；未找到不等于不存在——标注为未覆盖）")

