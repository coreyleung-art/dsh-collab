#!/usr/bin/env python3
"""核正两个数字（对方量到 3 件 / 78 个，我报 ≥5 件 / 117 个）
① 分离统计：含【裁判 id】的文件数 vs 含【任一归属标记】的文件数（我上一条把后者说成了前者）
② 逐件打印首行，判定"首行证据"到底几件（我把「内容证据」说成了「首行证据」）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== tmp-counts-and-firstline-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 核正两个数字（对方量到 3 件 / 78 个，我报 ≥5 件 / 117 个）")
    print("  · ① 分离统计：含【裁判 id】的文件数 vs 含【任一归属标记】的文件数（我上一条把后者说成了前者）")
    print("  · ② 逐件打印首行，判定'首行证据'到底几件（我把「内容证据」说成了「首行证据」）")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/tmp-counts-and-firstline-check.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/tmp-counts-and-firstline-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

ME = "session-1ffded95"
AUTHOR = "session-b250bf9d"
XQ = "session-fa1f9150"
REVIEWER = "session-4d0e75cf"
EXTS = {".sh", ".py", ".json", ".jsonl", ".txt", ".md", ".out", ".rc", ".log", ".err", ".yml", ".yaml", ".mjs"}

names = [n for n in sorted(os.listdir("/tmp")) if os.path.isfile(os.path.join("/tmp", n))]
print(f"/tmp 顶层文件总数 = {len(names)}")

n_me = n_any = n_scan = 0
me_list = []
for n in names:
    if os.path.splitext(n)[1].lower() not in EXTS:
        continue
    p = os.path.join("/tmp", n)
    try:
        if os.path.getsize(p) > 2 * 1024 * 1024:
            continue
        txt = open(p, "rb").read().decode("utf-8", "replace")
    except Exception:
        continue
    n_scan += 1
    has_me = ME in txt
    has_any = has_me or (AUTHOR in txt) or (XQ in txt) or (REVIEWER in txt)
    if has_me:
        n_me += 1
        me_list.append(n)
    if has_any:
        n_any += 1

print(f"扫描（文本类、<2MB） = {n_scan}")
print(f"★ 含【裁判 session id】的文件 = {n_me}   ← 我上一条应报这个数")
print(f"★ 含【任一归属标记】的文件 = {n_any}   ← 我上一条误报成了「含裁判 id」")
print(f"  差 = {n_any - n_me}（差值来自只含他人 id 的文件）")
print("\n含裁判 id 的文件（前 25）:")
for n in me_list[:25]:
    print("   ", n)

print()
print("=" * 74)
print("【②】作者所列 12 件的【首行】逐件判定（首行证据到底几件）")
print("=" * 74)
NAMES = [
    "bb-audit.json", "channel-audit.log",
    "board-poll-notes_mac-mini_audit-verdict-index-20261008.jsonl",
    "ar_audit.sh", "ar_probe2.sh", "channel-audit.err",
    "channel-gate-weekly.log", "channel-gate-weekly.err.log",
    "audit-corey-i9-mechanism-crossconfirm-20261008.json",
    "audit-bbcard-false-red-rootcaused-20261008.json",
    "audit-probe-hit-and-claims-reconcile-20261008.json",
    "audit-g11-from-attribution-live-probe-20261008.json",
]
first_line_hits = 0
for n in NAMES:
    p = os.path.join("/tmp", n)
    if not os.path.isfile(p):
        print(f"  ❌ 不存在 {n}")
        continue
    try:
        first = open(p, "rb").read(300).decode("utf-8", "replace").splitlines()[0]
    except Exception:
        first = "<读取失败>"
    # 首行是否指名工具/领域
    named = bool(re.search(r"channel|R048|自动提醒器|auto-reminder|genebank|Traceback", first))
    if named:
        first_line_hits += 1
    print(f"  {'★首行点名' if named else '  首行无名'}  {n}")
    print(f"        {first[:120]}")
print(f"\n⇒ **首行**可判定归属的件数 = {first_line_hits}")
print("   我上一条说「至少 5 件」，那是把【内容证据】当成了【首行证据】")
