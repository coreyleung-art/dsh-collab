#!/usr/bin/env python3
"""收敛表完整性检查：议题 ↔ 卡键 是否指向同一对象。

由来（HR 2026-09-22）：明鉴的拟行存在【系统性偏移】——
  【议题】取自他当下正在讨论的新题目，【卡键/标识】取自当时已落的那张卡，
  两者天然错开一轮 ⇒ 议题被下一张卡「占用」。
HR 建议的机械检查：议题关键词须能在该行卡键所指的卡内命中，否则报错配。

用法：python3 table-integrity-check.py [--bb http://127.0.0.1:8792]
退出码：0 = 无错配；1 = 有错配
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, re, sys, urllib.request

BB = "http://127.0.0.1:8792"
if "--bb" in sys.argv:
    BB = sys.argv[sys.argv.index("--bb") + 1]
TABLE = "data/registry/thread-convergence-table-20260911"


def get(key):
    try:
        with urllib.request.urlopen(f"{BB}/{key}", timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"__error__": str(e)[:80]}


def main():
    env = get(TABLE)
    if "__error__" in env:
        print(f"表不可读: {env['__error__']}")
        return 2
    rows = env.get("value", {}).get("rows", [])
    print(f"收敛表 · {len(rows)} 行 · 读取于 {env.get('ts')} · ver={env.get('version')}")

    checked = skipped = 0
    bad, dup_issue = [], {}
    for i, r in enumerate(rows, 1):
        key = str(r.get("卡键", "")).strip()
        issue = str(r.get("议题", ""))
        tid = str(r.get("归属线程", ""))
        if not key or key in ("无产物", "无", "—"):
            skipped += 1
            continue
        card = get(key)
        if "__error__" in card:
            bad.append((i, issue[:44], key.split("/")[-1][:52], f"卡键 GET 失败: {card['__error__']}"))
            continue
        checked += 1
        txt = json.dumps(card.get("value", {}), ensure_ascii=False)
        # ★ 修（首跑抓到假阳性 R11）：原用「中文 2-4 字词」⇒ 把「标签三元」当成【一个词】，
        #   而卡里写的是「标签里的三项」⇒ 连写形式零命中 ⇒ 误报。
        #   根因是【词表粒度】错（与「序的来源」同族）：我按"人读起来像词"切，
        #   而匹配需要的是【最小可复用片段】⇒ 改为 2-gram + 覆盖率判据。
        grams = set()
        for run in re.findall(r"[\u4e00-\u9fa5]{2,}", issue):
            for i in range(len(run) - 1):
                grams.add(run[i:i + 2])
        latin = set(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{3,}", issue))
        cand = grams | latin
        hit = [w for w in cand if w in txt]
        cover = (len(hit) / len(cand)) if cand else 0
        if len(hit) < 2 or cover < 0.15:
            bad.append((i, issue[:44], key.split("/")[-1][:52],
                        f"议题关键词覆盖不足（命中 {len(hit)}/{len(cand)} = {cover:.0%}）"))
        # 顺带查重名（HR 曾把某行议题改成与另一行重名）
        dup_issue.setdefault(issue.strip(), []).append(i)

    print(f"  有卡键的行 {checked} 行 · 跳过（无产物）{skipped} 行")
    print(f"  ★ 错配 {len(bad)} 行")
    for i, iss, k, why in bad:
        print(f"    R{i} [{why}]")
        print(f"       议题: {iss}")
        print(f"       键  : {k}")
    dups = {k: v for k, v in dup_issue.items() if len(v) > 1 and k}
    print(f"  ★ 议题重名 {len(dups)} 组")
    for k, v in dups.items():
        print(f"    行 {v}: {k[:52]}")
    ok = not bad and not dups
    # ★ 2026-09-22 修（自指检查抓到）：原来这一行是【无条件判定】——
    #   而它上面刚报了条件（分母与读取时刻）。这正是我主张的「通过须带分母」，
    #   驿使 2026-09-22 也报了同族形态（拿一个条件去无条件断言另一个可测量的量）。
    #   ⇒ 判定行必须复述【检查点 · 分母 · 时刻】。
    print()
    print(f"判定: {'✅ 议题↔卡键全部对齐、无重名' if ok else '❌ 有错配或重名'}")
    print(f"  范围: 检查点=读表之后判定之前 · 覆盖=有卡键的 {checked} 行（跳过 {skipped} 行无产物）"
          f" · 读取于 {env.get('ts')} · ver={env.get('version')}")
    print(f"  ⇒ 本判定应读作「在有卡键的 {checked} 行上、于上述时刻、无错配无重名」——不是「全部检查通过」")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
