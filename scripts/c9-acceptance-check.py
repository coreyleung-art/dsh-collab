#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""c9-acceptance-check.py — G11/C9 验收的机械读法（v1.0.0）

依据：独立复核员 2026-10-08 **重载前预登记**的读法：
  断言1（运行态版本）：重载后至少一条成功日志行含 `runtimeVersion`，且**等于**磁盘 package.json 的 version
                      ⇒ 唯此能证「运行中的构建 = 磁盘上的构建」。
  断言2（重试可见）：未重试 ⇒ retryCount==0 且 calls[] 无 `(retry N)` 步骤；
                    发生重试 ⇒ retryCount == 重建法 k，且 calls[] 出现 `GET <板> (retry N)`（N 从 1 递增）。
  ★ 重建法保留的理由：**计数器不能自证** —— 若仪表报 0 而 k>0 ⇒ 判 FAIL（先查仪表），不采信计数器。

用法: python3 c9-acceptance-check.py [--log <path>] [--json] [--selftest] [--version]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== c9-acceptance-check 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · c9-acceptance-check.py — G11/C9 验收的机械读法（v1.0.0）")
    print("  · 依据：独立复核员 2026-10-08 **重载前预登记**的读法：")
    print("  · 断言1（运行态版本）：重载后至少一条成功日志行含 `runtimeVersion`，且**等于**磁盘 package.json 的 version")
    print("  · ⇒ 唯此能证「运行中的构建 = 磁盘上的构建」。")
    print("  · 命令/参数: log, json, selftest, version")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, tempfile")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/c9-acceptance-check.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

import argparse, json, os, re, sys, datetime

VERSION = "1.0.0"
__version__ = VERSION
LOG = os.path.expanduser("~/dsh-collab/logs/bb-card-send.log")
PKG = os.path.expanduser("~/dsh-plugin-bb-card-send/package.json")


def disk_version():
    try:
        return json.load(open(PKG, encoding="utf-8")).get("version")
    except Exception:
        return None


def load_success_lines(path):
    out = []
    try:
        for ln in open(path, encoding="utf-8", errors="ignore"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if d.get("result") in ("OK", "OK-WITH-TIMEOUT"):
                out.append(d)
    except FileNotFoundError:
        pass
    return out


CUM = [5000, 15000, 35000, 75000, 135000, 195000, 240000]   # 复核员预登记的累积退避（ms）


def reconstruct_k(elapsed_ms, call_ms_sum):
    """复核员的重建法：k = max{k : cum_k ≤ elapsed − Σcalls}（cum=[5,15,35,75,135,195,240]s）"""
    if elapsed_ms is None:
        return None
    budget = elapsed_ms - (call_ms_sum or 0)
    k = 0
    for i, c in enumerate(CUM, start=1):
        if c <= budget:
            k = i
    return k


def check(path=LOG, disk=None):
    disk = disk or disk_version()
    lines = load_success_lines(path)
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not lines:
        return {"observed_at": at, "verdict": "未证", "reason": "日志中无成功记录 ⇒ 无从判定"}
    latest = lines[-1]
    rv = latest.get("runtimeVersion")
    a1 = bool(rv) and rv == disk
    # 断言2：calls[] 中的 (retry N) 步数与 retryCount 对账
    calls = latest.get("calls") or []
    retry_steps = [c.get("step") for c in calls if isinstance(c, dict) and re.search(r"\(retry \d+\)", str(c.get("step")))]
    k = len(retry_steps)
    rc = latest.get("retryCount")
    call_ms_sum = sum(int(c.get("ms") or 0) for c in calls if isinstance(c, dict))
    k_time = reconstruct_k(latest.get("elapsedMs"), call_ms_sum)   # 复核员公式
    # ★ 2026-10-08 独立复核员：a2_state 曾用旧规则（含 or k_time==rc）⇒ 与判定**双规则并存**，
    #   出现「verdict=FAIL 而摘要说一致」的相反信号。现**与判定同一规则**（单一来源）。
    if k == 0 and rc == 0:
        a2_state = "未观测到重试"
    elif k == rc and k > 0:
        a2_state = "一致"
    else:
        a2_state = "不一致"
    # 时间法仅作「不得矛盾」的交叉核对；不一致则**显式标记**（结构化字段，非仅在文案里）
    a2_marked_inconsistency = bool(k_time is not None and k > 0 and k_time != k)
    if rv is None:
        verdict, reason = "未证", ("最近成功日志**无 runtimeVersion 字段** ⇒ 运行态尚未加载到带该字段的构建"
                                   "（重载未发生）；断言1 不成立")
    elif not a1:
        verdict, reason = "FAIL", f"runtimeVersion={rv} ≠ 磁盘 version={disk} ⇒ 运行中的构建与磁盘不一致"
    elif k == 0 and rc == 0:
        # ★ 复核员限定：不得因「一直没重试」判 PASS ⇒ 断言2 记未证
        verdict, reason = "未证", ("断言1 成立（runtimeVersion == 磁盘版本），但**断言2 未证**："
                                   "重载后尚未观测到任何重试 ⇒ 不得因「一直没重试」判 PASS")
    elif k == rc and k > 0:
        # ★ PASS 必须由**自包含信号**（calls[] 的 (retry N) 步数）成立；时间法只作交叉核对，
        #   不得用来把「无步骤」的情形抬成 PASS（复核员 2026-10-08「半修旁路」用例）。
        xnote = "" if (k_time is None or k_time == k) else f"；★交叉核对：时间法 k¹={k_time} ≠ 步骤计数 k={k} ⇒ 标记不一致"
        verdict, reason = "PASS", (f"断言1 成立；断言2：k={k} 个 (retry N) 步骤 == 仪表 retryCount={rc}，"
                                   f"且 calls[] 确含 (retry N){xnote}")
    elif rc == k and k == 0:
        verdict, reason = "未证", "断言2 未证：未观测到重试（不得因「一直没重试」判 PASS）"
    elif k_time is not None and k_time == rc and k == 0:
        # ★ 半修形态：仪表声称重试，但 calls[] 无任何 (retry N) 步骤 ⇒ 自包含信号不成立
        verdict, reason = "FAIL", (f"★ 半修旁路（复核员用例）：仪表 retryCount={rc} 且时间法 k¹={k_time} 相符，"
                                   f"但 **calls[] 中没有任何 (retry N) 步骤** ⇒ 自包含信号不成立 ⇒ 不得判 PASS")
    else:
        verdict, reason = "FAIL", (f"★ 计数器不能自证：重建法 k={k}（时间法 {k_time}）而仪表 retryCount={rc} "
                                   f"不一致 ⇒ 先查仪表（历史缺陷：成功路径曾硬编码 retryCount:0）")
    return {"observed_at": at, "disk_version": disk, "latest_log_at": latest.get("at"),
            "runtimeVersion": rv, "retryCount_instrument": rc,
            "reconstruction_k_calls": k, "reconstruction_k_time": k_time,
            "assertion1_runtime_version_matches_disk": a1,
            "assertion2_state": a2_state,
            "assertion2_marked_inconsistency": a2_marked_inconsistency,
            "criterion": ("断言1: 日志 runtimeVersion 存在且 == 磁盘 version；"
                          "断言2: PASS 需**自包含信号** k(calls[] 的 (retry N) 步数) == 仪表 retryCount 且 k>0；"
                          "k=0 且 rc=0 ⇒ 未证（不得因『一直没重试』判 PASS）；"
                          "时间法 k¹ 仅作**不得矛盾**的交叉核对——若 k¹≠k 则置 assertion2_marked_inconsistency=true **并保留 PASS**"
                          "（本选择为预登记口径：标记而非降级；使用者若需更保守，可据此字段自行降级）"),
            "verdict": verdict, "reason": reason,
            "pre_registered_by": "独立复核员 2026-10-08（重载前写下；含重建法公式与「不得因未重试判 PASS」限定）"}


def selftest():
    ok = fail = 0
    def chk(c, l):
        nonlocal ok, fail
        if c: ok += 1; print("  ✅", l)
        else: fail += 1; print("  ❌", l)
    import tempfile
    def w(lines):
        f = tempfile.NamedTemporaryFile("w", suffix=".log", delete=False, encoding="utf-8")
        for d in lines: f.write(json.dumps(d, ensure_ascii=False) + "\n")
        f.close(); return f.name
    # 正例：runtimeVersion == disk，未重试
    p = w([{"result": "OK", "at": "t1", "runtimeVersion": "9.9.9", "retryCount": 0, "calls": [{"step": "PUT local"}]}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "未证", "正例：版本一致但未重试 ⇒ 断言2 未证（按复核员限定）")
    # ★ 半修回归（复核员 2026-10-08）：rc=1 但 calls[] 无 (retry N) ⇒ 不得 PASS
    p = w([{"result": "OK", "at": "t-half", "runtimeVersion": "9.9.9", "retryCount": 1, "elapsedMs": 30000,
            "calls": [{"step": "PUT local"}, {"step": "GET local"}, {"step": "PUT central"}, {"step": "GET central"}]}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "FAIL", "★负控·半修(rc=1 但无 retry 步) ⇒ FAIL，不得 PASS")
    # 正例：rc=1 且 calls[] 含 1 个 retry 步 ⇒ PASS
    p = w([{"result": "OK", "at": "t-full", "runtimeVersion": "9.9.9", "retryCount": 1, "elapsedMs": 30000,
            "calls": [{"step": "PUT local"}, {"step": "GET local"}, {"step": "GET local (retry 1)"},
                      {"step": "PUT central"}, {"step": "GET central"}]}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "PASS", "正例·rc=1 且含 1 retry 步 ⇒ PASS（自包含信号成立）")
    # 负控①：无 runtimeVersion ⇒ 未证（不判 PASS）
    p = w([{"result": "OK", "at": "t2", "retryCount": 0, "calls": []}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "未证", "负控：无 runtimeVersion ⇒ 未证（不蒙混为 PASS）")
    # 负控②：版本不符 ⇒ FAIL
    p = w([{"result": "OK", "at": "t3", "runtimeVersion": "1.0.0", "retryCount": 0, "calls": []}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "FAIL", "负控：runtimeVersion≠磁盘 ⇒ FAIL")
    # 负控③：重建法 k>0 而仪表报 0 ⇒ FAIL（计数器不能自证）
    p = w([{"result": "OK", "at": "t4", "runtimeVersion": "9.9.9", "retryCount": 0,
            "calls": [{"step": "GET local (retry 1)"}]}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "FAIL", "负控：k=1 而仪表 0 ⇒ FAIL（先查仪表）")
    # 正例2：k == retryCount
    p = w([{"result": "OK", "at": "t5", "runtimeVersion": "9.9.9", "retryCount": 2,
            "calls": [{"step": "GET local (retry 1)"}, {"step": "GET central (retry 2)"}]}])
    r = check(p, disk="9.9.9"); chk(r["verdict"] == "PASS", "正例2：k=2 == retryCount=2 ⇒ PASS")
    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=LOG); ap.add_argument("--json", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--selftest", action="store_true"); ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version: print(json.dumps({"tool": "c9-acceptance-check", "version": VERSION})); return 0
    if a.selftest: return selftest()
    r = check(a.log)
    if a.json: print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"observed_at={r['observed_at']}  磁盘 version={r.get('disk_version')}")
        print(f"  最近成功日志 at={r.get('latest_log_at')}  runtimeVersion={r.get('runtimeVersion')}")
        print(f"  重建法 k={r.get('reconstruction_k')}  仪表 retryCount={r.get('retryCount_instrument')}")
        print(f"  → 判定：{r['verdict']}")
        print(f"    依据：{r['reason']}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
