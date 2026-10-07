#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""merge-r041.py —— 规则账本收敛：31 条「资源冲突」数据条目 → 1 条协议 R041（v2.16.1 → 2.17.0）

【依据】2026-10-03 与协调者（星桥 session-fa1f9150）双向确认：
  · 同意按 R041 收敛；**同一编号 2.17.0**（其侧 R001–R040，随 R041 补版本头）。
  · 我侧预演已过：84 → 54 条。

【为什么是「数据 → 外挂表」而不是删规则】
  `category=资源冲突` 的 31 条**没有一条是规则**，全是「某个具体对象的占用/冲突/处理方式」= 数据。
  数据移到 `data/ops/resource-constraints.json#ledgerIndex.keys`（按对象键检索，带 ruleId 溯源），
  账本只留 1 条**协议**（R041：涉及具体对象先查表；新对象级约束只加表不加规则）。

【★ 关键陷阱（我差点踩，记下来给对端）】
  RULES.md 里 **R 与 J 章节是「交错」的**，不是两块连续区：
    J31 在第 45 行，但 R009 在第 260 行、R040 在第 458 行。
  ⇒ **绝不可按行号截断**（"45 行以后全删"会连带删掉 32 条 R 规则 = 类别 A 事故）。
  ⇒ 必须**按 `^## <id>` 分章节**，只删 id 命中的段；并**断言被删的全是 J 开头**。

【安全设计】
  · 双载体**先备份**（.bak-merge-r041-<stamp>）
  · 写入走自家护栏 `safe-write-guard.guarded_write`（RULES.md 因**有意删除**内容用 allow_clobber）
  · 写后**读回断言**（条数/版本/被删 id 已消失/R 段数不变/R041 在位）
  · 被删段必须全为 J 开头 —— **否则拒绝写入**（防类别 A）

用法：python3 merge-r041.py            # 执行
     python3 merge-r041.py --dry-run  # 只报告将发生什么，不写盘
"""
import json, io, os, re, sys, shutil, datetime, importlib.util

REG = os.path.expanduser("~/dsh-collab/rules-registry")
RC_PATH = os.path.expanduser("~/dsh-collab/data/ops/resource-constraints.json")
PRE_PATH = os.path.expanduser("~/dsh-collab/data/preview/rules-merge-2.17.0.json")
TARGET_VERSION = "2.17.0"
DRY = "--dry-run" in sys.argv


def load(path):
    return json.load(io.open(path, encoding="utf-8"))


def section_id(sec):
    m = re.match(r"##\s+([A-Za-z]*\d+)", sec)
    return m.group(1) if m else None


def main():
    os.chdir(REG)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    rc = load(RC_PATH)
    remove = set(k["ruleId"] for k in rc["ledgerIndex"]["keys"])
    pre = load(PRE_PATH)
    r041 = next(r for r in pre["rules"] if r["id"] == "R041")

    # ── ① rules.json ───────────────────────────────────────────────────
    d = load("rules.json")
    before = len(d["rules"])
    dropped_j = [r["id"] for r in d["rules"] if r["id"] in remove]
    kept = [r for r in d["rules"] if r["id"] not in remove]
    if len(dropped_j) != 31:
        print("❌ 期望移出 31 条，实际 %d ⇒ 拒绝执行" % len(dropped_j)); return 1
    if any(r["id"] == "R041" for r in kept):
        print("❌ R041 已存在 ⇒ 拒绝重复执行"); return 1
    non_j = [i for i in dropped_j if not i.startswith("J")]
    if non_j:
        print("❌ 待移出中含非 J 条目 %s ⇒ 拒绝执行（防误删规则）" % non_j); return 1
    d["rules"] = kept + [r041]
    d["version"] = TARGET_VERSION
    d["lastUpdated"] = "2026-10-03"
    print("── rules.json: %d → %d 条（移出 %d 条 J，新增 R041），version → %s"
          % (before, len(d["rules"]), len(dropped_j), TARGET_VERSION))

    # ── ② RULES.md：按章节精确删（R/J 交错，禁按行号截断）──────────────
    md = io.open("RULES.md", encoding="utf-8").read()
    parts = re.split(r"(?m)^(?=## )", md)
    pre_md, secs = parts[0], parts[1:]
    kept_secs, dropped_secs = [], []
    for s in secs:
        (dropped_secs if section_id(s) in remove else kept_secs).append(s)
    dsid = [section_id(s) for s in dropped_secs]
    print("── RULES.md: 章节 %d；删 %d；留 %d" % (len(secs), len(dropped_secs), len(kept_secs)))
    if len(dropped_secs) != 31:
        print("❌ md 侧应删 31 段，实际 %d ⇒ 拒绝执行" % len(dropped_secs)); return 1
    if any(not str(i).startswith("J") for i in dsid):
        print("❌ 误命中非 J 章节 %s ⇒ 拒绝执行" % [i for i in dsid if not str(i).startswith("J")]); return 1

    r041_sec = ("## R041 ✅ %s\n- 分类: %s | 范围: %s | 状态: %s\n- 摘要: %s\n- 详情: %s\n\n"
                % (r041["name"], r041["category"], r041["scope"], r041["status"],
                   r041["summary"], r041["detail"]))
    idx = next((i for i, s in enumerate(kept_secs) if str(section_id(s)) == "R040"), len(kept_secs) - 1)
    kept_secs.insert(idx + 1, r041_sec)
    new_md = pre_md + "".join(kept_secs)
    new_md = re.sub(r"(>\s*v)[0-9.]+(\s*\|\s*)\d+(\s*条)",
                    r"\g<1>%s\g<2>%d\g<3>" % (TARGET_VERSION, len(d["rules"])), new_md, count=1)
    print("── RULES.md: R 段 %d → %d；版本行 → v%s | %d 条"
          % (len(re.findall(r"(?m)^## R\d{3}\b", md)), len(re.findall(r"(?m)^## R\d{3}\b", new_md)),
             TARGET_VERSION, len(d["rules"])))

    if DRY:
        print("\n[dry-run] 未写盘。")
        return 0

    # ── ③ 备份 + 写入（走自家护栏）────────────────────────────────────
    for f in ("rules.json", "RULES.md"):
        shutil.copy2(f, "%s.bak-merge-r041-%s" % (f, stamp))
    print("── 备份: *.bak-merge-r041-%s" % stamp)

    spec = importlib.util.spec_from_file_location(
        "swg", os.path.expanduser("~/dsh-collab/tools/safe-write-guard.py"))
    swg = importlib.util.module_from_spec(spec); spec.loader.exec_module(swg)
    swg.guarded_write("rules.json", json.dumps(d, ensure_ascii=False, indent=2), quiet=True)
    # RULES.md 是**有意删除**内容 ⇒ 显式 allow_clobber（护栏仍会留 .bak-safewrite）
    swg.guarded_write("RULES.md", new_md, allow_clobber=True, quiet=True)
    print("── 已写入（guarded_write）")

    # ── ④ 读回断言 ────────────────────────────────────────────────────
    rb_j = load("rules.json"); rb_m = io.open("RULES.md", encoding="utf-8").read()
    ok = True
    def chk(n, c, det=""):
        nonlocal ok; ok = ok and c
        print("   %s %-40s %s" % ("✅" if c else "❌", n, det))
    chk("json 条数 = 54", len(rb_j["rules"]) == 54, len(rb_j["rules"]))
    chk("version = 2.17.0", rb_j["version"] == TARGET_VERSION, rb_j["version"])
    chk("31 条 J 已移出 json", not any(r["id"] in remove for r in rb_j["rules"]))
    chk("R041 在 json", any(r["id"] == "R041" for r in rb_j["rules"]))
    chk("md 版本行 = v2.17.0 | 54 条", "v%s | %d 条" % (TARGET_VERSION, 54) in rb_m)
    chk("md 无被删 J 标题", not re.search(r"(?m)^## (%s)\b" % "|".join(sorted(remove)), rb_m))
    chk("md R 段数 = 41（无规则丢失）", len(re.findall(r"(?m)^## R\d{3}\b", rb_m)) == 41,
        len(re.findall(r"(?m)^## R\d{3}\b", rb_m)))
    print("\n   ⇒ %s" % ("全部通过" if ok else "★ 有失败项 —— 请用 .bak-merge-r041 回滚"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
