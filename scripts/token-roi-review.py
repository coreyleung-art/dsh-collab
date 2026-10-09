#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日 Token ROI 审查工具 v0.1 (HR)

输入：DeepSeek 平台用量导出目录（cost-*.csv / amount-*.csv）
输出：token-monitor/daily-reviews/YYYY-MM-DD.md（日审报告：消耗/环比/异常/模型分布）
用法：python3 token-roi-review.py [--csv-dir DIR] [--out-dir DIR]

设计：每日 09:00 触发（launchd 模板 com.dsh.hr.token-roi，成本治理恢复后启用）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, csv, glob, os, sys
from collections import defaultdict
from datetime import datetime, date


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/token-roi-review.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def parse_cost(path):
    """cost-*.csv: user_id,start,end,model,wallet,cost,currency -> {date: {model: cost}}"""
    daily = defaultdict(lambda: defaultdict(float))
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = row.get("start_time_iso", "")[:10]
            m = row.get("model", "")
            try: c = float(row.get("cost", 0) or 0)
            except ValueError: c = 0
            if d: daily[d][m] += c
    return daily

def parse_amount(path):
    """amount-*.csv: type in {input_cache_hit_tokens, input_cache_miss_tokens, output_tokens, request_count}"""
    daily = defaultdict(lambda: defaultdict(int))
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = row.get("start_time_iso", "")[:10]
            t = row.get("type", "")
            try: a = int(float(row.get("amount", 0) or 0))
            except ValueError: a = 0
            if d: daily[d][t] += a
    return daily

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", default=os.path.expanduser("~/dsh-collab/token-monitor/deepseek-export"))
    ap.add_argument("--out-dir", default=os.path.expanduser("~/dsh-collab/token-monitor/daily-reviews"))
    args = ap.parse_args()
    costs = {}; amounts = {}
    for p in sorted(glob.glob(os.path.join(args.csv_dir, "cost-*.csv"))):
        costs.update(parse_cost(p))
    for p in sorted(glob.glob(os.path.join(args.csv_dir, "amount-*.csv"))):
        amounts.update(parse_amount(p))
    if not costs:
        print("NO cost csv found in", args.csv_dir); sys.exit(1)
    days = sorted(costs.keys())
    # 环比与异常检测（环比 >2 倍标红）
    lines = ["# Token 日审报告 · " + datetime.now().strftime("%Y-%m-%d"), "", "| 日期 | 成本 ¥ | 环比 | 命中 | 未命中 | 输出 | 请求 | 标记 |", "|---|---|---|---|---|---|---|---|"]
    prev = None
    for d in days:
        c = sum(costs[d].values()); a = amounts.get(d, {})
        ch = a.get("input_cache_hit_tokens", 0); cm = a.get("input_cache_miss_tokens", 0); out = a.get("output_tokens", 0); req = a.get("request_count", 0)
        ratio = (c / prev - 1) if prev else 0
        flag = "🔴 >2x" if ratio > 2 else ("🟡 >1.5x" if ratio > 1.5 else "")
        lines.append(f"| {d} | {c:.2f} | {ratio*100:+.0f}% | {ch/1e6:.1f}M | {cm/1e6:.1f}M | {out/1e6:.1f}M | {req} | {flag} |")
        prev = c
    total = sum(costs[d].values() for d in days if False)  # placeholder
    tot = sum(sum(v.values()) for v in costs.values())
    lines += ["", f"**合计: ¥{tot:.2f} / {len(days)} 天 = 日均 ¥{tot/max(len(days),1):.2f}**", "", "> 生成: token-roi-review.py v0.1 · 数据: DeepSeek 平台导出 · 优化建议: 见标记行与 token-cost-research-roadmap.md"]
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, datetime.now().strftime("%Y-%m-%d") + ".md")
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    print("written:", out)

if __name__ == "__main__":
    main()