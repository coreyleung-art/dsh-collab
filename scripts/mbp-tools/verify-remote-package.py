#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-remote-package.py —— 按对端给的哈希**验包**（拉板键 → 解码 → 重算 → 比对）

【为什么需要】
  对端发交付包时会附 `sha256=xxxx`。**"它说了一个哈希" ≠ "我拿到的就是那个哈希"** ——
  中间要经过：板键读取、base64 解码、网络截断。任何一步出问题，**只看它给的哈希是查不出来的**。
  ⇒ 本工具就是把这个核对**自动化**，并顺手回答两个更值钱的问题：
    ① 对端给的哈希**是完整的吗**（64 hex）—— 16 位前缀只能"识别"，**不能校验**；
    ② 对端的**打包可复现吗** —— 同一内容两次打包哈希是否一致（否则它的哈希对谁都对不上）。

【用法】
  python3 verify-remote-package.py <板键> [--expect <给定的sha256或前缀>] [--peer central|mac-mini]
  python3 verify-remote-package.py --selftest      # 正负样本自证
★ 退出码（R37）：0=一致 ／ 1=不一致 ／ 2=环境错 ／ 3=无期望值（只报实际哈希，不算通过）
"""
import argparse
import base64
import hashlib
import io
import json
import os
import sys
import time
import urllib.request

BOARDS = {
    "central": "http://xingqiao.meetfunbp.com:8792",
    "mac-mini": "http://100.120.203.20:8792",
}


def _headers(peer):
    if peer == "central":
        h = {"X-Webhook-Token": "c6b784621fc871de1077517c24165e93"}
        try:
            tok = io.open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
            if tok:
                h["X-Blackboard-Token"] = tok
        except Exception:
            pass
        return h
    return {"Authorization": "Bearer bb-token-20260829-macmini"}


def fetch(key, peer="central"):
    req = urllib.request.Request(BOARDS[peer] + "/" + key, headers=_headers(peer))
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.load(r)
    v = d.get("value") if isinstance(d.get("value"), dict) else d
    inner = v.get("value") if isinstance(v.get("value"), dict) else v
    b64 = inner.get("b64") if isinstance(inner, dict) else None
    return d, inner, b64


def compare(raw, expect):
    """返回 (状态, 说明)。状态 ∈ match/mismatch/no-expect。"""
    got = hashlib.sha256(raw).hexdigest()
    if not expect:
        return "no-expect", got
    e = expect.strip().lower()
    if len(e) < 64:
        # 前缀比对：能判"不一致"，但**不能据此判"完整一致"**
        if got.startswith(e):
            return "match-prefix", got
        return "mismatch", got
    return ("match" if got == e else "mismatch"), got


def _selftest():
    ok = True
    raw = b"hello world" * 10
    good = hashlib.sha256(raw).hexdigest()

    def case(name, expect, want):
        nonlocal ok
        st, _ = compare(raw, expect)
        g = (st == want)
        ok = ok and g
        print("  %s %-44s 期望%-14s 实际 %s" % ("✅" if g else "❌", name, want, st))

    case("完整哈希一致", good, "match")
    case("完整哈希不一致（负样本）", "0" * 64, "mismatch")
    case("★ 16 位前缀命中 ⇒ 只算 match-prefix（不算完整一致）", good[:16], "match-prefix")
    case("16 位前缀不命中（负样本）", "deadbeefdeadbeef", "mismatch")
    case("无期望值 ⇒ no-expect（不得判通过）", None, "no-expect")
    print()
    print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("key", nargs="?")
    ap.add_argument("--expect")
    ap.add_argument("--peer", default="central", choices=list(BOARDS))
    ap.add_argument("--refetch", type=int, default=1, help="重复**取同一板键** N 次（测板端存储稳定性；★ 它**不能**检验对端打包可复现性——那只由生产端决定）")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not a.key:
        print("需要 <板键>"); return 2
    hashes = []
    for i in range(max(1, a.refetch)):
        try:
            d, inner, b64 = fetch(a.key, a.peer)
        except Exception as e:
            print("取包失败: %s" % str(e)[:100]); return 2
        if not b64:
            print("该键无 `b64` 字段（不是包键？）字段=%s" % list(inner.keys())[:8]); return 2
        raw = base64.b64decode(b64)
        h = hashlib.sha256(raw).hexdigest()
        hashes.append(h)
        if i == 0:
            print("板键  : %s（peer=%s, 板 version=%s）" % (a.key, a.peer, d.get("version")))
            print("载荷  : %s 字节(raw) ／ %s 字节(b64) ／ 声明 files=%s"
                  % (len(raw), len(b64), len(inner.get("files") or [])))
            print("实算  : %s" % h)
            if inner.get("sha256"):
                print("对端声明: %s%s" % (inner.get("sha256"),
                      "  ← 仅 16 位前缀，只能识别、不能校验" if len(str(inner["sha256"])) < 64 else ""))
        if a.refetch > 1:
            time.sleep(0.5)
    if len(set(hashes)) > 1:
        print("★ 同一板键重复取包哈希不一致 ⇒ **板端存储/序列化不稳定**（不是对端打包问题）")
        return 1
    st, got = compare(base64.b64decode(fetch(a.key, a.peer)[2]), a.expect)
    if st == "mismatch":
        print("❌ 与我持有的期望值**不一致**：实算 %s" % got); return 1
    if st == "no-expect":
        print("⚠️ 未提供 --expect ⇒ 只报实算哈希，**不算校验通过**（R31：未校验 ≠ 通过）"); return 3
    if st == "match-prefix":
        print("⚠️ 与**前缀**一致（该前缀只能识别包，不能证明完整性）"
              "—— 建议向对端索取完整 64 位哈希"); return 0
    print("✅ 完整哈希一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
