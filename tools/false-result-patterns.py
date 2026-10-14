#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""false-result-patterns — 「结果看上去对而实为假」的【可跑检查器】。

★★★ 立据（2026-10-12 一晚，八次实证 · 见 v7 §0.2.1）：
  ★ 八次【全都不是「代码不跑」】，而是 **代码跑得好好的，在报一个假结果**：
    · D-204 恒真负例（`0 == 0`）        · D-217 判据时变
    · D-228 `p2.status`（正确 returncode）· D-231 同一错在本工具自身
    · D-234 并发伪失败                   · D-237 检测面窄
    · D-240 只读三清单中的两个           · D-241 用截短键查板
  ★★ 而八次里有**三次是本线自己的探针**（D-228/D-237/D-241）。

★★ 故本门把其中【可机械检】的五种做成检查：
  P1 **`subprocess` 结果取 `status`**（★ 应为 `returncode`）—— ★ D-228/D-231 的根因
  P2 **`None` 被当绿**（★ 判据里 `in (0, None)` / `!= None` 型放行）—— ★ D-231
  P3 **恒真负例**（★ 见 `selftest-audit`，本门只检 `status` 与 `None` 两类）
  P4 **`grep` 型判据用长串**（★ 检测面窄的常见形态）—— ★ D-237
  P5 **硬编码时间戳**（★ 负控会过期）—— ★ D-225
  P6 **长文档标题序号与【实际行号顺序】不一致**（★ 只在【同层级 + 同父节】内比对）—— ★ D-247/D-252/D-387

三态：扫描面为空 ⇒ 「不可判」；无命中 ⇒ PASS；有 ⇒ FAIL（★ 列文件与行）。

★★★ **本门的已知局限（★ 如实声明，★ 不加补丁掩盖）**：
  ★ **P1 的变量判定是【文件级】而非【逐处数据流】** ——
    ★ 若同一变量名在文件里**既是 `subprocess` 结果、又别处是 HTTP 响应**（★ 实测 `scripts/bb-copy.py` 的 `r`），
    ★★ 则本门会**误报**那些 HTTP 的 `.status`。
  ★★ 要修需**逐处数据流分析**（★ 大工程）⇒ **故本门报的 P1 命中【必须人工核】**，★ 命中 ≠ 缺陷。
  ★ **P5（硬编码时间）多数是数据/日志行而非判据** —— ★ 同样须人工筛。
  ★ **P6 的序号面**：★ 它**只认中文序号** `一、…十、`（★ `§1.2` 型阿拉伯编号【不在面内】）；
    ★★ 并**必须作用域感知** —— ★ 修前（D-387）它把 H1–H3 拍平成一个序列，
    ★★ 于是【凡每个父节各自重新编号的文档】一律误报：★ 实测全仓 **42 处命中 = 42 处假阳性 · 真缺陷 0**。
"""
import io
import os
import re
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    # \u2605\u2605\u2605 2026-10-13 \u4fee\uff08D-242\uff09\uff1a\u9996\u7248 `\b\w+\.status\b` **\u8fc7\u5bbd** \u2014\u2605
    #   \u5b9e\u6d4b\u547d\u4e2d **105 \u5904**\uff0c\u2605\u2605 \u800c\u591a\u6570\u662f `args.status` / \u677f\u7684 `status` \u7b49**\u522b\u7684\u5bf9\u8c61**\u3002
    #   \u2605 \u4fee\u6cd5\uff1a**\u9650\u5b9a\u4e3a\u3010\u540c\u4e00\u4f5c\u7528\u57df\u5185\u6709 `subprocess.\u2026(` \u7684\u53d8\u91cf\u3011**\u2014\u2605 \u5373\u53d8\u91cf\u540d\u5fc5\u987b\u5728\u6587\u4ef6\u91cc\u51fa\u73b0\u8fc7 `= subprocess.`\u3002
    ("P1", r'\.status\b',
     '\u2605 subprocess \u7ed3\u679c\u53d6 `.status`\uff08\u2605 \u5e94\u4e3a `.returncode`\uff09\u2014\u2605 D-228/D-231 \u6839\u56e0',
     # ★★ 2026-10-13 修（ext E-3A）：原 `(getattr\()?\w+\.status` —★
     #   ★★ 而 `getattr(p, "status")` 里【没有 `.status` 子串】（是 `, "status"`）
     #   ⇒ 那个分支【永远匹配不到真形态】（死分支）⇒ 意图与实现分叉。
     #   ★ 现补：真的 `getattr(x, "status")` / `getattr(x, 'status')` 形态。
     re.compile(r'\b\w+\.status\b(?!\s*=)|\bgetattr\s*\(\s*[^,)]+\s*,\s*["\']status["\']\s*\)')),
    # \u2605\u2605 2026-10-13 \u4fee\uff08ext E-2\uff09\uff1a\u539f\u6ce8\u6807\u542b `== None or` \u800c**\u7f16\u8bd1\u5f0f\u4e0d\u542b**
    #   \u21d2 \u2605\u2605 **\u58f0\u660e\u4e0e\u6267\u884c\u4e0d\u4e00\u81f4**\uff08\u2605 \u6b63\u662f\u672c\u4ed3\u8981\u6293\u7684\u90a3\u4e00\u65cf\uff09\u3002
    #   \u2605 \u73b0\u8865\u4e0a\uff1a`== None or` / `is None or` / **\u96c6\u5408\u5b57\u9762\u91cf `{0, None}`**\uff08\u2605 ext E-3 变\u4f53 B\uff09\u3002
    # ★★ 2026-10-13 修（ext F-6）：【声明串与编译式同步】—★ 原声明串含 == None or/is None or 而编译式不含（有意收窄）。
    ("P2", r'not\s+in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]|in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]',
     '\u2605 `None` \u88ab\u5f53\u7eff\uff08\u2605 \u5f02\u5e38\u8def\u5f84\u4e0e\u6210\u529f\u540c\u5f62\uff09\u2014\u2605 D-231',
     # \u2605\u2605 2026-10-13 \u518d\u4fee\uff08\u2605 \u672c\u7eb3\u81ea\u67e5\uff09\uff1a\u4e0a\u4e00\u7248\u8865\u4e86 `== None or` / `is None or`
     #   \u21d2 \u2605\u2605 **\u62a5\u4e86 33 \u5904\u5047\u9633\u6027**\uff08\u2605 \u5b9e\u4f8b `if gap is None or gap > 1:` \u2014\u2605
     #      \u2605 \u90a3\u662f\u3010\u6b63\u5e38\u7684\u7a7a\u503c\u68c0\u67e5\u3011\uff0c\u4e0d\u662f\u300cNone \u5f53\u7eff\u300d\uff09\u3002
     #   \u2605 \u53ea\u6709\u3010**\u628a None \u4e0e 0 \u653e\u8fdb\u540c\u4e00\u96c6\u5408**\u3011\u624d\u662f\u672c\u5f62\u6001\uff08\u2605 \u96c6\u5408\u6210\u5458\u5224\u65ad\uff09\u3002
     re.compile(r'not\s+in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]|in\s*[\(\{]\s*0\s*,\s*None\s*[\)\}]')),
    ("P4", r'grep.*\\u00a7|\u00a7',
     '\u2605 `grep` \u578b\u5224\u636e\u7528\u957f\u4e32\uff08\u2605 \u68c0\u6d4b\u9762\u7a84\uff09\u2014\u2605 D-237',
     re.compile(r"re\.search\(\s*[\"'][^\"']{18,}[\"']\s*,\s*\w+\.(?:stdout|body|stdout\s*or\s*[\"']{2})\s*\)")),
    ("P5", r'20\d\d-\d\d-\d\dT',
     '\u2605 \u786c\u7f16\u7801\u65f6\u95f4\u6233\uff08\u2605 \u8d1f\u63a7\u4f1a\u968f\u65f6\u95f4\u5931\u6548\uff09\u2014\u2605 D-225',
     # ★★ 2026-10-13 修（ext E-3C）：原只认 `T` 分隔；★ 现也认【空格分隔】。
     re.compile(r'["\']20\d\d-\d\d-\d\d[T ]\d\d:\d\d[^"\']*["\']')),
    # ★★ 2026-10-13（D-252）：【标题序号 ≠ 实际行号顺序】—★ 一晚犯两次（v7 §0.1.1 · 索引 §0七）
    ("P6", r'^## \u4e00\u3001|^## \u4e8c\u3001',
     '\u2605★ 长文档的【标题序号】与【实际行号顺序\u3011不一致（\u2605 插新节后未重排）—\u2605 D-247/D-252',
     None),   # ★ None = 特殊处理（★ 需跨行比对，★ 不是单行正则）
]

# ★ 中文序号表（★ D-252）
CN_NUM = "\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341"


def _strip_fenced(src):
    """★★ 把【围栏代码块】内的行挖空（★ 保留行号）—— ★ 里面的 `# ── 一、…` 是脚本注释，不是标题。

    ★ 立据（D-387）：★ `docs/v7-external-review-request-audit-20261013-ext.md` 的复跑段
      ★ 用 `# ── 一、核实「对的部分」 ──` 当 **bash 注释** ⇒ 原实现把它当 H1 标题 ⇒ 误报。
    """
    out, fence = [], None
    for line in src.split("\n"):
        m = re.match(r'^\s*(`{3,}|~{3,})', line)
        if m:
            ch = m.group(1)[0]
            if fence is None:
                fence = ch
            elif fence == ch:
                fence = None
            out.append("")
            continue
        out.append("" if fence else line)
    return out


def _heading_seq(src):
    """★ 取【带中文序号】的 H1–H3 标题，并算出它所属的【作用域】。

    ★★ 作用域 = **(标题层级, 父节行号链)** —— ★ 立据（D-387）：
      ★ 原实现把 H1–H3 **拍平成一个序列** ⇒ 凡「每个父节各自从『一、』重新编号」的文档
      ★★ **必然被判乱序 + 重复**（★ 实测全仓 42 处命中 **42 处全是这一形态** ⇒ 假阳性率 100%）。
      ★ 修法：★ 同层 + 同父链 才算同一序列；★ 更浅的新标题出现时，★ **更深层的序列自然另起**。
    """
    par = {1: (), 2: None, 3: None}
    seq = []
    for i, line in enumerate(_strip_fenced(src), 1):
        hm = re.match(r'^(#{1,3}) ', line)
        if not hm:
            continue
        lvl = len(hm.group(1))
        # ★ 先按【本标题出现之前】的父链定作用域（★ 不含自己）
        if lvl == 1:
            scope = (1, ())
        elif lvl == 2:
            scope = (2, (par[1],))
        else:
            scope = (3, (par[1], par[2]))
        # ★ 再更新父链
        if lvl == 1:
            par[1], par[2], par[3] = (i,), None, None
        elif lvl == 2:
            par[2] = i
        else:
            par[3] = i
        # ★★★ 2026-10-13 修（D-319）：`[^\u4e00-\u9fff]{0,8}?` 允许 `## ★★ 二、…`（★ 两个星）。
        m = re.match(r'^#{1,3} [^\u4e00-\u9fff]{0,8}?([\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]+)\u3001', line)
        if m and m.group(1) in CN_NUM:
            seq.append({"line": i, "ch": m.group(1), "idx": CN_NUM.index(m.group(1)),
                        "lvl": lvl, "scope": scope})
    return seq


def check_section_order(src):
    """★★ 检【标题里的中文序号】是否与【实际出现顺序】一致。

    ★ 立据（D-247/D-252）：本纳一晚犯两次 —
      ★ v7 正文：`§0.1.1` 被插在 `§0.2` 之后；★ 索引：`七` 被插在 `六` 之前。
    ★★ ⇒ **同一作用域内**标题序号只要不升序，就说明【插入时没重排】。

    ★★★ 2026-10-15 修（D-387）：★ 加【作用域感知】+ 【跳过围栏内标题】（★ 详见上面两个 helper）。
      ★★ 修前的读数：★ 全仓 **42 处命中**；★ 独立复算（`_heading_seq` 扁平化的对照实现）⇒
      ★★ **42 处 100% 是跨层级/跨父节的重启**，★ 同作用域真缺陷 **0**。
      ★★ ⇒ 故本判据此前【消费了错的量】（★ v7 §11「判据消费了错的量」同形）。

    ★★ 已知边界（★ 不掩盖）：★ 它**仍只认中文序号** `一、…十、` ——
      ★ `§1.2` / `1.2` 型阿拉伯编号 **不在本判据面内**（★ 那一类须另立判据，★ 不得读作「已检」）。
    """
    bad = []
    by_scope = {}
    for item in _heading_seq(src):
        by_scope.setdefault(item["scope"], []).append(item)
    for scope, items in by_scope.items():
        for k in range(1, len(items)):
            if items[k]["idx"] < items[k - 1]["idx"]:
                bad.append({"kind": "DESC", "line": items[k]["line"],
                            "cur": items[k]["ch"], "prev": items[k - 1]["ch"],
                            "snippet": "序号 '%s' 出在 '%s' 之后（★ 同层级同父节）"
                                       % (items[k]["ch"], items[k - 1]["ch"])})
        _seen = {}
        for it in items:
            if it["idx"] in _seen:
                bad.append({"kind": "DUP", "line": it["line"], "cur": it["ch"],
                            "prev": _seen[it["idx"]]["ch"],
                            "snippet": "重复序号 '%s'（★ 同一作用域内出现两次）" % it["ch"]})
            else:
                _seen[it["idx"]] = it
        _nums = sorted({i["idx"] for i in items})
        _jumped = [(_nums[k - 1], _nums[k]) for k in range(1, len(_nums))
                   if _nums[k] > _nums[k - 1] + 1]
        if _jumped:
            first = items[0]
            bad.append({"kind": "JUMP", "line": first["line"], "cur": "", "prev": "",
                        "snippet": "★ 作用域（L%d · 起于第 %d 行）缺序号：%s"
                                   % (first["lvl"], first["line"],
                                      " · ".join("%d→%d" % j for j in _jumped))})
    bad.sort(key=lambda d: d["line"])
    return bad


def strip_docstrings(src, keep_newlines=True):
    """★ 剥三引号块与注释（★ 免自伤，★ R006 惯例）。

    ★★★ 2026-10-13 修（D-243，★ **第十次同形**）：
      ★ 首版把剥离后的文本**压成一行** ⇒ 在它上数行号 ⇒
      ★★ **行号与原文件完全对不上**（★ 本纳取上下文时发现）。
      ★★☃ ⇒ ★ 修法：**剥离时保留换行符**（★ `keep_newlines=True`）⇒ 行号与原一致。
      ★ ★ 而这正印证本线纪律「**行号不是证据，行号在某时刻的内容才是**」。
    """
    out = []
    i, n = 0, len(src)
    dq = '"' * 3
    sq = "'" * 3
    while i < n:
        c = src[i]
        if c == "#":
            j = src.find("\n", i)
            if j < 0:
                i = n
            else:
                if keep_newlines:
                    out.append("\n")     # ★ 保留换行 ⇒ 行号不漂
                i = j + 1                  # ★★ 修：跳过那个 \n（★ 否则与上一行【重复计】）
            continue
        if src.startswith(dq, i) or src.startswith(sq, i):
            q = src[i:i + 3]
            j = src.find(q, i + 3)
            if j < 0:
                i = n
            else:
                seg = src[i:j + 3]
                if keep_newlines:
                    out.append("\n" * seg.count("\n"))   # ★ 保留行数
                i = j + 3
            continue
        out.append(c)
        i += 1
    return "".join(out)


def scan_file(path, rel):
    try:
        raw = io.open(path, encoding="utf-8").read()
    except Exception:
        return []
    code = strip_docstrings(raw)
    # ★★★ 数据流过滤（D-242 + D-243）：★ 只有【被 `= subprocess.…(` 赋值过的变量】才算候选。
    #   ★ 首版只判「文件里出现过 `= subprocess.`」⇒ **仍误报**：
    #     ★★ 实例 `scripts/bb-copy.py`：文件里有 subprocess，★ **而 `r` 在那里是【HTTP 响应对象】**（★ 有 `.status`）。
    #   ★★ 修法：**逐个变量名判** —★ 只要该名字在文件里【有一处非-subprocess 赋值】⇒ 不算候选。
    subproc_vars = set(re.findall(r'(\w+)\s*=\s*subprocess\.[a-z_]+\s*\(', code))
    all_assigned = set(re.findall(r'\b(\w+)\s*=\s*[^=\n]', code))
    http_vars = set()
    for nm in subproc_vars:
        # ★ 同一名字若还有其他赋值（如 `r = sess.get(…)`）⇒ 它不只是 subprocess
        others = re.findall(r'\b%s\s*=\s*([^=\n]+)' % re.escape(nm), code)
        if any('subprocess' not in o for o in others):
            http_vars.add(nm)
    hits = []
    for cid, _hint, why, rx in CHECKS:
        if rx is None:
            continue          # ★ P6 需跨行比对（★ 在 audit() 单独处理）
        for m in rx.finditer(code):
            if cid == "P5":
                # ★★★ 2026-10-13 修（D-330）：**看【是否与「当前时间」比较】，★ 而非看有没有日期**—★
                #   ★ 立据（★ 三类样本逐类核）：
                #     ★ ① 样本值（`sample = "2026-10-08T07:38:09"`）·
                #     ★ ② 政策起点常量（`TS_POLICY_SINCE = '2026-09-11T08:25:00+08:00'`）·
                #     ★ ③ **负控的输入样本**（`_ts_check('2099-01-01T00:00:00+08:00', None)  # 指向未来 ⇒ 必须不平`）
                #   ★★ 三类【全不是缺陷】—★ 而第③类**恰恰是负控本身**。
                #   ★ 真缺陷形态：**那个时间戳在判据里与「当前时间」比较**（★ 随时间漂移）。
                _ls5 = code.split(chr(10))
                _c5 = code[:m.start()].count(chr(10))
                _w5 = chr(10).join(_ls5[max(0, _c5 - 2):_c5 + 3])
                # ★ “与当前时间比较”的词
                if not re.search(r"(now\(\)|utcnow|datetime\.now|time\.time\(\)|monotonic|当前时间|现在)", _w5):
                    continue
            if cid == "P2":
                # ★★★ 2026-10-13 修（D-322）：**看【那个分支里做什么】，★ 而非看有没有 None**—★
                #   ★ 立据：实测那两处都是【正确的】—★
                #     ★ `if den in (0, None): return "分母为 0 ⇒ **不输出比率**"`；
                #     ★ `if rc_c not in (0, None) and not out: return "执行失败 ⇒ 载体状态未知"`。
                #   ★★ 故判据改为：★ 看该行【往后 4 行】内是不是★★ **返回「不可判 / 不输出 / 未知」**—★
                #     ★ 若是 ⇒ **正确的三态处理**，★ **不算命中**；
                #     ★ 若是返回「通过/OK/True」或直接继续算⇒ **算命中**。
                _ls2 = code.split(chr(10))
                _c2 = code[:m.start()].count(chr(10))
                _blk2 = chr(10).join(_ls2[_c2:_c2 + 5])
                # ★ 正确的三态处理词
                if re.search(r"(不可判|不输出|未知|未建立|拒绝|空≠无|unknown|undecidable|refuse|skip)", _blk2, re.I):
                    continue
                if re.search(r"(返回\s*True|return\s+True|通过|✅|OK)", _blk2):
                    pass          # ★ 算命中
                elif re.search(r"(不可判|不输出|未知|拒绝)", _blk2):
                    continue
                # ★ 否则也算命中（★ 保守：不明确就报）
            if cid == "P1":
                # ★★ 2026-10-13 修（ext E-3A 的真根因）：原只从 `\w+\.status` 取变量名
                #   ⇒ 而 **`getattr(p, "status")` 形态下 `m.group(0)` 里没有 `.status` 子串**
                #   ⇒ `re.match` 匹配不到 ⇒ var=None ⇒ continue ⇒ ★★ **该形态永远静默**。
                #   ★ 现两条路各取一次变量名。
                var = re.match(r'\w+\.status', m.group(0))
                if var:
                    _v = var.group(0)[:-len('.status')]
                else:
                    var = re.match(r'getattr\s*\(\s*([^,)]+)\s*,', m.group(0))
                    _v = var.group(1).strip() if var else None
                if not _v:
                    continue
                # ★★★ 2026-10-13 修（D-320）：**改【邻近行判定】，★ 而非文件级**—★
                #   ★实测：`bb-copy.py` 里 **别处**有 `r = subprocess.…`，
                #     ★ 而 `r.status` 在 `with urlopen(…) as r:` 处—★
                #     ★★ **同名变量被复用** ⇒ 文件级必然误报（★ P1 十处全假）。
                #   ★ 新判据：**往上 40 行内找 `as <var>` 或 `<var> = subprocess`**，
                #     ★ 若那里是 `urlopen`/`http`/`url` 则**不算**。
                _lo = max(0, code[:m.start()].count(chr(10)) - 40)
                _win = chr(10).join(code.split(chr(10))[_lo:code[:m.start()].count(chr(10)) + 1])
                # ★★★ 2026-10-13 再修（D-320）：**取【最近的一次声明】，★ 而非窗口内任一**—★
                #   ★ 实测：`bb-upgrade.py` 窗口内**同时**有
                #     ★ `r = subprocess.run(...)`（★ 第 86 行）与 `with urlopen(...) as r:`（★ 第 94 行），
                #     ★★ 而 `r.status` 在【 95 行】⇒ **取最近的那个才对**。
                _ls = code.split(chr(10))
                _cur = code[:m.start()].count(chr(10))
                _decl = None
                for _k in range(_cur, max(-1, _cur - 40), -1):
                    _ln = _ls[_k] if 0 <= _k < len(_ls) else ""
                    if re.search(r"\bas\s+%s\b" % re.escape(_v), _ln) and re.search(r"(urlopen|urllib|requests\.|http)", _ln):
                        _decl = "http"; break
                    if re.search(r"\b%s\s*=\s*subprocess" % re.escape(_v), _ln):
                        _decl = "subprocess"; break
                if _decl == "http":
                    continue          # ★ 最近声明是 urlopen ⇒ `.status` 是对的
                if _v not in subproc_vars or _v in http_vars:
                    continue      # ★ 不是纯粹 subprocess 结果 ⇒ 不算
            # ★ \u53d6\u884c\u53f7
            ln = code[:m.start()].count("\n") + 1
            # ★ \u6392\u9664\u5de5\u5177\u81ea\u8eab\uff08\u2605 \u5b83\u7684\u6837\u672c\u5b57\u7b26\u4e32\u4f1a\u547d\u4e2d\uff09
            if rel.endswith("false-result-patterns.py"):
                continue
            hits.append({"check": cid, "file": rel, "line": ln,
                         "snippet": m.group(0)[:60], "why": why})
    return hits


def discover(roots):
    out = []
    for d in roots:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x != "node_modules" and not x.startswith(".")]
            for fn in filenames:
                if fn.endswith(".py"):
                    out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(out)


def discover_md(roots):
    """★ 枚举 .md 文件（★ 原 `discover()` 只收 `.py` ⇒ **md 面永远数不到**）。

    ★★★ 立据（D-387）：★ `main()` 原写 `files = discover(py_roots) + [p for p in
      discover(md_roots) if p.endswith(".md")]` —— ★★ 而 `discover()` 里 `if fn.endswith(".py")`
      ⇒ 后半段**恒为空** ⇒ ★ 打印的「扫描面 N 个 .py」**从不含 md**，
      ★★ 且 `if not files` 的【不可判】分支只看 py 面 ⇒ ★ **只有 .md 的根会被误报「扫描面为空」**。
    """
    out = []
    for d in roots:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith(".")]
            for fn in filenames:
                if fn.endswith(".md"):
                    out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT))
    return sorted(out)



def audit_md(roots):
    """★★ 对 .md 跑 P6（标题序号核对）—★ D-252。"""
    hits = []
    for d in roots:
        base = os.path.join(ROOT, d)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith(".")]
            for fn in sorted(filenames):
                if not fn.endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                try:
                    src = io.open(os.path.join(ROOT, rel), encoding="utf-8").read()
                except Exception:
                    continue
                for d in check_section_order(src):
                    hits.append({"check": "P6", "file": rel, "line": d["line"],
                                 "snippet": d["snippet"], "kind": d["kind"],
                                 "why": "★★ 长文档标题序号不升序（★ 插新节后未重排；★ 只在【同层级 + 同父节】内比对）"})
    return hits


def audit(roots):
    hits = []
    for rel in discover(roots):
        hits += scan_file(os.path.join(ROOT, rel), rel)
    return hits


def selftest():
    ok = tot = 0
    # ★ 正控：`.status` 型须命中
    tot += 1
    if scan_file_text('r = subprocess.run([...])\nrc = r.status\n'):
        ok += 1
        print("  ✅ 正控：`r.status` 命中（★ D-228/D-231 的根因）")
    else:
        print("  ❌ 正控：`r.status` 未命中")
    # ★ 负控：`.returncode` 不得命中
    tot += 1
    if not scan_file_text('rc = r.returncode\n'):
        ok += 1
        print("  ✅ 负控：`r.returncode` 不命中（★ 防过宽）")
    else:
        print("  ❌ 负控：`r.returncode` 被误伤")
    # ★ 正控：`None` 当绿须命中
    tot += 1
    if scan_file_text('bad = [r for r in rows if r.get("rc") not in (0, None)]\n'):
        ok += 1
        print("  ✅ 正控：`not in (0, None)` 命中（★ D-231）")
    else:
        print("  ❌ 正控：`not in (0, None)` 未命中")
    # ★ 正控：硬编码时间戳须命中
    tot += 1
    if scan_file_text('_fixture(updated_at="2026-10-11T00:20:00+08:00")\n'):
        ok += 1
        print("  ✅ 正控：硬编码时间戳命中（★ D-225）")
    else:
        print("  ❌ 正控：硬编码时间戳未命中")
    # ★ 负控：注释里的不得命中（★ 前剥离有效）
    tot += 1
    if not scan_file_text('# rc = r.status\n'):
        ok += 1
        print("  ✅ 负控：注释里的 `.status` 不命中（★ 已前剥离）")
    else:
        print("  ❌ 负控：注释未前剥离 ⇒ 自伤")
    # ★★ 正控（D-252）：序号乱序必命中
    tot += 1
    if check_section_order("## \u4e00\u3001A\n## \u4e09\u3001C\n## \u4e8c\u3001B\n"):
        ok += 1
        print("  \u2705 \u6b63\u63a7\uff1a\u5e8f\u53f7\u4e71\u5e8f\uff08\u4e00\u2192\u4e09\u2192\u4e8c\uff09\u547d\u4e2d\uff08\u2605 D-252\uff09")
    else:
        print("  \u274c \u6b63\u63a7\uff1a\u5e8f\u53f7\u4e71\u5e8f\u672a\u547d\u4e2d")
    # ★ 负控：正序\u4e0d\u5f97\u547d\u4e2d
    tot += 1
    if not check_section_order("## \u4e00\u3001A\n## \u4e8c\u3001B\n## \u4e09\u3001C\n"):
        ok += 1
        print("  \u2705 \u8d1f\u63a7\uff1a\u6b63\u5e8f\uff08\u4e00\u2192\u4e8c\u2192\u4e09\uff09\u4e0d\u547d\u4e2d\uff08\u2605 \u9632\u8fc7\u5bbd\uff09")
    else:
        print("  \u274c \u8d1f\u63a7\uff1a\u6b63\u5e8f\u88ab\u8bef\u4f24")
    # ★ 安全：无序号\u4e0d\u5f97\u62a5错
    tot += 1
    if check_section_order("## \u4e00\u3001A\n## \u4e8c\u3001B\n## \u4e8c\u3001C\n"):
        ok += 1
        print("  \u2705 \u6b63\u63a7\uff1a\u91cd\u590d\u5e8f\u53f7\uff08\u4e24\u4e2a\u300c\u4e8c\u300d\uff09\u547d\u4e2d\uff08\u2605 D-262\uff09")
    else:
        print("  \u274c \u6b63\u63a7\uff1a\u91cd\u590d\u5e8f\u53f7\u672a\u547d\u4e2d")
    tot += 1
    if not check_section_order("# A\n## B\n### C\n"):
        ok += 1
        print("  \u2705 \u5b89\u5168\uff1a\u65e0\u5e8f\u53f7\u6807\u9898\u4e0d\u62a5\u9519")
    else:
        print("  \u274c \u5b89\u5168\uff1a\u65e0\u5e8f\u53f7\u88ab\u8bef\u62a5")

    # ★★★ 2026-10-15 补（D-387）：【作用域感知】的双向控制 ——
    #   ★ 立据：修前全仓 42 处 P6 命中【全是跨作用域重启】，同作用域真缺陷 0
    #     ⇒ ★ 判据【消费了错的量】（★ v7 §11 同形）。
    #   ★★ 故【两向都测】：★ 真形态仍须红（正控）· ★ 重启形态不得红（负控）。
    _c387 = [
        ("正控", "跳号（一→二→四）必命中",
         "## 一、A\n## 二、B\n## 四、D\n", True),
        ("正控", "同父同级内真乱序（二→一）必命中",
         "## 一、A\n### 二、x\n### 一、y\n", True),
        ("负控", "跨父节各自从『一、』重新编号不得命中",
         "## 一、A\n### 一、a\n### 二、b\n## 二、B\n### 一、c\n### 二、d\n", False),
        ("负控", "父级之后子级重新起『一』不得命中",
         "## 二、A\n### 一、a\n### 二、b\n", False),
        ("负控", "围栏内的『## 九、』不得命中（★ 那是代码不是标题）",
         "## 一、A\n```bash\n## 九、cmd\n```\n## 二、B\n", False),
    ]
    for _k, _name, _src, _want in _c387:
        tot += 1
        _got = bool(check_section_order(_src))
        if _got == _want:
            ok += 1
            print("  \u2705 %s：%s（★ D-387）" % (_k, _name))
        else:
            print("  \u274c %s：%s（★ 实际 %s）" % (_k, _name, _got))


    # ★ 三态：不存在的根 ⇒ 空
    tot += 1
    if discover(["/tmp/__no_such_root__"]) == []:
        ok += 1
        print("  ✅ 正控：不存在的根 ⇒ 空列表（★ 调用方报「不可判」）")
    else:
        print("  ❌ 正控：不存在的根竟有结果")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def scan_file_text(src):
    """★ 供自证用：直接扫一段源码文本。"""
    code = strip_docstrings(src)
    return [1 for _c, _h, _w, rx in CHECKS if rx is not None and rx.search(code)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("false-result-patterns 1.0.0")
        return 0
    if a.selftest:
        return selftest()
    roots = a.root or ["tools", "scripts", "docs"]
    # ★★ 2026-10-13 修（D-259）：原写 `[r for r in roots if r != "docs"] or ["docs"]`
    #   ⇒ 左边非空（tools/scripts）⇒ **`or` 永不生效** ⇒ `audit_md` 扫错面 ⇒ **P6 永远 0 命中**。
    #   ★ 修法：py 面与 md 面分别定。
    py_roots = [r for r in roots if r != "docs"] or ["tools", "scripts"]
    md_roots = [r for r in roots] if a.root else ["docs"]
    hits = audit(py_roots) + audit_md(md_roots)
    py_files, md_files = discover(py_roots), discover_md(md_roots)
    files = py_files + md_files
    if a.json:
        print(json.dumps({"scanned": len(files), "hits": hits}, ensure_ascii=False, indent=1))
        return 0
    print("== false-result-patterns 1.0.0 ==")
    if not files:
        print("  ★ 扫描面为空 ⇒ 【不可判】（★ 未抽到 ≠ 不存在）")
        return 2
    _npy = len([x for x in files if x.endswith(".py")])
    _nmd = len([x for x in files if x.endswith(".md")])
    print("  扫描面：%d 个文件（★ %d .py + %d .md）"
          % (len(files), len(py_files), len(md_files)))
    from collections import Counter
    by = Counter(h["check"] for h in hits)
    print("  命中：%d（★ 按类：%s）" % (len(hits), dict(by)))
    print()
    for cid, _hint, why, _rx in CHECKS:
        sub = [h for h in hits if h["check"] == cid]
        if not sub:
            continue
        print("  ★ %s %s" % (cid, why))
        for h in sub[:6]:
            print("      %s:%s  `%s`" % (h["file"], h["line"], h["snippet"]))
        if len(sub) > 6:
            print("      … 另有 %d 处" % (len(sub) - 6))
        print()
    if hits:
        print("  ❌ %d 处命中 ⇒ ★ **每处须人工核**（★ 命中 ≠ 缺陷，★ 见 v7 §0.2.1）" % len(hits))
        print("     ★★ 本门已知局限：P1 变量判定是【文件级】非逐处 · P5 多数是数据行 ⇒ **必人工筛**")
        return 1
    print("  ✅ 未命中五类假结果形态")
    return 0


if __name__ == "__main__":
    sys.exit(main())
