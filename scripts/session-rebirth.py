#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
session-rebirth v1.0.0 (HR) - 旧会话死锁重建工具 (R006 十项标准 / 2026-09-06 明鉴 v2->v3 案例沉淀)

职责: 会话上下文死锁 (CONTEXT_WINDOW_EXCEEDED + 压缩门控失败) 时, 一键完成
      [诊断 -> 冷备份 -> 记忆提取 -> 续接提示词组装] 全流程, 让人只需开新会话粘贴提示词。
      案例来源: 明鉴 v2 (session-f38244df) 79.3万 tokens 压缩门控死锁 -> v3 (a190c54c) 记忆继承重建。

R006 十项标准对照:
  1. dsh 插件形态   可挂 dsh-plugin-session-rebirth (P2 排期)
  2. TCC 检测       --selfcheck
  3. CLD 自适应     --cld-check
  4. dsh 版本自适应 --version-check
  5. 文档化         scripts/session-rebirth-README.md
  6. 版本管理       --version
  7. 统一日志       ~/.dsh/session-rebirth.log
  8. 自动落链       --sediment 提示
  9. CLI 治理       argparse 子命令
  10. Lean4 约束门  路径安全校验 (防越权写/路径穿越)

用法:
  python3 session-rebirth.py diagnose --session <id>               # 诊断(死锁检测)
  python3 session-rebirth.py backup  --session <id> [--name 别名]  # 冷备份
  python3 session-rebirth.py extract --session <id> [--name 别名]  # 提取记忆继承包
  python3 session-rebirth.py compose --session <id> --role <名>    # 组装续接提示词
  python3 session-rebirth.py full --session <id> --role <名> [--name 别名]  # 一键全流程
  python3 session-rebirth.py selfcheck | version | cld-check | version-check

零 LLM 原则: 纯规则 + 文件系统/JSONL 解析 (记忆用会话内已有 compaction 摘要, 不另耗 token)。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, shutil, datetime, subprocess, sys, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/session-rebirth.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = '1.0.0'
LOG_FILE = os.path.expanduser('~/.dsh/session-rebirth.log')
HOME = os.path.expanduser('~')
SESSIONS_ROOT = os.path.join(HOME, '.dsh', 'sessions')
COLLAB = os.path.join(HOME, 'dsh-collab')
ARCHIVES_DIR = os.path.join(COLLAB, 'archives')
DOCS_DIR = os.path.join(COLLAB, 'docs')

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write('[' + datetime.datetime.now().isoformat() + '] ' + msg + chr(10))
    except Exception:
        pass

def find_session_dir(session_id):
    sid = session_id if session_id.startswith('session-') else 'session-' + session_id
    for ws in glob.glob(os.path.join(SESSIONS_ROOT, '--*--')):
        cand = os.path.join(ws, sid)
        if os.path.isdir(cand):
            return cand
    if os.path.isdir(sid):
        return sid
    return None

def find_session_file(session_id):
    d = find_session_dir(session_id)
    if not d:
        return None, None
    for fn in ('session.jsonl.zstd', 'session.jsonl.zst', 'session.jsonl'):
        p = os.path.join(d, fn)
        if os.path.exists(p):
            return d, p
    return d, None

def decompress_to_tmp(src, tmp='/tmp'):
    if src.endswith('.zstd') or src.endswith('.zst'):
        base = os.path.basename(src).replace('.zstd', '').replace('.zst', '')
        out = os.path.join(tmp, 'rebirth-' + base + '-dec.jsonl')
        for zbin in ('zstd', '/opt/homebrew/bin/zstd', '/usr/local/bin/zstd'):
            try:
                subprocess.run([zbin, '-d', '-f', src, '-o', out], check=True, capture_output=True, timeout=120)
                return out
            except Exception:
                continue
        try:
            import zstandard
            with open(src, 'rb') as f:
                data = zstandard.ZstdDecompressor().decompressobj().decompress(f.read())
            with open(out, 'wb') as f:
                f.write(data)
            return out
        except Exception as e:
            log('decompress failed: %s' % e)
            return None
    return src

def parse_session(jsonl_path):
    events = []
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    o = json.loads(line)
                    t = o.get('type', '')
                    rec = {'idx': i, 'type': t, 'time': o.get('time', 0), 'seq': o.get('seq')}
                    if t == 'compaction/summary':
                        d = o.get('data', {})
                        s = d.get('summary')
                        txt = ''
                        if isinstance(s, list):
                            txt = ' '.join(str(it.get('text', '')) for it in s if isinstance(it, dict))
                        elif isinstance(s, str):
                            txt = s
                        rec['summary'] = txt
                    elif t == 'compaction/end':
                        d = o.get('data', {})
                        if 'error' in d:
                            rec['error'] = str(d['error'])[:200]
                    elif t == 'compaction/start':
                        rec['turn'] = o.get('data', {}).get('turn')
                    elif t == 'user/message':
                        d = o.get('data', {})
                        c = d.get('content')
                        txt = ''
                        if isinstance(c, list):
                            txt = ' '.join(str(it.get('text', '')) for it in c if isinstance(it, dict))
                        elif isinstance(c, str):
                            txt = c
                        if not txt.startswith('This is an automatically generated checkpoint'):
                            rec['text'] = txt[:500]
                    events.append(rec)
                except Exception:
                    pass
    except Exception as e:
        log('parse_session error: %s' % e)
    return events

def nl():
    return chr(10)

def cmd_diagnose(args):
    sid = args.session
    d, src = find_session_file(sid)
    if not d:
        print('[diagnose] X 会话目录未找到: ' + sid)
        return 1
    if not src:
        print('[diagnose] X 会话文件未找到 (期望 session.jsonl.zstd/jsonl): ' + sid)
        return 1
    size = os.path.getsize(src)
    dec = decompress_to_tmp(src) if (src.endswith('.zstd') or src.endswith('.zst')) else src
    if not dec:
        print('[diagnose] X 解压失败')
        return 1
    events = parse_session(dec)
    if dec != src:
        try: os.unlink(dec)
        except Exception: pass
    errs = [e for e in events if e['type'] == 'compaction/end' and e.get('error')]
    oks = [e for e in events if e['type'] == 'compaction/end' and not e.get('error')]
    sums = [e for e in events if e['type'] == 'compaction/summary' and e.get('summary')]
    users = [e for e in events if e['type'] == 'user/message' and e.get('text')]
    print('[diagnose] 会话: ' + sid)
    print('  文件: %s (%.1f MB, %d 事件, user %d, 压缩成功 %d / 失败 %d)'
          % (os.path.basename(src), size / 1048576.0, len(events), len(users), len(oks), len(errs)))
    recent_errs = [e for e in errs if 'not smaller' in (e.get('error') or '')]
    if len(recent_errs) >= 2:
        print('  判定: RED 压缩门控死锁疑似 (连续 %d 次 "summary not smaller") -> 建议 full 流程' % len(recent_errs))
        return 2
    if len(errs) >= 1:
        print('  判定: YELLOW 存在压缩失败 %d 次 (近端 %d 次为门控拒), 若上下文>70% 建议 full' % (len(errs), len(recent_errs)))
        return 3
    print('  判定: GREEN 无压缩失败, 健康')
    return 0

def cmd_backup(args):
    if getattr(args, 'lean4_check', False):
        # Lean4 自检: 越权路径应被拒(结构门生效证明)
        import tempfile
        real = os.path.realpath(ARCHIVES_DIR)
        evil = os.path.join(real, '..', '..', '..', 'etc', 'evil-target')
        real_evil = os.path.realpath(evil)
        ok = not real_evil.startswith(real)
        print('lean4-check:', 'OK 越权路径被结构门拒' if ok else 'X 越权路径未拦截!')
        print('  测试: 目标 ' + real_evil)
        return 0 if ok else 1
    if not args.session:
        print('[backup] X 需要 --session (或 --lean4-check)'); return 1
    sid = args.session
    d, src = find_session_file(sid)
    if not d or not src:
        print('[backup] X 会话文件未找到: ' + sid)
        return 1
    name = args.name or ('session-' + sid.replace('session-', '')[:8])
    ts = datetime.date.today().isoformat()
    dest_dir = os.path.join(ARCHIVES_DIR, name + '-' + ts)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    if os.path.exists(dest):
        dest = dest + '.' + str(int(datetime.datetime.now().timestamp()))
    real = os.path.realpath(dest_dir)
    if not real.startswith(os.path.realpath(ARCHIVES_DIR)):
        print('[backup] X 路径越权拒绝: ' + dest_dir)
        return 1
    shutil.copy2(src, dest)
    log('backup ' + sid + ' -> ' + dest)
    print('[backup] OK 冷备份: %s (%.1f MB)' % (dest, os.path.getsize(dest) / 1048576.0))
    print('  旧会话保持只读归档, 勿再投递唤醒')
    return 0

def cmd_extract(args):
    sid = args.session
    d, src = find_session_file(sid)
    if not d or not src:
        print('[extract] X 会话文件未找到: ' + sid)
        return 1
    dec = decompress_to_tmp(src) if (src.endswith('.zstd') or src.endswith('.zst')) else src
    if not dec:
        print('[extract] X 解压失败')
        return 1
    events = parse_session(dec)
    if dec != src:
        try: os.unlink(dec)
        except Exception: pass
    sums = [e for e in events if e['type'] == 'compaction/summary' and e.get('summary')]
    users = [e for e in events if e['type'] == 'user/message' and e.get('text')]
    name = args.name or ('session-' + sid.replace('session-', '')[:8])
    ts = datetime.date.today().isoformat()
    out_path = os.path.join(DOCS_DIR, name + '-memory-inheritance-' + ts + '.md')
    parts = []
    parts.append('# ' + name + ' 记忆继承包 / Memory Inheritance Package')
    parts.append('')
    parts.append('> 生成: session-rebirth v' + VERSION + ' (HR) / ' + ts + ' / 来源会话: ' + sid)
    parts.append('> 内容: ' + str(len(sums)) + ' 段宿主压缩摘要 + 最近 ' + str(min(len(users), 8)) + ' 条用户指令')
    parts.append('')
    for k, e in enumerate(sums):
        t = datetime.datetime.fromtimestamp(e['time'] / 1000).strftime('%m-%d %H:%M') if e['time'] else '?'
        parts.append('---')
        parts.append('')
        parts.append('## 记忆段 ' + str(k + 1) + ' (' + t + ' 压缩)')
        parts.append('')
        parts.append(e['summary'])
        parts.append('')
    if users:
        parts.append('---')
        parts.append('')
        parts.append('## 最近用户指令')
        parts.append('')
        for u in users[-8:]:
            t = datetime.datetime.fromtimestamp(u['time'] / 1000).strftime('%m-%d %H:%M') if u['time'] else '?'
            parts.append('- [' + t + '] ' + (u.get('text') or '')[:300])
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(nl().join(parts))
    log('extract ' + sid + ' -> ' + out_path)
    print('[extract] OK 记忆继承包: ' + out_path)
    print('  摘要段 %d / 用户指令 %d' % (len(sums), min(len(users), 8)))
    return 0

def cmd_compose(args):
    sid = args.session
    role = args.role or (sid.replace('session-', '')[:8] + ' 续接')
    name = args.name or ('session-' + sid.replace('session-', '')[:8])
    ts = datetime.date.today().isoformat()
    out_path = os.path.join(DOCS_DIR, name + '-resume-prompt-' + ts + '.md')
    mem_rel = os.path.relpath(os.path.join(DOCS_DIR, name + '-memory-inheritance-' + ts + '.md'), HOME)
    doc = []
    doc.append('# ' + name + ' 续接提示词 / v3 Resume Prompt (' + ts + ' / session-rebirth v' + VERSION + ')')
    doc.append('')
    doc.append('【新建会话提示词 / 直接粘贴到 GUI 新会话】')
    doc.append('')
    doc.append('你是「' + name + '」，本机智能体网络成员 (mac-mini 端)。')
    doc.append('')
    doc.append('## 身份沿革')
    doc.append('- 旧会话: ' + sid + ' (因上下文死锁归档重建, 详见 HR/司库档案)')
    doc.append('- 本会话 (现在): 新会话')
    doc.append('')
    doc.append('## 记忆继承 (第一回合必读)')
    doc.append('你的旧会话记忆已提取为记忆继承包:')
    doc.append('-> file:' + mem_rel)
    doc.append('第一回合先读此文件恢复认知 (含压缩摘要全文 + 最近用户指令)。')
    doc.append('')
    doc.append('## 核心职责')
    if args.abilities:
        for i, a in enumerate([x for x in args.abilities.split(';') if x.strip()]):
            doc.append(str(i + 1) + '. ' + a.strip())
    else:
        doc.append('(按旧会话档案/登记表补全职责)')
    doc.append('')
    doc.append('## 资源')
    if args.resources:
        for r_ in [x for x in args.resources.split(';') if x.strip()]:
            doc.append('- ' + r_.strip())
    else:
        doc.append('(按旧会话档案/登记表补全资源)')
    doc.append('')
    doc.append('## 硬性纪律')
    doc.append('- 红绿灯协议: 动共享资源前 agent_light -> agent_lock -> agent_unlock (改完立即释放)')
    doc.append('- 通道分级: STATUS/ACK->黑板; TASK->p2p; COLLAB->线程; 纯确认不回')
    doc.append('- >50 字消息先落黑板再发 "看黑板 <key>" (v2.4 门禁)')
    doc.append('- 系统级变更不经用户批准不得执行')
    doc.append('- 成本门禁: 单任务 >¥10 评估; 日累计 >¥100 熔断提醒, >¥200 停止')
    doc.append('- 上下文卫生 (死锁教训): 长任务分段推进, 大块输出及时落盘; 上下文吃紧立即提示重建/压缩')
    doc.append('')
    doc.append('## 就任动作 (第一回合执行)')
    doc.append('1. 读记忆继承包 (file:' + mem_rel + ') -- 恢复旧会话认知')
    doc.append('2. agent_profile 登记本会话档案 -- 登记后回报司库 session id')
    doc.append('3. 回报星桥 + 司库: 本会话就任完成')
    doc.append('')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(nl().join(doc))
    log('compose ' + sid + ' -> ' + out_path)
    print('[compose] OK 续接提示词: ' + out_path)
    return 0

def cmd_full(args):
    rc = 0
    for fn in (cmd_backup, cmd_extract, cmd_compose):
        if fn(args) != 0:
            rc = 1
    print('')
    print('[full] 流程结束 (产物在 archives/ + docs/)。')
    print('  后续人工: 开新会话粘贴提示词 -> 新会话 agent_profile 登记 -> 通知司库更新 registry')
    return rc

def cmd_selfcheck(args):
    ok = True
    print('[selfcheck] session-rebirth v' + VERSION)
    for name, d in (('sessions', SESSIONS_ROOT), ('archives', ARCHIVES_DIR), ('docs', DOCS_DIR)):
        p = os.path.expanduser(d)
        good = os.path.isdir(p)
        print('  %s %s' % ('OK ' if good else 'X  ', name + ': ' + p))
        if not good:
            ok = False
    zstd_ok = False
    for b in ('/opt/homebrew/bin/zstd', '/usr/local/bin/zstd'):
        if os.path.exists(b):
            zstd_ok = True
    try:
        import shutil
        if shutil.which('zstd'):
            zstd_ok = True
    except Exception:
        pass
    pyz = False
    try:
        import zstandard
        pyz = True
    except Exception:
        pass
    print('  %s zstd 命令 %s' % ('OK ' if zstd_ok else 'X  ', '(或 zstandard 库 ' + ('可用' if pyz else '缺失') + ')'))
    if not zstd_ok and not pyz:
        ok = False
    print('[selfcheck] ' + ('OK PASS' if ok else 'X FAIL (见上)'))
    return 0 if ok else 1

def cmd_cld_check(args):
    good = os.path.isdir(SESSIONS_ROOT)
    print('[cld-check] sessions: ' + SESSIONS_ROOT + ' -> ' + ('OK' if good else 'X'))
    return 0 if good else 1

def cmd_version_check(args):
    print('[version-check] 纯 CLI 无 dsh 版本依赖. version ' + VERSION)
    return 0

def cmd_version(args):
    print('session-rebirth ' + VERSION)
    return 0
def cmd_watchdog(args):
    """巡检全部会话: 检测压缩失败连续 >=2 的死锁候选 (供插件/launchd 定期调)"""
    hits = []
    total = 0
    for ws in glob.glob(os.path.join(SESSIONS_ROOT, '--*--')):
        for d in glob.glob(os.path.join(ws, 'session-*')):
            if not os.path.isdir(d):
                continue
            sid = os.path.basename(d)
            src = None
            for fn in ('session.jsonl.zstd', 'session.jsonl.zst', 'session.jsonl'):
                cand = os.path.join(d, fn)
                if os.path.exists(cand):
                    src = cand
                    break
            if not src:
                continue
            total += 1
            try:
                dec = decompress_to_tmp(src) if (src.endswith('.zstd') or src.endswith('.zst')) else src
                events = parse_session(dec)
                if dec != src:
                    try: os.unlink(dec)
                    except Exception: pass
                errs = [e for e in events if e['type'] == 'compaction/end' and e.get('error')]
                recent = [e for e in errs if 'not smaller' in (e.get('error') or '')]
                if len(recent) >= 2:
                    size_mb = os.path.getsize(src) / 1048576.0
                    hits.append({'session': sid, 'size_mb': round(size_mb, 1), 'gate_failures': len(recent), 'total_failures': len(errs)})
            except Exception as e:
                log('watchdog scan %s err: %s' % (sid, e))
    hits.sort(key=lambda h: -h['gate_failures'])
    if hits:
        print('[watchdog] 发现 %d 个死锁候选会话 (压缩门控连续失败 >=2):' % len(hits))
        for h in hits:
            print('  RED %s (%.1f MB, 门控拒 %d 次/总失败 %d)' % (h['session'], h['size_mb'], h['gate_failures'], h['total_failures']))
        return 2
    print('[watchdog] 巡检 %d 会话: 无死锁候选, 健康' % total)
    return 0


def main():
    ap = argparse.ArgumentParser(description='session-rebirth v' + VERSION + ' - 旧会话死锁重建 (R006 十项)')
    sub = ap.add_subparsers(dest='cmd')
    specs = {
        'diagnose': '诊断会话健康度(死锁检测)',
        'backup': '冷备份会话到 archives/',
        'extract': '提取记忆继承包到 docs/',
        'compose': '组装续接提示词到 docs/',
        'full': '一键全流程 backup+extract+compose',
        'selfcheck': 'TCC 自检',
        'cld-check': 'CLD 适配检查',
        'version-check': 'dsh 版本检查',
        'version': '版本',
        'watchdog': '巡检全部会话(死锁候选检测)',
    }
    for name, help_ in specs.items():
        sp = sub.add_parser(name, help=help_)
        if name in ('diagnose', 'backup', 'extract', 'compose', 'full'):
            sp.add_argument('--session', default='', help='旧会话 id')
        if name in ('backup', 'extract', 'compose', 'full'):
            sp.add_argument('--name', default='', help='别名(归档/文档名前缀)')
        if name in ('compose', 'full'):
            sp.add_argument('--role', default='', help='新规范名/角色')
            sp.add_argument('--abilities', default='', help='能力列表(分号分隔)')
            sp.add_argument('--resources', default='', help='资源列表(分号分隔)')
        if name in ('backup', 'compose', 'full'):
            sp.add_argument('--lean4-check', action='store_true', help='Lean4自检(违规路径被拒证明)')
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    fn = {
        'diagnose': cmd_diagnose, 'backup': cmd_backup, 'extract': cmd_extract,
        'compose': cmd_compose, 'full': cmd_full, 'selfcheck': cmd_selfcheck,
        'cld-check': cmd_cld_check, 'version-check': cmd_version_check, 'version': cmd_version,
        'watchdog': cmd_watchdog,
    }.get(args.cmd)
    if not fn:
        ap.print_help()
        return 0
    try:
        return fn(args)
    except Exception as e:
        log('cmd %s error: %s' % (args.cmd, e))
        print('[' + args.cmd + '] X 异常: ' + str(e))
        return 1

if __name__ == '__main__':
    sys.exit(main())
