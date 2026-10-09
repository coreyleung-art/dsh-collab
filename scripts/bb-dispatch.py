#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-dispatch.py — 事件分发决策器（协调者判断门工具化）

用户指示（2026-08-23）：具体事件/工作该分发给谁 + 哪个角色应加入评估——
这个判断过程工具化、插件化、沉淀到链。

用法：
  python3 bb-dispatch.py --event "论文全文拉取落链"          # 自动匹配主责+协作者
  python3 bb-dispatch.py --event "外卖订单异常告警" 
  python3 bb-dispatch.py --event "黑板升级到 v0.7"
  python3 bb-dispatch.py --list-role                            # 列出角色能力库

输出：{event, primary(主责), collaborators(应加入评估), channels, reasons, decision_id}
  主责：负责执行的角色
  协作者：应加入评估/协作的角色（如涉及成本→HR、涉及质量→QA、涉及设备→设备协调）
  决策沉淀：写黑板 data/dispatch/<seq>（可追溯）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, re, urllib.request, time

import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-dispatch.log")


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

# ── 角色能力知识库（动态加载：优先黑板 data/frameworks/dispatch-kb，本地兜底）──
# 知识库由 bb-dispatch-learn.py 维护（自进化：新角色同步/决策回灌/版本化）
LOCAL_ROLES = {
    "4787d717": {"name": "数据调查", "ns": "investigate",
                 "keywords": ["论文", "调研", "调查", "爬虫", "信息源", "拉取", "数据资产", "知识向量", "情报"],
                 "assess": ["涉及数据来源可靠性"]},
    "a3bc8cba": {"name": "学习", "ns": "learning",
                 "keywords": ["学习", "探测", "固化", "聚类", "范本", "沟通学习", "场景学习"],
                 "assess": ["涉及探索/探测/学习类"]},
    "aa528267": {"name": "运营", "ns": "ops",
                 "keywords": ["外卖", "订单", "运营", "告警处理", "接单", "拒单", "上下架", "改价", "日报", "评价", "售后"],
                 "assess": ["涉及外卖业务动作"]},
    "45f89009": {"name": "运营", "ns": "ops",
                 "keywords": ["外卖", "订单", "日报", "流量", "关键字", "异常检查"],
                 "assess": []},
    "0e84e65c": {"name": "供应链", "ns": "supply-chain",
                 "keywords": ["供应链", "依赖", "npm", "pnpm", "lockfile", "采购", "库存", "xberg"],
                 "assess": ["涉及依赖/供应链变更"]},
    "ffb7c3ab": {"name": "QA", "ns": "qa",
                 "keywords": ["验收", "回归", "测试", "冒烟", "质量", "视觉回归", "基线"],
                 "assess": ["涉及交付质量/验收/回归"]},
    "54e809ed": {"name": "媒体", "ns": "media",
                 "keywords": ["媒体", "稿件", "内容", "发布", "论坛", "专栏", "社群"],
                 "assess": ["涉及对外内容/媒体"]},
    "55d4d1bd": {"name": "摄取", "ns": "ingest",
                 "keywords": ["摄取", "归档", "文档", "OCR", "解析", "PDF", "入库"],
                 "assess": ["涉及文档摄取/归档"]},
    "2a15e6b1": {"name": "HR", "ns": "registry",
                 "keywords": ["资源", "成本", "登记", "registry", "预算", "台账", "审计", "token", "配额"],
                 "assess": ["涉及成本/资源/预算/登记", "涉及多角色协作", "涉及新资产/新角色"]},
    "b193c782": {"name": "客服", "ns": "customer-service",
                 "keywords": ["客服", "IM", "客户", "值守", "回复", "会话", "工单"],
                 "assess": ["涉及客户沟通"]},
    "6ed4daf2": {"name": "恢复自查", "ns": "recovery",
                 "keywords": ["恢复", "自查", "崩溃", "重启", "健康", "巡检", "灾难"],
                 "assess": ["涉及恢复/健康/崩溃"]},
    "coordinator": {"name": "协调者", "ns": "iterations",
                 "keywords": ["协调", "分发", "制度", "协议", "黑板", "底座", "升级"],
                 "assess": ["涉及制度/协议/底座架构"]},
}

# 场景 → 应加入评估的角色（跨域协作判断，随知识库更新）
ASSESS_RULES = [
    {"trigger": ["成本", "预算", "资源", "配额", "token", "登记", "新角色", "新资产"], "roles": ["2a15e6b1"], "why": "成本/资源/登记归 HR"},
    {"trigger": ["质量", "验收", "交付", "回归", "上线"], "roles": ["ffb7c3ab"], "why": "质量验收归 QA"},
    {"trigger": ["设备", "算力", "GPU", "i9", "门店", "节点"], "roles": ["2a15e6b1"], "why": "算力/资源评估归 HR"},
    {"trigger": ["崩溃", "恢复", "重启", "健康"], "roles": ["6ed4daf2"], "why": "恢复自查归 6ed4daf2"},
    {"trigger": ["协议", "制度", "黑板", "底座"], "roles": ["coordinator"], "why": "底座架构归协调者"},
]

# ── 动态知识库加载（自进化核心：从黑板加载，可被 learn 更新）──
ROLES = dict(LOCAL_ROLES)   # 全局 ROLES，运行时被 _load_kb 覆盖

def _load_kb():
    """从黑板加载知识库（data/frameworks/dispatch-kb），失败用本地兜底"""
    global ROLES, ASSESS_RULES
    try:
        with urllib.request.urlopen(BB + "/data/frameworks/dispatch-kb", timeout=5) as r:
            kb = json.loads(r.read().decode()).get("value", {})
        if kb.get("roles"):
            ROLES = kb["roles"]
        if kb.get("assess_rules"):
            ASSESS_RULES = kb["assess_rules"]
        return kb.get("version", "?")
    except Exception:
        return "local"

def _embed(text):
    """bge-m3 本地 embedding（Ollama 零订阅）"""
    try:
        body = json.dumps({"model": "bge-m3", "prompt": text}).encode()
        req = urllib.request.Request("http://127.0.0.1:11434/api/embeddings", data=body,
                                     headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()).get("embedding", [])
    except Exception:
        return []

def _cos(a, b):
    try:
        import math
        return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) or 1)
    except Exception:
        return 0

def match_semantic(event):
    """语义匹配：角色能力描述向量 vs 事件向量（表述差异兜底）"""
    descs = {rid: " ".join(r.get("keywords", [])) for rid, r in ROLES.items()}
    ev = _embed(event)
    if not ev:
        return None, 0
    best, best_sim = None, 0
    for rid, desc in descs.items():
        if not desc:
            continue
        rv = _embed(desc)
        sim = _cos(ev, rv)
        if sim > best_sim:
            best, best_sim = rid, sim
    return best, best_sim

def match_primary(event):
    """主责匹配：最高关键词命中角色"""
    best, best_n = None, 0
    for rid, r in ROLES.items():
        n = sum(1 for kw in r["keywords"] if kw in event)
        if n > best_n:
            best, best_n = rid, n
    return best, best_n

def match_assess(event):
    """协作者匹配：场景规则命中"""
    adds = []
    for rule in ASSESS_RULES:
        if any(t in event for t in rule["trigger"]):
            for rid in rule["roles"]:
                if rid not in [a["id"] for a in adds]:
                    adds.append({"id": rid, "name": ROLES[rid]["name"], "why": rule["why"]})
    return adds

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", help="事件/任务描述")
    ap.add_argument("--list-role", action="store_true", help="列出角色能力库")
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--as", dest="caller", default="", help="调用者角色id（泛化：任意角色用它判断自己处理还是转交）")
    ap.add_argument("--semantic", action="store_true", help="启用语义匹配（bge-m3 本地向量，提升表述差异命中）")
    args = ap.parse_args()
    kb_ver = _load_kb()   # 自进化：启动加载黑板知识库（可被 learn 更新）

    if args.list_role:
        print("== 角色能力知识库 (kb v%s) ==" % kb_ver)
        for rid, r in ROLES.items():
            print("  %s (%s): %s" % (r["name"], rid, "、".join(r["keywords"][:5])))
        sys.exit(0)

    if not args.event:
        print("需 --event 描述事件/任务"); sys.exit(1)

    e = args.event
    primary_id, score = match_primary(e)
    if args.semantic and (primary_id is None or score < 1):
        sem_id, sem_sim = match_semantic(e)
        if sem_id and sem_sim > 0.45:
            primary_id = sem_id
            score = round(sem_sim, 3)
    assess = match_assess(e)

    result = {
        "event": e,
        "decision_id": "dispatch-%s" % str(int(time.time()*1000))[-8:],
        "primary": {"id": primary_id, "name": ROLES[primary_id]["name"], "score": score} if primary_id else None,
        "collaborators": assess,
        "channels": {
            "primary": "任务卡(p2p) 或黑板 data/%s/" % ROLES[primary_id]["ns"] if primary_id else "待定",
            "collaborators": "黑板 data/ 事件回流（评估）",
        },
        "reasons": "主责按职责域关键词匹配；协作者按场景规则（成本→HR/质量→QA/设备→HR/崩溃→恢复）",
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    # 泛化：--as 调用者视角
    if args.caller and primary_id:
        result["caller_view"] = {
            "caller": args.caller,
            "mine": primary_id == args.caller,
            "verdict": "✅ 归你处理" if primary_id == args.caller
                       else "↩️ 转交 %s（%s）" % (ROLES[primary_id]["name"], primary_id),
        }
    print(json.dumps(result, ensure_ascii=False, indent=1))

    if not args.no_audit:
        try:
            key = "data/dispatch/%s" % result["decision_id"]
            body = json.dumps({"event": e, "primary": result["primary"],
                               "collaborators": [a["id"] for a in assess],
                               "ts": result["ts"]}).encode()
            req = urllib.request.Request(BB + "/" + key, data=body, method="PUT",
                                         headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
            urllib.request.urlopen(req, timeout=5)
            print("\n✅ 决策已沉淀: 黑板 %s" % key)
        except Exception as ex:
            print("\n⚠️ 沉淀失败: %s" % str(ex)[:80])

if __name__ == "__main__":
    main()
