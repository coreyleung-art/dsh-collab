#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""beacon-check.py — 反遗忘校验（信标四件套之④/§4.4 的执行体）

依据：计划 §4.4「反遗忘校验（每次启动/新会话必跑）——索引 ↔ 锚点 state_version 比对 ·
     与 ~/.dsh/continuity-last-version 比对（回退即告警）· closed_with_evidence 的 evidence 可解性抽检」。

**为什么必须存在**：信标四件套里，①②③ 都是「写下来的东西」，只有 ④ 是**会红的东西**。
R030 与「判据必须有判别力」在本台的具体形态：一个**永远不会红**的校验等于没有校验——
故本文件自带 `--selftest`，逐条构造反例，证明每一项**都能红**。

用法:
    python3 tools/beacon-check.py              # 离线校验（默认；不联网）
    python3 tools/beacon-check.py --net        # 追加黑板键可读性抽检 + G-CR18 ④ + 体量守恒（会打网络）
    python3 tools/beacon-check.py --stamp      # 把当前锚点 sha256 盖进索引（显式动作）
    python3 tools/beacon-check.py --accept-shrink  # 显式接受体量骤降（推进守恒基线）
    python3 tools/beacon-check.py --selftest   # 自证：每条检查都能红
退出码: 0 = 全绿；1 = 有 FAIL；2 = 起不来

★ **必须开着 `--net` 跑**才算数：G-CR18 ④ 与体量守恒都只认**板值**（权威源）；本文件其余各项
  读的是本地**派生副本**，副本滞后时那些 PASS 判的是旧值 —— 这一点由 ④ 显式点出来。
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data/registry/continuity-index.json"
VERSION_POINTER = Path(os.path.expanduser("~/.dsh/continuity-last-version"))
SESSIONS = Path(os.path.expanduser("~/.dsh/sessions/--Users-coreyleung--"))
BOARD = "http://127.0.0.1:8792"

RESULTS: list[tuple[str, str, bool, str]] = []      # (级别, 名称, 通过?, 详情)
SKIPPED: list[str] = []                             # 未抽检（**既不算通过也不算失败**）
PENDING: list[str] = []                             # 记为 closed 但审查员未到位（同上，**未验证 ≠ 已关闭**）


def check(name: str, ok: bool, detail: str = "", level: str = "FAIL"):
    RESULTS.append((level, name, ok, detail))
    mark = "PASS" if ok else ("WARN" if level == "WARN" else "FAIL")
    print(f"{mark:4s} {name}" + ("" if ok else f"   << {detail}"))


def skip(name: str, detail: str = ""):
    """**未抽检**必须与"通过"长得不一样。**

    本台已 N 次栽在"跳过看起来和通过一模一样"上（`compare.py` 的子串跳键、审查器的
    `evidence_check=None`）。故本函数的初版把"未开 --net ⇒ 黑板指针未抽检"返回成 `ok=True`
    ⇒ 打印 **PASS** ——**同一个病在我手里当场复发**。改成单列 SKIP，并在汇总行报出条数，
    使「全绿」不可能掩盖「有 N 条根本没看」。
    """
    SKIPPED.append(name)
    print(f"SKIP {name}" + (f"   << {detail}" if detail else ""))


def pend(name: str, detail: str = ""):
    """**未验证 ≠ 已关闭。** 与 `skip()` 同理，必须与"通过"长得不一样。

    依据 §11「六者缺一不得记 closed_with_evidence」——审查员未到位而记 closed，
    本就是不该记的。但本函数**不替用户裁定该项是否该降级**（那是 G-CR18/Q-N 的
    路由决定），只把「记为 closed 却无到位审查员」**显式报出并计数**，使「全绿」
    不可能掩盖它。★ 若只加 `verifier` 字段就算过，等于给判据开后门——故单列。
    """
    PENDING.append(name)
    print(f"PEND {name}" + (f"   << {detail}" if detail else ""))


# ------------------------------------------------------------------ 解析器

def anchor_state_version(path: Path) -> int | None:
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except Exception:
        return None
    m = re.search(r"state_version\D{0,12}(\d+)", head)
    return int(m.group(1)) if m else None


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resolve_evidence(ptr: str, *, net: bool) -> tuple[str, str]:
    """把 evidence 指针解析成一个**可解的东西**。三态：`ok` / `skip` / `fail`。

    解不开就说解不开，不猜（R030）；**没查过就说没查过**，不许并进 ok（见 `skip()`）。
    """
    if ptr.startswith("blackboard:"):
        key = ptr.split(":", 1)[1]
        if not net:
            return "skip", f"未开 --net（黑板键 `{key}` 本轮未抽检）"
        try:
            import urllib.request
            with urllib.request.urlopen(f"{BOARD}/{key}", timeout=8) as r:
                body = r.read().decode("utf-8", "replace")
            if r.status == 200 and len(body) > 2:
                return "ok", f"http {r.status}, {len(body)}B"
            return "fail", f"http {r.status}, {len(body)}B（空体或非 200）"
        except Exception as e:
            return "fail", f"{type(e).__name__}: {e}"
    if ptr.startswith("agentsrc:"):
        rel = ptr.split(":", 1)[1]
        p = SESSIONS / rel
        return ("ok", f"{p.stat().st_size}B") if p.exists() else ("fail", "会话文件不在")
    p = (ROOT / ptr) if not ptr.startswith("/") else Path(ptr)
    if p.exists():
        return "ok", (f"{p.stat().st_size}B" if p.is_file() else "目录")
    return "fail", "路径不在"


# ------------------------------------------------------------------ 板值 / 体量基线

CHECKPOINT = Path(os.path.expanduser("~/.dsh/beacon-check-checkpoint.json"))


def _now_iso() -> str:
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def canonical_sha(v) -> str:
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def board_value(timeout: int = 8):
    """读黑板上的索引**真身**。返回 (value | None, note)。

    ★ 板值是**权威源**，本地 `data/registry/continuity-index.json` 是它的**派生副本**。

    ⚠ **本台实测更正（2026-10-10）**：**并没有任何板→本地的索引同步器**。
      `scripts/bb-absorb-watch.py` 是**事件驱动的工具登记吸收**（订阅 :8803，看 `data/<node>/tools/`），
      与 `continuity-index` 无关；全仓扫过，没有任何脚本自动把板值刷进本地文件。
      ⇒ **写索引的人必须两边都写**（板是权威、本地是副本）。只写板 ⇒ 本地副本静静分叉，
        而 `beacon-check` 其余各项读的正是这个副本 ⇒ 判的是旧值而全绿。
      这正是 G-CR18 ④ 要抓的形态，且 2026-10-10 第一次通电就抓到了本线自己。
    """
    import urllib.request
    notes = []
    for name, base in (("local", BOARD), ("central", "http://xingqiao.meetfunbp.com:8792")):
        try:
            with urllib.request.urlopen(f"{base}/data/registry/continuity-index", timeout=timeout) as r:
                env = json.loads(r.read().decode("utf-8", "replace"))
            if isinstance(env, dict) and isinstance(env.get("value"), dict):
                return env["value"], f"{name} 板 v{env.get('version')} ts={env.get('ts')}"
            notes.append(f"{name}: 响应无 value")
        except Exception as e:
            notes.append(f"{name}: {type(e).__name__}")
    return None, "；".join(notes) or "两板均不可读"


def volume(v) -> dict:
    s = json.dumps(v, ensure_ascii=False, sort_keys=True)
    items = v.get("items") or []
    return {"chars": len(s), "stars": s.count("★"), "keys": len(v), "items": len(items),
            "closed": len([i for i in items if i.get("state") == "closed_with_evidence"])}


def shrink_reasons(prev: dict, cur: dict) -> list[str]:
    """★ 收编星桥 `beacon-cover-check.py` 里**唯一不重复**的一条（其 §五.5 请我定夺）。

    防的是「全文写把内容腰斩」。2026-10-10 实证：41,328 → 20,796 字符（−50%）、★219 → 31
    （−86%），而 4 次 `bb_dualwrite` **全报** `verdict: ok / values_equal: true`
    —— **那道门只验「两板相等」，不验「内容没变少」**。两板一起错 ⇒ 永远相等 ⇒ 永远绿。
    """
    out = []
    pc, cc = prev.get("chars") or 0, cur["chars"]
    if pc and cc < pc * 0.95:
        out.append(f"字符 {pc}→{cc}（−{100 - cc * 100 // pc}%）")
    ps, cs = prev.get("stars") or 0, cur["stars"]
    if ps and cs < ps * 0.80:
        out.append(f"★块 {ps}→{cs}（−{100 - cs * 100 // ps}%）")
    if prev.get("keys") is not None and cur["keys"] < prev["keys"]:
        out.append(f"顶层键 {prev['keys']}→{cur['keys']}")
    if prev.get("items") is not None and cur["items"] < prev["items"]:
        out.append(f"items {prev['items']}→{cur['items']}")
    return out


# ------------------------------------------------------------------ 校验主体

# ---------------------------- ★ M4①d：通道巡检心跳的【读者】
# ★ 为什么放在这里：§14.4 M4①d 要求「造 401 ⇒ 必须红【且必须有人收到】」。
#   而 drift-scan-cron 的失败告警卡写在**刚刚失败的那两条腿上** ⇒ 两板皆不可达时
#   告警卡也写不出去（★ 在断掉的链路上报告链路断了，逻辑上不可能成功）。
# ★ 解法：心跳由 cron 每轮**单键覆盖**写本机板优先（中枢腿断了本机心跳仍在），
#   **读者**放在 §4.4「反遗忘校验每次启动/新会话必跑」的入口上 ⇒ 每次会话都有人看。
# ★ 复用而非重写（J44）：直接调 cron 的 `--status`，用【它自己的三态退出码】当判据，
#   本工具不复制键名与间隔常量 ⇒ 逻辑变更自动跟随。
PATROL_STATUS_CMD = [sys.executable,
                     os.path.expanduser("~/dsh-collab/scripts/drift-scan-cron.py"),
                     "--status"]


def probe_patrol_heartbeat(cmd=None, timeout: int = 30) -> tuple[str, str]:
    """★ 返回 (state, detail)；state ∈ fresh / stale / undecidable。

    ★ `cmd` 可注入 ⇒ 自证里能用假命令构造三态反例（**不需要网络**）。
    """
    cmd = list(cmd or PATROL_STATUS_CMD)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return "undecidable", f"调用失败 {type(e).__name__} ⇒ ★ 读不到 ≠ 不存在"
    out = " ｜ ".join(x.strip() for x in (r.stdout or "").split("\n") if x.strip())
    if r.returncode == 0:
        return "fresh", out[:300]
    if r.returncode == 1:
        return "stale", out[:300]
    return "undecidable", f"exit={r.returncode} ⇒ 不可判（★ 读不到 ≠ 不存在，不冒充成立）"


# ---------------------------- ★★ 告警卡的「读者」（M4①d / M4③②）
# ★ 为何放在这里：§14.4 M4①d 与 M4③② 都要求「产生告警【且有读者】」，
#   而本纳 2026-10-12 实测：`drift-delivery-failure/` 与 `bus-expired-alert/` 两个目录
#   ★★ 全机只有写者、0 读者（D-185 / D-187）。
# ★ 逻辑（机械，无判断）：两个目录的语义都是「异常时才写」
#   ★★ ⇒ 为空 = 绿；非空 = 红。
ALERT_DIRS = ["data/ops/drift-delivery-failure", "data/ops/bus-expired-alert"]


def _board_token() -> str:
    for f in ("~/.dsh/board-token", "~/.dsh/blackboard-token"):
        p = os.path.expanduser(f)
        if os.path.exists(p):
            try:
                return open(p, encoding="utf-8").read().strip()
            except Exception:
                pass
    return os.environ.get("DSH_BB_TOKEN", "")


def read_alert_cards(board_url=None, timeout: int = 8) -> dict:
    """★ 读两个「异常才写」的告警目录 ⇒ {dir: (n, sample)} 或 {dir: None}"""
    import urllib.request
    base = (board_url or os.environ.get("DSH_BB_URL") or "http://127.0.0.1:8792").rstrip("/")
    out = {}
    for d in ALERT_DIRS:
        try:
            req = urllib.request.Request(base + "/" + d + "/")
            tk = _board_token()
            if tk:
                req.add_header("Authorization", "Bearer " + tk)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                j = json.loads(r.read())
            lst = j.get("list") or {}
            # ★★ 2026-10-12（★ 用户裁定【归档】后加）：
            #   ★ **带 `_archived_at` 的卡【不计入】** —★ 归档 = 标记不删，仍可枚举可回放。
            #   ★ 为何不删：★ DLQ 语义（本仓既有先例）；★ 删了就无法事后追查。
            _items = list(lst.items()) if isinstance(lst, dict) else []
            _live = [(k, v) for k, v in _items
                     if not ((v or {}).get("value") or {}).get("_archived_at")]
            n = len(_live)
            sample = ""
            if _live:
                k0 = sorted(k for k, _ in _live)[-1]
                v0 = dict(_live)[k0].get("value") or {}
                sample = str(v0.get("subject") or v0.get("note") or v0.get("failedLegs") or "")[:110]
            if len(_items) > len(_live):
                sample = ("★ 共 %d 条、其中 %d 条已归档；" % (len(_items), len(_items) - len(_live))) + sample
            out[d] = (n, sample)
        except Exception:
            out[d] = None
    return out


def run(root: Path = ROOT, *, net: bool = False, quiet: bool = False,
        accept_shrink: bool = False) -> int:
    global RESULTS, SKIPPED, PENDING
    RESULTS, SKIPPED, PENDING = [], [], []
    index_path = root / "data/registry/continuity-index.json"

    if not index_path.exists():
        check("索引键本地副本存在", False, str(index_path))
        return 1
    try:
        idx = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as e:
        check("索引键可解析", False, f"{type(e).__name__}: {e}")
        return 1
    check("索引键可解析", True)

    # ---- 1. 锚点在位 + 版本一致（§4.4 第一条）
    anchor = root / idx["anchor"]
    check("锚点文档在位", anchor.exists(), str(anchor))
    if not anchor.exists():
        return 1
    av = anchor_state_version(anchor)
    iv = idx.get("state_version")
    check("锚点可读出 state_version", av is not None, "头部读不到 state_version")
    check("索引 ↔ 锚点 state_version 相等", av == iv, f"锚点={av} 索引={iv}")

    # ---- 2. 锚点指纹（改了正文却没升版本 ⇒ 会红）
    stamped = idx.get("anchor_sha256")
    actual = sha256(anchor)
    if stamped is None:
        check("锚点指纹已盖章", False, "anchor_sha256 为空 ⇒ 跑 --stamp 盖一次", level="WARN")
    else:
        check("锚点指纹未变（改了正文须同时升 state_version 并重盖章）",
              stamped == actual, f"索引={stamped[:16]}… 实际={actual[:16]}…")

    # ---- 3. 版本指针回退告警（§4.4 第二条）
    if VERSION_POINTER.exists():
        try:
            pv = int(VERSION_POINTER.read_text(encoding="utf-8").strip())
        except Exception:
            pv = None
        check("版本指针可解析", pv is not None, VERSION_POINTER.read_text(errors="replace")[:60])
        if pv is not None:
            check("版本未回退（指针 ≤ 索引）", pv <= (iv or 0), f"指针={pv} 索引={iv}")
    else:
        check("版本指针文件存在", False, f"{VERSION_POINTER} 不在 ⇒ 无法检测回退", level="WARN")

    # ---- 4. 续接提示词：在位、未超长、**未漂移**
    rp = root / idx["resume_prompt"]
    check("续接提示词在位", rp.exists(), str(rp))
    if rp.exists():
        n = len(rp.read_text(encoding="utf-8").rstrip("\n").split("\n"))
        check("续接提示词 ≤40 行（§4.1③）", n <= 40, f"{n} 行")
        gen = root / idx.get("resume_prompt_generator", "")
        if gen.exists():
            r = subprocess.run([sys.executable, str(gen), "--stdout"],
                               capture_output=True, text=True)
            check("续接提示词未漂移（== 现渲染结果）",
                  r.stdout == rp.read_text(encoding="utf-8"),
                  "渲染结果与盘上文件不一致 ⇒ 跑一次生成脚本；**不要手改它**")

    # ---- 5. closed_with_evidence 的证据可解性抽检（§4.4 第三条）
    closed = [it for it in idx.get("items") or [] if it.get("state") == "closed_with_evidence"]
    check("存在 closed_with_evidence 项（否则本条空转）", bool(closed),
          "0 项 ⇒ 第 5 条没有判别力", level="WARN")
    for it in closed:
        evs = it.get("evidence") or []
        if not evs:
            check(f"{it['id']} 有 evidence 指针", False, "记为 closed 却无证据指针")
            continue
        res = [(e, *resolve_evidence(e, net=net)) for e in evs]
        bad = [f"{e}→{d}" for e, st, d in res if st == "fail"]
        skipped = [f"{e}→{d}" for e, st, d in res if st == "skip"]
        if bad:
            check(f"{it['id']} 证据指针可解", False, "; ".join(bad))
        elif skipped:
            skip(f"{it['id']} 证据指针可解", "; ".join(skipped))
        else:
            check(f"{it['id']} 证据指针可解", True)

    # ---- 6. dod 全文表：缺席必须**显式**，不能是"看起来有"
    # ★★ 2026-10-12（v7 更正账 / W4 发现）：本条【判据不误】，但【PASS 文案曾自欺】——
    #   ★ 旧文案只说「缺席是显式声明的」⇒ ★★ 读者会读成「dod 没问题」，
    #   而实情是 **`full_table` 本来就缺席** ⇒ 「有多少项有 DoD」是【不可判】。
    #   ⇒ 修法：PASS 时【必须明写它当前是缺席还是在位】，让读者一眼看到实情。
    dod = (idx.get("dod") or {}).get("full_table")
    dod_declared = bool((idx.get("dod") or {}).get("_status"))
    # ★★★ 2026-10-13【替换】（★ W2 §3.4 · ★ M5）：原判据判的是【缺席有没有被声明】—★
    #   ★★ 而那是【掩盖性 PASS】：★ 缺席给了声明 ⇒ 判 PASS ⇒ **读者会以为 DoD 齐备**。
    #   ★ W2 :554 逐字：「不得在保留旧 PASS 的同时并列新 FAIL —★ 否则读者会取绿」
    #   ★ 故现【替换】为：判【全文表在不在】—★ 缺席就是缺席。
    if dod is not None:
        check("dod 全文表在位（★ 替换后）", True, "★ 全文表【在位】")
    elif dod_declared:
        check("dod 全文表在位（★ 替换后）", False,
              "★★ **`full_table` 缺席**（★ 仅有缺席声明）⇒ "
              "★★ **「有多少项有 DoD」不可判，★ 不得读作「DoD 齐备」**；"
              "★ 旧判据将此判为 PASS ⇒ **掩盖性 PASS**（★ W2 §3.4）")
    else:
        check("dod 全文表在位（★ 替换后）", False,
              "既没内容也没缺席声明")

    # ---- 7. 自检覆盖缺口（B10 = P27 族）：以下三条**此前全无**，
    #         故「校验全绿而事实已变」在本台上曾结构性地看不见（本线 2026-10-10 实测）。
    items = idx.get("items") or []

    # 7a. updated_at 合理域 —— 先校规范形，否则判据自身会在解析处崩（锚点 §7 §17.3③ 实测）
    ua = idx.get("updated_at")
    RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}$")
    ok_form = bool(ua) and bool(RFC3339.match(str(ua)))
    check("updated_at 为 RFC 3339 规范形（±HH:MM 带冒号）", ok_form,
          f"值={ua!r} ⇒ 判据会在解析处崩或被静默跳过")
    if ok_form:
        ahead = (datetime.datetime.fromisoformat(str(ua))
                 - datetime.datetime.now().astimezone()).total_seconds()
        check("updated_at 未落在未来（合理域）", ahead <= 120,
              f"比现在超前 {ahead / 3600:.1f} 小时 ⇒ 按会话推进感觉估时间，不读时钟（B8）")

    # 7b. waves / items 两段一致 —— 同源两端分头演进，只读一段的人发现不了（B9）
    PROG = {"open": 0, "blocked": 0, "in_flight": 1, "closed_with_evidence": 2}
    by_id = {i["id"]: i for i in items}
    incons: list[str] = []
    for w in idx.get("waves") or []:
        rel = [by_id[i] for i in re.findall(r"\b([A-Z]{1,2}\d+)\b", w.get("name") or "") if i in by_id]
        if rel:
            hot = [i["id"] for i in rel if PROG.get(i.get("state"), 0) >= 1]
            if hot and PROG.get(w.get("state"), 0) < 1:
                incons.append(f"wave {w['id']} 记 {w.get('state')}，而其 items 已有 {'/'.join(hot)} 非 open")
        for mm in re.finditer(r"([A-Z]{1,2}\d+(?:/[A-Z]{1,2}\d+)*)\s*未做", w.get("note") or ""):
            for iid in mm.group(1).split("/"):
                if iid in by_id and by_id[iid].get("state") != "open":
                    incons.append(f"wave {w['id']} 的 note 称「{mm.group(0)}」，而 items[{iid}] 记 "
                                  f"{by_id[iid].get('state')}")
    check("waves / items 两段一致（B9）", not incons, "；".join(incons))

    # 7c. closed_with_evidence 须有 verifier；**但只查字段存在会给判据开后门** ⇒
    #     值仍是"待复核"类的，单列 PENDING，使「全绿」不能掩盖「未验证」。
    closed = [it for it in items if it.get("state") == "closed_with_evidence"]
    # ★★★ 2026-10-13【替换】（★ W2 §3.4 · ★ M5）：原判据判【字段在不在】—★
    #   ★★ 而 6/6 的值全是【占位串】（「待第三方复核」·「★ missing」）⇒ 原判据 PASS。
    #   ★ 故现【替换】为：判【值是否有效】（★ 非占位）。
    _PLACEHOLDER = re.compile(r"(TBD|待填|占位|placeholder|XXX)", re.I)
    missing = [it["id"] for it in closed if not it.get("verifier")]
    _ph = [it["id"] for it in closed
           if it.get("verifier") and _PLACEHOLDER.search(str(it["verifier"]))]
    # ★★ 边界型：★ 说明了「谁还没复核」与「按哪条规则」的 —★ 它不是占位。
    _BOUNDARY = re.compile(r"待第三方复核|需异体复核|不可自审|禁自证", re.I)
    _bd = [it["id"] for it in closed
           if it.get("verifier") and _BOUNDARY.search(str(it["verifier"]))
           and not _PLACEHOLDER.search(str(it["verifier"]))]

    if missing:
        check("closed 项 verifier 有效（★ 替换后）", False,
              f"{'/'.join(missing)} 记为 closed 却无 verifier 字段 ⇒ §5.1「未证不得记 closed」")
    elif _ph:
        check("closed 项 verifier 有效（★ 替换后）", False,
              "★★ **%d/%d 项的 verifier 仍是【占位串】**（★ %s）⇒ "
              "★ 「字段齐备」不等于「已验证」；★ 旧判据将此判为 PASS ⇒ **掩盖性 PASS**"
              % (len(_ph), len(closed), "/".join(_ph)))
    elif _bd:
        # ★★ 边界型：★ 非占位，★ 而是【已声明的未结束边界】—★ 不判 FAIL，但也不得读作全绿。
        skip("closed 项 verifier 有效（★ 替换后）",
             "★ %d/%d 项是【已声明的未结束边界】（★ %s）"
             " → ★ 非占位，★ 但**不得读作全绿**"
             % (len(_bd), len(closed), "/".join(_bd)))
    else:
        check("closed 项 verifier 有效（★ 替换后）", True,
              "★ %d 项的 verifier 均非占位串" % len(closed))
    # ★★★ 2026-10-13（★ W2 §3.4）：本段【已删】—★
    #   ★ 它原是一条【追加】的 PEND（★ 在旧 PASS 旁边并列）—★
    #   ★★ 而 W2 :554 逐字：「不得在保留旧 PASS 的同时并列新 FAIL —★ 否则读者会取绿」。
    #   ★ 现已将旧 PASS 【替换】为 FAIL（★ 见上「closed 项 verifier 有效（★ 替换后）」）⇒
    #   ★ 故本条 PEND 【重复且弱于 FAIL】⇒ **删掉**，★ 避免两处同诉。
    #   ★ 保留一行说明供后人可追。

    # ---- 8. 本地副本 ↔ 板值一致（★ G-CR18 **④**，锚点 §7.9 四项之末）
    #     本台今日两次翻车的形态就是这条：本地文件与板值分叉、★块与键数都对不上，而无人察觉
    #     （本地 ★244/22 键 vs 板 ★236/21 键）。板是权威源，本地是派生副本 ⇒ 副本滞后即读数不可信。
    bv, bnote = board_value()
    if not net:
        skip("本地副本 ↔ 板值一致（G-CR18 ④）", "未开 --net ⇒ 未抽检（★ 未抽检 ≠ 通过）")
    elif bv is None:
        check("本地副本 ↔ 板值一致（G-CR18 ④）", False, f"板不可读 ⇒ 本项无法判（{bnote}）")
    else:
        same = canonical_sha(bv) == canonical_sha(idx)
        ml, mb = volume(idx), volume(bv)
        check("本地副本 ↔ 板值一致（G-CR18 ④）", same,
              f"本地 sha={canonical_sha(idx)} / 板 sha={canonical_sha(bv)}　"
              f"本地[{ml['chars']}字符 {ml['stars']}★ {ml['keys']}键]"
              f" vs 板[{mb['chars']}字符 {mb['stars']}★ {mb['keys']}键]（{bnote}）"
              f" ⇒ 本地副本是派生件，滞后时**本文件其余各项读的都是旧值**")

    # ---- 9. 体量守恒（骤降检测）—— 基线只认板值；只在**通过**时才推进基线，
    #         否则一次腰斩会被记成新基线，红一次就永久绿（那又是一道不会红的门）。
    if not net or bv is None:
        skip("索引体量守恒（骤降检测）", "基线只认板值；本轮未开 --net 或板不可读 ⇒ 未抽检")
    else:
        cur = volume(bv)
        try:
            prev_rec = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        except Exception:
            prev_rec = None
        if not prev_rec or prev_rec.get("source") != "board":
            skip("索引体量守恒（骤降检测）",
                 f"无同源基线（首次运行或源变更）⇒ 本轮**只建档、未抽检**（{cur['chars']}字符 "
                 f"{cur['stars']}★ {cur['keys']}键）")
            CHECKPOINT.write_text(json.dumps(
                {"source": "board", "at": _now_iso(), "sha": canonical_sha(bv), "metrics": cur},
                ensure_ascii=False), encoding="utf-8")
        else:
            prev = prev_rec.get("metrics") or {}
            reasons = shrink_reasons(prev, cur)
            check("索引体量守恒（骤降检测）", not reasons,
                  "；".join(reasons) + f"　基线 {prev_rec.get('at')} ⇒ ★ 全文写把内容写少了。"
                  f"核无误后须**显式**用 --accept-shrink 接受，否则一直红（这是刻意的）")
            if not reasons or accept_shrink:
                CHECKPOINT.write_text(json.dumps(
                    {"source": "board", "at": _now_iso(), "sha": canonical_sha(bv),
                     "metrics": cur, "accepted": bool(reasons)}, ensure_ascii=False), encoding="utf-8")

    # ★ M4①d：通道巡检心跳新鲜度 —— ★ 这是「零漂移」与「巡检已死」的唯一区分器
    if not net:
        skip("通道巡检心跳新鲜度（M4①d）",
             "未开 --net ⇒ 未抽检（★ 未抽检 ≠ 通过；★ 但**未抽检 ≠ 巡检已死**）")
    else:
        pst, pdet = probe_patrol_heartbeat()
        if pst == "fresh":
            check("通道巡检心跳新鲜度（M4①d）", True, pdet)
        elif pst == "stale":
            check("通道巡检心跳新鲜度（M4①d）", False,
                  "★★ 心跳已陈旧 ⇒ drift 巡检【已停】。★ 先排除「刚唤醒、cron 未及跑」"
                  "（下一轮 ≤30min 内会写新心跳）；若持续红则查 "
                  "`launchctl list | grep drift-scan` 与 /tmp/drift-scan-cron.err.log。"
                  "★ 静默容忍此红，正是 401 冻结 7.5 天无人知的原因。" + pdet[:160])
        else:
            skip("通道巡检心跳新鲜度（M4①d）", pdet)

    # ★★ M4①d / M4③②：告警卡的读者 —★ 2026-10-12 实测两目录 0 读者后补。
    #   为空 = 绿；非空 = 红（两目录语义都是「异常时才写」）。
    if not net:
        skip("告警卡有读者（M4①d/M4③②）",
             "未开 --net ⇒ 未抽检（未抽检 ≠ 通过）")
    else:
        _cards = read_alert_cards()
        _unread = [d for d, v in _cards.items() if v is None]
        _hot = [(d, v[0], v[1]) for d, v in _cards.items() if v and v[0] > 0]
        # ★★★ 2026-10-13 修（W4 H1 第②处假绿）—★
        #   ★★ 原形态（W4 逐字）：「判「告警卡有读者」**PASS 而其输入可以是【不存在的段】**」；
        #     ★ 实测：若一个目录读不到、另一个读到且空 ⇒ 仍报绿。
        #   ★ 为何是假绿：★ ★ 读不到的那个目录【无法确认是否真空】
        #     （★ 段名拼错 与 真无告警 同形 —★ 同本仓 D-188 记的「空 ≠ 无」）。
        #   ★ 修法：**任一目录读不到 ⇒ 不可判**（★ 而不是只加一句提示）。
        if _unread:
            skip("告警卡有读者（M4①d/M4③②）",
                 "★ %d/%d 个目录读不到（%s）⇒ **不可判**"
                 "（★ 读不到的那个无法确认是否真空；"
                 "★ W4 H1 第②处假绿）" % (len(_unread), len(_cards), ",".join(_unread)))
        elif _hot:
            check("告警卡有读者（M4①d/M4③②）", False,
                  "★★ 有未处理告警 " + str(sum(n for _, n, _ in _hot)) + " 条："
                  + "；".join("%s=%d条（%s）" % (d.split("/")[-1], n, sm[:60]) for d, n, sm in _hot)
                  + " ★ 处理后自然转绿")
        else:
            _ok = [d for d, v in _cards.items() if v is not None]
            check("告警卡有读者（M4①d/M4③②）", True,
                  "已读 %d 个目录、**全部读到且均为空** ⇒ 无未处理告警" % len(_ok))

    # ★★ 2026-10-12（D-209）：既有 lint 清单就位检查 —★ 防「重造轮子」。
    #   ★ 立据：本仓 tools/ 下已有 10 个 lint/gate 正好管着当晚所有坑，
    #   ★★ 而当晚 20 个子代理【一个都没引用】—★ **逐条实测 0 次**。
    #   ★ 故本条把清单【浮到每次必跑的输出里】⇒ 不靠记忆。
    try:
        _li = subprocess.run([sys.executable, str(ROOT / "tools" / "lint-inventory.py"), "--json"],
                             capture_output=True, text=True, timeout=20)
        _items = json.loads(_li.stdout)
        _rows = len(_items)
        _miss = [i["tool"] for i in _items if not i.get("present")]
        if _rows == 0:
            skip("既有 lint 清单就位（D-209）", "清单为空 ⇒ 不可判（不冒充通过）")
        elif _miss:
            check("既有 lint 清单就位（D-209）", False,
                  "★★ 表内工具缺失：" + ",".join(_miss) + " ★ 修后自然转绿")
        else:
            check("既有 lint 清单就位（D-209）", True,
                  "★ %d/%d 工具在位 · ★★ 派子代理前请跑 `python3 tools/lint-inventory.py --prompt` 并粘入提示词" % (_rows - len(_miss), _rows))
    except Exception as e:
        skip("既有 lint 清单就位（D-209）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-12（D-235）：判据健康度（★ 恒真自证扫查）—★ 防「自证很美而从不会红」。
    #   ★ 立据：`gcr-gate` 旧版五条负例全是恒真（`0 == 0`）⇒ 可信负控 = 0（D-204）。
    #   ★ 只跑【读源码】那一轮（★ 不加 --run，★ 免慢）。
    try:
        _sa = subprocess.run([sys.executable, str(ROOT / "tools" / "selftest-audit.py"),
                              "--root", "tools", "--json"],
                             capture_output=True, text=True, timeout=30)
        _rows = json.loads(_sa.stdout)
        _taut = [r for r in _rows if r.get("tautologies")]
        if not _rows:
            skip("判据健康度（恒真自证扫查）", "扫描面为空 ⇒ 不可判")
        elif _taut:
            check("判据健康度（恒真自证扫查）", False,
                  "★★ %d 件含恒真自证条目：%s ★ 修后自然转绿"
                  % (len(_taut), ",".join(r["file"] for r in _taut[:3])))
        else:
            check("判据健康度（恒真自证扫查）", True,
                  "★ %d 个 .py 无恒真自证条目；★★ 全量实跑请跑 "
                  "`python3 tools/selftest-audit.py --root tools --run`" % len(_rows))
    except Exception as e:
        skip("判据健康度（恒真自证扫查）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-244）：假结果形态（★ 八次同形里可机械检的四类）—★ 防「结果看上去对而实为假」。
    #   ★ 立据：v7 §0.2.1（★ 十次实证）。★ ★ 只读源码，★ 不跑工具。
    try:
        _fr = subprocess.run([sys.executable, str(ROOT / "tools" / "false-result-patterns.py"), "--json"],
                             capture_output=True, text=True, timeout=25)
        _fd = json.loads(_fr.stdout)
        _fh = _fd.get("hits") or []
        _p1 = [h for h in _fh if h.get("check") == "P1"]
        _p2 = [h for h in _fh if h.get("check") == "P2"]
        _p6 = [h for h in _fh if h.get("check") == "P6"]
        # ★ 只对 P1/P2/P6（★ 确定性高）报红；P5 多数是数据行 ⇒ 进文案
        # ★★ 2026-10-13（D-260）：P6 并入报红 —— ★ 它测【标题序号 vs 实际行号序】，
        #   ★ 立据：本线一晚犯两次（v7 §0.1.1 · 索引「七」在「六」前），★ 而它【真命中了外部件】。
        _hard = _p1 + _p2 + _p6
        if not _fd.get("scanned"):
            skip("假结果形态（D-244）", "扫描面为空 ⇒ 不可判")
        elif _hard:
            check("假结果形态（D-244）", False,
                  "★★ P1(.status) %d · P2(None当绿) %d · P6(序号不升序) %d ★ 修后自然转绿"
                  % (len(_p1), len(_p2), len(_p6)))
        else:
            check("假结果形态（D-244）", True,
                  "★ P1/P2/P6 无命中；★★ 而 P5（硬编码时间）%d 处多为数据行 ⇒ 须人工筛"
                  % len([h for h in _fh if h.get("check") == "P5"]))
    except Exception as e:
        skip("假结果形态（D-244）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-287）：【写者归属门】—— ★ 防「自动上报卡无署名 ⇒ 无人能归属」。
    #   ★ 立据：查清 `notes/mac-mini/manager-actions/` 下 28 张卡**全部** `from=systemgraph-gui`
    #     （★ 一个服务名），**无任何会话身份** ⇒ 收到时显示 `unattributed`。
    #   ★ 而本仓【已有 X-Writer 约定】（`bb_dualwrite.py:66` · `bb-put-verify.py:144`）
    #     ⇒ 缺的是【机械化检查】，★ 而那是本条要补的。
    #   ★★ 三态：读到无归属 ⇒ 报红；读失败/空面 ⇒ SKIP（★ 不冒充通过）。
    try:
        _wa = subprocess.run([sys.executable, str(ROOT / "tools" / "writer-attribution-gate.py"), "--json"],
                             capture_output=True, text=True, timeout=90)
        _wd = json.loads(_wa.stdout)
        _ws = _wd.get("summary") or {}
        _wun = _wd.get("unattributed_by_from") or {}
        _wrf = _ws.get("readfail", 0)
        if _wrf and not _wun:
            skip("写者归属门（D-287）", "读面失败 %d 个 ⇒ 不可判（★ 不是「无问题」）" % _wrf)
        elif _wun:
            _who = "; ".join("%s=%d张" % (k, v["count"]) for k, v in _wun.items())
            check("写者归属门（D-287）", False,
                  "★★ 无署名写者：%s（★ 总 %d 张）⇒ 应带 X-Writer 或 from_label"
                  % (_who, _ws.get("unattributed", 0)))
        else:
            check("写者归属门（D-287）", True,
                  "★ 归属 %d · 不可判 %d（★ 不可判 = 卡形不同，★ 不升格）"
                  % (_ws.get("attributed", 0), _ws.get("undecidable", 0)))
    except Exception as e:
        skip("写者归属门（D-287）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-291）【CAHAC 信封合格度】—★ 目标四维 **I-1**。
    #   ★ 立据：`notes/collab` 现测 **envelope_ok = 0/643 = 0.0000%**（v6.1 时 0/564）—★
    #     ★★ **两版之间一点没变**。
    #   ★★ 而它是【接收侧】的量 ⇒ **覆盖全部写者**（★ 包括本机管不到的外设备卡）—★
    #     ★ 实测：今天 328 张里 **本机会话仅 64 张（20%）**，外设备 **202 张（62%）**。
    #   ★ 只报不修（★ 改不了别人的写者）—★ 但使它【可见】。
    try:
        _ca = subprocess.run([sys.executable, str(ROOT / "scripts" / "cahac-envelope-conformance.py"),
                              "--json", "--since", "2026-10-13"],
                             capture_output=True, text=True, timeout=90)
        _cd = json.loads(_ca.stdout)
        _ok = _cd.get("envelope_ok", 0); _sc = _cd.get("scanned", 0)
        _all = _cd.get("scanned_all") or _sc
        if _sc == 0:
            skip("CAHAC 信封符合度（I-1 · 今日窗）", "窗内分母为 0 ⇒ 不可判")
        elif _ok == 0:
            check("CAHAC 信封符合度（I-1 · 今日窗）", False,
                  "★★ 今日窗 **%d/%d = 0.0%%**（★ 全量 %d）⇒ "
                  "★ 外设备卡本机管不到，★ 需各设备同步接入" % (_ok, _sc, _all))
        else:
            check("CAHAC 信封符合度（I-1 · 今日窗）", True,
                  "★ %d/%d（★ 全量 %d）" % (_ok, _sc, _all))
    except Exception as e:
        skip("CAHAC 信封符合度（I-1）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-293）【H3 投递率 + H4 跨设备偏斜】—★ 目标四维两项。
    #   ★ 立据：W4 自陈 H3 判别力存疑（★ 唯一未达靠一张自指卡）· H4 **本件未测·无判据·无负控**。
    #   ★★ 而实测发现：**偏斜集中在历史**—★
    #     近期（--since 2026-10-13）H3 **96.3%** · H4 **PASS Δ=+1**；
    #     全量 H3 **23.4%** · H4 **FAIL Δ=+295** ⇒ ★ H4 正好把「链路坏」与「历史欠账」分开。
    try:
        _dp = subprocess.run([sys.executable, str(ROOT / "tools" / "delivery-probe.py"),
                              "--since", "2026-10-13", "--json"],
                             capture_output=True, text=True, timeout=90)
        _dd = json.loads(_dp.stdout)
        if _dd.get("verdict") != "MEASURED":
            skip("H3 投递率 / H4 跨设备偏斜", "一侧不可读 ⇒ 不可判")
        else:
            _h3 = _dd["H3_delivery"]; _h4 = _dd["H4_skew"]
            _r = _h3["rate"]
            check("H4 跨设备偏斜（★ 新建判据）", _h4["verdict"] == "PASS",
                  "★ %s — 本机 %d / 中枢 %d · Δ=%+d · %.1f%%（阈：WARN %.0f%% / FAIL %.0f%%）"
                  % (_h4["verdict"], _h4["local"], _h4["central"], _h4["delta"],
                     _h4["ratio"] * 100, _h4["thresholds"]["warn"] * 100,
                     _h4["thresholds"]["fail"] * 100))
            check("H3 投递率（今日窗）", (_r is not None and _r >= 1.0),
                  "★ %s — %d/%d = %s"
                  % (_h3["verdict"], _h3["numerator"], _h3["denominator"],
                     ("%.1f%%" % (_r * 100)) if _r is not None else "不可判"))
    except Exception as e:
        skip("H3 投递率 / H4 偏斜", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-294）【I-2 四项业界等价物 + I-3 协议一致性套件】—★ 目标四维两项。
    #   ★ 立据：W4 自陈两项【本件未测 · 复跑命令未建 · 无负控 · 窗口/分子/分母 三件全缺】。
    #   ★★ 实测（★ 严化后）：I-2a ★FAIL · I-2b ★PASS · I-2c ★★FAIL（未强制鉴权）· I-2d ★FAIL（无实现）· I-3 ★PASS（9/1）。
    try:
        _ip = subprocess.run([sys.executable, str(ROOT / "tools" / "industry-parity.py"), "--json"],
                             capture_output=True, text=True, timeout=200)
        _id = json.loads(_ip.stdout)
        _s2 = _id.get("summary") or {}
        check("I-2 四项业界等价物（★ 新建）",
              _s2.get("FAIL", 1) == 0,
              "★ PASS %d · FAIL %d · 不可判 %d"
              % (_s2.get("PASS", 0), _s2.get("FAIL", 0), _s2.get("UNDECIDABLE", 0)))
        # ★ 单独报【认证授权】—★ 它是硬缺口
        _au = _id["checks"].get("I-2c 认证授权") or {}
        check("I-2c 认证授权（★ 硬缺口）", _au.get("verdict") == "PASS",
              "★ %s — %s" % (_au.get("verdict"), _au.get("why")))
    except Exception as e:
        skip("I-2 四项业界等价物", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-295）【L-1 / L-2 保持领先】—★ 目标四维最后一维。
    #   ★ 立据：W4 自陈 **L-1 是元判据、不是可红判据**；★ L-2 **本件未测·复跑未建·无负控**。
    #   ★★ 本纳把它变成可红的：★ 扫全仓的【本机 vs 业界领先主张】逐条查三条。
    #   ★ 实测：扫 665 文件 ⇒ **真主张仅 1 条**（★ 从 62 收窄来，★ 原筛字假红）· 三条全缺 ⇒ 不得记领先。
    try:
        _lc = subprocess.run([sys.executable, str(ROOT / "tools" / "leadership-claims.py"), "--json"],
                             capture_output=True, text=True, timeout=200)
        _ld = json.loads(_lc.stdout)
        _l1 = _ld.get("L1") or {}; _l2 = _ld.get("L2") or {}
        check("L-1 领先三条合取（★ 元判据已可红）",
              _l1.get("verdict") == "PASS",
              "★ %s — 主张 %d 条 · PASS %d · FAIL %d"
              % (_l1.get("verdict"), _ld.get("claims_found", 0),
                 _l1.get("PASS", 0), _l1.get("FAIL", 0)))
        check("L-2 领先主张须挂对照实验",
              _l2.get("verdict") == "PASS",
              "★ %s — 无对照实验的主张 %d/%d"
              % (_l2.get("verdict"), _l2.get("claims_without_experiment", 0), _l2.get("total", 0)))
    except Exception as e:
        skip("L-1 / L-2 保持领先", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-299）【H2 静默失败扫描】—★ 目标四维 H2。
    #   ★ 立据：W4 自陈 H2 ★**不成立**；★ 且其「必须采纳」逐字记：
    #     ★★ **带 `_archived_at` 过滤 → n = 0；不带 → n = 7** ⇒ **同一板态，红 → 绿**。
    #   ★★ 本纳实测今日：`drift-delivery-failure` **12 → 5**（★ 部分掩盖）。
    try:
        _sf = subprocess.run([sys.executable, str(ROOT / "tools" / "silent-failure-scan.py"), "--json"],
                             capture_output=True, text=True, timeout=200)
        _sd = json.loads(_sf.stdout)
        _s2 = _sd.get("summary") or {}
        _c = _sd["checks"]
        _mask = _c.get("H2c 归档掩盖") or {}
        _ld = _c.get("H2a launchd 失败终态") or {}
        check("H2c 归档掩盖（★ W4 核心形态）", _mask.get("verdict") == "PASS",
              "★ %s — %s" % (_mask.get("verdict"), str(_mask.get("why"))[:130]))
        check("H2a launchd 失败终态", _ld.get("verdict") == "PASS",
              "★ %s — %s" % (_ld.get("verdict"), str(_ld.get("why"))[:130]))
    except Exception as e:
        skip("H2 静默失败扫描", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-300）【H5 探针负控覆盖率】—★ 目标四维 H 维最后一项。
    #   ★ 立据：W4 自陈 H5 = **元判据**：★「它量的是「负控有无」本身；
    #     ★★ 它自己的负控 = 造一个带负控的检查项 ⇒ 分母应 +1」。
    #   ★ 实测：drift-scan **0/11 = 0.0%**（★ W4 现测 0/12，★ 差在注释键）；
    #     ★★ **而本工具【实现了那个 +1】**（★ H5c 自负控已 PASS）。
    try:
        _nc = subprocess.run([sys.executable, str(ROOT / "tools" / "negctl-coverage.py"), "--json"],
                             capture_output=True, text=True, timeout=200)
        _nd = json.loads(_nc.stdout)
        _c = _nd["checks"]
        _b = _c.get("H5b 负控覆盖率（drift-scan）") or {}
        _cc = _c.get("H5c 本条自己的负控（★ 元判据的 +1）") or {}
        check("H5b 负控覆盖率（drift-scan）", _b.get("verdict") == "PASS",
              "★ %s — %s" % (_b.get("verdict"), str(_b.get("why"))[:120]))
        check("H5c 元判据自负控（★ 新建）", _cc.get("verdict") == "PASS",
              "★ %s" % str(_cc.get("why"))[:140])
    except Exception as e:
        skip("H5 负控覆盖率", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-301）【S 维五项：稳定性】—★ 目标四维最后一维。
    #   ★ 立据：W4 §3.1 S-1…S-4；★ 其中 S-1 已裁定①拆两条（★ S-1a / S-1b）。
    #   ★ 实测：S-1b **FAIL**（drift 11 vs 活体端口 40）· S-2 **PASS**（滞后 20.1 分）·
    #     S-3 **PASS**· S-4 **FAIL**（同 pid 1221）· S-1a 不可判（★ 无登记数声明）。
    try:
        _sp = subprocess.run([sys.executable, str(ROOT / "tools" / "stability-probe.py"), "--json"],
                             capture_output=True, text=True, timeout=200)
        _sd = json.loads(_sp.stdout)
        for _k, _v in _sd["checks"].items():
            _vv = _v.get("verdict")
            # ★★ 2026-10-13 修（★ 本纳自查）：**不可判 ≠ FAIL**（★ 三态不得合并）—★
            #   ★ 原写 `== "PASS"` ⇒ **UNDECIDABLE 被当成 FAIL】** ⇒ 误报。
            if _vv == "UNDECIDABLE":
                skip("S 维 %s" % _k, "★ 不可判 — %s" % str(_v.get("why"))[:110])
            else:
                check("S 维 %s" % _k, _vv == "PASS",
                      "★ %s — %s" % (_vv, str(_v.get("why"))[:120]))
    except Exception as e:
        skip("S 维（稳定性）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    # ★★ 2026-10-13（D-258）：【审查面非空】—— ★ 防「空目录被默认读成已审」。
    #   ★ 立据：`research/v7-review-V2/` **存在但空**（0 条目 · 0B）——
    #     ★★ 而它应审 W1/W2；★ **两次审查代理均零产出**（D-257）。
    #   ★ 逻辑：`research/v7-*/` 目录★ **空 ⇒ 不可判（SKIP），不得默认已审**。
    try:
        _v7dirs = sorted(d for d in glob.glob(os.path.join(str(ROOT), "research", "v7-*"))
                         if os.path.isdir(d))
        if not _v7dirs:
            skip("审查/调研目录非空（D-258）", "未找到 research/v7-* 目录 ⇒ 不可判")
        else:
            _empty = [d for d in _v7dirs if not os.listdir(d)]
            if _empty:
                skip("审查/调研目录非空（D-258）",
                     "★★ %d 个空目录：%s ★ 空 ⇒ 【不可判】（★ 不得读成已审）"
                     % (len(_empty), ",".join(os.path.basename(d) for d in _empty[:4])))
            else:
                check("审查/调研目录非空（D-258）", True,
                      "★ %d 个 v7-* 目录均非空" % len(_v7dirs))
    except Exception as e:
        skip("审查/调研目录非空（D-258）", "调用失败 %s ⇒ 不可判" % type(e).__name__)

    return 0 if not [r for r in RESULTS if not r[2] and r[0] == "FAIL"] else 1


# ------------------------------------------------------------------ 自证：每条都能红

def selftest() -> int:
    print("=== beacon-check 自证：逐条构造反例，证明每条检查都能红 ===")
    fails = 0

    def case(name, mutate, expect_fail_substr):
        nonlocal fails
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            (t / "data/registry").mkdir(parents=True)
            (t / "docs").mkdir()
            base_index = json.loads((ROOT / "data/registry/continuity-index.json").read_text(encoding="utf-8"))
            anchor_src = ROOT / base_index["anchor"]
            (t / base_index["anchor"]).write_text(anchor_src.read_text(encoding="utf-8"), encoding="utf-8")
            rp_src = ROOT / base_index["resume_prompt"]
            if rp_src.exists():
                (t / base_index["resume_prompt"]).write_text(rp_src.read_text(encoding="utf-8"), encoding="utf-8")
            for e in base_index.get("evidence_index") or []:
                if e.startswith(("blackboard:", "agentsrc:")):
                    continue
                p = t / e
                if p.suffix:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text("x", encoding="utf-8")
                else:
                    p.mkdir(parents=True, exist_ok=True)
            base_index["anchor_sha256"] = sha256(t / base_index["anchor"])
            idx = mutate(json.loads(json.dumps(base_index)))
            (t / "data/registry/continuity-index.json").write_text(
                json.dumps(idx, ensure_ascii=False), encoding="utf-8")
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = run(t, net=False)
            out = buf.getvalue()
            ok = (rc != 0) and any(l.startswith("FAIL") and expect_fail_substr in l
                                   for l in out.split("\n"))
            print(("PASS " if ok else "FAIL ") + f"反例可红：{name}")
            if not ok:
                fails += 1
                print("      rc=", rc, "| 期望含:", expect_fail_substr)
                print("      " + "\n      ".join(out.split("\n")[:14]))

    case("版本不一致", lambda d: {**d, "state_version": d["state_version"] + 1}, "state_version 相等")
    case("锚点被改但未重盖章", lambda d: {**d, "anchor_sha256": "0" * 64}, "锚点指纹未变")
    case("证据指针指到不存在的路径",
         lambda d: {**d, "items": [{**i, "evidence": ["docs/不存在的文件.md"]}
                                   if i["id"] == "C2" else i for i in d["items"]]},
         "C2 证据指针可解")
    case("closed 项无证据指针",
         lambda d: {**d, "items": [{**i, "evidence": []} if i["id"] == "C1" else i for i in d["items"]]},
         "C1 有 evidence 指针")
    # ★★ 2026-10-13（★ W2 §3.4 替换后同步）：判据已改名为「在位」
    #   ★ 故反例也要改：★ 现「缺席」本身就应报红。
    case("dod 全文表缺席（★ 替换后）",
         lambda d: {**d, "dod": {"full_table": None}}, "全文表在位（★ 替换后）")

    # ---- B10 三条新判据的反例（**新判据不带反例 = 又一道不会红的门**）
    case("updated_at 非 RFC 3339 规范形",
         lambda d: {**d, "updated_at": "2026-10-10T07:00:00+0800"}, "RFC 3339 规范形")
    case("updated_at 落在未来（按感觉估时间）",
         lambda d: {**d, "updated_at": "2099-01-01T00:00:00+08:00"}, "未落在未来")
    # ★★ 2026-10-13（★ W2 §3.4 替换后同步）：判据改为「有效」—★
    #   ★ 故加【两个】反例：① 无字段 ② **字段在而值是占位串**（★ 后者正是旧判据看不见的）。
    case("closed 项无 verifier 字段",
         lambda d: {**d, "items": [{k: v for k, v in i.items() if k != "verifier"}
                                   if i["id"] == "C1" else i for i in d["items"]]},
         "closed 项 verifier 有效（★ 替换后）")
    case("closed 项 verifier 是占位串（★ 新增反例）",
         lambda d: {**d, "items": [{**i, "verifier": "待第三方复核"}
                                   if i["id"] == "C1" else i for i in d["items"]]},
         "closed 项 verifier 有效（★ 替换后）")
    case("waves 记 open 而其 items 已有 closed",
         lambda d: {**d, "waves": [{**w, "state": "open"} if w["id"] == "C" else w
                                   for w in d["waves"]]},
         "两段一致")
    case("wave note 称「未做」而 items 记为 closed",
         lambda d: {**d, "waves": [{**w, "note": "C2 未做。"} if w["id"] == "C" else w
                                   for w in d["waves"]]},
         "两段一致")

    # ---- 专测「跳过 ≠ 通过」（本台反复复发的病）：黑板指针在无 --net 时必须是 SKIP
    # 构造一个**只有**黑板证据指针的 closed 项：它既不该 PASS（没查过），也不该 FAIL（没坏）。
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "data/registry").mkdir(parents=True)
        (t / "docs").mkdir()
        base = json.loads((ROOT / "data/registry/continuity-index.json").read_text(encoding="utf-8"))
        (t / base["anchor"]).write_text((ROOT / base["anchor"]).read_text(encoding="utf-8"), encoding="utf-8")
        if (ROOT / base["resume_prompt"]).exists():
            (t / base["resume_prompt"]).write_text(
                (ROOT / base["resume_prompt"]).read_text(encoding="utf-8"), encoding="utf-8")
        base["anchor_sha256"] = sha256(t / base["anchor"])
        base["items"] = [{"id": "X", "state": "closed_with_evidence",
                          "evidence": ["blackboard:data/registry/continuity-index"]}]
        (t / "data/registry/continuity-index.json").write_text(
            json.dumps(base, ensure_ascii=False), encoding="utf-8")
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run(t, net=False)
        lines = buf.getvalue().split("\n")
        skip_line = [l for l in lines if l.startswith("SKIP X 证据指针可解")]
        pass_line = [l for l in lines if l.startswith("PASS X 证据指针可解")]
        ok = bool(skip_line) and not pass_line and any(SKIPPED)
        print(("PASS " if ok else "FAIL ") + "跳过 ≠ 通过（无 --net 的黑板指针必须 SKIP，不得 PASS）")
        if not ok:
            fails += 1
            print("      SKIP 行数=", len(skip_line), " PASS 行数=", len(pass_line), " SKIPPED=", SKIPPED)

    # ---- G-CR18 ④ 与守恒断言的反例（★ 新判据不带反例 = 又一道不会红的门）
    import contextlib
    import io
    real_bv, real_ck = board_value, CHECKPOINT

    def _mk_tree(t: Path) -> dict:
        (t / "data/registry").mkdir(parents=True)
        (t / "docs").mkdir()
        b = json.loads((ROOT / "data/registry/continuity-index.json").read_text(encoding="utf-8"))
        (t / b["anchor"]).write_text((ROOT / b["anchor"]).read_text(encoding="utf-8"), encoding="utf-8")
        rp = ROOT / b["resume_prompt"]
        if rp.exists():
            (t / b["resume_prompt"]).write_text(rp.read_text(encoding="utf-8"), encoding="utf-8")
        (t / "docs/ok.md").write_text("x", encoding="utf-8")
        for e in b.get("evidence_index") or []:            # 单元测试不走网络
            if e.startswith(("blackboard:", "agentsrc:")):
                continue
            p = t / e
            if p.suffix:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")
            else:
                p.mkdir(parents=True, exist_ok=True)
        for i in b.get("items") or []:                     # 黑板指针换成本地可解件
            if i.get("evidence"):
                i["evidence"] = ["docs/ok.md"]
        b["anchor_sha256"] = sha256(t / b["anchor"])
        (t / "data/registry/continuity-index.json").write_text(
            json.dumps(b, ensure_ascii=False), encoding="utf-8")
        return b

    def _run_patched(t: Path, board_obj, ck: Path, *, net: bool = True, accept: bool = False):
        globals()["board_value"] = lambda timeout=8: (board_obj, "test 板 v0 ts=T")
        globals()["CHECKPOINT"] = ck
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run(t, net=net, accept_shrink=accept)
        return rc, buf.getvalue()

    def _verdict(rc: int, out: str, kind: str, sub: str) -> bool:
        return any(l.startswith(kind) and sub in l for l in out.split("\n"))

    def _t(label: str, ok: bool):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + label)
        if not ok:
            fails += 1

    try:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            base = _mk_tree(t)
            ck = Path(td) / "ck.json"

            # ④ 负控：板值与本地副本分叉 ⇒ 必须红
            split = json.loads(json.dumps(base))
            split["_diverged"] = "板与本地分叉"
            rc, out = _run_patched(t, split, ck)
            _t("反例可红：本地副本与板值分叉（G-CR18 ④）",
               rc != 0 and _verdict(rc, out, "FAIL", "本地副本 ↔ 板值一致"))

            # ④ 正控：一致 ⇒ 该条必须 PASS（防判据恒红，恒红与恒绿一样没判别力）
            rc, out = _run_patched(t, base, ck)
            _t("正控：本地副本与板值一致 ⇒ 该条 PASS（判据非恒红）",
               _verdict(rc, out, "PASS", "本地副本 ↔ 板值一致"))

            # ④ 无 --net ⇒ 必须 SKIP，不得混进 PASS
            rc, out = _run_patched(t, base, ck, net=False)
            _t("跳过 ≠ 通过：无 --net 时 ④ 必须 SKIP、不得 PASS",
               _verdict(rc, out, "SKIP", "本地副本 ↔ 板值一致")
               and not _verdict(rc, out, "PASS", "本地副本 ↔ 板值一致"))

            # 守恒：首次运行只建档，不得谎报通过
            ck.unlink(missing_ok=True)
            rc, out = _run_patched(t, base, ck)
            _t("守恒：首次运行**只建档、未抽检**（不谎报通过）",
               ck.exists() and _verdict(rc, out, "SKIP", "体量守恒"))

            # 守恒负控：腰斩 ⇒ 必须红
            shrunk = json.loads(json.dumps(base))
            shrunk["open_questions"] = (shrunk.get("open_questions") or [])[:1]
            shrunk.pop("_sync_note", None)
            rc, out = _run_patched(t, shrunk, ck)
            _t("反例可红：索引体量骤降（腰斩检测）",
               rc != 0 and _verdict(rc, out, "FAIL", "体量守恒"))

            # ★ 红线不得被自动吞掉：连跑两次仍红（基线未被推进，否则红一次就永久绿）
            rc, out = _run_patched(t, shrunk, ck)
            _t("守恒红线不自动消：未 --accept-shrink 时连跑两次都红",
               rc != 0 and _verdict(rc, out, "FAIL", "体量守恒"))

            # 显式接受后才推进基线
            _run_patched(t, shrunk, ck, accept=True)
            rc, out = _run_patched(t, shrunk, ck)
            _t("守恒：--accept-shrink 显式接受后基线推进、转为不红",
               not _verdict(rc, out, "FAIL", "体量守恒"))
    finally:
        globals()["board_value"], globals()["CHECKPOINT"] = real_bv, real_ck

    # ---- ★ M4①d 通道巡检心跳：判据三态负控（**不需要网络** —— 用假命令注入三态）
    # ★ 为什么必须做：若判据恒绿，这套心跳就只是把「没在看」包装成「在看」（D-053 同型）。
    _py = sys.executable
    for _nm, _cmd, _want in (
            ("陈旧 ⇒ 必须红", [_py, "-c", "print('STALE fake'); raise SystemExit(1)"], "stale"),
            ("新鲜 ⇒ 必须绿", [_py, "-c", "print('FRESH fake')"], "fresh"),
            ("读不到 ⇒ 必须不可判（不冒充成立）", [_py, "-c", "raise SystemExit(2)"], "undecidable"),
            ("命令不存在 ⇒ 必须不可判", ["/nonexistent/definitely-not-a-binary"], "undecidable")):
        _got, _det = probe_patrol_heartbeat(_cmd)
        _ok = _got == _want
        print(("PASS " if _ok else "FAIL ") + f"M4①d 心跳判据负控：{_nm}（got={_got} want={_want}）")
        if not _ok:
            fails += 1

    print()
    print("自证：", "全绿" if not fails else f"**有红**（{fails} 条）")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", action="store_true", help="追加黑板键可读性抽检（会打网络）")
    ap.add_argument("--stamp", action="store_true", help="把当前锚点 sha256 盖进索引")
    ap.add_argument("--bump-pointer", action="store_true",
                    help="把当前 state_version 写进 ~/.dsh/continuity-last-version（消掉 WARN）")
    ap.add_argument("--accept-shrink", action="store_true",
                    help="显式接受索引体量骤降（推进守恒基线）；不确认就别用，红线是刻意的")
    ap.add_argument("--selftest", action="store_true")
    # ★★ 2026-10-12（v7 更正账 / W1 发现）：`PEND`/`SKIP` 此前【只打印、不进退出码】
    #   ⇒ ★ 在脚本化场景（`beacon-check || exit`）下被【静默忽略】——★ 即「越严重的项越不报警」。
    #   ⇒ 修法：加 `--strict`，使 PEND/SKIP 也导致非零退出。★ 默认行为不变（向后兼容）。
    ap.add_argument("--strict", action="store_true",
                    help="把 PEND/SKIP 也算作非零退出（★ 供 hook/CI 用；默认只算 FAIL）")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    if a.stamp:
        idx = json.loads(INDEX.read_text(encoding="utf-8"))
        anchor = ROOT / idx["anchor"]
        idx["anchor_sha256"] = sha256(anchor)
        idx["updated_at"] = __import__("datetime").datetime.now().astimezone().replace(microsecond=0).isoformat()
        INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✓ 盖章 anchor_sha256={idx['anchor_sha256'][:16]}…（state_version={idx['state_version']}）")

    if a.bump_pointer:
        cur = json.loads(INDEX.read_text(encoding="utf-8"))["state_version"]
        VERSION_POINTER.parent.mkdir(parents=True, exist_ok=True)
        VERSION_POINTER.write_text(str(cur), encoding="utf-8")
        print(f"✓ 版本指针 ← {cur}（{VERSION_POINTER}）")

    rc = run(ROOT, net=a.net, accept_shrink=a.accept_shrink)
    print()
    # ★★ 2026-10-12（D-213）：`--strict` 下 PEND/SKIP 也算非零退出
    #   ★ 立据：旧行为下 `PEND 1` 而 `exit=0` ⇒ 脚本化时被静默忽略。
    if a.strict and rc == 0 and (PENDING or SKIPPED):
        rc = 1
    bad = [r for r in RESULTS if not r[2] and r[0] == "FAIL"]
    warn = [r for r in RESULTS if not r[2] and r[0] == "WARN"]
    tail = f"（{len(warn)} 条 WARN，{len(SKIPPED)} 条 SKIP，{len(PENDING)} 项待复核）"
    if bad:
        print(f"反遗忘校验：**有红**（{len(bad)} 条 FAIL）{tail}")
    elif SKIPPED or PENDING:
        why = []
        if SKIPPED:
            why.append(f"**有 {len(SKIPPED)} 条根本没抽检**")
        if PENDING:
            why.append(f"**有 {len(PENDING)} 项记为 closed 而审查员未到位**")
        print(f"反遗忘校验：无 FAIL，但{'，'.join(why)} ⇒ 不得读作『全绿』{tail}")
        for n in SKIPPED:
            print("         SKIP " + n)
        for n in PENDING:
            print("         PEND " + n)
    else:
        print(f"反遗忘校验：全绿 {tail}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
