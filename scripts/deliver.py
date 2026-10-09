#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deliver.py — 交付链编排（11 步一条命令）

明鉴 · 2026-09-10 · v1.0.0

背景
----
一条完整交付链有 11 步：改文档 → 立场自检 → 全载体扫描 → 红队 → 派生 → 受众检查 →
生成 HTML → 界面验证 → 落标记 → 外部推送 → 逐字节验证。目前全靠手敲。
本工具把 11 步编排成一条命令：**每步可跳过、可单独跑、有汇总报告**。

11 步
-----
  01 立场自检      stance-auditor.py <master> --audience shareholder
  02 全载体扫描    consistency-scan.py --facts <facts> --roots <sources> <deploy_dir>
  03 红队          red-team.py prep <master> --out …            （只生成任务包，不派发）
  04 派生版        clean-external.py / stance-derive.py
  05 受众检查      audience-check.py <derived> --audience <受众>
  06 生成 HTML     md2flowernet.py <md> <html> <标题>
  07 界面验证      verify-ui.py <html>
  08 落标记        export-marker.py <deploy_dir>
  09 外部推送      **不自动执行** —— 只打印「请通知协作者推送」
  10 逐字节验证    verify-deploy.py --map <deploy-map.json>
  11 汇总          打印每步的退出码与结论

  ⚠️ 安全边界：第 09 步永远不自动执行。推送必须由人 / 协作者手动执行。

用法
----
  deliver.py steps                                          # 看有哪些步骤
  deliver.py run --config deliver.json                      # 跑完整链
  deliver.py run --config deliver.json --only scan,audit,ui # 只跑某几步
  deliver.py run --config deliver.json --dry-run            # 干跑：只打印将要执行什么
  deliver.py run --config deliver.json --skip-redteam --skip-ui --skip-marker --skip-verify
  deliver.py --version / --help

设计约束
--------
  · 工具存在性检查：脚本不存在 → 「⚠️ 跳过（工具缺失）」，不崩溃
  · 退出码传递：任一步退出码非 0 → 记录但继续（不中断），汇总里标 ❌
  · 每步打印 [NN/11] 步骤名 + stdout 摘要（最多 20 行）
  · 绝不自动推送

零外部依赖 · Python 3.9+
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/deliver.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
TOTAL = 11

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_DIRS = [
    SCRIPT_DIR,
    os.path.expanduser("~/dsh-collab/scripts"),
    os.path.expanduser("~/relationship-graph-app/gallery"),
    os.path.expanduser("~/dsh-tools"),
    os.path.expanduser("~"),
]
TOOL_FILES = {
    "stance-auditor": ["stance-auditor.py"],
    "consistency-scan": ["consistency-scan.py"],
    "red-team": ["red-team.py"],
    "clean-external": ["clean-external.py"],
    "stance-derive": ["stance-derive.py"],
    "audience-check": ["audience-check.py"],
    "md2flowernet": ["md2flowernet.py",
                     "~/relationship-graph-app/gallery/md2flowernet.py"],
    "verify-ui": ["verify-ui.py"],
    "export-marker": ["export-marker.py"],
    "verify-deploy": ["verify-deploy.py"],
}

STATUS_OK = "✅ 成功"
STATUS_SKIP = "⚠️ 跳过"
STATUS_FAIL = "❌ 失败"
STATUS_NOTRUN = "⏭ 未选"
STATUS_DRY = "🔍 干跑"

# 工具缺失 / 未选 时的退出码占位
NO_CODE = "—"


def _e(p):
    return os.path.abspath(os.path.expanduser(str(p)))


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────── 工具定位 ───────────────────────────
def resolve_tool(name, cfg, cfg_dir):
    """返回 (路径 or None, 是否存在)。配置里的 tools 显式覆盖优先（即使不存在也返回该路径）。"""
    override = (cfg.get("tools") or {}).get(name)
    if override:
        p = override if os.path.isabs(str(override)) else os.path.join(cfg_dir, str(override))
        p = _e(p)
        return p, os.path.exists(p)
    for d in TOOL_DIRS:
        for f in TOOL_FILES.get(name, []):
            p = f if os.path.isabs(f) else os.path.join(d, f)
            p = os.path.expanduser(p)
            if os.path.exists(p):
                return _e(p), True
    return None, False


def tool_missing_msg(name, path):
    if path:
        return "工具缺失: %s（%s）" % (path, name)
    return "工具缺失: %s（在 %s 下都找不到 %s）" % (
        name, "、".join(os.path.basename(d) for d in TOOL_DIRS),
        "/".join(TOOL_FILES.get(name, ["?"])))


# ─────────────────────────── 配置 ───────────────────────────
def load_config(path):
    p = _e(path)
    if not os.path.exists(p):
        print("❌ 找不到配置: %s" % p)
        sys.exit(2)
    try:
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as ex:
        print("❌ 解析 %s 失败: %s" % (p, ex))
        sys.exit(2)
    if not isinstance(cfg, dict):
        print("❌ 配置必须是 JSON 对象")
        sys.exit(2)
    cfg["_path"] = p
    cfg["_dir"] = os.path.dirname(p)
    return cfg


def cfg_path(cfg, v):
    """配置里的相对路径按配置文件所在目录解析。"""
    if not v:
        return None
    s = str(v)
    if s.startswith("~"):
        return _e(s)
    return _e(s) if os.path.isabs(s) else os.path.join(cfg["_dir"], s)


def sources_of(cfg):
    src = cfg.get("sources") or {}
    if isinstance(src, list):
        return {("s%d" % (i + 1)): v for i, v in enumerate(src)}
    if not isinstance(src, dict):
        return {}
    return src


def master_of(cfg):
    s = sources_of(cfg)
    return cfg_path(cfg, s.get("master") or (list(s.values())[0] if s else None))


def scan_roots(cfg):
    roots = []
    for v in sources_of(cfg).values():
        p = cfg_path(cfg, v)
        if p and p not in roots:
            roots.append(p)
    dd = cfg_path(cfg, cfg.get("deploy_dir"))
    if dd and dd not in roots:
        roots.append(dd)
    return roots


def derived_of(cfg):
    d = cfg.get("derived") or []
    return d if isinstance(d, list) else []


def html_of(cfg):
    h = cfg.get("html") or []
    return h if isinstance(h, list) else []


# ─────────────────────────── 11 步定义 ───────────────────────────
# 每步: no / key / name / tool / skip_hint / build(cfg, ctx, flags) -> (cmds, skip_reason)
#   cmds: [{"label": 子步骤名, "argv": [...]}]
#   skip_reason: 非空则整步跳过（工具缺失由执行层再判断一次）

def _b_stance(cfg, ctx, fl):
    m = master_of(cfg)
    if not m:
        return [], "配置无 sources.master"
    if not os.path.exists(m):
        return [], "master 不存在: %s" % m
    aud = cfg.get("stance_audience") or "shareholder"
    return [{"label": "立场自检 · %s" % aud,
             "argv": [ctx["tool"], m, "--audience", aud]}], None


def _b_scan(cfg, ctx, fl):
    facts = cfg_path(cfg, cfg.get("facts_file"))
    if not facts:
        return [], "无 facts_file"
    if not os.path.exists(facts):
        return [], "facts_file 不存在: %s" % facts
    roots = [r for r in scan_roots(cfg) if os.path.exists(r)]
    if not roots:
        return [], "无可扫描载体（sources / deploy_dir 均不存在）"
    return [{"label": "全载体扫描 · %d 个载体" % len(roots),
             "argv": [ctx["tool"], "--facts", facts, "--roots"] + roots}], None


def _b_redteam(cfg, ctx, fl):
    if fl.get("skip_redteam"):
        return [], "--skip-redteam"
    m = master_of(cfg)
    if not m or not os.path.exists(m):
        return [], "master 不存在"
    out = cfg_path(cfg, cfg.get("redteam_out")) or os.path.join(cfg["_dir"], "redteam-pack")
    return [{"label": "红队任务包（只生成，不派发）",
             "argv": [ctx["tool"], "prep", m, "--out", out]}], None


def _b_derive(cfg, ctx, fl):
    items = derived_of(cfg)
    if not items:
        return [], "无 derived"
    m = master_of(cfg)
    cmds = []
    for it in items:
        if not isinstance(it, dict):
            continue
        aud = str(it.get("audience") or "").strip()
        out = cfg_path(cfg, it.get("out"))
        src = cfg_path(cfg, it.get("in")) or m
        if not out:
            continue
        if not src or not os.path.exists(src):
            cmds.append({"label": "派生版 · %s" % aud, "argv": None,
                         "error": "源文件不存在: %s" % src})
            continue
        tname = str(it.get("tool") or "").strip()
        if not tname:
            tname = "stance-derive" if aud.lower() in ("partner", "public") else "clean-external"
        tp, ok = resolve_tool(tname, cfg, cfg["_dir"])
        if not ok:
            cmds.append({"label": "派生版 · %s" % aud, "argv": None,
                         "error": tool_missing_msg(tname, tp), "tool": tname})
            continue
        if tname == "stance-derive":
            argv = [tp, src, out, "--audience", aud or "partner"]
        else:
            argv = [tp, src, out]
        cmds.append({"label": "派生版 · %s（%s）" % (aud or "?", tname), "argv": argv})
    if not cmds:
        return [], "derived 配置不完整（缺 out）"
    return cmds, None


def _b_audience(cfg, ctx, fl):
    items = derived_of(cfg)
    if not items:
        return [], "无 derived"
    cmds = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out = cfg_path(cfg, it.get("out"))
        aud = str(it.get("audience") or "").strip()
        if not out:
            continue
        if not os.path.exists(out):
            cmds.append({"label": "受众检查 · %s" % aud, "argv": None,
                         "error": "派生版不存在（上一步可能失败）: %s" % out})
            continue
        cmds.append({"label": "受众检查 · %s" % aud,
                     "argv": [ctx["tool"], out, "--audience", aud or "partner"]})
    if not cmds:
        return [], "derived 配置不完整（缺 out）"
    return cmds, None


def _b_html(cfg, ctx, fl):
    items = html_of(cfg)
    if not items:
        return [], "无 html"
    cmds = []
    for it in items:
        if not isinstance(it, dict):
            continue
        md = cfg_path(cfg, it.get("md")) or master_of(cfg)
        out = cfg_path(cfg, it.get("out"))
        title = str(it.get("title") or cfg.get("name") or "")
        if not out:
            continue
        if not md or not os.path.exists(md):
            cmds.append({"label": "生成 HTML · %s" % os.path.basename(out), "argv": None,
                         "error": "md 不存在: %s" % md})
            continue
        cmds.append({"label": "生成 HTML · %s" % os.path.basename(out),
                     "argv": [ctx["tool"], md, out, title]})
    if not cmds:
        return [], "html 配置不完整（缺 out）"
    return cmds, None


def _b_ui(cfg, ctx, fl):
    if fl.get("skip_ui"):
        return [], "--skip-ui"
    items = html_of(cfg)
    if not items:
        return [], "无 html"
    cmds = []
    for it in items:
        out = cfg_path(cfg, it.get("out")) if isinstance(it, dict) else None
        if not out:
            continue
        if not os.path.exists(out):
            cmds.append({"label": "界面验证 · %s" % os.path.basename(out), "argv": None,
                         "error": "HTML 不存在（上一步可能失败）: %s" % out})
            continue
        cmds.append({"label": "界面验证 · %s" % os.path.basename(out),
                     "argv": [ctx["tool"], out]})
    if not cmds:
        return [], "无可用 HTML（html 配置缺 out）"
    return cmds, None


def _b_marker(cfg, ctx, fl):
    if fl.get("skip_marker"):
        return [], "--skip-marker"
    dd = cfg_path(cfg, cfg.get("deploy_dir"))
    if not dd:
        return [], "无 deploy_dir"
    if not os.path.isdir(dd):
        return [], "deploy_dir 不存在: %s" % dd
    argv = [ctx["tool"], dd]
    if cfg.get("name"):
        argv += ["--note", str(cfg["name"])]
    base = os.path.basename(dd.rstrip("/")) or dd
    return [{"label": "落标记 · %s" % base, "argv": argv}], None


def _b_push(cfg, ctx, fl):
    # 安全边界：永远不自动执行
    return [], "安全边界：外部推送不自动执行"


def _b_verify(cfg, ctx, fl):
    if fl.get("skip_verify"):
        return [], "--skip-verify"
    mp = cfg_path(cfg, cfg.get("deploy_map"))
    if not mp:
        dd = cfg_path(cfg, cfg.get("deploy_dir"))
        if dd:
            cand = os.path.join(dd, "deploy-map.json")
            mp = cand if os.path.exists(cand) else None
    if not mp:
        return [], "找不到 deploy-map.json（配置 deploy_map 或 deploy_dir/deploy-map.json）"
    if not os.path.exists(mp):
        return [], "deploy_map 不存在: %s" % mp
    return [{"label": "逐字节验证 · %s" % os.path.basename(mp),
             "argv": [ctx["tool"], "--map", mp]}], None


STEPS = [
    {"no": 1, "key": "stance", "alias": ["audit", "立场", "自检"], "name": "立场自检",
     "tool": "stance-auditor", "skip_hint": "无 master 时跳过", "build": _b_stance},
    {"no": 2, "key": "scan", "alias": ["扫描", "consistency"], "name": "全载体扫描",
     "tool": "consistency-scan", "skip_hint": "无 facts_file 时跳过", "build": _b_scan},
    {"no": 3, "key": "redteam", "alias": ["red", "红队"], "name": "红队",
     "tool": "red-team", "skip_hint": "--skip-redteam（只生成任务包，不派发）", "build": _b_redteam},
    {"no": 4, "key": "derive", "alias": ["派生", "derived"], "name": "派生版",
     "tool": "clean-external / stance-derive", "skip_hint": "无 derived 时跳过", "build": _b_derive},
    {"no": 5, "key": "audience", "alias": ["受众", "受众检查"], "name": "受众检查",
     "tool": "audience-check", "skip_hint": "无 derived 时跳过", "build": _b_audience},
    {"no": 6, "key": "html", "alias": ["生成html", "md2"], "name": "生成 HTML",
     "tool": "md2flowernet", "skip_hint": "无 html 时跳过", "build": _b_html},
    {"no": 7, "key": "ui", "alias": ["界面", "验证界面"], "name": "界面验证",
     "tool": "verify-ui", "skip_hint": "--skip-ui", "build": _b_ui},
    {"no": 8, "key": "marker", "alias": ["标记", "落标记"], "name": "落标记",
     "tool": "export-marker", "skip_hint": "--skip-marker", "build": _b_marker},
    {"no": 9, "key": "push", "alias": ["推送", "外部推送"], "name": "外部推送",
     "tool": "（无 — 人工执行）", "skip_hint": "永远跳过执行（安全边界）", "build": _b_push},
    {"no": 10, "key": "verify", "alias": ["逐字节", "deploy-verify"], "name": "逐字节验证",
     "tool": "verify-deploy", "skip_hint": "--skip-verify", "build": _b_verify},
    {"no": 11, "key": "summary", "alias": ["汇总", "报告"], "name": "汇总",
     "tool": "（内置）", "skip_hint": "—", "build": None},
]
STEP_BY_KEY = {s["key"]: s for s in STEPS}
# 每步的主工具名（用于工具存在性检查与展示）；多工具步骤在 build 内部各自解析
PRIMARY_TOOL = {
    "stance": "stance-auditor", "scan": "consistency-scan", "redteam": "red-team",
    "derive": "stance-derive", "audience": "audience-check", "html": "md2flowernet",
    "ui": "verify-ui", "marker": "export-marker", "verify": "verify-deploy",
}


def match_steps(only):
    """--only 解析：支持 key / 别名 / 序号 / 名称子串。返回 (选中的 no 集合, 未识别项)。"""
    if not only:
        return set(s["no"] for s in STEPS), []
    picked, unknown = set(), []
    for raw in str(only).split(","):
        t = raw.strip()
        if not t:
            continue
        tl = t.lower()
        hit = None
        for s in STEPS:
            if tl == s["key"] or tl in [a.lower() for a in s["alias"]] or tl == s["key"][:4]:
                hit = s["no"]
                break
            if t.isdigit() and int(t) == s["no"]:
                hit = s["no"]
                break
        if hit is None:
            for s in STEPS:
                if tl in s["name"].lower().replace(" ", ""):
                    hit = s["no"]
                    break
        if hit is None:
            unknown.append(t)
        else:
            picked.add(hit)
    return picked, unknown


# ─────────────────────────── 执行 ───────────────────────────
def run_cmd(argv, timeout, cwd=None):
    """返回 (退出码, 输出文本)。"""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        out = (r.stdout or "")
        if (r.stderr or "").strip():
            out += ("\n" if out and not out.endswith("\n") else "") + r.stderr
        return r.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "⏱️ 超时（> %ss）：%s" % (timeout, " ".join(argv))
    except FileNotFoundError as ex:
        return 127, "工具不存在: %s" % ex
    except PermissionError as ex:
        return 126, "无权执行: %s" % ex
    except Exception as ex:
        return 1, "执行异常: %s" % ex


def effective(argv):
    """实际执行的命令行：.py 一律用当前解释器跑（这些脚本多为 -rw-------，没有可执行位）。"""
    if argv and str(argv[0]).endswith(".py"):
        return [sys.executable] + list(argv)
    return list(argv)


def digest(text, limit=20, indent="    │ "):
    lines = [l.rstrip() for l in (text or "").splitlines()]
    lines = [l for l in lines if l.strip() and not _is_decoration(l)]
    if not lines:
        return [], 0
    shown = lines[:limit]
    extra = max(0, len(lines) - limit)
    return [indent + l for l in shown], extra


def _is_decoration(line):
    """纯分隔线 / 空框线，不配当「关键结论」。"""
    s = line.strip().strip("│|")
    if not s:
        return True
    return not any(ch.isalnum() or ("\u4e00" <= ch <= "\u9fff") for ch in s)


def last_conclusion(text):
    lines = [l.strip() for l in (text or "").splitlines()]
    lines = [l for l in lines if l.strip() and not _is_decoration(l)]
    if not lines:
        return "（无输出）"
    for l in reversed(lines):
        if any(k in l for k in ("✅", "❌", "⚠️", "结论", "通过", "失败", "问题", "总计", "发现")):
            return l[:80]
    return lines[-1][:80]


def cmd_steps(args):
    cfg = load_config(args.config) if args.config else None
    cfg_dir = cfg["_dir"] if cfg else os.getcwd()
    print("交付链 11 步 · deliver.py v%s" % VERSION)
    print("=" * 78)
    print("%-3s %-9s %-12s %-26s %s" % ("#", "key", "步骤", "调用工具", "可跳过条件"))
    print("-" * 78)
    for s in STEPS:
        tool = s["tool"]
        tname = PRIMARY_TOOL.get(s["key"])
        if tname:
            p, ok = resolve_tool(tname, cfg or {}, cfg_dir)
            tool = ("%s%s" % (os.path.basename(p) if p else tname,
                              "" if ok else "（缺）"))
        print("%02d  %-9s %-12s %-26s %s" % (s["no"], s["key"], s["name"], tool, s["skip_hint"]))
    print("-" * 78)
    print("⚠️ 第 09 步「外部推送」**永远不自动执行** —— 只打印「请通知协作者推送」（安全边界）。")
    if cfg:
        print("配置: %s（%s）" % (cfg["_path"], cfg.get("name") or "未命名"))
    else:
        print("提示: deliver.py steps --config deliver.json 可同时显示各工具是否就位。")
    return 0


def cmd_run(args):
    cfg = load_config(args.config)
    cfg_dir = cfg["_dir"]
    name = cfg.get("name") or os.path.basename(cfg["_path"])
    flags = {
        "skip_redteam": args.skip_redteam, "skip_ui": args.skip_ui,
        "skip_marker": args.skip_marker, "skip_verify": args.skip_verify,
    }
    selected, unknown = match_steps(args.only)
    timeout = float(cfg.get("timeout") or args.timeout or 180)

    print("交付链执行 · %s" % name)
    print("配置: %s" % cfg["_path"])
    print("模式: %s" % ("干跑（dry-run，不实际执行）" if args.dry_run else "实际执行"))
    if args.only:
        print("--only: %s（命中 %s）" % (args.only, ",".join(
            sorted("%02d" % n for n in selected)) or "无"))
    if unknown:
        print("⚠️ 未识别步骤（已忽略）: %s" % ", ".join(unknown))
        print("   可用 key: %s" % ", ".join(s["key"] for s in STEPS))
    print("")

    results = []
    for s in STEPS:
        if s["key"] == "summary":
            continue
        r = {"no": s["no"], "key": s["key"], "name": s["name"],
             "status": STATUS_NOTRUN, "exit": NO_CODE, "conclusion": "未选中"}
        if s["no"] not in selected:
            results.append(r)
            continue

        # 第 09 步：只出提示，永不执行（必须在通用「跳过」分支之前处理）
        if s["key"] == "push":
            r["status"] = STATUS_SKIP
            r["conclusion"] = "安全边界：推送必须由人 / 协作者执行"
            print("[%02d/%02d] %s —— ⚠️ 不执行（安全边界）" % (s["no"], TOTAL, s["name"]))
            print("    │ 📣 请通知协作者推送（deliver.py 不会、也不应该替你推送）：")
            dd = cfg_path(cfg, cfg.get("deploy_dir")) or "（未配置 deploy_dir）"
            du = cfg.get("deploy_url") or "（未配置 deploy_url）"
            print("    │    产物目录: %s" % dd)
            print("    │    目标地址: %s" % du)
            if args.dry_run:
                print("    │    （干跑模式：同样不执行）")
            print("")
            results.append(r)
            continue

        ctx = {"cfg": cfg, "run": None}
        tool_path, tool_ok = (None, False)
        tname = PRIMARY_TOOL.get(s["key"])
        if tname:
            tool_path, tool_ok = resolve_tool(tname, cfg, cfg_dir)
            if not tool_ok:
                r["status"] = STATUS_SKIP
                r["conclusion"] = tool_missing_msg(tname, tool_path)
                print("[%02d/%02d] %s —— ⚠️ 跳过（工具缺失）" % (s["no"], TOTAL, s["name"]))
                print("    │ %s" % r["conclusion"])
                print("")
                results.append(r)
                continue
            ctx["tool"] = tool_path

        cmds, skip_reason = s["build"](cfg, ctx, flags)
        if skip_reason and not cmds:
            r["status"] = STATUS_SKIP
            r["conclusion"] = skip_reason
            print("[%02d/%02d] %s —— ⚠️ 跳过（%s）" % (s["no"], TOTAL, s["name"], skip_reason))
            print("")
            results.append(r)
            continue

        # 干跑：只打印计划
        if args.dry_run:
            print("[%02d/%02d] %s —— 🔍 干跑（将执行 %d 个子步骤）" % (s["no"], TOTAL, s["name"], len(cmds)))
            pending = 0
            for c in cmds:
                if c.get("argv") is None:
                    pending += 1
                    print("    │ ⏳ 待前序产出：%s —— %s" % (c["label"], c.get("error") or "无法构造命令"))
                else:
                    print("    │ $ %s" % " ".join(shlex.quote(a) for a in effective(c["argv"])))
            r["status"] = STATUS_DRY
            r["exit"] = NO_CODE
            r["conclusion"] = "将执行 %d 个子步骤" % (len(cmds) - pending)
            if pending:
                r["conclusion"] += "（%d 个依赖前序产出，实跑时按序生成）" % pending
            print("")
            results.append(r)
            continue

        # 第 09 步已在上面单独处理（永不执行）
        print("[%02d/%02d] %s …" % (s["no"], TOTAL, s["name"]))
        codes = []
        conclusions = []
        for c in cmds:
            print("    ├─ %s" % c["label"])
            if c.get("argv") is None:
                print("    │  ⚠️ %s" % (c.get("error") or "无法构造命令"))
                codes.append(1)
                conclusions.append(c.get("error") or "无法构造命令")
                continue
            print("    │  $ %s" % " ".join(shlex.quote(a) for a in effective(c["argv"])))
            rc, out = run_cmd(effective(c["argv"]), timeout, cwd=cfg_dir)
            lines, extra = digest(out)
            for l in lines:
                print(l)
            if extra:
                print("    │ …（另有 %d 行未显示，最多显示 20 行）" % extra)
            codes.append(rc)
            if rc == 0:
                print("    │  ✅ exit=0")
            else:
                print("    │  ❌ exit=%d" % rc)
            conclusions.append(last_conclusion(out) if rc == 0 else
                               "exit=%d · %s" % (rc, last_conclusion(out)))
        r["exit"] = ",".join(str(c) for c in codes) if codes else NO_CODE
        if all(c == 0 for c in codes):
            r["status"] = STATUS_OK
        else:
            r["status"] = STATUS_FAIL
        r["conclusion"] = " ｜ ".join(conclusions)[:110] if conclusions else "（无输出）"
        print("")
        results.append(r)

    # ── 第 11 步：汇总 ──
    ok = [r for r in results if r["status"] == STATUS_OK]
    skip = [r for r in results if r["status"] in (STATUS_SKIP, STATUS_DRY)]
    fail = [r for r in results if r["status"] == STATUS_FAIL]
    notrun = [r for r in results if r["status"] == STATUS_NOTRUN]

    print("[%02d/%02d] %s" % (11, TOTAL, "汇总"))
    print("")
    if args.dry_run:
        print("（干跑模式：以下为计划，未实际执行）")
        print("")
    print("| 步骤 | 状态 | 退出码 | 关键结论 |")
    print("|---|---|---|---|")
    for r in results:
        print("| %02d %s | %s | %s | %s |" % (r["no"], r["name"], r["status"], r["exit"],
                                              str(r["conclusion"]).replace("|", "\\|")))
    print("| 11 汇总 | %s | %s | ✅ %d · ⚠️ %d · ❌ %d%s |"
          % (STATUS_OK, NO_CODE, len(ok), len(skip), len(fail),
             (" · ⏭ %d 未选" % len(notrun)) if notrun else ""))
    print("")
    print("合计: ✅ 成功 %d · ⚠️ 跳过/干跑 %d · ❌ 失败 %d%s" %
          (len(ok), len(skip), len(fail), (" · ⏭ 未选 %d" % len(notrun)) if notrun else ""))
    if fail:
        print("❌ 失败步骤: %s" % "、".join("第%02d步 %s（exit=%s）" % (r["no"], r["name"], r["exit"])
                                           for r in fail))
        print("   （已按约定「记录但继续」——不中断，请人工处理后再重跑对应步骤）")
    print("")
    print("📣 第 09 步外部推送**未执行**：请通知协作者手动推送（deliver.py 不会替你推送）。")

    report_path = args.report or cfg.get("report")
    if report_path:
        rp = cfg_path(cfg, report_path)
        os.makedirs(os.path.dirname(rp), exist_ok=True)
        with open(rp, "w", encoding="utf-8") as f:
            f.write("# 交付链执行报告 · %s\n\n> %s · 配置 %s · 模式 %s\n\n"
                    % (name, _now(), cfg["_path"], "dry-run" if args.dry_run else "执行"))
            f.write("| 步骤 | 状态 | 退出码 | 关键结论 |\n|---|---|---|---|\n")
            for r in results:
                f.write("| %02d %s | %s | %s | %s |\n" % (r["no"], r["name"], r["status"], r["exit"],
                                                          str(r["conclusion"]).replace("|", "\\|")))
            f.write("\n> 第 09 步外部推送未执行（安全边界）：请通知协作者手动推送。\n")
        print("📄 报告已写: %s" % rp)

    return 1 if fail else 0


# ─────────────────────────── main ───────────────────────────
def main():
    ap = argparse.ArgumentParser(
        prog="deliver.py",
        description="交付链编排（11 步一条命令）· 每步可跳过 / 可单独跑 / 有汇总报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="⚠️ 第 09 步「外部推送」永远不自动执行（安全边界）。\n"
               "示例:\n"
               "  deliver.py steps\n"
               "  deliver.py run --config deliver.json --dry-run\n"
               "  deliver.py run --config deliver.json --only scan,audit,ui\n")
    ap.add_argument("--version", action="version", version="deliver.py v%s" % VERSION)
    sub = ap.add_subparsers(dest="cmd")

    p1 = sub.add_parser("steps", help="看有哪些步骤")
    p1.add_argument("--config", "-c", default=None, help="可选：同时显示各工具是否就位")
    p1.set_defaults(func=cmd_steps)

    p2 = sub.add_parser("run", help="跑交付链（或干跑 / 只跑某几步）")
    p2.add_argument("--config", "-c", required=True, help="deliver.json 路径")
    p2.add_argument("--only", default=None, help="只跑某几步（key/别名/序号，逗号分隔，如 scan,audit,ui）")
    p2.add_argument("--dry-run", action="store_true", help="干跑：只打印将要执行什么，不实际跑")
    p2.add_argument("--skip-redteam", action="store_true", help="跳过第 03 步红队")
    p2.add_argument("--skip-ui", action="store_true", help="跳过第 07 步界面验证")
    p2.add_argument("--skip-marker", action="store_true", help="跳过第 08 步落标记")
    p2.add_argument("--skip-verify", action="store_true", help="跳过第 10 步逐字节验证")
    p2.add_argument("--timeout", type=float, default=None, help="单步超时秒数（默认取配置 timeout 或 180）")
    p2.add_argument("--report", default=None, help="把汇总报告写入该 md 文件（也可写在配置 report 字段）")
    p2.set_defaults(func=cmd_run)

    args = ap.parse_args()
    if not getattr(args, "func", None):
        ap.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
