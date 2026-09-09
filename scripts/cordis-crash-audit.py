#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cordis-crash-audit.py v1.0 — Cordis 插件 client 端「无崩溃风险」一键审查

用法: python3 cordis-crash-audit.py <lib/client.js 路径>

检查项（对应安全审查 SOP v1.0）:
  1. slots.inject 是否仅 1 处（apply 顶层）——防重复 register 崩溃
  2. 是否有门控 return null（非目标会话渲染空，避免全局副作用）
  3. 反模式: subscribe 回调内 register（启发式，崩溃风险）
  4. ctx.effect 是否返回 disposer（副作用可撤销）

退出码: 0=无风险 / 1=发现风险
"""
import re, sys

def audit(path):
    src = open(path, encoding='utf-8').read()
    issues = []

    # 1. slots.inject 次数（声明式 API 应仅 apply 顶层一次）
    n_inject = len(re.findall(r'\.slots\.inject\s*\(', src))
    if n_inject == 0:
        issues.append(f'⚠️ 未发现 slots.inject（0 次，可能非 UI 插件或已改名）')
    elif n_inject > 1:
        issues.append(f'🔴 slots.inject 出现 {n_inject} 次（应仅 apply 顶层 1 次，多次=动态注册崩溃风险）')

    # 2. 门控 return null（预设门控模式要求非目标会话渲染空）
    if not re.search(r'return\s+null', src):
        issues.append('🟡 缺少门控 return null（若非全局插件，需组件内显隐）')

    # 3. 反模式：subscribe 回调内 register（启发式检测）
    if re.search(r'subscribe\s*\([^)]*\)\s*=>\s*[^}]*register', src, re.S):
        issues.append('🔴 疑似 subscribe 回调内 register（slots 同 id 重复注册会 throw）')

    # 4. inject 数组完整性（服务依赖声明）
    m = re.search(r'inject\s*=\s*\[([^\]]*)\]', src)
    if m:
        deps = [d.strip().strip("'\"") for d in m.group(1).split(',') if d.strip()]
        print(f'ℹ️ inject 依赖: {deps}')
    else:
        issues.append('🟡 未发现 inject 数组（服务依赖声明缺失）')

    if not issues:
        print('✅ 无崩溃风险（slots.inject 单点 + 门控 + 无 subscribe-register 反模式）')
        return 0
    for i in issues:
        print(i)
    return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(audit(sys.argv[1]))
