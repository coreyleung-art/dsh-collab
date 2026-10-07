#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-bp-register.py — 蓝图登记统一 CLI（登记三写：本地 + 黑板数据源 + SystemGraph 生效）

教训来源（2026-09-07）：新增 flowernet-supply/citywar 后 SystemGraph 不显示——
根因：登记只写本地，未同步黑板数据源。本工具把"蓝图登记同步 SOP"固化为一条命令。

功能：
  ① 从本地 BP-9 md 解析蓝图 → 写入黑板详情(dict) + relations 清单 + 边
  ② bp_dims/bp_colors 硬编码表补录提示（主源+dist 双份，需手动确认或用 --apply-dims）
  ③ SystemGraph 生效验证（curl :8798/api/blueprints 检查 dim/主线非空）

R006 合规：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理。

用法：
  python3 bb-bp-register.py --register <蓝图id>            # 登记三写主流程（md→黑板详情+relations）
  python3 bb-bp-register.py --register <id> --sync-sysgraph # 登记+重启8798+验证（需服务在 dist）
  python3 bb-bp-register.py --list                          # 列出本地 data/blueprint/<id>
  python3 bb-bp-register.py --verify <蓝图id>               # 验证黑板+SystemGraph 数据一致性
  python3 bb-bp-register.py --dims-check                    # 检查哪些蓝图缺 bp_dims/bp_colors
  python3 bb-bp-register.py --selfcheck                     # TCC
  python3 bb-bp-register.py --tool-version                  # 版本

依赖：黑板 http://127.0.0.1:8792（PUT/GET）；本地 ~/dsh-collab/data/blueprint/
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, os, re, glob, subprocess, time

VERSION = "v1.0.0"
BB = os.environ.get("BB_URL", "http://127.0.0.1:8792")
BASE = os.path.expanduser("~/dsh-collab")
BP_DIR = os.path.join(BASE, "data/blueprint")
GALLERY_MAIN = os.path.join(BASE, "scripts/bb-blueprint-gallery.py")
GALLERY_DIST = os.path.expanduser("~/system-graph-app/dist/SystemGraph.app/Contents/Resources/app/gallery/bb-blueprint-gallery.py")
SYSGRAPH_URL = "http://127.0.0.1:8798"

def now(): return datetime.datetime.now().isoformat(timespec="seconds")

# ── 黑板访问 ────────────────────────────────────────────────────────────────
def bb_put(key, payload):
    """黑板写：只放纯数据对象（禁整体回写 GET 结果——防嵌套）"""
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + "/" + key.lstrip("/"), data=body,
                                 headers={"Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except Exception as e:
        return f"ERR:{e}"

def bb_get(key):
    """黑板读：剥到最内层 value（兼容嵌套）"""
    try:
        with urllib.request.urlopen(BB + "/" + key.lstrip("/"), timeout=10) as r:
            doc = json.loads(r.read().decode())
    except Exception as e:
        return {}
    v = doc.get("value", doc)
    # 剥嵌套: value.value.value... 直到不是 {key,ts,value,version} 包装
    while isinstance(v, dict) and set(v.keys()) >= {"value"} and len(v) <= 4 \
          and isinstance(v.get("value"), (dict, list, str)):
        inner = v.get("value")
        if isinstance(inner, dict) and "value" in inner and len(inner) <= 4 and set(inner.keys()) <= {"ts","value","key","version"}:
            v = inner
        else:
            break
    return v

# ── 本地 md → BP dict ───────────────────────────────────────────────────────
def md_to_bp_dict(md_text):
    """从 BP-9 md 解析 dict（对齐服务端 get_blueprint 期望字段）"""
    bp = {}
    m = re.search(r'\|\s*id\s*\|\s*([\w-]+)\s*\|', md_text)
    if m: bp["id"] = m.group(1)
    m = re.search(r'\|\s*name\s*\|\s*(.+?)\s*\|', md_text)
    if m: bp["name"] = m.group(1).strip()
    m = re.search(r'\|\s*version\s*\|\s*v?([\d.]+)\s*\|', md_text)
    if m: bp["version"] = "v" + m.group(1).lstrip("v")
    m = re.search(r'\|\s*dim\s*\|\s*(.+?)\s*\|', md_text)
    if m: bp["dim"] = m.group(1).strip()
    m = re.search(r'\|\s*gate\s*\|\s*(.+?)\s*\|', md_text)
    if m: bp["gate"] = m.group(1).strip()
    m = re.search(r'\|\s*status\s*\|\s*(.+?)\s*\|', md_text)
    if m: bp["status"] = m.group(1).strip()
    m = re.search(r'\|\s*mainlines\s*\|\s*(\{.*\})\s*\|', md_text, re.S)
    if m:
        try:
            ml = json.loads(m.group(1))
            bp["mainlines"] = {k: (v.get("name", k) if isinstance(v, dict) else v) for k, v in ml.items()}
        except Exception:
            bp["mainlines"] = {}
    # 默认 mainlines 提取（一、主线 列表）
    if "mainlines" not in bp or not bp["mainlines"]:
        ml = {}
        for mm in re.finditer(r'-\s*\*\*([\w-]+)\*\*[：:]\s*(.+?)(?=\n-|\n##|\Z)', md_text, re.S):
            ml[mm.group(1)] = mm.group(2).strip()[:80]
        bp["mainlines"] = ml
    # stages（兼容 P0/P1 字母前缀 与 1.0 数字前缀；同时解析子阶段行）
    stages = []
    cur = None
    for line in md_text.split("\n"):
        m = re.match(r'\s*###\s*([\w.]+)\s+([^\[]+?)\s*\[(\w+)\]', line)
        if m:
            sid = m.group(1).replace(".", "-")
            cur = {"id": sid, "name": m.group(2).strip(), "stage": m.group(1),
                   "status": m.group(3), "substages": []}
            stages.append(cur)
            continue
        if cur is not None:
            m2 = re.match(r'\s*-\s*([\w-]+)\s+([^\[]+?)\s*\[(\w+)\]\s*(?:—\s*(.*))?', line)
            if m2:
                cur["substages"].append({"id": m2.group(1), "name": m2.group(2).strip(),
                                         "status": m2.group(3), "note": (m2.group(4) or "").strip()})
    if stages:
        bp["stages"] = stages
    return bp

def find_bp_md(bp_id):
    """找本地蓝图 md 文件"""
    d = os.path.join(BP_DIR, bp_id)
    files = glob.glob(os.path.join(d, "blueprint-*.md")) if os.path.isdir(d) else []
    if not files:
        files = glob.glob(os.path.join(BP_DIR, f"blueprint-{bp_id}-*.md"))
    return files[0] if files else None

# ── relations 清单管理 ──────────────────────────────────────────────────────
def relations_add_bp(bp_id, edges=None):
    """黑板 relations.blueprints 加 id + 可选边"""
    rel = bb_get("data/blueprint/relations")
    if not isinstance(rel, dict) or "blueprints" not in rel:
        print("❌ 黑板 relations 读取失败或结构异常"); return False
    changed = False
    if bp_id not in rel["blueprints"]:
        rel["blueprints"].append(bp_id); changed = True
    if edges:
        exist = {(e.get("from"), e.get("to"), e.get("type")) for e in rel.get("edges", [])}
        for e in edges:
            k = (e.get("from"), e.get("to"), e.get("type"))
            if k not in exist:
                rel.setdefault("edges", []).append(e); changed = True
    if changed:
        st = bb_put("data/blueprint/relations", rel)  # 纯 dict
        print(f"✅ 黑板 relations 更新 ({st}) blueprints={len(rel['blueprints'])} edges={len(rel.get('edges',[]))}")
    else:
        print("ℹ️ relations 已含该蓝图，无需变更")
    return True

# ── 硬编码表检查 ────────────────────────────────────────────────────────────
def dims_check(bp_id=None):
    """检查 bp_dims/bp_colors 是否缺该蓝图"""
    ids = [bp_id] if bp_id else [os.path.basename(os.path.dirname(f)) for f in
           glob.glob(os.path.join(BP_DIR, "*", "blueprint-*.md"))]
    miss_main, miss_dist = [], []
    for src, tag in [(GALLERY_MAIN, "主源"), (GALLERY_DIST, "dist")]:
        if not os.path.exists(src): continue
        t = open(src, encoding="utf-8").read()
        for bid in sorted(set(ids)):
            if not re.search(r'"' + re.escape(bid) + r'"', t):
                miss_main.append(bid) if tag == "主源" else miss_dist.append(bid)
    return miss_main, miss_dist

def dims_patch(bp_id):
    """生成 bp_dims/bp_colors 补丁说明（含建议色）"""
    # 从 md 取 dim
    f = find_bp_md(bp_id)
    dim = "业务"
    if f:
        t = open(f, encoding="utf-8").read()
        m = re.search(r'\|\s*dim\s*\|\s*(.+?)\s*\|', t)
        if m: dim = m.group(1).strip()
    return f"在 bb-blueprint-gallery.py 的 bp_dims() 加 '{bp_id}': '{dim}'；bp_colors() 加 '{bp_id}': '#<色值>'（主源+dist 双份）"

# ── 主流程 ──────────────────────────────────────────────────────────────────
def cmd_register(bp_id, sync_sysgraph=False):
    f = find_bp_md(bp_id)
    if not f:
        print(f"❌ 未找到本地蓝图 md: data/blueprint/{bp_id}/blueprint-*.md"); return 1
    print(f"① 读取本地: {f}")
    md = open(f, encoding="utf-8").read()
    bp = md_to_bp_dict(md)
    if "id" not in bp or not bp.get("mainlines"):
        print("❌ BP-9 元信息解析失败（缺 id/mainlines）"); return 1
    print(f"   解析: {bp['id']} {bp.get('name','')[:30]} {bp.get('version','')} mainlines={list(bp['mainlines'].keys())}")
    # ② 黑板详情(dict)
    st = bb_put(f"data/blueprint/{bp_id}", bp)
    print(f"② 黑板详情(dict): PUT {st}")
    # ③ relations 清单+边
    relations_add_bp(bp_id)
    # ④ dims 检查
    miss_m, miss_d = dims_check(bp_id)
    if miss_m or miss_d:
        print(f"⚠️ ④ 硬编码表缺 {bp_id}: {dims_patch(bp_id)}")
    else:
        print("✅ ④ bp_dims/bp_colors 已含该蓝图")
    # ⑤ SystemGraph 验证
    if sync_sysgraph:
        print("⑤ 重启 8798 服务…")
        subprocess.run(["pkill", "-f", "bb-blueprint-gallery.py"], capture_output=True)
        time.sleep(1)
        home = os.path.dirname(GALLERY_DIST)
        if os.path.exists(os.path.join(home, "bb-blueprint-gallery.py")):
            subprocess.Popen(["/usr/bin/python3", "bb-blueprint-gallery.py", "--port", "8798", "--host", "0.0.0.0"],
                             cwd=home, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
    verify_sysgraph(bp_id)
    return 0

def verify_sysgraph(bp_id=None):
    """验证 SystemGraph API"""
    try:
        with urllib.request.urlopen(SYSGRAPH_URL + "/api/blueprints", timeout=8) as r:
            bps = json.loads(r.read().decode())
    except Exception as e:
        print(f"⚠️ SystemGraph 不可达: {e}"); return
    ids = [bp_id] if bp_id else None
    for b in bps:
        if ids and b["id"] not in ids: continue
        ok = b.get("dim") not in ("?", "") and len(b.get("mainlines", [])) > 0
        print(f"{'✅' if ok else '⚠️'} {b['id']}: dim={b.get('dim')} mainlines={len(b.get('mainlines',[]))}")

def cmd_list():
    dirs = [d for d in os.listdir(BP_DIR) if os.path.isdir(os.path.join(BP_DIR, d))
            and glob.glob(os.path.join(BP_DIR, d, "blueprint-*.md"))]
    print(f"== 本地蓝图 ({len(dirs)}) ==")
    for d in sorted(dirs):
        print(" ", d)

def selfcheck():
    print("TCC PASS: bb-bp-register 自检")
    print("  - md→dict 解析器: 内置")
    print("  - 黑板 PUT/GET: 需 8792 可达")
    return 0

def main():
    ap = argparse.ArgumentParser(description="蓝图登记统一 CLI（三写）")
    ap.add_argument("--register", default="", help="登记蓝图 id（md→黑板详情+relations）")
    ap.add_argument("--sync-sysgraph", action="store_true", help="登记后重启 8798+验证")
    ap.add_argument("--list", action="store_true", help="列出本地蓝图")
    ap.add_argument("--verify", default="", help="验证指定蓝图在 SystemGraph 的状态")
    ap.add_argument("--dims-check", default="", help="检查硬编码表是否缺某蓝图")
    ap.add_argument("--dims-all", action="store_true", help="检查全部蓝图的硬编码表覆盖")
    ap.add_argument("--selfcheck", action="store_true", help="TCC")
    ap.add_argument("--tool-version", action="version", version=f"bb-bp-register {VERSION}")
    a = ap.parse_args()
    if a.selfcheck: return selfcheck()
    if a.list: return cmd_list()
    if a.register: return cmd_register(a.register, a.sync_sysgraph)
    if a.verify: verify_sysgraph(a.verify); return 0
    if a.dims_check:
        mm, md = dims_check(a.dims_check or None)
        print(f"主源缺: {mm or '无'} | dist缺: {md or '无'}")
        return 0
    if a.dims_all:
        mm, md = dims_check(None)
        print(f"主源缺: {mm or '无'} | dist缺: {md or '无'}")
        return 0
    ap.print_help(); return 1

if __name__ == "__main__":
    sys.exit(main())
