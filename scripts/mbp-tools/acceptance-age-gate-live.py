#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重启后**决定性**验收：时效门是否真在运行进程里生效（一对正负样本）。

为什么不能只看代码：hazards **D 类（热替换延迟暴露）** —— 磁盘改了、跑着的进程可能还是旧的。
"日志里没出现丢弃" 也不能证明它没生效（没重放就没丢弃）—— 那是 **R035：没观测到 ≠ 不存在**。
⇒ 必须**主动制造两个事件**：
   ① **超龄卡**（ts = 48h 前）→ 期望：日志 `⏳ 丢弃陈旧卡` 且**不注入**
   ② **新鲜卡**（ts = 现在）→ 期望：正常 `📩 注入`
   两者必须**结论相反**，否则判据无判别力（若两个都不注入 ⇒ 说明是别的原因，不是时效门）。

落点用 `notes/mbp/`（**只有我的 inbox 监听**；对端监听 notes/mac-mini/ 与 notes/collab/ ⇒ 不打扰对端）。
"""
import json, os, subprocess, sys, time, urllib.request

BASE = "http://xingqiao.meetfunbp.com:8792"
TOK = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
H = {"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK, "Content-Type": "application/json"}
LOG = os.path.expanduser("~/.dsh/central-inbox.log")
ME = "session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
OTHER_FROM = "session-ab866871-b8ab-4377-8c85-add79d8920d2"   # 非本人（避开自回声判定）


def put(key, ts_ms, tag):
    card = {
        "from": OTHER_FROM, "to": "mbp", "type": "note",
        "subject": "【自测·可忽略】时效门验收 %s" % tag,
        "body": "验收用例：%s（%s）。本卡是判据样本，无需处理。" % (tag, key),
        "sent_at_epoch_ms": ts_ms, "ts": ts_ms // 1000, "reply_required": False,
    }
    req = urllib.request.Request(BASE + "/" + key, data=json.dumps(card, ensure_ascii=False).encode(),
                                 method="PUT", headers=H)
    r = urllib.request.urlopen(req, timeout=15)
    return r.status


def logtail(n=400):
    return subprocess.run(["tail", "-n", str(n), LOG], capture_output=True, text=True).stdout


now = int(time.time() * 1000)
k_old = "notes/mbp/selftest-agegate-old-%d" % (now // 1000)
k_new = "notes/mbp/selftest-agegate-new-%d" % (now // 1000)

print("══ 投放两个事件（同一路径前缀、同一 from/to，唯一差别是时间戳）══")
print("  ① 超龄卡 ts = 48h 前 :", k_old, "| PUT", put(k_old, now - 48 * 3600 * 1000, "超龄"))
time.sleep(6)
print("  ② 新鲜卡 ts = 现在    :", k_new, "| PUT", put(k_new, now, "新鲜"))
time.sleep(8)

tail = logtail()
old_lines = [l for l in tail.splitlines() if k_old.split("/")[-1] in l]
new_lines = [l for l in tail.splitlines() if k_new.split("/")[-1] in l]

print("\n══ ① 超龄卡的日志（期望：丢弃陈旧卡 / 不许有注入行）══")
for l in (old_lines or ["  (无该项目日志)"]):
    print("  " + l[-160:])
print("\n══ ② 新鲜卡的日志（期望：有 📩 注入行）══")
for l in (new_lines or ["  (无该项目日志)"]):
    print("  " + l[-160:])

old_dropped = any("丢弃陈旧卡" in l for l in old_lines)
old_injected = any("📩 注入" in l for l in old_lines)
new_injected = any("📩 注入" in l for l in new_lines)

print("\n══ 判定 ══")
ok = True


def ck(name, cond):
    global ok
    ok = ok and cond
    print("  %s %s" % ("✅" if cond else "❌", name))


ck("超龄卡被时效门丢弃（日志有「丢弃陈旧卡」）", old_dropped)
ck("超龄卡**没有**被注入", not old_injected)
ck("新鲜卡**正常注入**（阴性对照）", new_injected)
ck("两者结论相反 ⇒ 判据有判别力", (old_dropped and not old_injected) and new_injected)
print("\n  ⇒ " + ("✅ 时效门在运行进程里**确实生效**" if ok else "❌ 未生效/判据无判别力 —— 别当成功"))
sys.exit(0 if ok else 1)
