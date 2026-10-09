#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""index-rules-kb.py — 把外部规则集总纲逐条索引进 ChromaDB（R032 知识向量化归档）

为什么要它：
  `sources/AI工程规则总纲-v2.0-20261009.md`（i9 侧 trae 规则集，22 条编号规则 + 5 条基础规则）
  不并入 RULES.md 编号账（见 RULES.md「外部来源规则集」节），但需可语义检索。
  本脚本把**每条规则切成一个 chunk**，写进独立集合 `rules`，metadata 带 `item`（trae:E<n>）。

为什么独立集合而非 `wiki`：
  CLAUDE.md 明定 `wiki` 集合放 wiki 页面（与 notes/journals 分开）；原始规则文本不是 wiki 页面，
  混入会污染 wiki 检索面。按内容类型命名（notes/journals/dsh-docs/research/rules）是既有惯例。

嵌入：复用 `~/.claude/automation/lib.py::lm_embed`（LM Studio :1234，回退 Ollama :11434）
  —— 必须与既有集合同一嵌入空间，否则向量不可比。故本脚本只 add，**不**自带嵌入函数。

用法（须用带 chromadb 的 venv）：
  ~/.openchronicle/venv/bin/python ~/dsh-collab/scripts/index-rules-kb.py            # 索引
  ~/.openchronicle/venv/bin/python ~/dsh-collab/scripts/index-rules-kb.py --dry-run  # 只解析不写
  ~/.openchronicle/venv/bin/python ~/dsh-collab/scripts/index-rules-kb.py --query "中文引号"

约束门（⑩）：只读源文件；只写 ChromaDB（本地目录）；无 subprocess/eval/exec/网络除嵌入端点。
"""
import argparse
import os
import re
import sys
from pathlib import Path

SRC = Path("~/dsh-collab/rules-registry/sources/AI工程规则总纲-v2.0-20261009.md").expanduser()
LIB_DIR = Path("~/.claude/automation").expanduser()
COLLECTION = "rules"
SOURCE_TAG = "rules-registry/sources/AI工程规则总纲-v2.0-20261009.md"

# 标题 → 条目。只认「规则<中文数字>」「习惯<A-C>」「沟通规则」，排除附录的
# 「规则编号与文件映射」「规则化历史」等（它们同样以 ### 规则 开头）。
HEAD_RE = re.compile(r"^###\s*(规则[一二三四五六七八九十]+|习惯[ABC]|沟通规则：?\S*)\s*[:：]?\s*(.*)$")
PART_RE = re.compile(r"^##\s*(第[一二三四五六]部分[：:].*)$")

CN = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s: str) -> int:
    """中文数字 → 整数，支持 1–99（十/十一/二十/二十三）。"""
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + CN[s[1:]]
    if "十" in s:
        a, _, b = s.partition("十")
        return CN[a] * 10 + (CN[b] if b else 0)
    return CN[s]


def parse(text: str):
    """→ [{item, title, part, body}]，按文档顺序。"""
    items, cur, part = [], None, "(前言)"
    for line in text.splitlines():
        pm = PART_RE.match(line)
        if pm:
            part = pm.group(1).strip()
        hm = HEAD_RE.match(line)
        if hm:
            if cur:
                items.append(cur)
            head, rest = hm.group(1), hm.group(2).strip()
            if head.startswith("规则"):
                n = cn2int(head[2:])
                item = f"trae:E{n}"
            elif head.startswith("习惯"):
                item = f"trae:E-习惯{head[2:]}"
            else:
                item = f"trae:E-{head}"          # 沟通规则：比喻沟通 / 沟通规则：信息真实性
            title = head + (("：" + rest) if (rest and not rest.startswith("（")) else rest)
            cur = {"item": item, "title": title, "part": part, "body": [line]}
            continue
        if cur is not None:
            if re.match(r"^##\s", line):          # 遇到下一个 ## 分区 → 当前条目结束
                items.append(cur); cur = None; continue
            if re.match(r"^---\s*$", line):       # 分隔线也收尾
                items.append(cur); cur = None; continue
            cur["body"].append(line)
    if cur:
        items.append(cur)
    for it in items:
        it["body"] = "\n".join(it["body"]).strip()
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只解析不写库")
    ap.add_argument("--query", help="索引后按此查询集合（写入仍发生）")
    ap.add_argument("--src", default=str(SRC))
    a = ap.parse_args()

    src = Path(a.src).expanduser()
    if not src.exists():
        print(f"❌ 源文件不存在: {src}", file=sys.stderr)
        return 2
    items = parse(src.read_text(encoding="utf-8"))
    print(f"解析: {len(items)} 条")
    for it in items:
        print(f"  {it['item']:<16} [{it['part']}] {it['title'][:40]} ({len(it['body'])} 字符)")

    if a.dry_run:
        print("(--dry-run：未写库)")
        return 0

    sys.path.insert(0, str(LIB_DIR))
    import lib

    coll = lib._get_chroma().get_or_create_collection(COLLECTION)
    before = coll.count()
    docs = [it["body"] for it in items]
    ids = [it["item"] for it in items]
    metas = [{"source": SOURCE_TAG, "item": it["item"], "title": it["title"],
              "part": it["part"]} for it in items]
    embs = [lib.lm_embed(d) for d in docs]           # 逐条嵌入（27 条，本地，秒级）
    coll.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
    after = coll.count()
    print(f"✅ 写入集合 '{COLLECTION}': {before} → {after}（+{after - before}）")

    if a.query:
        emb = lib.lm_embed(a.query)
        r = coll.query(query_embeddings=[emb], n_results=5)
        print(f"\n查询「{a.query}」 top5:")
        for i, _id in enumerate(r["ids"][0]):
            m = r["metadatas"][0][i]
            dist = r["distances"][0][i]
            print(f"  {dist:.4f}  {m.get('item','?'):<16} {m.get('title','')[:44]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
