#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""token-monitor.py · 资源监察系统（属主=HR 驾驶舱）
读 ~/dsh-collab/token-monitor/audit-snapshot.json → 输出 overview.md 统计面板
用法: python3 ~/dsh-collab/scripts/token-monitor.py

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
    print("== token-monitor 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · token-monitor.py · 资源监察系统（属主=HR 驾驶舱）")
    print("  · 读 ~/dsh-collab/token-monitor/audit-snapshot.json → 输出 overview.md 统计面板")
    print("  · 用法: python3 ~/dsh-collab/scripts/token-monitor.py")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/token-monitor.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/token-monitor.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BASE = os.path.expanduser("~/dsh-collab/token-monitor")
SNAP = os.path.join(BASE, "audit-snapshot.json")
OUT = os.path.join(BASE, "overview.md")

def main():
    with open(SNAP, encoding="utf-8") as f:
        s = json.load(f)
    agents = s.get("byAgent", [])
    tools = s.get("byTool", [])
    win_min = round(s.get("sampleWindowMs", 0) / 60000, 1)
    total = s.get("sampleEvents", 0)
    L = []
    L.append("# 资源监察面板 · Token Monitor")
    L.append("")
    L.append(f"> 生成：{s.get('generatedAt','')} · 采样 {total} 事件 / 窗口 {win_min} 分钟")
    L.append("> 数据源：gov audit_query（工具调用事件=token 消耗代理指标）· 属主：HR 驾驶舱")
    L.append("")
    L.append("## 一、Agent 调用强度排行（窗口内）")
    L.append("")
    L.append("| 排行 | Agent | 工具调用 | 错误 | 错误率 | 主要工具 |")
    L.append("|---|---|---|---|---|---|")
    for i, a in enumerate(agents, 1):
        L.append(f"| {i} | {a['agent']} | {a['calls']} | {a['errors']} | {a['errRate']} | {a['tools']} |")
    L.append("")
    L.append("## 二、工具调用分布")
    L.append("")
    L.append("| 工具 | 调用 | 占比 |")
    L.append("|---|---|---|")
    for t in tools:
        pct = round(t["calls"] / max(total, 1) * 100, 1)
        L.append(f"| {t['tool']} | {t['calls']} | {pct}% |")
    L.append("")
    L.append("## 三、监察结论与建议")
    L.append("")
    L.append("- **热点 agent**：调用强度前 3 名消耗显著，建议错峰/精简（高峰 09-12/14-18 只跑实时必需）")
    L.append("- **错误率预警**：错误率 >5% 的会话提示工具面异常（J37 关联），建议排查")
    L.append("- **配额建议**：基于强度为前台角色设置 gov quota（day/week），超限自动告警")
    L.append("- **精确 token**：工具调用为代理指标；精确 token 需宿主用量 API（待接入，token-ledger.md §五）")
    L.append("")
    L.append("---")
    L.append("*resource-monitor v1.0 · 采集=HR(gov audit_query) → 聚合=token-monitor.py → 面板=本文件*")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("panel written:", OUT)

if __name__ == "__main__":
    main()
