#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""failure-pattern-lookup.py v1.0 — 故障模式库本地查询（三轨：P 码 / M 码 / G 码+六类别）

查什么：
  P1-P9   星桥侧复发模式（2026-10-04 库，kb dsh-failure-patterns）
  M1-M6   MBP 9-05 六根因模式（考古报告）
  G1-G31 / F1-F5 / 类别 A-F   MBP hazards 缺口码与类别（2026-10-04 导出）
用法：
  python3 failure-pattern-lookup.py <关键词或码>   如 P1 / M3 / G30 / 静默失败 / 管道掩码
  python3 failure-pattern-lookup.py --list         列出全部码
  python3 failure-pattern-lookup.py --selfcheck    正负样本自证（命中/未命中各一）
文档源（本地）：
  ~/dsh-collab/docs/failure-pattern-library-20261004.md
  ~/dsh-collab/archaeology-mbp/历史问题考古报告-20260905.md
  ~/dsh-collab/mbp-side-export-20261004/hazards/INDEX.md
  ~/dsh-collab/mbp-side-export-20261004/MANIFEST.md
退出码：0 命中 / 1 未命中 / 2 用法错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'

import os, re, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/failure-pattern-lookup.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

HOME = os.path.expanduser('~')
SOURCES = [
    (os.path.join(HOME, 'dsh-collab/docs/failure-pattern-library-20261004.md'), 'P 库（星桥模式）'),
    (os.path.join(HOME, 'dsh-collab/archaeology-mbp/历史问题考古报告-20260905.md'), 'M 库（9-05 考古）'),
    (os.path.join(HOME, 'dsh-collab/mbp-side-export-20261004/hazards/INDEX.md'), 'G 库（hazards 缺口）'),
    (os.path.join(HOME, 'dsh-collab/mbp-side-export-20261004/MANIFEST.md'), '清单（工具/类别）'),
]

def lookup(q):
    ql = q.lower()
    hits = []
    for path, label in SOURCES:
        if not os.path.isfile(path):
            continue
        try:
            text = open(path, encoding='utf-8').read()
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if ql in line.lower():
                ctx = '\n'.join(lines[max(0, i-1):i+2])
                hits.append((label, path, i + 1, line.strip(), ctx))
    return hits

def main():
    args = sys.argv[1:]
    if not args or '--help' in args:
        print(__doc__)
        return 2 if not args else 0
    if '--selfcheck' in args:
        # 正样本：P1 必命中；负样本：不存在的码必不命中
        pos = lookup('P1 壳进程崩溃循环')
        neg = lookup('ZX9-NO-SUCH-CODE-2026')
        ok = len(pos) > 0 and len(neg) == 0
        print('  selfcheck: ' + ('PASS' if ok else 'FAIL') + f'（正 {len(pos)} 命中 / 负 {len(neg)} 命中）')
        return 0 if ok else 1
    if '--list' in args:
        for path, label in SOURCES:
            print(f'== {label}: {path}')
        print('\n  常用码：P1-P9（星桥）· M1-M6（9-05）· G1-G31/F1-F5/类别A-F（MBP）')
        return 0
    q = ' '.join(args)
    hits = lookup(q)
    if not hits:
        print(f'  未命中: {q}\n  提示: 试 P 码/M 码/G 码/类别名（--list 看全表）')
        return 1
    print(f'  命中 {len(hits)} 处 · 查询: {q}\n')
    for label, path, ln, line, ctx in hits[:12]:
        print(f'── {label} · {os.path.basename(path)}:{ln}')
        print('   ' + ctx.replace('\n', '\n   ')[:400])
        print()
    if len(hits) > 12:
        print(f'  …共 {len(hits)} 处，只显前 12')
    return 0

if __name__ == '__main__':
    sys.exit(main())
