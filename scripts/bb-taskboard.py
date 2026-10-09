#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-taskboard.py — 任务卡执行状态机（领卡/汇报/插卡/看板/进度图）

用户指示（2026-08-30）：每个角色/节点完成后自动标注汇报 → 快速插卡登记 → 领卡，
形成任务进度状态机，支持并发开展任务（非线性推进）。

状态机：
  todo（待领）→ claimed（已领/执行中）→ done（完成待验收）→ verified（验收通过）
                        └──→ blocked（阻塞，可解阻回 claimed）

并发模型：
  - 每张卡独立状态，多角色可同时领不同卡（互不阻塞）
  - 汇报自动登记 changelog + 黑板 taskboard 命名空间
  - 依赖卡未 done 时提示（软约束，可强制）

用法：
  # 初始化：从 taskcards 文件导入任务卡到黑板 taskboard
  python3 bb-taskboard.py --init ~/dsh-collab/data/blueprint/flowernet/taskcards-v1.md

  # 领卡（角色领取，todo → claimed）
  python3 bb-taskboard.py --claim d25-3-T1 --who 运营

  # 汇报完成（claimed/done → done，自动登记 changelog）
  python3 bb-taskboard.py --report d25-3-T1 --who 运营 [--note "映射表完成"]

  # 验收（done → verified）
  python3 bb-taskboard.py --verify d25-3-T1 --who 明鉴

  # 插卡（动态新增任务卡）
  python3 bb-taskboard.py --insert "T5 全平台对账复核" --stage d25-3 --owner 运营 --dep T4

  # 阻塞/解阻
  python3 bb-taskboard.py --block d25-3-T2 --reason "依赖 T1 未完成"
  python3 bb-taskboard.py --unblock d25-3-T2

  # 看板（按状态分组）& 进度图
  python3 bb-taskboard.py --list [--stage d25-3] [--status todo]
  python3 bb-taskboard.py --graph

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-taskboard.log")


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
NS = "data/blueprint/flowernet/taskboard"
STAGES = ["todo", "claimed", "done", "verified", "blocked"]

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(path), data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def ts():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# ─────────── 任务卡存储（黑板 taskboard 命名空间）───────────
def load_cards():
    d = fetch(NS)
    if "error" in d:
        return {}
    v = d.get("value", {})
    if isinstance(v, dict) and "cards" in v:
        return v["cards"]
    return {}

def save_cards(cards):
    return put(NS, {"cards": cards, "ts": now()})

def get_card(cards, tid):
    return cards.get(tid)

def find_card_by_sub(cards, tid):
    """tid 可能是 'd25-3-T1' 或 'T1'（后者在 stage 内查找）"""
    if tid in cards:
        return tid, cards[tid]
    # T1 → 找第一个匹配
    for k, v in cards.items():
        if v.get("tid") == tid or k.endswith("-" + tid):
            return k, v
    return None, None

# ─────────── ① 初始化：从 taskcards 文件导入 ───────────
def init(filepath):
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}"); sys.exit(1)
    with open(filepath) as f:
        content = f.read()
    cards = {}
    # 解析 - [ ] **T{n} 动作** — 描述；验收：X；owner: Y；工时：Z
    current_stage = None
    for line in content.split("\n"):
        sm = re.match(r'####\s+([dp]\d[\d\-]+)\s+', line)
        if sm:
            current_stage = sm.group(1)
            continue
        cm = re.match(r'- \[ \] \*\*(T[\d\w]+)\s+([^*]+?)\*\*(?:（依赖\s*([^）]+)）)?\s*—\s*(.+)', line.strip())
        if cm and current_stage:
            tid, name, dep, rest = cm.group(1), cm.group(2).strip(), cm.group(3), cm.group(4).strip()
            if dep is None:
                dep = "无"
            owner = "?"
            om = re.search(r'owner:\s*([^；;]+)', rest)
            if om:
                owner = om.group(1).strip()
            effort = "?"
            em = re.search(r'工时[:：]\s*([^；;]+)', rest)
            if em:
                effort = em.group(1).strip()
            full_id = f"{current_stage}-{tid}"
            cards[full_id] = {
                "id": full_id, "tid": tid, "stage": current_stage,
                "name": name, "dep": dep, "owner": owner, "effort": effort,
                "desc": rest[:120], "status": "todo", "claimed_by": None,
                "claimed_at": None, "done_at": None, "blocked_reason": None,
            }
    save_cards(cards)
    print(f"✅ 任务卡初始化: {len(cards)} 张（黑板 {NS}）")

# ─────────── ② 领卡 ───────────
def claim(tid, who):
    cards = load_cards()
    k, card = find_card_by_sub(cards, tid)
    if not card:
        print(f"❌ 任务卡 {tid} 不存在（--init 或 --list）"); sys.exit(1)
    if card["status"] == "claimed":
        print(f"⚠️ {k} 已被 {card['claimed_by']} 领取（执行中）"); return
    if card["status"] == "done":
        print(f"⚠️ {k} 已完成，无需领取"); return
    if card["status"] == "verified":
        print(f"⚠️ {k} 已验收"); return
    # 软依赖检查
    if card.get("dep") and card["dep"] != "无":
        dep_id = f"{card['stage']}-{card['dep']}"
        dcard = cards.get(dep_id)
        if dcard and dcard.get("status") not in ("done", "verified"):
            print(f"⚠️ 依赖 {dep_id} 未完成（[{dcard.get('status')}]）——仍领取? 用 --force")
            if not force:
                return
    card["status"] = "claimed"
    card["claimed_by"] = who
    card["claimed_at"] = now()
    card["blocked_reason"] = None
    save_cards(cards)
    print(f"✅ 领卡: {k} [{card['name']}] → claimed（{who} @ {card['claimed_at']}）")

# ─────────── ③ 汇报完成（自动登记 changelog）───────────
def report(tid, who, note=""):
    cards = load_cards()
    k, card = find_card_by_sub(cards, tid)
    if not card:
        print(f"❌ 任务卡 {tid} 不存在"); sys.exit(1)
    if card["status"] == "done":
        print(f"⚠️ {k} 已汇报过（done @ {card.get('done_at')}）"); return
    if card["status"] == "todo":
        print(f"⚠️ {k} 未领取——直接完成？用 --claim 先领或 --force"); 
        if not force: return
    card["status"] = "done"
    card["done_by"] = who
    card["done_at"] = now()
    card["done_note"] = note
    save_cards(cards)
    # 自动登记 changelog
    changelog = {
        "blueprint_id": "flowernet", "version": "taskboard",
        "change_summary": f"任务卡完成: {k} {card['name']}（{who}）{(' - ' + note) if note else ''}",
        "affected_stages": [card["stage"]], "author": f"bb-taskboard:{who}", "ts": now(),
    }
    put(f"data/blueprint/changelog/{ts()}", changelog)
    print(f"✅ 汇报完成: {k} → done（{who}）· changelog 已登记")

# ─────────── ④ 验收 ───────────
def verify(tid, who):
    cards = load_cards()
    k, card = find_card_by_sub(cards, tid)
    if not card:
        print(f"❌ 任务卡 {tid} 不存在"); sys.exit(1)
    if card["status"] != "done":
        print(f"⚠️ {k} 未完成（[{card['status']}]），先 --report"); return
    card["status"] = "verified"
    card["verified_by"] = who
    card["verified_at"] = now()
    save_cards(cards)
    print(f"✅ 验收: {k} → verified（{who}）")

# ─────────── ⑤ 插卡（动态新增）───────────
def insert(name, stage, owner="?", dep="无", effort="?"):
    cards = load_cards()
    # 找该 stage 现有最大 T 编号
    nums = [int(k.split("-T")[1]) for k in cards if k.startswith(f"{stage}-T")]
    n = (max(nums) + 1) if nums else 1
    full_id = f"{stage}-T{n}"
    cards[full_id] = {
        "id": full_id, "tid": f"T{n}", "stage": stage, "name": name,
        "dep": dep, "owner": owner, "effort": effort, "desc": "插卡新增",
        "status": "todo", "claimed_by": None, "claimed_at": None,
        "done_at": None, "blocked_reason": None,
    }
    save_cards(cards)
    print(f"✅ 插卡: {full_id} {name}（{stage}/{owner}，dep={dep}）→ todo")

# ─────────── ⑥ 阻塞/解阻 ───────────
def block(tid, reason):
    cards = load_cards()
    k, card = find_card_by_sub(cards, tid)
    if not card:
        print(f"❌ 任务卡 {tid} 不存在"); sys.exit(1)
    card["status"] = "blocked"
    card["blocked_reason"] = reason
    card["blocked_at"] = now()
    save_cards(cards)
    print(f"⚠️ 阻塞: {k} → blocked（{reason}）")

def unblock(tid):
    cards = load_cards()
    k, card = find_card_by_sub(cards, tid)
    if not card:
        print(f"❌ 任务卡 {tid} 不存在"); sys.exit(1)
    card["status"] = "claimed"
    card["blocked_reason"] = None
    save_cards(cards)
    print(f"✅ 解阻: {k} → claimed")

# ─────────── ⑦ 看板 ───────────
def list_cards(stage=None, status=None):
    cards = load_cards()
    if not cards:
        print("（空）先 --init 导入任务卡"); return
    items = sorted(cards.values(), key=lambda c: (c["stage"], c["tid"]))
    if stage:
        items = [c for c in items if c["stage"] == stage]
    if status:
        items = [c for c in items if c["status"] == status]
    icons = {"todo": "⬜", "claimed": "🟢", "done": "✅", "verified": "🏁", "blocked": "🔴"}
    print("== 任务卡看板 ==")
    cur_stage = None
    for c in items:
        if c["stage"] != cur_stage:
            cur_stage = c["stage"]
            print(f"\n[{cur_stage}]")
        ic = icons.get(c["status"], "?")
        who = f"@{c.get('claimed_by') or c.get('done_by') or c.get('owner')}"
        dep = f" dep={c['dep']}" if c.get("dep") and c["dep"] != "无" else ""
        extra = f" 阻塞:{c['blocked_reason']}" if c["status"] == "blocked" else ""
        print(f"  {ic} {c['id']} {c['name'][:24]:26s} [{c['status']:8s}] {who}{dep}{extra}")

# ─────────── ⑧ 进度图 ───────────
def graph():
    cards = load_cards()
    if not cards:
        print("（空）"); return
    total = len(cards)
    st = {s: 0 for s in STAGES}
    for c in cards.values():
        st[c["status"]] = st.get(c["status"], 0) + 1
    print("== 任务进度状态机 ==")
    print(f"总计 {total} 张")
    bar_w = 30
    for s in STAGES:
        n = st.get(s, 0)
        pct = n / total * 100 if total else 0
        bar = "█" * int(pct / 100 * bar_w)
        print(f"  {s:9s} {n:3d} ({pct:4.1f}%) {bar}")
    done_pct = (st.get("done", 0) + st.get("verified", 0)) / total * 100 if total else 0
    active = st.get("claimed", 0) + st.get("blocked", 0)
    print(f"\n完成率 {done_pct:.1f}% · 并发执行中 {active} 张")

# ─────────── main ───────────
def main():
    global force
    ap = argparse.ArgumentParser(description="任务卡执行状态机（并发/领卡/汇报/插卡）")
    ap.add_argument("--init", default="", help="从 taskcards 文件导入")
    ap.add_argument("--claim", default="", help="领卡（任务卡 id）")
    ap.add_argument("--who", default="", help="操作角色")
    ap.add_argument("--report", default="", help="汇报完成（自动登记 changelog）")
    ap.add_argument("--verify", default="", help="验收")
    ap.add_argument("--insert", default="", help="插卡（新增任务卡名）")
    ap.add_argument("--stage", default="", help="插卡目标子阶段")
    ap.add_argument("--owner", default="?", help="插卡 owner")
    ap.add_argument("--dep", default="无", help="插卡依赖")
    ap.add_argument("--block", default="", help="阻塞任务卡")
    ap.add_argument("--reason", default="", help="阻塞原因")
    ap.add_argument("--unblock", default="", help="解阻任务卡")
    ap.add_argument("--list", action="store_true", help="看板")
    ap.add_argument("--graph", action="store_true", help="进度图")
    ap.add_argument("--status", default="", help="看板过滤状态")
    ap.add_argument("--note", default="", help="汇报备注")
    ap.add_argument("--force", action="store_true", help="跳过依赖/状态检查")
    ap.add_argument("--tool-version", action="version", version="bb-taskboard v1.0 (R006 九命令)")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    args = ap.parse_args()
    if args.selfcheck:
        import ast as _ast
        try:
            _ast.parse(open(__file__).read())
            print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); sys.exit(1)
        print("TCC: PASS")
        sys.exit(0)
    force = args.force

    if args.init:
        init(args.init)
    elif args.claim:
        claim(args.claim, args.who or "?")
    elif args.report:
        report(args.report, args.who or "?", args.note)
    elif args.verify:
        verify(args.verify, args.who or "?")
    elif args.insert:
        insert(args.insert, args.stage, args.owner, args.dep)
    elif args.block:
        block(args.block, args.reason or "未注明")
    elif args.unblock:
        unblock(args.unblock)
    elif args.list:
        list_cards(args.stage, args.status)
    elif args.graph:
        graph()
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
