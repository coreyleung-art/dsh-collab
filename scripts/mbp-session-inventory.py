#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mbp-session-inventory.py v2 — DSH 会话记录清单工具（zstandard 流式解压）

解压 ~/.dsh/sessions 全部 zstd JSONL 会话，产出结构化清单：
每会话：工作区 / 会话ID / 标题 / 时间范围 / 消息数 / 角色分布 / 首条用户消息 / 主题关键词
用法: python3 mbp-session-inventory.py [out_dir]
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, sys, glob, re
import zstandard as zstd
from collections import Counter

SESS = os.path.expanduser("~/.dsh/sessions")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/dsh-collab/archaeology-mbp/L3-sessions")

def read_session(fp):
    dctx = zstd.ZstdDecompressor()
    with open(fp, "rb") as fh:
        return dctx.stream_reader(fh).read()

def txt_of(content):
    """提取 data.content 或 data.message.content 的文本"""
    out = []
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict):
                t = c.get("text") or c.get("content") or ""
                if t:
                    out.append(str(t))
            elif isinstance(c, str):
                out.append(c)
    elif isinstance(content, dict):
        m = content.get("message") or content
        c = m.get("content")
        if isinstance(c, list):
            for x in c:
                if isinstance(x, dict) and x.get("text"):
                    out.append(str(x["text"]))
        elif isinstance(c, str):
            out.append(c)
    return " ".join(out)

def analyze(fp):
    raw = read_session(fp)
    lines = [l for l in raw.decode("utf-8", "ignore").splitlines() if l.strip()]
    evs = []
    for l in lines:
        try:
            evs.append(json.loads(l))
        except Exception:
            continue
    title, cwd = "", ""
    users, assts, tools, goals = [], [], 0, []
    times = []
    for e in evs:
        t = e.get("type", "")
        ts = e.get("time")
        if ts: times.append(ts)
        d = e.get("data") or {}
        if t == "session":
            cwd = d.get("cwd") or e.get("cwd") or ""
        elif t == "session/title":
            title = d.get("title", "")
        elif t == "user/message":
            users.append(txt_of(d.get("content")))
        elif t == "assistant/message":
            assts.append(txt_of((d.get("message") or {}).get("content")))
        elif t in ("tool/call", "tool/code-dispatch"):
            tools += 1
        elif t == "goal/change":
            g = d.get("goal") or {}
            if g.get("objective"):
                goals.append(g["objective"][:120])
    tmin = min(times) if times else 0
    tmax = max(times) if times else 0
    def iso(ms):
        import datetime
        return datetime.datetime.fromtimestamp(ms/1000).strftime("%m-%d %H:%M")
    first_user = next((u.strip()[:200] for u in users if u.strip()), "")
    # 主题关键词
    alltext = " ".join(users[:40]) + " " + title
    kw = ["CLD", "dsh", "插件", "法拍", "fapai", "景鸿", "会话", "跨机", "运维", "审计",
          "向量", "Chroma", "插件开发", "错误", "修复", "压测", "黑板", "情报", "采购",
          "花店", "花材", "银行", "监控", "部署", "打包", "market", "profile", "考古",
          "简历", "招聘", "论文", "ERP", "飞书", "企微", "外卖", "小程序"]
    hits = [k for k in kw if k.lower() in alltext.lower()]
    return {
        "path": fp,
        "file": os.path.basename(fp),
        "size_kb": os.path.getsize(fp) // 1024,
        "cwd": cwd,
        "title": title[:60],
        "users": len(users), "assistants": len(assts), "tools": tools,
        "tmin": iso(tmin), "tmax": iso(tmax),
        "first_user": first_user,
        "goals": goals[:3],
        "kw": hits,
    }

def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(SESS, "**", "*.zstd"), recursive=True))
    rows = []
    for fp in files:
        try:
            rows.append(analyze(fp))
        except Exception as ex:
            rows.append({"file": os.path.basename(fp), "err": str(ex)[:80]})
    out = os.path.join(OUT, "session-inventory.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    ok = [r for r in rows if "err" not in r]
    print("成功 %d / 失败 %d | 用户消息 %d / 助手消息 %d / 工具调用 %d" % (
        len(ok), len(rows)-len(ok),
        sum(r["users"] for r in ok), sum(r["assistants"] for r in ok),
        sum(r["tools"] for r in ok)))
    print("=== 会话清单（按用户消息数降序前 30）===")
    for r in sorted(ok, key=lambda x: -x["users"])[:30]:
        print("[U%3d A%3d T%3d %s~%s] %s" % (
            r["users"], r["assistants"], r["tools"], r["tmin"], r["tmax"], r["title"][:36]))
        print("    cwd=%s" % r["cwd"][:50])
        print("    首用户: %s" % r["first_user"][:70])
        print("    主题: %s" % ",".join(r["kw"]))
    print("清单已写:", out)

if __name__ == "__main__":
    main()
