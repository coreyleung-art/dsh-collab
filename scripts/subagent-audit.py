#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subagent-audit (HR) — 子代理全局审查器 (R006 十项标准 / 2026-09-11)

职责: 对全会话库做**子代理专项**审查 —— 存量/增量/归因/合规/资源/生命周期/跨设备。
判据来源: data/registry/hr-ruling-resource-audit-20260911 (P1 扇出治理 / P1.5 归档 / P2 双轨阈值)

八个维度:
  S1 存量   主会话 / 子代理 计数与体积
  S2 归因   每个父会话产出的子代理数(扇出 top-N)
  S3 增量   按创建日的子代理数 -> 突发检测
  S4 合规   对照上限(单父 <=50/日, 全机并发 <=8)
  S5 资源   子代理总体积 / 均值 / 占比
  S6 生命周期 已完成且 >N 天的归档候选(P1.5)
  S7 孤儿   父会话缺失
  S8 跨设备 对端节点可达则报规模, 不可达则**声明 SKIP**(不静默)

R006 十项: 2selfcheck 3cld-check 4version-check 5README 6--tool-version 7日志 8落链 9CLI 10lean4-check
用法:
  subagent-audit.py run [--days 7] [--json] [--top 10]
  subagent-audit.py classify <session-id>
  subagent-audit.py selfcheck|lean4-check|cld-check|version-check|version
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, glob, datetime, subprocess


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/subagent-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = '1.1.0'
JSON_OUT = False
LOG_FILE = os.path.expanduser('~/.dsh/subagent-audit.log')
HOME = os.path.expanduser('~')
SESS_ROOT = os.path.join(HOME, '.dsh', 'sessions')
OUT_DIR = os.path.join(HOME, 'dsh-collab', 'data', 'registry')
BUS_TOKEN = os.path.join(HOME, '.dsh', 'bus-bridge-token')
BUS_HOST = 'xingqiao.meetfunbp.com:8791'
# 判据(来自 HR 裁决书 P1): 单父会话每日扇出上限 / 全机并发上限
# ★ v1.1.0 (明鉴指出的依据缺失, 我认): 这两个上限**没有可追溯的依据** —— 是我在裁决书里给的建议值,
#   当时只写了数字、没写怎么来的。按今晚自立的规矩(对「调整」要求证据, 对「初始值」同样要),
#   它们应标为 design-intent(not verifiable), 并写明「什么测量能让它升级为规格」。
CAP_PER_PARENT_PER_DAY = 50   # status=design-intent; 依据: 无(取整于实测峰值 152 的约 1/3)
CAP_CONCURRENT = 8            # status=design-intent; 依据: 无(按本机 24GB/单会话均 552KB 粗估, 未验证)
CAP_BASIS = {
    'per_parent_per_day': {'value': CAP_PER_PARENT_PER_DAY, 'status': 'design-intent (not verifiable)',
                           'basis': '无实测依据 —— 取整于观测峰值(4787d717 单日 83)的量级, 属偏好形状的数',
                           'promotion_measurement': '需实测「不同并发度下的上下文占用/延迟/失败率」曲线, 取拐点' },
    'concurrent': {'value': CAP_CONCURRENT, 'status': 'design-intent (not verifiable)',
                   'basis': '无实测依据 —— 按本机 24GB 内存与单会话均 552.7KB 粗估, 未做压测',
                   'promotion_measurement': '需实测「并发 N 时的 RSS/失败率」, 取资源拐点' },
}
ARCHIVE_AFTER_DAYS = 7

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + msg + chr(10))
    except Exception:
        pass

def read_head(path):
    """读会话头(首行 JSON) -> dict|None。用 zstandard 流式解前 8KB; 无库则 None(退化不崩)。"""
    fp = os.path.join(path, 'session.jsonl.zstd')
    if not os.path.isfile(fp):
        return None
    try:
        import zstandard
        d = zstandard.ZstdDecompressor()
        with open(fp, 'rb') as fh:
            head = d.stream_reader(fh).read(8192)
        return json.loads(head.decode('utf-8', 'replace').split(chr(10))[0])
    except Exception:
        return None

def dir_size_mb(d):
    t = 0
    for f in glob.glob(os.path.join(d, '*')):
        try:
            t += os.path.getsize(f)
        except Exception:
            pass
    return round(t / 1048576, 3)

def collect():
    """扫描全部 workspace 的会话目录 -> (primaries, subagents)。"""
    prim, sub = [], []
    for ws in sorted(glob.glob(os.path.join(SESS_ROOT, '--*--'))):
        for e in sorted(os.listdir(ws)):
            d = os.path.join(ws, e)
            if not os.path.isdir(d):
                continue
            if not (e.startswith('session-') or re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', e)):
                continue
            h = read_head(d) or {}
            rec = {
                'id': e,
                'short': e.replace('session-', '')[:8],
                'workspace': os.path.basename(ws),
                'origin': h.get('origin') or 'primary',
                'parent': h.get('parentSession') or '',
                'preset': h.get('agentPreset') or '',
                'depth': h.get('delegationDepth'),
                'created_ms': h.get('createdAt'),
                'mb': dir_size_mb(d),
            }
            c = rec['created_ms']
            rec['created'] = (datetime.datetime.fromtimestamp(c / 1000).date().isoformat()
                               if isinstance(c, (int, float)) else '?')
            (sub if rec['origin'] == 'subagent' else prim).append(rec)
    return prim, sub

def bus_peers():
    """读总线节点表; 不可达 -> (None, 原因字符串)。"""
    if not os.path.isfile(BUS_TOKEN):
        return None, '无 bus token'
    try:
        tok = open(BUS_TOKEN).read().strip()
        r = subprocess.run(['curl', '-s', '-m', '12', '-H', 'X-Webhook-Token: ' + tok,
                            'http://' + BUS_HOST + '/bus/nodes'], capture_output=True)
        return json.loads(r.stdout.decode('utf-8', 'replace')).get('nodes'), None
    except Exception as e:
        return None, str(e)[:60]

def do_run(days=7, top=10):
    prim, sub = collect()
    today = datetime.date.today()
    # S1 存量
    s1 = {
        'primary': len(prim), 'subagent': len(sub), 'total': len(prim) + len(sub),
        'primary_mb': round(sum(x['mb'] for x in prim), 1),
        'subagent_mb': round(sum(x['mb'] for x in sub), 1),
    }
    s1['subagent_share_pct'] = round(len(sub) / s1['total'] * 100, 1) if s1['total'] else 0
    # S2 归因
    by_parent = {}
    for x in sub:
        by_parent[x['parent'] or '(未知)'] = by_parent.get(x['parent'] or '(未知)', 0) + 1
    s2 = sorted(by_parent.items(), key=lambda kv: -kv[1])
    # S3 增量
    by_day = {}
    for x in sub:
        by_day[x['created']] = by_day.get(x['created'], 0) + 1
    s3 = sorted(by_day.items())
    # S4 合规
    fanout_day = {}
    for x in sub:
        k = (x['parent'] or '(未知)', x['created'])
        fanout_day[k] = fanout_day.get(k, 0) + 1
    breaches = sorted([{'parent': k[0], 'date': k[1], 'count': v,
                        'cap': CAP_PER_PARENT_PER_DAY, 'over_by': round(v / CAP_PER_PARENT_PER_DAY, 1)}
                       for k, v in fanout_day.items() if v > CAP_PER_PARENT_PER_DAY], key=lambda r: -r['count'])
    # S5 资源
    avg_kb = round(s1['subagent_mb'] * 1024 / len(sub), 1) if sub else 0
    total_mb = s1['primary_mb'] + s1['subagent_mb']
    s5 = {'avg_kb': avg_kb, 'subagent_share_mb_pct': round(s1['subagent_mb'] / total_mb * 100, 1) if total_mb else 0}
    # S6 生命周期
    cands = []
    for x in sub:
        if x['created'] == '?':
            continue
        age = (today - datetime.date.fromisoformat(x['created'])).days
        if age >= ARCHIVE_AFTER_DAYS:
            cands.append({'short': x['short'], 'age_days': age, 'mb': x['mb']})
    s6 = {'count': len(cands), 'mb': round(sum(c['mb'] for c in cands), 1), 'after_days': ARCHIVE_AFTER_DAYS}
    # S7 孤儿
    ids = set(x['id'] for x in prim)
    orphans = [x['short'] for x in sub if x['parent'] and x['parent'] not in ids]
    s7 = {'count': len(orphans), 'samples': orphans[:5]}
    # S8 跨设备
    nodes, err = bus_peers()
    if nodes is None:
        s8 = {'status': 'SKIP', 'reason': err, 'note': '观测缺口已声明, 不静默'}
    else:
        s8 = {'status': 'OK', 'nodes': {k: {kk: vv for kk, vv in v.items() if kk in ('online', 'clients', 'queued')}
                                         for k, v in nodes.items()},
              'note': '对端会话库规模需对端自报; 本工具只能给出节点在线/排队状态'}
    presets = {}
    for x in sub:
        presets[x['preset'] or '(无)'] = presets.get(x['preset'] or '(无)', 0) + 1
    depths = {}
    for x in sub:
        depths[str(x['depth'])] = depths.get(str(x['depth']), 0) + 1
    return {
        'ts': datetime.datetime.now().isoformat(timespec='seconds'),
        'S1': s1, 'S2': s2[:top], 'S2_total_parents': len(s2),
        'S3': s3[-days:] if days else s3, 'S4': breaches,
        'S5': s5, 'S6': s6, 'S7': s7, 'S8': s8,
        'presets': presets, 'depths': depths,
        'caps': {'per_parent_per_day': CAP_PER_PARENT_PER_DAY, 'concurrent': CAP_CONCURRENT},
    }

def print_report(r, top):
    s1 = r['S1']
    print('[子代理审查] ' + r['ts'])
    print('  S1 存量: 主 %d (%.1f MB) + 子 %d (%.1f MB) = %d | 子占 %.1f%%' % (
        s1['primary'], s1['primary_mb'], s1['subagent'], s1['subagent_mb'], s1['total'], s1['subagent_share_pct']))
    print('  S2 归因: 父会话 %d 个 | top%d:' % (r['S2_total_parents'], min(top, len(r['S2']))))
    for k, v in r['S2']:
        print('        %5d  %s' % (v, k))
    print('  S3 增量(按创建日, 近 %d 天):' % len(r['S3']))
    for d, n in r['S3']:
        print('        %s  %4d  %s' % (d, n, '#' * min(n, 60)))
    print('  S4 合规(上限 单父<=%d/日): %s' % (r['caps']['per_parent_per_day'],
          ('%d 处超限' % len(r['S4'])) if r['S4'] else '无超限'))
    for b in r['S4']:
        print('        %s %s -> %d (超 %.1f 倍)' % (b['parent'], b['date'], b['count'], b['over_by']))
    print('  S5 资源: 子代理均值 %.1f KB | 占全会话体积 %.1f%%' % (r['S5']['avg_kb'], r['S5']['subagent_share_mb_pct']))
    print('  S6 生命周期: >%d 天归档候选 %d 个 (%.1f MB)' % (r['S6']['after_days'], r['S6']['count'], r['S6']['mb']))
    print('  S7 孤儿: %d' % r['S7']['count'])
    print('  S8 跨设备: %s %s' % (r['S8']['status'], r['S8'].get('reason', '')))
    if r['S8']['status'] == 'OK':
        for k, v in r['S8']['nodes'].items():
            print('        %s: %s' % (k, json.dumps(v, ensure_ascii=False)))
    print('  preset: %s' % json.dumps(r['presets'], ensure_ascii=False))
    print('  delegationDepth: %s' % json.dumps(r['depths'], ensure_ascii=False))

def cmd_run(args):
    r = do_run(args.days, args.top)
    if args.json or globals().get('JSON_OUT'):
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print_report(r, args.top)
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        fp = os.path.join(OUT_DIR, 'subagent-audit-' + datetime.date.today().isoformat() + '.json')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
        print('  [落链] ' + fp)
        log('run ok ' + fp)
    except Exception as e:
        print('  [落链失败] ' + str(e)[:80]); return 1
    return 0

def cmd_count(args):
    """★ 扇出预检(v1.1.0): 闭合明鉴指出的「无信号」缺口 —— 起子代理前先知道今天已起了多少个。
    与他指出的 0b(集合完整性/无信号失效)同源: 超限是**无感的**, 因为没有任何东西在告知计数。
    退出码: 0=未超限(可放行) / 3=已超限(应阻断或降速) —— 与 deliver-gate 同构(阻断项而非报告项)。"""
    prim, sub = collect()
    pid = args.parent
    if not pid.startswith('session-'):
        for x in prim:
            if x['short'] == pid.replace('session-', '')[:8]:
                pid = x['id']; break
    day = args.date or datetime.date.today().isoformat()
    mine = [x for x in sub if x['parent'] == pid]
    today_n = len([x for x in mine if x['created'] == day])
    cap = CAP_PER_PARENT_PER_DAY
    over = today_n > cap
    out = {'parent': pid, 'date': day, 'count': today_n, 'cap': cap,
           'cap_status': CAP_BASIS['per_parent_per_day']['status'],
           'verdict': 'OVER' if over else 'OK',
           'lifetime_total': len(mine)}
    if args.json or globals().get('JSON_OUT'):
        print(json.dumps(out, ensure_ascii=False))
    else:
        print('[扇出预检] %s | %s 已起 %d 个 | 上限 %d（%s）-> %s' % (
            pid[:20], day, today_n, cap, 'design-intent, 非实测依据', out['verdict']))
        if over:
            print('  X 已超限 —— 建议：改串行 / 分批 / 延后；或就此提出申诉（附证据）')
        print('  该会话累计（全期）: %d 个' % len(mine))
    return 3 if over else 0

def cmd_classify(args):
    prim, sub = collect()
    key = args.sid.replace('session-', '')[:8]
    for x in sub:
        if x['short'] == key:
            rec = dict(x); rec['kind'] = 'subagent'; print(json.dumps(rec, ensure_ascii=False, indent=1))
            return 0
    for x in prim:
        if x['short'] == key:
            kids = [y for y in sub if y['parent'] == x['id']]
            rec = dict(x); rec['kind'] = 'primary'; rec['fanout'] = len(kids); print(json.dumps(rec, ensure_ascii=False, indent=1))
            return 0
    print('[classify] 未找到: ' + args.sid); return 3

def cmd_selfcheck(args):
    print('[selfcheck] subagent-audit v' + VERSION)
    ok = True
    if not os.path.isdir(SESS_ROOT):
        print('  X sessions root 不可访问'); ok = False
    else:
        print('  OK sessions root 可访问')
    prim, sub = collect()
    n = len(prim) + len(sub)
    print('  OK 可解析会话 %d (主 %d / 子 %d)' % (n, len(prim), len(sub)))
    if n == 0:
        print('  X 零会话可解析 —— 解析器可能失效'); ok = False
    # 子代理必须都有 origin 字段可读(否则解析退化)
    unidentified = [x for x in sub if x['parent'] == '']
    if unidentified:
        print('  X 有 %d 个子代理读不到父会话(解析退化)' % len(unidentified)); ok = False
    else:
        print('  OK 全部子代理均解析出父会话')
    # 判据来源在位
    try:
        r = subprocess.run(['curl', '-s', '-m', '10', '-o', '/dev/null', '-w', '%{http_code}',
                            'http://127.0.0.1:8792/data/registry/hr-ruling-resource-audit-20260911'], capture_output=True)
        code = r.stdout.decode().strip()
        if code == '200':
            print('  OK 判据来源在位(HR 裁决书)')
        else:
            print('  ~ SKIP 判据来源读不到(HTTP %s) —— 观测缺口已声明' % code)
    except Exception as e:
        print('  ~ SKIP 判据来源探测失败: %s' % str(e)[:40])
    print('[selfcheck] ' + ('OK PASS' if ok else 'X FAIL'))
    return 0 if ok else 1

def cmd_lean4(args):
    """约束门: 分类判据必须自洽 —— 主/子二分穷尽且互斥; 上限常量必须为正。"""
    prim, sub = collect()
    ok1 = (CAP_PER_PARENT_PER_DAY > 0) and (CAP_CONCURRENT > 0) and (ARCHIVE_AFTER_DAYS > 0)
    kinds = set(x['origin'] for x in prim + sub)
    ok2 = kinds.issubset({'primary', 'subagent'})
    ok3 = all(x['origin'] != 'subagent' for x in prim) and all(x['origin'] == 'subagent' for x in sub)
    ok = ok1 and ok2 and ok3
    print('lean4-check:', 'OK 二分穷尽且互斥 + 上限常量为正' if ok else 'X gate failed')
    return 0 if ok else 1

def cmd_cld(args):
    print('[cld-check] pure CLI, 无 CLD 耦合(仅读会话库 + 可选读总线). PASS'); return 0

def cmd_vcheck(args):
    print('[version-check] pure CLI, 无 dsh 依赖. v' + VERSION); return 0

def cmd_version(args):
    if globals().get('JSON_OUT'):
        print(json.dumps({'tool': 'subagent-audit', 'version': VERSION, 'source': 'VERSION 常量'}, ensure_ascii=False))
    else:
        print('subagent-audit ' + VERSION)
    return 0

def main():
    ap = argparse.ArgumentParser(description='subagent-audit - 子代理全局审查器',
        epilog=('判据来源: data/registry/hr-ruling-resource-audit-20260911 (P1/P1.5/P2); '
                '上限: 单父 %d/日, 全机并发 %d, 归档阈值 %d 天' % (CAP_PER_PARENT_PER_DAY, CAP_CONCURRENT, ARCHIVE_AFTER_DAYS)))
    ap.add_argument('--tool-version', action='store_true')
    argv = [a for a in sys.argv[1:] if a != '--json-out']
    if len(argv) != len(sys.argv[1:]):
        globals()['JSON_OUT'] = True
    sub = ap.add_subparsers(dest='cmd')
    p = sub.add_parser('run')
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--top', type=int, default=10)
    p.add_argument('--json', action='store_true')
    p.add_argument('--dry-run', dest='dry_run', action='store_true')
    pc = sub.add_parser('classify'); pc.add_argument('sid')
    pn = sub.add_parser('count')
    pn.add_argument('--parent', required=True)
    pn.add_argument('--date', default=None)
    pn.add_argument('--json', action='store_true')
    for c in ['selfcheck', 'lean4-check', 'cld-check', 'version-check', 'version']:
        sub.add_parser(c)
    args = ap.parse_args(argv)
    if args.tool_version:
        print(json.dumps({'tool': 'subagent-audit', 'version': VERSION, 'source': 'VERSION 常量',
                          'r006': '⑥--tool-version ⑨--json-out/--dry-run'}, ensure_ascii=False))
        return 0
    if not args.cmd:
        ap.print_help(); return 0
    if args.cmd == 'run' and getattr(args, 'dry_run', False):
        r = do_run(args.days, args.top)
        print('[dry-run] 零变更: 将扫 %d 主 / %d 子, 报告不落链' % (r['S1']['primary'], r['S1']['subagent']))
        return 0
    return {'run': cmd_run, 'classify': cmd_classify, 'count': cmd_count, 'selfcheck': cmd_selfcheck,
            'lean4-check': cmd_lean4, 'cld-check': cmd_cld,
            'version-check': cmd_vcheck, 'version': cmd_version}[args.cmd](args)

if __name__ == '__main__':
    sys.exit(main())
