#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组装对端要的「三件套导出包」：问题类型 / 规则 / 工具。

输出目录：~/dsh-collab/data/packages/mbp-side-export-20261004/
内容（全部**只读复制**，不改动源）：
  EXPORT.md            导览（三件套说明 + 怎么用 + 边界）
  MANIFEST.md          **自动生成**的工具清单（用途/判据/用法）+ hazards G 码索引 + 类别定义索引
  hazards/             INDEX.md（G 码全量）+ rules.md（H1–H43）+ patterns/ + incidents/
  rules-registry/      我方账本 rules.json + RULES.md（三位数 R0xx 命名空间，供对照）
  tools/               全部通用工具（含 restart-audit / 沙箱 / 判据 / 发卡投递族）
  tools/_onetime/      一次性件（已明确标注为历史，勿重跑）
排除集：`.bak*` / `__pycache__` / `.DS_Store` / `._*`
"""
import os, re, shutil, sys, datetime

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, "dsh-collab/data/packages/mbp-side-export-20261004")
SRC_TOOLS = os.path.join(HOME, "dsh-collab/tools")
SRC_HAZ = os.path.join(HOME, "dsh-collab/hazards")
SRC_REG = os.path.join(HOME, "dsh-collab/rules-registry")

EXCLUDE = (".bak", "__pycache__", ".DS_Store", "._")
def ok(name): return not any(x in name for x in EXCLUDE)

shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)

# ── 复制三块 ────────────────────────────────────────────────────────────
def copy_tree(src, dst, skip_dirs=()):
    n = 0
    for r, ds, fs in os.walk(src):
        ds[:] = [d for d in ds if ok(d) and d not in skip_dirs]
        for f in fs:
            if not ok(f):
                continue
            rel = os.path.relpath(os.path.join(r, f), src)
            t = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(t), exist_ok=True)
            shutil.copy2(os.path.join(r, f), t)
            n += 1
    return n

n1 = copy_tree(SRC_HAZ, os.path.join(OUT, "hazards"))
n2 = copy_tree(SRC_TOOLS, os.path.join(OUT, "tools"))
n3 = 0
os.makedirs(os.path.join(OUT, "rules-registry"))
for f in ("rules.json", "RULES.md"):
    p = os.path.join(SRC_REG, f)
    if os.path.isfile(p):
        shutil.copy2(p, os.path.join(OUT, "rules-registry", f)); n3 += 1
print("复制：hazards %d / tools %d / rules-registry %d" % (n1, n2, n3))

# ── 自动生成 MANIFEST.md ────────────────────────────────────────────────
def first_docline(p):
    """取文件首个非空 docstring 行（作为"这是什么"）。"""
    try:
        txt = open(p, encoding="utf-8", errors="replace").read(4000)
    except Exception:
        return ""
    m = re.search(r'^\s*(?:"""|\'\'\'|/\*\*|\*|#)\s*(.+)$', txt, re.M)
    lines = [l.strip(" *\t") for l in txt.splitlines()[:40]]
    for l in lines:
        l = l.strip()
        if not l or l.startswith(("#!/", "# -*-", "import", "from", "const", "//", "/*", "*")):
            continue
        if len(l) > 8:
            return l[:150]
    return ""


rows_tools = []
for r, ds, fs in os.walk(os.path.join(OUT, "tools")):
    for f in sorted(fs):
        p = os.path.join(r, f)
        rel = os.path.relpath(p, os.path.join(OUT, "tools"))
        rows_tools.append((rel, os.path.getsize(p), first_docline(p) or "（无首行说明）"))
rows_tools.sort()

# restart-audit 的检查项（从 docstring 抽取 ①⑧⑨⑩⑪ 等行）
ra = open(os.path.join(OUT, "tools/restart-audit.py"), encoding="utf-8").read()
checks = re.findall(r"^\s*(?:[①-⑫]|\d+[a-z]?\.)\s*(.{3,90})$", ra[:6000], re.M)

# hazards G 码全量
idx = open(os.path.join(OUT, "hazards/INDEX.md"), encoding="utf-8").read()
gcodes = re.findall(r"^\|\s*\*\*(G[0-9]+(?:-追)?|F[0-9])\*\*\s*\|\s*([^|]{0,110})", idx, re.M)

# 类别定义
pat = open(os.path.join(OUT, "hazards/patterns/00-总表.md"), encoding="utf-8").read()
cats = re.findall(r"^\|\s*\*\*([A-F])\*\*\s*\|\s*([^|]{0,80})\|\s*([^|]{0,90})", pat, re.M)

H = []
H.append("# MANIFEST · MBP 侧三件套导出（自动生成，勿手改）")
H.append("")
H.append("> 生成：%s ｜ 生成脚本：`tools/build-side-export.py`" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
H.append("")
H.append("## 一、问题类型（hazards）")
H.append("")
H.append("**六大类别（会复发的形态）**：")
H.append("")
H.append("| 类 | 名称 | 一句话 |")
H.append("|---|---|---|")
for c, name, one in cats:
    nm = name.strip().strip("*").replace("**", "")[:60]
    H.append("| **%s** | %s | %s |" % (c, nm, one.strip()))
H.append("")
H.append("**缺口/复查项全量（G 码 + F 码，共 %d 条）**：" % len(gcodes))
H.append("")
H.append("| 码 | 一句话 |")
H.append("|---|---|")
for code, desc in gcodes:
    H.append("| **%s** | %s |" % (code, desc.strip().replace("\n", " ")[:110]))
H.append("")
H.append("完整定义与证据见 `hazards/INDEX.md`（§2 类别 / §3 事故索引 / §6b 缺口表）。")
H.append("")
H.append("## 二、规则")
H.append("")
H.append("- **hazards 自有规则 = `H1–H43`**（`hazards/rules.md`；铁律 A/B/C + H*；2026-10-04 由 `R1–R43` 改名，"
         "命名空间隔离，见 G6）")
H.append("- **规则账本 = `R001–R041`（三位数）**（`rules-registry/rules.json` + `RULES.md`；含 `retiredEntries` 退役索引）")
H.append("- **跨端引用必须带命名空间**：`mbp:H40` / `xq:R040`；**裸号只在同一命名空间内使用**")
H.append("")
H.append("## 三、工具清单（共 %d 个文件）" % len(rows_tools))
H.append("")
H.append("| 文件 | 字节 | 用途（首行说明） |")
H.append("|---|---|---|")
for rel, size, desc in rows_tools:
    H.append("| `%s` | %d | %s |" % (rel, size, desc))
H.append("")
H.append("### restart-audit 的检查项（重启前必跑；含 ⑧⑨⑨b⑩⑪）")
H.append("")
for c in checks[:20]:
    H.append("- %s" % c.strip())
H.append("")
open(os.path.join(OUT, "MANIFEST.md"), "w", encoding="utf-8").write("\n".join(H))
print("MANIFEST.md 生成：%d 工具 / %d 缺口码 / %d 类别" % (len(rows_tools), len(gcodes), len(cats)))
print("输出：", OUT)
