#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""waimai-audit v1.0 (HR) — 外卖运营全量审计聚合层（监察体系 L1）

聚合三审计源 → 归一化审计日志 → 操作统计 + 异常检测 + 熔断标记
数据源：
  1) 面板事件 token-monitor/events/events-YYYY-MM-DD.jsonl（8787 alerts，panel-event-adapter 产出）
  2) 总线捕捉 ~/.dsh/capture/events-*.jsonl（bus-capture 产出，过滤外卖相关 agent/消息）
  3) 工具审计统计 token-monitor/audit-snapshot.json（gov audit 快照，byAgent/byTool）
输出：~/dsh-collab/token-monitor/waimai-audit/audit-YYYY-MM-DD.jsonl（append-only）
熔断：拒单率>20% 或 操作异常率>10% 或 时均操作>50 → 写 token-monitor/replays/alerts.md（FUSED 标记）
零 LLM 成本。用法：python3 waimai-audit.py [--date YYYY-MM-DD] [--panel-url http://127.0.0.1:8787]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime, glob, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/waimai-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

TM = os.path.expanduser("~/dsh-collab/token-monitor")
OUT = os.path.join(TM, "waimai-audit")
ALERTS = os.path.join(TM, "replays", "alerts.md")
WAIMAI_AGENTS = ["aa528267", "waimai", "a17a52f8"]  # 外卖运营/HR 相关

def today(): return datetime.date.today().isoformat()

def load_jsonl(path):
    out = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if line:
                try: out.append(json.loads(line))
                except Exception: pass
    return out

def source_panel(date):
    """8787 alerts（直接拉 + 事件日志合并）"""
    rows = []
    p = os.path.join(TM, "events", "events-" + date + ".jsonl")
    for e in load_jsonl(p):
        rows.append({"ts": e.get("ts"), "store": e.get("store"), "action": e.get("kind"),
                     "params": json.dumps({"severity": e.get("severity")}, ensure_ascii=False),
                     "result": e.get("status"), "source": "panel"})
    return rows

def source_bus(date):
    """bus-capture 捕捉缓冲（外卖相关）"""
    rows = []
    for p in glob.glob(os.path.expanduser("~/.dsh/capture/events-*.jsonl")):
        for e in load_jsonl(p):
            ts = str(e.get("ts", ""))
            if date not in ts and date.replace("-", "") not in ts:
                continue
            text = json.dumps(e, ensure_ascii=False)
            if any(a in text for a in ["waimai", "外卖", "order", "接单", "拒单", "改价", "差评"]):
                rows.append({"ts": ts, "store": e.get("store", ""), "action": "bus_message",
                             "params": text[:200], "result": "", "source": "bus"})
    return rows

def source_gov_stats():
    """audit-snapshot 工具统计（只读参考）"""
    p = os.path.join(TM, "audit-snapshot.json")
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}

def detect_anomalies(rows):
    """异常检测：拒单率/异常率/频率"""
    issues = []
    total = len(rows)
    if total == 0:
        return issues, {}
    rejects = [r for r in rows if "reject" in str(r.get("action", "")).lower() or "拒" in str(r.get("action", ""))]
    reject_rate = len(rejects) / total
    err = [r for r in rows if r.get("result") in ("error", "failed", "500", "timeout")]
    err_rate = len(err) / total if total else 0
    # 时均频率（以最早-最晚时间估算窗口）
    ts = [r.get("ts", "") for r in rows if r.get("ts")]
    rate = None
    if len(ts) >= 2:
        try:
            fmt = "%Y-%m-%dT%H:%M:%S"
            t0 = datetime.datetime.strptime(ts[0][:19], fmt); t1 = datetime.datetime.strptime(ts[-1][:19], fmt)
            hours = max((t1 - t0).total_seconds() / 3600, 0.1)
            rate = total / hours
        except Exception:
            pass
    if reject_rate > 0.20: issues.append("拒单率 %.0f%% > 20%%" % (reject_rate * 100))
    if err_rate > 0.10: issues.append("异常率 %.0f%% > 10%%" % (err_rate * 100))
    if rate and rate > 50: issues.append("时均操作 %.0f > 50（频率异常）" % rate)
    return issues, {"total": total, "reject_rate": round(reject_rate, 3), "err_rate": round(err_rate, 3), "per_hour": round(rate, 1) if rate else None}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=today())
    args = ap.parse_args()
    rows = source_panel(args.date) + source_bus(args.date)
    rows.sort(key=lambda r: str(r.get("ts", "")))
    os.makedirs(OUT, exist_ok=True)
    log = os.path.join(OUT, "audit-" + args.date + ".jsonl")
    # 幂等：跳过已存在 ts+action+store 的行
    existing = {(r.get("ts"), r.get("action"), r.get("store")) for r in load_jsonl(log)}
    added = 0
    for r in rows:
        k = (r.get("ts"), r.get("action"), r.get("store"))
        if k in existing: continue
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        existing.add(k); added += 1
    issues, stats = detect_anomalies(rows)
    gov = source_gov_stats()
    summary = {"date": args.date, "rows": len(rows), "added": added, "stats": stats,
               "issues": issues, "gov_sample_events": gov.get("totalEvents")}
    with open(os.path.join(OUT, "summary-" + args.date + ".json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    if issues:
        with open(ALERTS, "a", encoding="utf-8") as f:
            f.write("\n## waimai-audit FUSED " + args.date + "\n- " + "；".join(issues) + "\n")
        print("⚠ ISSUES:", "；".join(issues))
    print("audit ok: rows=%d added=%d stats=%s issues=%s" % (len(rows), added, stats, issues or "-"))

if __name__ == "__main__":
    main()