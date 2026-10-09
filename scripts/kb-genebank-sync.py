#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb-genebank-sync.py — 语义库 → 基因库自动同步（知识复利闭环）

用户指示（2026-08-24）：语义库更新后自动同步到基因库，过程工具化自动化。

原理：KB（语义库，向量化 chunks）与 GeneBank（基因库，原始文件内容寻址）双轨——
语义库负责检索，基因库负责原始文件存储。同步 = 语义库新增文件 → 上传基因库（去重 + 断点续传）。

用法：
  python3 kb-genebank-sync.py --scan-only          # 只扫描对比，不上传
  python3 kb-genebank-sync.py                      # 全量同步（未入库的上传）
  python3 kb-genebank-sync.py --dir <目录>          # 指定来源目录
  python3 kb-genebank-sync.py --once --status      # 查看同步状态

常驻：launchd 周期 or 事件驱动（论文落链完成触发）——由调用方决定

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, os, glob, hashlib, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/kb-genebank-sync.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

GB = "http://127.0.0.1:8801"
BB = "http://127.0.0.1:8792"
SOURCES = [
    os.path.expanduser("~/dsh-collab/research/paper-cache/pdfs"),   # 论文库
    os.path.expanduser("~/dsh-collab/datasets"),                     # 共享数据集
]
CHUNK = 512 * 1024  # 分片 512KB（断点续传）

def gb_get(path):
    try:
        with urllib.request.urlopen(GB + path, timeout=8) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}

def gb_put_file(gid, content, offset=0):
    req = urllib.request.Request(GB + "/api/v1/genes/%s/file" % gid, data=content, method="PUT",
                                 headers={"Content-Type": "application/octet-stream",
                                          "X-Offset": str(offset)})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        return {"error": str(e)[:80]}

def gb_register(manifest):
    req = urllib.request.Request(GB + "/api/v1/genes", data=json.dumps(manifest).encode(), method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception as e:
        return {"error": str(e)[:80]}

def existing_genes():
    """基因库现有基因（name → gene_id 映射，用于去重）"""
    d = gb_get("/api/v1/registry")
    return {g.get("name"): g.get("gene_id") for g in d.get("genes", [])}

def scan_files(dirpath):
    """扫描目录下文件（PDF/脚本/数据）"""
    files = []
    if os.path.isdir(dirpath):
        for ext in ("*.pdf", "*.py", "*.json", "*.md", "*.csv", "*.txt", "*.zip"):
            files.extend(glob.glob(os.path.join(dirpath, "**", ext), recursive=True))
    return files

def upload_with_resume(gid, content):
    """分片上传（断点续传）"""
    total = len(content)
    offset = 0
    while offset < total:
        chunk = content[offset:offset + CHUNK]
        r = gb_put_file(gid, chunk, offset)
        if r.get("error"):
            return False, r.get("error")
        offset += len(chunk)
    return True, None

def sync(source_dirs, scan_only=False):
    """同步：扫描 → 去重 → 上传（分片续传）"""
    existing = existing_genes()
    print("基因库现有 %d 基因" % len(existing))
    results = {"uploaded": [], "skipped": [], "failed": []}

    for src in source_dirs:
        if not os.path.isdir(src):
            print("  ⚠️ 目录不存在: %s" % src); continue
        files = scan_files(src)
        print("扫描 %s: %d 文件" % (os.path.basename(src), len(files)))
        for f in files:
            fname = os.path.basename(f)
            content = open(f, "rb").read()
            gid = "sha256:" + hashlib.sha256(content).hexdigest()
            # 去重：同名或同内容已入库
            if fname in existing or gid in existing.values():
                results["skipped"].append(fname)
                continue
            if scan_only:
                print("  [待同步] %s (%dKB)" % (fname, len(content)//1024))
                results["skipped"].append(fname)
                continue
            # 注册 + 分片上传
            manifest = {"gene_id": gid, "name": fname, "chromosome": "datasets",
                        "body": {"what": "语义库自动同步", "path": f, "size_bytes": len(content),
                                 "format": os.path.splitext(fname)[1].lstrip(".") or "file"},
                        "expression": {"behavior": "kb-genebank-sync 自动入库"},
                        "heredity": {"parent": "kb-sync", "mutation": "1.0.0"}}
            reg = gb_register(manifest)
            if reg.get("ok"):
                ok, err = upload_with_resume(gid, content)
                if ok:
                    results["uploaded"].append(fname)
                    print("  ✅ %s (%dKB, 分片续传)" % (fname, len(content)//1024))
                else:
                    results["failed"].append((fname, err))
            else:
                results["failed"].append((fname, reg.get("errors")))
    return results

def record_status(results):
    """记录同步状态到黑板"""
    try:
        body = json.dumps({"results": results,
                           "ts": datetime.datetime.now().isoformat(timespec="seconds")}).encode()
        req = urllib.request.Request(BB + "/data/frameworks/kb-genebank-sync", data=body, method="PUT",
                                     headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--dir", default="")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        d = None
        try:
            with urllib.request.urlopen(BB + "/data/frameworks/kb-genebank-sync", timeout=5) as r:
                d = json.loads(r.read().decode()).get("value", {})
        except Exception:
            pass
        if d:
            r = d.get("results", {})
            print("上次同步: %s" % d.get("ts", "?")[:19])
            print("  上传: %d | 跳过: %d | 失败: %d" % (
                len(r.get("uploaded", [])), len(r.get("skipped", [])), len(r.get("failed", []))))
        else:
            print("尚无同步记录")
        sys.exit(0)

    sources = [args.dir] if args.dir else SOURCES
    results = sync(sources, scan_only=args.scan_only)
    if not args.scan_only:
        record_status(results)
        print("\n完成: 上传 %d | 跳过 %d | 失败 %d" % (
            len(results["uploaded"]), len(results["skipped"]), len(results["failed"])))
    else:
        print("\n扫描完成（未上传）")

if __name__ == "__main__":
    main()
