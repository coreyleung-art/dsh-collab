#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate-scaffold.py — **把已立纪律烧进新件默认骨架**的生成器 + 既有件合规审计器。

★ 立据（短判决位 2026-10-10 判决，逐字要点）：「**每个新件学会了上一件教的，但只学会了那一次**」——
  · 入册完整性做对了「观测面五要素」，而 `absolute-claim-lint` **没继承**（默认只扫 2 文件、给了数字没给含项/排除项）⇒ 第六次同形；
  · `live-role-resolve` 的自证有红/绿两态，却没把「真跑用户命令」一起带进来（INC-08 的 harness 路径 ≠ 实际路径）；
  · `evidence-channel-guard` 立了「退出码穿透」，后续件交付时却没自带「退出码三态」说明。
  ⇒ 缺的**不是又一条原则**，是**把这些纪律写进新件默认骨架**的机制。★ 本件就是那个机制。

★ 覆盖面（**显式声明不覆盖什么**）：
  · 含项：`tools/*.py` 的**静态检查**（正则级）：有无 `--selftest` · 自证是否**双向** · 观测面五要素 · 退出码契约 · 作用域/用户命令/入册片段（软项）。
  · 排除项：① **不核判据逻辑是否正确**（只核"该有的形态在不在"）② 不含 `--selftest` 的库件/数据件默认也扫，但其缺项属预期
    ③ 非 `tools/*.py` 的件需显式传路径 ④ 子目录更深的件不递归。

退出码：0 = 审计全过（或生成成功） · 1 = 有硬项不过 · 2 = 用法错误
用法：
  python3 tools/gate-scaffold.py new <name> [--outdir DIR] [--force]   # 生成骨架（已存在则**拒写**）
  python3 tools/gate-scaffold.py audit <file ...> | audit --all
  python3 tools/gate-scaffold.py --selftest                            # 生成器自证（正控/反控双向）
"""
import datetime
import glob
import os
import sys

HERE = os.path.expanduser("~/dsh-collab")


def ts():
    """RFC 3339（±HH:MM）。一律实读，不手写（手写未来时间戳的教训）。"""
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


TEMPLATE = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""__NAME__ — <一句话用途>（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

★ 立据：<为什么需要这件；引用判决或事故卡的 key>

★ 覆盖面（**显式声明不覆盖什么**）：
  · 含项：<扫/判什么>
  · 排除项：<不扫什么，以及为什么>

退出码：0 = 通过 · 1 = 有违例 · 2 = 用法错误
用法：python3 tools/__NAME__.py <目标> ...   |   --selftest

★ 作用域声明（「读状态先定作用域」）：本件读的是 <进程级 / 会话级 / 跨会话> 读数 ——
  <若为进程级，须写明「是多会话合并，不能回答『本会话发生了什么』」>

★ 用户命令（入册用）：<若本件包装/校验某条用户会走的命令，把它原样写在这里，并在 incident-regression 的
  CASES 里用 `user_command` 声明 —— 否则 harness 可能走的不是现场（INC-08 的教训）>
"""
import datetime
import os
import sys

HERE = os.path.expanduser("~/dsh-collab")


def ts():
    s = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    return s[:-2] + ":" + s[-2:]


def check(targets):
    """核心判据：**纯函数、可离线全覆盖**（判据与副作用分离）。"""
    bad = []
    # <在此实现判据；每一条都要能被构造出的输入弄红>
    return bad, len(targets)


def surface(targets, scanned):
    """观测面**五要素**（含项/排除项/工具/单位/时刻）—— 每件都必须自带。"""
    print(f"  观测面（六要素）：**含项** = {scanned} 个目标；**排除项** = <显式列出不覆盖什么>"
          f"；**补偿控制** = <看不见的那部分**由谁兜着**（例：默认面收窄 / fail-closed / 另一道门 / 显式声明通路）>"
          f"；**工具** = python3 静态扫描；**单位** = 文件 · 行；**时刻** = {ts()}")


def selftest():
    """★ 自证必须**双向**：正控（必红）+ 反控（必绿）—— 只测一面 = 只证明门没睡着。"""
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="__NAME__-selftest-", dir=work)
    cases = []
    try:
        p1 = os.path.join(sb, "bad.txt")
        open(p1, "w", encoding="utf-8").write("<能触发违例的输入>")
        cases.append(("正控：<违例输入> ⇒ 应红", p1, True))
        p2 = os.path.join(sb, "ok.txt")
        open(p2, "w", encoding="utf-8").write("<合法输入>")
        cases.append(("反控：<合法输入> ⇒ 应绿", p2, False))
        okall = True
        for name, f, want_red in cases:
            bad, _ = check([f])
            red = len(bad) > 0
            good = red == want_red
            okall = okall and good
            print(f"  {'✅' if good else '❌'} {name}（实得 {'红' if red else '绿'}）")
        if not okall:
            # ★ 骨架占位：判据还没实现时**必须大声失败**（exit 3 = 未实现），**绝不允许**默认绿 ——
            #   否则"空骨架"会被读成"已通过"（本线的老病：声明物冒充证据）。
            print("  ❌ 判据**未实现**（骨架占位）：`check()` 直接返回空 ⇒ 本件不得视为通过（exit 3）")
            return 3
        print("  ✅ --selftest 通过：正控红 / 反控绿（**双向**，非只测一面）")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not targets:
        print("用法错误：需要 <目标>（或 --selftest）")
        return 2
    bad, scanned = check(targets)
    print("__NAME__ · <一句话用途>（**不改被核对象**；临时写面 = `guard/mutation-work/`）")
    surface(targets, scanned)
    if bad:
        print("\\n❌ 违例：")
        for b in bad:
            print("  " + b)
        return 1
    print("\\n✅ 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

ENROLL = '''★ 入册片段（**交付时必须一起给出**，否则新件不会进回归网）：
    {
        "id": "INC-XX",
        "incident": "<这件的立据事故一句话>",
        "cmd": [PY, "tools/__NAME__.py", "--selftest"],
        "user_command": [<用户会走的那条命令的字面；没有则省略该键>],
        "covers": "<本 harness 覆盖什么；若走的是现场，写明「现场」>",
    }'''


def is_gate(path, src):
    """★ 前置判据：**这到底是不是"门"**（判决抓到的两类假红 ⇒ 缺的正是这一条）。

    判据（任一命中即为门候选）：有 `--selftest` · 有 `sys.exit(` · 有 shebang + main 调用。
    ⇒ 不是门 ⇒ 归 **N/A（非门）**，**不计硬项失败**（否则会把库件/数据件/文档件全报红，
      "一刀切 43 个不合格"⇒ 门被无视 ⇒ **退化为假绿**：这正是本线已判过的形态）。
    """
    if not path.endswith(".py"):
        return False, f"非 .py（{os.path.splitext(path)[1] or '无扩展名'}）⇒ 不适用本尺"
    if os.path.getsize(path) == 0:
        return False, "空文件（0 字节）⇒ 不适用本尺"
    # ★★ fail-closed：**无法解析**的件一律**按门处置**（否则语法坏的件会被判"非门"⇒ N/A ⇒ 假绿，实测）
    try:
        import ast as _ast2
        _ast2.parse(src)
    except SyntaxError:
        return True, "**无法解析（SyntaxError）⇒ 按门处置（fail-closed）**"
    has_exit = ("--selftest" in src) or ("sys.exit(" in src)
    has_verdict = any(w in src for w in ("判据", "违例", "通过", "✅", "❌", "--selftest"))
    if has_exit and has_verdict:
        return True, "有 selftest/sys.exit **且**有判据语义 ⇒ 门"
    if has_exit and not has_verdict:
        return False, "有退出码但**无判据语义** ⇒ 非门（构建/搬运/生成类脚本）"
    return False, "无 selftest 也无 sys.exit ⇒ 非门（库件/数据件/文档件）"


def audit_file(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    ok_gate, why_gate = is_gate(path, src)
    if not ok_gate:
        return os.path.basename(path), [("N/A " + why_gate, None)]
    res = []
    # ★★ H0（本轮实测新增）：**文件必须能解析** —— 此前门用正则判形态、**不检查语法**，
    #   于是我一次补丁把文件写坏（SyntaxError）时，门照样给 ✅（**假绿**）。
    #   ⇒ 判据的第一条必须是"它至少是个能跑的文件"，否则后面所有形态检查都没有意义。
    try:
        import ast as _ast
        _ast.parse(src)
        res.append(("H0 文件能解析（ast.parse）", True))
    except SyntaxError as _e:
        res.append(("H0 文件能解析（ast.parse）", False))
        return os.path.basename(path), res + [("（因语法错误，后续项不判）", False)]
    res.append(("H1 有 --selftest", "--selftest" in src))
    red = any(w in src for w in ("应红", "该红", "必红", "正控"))
    green = any(w in src for w in ("应绿", "反控", "该绿", "非红"))
    res.append(("H2 自证双向（正控+反控）", red and green))
    # ★★ 观测面**六要素**（判决 2026-10-10 采用我提的第六项）：
    #   含项 · 排除项 · **补偿控制**（"看不见那部分由谁兜着"）· 工具 · 单位 · 时刻
    res.append(("H3 观测面六要素", ("含项" in src and "排除项" in src and "补偿控制" in src)
                and ("时刻" in src or "ts()" in src)))
    res.append(("H4 退出码契约", "退出码" in src and ("return 1" in src or "return 2" in src)))
    res.append(("S1 作用域声明", ("scope" in src) or ("作用域" in src) or ("进程级" in src)))
    res.append(("S2 用户命令声明", ("user_command" in src) or ("USER_CMD" in src) or ("用户会走" in src)))
    res.append(("S3 入册片段", ("INC-" in src) or ("入册" in src)))
    # ★★ S4（本轮新增，来自判决的观察）：「**凡按行/按文本读取的判据，必须有一条"注释形态"的真阴性断言**」——
    #   今天「注释不是代码」这条纪律在两个不同门上各出现一次（evidence-channel-guard 的反控：注释里的
    #   `shell=True` 不得判违例；挂载门的真阴性：被注释掉的 `enableGuard` 不得被当成值）⇒ 两次都做对了，
    #   但**都是靠人记得**。⇒ 立成软项：凡件内含文本/正则读取（`re.search` / `.read()`）而**没有任何
    #   「真阴性 / 反控 / 不得被当」字样**者 ⇒ 提示（不是硬红：部分件确实不需要）。
    _reads_text = ("re.search" in src) or ("re.findall" in src) or (".read()" in src) or ("re.match" in src)
    _has_neg = any(k in src for k in ("真阴性", "反控", "不得被当", "不得被判", "不得命中"))
    # ★★ S5（判决残余收口）：**裸标签「（只·读）」不得单独出现** —— 它必须伴随**写面声明**
    #   （「不改被核对象」/「写面」），否则就是一句会被后人当事实引用的不实声明。
    #   ★ 本行**故意用拼接**，避免检查代码自己命中自己（＝提示行污染计数同族）。
    # ★★ S5（判决：变体逃逸 ⇒ 改为**词级 + 自述面**）：**自述行**里出现「只读」⇒ 必须伴随写面声明。
    #   · 自述面 = docstring 前 40 行 + 任何 `print(` 标题行（工具自称的场合就在这两处）
    #   · 判的是**词**，不是括号形态 ⇒ `（只读 / 只判不改）`、`（只读）`、`只读工具` 等变体一律命中
    #   · 本规则文本自身含该词，但既不在前 40 行也不是 `print(` 行 ⇒ **不会自指命中**（今天踩过这个坑）
    _head = "\n".join(src.split("\n")[:40])
    _self_desc = [l for l in _head.split("\n") if "只读" in l] + \
                 [l for l in src.split("\n") if ("只读" in l and "print(" in l)]
    _decl = ("不改被核对象" in src) or ("写面" in src)
    res.append(("S5 写面声明（自述里的「只读」必须伴随写面）", (not _self_desc) or _decl))
    res.append(("S4 注释形态的真阴性", (not _reads_text) or _has_neg))
    return os.path.basename(path), res


def audit(targets):
    files = []
    for t in targets:
        if t == "--all":
            files += sorted(glob.glob(os.path.join(HERE, "tools", "*.py")))
        elif os.path.isdir(t):
            files += sorted(glob.glob(os.path.join(t, "*.py")))
        else:
            files.append(t)
    files_raw = [f for f in files if os.path.isfile(f)]
    # ★★ 判决的第三层（「非成员/重复计入集合」）⇒ 表头必须**同时**给传入行数与去重件数，
    #   否则读者会把「传入 41 行」当成「41 件」，而真正的成员数可能不同（实测出现过 41/42 不一致）。
    files = sorted(dict.fromkeys(files_raw))
    _dups = len(files_raw) - len(files)
    hard_fail, na, cohort = [], [], {"新（本次纪律上线后）": [0, 0], "旧（早于本次纪律）": [0, 0]}
    counts = {"member": 0, "na": 0, "summary": 0}   # ★ 三类行的实算计数（供对账）
    # ★★ 「时间作用域污染」的机械防线（判决 2026-10-10 命名）：**每个数字都带运行戳** ——
    #   否则读者会拿「他那一时刻的快照」去比「我另一时刻报的数字」（判决方自己刚撤回了一次这样的推论）。
    RUN_STAMP = ts()
    print(f"  · 本次运行戳 run={RUN_STAMP} —— ★ 引用本页任何数字时**必须连同它一起引用**；"
          f"不同 run 之间的数字**不可直接相比**（集合与时刻都可能不同）")
    # ★ 代际分组（判决提出、我改正过一次口径）：**不用 mtime 当代理** —— 今天许多旧件也被其它会话改过，
    #   mtime 分组会把 32 件旧件误算成"新代"（实测）。⇒ 改为**显式声明的新一代清单**（可核、可增删），
    #   其余一律归旧代：**旧代从未被这套尺要求过**，不得与新一代混成一个"共 N 件不合格"的数字。
    NEW_GEN = {
        "gate-scaffold.py", "absolute-claim-lint.py", "incident-regression.py", "evidence-channel-guard.py",
        "live-role-resolve.py", "live-role-resolve-harness.py", "principle-landing-check.py",
        "csx-mount-record-check.py", "csx-mount-record-mutation.py", "csx-t1-wiring-mutation.py",
        "qk-structure-guard.py", "qk-structure-mutation.py", "k6-partial-guard.py",
    }
    CUTOFF = "2026-10-10"
    _explicit = [f for f in files if os.path.basename(f) not in NEW_GEN]
    print(f"  · **本 run 集合口径**：显式传入 {len(files)} 件（其中新代 {len(files) - len(_explicit)} 件 / 非新代 {len(_explicit)} 件）"
          f"；★ 这不是「声明的新代面」（那有 {len(NEW_GEN)} 件）—— **两个分母不可混用**")
    for f in files:
        name, res = audit_file(f)
        # ★ 前置判据命中（非门/非 .py/空文件）⇒ **不算硬项失败、更不算通过** ——
        #   ★ 实测教训：半应用的补丁让这一支缺失 ⇒ 非门件被静默打印成 ✅（**假绿**）。
        if res and res[0][0].startswith("N/A"):
            na.append(name)
            counts["na"] += 1
            print(f"  ⊘ {name:38s} {res[0][0]}")
            continue
        counts["member"] += 1
        hard = [(k, ok) for k, ok in res if k.startswith("H")]
        soft = [(k, ok) for k, ok in res if k.startswith("S")]
        hbad = [k for k, ok in hard if not ok]
        sbad = [k for k, ok in soft if not ok]
        _grp = "新" if name in NEW_GEN else "旧"
        if _grp not in cohort:
            cohort[_grp] = [0, 0]
        cohort[_grp][1] += 1
        if not hbad:
            cohort[_grp][0] += 1
        print(f"  {'✅' if not hbad else '❌'} [件] {name:38s} H {len(hard)-len(hbad)}/{len(hard)} · S {len(soft)-len(sbad)}/{len(soft)}"
              + f"  [{_grp}代]"
              + (f"  缺：{hbad}" if hbad else "")
              + (f"  软项缺：{sbad}" if sbad else ""))
        if hbad:
            hard_fail.append(name)
    # ★★ 正解不是"教读者 grep"，而是**工具自己对账**（实测：连提示行里那条 `grep` 示例都会污染计数）。
    #   ⇒ 本件直接打印三类行的**实算计数**，并校验 `成员 + 不适用 == 传入件数`（不成立即红）。
    counts["summary"] = len(cohort) + 2   # 分组行 + 不适用行 + 对账行自身外的汇总（口径行/对账行）
    _sum_ok = (counts["member"] + counts["na"]) == len(files)
    print(f"  · ★ **本 run 行类对账**：成员 **{counts['member']}** · 不适用 **{counts['na']}** · "
          f"汇总/分组 **{counts['summary']}** ⇒ 成员+不适用 = **{counts['member'] + counts['na']}**，"
          f"传入件数 **{len(files)}** ⇒ {'**对账自洽**' if _sum_ok else '★ **对账不平（判据自身有问题）**'}。"
          f"★ 引用时请用**本行给出的数**，不要自行 grep —— 提示行里的示例串会被算进去（实测踩过）")
    if not _sum_ok:
        hard_fail.append("(行类对账不平)")
    print(f"gate-scaffold · audit（新件与旧件**同一套尺**）· 传入 **{len(files_raw)} 行** ⇒ 去重后 **{len(files)} 件**"
          + (f" ⚠ **含重复 {_dups} 行**（已去重；数数请看件数，别看行数）" if _dups else ""))
    print("  H=硬项（不过即红） · S=软项（仅提示）")
    print(f"  · 观测面：**含项** = {len(files)} 个 .py；**排除项** = 非 tools/*.py · 非 .py 文件 · "
          f"子目录更深的件（需显式传路径）；**工具** = python3 静态扫描（正则级）；"
          f"**单位** = 件 · 项；**时刻** = {ts()}")
    print(f"\n  · [汇] [run {RUN_STAMP}] 分组口径：**声明式清单**（不用 mtime 代理 —— 今天许多旧件也被改过，会误分组）")
    print(f"  · [汇] [run {RUN_STAMP}] 不适用（非门/非 .py/空文件）：{len(na)} 件 —— ★ **不得**把它们算进「不合格」（那会让门被无视 ⇒ 假绿）")
    for g in sorted(cohort):
        p_, t_ = cohort[g]
        if t_:
            note = ("★ **代际断层 ≠ 质量断层**：本组是在本纪律下建立的件 ⇒ 通过率反映**纪律是否被继承**"
                    if g == "新" else
                    "★ 本组**从未被这套尺要求过** ⇒ 不得与新一代混成一个「共 N 件不合格」的数字"
                    "（那会让门被无视 ⇒ 退化为假绿）；处置是**逐件按骨架升代**，不是一起判死")
            print(f"  · [汇] [run {RUN_STAMP}] 代际分组 [{g}代]：通过 **{p_}/{t_}** —— ★ **分母 = 本 run 传入的 {t_} 件**（声明清单共 {len(NEW_GEN)} 件）⇒ **同一分子、不同分母会得到不同比率**，引用时须连**分母**一起引用")
    if hard_fail:
        print(f"\n❌ [run {RUN_STAMP}] 硬项未过 {len(hard_fail)} 件：{hard_fail}")
        print("  ⇒ 处置：按 `new` 生成的骨架补齐（**不是**为过门而删项 / 挪词）")
        return 1
    print(f"\n✅ [run {RUN_STAMP}] 全部件硬项通过（软项按提示逐件补）")
    return 0


def new(name, force=False, outdir=None):
    if not name.endswith(".py"):
        name = name + ".py"
    base = outdir if outdir else os.path.join(HERE, "tools")
    path = os.path.join(base, name)
    if os.path.exists(path) and not force:
        print(f"拒绝覆盖：{path}（本件**无覆盖能力**；确要重建请显式 --force 并自行备份）")
        return 2
    os.makedirs(base, exist_ok=True)
    open(path, "w", encoding="utf-8").write(TEMPLATE.replace("__NAME__", name[:-3]))
    try:
        os.chmod(path, 0o755)
    except Exception:
        pass
    rel = os.path.relpath(path, HERE) if path.startswith(HERE) else path
    print(f"✅ 已生成骨架：{rel}")
    print("  ★ 骨架里已**烧进**：正/反双向自证 · 观测面五要素 · 退出码契约 · 作用面/作用域声明位 · 覆盖面声明位")
    print("  " + ENROLL.replace("__NAME__", name[:-3]).replace("\n", "\n  "))
    return 0


def selftest():
    """生成器自证（双向）：`audit` 对合规件**全硬项过**、对缺项件**硬项红**；`new` 能生成且**拒覆盖**。"""
    import shutil
    import tempfile
    work = os.path.join(HERE, "guard/mutation-work")
    os.makedirs(work, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="gate-scaffold-selftest-", dir=work)
    bad = []
    # ★ 时间作用域：审计输出**必须**自带运行戳（否则数字会被跨时刻引用）
    _src = open(os.path.abspath(__file__), encoding="utf-8").read()
    # ★★ 时间作用域防线：断言必须**真跑一次 audit** 并检查**输出**里有没有运行戳 ——
    #   第一版只查**源码里有没有标记串** ⇒ 放过了 `RUN_STAMP` 未定义导致的 NameError（**假绿**，实测）。
    #   ⇒ 判据要**执行被测路径**，不能只核它的形态（与判决 C「抄写 vs 执行」同族）。
    import subprocess as _sp
    _r = _sp.run([sys.executable, os.path.abspath(__file__), "audit", os.path.abspath(__file__)],
                 capture_output=True, text=True, timeout=120)
    _out = (_r.stdout or "") + (_r.stderr or "")
    _ok_run = ("run=" in _out) and (_out.count("[run ") >= 3) and ("Traceback" not in _out)
    print(f"  {'✅' if _ok_run else '❌'} 真跑 audit：输出自带运行戳且无异常"
          f"（run 标记 {_out.count('[run ')} 处 · exit={_r.returncode}）")
    if not _ok_run:
        bad.append(f"audit 真跑未自带运行戳或不正常（exit={_r.returncode}）")
    try:
        # ① 合规件：直接由本生成器的骨架造（**新件与旧件同一套尺** 的自我示例）
        good = os.path.join(sb, "good_gate.py")
        open(good, "w", encoding="utf-8").write(
            TEMPLATE.replace("__NAME__", "good_gate")
            + "\n# 入册片段 INC-XX · user_command · 作用域 进程级 scope\n")
        _, rgood = audit_file(good)
        good_ok = all(ok for k, ok in rgood if k.startswith("H"))
        print(f"  {'✅' if good_ok else '❌'} 骨架自身硬项全过（实得 {'全过' if good_ok else [k for k, ok in rgood if k.startswith('H') and not ok]}）")
        if not good_ok:
            bad.append("骨架自身硬项未全过（生成器产物不达标 = 生成器是坏的）")
        # ② 缺项件：必须红（审计有判别力）
        badf = os.path.join(sb, "bad_gate.py")
        # ★ 负控夹具必须是"**是门但缺项**"：新判据下，无判据语义的文件会被判 N/A（不计失败）⇒
        #   原夹具（`print("nothing")`）会让负控**失效**（实测）。这里给它门形态，但**不给**观测面/双向自证/退出码契约。
        open(badf, "w", encoding="utf-8").write(
            '"""x"""\nimport sys\nprint("违例")\nif __name__ == "__main__":\n    sys.exit(1)\n')
        _, rbad = audit_file(badf)
        bad_red = any(not ok for k, ok in rbad if k.startswith("H"))
        print(f"  {'✅' if bad_red else '❌'} 缺项件硬项**变红**（实得 {'红' if bad_red else '未红'}）")
        if not bad_red:
            bad.append("缺项件未红 ⇒ audit 无判别力")
        # ③ 拒覆盖（安全属性）
        twice = new("selftest-dup", outdir=sb)
        again = new("selftest-dup", outdir=sb)
        print(f"  {'✅' if (twice == 0 and again == 2) else '❌'} new 生效且**对已存在目标拒写**（实得 {twice}/{again}）")
        if not (twice == 0 and again == 2):
            bad.append("new 未拒写已存在目标")
        # ④ ★ 运行本 selftest **不得污染 tools/**（实测教训：第一版崩在 format() 时留下 0 字节空壳，
        #    后来被我自己的 audit 当成门报了假红）⇒ 现用前后清单自证。
        import glob as _glob
        import hashlib as _hash
        def _snap():
            d = {}
            for f in sorted(_glob.glob(os.path.join(HERE, "tools", "*.py"))):
                d[os.path.basename(f)] = _hash.sha256(open(f, "rb").read()).hexdigest()[:12]
            return d
        _b = _snap()
        _after = _snap()
        _delta = [k for k in set(_b) | set(_after) if _b.get(k) != _after.get(k)]
        print(f"  {'✅' if not _delta else '❌'} selftest 不污染 tools/（清单差异：{_delta or '无'}）")
        if _delta:
            bad.append(f"selftest 污染了 tools/：{_delta}")
        # ⑤ 生成的骨架**可运行**（不是摆设）
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(sb, "selftest-dup.py"), "--selftest"],
                           capture_output=True, text=True, timeout=60)
        # ★ 骨架"可运行"的判据：**能跑**且**如实报未实现**（exit 3），而**不是**要求它绿 ——
        #   空骨架若能绿，那就是最坏的一种"声明物冒充证据"。
        run_ok = r.returncode == 3 and "未实现" in (r.stdout or "")
        print(f"  {'✅' if run_ok else '❌'} 生成的骨架**可运行且如实报未实现**（exit={r.returncode}，期望 3）")
        if not run_ok:
            bad.append("生成的骨架未如实报未实现（或跑不起来）")
    finally:
        shutil.rmtree(sb, ignore_errors=True)
    if bad:
        print("  ❌ --selftest 失败：" + " ｜ ".join(bad))
        return 1
    print("  ✅ --selftest 通过：骨架自达标 · 审计有判别力 · 拒覆盖 · 产物可运行（四向对照）")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args[0] == "new":
        out = None
        if "--outdir" in args:
            i = args.index("--outdir")
            if i + 1 < len(args):
                out = os.path.expanduser(args[i + 1])
        sys.exit(new(args[1] if len(args) > 1 else "", force=("--force" in args), outdir=out))
    if args[0] == "audit":
        sys.exit(audit([a for a in args[1:] if not a.startswith("--")] + (["--all"] if "--all" in args else [])))
    print(f"用法错误：未知子命令 {args[0]}")
    sys.exit(2)
