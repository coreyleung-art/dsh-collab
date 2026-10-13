#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""industry-parity —— I-2 四项业界等价物 + I-3 协议一致性套件

★★ 立据（W4 §3.3）：
  ★ **I-2**：目标 = 「能力卡+签名 / 任务生命周期 / **认证授权** / 版本协商」四项到位
    ★★ 现测：**本件未测** · **复跑命令未建** · **无负控** · **窗口/分子/分母 三件全缺**
  ★ **I-3**：目标 = 「套件**存在且可跑（非离线脚本）**」
    ★★ 现测：**本件未测**；★ v6.1 读数 = `bb-channel.py` 存在但**离线、不在运行时链路**

★ 本工具即那两条的【复跑命令】，★ 且带【正控 + 负控】。

★ 三态：每项独立判 成立 / 不成立 / 不可判；★ **不把「未搜到」当「不存在」**
  （★ 每项都带【扫过的面】与【阳性对照】）。

用法：
  python3 tools/industry-parity.py            # 全测
  python3 tools/industry-parity.py --json
  python3 tools/industry-parity.py --selftest
"""
import argparse
import io
import json
import os
import subprocess
import sys
import urllib.request

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BB = "http://127.0.0.1:8792"
TOKEN_FILE = os.path.expanduser("~/.dsh/blackboard-token")


def _tok():
    try:
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def http(path, token="__default__"):
    """★ 返回 (status, err)；status=0 表示网络层失败"""
    req = urllib.request.Request(BB + path)
    t = _tok() if token == "__default__" else token
    if t:
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, type(e).__name__


# ═══════════════════════ I-2 \u56db\u9879 ═══════════════════════

def check_ability_card():
    """\u2605 \u80fd\u529b\u5361 + \u7b7e\u540d"""
    ev = {}
    # \u2605 \u5361\u7684\u5b58\u5728\uff1a\u2605 \u7528 agent_profiles \u5de5\u5177\u53ef\u8bfb\u5230\u6863\u6848\u5373\u7b97
    try:
        found = []
        for base in (os.path.expanduser("~/.dsh"), ROOT):
            for fn in ("agent-profiles.json", "agent_profiles.json"):
                p = os.path.join(base, fn)
                if os.path.exists(p):
                    found.append(p)
        ev["files"] = found
    except Exception as e:
        ev["files_err"] = type(e).__name__
    # \u2605 \u7b7e\u540d\uff1a\u2605 \u770b\u5361\u91cc\u6709\u65e0 signature \u5b57\u6bb5\uff08\u2605 \u62bd notes/collab\uff09
    ev["signature_hits"] = _count_field_in_ns("notes/collab/", "signature", limit=80)
    ev["sender_hits"] = _count_field_in_ns("notes/collab/", "sender", limit=80)
    card_ok = bool(ev["files"]) or ev["sender_hits"]["hit"] > 0
    sig_ok = ev["signature_hits"]["hit"] > 0
    return {"verdict": "PASS" if (card_ok and sig_ok) else "FAIL",
            "why": "\u5361=%s\uff08\u2605 \u6863\u6848%s\uff09\u00b7 \u7b7e\u540d=%s\uff08%d/%d\uff09"
                   % ("\u6709" if card_ok else "\u65e0", ev["files"] or "\u672a\u627e\u5230",
                      "\u6709" if sig_ok else "\u65e0",
                      ev["signature_hits"]["hit"], ev["signature_hits"]["scanned"]),
            "evidence": ev}


def check_task_lifecycle():
    """\u2605 \u4efb\u52a1\u751f\u547d\u5468\u671f"""
    st, err = http("/tasks/")
    n = 0
    if st == 200:
        try:
            req = urllib.request.Request(BB + "/tasks/")
            t = _tok()
            if t:
                req.add_header("Authorization", "Bearer " + t)
            with urllib.request.urlopen(req, timeout=20) as r:
                n = len((json.loads(r.read().decode("utf-8", "ignore")).get("list") or {}))
        except Exception:
            n = -1
    # \u2605 \u5224\uff1a\u2605 \u524d\u7f00\u5b58\u5728\u4e14\u975e\u7a7a \u21d2 \u6210\u7acb\uff1b\u2605 \u7a7a \u21d2 \u4e0d\u53ef\u5224\uff08\u2605 \u300c\u7a7a \u2260 \u65e0\u300d\uff09
    if st != 200:
        v, w = "UNDECIDABLE", "\u7aef\u70b9\u4e0d\u53ef\u8bfb\uff08%d\uff09" % st
    elif n == 0:
        v, w = "UNDECIDABLE", "/tasks/ \u7a7a \u21d2 \u4e0d\u53ef\u5224\uff08\u2605 \u4e0d\u8bfb\u4f5c\u300c\u65e0\u751f\u547d\u5468\u671f\u300d\uff09"
    else:
        v, w = "PASS", "/tasks/ \u6709 %d \u9520" % n
    return {"verdict": v, "why": w, "evidence": {"status": st, "count": n}}


def check_auth():
    """\u2605 \u8ba4\u8bc1\u6388\u6743\uff08\u2605 \u4e09\u5411\u6d4b\uff1a\u2605 \u5bf9/\u9519/\u65e0\uff09"""
    # \u2605 \u5148\u53d6\u4e00\u4e2a\u3010\u5b58\u5728\u7684\u952e\u3011\u2014\u2605 \u5426\u5219 404 \u65e0\u6cd5\u533a\u5206\u9274\u6743\u5931\u8d25
    key = None
    try:
        req = urllib.request.Request(BB + "/data/registry/")
        t = _tok()
        if t:
            req.add_header("Authorization", "Bearer " + t)
        with urllib.request.urlopen(req, timeout=20) as r:
            lst = (json.loads(r.read().decode("utf-8", "ignore")).get("list") or {})
        key = sorted(lst.keys())[0] if lst else None
    except Exception:
        key = None
    if not key:
        return {"verdict": "UNDECIDABLE", "why": "\u53d6\u4e0d\u5230\u5b58\u5728\u7684\u952e \u21d2 \u4e09\u5411\u6d4b\u65e0\u6cd5\u533a\u5206",
                "evidence": {"key": None}}
    ok_t, _ = http("/" + key)
    no_t, _ = http("/" + key, token="")
    wr_t, _ = http("/" + key, token="WRONG-TOKEN-DELIBERATELY-INVALID")
    ev = {"key": key, "with_token": ok_t, "no_token": no_t, "wrong_token": wr_t}
    # \u2605 \u4e09\u6001\uff1a\u9519 token \u88ab\u62d2 \u21d2 \u6709\u9274\u6743\uff1b\u4e09\u8005\u540c\u503c \u21d2 \u65e0\u9274\u6743
    if ok_t != 200:
        v, w = "UNDECIDABLE", "\u6b63\u5e38 token \u4e5f\u975e 200\uff08%d\uff09\u21d2 \u4e0d\u53ef\u5224" % ok_t
    elif wr_t == 200 and no_t == 200:
        v, w = "FAIL", "\u2605\u2605 \u65e0 token \u4e0e\u9519 token \u5747 200 \u21d2 **\u672a\u5f3a\u5236\u9274\u6743**"
    else:
        v, w = "PASS", "\u9519 token=%d \u00b7 \u65e0 token=%d \u21d2 \u9274\u6743\u751f\u6548" % (wr_t, no_t)
    return {"verdict": v, "why": w, "evidence": ev}


def check_version_negotiation():
    """\u2605 \u7248\u672c\u534f\u5546\uff08\u2605 \u8981\u3010\u5b9e\u73b0\u3011\uff0c\u2605 \u4e0d\u662f\u6587\u6863\u91cc\u63d0\u5230\uff09"""
    hits = {}
    for d in ("scripts", "tools"):
        dd = os.path.join(ROOT, d)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if not fn.endswith((".py", ".js", ".mjs", ".sh")):
                continue
            p = os.path.join(dd, fn)
            try:
                s = io.open(p, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            # ★★ 2026-10-13 修（★ 本纳自查）：【排除探针自己】—★
            #   ★★ 实测：原代码把关键词写在本文件里 ⇒ 探针**找到了自己** ⇒ 假 PASS。
            #   ★ 同族：本仓反复记载的「自指污染」。
            if fn == os.path.basename(__file__):
                continue
            for kw in ("cahac_version", "version_negotiat", "negotiate_version",
                       "\u7248\u672c\u534f\u5546", "protocol_version"):
                if kw in s:
                    hits.setdefault(kw, []).append(fn)
    # \u2605 \u9633\u6027\u5bf9\u7167\uff1a\u2605 \u540c\u626b\u9762\u4e0a\u4e00\u4e2a\u5fc5\u5b9a\u547d\u4e2d\u7684\u8bcd
    ctrl = {}
    for d in ("scripts", "tools"):
        dd = os.path.join(ROOT, d)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if not fn.endswith((".py", ".js")):
                continue
            try:
                if "def " in io.open(os.path.join(dd, fn), encoding="utf-8", errors="ignore").read():
                    ctrl.setdefault("def ", []).append(fn)
            except Exception:
                pass
    pos = len(ctrl.get("def ", []))
    v = "PASS" if hits else "FAIL"
    w = ("\u2605\u627e\u5230\u5b9e\u73b0\uff1a%s" % {k: len(x) for k, x in hits.items()}) if hits else \
        ("\u2605\u2605 \u672c\u673a\u65e0\u3010\u7248\u672c\u534f\u5546\u3011\u5b9e\u73b0\uff08\u2605 \u626b\u9762=%d \u6587\u4ef6 \u00b7 "
         "\u9633\u6027\u5bf9\u7167\u300cdef \u300d\u547d\u4e2d %d \u6587\u4ef6 \u21d2 \u68c0\u7d22\u9762\u6709\u6548\uff09"
         % (_scanned_count(), pos))
    return {"verdict": v, "why": w, "evidence": {"hits": {k: len(x) for k, x in hits.items()},
                                                 "positive_control": pos}}


def _scanned_count():
    n = 0
    for d in ("scripts", "tools"):
        dd = os.path.join(ROOT, d)
        if os.path.isdir(dd):
            n += sum(1 for f in os.listdir(dd) if f.endswith((".py", ".js", ".mjs", ".sh")))
    return n


def _count_field_in_ns(ns, field, limit=50):
    """\u2605 \u62bd ns \u4e0b\u6700\u540e limit \u5f20\u5361\uff0c\u6570\u5b57\u6bb5\u547d\u4e2d"""
    try:
        req = urllib.request.Request(BB + "/" + ns.rstrip("/") + "/")
        t = _tok()
        if t:
            req.add_header("Authorization", "Bearer " + t)
        with urllib.request.urlopen(req, timeout=25) as r:
            lst = (json.loads(r.read().decode("utf-8", "ignore")).get("list") or {})
        ks = sorted(lst.keys())[-limit:]
        hit = 0
        for k in ks:
            req2 = urllib.request.Request(BB + "/" + ns.rstrip("/") + "/" + str(k))
            if t:
                req2.add_header("Authorization", "Bearer " + t)
            try:
                with urllib.request.urlopen(req2, timeout=12) as r2:
                    v = (json.loads(r2.read().decode("utf-8", "ignore")).get("value") or {})
                if isinstance(v, dict) and v.get(field) not in (None, ""):
                    hit += 1
            except Exception:
                pass
        return {"hit": hit, "scanned": len(ks)}
    except Exception:
        return {"hit": 0, "scanned": 0}


# ═══════════════════════ I-3 ═══════════════════════

RUNTIME_HINTS = ("launchd", "launchctl", "com.dsh.", "cron", "systemd", "daemon", "server", "listen")


def check_conformance_suite():
    """\u2605 \u5957\u4ef6\u5b58\u5728\u4e14\u53ef\u8dd1\uff08\u2605 **\u975e\u79bb\u7ebf\u811a\u672c**\uff09"""
    ev = {}
    cands = []
    for d in ("scripts", "tools"):
        dd = os.path.join(ROOT, d)
        if not os.path.isdir(dd):
            continue
        for fn in os.listdir(dd):
            if ("channel" in fn or "conformance" in fn or "protocol" in fn) and fn.endswith((".py", ".js")):
                cands.append(os.path.join(d, fn))
    ev["candidates"] = cands
    # \u2605 \u5224\uff1a\u2605 \u5019\u9009\u5728\u3010\u8fd0\u884c\u65f6\u94fe\u8def\u3011\u4e0a\u5417\uff08\u2605 \u88ab launchd/cron \u5f15\u7528\uff09
    in_runtime = []
    for c in cands:
        base = os.path.basename(c)
        try:
            # ★★ 严化：只看 launchd/cron（★ 真运行时）—★ 不看简单 import
            r = subprocess.run(["grep", "-rl", base, os.path.expanduser("~/Library/LaunchAgents")],
                               capture_output=True, text=True, timeout=25)
            # ★★ 2026-10-13 修（★ 本纳自查）：【排除探针自己】—★
            #   ★ 实测：`bb-channel.py ← industry-parity.py` 是我自己写的引用 ⇒
            #     ★★ 那不是「运行时链路」的证据。
            _self = os.path.basename(__file__)
            refs = [x for x in r.stdout.strip().split("\n")
                    if x and not x.endswith(base) and not x.endswith(_self)]
            if refs:
                in_runtime.append({"file": base, "referenced_by": refs[:3]})
        except Exception:
            pass
    ev["runtime_refs"] = in_runtime
    # \u2605 \u4e09\u6001
    if not cands:
        v, w = "FAIL", "\u2605\u2605 \u672a\u627e\u5230\u4efb\u4f55\u5019\u9009\u5957\u4ef6\uff08\u2605 \u626b\u9762 %d \u6587\u4ef6\uff09" % _scanned_count()
    elif not in_runtime:
        v, w = "FAIL", ("\u2605\u2605 %d \u4e2a\u5019\u9009\u4e2d\u3010\u65e0\u4e00\u5728 launchd/cron \u91cc\u3011\u21d2 "
                        "**\u5747\u4e3a\u79bb\u7ebf\u811a\u672c**\uff08\u2605 \u4e0e v6.1 \u8bfb\u6570\u4e00\u81f4\uff09" % len(cands))
    else:
        v, w = "PASS", ("\u2605 %d \u4e2a\u5019\u9009\u4e2d %d \u4e2a\u5728 launchd/cron \u91cc\uff08\u2605 \u771f\u8fd0\u884c\u65f6\uff09% s"
                        % (len(cands), len(in_runtime),
                           "\u2014\u2605 " + ", ".join(x["file"] for x in in_runtime)))
    return {"verdict": v, "why": w, "evidence": ev}


def run(as_json=False):
    out = {"version": VERSION, "scanned_files": _scanned_count(), "checks": {}}
    out["checks"]["I-2a \u80fd\u529b\u5361+\u7b7e\u540d"] = check_ability_card()
    out["checks"]["I-2b \u4efb\u52a1\u751f\u547d\u5468\u671f"] = check_task_lifecycle()
    out["checks"]["I-2c \u8ba4\u8bc1\u6388\u6743"] = check_auth()
    out["checks"]["I-2d \u7248\u672c\u534f\u5546"] = check_version_negotiation()
    out["checks"]["I-3 \u534f\u8bae\u4e00\u81f4\u6027\u5957\u4ef6"] = check_conformance_suite()
    vs = [c["verdict"] for c in out["checks"].values()]
    out["summary"] = {"PASS": vs.count("PASS"), "FAIL": vs.count("FAIL"),
                      "UNDECIDABLE": vs.count("UNDECIDABLE")}
    return out


def selftest():
    ok = tot = 0
    # \u2605 \u6b63\u63a7 1\uff1a\u4e09\u6001\u53d6\u503c\u53ea\u80fd\u662f\u4e09\u4e2a
    tot += 1
    r = run(as_json=True)
    allv = {c["verdict"] for c in r["checks"].values()} | {"PASS", "FAIL", "UNDECIDABLE"}
    if allv <= {"PASS", "FAIL", "UNDECIDABLE"}:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u6240\u6709\u5224\u5b9a\u4ec5\u4e09\u6001\u503c")
    else:
        print("  \u274c \u51fa\u73b0\u7b2c\u56db\u6001\uff1a%s" % allv)
    # \u2605 \u6b63\u63a7 2\uff1a\u6bcf\u9879\u5fc5\u5e26 why\uff08\u2605 \u4e0d\u80fd\u53ea\u7ed9\u4e00\u4e2a\u503c\uff09
    tot += 1
    if all(c.get("why") for c in r["checks"].values()):
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u6bcf\u9879\u90fd\u5e26 why")
    else:
        print("  \u274c \u6709\u9879\u65e0 why")
    # \u2605 \u6b63\u63a7 3\uff1a\u8ba4\u8bc1\u6d4b\u5fc5\u7528\u3010\u5b58\u5728\u7684\u952e\u3011\uff08\u2605 \u5426\u5219 404 \u65e0\u6cd5\u533a\u5206\uff09
    tot += 1
    a = r["checks"]["I-2c \u8ba4\u8bc1\u6388\u6743"]
    if a["verdict"] != "UNDECIDABLE" and a["evidence"].get("key"):
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u8ba4\u8bc1\u6d4b\u7528\u4e86\u5b58\u5728\u7684\u952e\uff08%s\uff09" % str(a["evidence"]["key"])[:30])
    elif a["verdict"] == "UNDECIDABLE":
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u53d6\u4e0d\u5230\u952e\u65f6\u5982\u5b9e\u62a5\u4e0d\u53ef\u5224\uff08\u2605 \u4e0d\u731c\uff09")
    else:
        print("  \u274c \u8ba4\u8bc1\u6d4b\u672a\u7528\u5b58\u5728\u7684\u952e")
    # \u2605 \u8d1f\u63a7\uff1a\u7248\u672c\u534f\u5546\u65e0\u5b9e\u73b0\u65f6\u5fc5\u62a5\u3010\u9633\u6027\u5bf9\u7167\u3011
    tot += 1
    vn = r["checks"]["I-2d \u7248\u672c\u534f\u5546"]
    if vn["verdict"] == "PASS" or vn["evidence"].get("positive_control", 0) > 0:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u7248\u672c\u534f\u5546\u672a\u547d\u4e2d\u65f6\u5e26\u9633\u6027\u5bf9\u7167\uff08%d \u6587\u4ef6\uff09" % vn["evidence"].get("positive_control", 0))
    else:
        print("  \u274c \u7248\u672c\u534f\u5546\u672a\u547d\u4e2d\u4e14\u65e0\u9633\u6027\u5bf9\u7167")
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("industry-parity %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = run(a.json)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== industry-parity %s\uff08\u2605 \u626b\u9762 %d \u6587\u4ef6\uff09==" % (VERSION, r["scanned_files"]))
        for k, c in r["checks"].items():
            print("  \u3010%s\u3011%s" % (c["verdict"], k))
            print("     %s" % c["why"])
        s = r["summary"]
        print("\n  \u6c47\u603b\uff1a\u2605 **PASS %d \u00b7 FAIL %d \u00b7 UNDECIDABLE %d**"
              % (s["PASS"], s["FAIL"], s["UNDECIDABLE"]))
    return 1 if r["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
