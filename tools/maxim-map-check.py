#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""maxim-map-check.py — 「**纪律 → 仪器**」映射表的可核性判据（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

★ 立据（短判决位 2026-10-10 收工判决，逐字要点）：
  「台账 = **把原则从「记性」搬到「映射表」，每条挂仪器入口** ⇒ **这是那个缺口的结构性解**……
    与我判的「缺的不是又一条原则，是一个**模具**」是**同一个答案的两面：模具管新件出生，台账管旧原则不丢**。」
  ⇒ **本件就是让这张映射表不再只是"写在那儿"，而是"可被机器核"**：
    每条纪律末尾的「（对应：…）」里引用的**工具**必须存在、**卡片**必须 HTTP 200；引不到的 ⇒ 红。

★ 判据形态（**执行，不是抄写**）：
  · 工具引用（`xxx.py` / 裸名）⇒ 断言 `tools/<name>` **文件存在**
  · 卡片引用（`notes/mac-mini/<key>`）⇒ 断言黑板 GET **HTTP 200**（双板任一可达即可；两块都不可达 ⇒ **不可判**，不是红）
  · 每条纪律必须**至少有一个**可解析的引用 ⇒ 否则红（"纪律没有仪器"＝口号）

★ 观测面（六要素）：
  · 含项 = `docs/context-survival-tracker.md` 里带「（对应：…）」的纪律行；**排除项** = ① 未带引用括号的行
    （不是本判据的对象）② 引用里非工具非卡片的自由文本 ③ 卡片的**内容正确性**（本件只核"可读到"）
    ④ 仪器的**判据是否有效**（那是各件自己的 selftest 的活）；**补偿控制** = ① 引用解析失败即红（fail-closed）
    ② 黑板两板都不可达 ⇒ 记「不可判」而非绿 ③ 每条纪律至少一个引用 ④ 打印每轮扫描面与运行戳；
  · 工具 = python3（解析 + curl）· 单位 = 条 · 时刻 = RFC3339。
  ★ **「只读」的准确含义**（判决补充实测：mtime 真的变了）：本件**不改被核对象**（不写 tracker、不写任何 `tools/*.py`），
    但会**执行索引里各仪的 `--selftest`** ⇒ 那些自检会在 **`guard/mutation-work/` 下创建/删除临时目录**
    ⇒ **该目录 mtime 会变**（实测只有它变）。⇒ 本件的写面 = **仅 `guard/mutation-work/`**，其余只读。

退出码：0 = 通过（全部引用可解析且可达） · 1 = 有悬空引用 · 2 = 用法错误
用法：python3 tools/maxim-map-check.py [--tracker <path>] | --selftest
"""
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.expanduser("~/dsh-collab")
TRACKER = os.path.join(HERE, "docs/context-survival-tracker.md")
BOARDS = ["http://127.0.0.1:8792", "http://106.53.214.108:8792"]
REF_BLOCK = re.compile(r"（对应：([^）]*)）")
INDEX_MARK = "★ 仪器索引"
INDEX_LINE = re.compile(r"^\s*-\s*(\d+)\s*⇒\s*(.+)$")
# ★ 判决 2026-10-10 抓到：**延续行**（`（对应：…）` 常有前导 `tools/`）会让工具名解析失败 ⇒ 误判「口号」。
#   ⇒ 允许可选 `tools/` 前缀（并放宽前导字符集）。
TOOL_TOKEN = re.compile(r"(?:^|[\s`（(])(?:tools/)?([A-Za-z0-9][A-Za-z0-9._-]*\.py)")
CARD_TOKEN = re.compile(r"(notes/[a-z0-9-]+/[A-Za-z0-9._-]+|data/[a-z0-9-]+/[A-Za-z0-9._-]+)")


def ts():
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


def http_ok(key):
    """三态：True=可达 · False=404 · None=两块都不可达（不可判）。"""
    unreachable = 0
    for base in BOARDS:
        try:
            r = subprocess.run(["curl", "-s", "-m", "6", "-o", "/dev/null", "-w", "%{http_code}",
                                f"{base}/{key}"], capture_output=True, text=True, timeout=12)
            code = (r.stdout or "").strip()
            if code == "200":
                return True
            if code == "404":
                return False
        except Exception:
            pass
        unreachable += 1
    return None if unreachable == len(BOARDS) else False


_SELFTEST_CACHE = {}


def tool_selftest_ok(abs_path):
    """索引里的工具**必须能过自己的自检**（若它支持 `--selftest`）⇒ 返回 (ok, 说明)。

    ★ 判决未声明④：把纪律 5 的仪器换成**真实但不相干**的件，判据仍报全覆盖 ⇒ **映射正确性在面外**。
      ⇒ 本函数只补**能做的那半**：**引用必须指向一个"自己能跑通"的仪器**（不能让坏件冒充仪器）；
      而"配对是否恰当"仍**不在面内**（见输出里的排除项声明），由**声明层复审**与人工裁决负责。
    """
    if abs_path in _SELFTEST_CACHE:
        return _SELFTEST_CACHE[abs_path]
    try:
        src = open(abs_path, encoding="utf-8", errors="replace").read()
    except Exception as e:
        _SELFTEST_CACHE[abs_path] = (False, f"读不到（{e.__class__.__name__}）")
        return _SELFTEST_CACHE[abs_path]
    if "--selftest" not in src:
        # ★★ 判决补充复现的洞：原实现把「无自检」记 **True（绿）** ⇒「**无自检＝通过**」——
        #   这正是本线反复判的 `absent ≠ pass`。⇒ 现改**三态**：通过 / 失败（红）/ **未核（既非通过也非失败）**。
        _SELFTEST_CACHE[abs_path] = (None, "该件**无 `--selftest`** ⇒ **未核**（既不算通过也不算失败）")
        return _SELFTEST_CACHE[abs_path]
    try:
        r = subprocess.run([sys.executable, abs_path, "--selftest"], cwd=HERE,
                           capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0 and "Traceback" not in ((r.stdout or "") + (r.stderr or ""))
        _SELFTEST_CACHE[abs_path] = (ok, f"`--selftest` exit={r.returncode}")
    except Exception as e:
        _SELFTEST_CACHE[abs_path] = (False, f"自检无法执行（{e.__class__.__name__}）")
    return _SELFTEST_CACHE[abs_path]


def scan(path):
    """返回 (纪律条, 悬空引用, 不可判引用, 无引用的纪律条)。"""
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    rules, dangling, unknown, no_ref = [], [], [], []
    selftest_notes = []          # ★ 必须在**索引校验之前**初始化（实测：放在后面 ⇒ UnboundLocalError）
    instrument_notes = []        # ★ 仪器准入（H1+H2）记录
    _per_rule = {}               # 每条纪律的仪器状态：pass / fail / unknown
    # ★ 机读仪器索引块：`- N ⇒ tools/x.py, tools/y.py` ⇒ 每条纪律的**可核**映射
    in_index, index = False, {}
    for i, ln in enumerate(lines, 1):
        if INDEX_MARK in ln:
            in_index = True
            continue
        if in_index:
            if ln.strip() == "" and index:
                in_index = False
                continue
            mm = INDEX_LINE.match(ln)
            if mm:
                index[int(mm.group(1))] = [t.strip() for t in re.split(r"[,\s]+", mm.group(2)) if t.strip()]
    for n, files in index.items():
        for f in files:
            ap = os.path.join(HERE, f)
            if not os.path.isfile(ap):
                dangling.append(f"{path}:仪器索引 纪律 {n} ⇒ 文件 `{f}` **不存在**")
                continue
            # ★ 未声明④的补强：仪器必须**自己能跑通**（不能让坏件冒充仪器）
            # ★★ 判决的观察机械化（2026-10-10）：「三件仪器都是今晚被它打过的」⇒
            #   **被引用的仪器必须自带 H1（有 --selftest）+ H2（正控与反控双向）** ——
            #   只有正控的仪器只能证明"没睡着"，证明不了"会醒"；没有它，映射表就成了引用名头。
            try:
                _tsrc = open(ap, encoding="utf-8", errors="replace").read()
            except Exception:
                _tsrc = ""
            _has_selftest = ("--selftest" in _tsrc)
            _has_pos = any(w in _tsrc for w in ("应红", "该红", "必红", "正控"))
            _has_neg = any(w in _tsrc for w in ("应绿", "反控", "该绿", "非红"))
            if not (_has_selftest and _has_pos and _has_neg):
                dangling.append(
                    f"仪器索引 纪律 {n} ⇒ `{f}` **不满足仪器准入**（H1 有自证={_has_selftest} · "
                    f"H2 双向：正控={_has_pos} 反控={_has_neg}）⇒ **没红的仪器不配当落脚**")
            else:
                instrument_notes.append(f"{f}: H1+H2 ✓")
            ok_s, why_s = tool_selftest_ok(ap)
            if ok_s is False:
                dangling.append(f"{path}:仪器索引 纪律 {n} ⇒ `{f}` **过不了自己的自检**（{why_s}）⇒ 不能当仪器")
                _per_rule.setdefault(n, []).append(("fail", f))
            elif ok_s is None:
                _per_rule.setdefault(n, []).append(("unknown", f))
            else:
                _per_rule.setdefault(n, []).append(("pass", f))
            _note = f"{f}: {why_s}"
            if _note not in selftest_notes:
                selftest_notes.append(_note)
    NUM = re.compile(r"^\s*(\d+)\.\s")
    covered = set()
    _last_num, _last_num_line = None, -99        # ★ 延续行归属：最近一条编号纪律
    for i, ln in enumerate(lines, 1):
        m = REF_BLOCK.search(ln)
        if not m:
            continue
        num = NUM.match(ln)
        if num:
            _last_num, _last_num_line = int(num.group(1)), i
        elif _last_num is None or (i - _last_num_line) > 8:
            # ★ 散文里的 `（对应：…）`（例：说明"本文件用 `（对应：…）` 指向仪器"的那段）⇒ **不是纪律**，跳过
            continue
        num = num if num else re.match(r"^(\d+)\.", f"{_last_num}.")   # 归到最近一条编号纪律
        head = ln.strip()[:60]
        rules.append((i, head))          # ★ 先计入纪律条数（有索引也算）
        if num:
            covered.add(int(num.group(1)))
        if num and int(num.group(1)) in index:
            continue                       # 本条的**机读映射**已在仪器索引里 ⇒ prose 不必再解析
        body = m.group(1)
        tools = {t for t in TOOL_TOKEN.findall(body)}
        cards = {c for c in CARD_TOKEN.findall(body)}
        if not tools and not cards:
            no_ref.append((i, head))
            continue
        for t in tools:
            if not os.path.isfile(os.path.join(HERE, "tools", t)):
                dangling.append(f"{path}:{i} ⇒ 工具 `{t}` **不存在**（纪律引用了空气）")
        for c in cards:
            ok = http_ok(c)
            if ok is False:
                dangling.append(f"{path}:{i} ⇒ 卡片 `{c}` **HTTP 404**（指向不存在的落盘物）")
            elif ok is None:
                unknown.append(f"{path}:{i} ⇒ 卡片 `{c}` **两板都不可达 ⇒ 不可判**（不是绿）")
    # ★★ 覆盖率对账（实测教训：只覆盖 6/10 却报"全绿" ⇒ **部分覆盖不得读成全部**）
    all_nums = set()
    for ln in lines:
        mm = re.match(r"^\s*(\d+)\.\s*\*\*", ln)     # 纪律条目 = 编号 + 粗体标题
        if mm:
            all_nums.add(int(mm.group(1)))
    covered |= set(index.keys())
    if instrument_notes:
        print(f"  · **仪器准入（H1 自证 + H2 双向）**：{len(instrument_notes)} 件通过"
              f"（{', '.join(sorted({x.split(':')[0] for x in instrument_notes}))[:90]}…）")
    for n, st in sorted(_per_rule.items()):
        if st and all(k == "unknown" for k, _ in st):
            dangling.append(f"仪器索引 纪律 {n} ⇒ 其仪器**全部无可执行自检**（{'、'.join(f for _, f in st)}）"
                            f"⇒ 该条映射**不可核**（『无自检』不是通过）⇒ 请换可自检的仪器或写明豁免理由")
    uncovered = sorted(all_nums - covered)
    coverage = {"total": len(all_nums), "covered": len(all_nums & covered), "uncovered": uncovered}
    return rules, dangling, unknown, no_ref, coverage, selftest_notes, _per_rule


def main():
    path = TRACKER
    if "--tracker" in sys.argv:
        i = sys.argv.index("--tracker")
        if i + 1 < len(sys.argv):
            path = os.path.expanduser(sys.argv[i + 1])
    RUN = ts()
    if not os.path.isfile(path):
        print(f"用法错误/环境错误：找不到 {path}")
        return 2
    # ★ 判决③：运行时标题**不得**自称「只读」—— 本件会执行各仪的 `--selftest`，
    #   那些自检在 `guard/mutation-work/` 建临时目录 ⇒ **有写面**。标题必须与事实一致。
    print("maxim-map-check · 「纪律 → 仪器」映射可核性（**不改被核对象**；唯一写面 = `guard/mutation-work/`）")
    print(f"  · 本次运行戳 run={RUN} —— ★ 引用本页数字须连同它一起引用")
    print(f"  观测面（六要素）：**含项** = {os.path.relpath(path, HERE)} 里带「（对应：…）」的纪律行；"
          f"**排除项** = ① 不带引用括号的行 ② 引用里的自由文本 ③ 卡片的**内容正确性**（只核可读到）、以及 ★**映射正确性**（「这条纪律配这个仪器」是否恰当 —— 本件只核引用**可解析且可达**，**配对恰当性由声明层复审与人工裁决负责**，实测：把某条纪律的仪器换成真实但不相干的件，本件**不报**）"
          f"④ 仪器判据本身是否有效（各件 selftest 的活）；**补偿控制** = ① 解析失败即红（fail-closed）"
          f"② 两板都不可达 ⇒ 记「不可判」而非绿 ③ 每条纪律至少一个引用 ④ 打印扫描面与运行戳；"
          f"**工具** = python3 + curl（**不改被核对象**；写面见下）；**单位** = 条；**时刻** = {RUN}")
    rules, dangling, unknown, no_ref, cov, selftest_notes, per_rule = scan(path)
    print(f"  · 扫描面：**纪律行 {len(rules)} 行**（含延续行；**单位=行**）· "
          f"**纪律条 {len(cov['total']) if isinstance(cov.get('total'), (list, set)) else cov['total']} 条**（**单位=编号去重**）· "
          f"**覆盖率对账**：纪律共 **{cov['total']}** 条 ⇒ 有可核映射 **{cov['covered']}** 条"
          + (f" ⇒ ★ **未覆盖差集 {cov['uncovered']}**（＝口号，须补映射）" if cov["uncovered"] else " ⇒ 全覆盖"))
    if cov["uncovered"]:
        dangling.append(f"纪律 {cov['uncovered']} **没有任何可核映射**（既无（对应：）也无仪器索引）⇒ 口号")
    if cov["total"] == 0:
        print("\n❌ **解析到 0 条纪律 ⇒ 空集不是通过**（解析失效 / 块被删 / 路径给错）")
        return 1
    if len(rules) == 0:
        print("\n❌ **解析到 0 条纪律 ⇒ 空集不是通过**（可能是解析失效 / 纪律块被删 / 路径给错）"
              "—— ★ 这正是判决早先教的：**「0 件」不得读成「干净」**")
        return 1
    if no_ref:
        for i, head in no_ref:
            dangling.append(f"{path}:{i} ⇒ **纪律没有任何可解析的仪器引用**（＝口号）：{head}")
    if unknown:
        print(f"  · 不可判（两板不可达，**不当作绿**）：{len(unknown)} 处")
        for u in unknown[:3]:
            print("    " + u)
    if selftest_notes:
        _seen = {}
        for st in per_rule.values():
            for k, f in st:
                _seen[f] = k          # 同一件被多条纪律引用 ⇒ 只数一次（判决：别把对数当件数）
        n_pass = sum(1 for k in _seen.values() if k == "pass")
        n_unk = sum(1 for k in _seen.values() if k == "unknown")
        n_fail = sum(1 for k in _seen.values() if k == "fail")
        print(f"  · 索引仪器自检：**通过 {n_pass}** · **未核 {n_unk}** · 失败 {n_fail}"
              f"（共 {len(selftest_notes)} 条去重记录；★ 三态分开数，**未核不得读成通过**）")
        shown = selftest_notes if len(selftest_notes) <= 8 else selftest_notes[:8]
        for x in shown:
            print(f"    - {x}")
        if len(selftest_notes) > len(shown):
            print(f"    … **已截断：另有 {len(selftest_notes) - len(shown)} 条未印出**（判决补充：截断必须标注）")
    if dangling:
        print(f"\n❌ [run {RUN}] 悬空引用 {len(dangling)} 处：")
        for d in dangling:
            print("  " + d)
        return 1
    print(f"\n✅ [run {RUN}] 通过：纪律 **{cov['total']}** 条**全覆盖**（可核映射 {cov['covered']} 条；"
          f"其中散文里带「（对应：）」的 {len(rules)} 条）· 悬空 **0** · 不可判 **{len(unknown)}**")
    return 0


def selftest():
    """双向：正控（引用不存在的工具 ⇒ 必红）+ 反控（引用真实工具/卡片 ⇒ 绿）。"""
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="maxim-map-check-selftest-", dir=work)
    bad = []
    try:
        p = os.path.join(sb, "t.md")
        # 反控：引用真实工具 + 真实卡片
        open(p, "w", encoding="utf-8").write(
            "1. **真实项** ←→ 有形式。（对应：`gate-scaffold.py` · notes/mac-mini/k6-handover-onepager）\n")
        _, d1, _, n1, _, _, _ = scan(p)
        ok_green = (len(d1) == 0) and (len(n1) == 0)
        print(f"  {'✅' if ok_green else '❌'} 反控：引用真实工具+真实卡片 ⇒ 绿（悬空 {len(d1)} · 不可判 {len(n1)}）")
        if not ok_green:
            bad.append("反控未绿")
        # 正控：引用不存在的工具
        open(p, "w", encoding="utf-8").write("2. **悬空项** ←→ 有形式。（对应：`no-such-tool-xyz.py`）\n")
        _, d2, _, _, _, _, _ = scan(p)
        ok_red = len(d2) == 1
        print(f"  {'✅' if ok_red else '❌'} 正控：引用不存在的工具 ⇒ 红（悬空 {len(d2)}）")
        if not ok_red:
            bad.append("正控未红")
        # 正控②：纪律没有任何引用 ⇒ 红（口号）
        open(p, "w", encoding="utf-8").write("3. **光有口号** ←→ 没有仪器。（对应：无）\n")
        _, d3, _, n3, _, _, _ = scan(p)
        ok_no_ref = (len(n3) == 1) and (len(d3) == 0)   # scan 把"无引用"单列；main 才转成悬空
        print(f"  {'✅' if ok_no_ref else '❌'} 正控：纪律**无仪器引用** ⇒ 红（悬空 {len(d3)} · 无引用 {len(n3)}）")
        if not ok_no_ref:
            bad.append("无引用未红")
        # 反控②：卡片 404 ⇒ 红（指向不存在的落盘物）
        open(p, "w", encoding="utf-8").write("4. **悬空卡** ←→ 有形式。（对应：notes/mac-mini/definitely-not-a-real-card-xyz）\n")
        _, d4, n4, _, _, _, _ = scan(p)
        ok_404 = (len(d4) == 1) or (len(n4) == 1)
        print(f"  {'✅' if ok_404 else '❌'} 反控/正控：卡片不可达 ⇒ 红或不可判（悬空 {len(d4)} · 不可判 {len(n4)}）")
        if not ok_404:
            bad.append("悬空卡未红/未不可判")
        # ★ 未声明④的补强控制：一个**自检必失败**的临时件 ⇒ 不得被当仪器
        badtool = os.path.join(sb, "bad_tool.py")
        open(badtool, "w", encoding="utf-8").write(
            'import sys\nif "--selftest" in sys.argv:\n    print("boom"); sys.exit(1)\n')
        ok_s, why_s = tool_selftest_ok(badtool)
        print(f"  {'✅' if not ok_s else '❌'} 反控：**过不了自检的件不得当仪器**（{why_s}）")
        if ok_s:
            bad.append("坏仪器未被拒")
        goodtool = os.path.join(sb, "good_tool.py")
        open(goodtool, "w", encoding="utf-8").write(
            'import sys\nif "--selftest" in sys.argv:\n    print("ok"); sys.exit(0)\n')
        ok_s2, _ = tool_selftest_ok(goodtool)
        print(f"  {'✅' if ok_s2 else '❌'} 反控：`--selftest` 通过的件可当仪器")
        if not ok_s2:
            bad.append("好仪器被拒")
        # ★★ 判决新缺口：**三态分支未被自证覆盖** ⇒ 补一条：某条纪律的仪器**无 `--selftest`** ⇒
        #   `scan()` 必须给出「不可核」的悬空项（用**已存在的**无自检真件做夹具，不新建文件、不污染 tools/）。
        open(p, "w", encoding="utf-8").write(
            "1. **三态分支夹具** ←→ 形式。（对应：`build-state-registry.py`）\n"
            "\n### ★ 仪器索引\n- 1 ⇒ tools/build-state-registry.py\n")
        _, d5, _, n5, _, _, _ = scan(p)
        ok_tri = any("不可核" in x for x in d5)
        print(f"  {'✅' if ok_tri else '❌'} 正控：仪器**无自检** ⇒ 必须判「不可核」（悬空 {len(d5)}）")
        if not ok_tri:
            bad.append("三态分支未被覆盖（无自检仪器未判不可核）")
        # ★ 判决③的断言：**真跑** main-path 并核对标题措辞（行为级，不查源码字符串）
        import subprocess as _sp
        _r = _sp.run([sys.executable, os.path.abspath(__file__), "--tracker", p], capture_output=True, text=True, timeout=120)
        _o = (_r.stdout or "") + (_r.stderr or "")
        ok_hdr = ("不改被核对象" in _o) and ("（**不改被核对象**；临时写面 = `guard/mutation-work/`）" not in _o)
        print(f"  {'✅' if ok_hdr else '❌'} 正控：运行时标题**不再自称「（**不改被核对象**；临时写面 = `guard/mutation-work/`）」**且写明写面（exit={_r.returncode}）")
        if not ok_hdr:
            bad.append("标题仍自称只读或未写写面")
        if bad:
            print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
            return 1
        # ★ 汇总行**如实列全**（此前少报了新增的两条：三态分支 · 标题措辞）
        print("  ✅ --selftest 通过：**正控 4**（悬空工具 · 无引用 · **坏自检件不得当仪器** · **无自检 ⇒ 不可核**）"
              "+ **反控 3**（真工具真卡 · 悬空卡可判 · 坏件被拒/好件可用）+ **1 条标题措辞真跑核**")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
