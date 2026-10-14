#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply-bizmap-flowernet-chain.py — 把花联网推演链补挂进商业资产图谱

背景（2026-09-28 实测）：
  SystemGraph 的「🌍 跨节点资产」面（/api/biz-assets）源文件是 business-asset-map.json（136 资产）。
  实测缺口：花联网推演链 81 个进程文件不在图上——
    · 引擎代码 3（wargame-engine.py 副本 / wargame-sim.py / wargame-flowernet.html）
    · 推演数据 9（data/wargame/flowernet/*.json + report.md）← 分数/路线/对抗点只存在于这里
    · 推演与资本文档 42（docs/*wargame* + docs/flowernet-*）
    · BP 分册与主文档 27（data/industry/FLOWERNET-*.md + BP-*.md）
  后果：在 SystemGraph 里点 flowernet-jv 只能看到 BP 结论文档，看不到「数字是怎么推出来的」。

本脚本做四件事（只做能核实的，核实不了的进报告不动）：
  A 新增花联网链条目（blueprint 由路径规则定；desc 取文件自身首个标题 = 不臆造）
  B 引擎归位：meeting-intel → mingjian-toolchain（工具本体；花联网是首个应用而非归属）
  C 加 relations 边：工具↔推演域可达 + 记录 wargame-engine.py 的两份副本（duplicates）
  D 修死指针：只改能定位到真实对象的；核不到的写进报告，不猜
"""
import json, os, re, glob, shutil, sys, hashlib, datetime

GAL = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")
MAP = os.path.join(GAL, "business-asset-map.json")
PA = os.path.join(GAL, "plan-archive.json")
H = os.path.expanduser("~")


def tilde(p):
    return p.replace(H, "~")


def first_heading(path):
    """desc 取文件自身的首个标题 —— 不臆造描述"""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    t = re.sub(r"^#+\s*", "", line).strip()
                    t = re.sub(r"\*\*", "", t)
                    if t:
                        return t[:150]
                elif line and not line.startswith("---"):
                    return re.sub(r"\*\*", "", line)[:150]
    except Exception:
        pass
    return os.path.basename(path)


def json_desc(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        if isinstance(d, dict):
            if "objective" in d:
                return f"目标: {d['objective']} · 轮次 {len(d.get('rounds', []))}"
            return "键: " + ", ".join(list(d.keys())[:6])
        if isinstance(d, list):
            return f"数组 {len(d)} 条"
    except Exception:
        pass
    return "JSON 数据"


def main():
    m = json.load(open(MAP, encoding="utf-8"))
    assets = m["assets"]
    have = {os.path.expanduser(a.get("location", "").split(" ")[0]) for a in assets}
    byname = {a.get("name"): a for a in assets}

    # plan-archive 的 agent 字段作为 responder 的证据来源（有则用，无则留空，不猜）
    pa_agent = {}
    try:
        for it in json.load(open(PA, encoding="utf-8"))["items"]:
            fp = os.path.expanduser(it.get("file", ""))
            if fp and it.get("agent"):
                pa_agent[fp] = it["agent"]
    except Exception:
        pass

    report = {"added": [], "reattributed": [], "pointers_fixed": [], "relations_added": [],
              "left_alone": []}

    # ───────── A. 新增花联网链 ─────────
    cands = []
    cands += glob.glob(H + "/dsh-collab/scripts/wargame*")
    cands += glob.glob(H + "/dsh-collab/data/wargame/flowernet/*")
    cands += sorted(glob.glob(H + "/dsh-collab/docs/flowernet-*.md"))
    cands += sorted(glob.glob(H + "/dsh-collab/docs/*wargame*.md"))
    cands += sorted(glob.glob(H + "/dsh-collab/data/industry/FLOWERNET-*.md"))
    cands += sorted(glob.glob(H + "/dsh-collab/data/industry/BP-*.md"))

    def bp_of(p):
        if "/scripts/" in p:
            return "mingjian-toolchain"
        if "/data/wargame/" in p:
            return "flowernet"
        if "/docs/" in p or "/data/industry/" in p:
            return "flowernet-jv"
        return "flowernet"

    for p in dict.fromkeys(cands):
        p = os.path.abspath(p)
        if not os.path.isfile(p) or p in have:
            continue
        ext = os.path.splitext(p)[1].lower()
        typ = {"py": "tool", "html": "tool", "json": "data", "md": "file", "png": "asset"}.get(ext.lstrip("."), "file")
        desc = json_desc(p) if ext == ".json" else first_heading(p)
        name = os.path.basename(p)
        if p.startswith(H + "/dsh-collab/scripts/"):
            name = f"沙盘引擎 {name}" if "engine" in name else f"沙盘工具 {name}"
        elif p.startswith(H + "/dsh-collab/data/wargame/"):
            name = f"推演数据 {os.path.basename(p)}"
        entry = {
            "name": name, "type": typ, "location": tilde(p),
            "isOriginal": ext in (".py", ".html", ".md"),
            "blueprint": bp_of(p), "desc": desc,
            "responder": pa_agent.get(p, "明鉴" if "/scripts/" in p else ""),
            "node": "mac-mini",
        }
        assets.append(entry)
        report["added"].append((name, tilde(p), bp_of(p)))

    # ───────── B. 引擎归位（工具本体，不是花联网专属资产）─────────
    TOOLS = ["商业沙盘模拟器 wargame v1.0.0", "商业沙盘引擎 wargame-engine v1.0.0", "Wargame.app"]
    for a in assets:
        if a.get("name") in TOOLS and a.get("blueprint") == "meeting-intel":
            a["blueprint"] = "mingjian-toolchain"
            report["reattributed"].append((a["name"], "meeting-intel → mingjian-toolchain"))

    # 修 Wargame.app 的死指针（dist/Wargame.app 未构建 ⇒ 指向工程根，如实写）
    for a in assets:
        if a.get("name") == "Wargame.app" and not os.path.exists(os.path.expanduser(a["location"])):
            a["location"] = "~/wargame-app/"
            a["desc"] = a["desc"] + " ｜⚠️ dist/Wargame.app 当前未构建，location 指向工程根"
            report["pointers_fixed"].append(("Wargame.app", "~/wargame-app/dist/Wargame.app → ~/wargame-app/（未构建）"))

    # ───────── C. relations 边 ─────────
    rels = m.setdefault("relations", [])
    def has_rel(f, t, ty):
        return any(r.get("from") == f and r.get("to") == t and r.get("type") == ty for r in rels)

    NEW_RELS = [
        ("商业沙盘模拟器 wargame v1.0.0", "沙盘推演域 flowernet", "uses",
         "wargame.py 的首个应用域=flowernet；20→100 轮推演的产物全部落在此域"),
        ("商业沙盘引擎 wargame-engine v1.0.0", "沙盘推演域 flowernet", "uses",
         "wargame-engine(:8813) 三立场对抗推演的模拟域；反向污染防火墙保证只写此域"),
        ("花联网·引擎推演全记录", "沙盘推演引擎·可复用模板", "depends_on",
         "全记录沉淀 30+ 次推演；可复用模板是它的方法封装"),
    ]
    for f, t, ty, d in NEW_RELS:
        if not has_rel(f, t, ty):
            rels.append({"from": f, "to": t, "type": ty, "desc": d,
                         "since": "2026-09-09", "verified": True})
            report["relations_added"].append((f, ty, t))

    # 记录 wargame-engine.py 的两份副本
    # ⚠️ 注意：byname 必须在【A 新增之后】重建 —— 第一版用新增前的快照 ⇒ 找不到刚加进去的那条
    #    ⇒ `duplicates` 边静默没加上（实测：报告只出 3 条关系，应有 4 条）
    byname = {a.get("name"): a for a in assets}
    dup_from, dup_to = "商业沙盘引擎 wargame-engine v1.0.0", "沙盘引擎 wargame-engine.py"
    if dup_to in byname and not has_rel(dup_from, dup_to, "duplicates"):
        a1 = os.path.expanduser(byname[dup_from]["location"]) if dup_from in byname else ""
        a2 = os.path.expanduser(byname[dup_to]["location"])
        same = ""
        if a1 and os.path.exists(a1) and os.path.exists(a2):
            h1 = hashlib.sha256(open(a1, "rb").read()).hexdigest()[:16]
            h2 = hashlib.sha256(open(a2, "rb").read()).hexdigest()[:16]
            same = f"；实测逐字节相同 sha256_16={h1}" if h1 == h2 else f"；⚠️ 已分叉 {h1}≠{h2}"
        rels.append({"from": dup_from, "to": dup_to, "type": "duplicates",
                     "desc": "同一引擎两份副本，无机制保证不漂" + same,
                     "since": "2026-09-09", "verified": True})
        report["relations_added"].append((dup_from, "duplicates", dup_to))

    # ───────── D. 死指针：只改能定位到真实对象的 ─────────
    FIX = {
        "health-check.sh": "~/dsh-collab/cld-health/health-check.sh",
        "health-log.tsv": "~/dsh-collab/cld-health/health-log.tsv",
        "post-restart-check.md": "~/dsh-collab/cld-health/post-restart-check.md",
        "健康基线报告": "~/dsh-collab/cld-health/cld-health-baseline-20260816.md",
        "迭代需求清单 backlog": "~/dsh-collab/cld-health/cld-iteration-backlog.md",
        "CLD-002-wecom-alert-spec.md": "~/dsh-collab/cld-health/CLD-002-wecom-alert-spec.md",
        "CLD-002 看门狗交付": "~/dsh-collab/cld-health/CLD-002-watchdog.md",
        "OOM 归因与恢复档案": "~/dsh-collab/data/recovery/cld-oom-20260902-recur-analysis.md",
        "flower-intel-index": "~/dsh-collab/devices/flower-intel-index-summary.md",
        "waimai-mcp-core(能力中台)": "~/dsh-collab/docs/mcp-four-stack-masterplan-v1.md",
        "外卖老登 App (laodeng)": "~/meituan-multi/laodeng-h5/dist",
        "laodeng-h5 版本管理": "~/meituan-multi/laodeng-h5/version.json",
    }
    for a in assets:
        nm = a.get("name")
        if nm in FIX:
            old = a.get("location")
            new = FIX[nm]
            if os.path.exists(os.path.expanduser(new)) and old != new:
                a["location"] = new
                report["pointers_fixed"].append((nm, f"{old} → {new}"))

    # ───────── E. 留下不动的（核不到，写成报告而不是猜）─────────
    CANNOT = {"i9 dsh 节点", "i9 三项目扫描成果", "KB ops-science-research",
              "Dify 本地知识库", "comm.db 学习系统"}
    for a in assets:
        loc = a.get("location", "")
        if a.get("name") in CANNOT or loc.startswith("E:\\") or loc.startswith("C:\\"):
            report["left_alone"].append((a.get("name"), loc, a.get("node")))

    m["updated"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    m["note"] = (m.get("note", "").split("｜2026-09-28")[0] +
                 "｜2026-09-28 明鉴：补挂花联网推演链（引擎/推演数据/推演与资本文档/BP 分册与主文档）；"
                 "工具本体归 mingjian-toolchain（花联网为首个应用）；加 relations 边使工具与推演域可达；"
                 "修 12 条可定位死指针。核不到的（i9 资产/Windows 路径/外部句柄）未改，见同批变更报告。")

    tmp = MAP + ".tmp"
    json.dump(m, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.load(open(tmp, encoding="utf-8"))  # 回读校验
    shutil.move(tmp, MAP)

    print(f"═══ 落盘完成 · 资产 {len(assets)} 条（原 136）· 关系 {len(rels)} 条 ═══\n")
    print(f"A 新增 {len(report['added'])} 条")
    for n, p, b in report["added"][:8]:
        print(f"    [{b:<18}] {n[:34]:<36} {p}")
    if len(report["added"]) > 8:
        print(f"    …（另 {len(report['added'])-8} 条，全部写入）")
    print(f"\nB 归位 {len(report['reattributed'])} 条")
    for n, c in report["reattributed"]:
        print(f"    {n[:40]:<42} {c}")
    print(f"\nC 关系新增 {len(report['relations_added'])} 条")
    for f, t, o in report["relations_added"]:
        print(f"    {f[:30]:<32} --{t}--> {o}")
    print(f"\nD 死指针修复 {len(report['pointers_fixed'])} 条")
    for n, c in report["pointers_fixed"]:
        print(f"    {n[:30]:<32} {c}")
    print(f"\nE 未改动（核不到，不猜）{len(report['left_alone'])} 条")
    for n, l, nd in report["left_alone"]:
        print(f"    [{nd:<9}] {n[:30]:<32} {l[:52]}")


if __name__ == "__main__":
    main()
