#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S13 机制激活可观测 —— 现测口径

指标定义（§12「机制激活可观测 | 0 | 每次激活可计数可查」）要求的是：
  某个机制**每次被触发**都在一个**可读的持久化计数器**上 +1。
本探针找的是这类计数器的**存在性**。找不到即 = 0，但必须写明【搜了哪些面】。

★ 阴性证据声明：本探针搜了 5 个面。5 面全 0 只说明【这 5 个面里没有】，
  不等于【不存在】—— 见文件末尾的「未搜到的面」。
"""
import glob, json, os, re, subprocess, urllib.request

HITS = []
FACES = []

# 面 1：黑板 data/ 键名
try:
    with urllib.request.urlopen("http://127.0.0.1:8792/data/", timeout=12) as r:
        keys = list(json.load(r)["list"].keys())
    m = [k for k in keys if re.search(r"activation[_/-]?count|机制激活计数|mech[_-]?activation", k, re.I)]
    FACES.append(("面1 黑板 data/ 键名（共 %d 键）" % len(keys), m))
    HITS += m
except Exception as e:
    FACES.append(("面1 黑板 data/ 键名", ["不可判：%s" % e]))

# 面 2：树外插件源码里的计数器标识符
pat = re.compile(r"activationCount|activation_count|机制激活计数|activateCount")
m = []
for f in glob.glob(os.path.expanduser("~/dsh-plugin-*/lib/*.js")):
    try:
        s = open(f, encoding="utf-8", errors="replace").read()
    except Exception:
        continue
    if pat.search(s):
        m.append(f)
FACES.append(("面2 树外插件 lib/*.js 源码", m))
HITS += m

# 面 3：仓库 tools/ 与 scripts/ 源码
m = []
for d in ("tools", "scripts"):
    for f in glob.glob(os.path.expanduser("~/dsh-collab/%s/**/*.py" % d), recursive=True):
        try:
            s = open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if pat.search(s):
            m.append(f)
FACES.append(("面3 仓库 tools/+scripts/ 源码", m))
HITS += m

# 面 4：本地持久化计数器文件（名含 counter/activation）
# ★ 判据收窄史（如实记，因为这正是「指标怎么定才不是事后编的」的实例）：
#   第 1 版 `activation|counter` ⇒ 命中 47 条，逐条看**全是 counterexample / counter-test**
#     （「举证反例」的 counter，不是「计数器」的 counter）⇒ 是噪声，不是命中。
#   第 2 版 剔掉 counterexample ⇒ 仍命中 41 条（counter-test / counter-wired 一类同病）。
#   第 3 版（本版）改为**只认形态明确的计数器文件名**：含 activation，或名尾为 count/counts。
#   ⇒ ★ 这就是「事后调阈值」的教科书形态，故把三代判据一并留档，不许只报最终版。
#   第 4 版（本版）：收窄后又命中 30 条，逐条看**全是 vendor 运行时**
#     （`node_modules/@deepseek-ai/dsh-subagent/lib/types/activation-setup-registry.js`）
#     —— 那是**别人的机制**，不是**我们的计数器**。⇒ 再剔 node_modules/vendor 路径。
NARROW = re.compile(r"activation|(^|[-_])counts?\.(json|txt|jsonl)$", re.I)
BROAD = re.compile(r"activation|counter", re.I)
VENDOR = re.compile(r"/node_modules/|/@deepseek-ai/|/\.pnpm/")
m, raw, vendor = [], [], []
for f in glob.glob(os.path.expanduser("~/.dsh/**/*"), recursive=True):
    if not os.path.isfile(f):
        continue
    b = os.path.basename(f)
    if BROAD.search(b):
        raw.append(f)
        if VENDOR.search(f):
            vendor.append(f)
        elif NARROW.search(b):
            m.append(f)
FACES.append(("面4 ~/.dsh 计数器形态文件（宽 %d · vendor %d · 剔后 %d）"
              % (len(raw), len(vendor), len(m)), m))
HITS += m

# 面 5：黑板 data/registry 键名
try:
    with urllib.request.urlopen("http://127.0.0.1:8792/data/registry/", timeout=12) as r:
        ks = list(json.load(r)["list"].keys())
    m = [k for k in ks if re.search(r"activat|counter", k, re.I)]
    # ★ 面5 的命中是**描述性卡片名**（如 `…-pending-activation-20260914`），
    #   卡片名里出现 activation ≠ 卡里存着计数器 ⇒ 单列出来，不计入 HITS。
    FACES.append(("面5 黑板 data/registry 键名（共 %d 键 · 描述性命中，不计入）" % len(ks), m))
except Exception as e:
    FACES.append(("面5 黑板 data/registry 键名", ["不可判：%s" % e]))

print("=== 机制激活计数器：5 面扫描 ===")
for name, hits in FACES:
    print("  %-46s 命中 %d %s" % (name, len(hits), hits[:3] if hits else ""))

print()
print("★ 命中总数（去重后）= %d" % len(set(HITS)))
if not HITS:
    print("★ 结论：0 个持久化「机制激活计数器」 ⇒ 与 §12 现状读数「0」一致（★ 这是现测，不是照抄）")
print()
print("★ 未搜到的面（阴性证据边界，★ 未搜到 ≠ 不存在）：")
print("    · 运行时内存态计数器（不落盘者，本探针结构上看不见）")
print("    · 中枢板 106.53.214.108:8792 的键空间")
print("    · 会话 JSONL 内部的自定义事件类型")
print("    · 日志文件中形如 'activated' 的行（本探针只查标识符，未做全文语义检索）")
