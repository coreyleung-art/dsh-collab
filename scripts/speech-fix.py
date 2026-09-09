#!/usr/bin/env python3
"""speech-fix.py — 语音转写称呼纠错工具（读 speech-fix-library.json 自动匹配替换）

用法:
  python3 speech-fix.py <输入文件或文本>           # 默认: 替换后打印到 stdout
  python3 speech-fix.py <file> --out <outfile>     # 输出到文件
  python3 speech-fix.py <file> --list              # 只列出命中不替换
  python3 speech-fix.py <file> --confirmed-only    # 仅应用 confirmed_by=user 条目
  python3 speech-fix.py <file> --no-inference      # 同 --confirmed-only
  python3 speech-fix.py --report <file>            # 命中统计报告
  python3 speech-fix.py --add <canonical> --variants "变体1,变体2" [--type org] [--desc "..."]  # 新增纠错条目
  python3 speech-fix.py --entries                  # 列出现有条目

规则:
  - 读 ~/dsh-collab/data/speech-fix-library.json 的 entries
  - variants 中每个变体按 "长词优先" 顺序替换为 canonical
  - 默认应用全部(含 inference)；risk=high 的条目默认跳过, 除非 --all
  - 同词多义(如通用词)靠变体白名单规避——只替换登记过的变体, 不碰通用词

作者: 明鉴 v3 · 2026-09-07
"""
import json, os, re, sys, datetime

LIB = os.path.expanduser("~/dsh-collab/data/speech-fix-library.json")

def load_lib():
    with open(LIB, encoding="utf-8") as f:
        return json.load(f)

def collect_rules(confirmed_only=False, include_high_risk=False):
    lib = load_lib()
    rules = []  # (variant, canonical, meta)
    for e in lib.get("entries", []):
        if confirmed_only and e.get("confirmed_by") != "user":
            continue
        if not include_high_risk and e.get("risk") == "high":
            continue
        # 变体去重: canonical 本身不进 variants 时不替换; 长词优先排序
        for v in sorted(set(e.get("variants", [])), key=len, reverse=True):
            if v == e.get("canonical"):
                continue  # canonical 已是正确写法, 无需替换
            rules.append((v, e["canonical"], {
                "id": e.get("id"), "type": e.get("type"),
                "confirmed_by": e.get("confirmed_by"), "note": e.get("note", ""),
            }))
    return rules

def apply(text, confirmed_only=False, include_high_risk=False):
    rules = collect_rules(confirmed_only, include_high_risk)
    hits = []
    for v, c, meta in rules:
        # 前缀补全保护: canonical 以 variant 开头(如 声通→声通科技),
        # 避免把已正确的 canonical 再替换成 canonical+重复后缀
        if c.startswith(v) and len(c) > len(v):
            suffix = c[len(v):]
            pat = re.compile(re.escape(v) + r'(?!' + re.escape(suffix) + ')')
            n = len(pat.findall(text))
            if n:
                text = pat.sub(c, text)
                hits.append({"variant": v, "canonical": c, "count": n, **meta})
            continue
        n = text.count(v)
        if n:
            text = text.replace(v, c)
            hits.append({"variant": v, "canonical": c, "count": n, **meta})
    return text, hits

def add_entry(canonical, variants_str, etype="org", desc="", confirmed="user"):
    """新增/更新纠错库条目"""
    with open(LIB, encoding="utf-8") as f:
        lib = json.load(f)
    variants = [v.strip() for v in variants_str.split(",") if v.strip()]
    variants.append(canonical)  # canonical 本身可安全匹配(工具会跳过==canonical)
    # 生成新 id
    n = len([e for e in lib["entries"] if e["id"].startswith("SF-")]) + 1
    new_id = f"SF-{n:03d}"
    for e in lib["entries"]:
        if e["canonical"] == canonical:
            new_id = e["id"]
            for v in variants:
                if v not in e["variants"]: e["variants"].append(v)
            e["confirmed_by"] = confirmed if confirmed in ("user", "inference") else e["confirmed_by"]
            print(f"✅ 更新条目 {new_id}: {canonical} (variants 合并)")
            break
    else:
        lib["entries"].append({
            "id": new_id, "canonical": canonical, "type": etype,
            "desc": desc or canonical, "variants": list(dict.fromkeys(variants)),
            "confirmed_by": confirmed, "source": f"CLI 添加 {datetime.date.today().isoformat()}",
            "ts": datetime.date.today().isoformat(), "risk": "low", "note": ""})
        print(f"✅ 新增条目 {new_id}: {canonical} variants={variants}")
    with open(LIB, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    return 0

def list_entries():
    with open(LIB, encoding="utf-8") as f:
        lib = json.load(f)
    print(f"== 纠错库条目 ({len(lib['entries'])}) ==")
    for e in lib["entries"]:
        print(f"  {e['id']} {e['canonical']} [{e.get('confirmed_by')}] ← {e.get('variants')}")
    return 0

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if "--entries" in args:
        return list_entries()
    if "--add" in args:
        i = args.index("--add")
        canonical = args[i + 1]
        vs = args[args.index("--variants") + 1] if "--variants" in args else ""
        tp = args[args.index("--type") + 1] if "--type" in args else "org"
        dc = args[args.index("--desc") + 1] if "--desc" in args else ""
        cf = args[args.index("--confirmed") + 1] if "--confirmed" in args else "user"
        return add_entry(canonical, vs, tp, dc, cf)
    confirmed_only = any(a in args for a in ("--confirmed-only", "--no-inference"))
    include_high_risk = "--all" in args
    do_list = "--list" in args
    do_report = "--report" in args
    out_path = None
    if "--out" in args:
        out_path = args[args.index("--out") + 1]
    target = next(a for a in args if not a.startswith("--") and a != out_path)
    if do_report and os.path.exists(target):
        text = open(target, encoding="utf-8").read()
        _, hits = apply(text, confirmed_only, include_high_risk)
        total = sum(h["count"] for h in hits)
        print(f"命中 {len(hits)} 类变体, 共 {total} 处替换")
        for h in sorted(hits, key=lambda x: -x["count"]):
            print(f"  [{h['id']}] {h['variant']} → {h['canonical']} × {h['count']}  ({h['confirmed_by']})")
        return 0
    if os.path.exists(target):
        text = open(target, encoding="utf-8").read()
    else:
        text = target  # 直接当作文本
    text, hits = apply(text, confirmed_only, include_high_risk)
    if do_list:
        for h in hits:
            print(f"[{h['id']}] {h['variant']} → {h['canonical']} × {h['count']} ({h['confirmed_by']})")
        return 0
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已替换并写入: {out_path} ({len(hits)} 类命中)")
    else:
        sys.stdout.write(text)
    return 0

if __name__ == "__main__":
    sys.exit(main())
