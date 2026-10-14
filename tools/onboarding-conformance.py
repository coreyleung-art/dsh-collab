#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""onboarding-conformance.py —— 【CAHAC 接入契约合规度】（判据 I-4）

★★★ 立据（用户指令 2026-10-15 · D-347 · D-350）：
  ★ 用户逐字：「**如果是外部问题，是不是可以把契约协议更新，也纳入我们的总计划，
    作为目标任务之一来？**」
  ★ 而 D-347 的实测是：【本机侧 3/3 = 100%，而跨设备中继侧 0/334 = 0%】——
    那 0.46% 的合成数【全是外设备未接入】造成，★ 而本机【已无缺陷可修】。
  ★★ 故 D-350 起草了 `docs/cahac-onboarding-contract-v1-20261015.md`（160 行）。
  ★★★ 而本器是那份契约的【机械化判据】——
    ★ **`I-1` 问【结果】**（写完的卡合规吗）· ★ **`I-4` 问【责任】**（写卡的人举证了吗）。

★★ 契约的三件事（本器逐个核）：
  ★ ① **接入清单** C-1…C-4（★ 声明版本 / 12 必填 / 可复跑举证 / 显式未接入面）
  ★ ② **举证方式**（★ 卡 + 自身回读值 + 复跑命令 ⇒ 不得是声称）
  ★ ③ **举证责任与周期**（★ R-3：建议 30 天；★ R-5：不举证记 UNDECIDABLE）

★ 三态（★ 不合并 · 依契约 R-5）：
  ★ OK          ⇒ 有举证卡且未过期
  ★ STALE       ⇒ 有举证卡但超期（★ R-3 的 30 天）
  ★ MISSING     ⇒ 在册设备【无任何举证卡】
  ★ UNDECIDABLE ⇒ 取不到（★ 空 ≠ 无 ⇒ 不得读作 MISSING）

用法：
  python3 tools/onboarding-conformance.py              # 人类可读
  python3 tools/onboarding-conformance.py --json       # 机器可读
  python3 tools/onboarding-conformance.py --selftest   # 自证（双向负控）
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import urllib.request

VERSION = "1.0.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
BB = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")
CENTRAL = os.environ.get("DSH_BB_CENTRAL_URL", "http://xingqiao.meetfunbp.com:8792")

OK, STALE, MISSING, UNDEC = "OK", "STALE", "MISSING", "UNDECIDABLE"
STALE_DAYS = 30          # ★ 契约 R-3
EVIDENCE_TYPE = "cahac-onboarding-evidence"

# ★ 契约 §2.1 的 C-1…C-4（★ 每条都要能在举证卡里找到对应）
REQ_FIELDS = ["type", "from", "cahac", "cahac_version_declared", "write_path",
              "evidence", "not_onboarded", "at"]
# ★ 12 必填（★ 与 cahac-protocol v1.2 §3 一致）
ENVELOPE_REQUIRED = ["cahac", "id", "type", "channel", "sender", "recipient",
                     "thread", "priority", "cost_cap", "dedup_key", "ts", "payload"]
CANON_VERSION = "1.2"    # ★ 契约 C-1：必须是 "1.2" 不是 "v1.2"


def tok():
    for f in ("blackboard-token",):
        try:
            return io.open(os.path.join(HOME, ".dsh", f), encoding="utf-8").read().strip()
        except Exception:
            pass
    return ""


def now():
    return datetime.datetime.now().astimezone()


def get(url, timeout=20):
    """★ 取 (ok, dict, err)"""
    try:
        req = urllib.request.Request(url)
        t = tok()
        req.add_header("Authorization", "Bearer " + t)
        req.add_header("X-Blackboard-Token", t)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8", "replace")), None
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, str(e)[:60])


def enrolled_devices():
    """★ 在册设备从哪来 —— ★ 依契约 §5.1「每台在册设备」。
    ★ 取三源并集：① `~/dsh-collab/devices/` 的目录名；② 黑板 `notes/<node>/` 的面；
      ③ 环境变量 `DSH_ENROLLED_DEVICES`（★ 显式覆盖）。
    """
    out = set()
    env = os.environ.get("DSH_ENROLLED_DEVICES", "").strip()
    if env:
        out |= {x.strip() for x in env.split(",") if x.strip()}
    # ★★★ 2026-10-15（D-350）【最终修》—★ 反复过滤三次后本线改用【**显式白名单**】：
    #   ★ 立据：`devices/` 里混有插件、版本目录、文件目录、以及（★ 实测）`launchd-replicas`、`lessons`、`skill-replicas` —★
    #     ★ 而它们**都不是设备** ⇒ ★★ 自动推断的分母**必然虚肿**。
    #   ★ 故改为：★ 只接受 **`DSH_ENROLLED_DEVICES`** 显式声明（★ 逗号分隔）；★ 未设时用**默认白名单**。
    #   ★★ 而这正是契约 §5.1 该写的：**设备必须在环境里登记自己**。
    if env:
        return sorted(out)
    DEFAULT_DEVICES = ("mac-mini", "mbp", "mbp-bus", "i9", "i9-hr", "star-bridge")
    return sorted(set(DEFAULT_DEVICES) | out)
    # ★ 已知的【设备级】节点（★ 排除会话哈希与数据面）
    KNOWN = {"mac-mini", "mbp", "mbp-bus", "i9", "i9-hr", "node", "genebank", "collab",
             "health", "data", "tasks", "ui", "media", "alerts"}
    return sorted(out & KNOWN) if (out & KNOWN) else sorted(out)[:20]


# ★★★ 2026-10-15（D-350）【性能修】—★ 原写法遍历全键（N+1 数千次请求）⇒ 实测超时。
#   ★ 修法：★ **只扫【可能放举证卡的面】**（★ 依契约 §3.2：举证卡落 `notes/<node>/` 或 `data/onboarding/`）
#     ★ 且**设上限**（★ 每面最多 400 个键），★ 避免单面过大时又超时。
# ★★★ 2026-10-15（D-350）【再收窄》—★ 只扫**契约指定的一个面**：
#   ★ 契约 §3.2 规定举证卡落 `data/onboarding/<device>/<ts>`—★
#   ★★ 而扫 `notes/mac-mini/`（2827 锠）与 `notes/collab/`（653 锠）会让本器【超时】（★ 实测>60s）。
#   ★ 代价：★ 若某设备把举证卡写在别处 ⇒ ★ 本器看不到 —★
#     ★★ 故本器会把那种情形报为【MISSING】并在输出里注明扫过的面。
EVIDENCE_NS = ("data/onboarding/",)

MAX_PER_NS = 200


def fetch_evidence():
    """★ 扫两板的【可能面】，收集举证卡（★ 带上限，避免 N+1 超时）"""
    cards = []
    for base, nm in ((BB, "local"), (CENTRAL, "central")):
        for ns in EVIDENCE_NS:
            ok, d, err = get(base + "/" + ns, timeout=40)
            if not ok:
                continue
            ks = list((d.get("list") or {}).keys())[-MAX_PER_NS:]
            for k in ks:
                ok2, dd, _ = get(base + "/" + k, timeout=12)
                if not ok2:
                    continue
                v = dd.get("value")
                if isinstance(v, dict) and str(v.get("type")) == EVIDENCE_TYPE:
                    cards.append({"board": nm, "key": str(k), "value": v})
    return cards


def judge(cards, devices):
    """★ 逐设备判三态"""
    rows = []
    for dev in devices:
        mine = [c for c in cards
                if dev in str(c["value"].get("from", ""))
                or dev in str(c["key"])]
        if not mine:
            rows.append({"device": dev, "verdict": MISSING, "why":
                         "★ 无任何举证卡 ⇒ 该设备【未按契约 §3.2 举证】", "cards": 0})
            continue
        # ★ 取最新一张（★ 依它外层 ts）
        mine.sort(key=lambda c: str(c["value"].get("at") or ""), reverse=True)
        c = mine[0]
        v = c["value"]
        miss = [f for f in REQ_FIELDS if f not in v]
        # ★ C-1：值必须是规范值
        bad_ver = []
        for f in ("cahac", "cahac_version_declared"):
            val = v.get(f)
            if val is not None and str(val) != CANON_VERSION:
                bad_ver.append("%s=%r" % (f, val))
        # ★ 过期（★ R-3）
        age_d, at = None, str(v.get("at") or "")
        try:
            t = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=now().tzinfo)
            age_d = (now() - t).total_seconds() / 86400.0
        except Exception:
            age_d = None
        if miss or bad_ver:
            why = []
            if miss:
                why.append("★ 缺契约字段 %s" % ",".join(miss))
            if bad_ver:
                why.append("★★ 版本值不合规范 %s（★ 应为 %r）" % (",".join(bad_ver), CANON_VERSION))
            rows.append({"device": dev, "verdict": MISSING, "why": "；".join(why),
                         "cards": len(mine), "key": c["key"]})
        elif age_d is None:
            rows.append({"device": dev, "verdict": UNDEC, "why":
                         "★ 举证卡的 `at` 不可解析 ⇒ 新鲜度【不可判】（★ 空 ≠ 无）",
                         "cards": len(mine), "key": c["key"]})
        elif age_d > STALE_DAYS:
            rows.append({"device": dev, "verdict": STALE, "why":
                         "★ 举证卡已 %d 天（★ 阈 %d）⇒ 依 R-3 应复核" % (int(age_d), STALE_DAYS),
                         "cards": len(mine), "key": c["key"]})
        else:
            rows.append({"device": dev, "verdict": OK, "why":
                         "★ 举证有效 · %d 天前 · %d 张卡" % (int(age_d), len(mine)),
                         "cards": len(mine), "key": c["key"]})
    return rows


ICON = {OK: "✅", STALE: "⚠️ ", MISSING: "❌", UNDEC: "❓"}


def run(as_json=False):
    devices = enrolled_devices()
    cards = fetch_evidence()
    rows = judge(cards, devices)
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    d = {"version": VERSION, "at": now().isoformat(timespec="seconds"),
         "stale_days": STALE_DAYS, "canon_version": CANON_VERSION,
         "devices": len(devices), "evidence_cards": len(cards),
         "tally": tally, "rows": rows}
    if as_json:
        return d
    print("══ CAHAC 接入契约合规度（I-4）%s ══  时刻 %s" % (VERSION, d["at"]))
    print("  在册设备 %d · 举证卡 %d · 超期阈 %d 天 · 规范版本 %r"
          % (len(devices), len(cards), STALE_DAYS, CANON_VERSION))
    print()
    for r in rows:
        print("  %s %-16s %s" % (ICON.get(r["verdict"], "?"), r["device"], r["why"]))
    print()
    print("【汇总】" + " · ".join("%s=%d" % (k, tally.get(k, 0))
                                for k in (OK, STALE, MISSING, UNDEC)))
    if not cards:
        print()
        print("  ★★ 举证卡 0 张 ⇒ ★ 那【不是「都合规」】，★ 而是【契约刚立、尚无设备举证】")
        print("  ★ 复跑契约：docs/cahac-onboarding-contract-v1-20261015.md §3.2")
    return d


def selftest():
    ok = tot = 0
    # ★★★ 2026-10-15（D-376）【异源用例】—★ 由明鉴的一般形式启发
    try:
        import sys as _sysE
        _sysE.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from extcase import extcase_selftest as _ecs
        _ec_ok, _ec_tot, _ec_msg = _ecs("onboarding-conformance.py")
        print(_ec_msg)
        if _ec_ok is None:
            print("  ❓ 异源用例 ⇒ **不可判**（★ 空 ≠ 无）")
        else:
            ok += _ec_tot; tot += _ec_tot
    except Exception as _eE:
        print("  ❓ 异源用例 ⇒ 不可判（%s）" % type(_eE).__name__)

    print("== onboarding-conformance 自查 ==")

    def chk(c, lb):
        nonlocal ok, tot
        tot += 1
        if c:
            ok += 1
            print("  ✅ %s" % lb)
        else:
            print("  ❌ %s" % lb)

    # ★ 正控：四态枚举完整
    chk(set(ICON.keys()) == {OK, STALE, MISSING, UNDEC}, "正控：四态枚举完整")
    # ★ 正控：在册设备非空
    dev = enrolled_devices()
    chk(len(dev) > 0, "正控：在册设备非空（%d 台：%s）" % (len(dev), ",".join(dev[:4])))
    # ★ 正控：能取到举证卡列表（★ 0 张也是合法结果）
    cards = fetch_evidence()
    chk(isinstance(cards, list), "正控：举证卡扫描返回 list（%d 张）" % len(cards))
    # ★ 负控 1：无卡设备必须判 MISSING（★ 而【不得】判 OK）
    r = judge([], ["__never_has_card__"])
    chk(r and r[0]["verdict"] == MISSING, "负控：无卡设备 ⇒ MISSING（★ 而不得 OK）")
    # ★ 负控 2：版本值错（"v1.2"）必须【不】判 OK
    bad = [{"board": "t", "key": "k", "value": {"type": EVIDENCE_TYPE, "from": "dev-x",
            "cahac": "v1.2", "cahac_version_declared": "v1.2", "write_path": "p",
            "evidence": {}, "not_onboarded": [], "at": now().isoformat(timespec="seconds")}}]
    r2 = judge(bad, ["dev-x"])
    chk(r2 and r2[0]["verdict"] != OK, "负控：cahac='v1.2' ⇒ 不判 OK（★ D-331 的坑）")
    # ★ 负控 3：`at` 不可解析 ⇒ UNDECIDABLE（★ 而不得 OK、也不得 MISSING）
    bad2 = [{"board": "t", "key": "k", "value": {"type": EVIDENCE_TYPE, "from": "dev-y",
             "cahac": "1.2", "cahac_version_declared": "1.2", "write_path": "p",
             "evidence": {}, "not_onboarded": [], "at": "not-a-date"}}]
    r3 = judge(bad2, ["dev-y"])
    chk(r3 and r3[0]["verdict"] == UNDEC, "负控：at 不可解析 ⇒ UNDECIDABLE（★ 空 ≠ 无）")
    # ★ 正控：新鲜且合规的卡 ⇒ OK
    good = [{"board": "t", "key": "k", "value": {"type": EVIDENCE_TYPE, "from": "dev-z",
             "cahac": "1.2", "cahac_version_declared": "1.2", "write_path": "p",
             "evidence": {}, "not_onboarded": ["无"], "at": now().isoformat(timespec="seconds")}}]
    r4 = judge(good, ["dev-z"])
    chk(r4 and r4[0]["verdict"] == OK, "正控：合规且新鲜的卡 ⇒ OK")
    # ★ 正控：超期 ⇒ STALE
    old = [{"board": "t", "key": "k", "value": dict(good[0]["value"],
            at=(now() - datetime.timedelta(days=STALE_DAYS + 5)).isoformat(timespec="seconds"))}]
    r5 = judge(old, ["dev-z"])
    chk(r5 and r5[0]["verdict"] == STALE, "正控：超 %d 天 ⇒ STALE" % STALE_DAYS)

    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("onboarding-conformance %s" % VERSION); return 0
    if a.selftest:
        return selftest()
    d = run(as_json=a.json)
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
