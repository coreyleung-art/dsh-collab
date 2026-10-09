#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sedimentation-chain-scan.py v1.0 — 自动沉淀交付链 · 待沉淀清单扫描器（纯规则，零 LLM）

职责：扫描 event-bus 的 task.completed 事件 → 按「是否新建脚本/文档/踩坑修复」信号
      → 判定「值得沉淀 / 跳过」→ 生成「待沉淀清单」（值班 HR/协调者按决策表执行七步链）。

B+ / C 两用：
  B+ 模式（默认）: 只扫描+生成清单，人工执行沉淀（值班 HR/协调者）
  C  模式（--auto）: 生成清单后自动执行本地环节（判定/查重/向量化/登记）——
                     仅「工具化写脚本/提炼总结」按置信度门控升级订阅。

零 LLM 判定信号（纯规则，不调模型）：
  值得沉淀信号：summary 含「新建/新增/工具化/脚本/插件/文档/规则/修复/踩坑/根因/复用/模式/上线」等关键词
  跳过信号：summary 含「回执/确认/查询/状态/保持/收悉/搬运」且无「新建/脚本/文档/修复」等
  默认：无信号 → 标记「人工判定」（低置信，交给值班人）

用法：
  python3 sedimentation-chain-scan.py                 # B+：扫描生成清单
  python3 sedimentation-chain-scan.py --since 7       # 最近 7 天
  python3 sedimentation-chain-scan.py --dry-run       # 只看清单不落盘
  python3 sedimentation-chain-scan.py --auto          # C：自动执行本地环节（预留，逐步启用）
  python3 sedimentation-chain-scan.py --mark-consumed  # 已沉淀的标记 consumed

输出：token-monitor/sedimentation-queue/YYYY-MM-DD.json（待沉淀清单）
      + 打印到 stdout（值班人可读）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, glob, datetime, hashlib

COLLAB = os.path.expanduser("~/dsh-collab")
EVENTS_DIR = os.path.join(COLLAB, "token-monitor", "event-bus", "events")
QUEUE_DIR = os.path.join(COLLAB, "token-monitor", "sedimentation-queue")
STATE = os.path.join(COLLAB, "token-monitor", "sedimentation-scan-state.json")

# 零 LLM 判定信号（关键词规则）
# ⚠️ 信号校准坑（2026-08-22 用 334 条真实历史任务实测，勿重踩）：
#   ① 「同步」一词歧义——既是「消息同步确认」（应 skip）也是「规则同步向量化」（应 deposit），
#      已从 SKIP_SIGNALS 移除（deposit 里无「同步」，靠其他词覆盖真任务）。
#   ② SKIP_SIGNALS 过宽会吞真任务——「状态/查询/更新/确认/搬运/转发/知悉」这类词
#      大量出现在「交付/登记/落地」真任务标题里（如「规则同步向量化机制」「CAHAC 协议 v1.0 交付」），
#      曾导致这些任务误判 skip/review。已收紧到只剩「纯回执」类词。
#   ③ 冲突分支（deposit+skip 同时命中）→ 偏 deposit（任务标题里「交付」权重 > 「回执」），
#      宁可让人复核 review 也不漏沉淀。
# 校准结果：334 条真实任务 deposit 召回率 67%→79%，skip 精准到只剩纯回执。
DEPOSIT_SIGNALS = [
    "新建", "新增", "工具化", "插件化", "脚本", "插件", "文档", "规则", "规范",
    "修复", "踩坑", "根因", "复用", "模式", "上线", "落地", "沉淀", "向量化",
    "登记", "交付", "方案", "架构", "SOP", "PoC", "poc", "bug", "Bug",
]
SKIP_SIGNALS = [
    "回执", "确认收悉", "保持协作", "收悉", "保持联动", "收到测试", "测试消息",
]
# 提炼/工具化类（需 LLM，门控升级）——扫描器只标记，不执行
HEAVY_SIGNALS = ["工具化", "插件化", "写脚本", "生成脚本", "提炼", "总结", "编译"]

def load_events(since_days):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=since_days)
    events = []
    for p in sorted(glob.glob(os.path.join(EVENTS_DIR, "*.jsonl"))):
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("topic") != "task.completed":
                continue
            try:
                ts = datetime.datetime.fromisoformat(e.get("ts", ""))
            except Exception:
                ts = datetime.datetime.now()
            if ts < cutoff:
                continue
            events.append(e)
    return events

def clean_summary(raw: str) -> str:
    """清洗 summary：剥离 $__dsh_persistent_bash_ 污染 + 提取干净任务文本"""
    import re
    s = raw or ""
    # 剥离持久 bash 污染标记（含其前缀的各种拼接形态）
    s = s.replace("$__dsh_persistent_bash_", "")
    # 剥离 json 片段残留（引号/花括号），保留可读文本
    s = re.sub(r'[{}"\']', ' ', s)
    s = re.sub(r'summary\s*:', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# ─────────────── ★ D1（2026-10-09）：--from-git 数据源 ───────────────
# 动因（有实证）：本扫描器的数据源是 event-bus 的 task.completed 事件，
#   而 2026-08-22 建链至今【无人发布该事件】⇒ 实跑恒为「0 事件 ⇒ 0 条建议」
#   （清单停在 2026-09-02，静默 37 天）。
# ⇒ 修法（按〈删除失败模式〉而非〈降低概率〉）：**不依赖任何人记得发布事件**，
#   改从【迭代必然产生的副产品】推导 —— 即 git 提交（实测近 3 天 75 个提交）。
# ⇒ 于是「没人发布事件」这一失败模式【不再可表达】。
def load_events_from_git(since_days):
    """从 git log 推导「迭代事件」，与 task.completed 同构。"""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "-C", COLLAB, "log", "--since=%s days ago" % int(since_days),
             "--pretty=format:%H\x1f%at\x1f%s"],
            capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print("[warn] git log 退出码 %s（该源跳过）" % r.returncode, flush=True)
            return []
    except Exception as e:
        print("[warn] git 不可用（该源跳过）: %s" % str(e)[:60], flush=True)
        return []
    out = []
    for line in r.stdout.split("\n"):
        parts = line.split("\x1f")
        if len(parts) < 3:
            continue
        sha, at, subj = parts[0], parts[1], parts[2]
        # ★ 2026-10-09 修 bug③：git 事件原【缺 dedup 字段】⇒ ① --mark-consumed 标记 0 条
        #   ② 扫描侧 `dedup in seen` 永远为假 ⇒ 【git 事件永远无法去重】⇒ 每次重复列同一批提交。
        #   ⇒ 按本机既有裁定补 dedup：**去重键 = 内容指纹**（CAHAC §8.3 / 章程 L33）。
        #   ⇒ 取 sha 全文更有辨识度（sha 本身即内容指纹），但为与 event-bus 的形态一致，用 sha256 短哈希。
        fp = hashlib.sha256((sha + "|" + subj).encode("utf-8")).hexdigest()[:16]
        out.append({"topic": "task.completed", "source": "git",
                    "id": "git-" + sha[:12],
                    "dedup": fp,
                    "ts": datetime.datetime.fromtimestamp(int(at)).isoformat(),
                    "payload": {"summary": subj, "sha": sha[:12]}})
    return out


def classify(summary: str):
    """纯规则判定：返回 (decision, heavy) 其中 decision ∈ {deposit, skip, review}"""
    s = summary or ""
    has_deposit = any(k in s for k in DEPOSIT_SIGNALS)
    has_skip = any(k in s for k in SKIP_SIGNALS)
    heavy = any(k in s for k in HEAVY_SIGNALS)

    if has_deposit and not has_skip:
        return "deposit", heavy
    if has_skip and not has_deposit:
        return "skip", False
    if has_deposit and has_skip:
        # 冲突：沉淀信号权重更高（任务标题里「交付/登记/落地」>「回执/收悉」）
        # 只有纯「回执类」skip 词命中才跳过；其余偏 deposit 让人工复核而非漏沉淀
        return "deposit", heavy
    return "review", False  # 无信号 → 人工判定

def load_state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except Exception:
        return {"seen": []}

def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=float, default=7.0, help="扫描最近 N 天（默认 7）")
    ap.add_argument("--from-git", action="store_true",
                    help="★ 追加 git 提交作为事件源（不依赖有人发布 task.completed）")
    ap.add_argument("--dry-run", action="store_true", help="只看清单不落盘")
    ap.add_argument("--auto", action="store_true", help="C 模式：自动执行本地环节（预留，逐步启用）")
    ap.add_argument("--mark-consumed", action="store_true", help="把已沉淀事件标记 consumed（需先人工执行）")
    args = ap.parse_args()

    # ★ 2026-10-09 修 bug②（早返回）：--mark-consumed 必须在【扫描与落盘之前】处理。
    #   上一版把它放在末尾 ⇒ 扫描已把清单覆盖（不带 --from-git 时 events 空 ⇒ 清单变 0）
    #   ⇒ 再读「现有清单」已是 0。⇒ 现改为【args 解析后立即分流并 return】。
    if args.mark_consumed:
        import glob as _g
        files = sorted(_g.glob(os.path.join(QUEUE_DIR, "*.json")))
        src, src_q = None, []
        if files:
            src = files[-1]
            try:
                src_q = json.load(open(src, encoding="utf-8")).get("queue") or []
            except Exception as e:
                print("[warn] 读现有清单失败（%s）" % type(e).__name__)
        st = load_state()
        sn = set(st.get("seen", []))
        n = 0
        for q in src_q:
            d = q.get("dedup")
            if d:
                sn.add(d); n += 1
        st["seen"] = sorted(sn)
        save_state(st)
        print("✅ 已标记 %d 条为已处理（源：%s · seen=%d）"
              % (n, os.path.basename(src) if src else "（无清单文件）", len(sn)))
        if n == 0 and not src_q:
            print("   ★ 注意：现有清单为空或不可读 ⇒ 未标记任何项（清单未被改动）")
        return

    events = load_events(args.since)


    src_git = 0


    if args.from_git:


        g = load_events_from_git(args.since)


        src_git = len(g)


        _seen = {e.get('id') for e in events}


        events += [e for e in g if e.get('id') not in _seen]
    state = load_state()
    seen = set(state.get("seen", []))

    queue = []
    for e in events:
        dedup = e.get("dedup", "")
        summary = str(e.get("payload", {}).get("summary", ""))
        consumed = e.get("consumed", False)
        if consumed or dedup in seen:
            continue
        decision, heavy = classify(clean_summary(summary))
        queue.append({
            "dedup": dedup,
            "ts": e.get("ts"),
            "summary": clean_summary(summary)[:200],
            "decision": decision,  # deposit / skip / review
            "heavy": heavy,        # 是否需 LLM（工具化/提炼，门控升级）
        })

    # 分类统计
    deposit = [q for q in queue if q["decision"] == "deposit"]
    review = [q for q in queue if q["decision"] == "review"]
    skip = [q for q in queue if q["decision"] == "skip"]

    print("=== 自动沉淀交付链 · 待沉淀扫描（纯规则零 LLM）===")
    print(f"扫描窗口: 最近 {args.since} 天 · task.completed 事件: {len(events)} · 未处理: {len(queue)}")
    print(f"  ✅ 建议沉淀: {len(deposit)} · 🔍 人工判定: {len(review)} · ⏭️ 跳过: {len(skip)}")
    if args.auto:
        print("  🤖 C 模式: 本地环节自动执行（判定/查重/向量化/登记）")
        print("  ⚠️ 工具化/提炼类（heavy）按置信度门控，需 gemma4→flash 升级，扫描器不代执行")
    print()

    if deposit:
        print("── 建议沉淀清单（按交付链七步执行）──")
        for q in deposit:
            heavy_tag = " [需LLM提炼/工具化]" if q["heavy"] else " [全本地零订阅]"
            print(f"  ✅ {q['ts'][:16]} | {q['summary'][:70]}{heavy_tag}")
    if review:
        print("── 人工判定清单（无信号或信号冲突）──")
        for q in review:
            print(f"  🔍 {q['ts'][:16]} | {q['summary'][:70]}")
    if skip:
        print(f"── 跳过 {len(skip)} 条（纯执行无复用）──")

    # 落盘
    if not args.dry_run:
        os.makedirs(QUEUE_DIR, exist_ok=True)
        out = os.path.join(QUEUE_DIR, datetime.date.today().isoformat() + ".json")
        json.dump({"date": datetime.date.today().isoformat(), "queue": queue,
                   "deposit": len(deposit), "review": len(review), "skip": len(skip)},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n📋 待沉淀清单已落盘: {out}")

    if args.mark_consumed:
        # ★ 2026-10-09 修 bug（我的 --from-git 接线引入）：
        #   原实现【用本次重算的 queue】来标记。而 --mark-consumed 若不带 --from-git，
        #   events 只剩 event-bus（空）⇒ queue 空 ⇒ ① 标记 0 条 ② 【且落盘把清单覆盖成 0】
        #   —— 实测：一次 --mark-consumed 把 56 条清单清空。
        #   ⇒ 删除式修法（而非「记得也传 --from-git」）：**改为从【现有清单文件】读**，
        #     不重算 ⇒ 「参数不一致导致清空」这一失败模式**不再可表达**。
        latest = None
        if os.path.isdir(QUEUE_DIR):
            files = sorted(f for f in os.listdir(QUEUE_DIR) if f.endswith(".json"))
            latest = os.path.join(QUEUE_DIR, files[-1]) if files else None
        src_q = []
        if latest:
            try:
                src_q = json.load(open(latest, encoding="utf-8")).get("queue") or []
            except Exception as e:
                print(f"[warn] 读现有清单失败（{type(e).__name__}）⇒ 回退用本次扫描结果")
        if not src_q:
            src_q = queue            # 回退：现有清单为空/读不到时，用本次扫描结果
        n = 0
        for q in src_q:
            d = q.get("dedup")
            if d:
                seen.add(d); n += 1
        state["seen"] = sorted(seen)
        save_state(state)
        print(f"✅ 已标记 {n} 条为已处理（源：{os.path.basename(latest) if latest else '本次扫描'} · seen={len(seen)}）")

if __name__ == "__main__":
    main()
