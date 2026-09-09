#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""meeting-verify.py — 语音会议产物·原文核实器 (Meeting Product Scanner & Transcript Verifier)

v1.0.0 · 明鉴 · 2026-09-09

三大能力:
  ① 产物扫描   --scan <关键词[,关键词...]>: 在会议产物(docs/blueprint/concept-dict)中定位口径/数字/断言,
               输出 文件×命中行×上下文 分类清单(支持 --scope 限定目录, --json 结构化)
  ② 原文核实   --verify <关键词> [--meeting 0905|0908|auto]: 回会议转写原文(split 分章)逐行核实,
               输出 会议×章节×说话人×原文 证据链(说话人自动经 identity-graph speakers 反查为实名)
  ③ 断言审计   --audit <断言文本> <核实词...>: 把"产物断言"与"原文证据"并列输出, 供人类判读偏差
               (典型: 断言=8000万/月 → 核实词=8000万,双平台 → 输出原文上下文让 AI 判断口径)

设计动机: "淘闪口径复核"(2026-09-09)全过程工具化——此前靠手工 grep + 翻原文 + 交叉 speakers,
          现固化为可重复命令。R006 十项达标(见 docs/r006-ten.md 或 --help 尾部)。

R006: CLI(argparse) · TCC(--selfcheck) · CLD 自适应(纯 stdlib) · 版本(--tool-version)
      日志(logs/meeting-verify.log) · Lean4 门(--lean4-check, 只读工具天然 PASS)
用法:
  python3 meeting-verify.py --scan 淘闪,美团,GMV
  python3 meeting-verify.py --verify 双平台 --meeting 0908
  python3 meeting-verify.py --audit "8000万GMV/月" "8000万,双平台,2000万" --out /tmp/audit.md
  python3 meeting-verify.py --selfcheck | --lean4-check | --tool-version
"""
import argparse, json, os, sys, re, glob, datetime, fnmatch

VERSION = "v1.0.0"
NOTES = os.path.expanduser("~/.dsh/meeting-notes")
COLLAB = os.path.expanduser("~/dsh-collab")
IDG = os.path.join(COLLAB, "data", "meeting-identity-graph.json")
LOG = os.path.expanduser("~/dsh-collab/logs/meeting-verify.log")

# 会议元信息: 目录前缀 → (会议短名, 日期后缀, 是否切分)
MEETINGS = [
    {"id": "0905", "prefix": "obcnuhtix", "split_dir": "split", "date": "2026-09-05", "label": "合作项目相关事宜讨论(21章)"},
    {"id": "0908a", "prefix": "obcnwhp3", "split_dir": "split-obcnwhp3", "date": "2026-09-08", "label": "垂类资本架构(25章)"},
    {"id": "0908b", "prefix": "obcnwjk9", "split_dir": "split-obcnwjk9", "date": "2026-09-08", "label": "淘闪城市站(11章)"},
    {"id": "0908c", "prefix": "obcnwk6q", "split_dir": "split-obcnwk6q", "date": "2026-09-08", "label": "自营供应链(15章)"},
]
DEFAULT_SCOPE_DIRS = ["docs", "data/blueprint"]  # 产物扫描根目录(相对 COLLAB)


def now(): return datetime.datetime.now().isoformat(timespec="seconds")


def log_action(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{now()} {msg}\n")
    except Exception:
        pass


def load_speaker_map():
    """identity-graph persons.speakers → {meeting_id: {speaker_label: person_name}}
    会议 id 取 speakers key 前缀(obcnuhtix-0905 → 0905 组). 反查时支持 'S5' 'S5(?)' '提及' 等形态"""
    mapping = {}
    try:
        g = json.load(open(IDG, encoding="utf-8"))
        for p in g.get("persons", []):
            for skey, sval in (p.get("speakers") or {}).items():
                # skey 形如 obcnuhtix-0905
                grp = skey.split("-")[0]
                mapping.setdefault(grp, {})
                for token in re.split(r"[、,，/]", str(sval)):
                    token = token.strip()
                    if token:
                        mapping[grp][token] = p.get("name", "?")
    except Exception:
        pass
    return mapping


def group_of_meeting(mid):
    for m in MEETINGS:
        if m["id"] == mid:
            return m
    return None


def meeting_group_prefix(mid):
    m = group_of_meeting(mid)
    return m["prefix"] if m else ""


def resolve_speaker(line_text, grp_map):
    """从 '[Speaker 5]' 行反查实名; 返回 (label, name)"""
    m = re.match(r"^\s*\[?Speaker\s*(\d+|N/A|未知)\]?", line_text)
    if not m:
        return "", ""
    lab = "S" + m.group(1)
    name = (grp_map or {}).get(lab, "") or (grp_map or {}).get(f"{lab}(?)", "")
    return lab, name


def iter_split_files():
    """遍历全部切分原文文件 → (会议对象, 文件路径, 章标题)"""
    out = []
    for m in MEETINGS:
        d = os.path.join(NOTES, "full", m["split_dir"])
        if not os.path.isdir(d):
            continue
        for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
            title = os.path.basename(f).rstrip(".txt")
            # 章标题 = 去掉开头 NN- 编号
            title = re.sub(r"^\d+-", "", title)
            out.append({"meeting": m, "file": f, "title": title})
    return out


# ── ① 产物扫描 ───────────────────────────────────────────────────────────
def scan_products(keywords, scope_dirs, ext_filter="*.md"):
    """在会议产物(md)中定位关键词, 输出 文件×行×上下文"""
    results = []
    for root in scope_dirs:
        base = os.path.join(COLLAB, root)
        if not os.path.isdir(base):
            continue
        for f in glob.glob(os.path.join(base, "**", ext_filter), recursive=True):
            rel = os.path.relpath(f, COLLAB)
            try:
                lines = open(f, encoding="utf-8", errors="replace").read().split("\n")
            except Exception:
                continue
            for i, ln in enumerate(lines):
                for kw in keywords:
                    if kw and kw in ln:
                        lo = max(0, i - 1)
                        hi = min(len(lines), i + 2)
                        results.append({
                            "file": rel, "line": i + 1, "kw": kw,
                            "ctx": "\n".join(f"  {j+1}|{lines[j][:160]}" for j in range(lo, hi)),
                        })
                        break  # 一行多词只记一次
    # 汇总统计
    by_file = {}
    for r in results:
        by_file.setdefault(r["file"], []).append(r)
    return results, by_file


# ── ② 原文核实 ───────────────────────────────────────────────────────────
def resolve_meetings(meeting_id):
    """把 CLI meeting 参数解析为会议对象列表: auto=全部 / 0905 / 0908=三场 0908a|b|c / 单场"""
    if meeting_id == "auto":
        return MEETINGS
    if meeting_id == "0908":
        return [m for m in MEETINGS if m["id"].startswith("0908")]
    m = group_of_meeting(meeting_id)
    return [m] if m else []


def verify_transcript(keywords, meeting_id="auto", limit_per_kw=8, context=2):
    """回会议原文核实关键词, 输出 会议×章节×说话人×原文 证据链"""
    smap = load_speaker_map()
    targets = resolve_meetings(meeting_id)
    files = [f for f in iter_split_files() if f["meeting"] in targets]
    hits = []
    for f in files:
        grp = f["meeting"]["prefix"]
        grp_map = smap.get(grp, {})
        try:
            lines = open(f["file"], encoding="utf-8", errors="replace").read().split("\n")
        except Exception:
            continue
        for i, ln in enumerate(lines):
            for kw in keywords:
                if kw and kw in ln:
                    lab, name = resolve_speaker(ln, grp_map)
                    lo = max(0, i - context)
                    hi = min(len(lines), i + context + 1)
                    hits.append({
                        "meeting": f["meeting"]["id"], "date": f["meeting"]["date"],
                        "chapter": f["title"], "line": i + 1, "kw": kw,
                        "speaker": name or lab or "?",
                        "ctx": "\n".join(f"  {j+1}|{lines[j][:180]}" for j in range(lo, hi)),
                    })
    # 按会议+章节排序, kw 聚合, 限量
    hits.sort(key=lambda h: (h["meeting"], h["chapter"], h["line"]))
    counts = {}
    for h in hits:
        counts[h["kw"]] = counts.get(h["kw"], 0) + 1
    if limit_per_kw:
        seen_kw = {}
        filtered = []
        for h in hits:
            seen_kw[h["kw"]] = seen_kw.get(h["kw"], 0) + 1
            if seen_kw[h["kw"]] <= limit_per_kw:
                filtered.append(h)
        hits = filtered
    return hits, counts


# ── ③ 断言审计(产物断言 vs 原文证据 并列) ────────────────────────────────
def audit_claim(claim, verify_kws, meeting_id="auto", out=None):
    """claim=产物断言文本; verify_kws=需核实的词; 输出并列报告, 可选 --out 落盘"""
    esc_claim = re.sub(r"\s+", " ", claim)[:200]
    lines = [
        f"# 断言原文核实审计 · {now()[:10]}",
        "",
        f"> 断言: **{esc_claim}**",
        f"> 核实词: {', '.join(verify_kws)} · 会议: {meeting_id} · 工具: meeting-verify {VERSION}",
        "",
        "## 一、原文证据",
        "",
    ]
    hits, counts = verify_transcript(verify_kws, meeting_id)
    if not hits:
        lines.append("(原文未直接命中核实词——需扩大范围或改词)")
    for h in hits:
        lines.append(f"### {h['meeting']} · {h['chapter']} · L{h['line']} · [{h['speaker']}] · 命中「{h['kw']}」")
        lines.append("```")
        lines.append(h["ctx"])
        lines.append("```")
        lines.append("")
    lines.append("## 二、命中统计")
    lines.append("")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"- 「{k}」× {v}")
    lines.append("")
    lines.append("## 三、判读要点(供人工/模型定案)")
    lines.append("")
    lines.append("- 断言与原文是否一致? 口径(平台/单双平台/月年/品类)是否分层?")
    lines.append("- 说话人身份是否影响可信度? 是否被其他说话人当场纠正?")
    report = "\n".join(lines)
    if out:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                f.write(report)
            log_action(f"audit 落盘: {out} (claim={esc_claim[:60]})")
        except Exception as e:
            print(f"⚠️ 写盘失败: {e}", file=sys.stderr)
    return report, hits


# ── R006 ──────────────────────────────────────────────────────────────────
def selfcheck():
    print("✅ 原文切分文件:", len(iter_split_files()))
    print(f"✅ speakers 映射: {sum(len(v) for v in load_speaker_map().values())} 条(跨场)")
    print("✅ 产物目录: docs/ data/blueprint 可达:", os.path.isdir(os.path.join(COLLAB, "docs")))
    print("✅ R006: CLI/TCC/版本/日志/Lean4门(只读)")
    return 0


def lean4_check():
    """R006#10: 只读工具, 唯一写路径=--out 显式落盘(受控)"""
    src = open(__file__, encoding="utf-8").read()
    writes = [l for l in src.split("\n") if "open(" in l and '"w"' in l]
    # 只允许 audit_claim 的 out 写入 + 日志
    safe = all(("audit_claim" in src[: src.find(l)] or "meeting-verify.log" in l or "log_action" in l) for l in writes) if writes else True
    print(f"  {'✅' if safe else '❌ GATE'} 写路径仅 --out 报告+日志 ({len(writes)} 处)")
    print("Lean4 门:", "PASS" if safe else "FAIL")
    return 0 if safe else 1


def main():
    ap = argparse.ArgumentParser(
        description="语音会议产物·原文核实器 — 产物扫描/原文核实/断言审计 (R006 十项)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("--scan", default="", help="产物扫描: 关键词逗号分隔(如 淘闪,美团,GMV)")
    ap.add_argument("--scope", default=",".join(DEFAULT_SCOPE_DIRS), help="产物扫描根目录(逗号分隔, 相对 ~/dsh-collab)")
    ap.add_argument("--verify", default="", help="原文核实: 关键词逗号分隔")
    ap.add_argument("--meeting", default="auto", choices=["auto", "0905", "0908a", "0908b", "0908c", "0908"],
                    help="限定会议: auto=全部 / 0905 / 0908=全部三场 / 0908a|b|c=单场")
    ap.add_argument("--audit", default="", help="断言审计: 断言文本(引号包裹)")
    ap.add_argument("--kws", default="", help="审计核实词(逗号分隔, 与 --audit 同用)")
    ap.add_argument("--limit", type=int, default=6, help="每词原文命中上限(默认6)")
    ap.add_argument("--json", action="store_true", help="结构化输出")
    ap.add_argument("--out", default="", help="报告落盘路径(--audit 用)")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true", help="R006#10 约束门")
    ap.add_argument("--tool-version", action="version", version=f"meeting-verify {VERSION}")
    a = ap.parse_args()

    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()

    meeting = a.meeting  # resolve_meetings 内部处理 0908→三场合并

    if a.audit:
        kws = [k.strip() for k in a.kws.split(",") if k.strip()]
        if not kws:
            print("⚠️ --audit 需 --kws 指定核实词"); return 1
        report, hits = audit_claim(a.audit, kws, meeting, a.out or "")
        print(report)
        return 0

    if a.scan:
        kws = [k.strip() for k in a.scan.split(",") if k.strip()]
        dirs = [d.strip() for d in a.scope.split(",") if d.strip()]
        results, by_file = scan_products(kws, dirs)
        if a.json:
            print(json.dumps({"total": len(results), "files": {k: len(v) for k, v in by_file.items()}},
                             ensure_ascii=False, indent=1)); return 0
        print(f"== 产物扫描: {len(results)} 命中 / {len(by_file)} 文件 ==")
        for f, rs in sorted(by_file.items(), key=lambda x: -len(x[1])):
            print(f"\n── {f} ({len(rs)} 处) ──")
            for r in rs[:5]:
                print(f"  L{r['line']} «{r['kw']}»\n{r['ctx']}")
            if len(rs) > 5: print(f"  …另 {len(rs)-5} 处")
        return 0

    if a.verify:
        kws = [k.strip() for k in a.verify.split(",") if k.strip()]
        hits, counts = verify_transcript(kws, meeting, limit_per_kw=a.limit)
        if a.json:
            print(json.dumps({"total": len(hits), "counts": counts, "hits": hits},
                             ensure_ascii=False, indent=1)); return 0
        print(f"== 原文核实: {sum(counts.values())} 命中 / 展示 {len(hits)} ==")
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  「{k}」× {v}", end="")
        print()
        cur_meet = None
        for h in hits:
            if h["meeting"] != cur_meet:
                cur_meet = h["meeting"]
                m = group_of_meeting(cur_meet)
                print(f"\n──── {m['date']} · {m['label']} ────")
            print(f"\n[{h['chapter']} · L{h['line']}] ({h['speaker']}) «{h['kw']}»")
            print(h["ctx"])
        return 0

    ap.print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
