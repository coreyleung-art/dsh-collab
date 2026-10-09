#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint.py — 蓝图管理中枢工具（动态更新工具化）

用户指示（2026-08-23）：动态更新蓝图的过程工具化插件化。
任何工作/项目登记到蓝图子阶段、更新状态，走本工具（规范、可校验、沉淀黑板）。

用法：
  查看: python3 bb-blueprint.py --list                    # 蓝图树（主阶段→子阶段→工作）
  登记: python3 bb-blueprint.py --add-work "外卖导入" --stage d25-3 --owner 运营 --status active
  更新: python3 bb-blueprint.py --update-work "外卖导入" --status done
  子阶段: python3 bb-blueprint.py --stage-status d25-3 --status done
  同步: python3 bb-blueprint.py --sync                    # 从黑板 data/ 域扫描自动映射

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, ast, datetime, urllib.request

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint.log")


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

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def get_stages():
    return fetch("/data/blueprint/stages").get("value", {})

def get_works():
    return fetch("/data/blueprint/works").get("value", {}).get("blueprint_map", [])

def save_works(works):
    put("/data/blueprint/works", {"blueprint_map": works,
         "ts": datetime.datetime.now().isoformat(timespec="seconds")})

def save_stages(stages):
    put("/data/blueprint/stages", stages)

def find_stage(stage_id):
    """查子阶段或主阶段（校验 id 存在）"""
    stages = get_stages()
    for s in stages.get("stages", []):
        if s.get("id") == stage_id:
            return s, "main"
        for ss in s.get("substages", []):
            if ss.get("id") == stage_id:
                return ss, "sub"
    return None, None

def list_all():
    stages = get_stages()
    works = get_works()
    by_stage = {}
    for w in works:
        by_stage.setdefault(w.get("stage"), []).append(w)
    out = []
    out.append("== 蓝图树 ==")
    for s in stages.get("stages", []):
        out.append("[%s] %s %s (%s)" % (s.get("mainline",""), s.get("stage",""), s.get("name",""), s.get("status","")))
        ws = by_stage.get(s.get("id"), [])
        for w in ws:
            out.append("    └ %s (%s/%s)" % (w.get("work"), w.get("status"), w.get("owner")))
        for ss in s.get("substages", []):
            out.append("    ├ %s %s [%s]" % (ss.get("id"), ss.get("name"), ss.get("status")))
            ssws = by_stage.get(ss.get("id"), [])
            for w in ssws:
                out.append("    │   └ %s (%s/%s)" % (w.get("work"), w.get("status"), w.get("owner")))
    print("\n".join(out))

def add_work(name, stage_id, owner, status):
    s, kind = find_stage(stage_id)
    if not s:
        print("❌ 阶段 %s 不存在（--list 查看）" % stage_id); sys.exit(1)
    works = get_works()
    # 去重
    if any(w.get("work") == name for w in works):
        print("⚠️ 工作 '%s' 已存在（--update-work 更新）" % name); sys.exit(1)
    works.append({"work": name, "stage": stage_id, "owner": owner, "status": status,
                  "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    save_works(works)
    print("✅ 已登记: %s → %s (%s/%s)" % (name, stage_id, status, owner))

def update_work(name, status):
    works = get_works()
    for w in works:
        if w.get("work") == name:
            w["status"] = status
            w["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
            save_works(works)
            print("✅ 已更新: %s → %s" % (name, status))
            return
    print("❌ 工作 '%s' 不存在（--add-work 先登记）" % name); sys.exit(1)

def stage_status(stage_id, status):
    stages = get_stages()
    s, kind = find_stage(stage_id)
    if not s:
        print("❌ 阶段 %s 不存在" % stage_id); sys.exit(1)
    # 找到并更新
    for m in stages.get("stages", []):
        if m.get("id") == stage_id:
            m["status"] = status
        for ss in m.get("substages", []):
            if ss.get("id") == stage_id:
                ss["status"] = status
    save_stages(stages)
    print("✅ 阶段 %s 状态 → %s" % (stage_id, status))


# 子阶段 → 下一步候选工作建议（推进蓝图的知识库）
NEXT_SUGGESTIONS = {
    "d25-3": {"work": "外卖商品订单→ERP 数据打通执行（commodityData 17426行→product/variety upsert）", "owner": "运营/协调者", "why": "数据已回溯完成，导入是 2.5 闭环关键步"},
    "d25-4": {"work": "ERP 流程闭环验收（进销存/采购/生产/销售/财务一体化打通度）", "owner": "TRAE/开发", "why": "MCP 接入后应验证流程闭环"},
    "d3-3": {"work": "决策-执行闭环（接单/定价/补货自动化规则落地）", "owner": "运营/协调者", "why": "感知已就绪(面板8787)，决策执行是 3.0 关键"},
    "d3-4": {"work": "无人值守试点（任一生产/运营环节 7x24 无人值守验证）", "owner": "运营/i9", "why": "3.0 里程碑"},
    "d4-1": {"work": "数据聚合方案（订单/传感/工艺/履约 统一 schema + 入库管道）", "owner": "4787d717/协调者", "why": "垂直引擎前置"},
    "d4-2": {"work": "flower-yolo 训练推进（论文吸收→评估→开跑，用户已拍板）", "owner": "i9", "why": "4.0 首块试金石，决策已定"},
    "d4-3": {"work": "数据飞轮设计（模型下发→更优执行→数据回流闭环）", "owner": "协调者", "why": "护城河"},
    "p2-2": {"work": "预加工标准化试点（保鲜/插泥/包扎 SOP 化）", "owner": "运营/门店", "why": "物理 2.0 关键"},
    "p2-3": {"work": "流水线工位分工（10分钟/束节拍验证）", "owner": "运营/门店", "why": "物理 2.0 里程碑"},
    "p3-2": {"work": "传感器方案评估（手套/摄像头 工艺数据化，先调研后投入）", "owner": "4787d717/i9", "why": "物理 3.0 桥梁，重资产需评估"},
}

def next_work():
    """评估推进蓝图：找待推进子阶段(todo/partial) + 候选工作 + 依赖提示"""
    stages = get_stages()
    works = get_works()
    done_works = set(w.get("work") for w in works if w.get("status") == "done")
    print("== 蓝图推进评估（下一步可做什么）==")
    print("当前: %s\n" % stages.get("current_position", ""))
    for s in stages.get("stages", []):
        for ss in s.get("substages", []):
            st = ss.get("status", "todo")
            if st in ("todo", "partial"):
                sug = NEXT_SUGGESTIONS.get(ss.get("id"))
                line = "  [%s] %s-%s %s (%s)" % (st, s.get("stage",""), ss.get("id",""), ss.get("name",""), ss.get("note",""))
                print(line)
                if sug:
                    print("      → 建议: %s" % sug.get("work"))
                    print("        负责人: %s | 理由: %s" % (sug.get("owner"), sug.get("why")))
                else:
                    print("      → 无预设建议（需人工评估）")

def sync():
    """从黑板 data/ 域扫描，推断工作归属蓝图子阶段（自动映射）"""
    data = fetch("/data/")
    ks = list(data.get("list", {}).keys())
    # 域→蓝图子阶段的启发式映射
    DOMAIN_MAP = {
        "data/erp/": "d25", "data/recovery/": "d3", "data/learning/": "d4-1",
        "data/ops/": "d3-2", "data/i9/": "d3-1", "data/frameworks/": "d3",
        "data/investigate/": "d4-1", "data/qa/": "d3", "data/blueprint/": "d3",
    }
    found = {}
    for k in ks:
        for prefix, stage in DOMAIN_MAP.items():
            if k.startswith(prefix):
                ns = k.split("/")[1]
                found.setdefault(ns, {"stage": stage, "count": 0})
                found[ns]["count"] += 1
    print("== 黑板域 → 蓝图阶段 自动映射 ==")
    for ns, info in sorted(found.items()):
        print("  data/%s/ → %s (%d keys)" % (ns, info["stage"], info["count"]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--add-work", dest="name", default="")
    ap.add_argument("--stage", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--update-work", dest="upd", default="")
    ap.add_argument("--status", default="")
    ap.add_argument("--stage-status", dest="ss", default="")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="TCC 自检")
    ap.add_argument("--next", action="store_true", help="蓝图推进评估：下一步可做什么")
    args = ap.parse_args()

    if args.selfcheck:
        try:
            ast.parse(open(__file__).read())
            print("✅ 语法 OK")
        except SyntaxError:
            print("❌ 语法"); sys.exit(1)
        print("TCC: PASS")
        sys.exit(0)
    elif args.list:
        list_all()
    elif args.name:
        if not args.stage or not args.owner or not args.status:
            print("--add-work 需 --stage --owner --status"); sys.exit(1)
        add_work(args.name, args.stage, args.owner, args.status)
    elif args.upd:
        if not args.status:
            print("--update-work 需 --status"); sys.exit(1)
        update_work(args.upd, args.status)
    elif args.ss:
        if not args.status:
            print("--stage-status 需 --status"); sys.exit(1)
        stage_status(args.ss, args.status)
    elif args.next:
        next_work()
    elif args.sync:
        sync()
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
