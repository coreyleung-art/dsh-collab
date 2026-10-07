#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从对端取 0.2.11 到暂存区（**不安装**），逐文件 sha256 + 排除集 + 读回断言。

纪律来源：
  · H6/§4.2：**排除** `.bak*`、`.git`、`._*`、`__pycache__`
  · G14：`dsh.bundle.patch` 指向的文件（`cordis.patch.yml`）**必须**在交付集里
  · H38：交付必须**逐文件哈希**并**读回复算**
"""
import hashlib, os, subprocess, sys

PEER_DIR = "~/.dsh/profiles/web/node_modules/dsh-plugin-central-inbox"
HOST = "coreyleung@100.120.203.20"
STAGE = os.path.expanduser("~/dsh-collab/data/packages/staging-central-inbox-0.2.11")

FILES = ["package.json", "cordis.patch.yml", "CHANGELOG.md", "README.md", "cli.js", ".gitignore",
         "lib/index.js", "lib/route.js", "lib/selftest.js", "lib/selfcheck.js",
         "lib/adapt.js", "lib/index.d.ts"]


def sh(cmd):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, cmd],
                       capture_output=True)
    return r.returncode, r.stdout, r.stderr


os.makedirs(STAGE, exist_ok=True)
print("暂存区:", STAGE)
rows = []
for f in FILES:
    dst = os.path.join(STAGE, f)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    rc, out, err = sh("cat %s/%s" % (PEER_DIR, f))
    if rc != 0:
        print("  ⚠️ 取失败 %s: %s" % (f, (err or b"")[:80]))
        continue
    open(dst, "wb").write(out)
    h = hashlib.sha256(out).hexdigest()
    # 读回复算（H38）
    back = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    rows.append((f, len(out), h, h == back))

print("\n%-22s %8s  %-16s %s" % ("文件", "字节", "sha256(前16)", "读回一致"))
for f, n, h, ok in rows:
    print("%-22s %8d  %-16s %s" % (f, n, h[:16], "✅" if ok else "❌"))

# 排除集断言：暂存区不得混入 .bak/.git
bad = []
for r, ds, fs in os.walk(STAGE):
    for n in fs:
        if ".bak" in n or n.startswith("._") or "__pycache__" in r or "/.git/" in os.path.join(r, n):
            bad.append(os.path.relpath(os.path.join(r, n), STAGE))
print("\n排除集断言: %s" % ("✅ 干净（无 .bak/.git/._）" if not bad else "❌ 混入 %s" % bad))

# G14 断言
pj = os.path.join(STAGE, "package.json")
import json
d = json.load(open(pj, encoding="utf-8"))
patch = (d.get("dsh") or {}).get("bundle", {}).get("patch")
present = bool(patch) and os.path.isfile(os.path.join(STAGE, patch.lstrip("./")))
print("G14 断言: version=%s  dsh.bundle.patch=%s  在位=%s %s"
      % (d.get("version"), patch, present, "✅" if present else "❌"))
sys.exit(0 if (not bad and present and all(r[3] for r in rows)) else 1)
