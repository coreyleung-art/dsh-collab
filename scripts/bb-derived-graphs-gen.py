#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-derived-graphs-gen.py v1.0.0 —— 派生图谱【派生字段】生成器

★ 出处（2026-10-15 · 用户裁决「3 个 orphaned 派生图谱写生成器」· 经 J44 建前门修正）：
  ★★★ 门 + 文档阅读【改变了结论】——原本三个里**只有两个真的需要生成器**：
    · `business-asset-map.json` ⇒ ★ **不是 orphaned**：`bb-asset-relations.py` 就是它的维护工具
      （`--add`/`--add-asset`/`--del` 人工逐条确认；refresh 里作**只读 selfcheck** 是设计如此）
      ⇒ ★ **改分类，不建生成器**（★ 减法优先）
    · `knowledge-graph.json` ⇒ 图内容是**策展的**（节点手工带 `dim`/`color`/`r`），
      而 **`reportCount`/`paperCount` 是派生的** —— ★ 且它**曾自相矛盾**：
      自带 `_reportCountFix` 记录「本文件自报 89，而自身 nodes 里实有 92（差 3）」
      ⇒ ★★ **这正是「人工维护派生字段」会天然产生的错**。
    · `mechanism.json` ⇒ **`gate_health` 可派生**，且**它自注陈旧**：
      `gate_health` 基于 75 条规则的报告，而 `_ledgerNow` 说账本已到 **79**
      ⇒ ★ 它自己写了「两者不是同一时刻的读数」。

★★★ 设计原则（★ 与 hardware/workflow 两个生成器同法）：
  ★ **只动【派生字段】，绝不碰【策展内容】。**
  本工具【不新增/不删除任何节点、边、协议、门】—— ★ 它只做两件事：
    ① 用【实际内容】重算派生计数（★ 让文件不再自相矛盾）
    ② 补/更新元信息（version/updated/generatedAt/generatedBy/sourceOfTruth）

★ 三态（★ 与今晚其它判据一致）：
  · rc=0 一致（重算结果与现状相同）· rc=1 有差异（★ 发现文件自相矛盾 = 履行职责）· rc=2 不可判

★ 用法：
  python3 bb-derived-graphs-gen.py --selfcheck
  python3 bb-derived-graphs-gen.py                     # 演练（零变更）
  python3 bb-derived-graphs-gen.py --go                # 真写
  python3 bb-derived-graphs-gen.py --target mechanism  # 只做 mechanism
  python3 bb-derived-graphs-gen.py --json
"""
import os, sys, json, argparse, datetime, subprocess

VERSION = "1.0.0"
R006_SELFCHECK = True

SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
GALLERY = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")
KG = os.path.join(GALLERY, "knowledge-graph.json")
MECH = os.path.join(GALLERY, "mechanism.json")
GATE_REPORT = os.path.expanduser("~/dsh-collab/rules-registry/gate-audit-report-latest.json")
LOG = os.path.expanduser("~/dsh-collab/logs/bb-derived-graphs-gen.log")


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def selfcheck():
    print("== bb-derived-graphs-gen 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · 读 knowledge-graph.json / mechanism.json / rules-registry/gate-audit-report-latest.json")
    print("  · ★ 只重算【派生字段】，★ 不新增/不删除任何节点·边·协议·门")
    print("  · 写回同路径（★ 仅 --go）")
    print("【② 不该发生路径清单】")
    print("  · ★ **不增删策展内容** · 不删文件 · 不改权限 · 不访问网络")
    print("【③ 依赖完整性】")
    print("  · knowledge-graph: %s" % ("存在 ✓" if os.path.exists(KG) else "★ 缺失"))
    print("  · mechanism:       %s" % ("存在 ✓" if os.path.exists(MECH) else "★ 缺失"))
    print("  · gate-audit 报告: %s" % ("存在 ✓" if os.path.exists(GATE_REPORT) else "★ 缺失（mechanism 模式将判不可判）"))
    print("  · 标准库: json/os/argparse · python %s" % sys.version.split()[0])
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    return 0


def gen_knowledge():
    """★ 用【实际 nodes】重算派生计数；★ 不碰任何节点"""
    d = json.load(open(KG, encoding="utf-8"))
    nodes = d.get("nodes") or []
    by_kind = {}
    for n in nodes:
        by_kind[n.get("kind")] = by_kind.get(n.get("kind"), 0) + 1
    actual_report = by_kind.get("krep", 0)
    actual_paper = by_kind.get("kpaper", 0)
    cur_report = d.get("reportCount")
    cur_paper = d.get("paperCount")
    diff = []
    if cur_report != actual_report:
        diff.append("reportCount %s → %s" % (cur_report, actual_report))
    if cur_paper != actual_paper:
        diff.append("paperCount %s → %s" % (cur_paper, actual_paper))
    newd = dict(d)
    newd["reportCount"] = actual_report
    newd["paperCount"] = actual_paper
    newd["kinds"] = by_kind                      # ★ 新派生字段：kind 分布（★ 便于自查矛盾）
    newd["version"] = d.get("version") or "1.0.0"
    newd["updated"] = datetime.date.today().isoformat()
    newd["generatedAt"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newd["generatedBy"] = "bb-derived-graphs-gen.py v" + VERSION
    newd["sourceOfTruth"] = "★ 本文件自身 nodes（★ 派生计数由【实际节点】重算，非人工维护）"
    return newd, diff, {"nodes": len(nodes), "edges": len(d.get("edges") or []), "byKind": by_kind}


def gen_mechanism():
    """★ 用 gate-audit 报告重算 gate_health；★ 不碰 protocols/gates/locks/links"""
    d = json.load(open(MECH, encoding="utf-8"))
    if not os.path.exists(GATE_REPORT):
        return None, ["★ 不可判：找不到 %s" % GATE_REPORT], {}
    rep = json.load(open(GATE_REPORT, encoding="utf-8"))
    # ★★★ 2026-10-15【本线自己踩的坑，如实记】：
    #   ★ 我第一版写的是 `rep.get("paper_gates")` —— ★★ 而报告里的 `paper_gates` 是 **list（48 条）**，
    #     不是计数 ⇒ ★ 我把【整个列表】写进了本该是整数的字段，★ 并把 `structural_gates` 写成了 None。
    #   ⇒ ★★ 与今晚第 ②③⑧ 号 bug【同族】：**没核字段的真实形状就取值。**
    #   ★ 修法：**一律用 len() 从【实际集合】算**，★ 而不是信字段名暗示的类型。
    #   报告真实形状（实测）: `rules`=list(75) · `paper_gates`=list(48) · `stats`=dict · `source`=str
    # ★★ 优先用报告【自带的 stats】（★ 实测 `{"total":75,"structural":27,"paper":48,"doc_only":0}`）
    #   —— ★ 那是报告作者自己的口径，★ 比我从集合推更权威。
    stats = rep.get("stats") or {}

    def _pick(stat_key, list_key):
        v = stats.get(stat_key)
        if isinstance(v, int):
            return v, "stats.%s" % stat_key
        return len(rep.get(list_key) or []), "len(%s)" % list_key

    total, total_src = _pick("total", "rules")
    paper, paper_src = _pick("paper", "paper_gates")
    structural, struct_src = _pick("structural", "__structural_fallback__")
    if struct_src.startswith("len("):
        # ★ stats 无显式值 ⇒ 用【可核的派生式】（★ 实测 75-48=27 与原值一致）
        structural, struct_src = total - paper, "派生 total-paper"
    _srcs = {"total": total_src, "paper": paper_src, "structural": struct_src}
    if total == 0:
        return None, ["★ 不可判：gate-audit 报告的 rules 为空（★ 不猜）"], {}
    # ★ 账本条数（★ 用于暴露「两者不是同一时刻」这一事实）
    # ★★★ J44 复用（2026-10-15）：★ **不自己解析 RULES.md** ——
    #   ★ 本线第一版扫「前 N 行取最大条数」⇒ 实测 **null**（★ 因为条数在**第 15 行**
    #     的 `> v2.23.12 | 79 条 | …`，★ 不在前 8 行）⇒ ★ **自己解析会随格式漂移而静默失效**。
    #   ★★ 而本机【已有】`rules-integrity.py --json` 给出 `declared.count` 与 `actual_headings`
    #     （★ 且它自己会报「计数不可核 = 声明无效」）⇒ ★ **调用它，不重写它**。
    ledger_n = None
    try:
        r = subprocess.run(["python3", os.path.join(SCRIPTS, "rules-integrity.py"), "--json"],
                           capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        ri = json.loads((r.stdout or "").strip())
        ledger_n = (ri.get("declared") or {}).get("count")
    except Exception:
        ledger_n = None
    newgh = {
        "ts": datetime.date.today().isoformat(),
        "source": "gate-auditor · " + os.path.basename(GATE_REPORT),
        "total_rules": total,
        "structural_gates": structural,
        "paper_gates": paper,
        "note": "★ 本值由 bb-derived-graphs-gen.py 从 gate-audit 报告【重算】（★ 非人工抄写）",
        "ledger_rules": ledger_n,
        "consistent": (ledger_n is None or ledger_n == total),
        "_valueSources": _srcs,
    }
    cur = d.get("gate_health") or {}
    diff = []
    if cur.get("total_rules") != total:
        diff.append("gate_health.total_rules %s → %s" % (cur.get("total_rules"), total))
    if ledger_n is not None and ledger_n != total:
        diff.append("★ 报告(%s) 与账本(%s) 仍不同 ⇒ ★ 本字段【如实标为不一致】，★ 不伪装成同一时刻"
                    % (total, ledger_n))
    newd = dict(d)
    newd["gate_health"] = newgh
    newd["version"] = d.get("version") or "1.0.0"
    newd["updated"] = datetime.date.today().isoformat()
    newd["generatedAt"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    newd["generatedBy"] = "bb-derived-graphs-gen.py v" + VERSION
    newd["sourceOfTruth"] = "protocols/gates/locks/links=策展；gate_health=" + os.path.basename(GATE_REPORT)
    return newd, diff, {"protocols": len(d.get("protocols") or []), "gates": len(d.get("gates") or []),
                        "total_rules": total, "ledger_rules": ledger_n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--target", choices=["knowledge", "mechanism", "all"], default="all")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()

    results = {}
    anydiff = False
    undecidable = False
    for tgt, path, fn in (("knowledge", KG, gen_knowledge), ("mechanism", MECH, gen_mechanism)):
        if a.target not in (tgt, "all"):
            continue
        if not os.path.exists(path):
            results[tgt] = {"ok": False, "state": "不可判", "note": "文件不存在"}
            undecidable = True
            continue
        newd, diff, info = fn()
        if newd is None:
            results[tgt] = {"ok": False, "state": "不可判", "diff": diff, "info": info}
            undecidable = True
            continue
        real = [x for x in diff if not x.startswith("★")]   # ★ 去掉「如实标注」类说明
        if real:
            anydiff = True
        state = "有差异" if real else "一致"
        if a.go:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(newd, f, ensure_ascii=False, indent=1)
        results[tgt] = {"ok": True, "state": state, "diff": diff, "info": info, "wrote": a.go}

    code = 2 if undecidable else (1 if anydiff else 0)
    if a.json:
        print(json.dumps({"state": {k: v["state"] for k, v in results.items()},
                          "rc": code, "dry": not a.go, "detail": results, "version": VERSION},
                         ensure_ascii=False))
    else:
        for k, v in results.items():
            print("  %-11s 【%s】%s" % (k, v["state"], "（已写）" if v.get("wrote") else ""))
            for x in v.get("diff") or []:
                print("     · %s" % x)
            if v.get("info"):
                print("     info: %s" % json.dumps(v["info"], ensure_ascii=False)[:150])
        print("  ★ rc=%d %s" % (code, "（★ 演练，零变更）" if not a.go else ""))
    log("target=%s go=%s rc=%d" % (a.target, a.go, code))
    return code


if __name__ == "__main__":
    sys.exit(main())
