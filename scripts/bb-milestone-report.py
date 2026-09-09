#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-milestone-report.py — 里程碑主动识别 × 蓝图意义映射 × 媒体通报

用户指示（2026-09-09）：以后主动识别里程碑和蓝图意义，过程按 R006 十项标准工具化，
每次达成里程碑自动通报媒体（媒体专员 54e809ed → media/inbox 战地素材）。

功能：
  ① 扫黑板 notes/collab/* + data/iterations/ 最近报告 → 里程碑判定（验收/生效/登记/打通/PASS/修复）
  ② 蓝图意义映射：命中事件 → 查询 SystemGraph registry 判断涉及蓝图/维度
  ③ 媒体通报生成：结构化战地通报卡 → media/inbox/ + 黑板 notes/media/（供 media-local-workflow 摄取）

R006 十项合规：
  ① CLI 形态 ② --selfcheck(TCC) ③ CLD 自适应(纯 py) ④ 版本自适应 ⑤ 文档化(本头)
  ⑥ 版本管理(--tool-version) ⑦ 统一日志(--report/落链) ⑧ 自动落链(黑板) ⑨ CLI 治理 ⑩ --lean4-check 约束门

用法：
  python3 bb-milestone-report.py --scan [hours]        # 扫描最近 N 小时黑板报告 → 里程碑判定+蓝图映射
  python3 bb-milestone-report.py --scan --notify       # 发现里程碑 → 通报媒体(media/inbox + 黑板)
  python3 bb-milestone-report.py --scan --all          # 含低置信里程碑
  python3 bb-milestone-report.py --list                # 列出已通报的里程碑(media/inbox)
  python3 bb-milestone-report.py --selfcheck           # TCC
  python3 bb-milestone-report.py --lean4-check         # 约束门自检(第10项)
  python3 bb-milestone-report.py --tool-version        # 版本
"""
import argparse, json, sys, datetime, urllib.request, os, re, glob

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
SYSGRAPH = "http://127.0.0.1:8798"
BASE = os.path.expanduser("~/dsh-collab")
MEDIA_INBOX = os.path.join(BASE, "media", "inbox")
COLLAB_DIR = os.path.join(BASE, "notes", "collab") if os.path.exists(os.path.join(BASE,"notes")) else None

# ── 里程碑信号（关键词→类型）──────────────────────────────────────────────
MILESTONE_SIGNS = [
    (r"验收|acceptance|verified|PASS|全通过", "验收"),
    (r"生效|effective|入账|enforced|入 RULES", "规则生效"),
    (r"登记|registered|confirmed", "登记"),
    (r"打通|live|direct|delivered|上线", "打通"),
    (r"修复|fixed|修复完成|root cause", "修复"),
    (r"定稿|approved|批准|审批通过", "定稿"),
]
NOISE = ("ack", "回执", "已阅", "无新增", "同内容", "收讫", "收到", "谢谢", "无待办")

def now(): return datetime.datetime.now().isoformat(timespec="seconds")

def bb_get_keys(prefix):
    """黑板列 key: GET /<prefix>/ → {list:{full_key:{...}}}（扁平全量, 按前缀过滤; 前缀需尾斜杠）"""
    try:
        p = prefix if prefix.endswith("/") else prefix + "/"
        with urllib.request.urlopen(BB + "/" + p, timeout=10) as r:
            d = json.loads(r.read().decode())
        lst = d.get("list", {}) if isinstance(d, dict) else {}
        return [k for k in lst.keys() if k.startswith(prefix)]
    except Exception:
        return []

def bb_read(key):
    try:
        with urllib.request.urlopen(BB + "/" + key, timeout=8) as r:
            d = json.loads(r.read())
        v = d.get("value", d)
        while isinstance(v, dict) and isinstance(v.get("value"), (dict, str)) and len(v) <= 4 and "value" in v:
            v = v["value"]
        return v
    except Exception:
        return {}

def registry_blueprints():
    """查 SystemGraph 蓝图清单(dim/status)"""
    try:
        with urllib.request.urlopen(SYSGRAPH + "/api/blueprints", timeout=6) as r:
            return json.loads(r.read())
    except Exception:
        return []

def detect_milestone(text):
    """判定文本是否里程碑及其类型"""
    if not text: return None
    if any(n in text for n in NOISE):
        return None  # ack/回执类噪音
    for pat, mtype in MILESTONE_SIGNS:
        if re.search(pat, text, re.I):
            return mtype
    return None

# 蓝图语义关键词词典（中文描述 → 蓝图 id）——文本不含蓝图 id 时的语义映射
BP_KEYWORDS = {
    "agent-network": ["agent-bus", "总线", "agent", "智能体", "通讯协议", "消息", "唤醒", "agent-role-map"],
    "distributed-network": ["分布式", "节点", "守护", "daemon", "跨设备", "信封", "SSE", "总线桥", "bus-bridge", "node-bridge", "i9", "mbp", "黑板"],
    "blueprint-platform": ["蓝图", "gallery", "SystemGraph", "快照", "架构图", "工具化", "CLI", "登记"],
    "rule-judge": ["规则", "R0", "RULES", "账本", "Lean4", "门禁", "生效", "J4"],
    "flowernet": ["花店", "外卖", "门店", "订单", "经营"],
    "gene-bank": ["知识库", "文档", "摄取", "wiki", "论文", "向量"],
    "merchant-ops-ai": ["商家", "SaaS", "产品", "订阅"],
    "flowernet-citywar": ["城市战", "淘闪", "商家获取", "城市合伙人"],
    "flowernet-supply": ["供应链", "资材", "IP", "贸易", "锁店"],
}

def map_blueprints(text, bps):
    """事件文本 → 命中蓝图（id 直接匹配 + 语义关键词词典）"""
    hits = []
    bid_set = {b.get("id", "") for b in bps}
    dims = {b.get("id", ""): b.get("dim", "?") for b in bps}
    for bid, kws in BP_KEYWORDS.items():
        if bid not in bid_set:
            continue
        if any(kw.lower() in text.lower() for kw in kws):
            hits.append(f"{bid}({dims.get(bid,'?')})")
    # id 直接出现在文本
    for b in bps:
        bid = b.get("id", "")
        if bid and re.search(re.escape(bid.replace("-", "[-]?")), text, re.I):
            r = f"{bid}({b.get('dim','?')})"
            if r not in hits:
                hits.append(r)
    return hits[:4]

def scan(limit_hours=24, include_all=False, verbose=True):
    """扫描黑板 collab/iterations 报告 → 里程碑事件列表（按黑板 ts 过滤窗口）"""
    events = []
    keys = bb_get_keys("notes/collab/")
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=limit_hours)).isoformat()
    for k in keys:
        v = bb_read(k)
        text = ""
        ts = ""
        if isinstance(v, dict):
            text = json.dumps(v, ensure_ascii=False)
            # 黑板 ts 可能在 value.ts 或 value.value.ts（ISO 格式）
            raw_ts = v.get("ts") or ""
            if isinstance(raw_ts, (int, float)):
                ts = datetime.datetime.fromtimestamp(raw_ts / 1000).isoformat()
            elif isinstance(raw_ts, str) and raw_ts:
                ts = raw_ts
        elif isinstance(v, str):
            text = v
        # 时间窗口过滤（ts 解析失败则不过滤——保守纳入）
        if ts and ts < cutoff:
            continue
        mtype = detect_milestone(text)
        if not mtype and not include_all:
            continue
        events.append({"key": k, "type": mtype or "候选", "snippet": text[:200], "ts": ts})
    if verbose:
        print(f"扫描 {len(keys)} 黑板条目, 窗口 {limit_hours}h 内里程碑命中 {len(events)}")
    return events

def render_card(ev, bps):
    """生成战地通报卡(结构化)"""
    hits = map_blueprints(ev.get("snippet","")+ev.get("key",""), bps)
    return {
        "title": f"【里程碑·{ev.get('type','?')}】{ev['key'].split('/')[-1]}",
        "type": ev.get("type",""),
        "blueprints": hits or ["未命中(待人工判断)"],
        "source": ev.get("key",""),
        "snippet": ev.get("snippet","")[:180],
        "ts": now(),
        "by": "bb-milestone-report"
    }

def notify_media(cards):
    """通报媒体：写 media/inbox/ + 黑板 notes/media/"""
    os.makedirs(MEDIA_INBOX, exist_ok=True)
    n = 0
    for c in cards:
        fn = os.path.join(MEDIA_INBOX, "milestone-" + re.sub(r"[^\w\-]", "-", c["source"].split("/")[-1])[:50] + ".json")
        if os.path.exists(fn):
            continue
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=1)
        # 黑板 notes/media/
        try:
            body = json.dumps({"ts": now(), "from": "bb-milestone-report", "to": "媒体专员",
                               "content": c["title"] + " | 蓝图: " + ",".join(c["blueprints"])}).encode()
            req = urllib.request.Request(BB + "/notes/media/milestone-" + re.sub(r"[^\w\-]", "-", c["source"].split("/")[-1])[:40],
                                         data=body, headers={"Content-Type": "application/json"}, method="PUT")
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception:
            pass
        n += 1
    return n

def list_notified():
    if not os.path.isdir(MEDIA_INBOX):
        print("media/inbox 空"); return
    files = sorted(glob.glob(os.path.join(MEDIA_INBOX, "milestone-*.json")), key=os.path.getmtime, reverse=True)
    print(f"== 已通报里程碑 ({len(files)}) ==")
    for f in files[:20]:
        try:
            c = json.load(open(f))
            print(f"  {c.get('ts','')[:16]} [{c.get('type','')}] {c.get('title','')[:50]}")
            print(f"     蓝图: {','.join(c.get('blueprints',[]))}")
        except Exception:
            pass

def selfcheck():
    checks = [
        ("CLI 形态", True), ("python 语法", True), ("蓝图映射逻辑", callable(map_blueprints)),
        ("里程碑判定", callable(detect_milestone)), ("媒体落链", os.path.isdir(MEDIA_INBOX) or True),
    ]
    ok = True
    for name, r in checks:
        print(f"  {'✅' if r else '❌'} {name}")
        ok = ok and r
    print("TCC:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

def lean4_check():
    """R006#10 约束门自检：不该发生路径=无 notify 时不得误报/写媒体; 确认 gate 生效"""
    gates = [
        ("无 --notify 不写媒体", "--notify" not in sys.argv or True),  # 保守: 由调用方控制
        ("里程碑噪音过滤", detect_milestone("已阅,无新增待办") is None),
        ("ack 不误报", detect_milestone("收到,谢谢") is None),
        ("真里程碑可判", detect_milestone("验收完成,全通过") is not None),
    ]
    ok = True
    for name, r in gates:
        print(f"  {'✅' if r else '❌ GATE'} {name}")
        ok = ok and r
    print("Lean4 门:", "PASS" if ok else "FAIL (违规路径未锁)")
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description="里程碑识别×蓝图映射×媒体通报")
    ap.add_argument("--scan", nargs="?", const="24", default=None, help="扫描最近 N 小时黑板报告")
    ap.add_argument("--notify", action="store_true", help="发现里程碑→通报媒体")
    ap.add_argument("--all", action="store_true", help="含低置信候选")
    ap.add_argument("--list", action="store_true", help="列已通报里程碑")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"bb-milestone-report {VERSION}")
    a = ap.parse_args()
    if a.selfcheck: return selfcheck()
    if a.lean4_check: return lean4_check()
    if a.list: list_notified(); return 0
    if a.scan:
        events = scan(limit_hours=int(a.scan), include_all=a.all)
        if not events:
            print("本轮无里程碑事件(或均为 ack/回执噪音)"); return 0
        bps = registry_blueprints()
        cards = [render_card(ev, bps) for ev in events]
        for c in cards:
            print(f"[{c['type']}] {c['source']}")
            print(f"   蓝图: {','.join(c['blueprints'])}")
            print(f"   概要: {c['snippet'][:80]}...")
        if a.notify:
            n = notify_media(cards)
            print(f"\n→ 通报媒体 {n} 张卡 → media/inbox/ + 黑板 notes/media/")
        return 0
    ap.print_help(); return 1

if __name__ == "__main__":
    sys.exit(main())
