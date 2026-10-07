#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-delivery.py —— 跨端「送达」验证器（把判据放到**对端**）

【为什么必须存在】（2026-10-03 实测事故，代价：3 张卡全部静默丢失，用户才发现）
  我发出卡片后做了「双板写入 + 逐板回读断言」，全 ✅，于是当成"已送达"。
  但随后用户指出「**星桥根本没有收到**」。到对端机器查日志，真相是：
      📩 注入 mac-mini: <key> → **null** [central] queued      ← 三张卡全这样
      📩 注入 mac-mini: <key> → session-fa1f9150-… delivered   ← 对照组（能解析 to 的卡）
  ⇒ **本地「写成功 + 回读成功」完全不能证明送达。**
     本地断言只能证明"我写进了板子"；**送达与否的观测点在对端**。
  ⇒ 一句话：**端到端投递的判据在对端，不在本地。**

【它怎么判】读对端 `~/.dsh/central-inbox.log` 里该 key 的结局行，按结局判定：
    delivered / duplicate        → ✅ 端到端确认送达
    null / queued                → ❌ **未送达**（收件人解析失败或仅排队 —— 静默丢失的签名）
    日志里查不到                  → ⚠️ **无法确认**（不是"没送到"）
  ★ 最后一条是 R31/R035 的落地：**"没观测到" ≠ "不存在"**。
    所以"查不到"**绝不判成功**，只判"无法确认"，并给下一步（加长等待 / 换判据 / 找对端确认）。

【用法】
  python3 verify-delivery.py --key notes/mac-mini/card-xxx [--peer mac-mini] [--wait 30]
  python3 verify-delivery.py --selftest              # 正负样本自证（不联网）
  python3 verify-delivery.py --last-sent             # 验证我最近发出的那张卡

【覆盖范围（★ 边界，别过度信任）】
  · `ssh:` 探针需要免密 SSH 可达；**不可达时判「无法确认」，不判成功**。
  · 只读对端日志的**结局行**；对端日志被轮转/清空时同为"无法确认"。
  · 它验证「卡是否进入对端会话」，**不验证对端是否已读/已处理**。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

# 对端 → 探针。ssh 可达则用 ssh 读日志；否则 label 为 None 表示"无探针 ⇒ 只能判无法确认"。
PEERS = {
    "mac-mini": {"ssh": "coreyleung@100.120.203.20", "log": "~/.dsh/central-inbox.log"},
    "i9":       {"ssh": "coreyleung@100.118.15.71",  "log": "~/.dsh/central-inbox.log"},
    "mbp":      {"ssh": "coreyleung@100.112.111.120", "log": "~/.dsh/central-inbox.log"},
}

SENT_RE = re.compile(r"注入\s+\S+:\s*(\S+)\s*→\s*(\S+)\s*\[(\w+)\]\s*(\w+)")


def parse_outcomes(log_text, key):
    """从对端日志文本里抽出该 key 的全部结局行。返回 [(target, verdict)]。"""
    out = []
    for line in log_text.splitlines():
        if key not in line:
            continue
        m = SENT_RE.search(line)
        if m:
            out.append((m.group(2), m.group(4)))     # (解析出的注入目标, 结局)
    return out


def judge(outcomes):
    """按结局判定 (status, level)。status ∈ delivered/unroutable/unconfirmed。

    ★★ 判据修正（2026-10-03 用**真实负样本**测出来的自身缺陷 —— 我第一版判错了）：
      第一版写 `any(v in ("delivered","duplicate")) ⇒ delivered`。
      实测拿「本次事故卡」回放，对端结局是 `('null','queued')` + `('null','duplicate')`
      ⇒ 第一版**判成「确认送达」** —— **正好把事故卡判成成功**，等于这个判据在最关键处失效。
      根因：**`duplicate` 只表示「去重命中」，不是送达证据** ——
        它与"上一次尝试是否送到"完全无关（事故卡的 duplicate 正是"又一次排队"的重复）。
      ⇒ 改为**只把「有真实注入目标 且 结局=delivered」当送达证据**；
        `duplicate` 单独出现**不构成证据**（判 unconfirmed，不得判成功）。
      ★ 这就是 R31 在我**自己的新判据**上复现：**判据必须在真实正负样本上验过**
        —— 尤其要拿"应该判失败的那种输入"去验（我正是靠这一步发现它判错）。
    """
    if not outcomes:
        return "unconfirmed", "⚠️"
    has_target = lambda t: t not in ("null", "None", "")
    evidence_delivered = any(has_target(t) and v == "delivered" for t, v in outcomes)
    # ★ 新增 pending：**目标已解析**但排队待唤醒（对端 0.2.11「排完整 id 待唤醒·不丢卡」的形态）
    evidence_pending = any(has_target(t) and v == "queued" for t, v in outcomes)
    evidence_unroutable = any(not has_target(t) for t, v in outcomes)
    if evidence_delivered:
        return "delivered", "✅"
    if evidence_unroutable:
        return "unroutable", "❌"
    if evidence_pending:
        return "pending", "⏳"
    return "unconfirmed", "⚠️"


def fetch_log(peer, limit=400):
    """读对端日志尾部。返回 (text|None, note)。不可达 ⇒ None（**不判成功**）。"""
    cfg = PEERS.get(peer)
    if not cfg:
        return None, "未知对端 %s（无探针）" % peer
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", cfg["ssh"],
           "tail -%d %s 2>/dev/null" % (limit, cfg["log"])]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None, "ssh 返回 %d（%s）" % (r.returncode, (r.stderr or "").strip()[:60])
        return r.stdout, "ssh ok"
    except Exception as e:
        return None, "ssh 失败: %s" % str(e)[:60]


def verify(key, peer, wait=0, poll_every=6):
    t0 = time.time()
    note = ""
    while True:
        text, note = fetch_log(peer)
        if text is not None:
            outcomes = parse_outcomes(text, key)
            status, level = judge(outcomes)
            if status != "unconfirmed" or time.time() - t0 >= wait:
                return status, level, outcomes, note
        elif time.time() - t0 >= wait:
            return "unconfirmed", "⚠️", [], note
        if time.time() - t0 >= wait:
            text2, _ = fetch_log(peer)
            if text2 is not None:
                outcomes = parse_outcomes(text2, key)
                status, level = judge(outcomes)
                return status, level, outcomes, note
            return "unconfirmed", "⚠️", [], note
        time.sleep(poll_every)


# ─────────────────────────── 正负样本自证 ───────────────────────────
def _selftest():
    print("verify-delivery 自证（判据必须能区分「送达 / 未送达 / 无法确认」）")
    ok = True

    def case(name, text, key, want_status):
        nonlocal ok
        st, lv = judge(parse_outcomes(text, key))
        good = (st == want_status)
        ok = ok and good
        print("  %s %-46s 期望 %-12s 实际 %-12s" % ("✅" if good else "❌", name, want_status, st))

    K = "notes/mac-mini/card-x"
    case("对端日志 = delivered（实测形态）",
         "[10:13:13] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] delivered" % K, K, "delivered")
    case("delivered + duplicate（同一 key 多次注入，含真送达）",
         "[10:13:13] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] delivered\n"
         "[10:13:22] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] duplicate" % (K, K), K, "delivered")
    case("★ 仅 duplicate（无 delivered 证据）⇒ 不得判成功，须 unconfirmed",
         "[10:13:22] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] duplicate" % K, K, "unconfirmed")
    case("★ target 已解析 + queued ⇒ **pending**（不是丢卡）",
         "[22:30:00] 📩 注入 mac-mini: %s → session-fa1f9150-c949 [central] queued" % K, K, "pending")
    case("★ target=null + queued ⇒ unroutable（**解析失败才是真丢**）",
         "[09:59:48] 📩 注入 mac-mini: %s → null [central] queued" % K, K, "unroutable")
    case("★ 对端日志 = null + queued（事故形态 ⇒ 必须判未送达）",
         "[09:59:48] 📩 注入 mac-mini: %s → null [central] queued" % K, K, "unroutable")
    case("★★ 事故卡**真实形态**：null/queued + null/duplicate ⇒ 必须 unroutable（我第一版在此判错成 delivered）",
         "[09:59:48] 📩 注入 mac-mini: %s → null [central] queued\n"
         "[09:59:58] 📩 注入 mac-mini: %s → null [central] duplicate" % (K, K), K, "unroutable")
    case("对端日志完全没有该 key ⇒ 无法确认（**不得判成功**）",
         "[10:00:00] 📩 注入 mac-mini: notes/别的卡 → session-x delivered", K, "unconfirmed")
    case("对端日志为空（日志被轮转）⇒ 无法确认",
         "", K, "unconfirmed")
    print()
    print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def _last_sent():
    """从我的发布记录（本机板 notes/mac-mini/ 最新）取最近一张卡 —— 便于一键复核。"""
    try:
        import urllib.request
        tok = open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
        req = urllib.request.Request("http://xingqiao.meetfunbp.com:8792/notes",
                                     headers={"X-Blackboard-Token": tok, "Authorization": "Bearer " + tok})
        lst = json.load(urllib.request.urlopen(req, timeout=15)).get("list") or {}
        mine = [(v.get("ts") or "", k) for k, v in lst.items()
                if k.startswith("notes/mac-mini/") and "card-1791" in k]
        mine.sort(reverse=True)
        return mine[0][1] if mine else None
    except Exception as e:
        print("  取最近卡失败: %s" % str(e)[:80])
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key")
    ap.add_argument("--peer", default="mac-mini")
    ap.add_argument("--wait", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--last-sent", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    key = a.key or (_last_sent() if a.last_sent else None)
    if not key:
        print("需要 --key 或 --last-sent"); return 2
    status, level, outcomes, note = verify(key, a.peer, wait=a.wait)
    print("对端送达验证 · peer=%s" % a.peer)
    print("  key : %s" % key)
    print("  结局: %s" % (outcomes or "（对端日志中无该 key）"))
    print("  探针: %s" % note)
    if status == "delivered":
        print("  %s 端到端**确认送达**（对端会话已收到）" % level)
        return 0
    if status == "pending":
        print("  %s **已解析但排队待唤醒** —— 目标已定位（%s），投递待对端唤醒。"
              % (level, outcomes[0][0] if outcomes else "?"))
        print("     ⇒ 这**不是**丢卡（与 `null`+queued 的解析失败不同）；可稍后用 --wait 复验。")
        return 3
    if status == "unroutable":
        print("  %s **未送达** —— 收件人解析失败/仅排队（静默丢失签名）。" % level)
        print("     ⇒ 检查 `to` 是否可解析：必须是 中枢别名 / 角色名 / **完整会话 id**；")
        print("       节点别名（mac-mini/mbp/i9）会被对端 `resolveTargetId` 判为 unresolvable。")
        return 1
    print("  %s **无法确认**（%s）—— ★ 这**不是**「已送达」。" % (level, note or "对端日志无该 key"))
    print("     ⇒ 「没观测到」≠「不存在」：请加长等待（--wait）、或请对端确认、或换判据。")
    return 2


if __name__ == "__main__":
    sys.exit(main())
