#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冻结快照器 —— 按裁判 addendum-2 授的五条判据实现

判据来源
    audits/20261009/starbridge-stage-review-addendum-2.md（sha256[0:16] c7cb0e12702423e7）
    裁判原文：「它需要判据，否则会重演 49 秒失效」

五条判据（逐条落实）
    ① 副本须落**不同目录**（不得原地冻结）
    ② **只读属性**（0444）
    ③ hash / 字节 / **mtime 三者齐备**
    ④ manifest **分列**「快照路径」与「生产路径当前值」
    ⑤ ★ **引用者（信息包）自身 mtime 须 ≥ 所有被引用快照 mtime**
       —— 可机械检验：`stat -f '%m %N'` 排序，末行应是引用者

本脚本的副作用（自我声明，回应 N6）
    写：<outdir>/ 下的副本与 manifest.json
    不写：任何被冻结的源文件（只读源，从不回写）
    不执行子进程（除 shasum）
"""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import datetime
from pathlib import Path

# 归属说明（2026-10-09）：**判据来源 = 裁判 addendum-2（五条），实现可移植**；
#   保留理由：它冻结的**对象是我方交付物** ⇒ 我方仍需它冻结自己的产物。
#   可移交：五判据的断言实现 + 判据⑤机械检验 + **可重入性**（跑前统一解冻）。
#   登记：blackboard:data/registry/audit-tool-handover

HOME = Path.home()
COLLAB = HOME / "dsh-collab"


def sha256_16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print("用法: freeze-snapshot.py <outdir> <file...> [--verify <referrer>]")
        print("  例: freeze-snapshot.py audits/20261009/frozen-snapshot-v1 \\")
        print("        data/registry/a.json tools/b.py --verify docs/info-package.md")
        sys.exit(2)

    outdir = Path(os.path.expanduser(args[0]))
    files = args[1:]
    referrer = None
    if "--verify" in sys.argv:
        referrer = sys.argv[sys.argv.index("--verify") + 1]

    # ① 落不同目录：禁止输出目录与任何源文件同目录（原地冻结）
    outdir.mkdir(parents=True, exist_ok=True)

    # ★★ 可重入的**不变量修复**（X15 · 半修形态③的自纠）：
    #   上一轮我为「副本无法覆盖」补了一个**站点**修复（见下 dst.exists 分支），
    #   但 manifest.json 同样被 chmod 0444 ⇒ 重跑时 write_text 仍 PermissionError。
    #   ⇒ 站点修复只治了一个症状。此处改为**根除**：跑之前把 outdir 下所有已存在文件恢复写权限。
    _unfrozen = 0
    for _p in outdir.rglob("*"):
        if _p.is_file():
            try:
                os.chmod(_p, stat.S_IWUSR | stat.S_IRUSR)
                _unfrozen += 1
            except OSError:
                pass
    if _unfrozen:
        print("（可重入）已恢复 %d 个既有快照文件的写权限，本次将覆盖" % _unfrozen)

    for f in files:
        fp = Path(os.path.expanduser(f))
        if fp.parent.resolve() == outdir.resolve():
            print("✗ 判据①违反：%s 与输出目录同目录（原地冻结）" % f)
            sys.exit(1)

    rows = []
    for f in files:
        src = Path(os.path.expanduser(f))
        if not src.exists():
            rows.append({"source": f, "status": "MISSING"})
            continue
        rel = str(src.resolve()).replace(str(COLLAB) + "/", "")
        dst = outdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # ★ 可重入修复（X14）：上一轮已把副本 chmod 0444 ⇒ 直接 copy2 会 PermissionError。
        #   故先恢复写权限再删。首次运行此分支不触发。
        if dst.exists():
            os.chmod(dst, stat.S_IWUSR | stat.S_IRUSR)
            dst.unlink()
        shutil.copy2(src, dst)                       # 保留 mtime
        st_src = src.stat()
        # ② 只读属性
        os.chmod(dst, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        rows.append({
            "source": f,
            "snapshot": str(dst),
            "sha256_16": sha256_16(src),             # ③ hash
            "bytes": st_src.st_size,                 # ③ 字节
            "source_mtime": int(st_src.st_mtime),    # ③ mtime
            "snapshot_mtime": int(dst.stat().st_mtime),
            "mode": oct(stat.S_IMODE(dst.stat().st_mode)),
            "status": "frozen",
        })

    manifest = {
        "schema": "frozen-snapshot/v1",
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "criteria_source": "audits/20261009/starbridge-stage-review-addendum-2.md (sha256[0:16] c7cb0e12702423e7)",
        "criteria": [
            "① 落不同目录（不得原地冻结）",
            "② 只读属性",
            "③ hash/字节/mtime 三者齐备",
            "④ manifest 分列快照路径与生产路径当前值",
            "⑤ 引用者自身 mtime ≥ 所有被引用快照 mtime（可机械检验）",
        ],
        "outdir": str(outdir),
        "referrer": referrer,
        "count": len([r for r in rows if r.get("status") == "frozen"]),
        "items": rows,
    }

    # ④ 分列「生产路径当前值」—— 冻结后重测，用于检出「快照后源又变了」
    drift = []
    for r in rows:
        if r.get("status") != "frozen":
            continue
        cur = Path(os.path.expanduser(r["source"]))
        now_h = sha256_16(cur)
        now_m = int(cur.stat().st_mtime)
        r["live_path_current"] = {"sha256_16": now_h, "mtime": now_m}
        if now_h != r["sha256_16"] or now_m != r["source_mtime"]:
            drift.append(r["source"])
    manifest["drift_since_freeze"] = drift

    mf = outdir / "manifest.json"
    mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(mf, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    print("快照目录: %s" % outdir)
    print("冻结项数: %d" % manifest["count"])
    if drift:
        print("★ 冻结后源又变: %s" % drift)
    else:
        print("冻结后源零漂移 ✓")

    # ⑤ 机械检验：mtime 排序，引用者应在末
    if referrer:
        rp = Path(os.path.expanduser(referrer))
        if not rp.exists():
            print("✗ 引用者不存在: %s" % referrer)
            sys.exit(1)
        items = [(r["snapshot_mtime"], r["snapshot"]) for r in rows if r.get("status") == "frozen"]
        items.append((int(rp.stat().st_mtime), str(rp)))
        items.sort()
        mx_snap = max(r["snapshot_mtime"] for r in rows if r.get("status") == "frozen")
        ref_m = int(rp.stat().st_mtime)
        print()
        print("判据⑤ 机械检验（mtime 升序，末行应为引用者）:")
        for m, p in items[-4:]:
            mark = " ← 引用者" if p == str(rp) else ""
            print("  %d  %s%s" % (m, p, mark))
        if ref_m >= mx_snap:
            print("⇒ ✅ 判据⑤ 成立（引用者 mtime %d ≥ 快照最大 %d）" % (ref_m, mx_snap))
        else:
            print("⇒ ❌ 判据⑤ 不成立（引用者 %d < 快照最大 %d）⇒ **须在快照之后重写引用者**" % (ref_m, mx_snap))
            sys.exit(3)


if __name__ == "__main__":
    main()
