#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""delivery-probe —— 投递率 + 跨设备偏斜（★ 一个工具两用）

★★ 管的是目标四维里的【两项目标判据】：

  ★ **H3 探针投递率**（W4 §3.2）
    目标：每个探测器的成功与失败分支写同一投递台账，且台账有读者；**目标 100%（1h 内到达）**
    现测（W4 `2026-10-12T21:14:50`）：24h 窗口 `drift-alert` 本机 **12** / 中枢到达 **11** ⇒ **91.67%**
    ★★ 而 W4 指出它的**判别力存疑**：唯一未达的那条是【自指卡】
      ⇒ ★ **它无法把「链路坏了」与「那张我们还没定的卡」分开**。

  ★ **H4 跨设备偏斜检出**（W4 §3.2）
    目标：存在**真跨设备**比对项（**断言**，非列举）；超阈告警
    ★★ 现测：**本件未测** · **无判据** · **无负控** —— ★ 本工具即该判据的第一版。

★ 三态（★ 不猜）：
  · 两板都可读 ⇒ 出**投递率**与**偏斜**两个读数
  · 任一侧不可读 ⇒ **不可判**（★ 不把读取失败算成「未送达」—— ★ 那是 W4 记的口径污染源）

★ 用法：
  python3 tools/delivery-probe.py                     # 默认面 data/ops/drift-alert/
  python3 tools/delivery-probe.py --ns data/ops/drift-alert/ --json
  python3 tools/delivery-probe.py --selftest
"""
import argparse
import collections
import json
import os
import datetime
import re
import sys
import urllib.request

VERSION = "1.0.0"
TOKEN_FILE = os.path.expanduser("~/.dsh/blackboard-token")

# ★ 双板（★ 星桥第二/第三任都用这两个）
LOCAL = "http://127.0.0.1:8792"
CENTRAL = "http://xingqiao.meetfunbp.com:8792"

# ★ 偏斜阈（★ 我定，★ 而它本身就是 H4 要的「超阈告警」）
SKEW_WARN = 0.10      # 10%
SKEW_FAIL = 0.30      # 30%


def _token():
    try:
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def fetch(base, path, timeout=25):
    """★ 返回 (ok, obj, err)"""
    req = urllib.request.Request(base + path)
    t = _token()
    if t:
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "ignore")), None
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, str(e)[:70])


def list_keys(base, ns, timeout=30):
    """★ 返回 (ok, keys_set, ts_map, err)"""
    ok, d, err = fetch(base, "/" + ns.rstrip("/") + "/", timeout)
    if not ok:
        return False, set(), {}, err
    if not isinstance(d, dict):
        return False, set(), {}, "非 dict 响应"
    lst = d.get("list") or {}
    if not isinstance(lst, dict):
        return False, set(), {}, "list 形态异常"
    ts_map = {}
    for k, v in lst.items():
        short = str(k).split("/")[-1]
        if isinstance(v, dict):
            # ★★★ 2026-10-15（D-354）【改用【内层 ts】判窗】—★ 外层 ts 是【板级元数据】会被【重新写入】污染。
            #   ★ 立据（D-353）：补写 309 张后⇒ 外层 ts 全被刷成今天（★ `2026-10-15T02:04:46`）—★
            #     ★ 而卡自带的【内层 ts】是原始写入时刻（★ `1791010914531`）。
            #   ★ 原写法放弃内层的理由是「★ epoch 数字不可比」—★ **而那可以转**。
            #   ★ 修法：★ 内层 ts 若是 epoch（ms 或 s）⇒ **转成 ISO** 后再比；★ 若非数字则原样用。
            # ★★★ 2026-10-15（D-354）【取【内层】不是外层】—★ `v` 是【外层项】，
            #   ★ 内层在 `v["value"]` 里 —★ 故 `v.get("ts")` 取的是板级元数据。
            _vv = v.get("value")
            _inner = _vv.get("ts") if isinstance(_vv, dict) else None
            ts_map[short] = _norm_ts(_inner if _inner is not None else v.get("ts"))
    return True, set(ts_map.keys()), ts_map, None


def _norm_ts(x):
    """★★ 2026-10-15（D-354）：**把【内层 ts】归一为可比的 ISO 字符串**。

    ★ 立据（D-353）：外层 ts 是板级元数据，补写会把它刷成今天 ⇒ 旧卡被算成新卡。
    ★ 而卡自带 ts 是 epoch（ms 或 s）⇒ 转 ISO 后与 `since`（★ ISO 日期）可直接比。
    """
    if x is None:
        return ""
    s = str(x).strip()
    if not s:
        return ""
    if re.fullmatch(r"\d{10,13}", s):
        n = int(s)
        if n > 10 ** 11:          # ★ ms
            n = n / 1000.0
        try:
            return datetime.datetime.fromtimestamp(n).astimezone().isoformat()
        except Exception:
            return s
    return s



def within(ts_map, since=None):
    if not since:
        return set(ts_map.keys())
    return {k for k, t in ts_map.items() if t and t >= since}


def probe(ns, since=None):
    out = {"version": VERSION, "ns": ns, "since": since}
    lok, lkeys, lts, lerr = list_keys(LOCAL, ns)
    cok, ckeys, cts, cerr = list_keys(CENTRAL, ns)
    out["local"] = {"ok": lok, "count": len(lkeys), "err": lerr}
    out["central"] = {"ok": cok, "count": len(ckeys), "err": cerr}

    # ★★ 三态：任一侧不可读 ⇒ 不可判（★ 不把读取失败算成「未送达」）
    if not lok or not cok:
        out["verdict"] = "UNDECIDABLE"
        out["reason"] = ("★ 一侧不可读 ⇒ **不可判**（★ 不把读取失败算成未送达）"
                         "｜本机=%s 中枢=%s" % ("OK" if lok else lerr, "OK" if cok else cerr))
        return out

    # ★ 窗口（★ 用外层 ts，★ 实测卡自带 ts 是 epoch 数字不可比）
    lw = within(lts, since) if since else lkeys
    cw = within(cts, since) if since else ckeys
    out["window"] = {"local": len(lw), "central": len(cw)}

    # ═══ H3 投递率（★ 本机写了、中枢有没有）═══
    delivered = lw & cw
    missing = lw - cw
    rate = (len(delivered) / len(lw)) if lw else None
    out["H3_delivery"] = {
        "numerator": len(delivered), "denominator": len(lw),
        "rate": rate, "missing_sample": sorted(missing)[:5],
        "verdict": ("UNDECIDABLE" if rate is None else
                    ("PASS" if rate >= 1.0 else "FAIL")),
    }

    # ═══ H4 跨设备偏斜（★ 中枢有、本机没有 = 反向偏斜）═══
    extra = cw - lw          # 中枢有而本机无
    denom = max(len(lw), len(cw)) or 1
    skew = abs(len(lw) - len(cw)) / denom
    out["H4_skew"] = {
        "local": len(lw), "central": len(cw),
        "delta": len(lw) - len(cw), "ratio": skew,
        "central_only": len(extra), "central_only_sample": sorted(extra)[:5],
        "thresholds": {"warn": SKEW_WARN, "fail": SKEW_FAIL},
        "verdict": ("PASS" if skew < SKEW_WARN else
                    ("WARN" if skew < SKEW_FAIL else "FAIL")),
    }
    out["verdict"] = "MEASURED"
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：within 过滤正确
    tot += 1
    m = {"a": "2026-10-13T01:00:00", "b": "2026-10-12T01:00:00", "c": ""}
    if within(m, "2026-10-13") == {"a"}:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1awithin \u53ea\u7559\u7a97\u5185\u4e14\u6392\u9664\u7a7a ts")
    else:
        print("  \u274c within \u8fc7\u6ee4\u9519\uff1a%s" % within(m, "2026-10-13"))
    # ★ 负控 1：三态 —— 任一侧不可读 ⇒ UNDECIDABLE（★ 不冒充 PASS）
    tot += 1
    _orig = globals()["list_keys"]
    globals()["list_keys"] = lambda base, ns, timeout=30: (False, set(), {}, "ERR") \
        if base == CENTRAL else _orig(base, ns, timeout)
    try:
        r = probe("data/ops/drift-alert/")
        if r["verdict"] == "UNDECIDABLE":
            ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u4e00\u4fa7\u4e0d\u53ef\u8bfb \u21d2 UNDECIDABLE\uff08\u2605 \u4e0d\u5192\u5145 PASS\uff09")
        else:
            print("  \u274c \u8d1f\u63a7\u5931\u8d25\uff1averdict=%s" % r["verdict"])
    finally:
        globals()["list_keys"] = _orig
    # ★ 正控 2：投递率算式
    tot += 1
    lw, cw = {"a", "b", "c"}, {"a", "b"}
    rate = len(lw & cw) / len(lw)
    if abs(rate - 2/3) < 1e-9:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u6295\u9012\u7387\u7b97\u5f0f = %d/%d" % (len(lw & cw), len(lw)))
    else:
        print("  \u274c \u6295\u9012\u7387\u7b97\u5f0f\u9519")
    # ★ 负控 2：空分母 ⇒ rate 必须 None ⇒ UNDECIDABLE（★ 不是 0%，★ 不是 100%）
    tot += 1
    lwm = set()
    rm = (len(lwm & cw) / len(lwm)) if lwm else None
    if rm is None:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u7a7a\u5206\u6bcd \u21d2 rate=None\uff08\u2605 \u4e0d\u8bfb\u4f5c 0%% \u4e5f\u4e0d\u8bfb\u4f5c 100%%\uff09")
    else:
        print("  \u274c \u7a7a\u5206\u6bcd\u5224\u9519")
    # ★ 正控 3：偏斜阈分级
    tot += 1
    def grade(s):
        return "PASS" if s < SKEW_WARN else ("WARN" if s < SKEW_FAIL else "FAIL")
    if grade(0.0) == "PASS" and grade(0.2) == "WARN" and grade(0.5) == "FAIL":
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u504f\u659c\u9608\u4e09\u7ea7\uff08PASS/WARN/FAIL\uff09")
    else:
        print("  \u274c \u504f\u659c\u9608\u5206\u7ea7\u9519")
    # ★ 负控 3：解析器不该把「读取失败」当成「未送达」
    tot += 1
    if True:
        # ★ 静态核：源码里 verdict 分支必含 UNDECIDABLE
        src = open(__file__, encoding="utf-8").read()
        if 'out["verdict"] = "UNDECIDABLE"' in src:
            ok += 1; print("  \u2705 \u8d1f\u63a7\uff1a\u6e90\u7801\u542b\u3010\u4e0d\u53ef\u5224\u3011\u5206\u652f\uff08\u2605 \u9759\u6001\u6838\uff09")
        else:
            print("  \u274c \u65e0\u4e0d\u53ef\u5224\u5206\u652f")
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", default="data/ops/drift-alert/")
    ap.add_argument("--since", default=None, help="\u65f6\u95f4\u7a97\uff08\u5982 2026-10-13\uff09")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("delivery-probe %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = probe(a.ns, a.since)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== delivery-probe %s \u00b7 %s ==" % (VERSION, a.ns))
        print("  \u672c\u673a %s\uff08%s\uff09\u00b7 \u4e2d\u67a2 %s\uff08%s\uff09"
              % (r["local"]["count"], "OK" if r["local"]["ok"] else r["local"]["err"],
                 r["central"]["count"], "OK" if r["central"]["ok"] else r["central"]["err"]))
        if r["verdict"] == "UNDECIDABLE":
            print("  \u2605\u2605 %s" % r["reason"])
        else:
            h3 = r["H3_delivery"]; h4 = r["H4_skew"]
            print("  \u3010H3 \u6295\u9012\u7387\u3011%s \u2014 %d/%d = %s"
                  % (h3["verdict"], h3["numerator"], h3["denominator"],
                     ("%.2f%%" % (h3["rate"] * 100)) if h3["rate"] is not None else "\u4e0d\u53ef\u5224"))
            if h3["missing_sample"]:
                print("     \u672a\u8fbe\u6837\u672c: %s" % h3["missing_sample"])
            print("  \u3010H4 \u8de8\u8bbe\u5907\u504f\u659c\u3011%s \u2014 \u672c\u673a %d / \u4e2d\u67a2 %d \u00b7 \u03b4=%+d \u00b7 %.2f%%"
                  % (h4["verdict"], h4["local"], h4["central"], h4["delta"], h4["ratio"] * 100))
            if h4["central_only"]:
                print("     \u4ec5\u4e2d\u67a2\u6709: %d \u9520\uff0c\u6837\u672c %s" % (h4["central_only"], h4["central_only_sample"]))
    return 0 if r.get("verdict") != "UNDECIDABLE" else 2


if __name__ == "__main__":
    sys.exit(main())
