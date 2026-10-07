#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unit-review.py — 逐单元语义审查工具链（切分 → 派任务 → 合并结果）

为什么存在
----------
关键词搜索做审查漏报率极高：同一份文档，关键词法报「12 项全通过」，
改成逐单元语义审查后发现 570 项。但逐单元审查目前全靠手工 —— 本工具把它流水线化。

子命令
------
  pack    <file.md> --out DIR [--context 3] [--max-units 40]
          把文档切成语义单元，生成 units.json + PROMPT.md（+ results/ 目录）

  merge   results/*.json --out FINDINGS.md [--units units.json]
          合并多份审查结果：核验覆盖度、按 unit_id 去重、档位分歧单列

  preview <file.md> [--limit 60]
          只预览切分结果，不生成任务包

切分规则（按语义边界，不按行）
------------------------------
  heading     # ~ ###### 开头的行（每个标题独立成单元）
  table_row   | 开头的行，连续表格行合成一个单元（含表头）
  list_item   - / * / 1. 开头，连续列表项合成一个单元
  code        ``` 围栏内，整体一个单元
  para        其他连续非空行

零外部依赖（Python 3.9+ 标准库），中文输出。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

# ---------------------------------------------------------------- 常量

DEFAULT_CONTEXT = 3
DEFAULT_MAX_UNITS = 40
DEFAULT_COVERAGE_THRESHOLD = 0.9

SEV_MUST = "必须改"
SEV_OPT = "可选优化"
SEV_KEEP = "明确不要改"
SEV_UNRATED = "未分级"
SEV_ORDER = [SEV_MUST, SEV_OPT, SEV_KEEP]

UNIT_TYPES = ["heading", "table_row", "list_item", "code", "para"]
MERGEABLE = ("table_row", "list_item", "code", "para")  # 连续同类合并成单元

HEADING_RE = re.compile(r"^#{1,6}(?:\s|$)")
TABLE_RE = re.compile(r"^\s*\|")
LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")

BAR = "=" * 64


# ---------------------------------------------------------------- 工具函数

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fenced(text):
    """用围栏包住任意文本（文本自身含 ``` 时升级为四反引号）。"""
    fence = "````" if "```" in text else "```"
    return "%s\n%s\n%s" % (fence, text, fence)


def line_span(unit):
    if unit["start_line"] == unit["end_line"]:
        return str(unit["start_line"])
    return "%d-%d" % (unit["start_line"], unit["end_line"])


def clip(text, n=64):
    flat = text.replace("\n", " ⏎ ")
    return flat if len(flat) <= n else flat[:n] + "…"


# ---------------------------------------------------------------- 切分

def classify(line, in_code):
    if in_code:
        return "code"
    if FENCE_RE.match(line):
        return "code"
    if HEADING_RE.match(line):
        return "heading"
    if TABLE_RE.match(line):
        return "table_row"
    if LIST_RE.match(line):
        return "list_item"
    if not line.strip():
        return "blank"
    return "para"


def segment(text):
    """把文本切成语义单元（未编号）。"""
    lines = text.split("\n")
    units = []
    cur = None
    in_code = False

    def flush():
        nonlocal cur
        if cur is not None and any(l.strip() for l in cur["lines"]):
            units.append(cur)
        cur = None

    for lineno, line in enumerate(lines, start=1):
        kind = classify(line, in_code)
        if kind == "blank":
            flush()
            continue
        if cur is not None and cur["type"] == kind and kind in MERGEABLE:
            cur["lines"].append(line)
            cur["end_line"] = lineno
        else:
            flush()
            cur = {"type": kind, "start_line": lineno, "end_line": lineno, "lines": [line]}
        if FENCE_RE.match(line):
            in_code = not in_code

    flush()
    return units, in_code  # in_code 残留 True = 围栏没闭合


def build_units(text):
    raw, unclosed = segment(text)
    width = max(3, len(str(len(raw))))
    units = []
    for i, u in enumerate(raw, start=1):
        body = "\n".join(u["lines"])
        units.append({
            "id": "U" + str(i).zfill(width),
            "type": u["type"],
            "start_line": u["start_line"],
            "end_line": u["end_line"],
            "line_count": u["end_line"] - u["start_line"] + 1,
            "chars": len(body),
            "text": body,
        })
    return units, unclosed


def type_histogram(units):
    hist = {}
    for u in units:
        hist[u["type"]] = hist.get(u["type"], 0) + 1
    return hist


def hist_str(hist):
    return " / ".join("%s %d" % (t, hist[t]) for t in UNIT_TYPES if hist.get(t))


def context_of(units, index, ctx):
    """返回 (上文列表, 下文列表)，元素带 unit 与相对位置。"""
    lo = max(0, index - ctx)
    hi = min(len(units), index + 1 + ctx)
    before = units[lo:index]
    after = units[index + 1:hi]
    return before, after


# ---------------------------------------------------------------- preview

def cmd_preview(args):
    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        print("❌ 找不到文件：%s" % src)
        return 2
    text = read_text(src)
    units, unclosed = build_units(text)
    hist = type_histogram(units)

    print("切分预览 · %s" % os.path.basename(src))
    print(BAR)
    print("单元总数：%d" % len(units))
    print("类型分布：%s" % (hist_str(hist) or "（空文档）"))
    print("行数总计：%d" % len(text.split("\n")))
    if unclosed:
        print("⚠️ 代码围栏未闭合（``` 数量为奇数），最后一段可能被整体并入 code 单元")
    print("-" * 64)
    limit = args.limit
    for u in units[:limit]:
        print("%s  %-9s L%-7s %s" % (u["id"], u["type"], line_span(u), clip(u["text"])))
    if len(units) > limit:
        print("…（其余 %d 个单元未显示，--limit 可调）" % (len(units) - limit))
    return 0


# ---------------------------------------------------------------- pack

KEY_PROMPT = (
    "不要只报「含敏感词」的行；要报「**读起来不对**」的行。\n"
    "判断标准：删掉这句话，读者是否少知道一个关于生意的事实？如果答\"是\"，它可能是元话语。"
)

RULES_7 = """1. **必须具体引用原文** —— `original` 必须是原文里的逐字片段（可截断，不可改写、不可概括）。
2. **必须给可直接替换的句子** —— `suggest` 要能整句贴回原文替换掉原句；写「建议优化」「表达更清晰」这类空话等于没交作业。
3. **区分「必须改」与「不要改」** —— 每个你读过的单元都要表态：该动的写 `必须改`，不该动的写 `明确不要改` 并说清为什么不要动（防止下一轮把好句子改坏）。
4. **必须回报 units_reviewed** —— 如实填写你真正读完的单元数；没读完就写实际数字，不许凑数。抽样审查会被自动标为「⚠️ 疑似抽样」。
5. **不编造** —— 行号、单元号、原文片段都必须来自任务包；拿不准的写进 `issue` 里标明「不确定」。
6. **结果写进指定文件** —— 只写指定的 JSON 文件，内容只放合法 JSON（不要 markdown 围栏、不要解释性前言）。
7. **不修改被审文件** —— 源文档和 units.json 一律只读；你的产出只有结果 JSON。
"""


def render_prompt(src, units_all, batch_ids, batch_index, batch_count, ctx, results_dir, out_dir):
    total_all = len(units_all)
    batch_size = len(batch_ids)
    index_of = {u["id"]: i for i, u in enumerate(units_all)}

    out = []
    out.append("# 逐单元语义审查任务包")
    out.append("")
    out.append("## 一、角色设定")
    out.append("")
    out.append("**你是一名严格的内容审查员。**")
    out.append("")
    out.append("你的任务不是找敏感词，而是逐个单元判断：这句话读起来对不对、该不该出现在这份文档里。")
    out.append("关键词法的漏报率极高（同一份文档，关键词法报「12 项全通过」，逐单元语义审查会发现 570 项），")
    out.append("所以**不许用关键词扫描代替阅读**，必须逐单元读完再下判断。")
    out.append("")
    out.append("## 二、审查范围")
    out.append("")
    out.append("本次共 %d 个单元，你必须全部读过。" % batch_size)
    if batch_count > 1:
        others = "、".join(
            ("PROMPT.md" if i == 1 else "PROMPT-%03d.md" % i)
            for i in range(1, batch_count + 1) if i != batch_index
        )
        out.append("")
        out.append("> 全文共 %d 个单元，本篇是第 %d/%d 批（其余批次见 %s）。"
                   % (total_all, batch_index, batch_count, others))
    out.append("")
    out.append("- 源文件：`%s`" % src)
    out.append("- 结果写到：`%s`（文件名自取，建议 `%s/审查员名.json`）" % (results_dir, results_dir))
    out.append("- 上下文：每个单元附带前后各 %d 个单元，**仅用于理解语境，不列入本批审查对象**。" % ctx)
    out.append("")
    out.append("### 本批单元清单（%d 个，逐个读完，一个都不许跳）" % batch_size)
    out.append("")
    out.append("| # | 单元 | 类型 | 行号 | 字数 |")
    out.append("|---|------|------|------|------|")
    for n, u in enumerate(batch_ids, start=1):
        out.append("| %d | %s | %s | %s | %d |" % (n, u["id"], u["type"], line_span(u), u["chars"]))
    out.append("")
    out.append("## 三、审查单元（含上下文，内联全文）")
    out.append("")

    for u in batch_ids:
        i = index_of[u["id"]]
        before, after = context_of(units_all, i, ctx)
        out.append("---")
        out.append("")
        out.append("### ★ 审查目标 %s · %s · 第 %s 行" % (u["id"], u["type"], line_span(u)))
        out.append("")
        if before:
            out.append("【上文（上下文，不审）】")
            out.append("")
            for b in before:
                out.append("`%s` · %s · 第 %s 行" % (b["id"], b["type"], line_span(b)))
                out.append("")
                out.append(fenced(b["text"]))
                out.append("")
        out.append("【★ 本单元（审查目标）】")
        out.append("")
        out.append(fenced(u["text"]))
        out.append("")
        if after:
            out.append("【下文（上下文，不审）】")
            out.append("")
            for a in after:
                out.append("`%s` · %s · 第 %s 行" % (a["id"], a["type"], line_span(a)))
                out.append("")
                out.append(fenced(a["text"]))
                out.append("")
    out.append("---")
    out.append("")
    out.append("## 四、七条铁律")
    out.append("")
    out.append(RULES_7.rstrip())
    out.append("")
    out.append("## 五、★ 关键提示词")
    out.append("")
    for ln in KEY_PROMPT.split("\n"):
        out.append("> " + ln)
    out.append("")
    out.append("## 六、机器可读输出契约")
    out.append("")
    out.append("结果只写一个 JSON 文件，字段固定如下（下面的数字是示例值，`units_reviewed` 必须填你实际读完的数量）：")
    out.append("")
    sample = {
        "reviewer": "视角名或审查员名",
        "units_reviewed": batch_size,
        "units_total": batch_size,
        "findings": [
            {
                "unit_id": "U012",
                "line": 45,
                "severity": "必须改",
                "issue": "这句话只交代了过程，没有交代读者需要的事实",
                "original": "原文片段（逐字）",
                "suggest": "可直接替换的句子",
            }
        ],
    }
    out.append("```json")
    out.append(json.dumps(sample, ensure_ascii=False, indent=2))
    out.append("```")
    out.append("")
    out.append("- `severity` 只能取三个值之一：`必须改` / `可选优化` / `明确不要改`。")
    out.append("- `unit_id` 必须是本批清单里的单元号；`line` 用该单元的起始行号。")
    out.append("- `findings` 可以为空数组，但**每个单元你都要在心里过一遍**；不打算改的单元用 `明确不要改` 表态。")
    out.append("- `units_total` 固定填 %d（本批单元总数），`units_reviewed` 填你实际读过的数量。" % batch_size)
    out.append("")
    out.append("## 七、最后再说一遍")
    out.append("")
    out.append("不许抽样。不许用关键词代替阅读。不许修改被审文件（`%s` 只读）。" % src)
    out.append("")
    return "\n".join(out)


def cmd_pack(args):
    src = os.path.abspath(args.file)
    if not os.path.isfile(src):
        print("❌ 找不到文件：%s" % src)
        return 2

    text = read_text(src)
    units, unclosed = build_units(text)
    total = len(units)
    hist = type_histogram(units)
    out_dir = os.path.abspath(args.out)
    results_dir = os.path.join(out_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    ctx = max(0, args.context)
    max_units = max(1, args.max_units)

    units_json = {
        "source": src,
        "generated_at": now_str(),
        "context": ctx,
        "max_units_per_prompt": max_units,
        "total_units": total,
        "type_counts": hist,
        "units": [
            dict(
                {
                    "id": u["id"],
                    "type": u["type"],
                    "start_line": u["start_line"],
                    "end_line": u["end_line"],
                    "line_count": u["line_count"],
                    "chars": u["chars"],
                    "text": u["text"],
                },
                # 每个单元自带前后各 ctx 个单元作为上下文（默认 3）
                context_before=[
                    {"id": b["id"], "type": b["type"], "start_line": b["start_line"], "text": b["text"]}
                    for b in context_of(units, i, ctx)[0]
                ],
                context_after=[
                    {"id": a["id"], "type": a["type"], "start_line": a["start_line"], "text": a["text"]}
                    for a in context_of(units, i, ctx)[1]
                ],
            )
            for i, u in enumerate(units)
        ],
    }
    units_path = os.path.join(out_dir, "units.json")
    write_text(units_path, json.dumps(units_json, ensure_ascii=False, indent=2) + "\n")

    batches = [units[i:i + max_units] for i in range(0, total, max_units)] or [[]]
    prompt_paths = []
    for bi, batch in enumerate(batches, start=1):
        name = "PROMPT.md" if bi == 1 else "PROMPT-%03d.md" % bi
        path = os.path.join(out_dir, name)
        write_text(path, render_prompt(src, units, batch, bi, len(batches), ctx, results_dir, out_dir))
        prompt_paths.append((name, len(batch)))

    print("任务包已生成 · %s" % out_dir)
    print(BAR)
    print("源文件　：%s" % src)
    print("单元总数：%d（%s）" % (total, hist_str(hist) or "空文档"))
    print("上下文　：前后各 %d 个单元" % ctx)
    print("每包上限：%d 个单元" % max_units)
    if unclosed:
        print("⚠️ 代码围栏未闭合（``` 数量为奇数），请先修源文件再派任务")
    print("-" * 64)
    for name, size in prompt_paths:
        print("提示词　：%s（本批 %d 个单元）" % (os.path.join(out_dir, name), size))
    print("单元清单：%s" % units_path)
    print("结果目录：%s  ← 审查员把 JSON 写到这里" % results_dir)
    return 0


# ---------------------------------------------------------------- merge

def normalize_severity(value):
    s = str(value or "").strip()
    if not s:
        return SEV_UNRATED
    if s in SEV_ORDER:
        return s
    low = s.lower()
    if "不要" in s or "不该" in s or "无需" in s or "保持" in s or "no change" in low or "keep" in low:
        return SEV_KEEP
    if "必须" in s or "必修" in s or "must" in low or "blocker" in low or "critical" in low:
        return SEV_MUST
    if "可选" in s or "建议" in s or "优化" in s or "optional" in low or "should" in low or "minor" in low:
        return SEV_OPT
    return SEV_UNRATED


def load_result(path):
    raw = read_text(path).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    data = json.loads(raw)
    if isinstance(data, list):
        return {"reviewer": os.path.basename(path), "findings": data}
    return data


def collect_results(paths):
    reviewers = []
    problems = []
    for p in paths:
        try:
            data = load_result(p)
        except Exception as exc:  # noqa: BLE001
            problems.append((p, "JSON 解析失败：%s" % exc))
            continue
        name = str(data.get("reviewer") or os.path.splitext(os.path.basename(p))[0]).strip()
        findings = data.get("findings") or []
        if not isinstance(findings, list):
            problems.append((p, "findings 不是数组，已忽略"))
            findings = []
        norm = []
        for f in findings:
            if not isinstance(f, dict):
                continue
            norm.append({
                "unit_id": str(f.get("unit_id") or "").strip(),
                "line": f.get("line"),
                "severity": normalize_severity(f.get("severity")),
                "severity_raw": str(f.get("severity") or "").strip(),
                "issue": str(f.get("issue") or "").strip(),
                "original": str(f.get("original") or "").strip(),
                "suggest": str(f.get("suggest") or "").strip(),
                "reviewer": name,
                "source": p,
            })
        reviewers.append({
            "path": p,
            "name": name,
            "units_reviewed": data.get("units_reviewed"),
            "units_total": data.get("units_total"),
            "findings": norm,
        })
    return reviewers, problems


def dedup_findings(findings):
    """按 (unit_id/line, severity, issue) 去重合并。"""
    groups = {}
    order = []
    for f in findings:
        ukey = f["unit_id"] or ("line:%s" % f["line"])
        ikey = re.sub(r"\s+", "", f["issue"])[:80]
        key = (ukey, f["severity"], ikey)
        if key not in groups:
            groups[key] = {
                "unit_id": f["unit_id"],
                "line": f["line"],
                "severity": f["severity"],
                "issue": f["issue"],
                "original": f["original"],
                "suggest": f["suggest"],
                "reviewers": [],
                "dupes": 0,
            }
            order.append(key)
        g = groups[key]
        if f["reviewer"] not in g["reviewers"]:
            g["reviewers"].append(f["reviewer"])
        else:
            g["dupes"] += 1
        if not g["original"] and f["original"]:
            g["original"] = f["original"]
        if not g["suggest"] and f["suggest"]:
            g["suggest"] = f["suggest"]
    return [groups[k] for k in order]


def cmd_merge(args):
    paths = []
    for pat in args.results:
        hits = sorted(glob.glob(pat))
        paths.extend(hits if hits else ([pat] if os.path.isfile(pat) else []))
    seen = set()
    paths = [p for p in paths if not (p in seen or seen.add(p))]
    if not paths:
        print("❌ 没有匹配到任何结果文件：%s" % " ".join(args.results))
        return 2

    reviewers, problems = collect_results(paths)

    # units.json：显式指定，或在 results 同级/上级自动查找
    units_path = args.units
    if not units_path:
        for cand in (
            os.path.join(os.path.dirname(os.path.abspath(paths[0])), "units.json"),
            os.path.join(os.path.dirname(os.path.abspath(paths[0])), "..", "units.json"),
            "units.json",
        ):
            if os.path.isfile(cand):
                units_path = cand
                break
    units_meta = None
    if units_path and os.path.isfile(units_path):
        try:
            units_meta = json.loads(read_text(units_path))
        except Exception:  # noqa: BLE001
            units_meta = None

    all_findings = [f for r in reviewers for f in r["findings"]]
    merged = dedup_findings(all_findings)

    by_sev = {SEV_MUST: [], SEV_OPT: [], SEV_KEEP: [], SEV_UNRATED: []}
    for m in merged:
        by_sev[m["severity"]].append(m)

    # 档位分歧：同一 unit_id 出现 ≥2 种真实档位
    unit_sevs = {}
    for m in merged:
        if m["severity"] == SEV_UNRATED or not m["unit_id"]:
            continue
        unit_sevs.setdefault(m["unit_id"], {})
        unit_sevs[m["unit_id"]].setdefault(m["severity"], []).append(m)
    conflicts = {u: s for u, s in unit_sevs.items() if len(s) > 1}
    conflict_marked = set(conflicts)

    threshold = args.coverage_threshold
    total_units = (units_meta or {}).get("total_units")
    all_unit_ids = [u["id"] for u in (units_meta or {}).get("units", []) or []]

    covered = set()
    for r in reviewers:
        for f in r["findings"]:
            if f["unit_id"]:
                covered.add(f["unit_id"])
    if all_unit_ids:
        covered &= set(all_unit_ids)
        uncovered = [u for u in all_unit_ids if u not in covered]
    else:
        uncovered = []

    out = []
    out.append("# 审查结果合并报告")
    out.append("")
    out.append("- 生成时间：%s" % now_str())
    out.append("- 输入结果：%d 份" % len(reviewers))
    if problems:
        out.append("- ⚠️ 解析问题：%d 条（见文末）" % len(problems))
    out.append("- 审查员：%s" % ("、".join(r["name"] for r in reviewers) or "（无）"))
    out.append("- findings：原始 %d 条 → 去重后 %d 条" % (len(all_findings), len(merged)))
    if total_units is not None:
        out.append("- 单元总数：%s（来自 %s）" % (total_units, units_path))
    out.append("")

    def render_section(title, items, empty_hint):
        out.append("## %s" % title)
        out.append("")
        out.append("（%d 项）" % len(items))
        out.append("")
        if not items:
            out.append("_%s_" % empty_hint)
            out.append("")
            return
        for m in items:
            head = m["unit_id"] or ("行 %s" % m["line"])
            tags = []
            if m["unit_id"] in conflict_marked:
                tags.append("⚠️ 档位分歧")
            if m["severity"] == SEV_UNRATED:
                tags.append("未分级（原值：%s）" % (m["severity_raw"] or "空"))
            out.append("### %s · 第 %s 行%s" % (head, m["line"] if m["line"] is not None else "?", " " + " ".join(tags) if tags else ""))
            out.append("")
            out.append("- 问题：%s" % (m["issue"] or "（未填写）"))
            if m["original"]:
                out.append("- 原文：`%s`" % m["original"].replace("`", "'"))
            if m["suggest"]:
                out.append("- 建议替换：%s" % m["suggest"])
            out.append("- 审查员：%s%s" % ("、".join(m["reviewers"]), "（%d 份重复提交已合并）" % m["dupes"] if m["dupes"] else ""))
            out.append("")

    render_section(SEV_MUST, by_sev[SEV_MUST], "没有「必须改」的条目。")
    render_section(SEV_OPT, by_sev[SEV_OPT] + by_sev[SEV_UNRATED], "没有「可选优化」的条目。")
    render_section(SEV_KEEP, by_sev[SEV_KEEP], "没有「明确不要改」的条目。")

    out.append("## 冲突")
    out.append("")
    out.append("（%d 项）" % len(conflicts))
    out.append("")
    if not conflicts:
        out.append("_各审查员档位一致，无冲突。_")
        out.append("")
    else:
        out.append("下列单元在不同审查员之间档位不一致；条目仍保留在上方对应档位章节中，未做取舍，请人工裁决。")
        out.append("")
        for uid in sorted(conflicts):
            out.append("### %s" % uid)
            out.append("")
            for sev in SEV_ORDER:
                for m in conflicts[uid].get(sev, []):
                    out.append("- **%s**（%s）：%s" % (
                        sev,
                        "、".join(m["reviewers"]),
                        m["issue"] or "（未填写）",
                    ))
                    if m["suggest"]:
                        out.append("  - 建议：%s" % m["suggest"])
            out.append("")

    out.append("## 审查覆盖度")
    out.append("")
    out.append("| 审查员 | units_reviewed | units_total | 覆盖率 | 判定 |")
    out.append("|--------|---------------|-------------|--------|------|")
    for r in reviewers:
        rev, tot = r["units_reviewed"], r["units_total"]
        try:
            ratio = float(rev) / float(tot) if float(tot) > 0 else None
        except (TypeError, ValueError):
            ratio = None
        if ratio is None:
            pct, verdict = "—", "⚠️ 未提供 units_reviewed/units_total"
        else:
            pct = "%.0f%%" % (ratio * 100)
            verdict = "✅ 覆盖达标" if ratio >= threshold else "⚠️ 疑似抽样"
        out.append("| %s | %s | %s | %s | %s |" % (
            r["name"],
            rev if rev is not None else "—",
            tot if tot is not None else "—",
            pct,
            verdict,
        ))
    out.append("")
    out.append("判定阈值：`units_reviewed / units_total >= %.0f%%`，低于该值标「⚠️ 疑似抽样」。" % (threshold * 100))
    out.append("")
    if all_unit_ids:
        cov_pct = 100.0 * len(covered) / len(all_unit_ids)
        out.append("- 单元级覆盖（有 finding 的单元视为被读到）：%d/%d（%.0f%%）" % (len(covered), len(all_unit_ids), cov_pct))
        if uncovered:
            shown = "、".join(uncovered[:60])
            more = "" if len(uncovered) <= 60 else " …（共 %d 个）" % len(uncovered)
            out.append("- 未被任何审查员触及的单元（%d 个）：%s%s" % (len(uncovered), shown, more))
            out.append("  - 注意：单元没有 finding 属正常（不打算改），这里只表示该单元没被写进任何结果；")
            out.append("    若要严格核对「是否真读过」，以各审查员的 units_reviewed 为准。")
        else:
            out.append("- ✅ 每个单元都至少被一名审查员触及。")
    else:
        out.append("- 未找到 units.json，无法做单元级覆盖核算（可用 `--units` 指定）。")
    out.append("")
    out.append("### 档位统计")
    out.append("")
    out.append("- 必须改：%d" % len(by_sev[SEV_MUST]))
    out.append("- 可选优化：%d" % len(by_sev[SEV_OPT]))
    out.append("- 明确不要改：%d" % len(by_sev[SEV_KEEP]))
    if by_sev[SEV_UNRATED]:
        out.append("- 未分级：%d" % len(by_sev[SEV_UNRATED]))
    out.append("- 冲突单元：%d" % len(conflicts))
    out.append("")

    if problems:
        out.append("### 解析问题")
        out.append("")
        for p, msg in problems:
            out.append("- `%s`：%s" % (p, msg))
        out.append("")

    dest = os.path.abspath(args.out)
    write_text(dest, "\n".join(out))

    print("审查结果已合并 · %s" % dest)
    print(BAR)
    print("输入结果：%d 份（%s）" % (len(reviewers), "、".join(r["name"] for r in reviewers) or "无"))
    print("findings：原始 %d 条 → 去重后 %d 条" % (len(all_findings), len(merged)))
    print("必须改 %d / 可选优化 %d / 明确不要改 %d%s" % (
        len(by_sev[SEV_MUST]), len(by_sev[SEV_OPT]), len(by_sev[SEV_KEEP]),
        " / 未分级 %d" % len(by_sev[SEV_UNRATED]) if by_sev[SEV_UNRATED] else "",
    ))
    print("冲突单元：%d" % len(conflicts))
    print("-" * 64)
    for r in reviewers:
        rev, tot = r["units_reviewed"], r["units_total"]
        try:
            ratio = float(rev) / float(tot) if float(tot) > 0 else None
        except (TypeError, ValueError):
            ratio = None
        verdict = "⚠️ 疑似抽样" if (ratio is not None and ratio < threshold) else ("✅ 覆盖达标" if ratio is not None else "⚠️ 缺字段")
        print("覆盖度　：%-16s %s/%s  %s" % (
            r["name"], rev if rev is not None else "—", tot if tot is not None else "—", verdict))
    if all_unit_ids:
        print("单元覆盖：%d/%d" % (len(covered), len(all_unit_ids)))
    if problems:
        print("⚠️ 解析问题：%d 条（见报告文末）" % len(problems))
    return 0


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(
        prog="unit-review.py",
        description="逐单元语义审查工具链：切单元 → 生成任务包 → 合并审查结果",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  unit-review.py preview doc.md
  unit-review.py pack doc.md --out /tmp/ur/ --context 3 --max-units 40
  unit-review.py merge /tmp/ur/results/*.json --out FINDINGS.md
""",
    )
    sub = p.add_subparsers(dest="cmd")

    pk = sub.add_parser("pack", help="切单元并生成审查任务包")
    pk.add_argument("file", help="待审查的 markdown 文件")
    pk.add_argument("--out", required=True, help="输出目录，如 /tmp/ur/")
    pk.add_argument("--context", type=int, default=DEFAULT_CONTEXT, help="前后各 N 个单元作为上下文（默认 3）")
    pk.add_argument("--max-units", type=int, default=DEFAULT_MAX_UNITS, help="单个任务包的最大单元数（默认 40）")
    pk.set_defaults(func=cmd_pack)

    mg = sub.add_parser("merge", help="合并审查结果 JSON")
    mg.add_argument("results", nargs="+", help="结果 JSON 路径（支持通配符）")
    mg.add_argument("--out", required=True, help="输出报告路径，如 FINDINGS.md")
    mg.add_argument("--units", help="units.json 路径（默认自动查找）")
    mg.add_argument("--coverage-threshold", type=float, default=DEFAULT_COVERAGE_THRESHOLD,
                    help="覆盖度阈值，低于此值标「疑似抽样」（默认 0.9）")
    mg.set_defaults(func=cmd_merge)

    pv = sub.add_parser("preview", help="预览切分结果")
    pv.add_argument("file", help="待预览的 markdown 文件")
    pv.add_argument("--limit", type=int, default=60, help="最多显示多少个单元（默认 60）")
    pv.set_defaults(func=cmd_preview)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
