# awesome-agent-failures Taxonomy → dsh-plugin-reviewer 规则映射

> 映射日期: 2026-09-07 · 规则库 v1.1.0 · 作者 4787d717
> 来源: [vectara/awesome-agent-failures taxonomy.md](https://raw.githubusercontent.com/vectara/awesome-agent-failures/main/docs/taxonomy.md)
> 目的: 把社区归纳的 Agent 运行时失败模式，落成我们审查**承载 Agent 的插件代码**时的静态护栏检查。

## 映射原则

taxonomy 描述的失败发生在 **Agent 运行时行为**层面；而 `reviewer.py` 审查的是**插件源代码**。二者并不一一同构，因此映射采取「**每种失败模式 → 插件代码中应体现的治理护栏构件**」策略：

- **direction = positive**（在源码中命中护栏写法 = 达标 PASS；缺失 = warn 需人工复核）
- **不进 veto_groups**：护栏缺失是「治理缺口」而非「恶意行为」，不应一票否决，但应提示复核（runtime 行为静态无法确诊）
- 与既有的 A-J 安全维度互补：A-J 回答「这个插件会不会害宿主」，K 回答「这个插件承载的 Agent 会不会跑偏」

## 映射表

| taxonomy 失败模式 | 失败本质 | 对应审查护栏(K) | 护栏在源码中的信号示例 | taxonomy 缓解策略 |
|---|---|---|---|---|
| **Tool Hallucination** | 工具输出错误→Agent 据假信息决策 | `K1_tool_hallucination` | cross-check / source-verif / confidence / hallucination detect / double-check | 源核对 + 多独立源交叉 + 置信度阈值 |
| **Response Hallucination** | Agent 把工具输出组合成与事实不符的响应 | `K2_response_hallucination` | fact-check / verif tool output / reconcile / ground truth | 输出与工具结果做事实一致性校验 |
| **Goal Misinterpretation** | 误解意图→优化错误目标、浪费资源 | `K3_goal_clarification` | clarify / confirm intent / ambiguous→ask / human confirm | 人机回路 + 目标分解验证 |
| **Plan Generation Failures** | 计划有缺陷→先做破坏性副作用 | `K4_plan_before_act` | plan-then-act / dry-run / preview / stage-commit / read-then-write | 先确认可行性再执行副作用 |
| **Incorrect Tool Use** | 选错工具/错参数→删除等不可逆后果 | `K5_destructive_confirm`（根治）+ `K4` | confirm-delete / approval / human-in-the-loop gate | 参数 schema 强制 + 破坏性动作人审 |
| **Verification & Termination Failures** | 提前终止或死循环 | `K6_termination_guard` | max-iter/step / timeout / budget / loop-detect / cancel | 进度监控 + 超时 + 明确完成判据 |
| **Prompt Injection** | 恶意输入覆盖系统指令 | `K7_prompt_injection_guard` | instruction-isolate / untrusted-as-data / sys-prompt-boundary | 输入验证 + 指令隔离 + 高风险人审 |

## 与主报告根因的联动

taxonomy 7 类与我们在 [ai-agent-governance-negative-cases-2026](../ai-agent-governance-negative-cases/ai-agent-governance-negative-cases-2026.md) 提炼的六大根因存在映射：
- Incorrect Tool Use / Goal Misinterpretation / Plan Generation → **C1 权限失控、C3 人在回路失效**
- Prompt Injection → **C2 提示注入**（K7 与既有 C2/I 组互补，K7 侧重「指令隔离设计存在性」）
- Verification & Termination → **C6 成本失控**（K6 侧重源码级终止护栏）
- Tool/Response Hallucination → **事实一致性治理**（新增维度，K1/K2）

## 现有规则与 taxonomy 的重叠/边界

| 相关既有规则 | 侧重 | 与 taxonomy 差异 |
|---|---|---|
| `C2_download_exec` / `C1_eval_exec` | 检测恶意代码执行 | 恶意意图检测（negative） |
| `J7_cmd_whitelist` | 命令执行面是否过度开放 | 权限面（negative） |
| `I3/I4/I6` | 会话外传/静默外连 | 数据盗取（negative） |
| **K 组（新增）** | 护栏**设计存在性**（positive） | 治理健康度——不判恶意，判「跑偏防护有没有」 |

## 使用建议

- **第三方 Agent/编排插件**：K 组缺失 3 项以上 → 强烈建议人工复核后再授予执行权限
- **自研 Agent 编排插件**（跳 B/C/H/I/J）：K 组反而应作为重点自检维度（我们自己的 Agent 同样会 Tool Hallucination / 死循环 / 被注入）
- 与人工台账配合：K 命中只是「存在护栏代码」，仍需人确认护栏确实接线到高危动作

## 待扩展（taxonomy 之外）

taxonomy.md 仅 7 类，但 [README](../ai-agent-governance-negative-cases/ai-agent-governance-negative-cases-2026.md) 案例库还暴露了 taxonomy 未单列的失败模式，建议后续补充 K 组：
- 多 Agent 协调失败（互相覆盖/无锁）→ 建议 `K8_coordination_guard`（对应我方 agent_lock 红绿灯）
- 记忆/上下文投毒（MemGhost）→ 建议 `K9_memory_trust`
- 成本/预算硬封顶（$47K 死循环）→ 建议并入 `K6` 强化或 `K10_budget_cap`
- 供应链（skill/MCP 消费端审查）→ **已立项为下一迭代 L 组**，见 `README.md`「下一迭代」与规则文件说明
