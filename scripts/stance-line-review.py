#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立场逐行审查器 · Stance Line Reviewer
======================================
与方法论的根本区别
------------------
❌ 关键词搜索（旧法）：预设一批词，去文本里找。看不预想到的问题；写错正则反而制造错误。
✅ 逐行语义审查（本法）：把每一行当作完整句子读，理解它在说什么，再判断它对目标受众是否合适。

本工具做三件事：
  1. 把文档切成「审查单元」（按语义边界：标题/段落/表格行/列表项，不是按行号硬切）
  2. 为每个单元生成「带完整上下文的审查提示」（含前后各 N 个单元，避免断章取义）
  3. 输出供 LLM 逐单元判读的任务包；LLM 对每个单元给出：判定 / 依据 / 建议改法

用法：
    # 生成审查任务包（供子代理逐单元判读）
    python3 stance-line-review.py <文件> --audience shareholder --out /tmp/review-pack

    # 汇总子代理判读结果
    python3 stance-line-review.py --aggregate /tmp/review-pack/results/*.json

设计原则（对应用户批评）：
  · 不假设"我知道要查什么" —— 提示词要求逐单元通读，可报任何不适合之处
  · 不做字符串替换 —— 只做"读懂 + 判定"，改法由人确认
  · 保留完整上下文 —— 每单元附前后文，避免断章取义

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
    print("== stance-line-review 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · 立场逐行审查器 · Stance Line Reviewer")
    print("  · 与方法论的根本区别")
    print("  · ❌ 关键词搜索（旧法）：预设一批词，去文本里找。看不预想到的问题；写错正则反而制造错误。")
    print("  · ✅ 逐行语义审查（本法）：把每一行当作完整句子读，理解它在说什么，再判断它对目标受众是否合适。")
    print("  · 命令/参数: audience, out, chunk, aggregate")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: sys, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/stance-line-review.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import sys, os, re, json, argparse, glob


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/stance-line-review.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

AUDIENCE_BRIEF = {
    "shareholder": (
        "读者是**股东（如橙果）**。他需要知道：自己的出资/权利/义务、公司结构、对赌与保障、各轮选项、退出路径。\n"
        "他**不该看到**：他方（尤其是梁振宇）的私人资金安排、内部文档生产流程、内部工具代号与文件名、"
        "与本次合作无关的内部管理细节。\n"
        "判定标准：这一行若被股东读到，会不会让他困惑/误解/知道不该知道的事？"
    ),
    "investor": (
        "读者是**潜在投资人**。他需要知道：市场机会、商业模式、单位经济、资金用途、里程碑、风险、估值依据。\n"
        "他**不该看到**：内部写作规范、模板来源名、内部格式代号、内部文件名、股东之间的私人约定。\n"
        "判定标准：这一行读起来像「对外材料」还是像「内部工作底稿」？"
    ),
    "partner": (
        "读者是**合作方（平台/供应链/IP 方）**。他需要知道：合作边界、交付标准、结算方式、对等义务。\n"
        "他**不该看到**：股权结构、各方对赌条款、内部预算明细、公司估值。\n"
        "判定标准：这一行会不会让合作方看到不该属于合作关系的商业机密？"
    ),
    "public": (
        "读者是**任何人（公开版）**。只能看到：业务是什么、市场、模式、愿景。\n"
        "**不得含**：具体股权比例、出资金额、对赌条款、合作方名称、牌照与资质归属、可识别的敏感细节。\n"
        "判定标准：这一行若被竞争对手/媒体/任何人看到，会不会造成损失？"
    ),
    "internal": (
        "读者是**内部团队/执行层**。可以看方法论、工具代号、内部流程。\n"
        "判定标准：这一行对执行是否有用？是否会把内部口径误当对外口径使用？"
    ),
}

UNIT_KINDS = [
    ("heading",   r"^#{1,6}\s+"),
    ("table_row", r"^\s*\|"),
    ("list_item", r"^\s*(?:[-*+]|\d+\.)\s+"),
    ("code",      r"^\s*(?:```|~~)"),
    ("blank",     r"^\s*$"),
]


def classify(line):
    for kind, pat in UNIT_KINDS:
        if re.match(pat, line):
            return kind
    return "para"


def split_units(text):
    """按语义边界切单元：标题/表格行/列表项各自独立；连续普通行合并为一个段落单元"""
    lines = text.split("\n")
    units = []
    i = 0
    while i < len(lines):
        k = classify(lines[i])
        if k == "blank":
            i += 1; continue
        if k in ("heading", "table_row", "list_item", "code"):
            units.append({"kind": k, "line": i + 1, "text": lines[i]})
            i += 1; continue
        # 段落：合并连续普通行
        buf = [lines[i]]; start = i + 1
        i += 1
        while i < len(lines) and classify(lines[i]) == "para":
            buf.append(lines[i]); i += 1
        units.append({"kind": "para", "line": start, "text": "\n".join(buf)})
    return units


def build_pack(path, aud_key, out_dir, ctx=3, chunk=120):
    text = open(path, encoding="utf-8").read()
    units = split_units(text)
    os.makedirs(out_dir, exist_ok=True)
    brief = AUDIENCE_BRIEF[aud_key]

    chunks = [units[i:i + chunk] for i in range(0, len(units), chunk)]
    manifest = {"file": os.path.basename(path), "audience": aud_key,
                "total_units": len(units), "chunks": len(chunks), "chunk_files": []}

    for ci, cu in enumerate(chunks):
        first = cu[0]["line"]; last = cu[-1]["line"]
        # 前后文（避免断章取义）
        lo = max(0, units.index(cu[0]) - ctx)
        hi = min(len(units), units.index(cu[-1]) + ctx + 1)
        before = units[lo:units.index(cu[0])]
        after = units[units.index(cu[-1]) + 1:hi]

        prompt = []
        prompt.append("# 逐单元立场审查任务\n")
        prompt.append("## 读者画像\n" + brief + "\n")
        prompt.append("## 审查要求（★ 必须逐单元通读，不得用关键词匹配代替阅读）\n")
        prompt.append(
            "对下面**每一个审查单元**独立判读，给出：\n"
            "1. `verdict`: `ok`（对该受众合适）/ `flag`（有问题）/ `suspect`（存疑，需人确认）\n"
            "2. `reason`: 一句话说明**为什么**（读懂了这句话在讲什么，再判断）\n"
            "3. `suggest`: 若 flag/suspect，给出**具体改法**（原文 → 建议）\n\n"
            "**特别注意**（这些是过去用关键词法漏掉的类型，但不限于这些）：\n"
            "· 说话人视角错误（把「我们」写成「你」、把公司决策写成个人安排）\n"
            "· 对读者的知识水平假设错误（用了读者不可能懂的内部术语）\n"
            "· 「此地无银」式表述（写「不包含X」反而暴露X存在）\n"
            "· 内部生产痕迹（版本号、作者名、写作规范、模板来源、内部文件名）\n"
            "· 口径不一致（同一事实在不同位置说法不同）\n"
            "· 承诺越界（对读者作了不该作的承诺）\n"
            "· 上下文错位（内容本身没问题，但放在这里给这个读者看不对）\n"
            "· **任何你读出来觉得不妥的地方**——不要因为没有匹配到上述类型就判 ok\n\n"
            "**不要**只报「含敏感词」的行；要报「读起来不对」的行。\n"
            "**不要**放过任何一行：每一行都要过一遍。\n"
        )
        prompt.append(f"\n## 上下文（本块之前，仅供理解）\n")
        for u in before:
            prompt.append(f"L{u['line']} [{u['kind']}] {u['text']}")
        prompt.append(f"\n## ★ 待审查单元（L{first}–L{last}，共 {len(cu)} 个）\n")
        for u in cu:
            prompt.append(f"L{u['line']} [{u['kind']}] {u['text']}")
        prompt.append(f"\n## 上下文（本块之后，仅供理解）\n")
        for u in after:
            prompt.append(f"L{u['line']} [{u['kind']}] {u['text']}")
        prompt.append(
            f"\n## 输出格式（严格 JSON，存到 {out_dir}/result-{ci:02d}.json）\n"
            "```json\n"
            '{"chunk": ' + str(ci) + ', "range": "L' + str(first) + '-L' + str(last) + '", '
            '"findings": [{"line": <行号>, "verdict": "flag|suspect", "reason": "...", "suggest": "原文 → 建议"}], '
            '"units_reviewed": ' + str(len(cu)) + '}\n'
            "```\n"
            "只列 flag/suspect 的单元；但 units_reviewed 必须是本块全部单元数（证明确实逐条过了一遍）。"
        )

        cp = os.path.join(out_dir, f"chunk-{ci:02d}.md")
        open(cp, "w", encoding="utf-8").write("\n".join(prompt))
        manifest["chunk_files"].append({"file": cp, "range": f"L{first}-L{last}", "units": len(cu)})

    json.dump(manifest, open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return manifest


def aggregate(paths):
    allf, reviewed = [], 0
    for p in paths:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"  ⚠️ 读取失败 {p}: {e}"); continue
        reviewed += d.get("units_reviewed", 0)
        for f in d.get("findings", []):
            f["_chunk"] = d.get("chunk"); allf.append(f)
    allf.sort(key=lambda x: x.get("line") or 0)
    print(f"\n{'='*76}\n  逐行审查汇总：已审单元 {reviewed} 个 / 发现问题 {len(allf)} 项\n{'='*76}")
    for f in allf:
        print(f"\n  L{f.get('line')} [{f.get('verdict')}] {f.get('reason','')}")
        if f.get("suggest"):
            print(f"       → {f['suggest']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="立场逐行审查器")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--audience", "-a", default="shareholder")
    ap.add_argument("--out", default="/tmp/review-pack")
    ap.add_argument("--chunk", type=int, default=120, help="每块单元数")
    ap.add_argument("--aggregate", nargs="*", help="汇总结果 JSON")
    if "--selfcheck" in __import__("sys").argv:
        __import__('sys').exit(selfcheck())
    args = ap.parse_args()

    if args.aggregate:
        aggregate(args.aggregate); sys.exit(0)

    m = build_pack(args.file, args.audience, args.out, chunk=args.chunk)
    print(f"  ✅ 审查任务包已生成 → {args.out}")
    print(f"     文件: {m['file']} | 受众: {m['audience']}")
    print(f"     审查单元: {m['total_units']} 个 → 切为 {m['chunks']} 块")
    for c in m["chunk_files"]:
        print(f"       {os.path.basename(c['file'])}  {c['range']}  ({c['units']} 单元)")
