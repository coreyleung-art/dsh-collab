#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""inbox-state-tagger.py — 给 inbox 条目补 CAHAC `state`（S1 的实现侧）

为什么需要：
  CAHAC §7.5 定了【五个时点与唯一责任方】，但**实现侧缺一个调用点** ——
  `~/.dsh/inbox` 的写入者是既有机制（`mac-mini-inbox-watch` / `central-wake` 等），
  给它们加写 `state` 的动作需另授权。
  ⇒ 本工具是那块【可被调用的拼图】，**不自动运行、不自行接入任何 daemon**。

★ 安全约束（本工具的设计前提）：
  ① **默认 `--dry-run`**：不做任何写入；要看效果必须显式 `--apply`
  ② **只补不覆盖**：已有 `state` 字段的条目**一律不动**（避免把同名字段改成协议状态）
  ③ **只认合法枚举**：写入值必须是 CAHAC §7.2 的 7 态之一
  ④ **写前备份 + 写后回读**：每条改动都留 `.state-tag.bak`，并回读确认

用法：
  python3 inbox-state-tagger.py                 # dry-run：只报将改哪些
  python3 inbox-state-tagger.py --apply         # 真写（需授权者调用）
  python3 inbox-state-tagger.py --since 20261009  # 只处理该日期之后的条目
  python3 inbox-state-tagger.py --selftest      # 自测
退出码：0 正常 · 1 有异常 · 2 用法错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

import argparse
import json
import os
import shutil
import sys
import time

INBOX = os.path.expanduser("~/.dsh/inbox")
LEGAL = ["todo", "claimed", "done", "verified", "blocked", "failed", "timeout"]
# ★ 推断规则（保守）：只对【没有 state 字段】的条目给一个初始值。
#   默认 todo = 「已生成、待处理」（§7.5 时点① 由发卡方写；此处为补写）。
DEFAULT_STATE = "todo"


def candidates(inbox=None, since=None):
    """列出候选条目：有 JSON、是 dict、**没有 state 字段**、（可选）mtime >= since。"""
    d = inbox or INBOX
    out = []
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json") or name.startswith("."):
            continue
        path = os.path.join(d, name)
        try:
            with open(path, encoding="utf-8") as f:
                obj = json.load(f)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if "state" in obj:            # ★ 只补不覆盖
            continue
        if since:
            dt = time.strftime("%Y%m%d", time.localtime(os.path.getmtime(path)))
            if dt < str(since):
                continue
        out.append((name, path))
    return out


def apply_one(path, state=DEFAULT_STATE, backup=True):
    """写一条：备份 → 改 → 回读。返回 (ok, 说明)。"""
    if state not in LEGAL:
        return False, "非法枚举：%s" % state
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if "state" in obj:
        return False, "已存在 state，未覆盖（只补不覆盖）"
    if backup:
        shutil.copy2(path, path + ".state-tag.bak")
    obj["state"] = state
    obj["_state_written_by"] = "inbox-state-tagger"
    obj["_state_written_at"] = int(time.time())
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    # ★ 写后必读
    with open(path, encoding="utf-8") as f:
        back = json.load(f)
    return (back.get("state") == state), ("回读 state=%s" % back.get("state"))


def selftest():
    import tempfile
    fails = neg = pos = 0

    def c(name, cond, detail="", kind="pos"):
        nonlocal fails, neg, pos
        if kind == "pos":
            pos += 1
        else:
            neg += 1
        good = bool(cond)
        print("  %s %-6s %-40s %s" % ("✅" if good else "❌", kind, name, detail))
        if not good:
            fails += 1

    print("== inbox-state-tagger selftest ==")
    tmp = tempfile.mkdtemp(prefix="tagger-")
    os.makedirs(tmp, exist_ok=True)
    # 正例：无 state 的条目应被列为候选
    a = os.path.join(tmp, "a.json")
    json.dump({"from": "x", "to": "y"}, open(a, "w"))
    c("无 state ⇒ 列为候选", len(candidates(tmp)) == 1, "1 条")
    # 负例：已有 state 的条目【不得】被列为候选
    b = os.path.join(tmp, "b.json")
    json.dump({"from": "x", "state": {"demo": 1}}, open(b, "w"))
    c("已有 state（同名字段）⇒ 不列候选", len(candidates(tmp)) == 1,
      "仍 1 条（只补不覆盖）", kind="neg")
    # 正例：apply 一条
    ok, why = apply_one(a, "todo")
    c("apply 后回读一致", ok and json.load(open(a)).get("state") == "todo", why)
    # 负例：重复 apply 必须被拒
    ok2, why2 = apply_one(a, "todo")
    c("重复 apply ⇒ 拒（不覆盖）", ok2 is False, why2[:30], kind="neg")
    # 负例：非法枚举必须被拒
    cc = os.path.join(tmp, "c.json")
    json.dump({"from": "x"}, open(cc, "w"))
    ok3, why3 = apply_one(cc, "BOGUS")
    c("非法枚举 ⇒ 拒", ok3 is False, why3[:30], kind="neg")
    # 正例：备份文件已生成
    c("备份已生成", os.path.exists(a + ".state-tag.bak"), ".state-tag.bak")
    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条" % (fails, neg, pos))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="给 inbox 条目补 CAHAC state（默认 dry-run）")
    ap.add_argument("--apply", action="store_true", help="真写（默认只演练）")
    ap.add_argument("--since", default=None, help="只处理该日期(YYYYMMDD)之后的条目")
    ap.add_argument("--state", default=DEFAULT_STATE, choices=LEGAL, help="写入的状态")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    cand = candidates(since=a.since)
    total = len([n for n in os.listdir(INBOX) if n.endswith(".json") and not n.startswith(".")])
    res = {"mode": "apply" if a.apply else "dry-run",
           "inbox_total": total, "candidates": len(cand),
           "state_to_write": a.state, "since": a.since,
           "would_change": [n for n, _ in cand[:10]]}
    if a.apply:
        done = okn = 0
        for name, path in cand:
            ok, why = apply_one(path, a.state)
            done += 1
            okn += 1 if ok else 0
        res["applied"] = done
        res["succeeded"] = okn
    # ★ 写后自报合规率变化
    res["note"] = ("dry-run：未写任何文件。加 --apply 才真写（需授权者调用）。"
                   if not a.apply else "已写；下一次 cahac-compliance-report 会反映新合规率")
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json
          else "\n".join("%s: %s" % (k, v) for k, v in res.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
LOG = os.path.join(COLLAB, "logs", "inbox-state-tagger.log")


def log(msg):
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass
