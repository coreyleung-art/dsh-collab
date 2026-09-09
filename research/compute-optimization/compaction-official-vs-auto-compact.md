# 官方 compaction 系列 vs 第三方 dsh-auto-compact 差异对比

> 调研：数据调查员 9828aa93 · 2026-08-18
> 用途：供应链评估补充输入（thread-msxjpn3c-171e1mgf 接单）· 关联 CLD-017 压缩试点
> 证据级别：官方项=本机 runtime 包源码/配置实测（v0.1.0-rc.6）；第三方项=market 索引描述（源码未审，装前查源码纪律不变）

---

## 一、结论先行

1. **官方方案已安装且默认开启**：@deepseek-ai/dsh-compaction（服务缝 ctx.compaction）+ dsh-compaction-basic（策略/摘要后端）+ dsh-compaction-tool-result-pruner（工具结果裁剪）+ dsh-command-compact（/compact 命令），v0.1.0-rc.6 已在 runtime node_modules，liangshen/librarian/waimai-ops 预设已挂载。
2. **自动触发从未生效的根因已定位**：compaction-basic 默认阈值 = 上下文压力的 **80%**（DEFAULT_THRESHOLD_RATIO=0.8），按 contextWindow=1M 计 ≈ **800k token**；当前会话最大 21.1MB（压缩体积）远低于阈值 → auto=true 也永远不会触发。**手动 /compact 是当前唯一可行入口**，或经「新预设继承」调低 thresholdRatio。
3. **第三方 dsh-auto-compact（默认 256K 阈值）恰好补「自动触发」缺口**：官方默认阈值太高，第三方 256K 更贴近实际水位；但属低星第三方，需先审源码、确认与官方 ctx.compaction 服务缝的兼容性（是否复用官方引擎）。
4. **建议**：CLD-017 试点走官方 API（/compact 手动 + 度量）；自动触发缺口优先考虑「官方 compaction-basic 调低 thresholdRatio」而非第三方（同缝、可控、无新依赖）；仅当官方配置路径不可行再评估 dsh-auto-compact。

## 二、官方 compaction 系列（已实测）

| 组件 | 角色 | 关键实现（本机实测） |
|---|---|---|
| @deepseek-ai/dsh-compaction | 抽象服务缝（ctx.compaction） | 引擎接口/错误码/checkpoint 源；toolPairing 平衡校验 |
| @deepseek-ai/dsh-compaction-basic | 策略 + LLM 摘要后端 | DEFAULT_THRESHOLD_RATIO=**0.8**；DEFAULT_RETAIN_RATIO=**0.16**（保留 16% 原文尾部）；maxTokens 默认 **8192**；auto 默认 **true**；compactionRetries/maxOverflowRetries 默认 1 |
| @deepseek-ai/dsh-compaction-tool-result-pruner | 工具结果裁剪（model-free head/middle/tail） | thresholdChars=**8192** / headChars=**4096** / tailChars=**1024**（与预设配置一致）；replay-safe |
| @deepseek-ai/dsh-command-compact | 人工入口 | /compact 斜杠命令 |

**触发与保留语义**（lib/index.js 实测）：
- thresholdTokens = contextWindow × thresholdRatio（1M × 0.8 = 800k token 触发自动压缩）。
- 摘要后保留：16% 原文尾部（verbatim tail）+ LLM 摘要（≤8192 token）+ 结构性 checkpoint。
- 按 provider/model 可做精确覆盖（modelPolicies），支持 thresholdRatio/retainRatio/retainTokens/summarizationModel 等配置键。

**优势**：官方维护、已装已挂载、与 ctx.compaction 服务缝统一、pruner 与策略协同、配置可精确到模型级。
**缺口**：默认 80%×1M 阈值对本网络水位（单会话 3-21MB 压缩体积）过高 → 自动压缩实际不触发；需手动 /compact 或调阈值。

## 三、第三方 dsh-auto-compact（market 索引，源码待审）

| 项 | 值 |
|---|---|
| 来源 | github: Zh-U-hB/dsh-auto-compact（market 索引，低星） |
| 定位 | 自动阈值触发压缩（默认 **256K**），作用于每个会话与 agent preset |
| 与官方关系 | 未知——是否复用 ctx.compaction 服务缝 / compaction-basic 引擎，**待源码审查** |
| 风险 | ① 低星第三方，维护持续性未知；② 与官方策略并存时行为可能重叠/冲突；③ 自动触发若误判可能打断实时会话（外卖/客服）；④ 装前查源码纪律（供应链 0e84e65c 执行） |

**优势**：256K 阈值贴近实际水位，补官方自动触发缺口；开箱即用（宣称）。
**劣势**：非官方、与官方服务缝兼容性未知、自动行为可控性/审计性弱于官方。

## 四、对比表

| 维度 | 官方 compaction 系列 | 第三方 dsh-auto-compact |
|---|---|---|
| 维护方 | deepseek-ai（官方，deepseek-harness monorepo） | Zh-U-hB（个人，低星） |
| 安装状态 | ✅ 已装 v0.1.0-rc.6 + 已挂载 3 预设 | ❌ 未装（候选） |
| 入口 | /compact 命令 + ctx.compaction 服务缝 | 自动触发（默认 256K） |
| 触发阈值 | 0.8 × contextWindow（1M → 800k token） | 256K token（默认） |
| 摘要实现 | LLM 摘要后端（summarizationProvider/Model 可配）+ 16% 原文尾部 | 待源码审查 |
| 工具结果裁剪 | ✅ 内置 pruner（8192/4096/1024） | 未知 |
| 预设集成 | ✅ liangshen/librarian/waimai-ops | 宣称「每个 preset」 |
| 配置粒度 | 模型级覆盖（modelPolicies） | 未知 |
| 主要风险 | 默认阈值过高 → 自动不触发 | 非官方、兼容性未知、自动打断风险 |
| 适用场景 | CLD-017 试点主路径（手动 + 度量） | 自动触发补充（评估后） |

## 五、建议

1. **试点（CLD-017）**：只用官方 API —— /compact 手动触发 3b5efeef→de7b29de 分批，按 compact-measurement-protocol.md 采集；同时验证手动路径是否受 0.8 阈值限制（查 ManualCompactionError 语义）。
2. **自动触发缺口**：优先尝试「新预设继承」配置 compaction-basic thresholdRatio（如 0.3-0.5 × contextWindow 或 retainTokens 直配），在测试会话验证后推广；不动 shipped standard 预设。
3. **第三方**：供应链 0e84e65c 装前审源码（重点：是否 import @deepseek-ai/dsh-compaction、auto 触发钩子、与 tokenMeter 的关系）；审完再决定是否 A/B。

## 六、证据来源

- 本机 runtime：/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh-compaction-basic/lib/index.js（阈值/保留/auto 默认值）、dsh-compaction-tool-result-pruner/lib/index.js（裁剪默认值）、package.json（v0.1.0-rc.6）
- ~/.dsh/market/index.json：官方 4 组件 + dsh-auto-compact 描述
- ~/.dsh/.agent-presets/{liangshen,librarian,waimai-ops}/agent.cordis.yml：compaction 组挂载 + pruner 阈值配置
- ~/.dsh/storages/session_projcache.json：contextWindow=1000000

## 七、待查证

1. dsh-auto-compact 源码（是否复用官方服务缝、256K 阈值是否可配、触发钩子位置）。
2. 手动 /compact 是否受 thresholdRatio 门控（ManualCompactionError 触发条件）。
3. 调低 thresholdRatio 对实时会话的副作用（自动触发时机/摘要中断）。
4. compaction-basic 的 summarizationModel 默认值（空串=跟随主模型？）与摘要成本。

*对比 v0.1 · 数据调查员 · 2026-08-18*
