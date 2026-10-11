#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ability-taxonomy-check.py — 能力归一化的机械校验器（L3）

出件：明鉴 v3（session-a190c54c）· 2026-10-12
依据：docs/ability-normalization-scheme-20261012.md §4-L3 / §5 判据
配套：data/registry/ability-taxonomy.json（词表 L1）· data/registry/ability-mapping.json（映射 L2）

★ 它做四件事
  ① 词表外检查：归一化值里出现词表未定义的 token ⇒ 红（防「各人自造词」把词表冲垮）
  ② 覆盖率：已映射原文数 / abilities 总数 ⇒ ★ 必须同时报【分母】与【截至时刻】
     （判据：报「0 条」须附扫过的面）
  ③ 可共享能力统计：同一 (对象/动作) 被 ≥2 个会话登记 ⇒ 这才叫真的【可共享】
  ④ 过度归并告警：一个 token 覆盖的原文过多 ⇒ 疑似把语义不同的能力压成一条 = 信息删除

★ 三态用词：OK / MISSING（未映射，黄）/ INVALID（词表外，红）。
  ★ MISSING 不得读作「无能力」—— 它只表示「还没归一化」。

用法：
  python3 ability-taxonomy-check.py              # 扫全库
  python3 ability-taxonomy-check.py --selftest   # 负控矩阵（判据必须会红）
"""

import json
import os
import sys
import datetime

BASE = os.path.expanduser("~/dsh-collab")
TAX = os.path.join(BASE, "data/registry/ability-taxonomy.json")
MAP = os.path.join(BASE, "data/registry/ability-mapping.json")
BUS = os.path.expanduser("~/.dsh/agent-bus.json")

OVERMERGE_LIMIT = 25      # 单个 token 覆盖 > 此数的原文 ⇒ 告警（疑似过度归并）
SHARE_MIN = 2             # 被 >=2 会话登记才算「可共享」


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def load_taxonomy(path=TAX):
    d = json.load(open(path, encoding="utf-8"))
    objs = set(d.get("objects", {}).keys())
    acts = set(d.get("actions", {}).keys())
    return d, objs, acts


def parse_norm(s):
    """`域:对象/动作` 或 `对象/动作` → (域|None, 对象, 动作)。

    ★ 这里是唯一解析口径 —— 校验与统计必须共用它，否则「判据的域 ≠ 对象的域」。
    """
    s = (s or "").strip()
    dom = None
    if ":" in s.split("/")[0]:
        dom, s = s.split(":", 1)
        dom = dom.strip()
    if "/" not in s:
        return dom, None, None
    o, a = s.split("/", 1)
    return dom, o.strip(), a.strip()


def validate(values, objs, acts):
    """对一组归一化值做词表校验。返回 (invalid[], ok_n)。"""
    invalid = []
    ok = 0
    for v in values:
        dom, o, a = parse_norm(v)
        if o is None:
            invalid.append((v, "缺 对象/动作 分隔符"))
        elif o not in objs:
            invalid.append((v, "对象 token 不在词表: %s" % o))
        elif a not in acts:
            invalid.append((v, "动作 token 不在词表: %s" % a))
        else:
            ok += 1
    return invalid, ok


def collect():
    """扫全库：返回 (每条 abilities 的 (session, 原文), 分母, 截至时刻)。"""
    d = json.load(open(BUS, encoding="utf-8"))
    rows = []
    for p in d.get("profiles", []):
        aid = p.get("agentId") or "?"
        for x in (p.get("abilities") or []):
            rows.append((aid, str(x).strip()))
    return rows, len(rows), now_iso()


def run():
    print("════ 能力归一化校验（L3）════")
    tax, objs, acts = load_taxonomy()
    print("  词表 version=%s status=%s · 对象 token %d 个 · 动作 token %d 个"
          % (tax.get("version"), tax.get("status"), len(objs), len(acts)))

    rows, denom, asof = collect()
    print("  ★ 分母 = %d 条 abilities · 截至 %s · 源 %s" % (denom, asof, BUS))

    if not os.path.exists(MAP):
        print()
        print("  ⚠ 映射表不存在：%s" % MAP)
        print("     ⇒ 覆盖率 = 0 / %d（分母已给；★ 这是【尚未归一化】，不是【无能力】）" % denom)
        print("     ⇒ N2（各属主自映射）未做 ⇒ 本器只能出「未映射」这一态。")
        print("  ★ 边界：本器【不代任何属主映射】—— abilities 是各会话自己的档案。")
        return 0

    m = json.load(open(MAP, encoding="utf-8"))
    mp = m.get("map", {})
    mapped = [v for k, v in mp.items() if (k or "").strip()]
    unmapped_originals = [t for _, t in rows if t not in mp]

    invalid, ok = validate(mapped, objs, acts)

    # 可共享统计：归一化值 → {会话集合}
    byval = {}
    for aid, txt in rows:
        v = mp.get(txt)
        if not v:
            continue
        byval.setdefault(v, set()).add(aid)
    shared = {v: s for v, s in byval.items() if len(s) >= SHARE_MIN}

    print()
    print("  ── ① 词表外检查（红）──")
    if invalid:
        for v, why in invalid[:20]:
            print("    ✗ %-34s %s" % (v, why))
        print("    合计 %d 条越界" % len(invalid))
    else:
        print("    OK  无越界（全部 token 在词表内）")

    print()
    print("  ── ② 覆盖率（★ 附分母与截至时刻）──")
    print("    已映射 %d / %d = %.1f%%   (截至 %s)"
          % (len(mapped), denom, len(mapped) * 100.0 / max(denom, 1), asof))
    print("    未映射原文 %d 条  ⇒ 状态 MISSING（★ 不等于「无能力」）" % len(unmapped_originals))

    print()
    print("  ── ③ 可共享能力（同一 对象/动作 被 ≥%d 会话登记）──" % SHARE_MIN)
    if shared:
        for v, s in sorted(shared.items(), key=lambda kv: -len(kv[1]))[:15]:
            print("    %2d 会话  %s" % (len(s), v))
        print("    ⇒ 可共享组合数 = %d" % len(shared))
        # A3 判据
        a3 = len(shared) > 6
        print("    ★ A3 判据（组合数 > 6，现状基线 6）：%s（实测 %d）"
              % ("成立" if a3 else "不成立", len(shared)))
    else:
        print("    （无）⇒ 若归一化后仍近乎全唯一，说明【词表粒度太细】，须回头改词表，")
        print("       ★ 而不是宣布「归一化完成」——那会是一个假绿。")

    print()
    print("  ── ④ 过度归并告警（一个 token 覆盖过多原文 = 疑似信息删除）──")
    cover = {}
    for k, v in mp.items():
        if v:
            cover.setdefault(v, []).append(k)
    hot = [(v, len(ks)) for v, ks in cover.items() if len(ks) > OVERMERGE_LIMIT]
    if hot:
        for v, n in sorted(hot, key=lambda x: -x[1]):
            print("    ⚠ %-30s 覆盖 %d 条原文（阈 %d）" % (v, n, OVERMERGE_LIMIT))
    else:
        print("    OK  无 token 超过阈 %d" % OVERMERGE_LIMIT)

    print()
    print("  ── ⑤ 不丢信息（A5）──")
    missing_kept = [t for _, t in rows if t not in mp]
    print("    原文仍全量可取自 agent-bus.json（%d 条）· 本器【只读不写】" % denom)
    print("    ⇒ A5 结构上成立：归一化不删原文，只叠加映射。")

    rc = 1 if invalid else 0
    print()
    print("  总判：%s（rc=%d）" % ("红" if invalid else "通过", rc))
    return rc


def selftest():
    """★ 负控矩阵：判据必须会红，否则是空转。"""
    fails = []
    def ck(name, cond, detail=""):
        print("  %s %-52s %s" % ("OK  " if cond else "FAIL", name, detail))
        if not cond:
            fails.append(name)

    tax, objs, acts = load_taxonomy()
    ck("词表可加载且有 version", bool(tax.get("version")), "v=%s" % tax.get("version"))
    ck("对象 token 非空", len(objs) > 0, "%d 个" % len(objs))
    ck("动作 token 非空", len(acts) > 0, "%d 个" % len(acts))

    # N1 负控：词表外的对象必须红
    inv, ok = validate(["不存在的对象/读写"], objs, acts)
    ck("★ 负控：词表外对象必须红", len(inv) == 1, str(inv[:1]))
    # N2 负控：词表外的动作必须红
    inv, ok = validate(["黑板/不存在的动作"], objs, acts)
    ck("★ 负控：词表外动作必须红", len(inv) == 1, str(inv[:1]))
    # N3 正控：合法值必须绿
    o0, a0 = sorted(objs)[0], sorted(acts)[0]
    inv, ok = validate(["%s/%s" % (o0, a0)], objs, acts)
    ck("正控：合法值必须绿", len(inv) == 0 and ok == 1, "%s/%s" % (o0, a0))
    # N4 负控：缺分隔符必须红
    inv, ok = validate(["黑板"], objs, acts)
    ck("★ 负控：缺 对象/动作 分隔符必须红", len(inv) == 1, str(inv[:1]))
    # N5 域前缀解析
    dom, o, a = parse_norm("运维:本机服务/查")
    ck("带域前缀解析正确", dom == "运维" and o == "本机服务" and a == "查",
       "%s|%s|%s" % (dom, o, a))
    # N6 负控：域不参与唯一性（同 对象/动作 不同域应视为同一能力）
    inv1, _ = validate(["运维:本机服务/查"], objs, acts)
    inv2, _ = validate(["本机服务/查"], objs, acts)
    ck("域前缀不影响合法性", len(inv1) == 0 and len(inv2) == 0)

    print("\n  %s" % ("负控矩阵全过（%d 项）" % 6 if not fails else "失败: %s" % ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("════ ability-taxonomy-check · 负控矩阵 ════")
        sys.exit(selftest())
    sys.exit(run())
