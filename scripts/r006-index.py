#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
r006-index.py — R006 规格文档的内容索引生成器（+ 自校验）
=============================================================
用途：把 `docs/R006-插件化工具化标准-v3.0.md` 解析成**机器可读索引**，
     供智能体在 10 秒内定位到"要做插件/工具该看哪一节"，避免重复检索浪费 token。

产出：
  docs/R006-index.json   # 结构化：section / anchor / keywords / summary / lines
  docs/R006-index.md     # 人类可读速查表（含快速话术）

用法：
  python3 r006-index.py                 # 生成（覆盖）
  python3 r006-index.py --verify        # 自校验：锚点必须真实存在于文档、历史文档路径必须存在、KB 名必须与规格一致
  python3 r006-index.py --query "约束门" # 本地关键词命中（无需向量库）
退出码：0 成功 / 1 校验失败 / 2 用法或 IO 错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, hashlib


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/r006-index.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SPEC = os.path.expanduser("~/dsh-collab/docs/R006-插件化工具化标准-v3.0.md")
OUT_JSON = os.path.expanduser("~/dsh-collab/docs/R006-index.json")
OUT_MD = os.path.expanduser("~/dsh-collab/docs/R006-index.md")
KB_NAME = "r006-tooling-standard-kb"
LEGACY = [
    "labforge-r006-alignment.md", "meeting-verify-r006-ten.md", "plugin-eval-rule-v1.md",
    "plugin-selfcheck-spec-v1.md", "r006-proposal-lean4-gate-v1.md",
    "wargame-engine-r006-ten.md", "wargame-r006-ten.md",
]
REFS = [
    ("dsh-plugin-cldvoice-activate", "~/dsh-collab/devices/dsh-plugin-cldvoice-activate/"),
    ("dsh-plugin-agent-way (agent-bus)", "~/dsh-plugin-agent-bus/"),
    ("wargame-engine", "~/dsh-collab/scripts/wargame-engine.py"),
]


def slug(text: str) -> str:
    """GitHub 风格锚点：小写、去标点、空格转连字符（保留中文与数字）"""
    t = text.strip().lower()
    t = re.sub(r"[`*（）()：:，,。.、/??!！?？\"'\[\]{}|>#+]+", "", t)
    t = re.sub(r"\s+", "-", t)
    return t


def parse_sections(text: str):
    """切分 § 与二级标题；返回 section 列表"""
    lines = text.split("\n")
    secs, cur = [], None
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^(#{2,3})\s+(.*)$", ln)
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        cur = {"level": level, "title": title, "anchor": slug(title), "line": i, "body": []}
        secs.append(cur)
    # 归属正文
    for idx, s in enumerate(secs):
        end = secs[idx + 1]["line"] - 1 if idx + 1 < len(secs) else len(lines)
        s["body"] = lines[s["line"]:end]
    return secs


def keywords(body, title, limit=14):
    """关键词：**标识符优先**（工具名/路径/常量），再反引号词、加粗词、标题词、短词

    2026-09-11 修正：此前单纯按出现顺序取前 14 个 → 工具名会被通用词挤掉
    （实测 §7 里 `reflect-enroll` / `wargame` 均不在关键词中，于是 `--query` 查不到）。
    索引存在的意义就是"10 秒内找到"，**能指代产物的标识符必须优先入库**。
    """
    joined = "\n".join(body)
    # ① 标识符类（最高优先）：工具/插件名、文件路径、文件名、常量
    ident_re = re.compile(
        r"dsh-plugin-[a-z0-9-]+"                       # 插件名
        r"|~/[A-Za-z0-9_./~-]{2,60}"                   # 家目录路径
        r"|[A-Za-z0-9_./-]*[A-Za-z][A-Za-z0-9_./-]*\.(?:py|js|mjs|ts|json|md|yml|yaml|sh)\b"  # 文件名
        r"|[A-Z][A-Z0-9_]{3,}"                         # 常量（VERSION_REGRESSION 等）
        r"|[a-z][a-z0-9]+(?:-[a-z0-9]+){1,4}"          # 连字符标识符（reflect-enroll 等）
    )
    idents = []
    for m in ident_re.findall(joined):
        m = m.strip().rstrip("/")
        if m and m not in idents:
            idents.append(m)
    cand = idents
    cand += re.findall(r"`([^`]{2,24})`", joined)
    cand += re.findall(r"\*\*([^*]{2,24})\*\*", joined)
    cand += [w for w in re.split(r"[\s、，,。.：:；;（）()/｜|]+", title) if 1 < len(w) < 20]
    seen, out = set(), []
    for c in cand:
        c = c.strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
        if len(out) >= limit:
            break
    return out


def summary(body, limit=160):
    """摘要：取正文第一条非空、非表格分隔、非目录项的文字"""
    for ln in body:
        t = ln.strip()
        if not t or t.startswith("|---") or t.startswith("- [") or t.startswith("> **"):
            continue
        t = re.sub(r"^[-*]\s+", "", t)
        t = t.replace("**", "").replace("`", "")
        return t[:limit]
    return ""


def build():
    if not os.path.isfile(SPEC):
        print(f"规格文档不存在: {SPEC}", file=sys.stderr)
        sys.exit(2)
    text = open(SPEC, encoding="utf-8").read()
    secs = parse_sections(text)
    entries = []
    for s in secs:
        if s["level"] < 2:
            continue
        entries.append({
            "title": s["title"], "anchor": s["anchor"], "line": s["line"],
            "keywords": keywords(s["body"], s["title"]), "summary": summary(s["body"]),
        })
    doc = {
        "spec": SPEC,
        "spec_sha256_16": hashlib.sha256(text.encode()).hexdigest()[:16],
        "spec_lines": len(text.split("\n")),
        "kb": KB_NAME,
        "sections": entries,
        "legacy_docs": [os.path.expanduser("~/dsh-collab/docs/" + f) for f in LEGACY],
        "reference_impls": [{"name": n, "path": p} for n, p in REFS],
        "quick_queries": {
            "要做插件/工具 → 需要满足什么": "§2 十项逐项规格 + §3 交付物模板",
            "约束门怎么写": "§4 四种门型 + --lean4-check 六项模板",
            "交付前怎么验收": "§5 验收流程（三条命令）",
            "踩过的坑": "§6 常见坑（7 条）",
            "照抄哪个实例": "§7 参考实现",
            "还要补哪些工具": "§8 存量工具补课排期",
        },
    }
    json.dump(doc, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    md = [f"# R006 内容索引（自动生成，勿手改）\n",
          f"> 规格：`{SPEC}` · sha256(前16) `{doc['spec_sha256_16']}` · {doc['spec_lines']} 行 · KB `{KB_NAME}`",
          f"> 重新生成：`python3 {os.path.expanduser('~/dsh-collab/scripts/r006-index.py')}` · 自校验加 `--verify`\n",
          "## 章节速查\n", "| 节 | 锚点 | 关键词 | 摘要 |", "|---|---|---|---|"]
    for e in entries:
        md.append(f"| {e['title']} | `#{e['anchor']}` | {', '.join(e['keywords'][:8])} | {e['summary'][:90]} |")
    md += ["\n## 快速话术\n"]
    for q, a in doc["quick_queries"].items():
        md.append(f"- **{q}** → {a}")
    md += ["\n## 历史文档（已并入 v3.0，保留作证据）\n"]
    for p in doc["legacy_docs"]:
        md.append(f"- `{p}`")
    md += ["\n## 参考实现\n"]
    for r in doc["reference_impls"]:
        md.append(f"- **{r['name']}** — `{r['path']}`")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(md) + "\n")
    return doc


def verify(doc):
    text = open(SPEC, encoding="utf-8").read()
    fails = []
    # 1) 每个锚点必须能在文档中由某个标题推出
    titles = [m.group(2).strip() for m in re.finditer(r"^(#{2,3})\s+(.*)$", text, re.M)]
    anchors = {slug(t) for t in titles}
    for e in doc["sections"]:
        if e["anchor"] not in anchors:
            fails.append(f"锚点在文档中不存在: {e['anchor']}")
    # 2) 历史文档必须存在
    for p in doc["legacy_docs"]:
        if not os.path.isfile(p):
            fails.append(f"历史文档缺失: {p}")
    # 3) KB 名必须与规格正文一致（防改了一处忘了另一处）
    if KB_NAME not in text:
        fails.append(f"规格正文未提及 KB 名 {KB_NAME}")
    # 4) 参考实现路径存在性（warn 级 → 计入 fails 以便发现漂移）
    for r in doc["reference_impls"]:
        p = os.path.expanduser(r["path"])
        if not os.path.exists(p):
            fails.append(f"参考实现路径不存在: {r['path']}")
    # 5) 索引与文档指纹一致（过期索引会骗人）
    cur = hashlib.sha256(text.encode()).hexdigest()[:16]
    if cur != doc["spec_sha256_16"]:
        fails.append(f"索引指纹过期: 索引={doc['spec_sha256_16']} 现状={cur}（请重跑生成）")
    return fails


def main():
    ap = argparse.ArgumentParser(description="R006 内容索引生成/校验")
    ap.add_argument("--verify", action="store_true", help="校验已有索引（锚点/路径/指纹）")
    ap.add_argument("--query", metavar="KW", help="本地关键词命中（不依赖向量库）")
    a = ap.parse_args()

    if a.verify:
        if not os.path.isfile(OUT_JSON):
            print("索引不存在，请先运行生成"); sys.exit(2)
        doc = json.load(open(OUT_JSON, encoding="utf-8"))
        fails = verify(doc)
        for f in fails:
            print("  ❌", f)
        print(f"  索引校验: {'✅ 通过' if not fails else f'❌ {len(fails)} 项失败'}"
              f"（{len(doc['sections'])} 节 · 指纹 {doc['spec_sha256_16']}）")
        sys.exit(0 if not fails else 1)

    if a.query:
        if not os.path.isfile(OUT_JSON):
            print("索引不存在，请先运行生成"); sys.exit(2)
        doc = json.load(open(OUT_JSON, encoding="utf-8"))
        kw = a.query.lower()
        # 2026-09-11：除 title/keywords/summary 外，**也搜章节正文**——否则被挤出
        # 关键词表的工具名（如 reflect-enroll / wargame）永远查不到，违背索引目的
        try:
            spec_lines = open(SPEC, encoding="utf-8").read().split("\n")
        except Exception:
            spec_lines = []
        secs = doc["sections"]
        hits = []
        for i, e in enumerate(secs):
            if (kw in e["title"].lower()
                    or any(kw in k.lower() for k in e["keywords"])
                    or kw in (e["summary"] or "").lower()):
                hits.append(e); continue
            if spec_lines:
                lo = max(0, (e.get("line") or 1) - 1)
                hi = (secs[i + 1].get("line") - 1) if i + 1 < len(secs) else len(spec_lines)
                if kw in "\n".join(spec_lines[lo:hi]).lower():
                    hits.append(e)
        print(f"  本地索引命中 {len(hits)} 节（query={a.query}）：")
        for h in hits:
            print(f"    §{h['title']} → {SPEC}#{h['anchor']}（行 {h['line']}）")
        sys.exit(0 if hits else 1)

    doc = build()
    print(f"  ✅ 已生成：{OUT_JSON}")
    print(f"  ✅ 已生成：{OUT_MD}")
    print(f"     规格 {doc['spec_lines']} 行 · 索引 {len(doc['sections'])} 节 · 指纹 {doc['spec_sha256_16']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
