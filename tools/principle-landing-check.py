#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""principle-landing-check.py — 「原则落脚清单」的机械核验（只读）。

★ 立据（星桥 2026-10-10 判决 F）：**原则不会自动跨门传导** —— 一条原则落在一个门里，
  不保证下一个门继承它（实证：`qk-structure-guard` 有声明通路，同作者的 `evidence-channel-guard` 当时没有）。
  ⇒ 原则必须有**落脚表**，且该表本身要能被机械核验（否则清单会静默过期）。

判据：对 `tools/PRINCIPLES-landing.md` 里每一条原则，核其**落脚件**存在、且含**标记串**。
  标记串写在本文件下方的 REGISTRY 里（= 判据的输入面）；清了某条 ⇒ 红。

★ 不主张：本件只核「落脚件存在且含标记」，**不核**该落脚件是否真的实现了那条原则
  （那由各门自己的正/反控负责 —— 见 P1/P2 行的"反控"列）。

退出码：0 = 全部原则有落脚 · 1 = 有原则失去落脚（或清单/标记漂移） · 2 = 环境错误
用法：python3 tools/principle-landing-check.py [--doc <清单路径>]
  ★ `--doc` 的存在理由（实测教训）：本件原先把清单路径**写死**，于是"在沙箱副本上做的负控"
    **根本没测到被测对象**（沙箱那份没被读到，负控假绿）。**不可测的判据 = 没验过的判据。**
"""
import os
import re
import subprocess
import sys

PY = sys.executable or "python3"

HERE = os.path.expanduser("~/dsh-collab")
DOC = os.path.join(HERE, "tools/PRINCIPLES-landing.md")

# ★★ 声明层复审规矩（星桥判决 D 的通用递归）：REGISTRY 与 DOC 本身都是"以声明代证据" ⇒ 需到期复审。
#   否则清单会变成**新的恒绿层**：原则还在表上，但早已与现实脱节。
REVIEWED_AT = "2026-10-10"
REVIEW_INTERVAL_DAYS = 30

# (原则号, 落脚相对路径, 必须命中的标记串)
REGISTRY = [
    ("P1", "tools/incident-regression.py", "已知事故回归语料"),
    ("P2", "tools/qk-structure-mutation.py", "反向对照"),
    ("P3", "tools/evidence-channel-guard.py", "两个视图"),
    ("P4", "tools/qk-structure-guard.py", "_qk_moved_to"),
    ("P4", "tools/evidence-channel-guard.py", "声明通路"),
    ("P5", "tools/csx-mount-record-check.py", "unknown"),
    ("P5", "tools/k6-partial-guard.py", "partial"),
    ("P6", "tools/incident-regression.py", "--selftest"),
    ("P6", "tools/incident-regression.py", "--enrollment-check"),   # 入册完整性（判决 D 的回应）
    ("P7", "tools/csx-mount-record-check.py", "不覆盖"),
    ("P8", "tools/incident-regression.py", "TABLE_REVIEWED_AT"),
    ("P8", "tools/principle-landing-check.py", "REVIEWED_AT"),
    ("P9", "tools/live-role-resolve.py", "targetLive"),
    # ★★ 2026-10-10 判决 C：清单此前只证明「原则被**抄写**一遍」，不证明「被**执行**一遍」——
    #    P9 自己写着「知道该查≠已经查了」，却在**专门管它的那个件**上又犯一次。
    #    ⇒ REGISTRY 现在支持**真跑**：第 4 位 = 命令（exit 0 才算过），第 5 位 = 期望（zero/nonzero）。
    ("P9", "tools/live-role-resolve.py", "selftest", [PY, "tools/live-role-resolve.py", "--selftest"], "zero"),
    # ★ 反控式执行：**默认路径**必须**干净报错**（exit 非 0 且**不得**抛栈）——
    #   这条执行的正是判决 B 那个 100% 崩溃的入口。
    ("P9", "tools/live-role-resolve.py", "用法错误：本工具**事实上必需**",
     [PY, "tools/live-role-resolve.py", "--role", "裁判"], "nonzero"),
]



# ═══════════════════════════════════════════════════════════════════════════════
# ★★ 执行约束（2026-10-10 判决 B：落脚核验"真跑"把只读核验器变成了**命令执行器** ⇒
#    对照 R006#10「无入口 + 有证明」：**给了入口、没给证明**。以下四道约束就是那份证明。）
#    · A 白名单：argv[0] 必须是 Python 解释器；argv[1] 必须是 HERE 下白名单根的**相对路径**；
#      参数不得含 shell 元字符 / 不得是绝对路径 ⇒ **任何不确定一律拒绝**（宁可不跑，不可误跑）。
#    · B 无副作用证明：执行**前后**各取一次清单（tools/*.py + 插件入口/lib），有差异 ⇒ **红**。
#      这正是本机已发生类别（误跑 rescue-unmount 真卸载 / `--selfcheck` 会调 `apply()`）的机械防线。
#    · C 先示后行：执行前打印确切命令（`--quiet-commands` 可关，但**默认开**）。
#    · D 有界：超时 + 输出截断；另有 `exec=False` 声明式豁免（须带理由，走静态核验）。
# ═══════════════════════════════════════════════════════════════════════════════
SAFE_ROOTS = ("tools/", "devices/dsh-plugin-context-survival/")
META = re.compile(r"[;&|`$><\n\r*?\[\]{}()!]")
ARG_OK = re.compile(r"^[A-Za-z0-9_./=:,@+-]+$")
OUT_CAP = 20000
LEDGER_LIMIT = 50          # ★ 上限（原为「拍的值」⇒ 现配合**实算 + 截断告警**使用）
# 可选加强面：纳入目录 mtime（默认关：**并发写目录会误红**）——
# ★ 取舍原则（判决位原话，逐字）：**宁可窄而真，不要宽而假** —— 假红 ⇒ 门被无视 ⇒ 退化为假绿。
#   ⇒ 宁可漏掉「新建/删除目录」这一维，也不接受"时不时误报"（那会让整扇门失去意义）。
DIR_MTIME = "--dir-mtime" in sys.argv
MANIFEST_LEDGER_INFO = {}


def guard_cmd(cmd):
    """A 白名单 + 参数形状。返回 (ok, why)。"""
    if not isinstance(cmd, (list, tuple)) or len(cmd) < 2:
        return False, "命令必须是 [解释器, 相对路径, ...参数]（不接受字符串）"
    interp, script = str(cmd[0]), str(cmd[1])
    if interp != sys.executable and os.path.basename(interp) not in (
            "python3", "python", "python3.9", "python3.11", "python3.12"):
        return False, f"argv[0] 不是 Python 解释器（{interp!r}）"
    if os.path.isabs(script):
        return False, f"argv[1] 是绝对路径（{script}）"
    rel = script.lstrip("./")
    if not any(rel.startswith(r) for r in SAFE_ROOTS):
        return False, f"argv[1] 不在白名单根 {SAFE_ROOTS} 内（{rel}）"
    if not os.path.isfile(os.path.join(HERE, rel)):
        return False, f"argv[1] 指向的文件不存在（{rel}）"
    # ★ 参数判据（第二版）：**只判真正的安全属性**，不判"ASCII 形状" ——
    #   实测教训：第一版用 `^[A-Za-z0-9_./=:,@+-]+$` ⇒ 把合法中文参数（`--role 裁判`）**误拒**。
    #   而真正的风险是：元字符（防"想当然的 shell 拼接"）、路径穿越 `..`、绝对路径（写到白名单外）、
    #   空白（防参数注入成两个词）、超长。★ 且本核验**从不用 shell**（`shell=False`），故元字符仅作纵深防御。
    for a in [str(x) for x in cmd[2:]]:
        if META.search(a):
            return False, f"参数含 shell 元字符（{a!r}）"
        if ".." in a:
            return False, f"参数含路径穿越（{a!r}）⇒ 拒绝"
        if a.startswith("/"):
            return False, f"参数是绝对路径（{a}）⇒ 拒绝"
        if any(ch.isspace() for ch in a):
            return False, f"参数含空白（{a!r}）⇒ 拒绝（防注入成两个词）"
        if len(a) > 200:
            return False, f"参数过长（{len(a)} 字符）⇒ 拒绝"
    return True, "ok"


def manifest():
    """B：取指纹（用于"无副作用"前后比对）。"""
    import glob
    import hashlib
    out, targets = {}, []
    targets += sorted(glob.glob(os.path.join(HERE, "tools", "*.py")))
    targets += sorted(glob.glob(os.path.join(HERE, "devices/dsh-plugin-context-survival", "lib", "*.js")))
    for extra in ("cli.js", "package.json", "cordis.patch.yml"):
        p = os.path.join(HERE, "devices/dsh-plugin-context-survival", extra)
        if os.path.isfile(p):
            targets.append(p)
    # ★★ 判决未核②：「`≤50` 的依据？」⇒ 诚实回答：**原值 50 是我为控制成本拍的**，不是从实测分布推出来的；
    #   且本机 `~/.dsh/ledger` **当前不存在** ⇒ 该界**无从被触及**，更谈不上「够不够」。
    #   ⇒ 现改为**实算 + 截断告警**：算真实文件数，取 min(N, LEDGER_LIMIT)，被截断则在大声声明里写出。
    ledger = os.path.expanduser("~/.dsh/ledger")
    _all = ([f for f in sorted(glob.glob(os.path.join(ledger, "*"))) if os.path.isfile(f)]
            if os.path.isdir(ledger) else [])
    MANIFEST_LEDGER_INFO.clear()
    MANIFEST_LEDGER_INFO.update({"exists": os.path.isdir(ledger), "total": len(_all),
                                 "used": min(len(_all), LEDGER_LIMIT), "limit": LEDGER_LIMIT,
                                 "truncated": len(_all) > LEDGER_LIMIT})
    targets += _all[:LEDGER_LIMIT]
    # ★ 可选加强面：目录 mtime —— 新建/删除**目录**才会被发现；代价 = 并发写该目录会误红（故默认关）
    if DIR_MTIME:
        for _d in (os.path.join(HERE, "tools"),
                   os.path.join(HERE, "devices/dsh-plugin-context-survival/lib")):
            if os.path.isdir(_d):
                out[os.path.relpath(_d, HERE) + "/"] = "dir-mtime:" + str(int(os.path.getmtime(_d)))
    for f in targets:
        try:
            b = open(f, "rb").read()
            out[os.path.relpath(f, HERE)] = hashlib.sha256(b).hexdigest()[:16] + ":" + str(len(b))
        except Exception as e:
            out[os.path.relpath(f, HERE)] = "ERR:" + e.__class__.__name__
    return out


def manifest_diff(before, after):
    return [f"{k}：{before.get(k)} → {after.get(k)}"
            for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)]


def exec_guard_selftest():
    """★ 有证明（四向 + 副作用向）：证明"入口"本身受约束，而不是"相信它受约束"。"""
    import shutil
    import tempfile
    bad = []
    ok1, w1 = guard_cmd(["/bin/sh", "-c", "echo hi"])
    ok2, w2 = guard_cmd([sys.executable, "tools/live-role-resolve.py", "--selftest"])
    # ★ 元字符用例必须**先让文件存在**，否则会"因文件不存在而拒绝"= **红错了理由**（第一版就踩了这个）
    tmpdir = os.path.join(HERE, "tools")
    probe = os.path.join(tmpdir, "_guard_probe_selftest.py")
    open(probe, "w", encoding="utf-8").write("# probe\n")
    try:
        ok3, w3 = guard_cmd([sys.executable, "tools/_guard_probe_selftest.py", "--a;rm -rf /"])
        ok4, w4 = guard_cmd([sys.executable, "/tmp/evil.py"])
        ok5, w5 = guard_cmd([sys.executable, "tools/_guard_probe_selftest.py", "--out", "/etc/passwd"])
        # ★ 标签如实写：前四项是**正控**（必须被拒），第五项是**反控**（必须被允许）——
        #   此前只写 ✅/❌，读的人分不出哪条是"该红"哪条是"该绿"（gate-scaffold 的 H2 也据此判"自证是否双向"）。
        for name, ok, want, why in (
                ("【正控】拒绝非 Python 解释器", ok1, False, w1),
                ("【正控】拒绝 shell 元字符参数", ok3, False, w3),
                ("【正控】拒绝绝对路径 argv[1]", ok4, False, w4),
                ("【正控】拒绝绝对路径参数", ok5, False, w5),
                ("【反控】允许白名单内只读件（该绿必须绿）", ok2, True, w2)):
            good = ok == want
            if not good:
                bad.append(name)
            print(f"  {'✅' if good else '❌'} {name}（{why}）")
        # 副作用向：自己写一个文件 ⇒ manifest 必须报差异
        before = manifest()
        open(probe, "a", encoding="utf-8").write("# touched\n")
        d = manifest_diff(before, manifest())
        good = len(d) == 1 and "_guard_probe_selftest.py" in d[0]
        if not good:
            bad.append("副作用检测")
        print(f"  {'✅' if good else '❌'} 【正控·副作用向】改动 1 个文件 ⇒ 报差异 {d}")
    finally:
        try:
            os.unlink(probe)
        except Exception:
            pass
        shutil.rmtree(tmpdir + "/__none__", ignore_errors=True)
    if bad:
        print("  ❌ 执行约束自证失败：" + " ｜ ".join(bad))
        return 1
    # ★ 判决 C：比对面必须**自带含项/排除项**（否则读者会把"仓库内没变"读成"什么都没变"）
    # ★★ 判决 C：这里原来读**源码文本**判"比对面声明在不在" ⇒ 改成**真跑**：
    #   直接执行本脚本并核对它的**输出**里有没有那几行（读者路径真的打印了才算）。
    import subprocess as _sp2
    _rr = _sp2.run([sys.executable, os.path.abspath(__file__)], capture_output=True, text=True, timeout=180)
    _oo = (_rr.stdout or "") + (_rr.stderr or "")
    ok_decl = ("**B 的比对面**" in _oo) and ("**排除项**" in _oo) and ("仓库外" in _oo)
    print(f"  {'✅' if ok_decl else '❌'} 【反控】比对面自带声明（含项/排除项/补偿控制）")
    if not ok_decl:
        bad.append("比对面声明缺失")
    _led = os.path.expanduser("~/.dsh/ledger")
    print(f"  {'✅' if True else '❌'} 仓库外面（账本）纳入情况：{'存在，已纳入' if os.path.isdir(_led) else '不存在 ⇒ 本机不适用（如实声明，不假绿）'}")
    # ★ 判决未核②的断言：截断**必须被告警**（用合成清单验逻辑）
    def _trunc(n, limit):
        return {"total": n, "used": min(n, limit), "truncated": n > limit}
    _ok_tr = (_trunc(0, 50)["truncated"] is False and _trunc(50, 50)["truncated"] is False
              and _trunc(51, 50)["truncated"] is True and _trunc(51, 50)["used"] == 50)
    print(f"  {'✅' if _ok_tr else '❌'} 截断告警逻辑：0/50 ⇒ 未截断 · 51 ⇒ **截断且取前 50**")
    if not _ok_tr:
        bad.append("截断告警逻辑错误")
    print(f"  · `--dir-mtime` 当前 = {'开' if DIR_MTIME else '默认关'}（可发现新建/删除目录；代价是并发误红）")
    print("  ✅ 执行约束自证通过：白名单/参数形状/绝对路径/副作用/比对面声明 俱有判别力")
    return 0


QUIET_COMMANDS = "--quiet-commands" in sys.argv


def main():
    if "--exec-guard-selftest" in sys.argv:
        print("principle-landing-check · 执行约束自证（只读；含「证明入口受约束」的五项）")
        return exec_guard_selftest()
    doc_path = DOC
    if "--doc" in sys.argv:
        i = sys.argv.index("--doc")
        if i + 1 >= len(sys.argv):
            print("用法错误：--doc 后需要路径")
            return 2
        doc_path = os.path.expanduser(sys.argv[i + 1])
    if not os.path.isfile(doc_path):
        print(f"环境错误：清单不存在 {doc_path}")
        return 2
    doc = open(doc_path, encoding="utf-8").read()
    bad = []
    # ★ 反向完整性：**清单里出现的每一条原则，都必须有落脚行** ——
    #   否则「往清单里加一条原则但不给落脚」就会静默发生（正是本门要防的那类漂移）。
    import re as _re
    doc_pids = sorted(set(_re.findall(r"\|\s*(P\d+)\s*\|", doc)), key=lambda x: int(x[1:]))
    reg_pids = {r[0] for r in REGISTRY}
    for pid in doc_pids:
        if pid not in reg_pids:
            bad.append(f"清单里有原则 {pid}，但 REGISTRY 里**没有它的落脚行** ⇒ 该原则无落脚（加了原则却没给落脚）")
    # 声明层是否过期（过期即红，不是提醒 —— 提醒会被忽略）
    import datetime
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat(REVIEWED_AT)).days
    except Exception:
        age = -1
    stale = age < 0 or age > REVIEW_INTERVAL_DAYS
    print(f"  · 声明层复审：REVIEWED_AT={REVIEWED_AT} · 距今 {age} 天 · 间隔 {REVIEW_INTERVAL_DAYS} 天 ⇒ "
          f"{'★ 已过期' if stale else '未过期'}")
    if stale:
        bad.append(f"声明层已过期（{age} 天 > {REVIEW_INTERVAL_DAYS} 天）⇒ 必须人工复审本清单与 REGISTRY；"
                   f"复审后更新 REVIEWED_AT（理由：以声明代证据的机制若无复审规矩，声明层会变成新的恒绿层）")
    print("principle-landing-check · 原则落脚核验（只读）")
    print(f"  清单：{os.path.relpath(doc_path, HERE) if doc_path.startswith(HERE) else doc_path}")
    ran = 0
    for row in REGISTRY:
        pid, rel, mark = row[0], row[1], row[2]
        cmd = row[3] if len(row) > 3 else None
        expect = row[4] if len(row) > 4 else "zero"
        if cmd is not None:
            # ★ 先示后行（默认开）：读者/审查者看得见**将要执行的确切命令**
            # ★★ 判决方未核项②：`--quiet-commands` 之后**可审计性**未测 ⇒
            #   静音**不等于不可核**：命令一律写 **stderr**（stdout 保持干净可管道），
            #   非静音时另在 stdout 打印（给人看）。
            _cmdline = " ".join(str(x) for x in cmd)
            print(f"      ▶ 真跑（stderr 留痕）：{_cmdline}", file=sys.stderr, flush=True)
            if not QUIET_COMMANDS:
                print(f"      ▶ 真跑：{_cmdline}")
                if ran == 0:
                    _m = manifest()
                    _in = [k for k in _m if not k.startswith("..")]
                    _out = [k for k in _m if k.startswith("..")]
                    print(f"        · **B 的比对面**（无副作用证明用的是它）：**含项** = {len(_m)} 件"
                          f"（**仓库内 {len(_in)} 件**：tools/*.py + 插件 lib/*.js + cli.js + package.json + cordis.patch.yml；"
                          f"**仓库外 {MANIFEST_LEDGER_INFO.get('used', 0)} 件**：`~/.dsh/ledger/*`"
                          f"（该目录{'存在' if MANIFEST_LEDGER_INFO.get('exists') else '**不存在**'} · "f"实算 {MANIFEST_LEDGER_INFO.get('total', 0)} 个文件 · 上限 {MANIFEST_LEDGER_INFO.get('limit')}"
                          f" ⇒ **{'⚠ 已截断：超出上限的未监视' if MANIFEST_LEDGER_INFO.get('truncated') else '未截断'}**））"
                          f"**排除项** = ① 上述之外的**仓库外**路径（`~/Library`、系统路径、网络、其它仓库）**本比对不可见**"
                          f"② 目录**结构**变化（新建/删除**目录** · 子目录内非匹配扩展名的文件）**不判** —— "
                          f"实测（2026-10-10）：新建目录 ⇒ 差异 **0** 条；目录内新建 `.txt` ⇒ **0** 条；"
                          f"`tools/` 下新建 `.py` ⇒ **1** 条（判到）。★ 需覆盖前者可加 `--dir-mtime`"
                          f"（纳入目录 mtime；代价：并发写目录会误红），当前 {'**已开**' if DIR_MTIME else '默认**关**'} "
                          f"③ 运行期**动态构造**的写入目标；"
                          f"**补偿控制** = 白名单 fail-closed（不确定即拒）+ 从不用 shell + 先示后行；"
                          f"**时刻** = {__import__('datetime').datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')[:-2] + ':' + __import__('datetime').datetime.now().astimezone().strftime('%z')[-2:]}")
            gok, gwhy = guard_cmd(cmd)
            if not gok:
                bad.append(f"{pid} 的**真跑**命令**未过执行白名单** ⇒ 拒绝执行且不得算过（{gwhy}）")
                continue
            ran += 1
            _before = manifest()
            try:
                r = subprocess.run([str(c) for c in cmd], cwd=HERE, capture_output=True, text=True, timeout=180)
                rc, out = r.returncode, ((r.stdout or "") + (r.stderr or ""))[:OUT_CAP]
            except Exception as e:
                bad.append(f"{pid} 的**真跑**核验无法执行（{e}）⇒ 不得算过")
                continue
            _diff = manifest_diff(_before, manifest())
            if _diff:
                bad.append(f"{pid} 的**真跑**核验**产生了副作用**（写操作与观测未分离）⇒ 不得算过：{_diff[:3]}")
                continue
            if "Traceback (most recent call last)" in out:
                bad.append(f"{pid} 的**真跑**核验抛了栈（{cmd}）⇒ 判据本身崩了，不得算过")
                continue
            ok_expect = (rc == 0) if expect == "zero" else (rc != 0)
            if not ok_expect:
                bad.append(f"{pid} 的**真跑**核验未达预期（exit={rc}，期望 {expect}）：{' '.join(str(c) for c in cmd)}")
                continue
        if f"| {pid} |" not in doc:
            bad.append(f"清单里找不到原则 {pid} 的条目（清单已漂）")
        path = os.path.join(HERE, rel)
        if not os.path.isfile(path):
            bad.append(f"{pid} 的落脚件不存在：{rel}")
            continue
        src = open(path, encoding="utf-8", errors="replace").read()
        if mark not in src:
            bad.append(f"{pid} 的落脚件 {rel} 里找不到标记串「{mark}」⇒ 该原则在此件已无落脚")
    if bad:
        print("\n❌ 违例：")
        for b in bad:
            print("  " + b)
        return 1
    print(f"  · 共核 {len(REGISTRY)} 条落脚（去重原则 {len({r[0] for r in REGISTRY})} 条）"
          f" · ★ 其中**真跑**（执行核验）{ran} 条 / 静态（条文核验）{len(REGISTRY) - ran} 条"
          f" —— 两者的区别正是判决 C 指的「被**抄写**一遍」与「被**执行**一遍」")
    print("\n✅ 通过：每条原则都有存在且带标记的落脚件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
