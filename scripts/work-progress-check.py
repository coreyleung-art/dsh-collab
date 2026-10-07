#!/usr/bin/env python3
"""
work-progress-check.py — 派发工作的存活检查（候选A「指称完整性」的镜像落地）

★ 核心设计（为什么这样设计）：
  不查「你完成了吗」（那是信对方的话），只查「产物在变化吗」（客观证据）。
  这是候选A 的镜像：**把「我派发了」当成「它在执行」** 是同一族错误，
  故本工具不接受任何自述，只读文件系统的 mtime 与存在性。

判据（三态，对应候选A 的三层）：
  ACTIVE  —— 窗口内有文件变化              = 真的在跑
  STALLED —— 产物存在但超过阈值无变化      = 停摆（昨天 40 分钟那次）
  EMPTY   —— 目录不存在或无任何产物        = 从未开始（可能派发就失败了）

用法：
  work-progress-check.py --dir <dir> [--dir <dir> ...] [--stall-min 15] [--json] [--dry-run]
  work-progress-check.py --manifest <json>          # 从 manifest 读多目标
  work-progress-check.py --selfcheck

退出码：0 全部 ACTIVE · 1 有 STALLED/EMPTY · 2 用法或 IO 错误
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

VERSION = "1.0.0"
TOOL = "work-progress-check"
LOG = os.path.expanduser("~/dsh-collab/logs/work-progress-check.log")

# ⑩ 约束门：本工具的「不该发生路径」——
#   它绝不写任何被检查对象，也绝不发通知（只输出结论，由人/上层决定动作）。
WRITE_CAPABLE = False   # 常量，源码扫描可核验


def log(rec):
    """⑦ 统一日志（失败也留痕）"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "tool": TOOL, **rec}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[{TOOL}] 日志写入失败：{e}\n")


def scan_dir(path, stall_min):
    """扫一个目录的状态。只读，不写。"""
    p = os.path.expanduser(path)
    if not os.path.isdir(p):
        return {"path": p, "state": "EMPTY", "reason": "目录不存在",
                "files": 0, "last_mtime": None, "idle_min": None}

    newest, count = 0.0, 0
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for fn in files:
            try:
                m = os.path.getmtime(os.path.join(root, fn))
                count += 1
                if m > newest:
                    newest = m
            except OSError:
                pass

    if count == 0:
        return {"path": p, "state": "EMPTY", "reason": "目录存在但无文件",
                "files": 0, "last_mtime": None, "idle_min": None}

    idle = (time.time() - newest) / 60.0
    state = "ACTIVE" if idle <= stall_min else "STALLED"
    return {
        "path": p, "state": state, "files": count,
        "last_mtime": datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M:%S"),
        "idle_min": round(idle, 1),
        "reason": "" if state == "ACTIVE" else f"已 {idle:.0f} 分钟无变化（阈值 {stall_min} 分钟）",
    }


def render(results, stall_min):
    icons = {"ACTIVE": "✅", "STALLED": "⏸", "EMPTY": "❌"}
    print(f"== 派发工作存活检查（阈值 {stall_min} 分钟）==")
    print(f"{'状态':<8}{'目标':<58}{'文件':>5}  {'最后变化':<20}{'空闲'}")
    print("-" * 108)
    for r in results:
        ico = icons.get(r["state"], "?")
        short = r["path"].replace(os.path.expanduser("~"), "~")
        if len(short) > 56:
            short = "…" + short[-55:]
        idle = f"{r['idle_min']:.0f}min" if r["idle_min"] is not None else "-"
        print(f"{ico} {r['state']:<6}{short:<58}{r['files']:>5}  {str(r['last_mtime'] or '-'):<20}{idle}")
    print()
    n_act = sum(1 for r in results if r["state"] == "ACTIVE")
    n_sta = sum(1 for r in results if r["state"] == "STALLED")
    n_emp = sum(1 for r in results if r["state"] == "EMPTY")
    print(f"  合计：{len(results)} 目标 · ACTIVE {n_act} · STALLED {n_sta} · EMPTY {n_emp}")
    for r in results:
        if r["state"] != "ACTIVE":
            print(f"    ⚠️ {r['state']}: {r['path'].replace(os.path.expanduser('~'), '~')} —— {r['reason']}")
    if n_sta or n_emp:
        print()
        print("  ★ 注意：STALLED ≠ 失败，EMPTY ≠ 未派发。本工具只报「产物没有在变化」。")
        print("     这正是候选A 的镜像 —— 不看自述，只看所指对象是否真的在动。")


def selfcheck():
    print("== work-progress-check 自查 ==")
    print("【① 能力清单】")
    print("  · 扫目录产物 mtime → 判定 ACTIVE / STALLED / EMPTY")
    print("  · 多目标（--dir 多次 或 --manifest）")
    print("  · 只读：不写被检查对象，不发通知")
    print("【② 不该发生路径清单】")
    print("  · 写被检查对象 → 结构上无写入能力（WRITE_CAPABLE=False，源码可核验）")
    print("  · 自动发通知/唤醒 → 无此能力（只输出结论）")
    print("  · 把 STALLED 说成失败 → 输出里显式声明二者不等于")
    print("【③ 依赖完整性】")
    print(f"  · Python {sys.version.split()[0]}（只标准库）")
    print(f"  · 日志路径：{LOG}")
    print("  ✅ 无外部依赖")


def main():
    ap = argparse.ArgumentParser(description="派发工作存活检查（候选A 的镜像落地）")
    ap.add_argument("--dir", action="append", default=[], help="要检查的目录（可多次）")
    ap.add_argument("--manifest", help="JSON：{\"targets\":[{\"name\":..,\"path\":..}]}")
    ap.add_argument("--stall-min", type=int, default=15, help="超过多少分钟无变化算 STALLED（默认 15）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印将要检查什么，不做扫描")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()

    if args.tool_version:
        print(VERSION); return 0
    if args.selfcheck:
        selfcheck(); return 0

    targets = [{"name": os.path.basename(d.rstrip("/")), "path": d} for d in args.dir]
    if args.manifest:
        try:
            mf = json.load(open(os.path.expanduser(args.manifest), encoding="utf-8"))
            targets += mf.get("targets", [])
        except Exception as e:
            print(f"manifest 读取失败：{e}", file=sys.stderr); return 2

    if not targets:
        print("错误：需 --dir 或 --manifest 指定目标", file=sys.stderr)
        return 2

    if args.dry_run:
        print(f"将检查 {len(targets)} 个目标（阈值 {args.stall_min} 分钟）：")
        for t in targets:
            print(f"  · {t.get('name','?')}  {t.get('path','')}")
        print("（dry-run：未做任何扫描，未写日志）")
        return 0

    results = [dict(scan_dir(t["path"], args.stall_min), name=t.get("name", "")) for t in targets]
    log({"action": "scan", "targets": len(results),
         "states": {r["state"]: sum(1 for x in results if x["state"] == r["state"]) for r in results}})

    if args.json:
        print(json.dumps({"stall_min": args.stall_min, "results": results}, ensure_ascii=False, indent=2))
    else:
        render(results, args.stall_min)

    return 0 if all(r["state"] == "ACTIVE" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
