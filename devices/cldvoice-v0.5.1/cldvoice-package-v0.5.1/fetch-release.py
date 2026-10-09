#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-release.py — CLD-Voice 部署包 · 接收方一键取包

从星桥中枢黑板取回发布包(分片拼接→校验 sha256→解包)。
用法:
  python3 fetch-release.py --name cldvoice --version v0.4.8 [--from mbp] --out /tmp
"""
import argparse, base64, hashlib, json, os, subprocess, sys, urllib.request

CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://106.53.214.108:8792")


def get(key):
    with urllib.request.urlopen(f"{CENTRAL_BB}/{key.lstrip('/')}", timeout=30) as r:
        return json.loads(r.read().decode())["value"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="cldvoice")
    ap.add_argument("--version", default="v0.4.8")
    ap.add_argument("--from", dest="frm", default="mbp")
    ap.add_argument("--out", default="/tmp")
    a = ap.parse_args()

    key = f"data/{a.frm}/release/{a.name}-{a.version}"
    print(f"[fetch] 读 manifest: {key}/manifest")
    man = get(key + "/manifest")
    print(f"[fetch] {man['name']} {man['version']}  sha256={man['sha256'][:16]}...  {man['parts']} 片")

    b64 = ""
    for i in range(man["parts"]):
        seg = get(f"{key}/part-{i}")["seg"]
        b64 += seg
        print(f"  取片 part-{i}: {len(seg)} 字符")

    data = base64.b64decode(b64)
    sha = hashlib.sha256(data).hexdigest()
    if sha != man["sha256"]:
        print(f"[fetch] ❌ sha256 不匹配({sha[:16]} != {man['sha256'][:16]}) — 取包失败")
        return 1
    print(f"[fetch] ✅ sha256 校验通过")

    os.makedirs(a.out, exist_ok=True)
    out = os.path.join(a.out, f"{a.name}-{a.version}.tar.gz")
    open(out, "wb").write(data)
    dest = os.path.join(a.out, f"{a.name}-{a.version}")
    os.makedirs(dest, exist_ok=True)
    subprocess.run(["tar", "-xzf", out, "-C", dest], check=True)
    print(f"[fetch] ✅ 已解包到: {dest}")
    print(f"[fetch] 下一步: cd {dest}/*; 按 INSTALL.md 安装; 跑 ./deploy-check.sh 自检后回报")
    return 0


if __name__ == "__main__":
    sys.exit(main())
