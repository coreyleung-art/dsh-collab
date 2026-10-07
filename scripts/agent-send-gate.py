#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""agent-send-gate.py — agent_send 审计门禁守护（v2.5，对齐 v2.4 语义）

扫描跨会话消息，审计「全文未落黑板」违规（>50 字且无黑板引用）：
  ① 记录违规（黑板 data/audit/agentsend-violations.jsonl + 本地 logs/）
  ② 防刷屏（纯确认不回——低于阈值不告警）

v2.5 变更（2026-08-31 星桥评估落地，方案 docs/agentsend-gate-audit-alignment-v1.md）：
  - THRESHOLD 200 → 50（与 v2.4 运行时门禁一致）
  - 移除业务标记白名单豁免（✅/【】/收到/确认/@ 等 15 个——合法对话不再是豁免理由）
  - 豁免仅保留与 v2.4 一致的四类：广播 / 看黑板 / urgent / 黑板路径 (notes/|data/|tasks/)
  - 新增 --since <hours>（默认 24h，防历史存量噪音）与 --all（全量盘点）
  - 新增 --stats（分桶统计）与 --apply（默认 dry-run 只输出不落盘）

用法:
  python3 agent-send-gate.py --once                # 单次扫描（近 24h）
  python3 agent-send-gate.py --interval 300        # 常驻（每 5 分钟，默认）
  python3 agent-send-gate.py --since 168 --once    # 近 7 天
  python3 agent-send-gate.py --all --stats --once  # 全量盘点 + 统计
  python3 agent-send-gate.py --once --apply        # 扫描并落盘违规

判定（与 v2.4 lib/index.js 逐字符对齐）:
  违规 = 长度 > 50 字
         AND 非广播
         AND 不含 '看黑板'
         AND 不含 'urgent'
         AND 不含黑板路径 (notes/|data/|tasks/)[a-z0-9\-/]+
         AND 在时间窗内（--since 默认 24h）
  豁免 = 广播 / 看黑板 / urgent / 黑板路径

输出: 黑板 data/audit/agentsend-violations.jsonl（append-only）+ 本地 logs/
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, time, datetime, urllib.request

BB = "http://127.0.0.1:8792"
VIOLATIONS = "data/audit/agentsend-violations.jsonl"
THRESHOLD = 50  # v2.5: 与 v2.4 运行时门禁对齐（200 → 50）
GATE_TAG = "audit-v2"  # 审计记录版本标记

# 与 v2.4 lib/index.js 相同的黑板路径正则
BB_PATH_RE = __import__("re").compile(r"(notes/|data/|tasks/)[a-z0-9\-/]+")

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_ts():
    return int(time.time())

def get_bb(path):
    try:
        req = urllib.request.Request(BB + "/" + path.lstrip("/"))
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None

def log_violation(entry):
    # 落盘违规记录
    out = os.path.expanduser("~/dsh-collab/scripts/logs/agentsend-violations.jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # 同步黑板（审计可查）
    try:
        req = urllib.request.Request(BB + "/" + VIOLATIONS.lstrip("/"))
        # 黑板无 append，读-改-写（简化：写独立键）
        req2 = urllib.request.Request(
            BB + f"/{VIOLATIONS.rsplit('/',1)[0]}/v-{int(time.time())}",
            data=json.dumps({"value": entry}, ensure_ascii=False).encode(), method="PUT")
        urllib.request.urlopen(req2, timeout=5)
    except Exception:
        pass

def is_violation(m, since_ts):
    """v2.5 判定：与 v2.4 语义一致（精确豁免）"""
    text = m.get("text", "")
    kind = m.get("kind", "normal")
    # 豁免 1：广播
    if kind == "broadcast":
        return False, "broadcast"
    # 豁免 2：看黑板
    if "看黑板" in text:
        return False, "bb_ref"
    # 豁免 3：urgent
    if "urgent" in text.lower():
        return False, "urgent"
    # 豁免 4：黑板路径
    if BB_PATH_RE.search(text):
        return False, "bb_path"
    # 时间窗（消息 time 为 ms 时间戳）
    msg_ts = m.get("time", 0)
    if isinstance(msg_ts, str):
        try:
            msg_ts = int(float(msg_ts))
        except Exception:
            msg_ts = 0
    if msg_ts > 10 ** 12:  # ms → s
        msg_ts //= 1000
    if since_ts and msg_ts and msg_ts < since_ts:
        return False, "outside_window"
    # 阈值
    if len(text) <= THRESHOLD:
        return False, "short"
    # 违规：>50 字且无任何豁免
    return True, "violation"


def scan(since_hours=24, all_=False, apply=False):
    """扫描 agent-bus.json，审计违规（v2.5）"""
    bus_file = os.path.expanduser("~/.dsh/agent-bus.json")
    if not os.path.exists(bus_file):
        print(f"[agent-send-gate] {now()} 无 agent-bus.json，跳过")
        return 0, {}

    try:
        data = json.load(open(bus_file, encoding="utf-8"))
    except Exception as e:
        print(f"[agent-send-gate] {now()} 读取 agent-bus.json 失败: {e}")
        return 0, {}

    since_ts = 0 if all_ or since_hours <= 0 else now_ts() - since_hours * 3600

    violations = 0
    stats = {"total": 0, "exempt": {}, "violations": 0, "samples": []}
    threads = data.get("threads", [])
    for t in threads:
        for m in t.get("messages", []):
            stats["total"] += 1
            is_v, reason = is_violation(m, since_ts)
            if not is_v:
                stats["exempt"][reason] = stats["exempt"].get(reason, 0) + 1
                continue
            # 违规
            entry = {
                "ts": now(),
                "gate": GATE_TAG,
                "from": m.get("from", "?"),
                "to": m.get("to", "?"),
                "len": len(m.get("text", "")),
                "preview": m.get("text", "")[:80],
                "thread": t.get("id", "?"),
                "msg_time": m.get("time", 0),
            }
            stats["violations"] += 1
            if len(stats["samples"]) < 5:
                stats["samples"].append(entry["preview"])
            if apply:
                log_violation(entry)
            violations += 1
            print(f"[agent-send-gate] {now()} ⚠️ 违规 {entry['from'][:14]} → {entry['to'][:14]} ({entry['len']}字): {entry['preview']}")

    print(f"[agent-send-gate] {now()} 扫描完成: {violations} 条违规 "
          f"(总 {stats['total']}, 豁免 {sum(stats['exempt'].values())}, 时间窗 {'全量' if all_ else f'近{since_hours}h'})")
    return violations, stats

def main():
    ap = argparse.ArgumentParser(description="agent_send 审计门禁（v2.5 对齐 v2.4）")
    ap.add_argument("--once", action="store_true", help="单次扫描")
    ap.add_argument("--interval", type=int, default=300, help="常驻间隔秒")
    ap.add_argument("--since", type=int, default=24, help="时间窗小时（0=不限；默认 24）")
    ap.add_argument("--all", dest="all_", action="store_true", help="全量盘点（忽略时间窗）")
    ap.add_argument("--stats", action="store_true", help="输出分桶统计")
    ap.add_argument("--apply", action="store_true", help="落盘违规记录（默认 dry-run 只输出）")
    args = ap.parse_args()

    if args.all_:
        args.since = 0

    while True:
        try:
            n, stats = scan(since_hours=args.since, all_=args.all_, apply=args.apply)
            if args.stats:
                print(json.dumps(stats, ensure_ascii=False, indent=1))
        except Exception as e:
            print(f"[agent-send-gate] {now()} scan error: {e}")
        if args.once:
            break
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
