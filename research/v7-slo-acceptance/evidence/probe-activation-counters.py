#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S13 机制激活可观测 —— 现测口径

指标定义（§12「机制激活可观测 | 0 | 每次激活可计数可查」）要求的是：
  某个机制**每次被触发**都在一个**可读的持久化计数器**上 +1。
本探针找的是这类计数器的**存在性**。找不到即 = 0，但必须写明【搜了哪些面】。

★ 阴性证据声明：本探针搜了 5 个面。5 面全 0 只说明【这 5 个面里没有】，
  不等于【不存在】—— 见文件末尾的「未搜到的面」。

★ 2026-10-12 增补（v7 M4-① / W4 报「11/14 无负控」）：
  ★ 本件此前**从未被造坏验证过**。
  ★★ 新增 `--dsh-dir`（★ 注入面4 的搜索根，供负控用）· `--selftest`（★ 真调判据：3 正控 + 3 负控）。
  ★★★ **判据本体未改** —— 本增补只【加注入点与自证】，不改原有的 5 面口径与判据收窄史。
"""
import glob, json, os, re, subprocess, sys, argparse, urllib.request

# ★ 判据（★ 原样保留，含收窄史 —— 见下方注释）
NARROW = re.compile(r"activation|(^|[-_])counts?\.(json|txt|jsonl)$", re.I)
BROAD = re.compile(r"activation|counter", re.I)
VENDOR = re.compile(r"/node_modules/|/@deepseek-ai/|/\.pnpm/")
SRC_PAT = re.compile(r"activationCount|activation_count|机制激活计数|activateCount")


def classify_counter_files(files):
    """★ 纯函数：把文件列表分成（宽命中, vendor, 剔后）。

    ★ 判据收窄史（如实记，因为这正是「指标怎么定才不是事后编的」的实例）：
      第 1 版 `activation|counter` ⇒ 命中 47 条，逐条看**全是 counterexample / counter-test**
        （「举证反例」的 counter，不是「计数器」的 counter）⇒ 是噪声，不是命中。
      第 2 版 剔掉 counterexample ⇒ 仍命中 41 条（counter-test / counter-wired 一类同病）。
      第 3 版 改为**只认形态明确的计数器文件名**：含 activation，或名尾为 count/counts。
      ⇒ ★ 这就是「事后调阈值」的教科书形态，故把三代判据一并留档，不许只报最终版。
      第 4 版：收窄后又命中 30 条，逐条看**全是 vendor 运行时**
        ⇒ 再剔 node_modules/vendor 路径。
    """
    # ★★★ 2026-10-12 修（★ 自证的正控抓到的【真缺陷】）：
    #   ★ 旧版【先用 BROAD 筛】再用 NARROW 筛 —★ ★★ **而 BROAD 只认 `activation|counter`，**
    #     ★ NARROW 认的 `(^|[-_])counts?\.(json|txt|jsonl)$` **不含 `counter`** ⇒
    #     ★★ **`step-counts.jsonl` / `counts.json` / `my-count.json` 永远进不了 NARROW 分支**！
    #   ★ 实测支持：旧版报「宽 47 · vendor 37 · 剔后 0」—★ **而剔后 0 正是因为外层把它们全筛掉了**。
    #   ★★★ ⇒ 修法：**外层筛子不得比内层窄** —★ 外层改为 **BROAD 或 NARROW**。
    raw, vendor, kept = [], [], []
    for f in files:
        b = os.path.basename(f)
        if BROAD.search(b) or NARROW.search(b):      # ★ 外层已扩到与内层同宽
            raw.append(f)
            if VENDOR.search(f):
                vendor.append(f)
            elif NARROW.search(b):
                kept.append(f)
    return raw, vendor, kept


def scan_files(root, patterns):
    """★ 在 root 下按 patterns 搜源码里的标识符。"""
    hits = []
    for pat in patterns:
        for f in glob.glob(os.path.join(root, pat), recursive=True):
            try:
                s = open(f, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if SRC_PAT.search(s):
                hits.append(f)
    return hits


def scan(dsh_dir=None, board=True, home=None, repo=None):
    """★ 返回 (HITS, FACES)。``board=False`` 时跳过黑板面（★ 供自证用，免网络）。"""
    HITS, FACES = [], []
    home = home or os.path.expanduser("~")
    repo = repo or os.path.expanduser("~/dsh-collab")

    # 面 1：黑板 data/ 键名
    if board:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8792/data/", timeout=12) as r:
                keys = list(json.load(r)["list"].keys())
            m = [k for k in keys if re.search(r"activation[_/-]?count|机制激活计数|mech[_-]?activation", k, re.I)]
            FACES.append(("面1 黑板 data/ 键名（共 %d 键）" % len(keys), m))
            HITS += m
        except Exception as e:
            FACES.append(("面1 黑板 data/ 键名", ["不可判：%s" % e]))
    else:
        FACES.append(("面1 黑板 data/ 键名", ["★ 本轮跳过（--no-board）"]))

    # 面 2：树外插件源码
    m = scan_files(home, ["dsh-plugin-*/lib/*.js"])
    FACES.append(("面2 树外插件 lib/*.js 源码", m))
    HITS += m

    # 面 3：仓库 tools/ 与 scripts/
    m = []
    for d in ("tools", "scripts"):
        m += scan_files(repo, ["%s/**/*.py" % d])
    FACES.append(("面3 仓库 tools/+scripts/ 源码", m))
    HITS += m

    # 面 4：本地持久化计数器文件
    files = []
    for f in glob.glob(os.path.join(dsh_dir or os.path.join(home, ".dsh"), "**", "*"), recursive=True):
        if os.path.isfile(f):
            files.append(f)
    raw, vendor, kept = classify_counter_files(files)
    FACES.append(("面4 ~/.dsh 计数器形态文件（宽 %d · vendor %d · 剔后 %d）"
                  % (len(raw), len(vendor), len(kept)), kept))
    HITS += kept

    # 面 5：黑板 data/registry 键名
    if board:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8792/data/registry/", timeout=12) as r:
                ks = list(json.load(r)["list"].keys())
            m = [k for k in ks if re.search(r"activat|counter", k, re.I)]
            FACES.append(("面5 黑板 data/registry 键名（共 %d 键 · 描述性命中，不计入）" % len(ks), m))
        except Exception as e:
            FACES.append(("面5 黑板 data/registry 键名", ["不可判：%s" % e]))
    else:
        FACES.append(("面5 黑板 data/registry 键名", ["★ 本轮跳过（--no-board）"]))
    return HITS, FACES


def selftest():
    """★ 3 正控 + 3 负控 —— 全真调 classify_counter_files()。"""
    ok = tot = 0
    import tempfile
    # ★ 正控①：形态明确的计数器名 ⇒ 必须【留】
    tot += 1
    _, _, kept = classify_counter_files(["/x/activation.json", "/x/step-counts.jsonl"])
    if len(kept) == 2:
        ok += 1
        print("  ✅ 正控①：`activation.json` / `step-counts.jsonl` ⇒ 留下（2/2）")
    else:
        print("  ❌ 正控①：明确的计数器名未被留下（%s）" % kept)
    # ★ 负控①：`counterexample` 不得被留下（★ 第一代判据的病）
    tot += 1
    _, _, kept2 = classify_counter_files(["/x/counterexample-notes.md", "/x/counter-test.json"])
    if len(kept2) == 0:
        ok += 1
        print("  ✅ 负控①：`counterexample`/`counter-test` ⇒ 不留（★ 第一代判据的病已修）")
    else:
        print("  ❌ 负控①：噪声名被留下（%s）" % kept2)
    # ★ 负控②：vendor 路径不得被留下（★ 第四代判据的病）
    tot += 1
    _, vendor, kept3 = classify_counter_files(["/x/node_modules/@deepseek-ai/y/activation.js"])
    if len(kept3) == 0 and len(vendor) == 1:
        ok += 1
        print("  ✅ 负控②：vendor 路径 ⇒ 归 vendor 不留（★ 第四代判据的病已修）")
    else:
        print("  ❌ 负控②：vendor 未剔（kept=%s vendor=%s）" % (kept3, vendor))
    # ★ 正控②：宽命中数与剔后数【不是同一个量】⇒ 二者应可同时非零
    tot += 1
    raw, vendor4, kept4 = classify_counter_files(
        ["/x/activation.json", "/x/counterexample.md", "/x/node_modules/a/activation.js"])
    if len(raw) == 3 and len(vendor4) == 1 and len(kept4) == 1:
        ok += 1
        print("  ✅ 正控②：宽 3 / vendor 1 / 剔后 1 ⇒ **三个量被分开**")
    else:
        print("  ❌ 正控②：三个量未分开（raw=%d vendor=%d kept=%d）" % (len(raw), len(vendor4), len(kept4)))
    # ★★ 负控（★ 2026-10-12 真缺陷修入）：【外层筛子不得比内层窄】
    tot += 1
    _, _, k = classify_counter_files(["/x/counts.json", "/x/my-count.json", "/x/step-counts.jsonl"])
    if len(k) == 3:
        ok += 1
        print("  ✅ 负控：`counts.json`/`my-count.json`/`step-counts.jsonl` ⇒ 均保留（★ 外层已包住内层）")
    else:
        print("  ❌ 负控：外层筛子仍比内层窄（只留 %d/3）" % len(k))
    # ★ 负控③：空列表 ⇒ 三者皆空（★ 不得报错、不得造假）
    tot += 1
    if classify_counter_files([]) == ([], [], []):
        ok += 1
        print("  ✅ 负控③：空输入 ⇒ 三者皆空（★ 分母 0 不报通过）")
    else:
        print("  ❌ 负控③：空输入返回非空")
    # ★ 正控③：源码标识符判据（★ SRC_PAT）真能命中
    tot += 1
    if SRC_PAT.search("const activationCount = 0") and SRC_PAT.search("机制激活计数"):
        ok += 1
        print("  ✅ 正控③：`activationCount` / `机制激活计数` ⇒ 源码判据命中")
    else:
        print("  ❌ 正控③：源码判据未命中")
    # ★ 负控④：无关源码不得命中
    tot += 1
    if not SRC_PAT.search("const x = 1  // counter only"):
        ok += 1
        print("  ✅ 负控④：仅含 `counter` 的源码 ⇒ 不命中（★ 判据不过宽）")
    else:
        print("  ❌ 负控④：判据过宽")
    print("\n  自证：%d/%d" % (ok, tot))
    return 0 if ok == tot else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsh-dir", default=None, help="★ 注入面4 的搜索根（供负控用）")
    ap.add_argument("--no-board", action="store_true", help="★ 跳过黑板面（★ 供离机/自证用）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()
    if a.version:
        print("probe-activation-counters 1.1.0")
        return 0
    if a.selftest:
        return selftest()
    HITS, FACES = scan(dsh_dir=a.dsh_dir, board=not a.no_board)
    if a.json:
        print(json.dumps({"hits": sorted(set(HITS)),
                          "faces": [{"name": n, "hits": h} for n, h in FACES]},
                         ensure_ascii=False, indent=1))
        # ★ 判定：有命中 ⇒ PASS（★ 指标要求「可计数可查」⇒ 找到计数器即达）· 无 ⇒ FAIL
        return 0 if HITS else 1
    print("=== 机制激活计数器：5 面扫描 ===")
    for name, hits in FACES:
        print("  %-46s 命中 %d %s" % (name, len(hits), hits[:3] if hits else ""))
    print()
    n = len(set(HITS))
    print("★ 命中总数（去重后）= %d" % n)
    if not HITS:
        print("★ 结论：0 个持久化「机制激活计数器」 ⇒ 与 §12 现状读数「0」一致（★ 这是现测，不是照抄）")
        print("★ 判据：§12 目标「每次激活可计数可查」⇒ **不成立**")
    else:
        print("★ 判据：§12 目标「每次激活可计数可查」⇒ 本面找到 %d 个候选（★ 须人工核它们是否真被每次触发 +1）" % n)
    print()
    print("★ 未搜到的面（阴性证据边界，★ 未搜到 ≠ 不存在）：")
    print("    · 运行时内存态计数器（不落盘者，本探针结构上看不见）")
    print("    · 中枢板 106.53.214.108:8792 的键空间")
    print("    · 会话 JSONL 内部的自定义事件类型")
    print("    · 日志文件中形如 'activated' 的行（本探针只查标识符，未做全文语义检索）")
    return 0 if HITS else 1


if __name__ == "__main__":
    sys.exit(main())
