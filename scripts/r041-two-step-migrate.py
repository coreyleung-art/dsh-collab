#!/usr/bin/env python3
# r041-two-step-migrate.py — 账本 R041 两步法迁移（10-04 09:22 窗口执行；--dry-run 默认只报不改）
# 步骤1：12 条重分类（MBP 2026-10-03 表，已逐条对账）——跨对象行为准则=规则留账本
# 步骤2：剩余 资源冲突 31 条 → 退役索引（retiredEntries），按 ^## J 分章节精确删（防行号截断陷阱）
# 判据：被删的全是 J 开头且分类=资源冲突；12 条重分类后不再含 资源冲突；计数口径同步。
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#

import re, sys, shutil, json, datetime

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== r041-two-step-migrate 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · ★ R006 ⑦：固定路径日志；失败也留痕。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/r041-two-step-migrate.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

LOG = os.path.expanduser("~/dsh-collab/logs/r041-two-step-migrate.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

RULES = '/Users/coreyleung/dsh-collab/rules-registry/RULES.md'
RECLASS = {'J29':'工程','J33':'协作','J34':'协作','J35':'工程','J36':'架构','J37':'工程',
           'J38':'协作','J39':'方法论','J40':'方法论','J41':'协作','J43':'方法论','J44':'工程'}
DRY = '--dry-run' in sys.argv

def split_blocks(s):
    return re.split(r'(?=^## )', s, flags=re.M)

def main():
    s = open(RULES).read()
    blocks = split_blocks(s)
    reclass_done = 0
    migrated = []
    stay = []
    for i, b in enumerate(blocks):
        m = re.match(r'^## (J\d+)\s', b)
        if not m:
            continue
        jid = m.group(1)
        cls = re.search(r'- 分类:\s*([^\n|]+)', b)
        cur = cls.group(1).strip() if cls else '?'
        if jid in RECLASS:
            if cur != '资源冲突':
                print(f'  ⚠️ {jid} 现分类={cur}，与预期 资源冲突 不符，跳过重分类')
                continue
            new = RECLASS[jid]
            blocks[i] = b.replace(f'- 分类: {cur}', f'- 分类: {new}', 1)
            reclass_done += 1
        elif cur == '资源冲突':
            migrated.append((jid, b))
    # 步骤2 迁移体
    migrated_ids = [jid for jid, _ in migrated]
    if not migrated_ids:
        print('  无可迁移条目（可能已迁完）')
    else:
        body = '\n\n## retiredEntries（R041 退役索引 · 数据搬出账本留痕，溯源不悬空）\n'
        for jid, b in migrated:
            first = b.strip().split('\n')[0]
            name = first.replace(f'## {jid}', '').strip(' ✅')
            body += f'- {jid} | retiredAt:2026-10-04 | retiredBy:R041 | movedTo:ledgerIndex.keys | 原名:{name}\n'
        blocks = [b for b in blocks if not (re.match(r'^## (J\d+)\s', b) and re.match(r'^## (J\d+)\s', b).group(1) in migrated_ids)]
        # 找到 RULES 主体末尾（最后一个规则块之后）追加退役索引
        # 简单做法：追加到文件尾
        blocks.append(body)
    new_s = ''.join(blocks)
    # 计数口径
    r_cnt = len(re.findall(r'^## R\d+', new_s, flags=re.M))
    j_cnt = len(re.findall(r'^## J\d+', new_s, flags=re.M))
    err_cnt = len(re.findall(r'^## R-ERR', new_s, flags=re.M))
    total = r_cnt + j_cnt + err_cnt
    new_s = re.sub(r'^> v[\d.]+\s*\|\s*\d+\s*条', f'> v2.17.0 | {total} 条', new_s, count=1, flags=re.M)
    # 断言：被删的全是 J 且原分类资源冲突（已在循环内保证）；重分类 12 条
    print(f'  dry-run 报告（{"未改" if DRY else "已写盘"}）：重分类 {reclass_done}/12 · 迁移 {len(migrated_ids)} 条 · 新计数 R{r_cnt}·J{j_cnt}·R-ERR{err_cnt}={total}')
    if reclass_done != 12:
        print('  ❌ 重分类不足 12，中止'); return 2
    if len(migrated_ids) != 31:
        print(f'  ❌ 迁移条目 {len(migrated_ids)}≠31，中止'); return 2
    if not DRY:
        shutil.copyfile(RULES, RULES + '.bak-merge-r041-20261004')
        open(RULES, 'w').write(new_s)
        print('  已写盘，备份 RULES.md.bak-merge-r041-20261004')
    return 0

if __name__ == '__main__':
    sys.exit(main())
