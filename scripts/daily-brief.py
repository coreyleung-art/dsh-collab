#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily-brief v1.0 (HR) — 24h 工作简报自动归集生成

数据源（黑板/审计，零 LLM）：
  1) resource-registry.md 更新日志（主线+分支线任务）
  2) approval-daily / approval-ledger（审批定档）
  3) waimai-audit summary（日常检查-外卖监察）
  4) wakeup-queue（黑板订阅唤醒）
  5) token-monitor replays/daily-trend（成本）
输出：reports/daily-brief-YYYY-MM-DD.md（简报）
用法：python3 daily-brief.py [--days 1] [--days7]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/daily-brief.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
TM = os.path.join(COLLAB, "token-monitor")
OUT = os.path.join(COLLAB, "reports")

def today():
    return datetime.date.today().isoformat()

def read_registry(days=1):
    items = []
    p = os.path.join(COLLAB, "resource-registry.md")
    if not os.path.exists(p):
        return items
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    for line in open(p, encoding="utf-8", errors="ignore"):
        if "| 2026-08-" in line and "| v1.0." in line:
            m = re.search(r"\| (\d{4}-\d{2}-\d{2}) \| v1\.0\.(\d+) \| (.*)", line)
            if m and m.group(1) >= cutoff:
                items.append({"date": m.group(1), "version": "v1.0." + m.group(2), "desc": m.group(3)[:200]})
    return items

def read_approval_daily():
    p = os.path.join(TM, "approval-daily-" + today() + ".json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return None

def read_audit_summary():
    p = os.path.join(TM, "waimai-audit", "summary-" + today() + ".json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return None

def read_wakeups():
    rows = []
    for p in glob.glob(os.path.join(TM, "wakeup-queue", "*.jsonl")):
        for line in open(p, encoding="utf-8", errors="ignore"):
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return [r for r in rows if r.get("ts", "").startswith(today())]

def push_wecom(report, out):
    """POST 8790/send 推送到企微（外联通讯员提供的入口）"""
    import urllib.request
    try:
        data = json.dumps({"channel": "wecom", "level": "P1", "source": "daily-brief",
                           "text": report[:3500]}).encode()
        req = urllib.request.Request("http://127.0.0.1:8790/send", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            print("PUSH_WECOM:", resp.status, resp.read().decode("utf-8", "ignore")[:120])
    except Exception as ex:
        print("PUSH_WECOM_FAIL:", ex)

def read_fuse_config():
    p = os.path.join(COLLAB, "approval-config.json")
    try:
        cfg = json.load(open(p, encoding="utf-8"))
        g = cfg.get("cost_gate", {}).get("global_fuse", {})
        return "单日熔断: FUSED>=%s / HALT>=%s（%s）· 周兜底 %s" % (g.get("fused_yuan"), g.get("halt_yuan"), g.get("period"), cfg.get("cost_gate", {}).get("period_fuse", {}).get("weekly_halt_yuan"))
    except Exception:
        return ""

def read_cost_trend():
    p = os.path.join(TM, "replays", "daily-trend.md")
    if os.path.exists(p):
        lines = open(p, encoding="utf-8", errors="ignore").read().splitlines()
        for l in reversed(lines):
            if today() in l:
                return l
    return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--days7", action="store_true")
    ap.add_argument("--push-wecom", action="store_true", help="生成后推送到企微（8790 webhook）")
    args = ap.parse_args()
    days = 7 if args.days7 else args.days
    registry = read_registry(days)
    approval = read_approval_daily()
    audit = read_audit_summary()
    wakeups = read_wakeups()
    cost = read_cost_trend()
    kw = ["架构", "协议", "制度", "规则", "体系", "监察", "放行", "审批", "索引", "论文", "S6", "成本门禁"]
    mainline = [i for i in registry if any(k in i["desc"] for k in kw)]
    branches = [i for i in registry if i not in mainline]
    L = ["# 24h 工作简报 · " + today(), "",
         "> 自动归集：registry 更新日志 + 审批台账 + 外卖监察 + 黑板订阅 + 成本趋势 · HR daily-brief v1.0",
         "", "## 一、主线推进（%d 项）" % len(mainline)]
    for i in mainline:
        L.append("- **%s** %s" % (i["version"], i["desc"][:130]))
    L += ["", "## 二、智能体分支线（%d 项）" % len(branches)]
    for i in branches:
        L.append("- **%s** %s" % (i["version"], i["desc"][:130]))
    L += ["", "## 三、日常检查"]
    if audit:
        s = audit.get("stats", {})
        L.append("- 外卖监察：操作 %d 条 · 拒单率 %.0f%% · 异常率 %.0f%% · 时均 %.1f" % (
            audit.get("rows", 0), s.get("reject_rate", 0) * 100, s.get("err_rate", 0) * 100, s.get("per_hour", 0) or 0))
    else:
        L.append("- 外卖监察：今日审计未跑（09:20 launchd）")
    if approval:
        L.append("- 审批巡检：%d 任务 · 档位分布 %s · 需确认 %d" % (
            approval.get("tasks", 0), approval.get("distribution", {}), len(approval.get("need_confirm", []))))
    L.append("- 黑板订阅唤醒：%d 条（队列 wakeup-queue）" % len(wakeups))
    L += ["", "## 四、成本", "- " + (cost if cost else "今日成本趋势待每日回放更新"), "- " + read_fuse_config()]
    L += ["", "## 五、下一步建议", "- 由 HR 按主线遗留补充"]
    report = "\n".join(L)
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "daily-brief-" + today() + ".md")
    open(out, "w", encoding="utf-8").write(report + "\n")
    print(report)
    print("\nBRIEF_SAVED:", out)
    if args.push_wecom:
        push_wecom(report, out)

if __name__ == "__main__":
    main()
