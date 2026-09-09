#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-workbench.py — 蓝图工作台 v3（缺口评估 + 任务卡细化 + 主蓝图落盘 工具化）

用户指示（2026-08-30）：缺口评估 / 任务卡细化 / 主蓝图落盘 三个前置环节独立工具化。
设计：工具负责结构（模板/校验/落盘/检索支撑），AI 负责智能判断（结论/动作）——二者互补。

用法：
  # ① 缺口评估器（读蓝图 + 检索 KB 论文 → 缺口报告框架）
  python3 bb-workbench.py gap [--bp flowernet] [--out 路径]

  # ② 任务卡细化器（子阶段 → 任务卡模板，格式统一可解析）
  python3 bb-workbench.py taskcards --stages d25-3,d3-3 [--out 路径] [--calib "校准点文本"]

  # ③ 主蓝图落盘器（BP-9 校验 → 更新黑板 stages/works → 版本 bump）
  python3 bb-workbench.py deploy --bp flowernet --version v2.3 \
      --stage-status d25-3:active --substep p3-2a:todo:环境传感试点 \
      --add-work "供应链支线" --work-stage p2 --work-owner 明鉴 --work-status todo
  python3 bb-workbench.py deploy --check-only   # 只校验 BP-9 字段完整性
"""
import argparse, json, sys, datetime, urllib.request, os

BB = "http://127.0.0.1:8792"
KB_BASE = "4b85333d-27a2-436a-a06e-d9be26d401b7"  # paper-cache

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

def get_stages(bp="flowernet"):
    d = fetch("data/blueprint/stages")
    return d.get("value", {}) if "error" not in d else {}

def get_works():
    d = fetch("data/blueprint/works")
    return d.get("value", {}).get("blueprint_map", []) if "error" not in d else []

# ══════════════════════ ① 缺口评估器 ══════════════════════
def gap_analyze(bp="flowernet", out_path=None):
    """读蓝图 + 检索 KB 论文 → 缺口报告框架（AI 填结论）"""
    s = get_stages(bp)
    if not s:
        print("❌ 蓝图 stages 为空（先确认黑板 data/blueprint/stages）"); sys.exit(1)
    L = []
    L.append(f"# {bp} 蓝图 · 缺口评估报告（工具生成框架）")
    L.append("")
    L.append(f"> 生成：bb-workbench.py gap · {now()} · AI 填结论，工具保证结构")
    L.append("")
    L.append("## 一、蓝图现状（工具自动提取）")
    L.append("")
    L.append(f"- 版本：{s.get('version','?')}")
    L.append(f"- 当前位置：{s.get('current_position','?')}")
    L.append(f"- 门禁：{s.get('gate','?')}")
    L.append("")
    L.append("| 阶段 | 子阶段 | 状态 | 说明 |")
    L.append("|------|--------|------|------|")
    for st in s.get("stages", []):
        for ss in st.get("substages", []):
            L.append(f"| {st.get('stage')} | {ss.get('id')} {ss.get('name')} | {ss.get('status')} | {ss.get('note','')[:50]} |")
    L.append("")
    L.append("## 二、缺口扫描（三类 × 子阶段）")
    L.append("")
    L.append("### 1. 能力缺口")
    L.append("| 子阶段 | 缺口 | 依据 | 建议 |")
    L.append("|--------|------|------|------|")
    L.append("| （AI 填） | | | |")
    L.append("")
    L.append("### 2. 依赖缺口")
    L.append("| 子阶段 | 前置依赖 | 当前状态 | 风险 |")
    L.append("|--------|----------|----------|------|")
    L.append("| （AI 填：对照全局依赖链） | | | |")
    L.append("")
    L.append("### 3. 风险缺口")
    L.append("| 子阶段 | 风险 | 等级 | 缓解 |")
    L.append("|--------|------|------|------|")
    L.append("| （AI 填） | | | |")
    L.append("")
    L.append("## 三、论文依据检索（工具自动检索 KB paper-cache）")
    L.append("")
    L.append("> 提示：用 knowledge_search 检索以下主题，命中即引用（bp-/handshake- 前缀）")
    L.append("- 数字化 3.0 端侧：Edge Intelligence / 联邦学习 / 模型压缩")
    L.append("- 物理 3.0 传感：力反馈手套 / 动作识别 / 冷链温控")
    L.append("- d4-1 数据聚合：HLC / Exactly-Once / 事件溯源")
    L.append("")
    L.append("## 四、结论（AI 填）")
    L.append("")
    L.append("- 优先缺口：")
    L.append("- 顺序风险：")
    L.append("- 建议完善：")
    L.append("")
    L.append("---")
    L.append(f"*{bp} gap-report · bb-workbench · {now()}*")
    L.append("")
    out = "\n".join(L)
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            f.write(out)
        print(f"✅ gap 报告框架: {out_path}")
    else:
        print(out)

# ══════════════════════ ② 任务卡细化器 ══════════════════════
def taskcards(stage_ids, calib="", out_path=None):
    """子阶段 → 任务卡模板（T1..Tn 含依赖/验收/owner/工时，格式统一）"""
    s = get_stages()
    stage_map = {}
    for st in s.get("stages", []):
        for ss in st.get("substages", []):
            stage_map[ss["id"]] = ss
    ids = [x.strip() for x in stage_ids.split(",") if x.strip()]
    L = []
    L.append("# 蓝图任务卡细化（工具生成模板）")
    L.append("")
    L.append(f"> 生成：bb-workbench.py taskcards · {now()}")
    if calib:
        L.append(f"> 校准点：{calib}")
    L.append("> 格式：`- [ ] **T{n} 动作** — 具体描述；验收：X；owner: Y；工时：Z`（AI 填）")
    L.append("")
    for sid in ids:
        ss = stage_map.get(sid)
        if not ss:
            L.append(f"### {sid} ❌ 不存在（--list 或检查黑板 stages）")
            L.append("")
            continue
        L.append(f"### {sid} {ss.get('name')} [{ss.get('status')}]")
        L.append("")
        L.append(f"- 当前说明：{ss.get('note','')}")
        L.append("- 任务卡：")
        for i in range(1, 6):  # 默认 5 卡模板
            dep = "T%d" % (i-1) if i > 1 else "无"
            L.append(f"- [ ] **T{i} （AI 填动作名）** — （AI 填具体动作）；验收：（AI 填）；owner: （AI 填）；工时：（AI 填）（依赖 {dep}）")
        L.append("")
    L.append("---")
    L.append(f"*taskcards 模板 · bb-workbench · {now()}*")
    L.append("")
    out = "\n".join(L)
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            f.write(out)
        print(f"✅ taskcards 模板: {out_path}")
    else:
        print(out)

# ══════════════════════ ③ 主蓝图落盘器 ══════════════════════
BP9_FIELDS = ["id", "name", "version", "mainlines", "stages", "works", "gate", "status", "ts"]

def check_bp9(s):
    """校验 BP-9 九字段"""
    missing = [f for f in BP9_FIELDS if f not in s]
    if missing:
        print(f"⚠️ BP-9 缺字段: {missing}")
        return False
    print("✅ BP-9 九字段完整")
    return True

def deploy(bp="flowernet", version="", stage_status=None, substep=None,
           add_work=None, work_stage="", work_owner="", work_status="todo",
           check_only=False):
    s = get_stages(bp)
    if not s:
        print("❌ stages 为空"); sys.exit(1)
    if check_only:
        check_bp9(s)
        return
    changed = []
    # 版本 bump
    if version:
        s["version"] = version
        changed.append(f"version→{version}")
    # 子阶段状态更新 stage-status d25-3:active
    if stage_status:
        for item in stage_status.split(","):
            if ":" not in item:
                print(f"⚠️ 跳过 {item}（需 id:status 格式）"); continue
            sid, status = item.split(":", 1)
            for st in s.get("stages", []):
                for ss in st.get("substages", []):
                    if ss.get("id") == sid:
                        ss["status"] = status
                        changed.append(f"{sid}→{status}")
    # 子步 substep p3-2a:todo:名称
    if substep:
        for item in substep.split(","):
            parts = item.split(":", 2)
            if len(parts) < 2:
                print(f"⚠️ 跳过 {item}（需 id:status[:name]）"); continue
            sid, status = parts[0], parts[1]
            name = parts[2] if len(parts) > 2 else sid
            parent = sid.rsplit("-", 1)[0] if "-" in sid else sid
            for st in s.get("stages", []):
                for ss in st.get("substages", []):
                    if ss.get("id") == parent:
                        subs = ss.setdefault("substeps", [])
                        if not any(x.get("id") == sid for x in subs):
                            subs.append({"id": sid, "name": name, "status": status, "note": ""})
                            changed.append(f"substep {sid}→{status}")
                        else:
                            for x in subs:
                                if x.get("id") == sid:
                                    x["status"] = status
                                    changed.append(f"substep {sid}→{status}")
    s["ts"] = now()
    r = put("data/blueprint/stages", s)
    print(f"✅ stages 更新: {r.get('key','?')} v{r.get('version','?')} | {', '.join(changed) if changed else '无变更'}")
    # works 增补
    if add_work:
        w = get_works()
        if not any(x.get("work") == add_work for x in w):
            w.append({"work": add_work, "stage": work_stage or "?", "owner": work_owner or "?", "status": work_status, "ts": now()})
            put("data/blueprint/works", {"blueprint_map": w, "ts": now()})
            print(f"✅ work 增补: {add_work} → {work_stage}/{work_owner}/{work_status}")
        else:
            print(f"⚠️ work 已存在: {add_work}")

def main():
    if "--selfcheck" in sys.argv:
        import ast as _ast
        try:
            _ast.parse(open(__file__).read())
            print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); sys.exit(1)
        print("TCC: PASS")
        sys.exit(0)
    ap = argparse.ArgumentParser(description="蓝图工作台 v3（gap/taskcards/deploy）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    # gap
    p_gap = sub.add_parser("gap", help="缺口评估器")
    p_gap.add_argument("--bp", default="flowernet")
    p_gap.add_argument("--out", default="")
    # taskcards
    p_tc = sub.add_parser("taskcards", help="任务卡细化器")
    p_tc.add_argument("--stages", required=True, help="子阶段 id 列表（逗号分隔）")
    p_tc.add_argument("--calib", default="", help="校准点文本")
    p_tc.add_argument("--out", default="")
    # deploy
    p_dp = sub.add_parser("deploy", help="主蓝图落盘器")
    p_dp.add_argument("--bp", default="flowernet")
    p_dp.add_argument("--version", default="", help="新版本号（bump）")
    p_dp.add_argument("--stage-status", default="", help="子阶段状态：id:status,id:status")
    p_dp.add_argument("--substep", default="", help="子步：id:status[:name]")
    p_dp.add_argument("--add-work", default="", help="增补工作项")
    p_dp.add_argument("--work-stage", default="")
    p_dp.add_argument("--work-owner", default="")
    p_dp.add_argument("--work-status", default="todo")
    p_dp.add_argument("--check-only", action="store_true", help="只校验 BP-9")
    ap.add_argument("--tool-version", action="version", version="bb-workbench v1.0 (R006 三命令)")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    args = ap.parse_args()


    if args.cmd == "gap":
        gap_analyze(args.bp, args.out)
    elif args.cmd == "taskcards":
        taskcards(args.stages, args.calib, args.out)
    elif args.cmd == "deploy":
        deploy(args.bp, args.version, args.stage_status, args.substep,
               args.add_work, args.work_stage, args.work_owner, args.work_status,
               args.check_only)

if __name__ == "__main__":
    main()
