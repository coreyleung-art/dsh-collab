#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route-feedback.py v1.0 — 判定反馈收集器（纯规则，零 LLM）

职责：收集「扫描器判定 vs 值班人实际裁决」的反馈对，作为 v1.2 学习型路由（RouteLLM）的训练数据。

背景：
  沉积链扫描器（sedimentation-chain-scan.py）用静态关键词规则判定 deposit/skip/review，
  review 占 ~20% 需人工；本收集器把「人工最终裁决」记下来，攒够数据后学出更准的判定器，
  替代死关键词 → 降低 review 占比 → 省值班判定 token。

数据形态（一条反馈 = 一行 JSONL）：
  {"ts": "...", "dedup": "...", "summary": "...", "scanned": "deposit|skip|review", "actual": "deposit|skip", "note": "..."}

用法：
  python3 route-feedback.py --record <dedup> --actual deposit|skip [--note 备注]
      # 值班人处理完一条待沉淀清单后，记录实际裁决
      # 自动从 sedimentation-queue/ 清单里反查该 dedup 的 summary + scanned 判定
  python3 route-feedback.py --stats
      # 看累计反馈数、扫描器判定 vs 人工裁决的一致性（混淆矩阵）、学习就绪度
  python3 route-feedback.py --export [--out PATH]
      # 导出为训练数据（JSONL），供 v1.2 学习型路由使用

学习就绪度：攒够 ~500 条（且 review 占比下降趋势可见）即可进 v1.2 学习型路由。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, glob, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/route-feedback.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
QUEUE_DIR = os.path.join(COLLAB, "token-monitor", "sedimentation-queue")
FEEDBACK = os.path.join(COLLAB, "token-monitor", "route-feedback.jsonl")
READY_THRESHOLD = 500  # 学习就绪阈值（攒够多少条反馈可进 v1.2）

def load_latest_queue():
    """读最新的待沉淀清单，构建 dedup -> entry 映射"""
    files = sorted(glob.glob(os.path.join(QUEUE_DIR, "*.json")), reverse=True)
    mapping = {}
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
            for q in data.get("queue", []):
                mapping[q.get("dedup", "")] = q
        except Exception:
            continue
    return mapping

def load_feedback():
    """读已有反馈"""
    out = []
    if os.path.exists(FEEDBACK):
        for line in open(FEEDBACK, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    return out

def record(dedup, actual, note):
    mapping = load_latest_queue()
    entry = mapping.get(dedup)
    if entry is None:
        print(f"⚠️ dedup {dedup} 不在最新待沉淀清单中（可能已过期或清单已清理）")
        return 1
    row = {
        "ts": datetime.datetime.now().isoformat(),
        "dedup": dedup,
        "summary": _clean(entry.get("summary", ""))[:200],
        "scanned": entry.get("decision", "review"),  # 扫描器判定
        "actual": actual,                             # 人工裁决
        "note": note or "",
    }
    with open(FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"✅ 已记录反馈: scanned={row['scanned']} → actual={row['actual']} | {row['summary'][:50]}")
    return 0

def _clean(raw):
    """复用扫描器的摘要清洗（剥离 $__dsh_persistent_bash_ 污染 + json 残留）"""
    import re
    s = (raw or "").replace("$__dsh_persistent_bash_", "")
    s = re.sub(r'[{}"\']', ' ', s)
    s = re.sub(r'summary\s*:', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def stats():
    fb = load_feedback()
    if not fb:
        print("尚无反馈数据。用法：python3 route-feedback.py --record <dedup> --actual deposit|skip")
        return 0

    # 混淆矩阵：scanned vs actual
    from collections import Counter
    matrix = Counter()
    for r in fb:
        matrix[(r.get("scanned"), r.get("actual"))] += 1

    print(f"=== 判定反馈统计 ===")
    print(f"累计反馈: {len(fb)} 条 · 学习就绪阈值: {READY_THRESHOLD} 条")
    print(f"就绪度: {'✅ 可进 v1.2' if len(fb) >= READY_THRESHOLD else f'⏳ 还需 {READY_THRESHOLD - len(fb)} 条'}")

    # 一致性：扫描器判定 == 人工裁决 的比例
    agree = sum(1 for r in fb if r.get("scanned") == r.get("actual"))
    print(f"\n扫描器与人工一致率: {agree}/{len(fb)} = {agree*100//len(fb)}%")

    print("\n混淆矩阵（scanned → actual）:")
    for (s, a), c in sorted(matrix.items()):
        flag = "  ← 扫描器误判" if s != a else ""
        print(f"  {s:8} → {a:8} : {c}{flag}")

    # 最常见的误判模式（供调信号参考）
    mis = [(r, (r.get("scanned"), r.get("actual"))) for r in fb if r.get("scanned") != r.get("actual")]
    if mis:
        print(f"\n误判样本（{len(mis)} 条，抽查前 5 条供调信号）:")
        for r, _ in mis[:5]:
            print(f"  {r.get('scanned')}→{r.get('actual')} | {r.get('summary','')[:60]}")
    return 0

def export(out_path):
    fb = load_feedback()
    if not fb:
        print("无反馈数据可导出")
        return 1
    with open(out_path, "w", encoding="utf-8") as f:
        for r in fb:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"✅ 导出 {len(fb)} 条反馈到 {out_path}（供 v1.2 学习型路由训练）")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", help="记录一条反馈的 dedup id")
    ap.add_argument("--actual", choices=["deposit", "skip"], help="人工实际裁决")
    ap.add_argument("--note", default="", help="备注")
    ap.add_argument("--stats", action="store_true", help="看统计")
    ap.add_argument("--export", action="store_true", help="导出训练数据")
    ap.add_argument("--out", default=os.path.join(COLLAB, "token-monitor", "route-feedback-train.jsonl"), help="导出路径")
    args = ap.parse_args()

    if args.stats:
        return stats()
    if args.export:
        return export(args.out)
    if args.record and args.actual:
        return record(args.record, args.actual, args.note)
    ap.print_help()
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
