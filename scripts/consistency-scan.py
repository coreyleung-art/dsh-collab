#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事实一致性扫描器 · consistency-scan.py
========================================
解决「同一个事实有多个载体」的漏改问题：正文 markdown、图表 JS 里的字符串、
另一份文档的表格、派生版、**生成的 HTML 产物** —— 改一处漏多处。

用法：
    consistency-scan.py --facts facts.json --roots <目录或文件> [<目录或文件> ...]
                        [--json] [--ext .html,.md,.js,.json]

facts.json 格式：
    {
      "出让比例.Pre-A": { "correct": ["10-20%"], "stale": ["10-15%"] },
      "出让比例.A轮":   { "correct": ["6-12%"],  "stale": ["15-20%"] }
    }
    correct = 现在的正确口径（应当出现）
    stale   = 已废弃的旧值（不应当再出现）

行为要点：
  ✓ 递归扫描目录；--ext 过滤（默认 .html,.htm,.md,.js,.json,.txt,.css）
  ✓ 跳过 .git / node_modules / .export-* / 一切隐藏（. 开头）文件与目录
  ✓ 路径输出用 ~ 缩写
  ✓ 显式传入的文件路径始终扫描（不受 --ext 限制）
  ✓ 大小写敏感（事实文本大小写通常有意义，避免误报）
  ✓ 若某旧值是某新值的子串，落在新值内部的旧值匹配会被抑制，不计为残留
    （否则「10%」会把「10-20%」全部误报成旧值）
  ✓ 二进制文件（含 NUL 字节）自动跳过

退出码：
    0 = 全部干净（无残留）
    1 = 有残留（需要处理）
    2 = 用法/IO 错误（facts.json 缺失或格式错、所有 roots 都不存在等）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== consistency-scan 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 事实一致性扫描器 · consistency-scan.py")
    print("  · 解决「同一个事实有多个载体」的漏改问题：正文 markdown、图表 JS 里的字符串、")
    print("  · 另一份文档的表格、派生版、**生成的 HTML 产物** —— 改一处漏多处。")
    print("  · consistency-scan.py --facts facts.json --roots <目录或文件> [<目录或文件> ...]")
    print("  · 命令/参数: facts, roots, json, ext")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, json, os, sys, time")
    print("  · ★ 第三方: bisect ⇒ 缺失时行为须明确（拒绝或降级），不得抛栈")
    print("  · 固定日志: ~/dsh-collab/logs/consistency-scan.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import json
import os
import sys
import time
from bisect import bisect_right

# ---------------------------------------------------------------- 常量


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/consistency-scan.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

DEFAULT_EXTS = [".html", ".htm", ".md", ".js", ".json", ".txt", ".css"]

# 这些目录名一律不进入（隐藏目录由 . 前缀规则另外覆盖）
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__",
    ".venv", "venv", ".mypy_cache", ".pytest_cache", ".idea", ".vscode",
}

SEP = "=" * 64
SUBSEP = "-" * 64
MAX_FILE_BYTES = 64 * 1024 * 1024   # 单文件上限，防手滑扫到大 blob
SNIPPET_PAD = 14                    # 上下文片段左右各取多少字符
HOME = os.path.expanduser("~")


# ---------------------------------------------------------------- 小工具

def setup_stdout():
    """保证中文在任意 locale 下都能输出。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def abbrev(path):
    """把绝对路径缩写成 ~/... 形式。"""
    ap = os.path.abspath(path)
    if ap == HOME:
        return "~"
    if ap.startswith(HOME + os.sep):
        return "~" + ap[len(HOME):]
    return ap


def norm_ext(token):
    token = token.strip().lower()
    if not token:
        return None
    return token if token.startswith(".") else "." + token


def is_hidden(name):
    return name.startswith(".")


def skip_dir(name):
    if is_hidden(name):          # 含 .git / .export-* / .venv 等
        return True
    return name in SKIP_DIRS


# ---------------------------------------------------------------- 文件收集

def collect_files(roots, exts):
    """返回 (files, missing_roots, skipped_count)。files 已按 realpath 去重。"""
    files = []
    missing = []
    seen = set()
    skipped = {"ext": 0, "hidden": 0, "binary": 0, "size": 0, "unreadable": 0}

    def add(path):
        try:
            key = os.path.realpath(path)
        except Exception:
            key = os.path.abspath(path)
        if key in seen:
            return
        seen.add(key)
        files.append(path)

    for root in roots:
        if not os.path.exists(root):
            missing.append(root)
            continue
        if os.path.isfile(root):
            add(root)            # 显式指定的文件：不受 --ext 限制
            continue
        for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
            dirnames[:] = sorted(d for d in dirnames if not skip_dir(d))
            for fn in sorted(filenames):
                if is_hidden(fn):
                    skipped["hidden"] += 1
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext not in exts:
                    skipped["ext"] += 1
                    continue
                add(os.path.join(dirpath, fn))

    return files, missing, skipped


def read_text(path):
    """读取文本；二进制或过大返回 None，并给出原因。"""
    try:
        size = os.path.getsize(path)
    except OSError:
        return None, "unreadable"
    if size > MAX_FILE_BYTES:
        return None, "size"
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None, "unreadable"
    if b"\x00" in raw:
        return None, "binary"
    try:
        return raw.decode("utf-8"), None
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), None


class LineIndex(object):
    """偏移量 → 行号 / 行文本。"""

    def __init__(self, text):
        self.text = text
        starts = [0]
        idx = text.find("\n")
        while idx >= 0:
            starts.append(idx + 1)
            idx = text.find("\n", idx + 1)
        self.starts = starts

    def line_no(self, offset):
        return bisect_right(self.starts, offset)

    def line_text(self, offset):
        ln = self.line_no(offset)
        start = self.starts[ln - 1]
        end = self.starts[ln] - 1 if ln < len(self.starts) else len(self.text)
        return self.text[start:end].rstrip("\r")


def find_all(text, needle):
    """非重叠查找全部出现位置，返回 [(start, end), ...]。"""
    spans = []
    if not needle:
        return spans
    n = len(needle)
    pos = text.find(needle)
    while pos >= 0:
        spans.append((pos, pos + n))
        pos = text.find(needle, pos + n)
    return spans


def make_snippet(line_text, col, length):
    """给出一行内匹配处的上下文片段，形如 …让 10-15% 的…（保留紧邻空格）"""
    line = line_text.replace("\t", " ")
    left_at = max(0, col - SNIPPET_PAD)
    right_at = min(len(line), col + length + SNIPPET_PAD)
    left = line[left_at:col]
    match = line[col:col + length]
    right = line[col + length:right_at]
    prefix = "…" if left_at > 0 else ""
    suffix = "…" if right_at < len(line) else ""
    if prefix:
        left = left.lstrip()
    if suffix:
        right = right.rstrip()
    return "{}{}{}{}{}".format(prefix, left, match, right, suffix)


# ---------------------------------------------------------------- 扫描

def scan(facts, files, exts):
    """核心扫描。返回 (results, stats)。"""
    # 预载文件内容
    loaded = []          # (path, text, LineIndex_or_None)
    stats = {"files_scanned": 0, "skipped": {"binary": 0, "size": 0, "unreadable": 0}}

    for path in files:
        text, why = read_text(path)
        if text is None:
            stats["skipped"][why] = stats["skipped"].get(why, 0) + 1
            continue
        loaded.append([path, text, None])
        stats["files_scanned"] += 1

    results = []
    for name, spec in facts.items():
        correct_vals = [v for v in (spec.get("correct") or []) if isinstance(v, str) and v]
        stale_vals = [v for v in (spec.get("stale") or []) if isinstance(v, str) and v]

        correct_hits = {v: [] for v in correct_vals}   # v -> [(file_idx, start, end)]
        stale_hits = {v: [] for v in stale_vals}
        suppressed = 0

        for fidx, entry in enumerate(loaded):
            text = entry[1]
            # 先收集所有新值的 span（同事实内），用于子串重叠抑制
            correct_spans = []
            for v in correct_vals:
                spans = find_all(text, v)
                if spans:
                    correct_hits[v].extend((fidx, s, e) for (s, e) in spans)
                    correct_spans.extend(spans)
            for v in stale_vals:
                for (s, e) in find_all(text, v):
                    if any(cs <= s and e <= ce for (cs, ce) in correct_spans):
                        suppressed += 1
                        continue
                    stale_hits[v].append((fidx, s, e))

        # 汇总
        def build(value, hits):
            out = {"value": value, "count": len(hits), "files": len({h[0] for h in hits}),
                   "locations": []}
            for (fidx, s, e) in hits:
                entry = loaded[fidx]
                if entry[2] is None:
                    entry[2] = LineIndex(entry[1])
                idx = entry[2]
                line_text = idx.line_text(s)
                col = s - (idx.starts[idx.line_no(s) - 1])
                loc = {
                    "path": abbrev(entry[0]),
                    "abs_path": os.path.abspath(entry[0]),
                    "line": idx.line_no(s),
                    "col": col + 1,
                    "snippet": make_snippet(line_text, col, e - s),
                }
                out["locations"].append(loc)
            return out

        correct_report = [build(v, correct_hits[v]) for v in correct_vals]
        stale_report = [build(v, stale_hits[v]) for v in stale_vals]

        stale_total = sum(r["count"] for r in stale_report)
        correct_total = sum(r["count"] for r in correct_report)

        results.append({
            "name": name,
            "ok": stale_total == 0,
            "stale_total": stale_total,
            "correct_total": correct_total,
            "suppressed_overlap": suppressed,
            "stale": stale_report,
            "correct": correct_report,
        })

    return results, stats


# ---------------------------------------------------------------- 输出

def render(results, files_scanned, missing, skipped, roots, exts):
    lines = []
    lines.append("事实一致性扫描 · {} 个事实 · 扫 {} 个文件".format(len(results), files_scanned))
    lines.append(SEP)

    for r in results:
        if r["ok"]:
            lines.append("✅ {}".format(r["name"]))
            note = ""
            if r["correct_total"] == 0:
                note = "（新值未出现，请核对是否漏改/写错）"
            elif r["suppressed_overlap"]:
                note = "（已抑制 {} 处与新值重叠的旧值匹配）".format(r["suppressed_overlap"])
            lines.append("   残留 0 处 · 新值覆盖 {} 处{}".format(r["correct_total"], note))
        else:
            lines.append("⚠️ {}".format(r["name"]))
            for sv in r["stale"]:
                if sv["count"] == 0:
                    continue
                lines.append("   残留旧值 {}（{} 处）:".format(sv["value"], sv["count"]))
                for loc in sv["locations"]:
                    lines.append("     {}:{}   {}".format(loc["path"], loc["line"], loc["snippet"]))
            for cv in r["correct"]:
                mark = "✅" if cv["count"] > 0 else "⚠️"
                lines.append("   新值 {} 覆盖 {} 处 {}".format(cv["value"], cv["count"], mark))
            if r["suppressed_overlap"]:
                lines.append("   （已抑制 {} 处与新值重叠的旧值匹配）".format(r["suppressed_overlap"]))

    if missing:
        lines.append(SUBSEP)
        for m in missing:
            lines.append("⚠️ 跳过不存在的路径：{}".format(abbrev(m)))

    lines.append(SUBSEP)
    bad = [r for r in results if not r["ok"]]
    if bad:
        lines.append("结论：{} 个事实有残留，需处理".format(len(bad)))
    else:
        lines.append("结论：全部干净，无残留 ✅")
    return "\n".join(lines)


def main(argv=None):
    setup_stdout()
    parser = argparse.ArgumentParser(
        prog="consistency-scan.py",
        description="事实一致性扫描：报告每个事实的残留旧值与新值覆盖情况",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="退出码：0=全部干净 / 1=有残留 / 2=用法或 IO 错误",
    )
    parser.add_argument("--facts", required=True, help="事实表 JSON 路径")
    parser.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    parser.add_argument("--roots", nargs="+", required=True, help="要扫描的目录或文件（可多个）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON（不输出人读报告）")
    parser.add_argument("--ext", default=",".join(DEFAULT_EXTS),
                        help="要扫描的扩展名，逗号分隔（默认 %s）" % ",".join(DEFAULT_EXTS))
    args = parser.parse_args(argv)

    exts = set(filter(None, (norm_ext(t) for t in args.ext.split(","))))
    if not exts:
        exts = set(DEFAULT_EXTS)

    if not os.path.isfile(args.facts):
        sys.stderr.write("错误：facts 文件不存在：{}\n".format(args.facts))
        return 2
    try:
        with open(args.facts, "r", encoding="utf-8") as fh:
            facts = json.load(fh)
    except Exception as exc:
        sys.stderr.write("错误：facts 文件解析失败：{}\n".format(exc))
        return 2
    if not isinstance(facts, dict) or not facts:
        sys.stderr.write("错误：facts 必须是非空对象：{\"事实名\": {\"correct\": [...], \"stale\": [...]}}\n")
        return 2
    for name, spec in facts.items():
        if not isinstance(spec, dict) or ("correct" not in spec and "stale" not in spec):
            sys.stderr.write("错误：事实「{}」缺少 correct / stale 字段\n".format(name))
            return 2

    files, missing, skipped = collect_files(args.roots, exts)
    # 事实表自身是「判定标准」而不是「载体」：若 roots 覆盖到它，必须排除，
    # 否则每个旧值都会在 facts.json 里被自己命中一次（假残留）。
    facts_key = os.path.realpath(os.path.abspath(args.facts))
    files = [f for f in files if os.path.realpath(os.path.abspath(f)) != facts_key]
    if not files and missing:
        sys.stderr.write("错误：所有 roots 都不存在：{}\n".format(", ".join(missing)))
        return 2

    results, stats = scan(facts, files, exts)
    bad = [r for r in results if not r["ok"]]

    if args.json:
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "facts_count": len(results),
            "files_scanned": stats["files_scanned"],
            "roots": [abbrev(r) for r in args.roots],
            "missing_roots": [abbrev(m) for m in missing],
            "exts": sorted(exts),
            "results": results,
            "summary": {
                "facts_with_stale": len(bad),
                "facts_clean": len(results) - len(bad),
                "stale_occurrences": sum(r["stale_total"] for r in results),
                "correct_occurrences": sum(r["correct_total"] for r in results),
                "clean": not bad,
            },
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render(results, stats["files_scanned"], missing, skipped,
                                args.roots, exts) + "\n")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
