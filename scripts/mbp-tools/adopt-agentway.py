#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adopt-agentway.py —— 从黑板取 agent-way 包并采纳（通用版，取代 adopt-agentway-1519.py）。

为什么泛化（Φ8「同一操作出现两次就工具化」）：
  1.5.19 与 1.5.20 都是「板取包 → 采纳 → /reload 生效」同一形态 ⇒ 参数化，避免每版复制脚本。

★ 内建纪律（每条都来自本项目的实测事故）：
  · **双头取包**：中枢读 `data/*` 键必须同时带 `X-Webhook-Token` **与** `X-Blackboard-Token`；
    只带后者会被板端当成「前缀查询」返回空列表 ⇒ 会误判「键不存在」（MBP 实踩）。
  · **完整性**：校验字节数与 sha256 前缀（对端声明值）。
  · **包内断言**：version 一致、`dsh.bundle.patch` 指向的文件**随包存在**（事故 #3/#4 的形态）。
  · **装后断言**：patch 文件**装后仍在**（本脚本 1.5.19 时补上的盲区）、逐文件读回 sha256 一致、无 `.bak` 残留。
  · **备份**：整个插件目录备份到 `data/backups/`，并打印回滚命令。

用法：
  python3 adopt-agentway.py --version 1.5.20 \
      --key data/packages/agent-way-1520-5d1b74b0.tgz-b64 \
      --size 75482 --sha-prefix 5d1b74b0
  （--size/--sha-prefix 可省略 ⇒ 只做结构断言，不校验对端声明值）
退出码：0=成功（磁盘 version 符合且无残留）｜1=断言失败（按打印路径回滚）
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request

BASE = "http://xingqiao.meetfunbp.com:8792"
TOK = open(os.path.expanduser("~/.dsh/blackboard-token"), encoding="utf-8").read().strip()
H = {
    "X-Webhook-Token": os.environ.get("BB_SECRET_PLACEHOLDER",""),
    "X-Blackboard-Token": TOK,
    "Bearer": TOK,
}
TGT = os.path.expanduser("~/.dsh/profiles/web/node_modules/dsh-plugin-agent-way")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--size", type=int, default=0)
    ap.add_argument("--sha-prefix", default="")
    ap.add_argument("--stamp", default=datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    a = ap.parse_args()
    fail = []
    pkg = "/tmp/agent-way-%s.tgz" % a.version.replace(".", "")

    # ① 取包（双头）
    raw = json.load(urllib.request.urlopen(urllib.request.Request(BASE + "/" + a.key, headers=H), timeout=60))
    v = raw.get("value", raw)
    v = v.get("value", v) if isinstance(v, dict) and "value" in v else v
    if not isinstance(v, dict) or "b64" not in v:
        print("❌ 取包失败（非 b64 值；**先检查是否漏了 X-Webhook-Token 头**）: %s"
              % json.dumps(raw, ensure_ascii=False)[:200])
        return 1
    open(pkg, "wb").write(base64.b64decode(v["b64"]))
    size, digest = os.path.getsize(pkg), sha(pkg)
    print("① 取包 %s\n   大小=%d B%s   sha256=%s…%s"
          % (a.key, size, "（声明 %d）" % a.size if a.size else "", digest[:8],
             "（声明 %s）" % a.sha_prefix if a.sha_prefix else ""))
    if a.size and size != a.size:
        fail.append("大小不符")
    if a.sha_prefix and not digest.startswith(a.sha_prefix):
        fail.append("sha256 前缀不符")

    # ② 解包 + 结构断言
    tmp = tempfile.mkdtemp(prefix="aw-%s-" % a.version)
    with tarfile.open(pkg) as tf:
        names = tf.getnames()
        tf.extractall(tmp)
    root = next((d for d, _, fs in os.walk(tmp) if "package.json" in fs), None)
    if root is None:
        print("❌ 包内找不到 package.json")
        return 1
    pj = json.load(open(os.path.join(root, "package.json"), encoding="utf-8"))
    patch_rel = (pj.get("dsh", {}).get("bundle", {}) or {}).get("patch") or ""
    print("② 条目 %d 个；包内 version=%s（期望 %s）；dsh.bundle.patch=%s"
          % (len(names), pj.get("version"), a.version, patch_rel or "（未声明）"))
    if pj.get("version") != a.version:
        fail.append("包内版本不是 %s" % a.version)
    if any(n.endswith(".bak") for n in names):
        fail.append("包内含 .bak")
    if patch_rel and not os.path.isfile(os.path.join(root, patch_rel.lstrip("./"))):
        fail.append("声明了 %s 却没打进包（事故 #3 同形）" % patch_rel)

    # ③ 守护相关落点（只读报告，行为实测在真重启时做）
    src = open(os.path.join(root, "lib", "index.js"), encoding="utf-8").read() if os.path.isfile(os.path.join(root, "lib", "index.js")) else ""
    print("③ lib/index.js %d B；开火判据相关标记：" % len(src))
    for needle in ("argv0", "$2==p", "$2 == p", "startedAt", "105", "115", "先等旧实例"):
        hits = [i + 1 for i, ln in enumerate(src.splitlines()) if needle in ln]
        print("   %s %-14s %s" % ("✅" if hits else "· ", needle, hits[:4] if hits else "未命中"))
    if not src:
        fail.append("包内缺 lib/index.js")

    # ④ 备份 + 安装 + 装后断言
    bak = os.path.expanduser("~/dsh-collab/data/backups/dsh-plugin-agent-way.pre-%s-%s" % (a.version, a.stamp))
    before = {f: sha(os.path.join(TGT, f)) for f in
              [os.path.relpath(os.path.join(d, x), TGT) for d, _, fs in os.walk(TGT) for x in fs]}
    shutil.copytree(TGT, bak)
    print("④ 备份 → %s" % bak)
    changed, added = [], []
    for d, _, fs in os.walk(root):
        for f in fs:
            s = os.path.join(d, f)
            rel = os.path.relpath(s, root)
            dst = os.path.join(TGT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(s, dst)
            new_hash = sha(dst)
            if new_hash != sha(s):
                fail.append("读回不一致: %s" % rel)
            if rel in before:
                if before[rel] != new_hash:
                    changed.append(rel)
            else:
                added.append(rel)
    print("   变更 %d 个：%s" % (len(changed), sorted(changed)[:10]))
    print("   新增 %d 个：%s" % (len(added), sorted(added)[:10]))
    disk_ver = json.load(open(os.path.join(TGT, "package.json"), encoding="utf-8")).get("version")
    leftover = [os.path.relpath(os.path.join(d, f), TGT) for d, _, fs in os.walk(TGT) for f in fs if ".bak" in f]
    if patch_rel and not os.path.isfile(os.path.join(TGT, patch_rel.lstrip("./"))):
        fail.append("装后缺 %s（冷启动会报 overlay ENOENT，事故 #3 同形）" % patch_rel)
    print("   磁盘 version=%s ｜ patch 装后=%s ｜ .bak 残留=%s"
          % (disk_ver, "在 ✅" if not patch_rel or os.path.isfile(os.path.join(TGT, patch_rel.lstrip("./"))) else "缺 ❌",
             leftover or "无 ✅"))
    if disk_ver != a.version:
        fail.append("磁盘版本不是 %s" % a.version)
    if leftover:
        fail.append(".bak 残留")
    # ⑤ mtime 归一（tar 常把 mtime 写成 1970，会干扰后续 mtime 判据）
    for d, _, fs in os.walk(TGT):
        for f in fs:
            try:
                os.utime(os.path.join(d, f), None)
            except Exception:
                pass

    print("\n⇒ %s" % ("✅ 已采纳 agent-way %s（下一步：spawn-detached.sh tools/verify-post-reload.sh → POST /reload）" % a.version
                      if not fail else "❌ 断言失败 %s ⇒ 回滚：rm -rf %s && cp -R %s %s" % (fail, TGT, bak, TGT)))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
