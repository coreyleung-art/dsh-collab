#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""convention-pr.py — 公约提案通道（类似 PR，端侧主桥可提交）
用户 2026-09-09: 公约维护不该单方面(mac-mini)，端侧(MBP/i9 主桥)应能提交补充意见
类比 Git PR: submit(端侧提) → review(评审) → merge/reject(裁决) → 版本bump → notify-nodes

用法:
  python3 convention-pr.py list [--status pending|review|merged|rejected]
  python3 convention-pr.py submit --from mbp:mbp-bus --clause "§3.1.1-B" --title "..." --suggest "..." --reason "..."
  python3 convention-pr.py review <pr_id>
  python3 convention-pr.py merge <pr_id>
  python3 convention-pr.py reject <pr_id> --reason "..."
Lean4: 提案格式强制校验(字段齐全); G-C34/C35

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/convention-pr.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

PROPOSALS_DIR = os.path.expanduser("~/dsh-collab/data/registry/convention-proposals")
REQUIRED = ["pr_id", "title", "clause", "suggest", "reason", "proposer", "ts", "status"]
VALID_STATUS = ["pending", "review", "merged", "rejected"]
# 可提交方(端侧主桥/协调者/本机角色)
ALLOWED_PROPOSERS_PREFIX = ["mbp", "i9", "mac-mini", "server", "bus:"]

def ensure_dir():
    os.makedirs(PROPOSALS_DIR, exist_ok=True)

def load_all():
    ensure_dir()
    prs = []
    for f in sorted(os.listdir(PROPOSALS_DIR)):
        if f.endswith(".json"):
            try:
                prs.append(json.load(open(os.path.join(PROPOSALS_DIR, f))))
            except Exception:
                pass
    return prs

def next_seq():
    today = datetime.date.today().strftime("%Y%m%d")
    existing = [p for p in load_all() if p.get("pr_id", "").startswith(f"CP-{today}")]
    return f"CP-{today}-{len(existing)+1:03d}"

def validate(pr):
    """Lean4 G-C34: 提案格式强制——字段齐全+状态合法"""
    missing = [k for k in REQUIRED if not pr.get(k)]
    if missing:
        return False, f"缺字段: {missing}"
    if pr.get("status") not in VALID_STATUS:
        return False, f"状态非法: {pr.get('status')}"
    if not pr.get("reason") or len(pr["reason"]) < 5:
        return False, "reason 过短(须带实测/场景理由, R030)"
    return True, "ok"

def proposer_ok(frm):
    """G-C35: 提出方合法(端侧主桥 mbp:/i9: 或本机)"""
    for p in ALLOWED_PROPOSERS_PREFIX:
        if str(frm).startswith(p): return True
    return False

def submit(args):
    pr = {"pr_id": next_seq(), "title": args.title, "clause": args.clause,
          "suggest": args.suggest, "reason": args.reason, "proposer": args.from_,
          "ts": datetime.datetime.now().isoformat(), "status": "pending"}
    ok, msg = validate(pr)
    if not ok:
        print(f"❌ {msg}"); return 1
    if not proposer_ok(pr["proposer"]):
        print(f"❌ 提出方 {pr['proposer']} 不在允许列表(端侧桥 mbp:/i9:/本机)"); return 1
    fp = os.path.join(PROPOSALS_DIR, pr["pr_id"] + ".json")
    json.dump(pr, open(fp, "w"), ensure_ascii=False, indent=2)
    print(f"✅ 提案已提交: {pr['pr_id']} ({pr['proposer']})\n   {pr['title']}\n   状态: pending → 待 review")
    return 0

def list_prs(args):
    prs = load_all()
    if args.status:
        prs = [p for p in prs if p.get("status") == args.status]
    if not prs:
        print("(无提案)"); return 0
    for p in prs:
        print(f"[{p.get('status','?'):<8}] {p.get('pr_id')} {p.get('proposer','?'):<16} {p.get('title','')[:40]}")
        if p.get("status") in ("pending", "review"):
            print(f"        条款:{p.get('clause','')} | 建议:{str(p.get('suggest',''))[:60]}")
    return 0

def transition(pr_id, new_status, reason=None):
    fp = os.path.join(PROPOSALS_DIR, pr_id + ".json")
    if not os.path.exists(fp):
        print(f"❌ 提案 {pr_id} 不存在"); return 1
    pr = json.load(open(fp))
    pr["status"] = new_status
    if reason:
        pr["review_note"] = reason
    json.dump(pr, open(fp, "w"), ensure_ascii=False, indent=2)
    print(f"✅ {pr_id} → {new_status}" + (f" | {reason}" if reason else ""))
    # merged 提示触发 notify-nodes + 版本 bump
    if new_status == "merged":
        print(f"⚠️ 已合并——请: ①并入公约文本 ②版本 bump(v1.x) ③notify-nodes.sh 抄送全节点")
    return 0

def main():
    ap = argparse.ArgumentParser(description="公约提案通道(PR)")
    sub = ap.add_subparsers(dest="cmd")
    sp = sub.add_parser("list"); sp.add_argument("--status", default=None)
    sp2 = sub.add_parser("submit")
    sp2.add_argument("--from", dest="from_", required=True)
    sp2.add_argument("--clause", required=True)
    sp2.add_argument("--title", required=True)
    sp2.add_argument("--suggest", required=True)
    sp2.add_argument("--reason", required=True)
    for cmd in ["review", "merge", "reject"]:
        s = sub.add_parser(cmd); s.add_argument("pr_id")
    srej = sub.add_parser("reject"); srej.add_argument("pr_id"); srej.add_argument("--reason", default="")
    # reject 需 reason——上面循环已建, 补
    args = ap.parse_args()
    if args.cmd == "list": return list_prs(args)
    if args.cmd == "submit": return submit(args)
    if args.cmd == "review": return transition(args.pr_id, "review")
    if args.cmd == "merge": return transition(args.pr_id, "merged")
    if args.cmd == "reject":
        if not args.reason: print("❌ reject 需 --reason"); return 1
        return transition(args.pr_id, "rejected", args.reason)
    ap.print_help(); return 1

if __name__ == "__main__":
    sys.exit(main())
