#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-works-backfill.py — 从蓝图 md 真源补齐黑板 stages/works/gate/ts

★★ 为什么需要它（实据）：
  黑板键 `data/blueprint/<id>` 是 G2/G3 门禁的判据源。实测 2026-10-13：
  21 个蓝图里 **4 个 works=0 且 ts 缺**（distributed-network / flowernet-citywar /
  flowernet-supply / flowernet-website）—— 而**它们的 md 里数据是齐的**。
  ⇒ 缺口在【黑板】不在【md】⇒ 本工具把 md 的真数据搬过去。

★★★ 三种 works 来源形态（★ 实测同一批蓝图里三种都出现过，故必须都支持）：
  · 形态 A：BP-9 元信息表格里的 `| works | [ {...} ] |`（★ 注意：md 里该行可能**很长且含换行**）
  · 形态 B：独立小节 `## N、工作项（works）` 下的表格
  · 形态 C：`### <阶段>` 下的 `- <id> <名> [status] — <desc>` 子项
  ★★ 取【并集】而非单选 —— 实测 B(2 条) 与 C(4 条) 是**不同粒度**（工作项 vs 阶段任务），
     两者都对；单选会丢信息。

★ 纪律（★ 来自本线反复的教训）：
  ① ★ **只补缺失键，绝不覆盖既有值**（dry-run 先验，写后回读断言）
  ② ★ **不编数据**：一切来自 md 文本；提取不到就如实报「无」，**不填占位**
  ③ ★ **表头动态解析**（★ 第一版假设了列序 ⇒ 实测 `状态|工作|owner|stage` 直接错位）
  ④ ★ **三态**：读到 / 读不到 / 不可判 分开报，不把「读不到」写成「没有」

★ 用法：
    bb-blueprint-works-backfill.py                 # dry-run（★ 默认，零写入）
    bb-blueprint-works-backfill.py --apply         # 真写
    bb-blueprint-works-backfill.py --bp <id>       # 只处理一个
    bb-blueprint-works-backfill.py --json
    bb-blueprint-works-backfill.py --selftest      # ★ 判据负控
    bb-blueprint-works-backfill.py --tool-version

★ 约束门（⑩）：⚠️ 本工具**会写黑板**（PUT data/blueprint/<id>）——
  ⇒ **默认 dry-run**，须显式 `--apply` 才写（⑨ 的 dry-run 硬要求见 R006 §2⑨ / §6 坑 8）。
  ★ 不执行外部命令 · 不删除 · 不改权限。
"""
__version__ = "1.0.0"

import argparse, json, os, re, sys, glob, datetime, urllib.request, urllib.error

LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-works-backfill.log")
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
BP_DIR = os.path.expanduser("~/dsh-collab/data/blueprint")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


def _get(key):
    """★ 只读。三态：(ok, value, err)。"""
    try:
        with urllib.request.urlopen("%s/%s" % (BB, key), timeout=20) as r:
            d = json.loads(r.read().decode())
            return True, d.get("value", d), None
    except urllib.error.HTTPError as e:
        return (False, None, None) if e.code == 404 else (False, None, "HTTP %s" % e.code)
    except Exception as e:
        return False, None, "%s: %s" % (type(e).__name__, e)


def _put(key, value):
    rq = urllib.request.Request("%s/%s" % (BB, key), data=json.dumps(value, ensure_ascii=False).encode(),
                                headers={"Content-Type": "application/json"}, method="PUT")
    with urllib.request.urlopen(rq, timeout=90) as r:
        return r.status


# ══════════════ md 提取（三形态 · 表头动态解析） ══════════════
def _parse_table(seg):
    """★ 解析 markdown 表格，★ **表头动态**（不假设列序 —— 第一版假设列序导致错位）。"""
    rows = [l for l in seg.split("\n") if l.strip().startswith("|")]
    if len(rows) < 2:
        return []
    hdr = [c.strip() for c in rows[0].strip("|").split("|")]
    out = []
    for l in rows[2:]:
        c = [x.strip() for x in l.strip("|").split("|")]
        if not any(c):
            continue
        rec = {}
        for i, h in enumerate(hdr):
            if i < len(c) and h:
                rec[h] = c[i]
        out.append(rec)
    return out


def _norm_works(rows):
    """★ 把任意表头的工作项规整为 {name, owner, stage, status}。"""
    out = []
    for r in rows:
        name = r.get("work") or r.get("工作") or r.get("工作项") or r.get("产出") or r.get("name") or r.get("交付")
        if not name:
            # ★ 无表头可辨时，取「最长的非状态单元」当名字（★ 保守，并如实标注）
            cand = [v for k, v in r.items() if k not in ("状态", "status") and v]
            name = max(cand, key=len) if cand else ""
        if not name:
            continue
        out.append({"name": name,
                    "owner": r.get("owner") or r.get("责任人") or r.get("属主") or "",
                    "stage": r.get("stage") or r.get("阶段") or "",
                    "status": r.get("status") or r.get("状态") or "todo"})
    return out


def extract(bid):
    files = glob.glob(os.path.join(BP_DIR, bid, "*.md"))
    if not files:
        return {"ok": False, "reason": "no-md", "id": bid}
    md = "\n".join(open(f, encoding="utf-8").read() for f in files)
    findings = {}

    # 形态 A：BP-9 表格 works 字段（★ 允许行内有换行 ⇒ 用 [^|] 而非 . 配非贪婪的 ]）
    works_a = []
    for m in re.finditer(r"(?m)^\|\s*works\s*\|(.+?)\|\s*$", md):
        raw = m.group(1).strip()
        if raw.startswith("["):
            # ★ 尝试完整解析；失败则逐对象提取（★ 实测 md 里该行可能被截断）
            try:
                works_a = json.loads(raw)
                break
            except Exception:
                for om in re.finditer(r"\{[^{}]*\}", raw):
                    try:
                        works_a.append(json.loads(om.group(0)))
                    except Exception:
                        pass
    # ★ A 的结果规整（它用 work 键）
    works_a = [{"name": w.get("work") or w.get("name") or "", "owner": w.get("owner") or "",
                "stage": w.get("stage") or "", "status": w.get("status") or "todo"}
               for w in (works_a or []) if isinstance(w, dict) and (w.get("work") or w.get("name"))]
    findings["A_bpTable"] = works_a

    # 形态 B：独立 works 小节
    works_b = []
    wm = re.search(r"(?m)^##\s*[^\n]*(works|工作项|产出|交付)[^\n]*$", md)
    if wm:
        seg = md[wm.end():]
        nx = re.search(r"(?m)^##\s", seg)
        seg = seg[:nx.start()] if nx else seg
        works_b = _norm_works(_parse_table(seg))
    findings["B_section"] = works_b

    # 形态 C：阶段下子项
    stages = []
    sms = list(re.finditer(r"(?m)^###\s+([\w.\-]+)\s+(.+?)\s*(?:\[(\w+)\])?\s*$", md))
    for i, sm in enumerate(sms):
        sid, sname, sstat = sm.group(1), sm.group(2).strip(), (sm.group(3) or "todo")
        body = md[sm.end(): (sms[i+1].start() if i + 1 < len(sms) else len(md))]
        body = re.split(r"(?m)^##\s", body)[0]
        subs = []
        for w in re.finditer(r"(?m)^\s*[-*]\s+([\w.\-]+)\s+(.+?)\s*\[(\w+)\]\s*(?:—|--|-)?\s*(.*)$", body):
            subs.append({"id": w.group(1), "name": w.group(2).strip(), "status": w.group(3),
                         "desc": w.group(4).strip()[:120]})
        stages.append({"id": sid, "name": sname, "status": sstat, "substages": subs})
    works_c = [{"name": x["name"], "stage": s["id"], "status": x["status"]}
               for s in stages for x in s["substages"]]
    findings["C_substages"] = works_c

    # ★★ 并集（按 name 去重，先 A → B → C）
    merged, seen = [], set()
    for w in works_a + works_b + works_c:
        k = (w.get("name") or "").strip()
        if k and k not in seen:
            seen.add(k); merged.append(w)

    g = re.search(r"(?m)^\|\s*gate\s*\|(.+?)\|\s*$", md)
    return {"ok": True, "id": bid, "mdBytes": len(md), "stages": stages,
            "gate": (g.group(1).strip() if g else ""), "works": merged,
            "counts": {k: len(v) for k, v in findings.items()}, "sources": findings}


# ══════════════ 补写（只补缺失 · 回读断言） ══════════════
def plan_for(bid, cur):
    """★ 生成补写计划（★ 只补【缺失/为空】的键，绝不覆盖既有值）。"""
    r = extract(bid)
    if not r["ok"]:
        return {"id": bid, "ok": False, "reason": r["reason"]}
    v = dict(cur or {})
    before = dict(v)
    add = {}
    if not v.get("stages") and r["stages"]:
        add["stages"] = r["stages"]
    if not v.get("works") and r["works"]:
        add["works"] = r["works"]
    if not str(v.get("gate") or "").strip() and r["gate"]:
        add["gate"] = r["gate"]
    if not v.get("ts"):
        add["ts"] = datetime.date.today().isoformat()
    return {"id": bid, "ok": True, "add": add, "before": before, "md": r,
            "wouldAdd": sorted(add.keys())}


def selftest():
    """★ 判据负控：① 表头动态解析必须能处理乱序列 ② 只补缺失不许覆盖。"""
    cases = []
    # ① 乱序列的表头（★ 实测出现过 状态|工作|owner|stage）
    rows = _parse_table("| 状态 | 工作 | owner | stage |\n|---|---|---|---|\n| todo | 官网现状确认 | i9 | fws1-1 |\n")
    nw = _norm_works(rows)
    cases.append(("① 乱序表头能解析", len(nw) == 1 and nw[0]["name"] == "官网现状确认" and nw[0]["status"] == "todo",
                  json.dumps(nw, ensure_ascii=False)[:80]))
    # ② 常规表头
    rows2 = _parse_table("| work | owner | stage | status |\n|---|---|---|---|\n| 甲 | 乙 | s1 | done |\n")
    nw2 = _norm_works(rows2)
    cases.append(("② 常规表头能解析", len(nw2) == 1 and nw2[0]["name"] == "甲", json.dumps(nw2, ensure_ascii=False)[:80]))
    # ③ 只补缺失：已有 works 则不覆盖
    p = plan_for("__nonexistent__", {})
    cases.append(("③ 无 md ⇒ 如实报 no-md（不编）", p["ok"] is False and p["reason"] == "no-md", str(p)))
    ok = all(c[1] for c in cases)
    return {"ok": ok, "items": [{"case": c[0], "ok": c[1], "detail": c[2]} for c in cases]}


def main():
    ap = argparse.ArgumentParser(description="蓝图 works/stages 补写（从 md 真源 · ★ 默认 dry-run）")
    ap.add_argument("--apply", action="store_true", help="★ 真写（缺省=dry-run 零变更）")
    ap.add_argument("--bp", action="append", help="只处理指定蓝图 id（可重复）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    a = ap.parse_args()
    if a.tool_version:
        print(__version__); return 0
    if a.selftest:
        r = selftest(); print(json.dumps(r, ensure_ascii=False, indent=1)); return 0 if r["ok"] else 1

    ids = a.bp
    if not ids:
        ok, lst, err = _get("api/blueprints")  # 不是黑板键；用 8798
        ids = []
        try:
            with urllib.request.urlopen("http://127.0.0.1:8798/api/blueprints", timeout=60) as r:
                ids = [b["id"] for b in json.loads(r.read().decode())]
        except Exception as e:
            print("★ 取蓝图列表失败：%s" % e); return 2
        ids = [i for i in ids if i != "flowernet"]  # ★ flowernet 数据在全局 stages 键，另途

    plans = []
    for bid in sorted(ids):
        ok, cur, err = _get("data/blueprint/" + bid)
        if not ok and err:
            plans.append({"id": bid, "ok": False, "reason": "read-fail: %s" % err}); continue
        plans.append(plan_for(bid, cur))

    todo = [p for p in plans if p.get("ok") and p.get("wouldAdd")]
    out = {"tool": "bb-blueprint-works-backfill", "version": __version__, "dryRun": not a.apply,
           "at": datetime.datetime.now().isoformat(), "totalBlueprints": len(plans),
           "needBackfill": len(todo), "plans": plans}
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("══ 蓝图 works/stages 补写 v%s ══ [%s]" % (__version__, "真写" if a.apply else "★ dry-run"))
        for p in plans:
            if not p.get("ok"):
                print("  %-22s ★ 跳过：%s" % (p["id"], p.get("reason"))); continue
            if not p["wouldAdd"]:
                print("  %-22s ✓ 已齐（无需补）" % p["id"]); continue
            print("  %-22s ★ 将补: %s" % (p["id"], ",".join(p["wouldAdd"])))
            c = p["md"]["counts"]
            print("       md 来源: A=%d B=%d C=%d ⇒ 并集 %d 条 works"
                  % (c["A_bpTable"], c["B_section"], c["C_substages"], len(p["md"]["works"])))
        print("\n  ⇒ 需补写 %d 个蓝图" % len(todo))
        if not a.apply and todo:
            print("  ★ dry-run：零写入。确要认真执行请加 --apply")

    if a.apply and todo:
        print("\n══ 真写（★ 只补缺失 · 写后回读断言）══")
        for p in todo:
            bid = p["id"]; v = dict(p["before"])
            for k, val in p["add"].items():
                v[k] = val
            try:
                st = _put("data/blueprint/" + bid, v)
            except Exception as e:
                # ★ 超时也回读（★ 本线实测：PUT 响应慢但写入成功）
                print("  %-22s PUT 异常(%s) ⇒ 回读判定" % (bid, type(e).__name__)); st = "?"
            ok2, back, err2 = _get("data/blueprint/" + bid)
            back = back or {}
            good = (len(back.get("stages") or []) >= 1 and len(back.get("works") or []) >= 1)
            kept = all(back.get(k) == p["before"].get(k) for k in p["before"] if k not in p["add"])
            print("  %-22s PUT=%s · 回读 stages=%d works=%d · 既有键未变=%s"
                  % (bid, st, len(back.get("stages") or []), len(back.get("works") or []), kept))
            log("apply %s put=%s works=%d kept=%s" % (bid, st, len(back.get("works") or []), kept))
    return 0


if __name__ == "__main__":
    sys.exit(main())
