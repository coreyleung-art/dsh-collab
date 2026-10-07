#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-upgrade.py — 底座升级流水线（进化循环第 2 步，半自动）

标准化底座升级流程：版本递增 → 注入变更 → 语法检查 → 起测试实例 → 冒烟测试 →
切换 plist → 验证生产 → 落链（黑板+registry）→ 复用评估（自动调 bb-reuse-check）。

用法：
  python3 bb-upgrade.py --from v0.5 --to v0.6 --script scripts/blackboard-server-v0.6.py
                         --what "新增能力描述" --deps "依赖" --hub-dep "中枢依赖" --node-side "节点侧"
  python3 bb-upgrade.py --dry-run --from v0.5 --to v0.6 --script <path>   # 只跑到测试

流程步骤（每步打印 + 可选 --dry-run 截断）：
  1. 语法检查 py_compile
  2. 起测试实例（随机端口 879x + 独立 data-dir）
  3. 冒烟测试集：/clock /timeline /subs /help /ns-registry PUT/DELETE
  4. （非 dry-run）切 plist + launchctl 重启
  5. （非 dry-run）验证生产 /clock
  6. 复用评估（调 bb-reuse-check.py）
  7. 落链登记黑板 data/iterations/
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, subprocess, sys, time, datetime, random, urllib.request

BB = "http://127.0.0.1:8792"
PLIST = os.path.expanduser("~/Library/LaunchAgents/com.dsh.hr.blackboard-server.plist")
SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
GENEBANK = os.path.join(SCRIPTS, "genebank-server.py")
REUSE = os.path.join(SCRIPTS, "bb-reuse-check.py")

SMOKE_TESTS = [
    ("GET", "/clock", "clock"),
    ("GET", "/timeline?limit=2", "timeline"),
    ("GET", "/subs", "subs"),
    ("GET", "/help", "help"),
    ("GET", "/ns-registry", "ns-registry"),
]

def run(cmd, timeout=30):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def http(method, url, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            return r.status, json.loads(r.read().decode())
    except Exception as e:
        return 0, {"error": str(e)[:100]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="vfrom", required=True)
    ap.add_argument("--to", dest="vto", required=True)
    ap.add_argument("--script", required=True, help="新版本脚本路径")
    ap.add_argument("--what", required=True, help="变更描述")
    ap.add_argument("--deps", default="", help="依赖")
    ap.add_argument("--hub-dep", default="无", help="中枢依赖")
    ap.add_argument("--node-side", default="", help="节点侧情况")
    ap.add_argument("--dry-run", action="store_true", help="只跑到测试，不切生产")
    args = ap.parse_args()

    script_path = args.script if os.path.isabs(args.script) else os.path.join(SCRIPTS, args.script)
    port = 8790 + random.randint(1, 90)  # 8791-8880 测试端口
    testdir = "/tmp/bb-upgrade-test-%s" % args.vto

    print("== 底座升级流水线 %s → %s ==" % (args.vfrom, args.vto))
    print("脚本: %s | 变更: %s" % (script_path, args.what))

    # 1. 语法检查
    print("\n[1/7] 语法检查...")
    rc, out = run("python3 -m py_compile %s" % script_path)
    if rc != 0:
        print("❌ 语法错误:\n%s" % out); sys.exit(1)
    print("✅ 语法通过")

    # 2. 起测试实例
    print("[2/7] 起测试实例 :%d (data=%s)..." % (port, testdir))
    run("rm -rf %s && mkdir -p %s" % (testdir, testdir))
    rc, out = run("nohup python3 %s --port %d --data-dir %s > /tmp/bb-upgrade-%s.log 2>&1 & echo $!"
                  % (script_path, port, testdir, args.vto))
    pid = out.strip().split()[-1] if out.strip() else "?"
    time.sleep(1.5)

    # 3. 冒烟测试集
    print("[3/7] 冒烟测试集...")
    failed = []
    for method, path, name in SMOKE_TESTS:
        st, data = http(method, "http://127.0.0.1:%d%s" % (port, path))
        ok = st == 200 and "error" not in data
        print("  %s %s → %s" % ("✅" if ok else "❌", name, st))
        if not ok: failed.append(name)
    # PUT/DELETE 冒烟
    st, data = http("PUT", "http://127.0.0.1:%d/smoke/upgrade" % port, {"t": 1})
    ok = st == 200 and data.get("seq")
    print("  %s PUT 带seq → %s" % ("✅" if ok else "❌", st))
    if not ok: failed.append("PUT")
    run("kill %s 2>/dev/null" % pid)
    if failed:
        print("❌ 冒烟失败: %s" % failed); sys.exit(1)
    print("✅ 冒烟全过")

    if args.dry_run:
        print("\n(dry-run 模式：不切生产、不落链)")
        print("✅ 流水线验证完成 %s→%s（测试通过，可正式升级）" % (args.vfrom, args.vto))
        sys.exit(0)

    # 4. 切换 plist
    print("[4/7] 切换 plist → launchctl 重启...")
    old_script = "blackboard-server-%s.py" % args.vfrom
    new_script = os.path.basename(script_path)
    s = open(PLIST, encoding="utf-8").read()
    if old_script in s:
        s2 = s.replace(old_script, new_script)
        open(PLIST, "w", encoding="utf-8").write(s2)
        print("  plist: %s → %s" % (old_script, new_script))
    else:
        print("  ⚠️ plist 未找到 %s（需手动确认）" % old_script)
    run("launchctl unload %s 2>/dev/null" % PLIST)
    time.sleep(1)
    run("for pid in $(lsof -ti tcp:8792 2>/dev/null); do kill -9 $pid 2>/dev/null; done")
    time.sleep(1)
    run("launchctl load %s 2>/dev/null" % PLIST)
    time.sleep(2.5)

    # 5. 验证生产
    print("[5/7] 验证生产...")
    st, data = http("GET", BB + "/clock")
    print("  %s 生产 /clock seq=%s" % ("✅" if st == 200 else "❌", data.get("seq")))
    if st != 200:
        print("❌ 生产未起，回滚? 手动检查"); sys.exit(1)

    # 6. 复用评估
    print("[6/7] 复用评估（bb-reuse-check）...")
    rc, out = run("python3 %s --capability \"%s\" --deps \"%s\" --hub-dependent \"%s\" --node-side \"%s\""
                  % (REUSE, args.what, args.deps, args.hub_dep, args.node_side))
    grade_line = [l for l in out.split("\n") if '"grade"' in l]
    grade = grade_line[0].split(":")[-1].strip().strip('",') if grade_line else "?"
    print("  复用分级: %s" % grade)

    # 7. 落链登记
    print("[7/7] 落链登记...")
    body = json.dumps({
        "item": "blackboard-%s（升级流水线）" % args.vto,
        "what": args.what,
        "reuse_grade": grade,
        "verify": "冒烟全过 + 生产验证",
        "rollback": "plist 指回 blackboard-server-%s.py" % args.vfrom,
        "ts": datetime.datetime.now().isoformat(timespec="seconds")
    }).encode()
    req = urllib.request.Request(BB + "/data/iterations/upgrade-%s" % args.vto, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=5) as r:
        print("  ✅ 落链: %s" % r.read().decode()[:60])

    print("\n✅ 升级完成 %s→%s | 复用分级: %s" % (args.vfrom, args.vto, grade))

if __name__ == "__main__":
    main()
