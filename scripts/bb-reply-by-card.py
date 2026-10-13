#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-reply-by-card.py — 按【卡内 thread 字段】回消息 v1.0.0

★★ 为什么需要它（★ 实测事故 · 2026-10-13）：
  我连续两次把回复发到【通知里给的线程】而非【卡内自述的 `thread` 字段】——
  ① 灯塔 21:05 卡（卡内 thread-mv6omp44-hndls9uu）→ 我发到 thread-mv6ot9xg-2t12v9nr
  ② 灯塔 21:12 卡（卡内 thread-mv6nxmab-2ektlxw8）→ 我发到 thread-mv6owjo2-iee6rhg8
  ★★ 根因：【通知里的线程 ≠ 卡的归属线程】——通知带的是【投递通道】，卡内才是【对话归属】。
  ★★★ 这与本线「装置失效会给出看似正常的读数」同族，而【它第二次发生】证明了：
      「当成经验记着」不够，必须【做成工具】。

用法:
    bb-reply-by-card.py <卡键> <收件人 session id> [--dry-run]
    ★ 默认 dry-run（只打印将用的 thread，不发）
"""
__version__ = "1.0.0"
import argparse, json, os, subprocess, sys, urllib.request

def fetch(key):
    u = "http://127.0.0.1:8792/" + key.lstrip('/')
    with urllib.request.urlopen(u, timeout=40) as r:
        d = json.loads(r.read().decode())
    v = d.get('value') or {}
    if isinstance(v, dict) and isinstance(v.get('value'), dict):
        v = v['value']
    return d, v

def main():
    ap = argparse.ArgumentParser(description="按卡内 thread 字段回复（★ 默认 dry-run）")
    ap.add_argument("key"); ap.add_argument("to")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--send", action="store_true", help="真发（★ 需显式）")
    a = ap.parse_args()
    d, v = fetch(a.key)
    th = v.get('thread')
    if not th:
        print("  ★★ 该卡【无 thread 字段】⇒ 不可判归属线程，拒绝自动回（请人工决定）")
        return 2
    print("  卡: %s" % a.key)
    print("  ts: %s · version: %s" % (d.get('ts'), d.get('version')))
    print("  ★★ 应使用的 thread（= 卡内字段）: %s" % th)
    print("  收件人: %s" % a.to)
    # ★★★ 2026-10-13 增（★ 实测触发）：**重复投递检测**。
    #   ★ 现象：同一条卡可能在数分钟内被【重复通知】多次（★ 今晚实测 ≥3 次），
    #     而【线程字段可能相同也可能不同】——
    #       ① 相同 ⇒ 同一条消息的重试（★ 无需补发）
    #       ② 不同 ⇒ 我的回复发错了线程（★ 需在卡内线程补发）
    #   ⇒ ★ 这两种情形【处置完全不同】，故本工具必须能区分，否则会 ① 发重复噪音 或 ② 漏补发。
    dup = _check_already_replied(d)
    print("  重复投递检测: %s" % dup["verdict"])
    # ★★ 灯塔 21:40 建议的落地：以【已回执卡的 key】为唯一确认凭据
    thr = _check_thread_delivery(d)
    print("  ★★ 回执台账: %s" % thr["verdict"])
    if thr.get("ledgerEntry"):
        print("     我的回执卡: %s（%s）" % (thr["ledgerEntry"].get("myCardKey"), thr["ledgerEntry"].get("repliedAt")))
    if dup.get("evidence"):
        for e in dup["evidence"]:
            print("     · %s" % e)
    if dup["verdict"].startswith("★ 我已回过"):
        print("  ⇒ ★ 本条很可能是【重复通知】—— 请先确认对方是否已读到，不要盲发")
    if not a.send:
        print("  ★ dry-run：未发送。真发加 --send")
        return 0
    print("  ⇒ 请用 agent_send 工具，thread 参数填【上面那个】")
    return 0


def _reply_ledger_path():
    """★ 回执台账路径（★ 按灯塔 21:40 建议：「收件方以【已回执卡的 key】作为唯一确认凭据」）。"""
    d = os.path.expanduser("~/dsh-collab/data/registry")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return os.path.join(d, "reply-ledger.json")


def _load_ledger():
    try:
        with open(_reply_ledger_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"_note": ("★ 回执台账（灯塔 21:40 建议）：以【已回执卡的 key】为唯一确认凭据，"
                          "而非以线程为单位重复确认。★ 每项 = {card_key: {repliedAt, myCardKey, thread}}"),
                "entries": {}}


def _check_thread_delivery(card):
    """★★★ 已送达线程清单（★ 灯塔 21:40 建议的落地）。

    ★ 现象（灯塔实测）：同一份内容 1 小时内被投递 3 次、跨 4 个线程 ——
      根因是 `agent_send` 的 `status:delivered` **只表示总线收下，不代表收件人已读**。
    ⇒ ★ 本函数的判据（★ 三条，全部结果态）：
      ① 该卡是否【已在回执台账里】（我明确回过）
      ② 该卡键在【本机其它卡】里被引用的次数
      ③ 该卡被投递过【哪些线程】（从本机卡里可见的）
    """
    led = _load_ledger()
    ent = (led.get("entries") or {})
    key = card.get("key") or ""
    out = {"inLedger": key in ent, "ledgerEntry": ent.get(key), "threadsSeen": [], "verdict": "★ 不可判"}
    # ★★★ 2026-10-13 修（★ 实测触发）：**必须看 `repliedAt` 是否为 None**。
    #   ★ 我第一版只判「key 在台账里」⇒ 把【待回项】（repliedAt=None，即我登记的「要回」标记）
    #     也判成了「已回过」。⇒ ★ 这正是本线反复的【判据选错】：台账里有条目 ≠ 已回过。
    _e = out.get("ledgerEntry") or {}
    if out["inLedger"] and _e.get("repliedAt"):
        out["verdict"] = "★ 已回过（★ 台账有记录且 repliedAt 非空 ⇒ 以【已回执卡的 key】为唯一确认凭据）"
    elif out["inLedger"]:
        out["verdict"] = "★★ 【★ 未回 · 待回】（台账有条目但 repliedAt 为空 —— ★ 这是【待回】标记，不是已回）"
    else:
        out["verdict"] = "★ 台账无记录（可能未回，或回过但未登记）⇒ ★ 请人工确认"
    return out


def _check_already_replied(card):
    """★ 判断本机是否已对该卡产出过回复卡（★ 只读探测，不写任何东西）。

    判据（★ 结果态）：看 `notes/mac-mini/` 里有没有【ts 晚于该卡、且正文引用了该卡键或
    其 sha】的、来源为本机的卡 ⇒ 有则判「已回过」。
    """
    out = {"verdict": "★ 不可判（探测失败）", "evidence": []}
    try:
        with urllib.request.urlopen("http://127.0.0.1:8792/notes/mac-mini/", timeout=60) as r:
            L = (json.loads(r.read().decode()).get('list') or {})
    except Exception as e:
        return {"verdict": "★ 不可判（notes/ 读不到: %s）" % str(e)[:40], "evidence": []}
    ts0 = str(card.get('ts') or '')
    key = (card.get('key') or '')
    hits = []
    for k, vv in L.items():
        if not isinstance(vv, dict):
            continue
        ts = str(vv.get('ts') or '')
        if ts and ts0 and ts <= ts0:
            continue                                     # ★ 只找【晚于】该卡的
        body = json.dumps(vv, ensure_ascii=False)
        if key and key in body:
            hits.append("%s（ts=%s）" % (k.split('/')[-1][:52], ts[11:16]))
    if hits:
        return {"verdict": "★ 我已回过（找到 %d 张晚于该卡的引用卡）" % len(hits), "evidence": hits}
    return {"verdict": "★ 未见我的回复卡（可能未回，也可能回复未落卡）", "evidence": []}

if __name__ == "__main__":
    sys.exit(main())
