#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rules-sync v1.0 (HR) — 规则文件同步向量化（J46 配套：规则更新→自动入 ChromaDB）

扫描 dsh-collab 规则/制度文件 → 变更则 chroma_index（rel 前缀 dsh-collab/ 命名空间隔离）。
幂等：mtime+sha 快照。零 LLM 成本。
用法：python3 rules-sync.py [--force]
launchd：com.dsh.hr.rules-sync（每日 09:35）

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
    print("== rules-sync 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · rules-sync v1.0 (HR) — 规则文件同步向量化（J46 配套：规则更新→自动入 ChromaDB）")
    print("  · 扫描 dsh-collab 规则/制度文件 → 变更则 chroma_index（rel 前缀 dsh-collab/ 命名空间隔离）。")
    print("  · 幂等：mtime+sha 快照。零 LLM 成本。")
    print("  · 用法：python3 rules-sync.py [--force]")
    print("  · 命令/参数: force")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, time")
    print("  · ★ 第三方: chromadb, lib ⇒ 缺失时行为须明确（拒绝或降级），不得抛栈")
    print("  · 固定日志: ~/dsh-collab/logs/rules-sync.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, hashlib, datetime, sys
sys.path.insert(0, "/Users/coreyleung/.claude/automation")
from lib import chroma_index


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/rules-sync.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
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
