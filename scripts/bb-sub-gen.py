#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-sub-gen v1.0 (HR) — 黑板订阅守护生成器（角色就任基础设施）

职责：新角色就任时一键生成 bb-sub 订阅守护（com.dsh.bb-sub.<role> plist + launchctl load）
      ——解决「新角色未接订阅守护」治理问题（星舵实例 2026-08-30 教训）。

用法：
  python3 bb-sub-gen.py --role xingduo --prefixes "data/iterations/,data/blueprint/,data/progress/,notes/mac-mini/,notes/collab/" [--inbox bb] [--load]
  python3 bb-sub-gen.py --audit          # 差异审计：agent_profiles vs launchctl bb-sub
  python3 bb-sub-gen.py --list           # 列出已注册守护

前置：xingduo 实例已手工补建（~/Library/LaunchAgents/com.dsh.bb-sub.xingduo.plist）可作模板参考。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, os, subprocess, re, glob, json


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-sub-gen.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LAUNCH_AGENTS = os.path.expanduser('~/Library/LaunchAgents')
BB_SUB_PREFIX = 'com.dsh.bb-sub.'

def generate_plist(role, prefixes, inbox='bb'):
    plist_path = os.path.join(LAUNCH_AGENTS, f'{BB_SUB_PREFIX}{role}.plist')
    # 订阅器路径（bb-sub 常驻，复用既有）
    bb_sub = os.path.expanduser('~/dsh-collab/scripts/bb-subscribe.py')
    if not os.path.exists(bb_sub):
        # 尝试其他位置
        for cand in ['/Users/coreyleung/dsh-collab/scripts/blackboard-subscribe.py',
                     '/Users/coreyleung/dsh-collab/rust-tools/dist/dsh-tools']:
            if os.path.exists(cand):
                bb_sub = cand
                break
    inbox_file = os.path.expanduser(f'~/.dsh/inbox/{inbox}/{role}.jsonl')
    os.makedirs(os.path.dirname(inbox_file), exist_ok=True)
    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{BB_SUB_PREFIX}{role}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{bb_sub}</string>
        <string>--prefixes</string>
        <string>{prefixes}</string>
        <string>--inbox</string>
        <string>{inbox_file}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/bb-sub-{role}.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/bb-sub-{role}.err</string>
</dict>
</plist>
'''
    with open(plist_path, 'w', encoding='utf-8') as f:
        f.write(plist)
    return plist_path

def load_plist(role):
    label = f'{BB_SUB_PREFIX}{role}'
    r = subprocess.run(['launchctl', 'load', os.path.join(LAUNCH_AGENTS, f'{label}.plist')], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()

def list_daemons():
    plists = glob.glob(os.path.join(LAUNCH_AGENTS, f'{BB_SUB_PREFIX}*.plist'))
    return sorted(os.path.basename(p).replace(BB_SUB_PREFIX, '').replace('.plist', '') for p in plists)

def audit():
    """差异审计：agent_profiles 已登记角色 vs launchctl 已注册守护"""
    bus = json.load(open(os.path.expanduser('~/.dsh/agent-bus.json'), encoding='utf-8'))
    profiles = bus.get('profiles', [])
    daemons = set(list_daemons())
    # 已登记角色的职能关键词（role + abilities 提取英文职能词）
    FUNC_MAP = [('coordinator', ['协调者', '中枢', 'coordinator', '星桥']),
                ('hr', ['资源管理', '成本监察', 'HR', '司库']),
                ('qa', ['QA', '验收', '验金石']),
                ('device', ['设备协调', '罗盘']),
                ('learning', ['学习引擎', '知了']),
                ('recovery', ['恢复评估', '自查', '守望']),
                ('supply', ['供应链', '依赖', '守链']),
                ('xingduo', ['进度监督', '星舵']),
                ('media', ['媒体', '拾光']),
                ('ingest', ['摄取', '归档', '文汇']),
                ('custserv', ['智能客服', '回声']),
                ('sysops', ['系统运维', '守灯塔']),
                ('health', ['健康审查', '守灯']),
                ('insight', ['用户洞察', '明鉴'])]
    missing = []
    for dname, kws in FUNC_MAP:
        if dname not in daemons:
            # 该职能有登记角色但无守护
            has_role = any(any(k in str(p.get('role') or '') for k in kws) for p in profiles)
            if has_role:
                missing.append(f'{dname} ({kws[0]})')
    return len(profiles), daemons, missing

def main():
    ap = argparse.ArgumentParser(description='黑板订阅守护生成器（HR）')
    ap.add_argument('--role', help='角色名（如 xingduo）')
    ap.add_argument('--prefixes', help='订阅前缀（逗号分隔，如 data/iterations/,data/blueprint/）')
    ap.add_argument('--inbox', default='bb', help='收件箱子目录（默认 bb）')
    ap.add_argument('--load', action='store_true', help='生成后 launchctl load')
    ap.add_argument('--list', action='store_true', help='列出已注册守护')
    ap.add_argument('--audit', action='store_true', help='差异审计（角色 vs 守护）')
    args = ap.parse_args()

    if args.list:
        print('已注册 bb-sub 守护:', list_daemons())
        return 0
    if args.audit:
        roles, daemons, missing = audit()
        print(f'已登记档案: {roles} | 已注册守护: {len(daemons)}')
        print('守护列表:', sorted(daemons))
        if missing:
            print('⚠️ 缺订阅守护的角色:', missing)
            print('  建议: python3 bb-sub-gen.py --role <名> --prefixes "..." --load')
        else:
            print('✅ 无缺口')
        return 0
    if args.role and args.prefixes:
        plist_path = generate_plist(args.role, args.prefixes, args.inbox)
        print(f'plist 生成: {plist_path}')
        if args.load:
            ok, err = load_plist(args.role)
            print('launchctl load:', 'OK' if ok else f'FAIL {err}')
        return 0
    ap.print_help()
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
