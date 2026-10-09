---
name: reuse-before-build
description: J44「资源复用纪律」的执行门——建任何新工具/脚本/机制之前先跑它：它会搜本机 2100+ 项已有资产；有命中不显式裁决就直接拒绝（exit 1），并留痕可事后核。触发词：建新工具前/要不要新建/复用检查/J44/reuse check/先查再建/避免重复造轮子。
---

# 建前复用门（J44 执行件）

## 触发场景

**在【动手建任何东西之前】跑它**：
- 建新脚本 / 新工具 / 新插件 / 新机制 / 新制度
- 「要不要做一个 X？」之前
- 发现自己在重复某个模式

## 为什么（J44 是 enforced 却曾无执行件）

`rules-registry/RULES.md` **J44** 原文：
> **安装任何工具前先全面搜索本地是否已有**（glob/知识库/工具面）；
> **能调用/映射/标记打通的都不新建**

**而实测（2026-10-09）**：J44 只被两个脚本引用，**都是「规则同步/分类」用途** ⇒ **没有任何手段检查它是否被遵守。**
**⇒ 后果真实发生**：当天差点新建一个已存在的沉淀链扫描器（`sedimentation-chain-scan.py`，2026-08-22 建）。

## 快速使用

```bash
# ① 建之前：声明你要做什么
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --intent "新建一个沉淀扫描器"
#   ⇒ 有命中且未裁决 ⇒ exit 1（门拒绝）

# ② 看过候选后显式裁决（三选一）
python3 ~/dsh-collab/scripts/j44-reuse-gate.py \
  --intent "新建一个沉淀扫描器" --artifact my-scan.py \
  --verdict reuse --note "已有 sedimentation-chain-scan.py，复用之"
#   ⇒ exit 0 且留痕

# ③ 事后核验（可核出「当时是否查过」）
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --check my-scan.py
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --list
```

## 三种裁决（冻结枚举）

| verdict | 含义 | 后续动作 |
|---|---|---|
| **`reuse`** | 已有可直接复用 | **不新建**，直接调已有的 |
| **`adapt`** | 已有但需改造 | 改造它（**不新建**），并记改了什么 |
| **`no-overlap`** | 虽有命中但确实不重复 | 可新建，**须在 note 里说明为何不重复** |

## 退出码

| 码 | 含义 |
|---|---|
| **0** | 门通过（无命中，或已显式裁决）|
| **1** | **门未过**（有命中而未裁决）⇒ **不得据此新建** |
| **2** | 用法或环境错误 |

## 与 `local-prior-art` 的分工

| skill | 管什么 |
|---|---|
| **`local-prior-art`** | **「有没有」** —— 纯发现（想查就查）|
| **`reuse-before-build`**（本 skill）| **「建之前必须查」** —— **带门与留痕**（查了没？留证）|

**⇒ 前者是发现工具，后者是执行门。两者配合：先用前者找到候选，再用后者留痕裁决。**

## 自检

```bash
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --selftest      # 0 FAIL
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --lean4-check   # 6/6 绿
```
