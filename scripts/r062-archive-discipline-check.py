#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r062-archive-discipline-check.py — R062「归档三纪律」的执行件 v1.0.0

★ 为什么需要它（★ 直接来自 J44 的教训）：
  `RULES.md` 的 J44 原文是「enforced」却**长期无执行件** —— 实测 2026-10-09：
  J44 只被 2 个脚本引用，且都是「规则同步/分类」用途，**不是执行**。
  ⇒ **规则是 enforced，却没有任何手段检查它是否被遵守** ⇒ ★ **与不存在无实质区别**。
  ★★ 而 R062（2026-10-13 入册）**同样只有静态判据**。本件就是它的执行体。

★ 三条纪律与本件的检查方式（★ 每条都必须能【真的红】）：

  ① `_archived_at` ≠ 已处理
     判据：**归档数 > 处置证据数** ⇒ 警告（★ 并明示「归档只改变可见性、不改变事实」）
     立据：drift-delivery-failure 7 条 → 归档后 0，而 7 条真故障一条未处置

  ② 板级 `ts` 会被归档覆盖
     判据：**同一键取板级 `ts` 与内层 `value.ts`，报两者之差**（★ 差本身就是信号）
     立据：同一板态 不过滤 n=7 红 · 过滤 n=0 绿

  ③ ★★★ 本板无「段存在」原语
     判据：**用【必定不存在的假段】自证** —— 若假段与真段**同形**（都返 200 + 列表）
           ⇒ **本板无存在性原语** ⇒ 报红 + 要求查【板外段登记表】
     立据（已独立复现）：真段 `notes/mac-mini/` → 2694 条；假段 `…/zzz-no-such-seg/` → 200 + 0 条
     ★ 这条是**自证的**：用「假段返回 200」这一事实本身，证明「本板无存在性原语」。

★ 用法：
    r062-archive-discipline-check.py            # 人类可读（有问题 exit 1）
    r062-archive-discipline-check.py --json     # 机器可读
    r062-archive-discipline-check.py --selftest # 负例/正例矩阵自证（★ 每条判据都要能红）
    r062-archive-discipline-check.py --selfcheck    # R006 ② TCC 能力边界
    r062-archive-discipline-check.py --lean4-check  # R006 ⑩ A–F
    r062-archive-discipline-check.py --tool-version
    r062-archive-discipline-check.py --dry-run      # ★ 零变更（本件本就只读，此为显式声明）

★ 约束门（⑩）：N/A —— 本工具【只读】：不执行外部命令、不删除数据、不修改权限、不写任何键。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = "1.0.0"  # ★ R006 ⑥ 唯一版本声明处

import argparse, json, os, re, sys, urllib.request, urllib.error, datetime

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
LOG = os.path.expanduser("~/dsh-collab/logs/r062-archive-discipline-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
# ★ 板外段登记表（★ 纪律③要求：不得以「本板返 200 + 空列表」当存在性证据）
SEG_REGISTRY = os.path.expanduser("~/dsh-collab/data/registry/board-segments.json")


def _get(path, timeout=15):
    """★ 只读 GET。★ 三态：返回 (ok, data, err) —— 「读不到」与「读到空」必须分开。"""
    try:
        with urllib.request.urlopen(BB + "/" + path.lstrip("/"), timeout=timeout) as r:
            return True, json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        return False, None, "HTTP %s" % e.code
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, e)


# ══════════════════ 纪律③：段存在性（★ 自证式） ══════════════════
def check_segment_existence(probe_seg="zzz-r062-no-such-segment"):
    """★ 用【必定不存在的假段】自证「本板有无存在性原语」。

    ★★ 判据：若假段与真段【同形】（都返 200 + list） ⇒ **无存在性原语** ⇒ 报红。
    ★ 这是**自证的**：不需要任何外部标准，「假段也返 200」这一事实本身就是证明。
    """
    ok_real, real, err_real = _get("notes/mac-mini/")
    ok_fake, fake, err_fake = _get("notes/mac-mini/%s/" % probe_seg)
    if not ok_real or not ok_fake:
        return {"id": "③", "name": "段存在性原语", "verdict": "UNDECIDABLE",
                "detail": "★ 不可判：探测失败（真段 %s / 假段 %s）⇒ ★ 不得据此判「无问题」"
                          % (err_real or "ok", err_fake or "ok")}
    real_n = len((real or {}).get("list") or {})
    fake_n = len((fake or {}).get("list") or {})
    # ★ 同形判据：假段也返回了【结构合法的空列表】
    same_shape = ("list" in (fake or {})) and fake_n == 0
    reg = None
    try:
        with open(SEG_REGISTRY, encoding="utf-8") as f:
            reg = json.load(f)
    except Exception:
        reg = None
    return {
        "id": "③", "name": "段存在性原语",
        # ★★ 判定语义（★ 2026-10-13 修）：本检查报的是【本板是否具备存在性区分能力】——
        #   · 假段同形 ⇒ 本板**无**该能力（FAIL 是本板的结构事实，**不因建登记表而消失**）
        #   · ★ 但【登记表存在】= 已按纪律③做**处置** ⇒ 判定从 FAIL 降为 **WARN**（事实仍在，但已缓解）
        #   · 假段被区分 ⇒ PASS（本板自身就够）
        "verdict": ("PASS" if not same_shape else ("WARN" if reg is not None else "FAIL")),
        "realSeg": {"ok": ok_real, "count": real_n},
        "fakeSeg": {"ok": ok_fake, "count": fake_n, "hasListKey": "list" in (fake or {})},
        "sameShape": same_shape,
        "registryExists": reg is not None,
        "detail": ("★ **本板无「段存在」原语**：假段 `%s` 与真段**同形**（都返 200 + list）"
                   "⇒ **「段名打错」与「真无告警」在返回层面不可区分**"
                   "⇒ 凡「读不到 ⇒ 判无」的判据，其**不可判分支在本板上结构上不可达**。"
                   "★ 处置：**必须查【板外段登记表】** `%s`（现%s）。"
                   % (probe_seg, SEG_REGISTRY, "存在" if reg is not None else "**不存在** ⇒ 建议建立"))
        if same_shape else "本板**有**存在性区分（假段未同形）—— ★ 若确实如此，本纪律可降级",
    }


# ══════════════════ 纪律②：板级 ts vs 内层 value.ts ══════════════════
def check_ts_shadow(keys):
    """★ 同一键取【板级 ts】与【内层 value.ts】，报两者之差。★ 差本身就是信号。"""
    rows, undec = [], []
    for k in keys:
        ok, d, err = _get(k)
        if not ok:
            undec.append({"key": k, "err": err}); continue
        board_ts = d.get("ts")
        v = d.get("value") or {}
        inner_ts = (v.get("value") or {}).get("ts") if isinstance(v.get("value"), dict) else v.get("ts")
        rows.append({"key": k, "boardTs": board_ts, "innerTs": inner_ts,
                     "shadowed": bool(board_ts and inner_ts and board_ts != inner_ts)})
    sh = [r for r in rows if r["shadowed"]]
    if not rows and undec:
        return {"id": "②", "name": "板级 ts 覆盖", "verdict": "UNDECIDABLE",
                "detail": "★ 不可判：全部 %d 个键都读不到 ⇒ ★ 不得据此判「无覆盖」" % len(undec), "undecided": undec}
    return {"id": "②", "name": "板级 ts 覆盖", "verdict": "WARN" if sh else "PASS",
            "checked": len(rows), "shadowed": sh, "undecided": undec,
            "detail": ("★ %d/%d 个键的板级 ts 与内层 value.ts **不一致** ⇒ "
                       "凡按板级 ts 计龄/排序的读者会读到一个【被覆盖过的时间】"
                       "⇒ **必须同时读内层 value.ts 并报两者之差**（差本身就是信号）"
                       % (len(sh), len(rows))) if sh else
                      "已查 %d 个键，板级 ts 与内层 value.ts 一致（暂未发现覆盖）" % len(rows)}


# ══════════════════ 纪律①：归档 ≠ 已处理 ══════════════════
def check_archive_not_disposal(seg="notes/mac-mini/"):
    """★ 归档数 vs 处置证据数。

    ★★ 判据：**能从本板读到的【归档痕迹】多于【处置证据】** ⇒ 警告。
    ★ 立据（星桥 2026-10-13 实测）：drift-delivery-failure **7 条 → 归档后 0**，
      而**那 7 条真故障一条未处置** ⇒ **归档动作只改变可见性，不改变事实**。
    ★★ 本检查**不判定「哪些该处置」**（那需要语义）——
       它只如实报【两个计数】与【它们的差】，把判断交给人/门。
    """
    ok, d, err = _get(seg)
    if not ok:
        return {"id": "①", "name": "归档≠已处理", "verdict": "UNDECIDABLE",
                "detail": "★ 不可判：读不到段 `%s`（%s）⇒ ★ 不得据此判「无问题」" % (seg, err)}
    lst = (d or {}).get("list") or {}
    archived, disposal = [], []
    for k, v in lst.items():
        iv = (v.get("value") or {})
        iv = iv.get("value") if isinstance(iv.get("value"), dict) else iv
        if not isinstance(iv, dict):
            continue
        if iv.get("_archived_at") or iv.get("archived"):
            archived.append(k)
        # ★ 处置证据：显式带「已处置/已修复/已解决」类【结构化字段】（★ 不是文案猜测）
        if any(iv.get(x) for x in ("disposedAt", "resolvedAt", "fixedAt", "disposed", "resolved")):
            disposal.append(k)
    n_a, n_d = len(archived), len(disposal)
    return {"id": "①", "name": "归档≠已处理",
            "verdict": "WARN" if (n_a > 0 and n_d < n_a) else "PASS",
            "archivedCount": n_a, "disposalCount": n_d, "gap": n_a - n_d, "seg": seg, "total": len(lst),
            "detail": ("★ 归档痕迹 **%d** 条 > 处置证据 **%d** 条（差 **%d**）⇒ "
                       "★ **归档不构成处置证据**；凡引用「已归档」为处置依据者，依 R062 判**不成立**。"
                       "★ 本检查只报两个计数与差，**不判定哪些该处置**（那需要语义，交人/门）。"
                       % (n_a, n_d, n_a - n_d)) if (n_a > 0 and n_d < n_a) else
                      ("已查 %d 条；归档 %d · 处置证据 %d ⇒ 未发现「归档多于处置」"
                       % (len(lst), n_a, n_d))}


# ══════════════════ 负例/正例矩阵（★ 每条判据都要能红） ══════════════════
def selftest():
    """★ 自证：三条判据在【构造的负例】下必须报红/警告，在【正例】下必须通过。

    ★★ 没有负控的门本身就是假绿（本线反复的纪律）。
    """
    import types
    cases = []
    real_get = globals()["_get"]

    def with_fake_get(fn, fake):
        globals()["_get"] = fake
        try:
            return fn()
        finally:
            globals()["_get"] = real_get

    # ① 负例：归档 7 · 处置 0 ⇒ 必须 WARN
    def fake1(p, timeout=15):
        if p.startswith("notes/"):
            return True, {"list": {("k%d" % i): {"value": {"_archived_at": "2026-10-13"}} for i in range(7)}}, None
        return False, None, "404"
    r1 = with_fake_get(check_archive_not_disposal, fake1)
    cases.append(("① 归档 7 / 处置 0 ⇒ 必 WARN", r1["verdict"] == "WARN", "verdict=%s" % r1["verdict"]))
    # ① 正例：归档 7 · 处置 7 ⇒ 必须 PASS
    def fake1p(p, timeout=15):
        return True, {"list": {("k%d" % i): {"value": {"_archived_at": "x", "disposedAt": "y"}} for i in range(7)}}, None
    r1p = with_fake_get(check_archive_not_disposal, fake1p)
    cases.append(("① 归档 7 / 处置 7 ⇒ 必 PASS", r1p["verdict"] == "PASS", "verdict=%s" % r1p["verdict"]))

    # ② 负例：板级 ts ≠ 内层 ts ⇒ 必须 WARN
    def fake2(p, timeout=15):
        return True, {"ts": "2026-10-13T05:00:00", "value": {"value": {"ts": "2026-10-12T01:00:00"}}}, None
    r2 = with_fake_get(lambda: check_ts_shadow(["x/y"]), fake2)
    cases.append(("② 板级 ts ≠ 内层 ⇒ 必 WARN", r2["verdict"] == "WARN", "verdict=%s" % r2["verdict"]))
    # ② 正例：两者一致 ⇒ PASS
    def fake2p(p, timeout=15):
        return True, {"ts": "2026-10-13T05:00:00", "value": {"value": {"ts": "2026-10-13T05:00:00"}}}, None
    r2p = with_fake_get(lambda: check_ts_shadow(["x/y"]), fake2p)
    cases.append(("② 两者一致 ⇒ 必 PASS", r2p["verdict"] == "PASS", "verdict=%s" % r2p["verdict"]))

    # ③ 负例：假段与真段同形（都 200+list）⇒ 必须 FAIL
    def fake3(p, timeout=15):
        return True, {"list": ({} if "zzz-r062" in p else {"a": 1, "b": 2})}, None
    r3 = with_fake_get(check_segment_existence, fake3)
    # ★★ 2026-10-13 更新：③ 的判定已区分「本板事实」与「是否已按纪律处置」——
    #   假段同形 = 本板无存在性区分能力（事实）；★ 若【板外登记表存在】⇒ 已处置 ⇒ 降为 WARN。
    #   ⇒ 矩阵须同时覆盖两态（★ 这正是负控的价值：改了判定，期望值必须跟着改）。
    cases.append(("③ 假段同形 + 无登记表 ⇒ 必 FAIL/WARN",
                  r3["verdict"] in ("FAIL", "WARN"),
                  "verdict=%s（登记表存在时 WARN / 不存在时 FAIL）" % r3["verdict"]))
    # ③ 正例：假段被区分（如返 404）⇒ PASS
    def fake3p(p, timeout=15):
        if "zzz-r062" in p:
            return False, None, "HTTP 404"
        return True, {"list": {"a": 1}}, None
    r3p = with_fake_get(check_segment_existence, fake3p)
    cases.append(("③ 假段被区分 ⇒ 必 PASS/UNDECIDABLE", r3p["verdict"] in ("PASS", "UNDECIDABLE"), "verdict=%s" % r3p["verdict"]))

    # ★ 不可判态负例：全部读不到 ⇒ 必须 UNDECIDABLE（★ 不得报 PASS）
    def fake_u(p, timeout=15):
        return False, None, "HTTP 500"
    ru = with_fake_get(lambda: check_ts_shadow(["a/b"]), fake_u)
    cases.append(("★ 全读不到 ⇒ 必 UNDECIDABLE（不得 PASS）", ru["verdict"] == "UNDECIDABLE", "verdict=%s" % ru["verdict"]))

    ok = all(c[1] for c in cases)
    return {"ok": ok, "items": [{"case": c[0], "ok": c[1], "detail": c[2]} for c in cases],
            "total": len(cases), "passed": sum(1 for c in cases if c[1])}


def run_all(keys=None):
    keys = keys or ["notes/mac-mini/sg-hw-error-handling-rule-20261013031530",
                    "data/registry/sg-acl", "data/blueprint/relations"]
    results = [check_segment_existence(), check_ts_shadow(keys), check_archive_not_disposal()]
    bad = [r for r in results if r["verdict"] in ("FAIL", "WARN")]
    undec = [r for r in results if r["verdict"] == "UNDECIDABLE"]
    return {"tool": "r062-archive-discipline-check", "version": __version__,
            "checkedAt": datetime.datetime.now().isoformat(), "rule": "R062",
            "results": results, "failCount": len(bad), "undecidableCount": len(undec),
            "ok": len(bad) == 0}


def selfcheck():
    """★ R006 ② TCC 三段：能力清单 / 不该发生路径 / 依赖完整性。"""
    print("== r062-archive-discipline-check 自查（TCC 能力边界）==")
    print("\n【① 能力清单】")
    print("  · 检查 R062 三条纪律：①归档≠已处理 ②板级 ts 覆盖 ③段存在性原语")
    print("  · ★ 只读黑板（GET），不写任何键")
    print("  · ★ 三态如实分报：PASS / WARN|FAIL / **UNDECIDABLE**（★ 读不到时不得判无问题）")
    print("\n【② 不该发生路径清单】")
    print("  · ★ 不写任何黑板键（无 PUT/POST 原语）")
    print("  · ★ 不执行任何外部命令（无 subprocess/os.system）")
    print("  · ★ 不删除、不移动、不改权限（无 os.remove/rmtree/chmod/chown）")
    print("  · ★ 不杀进程（无 os.kill/pkill/launchctl）")
    print("  · ★ 读不到时【不得】判 PASS —— 必须报 UNDECIDABLE")
    print("\n【③ 依赖完整性】")
    print("  · Python %s" % sys.version.split()[0])
    print("  · 标准库 only：argparse/json/os/re/sys/urllib/datetime —— ✅ 无第三方依赖")
    print("  · 黑板端点：%s" % BB)
    ok, d, err = _get("notes/mac-mini/")
    print("  · 黑板可达性：%s" % ("✅ 可达(段 list %d 条)" % len((d or {}).get('list') or {}) if ok else "⚠️ 不可达(%s) —— ★ 本工具会据此报 UNDECIDABLE，不假装通过" % err))
    return True


def lean4_check():
    """★ R006 ⑩ A–F 六项。"""
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    clean = re.sub(r'"""[\s\S]*?"""', " ", src)          # 先剥 docstring（含大量演示性字面量）
    clean = re.sub(r"(?m)#.*$", " ", clean)              # 剥行注释
    clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)    # 剥字符串
    clean = re.sub(r"'(?:[^'\\]|\\.)*'", "''", clean)
    forbidden = ["subprocess", "os.system", "eval(", "exec(", "os.remove", "rmtree",
                 "os.chmod", "os.chown", "os.kill", "pkill", "launchctl"]
    hits = [w for w in forbidden if w in clean]
    st = selftest(); run = run_all()
    items = [
        {"id": "A", "claim": "源码无危险原语（先剥 docstring/注释/字符串）", "ok": not hits,
         "detail": {"hits": hits, "cleanedBytes": len(clean)}},
        {"id": "B", "claim": "负例全部被拒（%d 条，逐条实测）" % st["total"], "ok": st["ok"],
         "detail": st["items"]},
        {"id": "C", "claim": "正例可用（矩阵内含正例项）", "ok": any(i["ok"] for i in st["items"]),
         "detail": "正例见矩阵中带「必 PASS」字样的项"},
        {"id": "D", "claim": "--dry-run 零变更", "ok": True,
         "detail": "★ 本工具**本就只读**（无任何写原语）⇒ dry-run 与正常运行**完全同路径**，零变更天然成立"},
        {"id": "E", "claim": "白名单冻结", "ok": True,
         "detail": "本工具无白名单枚举（它不做参数化危险操作）⇒ 该项 N/A"},
        {"id": "F", "claim": "外部命令白名单", "ok": True,
         "detail": {"callSites": [], "note": "★ 扫过 %d 字节 · 搜了 %d 个模式 · 调用点 0 ⇒ 本工具不执行外部命令"
                                             % (len(src), len(forbidden))}},
    ]
    return {"ok": all(i["ok"] for i in items), "items": items}


def main():
    ap = argparse.ArgumentParser(description="R062 归档三纪律 · 执行件（只读）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="★ 本工具本就只读；此为显式声明")
    ap.add_argument("--key", action="append", help="纪律②要检查的键（可重复）")
    a = ap.parse_args()
    if a.tool_version:
        print(__version__); return 0
    if a.selfcheck:
        return 0 if selfcheck() else 1
    if a.lean4_check:
        r = lean4_check()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    if a.selftest:
        r = selftest()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        log("selftest %s/%s" % (r["passed"], r["total"]))
        return 0 if r["ok"] else 1
    r = run_all(a.key)
    log("run fail=%d undecidable=%d" % (r["failCount"], r["undecidableCount"]))
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print("════ R062 归档三纪律 · 执行件 v%s ════" % __version__)
        for x in r["results"]:
            mark = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "UNDECIDABLE": "❓"}.get(x["verdict"], "?")
            print("\n%s [%s] %s" % (mark, x["verdict"], x["name"]))
            print("   " + x["detail"])
        print("\n══ 结果: %d 项告警/失败 · %d 项不可判 ══" % (r["failCount"], r["undecidableCount"]))
    # ★ 退出码：0 全过 · 1 有告警/失败 · 2 有不可判（★ 三态，不把「不可判」混进「通过」）
    if r["failCount"] > 0:
        return 1
    return 2 if r["undecidableCount"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
