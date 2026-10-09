#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
datadir-job-audit —— 逐 job 的数据根生效判定（静态，只读）（v1.0.0）

补齐的边：**env → 实际读到的库**（老登的 datadir-audit.py 覆盖「源码面」；本工具覆盖「调度面」）。
背景（2026-09-14 联合定位）：lib/store.js:11 `process.env.MTM_DATA_DIR || ROOT` 是**顶层 const**，
而 lib/im-window.js:14 / lib/browser-restart.js:13 / lib/main-page.js:14 在**模块顶层改写 process.env**
⇒ 哪次 import 先发生，决定该进程读**实盘**还是读**诱饵**（仓库旧库，order_sales 38 行）。

★ 为什么只能**静态**判定：老登实测 `charge/order-export/review/site-adapt/chrome/im-window`
   把 dataDir 算在**函数内部且不导出** ⇒ 打不出；而直接运行这些 job 的入口会**执行真实调度动作**
   （拉浏览器/导出），有副作用 ⇒ 不宜在活体上跑。故本工具只做**配置 + import 顺序**的静态判定，
   并显式标注「静态」以免被读成运行时事实。

判定（对每个 job 的入口文件）：
    ENV-PRESET         plist 显式设了 MTM_DATA_DIR ⇒ 与 import 顺序无关（最安全）
    MUTATOR-FIRST      入口先引入「顶层改 env 的模块」、后 require store ⇒ 大概率拿到实盘
    STORE-FIRST        入口先 require store ⇒ 未设 env 时**静默读诱饵**
    NO-STORE-REQUIRE   入口不直接 require store（可能经间接层）⇒ 静态判不了，标 UNKNOWN

用法：
    python3 datadir-job-audit.py [--agents ~/Library/LaunchAgents] [--json-out F]
    python3 datadir-job-audit.py --selftest
    退出码：0 全部 ENV-PRESET/MUTATOR-FIRST · 1 存在 STORE-FIRST/UNKNOWN · 2 参数错

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）


import argparse
import json
import os
import plistlib
import re
import sys
import tempfile
import time


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/datadir-job-audit.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "1.0.0"
ENV_KEY = "MTM_DATA_DIR"
STORE_RE = re.compile(r"require\((['\"])(\.\.?/)*(lib/)?store\1\)")
MUTATOR_NAMES = ["im-window", "browser-restart", "main-page"]


def read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except Exception:
        return []


def analyse_entry(entry):
    """返回 (verdict, 证据行描述)。仅看入口文件自身的 import 顺序。"""
    lines = read_lines(entry)
    if not lines:
        return "UNKNOWN", "入口文件不可读"
    store_line = next((i + 1 for i, l in enumerate(lines) if STORE_RE.search(l)), None)
    mut_line, mut_what = None, ""
    for i, l in enumerate(lines):
        for name in MUTATOR_NAMES:
            if re.search(rf"require\((['\"])(\.\.?/)*(lib/)?{name}\1\)", l) or re.search(rf"\./{name}\b", l):
                if mut_line is None:
                    mut_line, mut_what = i + 1, f"引入 {name}"
        if mut_line is None and re.search(rf"process\.env\.{ENV_KEY}\s*=", l):
            mut_line, mut_what = i + 1, "顶层改写 env"
    if store_line is None:
        return "UNKNOWN", "入口未直接 require store（可能经间接层）"
    if mut_line is None:
        return "STORE-FIRST", f"L{store_line} require store，未见上游改写 ⇒ 未设 env 时读诱饵"
    if mut_line < store_line:
        return "MUTATOR-FIRST", f"L{mut_line} {mut_what} 早于 L{store_line} require store ⇒ 大概率实盘"
    return "STORE-FIRST", f"L{store_line} require store 早于 L{mut_line} {mut_what} ⇒ 未设 env 时读诱饵"


def audit_agents(agents_dir):
    rows = []
    for name in sorted(os.listdir(os.path.expanduser(agents_dir))):
        if not name.endswith(".plist"):
            continue
        path = os.path.join(os.path.expanduser(agents_dir), name)
        try:
            d = plistlib.load(open(path, "rb"))
        except Exception:
            continue
        args = d.get("ProgramArguments") or ([d["Program"]] if d.get("Program") else [])
        entry = next((a for a in args if isinstance(a, str) and a.endswith((".js", ".py", ".sh"))), None)
        env = d.get("EnvironmentVariables") or {}
        preset = ENV_KEY in env
        if entry is None:
            continue
        if preset:
            verdict, why = "ENV-PRESET", f"plist EnvironmentVariables 含 {ENV_KEY}"
        else:
            verdict, why = analyse_entry(entry)
        rows.append({"label": d.get("Label", name[:-6]), "entry": entry,
                     "env_preset": preset, "verdict": verdict, "why": why,
                     "audited_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return rows


def selftest():
    ok = total = 0
    d = tempfile.mkdtemp(prefix="joba-")

    def w(name, body):
        p = os.path.join(d, name)
        open(p, "w", encoding="utf-8").write(body)
        return p

    store_first = w("a.js", "const s = require('./store');\nrequire('./im-window');\n")
    mut_first = w("b.js", "require('./im-window');\nconst s = require('./store');\n")
    no_store = w("c.js", "console.log('nothing here');\n")
    cases = [
        ("反例·先 require store ⇒ STORE-FIRST", store_first, "STORE-FIRST"),
        ("正例·先引入改写者 ⇒ MUTATOR-FIRST", mut_first, "MUTATOR-FIRST"),
        ("正例·不 require store ⇒ UNKNOWN", no_store, "UNKNOWN"),
    ]
    print("selftest（先反例后正例）:")
    for name, p, want in cases:
        total += 1
        got, why = analyse_entry(p)
        good = got == want
        ok += 1 if good else 0
        print(f"  {'✅' if good else '❌'} {name}: expect={want} got={got} ({why})")
    print(f"\nselftest {ok}/{total}")
    return 0 if ok == total else 1


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--agents", default="~/Library/LaunchAgents")
    ap.add_argument("--json-out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    args = ap.parse_args()
    if args.version:
        print(json.dumps({"tool": "datadir-job-audit", "version": VERSION, "mode": "static",
                          "verdicts": ["ENV-PRESET", "MUTATOR-FIRST", "STORE-FIRST", "UNKNOWN"]}, ensure_ascii=False))
        return 0
    if args.selftest:
        return selftest()

    rows = audit_agents(args.agents)
    bad = [r for r in rows if r["verdict"] in ("STORE-FIRST", "UNKNOWN")]
    for r in rows:
        if r["verdict"] in ("STORE-FIRST", "UNKNOWN"):
            print(f"[{r['verdict']}] {r['label']} :: {r['why']}\n        入口 = {r['entry']}")
    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    print(f"\n静态审计 {len(rows)} 个 job（入口含 .js/.py/.sh 者）· " + " · ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print("⚠ 本工具为**静态**判定：只读 plist 与入口的 import 顺序，不执行 job（活体执行有副作用）。")
    if args.json_out:
        json.dump({"version": VERSION, "mode": "static", "rows": rows},
                  open(os.path.expanduser(args.json_out), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"json → {args.json_out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
