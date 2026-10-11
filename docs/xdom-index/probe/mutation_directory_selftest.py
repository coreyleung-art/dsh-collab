#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mutation_directory_selftest.py — 证明 xdom-directory.py 的 --selftest / 结构门【会变红】（v3，对 v0.4.0）

★ 为什么必须有这一支
  本轮的教训（我对 int 的 S3）：一条控若不能被负控打红，它就是**空转绿**。
  「N PASS / 0 FAIL」在**未经变异检验**前，**不构成**它有效的证据。
  做法：把源读进内存 → 一处变异 → 内存 exec → 跑 selftest → 比对 PASS/FAIL。
  ★ 全程不落盘、不改仓库任何一行。

★ 探针自身的错（自曝，第一版）
  v1 里写了 `hit = "★ 期望控" in txt and ...` —— 那字面量只存在于**本探针源码**，
  工具输出里根本没有 ⇒ 恒 False ⇒ 四行全报「期望控未命中」。
  ★ 同族错误：**判据的对象取错了**（不是读数错）。本版已修，并逐行核命中。

★ v3（对 v0.4.0）新增两组 —— ★ 且**两组都直接针对 v0.4.0 那一处旗舰修复**：
  · **M12–M15（selftest 模式）**：把 v0.4.0 新加的四条能力逐条打回 v0.3.0 口径
    ⇒ ★ 若打回去之后 selftest 仍全绿，那 v0.4.0 的修复就是**没有控的**（空转绿）。
  · **M16（gate 模式，新引入）**：★ 前 15 个变异都只检验「读数对不对」，
    **没有一个检验「门会不会拒绝」**。M16 往源码里注入**一处真写请求调用点**，
    再问**门自己**（`scan_forbidden`）—— ★ 期望它必须命中。
    ⇒ ★ 这一条才是 R006 ⑩「约束前置·不可绕过」的**唯一**直接证据。

用法: python3 docs/xdom-index/probe/mutation_directory_selftest.py
"""
import contextlib
import io
import re
import sys

SRC = "/Users/coreyleung/dsh-collab/docs/xdom-index/xdom-directory.py"

SORT_LINE = '    keys = sorted(k for k in logs if k.startswith(LOG_PREFIX))\n'
OWED_LINE = '    owed = [p for p in posts if p["requires_reply"]]\n'
REQ_LINE = '        requires = rr and ball not in _NO_BALL\n'
UNREAD_LINE = '                                       if p["to"] == party and (upto is None or p["key"] > upto))}\n'
REF_LINE = '    if r.startswith(LOG_PREFIX):\n        return "letter"\n'
REUSE_LINE = '    reused = {t: n for t, n in topics.items() if n >= 2}\n'
FACT_KEYS_LINE = '        "edges_fact": facts, "edges_inferred": inferred,\n'
INFER_SCAN_LINE = '        for j in range(i + 1, len(posts)):\n'
INFER_COND_LINE = '        if not (a["reply_required"] and a["ball"] == a["to"]):\n'
AWAITING_LINE = '    if "awaiting" in m:\n        return m.get("awaiting"), True\n'
SESSION_MATCH_LINE = '    mm = _SESSION_RE.match(v)\n'
REPLY_TO_LINE = '    rk = m.get("reply_to_key")\n'
SKEW_LINE = '            out.append(W_KEY_VS_FIELD)\n'
GATE_ANCHOR = 'LOG_PREFIX = NS + "/log/"\n'

# ★ mode: "selftest"（比对 PASS/FAIL 是否变红） · "gate"（问门自己：注入的写请求有没有被拒）
MUTANTS = [
    # ── 既有 7 条（对 v0.2.0 就有的控；★ 每换一版都必须**重跑**，锚点会漂）──
    ("M1 欠账表 = 全部楼（丢掉 requires_reply 过滤）", "selftest", OWED_LINE,
     "    owed = posts\n", "正控：要求回复的楼 = 2（t1 两楼）"),
    ("M2 去掉键序排序（改用输入顺序）", "selftest", SORT_LINE,
     "    keys = [k for k in logs if k.startswith(LOG_PREFIX)]\n",
     "★ 负控：打乱输入 ⇒ 末楼仍按键序为 t2-c（不被输入序带偏）"),
    ("M3 未读判据方向反转（k>upto → k<upto）", "selftest", UNREAD_LINE,
     '                                       if p["to"] == party and (upto is None or p["key"] < upto))}\n',
     "★ 负控：水位退回第一楼 ⇒ 未读=1（证明未读计数是真算的）"),
    ("M4 忽略 reply_required（只看球）", "selftest", REQ_LINE,
     "        requires = ball not in _NO_BALL\n",
     "★ 拆分控：球在 int 但【明说勿回】⇒ 不要求回复"),
    ("M5 忽略 ball 的 none 判定（只要求回复）", "selftest", REQ_LINE,
     "        requires = rr\n",
     "★ 拆分控：要求回但【球在 none】⇒ 不要求回复（谁也不欠）"),
    ("M6 ref 分类：把信键也判成文件路径", "selftest", REF_LINE,
     '    if r.startswith(LOG_PREFIX):\n        return "path"\n',
     "★ ref 控：指向信键的 ref = 1"),
    ("M7 topic 复用数 = 全部 topic（丢掉 ≥2 过滤）", "selftest", REUSE_LINE,
     "    reused = topics\n",
     "★ topic 控：夹具里 t1 有 2 楼 ⇒ 被复用 topic 数 = 1"),

    # ── v0.3.0 起的 4 条（P2 计划里的 M8–M11）──
    ("M8 fact / inferred **合并成一个 list**（分栏控）", "selftest", FACT_KEYS_LINE,
     '        "edges_fact": facts + inferred, "edges_inferred": inferred,\n',
     "★ **分栏控（直接读返回结构，不读 totals）**：`edges_fact`=1 且 `edges_inferred`=4"),
    ("M9 推断边取**最后一封**（「第一封」判据失效）", "selftest", INFER_SCAN_LINE,
     "        for j in range(len(posts) - 1, i, -1):\n",
     "★ 边控：k2 的推断目标 = **第一封**来自 int 的信（k3），不是最后一封"),
    ("M10 推断判据**忽略 ball**（只用 reply_required）", "selftest", INFER_COND_LINE,
     '        if not a["reply_required"]:\n',
     "★ 边控：推断边 = 4（k1→k3 · k2→k3 · k3→k4 · k4→k6）"),
    ("M16 往源码注入一处**真写请求**调用点 ⇒ 门必须拒绝", "gate", GATE_ANCHOR,
     GATE_ANCHOR + 'def _mut_probe(u):\n'
                   '    return urllib.request.Request(u, method="PUT")\n',
     "（gate 模式：期望「拒绝」= 命中非空）"),

    # ── ★★ v0.4.0 新加 4 条：逐条把 v0.4.0 的修复打回 v0.3.0 口径 ──
    ("M12 丢掉 v2 的 `awaiting`（★ 打回 v0.3.0 的 schema 盲）", "selftest", AWAITING_LINE,
     '    if "awaiting" in m:\n        return None, False\n',
     "★★ **回归控（本组最重要的一条）**：v2 信 `awaiting='ext'` ⇒ requires_reply=**True**"),
    ("M13 参与方不剥 `session-` 前缀（归一失效）", "selftest", SESSION_MATCH_LINE,
     "    mm = None\n",
     "★ 归一键控：`to=session-…` **剥前缀后归一到 `ext`**（★ 原始串保留在 `to_raw`，不改事实）"),
    ("M14 丢掉 v2 的 `reply_to_key`（v2 事实边消失）", "selftest", REPLY_TO_LINE,
     "    rk = None\n",
     "★ 事实边控：v2 的 `reply_to_key` **能**落成事实边"),
    ("M15 丢掉时间不符告警（键段 vs 字段时间）", "selftest", SKEW_LINE,
     "            pass\n",
     "★ 告警控：键段 02:40 vs epoch **02:02:02** ⇒ 差 38 分钟 ⇒ `W-KEY-VS-FIELD-TS` 必亮"),
]


def score_selftest(src):
    """调 selftest()，捕获 stdout ⇒ (pass, fail, 文本 或 异常文本)。"""
    ns = {"__name__": "notmain", "__file__": SRC}
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(src, SRC, "exec"), ns)
            ns["selftest"]()
    except Exception as e:                                    # 变异体直接崩，也算被抓到
        return -1, -1, f"{type(e).__name__}: {e}"
    text = buf.getvalue()
    m = re.search(r"selftest: (\d+) PASS / (\d+) FAIL", text)
    return (int(m.group(1)), int(m.group(2)), text) if m else (None, None, text)


def score_gate(src):
    """把**变异后的源码**喂给**变异后的门自己** ⇒ 返回命中列表（或异常）。
    ★ 这一支问的不是「读数对不对」，而是「**门会不会拒绝**」——
      它是 R006 ⑩「约束前置·不可绕过」唯一直接的证据。"""
    ns = {"__name__": "notmain", "__file__": SRC}
    try:
        exec(compile(src, SRC, "exec"), ns)
        return ns["scan_forbidden"](src)
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main():
    base = open(SRC, encoding="utf-8").read()
    p0, f0, _ = score_selftest(base)
    g0 = score_gate(base)
    print(f"═══ 对照组（未变异）═══ selftest {p0} PASS / {f0} FAIL · 门命中 {g0 or '无'}")
    if p0 is None or p0 < 0:
        print("★ 对照组没跑出读数 ⇒ 无法判定")
        return 2
    if g0:                                    # ★ 门在**未变异**源码上就命中 ⇒ 门自己坏了
        print(f"★ 对照组门就命中 {g0} ⇒ ★ **门在干净源码上假阳性**，后续 gate 组全部不可判")
        return 2

    bad = 0
    print("\n═══ 变异组 ═══")
    for name, mode, anchor, repl, expect in MUTANTS:
        n = base.count(anchor)
        if n != 1:
            print(f"  ⚠ {name}: 锚点出现 {n} 次（≠1）⇒ 变异未施加，本行【不可判】")
            bad += 1
            continue
        mutated = base.replace(anchor, repl)
        if mode == "gate":
            hits = score_gate(mutated)
            turned = bool(hits) and not isinstance(hits, str)
            print(f"  {'✅ 变红' if turned else '❌ 纹丝不动（空转绿！）'}  {name}\n"
                  f"      gate 模式 · 门命中 = {hits if not isinstance(hits, str) else hits}"
                  f"（对照 干净源码命中 {'无' if not g0 else g0}）")
        else:
            p, f, txt = score_selftest(mutated)
            turned = (p is not None and (p < 0 or f > f0))
            hit = ("❌ " + expect) in (txt or "")
            print(f"  {'✅ 变红' if turned else '❌ 纹丝不动（空转绿！）'}  {name}\n"
                  f"      {'崩溃' if (p is not None and p < 0) else f'{p} PASS / {f} FAIL'}"
                  f"（对照 {p0}/{f0}） · 期望控{'确已' if hit else '★未'}命中"
                  f"{'' if hit else f'「{expect}」'}")
        if not turned:
            bad += 1

    print(f"\n结论：{'★ 该自检【会变红】—— 是真控' if bad == 0 else f'★ 有 {bad} 项未通过变异检验'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
