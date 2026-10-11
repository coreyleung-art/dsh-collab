#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xdom-directory.py — 跨域邮箱【只读目录页】生成器（v0.2.0）

★ 为什么有这一支
  邮箱只有两层：信（`notes/xdom/log/**`）与水位（`notes/xdom/cursor/<party>`）。
  一封信属于哪一摊、**现在还欠谁一句**，只能靠人逐封读 ⇒ 多帖并行时账目不清。
  本支把 log **派生**成一页目录。

★ v0.1 → v0.2 的改动（★ 被实测逼出来的，不是我坐着想的）
  v0.1 按 `topic` 分帖。**实测：15 楼 15 个互不相同的 topic ⇒ 分成 15 个单楼帖，聚合为零。**
  ⇒ 于是 v0.2 不再假装有"帖"，改为**把三个读数当证据印出来**，并**明确标出哪一条算不出来**：
      楼数 · 要求回复的楼数 · ★「现在还欠谁一句」= 不可判（缺回复链）
  ★ 我不为了让页面好看而**造线**（推测性聚类会把事实变成我的推断）。

★ 本支定位（四条，写死）
  ① **只读**：只 GET，**不写任何键**（全文无 PUT/POST/DELETE）。
  ② **派生**：整页可由 log 重建 ⇒ 读模型，不是新的事实来源；删了随时可再生成。
  ③ **不改 schema**：`log/**` 与 `cursor/**` 的字段集**一个都不动** ⇒ 不构成通道变更。
  ④ ★ **三态**：算不出来的，页面上写「不可判」，**不写 0**（0 是"算过且为零"，与"没得算"不同）。

用法:
  xdom-directory.py                    # 打印 Markdown 目录页（默认读本机板）
  xdom-directory.py --board central    # 读中枢板
  xdom-directory.py --json             # 机器可读
  xdom-directory.py --selftest         # 正控 + 负控 + 拆分控（合成夹具，不碰真板）
"""

__version__ = "0.2.0"

import argparse
import json
import sys
import urllib.request

BOARDS = {"local": "http://127.0.0.1:8792",
          "central": "http://xingqiao.meetfunbp.com:8792"}
NS = "notes/xdom"
LOG_PREFIX = NS + "/log/"
CUR_PREFIX = NS + "/cursor/"
_NO_BALL = (None, "", "none")


# ═══ 取数（唯一外部依赖：一次 GET，list 里 value 内联）═══
def fetch_list(base, prefix, timeout=40):
    """GET <base>/<prefix> ⇒ {key: value}。★ 只读。"""
    with urllib.request.urlopen(f"{base}/{prefix}", timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    lst = d.get("list", d)
    return {k: (v.get("value", v) if isinstance(v, dict) else v) for k, v in lst.items()}


def _ref_class(r):
    """一条 ref 指向什么：本邮箱的信键 / 仓库内文件路径 / 其他。"""
    if not isinstance(r, str) or not r:
        return "other"
    if r.startswith(LOG_PREFIX):
        return "letter"
    if "/" in r or r.endswith((".md", ".py", ".json", ".sh")):
        return "path"
    return "other"


# ═══ 聚合（纯函数 ★ 自检就测它，不测网络）═══
def build_index(logs, cursors):
    """⇒ {posts[], owed[], threads[], threading{}, unread{}, totals{}}。

    ★ 时间序一律用**键序**（键前缀 `%Y%m%dT%H%M%S`）⇒ 不依赖各板 ts 解析差异。
    """
    keys = sorted(k for k in logs if k.startswith(LOG_PREFIX))
    posts, ref_cls, topics = [], {"letter": 0, "path": 0, "other": 0}, {}
    for k in keys:
        m = logs[k] or {}
        topic = m.get("topic") or "(无题)"
        rr = bool(m.get("reply_required"))
        ball = m.get("ball")
        requires = rr and ball not in _NO_BALL
        for r in (m.get("ref") or []):
            ref_cls[_ref_class(r)] += 1
        topics[topic] = topics.get(topic, 0) + 1
        posts.append({"key": k, "ts": m.get("ts"), "from": m.get("from"), "to": m.get("to"),
                      "topic": topic, "ball": ball, "reply_required": rr,
                      "requires_reply": requires, "subject": m.get("subject") or ""})

    owed = [p for p in posts if p["requires_reply"]]
    reused = {t: n for t, n in topics.items() if n >= 2}

    unread = {}
    for ck, cm in (cursors or {}).items():
        party = ck[len(CUR_PREFIX):] if ck.startswith(CUR_PREFIX) else ck
        upto = (cm or {}).get("upto")
        unread[party] = {"upto": upto,
                         "unread": sum(1 for p in posts
                                       if p["to"] == party and (upto is None or p["key"] > upto))}

    return {
        "posts": posts, "owed": owed,
        "threads": sorted(({"topic": t, "posts": n} for t, n in topics.items()),
                          key=lambda x: (-x["posts"], x["topic"])),
        "threading": {"topics": len(topics), "topics_reused": len(reused),
                      "ref_edges_to_letters": ref_cls["letter"],
                      "ref_to_paths": ref_cls["path"], "ref_other": ref_cls["other"]},
        "unread": unread,
        "totals": {"posts": len(posts), "requires_reply": len(owed),
                   "parties": sorted({p["from"] for p in posts} | {p["to"] for p in posts})},
    }


# ═══ 渲染 ═══
def render_md(idx, board):
    T, TH = idx["totals"], idx["threading"]
    L = ["# 跨域邮箱 · 目录页（只读派生）", "",
         f"> 板源 `{board}` · **{T['posts']} 楼** · 要求回复的楼 **{T['requires_reply']}** · "
         f"参与方 {'/'.join(T['parties'])}",
         "> ★ 本页由 `notes/xdom/log/**` **派生**，不新增事实；"
         "★ `log/**` 与 `cursor/**` 的**字段集未被改动**；★ 本页**不写任何键**。", ""]

    L += ["## 〇、★ 三个读数 —— 第三个【算不出来】，不许写成 0", "",
          "| 读数 | 值 | 口径 |", "|---|---|---|",
          f"| 楼数 | **{T['posts']}** | `{LOG_PREFIX}**` 的键数 |",
          f"| **要求回复**的楼 | **{T['requires_reply']}** | `reply_required=true ∧ ball ∉ {{none,空}}` |",
          "| ★ **现在还欠谁一句** | ★ **不可判** | 需**回复链**（`ref` 指向信键）才能把「要求回复」降级为「已回」——"
          f" 实测该链只有 **{TH['ref_edges_to_letters']}** 条边（见 §二） |", ""]

    L += ["## 一、逐封账目（时间倒序 · 事实，不是推断）", "",
          "| 楼（键尾） | 时间 | from→to | 球 | **要求回** | 标题 |", "|---|---|---|---|---|---|"]
    for p in reversed(idx["posts"]):
        L.append(f"| `{p['key'][len(LOG_PREFIX):]}` | {p['ts']} | {p['from']}→{p['to']} | "
                 f"{p['ball']} | {'★ **是**' if p['requires_reply'] else '否'} | {p['subject'][:44]} |")
    L.append("")
    L.append("> ★ 「要求回=是」**不等于**「现在还欠」—— 前者是这封的属性，后者要看后面有没有人回过。"
             "本页**只印前者**。")
    L.append("")

    L += ["## 二、线的载体（★ 为什么 §〇 第三条算不出来）", "",
          "| 读数 | 值 | 说明 |", "|---|---|---|",
          f"| topic 总数 | {TH['topics']} | |",
          f"| **被 ≥2 楼复用的 topic** | **{TH['topics_reused']}** | 0 ⇒ 按 topic 分帖会退化成"
          f" {TH['topics']} 个单楼帖，**不提供任何结构** |",
          f"| **指向本邮箱信键的 `ref` 边** | **{TH['ref_edges_to_letters']}** | 这才是「回复链」的载体；"
          "边数太少 ⇒「欠谁」不可算 |",
          f"| `ref` 指向仓库文件路径（非信） | {TH['ref_to_paths']} | 是「引用了哪份文件」，不是「回了哪封信」 |",
          f"| `ref` 其他 | {TH['ref_other']} | |", ""]

    L += ["## 三、水位（未读）", "", "| 参与方 | 水位 up to | 未读 |", "|---|---|---|"]
    for p, u in sorted(idx["unread"].items()):
        L.append(f"| `{p}` | `{u['upto']}` | {u['unread']} |")
    L.append("")
    return "\n".join(L)


# ═══ 自检（正控 / 负控 / 拆分控 ★ 且经变异证明会变红）═══
def _fixture():
    """基础夹具：t1 两楼（第二楼把球交给 ext ⇒ 欠 ext 一句）· t2 通报（收口）。"""
    logs = {
        LOG_PREFIX + "20261010T100000-ext-t1-a": {"topic": "t1", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T10:00:00", "ball": "int",
                                                  "reply_required": True, "subject": "第一封", "ref": []},
        LOG_PREFIX + "20261010T110000-int-t1-b": {"topic": "t1", "from": "int", "to": "ext",
                                                  "ts": "2026-10-10T11:00:00", "ball": "ext",
                                                  "reply_required": True, "subject": "回第一封", "ref": []},
        LOG_PREFIX + "20261010T120000-ext-t2-c": {"topic": "t2", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T12:00:00", "ball": "none",
                                                  "reply_required": False, "subject": "通报", "ref": []},
    }
    cursors = {CUR_PREFIX + "ext": {"upto": LOG_PREFIX + "20261010T110000-int-t1-b", "party": "ext"}}
    return logs, cursors


def _fixture_ball():
    """★ 专为「球权 ∧ 回复要求」两条子判据造的夹具。

    上面那份**不具区分力**：t2 是 `ball="none" ∧ reply_required=False`，两条子判据**同时为假**
    ⇒ 变异其中任一条，结果照旧 ⇒ 控照绿。这里把两条各自单独拉出来压。
    ★ 这份夹具是**变异测试逼出来的**，见同目录 probe/。
    """
    return {
        # t3：球交给 int，但发信方【明说勿回】⇒ 应判【不要求回复】
        LOG_PREFIX + "20261010T200000-ext-t3-a": {"topic": "t3", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T20:00:00", "ball": "int",
                                                  "reply_required": False, "subject": "知会勿回", "ref": []},
        # t4：要求回复，但【球在 none】（本方收口陈述）⇒ 谁也不欠
        LOG_PREFIX + "20261010T210000-ext-t4-a": {"topic": "t4", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T21:00:00", "ball": "none",
                                                  "reply_required": True, "subject": "收口陈述", "ref": []},
    }, {}


def _fixture_ref():
    """★ 专为 ref 分类造的夹具：1 条指向信键 + 1 条指向文件路径 + 1 条指其他。"""
    return {
        LOG_PREFIX + "20261010T220000-ext-t5-a": {"topic": "t5", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T22:00:00", "ball": "none",
                                                  "reply_required": False, "subject": "回信",
                                                  "ref": [LOG_PREFIX + "20261010T100000-ext-t1-a"]},
        LOG_PREFIX + "20261010T230000-ext-t6-a": {"topic": "t6", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T23:00:00", "ball": "none",
                                                  "reply_required": False, "subject": "引文件",
                                                  "ref": ["docs/some.md", "tools/x.py:66"]},
        LOG_PREFIX + "20261011T000000-ext-t7-a": {"topic": "t7", "from": "ext", "to": "int",
                                                  "ts": "2026-10-11T00:00:00", "ball": "none",
                                                  "reply_required": False, "subject": "空引",
                                                  "ref": ["bareword"]},
    }, {}


def selftest():
    ok = fail = 0

    def chk(cond, name):
        nonlocal ok, fail
        print(("  ✅ " if cond else "  ❌ ") + name)
        ok += bool(cond)
        fail += (not cond)

    def by(logs, cur=None):
        return {p["key"]: p for p in build_index(logs, cur or {})["posts"]}

    logs, cursors = _fixture()
    ix = build_index(logs, cursors)
    P = by(logs)
    chk(ix["totals"]["posts"] == 3, "正控：3 楼")
    chk(ix["threading"]["topics"] == 2, "正控：2 个 topic")
    chk(ix["totals"]["requires_reply"] == 2, "正控：要求回复的楼 = 2（t1 两楼）")
    chk(P[LOG_PREFIX + "20261010T120000-ext-t2-c"]["requires_reply"] is False,
        "正控：t2（ball=none ∧ 不要求回）⇒ 不要求回复")
    chk(ix["unread"]["ext"]["unread"] == 0, "正控：ext 水位已到 t1 第 2 楼 ⇒ 未读 0")

    # 负控 1：打乱输入顺序 ⇒ 楼序仍按【键序】
    rev = dict(reversed(list(logs.items())))
    chk(list(by(rev))[-1].endswith("t2-c"), "★ 负控：打乱输入 ⇒ 末楼仍按键序为 t2-c（不被输入序带偏）")

    # 负控 2：加一封【不要求回】的信 ⇒ 要求回复的楼数不变（证明这是真数的，不是恒等于楼数）
    logs2 = dict(logs, **{LOG_PREFIX + "20261010T130000-int-t8-d": {
        "topic": "t8", "from": "int", "to": "ext", "ts": "2026-10-10T13:00:00",
        "ball": "none", "reply_required": False, "subject": "收口", "ref": []}})
    chk(build_index(logs2, cursors)["totals"]["requires_reply"] == 2,
        "★ 负控：加一封不要求回的信 ⇒ 要求回复数仍为 2（不是恒等于楼数）")

    # 负控 3：水位退回第一楼 ⇒ 未读必须变 1
    cur2 = {CUR_PREFIX + "ext": {"upto": LOG_PREFIX + "20261010T100000-ext-t1-a", "party": "ext"}}
    chk(build_index(logs, cur2)["unread"]["ext"]["unread"] == 1,
        "★ 负控：水位退回第一楼 ⇒ 未读=1（证明未读计数是真算的）")

    # ★★ 拆分控：把「球权」「回复要求」两条子判据各自单独压住
    B = by(*_fixture_ball())
    chk(B[LOG_PREFIX + "20261010T200000-ext-t3-a"]["requires_reply"] is False,
        "★ 拆分控：球在 int 但【明说勿回】⇒ 不要求回复")
    chk(B[LOG_PREFIX + "20261010T210000-ext-t4-a"]["requires_reply"] is False,
        "★ 拆分控：要求回但【球在 none】⇒ 不要求回复（谁也不欠）")

    # ★★ ref 分类控：证明「回复链」这个读数真在数东西
    R = build_index(*_fixture_ref())["threading"]
    chk(R["ref_edges_to_letters"] == 1, "★ ref 控：指向信键的边 = 1")
    chk(R["ref_to_paths"] == 2, "★ ref 控：指向文件路径的边 = 2（docs/some.md · tools/x.py:66）")
    chk(R["ref_other"] == 1, '★ ref 控：裸词 "bareword" 归 other = 1')

    # ★★ topic 复用控：0 与 >0 两种都要能出
    chk(build_index(logs, cursors)["threading"]["topics_reused"] == 1,
        "★ topic 控：夹具里 t1 有 2 楼 ⇒ 被复用 topic 数 = 1")

    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


def main():
    ap = argparse.ArgumentParser(description="跨域邮箱只读目录页生成器")
    ap.add_argument("--board", default="local", choices=sorted(BOARDS))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    base = BOARDS[a.board]
    logs = fetch_list(base, LOG_PREFIX)
    try:
        cursors = fetch_list(base, CUR_PREFIX)
    except Exception:
        cursors = {}
    idx = build_index(logs, cursors)
    print(json.dumps(idx, ensure_ascii=False, indent=1) if a.json
          else render_md(idx, a.board))
    return 0


if __name__ == "__main__":
    sys.exit(main())
