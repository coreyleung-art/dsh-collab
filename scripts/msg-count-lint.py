#!/usr/bin/env python3
"""发送前检查：消息里的计数有没有带时点/口径。

由来（星桥 2026-09-14 的诊断）：我「报数可靠性 < 核数可靠性」不是能力差而是结构差 ——
核数只需对照（人有天然优势），报数却要求把「窗口/分母/端点」绑进产物，而绑定这件事
工具能做、人记不住。所以修法不是「下次注意」，而是把窗口与分母做成【发送前的必填项】。

它做什么：扫一段文字，找出【裸计数】—— 形如 N 条 / N 个 / N 张 / N 次 / N 处 / N 键 的
数字，而其附近（同一行内）没有限定词（截至 / 实测 / 约 / 时点 / 于 HH:MM / （…口径…））。

用法：
  python3 msg-count-lint.py <file>          # 检查文件
  echo "文本" | python3 msg-count-lint.py -   # 检查 stdin
退出码：0 = 没发现裸计数；1 = 有裸计数（发出前应补时点或口径）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import re, sys

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/msg-count-lint.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LIMITERS = ["截至", "实测", "约", "时点", "口径", "快照", "来源", "mtime",
            "seeded", "seed", "于 ", "前为", "当时", "自 ", "起"]

# 裸计数候选：数字 + 单位。单位表取自实际写法。
UNITS = r"(?:条|个|张|次|处|键|字段|行|份|对|人|列|段|块|类|种|面|项)"
PAT = re.compile(rf"(\d[\d,]*)\s*{UNITS}")

# 允许例外的上下文（明显不是统计量的）
EXEMPT_CTX = ["thread-mu", "sha256", "v1.", "v3.", "L8", "L9", "行 ", "第 ",
              "HTTP ", "20", "40", "404", "200"]


def lint(text, window=26):
    bad = []
    for line in text.split("\n"):
        for m in PAT.finditer(line):
            ctx = line[max(0, m.start() - window): m.end() + window]
            if any(k in ctx for k in LIMITERS):
                continue
            if any(k in ctx for k in EXEMPT_CTX):
                continue
            bad.append((m.group(0), ctx.strip()))
    return bad


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "-"
    text = sys.stdin.read() if arg == "-" else open(arg, encoding="utf-8").read()
    bad = lint(text)
    n_lines = len([l for l in text.split("\n") if l.strip()])
    print(f"检查 {n_lines} 行 · 发现裸计数 {len(bad)} 处")
    for tok, ctx in bad[:25]:
        print(f"  ★ {tok:12} …{ctx}…")
    if len(bad) > 25:
        print(f"  …另有 {len(bad) - 25} 处")
    if not bad:
        print("  ✅ 未发现裸计数（但本检查只覆盖『数字+单位』形态，不覆盖其它种类的裸值）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
