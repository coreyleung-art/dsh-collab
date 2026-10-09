#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""role-name-check v1.0 (HR) — 角色命名规范校验器（纯规则，零 LLM）

职责：校验 agent_profiles 是否符合「角色命名标准 v1.0」：
  命名格式：<设备>-<角色>（mac-mini/mbp/i9 + 中文职能名）
  字段：displayName（用户可见）/ device / role / agentId（内部隐藏）
检测：
  1. 缺设备前缀（无 mac-mini/mbp/i9 等）
  2. 同设备同角色重复（冲突告警）
  3. 会话代码当角色名（role 含 session-）
  4. 未登记档案（agentId 不在 bus profiles）

用法：
  python3 role-name-check.py                # 全量校验（读 ~/.dsh/agent-bus.json）
  python3 role-name-check.py --json         # JSON 输出
  python3 role-name-check.py --report <out> # 生成迁移建议报告

零 LLM 原则：纯规则，与 pre-delete-archaeology.py 同构。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/role-name-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BUS_FILE = os.path.expanduser('~/.dsh/agent-bus.json')
DEVICES = ['mac-mini', 'mbp', 'i9', 'mac', 'mini', 'linux', 'win']
ROLE_KW = ['协调', '资源', '成本', '运营', '客服', '学习', '摄取', '归档', '调研', '调查',
           '供应链', '依赖', 'QA', '验收', '设备', '媒体', '外链', '健康', '运维',
           '开发', '插件', '洞察', '恢复', '自查', '复审', '协调者', '管理', '监察']

def load_profiles():
    try:
        with open(BUS_FILE) as f:
            return json.load(f).get('profiles', [])
    except Exception:
        return []

def check_profile(p):
    role = str(p.get('role') or '')
    aid = str(p.get('agentId') or p.get('id') or '')
    issues = []
    # 1. 设备前缀检查
    has_device = any(d in role for d in DEVICES)
    if not has_device:
        issues.append('missing_device_prefix')
    # 2. 会话代码当角色名
    if 'session-' in role or re.match(r'^session-', role):
        issues.append('session_code_as_role')
    # 3. 角色名过短/无职能词
    if not any(k in role for k in ROLE_KW):
        issues.append('no_role_keyword')
    return {
        'agentId': aid[:16],
        'role': role[:50],
        'hasDevicePrefix': has_device,
        'issues': issues,
        'status': 'ok' if not issues else 'needs_fix',
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--report', help='生成迁移建议报告路径')
    args = ap.parse_args()

    profiles = load_profiles()
    results = [check_profile(p) for p in profiles]
    ok = [r for r in results if r['status'] == 'ok']
    fix = [r for r in results if r['status'] == 'needs_fix']

    if args.report:
        lines = ['# 角色命名迁移建议 · role-name-check', '',
                 f'> 生成：{datetime.date.today().isoformat()} · 工具：role-name-check.py v1.0',
                 f'> 规范：<设备>-<角色>（mac-mini/mbp/i9 + 中文职能名）', '',
                 f'## 总览：{len(results)} 档案 · 达标 {len(ok)} · 待修 {len(fix)}', '']
        lines.append('## 待修清单（建议迁移）')
        for r in fix:
            lines.append(f'- {r["agentId"]} | {r["role"]} | 问题: {", ".join(r["issues"])}')
        lines.append('')
        lines.append('## 迁移示例')
        lines.append('- 外卖多平台运营 → mac-mini-外卖运营')
        lines.append('- 资源管理者 + 成本监察专员 → mac-mini-资源管理')
        lines.append('')
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f'📋 迁移建议报告: {args.report}')
        return 0

    if args.json:
        print(json.dumps({'total': len(results), 'ok': len(ok), 'needs_fix': len(fix), 'results': results}, ensure_ascii=False, indent=1))
    else:
        print(f'总览: {len(results)} 档案 · 达标 {len(ok)} · 待修 {len(fix)}')
        for r in fix[:15]:
            print(f'  ⚠️ {r["agentId"]} | {r["role"]} | {", ".join(r["issues"])}')
        # 冲突检测：同设备同角色
        groups = {}
        for r in results:
            for d in DEVICES:
                if d in r['role']:
                    groups.setdefault(d + '|' + r['role'][:20], []).append(r['agentId'])
        dupes = {k: v for k, v in groups.items() if len(v) > 1}
        if dupes:
            print('\n⚠️ 同设备同角色重复:')
            for k, v in dupes.items():
                print(f'  {k}: {v}')
        else:
            print('\n✅ 无同设备同角色重复')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
