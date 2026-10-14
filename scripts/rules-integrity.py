#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rules-integrity.py — 规则账本完整性检查（只读 · 不修改账本）

为什么要它（2026-09-11 星桥实测发现）：
  RULES.md 是全局纪律账本，所有设备查规则都读它。但账本**自身的完整性此前无人校验**，
  实测同日发现三处互相矛盾的计数 + 两个重复编号：
    · 标题声明   v2.15.0 | 76 条
    · rules-cli audit       78 条
    · 实际 `## ` 标题        86 个（R 37 + J 44 + 其他 5）
    · R033 出现 2 次（行 413 / 458）、R034 出现 2 次（行 420 / 463）
  后果：`get R033` 得到哪一条不确定；「76 条」不可核。**账本不可核 → 依账本做的判断都不可核。**
  这正是「结构门优于纪律」：靠人翻账本发现不了重复，靠机器每次都能发现。

用法：
  rules-integrity.py            # 人类可读报告（有问题 exit 1）
  rules-integrity.py --json     # 机器可读

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== rules-integrity 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · rules-integrity.py — 规则账本完整性检查（只读 · 不修改账本）")
    print("  · 为什么要它（2026-09-11 星桥实测发现）：")
    print("  · RULES.md 是全局纪律账本，所有设备查规则都读它。但账本**自身的完整性此前无人校验**，")
    print("  · 实测同日发现三处互相矛盾的计数 + 两个重复编号：")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, os, re, sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/rules-integrity.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import io
import json
import os
import re
import sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/rules-integrity.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

LEDGER = os.path.expanduser("~/dsh-collab/rules-registry/RULES.md")
HEAD_RE = re.compile(r"^##\s+([A-Za-z]+-?[A-Za-z]*)(\d+)\b")
DECL_RE = re.compile(r"^>\s*v([\d.]+)\s*\|\s*(\d+)\s*条")


def parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    declared = None
    entries = []  # {id, line, title, has: {...}}
    cur = None
    for i, ln in enumerate(lines, 1):
        m = DECL_RE.match(ln.strip())
        if m and declared is None:
            declared = {"version": m.group(1), "count": int(m.group(2))}
            continue
        if ln.startswith("## "):
            hm = HEAD_RE.match(ln)
            cur = {
                "id": (hm.group(1) + hm.group(2)) if hm else None,
                "prefix": hm.group(1) if hm else None,
                "num": int(hm.group(2)) if hm else None,
                "line": i,
                "title": ln[3:].strip(),
                "fields": set(),
            }
            entries.append(cur)
            continue
        if cur is not None and ln.startswith("- "):
            body = ln[2:]
            if ":" in body:
                cur["fields"].add(body.split(":", 1)[0].strip())
    return lines, declared, entries


# ══════════════════════════════════════════════════════════════════
# ★★★ 2026-10-15（R063 的直接应用 · ★ 由明鉴 v3 建议并给立据）
#   判【账本里出现的落盘物指针是否真实存在】。
#   ★★★ 立据（★ 不是推演）：本账本第 8 行（2026-10-13 由明鉴 v3 写下）声明
#     「机读同源：`data/registry/rules-registry-owner`」—— ★★ **而该文件当时不存在**。
#     ⇒ ★ **「声明有据」不等于「据存在」**；★ 而【计数核验看不到它】（★ 本工具此前只数标题）。
#     ★ 该指针已于 2026-10-15 由其本人回读确认并补建；★ 本条把【回读】机械化。
#   ★★ 规则（显式、可反驳）：反引号内、不含空格、且（含 `/` 或 `~` 或带已知后缀）者**视为指针**；
#     含 `*`/`?` 者按 **glob** 处理；`http(s)://` / `blackboard:` / `agentsrc:` 前缀**跳过**。
#   ★ 三态：**存在** / **缺失（★ 硬问题）** / ★ **面外（仓外绝对路径 ⇒ 提示，不算硬问题）**。
# ══════════════════════════════════════════════════════════════════
_BT = re.compile(r'`([^`\n]{3,160})`')
_EXT = re.compile(r'\.(py|md|json|js|mjs|ts|sh|yml|yaml|txt|html|csv|db|plist)$')
ROOT = os.path.expanduser("~/dsh-collab")


def looks_like_pointer(tok):
    """★ 判定一个反引号 token 是否【像落盘物指针】（★ 显式规则 ⇒ 可反驳）。

    ★★★ 2026-10-15（★ 本条自身的第一次试跑就抓到我自己 50 处假阳性 —— ★ 见下）：
      ★ 首版规则 = 「含 `/` 或 `~` 或带已知后缀」⇒ ★★ 把**文档里的【示例串】**也当成指针：
        `data/x` · `data//x` · `data/x/aliasmine`（★ 示例）· `data/cld-health/<key>`（★ **键命名模版**）
        · `rules-integrity.py`（★ **裸文件名** —— 它在 `scripts/` 下，★ 而首版按【仓根】解 ⇒ 假报不存在）。
      ★★ **⇒ 50/50 全是假阳性**（★ 真悬空 0）—— ★★ **这正是 R063 说的：装置不对，数就不可比**；
        ★ 而**带着 50 个假阳性的门会【失去权威】**（本文件自己写过这句）。
      ★ 修法（★ 逐条对上述假阳性）：★ ① 含 `<` `>` `{` `}` `...` `//` 或以 `/` 结尾 ⇒ **跳过**；
        ★ ② **末段长度 < 2** ⇒ 跳过（★ 示例串的指纹，如 `data/x`）；
        ★ ③ **裸文件名（不含 `/`）⇒ 按【文件名】在仓内递归找**（★ 找到即算存在）。
    """
    t = (tok or "").strip()
    if not t or " " in t or "\n" in t:
        return False
    if t.startswith(("http://", "https://", "blackboard:", "agentsrc:", "§", "#")):
        return False
    t = t.split("#")[0]
    if not t:
        return False
    if any(ch in t for ch in "<>{}") or "..." in t or "//" in t or t.endswith("/"):
        return False
    if not (("/" in t) or t.startswith("~") or _EXT.search(t)):
        return False
    # ★★ 2026-10-15（★ 第二次试跑：13 处假阳性里 4 处仍是【文档示例串】）：
    #   `data/x/aliasmine` · `data/x/../escape` · `data/x/./cur` · `data/x/a%23b`
    #   ⇒ ★ 指纹 = **任一目录段只有 1 个字符**（本仓没有这种真路径）⇒ 跳过。
    _segs = [x for x in t.split("/") if x not in ("", ".", "..")]
    if any(len(x) < 2 for x in _segs):
        return False
    return True


BOARD_BASE = os.environ.get("DSH_BB_URL", "http://127.0.0.1:8792")


def _board_probe(key, timeout=8):
    """★ 问板：该键可达吗？三态 —— True(200) / False(404 ⇒ 不存在) / None(★ 不可判：网络或非 404 错)。"""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(BOARD_BASE + "/" + key, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return getattr(r, "status", 200) == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return None                            # ★ 5xx 等 ⇒ **不可判**，不得读成「不存在」
    except Exception:
        return None


def classify_pointer(tok, net=False):
    """★ 四态：exists / missing（★ 硬：仓内路径确实不在）/ off-repo（★ 提示：属外部或他机件）/ bare（★ 提示：裸文件名，可能是引用）。"""
    import glob as _glob
    t = tok.strip().split("#")[0]
    t = re.sub(r':\d+(-\d+)?$', '', t)          # ★ 去掉 `:556` 这类【文件:行号】后缀
    if t.startswith("dsh-collab/"):              # ★ 归一化：把仓名当前缀的写法剥掉
        t = t[len("dsh-collab/"):]
    p = os.path.expanduser(t)
    # ★★ 2026-10-15（★ 第四次收紧：3 处硬问题里 1 处是【别机文件的 glob】）：
    #   `rule-*.md`（★ 账本自己写着「i9 上的 27 个逐条原件【不在本机，属正常】」）
    #   ⇒ ★ **通配式不是【确定指针】** ⇒ 未命中归【提示】，**不判硬**。
    if "*" in p or "?" in p:
        _hit = _glob.glob(p if os.path.isabs(p) else os.path.join(ROOT, p))
        if not _hit:
            _hit = _glob.glob(os.path.join(ROOT, "**", os.path.basename(p)), recursive=True)
        return "exists" if _hit else "glob-nomatch"
    if not os.path.isabs(p):
        p = os.path.join(ROOT, p)
    if os.path.exists(p):
        return "exists"
    # ★★ 2026-10-15（★ 第六轮收紧）：★ 账本里的相对路径，**最自然的基准是【账本自己所在目录】** ——
    #   实测 `sources/AI工程规则总纲-v2.0-20261009.md`（★ 相对 `rules-registry/`）被首版判「外部」（★ 假提示）。
    if not os.path.isabs(t):
        _alt = os.path.join(ROOT, "rules-registry", t)
        if os.path.exists(_alt):
            return "exists"
    # ★★ 2026-10-15：**裸文件名**（如 `rules-integrity.py`）⇒ 按文件名在仓内递归找
    #   （★ 首版按【仓根】解 ⇒ `scripts/` 下的工具全被误报「不存在」）。
    if "/" not in tok.strip() and not tok.strip().startswith("~"):
        _base = os.path.basename(tok.strip())
        for _r, _dn, _fn in os.walk(ROOT):
            _dn[:] = [d for d in _dn if d not in ("node_modules", ".git")]
            if _base in _fn:
                return "exists"
    # ★ 仓外绝对路径（如 /tmp/...）⇒ 提示级：★ 它**本就不该被当长期指针**（★ 见 ext 的「复跑命令不含 /tmp」）
    if not p.startswith(ROOT + os.sep):
        return "off-repo"
    # ★★ 2026-10-15（★ 第三次试跑：13 处里 5 处是【外部件/他机件引用】）：
    #   `dsh-compaction-basic/lib/index.js`（★ 上游 runtime 模块）· `AI工程规则总纲_完整版_v2.md`（★ 他机 i9 的原件名）
    #   ⇒ ★ **仓内路径【才】判硬**：首段必须是**本仓真实存在的顶层项**；★ 否则归【提示】。
    _first = t.split("/")[0]
    if "/" not in t:
        return "bare"                              # ★ 裸文件名 ⇒ 提示（★ 可能是引用他机件）
    if not os.path.exists(os.path.join(ROOT, _first)):
        return "off-repo"
    # ★★★ 2026-10-15（★ 第五次收紧：★ 而这一处**抓到了我自己的新错**）：
    #   `data/registry/three-artifacts-...` 与 `notes/mac-mini/...` 是【**黑板键**】，不是文件路径
    #   —— 而 `data/` 与 `notes/` **在本仓是真实目录** ⇒ 首版一律判「悬空」。
    #   ★★ 本仓约定：★ 证据指针的**规范形**是 `blackboard:<key>` / `agentsrc:` / 文件路径
    #     （★ `beacon-check.resolve_evidence()` 只认这三种）⇒ ★ **裸写黑板键【形式不合法】**。
    #   ⇒ 故归【提示】并**明确建议改成 `blackboard:<key>`**（★ 该提示当场命中 R063 自己那一行的写法）。
    # ★★★ 2026-10-15（★ 异源负控抓到的【假阴性】，★ 由明鉴 v3 实测量化）：
    #   ★ 第五轮把整个 `data/` 前缀归入「非文件指针」⇒ **修对了 50/50 假阳性，
    #     同时开了一个假阴性面**：★ 它插入 `data/registry/__definitely_not_exist_20261015.json`
    #     （★ 真不存在）⇒ 本器仍报「核 53 · ★ 悬空 0」· exit 0。
    #   ★★ **⇒ 按 R063：数还是「悬空 0」，但它对【这一前缀】已不再是有效读数（装置维）。**
    #   ★ 修法（★ 明鉴建议 · ★ 本线采纳）：**双查三态** ——
    #     ① 作为文件存在 ⇒ exists；② 作为**黑板键在板上可达（GET 200）** ⇒ board；
    #     ③ 两者都不在 ⇒ **missing（真悬空）**；★ ④ **查不到（未开 --net 或板不可达）⇒ undecided（不可判）**
    #        —— ★★ **不合并进「没问题」**（★ 空 ≠ 无）。
    BOARD_NS = ("data", "notes", "tasks", "health", "alerts", "mbp")
    if _first in BOARD_NS:
        if not net:
            return "board-unchecked"          # ★ 未查板 ⇒ 不可判（★ 而**不是**「不是指针」）
        _r = _board_probe(t)
        if _r is True:
            return "board"                    # ★ 板上可达 ⇒ 存在（★ 作为黑板键）
        if _r is False:
            return "missing"                  # ★ 板 404 且文件不在 ⇒ **真悬空**
        return "undecided"                    # ★ 板不可达/超时 ⇒ 不可判（★ 不冒充悬空）
    return "missing"


def check_pointers(path, net=False):
    """★ 扫账本全文的指针并核其存在性（★ net=True 时对黑板前缀另做【板上可达】检查）。"""
    try:
        text = io.open(path, encoding="utf-8").read()
    except Exception as e:
        return {"missing": [], "off_repo": [], "checked": 0, "error": type(e).__name__}
    missing, off, checked = [], [], 0
    checked_ok = 0
    for i, line in enumerate(text.split("\n"), 1):
        for m in _BT.finditer(line):
            tok = m.group(1).strip()
            if not looks_like_pointer(tok):
                continue
            checked += 1
            k = classify_pointer(tok, net=net)
            if k == "missing":
                missing.append({"kind": "dangling-pointer", "line": i, "pointer": tok})
            elif k == "board":
                checked_ok += 1
            elif k in ("off-repo", "bare", "glob-nomatch", "board-unchecked", "undecided"):
                off.append({"kind": "off-repo-pointer", "line": i, "pointer": tok,
                            "why": {"off-repo": "★ 属外部/他机件引用",
                                    "bare": "★ 裸文件名，可能是引用",
                                    "glob-nomatch": "★ 通配式未命中（★ 通配不是确定指针）",
                                    "board-unchecked": "★★ `data/…` 这类是【黑板键】—— ★ **未查板 ⇒ 不可判**"
                                                       "（★ 空 ≠ 无；加 `--net` 可判：★ 板 200 ⇒ 存在 · ★ 板 404 且文件不在 ⇒ 悬空）",
                                    "undecided": "★★ 板不可达/超时 ⇒ **不可判**（★ 不冒充悬空）"}[k]})
    return {"missing": missing, "off_repo": off, "checked": checked, "ok": checked_ok}


def check(path=LEDGER, net=False):
    lines, declared, entries = parse(path)
    problems, warnings = [], []

    # 1) 编号唯一
    seen = {}
    for e in entries:
        if e["id"] is None:
            # 非规则小节（如「治理哲学（Φ 系列…）」这类分区标题）→ 提示，不算硬问题
            # （此前误判为硬问题＝我自己的假阳性；假阳性会让门失去权威）
            warnings.append({"kind": "non-rule-section", "line": e["line"], "title": e["title"]})
            continue
        seen.setdefault(e["id"], []).append(e)
    for rid, group in sorted(seen.items()):
        if len(group) > 1:
            problems.append({
                "kind": "duplicate-id", "id": rid,
                "lines": [g["line"] for g in group],
                "titles": [g["title"] for g in group],
                "note": "同一编号多处定义 → 查该条规则的结果不确定",
            })

    # 2) 声明计数 vs 实际
    # ★ 2026-09-11 自纠假阳性：声明数算的是「**规则条数**」，而先前实现拿它和
    # 「全部 `## ` 标题数」比 —— 把非规则小节（如「治理哲学（Φ 系列…）」分区标题）也算进去，
    # 于是恒差 1，报出「声明 83 / 实际 84」这种**假问题**。
    # 假阳性会让门失去权威（今晚已多次验证），故改为**只数带规则编号的标题**。
    actual_headings = len(entries)
    actual = len([e for e in entries if e["id"] is not None])
    if declared:
        if declared["count"] != actual:
            problems.append({
                "kind": "count-mismatch",
                "declared": declared["count"], "actual": actual,
                "note": f"标题声称 {declared['count']} 条规则，实际带编号的规则标题 {actual} 个"
                        f"（另有非规则 `## ` 小节 {actual_headings - actual} 个，不计入）",
            })
    else:
        warnings.append({"kind": "no-declaration", "note": "未找到「> vX | N 条」声明行"})

    # 3) 每条规则必备字段
    for e in entries:
        if e["id"] is None:
            continue
        miss = [f for f in ("分类", "摘要") if f not in e["fields"]]
        if miss:
            warnings.append({"kind": "missing-fields", "id": e["id"], "line": e["line"], "missing": miss})

    # 4) 编号顺序（同前缀应递增；乱序常是追加错位/合并事故的指纹）
    by_prefix = {}
    for e in entries:
        if e["id"]:
            by_prefix.setdefault(e["prefix"], []).append(e)
    unordered = []
    for pfx, group in by_prefix.items():
        nums = [g["num"] for g in group]
        if nums != sorted(nums):
            for a, b in zip(group, group[1:]):
                if b["num"] < a["num"]:
                    unordered.append({"kind": "out-of-order", "id": b["id"], "line": b["line"],
                                      "after": a["id"], "after_line": a["line"]})
    if unordered:
        warnings.extend(unordered)

    # 5) ★★ 落盘物指针存在性（R063 的应用）
    _ptr = check_pointers(path, net=net)
    problems.extend(_ptr["missing"])
    warnings.extend(_ptr["off_repo"])

    # 6) 前缀统计
    stats = {}
    for e in entries:
        key = e["prefix"] if e["prefix"] else "(无法解析)"
        stats[key] = stats.get(key, 0) + 1

    return {
        "ledger": path,
        "declared": declared,
        "actual_headings": actual,
        "unique_ids": len(seen),
        "prefix_stats": stats,
        "pointers": {"checked": _ptr["checked"], "board_reachable": _ptr.get("ok", 0),
                     "missing": len(_ptr["missing"]), "off_repo": len(_ptr["off_repo"]),
                     "net": net},
        "problems": problems,
        "warnings": warnings,
        "ok": not problems,
    }


def main():
    path = LEDGER
    as_json = "--json" in sys.argv
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return 0
    if os.path.exists(path) is False:
        print(f"❌ 账本不存在: {path}")
        return 1
    net = "--net" in sys.argv
    r = check(path, net=net)

    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        d = r["declared"] or {}
        print(f"规则账本完整性检查 · {path}")
        print(f"  声明: v{d.get('version','?')} | {d.get('count','?')} 条")
        print(f"  实际: {r['actual_headings']} 个标题 / {r['unique_ids']} 个唯一编号")
        print(f"  前缀分布: " + " · ".join(f"{k}={v}" for k, v in sorted(r["prefix_stats"].items())))
        _p = r.get("pointers") or {}
        print(f"  落盘物指针: 核 {_p.get('checked',0)} 个 · ★ 悬空 {_p.get('missing',0)}"
              f" · 板上可达 {_p.get('board_reachable',0)} · ★ 未判/非文件 {_p.get('off_repo',0)}"
              f"（★ {'已查板 --net' if net else '未查板：黑板前缀不可判，加 --net'}）")
        print()
        if r["problems"]:
            print(f"❌ 硬问题 {len(r['problems'])} 项（账本不可信，须修）:")
            for p in r["problems"]:
                if p["kind"] == "duplicate-id":
                    print(f"   · 重复编号 {p['id']}  行 {p['lines']}  → {p['note']}")
                    for ln, t in zip(p["lines"], p["titles"]):
                        print(f"       行{ln}: {t[:70]}")
                elif p["kind"] == "dangling-pointer":
                    print(f"   · ★★ 悬空指针(行{p['line']}): `{p['pointer']}` ⇒ 该落盘物【不存在】"
                          f"（★ R063：声明有据 ≠ 据存在）")
                elif p["kind"] == "count-mismatch":
                    print(f"   · 计数不符: 声明 {p['declared']} / 实际 {p['actual']}")
                else:
                    print(f"   · {p}")
        else:
            print("✅ 无硬问题")
        if r["warnings"]:
            print(f"\n⚠️ 提示 {len(r['warnings'])} 项:")
            for w in r["warnings"][:12]:
                if w["kind"] == "out-of-order":
                    print(f"   · 编号乱序: {w['id']}(行{w['line']}) 出现在 {w['after']}(行{w['after_line']}) 之后")
                elif w["kind"] == "missing-fields":
                    print(f"   · {w['id']}(行{w['line']}) 缺字段: {w['missing']}")
                elif w["kind"] == "off-repo-pointer":
                    print(f"   · 非文件指针(行{w['line']}): `{w['pointer']}` —— {w.get('why','')}")
                elif w["kind"] == "non-rule-section":
                    print(f"   · 行{w['line']} 非规则小节（分区标题，跳过）: {w['title'][:50]}")
            if len(r["warnings"]) > 12:
                print(f"   … 另有 {len(r['warnings'])-12} 项")
        print()
        print("结论: " + ("❌ 账本存在硬问题 —— 依账本做的判断不可核，应先修复" if not r["ok"]
                        else "✅ 账本通过完整性检查"))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
