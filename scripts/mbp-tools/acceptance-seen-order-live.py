#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重启后**决定性**验收（二）：seen 后置修复是否真在运行进程里生效。

不变量（G28）：**注入失败不得写去重键**（写了下一次同内容事件会被判 dup ⇒ 永久丢）。
直接观测点：`~/.dsh/central-inbox-seen.json`（去重键集合，条目形如 `<key>#<内容指纹>`，防抖 30s 落盘）。

做法（一对正负样本，同样"主动制造事件"）：
  ① **失败注入**卡：`to` 用一个**解析不到**的目标 ⇒ 期望日志 `注入目标为 null，跳过`
     ⇒ 期望 seen 表里**没有**该 key（修复版行为）；旧版会**有**（失败也记号）。
  ② **成功注入**卡（阴性对照）：正常目标 ⇒ 期望日志 `📩 注入` ⇒ 期望 seen 表里**有**该 key
     ⇒ 证明"该写的时候仍会写"（否则"永远不写 seen"也能假通过 —— 类别 C）。

只有 ①②**结论相反**才说明修复真在运行进程里。
"""
import json, os, subprocess, sys, time, urllib.request

BASE = "http://xingqiao.meetfunbp.com:8792"
TOK = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
H = {"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK, "Content-Type": "application/json"}
LOG = os.path.expanduser("~/.dsh/central-inbox.log")
SEEN = os.path.expanduser("~/.dsh/central-inbox-seen.json")
OTHER_FROM = "session-ab866871-b8ab-4377-8c85-add79d8920d2"


def put(key, to, tag):
    now = int(time.time() * 1000)
    card = {"from": OTHER_FROM, "to": to, "type": "note",
            "subject": "【自测·可忽略】seen 后置验收 %s" % tag,
            "body": "验收用例 %s（%s）—— 判据样本，无需处理。" % (tag, key),
            "sent_at_epoch_ms": now, "ts": now // 1000, "reply_required": False}
    req = urllib.request.Request(BASE + "/" + key, data=json.dumps(card, ensure_ascii=False).encode(),
                                 method="PUT", headers=H)
    return urllib.request.urlopen(req, timeout=15).status


ts = int(time.time())
k_fail = "notes/mbp/selftest-seenorder-fail-%d" % ts
k_ok = "notes/mbp/selftest-seenorder-ok-%d" % ts

print("══ ① 失败注入卡（to 不可解析）══")
print("  PUT", k_fail, "→ to=zzz-unresolvable-node-xyz :", put(k_fail, "zzz-unresolvable-node-xyz", "失败路径"))
time.sleep(6)
print("══ ② 成功注入卡（阴性对照）══")
print("  PUT", k_ok, "→ to=mbp :", put(k_ok, "mbp", "成功路径"))

print("\n  等待 35s 让 seen 防抖落盘 …")
time.sleep(35)

tail = subprocess.run(["tail", "-n", "300", LOG], capture_output=True, text=True).stdout
seen = json.load(open(SEEN, encoding="utf-8"))
seen_blob = "\n".join(map(str, seen))

fail_log = [l for l in tail.splitlines() if k_fail.split("/")[-1] in l]
ok_log = [l for l in tail.splitlines() if k_ok.split("/")[-1] in l]
print("\n══ ① 失败卡日志 ══")
for l in (fail_log or ["  (无该项目日志)"]):
    print("  " + l[-155:])
print("══ ② 成功卡日志 ══")
for l in (ok_log or ["  (无该项目日志)"]):
    print("  " + l[-155:])

fail_null = any("注入目标为 null" in l for l in fail_log)
fail_injected = any("📩 注入" in l for l in fail_log)
ok_injected = any("📩 注入" in l for l in ok_log)
fail_in_seen = k_fail.split("/")[-1] in seen_blob
ok_in_seen = k_ok.split("/")[-1] in seen_blob

print("\n══ seen 表观测（条目数 %d）══" % len(seen))
print("  失败卡 key 在 seen 中: %s（期望 False）" % fail_in_seen)
print("  成功卡 key 在 seen 中: %s（期望 True）" % ok_in_seen)

ok = True


def ck(name, cond):
    global ok
    ok = ok and cond
    print("  %s %s" % ("✅" if cond else "❌", name))


print("\n══ 判定 ══")
ck("失败路径确实走到「目标为 null 跳过」", fail_null and not fail_injected)
ck("**失败卡未写 seen**（= seen 后置修复在运行进程里生效）", not fail_in_seen)
ck('成功卡写了 seen（阴性对照，证明不是「永远不写」）', ok_in_seen and ok_injected)
ck("两者结论相反 ⇒ 判据有判别力", (not fail_in_seen) and ok_in_seen)
print("\n  ⇒ " + ("✅ seen 后置修复**确实在运行进程里生效**" if ok else "❌ 未生效/判据无判别力 —— 别当成功"))
sys.exit(0 if ok else 1)
