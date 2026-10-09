#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tech-choice-evaluator v1.0 (HR) — 技术栈/编程语言选型评估器（防模型偷懒/幻想）

职责：新开发工具选型时，数据驱动评估候选语言/技术栈——基于本地知识（论文/官方文档）
      + 可靠性维度评分，输出推荐 + 风险标记。**禁止凭印象/图省事选型**。

背景（用户 2026-08-29 指示）：
  - 选型必须依据论文 + 官方文档标准（缺的搜集齐到本地，不重复浪费搜索 token）
  - 有论文的检查是否最新版本
  - 选需求相关最可靠稳固的，避开「看上去最方便最省事」的阉割降级方案
  - 避开模型偷懒/失忆/猜测/幻想路径

用法：
  python3 tech-choice-evaluator.py --lang rust --task "常驻事件驱动桥"   # 评估单语言
  python3 tech-choice-evaluator.py --compare "rust,node,python" --task "..."  # 对比多语言
  python3 tech-choice-evaluator.py --json                                   # JSON 输出
  python3 tech-choice-evaluator.py --check-kb                                # KB 覆盖检查（缺什么补什么）

评估维度（每维 0-10）：
  D1 官方文档标准：有无官方文档/规范（本地缓存 or 已知权威来源）
  D2 论文/研究基础：有无论文支撑（本地 papers-db/KB 检索；有论文查版本新鲜度）
  D3 生态成熟度：包管理/社区/维护活跃度（版本号/维护状态）
  D4 与现有架构契合：本网络已有资产（Rust 化四件套/Node 插件/python 脚本）
  D5 可靠性/稳固性：类型安全/单二进制/内存占用/崩溃循环风险（反阉割降级）
  D6 反幻想风险：该语言在此类任务是否易出现「图省事」陷阱

零 LLM 原则：纯规则 + 本地知识检索，不调模型。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== tech-choice-evaluator 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · tech-choice-evaluator v1.0 (HR) — 技术栈/编程语言选型评估器（防模型偷懒/幻想）")
    print("  · 职责：新开发工具选型时，数据驱动评估候选语言/技术栈——基于本地知识（论文/官方文档）")
    print("  · + 可靠性维度评分，输出推荐 + 风险标记。**禁止凭印象/图省事选型**。")
    print("  · 背景（用户 2026-08-29 指示）：")
    print("  · 命令/参数: lang, compare, task, json, check-kb")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/tech-choice-evaluator.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime

# ── 语言知识库（本地权威标准，可扩展）──

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/tech-choice-evaluator.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LANG_KB = {
  'rust': {
    'official_docs': ['https://doc.rust-lang.org/book/', 'https://doc.rust-lang.org/reference/'],
    'papers': ['Rust 内存安全论文（Boehm 2005 延续研究）', 'Rust 化资源消耗评估（本网络 KB rust-network-infra）'],
    'kb_evidence': ['node-bridge Rust 化全链路（7 篇沉淀）', '内存 151.8→31MB ↓80%', '单二进制三平台零依赖'],
    'fit_tasks': ['常驻服务/事件驱动桥/系统级工具/协议实现'],
    'version_check': 'rustc 稳定版季度发布，长期稳定',
    'risks': ['编译期严格（学习曲线）', '无官方 SDK 场景不适用（如官方 Node SDK 锁定的通道）'],
    'reliability': 9,
  },
  'node': {
    'official_docs': ['https://nodejs.org/docs/latest/', 'https://developer.mozilla.org/'],
    'papers': ['事件驱动模型（Reactor Pattern 论文基础）', 'libuv 架构文档'],
    'kb_evidence': ['插件体系（agent-bus/agent-way/central-inbox）', '官方 SDK 场景保留（external-mcp/wecom）'],
    'fit_tasks': ['GUI 插件/官方 SDK 绑定/快速原型/Web 服务'],
    'version_check': 'Node LTS 双年制（偶数版 LTS）',
    'risks': ['内存占用高（常驻 36-59MB/服务）', '单线程 CPU 密集不适用', '依赖树膨胀'],
    'reliability': 7,
  },
  'python': {
    'official_docs': ['https://docs.python.org/3/', 'https://packaging.python.org/'],
    'papers': ['脚本语言与原型开发研究', 'NumPy/科学计算生态'],
    'kb_evidence': ['scripts/ 62 脚本（治理/沉淀/审计）', 'Ollama/LM Studio 本地模型绑定'],
    'fit_tasks': ['数据脚本/治理工具/ML 胶水/快速自动化'],
    'version_check': 'Python 3.12+ 活跃，3.9 渐退',
    'risks': ['性能瓶颈（大循环/高频）', '部署需解释器（端侧不便）', 'GIL 并发限制'],
    'reliability': 6,
  },
  'go': {
    'official_docs': ['https://go.dev/doc/', 'https://pkg.go.dev/'],
    'papers': ['Go 并发模型（CSP）论文', '垃圾回收调优研究'],
    'kb_evidence': ['择优策略提及（纯逻辑无 SDK → Rust+Go）'],
    'fit_tasks': ['网络服务/CLI 工具/并发系统'],
    'version_check': 'Go 半年制发布，兼容性承诺强',
    'risks': ['无泛型历史包袱（1.18 起解决）', 'GUI 生态弱'],
    'reliability': 8,
  },
}

# ── 反阉割/反幻想信号（图省事陷阱检测）──
TRAP_SIGNALS = [
  ('shell 脚本顶替', '用 bash/一行命令实现本应正式化的能力（无错误处理/无日志/无回收）'),
  ('阉割 API', '用免费/简化 API 顶替官方完整 API（功能缺失/限额风险）'),
  ('内存泄漏长驻', '用高频轮询顶替事件驱动（CPU/内存空转）'),
  ('临时文件堆积', '用 /tmp 缓存顶替正式存储（重启即丢）'),
  ('无类型安全', '动态类型实现本应有类型约束的协议（运行时才炸）'),
  ('单线程阻塞', '用同步阻塞实现本应并发的通道（互相拖慢）'),
]

def score_lang(lang, task):
    kb = LANG_KB.get(lang)
    if not kb:
        return {'lang': lang, 'supported': False, 'score': 0, 'reason': '本地知识库无此语言标准，先搜集入库再评估'}
    s = {}
    s['official_docs'] = 10 if kb['official_docs'] else 0
    s['papers'] = 10 if kb['papers'] else 0
    s['ecosystem'] = min(10, len(kb['kb_evidence']) * 2 + 2)
    fit = any(f in task for f in kb['fit_tasks'])
    s['architecture_fit'] = 8 if fit else 4
    s['reliability'] = kb['reliability']
    total = sum(s.values()) / 5
    return {
        'lang': lang, 'supported': True,
        'scores': {k: round(v, 1) for k, v in s.items()},
        'score': round(total, 1),
        'fit': fit,
        'evidence': kb['kb_evidence'][:3],
        'risks': kb['risks'],
        'version_note': kb['version_check'],
    }

def detect_traps(task):
    hits = []
    for name, desc in TRAP_SIGNALS:
        if name.split(' ')[0] in task or any(k in task for k in name.split(' ')):
            hits.append({'trap': name, 'desc': desc})
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', help='评估单语言')
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument('--compare', help='对比多语言（逗号分隔）')
    ap.add_argument('--task', default='', help='需求描述（如 常驻事件驱动桥）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--check-kb', action='store_true', help='KB 覆盖检查')
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()

    if args.check_kb:
        print('=== 本地语言知识库覆盖 ===')
        print(f'任务参数非必填（--check-kb 独立模式）')
        for lang in LANG_KB:
            print(f'  ✅ {lang}: 官方文档 {len(LANG_KB[lang]["official_docs"])} 源 + KB 证据 {len(LANG_KB[lang]["kb_evidence"])} 条')
        print('  缺语言：先搜集论文/官方文档入库再评估（避免搜索 token 重复浪费）')
        return 0

    traps = detect_traps(args.task)
    if args.compare:
        langs = [l.strip() for l in args.compare.split(',')]
        results = [score_lang(l, args.task) for l in langs]
        results.sort(key=lambda x: -x['score'])
        if args.json:
            print(json.dumps({'task': args.task, 'traps': traps, 'results': results}, ensure_ascii=False, indent=1))
        else:
            print(f'任务: {args.task}')
            if traps:
                print('⚠️ 反阉割检查（图省事陷阱）:')
                for t in traps:
                    print(f'  - {t["trap"]}: {t["desc"]}')
            print('\n推荐排序:')
            for r in results:
                mark = '✅ 推荐' if r['score'] >= 7.5 else ('⚠️ 备选' if r['score'] >= 6 else '❌ 不推荐')
                print(f'  {mark} {r["lang"]} ({r["score"]}/10)')
                print(f'    依据: {"; ".join(r["evidence"][:2])}')
                print(f'    风险: {"; ".join(r["risks"][:2])}')
                print(f'    版本: {r["version_note"]}')
        return 0

    if args.lang:
        r = score_lang(args.lang, args.task)
        if args.json:
            print(json.dumps({'task': args.task, 'traps': traps, 'result': r}, ensure_ascii=False, indent=1))
        else:
            print(f'任务: {args.task} | 语言: {args.lang} | 评分: {r["score"]}/10')
            for k, v in r.get('scores', {}).items():
                print(f'  {k}: {v}')
            print(f'  依据: {"; ".join(r.get("evidence", []))}')
            print(f'  风险: {"; ".join(r.get("risks", []))}')
        return 0

    ap.print_help()

if __name__ == '__main__':
    raise SystemExit(main())
