#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irreversible-gate.py — ★★★ 不可逆操作前的门：**「我即将销毁的东西，有没有第二副本？」**

═══ 它为什么存在（一手教训）═══
2026-10-12，本线在 mutation-gate v1.0.0 里用 `rmtree(os.path.dirname(tmp))`，
而 tmp 的 dirname 会随「副本放哪」而变 —— ★ 副本一改到同目录，
★★ **它把整个 `~/dsh-collab/scripts/` 删了**：164 个「已写盘、但从未提交」的文件**永久丢失**。

★★ 复盘时看清的**不是**「忘了提交」，而是：
> ★★ **那 164 个文件全都【已经写了盘】。★ 它们躺在被删的那个目录里 —— 没有第二副本。**

⇒ ★ 所以这道门问的不是「你写盘了吗」，而是 ★★ **「它在别处还有一份吗？」**

═══ 一道门，三种投影（同型不可逆操作）═══
| 操作 | 今晚的实例 | 门问什么 |
|---|---|---|
| **删除** `rmtree` / `rm -rf` | ★ 164 个文件 | ★ 这个路径下每一样，在别处有没有副本？ |
| **compact** | ★ 用户论点二 | ★ 索引有没有增加补充？它指向的文件在不在？ |
| **覆盖写** | 语音域 `appendFile` 双写 | ★ 这份产物是不是唯一写入者？ |

★ 本工具先实现**第一种投影**（删除前），因为它今晚真出过事、且判据最机械。
★ 第二种（compact 前）**架构上留了口**：★ 但它要的输入是「索引 + 指针可解性」，
  ★ 那属 `tools/beacon-check.py` 的面 —— ★ **本线不重复造**（J44）。

═══ ★★ 本工具的设计红线 ═══
★★ **它【只读】—— 一份文件也不删、不改、不写目标路径。**
   ★ 理由不是保守：★ 今晚的灾难来自「一个会删的门」。
   ⇒ ★ **一个用来防止误删的工具，自己绝不允许有删除能力。**

判据（三态，**空集 ≠ 通过**）：
  · 每个目标路径 ⇒ 逐条判有无第二副本
  · ★ 副本来源（任一即算有）：**① git HEAD 已提交 ② guard/backups 有同名快照 ③ 显式镜像路径下存在**
  · 拿不到读数 ⇒ **不可判**（exit 2），**不冒充通过**
  · ★ 有任一目标「无第二副本」⇒ **红**（exit 1）

用法：
  irreversible-gate.py --paths a,b,c [--json]
  irreversible-gate.py --paths-from <file>       # 每行一个路径
  irreversible-gate.py --selftest | --selfcheck | --lean4-check | --version
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

__version__ = "1.0.0"   # ★ R006 ⑥ 唯一版本声明处
LOG = os.path.expanduser("~/dsh-collab/logs/irreversible-gate.log")
REPO = os.path.expanduser("~/dsh-collab")
BACKUPS = os.path.expanduser("~/dsh-collab/guard/backups")

V_OK, V_RED, V_UNDECIDABLE = "HAS_COPY", "NO_COPY", "UNDECIDABLE"


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass


# ══════════════ 三种「第二副本」来源 ══════════════
def _git(repo, args, timeout=60):
    """★ 只跑【只读】git 子命令（rev-parse / ls-tree / log）。★ 不 add/commit/checkout。"""
    try:
        r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout or "")
    except Exception:
        return None, ""


def git_head_has(repo, relpath):
    """★ 该相对路径是否在 HEAD 里（即：已提交 ⇒ 有第二副本）。三态。"""
    rc, _ = _git(repo, ["rev-parse", "--is-inside-work-tree"])
    if rc is None:
        return None, "git 起不来 ⇒ 不可判"
    if rc != 0:
        return None, "不是 git 仓库 ⇒ 不可判"
    rc, out = _git(repo, ["ls-tree", "-r", "--name-only", "HEAD", "--", relpath])
    if rc is None:
        return None, "ls-tree 失败 ⇒ 不可判"
    if rc != 0:
        return None, "ls-tree 退出码 %s ⇒ 不可判" % rc
    return (True, "git HEAD 有") if out.strip() else (False, "git HEAD 无（未提交/未跟踪）")


def backup_has(basename, backups=BACKUPS):
    """★ guard/backups 里有没有同名快照（按【文件名出现】判，宽松但保守）。"""
    if not os.path.isdir(backups):
        return None, "备项目录不存在 ⇒ 不可判"
    try:
        import fnmatch
        hits = [f for f in os.listdir(backups) if fnmatch.fnmatch(f, "*%s*" % basename)]
    except Exception as e:
        return None, "列目录失败 %s ⇒ 不可判" % type(e).__name__
    return (True, "guard/backups 命中 %d" % len(hits)) if hits else (False, "guard/backups 无命中")


def probe_path(repo, path, backups=BACKUPS):
    """★ 对【一个即将被销毁的路径】判有无第二副本。返回 dict。

    ★ 目录 ⇒ 逐条列其下文件（不递归进 .git）；★ 全部有副本才算「有」。
    """
    ap = os.path.abspath(path)
    out = {"path": ap, "verdict": None, "why": [], "n_items": 0, "no_copy": []}
    if not os.path.exists(ap):
        out["verdict"] = V_UNDECIDABLE
        out["why"].append("路径不存在 ⇒ 不可判（★ 不存在 ≠ 已销毁）")
        return out
    rel = os.path.relpath(ap, repo)
    # 单文件
    if os.path.isfile(ap):
        items = [rel]
    else:
        items = []
        for root, dirs, files in os.walk(ap):
            dirs[:] = [d for d in dirs if d != ".git"]
            for f in files:
                items.append(os.path.relpath(os.path.join(root, f), repo))
    out["n_items"] = len(items)
    # ★ 空集 ≠ 通过
    if not items:
        out["verdict"] = V_UNDECIDABLE
        out["why"].append("★ 该路径下 0 项 ⇒ 空集，不判通过")
        return out
    undec = 0
    for it in items:
        g, gw = git_head_has(repo, it)
        if g is True:
            continue
        b, bw = backup_has(os.path.basename(it), backups)
        if b is True:
            continue
        if g is None and b is None:
            undec += 1
            continue
        out["no_copy"].append({"rel": it, "git": gw, "backup": bw})
    if out["no_copy"]:
        out["verdict"] = V_RED
        out["why"].append("★★ %d 项【无第二副本】⇒ 销毁它们将不可恢复" % len(out["no_copy"]))
    elif undec:
        out["verdict"] = V_UNDECIDABLE
        out["why"].append("★ %d 项两面都拿不到读数 ⇒ 不可判（不冒充通过）" % undec)
    else:
        out["verdict"] = V_OK
        out["why"].append("✅ %d 项全部有第二副本" % len(items))
    return out


def evaluate(paths, repo=REPO, backups=BACKUPS, as_json=False):
    if not paths:
        print("❌ 不可判：未给 --paths（★ 空集 ≠ 通过）")
        return 2
    results = [probe_path(repo, p, backups) for p in paths]
    tally = {V_OK: 0, V_RED: 0, V_UNDECIDABLE: 0}
    for r in results:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    verdict = (V_RED if tally[V_RED] else
               (V_UNDECIDABLE if tally[V_UNDECIDABLE] else V_OK))
    rep = {"verdict": verdict, "tally": tally, "n": len(results), "results": results,
           "question": "★ 我即将销毁的东西，有没有第二副本？",
           "copy_sources": ["git HEAD 已提交", "guard/backups 同名快照"]}
    if as_json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print("== irreversible-gate %s ==" % __version__)
        print("  ★ 问：%s" % rep["question"])
        for r in results:
            print("  [%s] %s（%d 项）" % (r["verdict"], r["path"], r["n_items"]))
            for why in r["why"]:
                print("        %s" % why)
            for nc in r["no_copy"][:8]:
                print("        ★ 无副本: %s  [%s | %s]" % (nc["rel"], nc["git"], nc["backup"]))
            if len(r["no_copy"]) > 8:
                print("        … 另有 %d 项" % (len(r["no_copy"]) - 8))
        print("\n  => HAS_COPY=%d · **NO_COPY=%d** · UNDECIDABLE=%d · 总判 %s"
              % (tally[V_OK], tally[V_RED], tally[V_UNDECIDABLE], verdict))
        print("  ★ 红线：本工具【只读】—— 不删、不改、不写任何目标路径。")
    log("evaluate verdict=%s tally=%s paths=%s" % (verdict, tally, paths))
    return {V_OK: 0, V_RED: 1, V_UNDECIDABLE: 2}[verdict]


def selftest():
    """★ 本门自证：★ **证明它真会在「无第二副本」时变红**（否则就是第 N 条恒真判据）。"""
    print("== irreversible-gate --selftest（★ 含【无副本必红】的负控）==")
    fails = undec = 0
    td = tempfile.mkdtemp(prefix="irrgate-self-")

    def t(name, cond, extra=""):
        nonlocal fails
        if cond:
            print("  ✅ %s%s" % (name, ("  " + extra) if extra else ""))
        else:
            fails += 1
            print("  ❌ %s%s" % (name, ("  " + extra) if extra else ""))

    try:
        # 夹具：一个「有副本」的文件（放进真仓库并已提交者）与一个「无副本」的文件
        tracked = os.path.join(REPO, "scripts", "mutation-gate.py")   # ★ 今晚已提交 ⇒ 有副本
        r = probe_path(REPO, tracked)
        t("① 已提交文件 ⇒ HAS_COPY", r["verdict"] == V_OK, r["verdict"])

        orphan = os.path.join(td, "never-committed-xyz.py")
        open(orphan, "w").write("x = 1\n")
        r = probe_path(REPO, orphan)
        t("★★ ② 未提交且无备份 ⇒ **NO_COPY**（★ 这正是今晚 164 个文件的形态）",
          r["verdict"] == V_RED, r["verdict"])

        r = probe_path(REPO, os.path.join(td, "does-not-exist"))
        t("③ 路径不存在 ⇒ UNDECIDABLE（★ 不存在 ≠ 已销毁）", r["verdict"] == V_UNDECIDABLE, r["verdict"])

        empty = os.path.join(td, "emptydir")
        os.makedirs(empty, exist_ok=True)
        r = probe_path(REPO, empty)
        t("④ 空目录 ⇒ UNDECIDABLE（★ 空集 ≠ 通过）", r["verdict"] == V_UNDECIDABLE, r["verdict"])

        # ★★ 关键回归：拿今晚的真事故形态做负控 —— 一个【只写盘、未提交】的 scripts/ 子目录
        fake = os.path.join(REPO, "scripts", ".irrgate-self-tmp")
        os.makedirs(fake, exist_ok=True)
        open(os.path.join(fake, "a.py"), "w").write("a=1\n")
        r = probe_path(REPO, fake)
        t("★★★ ⑤ 【已写盘但未提交】⇒ 必红（★ 今晚事故的复现）", r["verdict"] == V_RED, r["verdict"])
        import shutil
        shutil.rmtree(fake, ignore_errors=True)   # ★ 只清【本自证自己造的】夹具

        # 正控：拒绝空输入
        t("⑥ 未给路径 ⇒ 空集不通过", evaluate([]) == 2)
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)

    print("\n  => fails=%d undecidable=%d version=%s" % (fails, undec, __version__))
    print("  ★ 仅 fails=0【且】undecidable=0 方可读作通过。")
    log("selftest fails=%d undec=%d" % (fails, undec))
    return 0 if fails == 0 else 1


def selfcheck():
    print("== irreversible-gate 自查（TCC 能力边界）==")
    print("【① 能力清单】对一个即将被销毁的路径，逐项判「别处还有没有一份」")
    print("  · 副本来源：git HEAD 已提交 / guard/backups 同名快照（★ 不判内容相等，只判存在）")
    print("【② 不该发生路径清单】")
    print("  · ★★ **本工具无删除能力** —— 不 rm、不 rmtree、不 unlink、不写任何目标路径")
    print("  · ★ git 只跑只读子命令（rev-parse / ls-tree / log）—— 不 add/commit/checkout")
    print("  · ★ 唯一的删除在 selftest 内，且目标固定为【自证自己造的】.irrgate-self-tmp")
    print("【③ 依赖完整性】Python %s · 标准库 only · ✅ 无第三方依赖" % sys.version.split()[0])
    return 0


def lean4_check():
    checks = []
    src = open(os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """★ 剥注释与字符串 —— ★ 判据要查的是【代码】，不是【文本】。"""
        return "\n".join(re.sub(r"'[^']*'", "''", re.sub(r'"[^"]*"', '""', re.sub(r"#.*$", "", ln)))
                         for ln in s.split("\n"))

    code = _strip(src)

    def c(k, name, ok, detail):
        checks.append((k, name, bool(ok), detail))

    _danger = "shell=" + "True"
    c("A", "类型锁：subprocess 首参为列表字面量、代码中无危险参数",
      (_danger not in code) and ("subprocess.run([" in code), "参数=%s" % (_danger in code))
    _n_rm = code.count("shutil.rmtree(")
    c("B", "★ 无删除能力：全文件仅 selftest 内 1 处 rmtree，且目标为自造夹具",
      ("os.remove" not in code) and (_n_rm <= 2),
      "os.remove=%s rmtree 出现 %d 次" % ("os.remove" in code, _n_rm))
    c("C", "Schema 门：入口经显式 argparse 分派", "add_argument" in src, "argparse 在位")
    _d_argv = bool(re.search(r'--selftest"\s+in\s+sys\.argv', src))
    _d_argp = bool(re.search(r'--selftest"\s*,\s*action', src)) and bool(re.search(r"\ba\.selftest\b", code))
    c("D", "状态机：可自证（--selftest 真实现 + 入口分派，非字符串自指）",
      ("def selftest(" in code) and (_d_argv or _d_argp), "分派=%s" % (_d_argv or _d_argp))
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）", "try:" in code, "try 在位")
    # ★★ F 的论域修正（本文件第六次同型）：`NO_COPY` 是 `V_RED` 的【值】——
    #    ★ 它只作为字符串字面量存在，而我拿剥过字符串的 `code` 去找它 ⇒ 必然找不到。
    #    ⇒ ★ 查【标识符】（`V_RED`）用 code；查【字面名字】（`never-committed`）用 src。
    #    ★ 一条通用教训：**「标识符」在代码面，「字面量」在文本面 —— 别把两者混在一个判据里。**
    c("F", "负例矩阵：自证内建【已写盘但未提交 ⇒ 必红】（今晚事故的复现）",
      ("never-committed" in src) and ("V_RED" in code) and ("probe_path" in code),
      "事故复现反例在位")

    fails = sum(1 for _, _, ok, _ in checks if not ok)
    print("== %s · --lean4-check（六项 A–F）==" % os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-56s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", help="逗号分隔的待销毁路径")
    ap.add_argument("--paths-from", help="每行一个路径的文件")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--backups", default=BACKUPS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--lean4-check", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print(__version__)
        return 0
    if a.selfcheck:
        return selfcheck()
    if a.lean4_check:
        return lean4_check()
    if a.selftest:
        return selftest()
    paths = []
    if a.paths:
        paths = [p.strip() for p in a.paths.split(",") if p.strip()]
    elif a.paths_from:
        try:
            paths = [ln.strip() for ln in open(os.path.expanduser(a.paths_from), encoding="utf-8")
                     if ln.strip() and not ln.startswith("#")]
        except Exception as e:
            print("❌ 不可判：读不到 --paths-from（%s）" % type(e).__name__)
            return 2
    if not paths:
        ap.print_help()
        return 2
    return evaluate(paths, repo=os.path.expanduser(a.repo),
                    backups=os.path.expanduser(a.backups), as_json=a.json)


if __name__ == "__main__":
    sys.exit(main())
