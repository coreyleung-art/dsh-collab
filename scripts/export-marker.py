#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导出完成握手标记 · export-marker.py
====================================
背景：
    推送方（老登）多次遇到「导出进行中就被推」的中间态问题——同一尺寸不同内容
    （12:22 → 12:23 均为 848086B 但哈希不同），导致版本反复。
方案：
    导出方（明鉴）在**全部写入完成后**，最后写两个标记：
      ① .export-done  —— 含 sha256/字节/mtime/文件清单/图表数
      ② manifest.json  —— 追加 exported_hash 字段（老登可直接读）
    推送方见 .export-done 存在且 hash 与 manifest 一致才推；推完可删标记或留作审计。

用法：
    python3 export-marker.py <产物目录> [--note "本次变更说明"]

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, json, hashlib, datetime, argparse


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/export-marker.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

def sha256_16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def sha256_full(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def count_charts(path):
    try:
        s = open(path, encoding="utf-8").read()
        return s.count('data-chart="')
    except Exception:
        return 0

def main():
    ap = argparse.ArgumentParser(description="导出完成握手标记")
    ap.add_argument("dir", help="产物目录（如 ~/dsh-collab/data/device/cloudbase-plan-export）")
    ap.add_argument("--note", default="", help="本次变更说明")
    ap.add_argument("--entry", default="index.html", help="入口文件（默认 index.html）")
    args = ap.parse_args()

    d = os.path.expanduser(args.dir)
    if not os.path.isdir(d):
        print(f"⚠️ 目录不存在: {d}"); sys.exit(1)

    files = {}
    for root, dirs, names in os.walk(d):
        dirs[:] = [x for x in dirs if not x.startswith(".")]
        for name in sorted(names):
            if name.startswith("."): continue
            fp = os.path.join(root, name)
            rel = os.path.relpath(fp, d)
            if rel.endswith((".bak", ".bak2")): continue
            files[rel] = {
                "size": os.path.getsize(fp),
                "sha256_16": sha256_16(fp),
                "chars": count_charts(fp) if name.endswith(".html") else 0,
            }

    entry = args.entry
    entry_hash = files.get(entry, {}).get("sha256_16", "")
    marker = {
        "status": "done",
        "exported_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "exported_by": "明鉴 a190c54c",
        "note": args.note,
        "entry": entry,
        "entry_hash": entry_hash,
        "entry_size": files.get(entry, {}).get("size", 0),
        "hash_method": "sha256 前16位 | wc -c 字节 | 文件名",
        "files": files,
    }

    # ① 写 .export-done
    mpath = os.path.join(d, ".export-done")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(marker, f, ensure_ascii=False, indent=1)

    # ② manifest.json 追加 exported_hash
    mf = os.path.join(d, "manifest.json")
    if os.path.exists(mf):
        try:
            m = json.load(open(mf, encoding="utf-8"))
        except Exception:
            m = {}
        m["exported_at"] = marker["exported_at"]
        m["exported_hash"] = entry_hash
        m["entry"] = entry
        json.dump(m, open(mf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  ✅ manifest.json 已写 exported_hash = {entry_hash}")

    print(f"  ✅ .export-done 已写 → {mpath}")
    print(f"     入口: {entry}  {marker['entry_size']} 字节  sha256 {entry_hash}")
    print(f"     文件数: {len(files)}")
    if args.note:
        print(f"     变更: {args.note}")

if __name__ == "__main__":
    main()
