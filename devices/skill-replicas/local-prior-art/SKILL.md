---
name: local-prior-art
description: 本机既有工具/资源/规则的【建前考古】入口——建新工具、写新脚本、定新制度、规划任何"要不要做一个X"之前，先用它查本机 2100+ 项已有资产，避免重复造轮子与"已存在而无人知"。触发词：建前考古/查本机有没有/已有实现/是否已有/复用既有/查重/有没有类似工具/先查再建/prior art。
---

# 建前考古 · 本机既有资产检索

## 触发场景

**在以下任一情形，先跑本工具再动手：**

- **要建新工具/新脚本/新制度/新规划**（"要不要做一个 X？"）
- **怀疑「这个功能是不是已经有人做过」**
- **用户问「之前是不是有过类似的」**
- **发现自己在重复某个模式**（尤其：**踩过的坑又想踩一次**）

## 为什么需要它（根因，2026-10-09 实测）

**实测出一个【结构性不对称】**：

| 外部世界 | 内部世界（本机 2120 项） |
|---|---|
| `web_search` ✓ | ✗ 无对应物 |
| `read_url` / `read_url_batch` ✓ | `read`（**必须先知路径**）|
| `read_url_site`（站点级枚举）✓ | ✗ **无目录级枚举** |
| **4 个发现工具** | **0 个发现工具** |

**⇒ 后果（当日实证，全部真实发生）：**

1. **我没找到 `r006-retrofit.js` / `r006-retrofit-scripts.js` / 273 条合规矩阵** —— 它们**一直都在**
2. **我差点新建一个已存在的沉淀链**（`sedimentation-chain-scan.py` 190 行，2026-08-22 建）
3. **我建的 4 个脚本有 3 个不达 R006**，而**唯一达标的那个是我明确知道标准时写的**
4. **历史上有过三次同类自我剖析**（09-01 / 09-08 / 09-13），根因**都不是「不知道标准」，而是【发现面缺口】**

## 快速使用

### 方式 A：检索（最常用）

```bash
python3 ~/dsh-collab/scripts/local-registry.py search <关键词>
# 例：
python3 ~/dsh-collab/scripts/local-registry.py search r006 retrofit
python3 ~/dsh-collab/scripts/local-registry.py search sediment
python3 ~/dsh-collab/scripts/local-registry.py search 去重 dedup
```

### 方式 B：机器读（供脚本消费）

```bash
python3 ~/dsh-collab/scripts/local-registry.py --json search <关键词>
```

### 方式 C：重建索引（本机新增大量工具后）

```bash
python3 ~/dsh-collab/scripts/local-registry.py build     # 约 1-2 秒
```

### 方式 D：直接消费索引文件（不依赖本工具）

```bash
jq '.items[] | select(.name|test("retrofit"))' ~/dsh-collab/data/local-registry-index.json
grep -i sediment ~/dsh-collab/data/local-registry-index.json
```

## 索引覆盖的 6 个源

| 源 | 内容 | 量级 |
|---|---|---|
| **S1** | `scripts/*.{py,js,sh}` + `devices/dsh-plugin-*`（工具实体）| ~330 |
| **S2** | R006 合规矩阵（历史合规状态）| 273 |
| **S3** | `resource-registry.md`（资源登记表 · 含历次迭代落链记录）| ~520 |
| **S4** | `rules-registry/RULES.md`（规则账本 R###）| ~52 |
| **S5** | 黑板 `data/registry/*`（登记卡）| ~930 |
| **S6** | `~/.dsh/skills/*`（技能）| 16 |

**合计约 2100 项**（随本机资产增长）。

## ★ 判据与已知限制（诚实声明）

**能力**：**词面匹配**（关键词命中 `name` / `desc`）。

**限制（务必知道）**：

- **★「无命中」不等于「不存在」** —— 试**同义词**、**更短的词**、或**换个角度**（如查"去重"而非"dedup"）
- **S5（黑板）离线时该源为空** —— 其余 5 源不受影响（**逐源独立，不互相拖累**）
- **`desc` 来自脚本 docstring 首行** ⇒ **没写中文 docstring 的脚本描述为空**（**这也是 R5 缺口的一种表现**）

## 与其他机制的关系

| 机制 | 分工 |
|---|---|
| **本工具** | **「有没有」** —— 发现面（discovery）|
| **`pre-delete-archaeology.py` + R007** | **「删前考古」** —— 删之前先查 |
| **`r006-recheck.py`** | **「达不达标」** —— R006 合规复核 |
| **`bb-reuse-check.py`** | **「能否跨节点复用」** —— 与"有没有"不同 |

**★ 缺口提示**：**目前有「删前考古」（R007）而【没有「建前考古」的规则/门】** —— 本 skill 是**软性**入口（依赖我注意到它）。
**⇒ 若要"删除失败模式"而非"降低概率"，需把「建前考古」立成规则 + 可执行门**（见 `docs/complete-assessment-r006-discovery-sedimentation-20261009.md` §7 P1）。

## 退出码

| 码 | 含义 |
|---|---|
| **0** | 有命中 / 执行成功 |
| **1** | **无命中**（**不等于不存在**，见上）|
| **2** | 用法错误或环境错误 |

## 自检

```bash
python3 ~/dsh-collab/scripts/local-registry.py --selftest   # 应 0 FAIL
```
