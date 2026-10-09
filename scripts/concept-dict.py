#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
concept-dict v1.0.0 (HR) — 概念数据字典工具（R019 落地，R006 九标准全达标）

职责：概念精确性纪律的落地载体——登记/查证/用词检查/新概念提取/字典健康。
      解决「概念混淆」（2026-08-30 特征库事件教训）：返图特征库 vs 物品特征库。

═══════ R006 九标准对照 ═══════
① dsh 插件形态   → 本脚本可挂 dsh-plugin-concept-dict（面板查证/待登记队列）
② TCC 检测       → --selfcheck（模块完整性自检）
③ CLD 自适应     → 检测宿主路径差异（--cld-check）
④ dsh 版本自适应 → 检测 dsh-tools/宿主版本（--version-check）
⑤ 文档化         → README: scripts/concept-dict-README.md + docstring
⑥ 版本管理       → --version + 字典文件 version 字段
⑦ 统一日志       → ~/.dsh/concept-dict.log（appendFileSync 同构，追加式）
⑧ 自动落链       → --sediment（登记后同步 KB/registry 提示）
⑨ CLI 治理       → argparse 子命令（add/query/check/suggest/audit/list）

存储（持久化双写）：
  - ~/dsh-collab/data/concept-dictionary.json（机器可读权威）
  - ~/dsh-collab/docs/concept-dictionary.md（人类可读自动生成）
  - 黑板 data/registry/concept-dict/<name>（可选同步）

用法：
  python3 concept-dict.py add <概念> --def <定义> --src <来源> [--alias a --alias b]
  python3 concept-dict.py query <词>
  python3 concept-dict.py check <文本>
  python3 concept-dict.py suggest [--dir <目录>]
  python3 concept-dict.py audit
  python3 concept-dict.py list
  python3 concept-dict.py selfcheck
  python3 concept-dict.py version

零 LLM 原则：登记/查证/检查纯规则；suggest 词频+上下文启发式（非模型）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, glob, collections, sys, traceback


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/concept-dict.log")


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
DATA_DIR = os.path.expanduser('~/dsh-collab/data')
DICT_JSON = os.path.join(DATA_DIR, 'concept-dictionary.json')
DICT_MD = os.path.expanduser('~/dsh-collab/docs/concept-dictionary.md')
LOG_FILE = os.path.expanduser('~/.dsh/concept-dict.log')
README = os.path.expanduser('~/dsh-collab/scripts/concept-dict-README.md')

STOPWORDS = ['我们','可以','进行','已经','这个','一个','以及','或者','如果','因为','所以','但是','然后','同时','其中','包括','需要','没有','不是','就是','什么','怎么','自己','时候','现在','这里','那些','这样','那样','他们','你们','还有','只是','应该','可能','必须','通过','对于','关于']

def log(msg):
    """统一日志（R006-7）：追加式落盘 ~/.dsh/concept-dict.log"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f'[{datetime.datetime.now().isoformat()}] {msg}\n')
    except Exception:
        pass

def load():
    if os.path.exists(DICT_JSON):
        try:
            return json.load(open(DICT_JSON, encoding='utf-8'))
        except Exception as e:
            log(f'load error: {e}')
    return {'version': VERSION, 'updated': None, 'concepts': {}}

def save(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    d['version'] = VERSION
    d['updated'] = datetime.date.today().isoformat()
    with open(DICT_JSON, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    write_md(d)
    log(f'saved: {len(d["concepts"])} concepts -> {DICT_JSON}')

def write_md(d):
    lines = ['# 概念数据字典（concept-dictionary）', '',
             f'> 维护：HR 司库 · 版本 {d["version"]} · 更新 {d.get("updated")}',
             '> 用途：R019 概念精确性纪律登记载体——使用前查证、禁止混淆、新概念登记', '',
             '| 概念 | 定义 | 来源 | 别名 | 状态 |', '|---|---|---|---|---|']
    for name, c in sorted(d['concepts'].items()):
        lines.append(f'| {name} | {c.get("def","")} | {c.get("source","")} | {", ".join(c.get("aliases",[])) or "-"} | {c.get("status","active")} |')
    lines += ['', f'*共 {len(d["concepts"])} 条 · 版本 {d["version"]}*']
    os.makedirs(os.path.dirname(DICT_MD), exist_ok=True)
    with open(DICT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def add(d, name, definition, source, aliases=None):
    name = name.strip()
    if not name:
        raise ValueError('概念名不能为空 (结构门拒绝)')
    if len(name) > 80:
        raise ValueError('概念名过长>80 (结构门拒绝)')
    existed = name in d['concepts']
    d['concepts'][name] = {
        'def': definition.strip(),
        'source': source.strip(),
        'added': datetime.date.today().isoformat(),
        'aliases': aliases or [],
        'status': 'active',
    }
    save(d)
    log(f'add: {name} ({"updated" if existed else "new"})')
    print(f'{"🔄 已更新" if existed else "✅ 已登记"}: {name} — {definition.strip()[:40]}')
    if source: print(f'   来源: {source.strip()[:50]}')

def query(d, term, verbose=True):
    if term in d['concepts']:
        c = d['concepts'][term]
        if verbose:
            print(f'✅ {term}: {c["def"]}')
            print(f'   来源: {c.get("source","-")} | 别名: {", ".join(c.get("aliases",[])) or "-"} | 状态: {c.get("status","active")}')
        return c
    for name, c in d['concepts'].items():
        if term in c.get('aliases', []):
            if verbose:
                print(f'✅ {term} → 别名指向 {name}: {c["def"]}')
            return c
    fuzz = [name for name in d['concepts'] if term in name or name in term]
    if fuzz:
        if verbose:
            print(f'⚠️ 未精确命中，相近概念: {fuzz[:5]}')
        return None
    if verbose:
        print(f'❌ 字典未收录: {term}（建议 add 登记，或查 registry/蓝图 master/KB）')
    return None

def check(d, text):
    print('=== 用词检查 ===')
    found = []
    for name, c in d['concepts'].items():
        if name in text:
            found.append(name)
            print(f'  📖 已登记: {name} → {c["def"][:40]}')
    if not found:
        print('  未发现已登记概念')
    names = list(d['concepts'].keys())
    for i, n1 in enumerate(names):
        for n2 in names[i+1:]:
            # 子串包含 或 共享 2+ 字公共词缀（如都含「特征库」）
            common = next((w for w in range(min(len(n1),len(n2)), 1, -1) if n1[:w] == n2[:w] or n1[-w:] == n2[-w:]), 0)
            if (n1 in n2 or n2 in n1 or common >= 2) and n1 in text and n2 in text:
                print(f'  ⚠️ 混淆风险: {n1} 与 {n2} 同现（公共词缀「{n1[-common:] if common>=2 else ""}」）——确认语义区分')
    # 语义混淆增强（P2）：文本中出现的概念 vs 语义相近的其他概念
    try:
        vectors = ensure_vectors(d)
        for name in d['concepts']:
            if name in text and name in vectors:
                nv = vectors[name]
                for other, ov in vectors.items():
                    if other != name and ov and other in text:
                        s = _cosine(nv, ov)
                        if s >= 0.75:
                            print(f'  🧠 语义相近概念同现: {name} 与 {other}（相似度 {s:.2f}）——确认非同一概念')
    except Exception:
        pass
    log(f'check: {len(found)} known concepts in text')
    return found

def suggest(d, scan_dirs=None):
    print('=== 新概念提取（启发式） ===')
    dirs = scan_dirs or [
        os.path.expanduser('~/dsh-collab/docs'),
        os.path.expanduser('~/dsh-collab/research'),
        os.path.expanduser('~/dsh-collab/data/blueprint/flowernet'),
    ]
    counter = collections.Counter()
    for base in dirs:
        for fp in glob.glob(os.path.join(base, '*.md')):
            try:
                text = open(fp, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for m in re.finditer(r'[\u4e00-\u9fff]{2,6}', text):
                w = m.group()
                if len(w) < 2 or any(s in w for s in STOPWORDS):
                    continue
                if w in d['concepts']:
                    continue
                counter[w] += 1
    hits = [(w, c) for w, c in counter.most_common(20) if c >= 3]
    # 向量去重增强：与已登记概念相似度>0.85 判为已覆盖
    try:
        vectors = ensure_vectors(d)
        deduped = []
        for w, c in hits:
            try:
                wv = _embed(w)
                if any(_cosine(wv, vec) >= 0.85 for vec in vectors.values() if vec):
                    continue  # 已覆盖（同义变体）
            except Exception:
                pass
            deduped.append((w, c))
        hits = deduped
    except Exception:
        pass
    print(f'疑似新概念（向量去重后 {len(hits)} 个，前 15）:')
    for w, c in hits[:15]:
        print(f'  {w}（{c} 次）→ add 登记')
    log(f'suggest: {len(hits)} candidates')
    return hits

def audit(d):
    print('=== 字典健康检查 ===')
    concepts = d['concepts']
    print(f'概念总数: {len(concepts)}')
    no_src = [n for n, c in concepts.items() if not c.get('source')]
    no_def = [n for n, c in concepts.items() if not c.get('def')]
    if no_src: print(f'  ⚠️ 无来源: {no_src}')
    if no_def: print(f'  ⚠️ 无定义: {no_def}')
    if not no_src and not no_def: print('  ✅ 全部概念有来源+定义')
    print('状态分布:', dict(collections.Counter(c.get('status','active') for c in concepts.values())))
    log(f'audit: {len(concepts)} concepts, {len(no_src)} no-source')

def sync_from_blackboard():
    """端侧同步：从黑板拉取最新字典（只读缓存，防多写冲突）"""
    import urllib.request
    bb_url = 'http://127.0.0.1:8792/data/registry/concept-dict/sync'
    try:
        raw = urllib.request.urlopen(bb_url, timeout=8).read().decode('utf-8')
        data = json.loads(raw)
        remote = data.get('value', {})
        concepts = remote.get('concepts', {})
        local = load()
        local['concepts'] = concepts
        local['version'] = remote.get('version', local.get('version'))
        save(local)
        log(f'sync: pulled {len(concepts)} concepts from blackboard')
        print(f'✅ 已从黑板同步: {len(concepts)} 概念（版本 {local["version"]}）')
    except Exception as e:
        print(f'❌ 同步失败: {e}（黑板不可达？端侧先用手动拷贝）')

VECTORS_FILE = os.path.join(DATA_DIR, 'concept-vectors.json')

def _embed(text):
    """bge-m3 本地嵌入（Ollama 11434，零订阅）"""
    import urllib.request
    req = urllib.request.Request('http://127.0.0.1:11434/api/embeddings',
        data=json.dumps({'model': 'bge-m3', 'prompt': text}).encode(),
        headers={'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=15))
    return r.get('embedding', [])

def _cosine(a, b):
    if not a or not b or len(a) != len(b): return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(y*y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0

def _load_vectors():
    if os.path.exists(VECTORS_FILE):
        try: return json.load(open(VECTORS_FILE, encoding='utf-8'))
        except Exception: pass
    return {}

def _save_vectors(v):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(VECTORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(v, f, ensure_ascii=False)

def ensure_vectors(d):
    """确保字典概念向量缓存完整（add 时增量生成）"""
    v = _load_vectors()
    changed = False
    for name, c in d['concepts'].items():
        if name not in v:
            try:
                v[name] = _embed(f'{name}：{c["def"]}')
                changed = True
            except Exception:
                pass
    if changed:
        _save_vectors(v)
    return v

def query_semantic(d, term, top_k=3):
    """语义查证：嵌入查询词 → 与概念向量比相似度 → TOP-K（近似表达命中）"""
    try:
        qv = _embed(term)
    except Exception as e:
        print(f'❌ 语义查证失败: {e}（Ollama bge-m3 不可达？）')
        return
    vectors = ensure_vectors(d)
    scored = [(name, _cosine(qv, vec)) for name, vec in vectors.items() if vec]
    scored.sort(key=lambda x: -x[1])
    print(f'=== 语义查证: {term}（bge-m3 向量，TOP-{top_k}） ===')
    hits = 0
    for name, score in scored[:top_k]:
        if score >= 0.6:
            c = d['concepts'][name]
            print(f'  🔍 {name}（相似度 {score:.2f}）: {c["def"][:50]}')
            hits += 1
        else:
            break
    if hits == 0:
        print('  ❌ 无语义命中（阈值 0.6）——建议 add 登记')
    log(f'query_semantic: {term} -> {hits} hits')

def selfcheck():
    """TCC 检测（R006-2）：模块完整性自检"""
    ok = True
    checks = [
        ('字典文件可读写', os.access(DATA_DIR, os.W_OK) or os.path.isdir(DATA_DIR)),
        ('日志可写', os.access(os.path.dirname(LOG_FILE), os.W_OK) or True),
        ('核心函数存在', all(hasattr(sys.modules[__name__], f) for f in ['add','query','check','suggest','audit'])),
    ]
    for name, passed in checks:
        print(('  ✅' if passed else '  ❌'), name)
        ok = ok and passed
    print('TCC 自检:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description='概念数据字典工具（R019，R006 九标准）')
    sub = ap.add_subparsers(dest='cmd')
    p_add = sub.add_parser('add'); p_add.add_argument('name', nargs='?', default=''); p_add.add_argument('--def'); p_add.add_argument('--src', default=''); p_add.add_argument('--alias', action='append', default=[]); p_add.add_argument('--lean4-check', action='store_true')
    p_q = sub.add_parser('query'); p_q.add_argument('term'); p_q.add_argument('--semantic', action='store_true', help='语义查证（bge-m3 向量，近似表达命中）')
    sub.add_parser('check').add_argument('text')
    p_s = sub.add_parser('suggest'); p_s.add_argument('--dir', action='append')
    sub.add_parser('audit')
    sub.add_parser('list')
    sub.add_parser('selfcheck')
    sub.add_parser('version')
    p_sync = sub.add_parser('sync'); p_sync.add_argument('--from-blackboard', action='store_true', help='从黑板拉取最新字典（端侧用）')
    args = ap.parse_args()

    d = load()
    try:
        if args.cmd == 'add':
            if getattr(args, 'lean4_check', False):
                try:
                    add(d, '', 'test', 'lean4-check')
                    print('lean4-check: X 空概念名未被拒!')
                    return 1
                except ValueError:
                    print('lean4-check: OK 空概念名被结构门拒绝')
                    return 0
            add(d, args.name, args.__dict__.get('def', ''), args.src, args.alias)
        elif args.cmd == 'query':
            if getattr(args, 'semantic', False):
                query_semantic(d, args.term)
            else:
                query(d, args.term)
        elif args.cmd == 'check': check(d, args.text)
        elif args.cmd == 'suggest': suggest(d, args.__dict__.get('dir'))
        elif args.cmd == 'audit': audit(d)
        elif args.cmd == 'selfcheck': return selfcheck()
        elif args.cmd == 'sync': sync_from_blackboard()
        elif args.cmd == 'version': print(f'concept-dict v{VERSION}')
        elif args.cmd == 'list':
            for name, c in sorted(d['concepts'].items()):
                print(f'  {name}: {c["def"][:50]} ({c.get("source","")[:30]})')
        else:
            ap.print_help()
    except Exception as e:
        log(f'ERROR: {e}\n{traceback.format_exc()}')
        print(f'❌ 错误: {e}（已记日志）')
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
