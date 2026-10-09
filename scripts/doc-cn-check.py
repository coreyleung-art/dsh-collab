#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc-cn-check.py — R039 工具中文描述文档机械门（2026-10-03 用户指示）

判据（R039 ④）：文档文件存在 + UTF-8 可读 + 中文字符数 > 100。
用法:
  doc-cn-check.py <docs文件...>       # 交付时自检（任意多个路径；全过 exit 0）
  doc-cn-check.py --manifest <path>   # 冻结清单模式（tool-doc-manifest.json，逐项核验）
  doc-cn-check.py --selfcheck         # 正反控：中文达标文件→PASS / 10字文件→FAIL / 空文件→FAIL
  doc-cn-check.py --json              # 机器可读输出
退出码: 0 全过 · 1 有失败 · 2 用法或 IO 错误

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, sys, tempfile


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/doc-cn-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

CN_MIN = 100

def cn_chars(text):
    return len([c for c in text if '\u4e00' <= c <= '\u9fff'])

def check_one(path):
    p = os.path.expanduser(path)
    if not os.path.exists(p):
        return {"path": path, "ok": False, "reason": "文件不存在", "cn": 0}
    try:
        with open(p, "r", encoding="utf-8") as f:
            s = f.read()
    except UnicodeDecodeError:
        return {"path": path, "ok": False, "reason": "非 UTF-8 可读", "cn": 0}
    except Exception as e:
        return {"path": path, "ok": False, "reason": str(e)[:60], "cn": 0}
    cn = cn_chars(s)
    if cn <= CN_MIN:
        return {"path": path, "ok": False, "reason": "中文字符数 %d ≤ %d" % (cn, CN_MIN), "cn": cn}
    return {"path": path, "ok": True, "reason": "中文 %d 字达标" % cn, "cn": cn}

def selfcheck():
    rows = []
    def ck(name, ok, detail=""):
        rows.append((name, ok, detail))
    # 正控：200 中文字 → PASS
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("正控文档。" + "中文" * 200)
        pos_p = f.name
    r = check_one(pos_p)
    ck("正控（中文200字→PASS）", r["ok"] is True, json.dumps(r, ensure_ascii=False))
    # 负控1：10 中文字 → FAIL
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("短文档。" + "中文" * 10)
        neg_p = f.name
    r = check_one(neg_p)
    ck("负控1（中文10字→FAIL）", r["ok"] is False, json.dumps(r, ensure_ascii=False))
    # 负控2：不存在 → FAIL
    r = check_one("/tmp/__doc_cn_no_such_file__.md")
    ck("负控2（不存在→FAIL）", r["ok"] is False, json.dumps(r, ensure_ascii=False))
    for p in (pos_p, neg_p):
        try: os.unlink(p)
        except Exception: pass
    nf = sum(1 for _, ok, _ in rows if not ok)
    for name, ok, detail in rows:
        print(("PASS " if ok else "FAIL ") + name + ("  — " + detail if detail else ""))
    print("selfcheck: " + ("PASS" if nf == 0 else "FAIL"))
    return 0 if nf == 0 else 1

def manifest_check(mpath):
    try:
        with open(os.path.expanduser(mpath), "r", encoding="utf-8") as f:
            m = json.load(f)
    except Exception as e:
        print(json.dumps({"ok": False, "error": "清单读取失败: %s" % str(e)[:80]}, ensure_ascii=False))
        return 2
    tools = m.get("tools") or []
    names = [t.get("name") for t in tools if isinstance(t, dict)]
    if len(names) != len(set(names)):
        print(json.dumps({"ok": False, "error": "清单工具名重复"}, ensure_ascii=False))
        return 1
    results = []
    for t in tools:
        r = check_one(t.get("docs", ""))
        r["name"] = t.get("name", "?")
        results.append(r)
    pending = m.get("pending") or []
    out = {"ok": all(r["ok"] for r in results), "checked": len(results), "passed": sum(1 for r in results if r["ok"]),
           "pending": pending, "results": results}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["ok"] else 1

def main():
    global CN_MIN
    ap = argparse.ArgumentParser(description="R039 工具中文描述文档机械门")
    ap.add_argument("paths", nargs="*", help="文档路径（1+ 个；与 --manifest 互斥）")
    ap.add_argument("--manifest", default=None, help="冻结清单 JSON 路径")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-cn", type=int, default=CN_MIN, help="中文字符数阈值（默认 100）")
    args = ap.parse_args()
    CN_MIN = args.min_cn
    if args.selfcheck:
        return selfcheck()
    if args.manifest:
        return manifest_check(args.manifest)
    if not args.paths:
        ap.print_usage()
        print("错误: 至少给一个文档路径，或 --manifest / --selfcheck")
        return 2
    results = [check_one(p) for p in args.paths]
    if args.json:
        print(json.dumps({"ok": all(r["ok"] for r in results), "results": results}, ensure_ascii=False))
    else:
        for r in results:
            print(("PASS " if r["ok"] else "FAIL ") + r["path"] + "  — " + r["reason"])
    return 0 if all(r["ok"] for r in results) else 1

if __name__ == "__main__":
    sys.exit(main())
