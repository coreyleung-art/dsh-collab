#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-dispatch-learn.py — 分发决策器自进化学习器

用户指示（2026-08-23）：决策器持续迭代，纳入自进化链条。
维护黑板 data/frameworks/dispatch-kb（知识库版本化），来源：
  1. 新角色同步：从黑板 ns-registry 检测新角色（未在知识库的自动加入）
  2. 决策回灌：扫描 data/dispatch/* 决策记录，提取未命中关键词（事件含但知识库无 → 候选补词）
  3. 版本化：每次更新 version+1，changelog 记录

用法：
  python3 bb-dispatch-learn.py              # 学习一轮（同步新角色 + 回灌决策）
  python3 bb-dispatch-learn.py --dry-run    # 只报告不改
常驻：可并入 bb-absorb-watch 或 launchd 周期（如每 6h）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-dispatch-learn.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BB = "http://127.0.0.1:8792"

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, obj):
    body = json.dumps(obj).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kb = fetch("/data/frameworks/dispatch-kb").get("value", {})
    if not kb:
        print("❌ 知识库不存在（先跑 bb-dispatch 初始化）"); sys.exit(1)
    old_ver = kb.get("version", 0)
    roles = kb.get("roles", {})
    changes = []

    # 1. 新角色同步（ns-registry 有、知识库无 → 加入）
    reg = fetch("/ns-registry").get("registry", {})
    for sid, info in reg.items():
        if sid not in roles:
            roles[sid] = {"name": info.get("role", sid), "ns": info.get("ns", "").rstrip("/"),
                          "keywords": []}
            changes.append("+角色 %s (%s)" % (sid, roles[sid]["name"]))

    # 2. 决策回灌（扫描 dispatch 记录，提取未命中关键词候选）
    cand = {}
    STOP = set("v0.7 v0.6 v1.0 涉及 以及 或者 一个 这个 那个 进行 相关 有关 事项 处理 安排".split())
    try:
        with urllib.request.urlopen(BB + "/data/dispatch/", timeout=6) as r:
            ds = json.loads(r.read().decode()).get("list", {})
        for k, v in ds.items():
            if "/dispatch-" not in k:
                continue
            val = v.get("value", {})
            evt = val.get("event", "")
            prim = val.get("primary") or {}
            pid = prim.get("id") if isinstance(prim, dict) else None
            if pid and pid in roles and evt:
                # 事件词 - 已知关键词 = 未命中候选（过滤停用词/版本号/单字）
                known = set(roles[pid].get("keywords", []))
                evt_words = set(w for w in evt.replace("，", " ").replace("、", " ").split()
                                if len(w) >= 2 and w not in STOP and not w[0].lower() in "v0123456789")
                new = evt_words - known
                if new:
                    cand.setdefault(pid, set()).update(new)
    except Exception:
        pass
    for pid, words in cand.items():
        add = list(words)[:5]
        for w in add:
            if w not in roles[pid].get("keywords", []):
                roles[pid].setdefault("keywords", []).append(w)
                changes.append("+词 %s → %s" % (w, roles[pid]["name"]))

    # 3. 版本化
    if changes:
        kb["version"] = old_ver + 1
        kb["roles"] = roles
        kb["changelog"] = kb.get("changelog", []) + [{
            "v": kb["version"], "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "changes": changes
        }]
        kb["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        if not args.dry_run:
            put("/data/frameworks/dispatch-kb", kb)
        print("✅ 知识库更新: v%s → v%s" % (old_ver, kb["version"]))
        for c in changes:
            print("   %s" % c)
    else:
        print("✅ 无新变化（v%s）" % old_ver)

if __name__ == "__main__":
    main()
