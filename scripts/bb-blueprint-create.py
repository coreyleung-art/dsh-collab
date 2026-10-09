#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-blueprint-create.py — 蓝图正式化工具（三件套纪律：文档+代码+依赖）

用户指示（2026-09-01）：每一个步骤都应形成文档/代码/依赖，不依赖模型本身。
本工具：① 从黑板 BP-9 数据生成本地持久化蓝图文档（data/blueprint/<id>/blueprint-<id>-vX.md）
       ② 校验 BP-9 九字段 ③ 生成 relations 依赖声明 ④ 落链黑板登记。

R006 九标准：CLI 形态/TCC(--selfcheck)/文档化/版本管理(--tool-version)/自动落链/CLI 治理

用法：
  python3 bb-blueprint-create.py --bp agent-network            # 生成本地文档（读黑板→落盘 md）
  python3 bb-blueprint-create.py --bp flowernet-platform       # 同上
  python3 bb-blueprint-create.py --bp blueprint-platform
  python3 bb-blueprint-create.py --list                       # 列出黑板已有蓝图
  python3 bb-blueprint-create.py --selfcheck                  # TCC

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, ast


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-blueprint-create.log")


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
BP9_FIELDS = ["id", "name", "version", "mainlines", "stages", "works", "gate", "status", "ts"]
VERSION = "v1.0.0"

def _url(path):
    return BB + ("/" + path.lstrip("/") if path else "")

def fetch(path):
    try:
        with urllib.request.urlopen(_url(path), timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def check_bp9(bp):
    missing = [f for f in BP9_FIELDS if f not in bp]
    if missing:
        print(f"⚠️ BP-9 缺字段: {missing}")
        return False
    print("✅ BP-9 九字段完整")
    return True

def gen_document(bp):
    """从 BP-9 dict 生成 markdown 文档"""
    L = []
    L.append(f"# blueprint:{bp['id']} · {bp.get('name','')} · {bp.get('version','')}")
    L.append("")
    L.append(f"> 生成：bb-blueprint-create.py · {now()} · 三件套纪律（文档/代码/依赖）")
    L.append(f"> 状态：{bp.get('status','')} · 门禁：{bp.get('gate','')}")
    L.append(f"> 依据：{bp.get('source','')}")
    L.append("")
    L.append("## 〇、BP-9 元信息")
    L.append("")
    L.append("| 字段 | 值 |")
    L.append("|------|-----|")
    for f in BP9_FIELDS:
        v = bp.get(f, "")
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)[:80] + "..."
        L.append(f"| {f} | {v} |")
    L.append("")
    L.append("## 一、主线")
    L.append("")
    for mid, m in (bp.get("mainlines") or {}).items():
        if isinstance(m, str):
            L.append(f"- **{mid}**：{m}")
        else:
            L.append(f"- **{mid}**：{m.get('name','')} — {m.get('desc','')}")
    L.append("")
    L.append("## 二、阶段与子阶段")
    L.append("")
    for st in bp.get("stages", []):
        L.append(f"### {st.get('stage')} {st.get('name')} [{st.get('status')}]")
        for ss in st.get("substages", []):
            L.append(f"- {ss.get('id')} {ss.get('name')} [{ss.get('status')}] — {ss.get('note','')}")
        L.append("")
    L.append("## 三、工作项（works）")
    L.append("")
    L.append("| 状态 | 工作 | owner | stage |")
    L.append("|------|------|-------|-------|")
    for w in bp.get("works", []):
        L.append(f"| {w.get('status','')} | {w.get('work','')} | {w.get('owner','')} | {w.get('stage','')} |")
    L.append("")
    L.append("## 四、依赖关系（relations）")
    L.append("")
    rel = bp.get("relations", {})
    if rel:
        for k, v in rel.items():
            L.append(f"- **{k}**：{', '.join(v) if isinstance(v, list) else v}")
    else:
        L.append("（无声明）")
    L.append("")
    L.append("## 四b、自动化开关锁（R027 + Lean4 逻辑锁）")
    L.append("")
    sw = bp.get("switches", {})
    if sw:
        for sid, sd in sw.items():
            L.append(f"- **{sid}**：{sd.get('automation','')}")
            L.append(f"  - 开关点：`{sd.get('switch_point','')}` · 默认态：{sd.get('default_state','OFF')}")
            L.append(f"  - 熔断：`{sd.get('kill_path','')}`")
            L.append(f"  - 授权：{sd.get('auth_required','')}")
    else:
        L.append("（无自动化开关声明——非 AI 自动化阶段或待补）")
    L.append("")
    L.append("## 五、门禁链")
    L.append("")
    L.append(bp.get("gate", ""))
    L.append("")
    L.append("---")
    L.append(f"*blueprint:{bp['id']} · {bp.get('version','')} · 三件套纪律落盘*")
    L.append("")
    return "\n".join(L)

def cmd_generate(bp_id):
    d = fetch(f"data/blueprint/{bp_id}")
    if "error" in d:
        print(f"❌ 黑板读 {bp_id}: {d['error']}"); sys.exit(1)
    bp = d.get("value", {})
    if not bp:
        print(f"❌ 黑板 {bp_id} 为空（value 嵌套？）")
        # 尝试 value.value
        bp = bp.get("value", {}) if isinstance(bp, dict) else {}
        if not bp:
            sys.exit(1)
    check_bp9(bp)
    md = gen_document(bp)
    # 落盘 data/blueprint/<id>/blueprint-<id>-vX.md
    ver = str(bp.get("version", "v1")).replace("（", "-").replace("）", "").replace(" ", "-")[:20]
    dpath = os.path.expanduser(f"~/dsh-collab/data/blueprint/{bp_id}")
    os.makedirs(dpath, exist_ok=True)
    fname = f"blueprint-{bp_id}-{ver}.md"
    fpath = os.path.join(dpath, fname)
    with open(fpath, "w") as f:
        f.write(md)
    print(f"✅ 文档落盘: {fpath}（{len(md)} 字节）")
    # 落链黑板登记
    note = {"bp": bp_id, "doc": fpath, "gen_ts": now(), "by": "bb-blueprint-create"}
    body = json.dumps(note, ensure_ascii=False).encode()
    req = urllib.request.Request(_url(f"data/blueprint/{bp_id}/doc-registry"),
                                 data=body, method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        print("✅ 落链:", r.read().decode()[:80])
    return fpath

def cmd_list():
    d = fetch("data/")
    ks = [k for k in d.get("list", {}) if k.startswith("data/blueprint/") and k.count("/") == 2]
    print("== 黑板已有蓝图 ==")
    for k in sorted(ks):
        print(" ", k)

def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    d = fetch("data/blueprint/stages")
    if "error" in d:
        print(f"❌ 黑板不可达: {d['error']}"); ok = False
    else:
        print("✅ 黑板连通")
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="蓝图正式化工具（三件套纪律）")
    ap.add_argument("--bp", default="", help="蓝图 id（agent-network/flowernet-platform/blueprint-platform/...）")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"bb-blueprint-create {VERSION}")
    args = ap.parse_args()
    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.list:
        cmd_list()
    elif args.bp:
        cmd_generate(args.bp)
    else:
        print(ap.format_help())

if __name__ == "__main__":
    main()
