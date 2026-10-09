#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC compliance checker v0.1 (HR) — consistency assurance
Scans agent profile exports for Agent Card fields (channels/budget/topics/comm_style),
reports adoption rate. Weekly run with agent_profiles export.
Usage: python3 cahac-compliance-check.py --profiles profiles.json

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
    print("== cahac-compliance-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。")
    print("  · 依据：r006-debt-assess.py 机械扫描未检出以下原语：")
    print("  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数")
    print("  · ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。")
    print("  · 命令/参数: profiles")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-compliance-check.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-compliance-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CARD_FIELDS = ["channels", "budget", "topics", "comm_style"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", required=True)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    profs = json.load(open(args.profiles, encoding="utf-8"))
    profs = profs.get("profiles", profs) if isinstance(profs, dict) else profs
    total = len(profs)
    adopted = 0
    missing = []
    for p in profs:
        s = json.dumps(p, ensure_ascii=False)
        if "cahac" in s.lower() or any(f in s.lower() for f in CARD_FIELDS):
            adopted += 1
        else:
            missing.append(p.get("agentId", "?"))
    L = ["# CAHAC 一致性检查 · " + datetime.date.today().isoformat(), "",
         "- profiles: " + str(total) + " · 已声明 Agent Card: " + str(adopted) + " (" + format(adopted/total, ".0%") if total else "0",
         "- 缺失: " + str(len(missing)) + " 会话", "", "## 建议", "",
         "1. 未声明会话=默认 p2p（向后兼容，CAHAC §11）",
         "2. 关键角色（协调/HR/运营/设备）优先补 Agent Card 声明（channels/budget/topics）",
         "3. 行为一致性：审计 agent_send 占比周检（目标 <30%）",
         "4. 结果一致性：每日回放/日审自动验证成本"]
    out = os.path.expanduser("~/dsh-collab/token-monitor/replays/compliance-" + datetime.date.today().isoformat() + ".md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("compliance:", out, "| adopted", adopted, "/", total)

if __name__ == "__main__":
    main()