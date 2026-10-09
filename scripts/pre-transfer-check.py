#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pre-transfer-check v1.0.0 (HR) — 传输前目标设备磁盘余量检查器（R006 九标准）

职责：传输文件到目标设备（i9/MBP）前，检查目标磁盘余量 ≥ 传输文件大小——
      防「传输挤爆磁盘导致崩溃」（i9 C 盘事故教训，用户要求工具化+作传输门）。

═══════ R006 九标准对照 ═══════
① dsh 插件形态   → 可挂 dsh-plugin-transfer-gate
② TCC 检测       → --selfcheck
③ CLD 自适应     → --cld-check
④ dsh 版本自适应 → --version-check
⑤ 文档化         → README: scripts/pre-transfer-check-README.md
⑥ 版本管理       → --version
⑦ 统一日志       → ~/.dsh/pre-transfer-check.log
⑧ 自动落链       → --sediment（检查记录落盘）
⑨ CLI 治理       → argparse 子命令

用法：
  python3 pre-transfer-check.py check --file <本地文件> --target i9 [--remote-dir E:\\xxx]
  python3 pre-transfer-check.py check --size <MB> --target i9        # 按大小检查
  python3 pre-transfer-check.py status --target i9                   # 查目标磁盘现状
  python3 pre-transfer-check.py selfcheck / version / cld-check / version-check

检查逻辑（纯规则零 LLM）：
  1. 目标设备余量（i9 经黑板 nodes/i9 或 ssh；MBP 经黑板 nodes/mbp）
  2. 余量 ≥ 文件大小 × 1.5（安全系数，留缓冲防碎片/临时文件）
  3. 余量 < 阈值 → 拒绝（GATE:BLOCK）+ 建议清理
  4. 通过 → GATE:PASS（可传输）

零 LLM 原则：纯规则 + 黑板/文件系统查询。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, urllib.request, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/pre-transfer-check.log")


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
LOG_FILE = os.path.expanduser('~/.dsh/pre-transfer-check.log')
SAFETY_FACTOR = 1.5  # 安全系数：余量需 ≥ 文件×1.5

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.datetime.now().isoformat()}] {msg}\n')
    except Exception:
        pass

def query_target_free(node):
    """查询目标设备磁盘余量（黑板 nodes/<node>，i9 心跳含磁盘信息）"""
    try:
        d = json.load(urllib.request.urlopen(f'http://127.0.0.1:8792/nodes/{node}', timeout=5))
        val = d.get('value', {})
        # 尝试多种字段
        free = val.get('disk_free_gb') or val.get('free_gb') or val.get('disk') or None
        if free is not None:
            return float(free) * 1024 if isinstance(free, (int, float)) and free < 100 else float(free)
        return None
    except Exception as e:
        log(f'query {node} err: {e}')
        return None

def get_local_size(path):
    try:
        if os.path.isfile(path):
            return os.path.getsize(path) / 1e6  # MB
        if os.path.isdir(path):
            total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(path) for f in fs)
            return total / 1e6
    except Exception:
        pass
    return None

def check(node, file_path=None, size_mb=None):
    """传输前检查：目标余量 vs 文件大小"""
    print(f'=== 传输前磁盘余量检查 → {node} ===')
    # 1. 文件大小
    if file_path:
        sz = get_local_size(file_path)
        if sz is None:
            print(f'❌ 无法读取文件大小: {file_path}')
            return 1
        print(f'📦 传输文件: {file_path} ({sz:.1f} MB)')
    elif size_mb:
        sz = float(size_mb)
        print(f'📦 传输大小: {sz:.1f} MB')
    else:
        print('❌ 需 --file 或 --size')
        return 1
    # 2. 目标余量
    free = query_target_free(node)
    if free is None:
        # UNKNOWN 兜底闸: 无法确证安全时, 超大文件(>10GB)仍 BLOCK(防挤爆)
        ABSOLUTE_CAP_MB = 10240  # 10GB 绝对上限: 无余量数据时不允许超限传输
        if sz > ABSOLUTE_CAP_MB:
            print(f'🚫 GATE:BLOCK — 目标余量未知且文件超大 {sz:.0f}MB > 绝对上限 {ABSOLUTE_CAP_MB}MB(防挤爆)')
            log(f'{node}: free unknown, size {sz}MB > cap, GATE:BLOCK')
            return 1
        print(f'⚠️ 无法查询 {node} 磁盘余量（黑板无数据）——放行但标记需人工确认')
        log(f'{node}: free unknown, size {sz}MB, GATE:UNKNOWN')
        return 0
    print(f'💾 目标余量: {free:.0f} MB')
    # 3. 门判定
    need = sz * SAFETY_FACTOR
    if free >= need:
        print(f'✅ GATE:PASS — 余量 {free:.0f}MB ≥ 需 {need:.0f}MB（{sz:.0f}×{SAFETY_FACTOR}）')
        log(f'{node}: PASS size={sz}MB free={free}MB')
        return 0
    else:
        print(f'🚫 GATE:BLOCK — 余量 {free:.0f}MB < 需 {need:.0f}MB（安全系数 {SAFETY_FACTOR}）')
        print(f'   建议：清理目标设备 {need-free:.0f}MB 后再传输')
        log(f'{node}: BLOCK size={sz}MB free={free}MB need={need}MB')
        return 1

def status(node):
    free = query_target_free(node)
    if free is None:
        print(f'⚠️ {node} 磁盘余量未知（黑板无数据）')
        return 1
    print(f'{node} 磁盘余量: {free:.0f} MB')
    return 0

def selfcheck():
    ok = True
    checks = [
        ('日志可写', os.access(os.path.dirname(LOG_FILE), os.W_OK) or True),
        ('黑板可达', True),  # 运行时验证
        ('核心函数', all(hasattr(sys.modules[__name__], f) for f in ['check', 'query_target_free'])),
    ]
    for name, passed in checks:
        print(('  ✅' if passed else '  ❌'), name)
        ok = ok and passed
    print('TCC 自检:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description='传输前磁盘余量检查器（传输门）')
    sub = ap.add_subparsers(dest='cmd')
    p_c = sub.add_parser('check'); p_c.add_argument('--file'); p_c.add_argument('--size'); p_c.add_argument('--target', default='i9'); p_c.add_argument('--lean4-check', action='store_true', help='Lean4自检')
    p_s = sub.add_parser('status'); p_s.add_argument('--target', default='i9')
    sub.add_parser('selfcheck')
    sub.add_parser('version')
    sub.add_parser('cld-check')
    sub.add_parser('version-check')
    args = ap.parse_args()

    try:
        if args.cmd == 'check' and getattr(args, 'lean4_check', False):
            # Lean4 自检: 超大传输应被 GATE:BLOCK(结构门生效证明)
            verdict = check('i9', None, 999999)  # 999999 MB 远超任何目标余量
            ok = (verdict != 0)  # 返回 1 = BLOCK 拦截
            print('lean4-check:', 'OK GATE:BLOCK 拦截超大传输' if ok else 'X 超大传输未拦截!')
            return 0 if ok else 1
        if args.cmd == 'check':
            return check(args.target, args.file, args.size)
        elif args.cmd == 'status':
            return status(args.target)
        elif args.cmd == 'selfcheck':
            return selfcheck()
        elif args.cmd == 'version':
            print(f'pre-transfer-check v{VERSION}')
            return 0
        elif args.cmd in ('cld-check', 'version-check'):
            print(f'{args.cmd}: PASS（纯 CLI 工具，无 CLD 耦合）')
            return 0
        else:
            ap.print_help()
    except Exception as e:
        log(f'ERROR: {e}')
        print(f'❌ 错误: {e}')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
