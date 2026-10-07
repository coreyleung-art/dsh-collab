#!/usr/bin/env python3
# verify-naming-standard.py — 独立复核 naming-standard-N1-N8-v1.md
# 只用标准库：从 md 里抽出机器可读判据块，结构校验 + 用文件自带判据复现测试向量。
# 退出码：0 全绿 / 1 校验失败 / 2 用法或 IO 错误（R006 ⑨ 语义）
import argparse, json, os, re, sys

DEFAULT_DOC = os.path.expanduser("~/dsh-collab/rules-registry/naming-standard-N1-N8-v1.md")

# ⑥ 版本单一来源：本脚本无包文件，故版本只此一处声明；--tool-version 从它读。
#    并由 `版本单一来源（反查自身源码）` 这条检查自动证明「不存在第二处声明」。
TOOL_VERSION = "1.1.0"

# ★ 变异自检：逐个放宽 operative 字段，若没有任何向量转红 → 该字段「未被覆盖」（R006 坑#3 空洞通过）
MUTATIONS = [
    ("slug_regex", lambda op: op.__setitem__("slug_regex", "^.*$")),
    ("tool_regex", lambda op: op.__setitem__("tool_regex", "^.*$")),
    ("slug_len_min", lambda op: op.__setitem__("slug_len_min", 0)),
    ("slug_len_max", lambda op: op.__setitem__("slug_len_max", 999)),
    ("tool_len_max", lambda op: op.__setitem__("tool_len_max", 999)),
    ("reserved_slugs", lambda op: op.__setitem__("reserved_slugs", [])),
]


def load_payload(path):
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"```json\n(.*?)\n```", text, re.S)
    if not m:
        raise ValueError("未找到 ```json 判据块")
    return json.loads(m.group(1)), text


def slug_issues(s, op):
    out = []
    if not s:
        return ["slug 为空"]
    if len(s) < op["slug_len_min"]:
        out.append("长度 < %d" % op["slug_len_min"])
    if len(s) > op["slug_len_max"]:
        out.append("长度 > %d" % op["slug_len_max"])
    if re.search(r"[A-Z]", s):
        out.append("含大写字母")
    if "_" in s:
        out.append("含下划线")
    if "." in s:
        out.append("含点号")
    if re.match(r"^[0-9]", s):
        out.append("以数字开头")
    if "--" in s:
        out.append("出现连续连字符")
    if s.endswith("-"):
        out.append("以连字符结尾")
    if re.search(r"[^a-z0-9-]", s):
        out.append("含 [a-z0-9-] 之外的字符")
    if not re.match(op["slug_regex"], s):
        out.append("不匹配 slug 正则")
    if s in op["reserved_slugs"]:
        out.append("命中原保留字")
    return out


def tool_issues(n, op):
    out = []
    if "-" in n:
        out.append("含连字符")
    if not re.match(op["tool_regex"], n):
        out.append("不匹配工具名正则")
    if len(n) > op["tool_len_max"]:
        out.append("长度 > %d" % op["tool_len_max"])
    return out


def mutation_selftest(op, vectors):
    """逐个字段放宽 → 断言至少一条向量转红；全不转红＝该字段未被任何向量覆盖。"""
    def verdicts(o):
        out = []
        for v in vectors:
            iss = slug_issues(v["input"], o) if v["kind"] == "slug" else tool_issues(v["input"], o)
            out.append("reject" if iss else "accept")
        return out

    base = verdicts(op)
    rows = []
    for name, mutate in MUTATIONS:
        if name not in op:
            rows.append({"field": name, "covered": False, "reason": "字段不在 operative 中", "flipped": []})
            continue
        o = json.loads(json.dumps(op))
        mutate(o)
        after = verdicts(o)
        flipped = [vectors[i]["input"] for i in range(len(vectors)) if after[i] != base[i]]
        rows.append({"field": name, "covered": len(flipped) > 0, "flipped": flipped[:3],
                     "reason": "" if flipped else "放宽该字段后没有任何向量转红 → 未被覆盖"})
    return rows


def main():
    ap = argparse.ArgumentParser(description="复核 N1–N8 落盘正文")
    ap.add_argument("--file", default=DEFAULT_DOC)
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--mutation", action="store_true", help="逐个字段做变异自检（证明每个 operative 字段都被向量覆盖）")
    ap.add_argument("--tool-version", action="store_true", help="打印本脚本版本（唯一来源）")
    try:
        args = ap.parse_args()
    except SystemExit:
        return 2
    if args.tool_version:
        # 不要求正文存在即可查询版本（用法：脚本可被其它工具用来核对版本）
        print(TOOL_VERSION)
        return 0
    try:
        payload, raw = load_payload(args.file)
    except (OSError, ValueError, json.JSONDecodeError) as err:
        sys.stderr.write("读取/解析失败：%s\n" % err)
        return 2

    op = payload.get("operative", {})
    norms = payload.get("norms", [])
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    chk("norm_ids 连续 N1–N8", [n.get("id") for n in norms] == ["N%d" % i for i in range(1, 9)],
        "实际 %d 条" % len(norms))
    chk("每条都有 rule 与 why", all(n.get("rule") and n.get("why") for n in norms))
    chk("保留字非空且无重复",
        len(op.get("reserved_slugs", [])) > 0 and len(set(op.get("reserved_slugs", []))) == len(op.get("reserved_slugs", [])),
        "%d 个" % len(op.get("reserved_slugs", [])))
    try:
        re.compile(op["slug_regex"]); re.compile(op["tool_regex"]); chk("两条正则可编译", True)
    except (KeyError, re.error) as err:
        chk("两条正则可编译", False, str(err))
    chk("声明了 authority 与 r047", bool(payload.get("authority")) and bool(payload.get("r047")))
    table_rows = len(re.findall(r"^\| \*\*N\d\*\* \|", raw, re.M))
    chk("正文表格行数与判据块条数一致", table_rows == len(norms),
        "表格 %d 行 / JSON %d 条" % (table_rows, len(norms)))

    vec = payload.get("test_vectors", [])
    vec_rows = []
    for v in vec:
        issues = slug_issues(v["input"], op) if v["kind"] == "slug" else tool_issues(v["input"], op)
        got = "reject" if issues else "accept"
        vec_rows.append({"input": v["input"], "kind": v["kind"], "expect": v["expect"],
                         "got": got, "ok": got == v["expect"], "issues": issues})
    chk("测试向量全部符合预期", all(r["ok"] for r in vec_rows), "%d/%d" % (sum(1 for r in vec_rows if r["ok"]), len(vec_rows)))
    chk("声明了 descriptive 分区（不把仅声明语义的字段当已证）",
        isinstance(payload.get("descriptive"), dict) and payload["descriptive"].get("enforced_by_this_verifier") is False)
    # ⑥ 版本单一来源：反查自身源码，证明不存在第二处版本声明
    src = open(os.path.abspath(__file__), "r", encoding="utf-8").read()
    decls = re.findall(r"^[ \t]*(?:TOOL_VERSION|VERSION|version)[ \t]*=[ \t]*[\"']\d+\.\d+\.\d+[\"']",
                       src, re.M)
    chk("版本单一来源（反查自身源码，仅 1 处声明）", len(decls) == 1,
        "找到 %d 处：%s" % (len(decls), decls))

    mutation = mutation_selftest(op, vec) if args.mutation else None
    if mutation is not None:
        uncovered = [m["field"] for m in mutation if not m["covered"]]
        chk("变异自检：每个 operative 字段都被向量覆盖", not uncovered,
            "未覆盖: %s" % (", ".join(uncovered) if uncovered else "无（%d 个字段全覆盖）" % len(mutation)))

    ok = all(c["ok"] for c in checks)
    result = {
        "file": args.file,
        "bytes": len(raw.encode("utf-8")),
        "authority": payload.get("authority", {}).get("id"),
        "r047_ledger_version": payload.get("r047", {}).get("ledger_version"),
        "checks": checks,
        "vectors": vec_rows,
        "mutation_selftest": mutation,
        "boundaries": len(payload.get("known_boundaries", [])),
        "errata": payload.get("errata", []),
        "verdict": "PASS" if ok else "FAIL",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for c in checks:
            print("%s %s %s" % ("✓" if c["ok"] else "✗", c["check"], c["detail"]))
        print("\n判定：%s" % result["verdict"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
