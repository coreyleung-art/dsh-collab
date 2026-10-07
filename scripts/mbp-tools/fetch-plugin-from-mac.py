#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch-plugin-from-mac.py —— 从 mac-mini 取插件源码目录并接入本机（通用版，v1.0.0，2026-10-04）。

为什么工具化（Φ8 两次法则）：`dsh-plugin-channel-gate` 与 `dsh-plugin-central-inbox` 都是
「对端源码目录 + profile `link:` 依赖」形态（用户指示「找 mac 拿」）⇒ 同一动作第二次，抽成通用工具。

做的事（每步带断言，遵守 R043 读回验证 / G9 防 npm 剪枝）：
  ① 逐文件取（ssh cat，**排除 `.bak*`/`.git`/`node_modules`/`__pycache__`/`._*`）+ **sha256 读回断言**；
  ② 与目标 node_modules 现状比对（版本 / 关键文件哈希），**存在则先备份**（保留可回滚实体副本）；
  ③ 建软链（node_modules/<name> → 源码目录）；
  ④ profile `package.json` 声明 `link:` 依赖（**绝不跑 npm install**；★ 语义：**既有缺失=警告**，**本次弄丢=失败**）；
  ⑤ 若插件带 selfcheck/selftest 则就地跑一次（失败即出声）。

用法：
  python3 fetch-plugin-from-mac.py --name dsh-plugin-central-inbox \
      --dep link:/Users/coreyleung/dsh-plugin-central-inbox \
      [--remote '~/dsh-plugin-central-inbox'] [--expect-version 0.2.14]
退出码：0=成功 ｜ 1=有断言失败（打印回滚命令）
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

HOST = "coreyleung@100.120.203.20"
PROFILE = os.path.expanduser("~/.dsh/profiles/web")
PJ = os.path.join(PROFILE, "package.json")
SKIP = (".bak", ".git/", "node_modules/", "__pycache__/", "._")


def ssh(cmd, binary=False):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, cmd], capture_output=True)
    return r.returncode, (r.stdout if binary else r.stdout.decode("utf-8", "replace")), r.stderr.decode("utf-8", "replace")


def skip(rel):
    return any(s in rel for s in SKIP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dep", required=True, help="profile 里声明的依赖值，如 link:/Users/coreyleung/xxx")
    ap.add_argument("--remote", default=None)
    ap.add_argument("--expect-version", default=None)
    ap.add_argument("--no-link", action="store_true", help="只取文件，不建软链")
    ap.add_argument("--no-dep", action="store_true", help="不改 profile 依赖")
    ap.add_argument("--stamp", default=subprocess.run(["date", "+%Y%m%d-%H%M%S"], capture_output=True, text=True).stdout.strip())
    a = ap.parse_args()
    remote = a.remote or ("~/" + a.name)
    dst = os.path.expanduser("~/" + a.name)
    nm = os.path.join(PROFILE, "node_modules", a.name)
    fail, warn = [], []

    # ① 逐文件取（排除噪音）
    rc, out, err = ssh("cd %s && find . -type f | sort" % remote)
    if rc != 0 or not out.strip():
        print("❌ 取清单失败（%s）：%s" % (remote, (err or out)[:160])); return 1
    files = [l.strip()[2:] for l in out.splitlines() if l.strip().startswith("./")]
    keep = [f for f in files if not skip(f)]
    print("① 对端 %d 个文件，排除噪音后取 %d 个（跳过 %d：%s…）"
          % (len(files), len(keep), len(files) - len(keep), [f for f in files if skip(f)][:3]))
    os.makedirs(dst, exist_ok=True)
    for rel in keep:
        rc, blob, err = ssh("cat %s/%s" % (remote, rel), binary=True)
        if rc != 0:
            fail.append("取失败 %s" % rel); continue
        p = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "wb").write(blob)
        ok = hashlib.sha256(open(p, "rb").read()).hexdigest() == hashlib.sha256(blob).hexdigest()
        if not ok:
            fail.append("读回不一致 %s" % rel)
    print("   已落盘 %s" % dst)
    try:
        ver = json.load(open(os.path.join(dst, "package.json"), encoding="utf-8")).get("version")
    except Exception as e:
        print("❌ 源码 package.json 不可读: %s" % e); return 1
    print("   源码 version=%s%s" % (ver, "（期望 %s）" % a.expect_version if a.expect_version else ""))
    if a.expect_version and ver != a.expect_version:
        fail.append("版本不符：%s ≠ %s" % (ver, a.expect_version))

    if a.no_link:
        print("② 跳过软链（--no-link）")
    # ② 与现状比对 + 备份
    if (not a.no_link) and os.path.exists(nm) and not os.path.islink(nm):
        cur = json.load(open(os.path.join(nm, "package.json"), encoding="utf-8")).get("version") if os.path.isfile(os.path.join(nm, "package.json")) else "?"
        bak = os.path.join(os.path.expanduser("~/dsh-collab/data/backups"), "%s.installed-%s-%s" % (a.name, cur, a.stamp))
        shutil.move(nm, bak)
        print("② 现状为实体目录（version=%s）⇒ 已备份搬离 → %s" % (cur, bak))
    elif os.path.islink(nm):
        print("② 现状已是软链 → %s" % os.readlink(nm))

    # ③ 软链
    want = os.path.relpath(dst, os.path.dirname(nm))
    if (not a.no_link) and (not os.path.lexists(nm)):
        os.symlink(want, nm)
        print("③ 已建软链 %s → %s" % (nm, want))
    if (not a.no_link) and (not os.path.islink(nm) or os.readlink(nm) != want):
        fail.append("软链不正确（%s）" % (os.readlink(nm) if os.path.islink(nm) else "非软链"))

    if not a.no_dep:
        # ④ profile 依赖声明（G9 安全语义）
        if a.no_dep:
            print("④ 跳过 profile 依赖（--no-dep）")
        shutil.copy2(PJ, PJ + ".bak-fetchplugin-" + a.stamp)
        d = json.load(open(PJ, encoding="utf-8"))
        before = set(d.get("dependencies") or {})
        deps = d.setdefault("dependencies", {})
        if deps.get(a.name) != a.dep:
            deps[a.name] = a.dep
            json.dump(d, open(PJ, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print("④ 已声明 %s = %s（备份 package.json.bak-fetchplugin-%s）" % (a.name, a.dep, a.stamp))
        else:
            print("④ 依赖已声明（无需改）")
        d2 = json.load(open(PJ, encoding="utf-8"))
        dd = d2.get("dependencies") or {}
        for k in ("dsh-plugin-agent-way", "dsh-plugin-central-inbox", "dsh-plugin-compliance",
                  "dsh-plugin-restart-audit", "dsh-plugin-channel-gate"):
            if k not in dd:
                (fail if k in before else warn).append(k)
        if warn:
            print("   ⚠️ 既有潜伏项（非本次造成，G9）：%s ⇒ npm install 会剪掉它们，建议另开一轮补齐" % warn)
        if any(isinstance(x, str) and x.startswith("dsh-") for x in fail):
            fail = [x for x in fail if not x.startswith("dsh-")] + ["本次弄丢依赖声明: %s" % [x for x in fail if x.startswith("dsh-")]]

    # ⑤ 就地 selfcheck（若带）
    for cand in ("lib/selfcheck.js", "lib/selftest.js", "selfcheck.js"):
        p = os.path.join(dst, cand)
        if os.path.isfile(p):
            r = subprocess.run(["/opt/homebrew/bin/node", p], cwd=dst, capture_output=True, text=True, timeout=120)
            tail = (r.stdout or r.stderr).strip().splitlines()
            print("⑤ 跑 %-18s rc=%d  %s" % (cand, r.returncode, (tail[-1] if tail else "")[:110]))
            if r.returncode != 0:
                fail.append("%s 非零退出" % cand)
            break

    print("\n⇒ %s" % ("✅ %s 已接入（源码 %s，软链 + link 依赖；生效走 /reload，无需重启应用）" % (a.name, dst)
                      if not fail else "❌ 断言失败 %s ⇒ 回滚见打印的备份路径" % fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
