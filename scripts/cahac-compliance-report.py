#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cahac-compliance-report.py — CAHAC 合规率上报 + 缺席可判别（S15/S12 落地）

为什么需要（依 2026-10-09 所有者授权、计划 §5 批 3）：
  CAHAC v1.0 有规范、有工具（cahac-compliance-check.py）、有 launchd（cahac-replay），
  却在 42 天里零落地 —— 因为「不实现也合法」（静默兼容条款 L20/L115/L217）⇒
  **未落地不产生任何信号**。
  ⇒ 本条落实 G1/G3 的解法：**把报警从「存在报警」反转为「缺席报警」**。

★ 三条设计原则（全部【引用已有原则】，无一条发明）：
  ① 「缺席须结构上可判别，不能靠有人注意到」（G3 §5 规则二 · 三源收敛）
  ② 「进度只能是『被验证过的工作』；规范存在/launchd 在跑/工具在售都不算」（G3 §5 规则一）
  ③ ★ 「心跳阈值须与检查周期同阶，否则报警恒真 —— 恒真报警与恒假读数【对称】」
     + 「刷新周期与阈值【都由一处导出】，不得各自硬编码而漂移」
     （HR 2026-09-22 · 见 scripts/bb-copy.py L983-985）

用法：
  python3 cahac-compliance-report.py --report      # 算合规率并写黑板
  python3 cahac-compliance-report.py --check       # 检查上报是否陈旧（缺席 ⇒ 报警）
  python3 cahac-compliance-report.py --status      # 只读打印，不写
  python3 cahac-compliance-report.py --selftest    # 负例/正例自测（含判别力与不误杀）
  python3 cahac-compliance-report.py --dry-run     # 零写盘（配合以上任一模式）

退出码：0 = 正常（含「合规率低但上报新鲜」）；1 = 检出缺席/异常；2 = 用法错误
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

# ═══════════════════════════════════════════════════════════════════
# ★ 单一来源（原则 ③）：刷新周期与陈旧阈值【同阶且同源】，禁止各自硬编码
#   —— 若把 refresh 与 threshold 写成两个各自独立的字面量，它们会漂移，
#      漂移的结果就是「报警恒真」或「报警恒假」（对称的两种零信息状态）。
# ═══════════════════════════════════════════════════════════════════
REFRESH_SECONDS = int(os.environ.get("CAHAC_REPORT_REFRESH_SECONDS", "900"))  # 上报周期
STALE_THRESHOLD_SECONDS = REFRESH_SECONDS * 2  # ★ 由 REFRESH 导出，不得独立硬编码

BB = os.environ.get("BB_BASE", "http://127.0.0.1:8792")
REPORT_KEY = "data/health/cahac-compliance"
INBOX_DIR = os.path.expanduser("~/.dsh/inbox")

# CAHAC §7.2 的合法 state 枚举（v1.2.1：已对齐 bb-taskboard）
LEGAL_STATES = {
    "todo", "claimed", "done", "verified", "blocked", "failed", "timeout",
}


# ─────────────────────────── 黑板 I/O ───────────────────────────
def bb_get(key, timeout=6):
    try:
        with urllib.request.urlopen("%s/%s" % (BB, key), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"_error": "%s: %s" % (type(e).__name__, e)}


def bb_put(key, value, timeout=6, dry=False):
    if dry:
        return {"_dry_run": True, "key": key}
    tok = ""
    try:
        tok = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
    except Exception:
        pass
    # ★ 2026-10-09 修：原写成 {"value": value} ⇒ 值被多包一层 ⇒
    #   写入返回 HTTP 200（**假成功**），而读回时 ts/rate_* 全为 None。
    #   ⇒ 黑板 PUT 的语义是【直接写值】。教训：**200 ≠ 写对了，必须回读比对内容**
    #     （与本体系既有「非 200 被当成成功」的教训对称）。
    body = json.dumps(value, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("%s/%s" % (BB, key), data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
        req.add_header("X-Blackboard-Token", tok)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"_http": r.status}
    except Exception as e:
        return {"_error": "%s: %s" % (type(e).__name__, e)}


# ─────────────────────── 合规率（数据层 · S12）───────────────────────
def compute_compliance(inbox_dir=None):
    """★ 原则 ②：合规率必须来自【数据层】（条目真的带了合法 state），
       而不是【声明层】（某工具声称支持 CAHAC）。
       —— 前者是「被验证过的工作」，后者是 liveness。"""
    # ★ 2026-10-09 修口径：`~/.dsh/inbox/*.json` 是 **JSONL**（每行一条），
    #   不是「一文件一条」—— 实证：文件数 2672 而总行数 5514（collab-inbox.json 单文件 580 行）。
    #   ⇒ 原来的「按文件遍历」把【文件数】当成了【条目数】⇒ 分母错。
    #   ⇒ 现按【行】计；非 JSON 行计入 total 但不算 with_state（诚实计入分母）。
    d = inbox_dir or INBOX_DIR
    total = 0
    with_state = 0
    legal = 0
    files = 0
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        # ★ 排除流程文件（不是条目）
        if name.startswith(".") or name in ("llm-ledger.json",):
            continue
        files += 1
        try:
            fh = open(os.path.join(d, name), encoding="utf-8")
        except Exception:
            continue
        with fh:
            for line in fh:
                if not line.strip():
                    continue
                total += 1
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                if "state" in obj:
                    with_state += 1
                    if str(obj.get("state")) in LEGAL_STATES:
                        legal += 1
    rate_with_state = (with_state / total) if total else 0.0
    rate_legal = (legal / total) if total else 0.0
    return {
        "ts": int(time.time()),
        "node": os.environ.get("DSH_NODE_ID", "mac-mini"),
        "files": files,          # ★ 文件数（供对照；条目数 = total）
        "total": total,
        "with_state": with_state,
        "legal_state": legal,
        "rate_with_state": round(rate_with_state, 6),
        "rate_legal": round(rate_legal, 6),
        # ★ 两个数必须同时报（S12 判据：声明层与数据层的差必须可见）
        # ★ 2026-10-09 实测发现：# with_state 会把【字段名叫 state 的内容字段】也算进去
        #   （实例：裁判卡片里有 {"state": {"demo": …, "gate": …}} ⇒ with_state=1 而 legal=0）
        #   ⇒ **唯一合规率是 rate_legal**（值须在合法枚举内），rate_with_state 只作参考。
        "rate_is": "rate_legal（唯一合规率：state 值须在合法枚举内）",
        "note": "rate_with_state 仅作参考（会含同名字段）；协议合规率 = rate_legal",
    }


# ─────────────────────── 缺席可判别（S15）───────────────────────
def verdict(age_seconds, max_age=None):
    """返回 (ok, 一句话)。★ 三态：新鲜 / 陈旧 / **未核**（缺 ts 不得当作通过 ——
       这是 2026-10-09 从裁判的 self-report-gate 学到的：缺字段 ⇒ 记「未核」而非「通过」）。"""
    if age_seconds is None:
        return None, "★ **未核**：上报体缺 `ts` ⇒ 无法判陈旧（**不得当作通过**）"
    m = max_age if max_age is not None else STALE_THRESHOLD_SECONDS
    if age_seconds > m:
        return False, ("★ **缺席**：上报已 %.0f 秒未更新（阈值 %d 秒 = 刷新周期 %d × 2）"
                       " ⇒ **该判据的落地情况不可知**" % (age_seconds, m, REFRESH_SECONDS))
    return True, "新鲜：%.0f 秒前上报（阈值 %d 秒）" % (age_seconds, m)


def check(dry=False, now=None):
    now = now or int(time.time())
    raw = bb_get(REPORT_KEY)
    if "_error" in raw:
        return 1, {"error": raw["_error"], "verdict": "未核（读不到黑板）"}
    v = raw.get("value", raw)
    ts = v.get("ts") if isinstance(v, dict) else None
    age = (now - int(ts)) if ts else None
    ok, why = verdict(age)
    return (0 if ok else 1), {
        "ts": ts, "age_seconds": age,
        "threshold_seconds": STALE_THRESHOLD_SECONDS,
        "refresh_seconds": REFRESH_SECONDS,
        "ok": ok, "verdict": why,
        "rate_with_state": (v or {}).get("rate_with_state"),
        "total": (v or {}).get("total"),
    }


# ─────────────────────────── selftest ───────────────────────────
def selftest():
    """负例（必须被拒/判缺席）+ 正例（必须通过）。★ 不得只报 FAIL 数（今日教训）。"""
    fails, neg_n, pos_n = 0, 0, 0
    R = REFRESH_SECONDS

    def neg(name, cond, detail, expect=False):
        """★ 三态判据：负例可以期望 False（判缺席）**或** None（判未核）。
        —— 2026-10-09 自测自身踩坑：原实现只认 `is False`，于是「缺 ts ⇒ 未核」
           这条【正确的三态行为】被误判为 ❌。⇒ 判据必须容纳第三态。"""
        nonlocal fails, neg_n
        neg_n += 1
        good = (cond is expect) and (expect is not True)  # expect ∈ {False, None}
        print("  %s 负例 %-28s %s" % ("✅" if good else "❌", name, detail))
        if not good:
            fails += 1

    def pos(name, cond, detail):
        nonlocal fails, pos_n
        pos_n += 1
        good = (cond is True)
        print("  %s 正例 %-28s %s" % ("✅" if good else "❌", name, detail))
        if not good:
            fails += 1

    print("== cahac-compliance-report selftest ==")
    print("【第一段：负例（必须判缺席/未核）】")
    neg("陈旧 ⇒ 判缺席", verdict(R * 3)[0], "age=3×refresh ⇒ 应 False")
    neg("恰好超阈值 ⇒ 判缺席", verdict(R * 2 + 1)[0], "age=2×refresh+1 ⇒ 应 False")
    neg("缺 ts ⇒ 判【未核】(三态)", verdict(None)[0], "age=None ⇒ 应 **None**（既不是 True 也不是 False）", expect=None)


    print("【第二段：正例（必须通过）】")
    pos("新鲜 ⇒ 通过", verdict(10)[0], "age=10s ⇒ 应 True")
    pos("合规率 0 ≠ 缺席（两件事）", verdict(10)[0],
        "★ 合规率 0（未落地）而上报新鲜 ⇒ 仍 True：**不得把「没落地」误报成「没上报」**")
    pos("恰好等于阈值 ⇒ 通过", verdict(R * 2)[0], "age=2×refresh ⇒ 应 True（> 才判缺席）")
    pos("阈值由刷新周期导出", STALE_THRESHOLD_SECONDS == REFRESH_SECONDS * 2,
        "threshold=%d == refresh=%d × 2" % (STALE_THRESHOLD_SECONDS, R))
    pos("枚举为 v1.2.1 对齐后的 7 态",
        LEGAL_STATES == {"todo", "claimed", "done", "verified", "blocked", "failed", "timeout"},
        "7 态与 §7.2 一致")

    print("\n  ★ 判别力自证（关键）：**若阈值与刷新周期不同阶会怎样**")
    bad_threshold = 30  # 故意设成远小于刷新周期 ⇒ 「报警恒真」
    always_fires = all(verdict(a, bad_threshold)[0] is False
                       for a in (R, R + 1, R * 5))
    print("    阈值=%ds 而刷新=%ds ⇒ 任意 age 都判缺席 = %s（**这就是「报警恒真」**）"
          % (bad_threshold, R, always_fires))
    pos("恒真报警可被本自测识别", always_fires is True,
        "⇒ 证明『阈值须与刷新同阶』这条原则**可被机械检出**")

    print("\n  selftest: %d FAIL ｜ 反例 %d 条 / 正例 %d 条（0 FAIL = 有判别力且正例不误杀）"
          % (fails, neg_n, pos_n))
    return 0 if fails == 0 else 1



# ─────────────── 防漂移：plist 的 StartInterval 必须 == REFRESH_SECONDS ───────────────
PLIST = os.path.expanduser("~/Library/LaunchAgents/com.dsh.cahac-compliance-report.plist")


def verify_plist():
    """★ 落实 HR 2026-09-22 原则（见 bb-copy.py L983-985）：
       「刷新周期与阈值【都由一处导出】，plist 的 StartInterval 与阈值
         **不得各自硬编码而漂移**」⇒ 本函数把 plist 与脚本常量做一致性核对。"""
    import plistlib
    if not os.path.exists(PLIST):
        return None, "★ **未核**：plist 不存在（%s）⇒ 周期上报未装载" % PLIST
    try:
        d = plistlib.load(open(PLIST, "rb"))
    except Exception as e:
        return None, "★ **未核**：plist 解析失败（%s）" % type(e).__name__
    si = d.get("StartInterval")
    if si == REFRESH_SECONDS:
        return True, "一致：plist StartInterval=%s == 脚本 REFRESH_SECONDS=%s" % (si, REFRESH_SECONDS)
    return False, ("★ **漂移**：plist StartInterval=%s ≠ 脚本 REFRESH_SECONDS=%s"
                   " ⇒ 阈值（=%s×2）与真实刷新周期不同阶 ⇒ **报警可能恒真或恒假**"
                   % (si, REFRESH_SECONDS, REFRESH_SECONDS))


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser(description="CAHAC 合规率上报 + 缺席可判别")
    ap.add_argument("--report", action="store_true", help="算合规率并写黑板")
    ap.add_argument("--check", action="store_true", help="检查上报是否陈旧")
    ap.add_argument("--status", action="store_true", help="只读打印")
    ap.add_argument("--selftest", action="store_true", help="自测")
    ap.add_argument("--dry-run", action="store_true", help="零写盘")
    ap.add_argument("--verify-plist", action="store_true", help="核对 plist 与脚本常量是否漂移")
    ap.add_argument("--refresh-seconds", type=int, default=None,
                    help="覆盖刷新周期（阈值随之导出，不会漂移）")
    a = ap.parse_args()
    global REFRESH_SECONDS, STALE_THRESHOLD_SECONDS
    if a.refresh_seconds:
        REFRESH_SECONDS = a.refresh_seconds
        STALE_THRESHOLD_SECONDS = REFRESH_SECONDS * 2

    if a.verify_plist:
        ok, why = verify_plist()
        print(json.dumps({"ok": ok, "verdict": why}, ensure_ascii=False, indent=2))
        return 0 if ok is True else 1
    if a.selftest:
        return selftest()
    if a.status:
        rc, info = check(dry=True)
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return rc
    if a.check:
        rc, info = check()
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return rc
    if a.report:
        rep = compute_compliance()
        rep["refresh_seconds"] = REFRESH_SECONDS
        rep["stale_threshold_seconds"] = STALE_THRESHOLD_SECONDS
        w = bb_put(REPORT_KEY, rep, dry=a.dry_run)
        # ★ 写后必读（本体系纪律）
        rb = bb_get(REPORT_KEY) if not a.dry_run else {}
        landed = isinstance(rb.get("value"), dict) and rb["value"].get("ts") == rep["ts"]
        out = {"report": rep, "write": w,
               "readback_equal": landed if not a.dry_run else "skip(dry-run)"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if a.dry_run:
            return 0
        return 0 if landed else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
