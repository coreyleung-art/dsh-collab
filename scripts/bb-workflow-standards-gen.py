#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bb-workflow-standards-gen.py v1.0.0 —— 工作流标准【生成器】

★ 出处（2026-10-14 · 用户裁决「补生成器，也补元信息」）：
  `workflow-standards.json` 实测 mtime 35 天陈旧、**无 version 之外的任何时间元信息**，
  且不在 `bb-gallery-refresh.py` 声明的 produces 里 ⇒ **从未接入自动更新路径**。

★★ 设计：人写 / 机器写【分工】
  · `workflow-standards.core.json` = **人工核心**（R006 摘要 · meta_usage · workflow 描述）
  · 本脚本 = **机器派生**：
      ① **校验每个 workflow 的 tool 是否真实存在** ⇒ ★ 把「文档里写了、机器上没这个工具」暴露出来
      ② **统计 term_distribution**（★ 数出来，不是手写）
      ③ 注入 version / updated / generatedAt

★ 三态（★ 不把「没查到」读成「不存在」）：
  · tool 存在            ⇒ "ok"
  · tool 不存在但声明了形态（rust/二进制/子命令）⇒ "external"（★ 非文件形态，不可用文件判据）
  · 什么都没声明          ⇒ "unknown"

★ 用法：
  python3 bb-workflow-standards-gen.py --selfcheck
  python3 bb-workflow-standards-gen.py            # 默认演练（零变更）
  python3 bb-workflow-standards-gen.py --go
"""
import os, sys, json, glob, argparse, datetime, time, re

VERSION = "1.0.0"
R006_SELFCHECK = True

GALLERY = os.path.expanduser("~/dsh-collab/data/blueprint/gallery")
CORE = os.path.join(GALLERY, "workflow-standards.core.json")
OUT = os.path.join(GALLERY, "workflow-standards.json")
SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
DOCROOTS = [os.path.expanduser("~/dsh-collab/docs"),
            os.path.expanduser("~/dsh-collab/rules-registry")]
LOG = os.path.expanduser("~/dsh-collab/logs/bb-workflow-standards-gen.log")


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().isoformat(), msg))
    except Exception:
        pass


def selfcheck():
    print("== bb-workflow-standards-gen 自查（TCC 能力边界）==")
    print("【① 能力清单】")
    print("  · 读 workflow-standards.core.json（人工核心）")
    print("  · 只读扫描 scripts/ 与 docs/（★ 判 tool 存在性 + 统计词频）")
    print("  · 写 workflow-standards.json（★ 仅 --go）")
    print("【② 不该发生路径清单】")
    print("  · 不删除文件 · 不修改权限 · 不执行任何扫描到的脚本 · 不终止进程")
    print("【③ 依赖完整性】")
    print("  · 标准库: os/glob/json/argparse/re · python %s" % sys.version.split()[0])
    print("  · 固定日志: %s" % LOG)
    print("  · 版本: %s" % VERSION)
    return 0


def tool_state(tool):
    """★ 三态：ok / external / unknown"""
    if not tool:
        return "unknown"
    t = tool.strip()
    # ★ 非文件形态（rust 子命令 / 二进制 / 组合表达式）⇒ 文件判据不适用
    if any(c in t for c in ("+", " ", "(")) or t.islower() and not t.endswith(".py"):
        if not t.endswith((".py", ".sh")):
            return "external"
    cand = os.path.join(SCRIPTS, t)
    if os.path.exists(cand):
        return "ok"
    return "missing"


def term_counts(terms):
    """★ 数出来，不是手写（★ 只读扫描 text 文件）"""
    blob = []
    for root in DOCROOTS:
        for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if not os.path.isfile(p):
                continue
            if not p.endswith((".md", ".json", ".txt")):
                continue
            try:
                blob.append(open(p, encoding="utf-8", errors="replace").read())
            except Exception:
                pass
    s = "\n".join(blob)
    return {t: len(re.findall(re.escape(t), s)) for t in terms}


def build():
    with open(CORE, encoding="utf-8") as f:
        core = json.load(f)
    wfs = []
    ok = ext = miss = unk = 0
    for w in core.get("workflows") or []:
        st = tool_state(w.get("tool"))
        ok += st == "ok"; ext += st == "external"; miss += st == "missing"; unk += st == "unknown"
        wfs.append({**w, "toolState": st})
    terms = list((core.get("term_distribution") or {}).keys()) or \
            ["自动化", "工具化", "插件化", "标准化", "工作流", "流水线", "泛化"]
    td = term_counts(terms)
    return {
        "version": core.get("version", "1.0.0"),
        "updated": datetime.date.today().isoformat(),
        "generatedAt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generatedBy": "bb-workflow-standards-gen.py v" + VERSION,
        "sourceOfTruth": "workflow-standards.core.json（人工核心）",
        "toolCheck": {"ok": ok, "external": ext, "missing": miss, "unknown": unk},
        "r006": core.get("r006"),
        "workflows": wfs,
        "meta_usage": core.get("meta_usage"),
        "term_distribution": td,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--go", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not os.path.exists(CORE):
        print("★ core 不存在: %s" % CORE, file=sys.stderr)
        return 2
    t0 = time.time()
    d = build()
    txt = json.dumps(d, ensure_ascii=False, indent=1)
    if a.json:
        print(json.dumps({"ok": True, "dry": not a.go, "workflows": len(d["workflows"]),
                          "toolCheck": d["toolCheck"], "bytes": len(txt),
                          "seconds": round(time.time() - t0, 1)}, ensure_ascii=False))
    else:
        print("workflow %d · tool 校验 %s · 产出 %d B" % (len(d["workflows"]), d["toolCheck"], len(txt)))
        for w in d["workflows"]:
            if w["toolState"] == "missing":
                print("  ★ tool 不存在: %-22s %s" % (w.get("id"), w.get("tool")))
    if a.go:
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(txt)
        log("go workflows=%d toolCheck=%s" % (len(d["workflows"]), d["toolCheck"]))
        if not a.json:
            print("✅ 已写 %s" % OUT)
    else:
        log("dry workflows=%d" % len(d["workflows"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
