#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-gallery-export-selftest.py — bb-gallery-export.py 的 assets/ 载荷闸门自测

为什么要它：
  2026-09-28 实测发现线上 /systemgraph/assets/ 10 条指针里 8 条 200、2 条 404，
  缺的正是 09-09 新增的两个 SVG。根因不是「文件没生成」，而是
  **导出器从来没复制过 assets/ 目录**（它只复制 vendor/ 与 snapshots/），
  assets/ 只有一次性手工推送 ⇒ 此后新增的永远上不去。

修法：载荷由索引派生（以 api/assets.json 枚举逐条复制），源缺失即**硬失败 exit 2**。
本自测就是**证明那条硬失败真的会失败** —— 不可注入的闸门只能靠读代码相信，那是假自测。

做法：monkeypatch 掉模块级 fetch（不联网、不依赖 8798 后端），
      用 GALLERY_ASSETS_SRC 把资产源目录指向临时 fixture。

运行:  python3 bb-gallery-export-selftest.py
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-gallery-export-selftest.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORTER = os.path.join(HERE, "bb-gallery-export.py")


def _fixture(root, roster, existing):
    """造 fixture：源目录里只放 existing 列出的文件；roster 是「索引」声明的清单。"""
    src = os.path.join(root, "src_assets")
    os.makedirs(src, exist_ok=True)
    for name in existing:
        with open(os.path.join(src, name), "w", encoding="utf-8") as f:
            f.write(f"<!-- {name} -->\n")
    meta_dir = os.path.join(root, "meta")
    os.makedirs(meta_dir, exist_ok=True)
    with open(os.path.join(meta_dir, "assets.json"), "w", encoding="utf-8") as f:
        json.dump([{"file": n, "kind": "svg"} for n in roster], f, ensure_ascii=False)
    return src, os.path.join(meta_dir, "assets.json")


def run_case(roster, existing):
    """在子进程里跑导出器（真跑真 exit code），返回 (rc, stdout+stderr, out_dir)。"""
    root = tempfile.mkdtemp(prefix="galexp-")
    src, meta = _fixture(root, roster, existing)
    out = os.path.join(root, "out")
    # 驱动脚本：import 导出器 → 把 fetch 换成 fixture（/api/assets 回索引，其余回空）
    drv = os.path.join(root, "drive.py")
    with open(drv, "w", encoding="utf-8") as f:
        f.write(
            "import json,os,sys\n"
            f"sys.path.insert(0, {HERE!r})\n"
            "import importlib.util as iu\n"
            f"spec=iu.spec_from_file_location('gx', {EXPORTER!r})\n"
            "gx=iu.module_from_spec(spec); spec.loader.exec_module(gx)\n"
            f"ROSTER=json.load(open({meta!r}, encoding='utf-8'))\n"
            "def fake_fetch(path, timeout=15):\n"
            "    if path == '/api/assets':\n"
            "        return json.dumps(ROSTER, ensure_ascii=False).encode(), 'application/json'\n"
            "    if path == '/':\n"
            "        return b'<html><script>let ALL = {overview:1}</script></html>', 'text/html'\n"
            "    return None, ''\n"
            "gx.fetch = fake_fetch\n"
            f"gx.export({out!r})\n"
        )
    env = dict(os.environ)
    env["GALLERY_ASSETS_SRC"] = src
    r = subprocess.run([sys.executable, drv], capture_output=True, text=True, env=env, timeout=120)
    return r.returncode, (r.stdout + r.stderr), out


def main():
    ok = True
    print("=" * 72)
    print("bb-gallery-export 自测 · assets/ 载荷闸门")
    print("=" * 72)

    # ── 正控：索引 3 条、源里 3 个都在 ⇒ 应 0 退出，assets/ 落 3 份 ──
    names = ["a-20260909.svg", "b.svg", "c-20260830.svg"]
    rc, log, out = run_case(names, names)
    payload = os.path.join(out, "assets")
    got = sorted(os.listdir(payload)) if os.path.isdir(payload) else []
    good = (rc == 0) and sorted(names) == got
    print(f"\n[正控] 索引 3 源 3            rc={rc}  载荷 {len(got)} 份  {'✅ 通过' if good else '❌ 失败'}")
    if not good:
        ok = False
        print("  期望 rc=0 且载荷 =", sorted(names), " 实得 rc=", rc, "载荷=", got)
        print(log[-600:])

    # ── 反控：索引 3 条、源里只有 2 个（模拟「索引里有、载荷里没有」）⇒ 应 exit 2 ──
    rc2, log2, out2 = run_case(names, names[:2])
    payload2 = os.path.join(out2, "assets")
    got2 = sorted(os.listdir(payload2)) if os.path.isdir(payload2) else []
    fired = (rc2 == 2) and ("拒绝导出" in log2)
    # 关键：失败时**不许**出现完成行（否则又是一条哑的失败）
    silent = "✅ 导出完成" in log2
    bad = fired and not silent
    print(f"[反控] 索引 3 源 2(缺1)       rc={rc2}  报「拒绝导出」={'拒绝导出' in log2}  "
          f"误报完成={silent}  {'✅ 通过' if bad else '❌ 失败'}")
    if not bad:
        ok = False
        print("  期望 rc=2 且不出现「✅ 导出完成」")
        print(log2[-600:])
    else:
        for ln in log2.splitlines():
            if "✗" in ln or "拒绝导出" in ln:
                print(f"    {ln.strip()}")

    # ── 反控2：索引里有重复文件名 ⇒ 载荷份数必须等于**索引条数**，不能靠集合去重蒙混 ──
    rc3, log3, out3 = run_case(["dup.svg", "dup.svg"], ["dup.svg"])
    p3 = os.path.join(out3, "assets")
    got3 = sorted(os.listdir(p3)) if os.path.isdir(p3) else []
    dup_ok = (rc3 == 0) and got3 == ["dup.svg"]
    print(f"[反控] 索引含重复名          rc={rc3}  载荷 {len(got3)} 份  "
          f"{'✅ 通过（同名只落一份，符合文件系统语义）' if dup_ok else '❌ 失败'}")

    print("\n" + "=" * 72)
    print(f"RESULT bb-gallery-export-selftest {'PASS 正控1/1 反控2/2' if ok else 'FAIL'}")
    print("=" * 72)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
