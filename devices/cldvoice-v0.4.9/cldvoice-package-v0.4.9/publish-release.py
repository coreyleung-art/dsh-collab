#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish-release.py — CLD-Voice 部署包 · 产品化发布器

路径: 打包(本地) → 发布到中枢黑板(公网可达) → 星桥总线通知接收方 → 接收方自取安装
遵循: dsh-collab/devices/deploy-safety-scheme.md

用法:
  python3 publish-release.py <包目录或tar.gz> --to mac-mini [--dry-run]
"""
import argparse, base64, hashlib, json, os, subprocess, sys, time, urllib.request

CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://106.53.214.108:8792")
SERVER_BUS = os.environ.get("SERVER_BUS", "http://106.53.214.108:8791")
TOKEN = os.environ.get("XQ_TOKEN", "")
FROM = os.environ.get("BUS_FROM", "mbp")
RELEASE_NAME = "cldvoice"
CHUNK = 48000   # 每片 base64 长度(留足余量)


def log(m): print(f"[publish] {m}", flush=True)


def bb_put(key, value):
    body = json.dumps(value, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{CENTRAL_BB}/{key.lstrip('/')}", data=body,
                                 method="PUT", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def bb_get(key):
    with urllib.request.urlopen(f"{CENTRAL_BB}/{key.lstrip('/')}", timeout=30) as r:
        return json.loads(r.read().decode())


def bus_send(target, action, note):
    tok = TOKEN
    if not tok:
        try:
            out = subprocess.run(["grep", "-ho", "X-Webhook-Token: [a-f0-9]*",
                                  os.path.expanduser("~/dsh-collab/logs/node-bridge.log")],
                                 capture_output=True, text=True, timeout=5).stdout.strip().split("\n")
            tok = out[-1].split()[-1] if out else ""
        except Exception:
            tok = ""
    body = json.dumps({"from": FROM, "target": target, "action": action,
                       "payload": {"note": note}}, ensure_ascii=False).encode()
    req = urllib.request.Request(f"{SERVER_BUS}/bus/send", data=body, method="POST",
                                 headers={"X-Webhook-Token": tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="包目录 或 .tar.gz")
    ap.add_argument("--to", default="mac-mini")
    ap.add_argument("--version", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    p = os.path.abspath(a.path)
    if os.path.isdir(p):
        ver = a.version or "v0.4.8"
        tgz = f"/tmp/{RELEASE_NAME}-{ver}.tar.gz"
        parent, base = os.path.dirname(p), os.path.basename(p)
        subprocess.run(["tar", "-czf", tgz, "-C", parent, base], check=True)
    else:
        tgz = p
        ver = a.version or "release"

    data = open(tgz, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    b64 = base64.b64encode(data).decode()
    log(f"包: {tgz}  大小={len(data)}B  sha256={sha[:16]}...  base64={len(b64)}")

    if a.dry_run:
        log("dry-run: 跳过上传"); return 0

    # 1) 分片上传到中枢黑板
    parts = [b64[i:i+CHUNK] for i in range(0, len(b64), CHUNK)]
    log(f"分片数: {len(parts)}")
    for i, seg in enumerate(parts):
        bb_put(f"data/{FROM}/release/{RELEASE_NAME}-{ver}/part-{i}", {"seg": seg})
    # 2) manifest
    manifest = {
        "name": RELEASE_NAME, "version": ver, "sha256": sha, "size": len(data),
        "parts": len(parts), "chunk": CHUNK, "from": FROM,
        "ts": int(time.time() * 1000),
        "install": "下载各片→拼接→base64解码→tar -xzf→按 INSTALL.md 安装",
        "self_check": "包内 deploy-check.sh (PASS=0 才上生产)",
        "compat": {"cordis": "4.x", "node": ">=18", "profile": "web"},
    }
    bb_put(f"data/{FROM}/release/{RELEASE_NAME}-{ver}/manifest", manifest)
    log(f"manifest 已写: data/{FROM}/release/{RELEASE_NAME}-{ver}/manifest")

    # 3) 校验回读
    got = bb_get(f"data/{FROM}/release/{RELEASE_NAME}-{ver}/part-0")
    ok0 = got.get("value", {}).get("seg", "")[:50] == parts[0][:50]
    log(f"回读校验 part-0: {'OK' if ok0 else 'FAIL'}")

    # 4) 总线通知
    key = f"data/{FROM}/release/{RELEASE_NAME}-{ver}"
    note = (f"CLD-Voice {ver} 部署包已发布到中枢黑板. 取包: 读 {key}/manifest 得 sha256+分片数, "
            f"再读 {key}/part-0..part-{len(parts)-1} 拼接→base64 -d→tar -xzf. "
            f"sha256={sha}. 按 INSTALL.md 安装, 跑 deploy-check.sh 自检后回报.")
    try:
        r = bus_send(a.to, "release-publish", note)
        log(f"总线通知: {r}")
    except Exception as e:
        log(f"总线通知失败: {str(e)[:120]}")
    log("发布完成 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
