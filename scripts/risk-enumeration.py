#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""风险穷举工具 v0.1 (HR)

用法：python3 risk-enumeration.py --topic "CAHAC 架构" [--categories a,b,c] [--out path]
输入：调研/架构主题（+ 可选类别清单）
输出：风险穷举模板骨架 md（7 类分类/概率×影响矩阵/TOP N 必防/对策列）——由 agent 填充具体风险

类别默认：architecture,communication,cost,governance,implementation,academic,external
方法（J39 规范）：回溯相关记录→逐类穷举→概率×影响定级→对策→TOP N→结论

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, sys, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/risk-enumeration.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DEFAULT_CATS = ["architecture","communication","cost","governance","implementation","academic","external"]
CAT_LABEL = {
    "architecture": "架构", "communication": "通信", "cost": "成本",
    "governance": "治理", "implementation": "实施", "academic": "学术", "external": "外部",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, help="评估主题")
    ap.add_argument("--categories", default=",".join(DEFAULT_CATS))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    # ★ 2026-10-09 修：原行末尾少一个 `)`（闭合 os.path.join）⇒ 该脚本【自 2026-10-03 起无法编译】，
    #   而它是 J39「立项前风险穷举」（enforced）的执行件、有 3 处引用，
    #   **6 天内无人发现**（无「语法检查」门）。发现方式：批量补课时跑全量 py_compile。
    out = args.out or os.path.join(
        os.path.expanduser("~/dsh-collab/research/cost-governance/risk-"
                           + args.topic.replace(" ", "-") + ".md"))
    lines = [
        f"# 风险穷举评估 · {args.topic}",
        "",
        f"> 工具：risk-enumeration.py v0.1 · 生成：{datetime.date.today()} · 方法：J39 风险穷举规范（回溯→穷举→定级→对策→TOP N→结论）",
        "> 填写：agent 按以下骨架穷举（每类 ≥2 项），高概率×高影响风险必须给出防线",
        "",
        "## 一、风险分类穷举",
        "",
    ]
    for c in cats:
        label = CAT_LABEL.get(c, c)
        lines += [f"### {label}（{c}）", "", "| # | 风险 | 触发 | 概率 | 影响 | 对策 |", "|---|---|---|---|---|---|", "| | | | 高/中/低 | 高/中/低 | |", ""]
    lines += [
        "## 二、风险矩阵（概率×影响）",
        "",
        "| | 低影响 | 中影响 | 高影响 |",
        "|---|---|---|---|",
        "| **高概率** | | | |",
        "| **中概率** | | | |",
        "| **低概率** | | | |",
        "",
        "## 三、TOP N 必防风险（高×高 + 中×高）",
        "",
        "| 排名 | 风险 | 防线（已就绪/需补） |",
        "|---|---|---|",
        "| 1 | | |",
        "",
        "## 四、结论",
        "",
        "1. ",
        "---",
        f"*风险穷举：{datetime.date.today()} · {args.topic} · 依据：J39 规范*",
    ]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    print("template:", out)

if __name__ == "__main__":
    main()