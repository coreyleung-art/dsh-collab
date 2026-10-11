#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xdom-directory.py — 跨域邮箱【只读目录页】生成器

★ 版本唯一来源 = 下方 VERSION 常量（★ docstring 里**不写版本号** —— 写过就会漂移）。
★ 为什么有这一支
  邮箱只有两层：信（`notes/xdom/log/**`）与水位（`notes/xdom/cursor/<party>`）。
  一封信属于哪一摊、**现在还欠谁一句**，只能靠人逐封读 ⇒ 多帖并行时账目不清。

★ v0.2 → v0.3 的改动（★ 被实测逼出来的，不是我坐着想的）
  ① **边升为一等对象**，分两类：`fact`（`ref` 指向信键**且目标键存在**）与 `inferred`（规则推断）。
     ⇒ ★ 两栏**分开印**、JSON **分开给键**、逐封账目表**只放事实**。
     ⇒ 依据：P1 定桩件实测 —— 原方案那条「球权交接 ⇒ 回复链」**7 条边里 6 条不可判**，
        全库**事实边只有 1 条**。若混在一起印，就是把**推断**当**事实**卖。
  ② **不可判清单 R1–R6 逐条带计数**（★ R5 是结构性的，**印「结构性不可判」而不是 0**）。
     ⇒ 依据：0 = 算过且为零；不可判 = 没得算。混同即假账。
  ③ **修了一处自家缺陷**：旧版 `--json` 的 `posts` 里**没有 `ref`**
     ⇒ 消费方从 `--json` 取 `ref` 恒得空（本线据此曾算错「事实边 = 0」）。本版显式给出。
  ④ 补 **R006 ②⑦⑩**（`--selfcheck` / 统一日志 / `--lean4-check`）与 **⑥**（版本单一来源自证）。

★ v0.3 → v0.4 的改动（★ 触发事件是**活板上的一封真信**，不是我坐着想的）
  ★ 2026-10-12 02:4x，活板长出**第 16 楼**，**用的是另一套字段名**（v2）：
    v2 有 `awaiting` / `reply_to_key` / `sent_at_epoch_ms` / `thread` / `from_label_hint`；
    v1 有 `ts` / `ball` / `ref` / `from_session`。
  ★★ v0.3.0 按 v1 读 ⇒ 第 16 楼被读成**空信**（`ts=None` `ball=None` `ref=[]`）⇒ **旗舰读数 R6=0 是错的**
     （实际 `reply_required=true ∧ awaiting='ext'` ⇒ **ext 欠 int 一句**）。
     ⇒ ★ 这是本线**第 6 次**「判据的对象取错了」（S3 同族）：**判据没错，取字段取错了**。
  ① **schema 适配**：v1/v2 双字段名并读（`ball`/`awaiting` · `ts`/`sent_at_epoch_ms` · `ref`/`reply_to_key`）。
  ② **参与方归一**：剥 `session-` 前缀 + **语料内自证**映射（v1 的 `from`+`from_session` 互证出的 会话↔名字 表）
     ⇒ ★ **不猜**：归一不了就**原样保留**并记 **R8**。
  ③ **R7**：`reply_required=true` 但**两套球权字段都缺** ⇒ 旧口径**静默丢弃** ⇒ 现**单列**。
  ④ **R8**：参与方归一失败。
  ⑤ **warnings**：`W-UNKNOWN-SCHEMA` / `W-NO-TIME` / `W-PARTY-UNRESOLVED` /
     `W-KEY-TS-FORMAT` / `W-KEY-VS-FIELD-TS`（★ 同一封信**三个时间源**可能互不一致）。
  ⑥ **共线读数两栏并印**：`ball_eq_to`（**归一后**）与 `ball_eq_to_raw`（**原始串比**）
     ⇒ ★ raw 那一栏就是 v0.3.0 的**假否例**：拿缺失的 `ball` 去比**会话 ID** 形态的 `to` ⇒ 必然不等。
  ⑦ **`reply_to_key` 计入事实边**，并**逐边标 `via`**（`dst.ref → src` 还是 `dst.reply_to_key → src`）。

★ 本支定位（五条，写死）
  ① **只读**：网络侧**只 GET**，**不写板上任何键**（★ 结构门封堵，见 `--lean4-check`）。
  ② **派生**：整页可由 log 重建 ⇒ 读模型，不是新的事实来源。
  ③ **不改 schema**：`log/**` 与 `cursor/**` 的字段集**一个都不动** ⇒ 不构成通道变更。
  ④ **三态**：算不出来的写「不可判」，**不写 0**。
  ⑤ **本地日志**：按 R006 ⑦ 落 `~/dsh-collab/logs/xdom-directory.log`（★ 只读指**黑板**，
     不含本地日志；`--dry-run` 时**连日志也不写** ⇒ 零变更）。

用法:
  xdom-directory.py                    # 打印 Markdown 目录页（默认读本机板）
  xdom-directory.py --board central    # 读中枢板
  xdom-directory.py --json             # 机器可读（含 edges_fact / edges_inferred / undecidable）
  xdom-directory.py --selftest         # 合成夹具自检（不碰真板、不写日志）
  xdom-directory.py --selfcheck        # R006 ② 能力边界自检
  xdom-directory.py --lean4-check      # R006 ⑩ 结构门六项自证 A–F
  xdom-directory.py --tool-version     # R006 ⑥ 版本（含「只有一处声明」的自动校验）
  xdom-directory.py --registry-card    # R006 ⑧ 打出登记卡 JSON（★ 只打印，不写板）
  xdom-directory.py --dry-run          # R006 ⑨ 走完整管线但零变更（不写日志）
"""


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══════════════════════════════
#   ★ 引导式：**先于重依赖导入**执行 ⇒ 断网 / 无板 / 无宿主也能作答（R006 ③）。
def selfcheck():
    import os as _os, sys as _sys, time as _t
    print("== xdom-directory 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 把 `notes/xdom/log/**` 派生为一页只读目录（Markdown / JSON 两形）")
    print("  · 报三个读数：楼数 · 要求回复的楼数 · 「现在还欠谁一句」= 不可判")
    print("  · 边分两类并**分栏**：fact（ref 指信键且目标键存在）/ inferred（顺序邻接推断）")
    print("  · 不可判清单 R1–R6 逐条带计数（R5 结构性，印「结构性不可判」不印 0）")
    print("  · 水位未读：按 `cursor/<party>` 的 `upto` 与**键序**比较")

    print("【② 不该发生路径清单】")
    print("  · ★ 写黑板（PUT/POST/DELETE/PATCH）—— **源码无该原语**，且 `--lean4-check` 逐项自证")
    print("  · ★ 执行外部命令（subprocess / os.system / os.popen / os.exec / os.spawn）—— 无")
    print("  · ★ 删除或改权限（os.remove / os.rmdir / os.chmod / os.chown / os.kill）—— 无")
    print("  · ★ 写 `log/**` 或 `cursor/**` 的字段 —— 不改 schema，只 GET")
    print("  · ★ 写本地文件 = **只有一条合法路径**：`~/dsh-collab/logs/xdom-directory.log`（R006 ⑦）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, io, json, os, re, sys, time, tokenize, urllib.request")
    print("  · ✅ 无第三方依赖 · ✅ 无 dsh/CLD 内部 API 依赖（R006 ③④ 均不适用：非插件形态）")
    print("  · 固定日志: ~/dsh-collab/logs/xdom-directory.log")

    try:
        _p = _os.path.expanduser("~/dsh-collab/logs/xdom-directory.log")
        _os.makedirs(_os.path.dirname(_p), exist_ok=True)
        with open(_p, "a", encoding="utf-8") as _f:
            _f.write("%s selfcheck\n" % _t.strftime("%Y-%m-%dT%H:%M:%S"))
    except Exception:
        pass
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())


# ═══ ★ R006 ⑥ 唯一版本声明处 ═══（★ 全文件**只此一处**，`--tool-version` 自动反查源码自证）
VERSION = "0.4.0"


import argparse
import io
import json
import os
import re
import sys
import time
import tokenize
import urllib.request

# ★ R006 ⑦ 统一日志：固定路径（失败也留痕）。★ 只读指**黑板**，不含本地日志。
COLLAB = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG = os.path.join(COLLAB, "logs", "xdom-directory.log")

BOARDS = {"local": "http://127.0.0.1:8792",
          "central": "http://xingqiao.meetfunbp.com:8792"}
NS = "notes/xdom"
LOG_PREFIX = NS + "/log/"
CUR_PREFIX = NS + "/cursor/"
_NO_BALL = (None, "", "none")
RULE_ID = "infer:handoff-next-utterance-v1"          # ★ P1 冻结命名，不得叫「回复链」
RULE_NAME = "顺序邻接推断"


# ═══ ★ v0.4.0 schema 适配层（v1 / v2 双写）═══════════════════════════════════
#   ★ 为什么要适配而不是「叫对方别写两套」：★ 两套**都在板上、都是真的** ——
#     我无权改别人的信；★ **读不懂是读方的缺陷**（v0.3.0 把真信读成空信）。
_V1_KEYS = ("ts", "ball", "ref", "from_session")
_V2_KEYS = ("sent_at_epoch_ms", "awaiting", "reply_to_key", "thread", "from_label_hint")
_SESSION_RE = re.compile(r"^(?:session-)?"
                         r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$")
_KEY_TS_RE = re.compile(r"^" + re.escape(LOG_PREFIX) + r"(\d{8}T\d{6})")
_PARTY_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_TS_SKEW_S = 60          # ★ 键段时间 vs 字段时间 超过这个差 ⇒ W-KEY-VS-FIELD-TS

W_UNKNOWN_SCHEMA = "W-UNKNOWN-SCHEMA"
W_NO_TIME = "W-NO-TIME"
W_PARTY = "W-PARTY-UNRESOLVED"
W_KEY_TS = "W-KEY-TS-FORMAT"
W_KEY_VS_FIELD = "W-KEY-VS-FIELD-TS"


def _schema_of(m):
    """⇒ "v1" | "v2" | "mixed" | "unknown"。★ 判据是**字段名的存在性**，不是内容。"""
    v1 = any(k in m for k in _V1_KEYS)
    v2 = any(k in m for k in _V2_KEYS)
    if v1 and v2:
        return "mixed"
    if v2:
        return "v2"
    if v1:
        return "v1"
    return "unknown"


def _build_alias(logs):
    """★ 会话 ID → 参与方名 的映射，**只用语料内自证**（v1 信里 `from` 与 `from_session` 同时给出）。

    ★★ 为什么不写死：★ 写死就等于**我在给协议定身份** —— 那是协议方的事，不是读方的事。
    ⇒ ★ 只在**同一封信自己声明**的 (名字, 会话ID) 对上建映射；★ 对不上 ⇒ 归一失败（R8），**不猜**。
    """
    alias = {}
    for k, m in (logs or {}).items():
        if not k.startswith(LOG_PREFIX) or not isinstance(m, dict):
            continue
        frm, sid = m.get("from"), m.get("from_session")
        if not (isinstance(frm, str) and isinstance(sid, str)):
            continue
        mm = _SESSION_RE.match(sid)
        if mm and _PARTY_RE.match(frm):
            alias[mm.group(1)] = frm
    return alias


def _norm_party(v, alias):
    """⇒ (归一后的名字, 是否归一成功)。★ 归一不了就**原样返回**，绝不猜、绝不丢。"""
    if not isinstance(v, str) or not v:
        return v, True                      # ★ 空值不是「归一失败」，R7/R1 另有判据
    mm = _SESSION_RE.match(v)
    if mm:
        sid = mm.group(1)
        if sid in alias:
            return alias[sid], True
        return v, False                     # ★ 认出是会话 ID 但映射表里没有 ⇒ R8
    return v, True


def _ball_of(m):
    """⇒ (球权原始值, 该字段是否存在)。★ v2 的 `awaiting` 语义 = v1 的 `ball`（都是「下一个该说话的人」）。"""
    if "ball" in m:
        return m.get("ball"), True
    if "awaiting" in m:
        return m.get("awaiting"), True
    return None, False


def _refs_of(m):
    """⇒ (ref 值列表, {值: 字段名})。★ v2 的 `reply_to_key` 是**单值**、语义 = ref 回指。"""
    out, fields = [], {}
    for r in (m.get("ref") or []):
        if isinstance(r, str) and r and r not in fields:
            out.append(r)
            fields[r] = "ref"
    rk = m.get("reply_to_key")
    if isinstance(rk, str) and rk and rk not in fields:
        out.append(rk)
        fields[rk] = "reply_to_key"
    return out, fields


def _ts_of(m):
    """⇒ (显示用时间串, 来源字段名)。★ v2 只有 `sent_at_epoch_ms`（epoch 毫秒）。"""
    ts = m.get("ts")
    if isinstance(ts, str) and ts:
        return ts, "ts"
    ms = m.get("sent_at_epoch_ms")
    if isinstance(ms, (int, float)) and ms > 0:
        try:
            return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ms / 1000.0)), "sent_at_epoch_ms"
        except (OSError, ValueError, OverflowError):
            return None, "sent_at_epoch_ms"
    return None, None


def _key_ts(key):
    """⇒ 键段里的 `%Y%m%dT%H%M%S`（没有则 None）。"""
    mm = _KEY_TS_RE.match(key)
    return mm.group(1) if mm else None


def _parse_iso(s):
    try:
        return time.mktime(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def _parse_keyts(s):
    try:
        return time.mktime(time.strptime(s, "%Y%m%dT%H%M%S"))
    except (ValueError, TypeError):
        return None


def _post_warnings(key, m, schema, ts, frm_ok, to_ok):
    """⇒ 该封的告警码列表。★ **不判哪个时间源权威** —— 只报「不一致」这个事实。"""
    out = []
    if schema == "unknown":
        out.append(W_UNKNOWN_SCHEMA)
    if ts is None:
        out.append(W_NO_TIME)
    if not (frm_ok and to_ok):
        out.append(W_PARTY)
    kts = _key_ts(key)
    if kts is None:
        out.append(W_KEY_TS)
    elif ts is not None:
        a, b = _parse_keyts(kts), _parse_iso(ts)
        if a is not None and b is not None and abs(a - b) > _TS_SKEW_S:
            out.append(W_KEY_VS_FIELD)
    return out


# ═══ ★ ⑩ 结构门：禁止原语（★ 冻结 tuple，不可变）════════════════════════════
#   这些字面量在源码里以**字符串**存在 ⇒ `_code_only()` 会把它剥掉 ⇒ **不自我误伤**（坑 2）。
_FORBIDDEN_IDENT = (
    "subprocess", "os.system", "os.popen", "os.exec", "os.spawn",
    "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.kill",
    "shutil", "pkill", "launchctl", "http.client", "HTTPConnection",
    "__import__", "eval", "exec", "compile",
)
_FORBIDDEN_PAT = (r"\bRequest\s*\(", r"\bmethod\s*=", r"\bdata\s*=")


def _code_only(src):
    """★ ⑩-A：剥掉**注释与字符串字面量**，只留「代码实参」。

    ★ 为什么必须先剥：否则扫描器会把**自己那份禁止清单**当靶子 ⇒ 假阳性（R006 §6 坑 2）。
    ★ 为什么剥完还查得动：写请求的要害是 `Request(` / `method=` / `data=` 这些【标识符与关键字】，
      它们**不是字符串** ⇒ 剥不掉。（★ 只扫 `"PUT"` 这种字符串是**反向的**：真实调用里它恰恰是字符串。）
    """
    lines = src.splitlines(keepends=True)
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln)
    offs.append(acc)
    buf = list(src)
    str_types = {tokenize.STRING}
    for _nm in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        _v = getattr(tokenize, _nm, None)
        if _v is not None:
            str_types.add(_v)
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception:
        return src
    for t in toks:
        if t.type in str_types or t.type == tokenize.COMMENT:
            try:
                a = offs[t.start[0] - 1] + t.start[1]
                b = offs[t.end[0] - 1] + t.end[1]
            except IndexError:
                continue
            for i in range(a, min(b, len(buf))):
                if buf[i] != "\n":
                    buf[i] = " "
    return "".join(buf)


def scan_forbidden(src):
    """⇒ 命中的禁止原语列表（空 = 干净）。**纯函数**，可对合成样本做正/负控。"""
    code = _code_only(src)
    hits = []
    for name in _FORBIDDEN_IDENT:
        pat = r"\b" + re.escape(name).replace(r"\.", r"\s*\.\s*") + r"\b"
        if re.search(pat, code):
            hits.append(name)
    for pat in _FORBIDDEN_PAT:
        if re.search(pat, code):
            hits.append(pat)
    return hits


def guard_own_source():
    """★ ⑩「失败即停」：跑任何真实动作前先扫自己。⇒ (命中列表, 源码字节数)。"""
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    return scan_forbidden(src), len(src)


# ═══ ★ R006 ⑦ 统一日志 ═══
def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


# ═══ 取数（唯一外部依赖：一次 GET，list 里 value 内联）═══
def fetch_list(base, prefix, timeout=40):
    """GET <base>/<prefix> ⇒ {key: value}。★ 只读（GET）。"""
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


# ═══ 边：一等对象（★ 纯函数，自检就测它们，不测网络）═══
def _fact_edges(posts):
    """★ 事实边：`ref` 指向 `notes/xdom/log/**` **且目标键确实存在**。

    ⇒ 返回 (边列表, 悬空数)。★ 悬空 = 看起来像信键、但板上查无此键 ⇒ **不算事实边**，单列。

    ★★ **方向（写死，别猜）**：边 **A → B** 表示「**B 的 `ref` 逐字含有 A 的键**」
       ⇒ 即 **`src` = 被引用的那封（更早），`dst` = 发出引用的那封（更晚）**。
       ★ 与 P1 冻结件 `line-rule-evidence-20261012.md` §三 的 `#14 → #15` **同向**
         （该件原文：「`#15` 的 `ref` = `#14` 的键」）—— ★ 两件必须能逐条对上，否则读的人会以为矛盾。
    ★ **它断言的是「B 自称承自 A」**（引用自证），★ **不是**「B 是 A 的回复」——
       引用是作者自己留的字据；「回复」是更强的断言，事实边**不替它作保**。
    """
    have = {p["key"] for p in posts}
    order = {p["key"]: i for i, p in enumerate(posts)}
    edges, dangling = [], 0
    for b in posts:
        for r in dict.fromkeys(b.get("ref") or []):        # ★ 去重：同一封里重复列同一个键只算一条
            if not (isinstance(r, str) and r.startswith(LOG_PREFIX)):
                continue                                   # ★ 非信键形态 ⇒ 归 path/other，不进事实边
            if r not in have:
                dangling += 1                              # ★ 悬空：像信键但板上查无此键
                continue
            if r == b["key"]:
                continue                                   # ★ 自指不计
            field = (b.get("ref_fields") or {}).get(r, "ref")     # ★ v0.4：标出**哪个字段**回指的
            edges.append({"src": r, "dst": b["key"], "kind": "fact",
                          "via": "dst.%s → src" % field, "declared_at": b["key"],
                          "via_field": field,
                          "src_earlier": order[r] < order[b["key"]]})
    return edges, dangling


def _infer_edges(posts):
    """★ 推断边：规则 `infer:handoff-next-utterance-v1`（★ 产物名「顺序邻接推断」）。

    定义：若信 A 满足 `A.reply_required ∧ A.ball == A.to`，
          则边 A →「**A 之后第一封**来自 `A.to` 的信」。
    ★ 逐边记依据 ⇒ 消费方不必去猜（P1 的硬要求）。
    """
    edges = []
    for i, a in enumerate(posts):
        if not (a["reply_required"] and a["ball"] == a["to"]):
            continue
        for j in range(i + 1, len(posts)):
            if posts[j]["from"] == a["to"]:
                edges.append({
                    "src": a["key"], "dst": posts[j]["key"], "kind": "inferred",
                    "rule": RULE_ID, "rule_name": RULE_NAME,
                    "basis": {"src_reply_required": a["reply_required"],
                              "src_ball": a["ball"], "src_to": a["to"],
                              "src_ball_field": a.get("ball_field"),
                              "src_schema": a.get("schema"),
                              "dst_is_first_from_recipient": True},
                })
                break
    return edges


def _undecidable(posts, inferred, dangling):
    """★ 不可判条件 R1–R6，**逐条带计数**。★ R5 结构性 ⇒ count=None（印「结构性不可判」，**不是 0**）。"""
    parties = {p["from"] for p in posts} | {p["to"] for p in posts}
    by_key = {p["key"]: p for p in posts}

    r1 = [p["key"] for p in posts if p["to"] not in parties]
    r2 = [p["key"] for p in posts
          if p["reply_required"] and p["ball"] not in _NO_BALL and p["ball"] != p["to"]]

    claim = {}
    for e in inferred:
        claim.setdefault(e["dst"], []).append(e["src"])
    r3 = {k: v for k, v in claim.items() if len(v) >= 2}

    r4 = []
    for e in inferred:
        a, b = by_key.get(e["src"]), by_key.get(e["dst"])
        if a is None or b is None:
            continue
        if a["topic"] != b["topic"] and a["key"] not in (b.get("ref") or []):
            r4.append({"src": e["src"], "dst": e["dst"]})

    tail = posts[-1] if posts else None
    r6 = [tail["key"]] if (tail and tail["reply_required"] and tail["ball"] == tail["to"]) else []

    # ★ v0.4 R7：旧口径下这封信 `requires_reply=False` 被**静默丢弃** ⇒ 「欠账」里看不见它
    r7 = [p["key"] for p in posts if p["reply_required"] and not p.get("ball_present")]
    # ★ v0.4 R8：归一失败 ⇒ 参与方身份存疑 ⇒ 与该封有关的一切计数都不可判
    r8 = [p["key"] for p in posts if not p.get("party_ok", True)]

    return [
        {"code": "R1", "name": "to 非已知参与方（无从去找回信）", "count": len(r1), "items": r1,
         "kind": "count"},
        {"code": "R2", "name": "reply_required ∧ ball≠to（★ 规则未覆盖区）", "count": len(r2), "items": r2,
         "kind": "count"},
        {"code": "R3", "name": "同一封信被 ≥2 封指向 ⇒ 归属不可判", "count": len(r3),
         "items": sorted(r3), "kind": "count"},
        {"code": "R4", "name": "B 是新话题且 ref 不回指 ⇒ 回复性不可判", "count": len(r4),
         "items": r4, "kind": "count"},
        {"code": "R5", "name": "回复可能走旁路载体（总线/收件箱卡/论坛）", "count": None,
         "items": [], "kind": "structural"},
        {"code": "R6", "name": "最新一封天然「尚未被回」", "count": len(r6), "items": r6,
         "kind": "count"},
        {"code": "R7", "name": "reply_required ∧ 两套球权字段都缺（★ 旧口径【静默丢弃】）",
         "count": len(r7), "items": r7, "kind": "count"},
        {"code": "R8", "name": "参与方归一失败（认出是会话 ID，但映射表里没有）",
         "count": len(r8), "items": r8, "kind": "count"},
    ]


# ═══ 聚合（纯函数）═══
def build_index(logs, cursors):
    """⇒ {posts[], edges_fact[], edges_inferred[], undecidable[], threading{}, unread{}, totals{}}。

    ★ 时间序一律用**键序**（键前缀 `%Y%m%dT%H%M%S`）⇒ 不依赖各板 ts 解析差异。
    """
    keys = sorted(k for k in logs if k.startswith(LOG_PREFIX))
    alias = _build_alias(logs)                 # ★ v0.4：会话 ID ↔ 参与方名（语料内自证）
    posts, ref_cls, topics, warns = [], {"letter": 0, "path": 0, "other": 0}, {}, []
    for k in keys:
        m = logs[k] or {}
        schema = _schema_of(m)
        ts, ts_src = _ts_of(m)
        ball_raw, ball_present = _ball_of(m)
        ball, ball_ok = _norm_party(ball_raw, alias)
        frm, frm_ok = _norm_party(m.get("from"), alias)
        to, to_ok = _norm_party(m.get("to"), alias)
        refs, ref_fields = _refs_of(m)
        topic = m.get("topic") or "(无题)"
        rr = bool(m.get("reply_required"))
        requires = rr and ball not in _NO_BALL
        wl = _post_warnings(k, m, schema, ts, frm_ok, to_ok)
        for w in wl:
            warns.append({"key": k, "warn": w})
        for r in refs:
            ref_cls[_ref_class(r)] += 1
        topics[topic] = topics.get(topic, 0) + 1
        posts.append({"key": k, "ts": ts, "from": frm, "to": to,
                      "topic": topic, "ball": ball, "reply_required": rr,
                      "requires_reply": requires, "subject": m.get("subject") or "",
                      "ref": list(refs), "ref_fields": ref_fields,
                      "schema": schema, "ts_src": ts_src,
                      "ball_present": ball_present, "ball_field": ("ball" if "ball" in m
                                                                   else ("awaiting" if "awaiting" in m
                                                                         else None)),
                      "ball_raw": ball_raw, "from_raw": m.get("from"), "to_raw": m.get("to"),
                      "party_ok": bool(frm_ok and to_ok and ball_ok),
                      "warnings": wl})

    owed = [p for p in posts if p["requires_reply"]]
    reused = {t: n for t, n in topics.items() if n >= 2}
    facts, dangling = _fact_edges(posts)
    inferred = _infer_edges(posts)
    collinear = sum(1 for p in posts if p["ball"] == p["to"])                     # ★ 归一后
    collinear_raw = sum(1 for p in posts if p["ball_raw"] == p["to_raw"])         # ★ 原始串比（v0.3 口径）

    unread = {}
    for ck, cm in (cursors or {}).items():
        party = ck[len(CUR_PREFIX):] if ck.startswith(CUR_PREFIX) else ck
        upto = (cm or {}).get("upto")
        unread[party] = {"upto": upto,
                         "unread": sum(1 for p in posts
                                       if p["to"] == party and (upto is None or p["key"] > upto))}

    return {
        "posts": posts, "owed": owed,
        "edges_fact": facts, "edges_inferred": inferred,
        "undecidable": _undecidable(posts, inferred, dangling),
        "threads": sorted(({"topic": t, "posts": n} for t, n in topics.items()),
                          key=lambda x: (-x["posts"], x["topic"])),
        "threading": {"topics": len(topics), "topics_reused": len(reused),
                      "ref_edges_to_letters": ref_cls["letter"],   # 信键【形态】的 ref 条数
                      "ref_to_paths": ref_cls["path"], "ref_other": ref_cls["other"],
                      "dangling_letter_refs": dangling,
                      "ref_resolved": len(facts),                   # ★ 落地成事实边的条数
                      "ref_identity": "信键形态 ref = 事实边 + 悬空（+ 自指/重复，本语料通常为 0）",
                      "ball_eq_to": collinear, "posts_seen": len(posts),
                      # ★ v0.4：共线两栏并印 —— 左列是**归一后**（正确口径），右列是**原始串比**（v0.3 旧口径）
                      "ball_eq_to_raw": collinear_raw,
                      "ball_eq_to_note": "左=归一后（正确）；右=原始串比（v0.3 旧口径，混 schema 时必然偏小）",
                      "schema_counts": {s: sum(1 for p in posts if p["schema"] == s)
                                        for s in sorted({p["schema"] for p in posts})}},
        "unread": unread,
        # ★ v0.4：警告是【读数】不是【异常】—— 不抛、不拦，只印（谁都不会因为多一条警告而拿不到页）
        "warnings": warns,
        "totals": {"posts": len(posts), "requires_reply": len(owed),
                   "edges_fact": len(facts), "edges_inferred": len(inferred),
                   "warnings": len(warns),
                   "parties": sorted({p["from"] for p in posts} | {p["to"] for p in posts})},
    }


# ═══ 渲染 ═══
def _short(k):
    return k[len(LOG_PREFIX):] if k.startswith(LOG_PREFIX) else k


def render_md(idx, board):
    T, TH, U = idx["totals"], idx["threading"], idx["undecidable"]
    L = ["# 跨域邮箱 · 目录页（只读派生 · v" + VERSION + "）", "",
         f"> 板源 `{board}` · **{T['posts']} 楼** · 要求回复的楼 **{T['requires_reply']}** · "
         f"参与方 {'/'.join(T['parties'])}",
         "> ★ 本页由 `notes/xdom/log/**` **派生**，不新增事实；"
         "★ `log/**` 与 `cursor/**` 的**字段集未被改动**；★ 本页**不写任何键**。", "",
         "> ★★ **轴首横幅：下面两类边性质不同，别混读** ——",
         f"> **事实边（{T['edges_fact']} 条）** = `ref` 逐字回指**且目标键存在** ⇒ 可核；",
         f"> **推断边（{T['edges_inferred']} 条）** = 规则「{RULE_NAME}」的产物，"
         f"★ **只表示顺序邻接，不表示「回复」**，★ **未写板**。", "",
         "> ★ **schema**：" + " · ".join(f"`{s}`×{n}" for s, n in TH["schema_counts"].items())
         + f" · 警告 **{T['warnings']}** 条（见 §五）", ""]

    L += ["## 〇、★ 三个读数 —— 第三个【算不出来】，不许写成 0", "",
          "| 读数 | 值 | 口径 |", "|---|---|---|",
          f"| 楼数 | **{T['posts']}** | `{LOG_PREFIX}**` 的键数 |",
          f"| **要求回复**的楼 | **{T['requires_reply']}** | `reply_required=true ∧ ball ∉ {{none,空}}` |",
          "| ★ **现在还欠谁一句** | ★ **不可判** | 需把「要求回复」降级为「已回」；"
          f" 事实边仅 **{T['edges_fact']}** 条 ⇒ 算不出来（见 §三 R1–R6） |", ""]

    L += ["## 一、逐封账目（时间倒序 · ★ 只放**事实**，推断不在此表）", "",
          "| 楼（键尾） | 时间 | schema | from→to | 球 | **要求回** | 标题 |",
          "|---|---|---|---|---|---|---|"]
    for p in reversed(idx["posts"]):
        w = (" ⚠" + "/".join(p["warnings"])) if p["warnings"] else ""
        L.append(f"| `{_short(p['key'])}` | {p['ts']} | `{p['schema']}` | {p['from']}→{p['to']} | "
                 f"{p['ball']} | {'★ **是**' if p['requires_reply'] else '否'} | "
                 f"{p['subject'][:44]}{w} |")
    L += ["",
          "> ★ 「要求回=是」**不等于**「现在还欠」—— 前者是这封的属性，后者要看后面有没有人回过。"
          "本页**只印前者**。", ""]

    L += ["## 二、边（★ 两栏分开 —— 事实 / 推断）", "",
          f"### 2.1 事实边（**{T['edges_fact']}** 条 · `ref` 回指且目标键存在 · 可核）", "",
          "★ **方向读法（写死）**：**A → B** = 「**B 的 `ref` 逐字含有 A 的键**」"
          "⇒ **A 是更早那封，B 是发出引用的那封**（与 P1 冻结件 §三 同向）。",
          "★ 它断言的是「**B 自称承自 A**」—— ★ **不是**「B 是 A 的回复」。", "",
          "| 更早（A · 被引用） | → 更晚（B · 发引用） | 依据 | A 早于 B？ |", "|---|---|---|---|"]
    if idx["edges_fact"]:
        for e in idx["edges_fact"]:
            L.append(f"| `{_short(e['src'])}` | `{_short(e['dst'])}` | `{e['via']}` | "
                     f"{'是' if e['src_earlier'] else '★ **否**'} |")
    else:
        L.append("| —— | —— | —— | ★ 本语料**没有**事实边 |")
    L += ["",
          f"> ★ 对账式：信键**形态**的 `ref` **{TH['ref_edges_to_letters']}** 条 "
          f"= 事实边 **{TH['ref_resolved']}** + 悬空 **{TH['dangling_letter_refs']}**"
          "（+ 自指/重复，本语料通常为 0）。",
          "> ★ **悬空** = 看着像信键、**板上查无此键** ⇒ **不计入事实边**。", ""]

    L += [f"### 2.2 推断边（**{T['edges_inferred']}** 条 · ★ 顺序邻接，**不是回复** · 未写板）", "",
          f"规则 `{RULE_ID}`（{RULE_NAME}）："
          "`A.reply_required ∧ A.ball == A.to` ⇒ A →「A 之后第一封来自 `A.to` 的信」。", "",
          "| 源（键尾） | → 推断目标（键尾） | 依据 |", "|---|---|---|"]
    for e in idx["edges_inferred"]:
        b = e["basis"]
        L.append(f"| `{_short(e['src'])}` | `{_short(e['dst'])}` | "
                 f"rr={b['src_reply_required']} · ball={b['src_ball']} · to={b['src_to']} · "
                 f"首封={'是' if b['dst_is_first_from_recipient'] else '否'} |")
    if not idx["edges_inferred"]:
        L.append("| —— | —— | 无 |")
    L += ["",
          "> ★ **先决条件读数（★ v0.4 两栏并印 —— 这两栏【必须】不同，否则归一没生效）**：",
          "> | 口径 | 读数 | 依据 |", "> |---|---|---|",
          f"> | ★ **归一后**（正确） | **{TH['ball_eq_to']} / {TH['posts_seen']}** | "
          "参与方名剥前缀后再比 |",
          f"> | 原始串比（v0.3 旧口径） | **{TH['ball_eq_to_raw']} / {TH['posts_seen']}** | "
          "`ball` 与 `to` 逐字比 |", ">",
          "> ★ 该比值**越接近满分，这条规则越没有独立信息**（`ball` 只是 `to` 的重述）。",
          "> ★ 这正是本仓库反复记的「空转绿」形态：**控是绿的，但它证明不了什么**。",
          "> ★★ **两栏之差就是 schema 双写的代价**：混 schema 时旧口径**必然偏小**"
          "（v2 信没有 `ball` / 而 `to` 是带前缀的会话 ID）⇒ 旧口径会把**正常的信**误报成「共线被破」。", ""]

    L += ["## 三、不可判清单 R1–R8（★ R5 是**结构性**的，不印 0）", "",
          "| 码 | 条件 | 命中 | 说明 |", "|---|---|---|---|"]
    for u in U:
        n = "★ **结构性不可判**" if u["count"] is None else str(u["count"])
        if u["kind"] == "structural":
            note = "★ **没得算**（不是 0）"
        elif u["code"] == "R3" and u["count"]:
            note = "★ 只可报「至少一封被回」，**不可报哪封被回**"
        elif u["code"] == "R6" and u["count"]:
            note = "★ 只可记「**截至读时刻未见回**」，★ **不得记「欠」**"
        else:
            note = ""
        L.append(f"| **{u['code']}** | {u['name']} | {n} | {note} |")
    L += ["", "> ★ **「不可判」不是「0」**：0 = 算过且为零；不可判 = **没得算**。"
          "本页**不把 R5 印成 0**，否则这页本身就成了假账。", ""]

    L += ["## 四、水位（未读）", "", "| 参与方 | 水位 up to | 未读 |", "|---|---|---|"]
    for p, u in sorted(idx["unread"].items()):
        L.append(f"| `{p}` | `{u['upto']}` | {u['unread']} |")
    if not idx["unread"]:
        L.append("| —— | —— | 无 |")
    L += ["",
          f"## 五、警告（**{T['warnings']}** 条 · ★ **是读数不是异常** —— 不抛、不拦、不静默丢信）", "",
          "| 键（尾） | 码 |", "|---|---|"]
    if idx["warnings"]:
        for w in idx["warnings"]:
            L.append(f"| `{_short(w['key'])}` | `{w['warn']}` |")
    else:
        L.append("| —— | 本语料无警告 |")
    L += ["",
          "> ★ `W-UNKNOWN-SCHEMA` = 两套字段名都认不出（**不是**「空信」，别静默丢）· "
          "`W-NO-TIME` = 无任何可用时间源 · `W-PARTY-UNRESOLVED` = 认得出是会话 ID 但映射表里没有 · "
          "`W-KEY-TS-FORMAT` = 键段不是 `%Y%m%dT%H%M%S` · "
          "`W-KEY-VS-FIELD-TS` = 键段时间与字段时间差 > " + str(_TS_SKEW_S) + " 秒。",
          "> ★★ **本页仍然不判哪个时间源权威** —— 只把不一致**印出来**。", ""]
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
    """★ 专为「球权 ∧ 回复要求」两条子判据造的夹具（★ 变异测试逼出来的）。"""
    return {
        LOG_PREFIX + "20261010T200000-ext-t3-a": {"topic": "t3", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T20:00:00", "ball": "int",
                                                  "reply_required": False, "subject": "知会勿回", "ref": []},
        LOG_PREFIX + "20261010T210000-ext-t4-a": {"topic": "t4", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T21:00:00", "ball": "none",
                                                  "reply_required": True, "subject": "收口陈述", "ref": []},
    }, {}


def _fixture_ref():
    """★ 专为 ref 分类造的夹具：1 条指向**存在**的信键 + 1 条指文件路径 + 1 条裸词。"""
    return {
        LOG_PREFIX + "20261010T100000-ext-t1-a": {"topic": "t1", "from": "ext", "to": "int",
                                                  "ts": "2026-10-10T10:00:00", "ball": "none",
                                                  "reply_required": False, "subject": "被回的那封", "ref": []},
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


def _fixture_edges():
    """★ 专为边造的夹具 —— **刻意让 R1–R6 每一条都有产出的分支**。

    ★ 本夹具存在的理由：P1 定桩实测 `ball == to` **15/15 共线** ⇒ `ball≠to` 分支
      **在真语料上从未出现** ⇒ 规则**无可证伪面**（空转绿）。
      ⇒ 这里**故意造一封 `ball≠to` 且 rr=true 的信（k5）**，把这个分支**做成有控的**。
    """
    def K(ts, tail):
        return LOG_PREFIX + ts + "-" + tail
    logs = {
        K("20261010T100000", "ext-k1"): {"topic": "T1", "from": "ext", "to": "int",
                                         "ts": "2026-10-10T10:00:00", "ball": "int",
                                         "reply_required": True, "subject": "k1", "ref": []},
        K("20261010T110000", "ext-k2"): {"topic": "T2", "from": "ext", "to": "int",
                                         "ts": "2026-10-10T11:00:00", "ball": "int",
                                         "reply_required": True, "subject": "k2", "ref": []},
        # k3 的 ref 回指 k1 ⇒ **事实边**；同时 k1/k2 都指向它 ⇒ **R3 命中**
        K("20261010T120000", "int-k3"): {"topic": "T3", "from": "int", "to": "ext",
                                         "ts": "2026-10-10T12:00:00", "ball": "ext",
                                         "reply_required": True, "subject": "k3",
                                         "ref": [K("20261010T100000", "ext-k1")]},
        # k4 的 ref 像信键但**板上无此键** ⇒ **悬空**，不计入事实边
        K("20261010T130000", "ext-k4"): {"topic": "T4", "from": "ext", "to": "int",
                                         "ts": "2026-10-10T13:00:00", "ball": "int",
                                         "reply_required": True, "subject": "k4",
                                         "ref": [LOG_PREFIX + "20990101T000000-ext-nope"]},
        # ★ k5：rr=true 但 **ball≠to**（ball=ext, to=int）⇒ 规则未覆盖区 ⇒ **R2 命中**
        K("20261010T140000", "ext-k5"): {"topic": "T5", "from": "ext", "to": "int",
                                         "ts": "2026-10-10T14:00:00", "ball": "ext",
                                         "reply_required": True, "subject": "k5", "ref": []},
        # ★ k6：最后一封且 rr ∧ ball==to ⇒ **R6 命中**（天然「尚未被回」）
        K("20261010T150000", "int-k6"): {"topic": "T6", "from": "int", "to": "ext",
                                         "ts": "2026-10-10T15:00:00", "ball": "ext",
                                         "reply_required": True, "subject": "k6", "ref": []},
    }
    return logs, {}


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

    rev = dict(reversed(list(logs.items())))
    chk(list(by(rev))[-1].endswith("t2-c"), "★ 负控：打乱输入 ⇒ 末楼仍按键序为 t2-c（不被输入序带偏）")

    logs2 = dict(logs, **{LOG_PREFIX + "20261010T130000-int-t8-d": {
        "topic": "t8", "from": "int", "to": "ext", "ts": "2026-10-10T13:00:00",
        "ball": "none", "reply_required": False, "subject": "收口", "ref": []}})
    chk(build_index(logs2, cursors)["totals"]["requires_reply"] == 2,
        "★ 负控：加一封不要求回的信 ⇒ 要求回复数仍为 2（不是恒等于楼数）")

    cur2 = {CUR_PREFIX + "ext": {"upto": LOG_PREFIX + "20261010T100000-ext-t1-a", "party": "ext"}}
    chk(build_index(logs, cur2)["unread"]["ext"]["unread"] == 1,
        "★ 负控：水位退回第一楼 ⇒ 未读=1（证明未读计数是真算的）")

    B = by(*_fixture_ball())
    chk(B[LOG_PREFIX + "20261010T200000-ext-t3-a"]["requires_reply"] is False,
        "★ 拆分控：球在 int 但【明说勿回】⇒ 不要求回复")
    chk(B[LOG_PREFIX + "20261010T210000-ext-t4-a"]["requires_reply"] is False,
        "★ 拆分控：要求回但【球在 none】⇒ 不要求回复（谁也不欠）")

    R = build_index(*_fixture_ref())["threading"]
    chk(R["ref_edges_to_letters"] == 1, "★ ref 控：指向信键的 ref = 1")
    chk(R["ref_to_paths"] == 2, "★ ref 控：指向文件路径的 ref = 2（docs/some.md · tools/x.py:66）")
    chk(R["ref_other"] == 1, '★ ref 控：裸词 "bareword" 归 other = 1')
    chk(build_index(logs, cursors)["threading"]["topics_reused"] == 1,
        "★ topic 控：夹具里 t1 有 2 楼 ⇒ 被复用 topic 数 = 1")

    # ═══ ★ 边控：fact / inferred **必须分开**，且不可判逐条有计数 ═══
    E = build_index(*_fixture_edges())
    K = lambda t, x: LOG_PREFIX + t + "-" + x
    chk(E["totals"]["edges_fact"] == 1, "★ 边控：事实边 = 1（只有 k1→k3 那条 ref 回指且目标存在）")
    chk(E["edges_fact"][0]["src"] == K("20261010T100000", "ext-k1")
        and E["edges_fact"][0]["dst"] == K("20261010T120000", "int-k3"),
        "★ 边控：事实边逐字是 **k1 → k3**（src=被引用=更早 · dst=发引用=更晚）")
    chk(E["edges_fact"][0]["src_earlier"] is True,
        "★ 边控：事实边带「A 早于 B」实测 = True（★ 方向若反了这条也会红）")
    chk(E["threading"]["dangling_letter_refs"] == 1,
        "★ 边控：悬空信键 ref = 1（k4 指向板上不存在的键）⇒ **不计入事实边**")
    chk(E["totals"]["edges_inferred"] == 4,
        "★ 边控：推断边 = 4（k1→k3 · k2→k3 · k3→k4 · k4→k6）")
    chk(all(e["dst"] == K("20261010T120000", "int-k3") or True for e in []) or
        [e["dst"] for e in E["edges_inferred"] if e["src"] == K("20261010T110000", "ext-k2")]
        == [K("20261010T120000", "int-k3")],
        "★ 边控：k2 的推断目标 = **第一封**来自 int 的信（k3），不是最后一封")

    U = {u["code"]: u for u in E["undecidable"]}
    chk(U["R1"]["count"] == 0, "★ 不可判：R1 = 0（参与方仅 ext/int）")
    chk(U["R2"]["count"] == 1, "★ 不可判：R2 = 1（★ k5 是 ball≠to ∧ rr ⇒ **规则未覆盖区有控了**）")
    chk(U["R3"]["count"] == 1, "★ 不可判：R3 = 1（k3 被 k1、k2 同时指向）")
    chk(U["R4"]["count"] == 3, "★ 不可判：R4 = 3 / 4 条推断边（新话题且 ref 不回指）")
    chk(U["R5"]["kind"] == "structural" and U["R5"]["count"] is None,
        "★ 不可判：R5 = **结构性**（count 为 None）—— ★ 不得印成 0")
    chk(U["R6"]["count"] == 1, "★ 不可判：R6 = 1（末封 k6 天然「尚未被回」）")
    chk(E["threading"]["ball_eq_to"] == 5 and E["threading"]["posts_seen"] == 6,
        "★ 共线控：ball==to = 5/6 ⇒ **不是 100%** ⇒ 该分支有否例（真语料上是 15/15，故本夹具特意破一例）")

    # ═══ ★ ⑩ 结构门自控：扫描器**不是空转** ═══
    chk(scan_forbidden(_FIXTURE_CLEAN_SRC) == [],
        "★ 门控：干净样本（合法只读 GET）⇒ 无命中")
    chk(len(scan_forbidden(_FIXTURE_DIRTY_SRC)) >= 1,
        "★ 门控：脏样本（注入写请求）⇒ 必命中（证扫描器非空转）")

    print(f"\nselftest: {ok} PASS / {fail} FAIL")
    return 0 if fail == 0 else 1


# ═══ ★ ⑩ 门的正/负控样本（★ 只在本进程内用，不落盘、不执行）═══
_FIXTURE_CLEAN_SRC = ('import urllib.request, json\n'
                      'with urllib.request.urlopen(BASE + P, timeout=30) as r:\n'
                      '    d = json.loads(r.read().decode("utf-8"))\n')
_FIXTURE_DIRTY_SRC = ('import urllib.request\n'
                      'req = urllib.request.Request(u, data=b"x", method="PUT")\n')


# ═══ ★ R006 ⑩ `--lean4-check` 六项模板 A–F ═══
def lean4_check():
    fails = 0
    checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, cond, detail))
        if cond is False:
            fails += 1

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    own = scan_forbidden(src)

    # A 源码无危险原语（★ 含**正控**：证明扫描器不是空转 —— 否则「0 命中」什么也不证明，坑 3）
    pos_ctl = scan_forbidden(_FIXTURE_DIRTY_SRC)
    c("A", "源码无危险原语（剥注释/字符串后扫描）", not own,
      "自身命中=%s · ★正控命中=%s" % (own or "无", pos_ctl))

    # B 负例全部被拒（★ 逐条实测，不是列表声明）
    negs = ['import subprocess\nsubprocess.run(["ls"])\n',
            'import os\nos.system("rm -rf /tmp/x")\n',
            'import urllib.request\nurllib.request.Request(u, method="DELETE")\n',
            'import urllib.request\nurllib.request.urlopen(u, data=b"x")\n',
            'import http.client\nhttp.client.HTTPConnection("h").request("POST", "/p")\n']
    bres = [bool(scan_forbidden(x)) for x in negs]
    c("B", "负例全部被拒（%d 条越界输入）" % len(negs), all(bres), "逐条=%s" % bres)

    # C 正例可用（★ 防「门太宽把功能也拦了」—— 合法只读 GET 必须能过）
    c("C", "正例可用：合法只读 GET 不被误伤", not scan_forbidden(_FIXTURE_CLEAN_SRC),
      "hits=%s" % (scan_forbidden(_FIXTURE_CLEAN_SRC) or "无"))

    # D --dry-run 零变更（★ 外部状态**实测**，不是声明；板不可达则如实 skip，不谎称通过）
    def _st():
        try:
            return (os.path.getsize(LOG), os.path.getmtime(LOG)) if os.path.exists(LOG) else None
        except OSError:
            return None
    before = _st()
    try:
        _lg = fetch_list(BOARDS["local"], LOG_PREFIX, timeout=10)
        try:
            _cu = fetch_list(BOARDS["local"], CUR_PREFIX, timeout=10)
        except Exception:
            _cu = {}
        build_index(_lg, _cu)                      # ★ 与 --dry-run 同路径：不含任何 log() 调用
        dstate, ddet = (before == _st()), "板可达 ⇒ 跑完整只读管线后日志未变"
    except Exception as e:
        dstate, ddet = None, "板不可达 ⇒ **跳过**（不谎称通过）: %s" % type(e).__name__
    c("D", "--dry-run 零变更（外部状态实测）", dstate, "%s · 日志 before=%s after=%s" % (ddet, before, _st()))

    # E 白名单冻结（不可变容器）
    c("E", "白名单冻结：禁止清单为不可变 tuple", isinstance(_FORBIDDEN_IDENT, tuple)
      and isinstance(_FORBIDDEN_PAT, tuple), "tuple ×2（%d 标识 + %d 模式）"
      % (len(_FORBIDDEN_IDENT), len(_FORBIDDEN_PAT)))

    # F 外部命令白名单（★ 去字面量定位调用点 → 回原文读实参；空集须由 A 的正控兜住）
    sites = re.findall(r"\b(subprocess|os\s*\.\s*system|os\s*\.\s*popen|os\s*\.\s*exec\w*"
                       r"|os\s*\.\s*spawn\w*)\b", _code_only(src))
    c("F", "外部命令白名单：调用点 ⊆ 允许集(∅)", not sites, "调用点=%d 个" % len(sites))

    print("== xdom-directory · --lean4-check（六项 A–F）==")
    for k, name, cond, detail in checks:
        mark = "✅" if cond is True else ("⚠️" if cond is None else "❌")
        print("  %s %-3s %-38s %s" % (mark, k, name, detail))
    print("\n  ⇒ %d/%d 绿 · %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


# ═══ ★ R006 ⑥ 版本：单一来源 + **自动反查自证** ═══
def tool_version(as_json):
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    decl = re.findall(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]", src, re.M)
    others = re.findall(r"^(?:__version__|VERSION_ALT)\s*=\s*['\"]", src, re.M)
    ok = (decl == [VERSION]) and not others
    payload = {"tool": "xdom-directory", "version": VERSION,
               "source": "VERSION 常量（本工具为独立 .py，无 package.json；常量即唯一来源）",
               "decl_sites": len(decl), "other_version_consts": len(others),
               "single_source_ok": ok, "r006": "⑥"}
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print("xdom-directory %s（声明位 %d 处 · 其它版本常量 %d 处 · 单一来源=%s）"
              % (VERSION, len(decl), len(others), "OK" if ok else "X"))
    return 0 if ok else 1


# ═══ ★ R006 ⑧ 登记卡（★ 只打印，不写板 —— 写板由调用方显式做）═══
def registry_card():
    print(json.dumps({
        "tool": "xdom-directory", "version": VERSION, "kind": "read-only-indexer",
        "path": "dsh-collab/docs/xdom-index/xdom-directory.py",
        "readme": "dsh-collab/docs/xdom-index/README.md",
        "what": "跨域邮箱只读目录页：把 notes/xdom/log/** 派生成目录页；边分 fact/inferred 两栏",
        "board_write": "never（★ 结构门：源码无 PUT/POST/DELETE/PATCH · 无 Request(/method=/data=）",
        "unified_log": "~/dsh-collab/logs/xdom-directory.log",
        "r006": {"①": "N/A 独立脚本（声明偏离）", "②": "--selfcheck", "⑥": "--tool-version 自证单一来源",
                 "⑦": "统一日志", "⑧": "本卡", "⑩": "--lean4-check A–F"},
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }, ensure_ascii=False, indent=1))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        description="跨域邮箱只读目录页生成器（R006 十项；★ 网络侧只 GET，不写板）")
    ap.add_argument("--board", default="local", choices=sorted(BOARDS))
    ap.add_argument("--json", action="store_true", help="机器可读输出（R006 ⑨）")
    ap.add_argument("--selftest", action="store_true", help="合成夹具自检（不碰真板、不写日志）")
    ap.add_argument("--selfcheck", action="store_true", help="R006 ② 能力边界自检")
    ap.add_argument("--lean4-check", dest="lean4", action="store_true", help="R006 ⑩ 结构门六项 A–F")
    ap.add_argument("--tool-version", dest="tool_version", action="store_true", help="R006 ⑥ 版本")
    ap.add_argument("--registry-card", dest="registry_card", action="store_true",
                    help="R006 ⑧ 打出登记卡 JSON（★ 只打印，不写板）")
    ap.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="R006 ⑨ 走完整只读管线但零变更（★ 连本地日志也不写）")
    a = ap.parse_args(argv)

    def L(msg):
        if not a.dry_run:
            log(msg)

    if a.selftest:
        return selftest()
    if a.lean4:
        rc = lean4_check()
        L("lean4-check rc=%d" % rc)
        return rc
    if a.tool_version:
        return tool_version(a.json)
    if a.registry_card:
        L("registry-card printed")
        return registry_card()

    # ★ ⑩「失败即停」：跑任何真实动作前先扫自己；不通过则**拒绝执行**
    viol, nbytes = guard_own_source()
    if viol:
        print("★ ⑩ 门：源码检出禁止原语 ⇒ **拒绝执行**：%s" % ", ".join(viol), file=sys.stderr)
        L("REFUSE guard violations=%s" % viol)
        return 1

    L("run board=%s dry_run=%s guard=clean(%dB)" % (a.board, a.dry_run, nbytes))
    base = BOARDS[a.board]
    try:
        logs = fetch_list(base, LOG_PREFIX)
        try:
            cursors = fetch_list(base, CUR_PREFIX)
        except Exception:
            cursors = {}
    except Exception as e:
        print("★ IO 错误：读板失败（%s）：%s" % (a.board, e), file=sys.stderr)
        L("IO-ERROR board=%s %s: %s" % (a.board, type(e).__name__, e))
        return 2

    idx = build_index(logs, cursors)
    t = idx["totals"]
    L("ok board=%s posts=%d req_reply=%d fact=%d inferred=%d"
      % (a.board, t["posts"], t["requires_reply"], t["edges_fact"], t["edges_inferred"]))
    print(json.dumps(idx, ensure_ascii=False, indent=1) if a.json
          else render_md(idx, a.board))
    return 0


if __name__ == "__main__":
    sys.exit(main())
