#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bus-dup-classify — 总线消息「重复」三分法分类器

判据（明鉴 × 星桥共定 2026-09-14，经双实现独立复算逐位一致）：
  ① 真重复       同文本 + 同 to                        ⇒ 病：同一次投递被做了多次
  ② 广播多副本   同文本 + 不同 to + 任一条 broadcast    ⇒ 机制产物，正常（一次投递产生多副本）
  ③ 多次独立投递 同文本 + 不同 to + 全非广播            ⇒ 人的选择，非重复但须与②区分

判据行（第六项判据，非数据要素）：本工具按 (归一化文本, to 元组, kind) 三字段判决。
  文本归一 **唯一动作 = 折叠连续空白**；不做大小写/标点归一。

对象声明（防 L2）：① 的对象 = 「同一收件人的同一文本投递」；
  ② ③ 的对象 = 「同一文本的多个收件人投递」。**二者对象不同：869 组与 408 组不可互代。**

边界：只判投递形态，不判「内容该不该发」，也不判对错。

用法: bus-dup-classify.py [--raw] [--json] [--version] [--selftest]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import collections
import datetime
import hashlib
import json
import os
import sys
import time

BUS = os.path.expanduser("~/.dsh/agent-bus.json")
VERSION = "1.0.0"

RULINGS = {
    "true_dup": "①真重复",
    "broadcast_copies": "②广播多副本",
    "independent_sends": "③多次独立投递",
}

# ① 并非同质：同文本+同 to 仍可由三种机制产生，处置互不相同。
# 判据（机器可判，判据行的一部分）：间隔众数占比 ≥50% 且众数 ≥60s ⇒ 调度驱动；
#   否则跨度 <2 天且条数 ≥20 ⇒ 单源爆发；其余 ⇒ 习惯性。
SOURCE_SHAPES = {
    "scheduled": "调度驱动（间隔整齐 ⇒ 设计内，非病）",
    "burst": "单源爆发（短窗高频 ⇒ 疑自动循环/重试）",
    "habitual": "习惯性（无规律/多源 ⇒ 才是「人反复发」）",
}



def _decode_strict(raw):
    """★ 严格解码（2026-09-22 新增，采纳驿使经明鉴转达的「穷尽五条件」之一：**解码无丢失**）。
    原写法 `errors="replace"` 会把**撕裂读造成的半个多字节序列**静默换成 U+FFFD ——
    **字节数看起来没少、字符却已经丢了**，而且 JSON 往往仍能解析 ⇒ **错误不可见**。
    ⇒ 改为严格解码：解不出来就抛，**交给外层重试**（本工具本来就有重试循环）。
    ⇒ 判据：**问「我的读取有没有跳过任何一个字节？」** —— 丢字符也算跳过。"""
    return raw.decode("utf-8")

def source_shape(group):
    ts = sorted(m.get("time", 0) / 1000 for _, m in group)
    if len(ts) < 3:
        return "habitual", {"mode_interval_s": None, "mode_share": None, "span_s": 0, "n_from": 1}
    iv = [round(b - a) for a, b in zip(ts, ts[1:])]
    mode, mc = collections.Counter(iv).most_common(1)[0]
    span = int(ts[-1] - ts[0])
    n_from = len({str(m.get("from")) for _, m in group})
    if mode >= 60 and mc / len(iv) >= 0.5:
        shape = "scheduled"
    elif span < 2 * 86400 and len(group) >= 20:
        shape = "burst"
    else:
        shape = "habitual"
    return shape, {"mode_interval_s": mode, "mode_share": round(mc / len(iv), 2),
                   "span_s": span, "n_from": n_from}


def load_bus(path=BUS, tries=20, delay=0.35):
    """总线是 20MB 单文件就地重写 ⇒ 撕裂读必然发生，解析+重试是必需项。
    重试预算来自实测：2026-09-14 20:15 一次读取第 1–5 次全报 Unterminated string，
    第 6 次才成功 —— 旧的 6×0.8s 预算在边缘上，本工具会直接判 bus-unreadable。
    （教训：重试次数不是"够用就行"，要按实测最坏情况留 3 倍余量。）"""
    last = None
    for _ in range(tries):
        try:
            with open(path, "rb") as f:
                raw = f.read()
            return json.loads(_decode_strict(raw)), raw
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(delay)
    raise RuntimeError(f"总线解析失败（{tries} 次重试）: {last}")


def snapshot_header(path=BUS, raw=None):
    try:
        st = os.stat(path)
        h = hashlib.sha256(raw).hexdigest()[:12] if raw is not None else "?"
        return (f"快照 mtime={datetime.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M:%S}"
                f" bytes={st.st_size} sha256[:12]={h}"
                f" 读取时刻={datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    except Exception:  # noqa: BLE001
        return "快照不可取 ⇒ 本次读数不得引用"


def norm(text, raw_mode=False):
    text = str(text or "")
    return text if raw_mode else " ".join(text.split())


def tos_of(msg):
    to = msg.get("to")
    if to is None:
        to = msg.get("recipients")
    if isinstance(to, (list, tuple)):
        return tuple(to)
    return (to,)


def iter_messages(bus):
    for thread in bus.get("threads", []):
        for msg in thread.get("messages", []):
            yield thread.get("id"), msg


def classify(msgs, raw_mode=False):
    """msgs: iterable of (thread_id, msg). 返回 (results, stats)."""
    by_pair = collections.defaultdict(list)   # (text, to) -> msgs
    by_text = collections.defaultdict(list)   # text -> msgs
    total = 0
    for tid, msg in msgs:
        total += 1
        text = norm(msg.get("text"), raw_mode)
        to = tos_of(msg)
        by_pair[(text, to)].append((tid, msg))
        by_text[text].append((tid, msg))

    res = {"true_dup": [], "broadcast_copies": [], "independent_sends": []}
    by_shape = collections.Counter()
    msgs_by_shape = collections.Counter()
    for (text, to), group in by_pair.items():
        if len(group) > 1:
            shape, shape_ev = source_shape(group)
            by_shape[shape] += 1
            msgs_by_shape[shape] += len(group)
            res["true_dup"].append({"text": text, "to": to, "count": len(group),
                                    "shape": shape, "shape_ev": shape_ev,
                                    "threads": sorted({t for t, _ in group})})

    for text, group in by_text.items():
        to_sets = {tos_of(m) for _, m in group}
        if len(group) < 2 or len(to_sets) < 2:
            continue
        kinds = {m.get("kind") for _, m in group}
        bucket = "broadcast_copies" if "broadcast" in kinds else "independent_sends"
        res[bucket].append({"text": text, "n_to": len(to_sets), "n_msgs": len(group),
                            "kinds": sorted(k for k in kinds if k)})

    for bucket in res:
        res[bucket].sort(key=lambda d: -d["count"] if "count" in d else -d["n_msgs"])

    stats = {
        "total_messages": total,
        "unique_texts": len(by_text),          # 未过滤量（降压前），必须先打印
        "unique_pairs": len(by_pair),
        "pair_with_dup": len(res["true_dup"]),
        "messages_in_dup": sum(d["count"] for d in res["true_dup"]),
        "broadcast_groups": len(res["broadcast_copies"]),
        "independent_groups": len(res["independent_sends"]),
        "different_to_total": len(res["broadcast_copies"]) + len(res["independent_sends"]),
        "dup_by_shape": dict(by_shape),
        "dup_msgs_by_shape": dict(msgs_by_shape),
    }
    return res, stats


def report(res, stats, header):
    print("【判据行】按 (折叠空白后的文本, to 元组, kind) 判决；① 与 ②③ 对象不同，不可互代")
    print("【判据行2】① 内部再按时间形态判产生机制（间隔众数占比/跨度/发件人数），三型处置不同")
    print(header)
    print(f"总消息 {stats['total_messages']} · 唯一文本 {stats['unique_texts']}（未过滤量）"
          f" · 唯一(文本,to) {stats['unique_pairs']}")
    print()
    print(f"{RULINGS['true_dup']:<16} {stats['pair_with_dup']:>6} 组"
          f" · 涉及 {stats['messages_in_dup']:>6} 条   ← 病（但须分层）")
    print(f"{RULINGS['broadcast_copies']:<16} {stats['broadcast_groups']:>6} 组   ← 机制产物")
    print(f"{RULINGS['independent_sends']:<16} {stats['independent_groups']:>6} 组   ← 人的选择")
    print(f"{'（不同 to 合计）':<16} {stats['different_to_total']:>6} 组   ← ②+③")
    print()
    for shape, label in SOURCE_SHAPES.items():
        g = stats["dup_by_shape"].get(shape, 0)
        m = stats["dup_msgs_by_shape"].get(shape, 0)
        print(f"  ①{shape:<10} {g:>5} 组 / {m:>5} 条   {label}")
    print()
    for item in res["true_dup"][:3]:
        ev = item["shape_ev"]
        print(f"  ①[{item['shape']}] x{item['count']} to={item['to']} "
              f"间隔众数={ev.get('mode_interval_s')}s 占比={ev.get('mode_share')} "
              f"跨度={ev.get('span_s')}s 发件人数={ev.get('n_from')}")
        print(f"       text={item['text'][:60]!r}")


def selftest():
    """合成语料：三型各一例 + 两个负例（唯一文本、不同文本同 to）。"""
    cases = [
        {"threads": [{"id": "t1", "messages": [
            {"text": "same", "to": ["a"], "kind": "normal"},
            {"text": "same", "to": ["a"], "kind": "normal"},        # ① 真重复
            {"text": "bc", "to": ["a"], "kind": "broadcast"},
            {"text": "bc", "to": ["b"], "kind": "broadcast"},       # ② 广播多副本
            {"text": "ind", "to": ["a"], "kind": "normal"},
            {"text": "ind", "to": ["b"], "kind": "normal"},         # ③ 多次独立投递
            {"text": "uniq", "to": ["a"], "kind": "normal"},        # 负例：唯一
            {"text": "x", "to": ["a"], "kind": "normal"},
            {"text": "y", "to": ["a"], "kind": "normal"},           # 负例：不同文本同 to
            {"text": "  bc  ", "to": ["c"], "kind": "broadcast"},   # 归一折叠 ⇒ 并入 ②
            {"text": "sched", "to": ["s"], "kind": "normal", "time": 0},
            {"text": "sched", "to": ["s"], "kind": "normal", "time": 900000},
            {"text": "sched", "to": ["s"], "kind": "normal", "time": 1800000},  # ⓪调度驱动
        ]}]}]
    res, stats = classify(iter_messages(cases[0]))
    checks = [
        ("①组数=2", stats["pair_with_dup"] == 2),
        ("①涉及=5", stats["messages_in_dup"] == 5),
        ("②组数=1", stats["broadcast_groups"] == 1),
        ("②含归一后的第3副本", res["broadcast_copies"][0]["n_msgs"] == 3),
        ("③组数=1", stats["independent_groups"] == 1),
        ("②+③=2", stats["different_to_total"] == 2),
        ("唯一文本=7", stats["unique_texts"] == 7),
        ("总消息=13", stats["total_messages"] == 13),
        ("①不吞②③", stats["pair_with_dup"] == 2 and stats["messages_in_dup"] == 5),
        ("⓪调度驱动识别出 1 组", stats["dup_by_shape"].get("scheduled") == 1),
        ("习惯性 1 组（same x2）", stats["dup_by_shape"].get("habitual") == 1),
        ("分层条数守恒", sum(stats["dup_msgs_by_shape"].values()) == stats["messages_in_dup"]),
        ("调度组间隔众数=900s",
         [d for d in res["true_dup"] if d["shape"] == "scheduled"][0]["shape_ev"]["mode_interval_s"] == 900),
    ]
    # 负例：--raw 下空白不同 ⇒ ②的第三副本脱钩，组内变 2 条
    res2, stats2 = classify(iter_messages(cases[0]), raw_mode=True)
    checks.append(("负例 raw 模式 ②=2条", res2["broadcast_copies"][0]["n_msgs"] == 2))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'✅' if ok else '❌'} {n}")
    print(f"selftest {len(checks) - len(bad)}/{len(checks)}")
    return 1 if bad else 0


def version(header):
    try:
        with open(__file__, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        sha = "?"
    print(f"bus-dup-classify.py v{VERSION}")
    print(f"file_sha256[:16]={sha}")
    print(f"reported_at={datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(header)


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--raw", action="store_true", help="不做空白折叠（未归一模式）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.version:
        try:
            _, raw = load_bus()
        except Exception as exc:  # noqa: BLE001
            raw = None
            print(f"[快照不可取] {exc}", file=sys.stderr)
        version(snapshot_header(raw=raw))
        return 0

    try:
        bus, raw = load_bus()
    except Exception as exc:  # noqa: BLE001
        print(f"[bus-unreadable] {exc}", file=sys.stderr)
        return 3
    res, stats = classify(iter_messages(bus), raw_mode=args.raw)
    header = snapshot_header(raw=raw)
    if args.json:
        print(json.dumps({"header": header, "stats": stats,
                          "criterion": "同文本+同to=真重复 / +不同to+broadcast=多副本 / +不同to+非广播=独立投递"},
                         ensure_ascii=False, indent=2))
    else:
        report(res, stats, header)
    return 1 if stats["pair_with_dup"] else 0


if __name__ == "__main__":
    sys.exit(main())
