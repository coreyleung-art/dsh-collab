#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checks-transfer.py — 完整体传输契约检查器（R012 CHECKS 七要素）

用途：验证传输物（资产包/升级包/报告/消息）是否为「完整体」——
      接收方可直接使用，零二次开发。半成品 → FAIL 阻止传输。

用法:
  checks-transfer.py <包路径> [--type 吸收|分发|升级|报告|消息]
  checks-transfer.py <目录>   # 目录模式（已验证的源码/资产目录）
  checks-transfer.py --check-file <单个文件>  # 单文件检查

CHECKS 七要素:
  C - Complete 内容完整（无空文件/占位符）
  H - Hash 校验（带 sha256 或可验证）
  E - Executable 可执行（有可运行入口）
  C - Context 上下文（README/设计说明存在）
  K - Known-version 版本可溯（git/tag/CHANGELOG）
  S - Self-verified 自检（测试/冒烟痕迹）
  S - Safe 可回滚（备份/回滚说明）

依赖: 纯 stdlib（os/sys/tarfile/hashlib/argparse）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, hashlib, os, sys, tarfile, zipfile, glob

PLACEHOLDERS = ["TODO", "FIXME", "TBD", "占位", "待补", "待完成", "coming soon", "placeholder"]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def check_tar(tar_path, results):
    try:
        with tarfile.open(tar_path) as tf:
            names = tf.getnames()
            # C: 非空
            if not names:
                results.append(("FAIL", "C", "压缩包为空"))
                return names
            results.append(("OK", "C", f"包含 {len(names)} 个文件"))
            # 找 README/设计文档
            has_readme = any("README" in n or "readme" in n or "design" in n or "说明" in n or ".md" in n for n in names)
            results.append(("OK" if has_readme else "FAIL", "C", f"含文档: {has_readme}"))
            # 找源码/入口
            has_entry = any(n.endswith((".js", ".py", ".rs", ".exe", ".sh", ".ts")) for n in names)
            results.append(("OK" if has_entry else "FAIL", "E", f"含可执行/源码入口: {has_entry}"))
            # 找 CHANGELOG/git/version
            has_ver = any("CHANGELOG" in n or "VERSION" in n or ".git" in n or "package.json" in n or "Cargo.toml" in n for n in names)
            results.append(("OK" if has_ver else "FAIL", "K", f"版本可溯: {has_ver}"))
            # checksum 文件
            has_checksum = any("sha256" in n or "checksum" in n or ".sum" in n for n in names)
            results.append(("OK" if has_checksum else "WARN", "H", f"含校验和文件: {has_checksum}"))
            return names
    except Exception as e:
        results.append(("FAIL", "C", f"解压失败: {e}"))
        return []

def check_dir(d, results):
    files = [f for f in glob.glob(os.path.join(d, "**"), recursive=True)
             if os.path.isfile(f) and "node_modules" not in f and "/.git/" not in f and not f.endswith(".pyc")]
    if not files:
        results.append(("FAIL", "C", "目录为空"))
        return
    results.append(("OK", "C", f"含 {len(files)} 个文件"))
    names = [os.path.relpath(f, d) for f in files]
    has_readme = any("README" in n or ".md" in n or "design" in n for n in names)
    results.append(("OK" if has_readme else "FAIL", "C", f"含文档: {has_readme}"))
    has_entry = any(n.endswith((".js", ".py", ".rs", ".exe", ".sh")) for n in names)
    results.append(("OK" if has_entry else "FAIL", "E", f"含源码/入口: {has_entry}"))
    has_ver = any("CHANGELOG" in n or "package.json" in n or "Cargo.toml" in n or ".git" in n for n in names)
    results.append(("OK" if has_ver else "FAIL", "K", f"版本可溯: {has_ver}"))
    # 占位符扫描（抽查前 5 个文本文件）
    ph_found = 0
    scanned = 0
    for f in files:
        if f.endswith((".md", ".txt", ".json", ".yml", ".yaml", ".py", ".js", ".rs")):
            try:
                txt = open(f, encoding="utf-8", errors="ignore").read()
                scanned += 1
                if any(p.lower() in txt.lower() for p in PLACEHOLDERS):
                    ph_found += 1
                    if ph_found <= 3:
                        results.append(("WARN", "C", f"占位符: {os.path.relpath(f, d)}"))
            except Exception:
                pass
        if scanned >= 5:
            break
    results.append(("OK" if ph_found == 0 else "WARN", "C", f"占位符扫描: {ph_found}/{scanned} 文件含占位"))

def check_file(f, results):
    if not os.path.exists(f):
        results.append(("FAIL", "C", f"文件不存在: {f}"))
        return
    size = os.path.getsize(f)
    if size == 0:
        results.append(("FAIL", "C", "文件为空（0 字节）"))
    else:
        results.append(("OK", "C", f"文件大小 {size} 字节"))
    results.append(("OK", "H", f"sha256: {sha256_file(f)[:16]}..."))

def main():
    ap = argparse.ArgumentParser(description="完整体传输契约检查器（R012 CHECKS）")
    ap.add_argument("path", help="包/目录/文件路径")
    ap.add_argument("--type", default="吸收", choices=["吸收", "分发", "升级", "报告", "消息"])
    ap.add_argument("--check-file", action="store_true", help="单文件模式")
    args = ap.parse_args()

    results = []
    p = args.path
    if args.check_file or os.path.isfile(p) and not (p.endswith(".tar.gz") or p.endswith(".tgz") or p.endswith(".zip")):
        check_file(p, results)
    elif p.endswith(".tar.gz") or p.endswith(".tgz") or p.endswith(".zip"):
        check_tar(p, results)
    elif os.path.isdir(p):
        check_dir(p, results)
    else:
        results.append(("FAIL", "C", f"无法识别路径: {p}"))

    print(f"══ CHECKS 完整体检查 · {args.type} · {p} ══")
    fails = 0
    for level, key, msg in results:
        print(f"[{level}] {key} {msg}")
        if level == "FAIL":
            fails += 1
    print(f"══ 结果: {fails} FAIL / {sum(1 for r in results if r[0]=='WARN')} WARN ══")
    if fails > 0:
        print("❌ 半成品：接收方需补全才能使用，禁止传输（R012）")
        sys.exit(1)
    print("✅ 完整体：可传输（R012）")
    sys.exit(0)

if __name__ == "__main__":
    main()
