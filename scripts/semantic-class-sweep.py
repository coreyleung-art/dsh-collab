#!/usr/bin/env python3
# semantic-class-sweep.py — 「语义类」陈旧候选面扫描器
#
# 背景：文档改版时有两类陈旧，性质不同、抓法也不同：
#   ① 版本号类  —— 有模式，grep 可判（可区分对错）
#   ② 语义类    —— 快照日期 / 未来时 / 状态描述，**没有可靠模式**，只能列候选后人工复读
# 本工具做的是 ②：它**不判对错**，只保证「风险行不遗漏已覆盖的模式」。
#
# ★ 诚实局限（实测）：
#   · 「标题含日期」这一类**可区分**——缺陷版会新增该行候选，干净版不会。
#   · 「未来时/时态」这一类**不可区分**——干净文本合法地提到「重启前…」时同样会被列入候选。
#   因此：候选为空 ≠ 无陈旧；候选非空 ≠ 有问题。必须人工复读。
#
# 用法：python3 semantic-class-sweep.py <文件> [<文件> ...]
# 退出码：0 无候选 / 1 有候选（需人工复读）/ 2 用法或 IO 错误
import re
import sys

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/semantic-class-sweep.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

PATTERNS = [
    ('标题含日期（快照须标更新日）', r'^#{1,6} .*（\d{4}-\d{2}-\d{2}[^）]*）'),
    ('未来时/待办态（须确认该事是否已发生）', r'重启后|下次重启|待验|待收|将改|尚未|即将|将要|之后生效'),
    ('相对时间词（会自然过期）', r'今天|昨天|本周|上周|本月|最近|目前'),
    ('现状声明里的否定/待定性', r'未验|未证|未常驻|未完成|不生效'),
]


def sweep(path):
    hits = []
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh, 1):
            for name, pattern in PATTERNS:
                if re.search(pattern, line):
                    hits.append((i, name, line.strip()[:100]))
    return hits


def main(argv):
    if len(argv) < 2:
        sys.stderr.write('用法: semantic-class-sweep.py <文件> [<文件> ...]\n')
        return 2
    total = 0
    for path in argv[1:]:
        try:
            hits = sweep(path)
        except OSError as err:
            sys.stderr.write('读取失败 %s: %s\n' % (path, err))
            return 2
        print('%s —— 候选 %d 行（需人工复读；本工具不判对错）' % (path, len(hits)))
        for line_no, name, text in hits:
            print('  L%-5d [%s] %s' % (line_no, name, text))
        total += len(hits)
    print('\n合计候选 %d 行。提醒：与「被核版本 + 核对时刻」配对使用（版本绑定）；候选为空不等于无陈旧。' % total)
    return 1 if total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
