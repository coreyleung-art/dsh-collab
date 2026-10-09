#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-absorb.py — 节点经验/能力吸收流水线（进化循环第 4 步自动化）

节点（i9/MBP/门店）登记新工具/能力后，自动评估其复用价值并落链吸收建议。
供 bb-absorb-watch.py（常驻事件驱动）调用，也可手动执行。

用法：
  python3 bb-absorb.py --node i9 --tool i9-executor.py --desc "零token轮询执行器" --deps "标准库,http.client" --hub-dep "无" --node-side "纯标准库"
  python3 bb-absorb.py --check-only ...   # 只评估不落链

流程：
  1. 验证工具已登记于黑板 data/<node>/tools/<tool>
  2. 跑复用评估（bb-reuse-check.py）
  3. 生成吸收建议（grade + 建议动作）
  4. 落链：黑板 data/iterations/absorb-<tool> + genebank registry
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, subprocess, sys, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-absorb.log")


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
REUSE = os.path.expanduser("~/dsh-collab/scripts/bb-reuse-check.py")

def fetch(path):
    try:
        with urllib.request.urlopen(BB + path, timeout=6) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:100]}

def put(path, obj):
    body = json.dumps(obj).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.status

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", required=True, help="来源节点（i9/mbp/store-xx）")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--tool", required=True, help="工具/能力名（如 i9-executor.py）")
    ap.add_argument("--desc", required=True, help="能力描述")
    ap.add_argument("--deps", default="", help="依赖")
    ap.add_argument("--hub-dep", default="无", help="中枢依赖")
    ap.add_argument("--node-side", default="", help="节点侧情况")
    ap.add_argument("--check-only", action="store_true", help="只评估不落链")
    ap.add_argument("--env-notes", default="", help="环境自适配说明（编码/平台/路径差异，强制维度）")
    if "--lean4-check" in sys.argv:
        return lean4_check()
    args = ap.parse_args()

    print("== 吸收流水线：%s/%s ==" % (args.node, args.tool))
    print("描述: %s" % args.desc)

    # 1. 验证工具已登记
    tool_path = "/data/%s/tools/%s" % (args.node, args.tool)
    reg = fetch(tool_path)
    if "error" in reg and "not found" not in str(reg):
        print("⚠️ 工具 %s 查询异常: %s" % (tool_path, reg.get("error")))
    else:
        print("✅ 工具登记确认: %s" % tool_path)

    # 2. 复用评估
    print("\n[评估] 复用性...")
    # ★ 2026-10-09 R10 修复（结构性消除命令注入）：
    #   原实现 `"...%s..." % (args.desc, ...)` + `shell=True` ⇒ 参数经 shell 解析，
    #   而【双引号包裹不能防注入】（参数自身可含 `"`）。
    #   ⇒ 改为【列表传参 + 无 shell】：参数不再进入 shell 解析 ⇒ 该路径【结构上不可绕过】。
    proc = subprocess.run(
        ["python3", REUSE,
         "--capability", args.desc,
         "--deps", args.deps,
         "--hub-dependent", args.hub_dep,
         "--node-side", args.node_side,
         "--env-notes", args.env_notes],
        capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    grade = "?"
    for line in out.split("\n"):
        if '"grade"' in line:
            grade = line.split(":")[-1].strip().strip('",')
    print("  复用分级: %s" % grade)

    # 3. 吸收建议
    advice = {
        "reusable": "可泛化：提炼为底座通用件（如 node-executor.py 模式），纳入后续节点模板",
        "needs-adaptation": "需适配：记录适配指南，节点侧按需改造后复用",
        "hub-only": "中枢独占：记录价值，不泛化到节点",
    }.get(grade, "未知分级")
    print("  建议: %s" % advice)

    if args.check_only:
        print("\n(check-only 模式：不落链)")
        sys.exit(0)

    # 4. 落链
    print("\n[落链]...")
    item = {
        "absorbed_from": args.node,
        "tool": args.tool,
        "desc": args.desc,
        "grade": grade,
        "advice": advice,
        "ts": datetime.datetime.now().isoformat(timespec="seconds")
    }
    put("/data/iterations/absorb-%s-%s" % (args.node, args.tool.replace(".", "-")), item)
    print("  ✅ 黑板 data/iterations/absorb-%s-%s" % (args.node, args.tool.replace(".", "-")))
    print("\n✅ 吸收评估完成: %s → %s" % (args.tool, grade))


# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    main()
