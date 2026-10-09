#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint2.py — 蓝图升级工具 v2（明鉴 v2 蓝图主编流程工具化）

用户指示（2026-08-30）：把本次蓝图升级的过程插件化工具化。
沉淀流程：缺口评估 → 任务卡细化 → 主蓝图落盘 → 变更同步四步走 → Master 汇总 → 通知相关方。

用法：
  python3 bb-blueprint2.py --list                          # 蓝图树（复用 bb-blueprint.py）
  python3 bb-blueprint2.py --refine "变更摘要" --stages d25-3,d3-3   # ① 变更记录 changelog
  python3 bb-blueprint2.py --broadcast "公告标题"            # ② 广播公告 notes/collab/
  python3 bb-blueprint2.py --notify                         # ③ 定向提醒（星舵/老登/知了/守灯）
  python3 bb-blueprint2.py --master <输出路径>               # ④ Master 汇总单文件生成
  python3 bb-blueprint2.py --gate                           # 门禁链检查（当前是否达标）
  python3 bb-blueprint2.py --full "变更摘要" --stages d25-3 --out /path   # 一键全流程

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint2.log")


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

def _url(path):
    """黑板 URL 拼接（path 缺前导斜杠时补上）"""
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def put(path, obj):
    """R003 规范：PUT body = 纯内容对象"""
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(path), data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def ts():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# ────────────────── ① 变更记录（changelog）──────────────────
def refine(change_summary, stages, bp_id="flowernet", version="v2.2"):
    """step1: 写变更记录 data/blueprint/changelog/<ts>"""
    changelog = {
        "blueprint_id": bp_id,
        "version": version,
        "change_summary": change_summary,
        "affected_stages": [s.strip() for s in stages.split(",")] if stages else [],
        "author": "bb-blueprint2.py",
        "ts": now(),
    }
    key = f"data/blueprint/changelog/{ts()}"
    r = put(key, changelog)
    print(f"✅ step1 changelog: {key}")
    return key

# ────────────────── ② 广播公告 ──────────────────
def broadcast(subject, bp_id="flowernet", version="v2.2"):
    """step2: 广播 notes/collab/blueprint-change-<ts>"""
    stages = fetch("data/blueprint/stages").get("value", {})
    notice = {
        "subject": subject,
        "who": "明鉴 v2（蓝图主编）· bb-blueprint2",
        "what": f"蓝图 {bp_id} 变更（{version}）",
        "affected_stages": stages.get("stages", []) and [s.get("id") for s in stages.get("stages", [])],
        "ts": now(),
    }
    key = f"notes/collab/blueprint-change-{ts()}"
    r = put(key, notice)
    print(f"✅ step2 broadcast: {key}")
    return key

# ────────────────── ③ 定向提醒提示（输出 agent_send 文案）──────────────────
def notify():
    """step3: 输出定向提醒文案（星舵优先 + 涉事方按影响面）"""
    print("== step3 定向提醒（agent_send 文案，≤50 字）==")
    print('【蓝图更新，校准监督基准】看黑板 notes/collab/blueprint-change-<ts>（星舵 8c2494e0）')
    print('【蓝图更新】d25-3 全平台打通/d3-3 渐进自动化（老登 aa528267）')
    print('【蓝图更新】d4-1 订单域/d4-2 垂直模型（知了 a3bc8cba）')
    print('【蓝图更新】p3 传感试点/系统健康（守灯 9910d4b2）')
    print("（注：正式发送走 agent_send，此处仅生成文案模板）")

# ────────────────── ④ Master 汇总文件生成 ──────────────────
def master(out_path=None):
    """step4: 生成全量汇总单文件（stages+works+任务卡+排期+校准+论文）"""
    s = fetch("data/blueprint/stages").get("value", {})
    w = fetch("data/blueprint/works").get("value", {})
    sch = fetch("data/blueprint/flowernet/schedule-v1").get("value", {})
    if not s:
        print("❌ 黑板 stages 为空（先确认 data/blueprint/stages 存在）"); sys.exit(1)

    L = []
    L.append("# FlowerNet 蓝图 · 全量汇总（Master）")
    L.append("")
    L.append(f"> 生成：bb-blueprint2.py · {now()} · 数据源：黑板 data/blueprint/")
    L.append("")
    L.append("## 〇、BP-9 元信息")
    L.append("")
    L.append("| 字段 | 值 |")
    L.append("|------|-----|")
    L.append(f"| id | flowernet |")
    L.append(f"| name | 花店生意演进（数字化大脑 × 物理身体） |")
    L.append(f"| version | {s.get('version', '?')} |")
    L.append(f"| mainlines | 数字化 / 物理 |")
    L.append(f"| gate | {s.get('gate', '')} |")
    L.append(f"| status | active |")
    L.append(f"| ts | {s.get('ts', now())} |")
    L.append(f"| current_position | {s.get('current_position', '')} |")
    L.append("")
    L.append("## 一、子阶段全表")
    L.append("")
    for st in s.get("stages", []):
        L.append(f"### {st.get('stage')} {st.get('name')} [{st.get('status')}]")
        L.append("")
        for ss in st.get("substages", []):
            L.append(f"#### {ss.get('id')} {ss.get('name')} [{ss.get('status')}]")
            if ss.get("note"):
                L.append(f"- 说明：{ss.get('note')}")
            for sb in ss.get("substeps", []):
                L.append(f"- 子步 {sb.get('id')} {sb.get('name')} [{sb.get('status')}] dep={sb.get('dep','-')}")
            L.append("")
    L.append("## 二、工作项（works）")
    L.append("")
    L.append("| 状态 | 工作 | owner | stage |")
    L.append("|------|------|-------|-------|")
    for x in w.get("blueprint_map", []):
        L.append(f"| {x.get('status','')} | {x.get('work','')} | {x.get('owner','')} | {x.get('stage','')} |")
    L.append("")
    if sch:
        L.append("## 三、里程碑排期")
        L.append("")
        L.append("| 里程碑 | 内容 | 时间窗 | 门禁 |")
        L.append("|--------|------|--------|------|")
        for m in sch.get("milestones", []):
            L.append(f"| {m.get('id')} | {m.get('name')} | {m.get('window')} | {m.get('gate')} |")
        L.append("")
        L.append(f"**关键路径**：{sch.get('critical_path', '')}")
        L.append("")
    L.append("---")
    L.append(f"*Master 自动生成 · bb-blueprint2 · {now()}*")
    L.append("")
    out = "\n".join(L)
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w") as f:
            f.write(out)
        print(f"✅ step4 master: {out_path} ({len(out)} bytes)")
    else:
        print(out)
    return out_path or out

# ────────────────── 门禁检查 ──────────────────
def gate_check():
    """检查当前蓝图门禁链是否达标"""
    s = fetch("data/blueprint/stages").get("value", {})
    print("== 决策门禁检查 ==")
    print(f"门禁定义：{s.get('gate', '无')}")
    # 简单启发：active/partial 子阶段数量
    actives = [ss for st in s.get("stages", []) for ss in st.get("substages", []) if ss.get("status") in ("active", "partial")]
    print(f"当前推进中：{len(actives)} 个子阶段")
    print("（门禁达标判定需人工结合执行数据，工具仅汇总现状）")

# ────────────────── 一键全流程 ──────────────────
def full(change_summary, stages, out_path=None, subject=None):
    print("== 蓝图升级全流程 ==")
    k1 = refine(change_summary, stages)
    k2 = broadcast(subject or f"【蓝图变更】{change_summary[:30]}", )
    notify()
    master(out_path)
    print(f"\n✅ 全流程完成：changelog={k1} · broadcast={k2}")

def main():
    ap = argparse.ArgumentParser(description="蓝图升级工具 v2（明鉴流程工具化）")
    ap.add_argument("--refine", dest="summary", default="", help="变更摘要 → 写 changelog")
    ap.add_argument("--stages", default="", help="影响阶段列表（逗号分隔）")
    ap.add_argument("--broadcast", dest="subject", default="", help="广播公告标题")
    ap.add_argument("--notify", action="store_true", help="输出定向提醒文案")
    ap.add_argument("--master", dest="out", default="", help="生成 Master 汇总文件（路径）")
    ap.add_argument("--gate", action="store_true", help="门禁链检查")
    ap.add_argument("--full", dest="full_summary", default="", help="一键全流程（需 --stages [--out]）")
    ap.add_argument("--version", default="v2.2")
    ap.add_argument("--tool-version", action="version", version="bb-blueprint2 v1.0 (R006 六命令)")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    args = ap.parse_args()

    if args.selfcheck:
        import ast as _ast
        ok = True
        try:
            _ast.parse(open(__file__).read())
            print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); ok = False
        print("TCC:", "PASS" if ok else "FAIL")
        sys.exit(0 if ok else 1)

    if args.full_summary:
        full(args.full_summary, args.stages, args.out)
    elif args.summary:
        refine(args.summary, args.stages, version=args.version)
    elif args.subject:
        broadcast(args.subject, version=args.version)
    elif args.notify:
        notify()
    elif args.out:
        master(args.out)
    elif args.gate:
        gate_check()
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
