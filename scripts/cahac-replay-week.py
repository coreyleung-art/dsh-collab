#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAHAC full-week offline replay v0.3 (HR) — real weekly billing x attribution x CAHAC counterfactual"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== cahac-replay-week 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · （头部无中文用途说明 ⇒ 能力清单为空，建议补 docstring）")
    print("  · 命令/参数: csv-dir, out")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: csv, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/cahac-replay-week.log")
    return 0


#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import csv, os, datetime, glob, argparse


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/cahac-replay-week.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SAVE = {"comm": 0.90, "exec": 0.50, "auto": 0.90}
SHARE = {"comm": 0.40, "exec": 0.35, "auto": 0.25}

def week_billing(csv_dir):
    daily = {}
    for p in sorted(glob.glob(os.path.join(csv_dir, "cost-*.csv"))):
        with open(p, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                d = row.get("start_time_iso", "")[:10]
                if "2026-08-12" <= d <= "2026-08-19":
                    try: daily[d] = daily.get(d, 0) + float(row.get("cost", 0) or 0)
                    except ValueError: pass
    return daily

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", default=os.path.expanduser("~/dsh-collab/token-monitor/deepseek-export"))
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--out", default=os.path.expanduser("~/dsh-collab/token-monitor/replays/cahac-replay-week-0812-0819.md"))
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    daily = week_billing(args.csv_dir)
    total = sum(daily.values())
    factor = sum(SHARE[k] * (1 - SAVE[k]) for k in SHARE)
    L = []
    L.append("# CAHAC 全周真实离线回放 · 8/12-8/19")
    L.append("")
    L.append("> generated: " + datetime.date.today().isoformat() + " · 账单=DeepSeek 精确导出(真实) · 归因=12.8h 聚合+峰值实测 · 反事实=CAHAC 通道模型")
    L.append("")
    L.append("## 一、全周真实成本(逐日)")
    L.append("")
    L.append("| 日期 | 实际 ¥ | CAHAC 反事实 ¥ | 节省 |")
    L.append("|---|---|---|---|")
    for d in sorted(daily):
        c = daily[d]; cf = c * factor
        L.append("| " + d + " | " + format(c, ".2f") + " | " + format(cf, ".2f") + " | " + format(1-factor, ".0%") + " |")
    L.append("| **合计** | **" + format(total, ".2f") + "** | **" + format(total*factor, ".2f") + "** | **" + format(1-factor, ".0%") + "** |")
    L.append("")
    L.append("## 二、切割定义(事件切割规范 v1.0 应用)")
    L.append("")
    L.append("| 成本部分 | 归因 | 切割类 | CAHAC 优化 | 节省 |")
    L.append("|---|---|---|---|---|")
    L.append("| 通信/协调 | 40% | ACK 75.3%+STATUS 20.1%→黑板, 实质 4.6% p2p | 黑板化(0.05/0.10x) | " + format(SAVE["comm"], ".0%") + " |")
    L.append("| 执行/台账 | 35% | run_code/bash/file→TASK | 本地路由+压缩(Local-Splitter) | " + format(SAVE["exec"], ".0%") + " |")
    L.append("| 自动化/事件 | 25% | EVENT→黑板/事件总线, BATCH→邮箱 | 事件化 | " + format(SAVE["auto"], ".0%") + " |")
    L.append("")
    L.append("## 三、结论")
    L.append("")
    L.append("1. 全周实际 ¥" + format(total, ".2f") + "（峰值 8/17-18 ¥1,426 占 80%）")
    L.append("2. CAHAC 反事实 ≈ ¥" + format(total*factor, ".2f") + "（节省 " + format(1-factor, ".0%") + "）")
    peak = daily.get("2026-08-17", 0) + daily.get("2026-08-18", 0)
    L.append("3. 若 8/17-18 已用 CAHAC：两天合计 ≈ ¥" + format(peak*factor, ".0f") + "（实际 ¥" + format(peak, ".0f") + "）")
    L.append("4. 反事实口径=通道权重模型(事件级)，精确 token 级待 v0.4(全线程历史)校准")
    L.append("---")
    L.append("*cahac-replay-week v0.3 · HR · 2026-08-19*")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f: f.write("\n".join(L))
    print("week replay: total ¥" + format(total, ".2f") + " -> CAHAC ¥" + format(total*factor, ".2f") + " (save " + format(1-factor, ".0%") + ")")

if __name__ == "__main__":
    main()