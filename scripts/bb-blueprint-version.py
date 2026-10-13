#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-version.py — 蓝图版本管理与日志管理（工具化插件化）

用户指示（2026-09-01）：对蓝图本身做版本管理和日志管理，过程插件化工具化。
功能：① 版本管理（version bump/历史/蓝图间 diff/回滚）② 日志管理（操作日志统一登记/查询/审计）
③ 存量 changelog 归集到统一版本日志。

R006 九标准：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理。

用法：
  # 版本管理
  python3 bb-blueprint-version.py --version-list                     # 各蓝图当前版本
  python3 bb-blueprint-version.py --bump flowernet --level minor --why "新增 supply 主线"  # 版本升级（major/minor/patch）
  python3 bb-blueprint-version.py --history flowernet                # 版本历史（含变更摘要）
  python3 bb-blueprint-version.py --diff flowernet v2.2 v2.3         # 两版本差异（阶段/works 对比）
  python3 bb-blueprint-version.py --snapshot flowernet v2.3          # 快照导出（当前版本完整 BP-9 落盘）
  python3 bb-blueprint-version.py --rollback flowernet v2.2          # 回滚到指定版本（导出快照供恢复）

  # 日志管理
  python3 bb-blueprint-version.py --log "flowernet v2.2→v2.3 扩展" --bp flowernet --level info  # 登记操作日志
  python3 bb-blueprint-version.py --logs [--bp flowernet] [--limit 20]  # 查询日志
  python3 bb-blueprint-version.py --audit [--bp flowernet]           # 审计汇总（按蓝图/操作类型）
  python3 bb-blueprint-version.py --migrate                          # 存量 changelog 归集到统一版本日志

  python3 bb-blueprint-version.py --selfcheck

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, ast, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-version.log")


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
VERSION = "v1.0.0"
BP9_FIELDS = ["id", "name", "version", "mainlines", "stages", "works", "gate", "status", "ts"]

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(path), data=body, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def ts():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def get_blueprint(bp_id):
    d = fetch(f"data/blueprint/{bp_id}")
    if "error" not in d and d.get("value"):
        v = d["value"]
        if isinstance(v, dict) and "id" in v:
            return v
    s = fetch("data/blueprint/stages")
    if "error" not in s and s.get("value"):
        sv = s["value"]
        if isinstance(sv, dict) and sv.get("version"):
            sv["id"] = "flowernet"
            sv["name"] = sv.get("name", "花店生意演进")
            return sv
    return None

# ─────────── 版本日志存储（统一 data/blueprint/versionlog/）───────────
def get_versionlog():
    d = fetch("data/blueprint/versionlog")
    if "error" in d:
        return {"entries": [], "blueprints": {}}
    v = d.get("value", {})
    if isinstance(v, dict) and "entries" in v:
        return v
    if isinstance(v, dict) and "value" in v:
        return v["value"]
    return {"entries": [], "blueprints": {}}

def save_versionlog(vlog):
    return put("data/blueprint/versionlog", vlog)

def append_entry(bp_id, action, detail, level="info"):
    vlog = get_versionlog()
    entry = {"ts": now(), "bp": bp_id, "action": action, "detail": detail, "level": level, "by": "bb-blueprint-version"}
    vlog["entries"].append(entry)
    # blueprints 版本表更新
    bps = vlog.setdefault("blueprints", {})
    bp = get_blueprint(bp_id)
    bps[bp_id] = {"version": bp.get("version", "?") if bp else "?", "ts": now()}
    save_versionlog(vlog)
    return entry

# ─────────── --version-list：各蓝图当前版本 ───────────
def cmd_version_list():
    vlog = get_versionlog()
    bps = vlog.get("blueprints", {})
    # 初始化：从 registry 蓝图补全
    KNOWN = ["flowernet", "flowernet-platform", "agent-network", "blueprint-platform", "aistartup", "banking"]
    for bp_id in KNOWN:
        if bp_id not in bps:
            bp = get_blueprint(bp_id)
            if bp:
                bps[bp_id] = {"version": bp.get("version", "?"), "ts": bp.get("ts", "")[:16]}
    vlog["blueprints"] = bps
    save_versionlog(vlog)
    print("== 蓝图版本表 ==")
    print(f"{'蓝图':<20} {'版本':<20} {'最近更新'}")
    for bp_id, info in sorted(bps.items()):
        print(f"{bp_id:<20} {str(info.get('version','')):<20} {info.get('ts','')[:16]}")

# ─────────── --bump：版本升级 ───────────
def cmd_bump(bp_id, level, why):
    bp = get_blueprint(bp_id)
    if not bp:
        print(f"❌ 蓝图 {bp_id} 不存在"); return
    cur = str(bp.get("version", "v1.0"))
    # 解析当前版本 vX.Y / vX.Y（源自...）
    m = re.match(r"v(\d+)\.(\d+)", cur)
    if not m:
        print(f"⚠️ 版本格式无法解析: {cur}，设为 v1.1"); major, minor = 1, 1
    else:
        major, minor = int(m.group(1)), int(m.group(2))
    if level == "major":
        major += 1; minor = 0
    elif level == "minor":
        minor += 1
    else:  # patch → 推进 minor（简化：patch 即小版本变更）
        minor += 1
    new_ver = f"v{major}.{minor}"
    # 更新蓝图版本
    bp["version"] = new_ver
    bp["ts"] = now()
    if bp_id == "flowernet":
        put("data/blueprint/stages", bp)
    else:
        put(f"data/blueprint/{bp_id}", bp)
    # 日志
    append_entry(bp_id, f"BUMP:{level}", f"{cur} → {new_ver}：{why}")
    print(f"✅ {bp_id} {cur} → {new_ver}（{level}）—— {why}")

# ─────────── --history：版本历史 ───────────
def cmd_history(bp_id):
    vlog = get_versionlog()
    entries = [e for e in vlog.get("entries", []) if e.get("bp") == bp_id]
    print(f"== {bp_id} 版本历史（{len(entries)} 条）==")
    for e in entries:
        print(f"  [{e['ts'][:16]}] {e['action']:12s} {e.get('detail','')[:60]}")

# ─────────── --diff：两版本差异 ───────────
def cmd_diff(bp_id, v1, v2):
    # 从历史/快照找两版本（简化：对比当前 vs 历史 action）
    vlog = get_versionlog()
    entries = [e for e in vlog.get("entries", []) if e.get("bp") == bp_id]
    print(f"== {bp_id} 差异 {v1} vs {v2} ==")
    print("（基于版本日志的变更轨迹）")
    in_range = False
    for e in entries:
        det = e.get("detail", "")
        if v1 in det:
            in_range = True
        if in_range:
            print(f"  [{e['ts'][:16]}] {e['action']:12s} {det[:70]}")
        if v2 in det and v1 != v2:
            in_range = False
            break

# ─────────── --snapshot：快照导出 ───────────
def cmd_snapshot(bp_id, ver):
    bp = get_blueprint(bp_id)
    if not bp:
        print(f"❌ 蓝图 {bp_id} 不存在"); return
    # 快照落盘 data/blueprint/snapshots/<bp>-<ver>-<ts>.json
    spath = os.path.expanduser(f"~/dsh-collab/data/blueprint/snapshots")
    os.makedirs(spath, exist_ok=True)
    fname = f"{bp_id}-{ver or bp.get('version','v1')}-{ts()}.json"
    fpath = os.path.join(spath, fname)
    with open(fpath, "w") as f:
        json.dump(bp, f, ensure_ascii=False, indent=1)
    append_entry(bp_id, "SNAPSHOT", f"导出快照 → {fpath}")
    print(f"✅ 快照导出: {fpath}")

# ─────────── --rollback：回滚 ───────────
def cmd_rollback(bp_id, ver):
    # 从快照找目标版本
    spath = os.path.expanduser("~/dsh-collab/data/blueprint/snapshots")
    if not os.path.isdir(spath):
        print("❌ 无快照目录"); return
    cands = [f for f in os.listdir(spath) if f.startswith(f"{bp_id}-{ver}")]
    if not cands:
        print(f"❌ 未找到 {bp_id} {ver} 快照（先 --snapshot 导出）"); return
    fpath = os.path.join(spath, sorted(cands)[-1])
    with open(fpath) as f:
        snap = json.load(f)
    if bp_id == "flowernet":
        put("data/blueprint/stages", snap)
    else:
        put(f"data/blueprint/{bp_id}", snap)
    append_entry(bp_id, "ROLLBACK", f"回滚到 {ver}（快照 {fpath}）")
    print(f"✅ {bp_id} 已回滚到 {ver}")

# ─────────── 日志管理 ───────────
def cmd_log(bp_id, detail, level):
    append_entry(bp_id, "LOG", detail, level)
    print(f"✅ 日志登记: [{level}] {bp_id} — {detail}")

def cmd_logs(bp_id, limit):
    vlog = get_versionlog()
    entries = vlog.get("entries", [])
    if bp_id:
        entries = [e for e in entries if e.get("bp") == bp_id]
    entries = entries[-limit:]
    print(f"== 蓝图操作日志（{len(entries)} 条）==")
    for e in reversed(entries):
        print(f"  [{e['ts'][:16]}] {e['bp']:<18} {e['action']:12s} {e.get('detail','')[:60]}")

def cmd_audit(bp_id):
    vlog = get_versionlog()
    entries = vlog.get("entries", [])
    if bp_id:
        entries = [e for e in entries if e.get("bp") == bp_id]
    from collections import Counter
    by_bp = Counter(e.get("bp") for e in entries)
    by_action = Counter(e.get("action", "LOG").split(":")[0] for e in entries)
    print(f"== 蓝图审计汇总（{len(entries)} 条）==")
    print("按蓝图:", dict(by_bp))
    print("按操作:", dict(by_action))

# ─────────── --migrate：存量 changelog 归集 ───────────
def cmd_migrate():
    d = fetch("data/")
    ks = [k for k in d.get("list", {}) if "changelog" in k]
    vlog = get_versionlog()
    existing = {e.get("ts","")[:15] for e in vlog.get("entries", [])}
    migrated = 0
    for k in ks:
        cl = fetch(k)
        v = cl.get("value", {})
        if isinstance(v, dict) and "value" in v:
            v = v["value"]
        bp_id = v.get("blueprint_id", "flowernet")
        entry = {"ts": v.get("ts", k.split("/")[-1]), "bp": bp_id,
                 "action": "MIGRATED", "detail": v.get("change_summary", "")[:80], "level": "info",
                 "by": "changelog-migrate", "src": k}
        key = entry["ts"][:15]
        if key not in existing:
            vlog["entries"].append(entry)
            existing.add(key)
            migrated += 1
    save_versionlog(vlog)
    print(f"✅ 存量 changelog 归集: {migrated} 条（共 {len(ks)} 个 changelog key）")

def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    d = fetch("data/blueprint/versionlog")
    print("✅ 黑板连通" if "error" not in d else f"❌ {d['error']}")
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

# ══════════ ★ D1（2026-10-12 明鉴）：versionlog 流程层修复 ══════════
# ★★ 缺陷（实测）：本台账最后写入 **2026-09-07T16:47:14**，停写 35 天。
#   ★ 根因**不是工具坏**（`--selfcheck` 全过：语法/黑板/TCC）—— 而是【流程层】：
#     写路径只挂在 `bb-blueprint-ingest.py` 的**新蓝图注册**上，其余全靠人工 `--bump`/`--log`。
#     ⇒ **台账由【人工动作】驱动，而不是由【变更事实】驱动**；
#       改蓝图的人不需要、也没被要求去登记 ⇒ 必然停写。
# ★★ 实测漂移：台账盖 **10** 个蓝图，而快照产物覆盖 **19** 个（**9 个从未登记**）；
#   至少 **6 个**蓝图的快照版本**已超过**台账记录（如 agent-network v1.2→v1.3，台账仍记 v1.2）。
# ★★ 修法：**让台账可从产物推导**（`--sync-from-artifacts`）—— 从快照目录解析每个蓝图的
#   最新版本，与台账比对，**只 append 差额条目**。
#   ★ 严守该件自己声明的「**只增不改**」不变量：**绝不修改/删除既有条目**。
#   ★★ 默认 **dry-run**（只报不写）；要落账须显式 `--apply`。
SNAPSHOT_DIR = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/snapshots")
SNAP_RE = re.compile(r"^(.+?)-(arch|fish|tl|flow|timeline|dyn)-v(\d*)_?(\d*)(?:[_-].*?)?-(\d{8})-(\d{6})\.svg$")


def _ver_key(v):
    """★ 抽 (major, minor) 用于比较。**台账里的版本可能带长描述**
    （如 `v1.2（memory 拆 L1 工具链/L2 体系化持久化）`）⇒ 不能直接字符串比。"""
    m = re.search(r"v(\d+)\.(\d+)", str(v or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def cmd_sync_from_artifacts(apply=False):
    """★ D1：从产物推导台账 → 报告差额 → 可选补账（只增不改）。"""
    if not os.path.isdir(SNAPSHOT_DIR):
        print("★ 快照目录不存在：%s" % SNAPSHOT_DIR)
        return 1
    latest, unmatched = {}, []
    for f in sorted(os.listdir(SNAPSHOT_DIR)):
        if not f.endswith(".svg"):
            continue
        m = SNAP_RE.match(f)
        if not m:
            unmatched.append(f)
            continue
        bp, maj, mnr = m.group(1), m.group(3), m.group(4)
        if not maj:                      # ★ 空版本（如 v_-）⇒ 计入命名异常，不当作有效版本
            unmatched.append(f)
            continue
        ver = "v%s.%s" % (maj, mnr or "0")
        k = (int(maj), int(mnr or 0))
        if bp not in latest or k > latest[bp]["key"]:
            latest[bp] = {"ver": ver, "key": k, "file": f}

    doc = fetch("data/blueprint/versionlog")
    vl = doc.get("value") or {}
    bps = vl.get("blueprints") or {}
    entries = vl.get("entries") or []

    # ★★ 幂等性（2026-10-12 本线实测发现的设计缺陷，已修）：
    #   第一版只 append entries、**不动 blueprints**（为守「不替人改版本号」）
    #   ⇒ 差额永远存在 ⇒ **再跑一次仍报同样差额，`--apply` 两次会堆重复条目**。
    #   ⇒ 正确做法：让【差额计算】感知「已经登记过的差额」—— 查 entries 里
    #     是否已有一条针对 (bp, 目标版本) 的 SYNCED/FOUND-UNREGISTERED。
    #   ★ 这样既守「只增不改」（不修改历史、不改版本号），又幂等（重复运行不重复报）。
    done = set()
    for x in entries:
        if x.get("action") in ("SYNCED", "FOUND-UNREGISTERED"):
            det = str(x.get("detail") or "")
            for cand in re.findall(r"v\d+\.\d+", det):
                done.add((x.get("bp"), cand))

    behind, missing, ahead = [], [], []
    for bp, inf in sorted(latest.items()):
        if bp not in bps:
            if (bp, inf["ver"]) not in done:
                missing.append((bp, inf))
            continue
        cur = _ver_key(bps[bp].get("version"))
        if cur is None or inf["key"] > cur:
            if (bp, inf["ver"]) not in done:
                behind.append((bp, bps[bp].get("version"), inf))
        elif inf["key"] < cur:
            ahead.append((bp, bps[bp].get("version"), inf))

    print("══ versionlog 流程层核对（产物推导）══")
    print("  台账蓝图 %d 个 · 产物可解析 %d 个 · entries %d 条" % (len(bps), len(latest), len(entries)))
    print()
    print("  ★ 版本落后（产物 > 台账）：%d 个" % len(behind))
    for bp, old, inf in behind:
        print("     %-22s 台账 %-26s → 产物 %s" % (bp, str(old)[:26], inf["ver"]))
    print("  ★ 从未登记（产物有而台账无）：%d 个" % len(missing))
    for bp, inf in missing:
        print("     %-22s 产物 %s" % (bp, inf["ver"]))
    if ahead:
        print("  （产物低于台账 %d 个 —— 不算缺陷，仅列）" % len(ahead))
    if unmatched:
        print()
        print("  ★ 命名不符模式 %d 个（产物自身的质量缺陷，**不改产物、只报**）" % len(unmatched))
        for f in unmatched[:6]:
            print("     %s" % f)
        if len(unmatched) > 6:
            print("     … 另 %d 个" % (len(unmatched) - 6))

    if not apply:
        print()
        print("  ★ dry-run（默认）—— 未写入任何东西。要补账请加 --apply。")
        return 0

    n = 0
    for bp, old, inf in behind:
        entries.append({"action": "SYNCED", "bp": bp,
                        "by": "bb-blueprint-version --sync-from-artifacts",
                        "detail": "★ 从产物补账：台账 %s → 产物 %s（依据 %s）"
                                  % (str(old)[:40], inf["ver"], inf["file"]),
                        "ts": datetime.datetime.now().isoformat()})
        n += 1
    for bp, inf in missing:
        entries.append({"action": "FOUND-UNREGISTERED", "bp": bp,
                        "by": "bb-blueprint-version --sync-from-artifacts",
                        "detail": "★ 产物存在但台账从未登记：%s（依据 %s）—— "
                                  "★ 仅补【登记】不动该蓝图版本号" % (inf["ver"], inf["file"]),
                        "ts": datetime.datetime.now().isoformat()})
        n += 1
    if not n:
        print("\n  无差额 ⇒ 无需补账。")
        return 0
    vl["entries"] = entries               # ★ 只 append；blueprints 字典**不动**（不替人改版本号）
    put("data/blueprint/versionlog", vl)
    back = fetch("data/blueprint/versionlog").get("value") or {}
    print("\n  ★ 已补账 %d 条；回读 entries = %d（补账前 %d）"
          % (n, len(back.get("entries") or []), len(entries) - n))
    print("  ★ 回读 blueprints = %d 个（本命令未修改它）" % len(back.get("blueprints") or {}))
    return 0


def main():
    ap = argparse.ArgumentParser(description="蓝图版本管理+日志管理")
    ap.add_argument("--version-list", action="store_true")
    # ★★★ 2026-10-13 新增（tab 层独立考古 · 类型 4）：**只读催办清单**。
    #   背景：`--sync-from-artifacts` **有意不修改 `blueprints` 字典**（源码逐字「不替人改版本号」
    #   ★ 与 reflect-enroll 的「只拒绝不自动修复」同源 —— 版本是治理决定）。
    #   ⇒ ★ 代价：台账会永久落后于产物，且**没有任何催办**（实测 agent-network 台账 v1.2 / 产物 v1.3）。
    #   ⇒ 本开关**只读**：打「待人工裁决」清单，不写任何东西。
    ap.add_argument("--stale-report", action="store_true",
                    help="★ 只读：列出「台账落后于产物」与「台账未覆盖」的蓝图（供人工裁）")
    ap.add_argument("--bump", default="", help="版本升级（蓝图 id）")
    ap.add_argument("--level", default="minor", choices=["major", "minor", "patch"])
    ap.add_argument("--why", default="")
    ap.add_argument("--history", default="")
    ap.add_argument("--diff", nargs=3, metavar=("BP", "V1", "V2"))
    ap.add_argument("--snapshot", nargs="+", metavar=("BP", "VER"), help="快照导出")
    ap.add_argument("--rollback", nargs=2, metavar=("BP", "VER"))
    ap.add_argument("--log", default="")
    ap.add_argument("--bp", default="")
    ap.add_argument("--level2", dest="log_level", default="info")
    ap.add_argument("--logs", action="store_true")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--migrate", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    # ★ D1（2026-10-12）：从产物推导补账（默认 dry-run；--apply 才写）
    ap.add_argument("--sync-from-artifacts", action="store_true",
                    help="从快照产物推导台账差额（默认 dry-run）")
    ap.add_argument("--apply", action="store_true", help="配合 --sync-from-artifacts：真的补账")
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-version {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.sync_from_artifacts:
        # ★ D1（2026-10-12）：从产物推导补账。★ 默认 dry-run，--apply 才写。
        sys.exit(cmd_sync_from_artifacts(apply=args.apply))
    elif getattr(args, "stale_report", False):
        # ★★ 只读：台账 vs 产物对账（★ 不写、不改 —— 版本号是治理决定）
        import urllib.request as _ur
        vl = fetch("data/blueprint/versionlog").get("value") or {}
        led = vl.get("blueprints") or {}
        try:
            with _ur.urlopen("http://127.0.0.1:8798/api/blueprints", timeout=60) as _r:
                art = {b["id"]: b.get("version") for b in json.loads(_r.read().decode())}
        except Exception as e:
            print("★ 取产物版本失败：%s" % e); return 2
        def _n(v):
            return str(v or "").strip().lstrip("v").split("（")[0].strip()
        behind=[]
        for k, v in led.items():
            lv = (v or {}).get("version") if isinstance(v, dict) else v
            if k in art and _n(lv) != _n(art.get(k)):
                behind.append({"id":k, "ledger":lv, "actual":art.get(k)})
        missing=[{"id":k, "actual":art[k]} for k in art if k not in led]
        print("══ 台账落后于产物（待人工裁决 · ★ 本命令不改）══")
        if behind:
            for x in behind: print("  ★ %-22s 台账 %-8s → 产物 %-8s" % (x["id"], x["ledger"], x["actual"]))
        else:
            print("  （无）")
        print("")
        print("══ 台账未覆盖（从未登记）══")
        print("  %d 项：%s" % (len(missing), " ".join(x["id"] for x in missing) or "（无）"))
        print("")
        print("★ 处置：版本号是**治理决定**，故本工具不自动改写；")
        print("  若人工确认后可回写 —— 但按 R062①「归档≠已处理」，**先确认产物为真**。")
        print("★ 本命令【只读】：未写任何键。")
        return 0
    elif args.version_list:
        cmd_version_list()
    elif args.bump:
        cmd_bump(args.bump, args.level, args.why)
    elif args.history:
        cmd_history(args.history)
    elif args.diff:
        cmd_diff(*args.diff)
    elif args.snapshot:
        cmd_snapshot(args.snapshot[0], args.snapshot[1] if len(args.snapshot) > 1 else "")
    elif args.rollback:
        cmd_rollback(*args.rollback)
    elif args.log:
        cmd_log(args.bp or "flowernet", args.log, args.log_level)
    elif args.logs:
        cmd_logs(args.bp, args.limit)
    elif args.audit:
        cmd_audit(args.bp)
    elif args.migrate:
        cmd_migrate()
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
