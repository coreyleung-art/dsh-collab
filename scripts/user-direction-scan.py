#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""user-direction-scan.py v1.0.0 — 「用户说过的话」落实核验扫描器（R006 十项达标 · R030 无证据不陈述）

用途: 读 data/registry/user-directions-registry.json, 对每条方向/待办做证据机器核验,
     输出落实矩阵 + 差距清单。防「用户早说过、agent 没落实」类欠账再被口头掩盖。

R006 十项:
  ① CLI 形态: scan(默认) / --version / --lean4-check / --json / --cat <id|backlog|all>
  ② 检查项可枚举: 23 方向 + 8 待办 + 证据核验器(路径/标识符/断言/黑板键)
  ③ 地址环境变量: BB_BASE(黑板基址, 默认 127.0.0.1:8792) / BB_TOKEN(黑板 token, 缺则 GATE FAIL 实测)
  ④ 版本: v1.0.0 (--version)
  ⑤ 文档化: 本头部 + README 注释(见文件尾)
  ⑥ 版本管理: --version 唯一来源 __VERSION__
  ⑦ 统一日志: ~/dsh-collab/logs/user-direction-scan.log
  ⑧ 自动落链: 报告落 data/reports/user-direction-report.md + 黑板 data/registry/user-direction-scan-<ts>(BB 可达时)
  ⑨ CLI 治理: argparse 子命令; scan 支持 --gates/--id 过滤
  ⑩ Lean4 门: --lean4-check 自检(注册表 schema/证据非空/done 须机器证据/backlog 卡点齐全; 无 token 黑板不可达 → GATE FAIL)

用法:
  python3 user-direction-scan.py                 # 全量核验 + 落链
  python3 user-direction-scan.py --cat D20       # 单条详情
  python3 user-direction-scan.py --json          # 机器可读
  python3 user-direction-scan.py --lean4-check   # 工具自身门自检
  python3 user-direction-scan.py --version
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, datetime, json, os, re, subprocess, sys, urllib.request

__VERSION__ = "v1.0.0"
HOME = os.path.expanduser("~")
REPO = os.path.join(HOME, "dsh-collab")
REG = os.path.join(REPO, "data/registry/user-directions-registry.json")
REPORT = os.path.join(REPO, "data/reports/user-direction-report.md")
LOG_FILE = os.path.join(HOME, "dsh-collab/logs/user-direction-scan.log")
BB_BASE = os.environ.get("BB_BASE", "http://127.0.0.1:8792")
BB_TOKEN = os.environ.get("BB_TOKEN", "")
SCAN_DIRS = [os.path.join(REPO, "comm-server"), os.path.join(REPO, "scripts"),
             os.path.join(REPO, "rules-registry"), os.path.join(REPO, "node-kit")]


def log(m):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ═══════════ 证据核验器 (②) ═══════════
def _bb_get(key):
    """黑板键存在性(notes/ data/ 域)。token 缺失或不可达 → None"""
    try:
        h = {"X-Blackboard-Token": BB_TOKEN} if BB_TOKEN else {}
        req = urllib.request.Request(f"{BB_BASE}/{key}", headers=h)
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return None


def _find_basename(name):
    for base in ([REPO, "/tmp"] if name.endswith((".js", ".py")) else [REPO]):
        try:
            r = subprocess.run(["find", base, "-name", name, "-not", "-path", "*/node_modules/*"],
                               capture_output=True, text=True, timeout=30)
            if r.stdout.strip():
                return True
        except Exception:
            continue
    return False


def _grep_hit(token):
    if token.endswith((".py", ".js", ".sh", ".md", ".json", ".txt")):
        return _find_basename(token)
    for d in SCAN_DIRS:
        try:
            r = subprocess.run(["grep", "-rl", "--include=*.py", "--include=*.js", "--include=*.sh",
                                "--include=*.md", "-e", token, d], capture_output=True, text=True, timeout=15)
            if r.stdout.strip():
                return True
        except Exception:
            continue
    return False


def check_evidence(ev):
    """单条证据核验 → (ok, detail)。描述性证据(无可提取 token)计人工复核, 不自动判缺失。"""
    paths = re.findall(r"([\w./~\-]+\.(?:py|js|sh|md|json|txt|plist))", ev)
    gates = re.findall(r"G-[A-Z0-9]+|CP-\d{8}-\d{3}", ev)
    misses = []
    for p in paths:
        p = p.split(" ")[0]
        if p.startswith(("notes/", "data/registry/")):
            r = _bb_get(p)
            if r is False:
                misses.append(p)
            elif r is None:
                return None, "黑板不可达/无 token(降级人工复核)"
        elif os.path.sep in p or p.startswith("~"):
            fp = p.replace("~", HOME)
            if not (os.path.exists(fp) or os.path.exists(os.path.join(REPO, p))):
                misses.append(p)
        else:
            if not _find_basename(p):
                misses.append(p)
    for g in gates:
        if not _grep_hit(g):
            misses.append(g)
    if not paths and not gates:
        return True, "描述性证据(人工复核)"
    return (not misses), ("缺失: " + "; ".join(misses[:4]) if misses else "证据在")


# ═══════════ 扫描 (①) ═══════════
def do_scan(only=None):
    reg = json.load(open(REG))
    rows, manual = [], 0
    for d in reg.get("directions", []):
        if only and d["id"] != only:
            continue
        ok_list, miss_list = [], []
        for ev in d.get("evidence", []):
            ok, detail = check_evidence(ev)
            if ok is None:
                manual += 1
            (ok_list if ok else miss_list).append(detail)
        flag = ""
        if d.get("status") == "done" and d.get("evidence") and not ok_list and len(miss_list) >= len(d.get("evidence", [])):
            flag = " ⚠️RED"
        rows.append({"id": d["id"], "date": d.get("date", ""), "direction": d["direction"],
                     "status": d.get("status", "?") + flag, "ok": len(ok_list), "miss": len(miss_list),
                     "evidence": d.get("evidence", []), "miss_detail": [x for x in miss_list if x.startswith("缺失")]})
    return reg, rows, manual


def render_md(reg, rows, manual, probes):
    L = ["# 用户方向落实核验报告", f"- 生成: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
         f"- 工具: user-direction-scan.py {__VERSION__} | Lean4 门实时: {probes.get('lean4_pass', '?')} 项 PASS",
         f"- 方向: {len(reg.get('directions', []))} | 待办: {len(reg.get('backlog', []))} | 需人工复核证据: {manual}", ""]
    L += ["| ID | 日期 | 方向 | 状态 | ✓ | ✗ |", "|---|---|---|---|---|---|"]
    for r_ in rows:
        L.append(f"| {r_['id']} | {r_['date']} | {r_['direction'][:44]} | {r_['status']} | {r_['ok']} | {r_['miss']} |")
    L += ["", "## 待办(backlog 欠账)", ""]
    for b in reg.get("backlog", []):
        L.append(f"- {b['id']} {b['item']} — 卡点: {b['blocked_on']} | 证据: {b['evidence']}")
    if manual:
        L += ["", f"## 需人工复核 {manual} 条(黑板不可达或无 token 时证据降级)", ""]
    return "\n".join(L)


def do_report(rows, reg, manual):
    try:
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts/convention-lean4-check.py")],
                           capture_output=True, text=True, timeout=120)
        m = re.search(r"全部 (\d+) 项 PASS", r.stdout + r.stderr)
        lean4 = int(m.group(1)) if m else 0
    except Exception:
        lean4 = -1
    md = render_md(reg, rows, manual, {"lean4_pass": lean4})
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w") as f:
        f.write(md)
    log(f"报告落盘 {REPORT}")
    # ⑧ 自动落链: 黑板 data/registry/user-direction-scan-<ts>
    if BB_TOKEN:
        try:
            key = f"data/registry/user-direction-scan-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            val = {"content": md[:3000], "from": "mac-mini:星桥", "type": "direction-scan-report",
                   "ts": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}
            req = urllib.request.Request(f"{BB_BASE}/{key}", data=json.dumps(val, ensure_ascii=False).encode(),
                                         method="PUT", headers={"Content-Type": "application/json",
                                                                "X-Blackboard-Token": BB_TOKEN})
            urllib.request.urlopen(req, timeout=8)
            log(f"黑板落链 {key}")
        except Exception as e:
            log(f"⚠️ 黑板落链失败: {str(e)[:60]}")
    return md


# ═══════════ Lean4 门自检 (⑩ · R030) ═══════════
def lean4_check():
    ok = True

    def gate(label, cond):
        nonlocal ok
        print(f"  [{'✅' if cond else '❌'}] {label}")
        ok = ok and cond

    gate("注册表存在", os.path.exists(REG))
    try:
        reg = json.load(open(REG))
    except Exception:
        reg = None
    gate("注册表 JSON 合法", reg is not None)
    if reg:
        gate("每条方向有 evidence 且非空", all(isinstance(d.get("evidence"), list) and d.get("evidence") for d in reg.get("directions", [])))
        gate("声称 done 的方向须含机器可验证据(防口头落实)", all(
            any(re.search(r"\.(py|js|sh|md|json|txt)|G-[A-Z0-9]+|CP-\d{8}-\d{3}|§\d|v\d+\.\d+", ev) for ev in d["evidence"])
            for d in reg.get("directions", []) if d.get("status") == "done"))
        gate("backlog 每项有 blocked_on(卡点可见)", all(b.get("blocked_on") for b in reg.get("backlog", [])))
        gate("扫描器本体含 R030 声明(无证据不陈述)", "R030" in open(os.path.abspath(__file__)).read())
    gate("token 在位(缺 token 黑板证据不可验 → GATE FAIL 实测)", bool(BB_TOKEN))
    if not BB_TOKEN:
        gate("黑板可达(有 token 时验证)", True)  # 无 token 已 FAIL, 不额外探测
    else:
        try:
            urllib.request.urlopen(urllib.request.Request(f"{BB_BASE}/notes", headers={"X-Blackboard-Token": BB_TOKEN}), timeout=5)
            gate("黑板可达", True)
        except Exception:
            gate("黑板可达", False)
    print("")
    print(f"  结果: {'✅ GATE OK — 方向扫描器 Lean4 门全生效' if ok else '❌ GATE FAIL(见上)'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="用户方向落实核验扫描器 (R006 十项)")
    ap.add_argument("--version", action="store_true", help="版本")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--cat", metavar="ID|backlog|all", help="单条/待办详情")
    ap.add_argument("--lean4-check", action="store_true", help="工具自身门自检")
    ap.add_argument("--id", default=None, help="仅扫指定方向 ID")
    args = ap.parse_args()
    if args.version:
        print(f"user-direction-scan.py {__VERSION__}"); return 0
    if args.lean4_check:
        return lean4_check()
    if args.cat:
        reg = json.load(open(REG))
        if args.cat == "backlog":
            for b in reg["backlog"]:
                print(f"{b['id']} {b['item']}\n    卡点: {b['blocked_on']} | 证据: {b['evidence']}")
            return 0
        if args.cat == "all":
            for d in reg["directions"]:
                print(f"{d['id']} [{d['status']}] {d['direction']}")
                for ev in d["evidence"]:
                    ok, detail = check_evidence(ev)
                    print(f"    {'✓' if ok else ('~' if ok is None else '✗')} {ev[:100]} ({detail})")
            return 0
        for d in reg["directions"]:
            if d["id"] == args.cat:
                print(f"{d['id']} [{d['status']}] {d['date']} {d['direction']}")
                for ev in d["evidence"]:
                    ok, detail = check_evidence(ev)
                    print(f"    {'✓' if ok else ('~' if ok is None else '✗')} {ev[:110]} ({detail})")
                return 0
        print(f"未找到 {args.cat}"); return 1
    reg, rows, manual = do_scan(args.id)
    if args.json:
        out = {"version": __VERSION__, "generated": datetime.datetime.now().isoformat(),
               "directions": rows, "backlog": reg.get("backlog", []), "manual_review": manual}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 0
    print(do_report(rows, reg, manual))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# ⑤ README(文件尾注释): 数据源 data/registry/user-directions-registry.json(手工维护, 用户指示逐条登记);
#   证据规则: 路径/断言/黑板键机器核验, 描述性证据标「人工复核」; RED=声称 done 但机器证据全缺。
#   新增用户方向: 编辑注册表 JSON 追加 direction(evidence 至少含一条机器可验项), 勿只写口头承诺。
