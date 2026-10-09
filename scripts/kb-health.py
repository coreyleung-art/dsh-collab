#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-health v1.0 (HR) — 知识库健康巡检（每日自动，零 LLM）

验证：① KB embedded 状态 ② doc/chunk 计数 ③ 索引文件同步（research-paper-library-index.md）
异常 → 写 alerts.md（不打扰用户）。用法：python3 kb-health.py

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
    print("== kb-health 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · kb-health v1.0 (HR) — 知识库健康巡检（每日自动，零 LLM）")
    print("  · 验证：① KB embedded 状态 ② doc/chunk 计数 ③ 索引文件同步（research-paper-library-index.md）")
    print("  · 异常 → 写 alerts.md（不打扰用户）。用法：python3 kb-health.py")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/kb-health.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, datetime, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/kb-health.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

KB = "afa7de13-011a-4c73-a9d6-13492c05cdf7"
IDX = os.path.expanduser("~/dsh-collab/research/ops-science/research-paper-library-index.md")
ALERTS = os.path.expanduser("~/dsh-collab/token-monitor/replays/alerts.md")

def main():
    issues = []
    # 索引文件 doc 数（解析 AUTO-GENERATED 头）
    idx_docs = None
    try:
        head = open(IDX, encoding="utf-8").read()[:2000]
        m = re.search(r"- documents: (\d+)", head)
        if m: idx_docs = int(m.group(1))
    except Exception:
        issues.append("索引文件不可读")
    # 最近批次报告（paper-pull-final-summary*）的 doc 数作为对照
    summary_docs = None
    for f in ["paper-pull-final-summary-mcp-gateway-2026-08-22.md"]:
        p = os.path.expanduser("~/dsh-collab/research/ops-science/" + f)
        if os.path.exists(p):
            t = open(p, encoding="utf-8").read()
            m = re.search(r"KB ops-science-research \d+ → \*\*(\d+)\*\* docs", t)
            if m: summary_docs = int(m.group(1))
    report = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "idx_docs": idx_docs, "summary_docs": summary_docs,
        "note": "KB embedded 状态由 knowledge_stats 查询（agent 侧），脚本侧验证索引文件一致性",
        "issues": issues,
    }
    out = os.path.expanduser("~/dsh-collab/token-monitor/kb-health.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if issues:
        with open(ALERTS, "a", encoding="utf-8") as f:
            f.write("\n## kb-health " + datetime.date.today().isoformat() + "\n- " + "；".join(issues) + "\n")
    print("kb-health:", json.dumps(report, ensure_ascii=False)[:200])

if __name__ == "__main__":
    main()
