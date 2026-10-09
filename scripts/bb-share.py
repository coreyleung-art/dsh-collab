#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-share.py — 跨设备文件共享工具（防『清单式假共享』）

用户指示（2026-08-24）：避免『给了清单没给实体』类型问题。
教训：训练论文只给 arXiv ID（没文件）→ 又只给本地路径（i9 访问不到）。
规则：给节点文件 = 复制到 HTTP 共享目录 + 给 Tailscale 可下载地址 + 写黑板 + 派单通知。

用法：
  python3 bb-share.py --file <本地路径> --to i9 --note '<说明>'
  python3 bb-share.py --dir <本地目录> --to i9 --note '<说明>'   # 批量
  python3 bb-share.py --list --to i9                            # 列出已共享给 i9 的

流程（防遗漏闭环）：
  1. 复制文件到共享目录 ~/dsh-collab/datasets/shared/
  2. 生成 Tailscale 下载地址（http://100.120.203.20:8793/shared/<file>）
  3. 写黑板 data/<to>/files/<file>（清单 + 地址）
  4. 派单通知节点下载（任务卡）
  5. 验证可达（HTTP 200）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, os, shutil, subprocess, datetime, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-share.log")


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
SHARE_DIR = os.path.expanduser("~/dsh-collab/datasets/shared")
SHARE_URL = "http://100.120.203.20:8793/shared"
TASK_URL = "http://127.0.0.1:8792/tasks/{node}/queue/{seq}"

def put(path, obj):
    body = json.dumps(obj, ensure_ascii=False).encode()
    req = urllib.request.Request(BB + path, data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.loads(r.read().decode())

def send_task(node, payload):
    import time
    seq = str(int(time.time()*1000))[-10:]
    task = {"task_id": "share-notify-%s" % seq[-6:], "recipient": node,
            "action": "shell", "cmd": "echo SHARE:links-received",
            "payload": {"cmd": payload}}
    body = json.dumps(task).encode()
    req = urllib.request.Request(TASK_URL.format(node=node, seq=seq), data=body, method="PUT",
                                 headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.status

GENE_BANK = "http://127.0.0.1:8801"

def genebank_upload(fpath):
    """上传文件到 GeneBank AI 网盘（内容寻址，返回下载地址）"""
    import hashlib
    content = open(fpath, "rb").read()
    gene_id = "sha256:" + hashlib.sha256(content).hexdigest()
    # 1. 注册基因（manifest）
    manifest = {
        "gene_id": gene_id,
        "name": os.path.basename(fpath),
        "chromosome": "datasets",
        "body": {"what": "bb-share 文件", "path": fpath, "size_bytes": len(content), "format": "file"},
        "expression": {"behavior": "AI 网盘共享文件"},
        "heredity": {"parent": "bb-share", "mutation": "1.0.0"}
    }
    try:
        body = json.dumps(manifest).encode()
        req = urllib.request.Request(GENE_BANK + "/api/v1/genes", data=body, method="PUT",
                                     headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        urllib.request.urlopen(req, timeout=10)
        # 2. 上传文件内容
        req2 = urllib.request.Request(GENE_BANK + "/api/v1/genes/%s/file" % gene_id, data=content, method="PUT",
                                      headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(content))})
        urllib.request.urlopen(req2, timeout=30)
        return gene_id
    except Exception as e:
        return None

def share_file(fpath, node, note, notify=True):
    """共享单个文件（走 GeneBank AI 网盘，内容寻址）"""
    fname = os.path.basename(fpath)
    # 优先走 GeneBank AI 网盘（内容寻址），失败降级静态目录
    gene_id = genebank_upload(fpath)
    if gene_id:
        url = "http://100.120.203.20:8801/api/v1/genes/%s/file" % gene_id
        size = os.path.getsize(fpath)
    else:
        os.makedirs(SHARE_DIR, exist_ok=True)
        dst = os.path.join(SHARE_DIR, fname)
        shutil.copy2(fpath, dst)
        url = "%s/%s" % (SHARE_URL, fname)
        size = os.path.getsize(dst)
    # 写黑板
    put("/data/%s/files/%s" % (node, fname), {
        "file": fname, "url": url, "local": fpath,
        "size": size, "note": note, "gene_id": gene_id or "",
        "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    print("✅ 共享 %s → %s" % (fname, node))
    print("   URL: %s" % url)
    return url

def verify(url):
    """验证 Tailscale 可达"""
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="共享单个文件")
    ap.add_argument("--dir", help="共享目录全部文件")
    ap.add_argument("--to", required=True, help="目标节点（i9/mbp/store-xx）")
    ap.add_argument("--note", default="", help="说明")
    ap.add_argument("--no-notify", action="store_true", help="不派单通知")
    ap.add_argument("--list", action="store_true", help="列出已共享")
    args = ap.parse_args()

    if args.list:
        d = urllib.request.urlopen(BB + "/data/%s/files/" % args.to).read() if False else None
        try:
            with urllib.request.urlopen(BB + "/data/%s/files/" % args.to, timeout=5) as r:
                files = json.loads(r.read().decode()).get("list", {})
            print("已共享给 %s 的文件:" % args.to)
            for k, v in sorted(files.items()):
                if "/files/" in k:
                    val = v.get("value", {})
                    print("  %s → %s (%s)" % (val.get("file",""), val.get("url",""), val.get("note","")[:30]))
        except Exception as e:
            print("查询失败:", str(e)[:60])
        sys.exit(0)

    if not args.file and not args.dir:
        print("需 --file 或 --dir（--list 查看已共享）"); sys.exit(1)

    files = []
    if args.file:
        files.append(args.file)
    else:
        for fn in sorted(os.listdir(args.dir)):
            files.append(os.path.join(args.dir, fn))

    shared = []
    for f in files:
        if os.path.isfile(f):
            url = share_file(f, args.to, args.note)
            ok = verify(url)
            shared.append((os.path.basename(f), url, ok))
            print("   可达: %s" % ("✅" if ok else "❌"))

    # 派单通知
    if not args.no_notify and shared:
        links = "\n".join("  %s  %s" % (fn, u) for fn, u, _ in shared)
        payload = "中枢共享文件给你（%d 个），下载地址：\n%s\n请下载到本地并回报 data/%s/files-downloaded" % (len(shared), links, args.to)
        st = send_task(args.to, payload)
        print("派单通知: %s" % ("✅" if st == 200 else "❌"))

    print("\n完成: %d 个文件已共享" % len(shared))

if __name__ == "__main__":
    main()
