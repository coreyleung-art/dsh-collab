#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""csx-mount-record-mutation.py — C5 负控：挂载记录判据**能不能红**（星桥批准的五条之一）。

★ 判据来源：「一个判据若没有能让它失败的输入，**它就不是判据，是日志**。」
★ 做法：把真日志复制到**沙箱**（不进 /tmp，跑完即删），施加 5 种「应当使它失败」的变异，
  逐条跑 `csx-mount-record-check.py`，要求**每条都红**；再跑一次未变异的基线要求**绿**。
★ 零接触：全程只被读取的原件是 `~/dsh-collab/logs/dsh-plugin-context-survival.log` 与插件目录；
  所有写入都落在沙箱里。

退出码：0 = 基线绿且 5 条变异全红 · 1 = 有变异没红（判据空转） · 2 = 环境错误
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

LOG = os.path.expanduser("~/dsh-collab/logs/dsh-plugin-context-survival.log")
PLUGIN = os.path.expanduser("~/dsh-collab/devices/dsh-plugin-context-survival")
CHECK = os.path.expanduser("~/dsh-collab/tools/csx-mount-record-check.py")
WORKROOT = os.path.expanduser("~/dsh-collab/guard/mutation-work")


def run_check(log_path, expect_current=False, mode=None):
    cmd = [sys.executable, CHECK, "--log", log_path]
    if expect_current:
        cmd.append("--expect-current")
    if mode is not None:
        cmd += ["--mode", mode]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def lines_of(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.readlines()


def main():
    if not os.path.isfile(LOG):
        print(f"环境错误：日志不存在 {LOG}")
        return 2
    os.makedirs(WORKROOT, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="mountrec-", dir=WORKROOT)
    try:
        base = os.path.join(sb, "base.log")
        shutil.copy2(LOG, base)

        code, out = run_check(base)
        print("=== [基线·未变异] python3 tools/csx-mount-record-check.py ===")
        print(out.rstrip())
        print(f"[exit:{code}]\n")
        results = {}
        if code != 0:
            print("!! 基线本应通过 ⇒ 先修判据再谈负控")
            return 1

        raw = lines_of(base)
        idx = [i for i, l in enumerate(raw) if '"line": "mounted"' in l or '"line":"mounted"' in l]
        if not idx:
            print("!! 基线日志里找不到 mount 记录 ⇒ 无法做变异")
            return 1

        def _mode_of(i):
            try:
                return json.loads(raw[i]).get("mode")
            except Exception:
                return None

        # ★★ 变异目标必须与**门的选取规则**一致：
        #   · 默认（结构档）⇒ 门取**最后一条 serve** ⇒ 变异就打最后一条 serve
        #   · `--mode any` ⇒ 门取最后一条任意 ⇒ 变异就打最后一条
        #   （此前一律打 idx[-1]，而最后一条是 smoke ⇒ 变异打偏、负控静默失效 —— 语料把它抓出来了）
        idx_serve = [i for i in idx if _mode_of(i) == "serve"]
        mi = idx_serve[-1] if idx_serve else idx[-1]
        print(f"!! 变异目标：第 {mi} 行（mode={_mode_of(mi)!r}）· 日志共 {len(idx)} 条 mount（serve {len(idx_serve)} 条）")

        mi_any = idx[-1]

        def mutate(name, fn, expect_current=False, drop_line=False, mode=None):
            p = os.path.join(sb, f"{name}.log")
            out_lines = [] if drop_line else list(raw)
            # ★ 显式 `--mode any` 的用例 ⇒ 门会取**最后一条任意**记录 ⇒ 变异也打那一条
            tgt = mi_any if mode == "any" else mi
            if not drop_line:
                obj = json.loads(raw[tgt])
                fn(obj)
                out_lines[tgt] = json.dumps(obj, ensure_ascii=False) + "\n"
            with open(p, "w", encoding="utf-8") as fh:
                fh.writelines(out_lines)
            c, o = run_check(p, expect_current, mode)
            # ★ 变异**必须真的改变了文本**（否则静默空变 ⇒ 负控假失效）——今天语料正是这样抓到我的
            _changed = (not drop_line) and (out_lines[tgt] != raw[tgt])
            if drop_line:
                _changed = True
            print(f"=== [变异 {name}]（目标行 {tgt} · 文本已改变={_changed}）===")
            print(o.rstrip())
            print(f"[exit:{c}]\n")
            results[name] = c != 0

        mutate("M1 抽掉整条 mount 行", None, drop_line=True)
        mutate("M2 删掉 bundleSha256", lambda o: o.pop("bundleSha256", None))
        mutate("M3 ts 改成非 RFC3339", lambda o: o.__setitem__("ts", "2026/10/10 07:31"))
        # ★ M4/M5 用 `--mode any`：否则会被 serve 筛选先拦下 —— 红是红了，但红的不是**被测的那条判据**（假红）
        mutate("M4 对盘面：version 改成 0.0.1", lambda o: o.__setitem__("version", "0.0.1"), expect_current=True, mode="any")
        mutate("M5 对盘面：entrySha256 翻一位", lambda o: o.__setitem__("entrySha256", ("0" if o["entrySha256"][0] != "0" else "1") + o["entrySha256"][1:]), expect_current=True, mode="any")
        # ★ M6–M8 对应星桥审查位那条：「冒烟 pid 与服务 pid 混着且无区分字段」⇒ C4 强形式不成立
        mutate("M6 删掉 mode 字段", lambda o: o.pop("mode", None))
        mutate("M7 删掉 modeEvidence（只有结论没有依据）", lambda o: o.pop("modeEvidence", None))

        # M8 需要把**所有** mount 记录都改成 smoke，再要求 --expect-current ⇒ 必须红
        p8 = os.path.join(sb, "M8.log")
        with open(p8, "w", encoding="utf-8") as fh:
            for l in raw:
                if '"line": "mounted"' in l or '"line":"mounted"' in l:
                    o = json.loads(l); o["mode"] = "smoke"; l = json.dumps(o, ensure_ascii=False) + "\n"
                fh.write(l)
        c8, o8 = run_check(p8, expect_current=True)
        print("=== [变异 M8 全部记录改成 smoke，再要求对盘面] ===")
        print(o8.rstrip())
        print(f"[exit:{c8}]\n")
        results["M8 只有 smoke 记录却要被当作在役"] = c8 != 0

        print("=== 判定 ===")
        for k, v in results.items():
            print(f"  {'✅' if v else '❌'} {k}：{'变红' if v else '未红（判据空转）'}")
        bad = [k for k, v in results.items() if not v]
        if bad:
            print("  ❌ 负控未通过：" + " ｜ ".join(bad))
            return 1
        print("  ✅ 基线绿，全部变异均红")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
