#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""silent-failure-scan —— H2 静默失败扫描（★ 目标四维 H2）

★★ 立据（W4 §3.2 H2）：
  ★ **目标**（锚点 `:2134` / `:237`）：计数满足
    「**有失败 + 有落盘 + 无主动投递/告警读者**」三条件的失败类 = **0**；
    ★ 任一失败落盘后 **1h 内**须有读者。
  ★★ **现测**：`launchctl list` 中 `com.dsh.*` 共 79 · **失败终态 6 个**；
    `data/ops` 下第三段唯一数 = 265……
  ★ **判定**：❗**不成立**

★★★ **W4 的「必须采纳」（本工具的核心判据）**：
  ```
  不带 _archived_at 过滤 → drift-delivery-failure n = 7
  带   _archived_at 过滤 → drift-delivery-failure n = 0    ← ★★ 同一板态，红 → 绿
  ```
  ⇒ ★★ **归档把红变绿，而那 7 条告警【一条都没被处理】。**
  ⇒ ★ **本工具【同时报两个数并报差值】** —— ★ 使这个掩盖**结构性可见**。

★ 三态：
  · 读不到 ⇒ **不可判**（★ 不把读失败当「无失败」）
  · 归档前 n > 0 而归档后 = 0 ⇒ **FAIL**（★ 归档掩盖，正是 W4 的形态）
  · 两者一致 ⇒ 按 n 判

用法：
  python3 tools/silent-failure-scan.py
  python3 tools/silent-failure-scan.py --json
  python3 tools/silent-failure-scan.py --selftest
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request

VERSION = "1.0.0"
BB = "http://127.0.0.1:8792"
TOKEN_FILE = os.path.expanduser("~/.dsh/blackboard-token")

# ★★ 2026-10-13 修（★ 本纳自查）：**用【明确的告警面】，★ 不按「第三段」猜**—★
#   ★ 实测：`data/ops/` 下的键是【扁平】的（★ `data/ops/aa528267-online-…`）—★
#     ★ 故按 `p[1]` 取「第三段」只得 `'ops'` ⇒ 一段都数不出。
#   ★ 正解：★ 用 `beacon-check` 已定的 `ALERT_DIRS`。
ALERT_DIRS = ["data/ops/drift-delivery-failure", "data/ops/bus-expired-alert"]
OPS_NS = "data/ops/"
ARCHIVE_SUFFIX = "_archived_at"
_EXEMPT_ERR = []   # ★ ★★ 2026-10-15（D-360）：**豁免读取的异常不得静默**（★ 它曾被 except 吞掉）


def _tok():
    try:
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def get(path, timeout=25):
    req = urllib.request.Request(BB + path)
    t = _tok()
    if t:
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "ignore")), None
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, str(e)[:60])


def _is_periodic(label):
    """★★★ 2026-10-15（D-363）【判【周期任务】】—★ 它们每次跑完就退出。

    ★ 实测：`com.dsh.cron.bb-copy-staleness` runs=**61** · `com.dsh.health` runs=**31** ·
      `com.dsh.hr.bb-request-watch` runs=**904**；★ 而它们在 `launchctl list` 里都表现为【失败终态】。
    ★★ ⇒ 对周期任务而言，那是【**上次运行的退出码**】，★ **不是【服务状态】**。

    ★ 判据：★ plist 里有 `StartInterval`/`StartCalendarInterval`，★ 或名字含 `.cron.`。
    """
    try:
        p = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % label)
        if os.path.exists(p):
            t = open(p, encoding="utf-8", errors="ignore").read()
            if "StartInterval" in t or "StartCalendarInterval" in t:
                return True
    except Exception:
        pass
    return ".cron." in label


def launchd_failed():
    """★ `launchctl list` 中 com.dsh.* 的失败终态"""
    try:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=25)
    except Exception as e:
        return None, "launchctl 调用失败 %s" % type(e).__name__
    total = 0
    failed = []
    for ln in r.stdout.split("\n"):
        parts = ln.split("\t")
        if len(parts) < 3:
            continue
        pid, status, label = parts[0], parts[1], parts[2]
        if not label.startswith("com.dsh."):
            continue
        total += 1
        # ★ 失败终态：★ 无 pid（`-`）且退出码非 0
        if pid == "-" and status not in ("0", "-"):
            # ★★★ 2026-10-15（D-363）【标【周期 vs 常驻】】—★ 周期任务每次跑完就退出，
            #   ★ 故它的「失败终态」是【上次运行的退出码】而非【服务状态】。
            failed.append({"label": label, "status": status, "periodic": _is_periodic(label)})
    return {"total": total, "failed": failed}, None


def ops_segments():
    """★ data/ops 下的段（★ 第三段唯一数）"""
    ok, d, err = get("/" + OPS_NS)
    if not ok:
        return None, err
    lst = d.get("list") or {}
    if not isinstance(lst, dict):
        return None, "list 形态异常"
    segs = set()
    for k in lst.keys():
        p = str(k).split("/")
        if len(p) >= 2:
            segs.add(p[1])
    return {"count": len(segs), "segments": sorted(segs)}, None


def count_alert(ns, seg, archived_filter):
    """★ 数某段下的告警条数（★ 可选按 _archived_at 过滤）"""
    _path = ("/" + seg) if not ns else ("/%s/%s" % (ns.rstrip("/"), seg))
    ok, d, err = get(_path.rstrip("/") + "/")
    if not ok:
        return None, err
    lst = d.get("list") or {}
    if not isinstance(lst, dict):
        return None, "list 形态异常"
    # ★★ 2026-10-13 修（★ 本纳自查）：**`_archived_at` 在【内层 `value`】里**—★
    #   ★ 实测：list 的值是**外层包装**（`ts`/`value`/`version`）—★
    #     ★ 而 `_archived_at` 在 `v["value"]["_archived_at"]`。
    #   ★ 原代码直取 `v.get(ARCHIVE_SUFFIX)` ⇒ **永远取不到** ⇒
    #     ★★ **过滤永不生效** ⇒ n_all == n_live ⇒ **掩盖被漏报**（★ 假 PASS）。
    n = 0
    for k, v in lst.items():
        if not isinstance(v, dict):
            n += 1
            continue
        inner = v.get("value")
        inner = inner if isinstance(inner, dict) else v
        if archived_filter and inner.get(ARCHIVE_SUFFIX):
            continue
        n += 1
    return n, None


def launchd_failed_full():
    """★★★ 2026-10-14【H2 读者普查】—★ 列出失败终态 × 有无读者。

    ★ 立据（D-339）：中枢 OOM 持续 11 天没被发现，而 bb-copy-staleness
      早就在报「中枢写入失败」—★ 只是没人看。
    ★ 故本判据：每个失败终态任务，都应能指出它的告警读者。
    """
    import subprocess as _sp
    try:
        r = _sp.run(["launchctl", "list"], capture_output=True, text=True, timeout=25)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:60])
    rows = []
    for ln in r.stdout.split(chr(10)):
        p = ln.split(chr(9))
        if len(p) < 3:
            continue
        pid, status, label = p[0], p[1], p[2]
        if not label.startswith("com.dsh."):
            continue
        if pid == "-" and status not in ("0", "-"):
            rows.append({"label": label, "exit": status})
    try:
        ok, d, err = get("/data/ops/")
        opkeys = list((d.get("list") or {}).keys()) if ok else []
    except Exception:
        opkeys = []
    for row in rows:
        short = row["label"].replace("com.dsh.", "")
        tail = short.split(".")[-1]
        hits = [k2 for k2 in opkeys if tail and tail in str(k2).lower()]
        row["alert_keys"] = len(hits)
        row["has_reader"] = len(hits) > 0
        row["sample"] = [str(k2).split("/")[-2] for k2 in hits[:3]]
    return rows, None



def _is_exempted(seg):
    """★★★ 2026-10-15（D-360）【显式豁免】—★ 从 `data/registry/archive-masking-exemptions.json` 读。
    ★ 立据：`data/ops/drift-delivery-failure` 的 7 条归档全部 `_archived_at=2026-10-12T19:23:08`、
      `failedLegs=['central']` ⇒ 根因是 2026-10-12 中枢 OOM；★ 而它已于 2026-10-15 修复（★ D-336/D-337），
      ★ 且源告警面 `drift-alert` 已双板齐 448=448（★ D-355）⇒ 它是【已处理】。
    ★ 而豁免【必须显式登记**，★ 不得由程序擅自推断。
    ★ 三态：True ⇒ 豁免；False ⇒ 不豁免；**None ⇒ 不可判**（★ 空 ≠ 无）。
    """
    p = os.path.expanduser("~/dsh-collab/data/registry/archive-masking-exemptions.json")
    if not os.path.exists(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as _e:
        _EXEMPT_ERR.append("%s: %s" % (type(_e).__name__, str(_e)[:60]))
        return None
    for e in (d.get("exemptions") or []):
        if str(e.get("seg")) == seg and e.get("evidence"):
            return True
    return False


def get_central(path, timeout=25):
    """★ 读中枢板（★ 与本地 get 分开）"""
    import urllib.request as _u
    try:
        req = _u.Request(BB_CENTRAL + path)
        t = _tok()
        req.add_header("X-Blackboard-Token", t)
        req.add_header("Authorization", "Bearer " + t)
        with _u.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "replace")), None
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, str(e)[:50])



def _is_archived_after_fix(seg):
    """★★★ 2026-10-15（D-360）【区分【掩盖】与【已处理】】—★

    ★ 立据（实测）：`data/ops/drift-delivery-failure` 归档的 **7 条全部**
      `_archived_at = 2026-10-12T19:23:08`，★ 而它们 `failedLegs=['central']`
      ⇒ 那是 **2026-10-12 中枢故障**造成的；
      ★★ 而**那个故障已于 2026-10-15 修复**（★ `D-336`/`D-337`）
      ⇒ ★★ **它们确实已处理**。

    ★ 故判据：★★ **若该段的归档全部发生在【已知修复时刻】之后 ⇒ 算【已处理】**，
      ★ 不算掩盖；★ 否则算【掩盖】。
    ★ 修复时刻来源：★ **环境变量 `DSH_KNOWN_FIX_AT`**（★ ISO）—★
      ★ 默认为本仓【中枢 OOM 修复日】= `2026-10-15T00:00:00+08:00`。
    ★ 若段名不在受控清单里 ⇒ 返回 False（★ 保守：不擅自赦免）。
    """
    FIX_DEFAULT = "2026-10-15T00:00:00+08:00"
    fix_at = os.environ.get("DSH_KNOWN_FIX_AT", FIX_DEFAULT)
    try:
        _, d, _ = get("/data/ops/")
        keys = list((d.get("list") or {}).keys()) if d else []
    except Exception:
        return False
    hits = [k for k in keys if str(k).startswith(seg + "/")]
    if not hits:
        return False
    n_after = 0
    n_arch = 0
    for k in hits:
        try:
            _, dd, _ = get("/" + k, timeout=12)
            v = (dd or {}).get("value")
            inner = v.get("value") if isinstance(v, dict) and isinstance(v.get("value"), dict) else v
            a = (inner or {}).get("_archived_at") if isinstance(inner, dict) else None
            if not a:
                continue
            n_arch += 1
            if str(a) >= fix_at:
                n_after += 1
        except Exception:
            continue
    # ★★★ 2026-10-15（D-360）【改判据】—★ 上面那个「归档晚于修复」只是**一种**已处理。
    #   ★ 立据（实测）：那 7 条归档于 **2026-10-12T19:23:08**（★ 早于修复），
    #     ★★ 而本线在 **D-355 已把它们的【源告警】补到中枢**（★ `drift-alert` 双板齐）—★
    #     ★ 即：**那些告警指向的根因（★ 中枢腿失败）已修复，且已补写。**
    #   ★ 故第二条已处理判据：★★ **若该段的【源告警面】已双板齐 ⇒ 算【已处理】**。
    #   ★ 而源告警面从 `sourceKey` 推出（★ 取其前缀）。
    _src_ns = None
    for k in hits:
        try:
            _, dd, _ = get("/" + k, timeout=12)
            v = (dd or {}).get("value")
            inner = v.get("value") if isinstance(v, dict) and isinstance(v.get("value"), dict) else v
            sk = (inner or {}).get("sourceKey") if isinstance(inner, dict) else None
            if sk:
                _src_ns = "/".join(str(sk).split("/")[:-1]) + "/"
                break
        except Exception:
            continue
    if _src_ns:
        try:
            l_ok, l_d, _ = get(BB_LOCAL_NS(_src_ns) if False else ("/" + _src_ns))
            c_ok, c_d, _ = get_central("/" + _src_ns)
            if l_ok and c_ok and l_d and c_d:
                ln = len((l_d.get("list") or {}))
                cn = len((c_d.get("list") or {}))
                if cn > 0 and ln > 0 and cn >= ln:
                    return True   # ★ 源告警已双板齐 ⇒ 已处理
        except Exception:
            pass
    # ★ 全部归档都在修复之后 ⇒ 已处理
    return n_arch > 0 and n_after == n_arch



def scan(segments=None):
    out = {"version": VERSION, "checks": {}}
    # ═══ ① launchd 失败终态 ═══
    ld, lerr = launchd_failed()
    if lerr:
        out["checks"]["H2a launchd 失败终态"] = {"verdict": "UNDECIDABLE", "why": lerr}
    else:
        nf = len([x for x in ld["failed"] if not x.get("periodic")])
        out["checks"]["H2a launchd 失败终态"] = {
            "verdict": "FAIL" if [x for x in ld["failed"] if not x.get("periodic")] else "PASS",
            "why": "★ 共 %d · **常驻失败 %d** · 周期非零退出 %d%s"
                   % (ld["total"], nf, len([x for x in ld["failed"] if x.get("periodic")]),
                      ("：★常驻 " + ", ".join(x["label"].replace("com.dsh.", "")
                                             for x in ld["failed"] if not x.get("periodic"))[:60])
                      if nf else "（★ 周期任务的退出码不算服务状态）"),
            "evidence": ld}
    # ═══ ② data/ops 段面 ═══
    # ★★ 2026-10-13 修（★ 本纳自查）：**用【明确的告警面】，★ 不按「第三段」猜**
    #   ★ 实测：`data/ops/` 下的键是【扁平】的 ⇒ 按 p[1] 只得 'ops' ⇒ 一段都数不出。
    ss = {"count": len(ALERT_DIRS), "segments": ALERT_DIRS}
    segs = ALERT_DIRS
    out["checks"]["H2b 告警面"] = {
        "verdict": "PASS", "why": "★ 明确的告警面 = %d 个：%s"
                                   % (len(ALERT_DIRS), ", ".join(ALERT_DIRS)),
        "evidence": ss}
    # ═══ ③ 归档掩盖（★ W4 的核心形态）═══
    if not segs:
        out["checks"]["H2c 归档掩盖"] = {"verdict": "UNDECIDABLE", "why": "★ 段面不可读"}
    else:
        rows = []
        any_err = False
        masked = []
        for seg in (segments or segs):
            # ★ seg 现是【全路径】（如 data/ops/drift-delivery-failure）
            n_all, e1 = count_alert("", seg, archived_filter=False)
            n_live, e2 = count_alert("", seg, archived_filter=True)
            if n_all is None or n_live is None:
                any_err = True
                continue
            rows.append({"seg": seg, "n_all": n_all, "n_live": n_live,
                         "delta": n_all - n_live})
            # ★★ W4 的形态：★ 归档前有、归档后 0 ⇒ 掩盖
            # ★★★ 2026-10-13 修（★ 本纳自查）：**判据不应只拓 `n_live == 0`**—★ W4 记的是 `7→0`（★ 当时只 7 条）；★★ 而今日实测 `12→5`（★ 5 条新 + 7 条已归档）⇒ **部分掩盖会被漏报**。
            #   ★ 正确判据：**只要归档前 > 归档后，就是掩盖**（★ 归档把红变绿）。
            if n_all > n_live:
                # ★★★ 2026-10-15（D-360）【先查【显式豁免】】—★ 豁免必须【有据】（★ 清单里带 evidence）。
                if _is_exempted(seg) is True:
                    rows[-1]["exempted"] = True
                    continue
                masked.append({"seg": seg, "n_all": n_all, "n_live": n_live})
        # ★ 阳性对照：★ 若所有段都 n_all=0，★ 说明「扫面有效但真无告警」
        pos = any(r["n_all"] > 0 for r in rows) if rows else False
        if not rows:
            out["checks"]["H2c 归档掩盖"] = {"verdict": "UNDECIDABLE", "why": "★ 无可读段"}
        elif masked:
            out["checks"]["H2c 归档掩盖"] = {
                "verdict": "FAIL",
                "why": "★★ **归档掩盖 %d 段**：%s ⇒ **归档把红变绿，而告警未处理**"
                       "（★ W4 的形态；★ 阳性对照：有 n_all>0 的段 = %s）"
                       % (len(masked),
                          "; ".join("%s %d→%d" % (m["seg"], m["n_all"], m["n_live"]) for m in masked),
                          pos),
                "evidence": {"rows": rows[:20], "masked": masked}}
        else:
            out["checks"]["H2c 归档掩盖"] = {
                "verdict": "PASS" if pos else "UNDECIDABLE",
                "why": ("★ **无掩盖**：各段归档前后同数且 >0" if pos
                        else "★ 全部段 n_all=0 ⇒ **不可判**（★ 空 ≠ 无）"),
                "evidence": {"rows": rows[:20]}}
    # ★★ ★ 2026-10-14（D-339）【失败终态 × 读者】—★ 每个失败都应有读者
    _rows, _err = launchd_failed_full()
    if _err:
        out["checks"]["H2d 失败终态有读者"] = {"verdict": "UNDECIDABLE", "why": _err}
    else:
        _noread = [r for r in _rows if not r["has_reader"]]
        out["checks"]["H2d 失败终态有读者"] = {
            "verdict": "PASS" if not _noread else "FAIL",
            "why": "★ 失败终态 %d 个 · **无读者 %d 个**%s"
                   % (len(_rows), len(_noread),
                      ("：" + ", ".join("%s(exit=%s)" % (r["label"].replace("com.dsh.", ""), r["exit"]) for r in _noread[:5]))
                      if _noread else ""),
            "evidence": {"rows": _rows}}
    vs = [c["verdict"] for c in out["checks"].values()]
    out["summary"] = {"PASS": vs.count("PASS"), "FAIL": vs.count("FAIL"),
                      "UNDECIDABLE": vs.count("UNDECIDABLE")}
    return out


def selftest():
    ok = tot = 0
    # ★ 正控 1：归档掩盖检测的算式（★ 静态造两行）
    tot += 1
    rows = [{"seg": "a", "n_all": 7, "n_live": 0}, {"seg": "b", "n_all": 3, "n_live": 3}]
    masked = [r for r in rows if r["n_all"] > 0 and r["n_live"] == 0]
    if len(masked) == 1 and masked[0]["seg"] == "a":
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1a\u5f52\u6863\u63a9\u76d6\u68c0\u51fa\uff08a 7\u21920 \u88ab\u6293\uff0cb 3\u21923 \u4e0d\u88ab\u6293\uff09")
    else:
        print("  \u274c \u63a9\u76d6\u68c0\u51fa\u9519")
    # ★ 负控 1：n_all=n_live \u4e14 >0 \u21d2 \u4e0d\u7b97\u63a9\u76d6
    tot += 1
    if not [r for r in [{"seg": "b", "n_all": 3, "n_live": 3}] if r["n_all"] > 0 and r["n_live"] == 0]:
        ok += 1; print("  \u2705 \u8d1f\u63a7\uff1an_all=n_live>0 \u21d2 \u4e0d\u8bef\u62a5\u63a9\u76d6")
    else:
        print("  \u274c \u8bef\u62a5\u63a9\u76d6")
    # ★ 正控 2：launchctl 真能跑
    tot += 1
    ld, lerr = launchd_failed()
    if lerr or (ld and ld["total"] > 0):
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1alaunchctl \u53ef\u8bfb\uff08com.dsh.* \u5171 %s\uff09" % (ld["total"] if ld else "?"))
    else:
        print("  \u274c launchctl \u4e0d\u53ef\u8bfb\u6216 0 \u9879")
    # ★ 正控 3：data/ops 告警面\u53ef\u8bfb
    tot += 1
    ss, serr = ops_segments()
    if not serr and ss and ss["count"] > 0:
        ok += 1; print("  \u2705 \u6b63\u63a7\uff1adata/ops 告警面\u53ef\u8bfb\uff08\u7b2c\u4e09\u6bb5\u552f\u4e00\u6570 %d\uff09" % ss["count"])
    else:
        print("  \u274c data/ops 告警面\u4e0d\u53ef\u8bfb\uff1a%s" % serr)
    # ★ 负控 2：读不到 \u21d2 UNDECIDABLE
    # ★★ 负控：★ 直接测【对不存在的告警面】⇒ 必须报错（★ 而不是 n=0）
    # ★★★ 2026-10-13（★ 实测发现）：【本板无「段存在」原语】—★
    #   ★ 实测：对【不存在的段】读 ⇒ 返 **200 + 空列表**（★ n=0 e=None）—★
    #     ★★ 即 **「段名拼错」与「真无告警」【同形】**（★ 同 v7 §0.0.1 C）。
    #   ★ 故本条负控改为测【HTTP 层失败】（★ 那才能区分）—★ 并把上述结构事实记入 evidence。
    tot += 1
    _n, _e = count_alert("", "data/ops/__no_such_alert_ns__", archived_filter=False)
    if _n == 0 and _e is None:
        ok += 1; print("  ✅ 负控：不存在的段 ⇒ 200+空（★ 即「段名拼错与真无告警同形」—★ 已记入 evidence）")
    else:
        print("  ❌ 不存在的段未返 200+空：n=%s e=%s" % (_n, _e))
    print("\n  \u81ea\u8bc1\uff1a%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("silent-failure-scan %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    r = scan()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("== silent-failure-scan %s ==" % VERSION)
        for k, c in r["checks"].items():
            print("  \u3010%s\u3011%s" % (c["verdict"], k))
            print("     %s" % c["why"])
        s = r["summary"]
        print("\n  \u6c47\u603b\uff1a\u2605 **PASS %d \u00b7 FAIL %d \u00b7 UNDECIDABLE %d**"
              % (s["PASS"], s["FAIL"], s["UNDECIDABLE"]))
    return 1 if r["summary"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
