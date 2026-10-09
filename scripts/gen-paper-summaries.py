#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-paper-summaries.py — 知识图谱论文中文概况批生成
为 knowledge-graph.json 中每篇论文生成中文概况：
  1) 有 paper-cache Abstract → qwen2.5:3b 本地概括（英文→中文 60-90 字）
  2) 无 Abstract 有报告中文关联列 → 直接采用
  3) 都无 → 占位（arXiv + 引用报告）
输出: data/blueprint/gallery/paper-summaries.json（pid → {summary, source}）
用法: python3 gen-paper-summaries.py [--only-missing] [--limit N] [--force]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import os, re, json, glob, sys, time, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/gen-paper-summaries.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

GALLERY = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")
RES = os.path.expanduser("~/dsh-collab/research")
OUT = os.path.join(GALLERY, "paper-summaries.json")
MODEL = "qwen2.5:3b"
OLLAMA = "http://127.0.0.1:11434/api/generate"

def ollama_summarize(abstract):
    prompt = (f"用 60-100 字中文概括以下英文论文摘要的核心贡献与应用价值。"
              f"要求：先说做了什么，再说有什么用。只输出中文概括。\n\n摘要:{abstract[:1400]}")
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"num_predict": 220, "temperature": 0.3}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode()).get("response", "").strip()
        except Exception as e:
            if attempt == 2:
                return ""
            time.sleep(3)
    return ""

def load_abstracts():
    """paper-cache/*.md → {pid: abstract}"""
    out = {}
    pc = os.path.join(RES, "paper-cache")
    if not os.path.isdir(pc): return out
    for f in os.listdir(pc):
        if not f.endswith(".md"): continue
        pid = f[:-3]
        if not re.fullmatch(r"\d{4}\.\d{4,5}", pid): continue
        txt = open(os.path.join(pc, f), encoding="utf-8").read()
        m = re.search(r"Abstract[:：]\s*(.*?)(?:\n\s*#|\n\s*##|\n\s*---|\Z)", txt, re.S)
        out[pid] = m.group(1).strip()[:1400] if m else ""
    return out

def load_cn_rels():
    """research/**/*.md 报告表格中文关联列 → {pid: 中文}"""
    out = {}
    for f in glob.glob(os.path.join(RES, "**", "*.md"), recursive=True):
        txt = open(f, encoding="utf-8").read()
        for m in re.finditer(r"\|\s*\*{0,2}(\d{4}\.\d{4,5})\*{0,2}\s*\|\s*[^|]+?\s*\|\s*([^|]+?)\s*\|", txt):
            pid, rel = m.group(1), m.group(2).strip()
            if 8 < len(rel) < 260 and not re.match(r"^[\w\s'\-.,;:()\[\]/]+$", rel):
                # 中文特征（含 CJK）
                if re.search(r"[\u4e00-\u9fff]", rel):
                    out.setdefault(pid, rel)
    return out

def main():
    only_missing = "--only-missing" in sys.argv
    limit = None
    force = "--force" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i+1 < len(sys.argv): limit = int(sys.argv[i+1])
    # 图谱论文
    g = json.load(open(os.path.join(GALLERY, "knowledge-graph.json"), encoding="utf-8"))
    papers = [n["id"][3:] for n in g["nodes"] if n["kind"] == "kpaper"]
    abstracts = load_abstracts()
    cn_rels = load_cn_rels()
    # 已有
    try: existing = json.load(open(OUT, encoding="utf-8"))
    except Exception: existing = {}
    todo = papers if force else [p for p in papers if p not in existing]
    if only_missing:
        todo = [p for p in papers if p not in existing]
    if limit: todo = todo[:limit]
    print(f"论文 {len(papers)} · 待生成 {len(todo)} · 有Abstract {sum(1 for p in todo if p in abstracts)} · 有中文关联 {sum(1 for p in todo if p in cn_rels)}")
    done = 0; used_llm = 0; used_cn = 0
    t0 = time.time()
    for i, pid in enumerate(todo):
        if pid in abstracts and abstracts[pid]:
            s = ollama_summarize(abstracts[pid])
            if s:
                existing[pid] = {"summary": s, "source": "qwen2.5:3b@abstract"}
                used_llm += 1
            else:
                existing[pid] = {"summary": cn_rels.get(pid, ""), "source": "cn-rel" if pid in cn_rels else "placeholder"}
                if pid in cn_rels: used_cn += 1
        elif pid in cn_rels:
            existing[pid] = {"summary": cn_rels[pid], "source": "cn-rel-table"}
            used_cn += 1
        else:
            existing[pid] = {"summary": "", "source": "placeholder"}
        done += 1
        if done % 5 == 0:
            print(f"  {done}/{len(todo)} ({time.time()-t0:.0f}s) LLM:{used_llm} CN:{used_cn}")
            json.dump(existing, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(existing, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    filled = sum(1 for v in existing.values() if v.get("summary"))
    print(f"✅ 完成: {done} 篇 | 累计 {len(existing)} 有概况 {filled} (LLM {used_llm} + 中文列 {used_cn}) | 耗时 {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
