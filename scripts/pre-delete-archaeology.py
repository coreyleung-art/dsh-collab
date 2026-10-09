#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre-delete-archaeology v1.0 (HR) — 删除前考古评估器（纯规则，零 LLM）

职责：删除文件/目录/资源前，先评估考古价值——「删之前先考古」制度化。
      对目标做内容类型识别 + 价值信号扫描 → 给出三级处置建议：
        ✅ safe_delete     零考古价值，可安全删除
        📋 archive_meta    二进制/结构化数据，保留元数据清单即可
        🧠 sediment_first  含独特经验/模式，先提炼向量化入库再删

用法：
  python3 pre-delete-archaeology.py --path <路径>          # 评估单个路径
  python3 pre-delete-archaeology.py --path <路径> --json    # JSON 输出（供工具链）
  python3 pre-delete-archaeology.py --batch <清单.txt>      # 批量（每行一路径）
  python3 pre-delete-archaeology.py --gen-manifest <路径>   # 生成考古清单文档

信号设计（纯规则，零 LLM）：
  无价值信号（日志/缓存/临时/噪音）：error/timeout/DEBUG/GET / /cache/ .log 高频重复
  价值信号（独特经验/配置/模式）：model_load_failed 独特样本/配置键/踩坑关键词/版本对照
  二进制判断：.gguf/.safetensors/.bin/.pth/.onnx/.model/.mlx → 元数据留档（名称/大小/来源）

零 LLM 原则：与 sedimentation-chain-scan.py 同构——规则判定，不调模型。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, datetime, collections


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/pre-delete-archaeology.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VALUE_NOISE = re.compile(r'(timeout|DEBUG|path required|n_cache_reuse|GET /|POST /|keep-alive)', re.I)
VALUE_SIGNAL = re.compile(r'(model_load_failed|exception|failed|错误|失败|配置|config|version|版本|踩坑|修复|root cause|OOM|out of memory|CUDA|port conflict|端口冲突)', re.I)
BINARY_EXT = {'.gguf', '.safetensors', '.bin', '.pth', '.onnx', '.model', '.mlx', '.safetensors', '.ckpt', '.pt', '.h5', '.zip', '.dmg', '.pkg'}
LOG_EXT = {'.log', '.out', '.err', '.jsonl', '.tsv'}
CACHE_HINTS = ['cache', 'log', 'tmp', 'temp', 'trash', '.Trash', 'server-logs']

def classify_path(path):
    """内容类型识别"""
    ext = os.path.splitext(path)[1].lower()
    base = os.path.basename(path).lower()
    if ext in BINARY_EXT:
        return 'binary'
    if ext in LOG_EXT or any(h in base for h in ['log']):
        return 'log'
    if any(h in path.lower() for h in CACHE_HINTS):
        return 'cache'
    if os.path.isdir(path):
        return 'dir'
    return 'text'

def scan_text_file(path, limit=20000):
    """文本文件考古扫描：噪音 vs 信号计数"""
    noise = 0; signal = 0; sig_samples = []
    try:
        with open(path, encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i > limit: break
                line = line.strip()
                if not line: continue
                if VALUE_NOISE.search(line): noise += 1
                if VALUE_SIGNAL.search(line):
                    signal += 1
                    if len(sig_samples) < 5:
                        sig_samples.append(line[:140])
    except Exception:
        return 0, 0, []
    return noise, signal, sig_samples

def assess(path):
    """评估单个路径 → 处置建议"""
    if os.path.isfile(path):
        size = os.path.getsize(path)
        kind = classify_path(path)
        if kind == 'binary':
            return {'path': path, 'kind': 'binary', 'size_gb': round(size/1e9, 2),
                    'verdict': 'archive_meta',
                    'reason': '二进制资产（模型/权重/打包）— 保留元数据清单（名称/大小/来源/用途），本体可删'}
        if kind in ('log', 'cache'):
            noise, signal, samples = scan_text_file(path)
            if signal == 0 or noise / max(signal, 1) > 50:
                return {'path': path, 'kind': kind, 'size_gb': round(size/1e9, 2),
                        'verdict': 'safe_delete',
                        'reason': f'日志/缓存噪音占绝对主导（noise {noise} vs signal {signal}），无考古价值'}
            return {'path': path, 'kind': kind, 'size_gb': round(size/1e9, 2),
                    'verdict': 'sediment_first', 'signals': samples,
                    'reason': f'含 {signal} 条价值信号（非噪音），先提炼向量化再删'}
        # 文本
        noise, signal, samples = scan_text_file(path)
        if signal > 0:
            return {'path': path, 'kind': kind, 'size_gb': round(size/1e9, 2),
                    'verdict': 'sediment_first', 'signals': samples,
                    'reason': f'文本含 {signal} 条价值信号，先评估是否沉淀'}
        return {'path': path, 'kind': kind, 'size_gb': round(size/1e9, 2),
                'verdict': 'safe_delete', 'reason': '纯文本无价值信号'}
    if os.path.isdir(path):
        total = 0; kinds = collections.Counter(); sub = []
        for dirpath, _, files in os.walk(path):
            for fn in files:
                fp = os.path.join(dirpath, fn)
                try: total += os.path.getsize(fp)
                except: pass
                k = classify_path(fp); kinds[k] += 1
        if kinds['binary'] > 0:
            return {'path': path, 'kind': 'dir', 'size_gb': round(total/1e9, 2),
                    'verdict': 'archive_meta',
                    'reason': f'目录含二进制资产 {kinds["binary"]} 个 — 生成考古清单后删'}
        if kinds['log'] > 0 or kinds['cache'] > 0:
            return {'path': path, 'kind': 'dir', 'size_gb': round(total/1e9, 2),
                    'verdict': 'safe_delete',
                    'reason': f'目录以日志/缓存为主（log {kinds["log"]} cache {kinds["cache"]}）— 可安全删除'}
        return {'path': path, 'kind': 'dir', 'size_gb': round(total/1e9, 2),
                'verdict': 'review', 'reason': '混合目录，建议人工复核'}
    return {'path': path, 'kind': 'missing', 'verdict': 'error', 'reason': '路径不存在'}

def gen_manifest(paths, out):
    """生成考古清单文档（二进制/资产删除前留档）"""
    rows = [assess(p) for p in paths]
    lines = ['# 删除前考古清单 · pre-delete-archaeology', '',
             f'> 生成：{datetime.date.today().isoformat()} · 工具：pre-delete-archaeology.py v1.0',
             f'> 原则：删之前先考古 — 无价值直接删，有价值留元数据/先沉淀', '']
    for r in rows:
        lines.append(f'## {r["path"]}')
        lines.append(f'- 类型: {r["kind"]} · 大小: {r["size_gb"]}GB')
        lines.append(f'- 判定: **{r["verdict"]}** — {r["reason"]}')
        if r.get('signals'):
            lines.append('- 价值信号样本:')
            for s in r['signals'][:3]:
                lines.append(f'  - {s}')
        lines.append('')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return out

def main():
    ap = argparse.ArgumentParser(description='删除前考古评估器（纯规则零 LLM）')
    ap.add_argument('--path', help='评估单个路径')
    ap.add_argument('--batch', help='批量清单文件（每行一路径）')
    ap.add_argument('--json', action='store_true', help='JSON 输出')
    ap.add_argument('--gen-manifest', help='生成考古清单到指定文件（配合 --path/--batch）')
    args = ap.parse_args()

    paths = []
    if args.path: paths = [args.path]
    elif args.batch:
        with open(args.batch) as f:
            paths = [l.strip() for l in f if l.strip()]

    if args.gen_manifest:
        out = gen_manifest(paths, args.gen_manifest)
        print(f'📋 考古清单已生成: {out}')
        return 0

    results = [assess(p) for p in paths]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            print(f'[{"✅" if r["verdict"]=="safe_delete" else "📋" if r["verdict"]=="archive_meta" else "🧠" if r["verdict"]=="sediment_first" else "⚠️"}] {r["path"]} ({r["size_gb"]}GB)')
            print(f'    判定: {r["verdict"]} — {r["reason"]}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
