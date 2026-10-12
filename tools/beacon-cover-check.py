#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ⚠️ DEPRECATED（2026-10-10T07:3x）—— 请勿使用。判据已归 tools/beacon-check.py 单点持有。
#
# 【为何弃用】分工文档 docs/division-of-labor-cu-vs-starbridge-20261010.md §A2 明写：
#   「只写一份判据：这三条实现在 beacon-check.py … gcr-gate.py 的 G-CR18 行调用它，不重写
#    —— 两处各写一份正是 B9 的病根（同源两端分头演进）。」
#   实测：beacon-check.py 现 22 条，已含 B10 三条（外部线 A2 已完成）⇒ 本文件 4 条全部重复。
#
# 【保留而非删除的理由】① 不删留痕；② ★ 本文件内有唯一不重复的一条：守恒性断言
#   （全文写前后 字符数/键数/★块数 骤降检测）—— beacon-check.py 没有这条。
#   ⇒ 是否收编由 beacon-check.py 属主（外部 CU 线）决定，本会话不自行推进。
#
# 【归属】本文件由 session-e317d6ab 自建，属越界产物（判据本应单点）。
#   见 docs/response-to-division-of-labor-20261010.md §二。
#
"""beacon-cover-check.py — G-CR18 信标自检覆盖门（P27 判据失明族的机械判据）

【为什么存在】
锚点 v5 §4.7 指出：`tools/beacon-check.py` 现有 17 条**不足以**发现四类失效，
其中前三类在 2026-10-10T07:0x 的实测中**同一次检查内并发存在**，而 beacon-check 报
「17 PASS / 0 WARN / exit 0」。本脚本把这四类变成**能红**的机械判据（G-CR18）。

【四判据】
  C1 两段一致   索引 `waves[]` 与 `items[]` 对同一波的状态不得互相矛盾
                ★ 未声明成员关系 ⇒ **WARN「不可判」**（★ 未知不并入任何一侧，见 §5.2）
  C2 时间戳      `updated_at` 须为 RFC 3339 规范形（`±HH:MM` 带冒号）且**不得晚于当前时刻**
  C3 verifier    `state == closed_with_evidence` 的项，`verifier` 字段不得缺失
  C4 双源       「本地副本」与「板值」须逐字段一致
                ★ 成因：`mk-resume-prompt.py` 读本地副本，而 `beacon-check --net` 校验板值
                  ⇒ **二者永不互校**（实测曾有 4 字段不一致）

【判别力纪律（本脚本自身的约束）】
  · **WARN 不等于 PASS** —— 输出里分别计数，且 `--strict` 下 WARN 亦致非 0。
  · 每条判据都**必须有负控**：`--selftest` 用合成 fixture 证明它**能红**。
    判据不跑负控就不知道它是不是恒真 —— 恒真的判据比没有判据更坏（它消耗信任）。
  · 板不可达 ⇒ C4 **SKIP**（不是 PASS）。★「未抽检 ≠ 通过」。

【用法】
  python3 tools/beacon-cover-check.py            # 打默认四判据
  python3 tools/beacon-cover-check.py --json     # 机读
  python3 tools/beacon-cover-check.py --strict   # WARN 亦致非 0
  python3 tools/beacon-cover-check.py --selftest # 负控矩阵（合成 fixture，不碰生产）

【exit】 0 = 全 PASS（含 SKIP/WARN 且未 --strict）· 1 = 有 FAIL（或 --strict 下有 WARN）· 2 = 用法/环境错
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data" / "registry" / "continuity-index.json"
BOARD_URL = "http://127.0.0.1:8792/data/registry/continuity-index"

# RFC 3339 规范形：偏移必须带冒号（`+08:00`），非 `+0800`
RFC3339 = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$")
# 非规范形（缺冒号的偏移）—— 单独识别，以便给出可行动的 reason
NON_RFC_OFFSET = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d{4}$")

# 状态序（用于 C1 的聚合比较）：数值越大越「靠后」
STATE_RANK = {
    "open": 0,
    "in_flight": 1,
    "closed_with_evidence": 2,
    "regressed": 1,
    "blocked": 0,
}


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def _parse_ts(s: str):
    """容错解析：接受 RFC3339 规范形；非规范形（+0800）也能读，但由 C2 判红。"""
    t = s.strip()
    m = NON_RFC_OFFSET.match(t)
    if m:
        t = t[:-2] + ":" + t[-2:]
    try:
        return dt.datetime.fromisoformat(t)
    except ValueError:
        return None


# ---------------------------------------------------------------- C1
def c1_two_segments(idx: dict) -> dict:
    """waves[] 与 items[] 状态一致性。

    ★ 判据要求 `waves[]` 显式声明成员（`items: [id, ...]`）才可判。
      未声明 ⇒ **WARN「不可判」**，**绝不判 PASS** —— 把「没查」当成「通过」正是 P27 本体。
    """
    items = {i.get("id"): i for i in idx.get("items") or [] if isinstance(i, dict)}
    waves = [w for w in (idx.get("waves") or []) if isinstance(w, dict)]
    if not waves:
        return {"id": "C1", "verdict": "WARN", "reason": "索引无 waves[] ⇒ 不可判（不等于通过）"}

    unresolved, conflicts, checked = [], [], 0
    for w in waves:
        wid = w.get("id")
        members = w.get("items")
        if not isinstance(members, list) or not members:
            unresolved.append(wid)
            continue
        missing = [m for m in members if m not in items]
        if missing:
            conflicts.append(f"wave {wid} 声明了不存在的成员 {missing}")
            continue
        ranks = [STATE_RANK.get(items[m].get("state"), -1) for m in members]
        if any(r < 0 for r in ranks):
            conflicts.append(f"wave {wid} 成员含未知 state")
            continue
        checked += 1
        wrank = STATE_RANK.get(w.get("state"), -1)
        if wrank < 0:
            conflicts.append(f"wave {wid} 自身 state 未知：{w.get('state')!r}")
            continue
        # 波的状态**不得领先于其最落后的成员**（波是成员的聚合，不能比成员更"完成"）
        if wrank > min(ranks):
            worst = min(members, key=lambda m: STATE_RANK.get(items[m].get("state"), 99))
            conflicts.append(
                f"wave {wid} 记 {w.get('state')!r}，但成员 {worst} 仍是 "
                f"{items[worst].get('state')!r} ⇒ 两段矛盾"
            )

    if conflicts:
        return {"id": "C1", "verdict": "FAIL", "reason": "；".join(conflicts),
                "detail": {"checked": checked, "unresolved": unresolved}}
    if unresolved:
        return {"id": "C1", "verdict": "WARN",
                "reason": f"{len(unresolved)} 个波未声明成员（{unresolved}）⇒ 不可判；"
                          f"已判 {checked} 个。★ 不可判 ≠ 通过",
                "detail": {"checked": checked, "unresolved": unresolved}}
    return {"id": "C1", "verdict": "PASS", "reason": f"{checked} 个波两段一致",
            "detail": {"checked": checked}}


# ---------------------------------------------------------------- C2
def c2_timestamp(idx: dict, now=None) -> dict:
    now = now or _now()
    raw = idx.get("updated_at")
    if not isinstance(raw, str) or not raw.strip():
        return {"id": "C2", "verdict": "FAIL", "reason": f"updated_at 缺失或非字符串：{raw!r}"}
    if NON_RFC_OFFSET.match(raw.strip()):
        return {"id": "C2", "verdict": "FAIL",
                "reason": f"updated_at 非 RFC 3339 规范形（偏移缺冒号）：{raw!r} ⇒ "
                          f"`datetime.fromisoformat` 在 Python<3.11 会抛 ValueError，"
                          f"会使本判据自身在解析处崩"}
    if not RFC3339.match(raw.strip()):
        return {"id": "C2", "verdict": "FAIL", "reason": f"updated_at 非法时间戳：{raw!r}"}
    t = _parse_ts(raw)
    if t is None:
        return {"id": "C2", "verdict": "FAIL", "reason": f"updated_at 无法解析：{raw!r}"}
    if t.tzinfo is None:
        return {"id": "C2", "verdict": "FAIL", "reason": f"updated_at 缺时区：{raw!r}"}
    if t > now:
        delta = t - now
        hrs = delta.total_seconds() / 3600.0
        return {"id": "C2", "verdict": "FAIL",
                "reason": f"updated_at 落在**未来**（超前 {hrs:.1f} 小时）："
                          f"{raw} > 现在 {now.isoformat(timespec='seconds')} ⇒ "
                          f"「更新于」不可信，且会显得比交付物更新",
                "detail": {"ahead_hours": round(hrs, 2)}}
    return {"id": "C2", "verdict": "PASS",
            "reason": f"{raw} 规范且未超前（现在 {now.isoformat(timespec='seconds')}）"}


# ---------------------------------------------------------------- C3
def c3_verifier(idx: dict) -> dict:
    items = [i for i in (idx.get("items") or []) if isinstance(i, dict)]
    if not items:
        return {"id": "C3", "verdict": "WARN", "reason": "索引无 items[] ⇒ 不可判（不等于通过）"}
    closed = [i for i in items if i.get("state") == "closed_with_evidence"]
    if not closed:
        return {"id": "C3", "verdict": "WARN",
                "reason": "无 closed_with_evidence 项 ⇒ 本条空转（★ 空转 ≠ 通过）"}
    missing = [i.get("id") for i in closed if not str(i.get("verifier") or "").strip()]
    if missing:
        return {"id": "C3", "verdict": "FAIL",
                "reason": f"{len(missing)}/{len(closed)} 个 closed_with_evidence 项无 verifier 字段："
                          f"{missing} ⇒ 与 §5.1「未证不得记 closed」冲突",
                "detail": {"closed": len(closed), "missing": missing}}
    return {"id": "C3", "verdict": "PASS",
            "reason": f"{len(closed)} 个 closed 项均有 verifier 字段",
            "detail": {"closed": len(closed)}}


# ---------------------------------------------------------------- C4
def _canon(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def c4_two_sources(local: dict, board=None, err: str | None = None) -> dict:
    if err is not None or board is None:
        return {"id": "C4", "verdict": "SKIP",
                "reason": f"板不可达（{err or '无值'}）⇒ 未抽检。★ 未抽检 ≠ 通过"}
    a, b = _canon(local), _canon(board)
    if a == b:
        return {"id": "C4", "verdict": "PASS", "reason": f"逐字段一致（sha {a[:16]}）"}
    lk, bk = set(local), set(board)
    diff = sorted(k for k in (lk & bk)
                  if json.dumps(local[k], sort_keys=True, ensure_ascii=False)
                  != json.dumps(board[k], sort_keys=True, ensure_ascii=False))
    detail = {"only_local": sorted(lk - bk), "only_board": sorted(bk - lk), "differing": diff}
    return {"id": "C4", "verdict": "FAIL",
            "reason": f"本地副本与板值不一致：{len(diff)} 字段不同 {diff[:6]}"
                      f" ⇒ mk-resume-prompt 读副本、beacon-check 校验板值，二者永不互校",
            "detail": detail}


# ---------------------------------------------------------------- selftest（负控矩阵）
def _fixture(**over):
    base = {
        "state_version": 4,
        "updated_at": "2026-10-10T07:00:00+08:00",
        "waves": [{"id": "C", "state": "in_flight", "items": ["C6"]},
                  {"id": "S", "state": "in_flight", "items": ["S5"]}],
        "items": [{"id": "C6", "state": "in_flight"},
                  {"id": "C3", "state": "closed_with_evidence", "verifier": "待第三方复核"},
                  {"id": "S5", "state": "in_flight"}],
    }
    base.update(over)
    return base


def selftest(now=None) -> int:
    now = now or _now()
    cases = []

    # C1 正例 / 负例
    cases.append(("C1 正例：波不领先成员", c1_two_segments(_fixture())["verdict"], "PASS"))
    bad1 = _fixture()
    bad1["waves"][0]["state"] = "closed_with_evidence"   # 波比成员更"完成"
    cases.append(("C1 负控：波领先成员 ⇒ 必红", c1_two_segments(bad1)["verdict"], "FAIL"))
    bad1b = _fixture(waves=[{"id": "C", "state": "in_flight"}])   # 未声明成员
    cases.append(("C1 负控：未声明成员 ⇒ 不可判(WARN) 非 PASS",
                  c1_two_segments(bad1b)["verdict"], "WARN"))
    bad1c = _fixture()
    bad1c["waves"][0]["items"] = ["NO_SUCH_ID"]
    cases.append(("C1 负控：成员不存在 ⇒ 必红", c1_two_segments(bad1c)["verdict"], "FAIL"))

    # C2 正例 / 负例
    cases.append(("C2 正例：规范且未超前", c2_timestamp(_fixture(), now)["verdict"], "PASS"))
    # ★★★ 2026-10-12 修（D-225，★ 本门自证自己抓到的）：
    #   ★ 旧版负控把时间戳【硬编码】为 `2026-10-11T00:20:00+08:00` —— ★ 写它【当时】确实是未来；
    #   ★★ 而 `now` 是【运行时取的】⇒ 到 2026-10-12 该时间已成【过去】⇒ 判 PASS（★ 而那是对的）
    #      ⇒ **负控随时间失效** ⇒ 本门自证报 `14/15`。
    #   ★★★ 修法：负控时间戳【相对于 now 生成】，不再硬编码。
    _ahead = (now + dt.timedelta(hours=3)).isoformat(timespec="seconds")
    cases.append(("C2 负控：未来时间戳（now+3h）⇒ 必红",
                  c2_timestamp(_fixture(updated_at=_ahead), now)["verdict"], "FAIL"))
    cases.append(("C2 负控：偏移缺冒号 ⇒ 必红",
                  c2_timestamp(_fixture(updated_at="2026-10-10T07:00:00+0800"), now)["verdict"], "FAIL"))
    cases.append(("C2 负控：缺时区 ⇒ 必红",
                  c2_timestamp(_fixture(updated_at="2026-10-10T07:00:00"), now)["verdict"], "FAIL"))
    cases.append(("C2 负控：缺字段 ⇒ 必红",
                  c2_timestamp({k: v for k, v in _fixture().items() if k != "updated_at"}, now)["verdict"], "FAIL"))
    # ★★ 新增正控：同一时间戳在【不同的 now】下判定必须相反（★ 证明这是真判据、不是恒真）
    #   ★ 即：t 在 now 之后 ⇒ FAIL；t 在 now 之前 ⇒ PASS
    _t = (now + dt.timedelta(hours=1)).isoformat(timespec="seconds")
    cases.append(("C2 正控：同一时间戳 · now 提前 ⇒ 必红",
                  c2_timestamp(_fixture(updated_at=_t), now)["verdict"], "FAIL"))
    cases.append(("C2 正控：同一时间戳 · now 推后 ⇒ 必绿",
                  c2_timestamp(_fixture(updated_at=_t), now + dt.timedelta(hours=2))["verdict"], "PASS"))

    # C3 正例 / 负例
    cases.append(("C3 正例：closed 均有 verifier", c3_verifier(_fixture())["verdict"], "PASS"))
    bad3 = _fixture()
    bad3["items"].append({"id": "C1", "state": "closed_with_evidence"})   # 无 verifier
    cases.append(("C3 负控：closed 缺 verifier ⇒ 必红", c3_verifier(bad3)["verdict"], "FAIL"))
    cases.append(("C3 负控：全无 closed ⇒ 空转(WARN) 非 PASS",
                  c3_verifier({"items": [{"id": "X", "state": "open"}]})["verdict"], "WARN"))

    # C4 正例 / 负例
    cases.append(("C4 正例：两源一致", c4_two_sources(_fixture(), _fixture())["verdict"], "PASS"))
    b = _fixture()
    b["updated_at"] = "2026-10-10T06:00:00+08:00"
    cases.append(("C4 负控：一字段不同 ⇒ 必红", c4_two_sources(_fixture(), b)["verdict"], "FAIL"))
    cases.append(("C4 负控：板不可达 ⇒ SKIP 非 PASS",
                  c4_two_sources(_fixture(), None, err="timeout")["verdict"], "SKIP"))

    fails = [c for c in cases if c[1] != c[2]]
    for name, got, want in cases:
        print(f"  {'✅' if got == want else '❌'} {name}  → {got}（期望 {want}）")
    print()
    print(f"负控矩阵：{len(cases) - len(fails)}/{len(cases)} 通过")
    return 1 if fails else 0


# ---------------------------------------------------------------- main
def _load_local():
    try:
        return json.loads(INDEX.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def _load_board():
    try:
        with urllib.request.urlopen(BOARD_URL, timeout=8) as r:
            env = json.loads(r.read().decode("utf-8"))
        return (env.get("value") if isinstance(env, dict) and "value" in env else env), None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="G-CR18 信标自检覆盖门")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="WARN 亦致非 0")
    ap.add_argument("--selftest", action="store_true", help="负控矩阵（合成 fixture，不碰生产）")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    idx, lerr = _load_local()
    if idx is None:
        print(f"✗ 本地索引不可读：{lerr}", file=sys.stderr)
        return 2
    board, berr = _load_board()

    results = [c1_two_segments(idx), c2_timestamp(idx), c3_verifier(idx),
               c4_two_sources(idx, board, berr)]

    tally = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1

    if a.json:
        print(json.dumps({"verdict": "fail" if tally["FAIL"] else "ok",
                          "tally": tally, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print("G-CR18 信标自检覆盖门（P27 判据失明族）")
        print(f"  ★ WARN 不等于 PASS；SKIP 不等于通过 —— 本门不把「没查」算成「绿」")
        print()
        for r in results:
            mark = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "SKIP": "SKIP"}[r["verdict"]]
            print(f"  {mark}  {r['id']}  {r['reason']}")
        print()
        print(f"计数：PASS {tally['PASS']} · WARN {tally['WARN']} · FAIL {tally['FAIL']} · SKIP {tally['SKIP']}")
        tail = "有 FAIL ⇒ 不通过"
        if not tally["FAIL"] and tally["WARN"]:
            tail = "无 FAIL，但有 WARN ⇒ ★ 不得读成全绿（--strict 下即为不通过）"
        elif not tally["FAIL"] and tally["SKIP"]:
            tail = "无 FAIL，但有 SKIP ⇒ ★ 未抽检 ≠ 通过"
        elif not tally["FAIL"]:
            tail = "全 PASS"
        print(f"⇒ {tail}")

    if tally["FAIL"]:
        return 1
    if a.strict and (tally["WARN"] or tally["SKIP"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
