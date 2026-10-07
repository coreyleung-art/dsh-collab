#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rules-sync v1.0 (HR) — 规则文件同步向量化（J46 配套：规则更新→自动入 ChromaDB）

扫描 dsh-collab 规则/制度文件 → 变更则 chroma_index（rel 前缀 dsh-collab/ 命名空间隔离）。
幂等：mtime+sha 快照。零 LLM 成本。
用法：python3 rules-sync.py [--force]
launchd：com.dsh.hr.rules-sync（每日 09:35）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, hashlib, datetime, sys
sys.path.insert(0, "/Users/coreyleung/.claude/automation")
from lib import chroma_index

COLLAB = os.path.expanduser("~/dsh-collab")
STATE = os.path.join(COLLAB, "token-monitor", "rules-sync-state.json")

# 规则/制度文件清单（"这类型规则"——更新即同步向量化）
RULES = [
    "resource-conflict-policy.md",      # J 规则集（底层规则本体）
    "foundation-wiki.md",               # SSOT
    "approval-ledger.md",               # 审批台账（J45）
    "approval-config.json",             # 审批开关/成本门禁配置
    "research/cost-governance/user-collaboration-discipline.md",  # J41-J44 细则
    "knowledge-continuous-update.md",   # 知识持续更新机制
    "blackboard-dispatch-protocol.md",  # 黑板投递协议
    "waimai-role-matrix.md",            # 外卖职责矩阵
    "subscriptions.json",               # 黑板/事件订阅表
]

MAX_CHARS = 2500

def safe_index(rel, content):
    """分块安全索引：段落>MAX_CHARS 按行组切块，逐块嵌入（规避长段落嵌入 500）"""
    import chromadb
    from lib import _get_chroma, lm_embed
    coll = _get_chroma().get_or_create_collection("notes")
    paras = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not paras:
        paras = [content.strip()]
    chunks = []
    for p in paras:
        if len(p) <= MAX_CHARS:
            chunks.append(p)
        else:
            lines = p.split("\n")
            cur = []
            cur_len = 0
            for ln in lines:
                if cur_len + len(ln) > MAX_CHARS and cur:
                    chunks.append("\n".join(cur)); cur = []; cur_len = 0
                cur.append(ln); cur_len += len(ln)
            if cur:
                chunks.append("\n".join(cur))
    total = 0
    for i, c in enumerate(chunks):
        try:
            emb = lm_embed(c)
            coll.add(documents=[c], embeddings=[emb],
                     metadatas=[{"source": rel, "chunk": i}], ids=["%s#chunk%d" % (rel, i)])
            total += 1
        except Exception:
            print("  chunk-fail (skip):", rel, i, len(c))
    return total

def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    try:
        state = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        state = {}
    indexed = 0
    for rel in RULES:
        p = os.path.join(COLLAB, rel)
        if not os.path.exists(p):
            print("MISS:", rel); continue
        cur = sha(p)
        if not args.force and state.get(rel, {}).get("sha") == cur:
            continue
        try:
            content = open(p, encoding="utf-8", errors="ignore").read()
            n = safe_index("dsh-collab/" + rel, content)
            state[rel] = {"sha": cur, "chunks": n, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            indexed += 1
            print("INDEXED:", rel, n, "chunks")
        except Exception as ex:
            print("ERR:", rel, str(ex)[:80])
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("rules-sync: indexed=%d total_files=%d" % (indexed, len(RULES)))

if __name__ == "__main__":
    main()
