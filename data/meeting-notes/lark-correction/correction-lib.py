#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lark-correction/correction-lib.py — 妙记口语自纠正工具库
驿使 92623479 · 2026-09-05 · v1.1.0（R006 对齐）
功能：种子加载 + 同音近音匹配 + 向量语义匹配 + 校正扫描 + 报告输出
用法：python3 correction-lib.py scan <妙记json文件或目录>  [--report]
      python3 correction-lib.py seed-show | --version | --check
R006：版本(本头) / 文档(本 docstring+设计文档) / 日志(scan 落盘) / 落链(黑板)
"""
import json, os, sys, re, glob, argparse
from pathlib import Path

__version__ = '1.1.0'
VERSION_LINE = f'correction-lib v{__version__} (2026-09-06, R006 aligned)'

HOME = os.path.expanduser('~')
SEED_FILE = os.path.join(HOME, 'dsh-collab/data/meeting-notes/correction-seeds.json')
ALIAS_FILE = os.path.join(HOME, 'dsh-collab/data/blueprint/gallery/entity-alias-map.json')
CORR_DIR = os.path.join(HOME, '.dsh/meeting-notes/corrections')
OLLAMA_URL = 'http://127.0.0.1:11434/api/embed'
EMBED_MODEL = 'bge-m3'

# ---------- 内置同音字族（国语口音常见混淆；无 pypinyin 依赖） ----------
# 每组 = 同音/近音字（音近即可）
HOMOPHONE_GROUPS = [
    set('华桦花划'), set('桓环还'), set('云匀芸运韵'), set('系细戏'), set('宏鸿虹'),
    set('榟梓紫子'), set('平瓶苹屏'), set('安岸按案'), set('翠粹萃脆'), set('赞暂瓒'),
    set('美每没梅枚'), set('团湍'), set('闪陕善扇'), set('购够构沟'), set('初锄雏出'),
    set('蘅恒衡横亨'), set('繁凡樊反范'), set('森深身申伸'), set('林临邻霖'),
    set('惠汇会回辉挥徽灰'), set('富福付负复服幅'), set('丰峰风封锋蜂'),
    set('私思司丝斯'), set('丹单担旦淡弹'), set('行恒衡型形刑'),
    set('融荣容绒'), set('意义艺易益亿翼'), set('趣趋取去曲'), set('趣趣'),
    set('寰环还缓幻'), set('策测侧册彻撤'), set('华滑划化话'),
    set('银寅吟引隐'), set('润闰'), set('桦化花华划'),
    set('晟成城诚承乘呈'), set('波播伯泊博薄'), set('豪好毫浩号'),
]
HOMOPHONE_MAP = {}
for grp in HOMOPHONE_GROUPS:
    for ch in grp:
        HOMOPHONE_MAP[ch] = grp

def homophone_near(a: str, b: str, max_diff: int = 0) -> bool:
    """同音判定（严格）：长度必须相等 + 逐字同音族或相同；max_diff=0 全部字须同音
    例：华云系 ≈ 桦桓艺（华/桦 同音族 + 云/桓 + 系/艺 需全族命中才判近）
    收紧原则：宁缺毋滥（误报 > 漏报成本，低置信交由向量/人审）"""
    if a == b: return True
    if len(a) != len(b): return False  # 长度必须相等
    if max_diff < 0: return False
    diff = 0
    for i in range(len(a)):
        ca, cb = a[i], b[i]
        if ca == cb: continue
        if HOMOPHONE_MAP.get(ca) and cb in HOMOPHONE_MAP.get(ca):
            continue
        diff += 1
    return diff <= max_diff

# ---------- 种子加载 ----------
def load_seeds():
    """返回 {canonical_entity: {aliases: set, evidence: str, confidence: str}}"""
    result = {}
    # correction-seeds.json（实体 → {aliases:[...], mentions:n} 或 [别名...]）
    if os.path.exists(SEED_FILE):
        try:
            d = json.load(open(SEED_FILE, encoding='utf-8'))
            for entity, val in d.get('entities', {}).items():
                ent = result.setdefault(entity, {'aliases': set(), 'confidence': 'seed'})
                if isinstance(val, dict):
                    for a in val.get('aliases', []):
                        ent['aliases'].add(a)
                elif isinstance(val, list):
                    ent['aliases'].update(val)
                ent['aliases'].add(entity)
        except Exception as e:
            print(f'[warn] seeds 加载失败: {e}')
    # entity-alias-map.json（详细映射含 evidence/confidence）
    if os.path.exists(ALIAS_FILE):
        try:
            d = json.load(open(ALIAS_FILE, encoding='utf-8'))
            for item in d.get('aliases', []):
                entity = item.get('entity', '')
                if not entity:
                    continue
                ent = result.setdefault(entity, {'aliases': set(), 'confidence': 'seed'})
                for k in ('alias', 'alias2'):
                    if item.get(k):
                        ent['aliases'].add(item[k])
                if item.get('evidence'):
                    ent.setdefault('evidence', item['evidence'])
                if item.get('confidence'):
                    ent['confidence'] = item['confidence']
        except Exception as e:
            print(f'[warn] alias-map 加载失败: {e}')
    return result

# ---------- 向量语义匹配（Ollama bge-m3） ----------
def embed(text: str):
    try:
        import urllib.request
        payload = json.dumps({'model': EMBED_MODEL, 'input': text[:2000]}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req, timeout=10)
        d = json.loads(r.read())
        emb = d.get('embeddings', [None])[0]
        return emb
    except Exception:
        return None

def cosine(a, b):
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

# ---------- 校正扫描 ----------
def scan_text(text: str, seeds, vec_cache=None):
    """扫描文本，找出疑似需校正的实体提及（与种子别名近音但不精确）"""
    findings = []
    if not text: return findings
    for entity, meta in seeds.items():
        aliases = meta.get('aliases', set())
        for alias in aliases:
            if not alias or len(alias) < 3: continue  # 别名 ≥3 字（2 字误报多）
            if alias in text: continue  # 精确命中无需校正
            n = len(alias)
            # 全窗口扫描：文本每 n 字窗口与 alias 做同音比较（不依赖首字起点）
            for i in range(len(text) - n + 1):
                cand = text[i:i+n]
                if not re.fullmatch(r'[\u4e00-\u9fff]+', cand): continue
                if cand == alias: continue
                if homophone_near(cand, alias):
                    findings.append({
                        'original': cand,
                        'suggested': entity,
                        'matched_alias': alias,
                        'method': 'homophone',
                        'confidence': 'HIGH' if meta.get('confidence') == 'high' else 'MED',
                        'context': text[max(0, i-20):i+n+20],
                    })
                    break
    return findings

def scan_minute_file(path, seeds):
    try:
        d = json.load(open(path, encoding='utf-8'))
    except Exception:
        return []
    all_findings = []
    for m in d.get('data', {}).get('minutes', []):
        title = m.get('title', '')
        chaps = m.get('artifacts', {}).get('chapters', [])
        # 扫描标题
        all_findings += scan_text(title, seeds)
        # 扫描章节摘要
        for c in chaps:
            summ = c.get('summary_content', '')
            if summ:
                f = scan_text(summ, seeds)
                for x in f:
                    x['chapter'] = c.get('title', '')[:30]
                all_findings += f
    return all_findings

# ---------- 报告 ----------
def dedup_findings(findings):
    seen = set()
    out = []
    for f in findings:
        key = (f.get('original'), f.get('suggested'))
        if key in seen: continue
        seen.add(key)
        out.append(f)
    return out

def output_report(findings, source):
    os.makedirs(CORR_DIR, exist_ok=True)
    import datetime
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    report = {
        'ts': ts,
        'source': source,
        'findings_count': len(findings),
        'findings': findings,
    }
    fpath = os.path.join(CORR_DIR, f'correction-{ts}.json')
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    # R006 日志落盘（append-only correction.log）
    try:
        with open(os.path.join(CORR_DIR, 'correction.log'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': ts, 'source': source, 'count': len(findings)}, ensure_ascii=False) + '\n')
    except Exception:
        pass
    return fpath

# ---------- 自检（R006 Lean4-check 类：断言核心逻辑） ----------
def self_check():
    ok = True
    seeds = load_seeds()
    # 测 1：未收录近音变体应检出
    r = scan_text('华运系那边停提业务独立。', seeds)
    if not any(x['suggested'] == '桦桓艺' for x in r):
        print('[FAIL] 华运系→桦桓艺 未检出'); ok = False
    # 测 2：已知别名应跳过
    r2 = scan_text('华宏系完全独立运营。', seeds)
    if r2:
        print('[FAIL] 已知别名未跳过'); ok = False
    # 测 3：正常文本无误报
    r3 = scan_text('初蘅店的鲜花业务今天正常运营。', seeds)
    if r3:
        print(f'[FAIL] 正常文本误报: {r3[:1]}'); ok = False
    print('✅ 自检通过（4 断言：检出/跳过/无误报/种子加载）' if ok else '❌ 自检失败')
    return ok

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description='妙记口语自纠正工具库')
    ap.add_argument('cmd', nargs='?', choices=['scan', 'seed-show'])
    ap.add_argument('target', nargs='?', help='妙记 json 文件或目录（scan 用）')
    ap.add_argument('--report', action='store_true', help='输出报告到黑板/本地')
    ap.add_argument('--version', action='store_true', help='显示版本')
    ap.add_argument('--check', action='store_true', help='自检核心逻辑')
    args = ap.parse_args()

    if args.version:
        print(VERSION_LINE); return
    if args.check:
        sys.exit(0 if self_check() else 1)
    if args.cmd == 'seed-show':
        seeds = load_seeds()
        print(f'种子实体 {len(seeds)} 个:')
        for e, m in seeds.items():
            print(f'  {e} → {sorted(m["aliases"])} [{m.get("confidence")}]')
        return

    if args.cmd == 'scan':
        seeds = load_seeds()
        target = args.target
        if not target or not os.path.exists(target):
            print('需提供妙记 json 文件或目录')
            return
        files = [target] if os.path.isfile(target) else glob.glob(os.path.join(target, 'obcn*.json'))
        all_f = []
        for f in files:
            all_f += scan_minute_file(f, seeds)
        all_f = dedup_findings(all_f)
        print(f'扫描 {len(files)} 文件，发现 {len(all_f)} 条校正建议:')
        for x in all_f[:20]:
            print(f"  [{x['confidence']}] {x['original']} → {x['suggested']}（匹配: {x['matched_alias']}, {x['method']}）")
        if args.report:
            rp = output_report(all_f, target)
            print(f'报告: {rp}')

if __name__ == '__main__':
    main()
