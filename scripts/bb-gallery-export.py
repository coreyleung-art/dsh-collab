#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gallery-export.py — 系统架构管理器静态导出(供 CloudBase 镜像/离线缓存)
抓取运行中 8798 服务的全部页面 + API 数据 + 静态资源 → 静态目录(CloudBase 可托管)
用法:
  python3 bb-gallery-export.py [--base http://127.0.0.1:8798] [--out DIR]
  --serve-out 同时起本地静态服务验证(DIR 可直接被静态托管)
"""
import argparse, json, os, urllib.request, re, sys, time

BASE = "http://127.0.0.1:8798"
API_ENDPOINTS = ["overview","blueprints","agents","versions","relations","assets",
    "agent-graph","mech-graph","mechanism","knowledge-graph","original","workflow",
    "philosophy","biz-assets","hardware","hwcomm","hwprobe","system-assets","rules",
    "rule-graph","islands","plan-archive"]
# 蓝图详情/快照是动态 per-bp 与 svg 文件 — 由 assets/snapshots 目录复制覆盖

def fetch(path, timeout=15):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            data = r.read()
            ct = r.headers.get("Content-Type", "")
            return data, ct
    except Exception as e:
        print(f"  ⚠️ {path}: {e}")
        return None, ""

def export(out, base=BASE):
    os.makedirs(out, exist_ok=True)
    api_dir = os.path.join(out, "api")
    os.makedirs(api_dir, exist_ok=True)
    print(f"① 抓取 {len(API_ENDPOINTS)} 个 API… (base={base})")
    manifest = {"version": "1.0", "exported": time.strftime("%Y-%m-%dT%H:%M:%S"), "apis": {}}
    for ep in API_ENDPOINTS:
        data, ct = fetch(f"/api/{ep}")
        if data is None: continue
        # JSON API 存文件
        fname = ep + (".json" if "json" in ct or ep not in ("overview",) else ".json")
        if data:
            with open(os.path.join(api_dir, ep + ".json"), "wb") as f:
                f.write(data)
            manifest["apis"][ep] = {"file": f"api/{ep}.json", "bytes": len(data)}
    # 蓝图详情页(动态) — 主页面含全部蓝图图谱, 详情可现场拉; 快照 svg 单独复制
    print(f"② 抓取主页 HTML…")
    html, _ = fetch("/")
    if html:
        # 让前端知道这是静态模式: 注入 window.__STATIC__
        s = html.decode("utf-8", "ignore")
        # 注入标记必须在 JS_TMPL script(已展开, 'let ALL' 开头)之前 —— __STATIC 常量在加载时读 window.__STATIC__
        marker = "<script>window.__STATIC__=true;window.__STATIC_API__='api/';</script>"
        anchor = '<script>let ALL = {overview'
        if anchor in s:
            s = s.replace(anchor, marker + anchor)
        elif '<script src="vendor/d3.min.js">' in s:
            s = s.replace('<script src="vendor/d3.min.js">',
                          marker + '<script src="vendor/d3.min.js">')
        with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
            f.write(s)
        manifest["html"] = {"file": "index.html", "bytes": len(s)}
    # 静态资源 vendor(d3)
    os.makedirs(os.path.join(out, "vendor"), exist_ok=True)
    for v in ["d3.min.js"]:
        d, _ = fetch(f"/vendor/{v}")
        if d:
            with open(os.path.join(out, "vendor", v), "wb") as f: f.write(d)
    # 快照 svg(蓝图三视图) — 从本地 snapshots 目录复制
    snap_src = os.path.expanduser("~/dsh-collab/data/blueprint/gallery/snapshots")
    if os.path.isdir(snap_src):
        snap_dst = os.path.join(out, "snapshots")
        os.makedirs(snap_dst, exist_ok=True)
        import shutil
        n = 0
        for f in os.listdir(snap_src):
            if f.endswith(".svg"):
                shutil.copy(os.path.join(snap_src, f), os.path.join(snap_dst, f)); n += 1
        print(f"③ 复制快照 SVG {n} 份")
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    # 统计目录大小
    total = sum(os.path.getsize(os.path.join(dp, fn)) for dp,_,fns in os.walk(out) for fn in fns)
    print(f"✅ 导出完成 → {out}  ({total/1024:.0f} KB, {len(manifest['apis'])} API)")
    return out

def export_out(base, out):
    old = globals().get('BASE')
    globals()['BASE'] = base
    try:
        export(out, base)
    finally:
        globals()['BASE'] = old

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--auto", action="store_true", help="自动探测可用基址(Funnel→本机)")
    ap.add_argument("--out", default=os.path.expanduser("~/dsh-collab/data/blueprint/gallery/static-export"))
    args = ap.parse_args()
    if args.auto:
        for cand in ["http://127.0.0.1:8798", "https://coreymac-mini.taild3fd86.ts.net/sg"]:
            try:
                urllib.request.urlopen(cand + "/api/overview", timeout=5)
                print(f"选用基址: {cand}")
                export_out(cand, args.out); return
            except Exception:
                continue
        print("⚠️ 无可达基址"); return
    export_out(args.base or BASE, args.out)

if __name__ == "__main__":
    main()
