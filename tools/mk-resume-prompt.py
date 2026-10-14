#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mk-resume-prompt.py — 由索引键渲染续接提示词（信标四件套之③ 的生成脚本）

依据：计划 §4.1③ 「③ 续接提示词 `docs/resume-prompt-starbridge-v3.md`（≤40 行）+ 生成脚本」，
     判据「新会话按前 3 步复述出『当前 wave + 下一步』」。

为什么是「生成」而不是「手写」：手写的续接提示词会**随计划漂移**——锚点更新了、提示词没更新，
读它的人就按旧状态干活，而它看起来完全正常。这与 §4.3 半修形态④「声明面 > 证据面」同源。
⇒ 本脚本把「当前 wave / 下一步」变成**从索引键算出来的量**，并在越界时**拒绝生成**。

用法:
    python3 tools/mk-resume-prompt.py                 # 渲染并写盘（越界则拒绝并 exit 2）
    python3 tools/mk-resume-prompt.py --check         # 只校验，不写盘
    python3 tools/mk-resume-prompt.py --stdout        # 打到标准输出
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "data/registry/continuity-index.json"
MAX_LINES = 40                       # §4.1③ 的字面上限
CLOSED = "closed_with_evidence"
WAVE_ORDER = ("S", "C", "0", "1", "2", "3", "4", "5")


def die(msg: str, code: int = 2):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def load():
    if not INDEX.exists():
        die(f"索引键本地副本不在：{INDEX}")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    anchor = ROOT / idx["anchor"]
    if not anchor.exists():
        die(f"锚点文档不在：{anchor}")
    head = anchor.read_text(encoding="utf-8")[:2000]
    m = re.search(r"state_version\D{0,12}(\d+)", head)
    if not m:
        die("锚点头部读不到 state_version")
    anchor_v = int(m.group(1))
    if anchor_v != idx["state_version"]:
        die(f"**版本不一致**：锚点 state_version={anchor_v}，索引 state_version={idx['state_version']}"
            f" —— 拒绝生成（否则新会话会按错状态干活）")
    return idx, anchor, anchor_v


def pick_wave(idx):
    """当前 wave = **正在推进的那一波**。

    先取 `in_flight`（真有人在动的）；没有才退到"按 §14 执行序第一个未 closed 的"。
    ⚠️ 不能只取"第一个未 closed"：那样若前序 wave 卡在 `blocked`，就会报出**前一波**当"当前"，
    而"下一步"却是后一波的项 —— 两处读数互相矛盾，读的人按哪条都错。
    （本条是"当前 wave 与下一步必须自洽"的判据，不是排序偏好。）
    """
    by_id = {w["id"]: w for w in idx["waves"]}
    # ★★★ 2026-10-15（D-385）【先取【WAVE_ORDER 之外的 open wave】】—★
    #   ★ 立据：★ `WAVE_ORDER` 是**硬编码**的（★ S/0/C…—★ 停在 v5/v6），
    #     ★★ 而本线加的 `V7`（★ v7 四维 14 判据）**不在里面** ⇒ ★★★ **永远选不到**，
    #     ★ 于是产出的提示词**指向旧工作**（★ `Wave S` / `C6`）。
    #   ★ 修法：★ **先找【不在 WAVE_ORDER 里】且 `state != closed` 的 wave**（★ 取**最后加入**的）
    #     —★ 因为【后加的 = 更新的工作】。
    _extra = [w for w in idx["waves"]
              if w.get("id") not in WAVE_ORDER and w.get("state") != CLOSED and w.get("id")]
    if _extra:
        return _extra[-1]
    for wid in WAVE_ORDER:
        w = by_id.get(wid)
        if w and w.get("state") == "in_flight":
            return w
    for wid in WAVE_ORDER:
        w = by_id.get(wid)
        if w and w.get("state") != CLOSED:
            return w
    return None


def next_item(idx):
    """下一步 = items 里第一条尚未 closed_with_evidence 的。

    ★★★ 2026-10-15（D-385）【同族修：优先取【当前 wave 的 item】】—★
      ★ 立据：★ 与 `pick_wave` **同一个原因** —★

        ★ 旧 `items`（★ `C1`…`C10`）停在 v5/v6，★ 而本线加的 v7 判据**在它们之后**，

        ★★ 故取【第一条未 closed】会永远报旧的（★ 实测：报だった `C6`）。

      ★ 修法：★ **先找【当前 wave 相关】的 item**（★ 按 id 前缀匹配），★ 找不到才退到原逻辑。
    """
    w = pick_wave(idx)
    _wid = (w or {}).get("id") or ""
    # ★ 当前 wave 是 V7 时，它的 item 是那些【不在旧集合里】的
    _LEGACY = {"C1", "C2", "C3", "C4", "C4-b", "C5", "C6", "C7", "C8", "C9", "C10"}
    if _wid and _wid not in ("S", "C", "0", "1", "2", "3", "4", "5"):
        _new = [it for it in idx["items"]
                if it.get("state") != CLOSED and it.get("id") not in _LEGACY]
        if _new:
            return _new[0]
    for it in idx["items"]:
        if it.get("state") != CLOSED:
            return it
    return None


def render(idx, anchor, anchor_v) -> str:
    w = pick_wave(idx)
    it = next_item(idx)
    ls = idx.get("last_session") or {}
    urgent = [q for q in idx.get("open_questions") or []
              if q.get("urgent") and not q.get("voided")]
    gaps = idx.get("known_gaps") or []

    L = []
    _m = re.search(r"-v(\d+)-", str(idx.get("anchor", "")))
    _ver = f"v{_m.group(1)}" if _m else "v?"
    L.append(f"# 续接提示词 · 星桥治理计划 {_ver} —— 给新会话的前 3 步")
    L.append("")
    L.append(f"> 生成自 `{INDEX.relative_to(ROOT)}`（state_version={anchor_v}）· 由 `tools/mk-resume-prompt.py` 渲染")
    L.append(f"> 锚点：`{idx['anchor']}`（**唯一权威**，本提示词只是索引，不是规格）")
    L.append("")
    L.append("## 前 3 步（照做，别跳）")
    L.append("")
    L.append(f"**① 读锚点** `{idx['anchor']}` —— **先读**头部 + §0/§1/§14/§15；"
             f"其余各节**已全部内联**（锚点自足 ⇒ 不必跳转他文件），需要时再展开。")
    L.append(f"**② 读索引** 黑板 `{idx.get('_board_key', 'data/registry/continuity-index')}`（本地副本 "
             f"`{INDEX.relative_to(ROOT)}`），比对 `state_version` 与锚点一致。")
    # ★★★ 2026-10-13 修（★ D-314 子代理实测发现）：【「必须 exit 0」与现状直接冲突】—★
    #   ★★ 立据：实测一个无上下文的子代理跑到这一步时 —★
    #     ★ `beacon-check` **报 14 FAIL / 8 SKIP、退出码 1** ⇒ ★★ **它直接卡住**；
    #     ★ 而那子代理选择了「**继续并如实报**」—★ ★ 那是对的。
    #   ★ 修法：改成**三态读法**（★ 不强制 exit 0，★ 而要求如实报）。
    L.append(f"**③ 跑反遗忘校验** `python3 {idx['beacon_check']} --net` \u2014\u2605 "
             f"**它现在会报红（★ 而那些红是真的）**：\u2605 exit 0 = 全绿 \u00b7 "
             f"exit 1 = 有红（★ **先如实转述红的内容，★ 不得绕过，也不得因此卡住**）。"
             f"\u2605\u2605 **「有红」≠「不能继续」** \u2014\u2605 "
             f"本计划的红正是**待推进的清单**。"
             f"\uff08`--net` 抽检黑板指针；\u2605 不加会显示 `SKIP` —\u2605 "
             f"★\u2605 **未抽检 ≠ 通过。**）")
    L.append("")
    L.append("")
    L.append("★★ **④ 派子代理前必做**：跑 `python3 tools/lint-inventory.py --prompt` → 把【既有 lint/gate 清单】粘进提示词。"
             " ★ 立据（D-209）：本仓 tools/ 下已有 **10** 个 lint/gate 正好管着当晚所有坑，★★ **而 20 个子代理一个都没引用**；门：`--check` 未含清单 ⇒ exit 1。")

    L.append("## 复述题（第 3 步之后立刻回答，答完再动手）")
    L.append("")
    if w:
        L.append(f"- **当前 wave = `Wave {w['id']}`**：{w.get('name', '')}")
        if w.get("state") == "blocked":
            L.append(f"  - 阻塞：{w.get('blocked_reason', '—')}")
        elif w.get("note"):
            L.append(f"  - 现状：{w['note']}")
    if it:
        L.append(f"- **下一步 = `{it['id']}`**：{it.get('name', '')}")
        if it.get("blocked_reason"):
            L.append(f"  - 阻塞：{it['blocked_reason']}")
    L.append("")
    L.append("## 上一会话是怎么死的（**别重蹈**）")
    L.append("")
    L.append(f"- `{ls.get('id', '?')}` ⇒ **{ls.get('status', '?')}**（{ls.get('ended_at', '?')}）")
    L.append(f"- 因：{ls.get('cause', '?')} ｜ 一手证据 + 门建议：`{ls.get('evidence', '?')}`")
    L.append("")
    L.append("## 要你（用户）拍板的（阻塞在决策，不阻塞在能力）")
    L.append("")
    if urgent:
        for q in urgent:
            L.append(f"- **{q['id']}**（{q.get('owner', '?')}）：{q['ask']}")
    else:
        L.append("- （无 —— 索引 `open_questions` 中无 `urgent: true` 且未作废的项）")
    L.append("")
    L.append("## 已知缺口（**别当已建成**）")
    L.append("")
    for g in gaps[:3]:
        L.append(f"- {g}")
    L.append("")
    L.append("## 纪律（违反即失去意义）")
    L.append("")
    L.append("- **R030**：不陈述没验证的东西；算不出的记 `absent`，**绝不填 0 冒充通过**。")
    L.append("- **closure 三要素**：DoD（含边界+负控）· evidence（可解指针）· **verifier（第三方，禁自证）**。")
    L.append("- **半修清单**：开关装上 ≠ 机制生效 ≠ 结果可控；**不可逆动作（重启/改 profile/载体换）先登记后执行**。")
    L.append(f"<!-- generated from state_version={anchor_v}; anchor_sha256="
             f"{hashlib.sha256(anchor.read_bytes()).hexdigest()[:16]}… -->")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验行数与版本一致性，不写盘")
    ap.add_argument("--stdout", action="store_true")
    a = ap.parse_args()

    idx, anchor, v = load()
    text = render(idx, anchor, v)
    n = len(text.rstrip("\n").split("\n"))

    if n > MAX_LINES:
        die(f"渲染出 {n} 行 > 上限 {MAX_LINES}（§4.1③）—— **拒绝写盘**。"
            f"续接提示词一旦超长，新会话就不会读完它；请精简索引键内容，不要抬高上限。", 2)

    if a.stdout:
        sys.stdout.write(text)
        print(f"--- {n}/{MAX_LINES} 行", file=sys.stderr)
        return
    if a.check:
        print(f"✓ 版本一致（state_version={v}）· 行数 {n}/{MAX_LINES}")
        return

    out = ROOT / idx["resume_prompt"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"✓ 写入 {out.relative_to(ROOT)}（{n}/{MAX_LINES} 行，state_version={v}）")


if __name__ == "__main__":
    main()
