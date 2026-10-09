#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gallery-export.py — 系统架构管理器静态导出(供 CloudBase 镜像/离线缓存)
抓取运行中 8798 服务的全部页面 + API 数据 + 静态资源 → 静态目录(CloudBase 可托管)
用法:
  python3 bb-gallery-export.py [--base http://127.0.0.1:8798] [--out DIR]
  --serve-out 同时起本地静态服务验证(DIR 可直接被静态托管)

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, urllib.request, re, sys, time


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-gallery-export.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

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
        idx_path = os.path.join(out, "index.html")
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(s)
        # ★★ 2026-09-28 修（明鉴 实测发现根因，我独立复算吻合）：
        #   原为 `"bytes": len(s)`，而 `s` 是**字符串**（第 48 行 `html.decode()` 的产物）
        #   ⇒ `len(s)` = **字符数**，不是字节数 ⇒ 线上实测声明 138762 而真实 **150200**，
        #     差 **11438** = 汉字的额外字节，与 `len(s.encode('utf-8')) - len(s)` 完全相等 ✓
        #   ⇒ ★ 同一份文件里第 42 行 `len(data)`（`data` 是 bytes）是**对的**
        #     ⇒ 根因精确为：**同一个 `len()` 在同一份代码里量了两种不同的量**（字符 / 字节）
        #   ⇒ 判据：**「这个 `len()` 量的是字节还是字符？」—— 无单位声明的计数不可核** ✓
        #   ★ 修法选择：**量写出去的那个文件**（`getsize`），而不是补一次 `encode()`
        #     —— 后者仍是一个**代理量**（换了编码/换行转换就又会错），
        #       前者量的是**真实产物的字节**，不可能错位 ✓
        manifest["html"] = {"file": "index.html", "bytes": os.path.getsize(idx_path)}
    # 静态资源 vendor(d3)
    os.makedirs(os.path.join(out, "vendor"), exist_ok=True)
    for v in ["d3.min.js"]:
        d, _ = fetch(f"/vendor/{v}")
        if d:
            with open(os.path.join(out, "vendor", v), "wb") as f: f.write(d)
    # ★★ 2026-09-28 补（明鉴 实测发现）：图库资产 assets/ —— **此前从未复制**
    #   前端取图路径（index.html:724）：`__BASE+'/assets/'+encodeURIComponent(a.file)`
    #   ⇒ 指针的基准命名空间是 **assets/**，**不是 snapshots/**。
    #     snapshots/ 供「蓝图三视图」用（index.html:1865 四处 __BASE+'/snapshots/'），是**另一个消费者**。
    #     ★ 我先前把两者并成一轴说「83 份只有 1 份可解析」—— 那是**假一轴**：
    #       两个命名空间之间**本来就互不引用**，api/*.json 里 svg 引用共 4 条，全部来自 assets.json。
    #   线上实测（2026-09-28，tm.meetfunbp.com/systemgraph/）：
    #     assets/ 下 10 条指针 → **8 条 200 且与本地逐字节相同**，缺的 2 条是
    #       distributed-agent-network-arch-20260909.svg / distributed-network-erd-20260909.svg
    #       （以及未列入 assets.json 的 meeting-identity-graph.json）—— 全是 **09-09 新增**的文件
    #     ⇒ 根因：assets/ **只有一次性手工推送，没有任何自动通道**
    #        （线上存在的文件内容 T ∈ (2026-09-02 21:53, 2026-09-09 00:07)），此后新增的永远上不去
    #   ⇒ 修法：**载荷由索引派生** —— 以刚抓下来的 api/assets.json 枚举为准**逐条**复制，
    #     而不是让「索引」和「载荷」各自独立枚举目录（独立枚举必然出现「索引里有、载荷里没有」）✓
    #   ⇒ 且源文件缺失时**硬失败 exit 2**，不静默跳过 —— 静默跳过正是那 2 个死指针的成因 ✓
    assets_meta = os.path.join(api_dir, "assets.json")
    n_assets = 0
    if os.path.exists(assets_meta):
        try:
            entries = json.load(open(assets_meta, encoding="utf-8"))
        except Exception as e:
            print(f"❌ assets.json 解析失败: {e} ⇒ 拒绝导出（否则载荷与索引会静默错位）")
            sys.exit(2)
        # 源目录可被环境变量覆盖（默认不变）—— 供自测注入 fixture，从而**能证明这条硬失败真的会失败**；
        # 不可注入的闸门只能靠读代码相信它 ⇒ 那是「假的 selftest」
        asset_src = os.environ.get("GALLERY_ASSETS_SRC",
                                   os.path.expanduser("~/dsh-collab/data/blueprint/gallery/assets"))
        asset_dst = os.path.join(out, "assets")
        os.makedirs(asset_dst, exist_ok=True)
        import shutil as _sh
        # 分母 = **索引里真正带 file 的条数**（不是 entries 总长）—— 计数必须与判据同口径
        want = [e for e in entries if isinstance(e, dict) and e.get("file")]
        missing = []
        for e in want:
            fn = e["file"]
            sp = os.path.join(asset_src, fn)
            if not os.path.exists(sp):
                missing.append(fn)
                continue
            _sh.copy(sp, os.path.join(asset_dst, fn))
            n_assets += 1
        if missing:
            print(f"❌ assets.json 索引了 {len(missing)} 个本地不存在的文件 ⇒ 拒绝导出（会产出死指针）:")
            for m in missing:
                print(f"     ✗ {m}")
            sys.exit(2)
        print(f"③ 复制图库资产 {n_assets}/{len(want)} 份 → assets/")
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
        print(f"④ 复制快照 SVG {n} 份")
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
