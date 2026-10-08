# CAHAC v1.2 批 2 · 考古报告（为 5 处待裁提供来历证据）

> **性质**：**考古报告**（依所有者 2026-10-09 指示：「批 2 的 5 处设计决策我判断不了，你考古一下给我更完整的信息」）。
> **★ 它不是材料的新版本，而是【材料的依据】**：`cahac-v1.2-batch2-decision-material.md` 给的是备选，本报告给的是**这些值/设计是怎么来的**。
> **方法**：只读检索；对比**草案 v0.1（19:36）→ v1.0（19:49，相隔 12 分钟）**；查**既有权威文档**（章程 / agent-bus-principles / bb-taskboard / comm-standard）。

---

## 0. 一句话总纲（★ 先看这个）

> **CAHAC v1.0 是在 12 分钟内从草案扩写成的** —— 草案 87 行、v1.0 371 行。
> ⇒ **⇒ 因此 v1.0 里【新引入的数值与状态】多为快速填写，未回到既有权威文档对齐**。
> ⇒ **而既有体系里【确实有权威定义】的三处（COLLAB 的通道 / dedup_key 的构造 / task 的状态机），CAHAC 与它们【不一致】。**

**所以这批裁决的性质，不是「选一个我喜欢的值」，而是**：**CAHAC 要不要与既有权威文档对齐？**

---

## 1. 硬证据表（每条都可复跑）

| # | 证据 | 出处 | 命令 |
|---|---|---|---|
| **E1** | **v0.1 → v1.0 相隔 12 分钟**（19:36:48 → 19:49:30）| mtime | `stat -f '%Sm' cahac-protocol-draft-v0.1.md cahac-protocol-v1.0.md` |
| **E2** | **草案【完全不含】`CREATED`/`QUEUED`/`ASSIGNED`** | 草案全文 | `grep -nE "CREATED\|QUEUED\|ASSIGNED" cahac-protocol-draft-v0.1.md` ⇒ **空** |
| **E3** | **草案的 COLLAB 行【无权重】**，只有成本档「中」 | 草案 L22 | `sed -n '22p' cahac-protocol-draft-v0.1.md` |
| **E4** | **草案的 ACK 行写「极低（目标消灭）」** | 草案 L24 | `sed -n '24p' cahac-protocol-draft-v0.1.md` |
| **E5** | **草案权重表 5 项**：`broadcast=10× / p2p=1× / event=0.5× / **blackboard 读=0.1×** / mailbox=0.05×` | 草案 L44 | `sed -n '44p' cahac-protocol-draft-v0.1.md` |
| **E6** | **v1.0 权重表 6 项**：`broadcast 10 / p2p 1 / eventbus 0.5 / **黑板写 0.1** / **黑板读 0.05** / mailbox 0.05` | v1.0 §5.2 | `sed -n '/^### 5.2 成本权重表/,+8p' cahac-protocol-v1.0.md` |
| **E7** | **章程明确「COLLAB→线程」**（而 CAHAC 写「p2p（线程内）」）| `docs/AGENT-NETWORK-CHARTER.md` L29 | `grep -n "COLLAB" docs/AGENT-NETWORK-CHARTER.md` |
| **E8** | **章程明确「去重键=内容指纹」** | `AGENT-NETWORK-CHARTER.md` L33 | `grep -n "去重键" docs/AGENT-NETWORK-CHARTER.md` |
| **E9** | **章程明确「反 ack 乒乓」是设计意图**（2026-10-04 MBP 提议）| `AGENT-NETWORK-CHARTER.md` L27 | `grep -n "反 ack" docs/AGENT-NETWORK-CHARTER.md` |
| **E10** | **`agent_thread` = 「读线程 / 跨会话历史」** | `docs/agent-bus-principles.md` L260 | `sed -n '260p' docs/agent-bus-principles.md` |
| **E11** | **章程里【没有】成本权重表** ⇒ 权重是 CAHAC 独有 | 章程全文 | `grep -nE "成本\|权重" docs/AGENT-NETWORK-CHARTER.md` ⇒ **空** |
| **E12** | **现役 task 状态机是 5 态**：`todo → claimed → done → verified`（+ `blocked`）| `scripts/bb-taskboard.py` 文档串 | `sed -n '1,20p' scripts/bb-taskboard.py` |
| **E13** | **CAHAC §7.3 的状态机【不含】上述任何一个** | v1.0 §7.3 | `sed -n '152p' cahac-protocol-v1.0.md` |
| **E14** | **61.8% / 26B / 19 天 / 98% 无出处**（我一度以为在 `chengguo-sources-scan` 找到，实为「市值 61.86 亿」）| 全库检索 | `grep -rn "61.8" docs/ research/` |

---

## 2. 逐项考古

### ① `CREATED` vs `QUEUED` —— **两个都是 v1.0 的 12 分钟里新造的**

**证据**：**E2** —— **草案里三个词一个都没有**。

**而 v1.0 里它们出现在四处且互不一致**：
- §4 L78：`CREATED→ASSIGNED→RUNNING→DONE/FAILED/TIMEOUT`
- §7.2 L148：`"state": "QUEUED|RUNNING|DONE|FAILED|TIMEOUT"`
- §7.3 L152：`QUEUED → RUNNING → …→ FAILED → (retry≤max) → QUEUED`
- §12 L222–231：`[*] --> CREATED / … / FAILED --> QUEUED`

**★ 而现役系统里的 task 状态机是【第三套】**（**E12**）：`todo → claimed → done → verified`（+`blocked`）。

> **⇒ 所以真实情况是【三套并存】**：CAHAC §4/§12 一套、CAHAC §7 一套、**在役 `bb-taskboard` 一套**。
> **⇒ 而三套里【唯一有实际运行数据的是第三套】。**

**⇒ 最小裁决问题**：**CAHAC 的 task 状态机，要不要与在役的 `bb-taskboard`（`todo/claimed/done/verified/blocked`）对齐？**
- **要对齐** ⇒ ①⑤ 一起解决（且迁移选项 B 就自然落地了）
- **不对齐** ⇒ 需说明「CAHAC 的 task 与 taskboard 的 task 是两种东西」

---

### ② `COLLAB` 0.8 —— **0.8 是 v1.0 新填的，且通道写错了**

**证据**：
- **E3**：草案的 COLLAB 行**没有权重**，只有成本档「**中**」
- **E7**：**章程说 `COLLAB→线程`**（独立通道），而 CAHAC §4 写 `p2p（线程内）`
- **E11**：**章程没有成本权重表** ⇒ 0.8 **没有任何既有依据**

**★ 而「中」这一档在草案里是【相对量级】而非精确值** ⇒ v1.0 把它变成了精确的 0.8 ⇒ **⇒ 但没说明换算依据**。

**⇒ 最小裁决问题**：**`COLLAB` 的成本该按【线程】还是【p2p】算？**
- 若 **COLLAB 是独立通道（章程口径）** ⇒ 0.8 是合理的独立定价，**只需补理由**
- 若 **COLLAB 就是 p2p 的一种** ⇒ 应为 1.0，**0.8 是错的**

---

### ③ `ACK` 0.05 —— ★ **机制完全解开了：它按【黑板读】的价计**

**证据链**：
1. **E4**：草案写 ACK「**极低（目标消灭）**」⇒ **这是【目标】不是实测**
2. **E9**：章程有明确的「**反 ack 乒乓**」设计意图（2026-10-04 MBP 提议）
3. **E5 → E6 的对比**：**草案的「blackboard 读」= 0.1** ⇒ **v1.0 改成 0.05，并新增「blackboard 写 = 0.1」**
4. **而 v1.0 §4 给 ACK 的值 = 0.05** ⇒ **⇒ 恰好等于 v1.0 的【黑板读】** ⇒ **⇒ 而 ACK 实际走【黑板写】**

> **⇒ 所以最可能的解释**：**v1.0 把「黑板读」从 0.1 降到 0.05 时，ACK 的值跟着（或照着）变成了 0.05 —— 而 ACK 是【写】。**
> **⇒ 这不是「定价决策」，是【对照失误】。**

**★ 而「低价是激励还是实测」这个问题，考古给出了答案**：
- **草案的用词是「目标消灭」** ⇒ **⇒ 它是【设计目标】**
- **章程的「反 ack 乒乓」** ⇒ **⇒ 它是【明确的意图】**
- ⇒ **⇒ 所以 ACK 的低价【是激励】—— 但它被填成了一个【属于另一种操作的价】**

**⇒ 最小裁决问题**：**保留「ACK 应廉价」这个意图的同时，怎么让它【价格自洽】？**
- 选 **A**（保留 0.05 + 定义一条独立轻量写路径）⇒ **保住了意图，且不再是「按黑板读计费」**
- 选 **B**（改 0.1）⇒ **自洽了，但放弃了对 ACK 的成本激励**

---

### ④ `dedup_key` 两套构造 —— ★ **章程已经定了：内容指纹**

**证据**：
- **E8**：**章程 L33 明文**：`同内容重投判 dup ⇒ 重投必须改内容（**去重键=内容指纹**）`
- **E14 相关**：草案 L65–66 只有**事件域**那套：`dedup_key 保证重复事件不重复处理`
- **而结构化命名式（`task:phoneuse-lookup`）出现在 v1.0 附录 A 的示例里**

> **⇒ 所以两套的来历是**：**指纹式 = 草案原有（且被章程确立）**；**结构式 = v1.0 附录 A 新加的示例**（**未回头改 §8.3，也未说明适用域**）。

**⇒ 最小裁决问题**：**结构化命名式要【保留为任务域】还是【删掉（因为章程已定内容指纹）？**
- ★ **注意**：**章程那条的语境是「同内容重投」** ⇒ 它解决的是**重投去重**；而**结构化命名式解决的是「同一任务的多次消息要能关联」** ⇒ **⇒ 二者可能确实是不同用途**（这正是我倾向 A 的理由）

---

### ⑤ `thread` / `task_id` —— **`thread` 的语义是现成的：跨会话历史**

**证据**：
- **E10**：`agent_thread` = 「读线程 / **跨会话历史**」
- 草案只提「已有 `agent_thread`/gov audit」⇒ **⇒ `thread` 是【既有工具的概念】，v1.0 直接拿来当信封字段**

**★ 而 `task_id` 属于任务卡体系**（`bb-taskboard` 的卡是**任务**）⇒ **⇒ 两者本是【不同体系的标识】**。

**⇒ 最小裁决问题**：**`thread`（跨会话历史）与 `task_id`（任务）的从属关系是什么？**
- ★ 我倾向的「**一 thread 可含多 task**」的**依据**：**§7.2 的 `envelope` 内含 §3 信封 ⇒ 可携带 `thread`** ⇒ 结构上支持「task 属于某 thread」

---

## 3. ★ 一条与裁决无关但更重要的发现

**CAHAC v1.0 有三个地方【与既有权威文档不一致】**（**E7 / E8 / E12**）：

| CAHAC 写 | 既有权威文档 | 冲突 |
|---|---|---|
| `COLLAB → p2p（线程内）` | 章程：`COLLAB → 线程` | **通道归属** |
| `dedup_key`（附录 A 用结构式）| 章程：`去重键=内容指纹` | **构造** |
| task 状态机 `CREATED/QUEUED/RUNNING/…` | 在役 `bb-taskboard`：`todo/claimed/done/verified/blocked` | **状态机** |

> **⇒ 这三处【都不是笔误，而是「12 分钟扩写时未回头对齐既有文档」】**。
> **⇒ 而这正是我提给 CAHAC 的 S2「域声明条款」要解决的问题**（**声明它管辖什么、与既有独立规范的关系**）——
> **⇒ 现在它有了三个具体实例，比抽象条款强得多。**

---

## 4. 复现命令（第三方可原样重跑）

```bash
cd ~/dsh-collab/research/cost-governance
# E1 时间线
stat -f '%Sm  %N' -t '%Y-%m-%d %H:%M:%S' cahac-protocol-draft-v0.1.md cahac-protocol-v1.0.md
# E2 草案无三词
grep -cE "CREATED|QUEUED|ASSIGNED" cahac-protocol-draft-v0.1.md          # ⇒ 0
# E3 E4 E5 草案原文
sed -n '22p;24p;44p' cahac-protocol-draft-v0.1.md
# E6 v1.0 权重表
sed -n '/^### 5.2 成本权重表/,+8p' cahac-protocol-v1.0.md
# E7 E8 E9 章程三条
grep -nE "COLLAB|去重键|反 ack" ~/dsh-collab/docs/AGENT-NETWORK-CHARTER.md
# E10 agent_thread 语义
grep -n "agent_thread" ~/dsh-collab/docs/agent-bus-principles.md
# E11 章程无权表
grep -cE "成本权重|权重表" ~/dsh-collab/docs/AGENT-NETWORK-CHARTER.md     # ⇒ 0
# E12 在役 task 状态机
sed -n '1,20p' ~/dsh-collab/scripts/bb-taskboard.py
# E13 CAHAC 状态机
sed -n '152p' cahac-protocol-v1.0.md
# E14 61.8 出处
grep -rn "61.8" ~/dsh-collab/docs/ ~/dsh-collab/research/ 2>/dev/null | head
```

---

## 5. 给裁决者的一句话

> **这 5 处里，真正需要你决定的是【一件事】：CAHAC 要不要与既有权威文档对齐？**
> · **要对齐** ⇒ ①③⑤ 有明确答案（对齐 `bb-taskboard` 的状态机 / 让 ACK 价格自洽 / thread 从属 task），②④ 只是补说明
> · **不对齐** ⇒ 那么需要说明**为什么 CAHAC 自成一套**，而这**本身就要写进规范**（否则下一个人还会问同样的问题）

**★ 而我不替这个决定** —— 因为它是**架构取向**，不是数值选择。
