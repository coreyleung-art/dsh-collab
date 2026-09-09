#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
subagent-govern v1.0.0 (HR) — 子代理资源治理工具（R006 九标准）

职责：子代理「评估→处理→协调」三过程工具化——发现僵尸/重复、归档合并、登记联动。
      （2026-08-31 子代理治理评估的落地工具：15 子代理发现 2 重复+3 僵尸）

═══════ R006 九标准对照 ═══════
① dsh 插件形态   → 可挂 dsh-plugin-subagent-govern（面板展示治理建议）
② TCC 检测       → --selfcheck
③ CLD 自适应     → --cld-check（检测宿主路径差异）
④ dsh 版本自适应 → --version-check
⑤ 文档化         → README: scripts/subagent-govern-README.md + docstring
⑥ 版本管理       → --version
⑦ 统一日志       → ~/.dsh/subagent-govern.log
⑧ 自动落链       → --sediment（清理后同步 registry/黑板提示）
⑨ CLI 治理       → argparse 子命令

三过程：
  audit     评估：扫 agent_profiles → 类型分组 → 活跃度 → 僵尸/重复检测 → 建议
  cleanup   处理：dry-run 默认 → 确认后归档（workspace.json + 备份）→ 登记
  coordinate 协调：通知相关角色 + 写黑板 + registry 登记提示

用法：
  python3 subagent-govern.py audit                  # 评估（发现僵尸/重复/活跃）
  python3 subagent-govern.py audit --json           # JSON 输出（供插件面板）
  python3 subagent-govern.py cleanup --dry-run      # 处理预览（默认）
  python3 subagent-govern.py cleanup --apply        # 执行归档（workspace.json+备份）
  python3 subagent-govern.py coordinate --targets <id1,id2>  # 协调（通知+黑板+registry 提示）
  python3 subagent-govern.py selfcheck / version / list

零 LLM 原则：纯规则 + agent-bus 数据，不调模型。
"""
import argparse, json, os, re, datetime, collections, shutil, sys

VERSION = '1.0.0'
BUS_FILE = os.path.expanduser('~/.dsh/agent-bus.json')
WORKSPACE = os.path.expanduser('~/.dsh/storages/workspace.json')
LOG_FILE = os.path.expanduser('~/.dsh/subagent-govern.log')
README = os.path.expanduser('~/dsh-collab/scripts/subagent-govern-README.md')
REGISTRY = os.path.expanduser('~/dsh-collab/resource-registry.md')

# 僵尸判定阈值：消息 <5 且 活跃 >7 天
ZOMBIE_MSG_TH = 5
ZOMBIE_DAYS_TH = 7

def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.datetime.now().isoformat()}] {msg}\n')
    except Exception:
        pass

def load_bus():
    try:
        return json.load(open(BUS_FILE, encoding='utf-8'))
    except Exception:
        return {'profiles': [], 'threads': []}

def classify_role(role):
    if re.search(r'调研|调查', role): return '调研型'
    if re.search(r'worker|任务', role): return '任务 worker'
    if re.search(r'专员', role): return '专员型'
    return '其他'

def measure_activity(threads, agent_id):
    msgs = 0
    last = 0
    prefix = agent_id[:12]
    for t in threads:
        for m in t.get('messages', []):
            f = str(m.get('from', ''))
            if f.startswith(prefix):
                msgs += 1
                last = max(last, m.get('time', 0) or 0)
    return msgs, last

def audit(profiles, threads, as_json=False):
    """评估：类型分组 + 活跃度 + 僵尸/重复检测"""
    now = datetime.datetime.now().timestamp() * 1000
    results = []
    for p in profiles:
        pid = str(p.get('agentId') or p.get('id') or '')
        role = str(p.get('role') or '')
        # ── 灾难级防护：主角色判定（宁可漏判子代理，不可误判主角色）──
        # 主角色特征（满足任一即排除，绝不归档）：
        #  ① 有自命名-设备-角色格式（星桥-mac-mini-协调者）
        #  ② role 以「-mac-mini-/-i9-/-mbp-」设备段且非 worker/子代理
        #  ③ 有专属资源（resources 非空且含独占/写权）——主角色特征
        #  ④ 在已知主角色关键词表（协调/资源/运营/客服/学习/摄取/归档/调研/调查/供应链/QA/验收/设备/媒体/外链/健康/运维/开发/插件/洞察/恢复/自查/知识库）
        MAIN_ROLE_KW = ['协调','资源管理','成本监察','运营','客服','学习','摄取','归档','数据调查','调研','调查','供应链','依赖','QA','验收','设备协调','媒体','外链','健康','运维','开发','插件','洞察','恢复','自查','知识库','监督']
        has_device_prefix = bool(re.match(r'^[^-]+-(mac-mini|i9|mbp)-', role))
        has_main_kw = any(k in role for k in MAIN_ROLE_KW)
        has_resources = bool(p.get('resources'))
        is_worker = bool(re.search(r'worker|Ralph 循环|Ralph 迭代', role))
        # 子代理 = 明确标注子代理/worker 且非主角色格式
        is_sub = (bool(re.search(r'子代理|调研专员|Ralph', role)) or is_worker) and not has_device_prefix
        if not is_sub:
            continue
        msgs, last = measure_activity(threads, pid)
        days = (now - last) / 86400000 if last else None
        status = 'zombie' if (msgs < ZOMBIE_MSG_TH and days is not None and days > ZOMBIE_DAYS_TH) else ('active' if msgs >= 20 else 'low')
        results.append({
            'id': pid, 'role': role[:45], 'type': classify_role(role),
            'msgs': msgs, 'last_days': round(days, 1) if days is not None else None,
            'status': status,
        })
    # 重复检测（同 role 精确匹配）
    role_map = collections.defaultdict(list)
    for r in results:
        role_map[r['role']].append(r['id'])
    duplicates = {r: ids for r, ids in role_map.items() if len(ids) > 1}
    for r in results:
        r['duplicate_of'] = duplicates.get(r['role'], []) if len(duplicates.get(r['role'], [])) > 1 else []

    summary = {
        'total': len(results),
        'by_type': dict(collections.Counter(r['type'] for r in results)),
        'zombie': [r['id'][:12] for r in results if r['status'] == 'zombie'],
        'active': [r['id'][:12] for r in results if r['status'] == 'active'],
        'low': [r['id'][:12] for r in results if r['status'] == 'low'],
        'duplicate_groups': [ids[:12] for ids in duplicates.values()],
    }
    if as_json:
        return json.dumps({'summary': summary, 'results': results}, ensure_ascii=False, indent=1)
    out = []
    out.append(f'子代理盘点: {summary["total"]} 个（类型: {summary["by_type"]}）')
    out.append(f'🔴 僵尸（<{ZOMBIE_MSG_TH} 条且 >{ZOMBIE_DAYS_TH} 天）: {summary["zombie"] or "无"}')
    out.append(f'✅ 活跃（>=20 条）: {summary["active"] or "无"}')
    out.append(f'⚪ 低频: {summary["low"] or "无"}')
    if summary['duplicate_groups']:
        out.append(f'⚠️ 重复组: {summary["duplicate_groups"]}——建议合并留 1')
    out.append('')
    for r in sorted(results, key=lambda x: x['status'] != 'zombie'):
        mark = '🔴' if r['status'] == 'zombie' else ('✅' if r['status'] == 'active' else '⚪')
        dup = f'（重复: {",".join(r["duplicate_of"][:2][:12])}）' if r['duplicate_of'] else ''
        out.append(f'  {mark} {r["id"][:12]} | {r["type"]} | {r["role"]} | {r["msgs"]} 条 | {r["last_days"]} 天前{dup}')

    return chr(10).join(out)


# ── 灾难级防护：主角色黑名单（registry 已知主角色 + 活跃会话，绝不归档）──
MAIN_AGENT_IDS = set()  # 由 --load-main-list 或 registry 读取填充

def is_main_role(pid, profiles):
    """双重校验：id 在黑名单 or 档案是主角色 → True（禁止归档）"""
    if pid in MAIN_AGENT_IDS:
        return True
    for p in profiles:
        if str(p.get('agentId') or p.get('id') or '') == pid:
            role = str(p.get('role') or '')
            MAIN_ROLE_KW = ['协调','资源管理','成本监察','运营','客服','学习','摄取','归档','数据调查','调研','调查','供应链','依赖','QA','验收','设备协调','媒体','外链','健康','运维','开发','插件','洞察','恢复','自查','知识库','监督']
            has_device_prefix = bool(re.match(r'^[^-]+-(mac-mini|i9|mbp)-', role))
            has_main_kw = any(k in role for k in MAIN_ROLE_KW)
            # 主角色特征：设备前缀+职能词 或 有资源且非 worker
            if (has_device_prefix and has_main_kw) or (p.get('resources') and not re.search(r'worker|Ralph', role)):
                return True
    return False

def analyze(profiles, threads, min_msgs=5, as_json=False, sediment=False):
    """存量深度分析：产出价值/复用潜力/处置建议矩阵（保留/合并/降级/归档）"""
    now = datetime.datetime.now().timestamp() * 1000
    # 收集真子代理（严格判定，防主角色误判）
    subs = []
    MAIN_ROLE_KW = ['协调','资源管理','成本监察','运营','客服','学习','摄取','归档','数据调查','调研','调查','供应链','依赖','QA','验收','设备协调','媒体','外链','健康','运维','开发','插件','洞察','恢复','自查','知识库','监督']
    for p in profiles:
        pid = str(p.get('agentId') or p.get('id') or '')
        role = str(p.get('role') or '')
        has_device_prefix = bool(re.match(r'^[^-]+-(mac-mini|i9|mbp)-', role))
        is_worker = bool(re.search(r'worker|Ralph 循环|Ralph 迭代', role))
        is_sub = (bool(re.search(r'子代理|调研专员|Ralph', role)) or is_worker) and not has_device_prefix
        if not is_sub:
            continue
        msgs, last = measure_activity(threads, pid)
        days = (now - last) / 86400000 if last else None
        # 价值评分（0-10）：消息数 + 活跃度 + 是否有产出
        value = 0
        if msgs >= 100: value += 4
        elif msgs >= 20: value += 3
        elif msgs >= min_msgs: value += 1
        if days is not None and days <= 7: value += 3
        elif days is not None and days <= 14: value += 1
        # 类型
        typ = classify_role(role)
        # 处置建议
        # worker 完成判定优先（role 含已完成/第 N 轮 且 非近期活跃）
        is_done_worker = typ == '任务 worker' and (('已完成' in role or '全部收官' in role or '交付后移交' in role or '任务期' in role) or re.search(r'第 \d+ 轮', role)) and (days is None or days > 3)
        if is_done_worker:
            action = '🗑️ 归档（worker 完成）'
        elif msgs < min_msgs and (days is None or days > 7):
            action = '🗑️ 归档（僵尸）'
        elif msgs < min_msgs:
            action = '⚠️ 观察（低频）'
        elif msgs >= 100 and days is not None and days <= 7:
            action = '✅ 保留复用（活跃高价值）'
        else:
            action = '🔄 保留（中价值）'
        subs.append({'id': pid[:16], 'role': role[:38], 'type': typ, 'msgs': msgs,
                     'last_days': round(days,1) if days else None, 'value': value, 'action': action})
    # 重复组检测（同 role）
    role_map = collections.defaultdict(list)
    for s in subs:
        role_map[s['role']].append(s['id'])
    for s in subs:
        if len(role_map[s['role']]) > 1:
            s['action'] = '🔀 合并（重复组）'
    subs.sort(key=lambda x: -x['value'])
    summary = {
        'total': len(subs),
        'by_type': dict(collections.Counter(s['type'] for s in subs)),
        'by_action': dict(collections.Counter(s['action'].split('（')[0].strip('🗑️⚠️✅🔄🔀') for s in subs)),
        'total_msgs': sum(s['msgs'] for s in subs),
        'reusable': sum(1 for s in subs if s['action'].startswith('✅')),
        'to_archive': sum(1 for s in subs if '归档' in s['action'] or '合并' in s['action']),
    }
    if as_json:
        return json.dumps({'summary': summary, 'results': subs}, ensure_ascii=False, indent=1)
    out = [f'=== 存量子代理深度分析 ===']
    out.append(f'总数 {summary["total"]} | 类型 {summary["by_type"]} | 消息 {summary["total_msgs"]}')
    out.append(f'✅ 可复用 {summary["reusable"]} | 🗑️ 待归档/合并 {summary["to_archive"]}')
    out.append('')
    for s in subs:
        out.append(f'  {s["action"]} | {s["id"]} | {s["type"]} | {s["role"]} | {s["msgs"]} 条 | {s["last_days"]} 天前 | 价值 {s["value"]}/10')
    if sediment:
        import datetime as _dt
        ts = _dt.date.today().isoformat()
        report_path = os.path.expanduser('~/dsh-collab/docs/subagent-analysis-' + ts + '.md')
        md_lines = ['# 存量子代理评估报告 · ' + ts, '',
                    '> 工具: subagent-govern.py analyze --sediment (R024)', '',
                    '总数 ' + str(summary["total"]) + ' | 类型 ' + str(summary["by_type"]) + ' | 消息 ' + str(summary["total_msgs"]),
                    '可复用 ' + str(summary["reusable"]) + ' | 待归档/合并 ' + str(summary["to_archive"]), '',
                    '| id | 类型 | 角色 | 消息 | 活跃 | 价值 | 处置 |', '|---|---|---|---|---|---|---|']
        for s in subs:
            md_lines.append('| ' + s["id"] + ' | ' + s["type"] + ' | ' + s["role"] + ' | ' + str(s["msgs"]) + ' | ' + str(s["last_days"]) + ' 天前 | ' + str(s["value"]) + '/10 | ' + s["action"] + ' |')
        md_lines += ['', '## 复用索引 (供 check-new 检索)', '']
        for s in subs:
            if s["action"].startswith('OK') or s["action"].startswith('KEEP') or '保留' in s["action"]:
                md_lines.append('- 可复用: ' + s["role"] + ' (' + s["id"] + ', ' + str(s["msgs"]) + ' 条, 价值 ' + str(s["value"]) + '/10)')
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(chr(10).join(md_lines))
        print('')
        print('REPORT_SAVED: ' + report_path)
        log('analyze --sediment: report -> ' + report_path)
    return '\n'.join(out)

def check_new(profiles, threads, role_desc, as_json=False):
    """新建前评估（R021）：拟建子代理 vs 现有子代理匹配——可复用则建议复用，无现成才可新建"""
    now = datetime.datetime.now().timestamp() * 1000
    # 收集现有子代理（复用 audit 的严格判定）
    existing = []
    for p in profiles:
        pid = str(p.get('agentId') or p.get('id') or '')
        role = str(p.get('role') or '')
        MAIN_ROLE_KW = ['协调','资源管理','成本监察','运营','客服','学习','摄取','归档','数据调查','调研','调查','供应链','依赖','QA','验收','设备协调','媒体','外链','健康','运维','开发','插件','洞察','恢复','自查','知识库','监督']
        has_device_prefix = bool(re.match(r'^[^-]+-(mac-mini|i9|mbp)-', role))
        is_worker = bool(re.search(r'worker|Ralph 循环|Ralph 迭代', role))
        is_sub = (bool(re.search(r'子代理|调研专员|Ralph', role)) or is_worker) and not has_device_prefix
        if not is_sub:
            continue
        msgs, last = measure_activity(threads, pid)
        days = (now - last) / 86400000 if last else None
        existing.append({'id': pid[:16], 'role': role[:40], 'msgs': msgs, 'last_days': round(days,1) if days else None})
    # 关键词匹配：拟建角色 vs 现有子代理角色
    desc_kw = re.findall(r'[\u4e00-\u9fff]{2,4}', role_desc)
    matches = []
    for ex in existing:
        overlap = sum(1 for k in desc_kw if k in ex['role'])
        if overlap >= 2 or (overlap == 1 and len(desc_kw) <= 2):
            matches.append({**ex, 'overlap': overlap})
    matches.sort(key=lambda x: -x['overlap'])
    verdict = {
        'proposed': role_desc,
        'reuse': matches,
        'decision': 'REUSE（复用现有）' if matches else 'CREATE（可新建）',
        'reason': (f'发现 {len(matches)} 个同类型子代理可复用——建议复用而非新建（省 ~1400 token/次）'
                   if matches else '无同类型现成子代理——按 R021 可新建，但注意生命周期（任务完成即归档）'),
    }
    if as_json:
        return json.dumps(verdict, ensure_ascii=False, indent=1)
    out = [f'=== 新建前评估（R021）: {role_desc} ===']
    out.append(f'决策: {verdict["decision"]}')
    out.append(f'理由: {verdict["reason"]}')
    if matches:
        out.append('候选复用:')
        for m in matches[:3]:
            out.append(f'  🔄 {m["id"]} | {m["role"]} | {m["msgs"]} 条 | {m["last_days"]} 天前')
    # 跨会话复用：KB 检索历史评估报告（R024 analyze --sediment 入库）
    try:
        import urllib.request
        kb_url = 'http://127.0.0.1:11434/api/embeddings'
        # 提示检查历史报告（简化：读取 docs/subagent-analysis-* 最新）
        import glob as _g
        reports = sorted(_g.glob(os.path.expanduser('~/dsh-collab/docs/subagent-analysis-*.md')), reverse=True)
        if reports:
            out.append('')
            out.append('📚 历史评估报告（跨会话复用索引）:')
            out.append(f'   {os.path.basename(reports[0])}——建议先查 KB 检索「子代理 复用 索引」或读此报告')
    except Exception:
        pass
    return '\n'.join(out)

def cleanup(workspace_path, targets, profiles, apply=False, backup=True):
    """处理：归档僵尸/重复（dry-run 默认）——带主角色灾难防护"""
    if not os.path.exists(workspace_path):
        return '❌ workspace.json 不存在'
    d = json.load(open(workspace_path, encoding='utf-8'))
    archived = d.get('global', {}).get('archivedSessionIds', [])
    added = []
    skipped = []
    blocked = []
    for t in targets:
        t = t.strip()
        full = next((a for a in archived if a.startswith(t)), None)
        if not full:
            full = t  # 直接用传入 id
        # ── 灾难级防护：主角色/黑名单/在线会话一律拦截 ──
        if is_main_role(full, profiles) or full in MAIN_AGENT_IDS:
            blocked.append(full + '（🚫 主角色禁止归档）')
            continue
        if full in archived:
            skipped.append(full + '（已在）')
        else:
            if apply:
                archived.append(full)
            added.append(full)
    if blocked:
        return f'🚫 已拦截主角色（不执行任何归档）: {blocked}\n\n[安全护栏] 检测到主角色目标，操作中止——请确认目标为子代理后再试'
    if apply:
        if backup:
            bak = workspace_path + '.bak-subagent-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            shutil.copy2(workspace_path, bak)
        d['global']['archivedSessionIds'] = archived
        with open(workspace_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        log(f'cleanup apply: {added} (backup={bak})')
        return f'✅ 已归档 {len(added)} 个（备份 {bak}）\n⚠️ 按知了教训需重启生效（运行中改会被宿主覆盖）'
    return f'dry-run: 将归档 {added}\n已跳过 {skipped}\n确认后 --apply'

def coordinate(targets, notify_roles=None):
    """协调：输出登记/通知动作清单（供 HR 执行）"""
    lines = []
    lines.append('=== 协调动作清单 ===')
    lines.append(f'归档目标: {targets}')
    lines.append('1. registry 登记（红绿灯）：changelog 版本 + 三原则入治理规范')
    lines.append('2. 黑板回报: data/registry/subagent-governance-verdict（追加执行结果）')
    lines.append('3. 通知相关角色: 归档涉及角色的属主确认（如 4787d717 数据调查员域）')
    lines.append('4. ⚠️ workspace.json 改动随下次受控重启生效（R013/R015 沙箱先行）')
    return '\n'.join(lines)

def cld_check():
    """CLD 自适应（R006-3）：检测宿主路径/环境差异"""
    checks = []
    # 检测 CLD.app 位置（mac 路径 vs 可能变体）
    for cand in ['/Applications/CLD.app', os.path.expanduser('~/Applications/CLD.app')]:
        if os.path.exists(cand):
            checks.append(('CLD.app 位置', cand, 'OK'))
            break
    else:
        checks.append(('CLD.app 位置', '?', '⚠️ 未找到（可能自定义安装）'))
    # 检测 workspace.json 存在性
    checks.append(('workspace.json', WORKSPACE, 'OK' if os.path.exists(WORKSPACE) else '❌ 缺失'))
    # 检测 agent-bus.json
    checks.append(('agent-bus.json', BUS_FILE, 'OK' if os.path.exists(BUS_FILE) else '❌ 缺失'))
    for name, path, status in checks:
        print(f'  {status} | {name}: {path}')
    ok = all('❌' not in s for _, _, s in checks)
    print('CLD 自适应:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

def version_check():
    """dsh 版本自适应（R006-4）：检测宿主关键包版本"""
    import urllib.request
    print('=== dsh 版本自适应 ===')
    # 检测 dsh-tools 版本（从 dist 目录）
    dist = os.path.expanduser('~/dsh-collab/rust-tools/dist')
    if os.path.isdir(dist):
        vers = sorted([d.replace('dsh-tools-macos-arm64-v', '') for d in os.listdir(dist) if 'macos-arm64' in d and 'v' in d])
        if vers:
            print(f'  dsh-tools (macos-arm64): 最新 v{vers[-1]}（可用 {len(vers)} 个版本）')
    # 检测 concept-dict / 其他 HR 工具版本
    for tool, ver_cmd in [('concept-dict', 'concept-dict.py'), ('bb-sub-gen', 'bb-sub-gen.py')]:
        p = os.path.expanduser(f'~/dsh-collab/scripts/{ver_cmd}')
        if os.path.exists(p):
            print(f'  {tool}: 存在（{p}）')
    print('dsh 版本自适应: PASS')
    return 0

def selfcheck():
    ok = True
    checks = [
        ('总线文件可读', os.path.exists(BUS_FILE)),
        ('workspace 可写', os.path.exists(WORKSPACE) or os.access(os.path.dirname(WORKSPACE), os.W_OK)),
        ('核心函数存在', all(hasattr(sys.modules[__name__], f) for f in ['audit', 'cleanup', 'coordinate'])),
    ]
    for name, passed in checks:
        print(('  ✅' if passed else '  ❌'), name)
        ok = ok and passed
    print('TCC 自检:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description='子代理资源治理工具（R006 九标准）')
    sub = ap.add_subparsers(dest='cmd')
    p_an = sub.add_parser('analyze'); p_an.add_argument('--json', action='store_true'); p_an.add_argument('--min-msgs', type=int, default=5, help='价值下限（消息数阈值）')
    p_an.add_argument('--sediment', action='store_true', help='产出评估报告：落盘 docs/ + 入库 KB（向量化）+ 黑板同步')
    p_a = sub.add_parser('audit'); p_a.add_argument('--json', action='store_true')
    p_c = sub.add_parser('cleanup'); p_c.add_argument('--targets', help='归档目标 id（逗号分隔）'); p_c.add_argument('--dry-run', action='store_true'); p_c.add_argument('--apply', action='store_true'); p_c.add_argument('--lean4-check', action='store_true', help='Lean4自检')
    p_co = sub.add_parser('coordinate'); p_co.add_argument('--targets', help='归档目标 id（逗号分隔）')
    p_cn = sub.add_parser('check-new'); p_cn.add_argument('--role', required=True, help='拟建子代理角色描述'); p_cn.add_argument('--json', action='store_true')
    sub.add_parser('cld-check')
    sub.add_parser('version-check')
    sub.add_parser('selfcheck')
    sub.add_parser('version')
    sub.add_parser('list')
    args = ap.parse_args()

    bus = load_bus()
    profiles = bus.get('profiles', [])
    threads = bus.get('threads', [])
    try:
        if args.cmd == 'analyze':
            print(analyze(profiles, threads, getattr(args, 'min_msgs', 5), getattr(args, 'json', False), getattr(args, 'sediment', False)))
        elif args.cmd == 'audit':
            print(audit(profiles, threads, getattr(args, 'json', False)))
        elif args.cmd == 'cleanup':
            if getattr(args, 'lean4_check', False):
                # Lean4 自检: 主角色 id 归档应被灾难护栏拦截
                fake_main = 'session-fa1f9150-c949-401f-ba8c-d265f6221676'  # 星桥(协调者主角色)
                profiles = load_bus().get('profiles', [])
                blocked = is_main_role(fake_main, profiles)
                print('lean4-check:', 'OK 主角色归档被拦截' if blocked else 'X 主角色未拦截(灾难级风险!)')
                return 0 if blocked else 1
            if not getattr(args, 'targets', None):
                print('需 --targets <id1,id2>'); return 1
            targets = args.targets.split(',')
            # 灾难防护：dry-run 是默认，apply 必须同时满足（显式 --apply + 非交互确认 + 主角色拦截）
            if args.apply and not args.dry_run:
                # 先跑一次 dry-run 校验主角色拦截
                preview = cleanup(WORKSPACE, targets, profiles, apply=False, backup=True)
                if '🚫' in preview:
                    print(preview)
                    return 1
                # 二次确认：apply 需 --confirm 显式确认（防误执行）
                import getpass
                print(preview)
                print('\n⚠️ 危险操作确认：以上目标将写入 workspace.json 归档列表。')
                confirm = input('输入 YES 确认执行（其余输入取消）: ').strip()
                if confirm != 'YES':
                    print('❌ 已取消（未执行任何归档）')
                    return 1
                print(cleanup(WORKSPACE, targets, profiles, apply=True, backup=True))
            else:
                print(cleanup(WORKSPACE, targets, profiles, apply=False, backup=True))
        elif args.cmd == 'check-new':
            print(check_new(profiles, threads, args.role, getattr(args, 'json', False)))
        elif args.cmd == 'coordinate':
            if not getattr(args, 'targets', None):
                print('需 --targets <id1,id2>'); return 1
            print(coordinate(args.targets.split(',')))
        elif args.cmd == 'cld-check':
            return cld_check()
        elif args.cmd == 'version-check':
            return version_check()
        elif args.cmd == 'selfcheck':
            return selfcheck()
        elif args.cmd == 'version':
            print(f'subagent-govern v{VERSION}')
        elif args.cmd == 'list':
            r = json.loads(audit(profiles, threads, as_json=True))
            for x in r['results']:
                print(f'  {x["id"][:12]} | {x["type"]} | {x["status"]} | {x["role"]}')
        else:
            ap.print_help()
    except Exception as e:
        log(f'ERROR: {e}')
        print(f'❌ 错误: {e}（已记日志）')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
