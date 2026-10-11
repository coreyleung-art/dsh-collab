#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qk-structure-mutation.py — `qk-structure-guard.py` 的负控：**它能不能红**。

★ 判据：「一个判据若没有能让它失败的输入，它就不是判据，是日志。」
★ 做法：把板值快照复制到沙箱，施加 5 种「应当使它失败/通过」的变异，逐条跑判据：
   M1 删 k3/k4/k5（07:16 事故形态）· M2 删 5 个 ★ 块 · M3 删 k6_wiring
   M4 迁移态却留全套进度子块（两处重复）· M5 迁移态只留指针（**应当绿** —— 反向对照，防判据恒红）
   ★ M5 是**反向对照**：只有"该红的红、该绿的绿"，才说明判据有判别力（不是恒红噪声）。
★ 零接触：只读板值并落沙箱副本；**不向板写任何东西**（**不改被核对象**；临时写面 = `guard/mutation-work/`）。

退出码：0 = M1–M4 红 且 M5 绿（基线也绿） · 1 = 有变异未按预期 · 2 = 环境错误
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.expanduser("~/dsh-collab")
GUARD = os.path.join(HERE, "tools/qk-structure-guard.py")
WORK = os.path.join(HERE, "guard/mutation-work")


def fixture():
    cands = sorted(glob.glob(os.path.join(HERE, "guard/backups/index-recovery/continuity-index-board-snapshot-ver*.json")))
    if not cands:
        return None
    return cands[-1]


def run(path):
    r = subprocess.run([sys.executable, GUARD, "--from", path], capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    fx = fixture()
    if fx is None:
        print("环境错误：找不到板值快照（先跑一次 curl 留档到 guard/backups/index-recovery/）")
        return 2
    os.makedirs(WORK, exist_ok=True)
    sb = tempfile.mkdtemp(prefix="qkstruct-", dir=WORK)
    try:
        base = os.path.join(sb, "base.json")
        shutil.copy2(fx, base)
        code, out = run(base)
        print("=== [基线·未变异] ===")
        print(out.rstrip())
        print(f"[exit:{code}]\n")
        if code != 0:
            print("!! 基线本应通过")
            return 1

        raw = json.load(open(base, encoding="utf-8"))

        def write(name, mutate, whole=False):
            obj = json.loads(json.dumps(raw))
            if whole:
                mutate(obj)
            else:
                mutate([x for x in obj["open_questions"] if x.get("id") == "Q-K"][0])
            p = os.path.join(sb, f"{name}.json")
            json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            return p

        def drop_keys(q, keys):
            for k in keys:
                q.pop(k, None)

        def drop_star(q):
            for k in [k for k in list(q) if k.startswith("★")]:
                q.pop(k, None)

        # ★ M6/M7 针对星桥那一问：**完全移出**的两种情形（必须一红一绿，否则就是"同痕"没解开）
        def drop_item(obj):
            obj["open_questions"] = [x for x in obj["open_questions"] if x.get("id") != "Q-K"]

        def case_m6(obj):
            drop_item(obj)                                  # 条目整个消失、无任何声明 ⇒ 必须红

        def case_m7(obj):
            drop_item(obj)
            obj["_qk_moved_to"] = "data/registry/context-survival-qk"   # 根级显式声明 ⇒ 应当绿

        cases = [
            ("M1 删 k3/k4/k5（07:16 事故形态）", lambda q: drop_keys(q, ["k3", "k4", "k5"]), True),
            ("M2 删 5 个 ★ 块", drop_star, True),
            ("M3 删 k6_wiring", lambda q: drop_keys(q, ["k6_wiring"]), True),
            ("M4 迁移态却仍留全套进度子块（两处重复）", lambda q: q.__setitem__("moved_to", "data/registry/context-survival-qk"), True),
            # ★ 现实中的 stub：掉**进度子块 + ★ 块**，但**保留指针元数据**（status/tracker）——
            #   第一版连 status/tracker 一起删了，于是"该绿的没绿"，暴露的是**判据**过严（已修）
            ("M6 条目整体消失且无声明（必须红·与误删同痕）", case_m6, True),
            ("M7 条目整体消失但有根级声明（应当绿）", case_m7, False),
            ("M5 迁移态只留指针（反向对照·应当绿）", lambda q: [drop_keys(q, ["k1", "k2", "k21", "k3", "k4", "k5", "k6", "k6_wiring"]), drop_star(q), q.__setitem__("moved_to", "data/registry/context-survival-qk")], False),
        ]

        results = {}
        for name, fn, want_red in cases:
            p = write(name.split()[0], fn, whole=name.startswith(("M6", "M7")))
            c, o = run(p)
            print(f"=== [变异 {name}] ===")
            print(o.rstrip())
            print(f"[exit:{c}]\n")
            results[name] = (c != 0) == want_red

        print("=== 判定 ===")
        for k, ok in results.items():
            print(f"  {'✅' if ok else '❌'} {k}：{'符合预期' if ok else '**不符合预期**'}")
        bad = [k for k, ok in results.items() if not ok]
        if bad:
            print("  ❌ 负控未通过：" + " ｜ ".join(bad))
            return 1
        print("  ✅ 基线绿 · M1–M4 红 · M5（反向对照）绿 ⇒ 判据既有判别力、又不恒红")
        return 0
    finally:
        shutil.rmtree(sb, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
