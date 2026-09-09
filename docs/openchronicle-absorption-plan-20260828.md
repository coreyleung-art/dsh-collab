# OpenChronicle 吸收完整计划 + 资源管理分析

> 记录：2026-08-28 ｜ 中枢 fa1f9150 ｜ 用户已拍板：同意吸收
> 关键前置发现：OpenChronicle 的 AX 捕获核心是 **Swift**（mac-ax-helper 607 行 + mac-ax-watcher 729 行），**已编译为二进制可复用**——这决定吸收路径

---

## 一、关键决策：桥接 vs 自研 vs 混合

### 决策依据（实测数据）

| 发现 | 影响 |
|------|------|
| AX 捕获核心是 Swift（1336 行），**非 Python** | Rust 重写 = 白写 1336 行 macOS 私有 API 绑定 |
| Swift helper **已编译为二进制**（venv/_bundled/mac-ax-helper + mac-ax-watcher）| **可复用**，无需重编 |
| Python 层只是「调 Swift + LLM 压缩 + MCP 暴露」| 桥接 MCP 引入 Python 常驻 + 双轨数据 |
| 本机 config.toml 已配本地 qwen（**零计费**）| LLM 压缩层成本可控 |

### 三方案对比

| 方案 | 做法 | 优点 | 缺点 | 成本 |
|------|------|------|------|------|
| **X1 桥接 MCP** | dsh 插件调 OpenChronicle 的 MCP server | 最快落地 | Python 常驻 + MCP 协议 + 数据在 ~/.openchronicle 双轨 | 小 |
| **X2 纯自研 Rust** | Rust 绑定 macOS AX + 自写记忆层 | 全 Rust 固化 | **重写 1336 行 Swift AX** + macOS-only，工作量大 | 大 |
| **X3 混合（推荐）** | **dsh 插件直接 spawn 已编译 Swift 二进制**，JSON 进我们记忆层 | 复用 Swift + 去 Python/MCP 中间层 + 数据归一化到统一记忆层 | 需写 Swift 二进制调用封装 | 中 |

**推荐 X3 混合**：
- 保留 OpenChronicle 的 Swift AX 捕获二进制（成熟、已编译）
- dsh 插件直接调它（`Command::new("mac-ax-helper")`），拿 JSON 结构化捕获
- 数据存进**统一记忆层**（不双轨）——用现有 knowledge 插件做索引
- 去掉 Python daemon + MCP 层（省常驻进程 + 协议开销）

## 二、更好的迭代方向（比「照搬 OpenChronicle」更优）

### 方向判断：OpenChronicle 只是「记忆系统的一层」——完整记忆分层应借鉴 MemGPT

```
┌─ 工作记忆（热）─ 当前会话上下文（agent-bus 已有）
├─ 感知记忆（新）─ OpenChronicle 捕获的屏幕/应用上下文 ← 本次吸收
├─ 长期记忆（温）─ knowledge 知识库（已有）+ 黑板（已有）
└─ 归档记忆（冷）─ 论文库/复盘/历史事件（已有雏形）
```

**更好的迭代方向**：不只「吸收 OpenChronicle 一个捕获器」，而是把它作为**「感知记忆」层的首个数据源**，接入已有的记忆分层架构。OpenChronicle 捕获 → 归一化 → 进统一记忆索引（knowledge 插件）→ agent 按需检索。

### 迭代阶梯（每步都有独立价值）

| 步 | 内容 | 独立价值 |
|----|------|---------|
| **S1**（本次）| dsh 插件调 Swift 二进制捕获 → JSON 落盘 | 有了「感知记忆」原始层 |
| **S2** | 捕获数据归一化 → 索引进 knowledge | 可语义检索屏幕上下文 |
| **S3** | 时间线聚合 + 会话精简（借鉴 AriadneMem 状态迁移边）| 防重复、省 token |
| **S4** | agent 主动查「用户此刻在做什么」（current_context 工具化）| 上下文感知能力 |
| **S5** | 跨设备（mac 捕获共享给 i9/MBP 查询）| 三端记忆统一 |

## 三、完整计划（S1-S5 里程碑）

### M1：感知捕获接入（S1）
- [ ] 写 `dsh-plugin-openchronicle`（cordis 插件）：spawn `mac-ax-helper` 二进制 → 解析 JSON → 写入记忆目录（~/.dsh/openchronicle-captures/）
- [ ] 捕获节流：复用 OpenChronicle 的 event_driven + 10min heartbeat + debounce（防过量）
- [ ] 验证：mac-mini 捕获正常，JSON 结构化落盘

### M2：归一化索引（S2）
- [ ] 捕获 JSON → 归一化为记忆文档（Markdown）
- [ ] 接入 knowledge 插件索引（语义检索）
- [ ] 验证：knowledge_search 能检索到「刚才用户在做 X」

### M3：时间线精简（S3）
- [ ] 时间线聚合（借鉴 OpenChronicle timeline + AriadneMem 状态迁移）
- [ ] 会话精简（软 20k/硬 50k token 上限）
- [ ] 验证：检索准确率 + token 占用可控

### M4：上下文工具（S4）
- [ ] `oc_current_context` 工具：agent 可查「用户此刻在做什么」
- [ ] 主动注入：agent 决策时可选注入当前上下文
- [ ] 验证：agent 感知用户实际工作

### M5：跨设备（S5）
- [ ] mac 捕获共享（黑板 notes/ 或 data/ 通道）
- [ ] i9/MBP 查询 mac 端记忆
- [ ] 验证：三端记忆统一

## 四、资源管理分析（防 token 浪费）

### 4.1 捕获成本（磁盘）
| 项 | 量级 | 控制 |
|----|------|------|
| AX 捕获 JSON | 每 10min 一次 × 2-5KB ≈ **~1MB/天** | event_driven + heartbeat 节流 |
| 记忆 Markdown | 会话压缩后 ~10KB/天 | soft/hard limit_tokens |
| 索引（knowledge）| 增量，可忽略 | 增量 upsert |

### 4.2 LLM 成本（token）
| 阶段 | 模型 | 频率 | 单次 | 日成本 |
|------|------|------|------|--------|
| 捕获分类（classifier）| 本地 qwen（**零计费**）| 每会话 | ~1k | 0 |
| 会话压缩（reducer）| 本地 qwen | 每 5-30min | ~2k | 0 |
| **检索（agent 侧）**| 云模型 | 按需 | 需评估 | **主要成本** |

**关键洞察**：OpenChronicle 自身的 LLM 成本是零（本地 qwen）——**真正的 token 成本在「agent 检索记忆」时**。所以：
- 检索必须用 **RAG**（只取相关 chunk，不全文塞入）
- 记忆写入时压缩（减冗余），检索时稀疏（只取相关）
- **正是「token 越来越省」主线的实现**：自动捕获 → 压缩 → 按需检索，替代「每次从零问用户」

### 4.3 避免浪费清单
| 风险 | 对策 |
|------|------|
| 捕获过量（每 10min 全屏 AX 树太大）| 复用 OpenChronicle 节流（event_driven + debounce 3s + 10min heartbeat）|
| 压缩过度（丢失重要上下文）| soft 20k / hard 50k 双阈值 + 24h 去重窗 |
| 检索噪音（无关 chunk 占上下文）| knowledge_search topK 调优 + BM25+向量混合 |
| 双轨数据（~/.openchronicle + 我们记忆）| **归一化到统一记忆层**（不双轨）|
| Python 常驻（daemon + MCP 进程）| X3 去 Python 层（直接调 Swift 二进制）|

### 4.4 规模预估（本机实测）
| 现有 | 规模 | 吸收后 |
|------|------|--------|
| agent-bus.json | 14MB（664 线程）| 不变 |
| ~/.chroma | 782MB | 增量 |
| ~/.openchronicle | 12MB index + 44K memory | 归一化后复用 |
| 新增捕获 | — | ~1MB/天（可忽略）|

## 五、结论

1. **吸收路径**：X3 混合（dsh 插件直接调 Swift 二进制）——复用 OpenChronicle 的成熟 AX 捕获，去 Python/MCP 中间层，数据归一化
2. **更好迭代方向**：不只照搬，而是作为「感知记忆」层接入统一记忆分层（MemGPT 思想）
3. **资源管理**：LLM 成本已零计费（本地 qwen）；真正的 token 省在「RAG 按需检索」——自动捕获→压缩→按需取，替代从零问用户
4. **里程碑**：S1 捕获接入 → S2 归一化索引 → S3 时间线精简 → S4 上下文工具 → S5 跨设备

---
*关联：memory-chain-vs-openchronicle-20260828.md / merge-morphology-openchronicle-eval-20260828.md / 记忆系统论文（MemGPT/AriadneMem）*
