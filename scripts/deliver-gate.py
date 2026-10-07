#!/usr/bin/env python3
"""
deliver-gate.py — 交付总闸（阻断项 vs 报告项）

★ 为什么需要它（2026-09-10，由 HR 司库的第 ⑤ 项逼出来）：
   HR 的原话：「**R006 十项里每一项都要标注它是「阻断项」还是「报告项」；阻断项未达标 = 禁止交付，
   而不是「记录一条问题」。**」
   它的判据来自 collect builder 的证据链：
     「加固前负例矩阵 142 条里放行 1 条 → --lean4-check 当场报『门未生效，禁止交付』」
   ★ 差别的本质：
     · 「我发现了一个漏」 —— **依赖我此刻的注意力**
     · 「门不让交」     —— **不依赖任何人的注意力**

★ 我（明鉴）用这条审自己时发现的缺口：
   我有 audit-snapshot / consistency-scan / verify-deploy / work-progress-check 等检查器，
   各自大多会 exit 1。**但没有任何一处会因为某个门没过而「禁止交付」。**
   → 它们全是「**报告项**」。**我连一个「阻断项」都没有。**
   → **各自 exit 1 ≠ 总闸**：我可以跑完发现不一致，然后照样交付，因为没有机制拦我。

★ 本工具就是那个总闸：
   读一份「阻断项清单」→ 逐项跑 → **任一阻断项不过 → 禁止交付**。

用法：
  deliver-gate.py check [--config blockers.json] [--dry-run] [--json]
  deliver-gate.py --selfcheck | --tool-version | --help

退出码：0 全部阻断项通过（可交付）· 1 有阻断项未过（禁止交付）· 2 用法或 IO 错误
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

VERSION = "1.0.0"
TOOL = "deliver-gate"
LOG = os.path.expanduser("~/dsh-collab/logs/deliver-gate.log")
DEFAULT_CONFIG = os.path.expanduser("~/dsh-collab/data/device/deliver-blockers.json")

# ⑩ 约束门：本工具**只跑清单里的命令**，不接受任意命令；
#    且它**只读被检查对象**，只写自己的日志。
ALLOWED_KINDS = ("script", "shell", "manual")


def log(rec):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "tool": TOOL, **rec}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[{TOOL}] 日志写入失败：{e}\n")


def fingerprint(items):
    """清单的声明位指纹（陷阱①：清单自身会漂移，须可核验）"""
    import hashlib
    canon = json.dumps([{"n": i.get("name", ""), "k": i.get("kind", ""), "c": i.get("cmd", "")} for i in items],
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:16]


def load_config(path):
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        return None, f"清单不存在：{p}"
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return None, f"清单解析失败：{e}"
    items = d.get("blockers", [])
    if not isinstance(items, list):
        return None, "清单 blockers 必须是数组"
    for it in items:
        if it.get("kind") not in ALLOWED_KINDS:
            return None, f"条目的 kind 非法：{it.get('kind')}（允许 {ALLOWED_KINDS}）"
    # ★ 陷阱①：核验清单声明位（条目数 + 指纹）—— 防「清单落后于工具而总闸仍报全过」
    fp = fingerprint(items)
    declared_n = d.get("declared_count")
    declared_fp = d.get("declared_fingerprint")
    if declared_n is not None and declared_n != len(items):
        return None, (f"★ 清单声明位不符：declared_count={declared_n} 实际={len(items)} —— "
                      f"清单已漂移，请先更新声明位（`--stamp` 可自动写入）")
    if declared_fp is not None and declared_fp != fp:
        return None, (f"★ 清单声明位不符：declared_fingerprint={declared_fp} 实际={fp} —— "
                      f"清单内容已变但未更新声明位")
    d["_fingerprint"] = fp
    return d, None


def run_item(it):
    """跑一个阻断项。返回 (passed, detail)"""
    kind = it["kind"]
    if kind == "manual":
        # 人工确认项：不自动通过 —— 明说需要人裁，而不是替人裁
        return None, "人工确认项（本工具不代判）"
    if kind == "script":
        cmd = it.get("cmd")
        if not cmd:
            return False, "缺 cmd"
        cwd = os.path.expanduser(it.get("cwd", "~/dsh-collab"))
        try:
            r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=it.get("timeout", 300))
        except subprocess.TimeoutExpired:
            return False, f"超时（{it.get('timeout', 300)}s）"
        ok = r.returncode == it.get("expect_exit", 0)
        tail = ((r.stdout or "") + (r.stderr or "")).strip().split("\n")[-3:]
        return ok, f"exit={r.returncode}（期望 {it.get('expect_exit', 0)}）| " + " / ".join(tail)[:160]
    return False, f"未支持的 kind：{kind}"


def cmd_check(args):
    cfg, err = load_config(args.config)
    if err:
        print(f"❌ {err}", file=sys.stderr)
        return 2

    blockers = cfg["blockers"]
    if args.dry_run:
        print(f"== 交付总闸 dry-run · {len(blockers)} 个阻断项 ==")
        for i, it in enumerate(blockers, 1):
            print(f"  {i:2d}. [{it['kind']}] {it.get('name', '?')}")
            if it.get("cmd"):
                print(f"      $ {it['cmd']}")
        print("\n（dry-run：未执行任何命令，未写日志）")
        return 0

    results = []
    for it in blockers:
        passed, detail = run_item(it)
        results.append({"name": it.get("name", "?"), "kind": it["kind"], "passed": passed, "detail": detail})

    hard_fail = [r for r in results if r["passed"] is False]
    pending = [r for r in results if r["passed"] is None]
    ok_count = len(results) - len(hard_fail) - len(pending)

    if args.json:
        print(json.dumps({
            "verdict": "BLOCK" if hard_fail else ("PENDING" if pending else "PASS"),
            "total": len(results), "passed": ok_count, "failed": len(hard_fail), "pending": len(pending),
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"== 交付总闸 · {len(results)} 个阻断项 ==")
        print(f"{'':2}{'状态':<6}{'阻断项':<44}详情")
        print("-" * 108)
        for r in results:
            mark = "✅" if r["passed"] else ("⏸" if r["passed"] is None else "❌")
            print(f"  {mark:<6}{r['name'][:42]:<44}{r['detail'][:56]}")
        print()
        # ★ 陷阱②：静默跳过比没有总闸更坏 —— 必须声明「它没查什么」
        print(f"  合计：通过 {ok_count} · 未过 {len(hard_fail)} · 待人工 {len(pending)}")
        print()
        print(f"  【必查项】{len(results)} —— " +
              ("全部已查" if not pending else f"{len(results) - len(pending)} 已查、{len(pending)} 待人工"))
        print(f"  【实查项】{ok_count + len(hard_fail)} —— 本次实际执行并得出结论的")
        if pending:
            print(f"  【★ 跳过项】{len(pending)}（必须声明原因，不得静默）")
            for r in pending:
                print(f"      · {r['name']} —— 原因：{r['detail']}")
        else:
            print(f"  【★ 跳过项】0 —— 本次无跳过")
        print()
        banner = cfg.get("banner", "== 交付总闸 ==")
        if hard_fail:
            print(f"  🚫 {banner}：**禁止交付** —— 有 {len(hard_fail)} 个阻断项未过")
            for r in hard_fail:
                print(f"      · {r['name']} — {r['detail']}")
            print()
            print("  ★ 这不是「记录一条问题」。这是**门不让交**。")
        elif pending:
            print(f"  ⏸ **暂缓** —— {len(pending)} 个人工确认项未决（本工具不代判）")
        else:
            print(f"  ✅ 全部阻断项通过 —— **可交付**")

    # ★ 陷阱③：总闸自己也是检查器 —— 它必须能证明「今天真的跑过」
    #    否则「没跑」与「跑了全过」不可区分（正是 audit-snapshot.py 的教训）
    import hashlib as _h
    stamp_rec = {
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": "BLOCK" if hard_fail else ("PENDING" if pending else "PASS"),
        "total": len(results), "failed": len(hard_fail), "pending": len(pending),
        "checkers": [r["name"] for r in results],
    }
    stamp_rec["self_sha256"] = _h.sha256(
        json.dumps(stamp_rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    try:
        stamp_path = os.path.expanduser(cfg.get("run_stamp", "~/dsh-collab/data/device/deliver-gate-last-run.json"))
        os.makedirs(os.path.dirname(stamp_path), exist_ok=True)
        with open(stamp_path, "w", encoding="utf-8") as f:
            json.dump(stamp_rec, f, ensure_ascii=False, indent=2)
        if not args.json:
            print(f"\n  ★ 总闸自证：本次运行已落戳 {stamp_path}")
            print(f"     ran_at={stamp_rec['ran_at']} · verdict={stamp_rec['verdict']} · sha256={stamp_rec['self_sha256']}")
            print(f"     （陷阱③：总闸坏了的那天，一切都会安静通过 —— 故它必须能证明『今天真的跑过』）")
    except Exception as e:
        sys.stderr.write(f"[{TOOL}] 落戳失败：{e}\n")

    log({"action": "check", "total": len(results), "failed": len(hard_fail), "pending": len(pending),
         "fingerprint": cfg.get("_fingerprint")})
    if hard_fail:
        return 1
    if pending:
        return 1   # 未决也算不能交付
    return 0


def selfcheck():
    print("== deliver-gate 自查 ==")
    print("【① 能力清单】")
    print("  · 读「阻断项清单」→ 逐项执行 → 任一项不过即禁止交付")
    print("  · 区分三种结果：通过 / 未过（阻断）/ 待人工（不代判）")
    print(f"  · 清单默认路径：{DEFAULT_CONFIG}")
    print("  · 日志：%s" % LOG)
    print("【② 不该发生路径清单】")
    print("  · 执行任意命令 → 结构上只从清单取 cmd，kind 冻结枚举 (script/shell/manual)")
    print("  · 替人裁人工项 → manual 项返回「不代判」，绝不自动通过")
    print("  · 清单缺失时假装通过 → 清单不存在即 exit 2（不是 0）")
    print("  · 写被检查对象 → 本工具只读，只写自己的日志")
    print("【③ 依赖完整性】")
    print(f"  · Python {sys.version.split()[0]}（只标准库）")
    print(f"  · 清单存在性：{'✅' if os.path.exists(DEFAULT_CONFIG) else '❌ 未建（需先写清单）'}")
    print("  ✅ 无外部依赖")
    return 0


def main():
    ap = argparse.ArgumentParser(description="交付总闸（阻断项 vs 报告项）")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="跑总闸")
    c.add_argument("--config", default=DEFAULT_CONFIG)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--json", action="store_true")
    ap.add_argument("--stamp", action="store_true", help="更新清单声明位（count + fingerprint）")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()

    if args.tool_version:
        print(VERSION); return 0
    if args.stamp:
        cfg, err = load_config(args.config)
        if err and "声明位不符" not in err:
            print(f"❌ {err}", file=sys.stderr); return 2
        raw = json.load(open(os.path.expanduser(args.config), encoding="utf-8"))
        items = raw["blockers"]
        raw["declared_count"] = len(items)
        raw["declared_fingerprint"] = fingerprint(items)
        raw["stamped_at"] = datetime.now().isoformat(timespec="seconds")
        json.dump(raw, open(os.path.expanduser(args.config), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"✅ 声明位已更新：count={raw['declared_count']} fp={raw['declared_fingerprint']}")
        return 0
    if args.selfcheck:
        return selfcheck()
    if args.cmd == "check":
        return cmd_check(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
