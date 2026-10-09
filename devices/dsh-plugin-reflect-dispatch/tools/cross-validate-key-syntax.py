#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cross-validate-key-syntax.py — 两套 key 校验器 × 黑板真实响应 的三列对照
由 dsh-plugin-reflect-dispatch 提供（2026-09-11）。用途：任何"写前校验"工具都可以拿它自检
"校验说 OK 但实际写入被拒"的漏点（即 bb-write 自己要防的 400 伪装陷阱）。
用法：python3 tools/cross-validate-key-syntax.py
"""
import json, os, re, sys, http.client

BBW = os.path.expanduser('~/dsh-collab/scripts/bb-write.py')
MINE = re.compile(r'^[a-z]+(/[A-Za-z0-9._-]+)+$')   # dsh-plugin-reflect-dispatch v1.1.2 口径
KEYS = ['data/reflect/__syn__/ok', 'data', 'data/', 'data//x', 'data/x/', 'data/x/y z',
        'data/x/a:b', 'data/x/a#b', 'data/x/中文', 'Data/x', 'data/X-1/y', 'data/x/a b/c']

def load_bbw():
    import importlib.util
    spec = importlib.util.spec_from_file_location('bbw', BBW)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def board_put(key, server=('127.0.0.1', 8792)):
    try:
        c = http.client.HTTPConnection(*server, timeout=6)
        body = json.dumps({'__syn__': 1}).encode()
        c.request('PUT', '/' + key.lstrip('/'), body,
                  {'Content-Type': 'application/json', 'Content-Length': str(len(body))})
        r = c.getresponse(); st = r.status; r.read(); c.close()
    except Exception as e:
        return 'ERR:' + str(e)[:26]
    if st == 200:   # 只清理真正写进去的
        try:
            c = http.client.HTTPConnection(*server, timeout=6)
            c.request('DELETE', '/' + key.lstrip('/')); r = c.getresponse(); r.read(); c.close()
        except Exception:
            pass
    return st

bbw = load_bbw()
print('%-24s %-10s %-10s %-8s %s' % ('key', 'bb-write', 'mine', 'board', 'verdict'))
gaps = 0
for k in KEYS:
    okb = bbw.validate_key(k)[0]
    okm = bool(MINE.match(k.lstrip('/')))
    st = board_put(k)
    if okb and st != 200:
        v = 'GAP: bb-write 说 OK 但 board=%s' % st; gaps += 1
    elif okm and st != 200:
        v = 'GAP: mine 说 OK 但 board=%s' % st; gaps += 1
    else:
        v = 'ok'
    print('%-24s %-10s %-10s %-8s %s' % (k, 'OK' if okb else 'REJECT', 'OK' if okm else 'REJECT', st, v))
print('\n漏点数 =', gaps, '（0 = 两套校验器都与黑板真实行为一致）')
sys.exit(1 if gaps else 0)
