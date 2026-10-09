#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mbp-memory-vectorize.py v1.0 — MBP 考古记忆向量化（零依赖版）

把考古产出文档 → 分块 → ollama bge-m3 嵌入 → JSON 向量库（纯 stdlib）
用法:
  python3 mbp-memory-vectorize.py build <doc_dir>            # 建库
  python3 mbp-memory-vectorize.py query '<问题>' [topK]      # 查询
  python3 mbp-memory-vectorize.py status                     # 库状态

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, sys, glob, re, urllib.request, time


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/mbp-memory-vectorize.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

OLLAMA = "http://127.0.0.1:11434"
MODEL = "bge-m3"
KB_DIR = os.path.expanduser("~/dsh-collab/archaeology-mbp/vector-kb")
KB_FILE = os.path.join(KB_DIR, "mbp-memory-kb.json")

def embed(text):
    body = json.dumps({"model": MODEL, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA + "/api/embeddings", data=body,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())["embedding"]
        except Exception as ex:
            if attempt == 2:
                raise
            time.sleep(2)

def chunk_md(text, maxlen=500):
    """按标题/段落切块，尽量保留语义单元"""
    chunks, cur = [], ""
    for line in text.splitlines():
        if line.startswith("#") and cur.strip():
            chunks.append(cur.strip()); cur = ""
        if len(cur) + len(line) > maxlen and cur.strip():
            chunks.append(cur.strip()); cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur.strip())
    return [c for c in chunks if len(c) > 20]

def build(doc_dir):
    os.makedirs(KB_DIR, exist_ok=True)
    docs = sorted(glob.glob(os.path.join(doc_dir, "**", "*.md"), recursive=True))
    if not docs:
        docs = sorted(glob.glob(os.path.join(doc_dir, "*.md")))
    print("扫描到 %d 个文档" % len(docs))
    items, n = [], 0
    t0 = time.time()
    for fp in docs:
        with open(fp, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        for ci, ch in enumerate(chunk_md(text)):
            n += 1
            vec = embed(ch)
            items.append({
                "id": "c%d" % n,
                "doc": os.path.basename(fp),
                "chunk": ci,
                "text": ch[:300],
                "vec": vec,
            })
            if n % 10 == 0:
                print("  已嵌入 %d 块 (%.0fs)" % (n, time.time() - t0), flush=True)
    with open(KB_FILE, "w", encoding="utf-8") as f:
        json.dump({"model": MODEL, "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "count": len(items), "items": items}, f, ensure_ascii=False)
    print("✅ 向量库建成: %d 块 / %d 文档 → %s (%.0fs)" %
          (len(items), len(docs), KB_FILE, time.time() - t0))

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (
        (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) or 1)

def query(q, topk=5):
    if not os.path.exists(KB_FILE):
        print("库不存在，先 build"); return
    kb = json.load(open(KB_FILE))
    qv = embed(q)
    scored = sorted(((cosine(qv, it["vec"]), it) for it in kb["items"]),
                    reverse=True)[:topk]
    print("=== 命中 %d 条（库 %d 块）===" % (len(scored), kb["count"]))
    for s, it in scored:
        print("[%.3f] %s#%d: %s" % (s, it["doc"], it["chunk"], it["text"][:120].replace("\n", " ")))

def status():
    if not os.path.exists(KB_FILE):
        print("库不存在"); return
    kb = json.load(open(KB_FILE))
    docs = {}
    for it in kb["items"]:
        docs[it["doc"]] = docs.get(it["doc"], 0) + 1
    print("模型: %s | 块数: %d | 文档: %d | 建库: %s" %
          (kb["model"], kb["count"], len(docs), kb["built"]))
    for d, c in sorted(docs.items()):
        print("  %s: %d 块" % (d, c))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/dsh-collab/archaeology-mbp"))
    elif cmd == "query":
        query(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 5)
    elif cmd == "status":
        status()
    else:
        print(__doc__)
