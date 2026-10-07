#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily-review-group v1.0 (HR) — 每日评价分析/差评预警发群（用户指令 2026-08-21）

读差评数据（aa528267 每日 10:00 落盘）→ 统计聚合（零 LLM）→ markdown 分析 → 8790/send target=群 chat_id 回发。
用法：python3 daily-review-group.py [--data-dir <dir>] [--chat-id <id>] [--dry-run]
群 chat_id（外联确认）：wrObL9WAAAmpV27LFG0NMGX4dZHAXngQ（新群）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, glob, datetime, urllib.request, re

GROUP_CHAT = "wrObL9WAAAmpV27LFG0NMGX4dZHAXngQ"
DATA_DIRS = [
    os.path.expanduser("~/Documents/trae_projects/openclaw-multi-agent-system/docs/reviews"),
    os.path.expanduser("~/dsh-collab/docs/reviews"),
    os.path.expanduser("~/waimai/docs/reviews"),
]
PUSH_URL = "http://127.0.0.1:8790/send"

def today(): return datetime.date.today().isoformat()

def find_data(data_dir):
    if data_dir:
        DATA_DIRS.insert(0, data_dir)
    for d in DATA_DIRS:
        files = sorted(glob.glob(os.path.join(d, "bad-review-*.md")))
        if files:
            return files[-1], d
    return None, None

def parse_reviews(path):
    """从差评报告 md 提取统计（店分布/分类关键词），零 LLM"""
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        text = ""
    stores = {}
    cats = {"花材品质": 0, "花图不符": 0, "包装": 0, "配送": 0, "其他": 0}
    for line in text.splitlines():
        for s in ["佛山", "初蘅", "江南西", "客村", "天河", "体育东"]:
            if s in line:
                stores[s] = stores.get(s, 0) + 1
        for c in cats:
            if c in line:
                cats[c] += 1
    total = sum(stores.values()) or len([1 for l in text.splitlines() if l.strip().startswith("-")])
    return {"total": total, "stores": stores, "cats": cats, "date": os.path.basename(path).replace("bad-review-", "").replace(".md", "")}

def build_md(stats):
    if not stats:
        return "## 📊 今日评价分析\n\n暂无差评数据（采集未运行或未落盘）"
    L = ["## 📊 评价分析 / 差评预警 · " + stats["date"], ""]
    L.append("**今日差评：%d 条**" % stats["total"])
    if stats["stores"]:
        L.append("\n**门店分布**：" + " · ".join("%s %d" % (k, v) for k, v in sorted(stats["stores"].items(), key=lambda x: -x[1])))
    L.append("\n**问题分类**：" + " · ".join("%s %d" % (k, v) for k, v in sorted(stats["cats"].items(), key=lambda x: -x[1]) if v > 0))
    L.append("\n_自动聚合 · 每日 11:00 · 详细见差评报告_")
    return "\n".join(L)

def push(text, chat_id):
    data = json.dumps({"channel": "wecom", "level": "P1", "source": "daily-review",
                       "text": text[:3500], "target": chat_id}).encode()
    req = urllib.request.Request(PUSH_URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status, r.read().decode("utf-8", "ignore")[:120]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="")
    ap.add_argument("--chat-id", default=GROUP_CHAT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path, d = find_data(args.data_dir)
    if not path:
        print("NO_DATA: 未找到差评报告（检查数据目录）")
        return
    stats = parse_reviews(path)
    md = build_md(stats)
    print("SOURCE:", path)
    print(md)
    if not args.dry_run:
        try:
            st, resp = push(md, args.chat_id)
            print("PUSH:", st, resp)
        except Exception as ex:
            print("PUSH_FAIL:", ex)

if __name__ == "__main__":
    main()
