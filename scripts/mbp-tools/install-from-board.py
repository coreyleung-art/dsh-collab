#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用：从黑板取包 → 验哈希/排除集/patch 在位 → 备份目标 → 覆盖安装 → 逐文件读回断言。

用法： install-from-board.py <板键> <目标插件目录> [--dry-run]
纪律：绝不 `--delete`（A 类）；排除 `.git/.bak/._/__pycache__`（H6）；逐文件 md5 读回（H38）；
      断言 `dsh.bundle.patch` 指向的文件在包内（G14）。
"""
import base64, datetime, hashlib, io, json, os, shutil, subprocess, sys, tarfile, tempfile

BASE = "http://xingqiao.meetfunbp.com:8792"
TOK = open(os.path.expanduser("~/.dsh/blackboard-token")).read().strip()
H = {"X-Blackboard-Token": TOK, "Authorization": "Bearer " + TOK}


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    key, target = sys.argv[1], os.path.expanduser(sys.argv[2])
    dry = "--dry-run" in sys.argv

    import urllib.request
    d = json.load(urllib.request.urlopen(urllib.request.Request(BASE + "/" + key, headers=H), timeout=40))
    v = d.get("value", {}); v = v.get("value", v) if isinstance(v, dict) else v
    raw = base64.b64decode(v["b64"])
    sha = hashlib.sha256(raw).hexdigest()
    print("包: %s\n  %d 字节  sha256=%s" % (key, len(raw), sha))
    print("  载荷自述: bytes=%s sha256=%s files=%s" % (v.get("bytes"), str(v.get("sha256"))[:16], len(v.get("files") or [])))
    if v.get("sha256") and not str(v["sha256"]).startswith(sha[:16]):
        print("  ⚠️ 载荷自述 sha256 与我复算不一致 —— 停"); return 1
    if v.get("bytes") and int(v["bytes"]) != len(raw):
        print("  ⚠️ 载荷自述字节数不一致 —— 停"); return 1

    tmp = tempfile.mkdtemp(prefix="pkg-")
    tgz = os.path.join(tmp, "p.tgz")
    open(tgz, "wb").write(raw)
    ex = os.path.join(tmp, "x"); os.makedirs(ex)
    with tarfile.open(tgz) as tf:
        names = tf.getnames()
        bad = [n for n in names if any(x in n for x in (".git/", ".bak", "._", "__pycache__"))]
        tf.extractall(ex)
    print("  tar 条目 %d；排除集命中 %d %s" % (len(names), len(bad), bad[:3]))
    if bad:
        print("  ⚠️ 包内含排除集成员 —— 停"); return 1

    # 定位包根（tar 可能带一层目录）
    root = ex
    subs = [n for n in os.listdir(ex) if os.path.isdir(os.path.join(ex, n))]
    if len(subs) == 1 and not os.path.isfile(os.path.join(ex, "package.json")):
        root = os.path.join(ex, subs[0])
    pj = os.path.join(root, "package.json")
    ver = json.load(open(pj, encoding="utf-8")).get("version") if os.path.isfile(pj) else None
    patch = None
    if os.path.isfile(pj):
        patch = (json.load(open(pj, encoding="utf-8")).get("dsh") or {}).get("bundle", {}).get("patch")
    patch_ok = bool(patch) and os.path.isfile(os.path.join(root, patch.lstrip("./")))
    print("  version=%s  dsh.bundle.patch=%s  在位=%s" % (ver, patch, patch_ok))
    if patch and not patch_ok:
        print("  ⚠️ 声明了 patch 但包内没有 —— 停（G14）"); return 1

    files = []
    for r, _, fs in os.walk(root):
        for n in fs:
            files.append(os.path.relpath(os.path.join(r, n), root))
    files.sort()

    if dry:
        print("  [dry-run] 将安装 %d 个文件到 %s" % (len(files), target)); return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = os.path.expanduser("~/dsh-collab/data/backups/") + os.path.basename(target) + ".pre-" + str(ver) + "-" + stamp
    shutil.copytree(target, bak)
    print("  备份 → %s（%d 文件）" % (bak, sum(len(f) for _, _, f in os.walk(bak))))

    for f in files:
        src, dst = os.path.join(root, f), os.path.join(target, f)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    print("  覆盖 %d 个文件" % len(files))

    bad2 = []
    for f in files:
        a = hashlib.md5(open(os.path.join(root, f), "rb").read()).hexdigest()
        b = hashlib.md5(open(os.path.join(target, f), "rb").read()).hexdigest()
        if a != b: bad2.append(f)
    print("  逐文件读回断言: %s" % ("✅ 全部一致" if not bad2 else "❌ 不一致 %s" % bad2))
    leftover = [f for r, _, fs in os.walk(target) for f in fs if ".bak" in f]
    print("  包内残留 .bak: %s" % (leftover or "无 ✅"))
    print("\n  ⇒ %s" % ("✅ 安装完成" if not bad2 and not leftover else "❌ 有断言失败，请回滚: cp -R %s/* %s/" % (bak, target)))
    return 0 if (not bad2 and not leftover) else 1


if __name__ == "__main__":
    sys.exit(main())
