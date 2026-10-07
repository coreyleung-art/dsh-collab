#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-r041-migration.py —— R041 收敛的**事后自校验**（给对方在自己的变更窗口里跑）

【为什么需要】
  迁移是"删 31 段 + 加 1 条 + 补退役索引"的高风险批量操作（本次已证明：**按行号截断会误删 32 条 R 规则**）。
  若只靠"脚本跑完了、我看了下没问题" ⇒ 那是**自我声明**，不是验证。
  ⇒ 本脚本把不变量写成断言，跑完 exit 0/1，让**机器**回答"迁干净了没有"。

【设计原则】
  · **不写死绝对条数**：各端账本谱系不同（我侧 54、对端 87），写死数字必然误报。
    只校验**不变量**（见下）。
  · **只读**：不写任何文件，可在窗口里随便跑。
  · 每条断言都对应一个**真实失败形态**（不是"看起来合理"的检查）。

【不变量（逐条对应一种失败）】
  A. 版本/条数   ：`version` 与 `md 版本行` 一致；`rules` 条数 == md 声明条数
  B. 数据已搬净  ：**不再有 `category == 资源冲突` 的条目**（取值可经 --moved-category 覆盖）
  C. 协议在位    ：存在 `R041`
  D. 退役索引    ：`retiredEntries` 非空，且**每个 id 都真的不在现役 rules 里**（防"搬了但索引写成现役"）
  E. 溯源可闭合  ：约束表每条 `ruleId` 必须命中 **现役 ∪ 退役**（防"数据搬走后溯源断裂"）
  F. md 侧同步   ：md **不存在**被退役 id 的 `## <id>` 标题（防"json 删了 md 没删"）
  G. md 无丢失   ：md 的 `## R\\d+` 标题数 >= json 的 R 系规则数（防"按行号截断误删 R 规则"）

【用法】
  python3 verify-r041-migration.py --registry ~/dsh-collab/rules-registry \
                                   [--constraints ~/dsh-collab/data/ops/resource-constraints.json]
  python3 verify-r041-migration.py --selftest     # 正负样本自证（不读真实账本）
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile


def load(p):
    """读 JSON；★ 空文件/缺文件给**明确异常**，不是裸栈（G29，2026-10-04）。

    背景：我拿本工具去**独立复核对端账本**时，对端**没有** `resource-constraints.json`
    （那是我方工件）⇒ 传进来是 0 字节 ⇒ 原实现直接 `json.JSONDecodeError` **裸栈退出**，
    使用者读到的是 traceback 而不是结论。⇒ 判据工具对「输入缺失」必须给可读结论。
    """
    if not os.path.isfile(p):
        raise FileNotFoundError(p)
    if os.path.getsize(p) == 0:
        raise ValueError("文件为空（0 字节）: %s" % p)
    return json.load(io.open(p, encoding="utf-8"))


def check(reg_dir, constraints_path=None):
    """返回 [(级别, 代码, 说明)]，级别 ∈ ✅/❌。纯函数，便于正负样本自测。"""
    out = []
    jp = os.path.join(reg_dir, "rules.json")
    mp = os.path.join(reg_dir, "RULES.md")
    if not os.path.isfile(jp):
        return [("❌", "A0", "缺 rules.json: %s" % jp)]
    d = load(jp)
    md = io.open(mp, encoding="utf-8").read() if os.path.isfile(mp) else None
    if md is None:
        return [("❌", "A0", "缺 RULES.md: %s" % mp)]

    rules = d.get("rules") or []
    ids = [r.get("id") for r in rules]

    # A 版本/条数
    m = re.search(r">\s*v([0-9.]+)\s*\|\s*(\d+)\s*条", md)
    if not m:
        out.append(("❌", "A1", "RULES.md 版本行格式不符（找不到 `> vX | N 条`）"))
    else:
        if m.group(1) != d.get("version"):
            out.append(("❌", "A2", "版本漂移: md=%s json=%s" % (m.group(1), d.get("version"))))
        if int(m.group(2)) != len(rules):
            out.append(("❌", "A3", "条数漂移: md=%s json=%d" % (m.group(2), len(rules))))

    # B 数据已搬净
    moved = [r.get("id") for r in rules if r.get("category") == "资源冲突"]
    if moved:
        out.append(("❌", "B1", "仍有 `category=资源冲突` 条目 %d 条: %s"
                    % (len(moved), ", ".join(str(x) for x in moved[:8]))))

    # C 协议在位
    if "R041" not in ids:
        out.append(("❌", "C1", "缺 R041（收敛后的协议条目）"))

    # D 退役索引
    ret = d.get("retiredEntries") or []
    if not ret:
        out.append(("❌", "D1", "缺 retiredEntries（数据搬出账本后必须留退役索引，否则溯源断裂）"))
    else:
        ret_ids = [e.get("id") for e in ret]
        still_live = [i for i in ret_ids if i in ids]
        if still_live:
            out.append(("❌", "D2", "退役索引里的 id 仍在现役 rules（矛盾）: %s" % ", ".join(map(str, still_live[:8]))))
        no_dest = [e.get("id") for e in ret if not e.get("movedTo")]
        if no_dest:
            out.append(("❌", "D3", "退役条目缺 `movedTo`（去向）: %s" % ", ".join(map(str, no_dest[:8]))))

    # E 溯源可闭合
    #   ★ G29（2026-10-04）：`--constraints` 命中「缺文件/空文件」时**必须给明确结论**，
    #     不得裸抛栈 —— 独立复核对端账本时对端根本没有我这个工件（实测踩到）。
    if constraints_path and not os.path.isfile(constraints_path):
        out.append(("❌", "E0", "缺约束表（--constraints 指向的文件不存在）: %s ⇒ **E 段溯源检查未执行**"
                    "（不是「通过」，请显式传对端/本方的约束表）" % constraints_path))
        c = None
    elif constraints_path:
        try:
            c = load(constraints_path)
        except Exception as e:
            out.append(("❌", "E0", "约束表不可读（%s）: %s ⇒ **E 段溯源检查未执行**（不是「通过」）"
                        % (type(e).__name__, str(e)[:80])))
            c = None
    else:
        c = None
    if c is not None:
        keys = ((c.get("ledgerIndex") or {}).get("keys") or [])
        live, retired = set(ids), set(e.get("id") for e in ret)
        dangle = [k.get("ruleId") for k in keys
                  if k.get("ruleId") is not None and k["ruleId"] not in live and k["ruleId"] not in retired]
        if dangle:
            out.append(("❌", "E1", "约束表 `ruleId` 悬空 %d 个（既非现役也非退役）: %s"
                        % (len(dangle), ", ".join(map(str, dangle[:8])))))
        if not keys:
            out.append(("❌", "E2", "约束表 `ledgerIndex.keys` 为空 ⇒ 数据没搬进去？"))

    # F md 侧同步（退役 id 不得仍有标题）
    if ret:
        pat = r"(?m)^##\s+(%s)\b" % "|".join(re.escape(str(e.get("id"))) for e in ret)
        left = re.findall(pat, md)
        if left:
            out.append(("❌", "F1", "md 仍保留已退役条目标题 %d 个: %s（json 删了 md 没删 ⇒ 双载体漂移）"
                        % (len(left), ", ".join(left[:8]))))

    # G md 无丢失
    md_r = len(re.findall(r"(?m)^##\s+R\d+\b", md))
    json_r = len([i for i in ids if re.fullmatch(r"R\d+", str(i))])
    if md_r < json_r:
        out.append(("❌", "G1", "md 的 R 标题(%d) 少于 json 的 R 条目(%d) ⇒ **疑似按行号截断误删 R 规则**"
                    % (md_r, json_r)))

    if not out:
        out.append(("✅", "OK", "全部不变量通过（数据已搬净 / 协议在位 / 退役索引成立 / 溯源闭合 / md 同步）"))
    return out


# ─────────────────────────── 正负样本自证 ───────────────────────────
def _write_fixture(d, rules, md, constraints=None):
    io.open(os.path.join(d, "rules.json"), "w", encoding="utf-8").write(
        json.dumps(rules, ensure_ascii=False, indent=2))
    io.open(os.path.join(d, "RULES.md"), "w", encoding="utf-8").write(md)
    cp = None
    if constraints is not None:
        cp = os.path.join(d, "constraints.json")
        io.open(cp, "w", encoding="utf-8").write(json.dumps(constraints, ensure_ascii=False, indent=2))
    return cp


def _good():
    rules = {"version": "2.17.0", "lastUpdated": "2026-10-03",
             "rules": [{"id": "R041", "category": "工程"}, {"id": "R001", "category": "协作"}],
             "retiredEntries": [{"id": "J1", "movedTo": "data/ops/resource-constraints.json#keys[file:x]"}]}
    md = "# 账本\n\n> v2.17.0 | 2 条 | x\n\n## R041 ✅ p\n- 分类: 工程\n\n## R001 ✅ q\n- 分类: 协作\n"
    con = {"ledgerIndex": {"keys": [{"key": "file:x", "ruleId": "J1"}]}}
    return rules, md, con


def _selftest():
    print("verify-r041-migration 自证（正负样本：每条不变量都要能被触发）")
    ok = True
    tmp = tempfile.mkdtemp(prefix="v041-")

    def run(name, rules, md, con, want_codes, expect_ok):
        nonlocal ok
        d = tempfile.mkdtemp(dir=tmp)
        cp = _write_fixture(d, rules, md, con)
        rows = check(d, cp)
        codes = [c for lv, c, _ in rows]
        good = (codes == ["OK"]) if expect_ok else all(c in codes for c in want_codes)
        ok = ok and good
        print("  %s %-46s 期望%-22s 实际 %s" % (
            "✅" if good else "❌", name,
            "OK" if expect_ok else "含 " + ",".join(want_codes), ",".join(codes)))

    r, m, c = _good()
    run("全量通过（负样本，防过杀）", r, m, c, [], True)

    r2 = json.loads(json.dumps(r)); r2["rules"].append({"id": "J7", "category": "资源冲突"})
    run("B1 仍有资源冲突条目", r2, m, c, ["B1"], False)

    r3 = json.loads(json.dumps(r)); r3["rules"] = [x for x in r3["rules"] if x["id"] != "R041"]
    run("C1 缺 R041", r3, m, c, ["C1"], False)

    r4 = json.loads(json.dumps(r)); r4["retiredEntries"] = []
    run("D1 缺退役索引", r4, m, c, ["D1"], False)

    r5 = json.loads(json.dumps(r)); r5["retiredEntries"][0]["movedTo"] = ""
    run("D3 退役条目缺去向", r5, m, c, ["D3"], False)

    c6 = {"ledgerIndex": {"keys": [{"key": "file:x", "ruleId": "J999"}]}}
    run("E1 约束表 ruleId 悬空", r, m, c6, ["E1"], False)

    m7 = m + "\n## J1 ✅ 没删干净\n- 分类: 资源冲突\n"
    run("F1 md 仍留退役条目标题", r, m7, c, ["F1"], False)

    m8 = m.replace("## R001 ✅ q\n", "")     # 模拟"按行号截断误删 R 规则"
    run("G1 md 的 R 标题少于 json（误删）", r, m8, c, ["G1"], False)

    m9 = m.replace("> v2.17.0 | 2 条", "> v9.9.9 | 5 条")
    run("A2/A3 版本与条数漂移", r, m9, c, ["A2", "A3"], False)

    print()
    print("  ⇒ %s" % ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default=os.path.expanduser("~/dsh-collab/rules-registry"))
    ap.add_argument("--constraints",
                    default=os.path.expanduser("~/dsh-collab/data/ops/resource-constraints.json"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    rows = check(a.registry, a.constraints)
    print("R041 迁移自校验 · registry=%s" % a.registry)
    for lv, code, msg in rows:
        print("  %s [%s] %s" % (lv, code, msg))
    bad = [r for r in rows if r[0] == "❌"]
    print()
    print("  ⇒ %s" % ("✅ 迁移干净" if not bad else "❌ %d 项不通过 —— **别当成功**" % len(bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
