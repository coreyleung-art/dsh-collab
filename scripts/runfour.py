#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
runfour.py — 四跑法标准框架（正跑 / 反跑 / 空数据跑 / 数据跑）

明鉴 · 2026-09-10 · v1.0.0

背景
----
现有 wargame-sim.py 里只有 `value`（六维加权打分）是真计算，enumerate / reverse /
capital 只输出步骤提示。「四跑法」这套方法一直缺少标准对比框架 —— 尤其是
**「数据跑纠正了空跑的什么判断」**这一核心价值，目前全靠人工写。本工具提供四跑法的
**结构化记录 + 对比分析**。

四跑定义
--------
  正跑 forward  从现状往上推：手上有什么 → 顺着现有能力能走到哪        → 下限路径
  反跑 reverse  从目标倒推：要达成目标前置条件是什么、分几阶段、分水岭在哪 → 前置条件清单
  空数据跑 blank 不代入任何真实数据，纯抽象排序：正常情况下哪些环节最关键  → 抽象基线排序
  数据跑 data   代入已知数据重跑，看纠正了什么                        → 校正表

  ⚠️ 四跑的价值不是走流程，是「数据跑纠正了空跑的什么判断」——
     如果答不出这一句，说明推演没做透。

用法
----
  runfour.py init    <主题> --out /tmp/four/                       # 1) 生成记录模板
  runfour.py fill    /tmp/four/ --run forward --judgments j.json    # 2) 填一跑结果（或交互）
  runfour.py compare /tmp/four/ --out COMPARISON.md                 # 3) ★ 对比分析
  runfour.py score   /tmp/four/ --positions positions.json          # 4) 六维打分（调 wargame-sim.py）
  runfour.py --version / --help

诚实红线（R1-R4）写进模板与 compare 自查表，不可绕过：
  R1 分数是判断不是测量
  R2 测算 ≠ 验证
  R3 冲突要标出、来源不明要标注
  R4 不能拿「推演出来的能行」当「真的能行」—— 必须列出待真实验证项

零外部依赖 · Python 3.9+
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import datetime
import json
import os
import re
import subprocess
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/runfour.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
FOUR_JSON = "four.json"
TEMPLATE_MD = "TEMPLATE.md"
COMPARISON_MD = "COMPARISON.md"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_WARGAME_CANDIDATES = [
    os.path.join(SCRIPT_DIR, "wargame-sim.py"),
    os.path.expanduser("~/dsh-collab/scripts/wargame-sim.py"),
]

# ─────────────────────────── 四跑元数据（模板与提示的唯一真源） ───────────────────────────
RUNS = [
    {
        "key": "forward",
        "label": "正跑",
        "sub": "从现状往上推",
        "key_out": "下限路径",
        "what": "手上有什么 → 顺着现有能力能走到哪",
        "questions": [
            "手上有什么？（能力 / 资源 / 数据 / 关系 / 资质，逐项列）",
            "顺着现有能力、不追加投入，最远能走到哪一步？（这就是下限路径）",
            "哪一步会卡住？卡住的直接原因是什么？",
            "下限路径的终点是什么状态？（不含任何「如果融到钱 / 如果有人给」）",
        ],
        "fill_hint": "judgments: [{\"claim\":\"判断\",\"basis\":\"依据\",\"conclusion\":\"结论\"}]",
    },
    {
        "key": "reverse",
        "label": "反跑",
        "sub": "从目标倒推",
        "key_out": "前置条件清单",
        "what": "要达成目标，前置条件是什么、分几阶段、分水岭在哪",
        "questions": [
            "目标是什么？（写成可判定达成与否的一句话）",
            "要达成它，前置条件有哪些？（资格 / 数据 / 战绩 / 能力 / 资本，逐条列）",
            "每条前置条件「怎么验证它已具备」？（verifiable 必须可观测，不能写「感觉有了」）",
            "分几个阶段？每阶段拿到什么、验证什么？",
            "分水岭/守门动作在哪一关？（赢下哪一关才上台阶）",
        ],
        "fill_hint": "prerequisites: [{\"id\":\"P1\",\"name\":\"…\",\"desc\":\"…\",\"verifiable\":\"…\"}], phases: [{\"name\":\"…\",\"goal\":\"…\",\"watershed\":\"…\"}]",
    },
    {
        "key": "blank",
        "label": "空数据跑",
        "sub": "不代入任何真实数据，纯抽象排序",
        "key_out": "抽象基线排序",
        "what": "正常情况下哪些环节最关键（无数字，只有逻辑）",
        "questions": [
            "先把真实数字遮住：这条业务链上，正常情况下哪些环节最关键？",
            "抽象（第一性）排序的前三名是谁？为什么他们最关键（讲逻辑，不讲数字）？",
            "如果只能抓一个环节，抓哪个？（key_link）",
            "这个排序的依据是什么？（例：缺口量级 / 不可替代性 / 行业普遍规律）",
        ],
        "fill_hint": "ranking: [{\"rank\":1,\"item\":\"环节\",\"why\":\"为什么最关键\"}], key_link: \"最关键的单一环节\"",
    },
    {
        "key": "data",
        "label": "数据跑",
        "sub": "代入已知数据重跑，看纠正了什么",
        "key_out": "校正表",
        "what": "代入真实数据后，排序/结论变了什么",
        "questions": [
            "代入哪些真实数据？（每个数字标注来源：回填 / 测算 / 待考证）",
            "重跑后哪几个环节的排序变了？",
            "空跑以为最优的，在数据下还是最优吗？有没有被反超？",
            "反超的原因是什么？（给出算式与结论）",
        ],
        "fill_hint": "calculations: [{\"name\":\"算式一\",\"formula\":\"…\",\"result\":\"…\",\"implication\":\"…\"}]",
    },
]
RUN_KEYS = [r["key"] for r in RUNS]
RUN_MAP = {r["key"]: r for r in RUNS}

# 诚实红线 R1-R4（不可绕过）
REDLINES = [
    ("R1", "分数是判断不是测量",
     "六维分数 / 可能性级别都是独立分析判断，不是测量值；可讨论、可调整，不得当客观事实引用。可能性只给「高/中/低」，不给百分比。",
     "本次哪些分数 / 级别只是判断？依据是什么？"),
    ("R2", "测算 ≠ 验证",
     "凡模型外推 / 会议口径一律标「测算」；只有真实财务 / 订单 / 回填数据才可标「已验证」。",
     "本次哪些数字是测算、哪些有真实回填？"),
    ("R3", "冲突要标出、来源不明要标注",
     "不同版本数字打架必须点明；无公开信源的数字标「待考证 / 需补信源」。",
     "本次有无打架数字 / 无源数字？标在哪一处？"),
    ("R4", "不能拿「推演出来的能行」当「真的能行」",
     "推演只产出假设。必须列出待真实验证项——未验证前不得对外宣称可行。",
     "本次待真实验证项有哪些？谁去验、用什么数据验？"),
]
REDLINE_MAP = {c: (name, desc, q) for c, name, desc, q in REDLINES}

CORE_HINT = ("四跑的价值不是走流程，是「数据跑纠正了空跑的什么判断」"
             "——如果答不出这一句，说明推演没做透")

PCT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％)|百分之[零一二三四五六七八九十百\d]+")
DERIVED_MARK_RE = re.compile(r"测算|估算|假设|外推|拍脑袋|待考证|待定|会议口径|目标值")


# ─────────────────────────────── 工具函数 ───────────────────────────────
def _today():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _e(p):
    return os.path.abspath(os.path.expanduser(p))


def _four_path(d):
    if os.path.isdir(d):
        return os.path.join(d, FOUR_JSON)
    return d


def load_four(d):
    p = _four_path(_e(d))
    if not os.path.exists(p):
        print("❌ 找不到记录文件: %s（先跑 runfour.py init）" % p)
        sys.exit(1)
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as ex:
        print("❌ 读 %s 失败: %s" % (p, ex))
        sys.exit(1)
    if not isinstance(data, dict):
        print("❌ %s 结构错误：顶层必须是对象" % p)
        sys.exit(1)
    return data, p


def save_four(data, p):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _cell(v):
    """Markdown 表格单元格：转义竖线、压平换行。"""
    s = "" if v is None else str(v)
    s = s.replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()
    return s if s else "—"


def _md_table(headers, rows, empty_hint="（空）"):
    if not rows:
        return ["_%s_" % empty_hint, ""]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(_cell(c) for c in r) + " |")
    out.append("")
    return out


def _norm_level(level):
    """级别归一化：只认 高/中/低。返回 (级别, 原始文本, 是否违规)。"""
    raw = (level or "").strip()
    for ch in ("高", "中", "低"):
        if ch in raw:
            return ch, raw, (raw != ch)
    return "?", raw, bool(raw)


def _blank_run():
    return {
        "forward": {"judgments": [], "summary": ""},
        "reverse": {"prerequisites": [], "phases": [], "summary": ""},
        "blank": {"ranking": [], "key_link": "", "summary": ""},
        "data": {"calculations": [], "summary": ""},
    }


def new_record(topic, date=None):
    return {
        "topic": topic,
        "created": date or _today(),
        "runs": _blank_run(),
        "corrections": [],
        "feasibility": [],
        "honesty": {"R1": "", "R2": "", "R3": "", "R4": ""},
        "verify_items": [],
    }


# ─────────────────────────────── init ───────────────────────────────
def _template_md(topic, created):
    L = []
    A = L.append
    A("# 四跑法记录模板 · %s" % topic)
    A("")
    A("> 建立日期 %s · 框架 runfour.py v%s" % (created, VERSION))
    A("> ")
    A("> ⚠️ **%s**" % CORE_HINT)
    A("")
    A("## 一、怎么用（4 步）")
    A("")
    A("```bash")
    A("runfour.py init    \"%s\" --out .           # 已生成 four.json" % topic)
    A("runfour.py fill    . --run forward  --judgments forward.json")
    A("runfour.py fill    . --run reverse  --judgments reverse.json")
    A("runfour.py fill    . --run blank    --judgments blank.json")
    A("runfour.py fill    . --run data     --judgments data.json")
    A("runfour.py fill    . --run corrections --judgments corrections.json   # ★ 核心")
    A("runfour.py fill    . --run feasibility --judgments feasibility.json")
    A("runfour.py fill    . --run honesty  --judgments honesty.json")
    A("runfour.py compare . --out COMPARISON.md   # ★ 生成对比分析")
    A("runfour.py score   . --positions positions.json")
    A("```")
    A("")
    A("不给 `--judgments` 时进入交互模式（逐条问答）。")
    A("")
    A("## 二、四跑定义与「每跑要回答的问题」")
    A("")
    A("| 跑法 | 做什么 | 关键输出 |")
    A("|---|---|---|")
    A("| **正跑 forward** | 从现状往上推：手上有什么 → 顺着现有能力能走到哪 | 下限路径 |")
    A("| **反跑 reverse** | 从目标倒推：要达成目标，前置条件是什么、分几阶段、分水岭在哪 | 前置条件清单 |")
    A("| **空数据跑 blank** | **不代入任何真实数据**，纯抽象排序：正常情况下哪些环节最关键 | 抽象基线排序 |")
    A("| **数据跑 data** | **代入已知数据**重跑，**看纠正了什么** | 校正表 |")
    A("")
    for i, r in enumerate(RUNS, 1):
        A("### %d. %s %s —— %s" % (i, r["label"], r["key"], r["sub"]))
        A("")
        A("关键输出：**%s**" % r["key_out"])
        A("")
        A("要回答的问题：")
        A("")
        for q in r["questions"]:
            A("- [ ] %s" % q)
        A("")
        A("填法（`four.json` → `runs.%s`）：`%s`" % (r["key"], r["fill_hint"]))
        A("")
    A("## 三、★ 校正表（本方法的核心产出）")
    A("")
    A("填 `corrections` —— **空跑以为最优的 → 数据跑反超为 → 为什么反超 → 数据依据**：")
    A("")
    A("```json")
    A(json.dumps({"corrections": [
        {"blank_thought": "空跑以为最优的环节",
         "data_shows": "数据跑反超为哪个环节",
         "why": "为什么反超（机制，不是复述数字）",
         "evidence": "数据依据（标明是回填还是测算）"}]},
        ensure_ascii=False, indent=2))
    A("```")
    A("")
    A("> 填不出校正表 = 这一轮推演没做透。空跑与数据跑得出同一个排序，说明数据没带来新信息，")
    A("> 要么数据选错，要么空跑一开始就偷看了数据。")
    A("")
    A("## 四、可能性评估（只给高/中/低，**不给百分比**）")
    A("")
    A("```json")
    A(json.dumps({"feasibility": [
        {"scope": "口径（哪个目标/哪条路径）", "level": "高|中|低",
         "preconditions": ["达到该级别的前置条件1", "前置条件2"]}]},
        ensure_ascii=False, indent=2))
    A("```")
    A("")
    A("## 五、诚实红线 R1-R4（不可绕过）")
    A("")
    A("| 编码 | 红线 | 说明 | 本次要回答 |")
    A("|---|---|---|---|")
    for code, name, desc, q in REDLINES:
        A("| %s | %s | %s | %s |" % (code, name, desc, q))
    A("")
    A("在 `four.json` → `honesty` 里逐个作答（R1-R4 各一段话）。**R4 必须落到「待真实验证项」清单**：")
    A("")
    A("```json")
    A(json.dumps({"honesty": {"R1": "…", "R2": "…", "R3": "…", "R4": "…"},
                  "verify_items": [
                      {"item": "待验证项", "why": "为什么必须真实验证",
                       "how": "怎么验（谁/用什么数据/什么标准）"}]},
                 ensure_ascii=False, indent=2))
    A("```")
    A("")
    A("## 六、four.json 空壳结构（这就是要填的东西）")
    A("")
    A("```json")
    A(json.dumps(new_record(topic, created), ensure_ascii=False, indent=2))
    A("```")
    A("")
    A("---")
    A("")
    A("> ⚠️ **%s**" % CORE_HINT)
    A("")
    return "\n".join(L)


def cmd_init(args):
    out = _e(args.out) if args.out else _e("./four-" + re.sub(r"\W+", "-", args.topic).strip("-").lower())
    os.makedirs(out, exist_ok=True)
    fp = os.path.join(out, FOUR_JSON)
    tp = os.path.join(out, TEMPLATE_MD)
    if os.path.exists(fp) and not args.force:
        print("⚠️ %s 已存在（加 --force 覆盖）" % fp)
        return 1
    created = args.date or _today()
    data = new_record(args.topic, created)
    save_four(data, fp)
    with open(tp, "w", encoding="utf-8") as f:
        f.write(_template_md(args.topic, created))

    print("✅ 四跑法记录模板已生成")
    print("   主题   : %s" % args.topic)
    print("   记录   : %s" % fp)
    print("   模板   : %s" % tp)
    print("")
    print("   空壳结构：runs.forward/judgments · runs.reverse/prerequisites+phases ·")
    print("             runs.blank/ranking · runs.data/calculations")
    print("             + corrections（★校正表）+ feasibility + honesty(R1-R4) + verify_items")
    print("")
    print("   四跑定义：")
    for r in RUNS:
        print("     %-8s %-6s %s → %s" % (r["key"], r["label"], r["what"], r["key_out"]))
    print("")
    print("   诚实红线：")
    for code, name, _d, _q in REDLINES:
        print("     %s %s" % (code, name))
    print("")
    print("   ⚠️ %s" % CORE_HINT)
    print("")
    print("   下一步：runfour.py fill %s --run forward --judgments forward.json" % out)
    return 0


# ─────────────────────────────── fill ───────────────────────────────
FIELD_SPEC = {
    "forward": {"list_key": "judgments", "fields": ["claim", "basis", "conclusion"], "unit": "判断"},
    "blank": {"list_key": "ranking", "fields": ["rank", "item", "why"], "unit": "排序项"},
    "data": {"list_key": "calculations", "fields": ["name", "formula", "result", "implication"], "unit": "算式"},
}
REVERSE_SPEC = {
    "prerequisites": ["id", "name", "desc", "verifiable"],
    "phases": ["name", "goal", "watershed"],
}
CORRECTION_FIELDS = ["blank_thought", "data_shows", "why", "evidence"]
FEASIBILITY_FIELDS = ["scope", "level", "preconditions"]
VERIFY_FIELDS = ["item", "why", "how"]


def _norm_items(items, fields, unit, unknown_log, list_fields=()):
    out = []
    if not isinstance(items, list):
        items = [items]
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            it = {fields[0]: it}
        for k in it:
            if k not in fields and k not in unknown_log:
                unknown_log.append(k)
        row = {}
        for f in fields:
            v = it.get(f, "")
            if f in list_fields:
                if isinstance(v, str):
                    v = [x.strip() for x in re.split(r"[,，;；]", v) if x.strip()]
                elif isinstance(v, list):
                    v = [str(x) for x in v]
                else:
                    v = []
            elif isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)
            row[f] = v
        if "id" in fields and not row["id"]:
            row["id"] = "P%d" % (i + 1)
        if "rank" in fields and not row["rank"]:
            row["rank"] = i + 1
        out.append(row)
    return out


def _apply_run(data, name, payload, unknown_log):
    """把一份 payload 写进 four.json 的某个部分，返回人类可读的填充摘要。"""
    runs = data.setdefault("runs", _blank_run())

    if name == "forward":
        spec = FIELD_SPEC["forward"]
        items = payload.get(spec["list_key"], payload) if isinstance(payload, dict) else payload
        rows = _norm_items(items, spec["fields"], spec["unit"], unknown_log)
        runs.setdefault("forward", {})["judgments"] = rows
        if isinstance(payload, dict) and "summary" in payload:
            runs["forward"]["summary"] = payload["summary"]
        return "正跑 forward：%d 条判断" % len(rows)

    if name == "reverse":
        payload = payload if isinstance(payload, dict) else {"prerequisites": payload}
        n = 0
        for key, fields in REVERSE_SPEC.items():
            if key in payload:
                rows = _norm_items(payload[key], fields, key, unknown_log)
                runs.setdefault("reverse", {})[key] = rows
                n += len(rows)
        if "summary" in payload:
            runs["reverse"]["summary"] = payload["summary"]
        return "反跑 reverse：%d 条（前置条件 %d / 阶段 %d）" % (
            n, len(runs.get("reverse", {}).get("prerequisites", [])),
            len(runs.get("reverse", {}).get("phases", [])))

    if name == "blank":
        spec = FIELD_SPEC["blank"]
        items = payload.get(spec["list_key"], []) if isinstance(payload, dict) else payload
        rows = _norm_items(items, spec["fields"], spec["unit"], unknown_log)
        runs.setdefault("blank", {})["ranking"] = rows
        if isinstance(payload, dict) and "key_link" in payload:
            runs["blank"]["key_link"] = payload["key_link"]
        if isinstance(payload, dict) and "summary" in payload:
            runs["blank"]["summary"] = payload["summary"]
        return "空数据跑 blank：%d 项排序，key_link=%s" % (
            len(rows), runs["blank"].get("key_link") or "（未填）")

    if name == "data":
        spec = FIELD_SPEC["data"]
        items = payload.get(spec["list_key"], []) if isinstance(payload, dict) else payload
        rows = _norm_items(items, spec["fields"], spec["unit"], unknown_log)
        runs.setdefault("data", {})["calculations"] = rows
        if isinstance(payload, dict) and "summary" in payload:
            runs["data"]["summary"] = payload["summary"]
        return "数据跑 data：%d 条算式" % len(rows)

    if name == "corrections":
        items = payload.get("corrections", payload) if isinstance(payload, dict) else payload
        rows = _norm_items(items, CORRECTION_FIELDS, "校正", unknown_log)
        data["corrections"] = rows
        return "★ 校正表：%d 条（空跑以为最优 → 数据跑反超为）" % len(rows)

    if name == "feasibility":
        items = payload.get("feasibility", payload) if isinstance(payload, dict) else payload
        rows = _norm_items(items, FEASIBILITY_FIELDS, "评估", unknown_log, list_fields=("preconditions",))
        for r in rows:
            lv, raw, bad = _norm_level(r.get("level"))
            r["level"] = lv
            if bad:
                print("  ⚠️ 可能性级别已归一化为「%s」（原始：%s）—— R1：只给高/中/低，不给百分比" % (lv, raw))
        data["feasibility"] = rows
        return "可能性评估：%d 条口径" % len(rows)

    if name == "honesty":
        h = data.setdefault("honesty", {"R1": "", "R2": "", "R3": "", "R4": ""})
        if not isinstance(payload, dict):
            payload = {}
        # 允许 {"honesty": {...}} 或直接 {"R1": "..."}
        if isinstance(payload.get("honesty"), dict):
            payload = payload["honesty"]
        filled = []
        for code, _n, _d, _q in REDLINES:
            if code in payload and str(payload[code]).strip():
                h[code] = payload[code]
                filled.append(code)
        msg = "诚实红线：已作答 %s" % ("/".join(filled) if filled else "（无）")
        if "verify_items" in payload:  # 同一份文件可顺带写入 R4 待验证项
            data["verify_items"] = _norm_items(payload["verify_items"], VERIFY_FIELDS, "验证项", unknown_log)
            msg += "；待真实验证项 %d 项" % len(data["verify_items"])
        return msg

    if name == "verify_items":
        items = payload.get("verify_items", payload) if isinstance(payload, dict) else payload
        rows = _norm_items(items, VERIFY_FIELDS, "验证项", unknown_log)
        data["verify_items"] = rows
        return "待真实验证项：%d 项（R4）" % len(rows)

    return ""


FILL_TARGETS = RUN_KEYS + ["corrections", "feasibility", "honesty", "verify_items", "all"]


def _interactive_fill(name):
    """交互式填入（无 --judgments 且 stdin 是 TTY 时）。"""
    print("── 交互填入：%s（直接回车跳过该条，空 claim/name/item 结束本段）──" % name)
    payload = {}
    if name == "forward":
        rows = []
        while True:
            claim = input("判断(claim)：").strip()
            if not claim:
                break
            rows.append({"claim": claim,
                         "basis": input("  依据(basis)：").strip(),
                         "conclusion": input("  结论(conclusion)：").strip()})
        payload = {"judgments": rows}
    elif name == "reverse":
        pre, ph = [], []
        while True:
            nm = input("前置条件名(空=结束)：").strip()
            if not nm:
                break
            pre.append({"id": "P%d" % (len(pre) + 1), "name": nm,
                        "desc": input("  说明：").strip(),
                        "verifiable": input("  怎么验证已具备：").strip()})
        while True:
            nm = input("阶段名(空=结束)：").strip()
            if not nm:
                break
            ph.append({"name": nm, "goal": input("  拿到什么：").strip(),
                       "watershed": input("  分水岭：").strip()})
        payload = {"prerequisites": pre, "phases": ph}
    elif name == "blank":
        rows = []
        while True:
            it = input("环节(空=结束)：").strip()
            if not it:
                break
            rows.append({"rank": len(rows) + 1, "item": it, "why": input("  为什么最关键：").strip()})
        payload = {"ranking": rows, "key_link": input("最关键的单一环节(key_link)：").strip()}
    elif name == "data":
        rows = []
        while True:
            nm = input("算式名(空=结束)：").strip()
            if not nm:
                break
            rows.append({"name": nm, "formula": input("  算式：").strip(),
                         "result": input("  结果：").strip(),
                         "implication": input("  含义：").strip()})
        payload = {"calculations": rows}
    elif name == "corrections":
        rows = []
        while True:
            bt = input("空跑以为最优的(空=结束)：").strip()
            if not bt:
                break
            rows.append({"blank_thought": bt,
                         "data_shows": input("  数据跑反超为：").strip(),
                         "why": input("  为什么反超：").strip(),
                         "evidence": input("  数据依据：").strip()})
        payload = {"corrections": rows}
    elif name == "feasibility":
        rows = []
        while True:
            sc = input("口径(空=结束)：").strip()
            if not sc:
                break
            lv = input("  级别(高/中/低)：").strip()
            pcs = [x.strip() for x in input("  前置条件(逗号分隔)：").split(",") if x.strip()]
            rows.append({"scope": sc, "level": lv, "preconditions": pcs})
        payload = {"feasibility": rows}
    elif name == "honesty":
        payload = {}
        for code, nm, _d, q in REDLINES:
            payload[code] = input("%s %s —— %s\n  > " % (code, nm, q)).strip()
    elif name == "verify_items":
        rows = []
        while True:
            it = input("待验证项(空=结束)：").strip()
            if not it:
                break
            rows.append({"item": it, "why": input("  为什么必须真实验证：").strip(),
                         "how": input("  怎么验：").strip()})
        payload = {"verify_items": rows}
    return payload


def cmd_fill(args):
    data, p = load_four(args.dir)
    name = args.run
    if name not in FILL_TARGETS:
        print("❌ 未知目标: %s（可选：%s）" % (name, ", ".join(FILL_TARGETS)))
        return 1

    src = args.judgments or args.file
    if src:
        src = _e(src)
        if not os.path.exists(src):
            print("❌ 找不到 %s" % src)
            return 1
        try:
            with open(src, encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as ex:
            print("❌ 解析 %s 失败: %s" % (src, ex))
            return 1
    elif sys.stdin.isatty():
        payload = _interactive_fill(name if name != "all" else "forward")
    else:
        payload = {}
        if args.summary:
            payload = {"summary": args.summary}

    if not payload and not args.summary:
        print("❌ 没有输入：用 --judgments <file> 或加 --summary「…」（TTY 下不给文件即交互模式）")
        return 1

    unknown = []
    msgs = []
    if name == "all":
        if not isinstance(payload, dict):
            print("❌ --run all 需要一份对象，键为 forward/reverse/blank/data/corrections/feasibility/honesty/verify_items")
            return 1
        for k, v in payload.items():
            if k not in FILL_TARGETS or k == "all":
                unknown.append(k)
                continue
            m = _apply_run(data, k, v, unknown)
            if m:
                msgs.append(m)
    else:
        m = _apply_run(data, name, payload, unknown)
        if m:
            msgs.append(m)
        if args.summary and name in RUN_KEYS:
            data.setdefault("runs", _blank_run()).setdefault(name, {})["summary"] = args.summary
            msgs.append("%s 小结已写入" % RUN_MAP[name]["label"])

    data["updated"] = _now()
    save_four(data, p)

    print("✅ 已写入 %s" % p)
    for m in msgs:
        print("   · %s" % m)
    if unknown:
        seen = []
        for k in unknown:
            if k not in seen:
                seen.append(k)
        print("   ⚠️ 忽略未知字段: %s" % ", ".join(seen))
    if name == "corrections" and len(data.get("corrections", [])) == 0:
        print("   ⚠️ 校正表为空 —— %s" % CORE_HINT)
    print("   下一步：runfour.py compare %s" % os.path.dirname(p))
    return 0


# ─────────────────────────────── compare ───────────────────────────────
def _section_summaries(d, L):
    A = L.append
    runs = d.get("runs", {})
    A("## 1. 四跑摘要")
    A("")

    # 1.1 正跑
    fw = runs.get("forward", {}) or {}
    js = fw.get("judgments", []) or []
    A("### 1.1 正跑 forward —— 从现状往上推（下限路径）")
    A("")
    A("- 判断数：**%d**" % len(js))
    A("- 小结：%s" % (fw.get("summary") or "（未填）"))
    A("")
    L.extend(_md_table(["判断 claim", "依据 basis", "结论 conclusion"],
                       [[j.get("claim"), j.get("basis"), j.get("conclusion")] for j in js],
                       "（未填：正跑的下限路径还没写）"))

    # 1.2 反跑
    rv = runs.get("reverse", {}) or {}
    pre = rv.get("prerequisites", []) or []
    ph = rv.get("phases", []) or []
    A("### 1.2 反跑 reverse —— 从目标倒推（前置条件清单）")
    A("")
    A("- 前置条件：**%d** 条 · 阶段：**%d** 个" % (len(pre), len(ph)))
    A("- 小结：%s" % (rv.get("summary") or "（未填）"))
    A("")
    L.extend(_md_table(["id", "前置条件", "说明", "怎么验证已具备"],
                       [[x.get("id"), x.get("name"), x.get("desc"), x.get("verifiable")] for x in pre],
                       "（未填：反跑的前置条件清单还没写）"))
    L.extend(_md_table(["阶段", "拿到什么", "分水岭 / 守门动作"],
                       [[x.get("name"), x.get("goal"), x.get("watershed")] for x in ph],
                       "（未填：阶段与分水岭还没写）"))

    # 1.3 空跑
    bl = runs.get("blank", {}) or {}
    rk = bl.get("ranking", []) or []
    A("### 1.3 空数据跑 blank —— 不代入任何真实数据（抽象基线排序）")
    A("")
    A("- 排序项：**%d** · 最关键单一环节 key_link：**%s**" % (len(rk), bl.get("key_link") or "（未填）"))
    A("- 小结：%s" % (bl.get("summary") or "（未填）"))
    A("")
    L.extend(_md_table(["#", "环节", "为什么最关键"],
                       [[x.get("rank"), x.get("item"), x.get("why")] for x in rk],
                       "（未填：空跑的抽象基线排序还没写）"))

    # 1.4 数据跑
    dt = runs.get("data", {}) or {}
    ca = dt.get("calculations", []) or []
    A("### 1.4 数据跑 data —— 代入已知数据重跑（校正表）")
    A("")
    A("- 算式：**%d** 条" % len(ca))
    A("- 小结：%s" % (dt.get("summary") or "（未填）"))
    A("")
    L.extend(_md_table(["算式", "公式", "结果", "含义"],
                       [[x.get("name"), x.get("formula"), x.get("result"), x.get("implication")] for x in ca],
                       "（未填：数据跑的重算还没写）"))
    A("")


def _section_corrections(d, L):
    A = L.append
    corr = d.get("corrections", []) or []
    A("## 2. ★ 校正表（本方法的核心产出）")
    A("")
    A("> 空跑以为最优的 → 数据跑反超为 → 为什么反超 → 数据依据。")
    A("> **这一节空着，等于这轮推演没做。**")
    A("")
    L.extend(_md_table(["空跑以为最优的", "数据跑反超为", "为什么反超", "数据依据"],
                       [[c.get("blank_thought"), c.get("data_shows"), c.get("why"), c.get("evidence")]
                        for c in corr],
                       "⚠️ 校正表为空 —— " + CORE_HINT))
    if corr:
        A("**逐条解读：**")
        A("")
        for i, c in enumerate(corr, 1):
            A("%d. 空跑把「%s」当成最优；代入数据后「%s」反超。机制：%s（依据：%s）"
              % (i, c.get("blank_thought") or "?", c.get("data_shows") or "?",
                 c.get("why") or "（未写原因——没写原因就等于没做数据跑）",
                 c.get("evidence") or "（未写依据）"))
        A("")
    return corr


def _section_methodology(d, L, corr):
    A = L.append
    bl = (d.get("runs", {}) or {}).get("blank", {}) or {}
    rk = bl.get("ranking", []) or []
    top = rk[0] if rk else {}
    A("## 3. 方法论收获")
    A("")
    if not corr:
        A("⚠️ **无法生成**：校正表为空，所以「数据跑纠正了空跑的什么判断」这一句答不出来。")
        A("")
        A("> %s" % CORE_HINT)
        A("")
        return
    A("### 3.1 一句话收获（自动生成，请人工复核措辞）")
    A("")
    bl_first = top.get("item") or "（空跑未填排序）"
    bl_why = top.get("why") or "（空跑未写判据）"
    c0 = corr[0]
    A("> 空跑排序「**%s**」（判据：%s）；数据跑排序「**%s**」（判据：%s）——"
      % (bl_first, bl_why, c0.get("data_shows") or "?", c0.get("evidence") or "?"))
    A("> 排序依据发生了切换：从「%s」切换到「%s」。"
      % (bl_why, c0.get("why") or "?"))
    A("")
    A("### 3.2 逐条差异")
    A("")
    for i, c in enumerate(corr, 1):
        A("- **%s** → **%s**：%s" % (c.get("blank_thought") or "?", c.get("data_shows") or "?",
                                     c.get("why") or "（未写）"))
    A("")
    A("### 3.3 常见切换形态（参考用，**非本次结论**，请按实际填写替换）")
    A("")
    A("- 「缺口量级」→「约束释放后的边际收益」：空跑看谁缺口大，数据跑看放开限制后谁真的多赚。")
    A("- 「绝对量大小」→「可动用性 / 确定性」：空跑看盘子大，数据跑看这笔钱我能不能真拿到。")
    A("- 「行业普遍性」→「我方独占性」：空跑看行业里最重要的环节，数据跑看我卡得住的那一环。")
    A("- 「单点最优」→「链路可行」：空跑挑最好的点，数据跑挑整条链跑得通的那条。")
    A("")
    A("> 判断标准：如果 3.1 那句话读起来像「数据证实了我原本的想法」，那多半是空跑偷看了数据，")
    A("> 而不是数据跑带来了新信息。")
    A("")


def _section_feasibility(d, L):
    A = L.append
    fe = d.get("feasibility", []) or []
    A("## 4. 可能性评估（只给 高 / 中 / 低，**不给百分比**）")
    A("")
    A("> R1：级别是判断不是测量。给出级别必须同时给出前置条件；前置条件不满足，级别即不成立。")
    A("")
    rows = []
    pct_hits = []
    for f in fe:
        lv, raw, bad = _norm_level(f.get("level"))
        pcs = f.get("preconditions")
        if isinstance(pcs, list):
            pcs_txt = "；".join(str(x) for x in pcs)
        else:
            pcs_txt = str(pcs or "")
        if PCT_RE.search(str(raw) + " " + pcs_txt + " " + str(f.get("scope") or "")):
            pct_hits.append(f.get("scope") or "?")
        rows.append([f.get("scope"), lv, pcs_txt])
    L.extend(_md_table(["口径 / 路径", "级别", "前置条件"], rows,
                       "（未填：用 runfour.py fill … --run feasibility 补，只给高/中/低）"))
    if pct_hits:
        A("⚠️ **检测到百分比表述**（%s）—— 本框架禁止用百分比表达可能性（R1：分数是判断不是测量），"
          "已按高/中/低口径归一化，请回填文本。" % "、".join(pct_hits))
        A("")
    A("级别判定口径：**高** = 前置条件已基本具备或已有真实数据支撑；**中** = 前置条件部分具备，"
      "关键一环仍待验证；**低** = 关键前置条件缺失，需外部条件变化才成立。")
    A("")
    A("> 说明：数据跑算式里的百分比属于「数据」，不构成 R1 违规；R1 只约束**可能性级别**")
    A("> （必须用高/中/低表达，不得写「成功率 70%」这类伪装成测量的判断）。")
    A("")
    return pct_hits


def _derive_verify_items(d):
    """R4 待真实验证项：优先用填写的，再从 中/低 级别口径 + 测算型依据 自动补。"""
    items = []
    explicit = d.get("verify_items", []) or []
    for v in explicit:
        if isinstance(v, dict):
            items.append({"item": v.get("item") or "?", "why": v.get("why") or "（未写）",
                          "how": v.get("how") or "（未写）", "src": "填写"})
        else:
            items.append({"item": str(v), "why": "（未写）", "how": "（未写）", "src": "填写"})

    for f in d.get("feasibility", []) or []:
        lv, _raw, _bad = _norm_level(f.get("level"))
        if lv in ("中", "低"):
            pcs = f.get("preconditions")
            pcs_txt = "；".join(str(x) for x in pcs) if isinstance(pcs, list) else str(pcs or "")
            items.append({"item": "「%s」达到「%s」可能性" % (f.get("scope") or "?", lv),
                          "why": "前置条件尚未全部满足，推演结论不构成可行性证据",
                          "how": pcs_txt or "（前置条件未填——需补）", "src": "自动（来自可能性评估）"})

    for c in d.get("corrections", []) or []:
        ev = str(c.get("evidence") or "")
        if DERIVED_MARK_RE.search(ev):
            items.append({"item": "「%s」反超所依据的数据需真实回填核验" % (c.get("data_shows") or "?"),
                          "why": "该依据含测算/假设/待考证标记，不是已验证数据（R2）",
                          "how": "用真实订单/财务/回填数据复算该算式", "src": "自动（来自校正表证据含测算）"})

    # 去重（按 item）
    seen, out = set(), []
    for it in items:
        if it["item"] in seen:
            continue
        seen.add(it["item"])
        out.append(it)
    return out


def _section_redlines(d, L, corr, verify_items, pct_hits):
    A = L.append
    A("## 5. 诚实红线 R1-R4 自查表")
    A("")
    hon = d.get("honesty", {}) or {}
    text_all = json.dumps(d, ensure_ascii=False)

    if pct_hits:
        r1 = "⚠️ 可能性评估出现 %d 处百分比表述（%s），须改为 高/中/低" % (len(pct_hits), "、".join(pct_hits[:3]))
    else:
        r1 = "✅ 可能性级别仅用 高/中/低，无百分比伪装测量"
    if not str(hon.get("R1") or "").strip():
        r1 += "；但 R1 未作答"

    if "已验证" in text_all:
        r2 = "⚠️ 文中出现「已验证」——请人工确认其背后有真实回填数据，否则改标「测算」"
    elif DERIVED_MARK_RE.search(text_all):
        r2 = "✅ 未冒称已验证（可见测算/假设类标记）"
    else:
        r2 = "✅ 未出现「已验证」表述"

    r3 = "✅ 已作答" if str(hon.get("R3") or "").strip() else "⚠️ 未作答（打架数字 / 无源数字尚未标注）"
    if corr and not str(hon.get("R3") or "").strip():
        r3 += "；注意校正表已有 %d 条差异，请确认其中数据来源是否标注" % len(corr)

    r4 = ("✅ 已列 %d 项待真实验证" % len(verify_items)) if verify_items \
        else "❌ 未列——不得把推演结论当已可行"

    L.extend(_md_table(["编码", "红线", "本次自查问题", "本次作答", "判定"],
                       [["R1", REDLINE_MAP["R1"][0], REDLINE_MAP["R1"][2], hon.get("R1") or "（未作答）", r1],
                        ["R2", REDLINE_MAP["R2"][0], REDLINE_MAP["R2"][2], hon.get("R2") or "（未作答）", r2],
                        ["R3", REDLINE_MAP["R3"][0], REDLINE_MAP["R3"][2], hon.get("R3") or "（未作答）", r3],
                        ["R4", REDLINE_MAP["R4"][0], REDLINE_MAP["R4"][2], hon.get("R4") or "（未作答）", r4]]))
    A("### R4 · 待真实验证项（**未验证前不得对外宣称可行**）")
    A("")
    if verify_items:
        L.extend(_md_table(["#", "待验证项", "为什么必须真实验证", "怎么验", "来源"],
                           [[i + 1, v["item"], v["why"], v["how"], v["src"]] for i, v in enumerate(verify_items)]))
    else:
        A("❌ **未列出任何待真实验证项 —— R4 不通过。**")
        A("")
        A("推演只产出假设。在列出「谁去验、用什么数据验」之前，本次四跑的所有结论只能当假设用。")
        A("")
    A("")


def build_comparison(d, src_path=None):
    topic = d.get("topic") or "（未命名主题）"
    corr = d.get("corrections", []) or []
    verify_items = _derive_verify_items(d)

    L = []
    A = L.append
    A("# 四跑法对比分析 · %s" % topic)
    A("")
    A("> 生成时间 %s · 框架 runfour.py v%s · 记录文件 %s · 建立日期 %s"
      % (_now(), VERSION, src_path or FOUR_JSON, d.get("created") or "?"))
    A("")

    A("## 0. 一句话（本方法的核心产出）")
    A("")
    if corr:
        chains = ["%s → %s" % (c.get("blank_thought") or "?", c.get("data_shows") or "?") for c in corr]
        head = "；".join(chains[:3])
        more = "（另 %d 条见校正表）" % (len(chains) - 3) if len(chains) > 3 else ""
        A("**数据跑纠正了空跑的 %d 处判断：%s%s。**" % (len(corr), head, more))
    else:
        A("⚠️ **校正表为空 —— 答不出「数据跑纠正了空跑的什么判断」。**")
        A("")
        A("> %s" % CORE_HINT)
    A("")

    _section_summaries(d, L)
    _section_corrections(d, L)
    _section_methodology(d, L, corr)
    pct_hits = _section_feasibility(d, L)
    _section_redlines(d, L, corr, verify_items, pct_hits)

    A("---")
    A("")
    A("> 本文件由 runfour.py compare 生成，内容全部来自 four.json 的填写；框架只做结构化对比，")
    A("> 不新增任何事实。**分数是判断不是测量（R1），测算 ≠ 验证（R2）。**")
    A("")
    return "\n".join(L)


def cmd_compare(args):
    data, p = load_four(args.dir)
    md = build_comparison(data, src_path=p)
    out = _e(args.out) if args.out else os.path.join(os.path.dirname(p), COMPARISON_MD)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)

    print(md)
    print("─" * 60)
    print("✅ 对比分析已生成: %s" % out)
    corr = data.get("corrections", []) or []
    verify_items = _derive_verify_items(data)
    if not corr:
        print("⚠️ 校正表为空 —— %s" % CORE_HINT)
        if args.strict:
            return 2
    else:
        print("★ 校正表 %d 条 · 待真实验证项 %d 条" % (len(corr), len(verify_items)))
    if not verify_items:
        print("❌ R4 不通过：未列出待真实验证项")
        if args.strict:
            return 2
    return 0


# ─────────────────────────────── score ───────────────────────────────
def _wargame_path():
    for c in _WARGAME_CANDIDATES:
        if os.path.exists(c):
            return c
    return None


def cmd_score(args):
    data, p = load_four(args.dir)
    pos = _e(args.positions)
    if not os.path.exists(pos):
        print("❌ 找不到 positions.json: %s" % pos)
        print("   格式（同 wargame-sim）: [{\"name\":\"…\",\"moat\":8,\"ceiling\":7,\"entry\":6,\"cap\":5,\"cash\":6,\"risk\":3}]")
        return 1
    tool = _wargame_path()
    if not tool:
        print("❌ 找不到 wargame-sim.py（找过: %s）" % " , ".join(_WARGAME_CANDIDATES))
        return 1

    cmd = [sys.executable, tool, "value", "--file", pos]
    print("▶ 调用现有引擎: %s" % " ".join(cmd))
    print("")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as ex:
        print("❌ 执行失败: %s" % ex)
        return 1
    out = (r.stdout or "") + (r.stderr or "")
    print(out.rstrip())
    print("")

    d = os.path.dirname(p)
    sp = os.path.join(d, "score.txt")
    ts = os.path.join(d, "score-%s.txt" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    header = "# 六维打分（runfour.py score 调 wargame-sim.py value）\n# 主题: %s\n# 时间: %s\n# positions: %s\n# 退出码: %d\n\n" % (
        data.get("topic") or "?", _now(), pos, r.returncode)
    for f in (sp, ts):
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(header + out)
    data.setdefault("score", {})
    data["score"] = {"positions": pos, "at": _now(), "exit": r.returncode,
                     "output": out.strip(), "file": sp}
    save_four(data, p)

    print("✅ 已保存: %s" % sp)
    print("   （同时留档 %s）" % os.path.basename(ts))
    if r.returncode != 0:
        print("⚠️ wargame-sim.py 退出码 %d —— 打分未正常完成" % r.returncode)
        return r.returncode
    return 0


# ─────────────────────────────── main ───────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        prog="runfour.py",
        description="四跑法标准框架（正跑/反跑/空数据跑/数据跑）· 结构化记录 + 对比分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="四跑定义:\n" + "\n".join(
            "  %-8s %-6s %s → %s" % (r["key"], r["label"], r["what"], r["key_out"]) for r in RUNS)
        + "\n\n⚠️ %s\n" % CORE_HINT)
    ap.add_argument("--version", action="version", version="runfour.py v%s" % VERSION)
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("init", help="为四跑法生成记录模板")
    p1.add_argument("topic", help="主题")
    p1.add_argument("--out", "-o", default=None, help="输出目录（默认 ./four-<主题>）")
    p1.add_argument("--date", default=None, help="建立日期（默认今天）")
    p1.add_argument("--force", action="store_true", help="覆盖已存在的 four.json")
    p1.set_defaults(func=cmd_init)

    p2 = sub.add_parser("fill", help="填入每一跑的结果（交互或用文件）")
    p2.add_argument("dir", help="四跑记录目录（含 four.json）")
    p2.add_argument("--run", "-r", required=True,
                    help="目标：%s" % "/".join(RUN_KEYS + ["corrections", "feasibility", "honesty", "verify_items", "all"]))
    p2.add_argument("--judgments", "-j", default=None, help="JSON 文件（正跑判断 / 反跑前置条件 / 空跑排序 / 数据跑算式 …）")
    p2.add_argument("--file", "-f", default=None, help="同 --judgments")
    p2.add_argument("--summary", "-s", default=None, help="该跑的小结（一段话）")
    p2.set_defaults(func=cmd_fill)

    p3 = sub.add_parser("compare", help="★ 生成对比分析（空跑 vs 数据跑的差异）")
    p3.add_argument("dir", help="四跑记录目录（含 four.json）")
    p3.add_argument("--out", "-o", default=None, help="输出 md（默认 <dir>/COMPARISON.md）")
    p3.add_argument("--strict", action="store_true",
                    help="校正表为空 / R4 未列验证项时以退出码 2 结束（推演未做透）")
    p3.set_defaults(func=cmd_compare)

    p4 = sub.add_parser("score", help="用现有引擎做六维打分（调 wargame-sim.py value）")
    p4.add_argument("dir", help="四跑记录目录（含 four.json）")
    p4.add_argument("--positions", "-p", required=True, help="positions.json（name/moat/ceiling/entry/cap/cash/risk）")
    p4.set_defaults(func=cmd_score)

    args = ap.parse_args()
    if not getattr(args, "func", None):
        ap.print_help()
        print("\n⚠️ %s" % CORE_HINT)
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
