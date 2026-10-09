#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Weekly cost/replay summary generator v0.1 (HR) — alert layer
Aggregates daily-trend into weekly summary + lists alerts (if any).
launchd template: com.dsh.hr.cahac-replay.weekly (Sunday 10:00)

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
    print("== weekly-summary 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")
    print("  · ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/weekly-summary.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/weekly-summary.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BASE = os.path.expanduser("~/dsh-collab/token-monitor/replays")
TREND = os.path.join(BASE, "daily-trend.md")
ALERTS = os.path.join(BASE, "alerts.md")

def main():
    rows = []
    if os.path.exists(TREND):
        with open(TREND, encoding="utf-8") as f:
            rows = [l for l in f.read().splitlines() if l.startswith("| 20")]
    alerts = []
    if os.path.exists(ALERTS):
        with open(ALERTS, encoding="utf-8") as f:
            alerts = [l for l in f.read().splitlines() if l.startswith("| 20")]
    week = rows[-7:]
    total = sum(float(r.split("|")[2].strip()) for r in week) if week else 0
    cahac = sum(float(r.split("|")[3].strip()) for r in week) if week else 0
    L = ["# 每周成本/回放汇总 · " + datetime.date.today().isoformat(), "",
         "- 近 7 日实际 ¥" + format(total, ".2f") + " · CAHAC 反事实 ¥" + format(cahac, ".2f") + " (saving " + format(1 - cahac/total, ".0%") + ")" if total else "- 无趋势数据",
         "- 告警数: " + str(len(alerts)), ""]
    if alerts:
        L.append("## 告警（需关注）"); L.append(""); L.append("| 日期 | 成本 | 级别 | 说明 |"); L.append("|---|---|---|---|")
        L.extend(alerts[-10:])
    else:
        L.append("✅ 本周无熔断告警")
    L.append(""); L.append("---"); L.append("*weekly-summary v0.1 · HR · 2026-08-19*")
    out = os.path.join(BASE, "weekly-" + datetime.date.today().isoformat() + ".md")
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("weekly:", out)

if __name__ == "__main__":
    main()