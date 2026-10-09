#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r006-u6-apply.py — U6 批次1（② TCC + ⑩ 约束门）canonical 块注入器（v1.0.0）

做三件事（★ 全部可回退，先备份）：
  1) 中和各工具里【旧的早期守卫】`if __name__ == "__main__" and "--selfcheck" in ...` /
     `... "--lean4-check" in ...` —— 改为 `if False:`，只动条件行，不动缩进体。
  2) 把 /tmp/r006/engine.txt 的 canonical 块插入到【最后一个 `if __name__ == "__main__":` 之前】。
     ⇒ 理由：块末守卫必须在 main() 之前触发，且必须让本文件其余 def 已执行完
       （否则 `_r006_legacy_narrative()` 取不到本器原有的 selfcheck()）。
  3) 两遍法「先算后填」：先注入 frozen 空集 → 跑各工具 `--r006-sets` 读【实际】三面 →
     再按实测值回填 frozen_* → 复注入。冻结集因此是【实测得到的】，不是猜的。

用法
    python3 scripts/r006-tcc-lean4/r006-u6-apply.py --dry-run     # 只打印将改哪些文件与差异行数
    python3 scripts/r006-tcc-lean4/r006-u6-apply.py --apply       # 真写（自动备份到 /tmp/r006/backup/）
    python3 scripts/r006-tcc-lean4/r006-u6-apply.py --verify      # 只跑 11 个工具的 --selfcheck/--lean4-check
"""
import os
import re
import sys
import ast
import json
import shutil
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.expanduser("~/dsh-collab/scripts")
ENGINE = os.path.join(HERE, "engine.txt")
BACKUP = os.path.join(HERE, "backup")
DECLS = os.path.join(HERE, "decls.json")
MARK_S = "# ═══════════ R006 ② TCC 能力边界自检 + ⑩ 约束门（canonical 块"
MARK_E = "# ══════════════════════════════ R006 块结束 ══════════════════════════════"
SHIM_S = "# ── R006 早期旗标垫片"
SHIM = '''# ── R006 早期旗标垫片（★ 必须在任何【模块级】参数校验之前） ──
# 动因：本器可能在模块级就校验 argv（如「不认识的参数 ⇒ 拒绝」），那会先于文件末的
# canonical 块，把 --selfcheck / --lean4-check / --r006-sets 当成非法参数拒掉
# （实测：selftest-inventory 与 verification-level-lint 都这样）。
# 做法：此处先把三个旗标摘出并暂存，再由文件末块的守卫统一分派 ——
# 既不绕过本器的严格参数治理，也不让治理挡掉自检入口本身。
import sys as _r006_sys
if __name__ == "__main__":
    _R006_EARLY_FLAGS = [f for f in ("--selfcheck", "--lean4-check", "--r006-sets", "--dry-run")
                         if f in _r006_sys.argv]
    if _R006_EARLY_FLAGS:
        _r006_sys.argv = [x for x in _r006_sys.argv if x not in _R006_EARLY_FLAGS]
else:
    _R006_EARLY_FLAGS = []
# ── 垫片结束 ──
'''
GUARD_RE = re.compile(r'^if __name__ == "__main__" and "--(selfcheck|lean4-check)" in .*:$')
MAIN_RE = re.compile(r'^if __name__ == "__main__":\s*$')


SHIM_E = "# ── 垫片结束 ──"


def add_shim(text):
    """把垫片插到【模块 docstring 之后、其余一切之前】；★ 已存在则【整段替换】（不是跳过）。
    —— 幂等检查若写成"存在就跳过"，垫片文本改了也不会生效（本批踩过：--dry-run 进不了捕获列表）。"""
    if SHIM_S in text:
        a = text.index(SHIM_S)
        b = text.index(SHIM_E, a) + len(SHIM_E)
        return text[:a] + SHIM.rstrip("\n") + text[b:], "替换"
    try:
        tree = ast.parse(text)
        n = tree.body[0]
        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str)):
            return text, "无 docstring ⇒ 跳过（须人工确认）"
        lines = text.splitlines(True)
        k = n.end_lineno
        return "".join(lines[:k]) + "\n" + SHIM + "\n" + "".join(lines[k:]), "插于 docstring 后"
    except Exception as e:
        return text, "AST 失败: %s" % e


def _ser(v):
    """JSON 序列化：frozenset/set → 排序列表（frozen_* 回填后不再是 list）。"""
    if isinstance(v, (frozenset, set)):
        return sorted(v)
    if isinstance(v, list):
        return [_ser(x) for x in v]
    if isinstance(v, dict):
        return {k: _ser(x) for k, x in v.items()}
    return v


def render(v, ind=0):
    pad = " " * ind
    if isinstance(v, frozenset):
        return "frozenset()" if not v else "frozenset({%s})" % ", ".join(repr(x) for x in sorted(v))
    if isinstance(v, dict):
        return "{\n" + "\n".join("%s    %r: %s," % (pad, k, render(v[k], ind + 4)) for k in v) + "\n" + pad + "}"
    if isinstance(v, list):
        return "[]" if not v else "[" + ", ".join(render(x, ind) for x in v) + "]"
    if isinstance(v, tuple):
        return "(" + ", ".join(repr(x) for x in v) + ("," if len(v) == 1 else "") + ")"
    return repr(v)


def build_block(decl):
    body = open(ENGINE, encoding="utf-8").read()
    return body.replace("@@DECL@@", render(decl, 0))


def neutralize(text):
    """旧早期守卫 → if False（只改条件行，最小 diff）。"""
    out, n = [], 0
    for ln in text.splitlines(True):
        if GUARD_RE.match(ln.rstrip("\n")):
            out.append('if False:  # ★ R006 ②⑩ 已迁移至文件末 canonical 块（原守卫并入）\n')
            n += 1
        else:
            out.append(ln)
    return "".join(out), n


def inject(text, block):
    lines = text.splitlines(True)
    if MARK_S in text:
        a = next(i for i, l in enumerate(lines) if l.startswith(MARK_S))
        b = next(i for i, l in enumerate(lines) if l.startswith(MARK_E))
        return "".join(lines[:a]) + block + "".join(lines[b + 1:]), "replace"
    idx = [i for i, l in enumerate(lines) if MAIN_RE.match(l)]
    if not idx:
        return text.rstrip("\n") + "\n\n\n" + block, "append"
    k = idx[-1]
    return "".join(lines[:k]) + block + "\n" + "".join(lines[k:]), "insert"


def run(argv, timeout=90):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=SCRIPTS)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:
        return 125, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    decls = json.load(open(DECLS, encoding="utf-8"))
    for _t in decls:
        decls[_t].setdefault("allowed_danger", {})
    if not os.path.isdir(BACKUP):
        os.makedirs(BACKUP)

    if a.verify:
        bad = 0
        for tool in decls:
            for flag in ("--selfcheck", "--lean4-check"):
                rc, out = run([sys.executable, tool, flag])
                mark = "OK  " if rc == 0 else "FAIL"
                if rc != 0:
                    bad += 1
                print("%s %-32s %-14s rc=%s" % (mark, tool, flag, rc))
                if rc != 0:
                    print("\n".join("      " + l for l in out.splitlines()[-8:]))
        print("\n=> %d 项非零" % bad)
        return 0 if bad == 0 else 1

    # ── pass 1：frozen 置空，注入
    for tool in decls:
        p = os.path.join(SCRIPTS, tool)
        if not os.path.isfile(p):
            print("!! 缺文件 %s" % tool)
            continue
        src = open(p, encoding="utf-8").read()
        if a.dry_run:
            nu, n = neutralize(src)
            nb, sh = add_shim(nu)
            nb, mode = inject(nb, build_block(decls[tool]))
            print("%-32s mode=%-8s 垫片=%-14s 中和守卫 %d 行 · %d→%d B" % (
                tool, mode, sh, n, len(src), len(nb)))
            continue
        if not os.path.exists(os.path.join(BACKUP, tool)):
            shutil.copy2(p, os.path.join(BACKUP, tool))
        decl = dict(decls[tool])
        decl["frozen_exec"] = frozenset()
        decl["frozen_write"] = frozenset()
        decl["frozen_danger"] = frozenset()
        src1, sh = add_shim(src)
        src2, n = neutralize(src1)
        src3, mode = inject(src2, build_block(decl))
        open(p, "w", encoding="utf-8").write(src3)
        rc = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
        print("%-32s pass1 %-8s 垫片=%-14s 守卫-%d 语法=%s" % (
            tool, mode, sh, n, "OK" if rc.returncode == 0 else "FAIL:" + rc.stderr[:200]))
        if rc.returncode != 0:
            return 1

    if a.dry_run:
        return 0

    # ── 读实测三面
    print("\n── 实测三面（先算后填）──")
    obs = {}
    for tool in decls:
        rc, out = run([sys.executable, tool, "--r006-sets"])
        try:
            d = json.loads(out[out.index("{"):out.rindex("}") + 1])
        except Exception:
            print("!! %s 读不到读数 rc=%s out=%s" % (tool, rc, out[:200]))
            return 1
        obs[tool] = d
        print("%-32s exec=%-28s write=%-42s danger=%s" % (
            tool, ",".join(d["observed_exec"]) or "-", ",".join(d["observed_write"]) or "-",
            ",".join(d["observed_danger"]) or "-"))

    # ── pass 2：回填 frozen，复注入
    print("\n── 回填 frozen_* 并复注入 ──")
    for tool in decls:
        d = obs[tool]
        decls[tool]["frozen_exec"] = frozenset(d["observed_exec"])
        decls[tool]["frozen_write"] = frozenset(d["observed_write"])
        decls[tool]["frozen_danger"] = frozenset(d["observed_danger"])
    # ★ 先序列化成字符串再落盘 —— `json.dump(o, open(p,"w"))` 会【先截断再序列化】，
    #   序列化抛异常时留下一个被截断的文件（本器第一版就踩了：decls.json 被清空）。
    _txt = json.dumps(_ser(decls), ensure_ascii=False, indent=1)
    open(DECLS, "w", encoding="utf-8").write(_txt)

    for tool in decls:
        p = os.path.join(SCRIPTS, tool)
        src = open(p, encoding="utf-8").read()
        lines = src.splitlines(True)
        a0 = next(i for i, l in enumerate(lines) if l.startswith(MARK_S))
        b0 = next(i for i, l in enumerate(lines) if l.startswith(MARK_E))
        out = "".join(lines[:a0]) + build_block(decls[tool]) + "".join(lines[b0 + 1:])
        open(p, "w", encoding="utf-8").write(out)
        r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
        print("%-32s pass2 语法=%s" % (tool, "OK" if r.returncode == 0 else "FAIL:" + r.stderr[:200]))
        if r.returncode != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
