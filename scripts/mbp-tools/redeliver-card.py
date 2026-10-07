#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重投卡（带**有界重试** + 逐次读对端日志验证）—— 对端 boot 窗口会丢卡（G30）。

为什么需要重试：对端 `agentBus.list()` 在重启后短暂为空 ⇒ 连**精确会话 id** 也判
`unresolvable` ⇒ `target=null` ⇒ 丢弃；其 0.2.11-A 修复只保证「失败不写 seen」，
**但没有任何东西触发重试** ⇒ 卡就此静默留在板上没人取。

做法：把要重投的卡从**板上读回**（不手抄），加一行重投标记（**必须改内容**：
对端去重键是内容指纹、不含 version ⇒ 同内容重投会被判 dup、不会注入），
换**新键**发布；每次发布后 `ssh` 读对端日志判定结局；失败则等待再试（≤3 次）。
"""
import json, os, subprocess, sys, time, urllib.request
from importlib.machinery import SourceFileLoader

pap = SourceFileLoader("pap", os.path.expanduser("~/dsh-collab/tools/publish-and-point.py")).load_module()

SRC_KEY = sys.argv[1] if len(sys.argv) > 1 else "notes/mac-mini/card-1791078593"
PEER = "session-fa1f9150-c949-401f-ba8c-d265f6221676"
HOST = "coreyleung@100.120.203.20"
BASE = "http://xingqiao.meetfunbp.com:8792"
TOK = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
H = {"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK}


def get(key):
    r = urllib.request.Request(BASE + "/" + key, headers=H)
    d = json.load(urllib.request.urlopen(r, timeout=15))
    v = d.get("value", {})
    return d, (v.get("value", v) if isinstance(v, dict) else v)


def peer_log(key):
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOST,
           "grep '%s' ~/.dsh/central-inbox.log | tail -4" % key.split("/")[-1]]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    return r.stdout.strip()


d0, card0 = get(SRC_KEY)
print("源卡:", SRC_KEY, "| version=", d0.get("version"), "| body=", len(str(card0.get("body", ""))), "字符")

for attempt in range(1, 4):
    card = {k: v for k, v in card0.items()
            if k not in ("sent_at_iso", "sent_at_epoch_ms", "version")}
    card["body"] = ("【重投 #%d · 你侧 boot 窗口丢弃】本卡首次投递时你侧 `agentBus.list()` 为空，"
                    "判 `unresolvable` ⇒ `target=null` ⇒ 丢弃（你日志实测）。内容未改，仅加此行以便通过去重。\n\n"
                    % attempt) + str(card0.get("body", ""))
    card["reply_required"] = True
    ok, key, detail = pap.publish_and_point("notes/mac-mini/", str(card.get("subject", "重投"))[:100],
                                            card, notify=["mac-mini"])
    print("\n--- 第 %d 次发布 ---" % attempt)
    print("  key =", key, "| boards =", detail.get("boards"))
    time.sleep(12)
    lg = peer_log(key)
    print("  对端日志:")
    for l in (lg.splitlines() or ["(无该键记录 — 可能未推达)"]):
        print("   ", l[-150:])
    if "queued" in lg or "delivered" in lg or "duplicate" in lg:
        print("  ✅ 本轮已进对端队列（未出现 null 跳过）")
        print("  ⇒ 最终键:", key)
        sys.exit(0)
    print("  ⚠️ 仍是 null/无记录 ⇒ 等待 25s 后重试")
    time.sleep(25)
print("\n❌ 3 次均未投达 —— 对端会话可能仍不在线（需其会话上线后再投）")
sys.exit(1)
