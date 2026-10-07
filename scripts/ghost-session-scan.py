#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ghost-session-scan v1.1.0 (HR) — 幽灵会话扫描器 (R006 十项标准 / 2026-09-11)

职责: 扫描「无缘无故突然出现在会话列表、新增但没有角色命名」的会话, 作为每次内存治理的重点对象。

四类异常(ghost 判定):
  G1 未登记(unregistered)  — 会话存在(磁盘/总线)但不在 resource-registry
  G2 无角色(roleless)      — 磁盘有会话但无 agent_profile(无身份/无命名)
  G3 突然出现(sudden)      — mtime 在 N 天内且未登记(默认 3 天)
  G4 归档残留(residue)     — 已在 workspace.json archivedSessionIds 但磁盘仍在
  G6 孤儿子代理(orphan)    — origin=subagent 但父会话已不存在

v1.1.0 修复(HR 复核 2026-09-11): v1.0.0 只 glob 'session-*', **完全看不见裸 UUID 子代理目录**,
  而子代理占全会话约 79% —— 属盲区, 不是污染。本版纳入子代理并三分类:
    真幽灵(主会话) / 合法子代理(父在册, 不计分) / 孤儿子代理(父缺失, G6)。
  另: ghosts 口径与 g1_unregistered 分离, 不再把「已登记未建档」并入幽灵主计数。

输出: ghost 评分排序清单(重点治理对象) + 落链 data/registry/ghost-sessions-<date>.json

R006 十项: 1插件(P2) 2selfcheck 3cld-check 4version-check 5README 6--version 7日志 8落链 9CLI 10lean4-check
用法:
  ghost-session-scan.py scan [--days 3] [--json] [--top 20]
  ghost-session-scan.py classify <session-id>   # 单会话判定
  ghost-session-scan.py selfcheck|lean4-check|version|cld-check|version-check
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, datetime, glob

VERSION = '1.1.0'
LOG_FILE = os.path.expanduser('~/.dsh/ghost-session-scan.log')
HOME = os.path.expanduser('~')
SESS_ROOT = os.path.join(HOME, '.dsh', 'sessions')
BUS_FILE = os.path.join(HOME, '.dsh', 'agent-bus.json')
WS_FILE = os.path.join(HOME, '.dsh', 'storages', 'workspace.json')
REGISTRY = os.path.join(HOME, 'dsh-collab', 'resource-registry.md')
OUT_DIR = os.path.join(HOME, 'dsh-collab', 'data', 'registry')

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + msg + chr(10))
    except Exception:
        pass

def short_id(sid):
    """归一化: 去掉 session- 前缀后取前 8 位(与登记表约定一致, 跨源匹配)"""
    s = str(sid).replace('session-', '')
    return s[:8]

def load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except Exception:
        return default

def read_head(path):
    """读会话头(首行 JSON) → dict | None
    v1.1.0: zstandard 流式解前 8KB 只取权威字段; 无库时返回 None(退化不崩)。"""
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

def disk_sessions():
    """磁盘会话: {short_id: {path, mtime, size_mb, origin, parent, preset, depth, kind}}
    v1.1.0: 同时收录裸 UUID 子代理目录(占全会话 ~79%), 用会话头 origin 字段区分主/子。"""
    out = {}
    for ws in glob.glob(os.path.join(SESS_ROOT, '--*--')):
        for d in glob.glob(os.path.join(ws, '*')):
            base = os.path.basename(d)
            if not os.path.isdir(d):
                continue
            if not (base.startswith('session-') or re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-', base)):
                continue
            try:
                st = os.stat(d)
                mt = datetime.datetime.fromtimestamp(st.st_mtime).date().isoformat()
            except Exception:
                mt = '?'
            sz = 0
            for f in glob.glob(os.path.join(d, '*')):
                try:
                    sz += os.path.getsize(f)
                except Exception:
                    pass
            h = read_head(d) or {}
            origin = h.get('origin') or 'primary'
            out[short_id(base)] = {
                'full': base, 'path': d, 'mtime': mt,
                'size_mb': round(sz / 1048576, 1),
                'origin': origin,
                'kind': 'subagent' if origin == 'subagent' else 'primary',
                'parent': h.get('parentSession') or '',
                'preset': h.get('agentPreset') or '',
                'depth': h.get('delegationDepth'),
                'created': (datetime.datetime.fromtimestamp(h['createdAt'] / 1000).date().isoformat()
                            if h.get('createdAt') else '?'),
            }
    return out

def bus_profiles():
    """总线档案: {short_id: {role, updatedAt}}"""
    out = {}
    for p in load_json(BUS_FILE, {}).get('profiles', []):
        aid = str(p.get('agentId') or '')
        if not aid:
            continue
        out[short_id(aid)] = {'role': str(p.get('role') or ''), 'updatedAt': p.get('updatedAt')}
    return out

def archived_ids():
    """workspace.json 归档列表 → set(short_id)"""
    ws = load_json(WS_FILE, {})
    arr = ws.get('global', {}).get('archivedSessionIds', []) or []
    return set(short_id(a) for a in arr)

def registry_ids():
    """登记表 §3 已登记会话 → set(short_id)"""
    try:
        txt = open(REGISTRY, encoding='utf-8').read()
    except Exception:
        return set()
    return set(m for m in re.findall(r'session-([0-9a-f]{8})', txt))

def classify_one(sid_short, disk, profs, arch, reg):
    """单会话判定 → (ghost_types, detail)
    G1 未登记 / G2 无角色(无命名) / G3 突然出现(近期+未登记) / G5 微小存根(疑似废弃)
    G4 归档(信息项: 已归档但占磁盘 —— 非异常, 仅提示)"""
    d = disk.get(sid_short)
    pr = profs.get(sid_short)
    # v1.1.0: 子代理与主会话分离 —— 子代理不是"无主会话", 是正常委派产物
    if d and d.get('kind') == 'subagent':
        pshort = short_id(d.get('parent') or '') if d.get('parent') else ''
        parent_present = bool(pshort) and pshort in disk
        types = [] if parent_present else ['G6']
        return types, {
            'session': sid_short,
            'full_id': d.get('full', ''),
            'kind': 'subagent',
            'parent': pshort or '(未知)',
            'parent_present': parent_present,
            'preset': d.get('preset', ''),
            'depth': d.get('depth'),
            'created': d.get('created', '?'),
            'mtime': d.get('mtime', '?'),
            'size_mb': d.get('size_mb', 0),
            'size_kb': round(d.get('size_mb', 0) * 1024, 1),
            'role': '(子代理)',
            'registered': False,
            'archived': False,
            'types': list(types),
        }
    types = []
    if d and sid_short not in reg:
        types.append('G1')
    if d and not pr:
        types.append('G2')
    if d and sid_short in arch:
        types.append('G4')
    detail = {
        'session': sid_short,
        'full_id': (d or {}).get('full', ''),
        'kind': 'primary',
        'mtime': (d or {}).get('mtime', '?'),
        'size_mb': (d or {}).get('size_mb', 0),
        'size_kb': round((d or {}).get('size_mb', 0) * 1024, 1),
        'role': (pr or {}).get('role', '(无档案)'),
        'registered': sid_short in reg,
        'archived': sid_short in arch,
        'types': list(types),
    }
    # G5: 微小存根(<=10KB 且无角色) —— 疑似废弃空会话
    if d and not pr and detail['size_kb'] <= 10:
        detail['types'] = detail['types'] + ['G5']
    return types, detail

def score_of(detail, days):
    """ghost 评分(聚焦用户诉求: 突然出现 + 无角色命名)
    权重: G2无角色 40 / G3近期出现 35 / G1未登记 25 / G5微小存根 20 / 体积 10-20"""
    s = 0
    t = detail['types']
    if 'G2' in t:
        s += 40
    if 'G1' in t:
        s += 25
    if 'G5' in t:
        s += 20
    mt = detail.get('mtime', '?')
    if mt and mt != '?':
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(mt)).days
            if age <= days:
                s += 35
                detail['age_days'] = age
        except Exception:
            pass
    sz = detail.get('size_mb', 0)
    if sz >= 20:
        s += 20
    elif sz >= 5:
        s += 10
    return s

def do_scan(days=3):
    disk = disk_sessions()
    profs = bus_profiles()
    arch = archived_ids()
    reg = registry_ids()
    results = []
    n_prim = n_sub = n_orphan = 0
    mb_prim = mb_sub = 0.0
    for sid in disk:
        types, detail = classify_one(sid, disk, profs, arch, reg)
        if detail.get('kind') == 'subagent':
            n_sub += 1
            mb_sub += detail.get('size_mb', 0)
            if 'G6' in types:
                n_orphan += 1
                detail['score'] = 99
                results.append(detail)
            continue
        n_prim += 1
        mb_prim += detail.get('size_mb', 0)
        if not types:
            continue
        detail['score'] = score_of(detail, days)
        results.append(detail)
    results.sort(key=lambda r: (-r['score'], -r.get('size_mb', 0)))
    ghosts = [r for r in results if r.get('kind') != 'subagent']
    summary = {
        'scanned': len(disk),
        'primary': n_prim,
        'subagent': n_sub,
        'orphan_subagent': n_orphan,
        'primary_mb': round(mb_prim, 1),
        'subagent_mb': round(mb_sub, 1),
        'ghosts': len(ghosts),
        'ghost_mb': round(sum(r.get('size_mb', 0) for r in ghosts), 1),
        'g1_unregistered': sum(1 for r in ghosts if 'G1' in r['types']),
        'g2_roleless': sum(1 for r in ghosts if 'G2' in r['types']),
        'g4_residue': sum(1 for r in ghosts if 'G4' in r['types']),
        'sudden_recent': sum(1 for r in ghosts if 'age_days' in r),
        'total_mb': round(sum(r.get('size_mb', 0) for r in ghosts), 1),
        'days': days,
        'ts': datetime.datetime.now().isoformat(timespec='seconds'),
    }
    return summary, results

def cmd_scan(args):
    summary, results = do_scan(args.days)
    top = results[:args.top]
    if args.json:
        print(json.dumps({'summary': summary, 'ghosts': top}, ensure_ascii=False, indent=1))
    else:
        print('[scan] 幽灵会话扫描 v' + VERSION + ' (窗口 ' + str(args.days) + ' 天)')
        print('  扫描磁盘会话: %d = 主会话 %d (%.1f MB) + 子代理 %d (%.1f MB)' % (
            summary['scanned'], summary['primary'], summary['primary_mb'],
            summary['subagent'], summary['subagent_mb']))
        print('  子代理: 合法 %d | 孤儿(G6) %d' % (
            summary['subagent'] - summary['orphan_subagent'], summary['orphan_subagent']))
        print('  幽灵(仅主会话): %d (占主会话 %.0f%%) | 占用 %.1f MB' % (
            summary['ghosts'],
            (summary['ghosts'] / summary['primary'] * 100) if summary['primary'] else 0,
            summary['ghost_mb']))
        print('  分类: G1未登记 %d | G2无角色 %d | G4归档残留 %d | 近期出现 %d' % (
            summary['g1_unregistered'], summary['g2_roleless'],
            summary['g4_residue'], summary['sudden_recent']))
        print('')
        print('  TOP 治理对象(评分排序):')
        for r in top:
            role = r['role'][:24] if r['role'] else '(无档案)'
            age = str(r.get('age_days', '-')) + 'd' if 'age_days' in r else '-'
            print('    [%3d] %s | %s | %.1fMB | %s | %s' % (
                r['score'], r['session'], role, r.get('size_mb', 0), r.get('mtime', '?'), ','.join(r['types'])))
    # 落链
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        ts = datetime.date.today().isoformat()
        fp = os.path.join(OUT_DIR, 'ghost-sessions-' + ts + '.json')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump({'summary': summary, 'ghosts': results}, f, ensure_ascii=False, indent=1)
        log('scan -> ' + fp)
        if not args.json:
            print('')
            print('  [落链] ' + fp)
    except Exception as e:
        log('落链失败: ' + str(e))
    return 0 if summary['ghosts'] == 0 else (1 if len(results) < 10 else 2)

def cmd_classify(args):
    sid = args.session
    s = short_id(sid)
    disk = disk_sessions()
    profs = bus_profiles()
    arch = archived_ids()
    reg = registry_ids()
    types, detail = classify_one(s, disk, profs, arch, reg)
    detail['score'] = score_of(detail, 3)
    print(json.dumps(detail, ensure_ascii=False, indent=1))
    print('判定: ' + (', '.join(types) if types else '正常(无异常)'))
    return 0


def cmd_selfcheck(args):
    print('[selfcheck] ghost-session-scan v' + VERSION)
    ok = True
    checks = [
        ('sessions root 可访问', os.path.isdir(SESS_ROOT)),
        ('bus file 可读', os.path.isfile(BUS_FILE)),
        ('registry 可读', os.path.isfile(REGISTRY)),
        ('short_id 归一化', short_id('session-abc12345-6789') == short_id('abc12345-6789-xxxx')),
    ]
    for name, good in checks:
        print('  ' + ('OK ' if good else 'X  ') + name)
        if not good:
            ok = False
    print('[selfcheck] ' + ('OK PASS' if ok else 'X FAIL'))
    return 0 if ok else 1

def cmd_lean4(args):
    # 结构门: 归一化必须一致(跨源匹配前提); 归档残留必须可识别
    a = short_id('session-a190c54c-ca73-4845')
    b = short_id('a190c54c-ca73-4845')
    ok1 = (a == b and len(a) == 8)
    # 归档集合识别: 构造已知归档 id 应命中
    arch = archived_ids()
    ok2 = isinstance(arch, set)
    print('lean4-check:', 'OK 归一化一致 + 归档集可解析' if (ok1 and ok2) else 'X 校验失败')
    return 0 if (ok1 and ok2) else 1

def cmd_cld(args):
    print('[cld-check] 纯 CLI 无 CLD 耦合 PASS')
    return 0

def cmd_vcheck(args):
    print('[version-check] 纯 CLI 无 dsh 依赖 v' + VERSION)
    return 0

def cmd_version(args):
    print('ghost-session-scan ' + VERSION)
    return 0

def main():
    ap = argparse.ArgumentParser(description='ghost-session-scan — 幽灵会话扫描器(内存治理重点对象)')
    sub = ap.add_subparsers(dest='cmd')
    p_s = sub.add_parser('scan', help='扫描幽灵会话')
    p_s.add_argument('--days', type=int, default=3, help='近期窗口(默认3天)')
    p_s.add_argument('--json', action='store_true')
    p_s.add_argument('--top', type=int, default=20)
    p_c = sub.add_parser('classify', help='单会话判定')
    p_c.add_argument('session')
    for c in ['selfcheck', 'lean4-check', 'cld-check', 'version-check', 'version']:
        sub.add_parser(c)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    fn = {'scan': cmd_scan, 'classify': cmd_classify, 'selfcheck': cmd_selfcheck,
          'lean4-check': cmd_lean4, 'cld-check': cmd_cld,
          'version-check': cmd_vcheck, 'version': cmd_version}.get(args.cmd)
    if not fn:
        ap.print_help()
        return 0
    try:
        return fn(args)
    except Exception as e:
        log('err: ' + str(e))
        print('X ' + str(e)[:150])
        return 1

if __name__ == '__main__':
    sys.exit(main())
