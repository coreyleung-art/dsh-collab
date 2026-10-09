#!/usr/bin/env python3
"""
audit-snapshot.py — 审计快照工具（治「我连续三次把过期快照当现状」这个毛病）

★ 为什么需要（一手事故，2026-09-10，同日三次）：
   ① enroll builder 纠正我：我 00:30 的快照 vs 它 00:40 补齐
   ② 我自己发现：审计结论没标时点
   ③ dispatch builder 又纠正我：我 00:37 的快照 vs 它 00:42 补齐

   ★ 共同结构：**我在 T 时刻测量，在 T+Δ 报告，且从不标注 T。**
     读者（包括后来的我）会把 T 时刻的状态当成当前状态。

★ 理论依据（不是「记得标时点」，而是「结构上必须带」）：
   · Φ13 证据有时点 —— 任何状态断言都必须带时点
   · 候选A 指称完整性 —— 断言所指的对象必须可被解析与复现
   · Φ9 约束前置 —— 把规则建进结构，不靠自觉（今天已证自觉会连续失败三次）

★ 两个命令，构成闭环：
   audit-snapshot.py capture <dir...> --tag <名>   # 审计时：落快照（含每文件 sha256 + 测量时刻）
   audit-snapshot.py check   <tag>                 # 报告前：diff 快照，主动标出「自测量以来已变化」

退出码：0 无变化 · 1 有变化/快照缺失 · 2 用法或 IO 错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

VERSION = "1.0.0"
TOOL = "audit-snapshot"
SNAP_DIR = os.path.expanduser("~/dsh-collab/data/audit-snapshots")
LOG = os.path.expanduser("~/dsh-collab/logs/audit-snapshot.log")

# ⑩ 结构门：本工具**只读被测对象**，只在自己的快照目录写。
#    它绝不修改被审计的目录 —— 这是「审计不得改变被审计对象」的结构保证。
READONLY_ON_TARGETS = True


def log(rec):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        rec = {"ts": datetime.now().isoformat(timespec="seconds"), "tool": TOOL, **rec}
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[{TOOL}] 日志写入失败：{e}\n")


def hash_file(p):
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def scan(targets):
    """只读扫描；返回 {相对路径: sha256}"""
    out = {}
    for t in targets:
        t = os.path.expanduser(t)
        if os.path.isfile(t):
            h = hash_file(t)
            if h:
                out[t] = h
            continue
        for root, dirs, files in os.walk(t):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
            for fn in files:
                p = os.path.join(root, fn)
                h = hash_file(p)
                if h:
                    out[p] = h
    return out


def cmd_capture(args):
    files = scan(args.dir)
    snap = {
        "tag": args.tag,
        "measured_at": datetime.now().isoformat(timespec="seconds"),
        "targets": [os.path.expanduser(d) for d in args.dir],
        "file_count": len(files),
        "files": files,
    }
    if args.dry_run:
        print(f"[dry-run] 将捕获 {len(files)} 文件快照（tag={args.tag}）—— 未写盘")
        return 0
    os.makedirs(SNAP_DIR, exist_ok=True)
    p = os.path.join(SNAP_DIR, f"{args.tag}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)
    log({"action": "capture", "tag": args.tag, "files": len(files)})
    print(f"✅ 快照已落：{p}")
    print(f"   测量时刻：{snap['measured_at']}")
    print(f"   文件数：{len(files)}")
    print()
    print("   ★ 报告时必须写「截至 %s」—— 这就是本工具存在的理由。" % snap["measured_at"])
    return 0


def cmd_check(args):
    p = os.path.join(SNAP_DIR, f"{args.tag}.json")
    if not os.path.exists(p):
        print(f"❌ 快照不存在：{p}", file=sys.stderr)
        print("   先跑 capture。", file=sys.stderr)
        return 1
    old = json.load(open(p, encoding="utf-8"))
    now = scan(old["targets"])
    oldf = old["files"]

    added = sorted(set(now) - set(oldf))
    removed = sorted(set(oldf) - set(now))
    changed = sorted(k for k in set(oldf) & set(now) if oldf[k] != now[k])
    total_changes = len(added) + len(removed) + len(changed)

    print(f"== 审计快照比对 · tag={args.tag} ==")
    print(f"   快照测量时刻：{old['measured_at']}")
    print(f"   本次比对时刻：{datetime.now().isoformat(timespec='seconds')}")
    print(f"   文件数：{old['file_count']} → {len(now)}")
    print()

    if total_changes == 0:
        print("   ✅ 无变化 —— 快照结论仍然有效")
        print(f"      （可作为「截至 {old['measured_at']}」的断言）")
        log({"action": "check", "tag": args.tag, "changes": 0})
        return 0

    print(f"   ⚠️ ★ 自测量以来有 {total_changes} 处变化 —— 快照结论**已过期，不可直接引用**")
    print()
    if changed:
        print(f"   【已修改】{len(changed)} 个：")
        for k in changed[:15]:
            print(f"     · {k.replace(os.path.expanduser('~'), '~')}")
            print(f"       {oldf[k][:16]}… → {now[k][:16]}…")
        if len(changed) > 15:
            print(f"     …（其余 {len(changed)-15} 个）")
    if added:
        print(f"   【新增】{len(added)} 个：")
        for k in added[:10]:
            print(f"     + {k.replace(os.path.expanduser('~'), '~')}")
    if removed:
        print(f"   【删除】{len(removed)} 个：")
        for k in removed[:10]:
            print(f"     - {k.replace(os.path.expanduser('~'), '~')}")
    print()
    print("   ★ 正确做法：重跑 capture，再用新的 measured_at 作断言。")
    print("     不要写「X 缺 Y」，要写「截至 HH:MM，X 缺 Y」。")
    log({"action": "check", "tag": args.tag, "changes": total_changes,
         "changed": len(changed), "added": len(added), "removed": len(removed)})
    return 1


def cmd_list(args):
    if not os.path.isdir(SNAP_DIR):
        print("（无快照）")
        return 0
    snaps = sorted(f for f in os.listdir(SNAP_DIR) if f.endswith(".json"))
    if not snaps:
        print("（无快照）")
        return 0
    print(f"== 审计快照（{len(snaps)} 份）==")
    for f in snaps:
        try:
            d = json.load(open(os.path.join(SNAP_DIR, f), encoding="utf-8"))
            print(f"  {d['tag']:<34} {d['measured_at']}  {d['file_count']} 文件")
        except Exception:
            print(f"  {f}  （读取失败）")
    return 0


def selfcheck():
    print("== audit-snapshot 自查 ==")
    print("【① 能力清单】")
    print("  · capture：只读扫描目标 → 落快照（每文件 sha256 + 测量时刻）")
    print("  · check：重新扫描 → 与快照 diff → 标出「自测量以来已变化」")
    print("  · list：列出已有快照")
    print("【② 不该发生路径清单】")
    print("  · 修改被审计对象 → 结构上无写入目标目录的能力（只写自己的 SNAP_DIR）")
    print("  · 把「无变化」说成「永远有效」→ check 输出始终带 measured_at，明示时效")
    print("  · 用过期快照下结论 → check 在发现变化时返回 exit 1 并显式警告「不可直接引用」")
    print("【③ 依赖完整性】")
    print(f"  · Python {sys.version.split()[0]}（只标准库：os/json/hashlib/argparse/datetime）")
    print(f"  · 快照目录：{SNAP_DIR}")
    print(f"  · 日志：{LOG}")
    print("  ✅ 无外部依赖")
    return 0


def main():
    ap = argparse.ArgumentParser(description="审计快照工具（Φ13 的工程化落地）")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("capture", help="审计时：落快照")
    c.add_argument("dir", nargs="+", help="要快照的目录/文件")
    c.add_argument("--tag", required=True, help="快照名（如 builder-audit）")
    c.add_argument("--dry-run", action="store_true")

    k = sub.add_parser("check", help="报告前：比对快照")
    k.add_argument("tag")

    sub.add_parser("list", help="列出快照")

    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="store_true")
    args = ap.parse_args()

    if args.tool_version:
        print(VERSION); return 0
    if args.selfcheck:
        return selfcheck()
    if args.cmd == "capture":
        return cmd_capture(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "list":
        return cmd_list(args)

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
