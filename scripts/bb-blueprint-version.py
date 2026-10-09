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
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, ast, re


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
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

def main():
    ap = argparse.ArgumentParser(description="蓝图版本管理+日志管理")
    ap.add_argument("--version-list", action="store_true")
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
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-version {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
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
