# 部件卡 · dsh-system-prompt（系统提示组装）

> 填卡：2026-09-05 · 依据：官方 subsystems/system-prompt.md
> 状态：learned（registry: system-prompt）

## 1. 一句话定位
[ctx.systemPrompt] own prompt contributor 与单次 assembly 间交换的数据：PromptSection(静态/按 assembly context 求值) + PromptContext(动态，作为持久 user-role snapshot)。contributor 注册→assembly 排序拼装。

## 2. 概念与定义
- **AssembleContext**：{scope?(决定哪些 provider/waterfall 参与), signal?(该 turn 控制信号)} merge-extensible(dsh-agent 加 agent)；assembleContextFor(agent,signal)。bare assembly=无 scope 无 signal。
- **ToolProviderResult**：{schemas(本次 assembly model 可见), knownNames?(pre-restriction 名全集——区分配置拼写错 vs 故意隐藏)}。
- **PromptSection**：{name(重复注册 throw), order(升序拼接，同序按 code-unit name), text(static|(ctx)=>string, 可含 {{variable}} 后由 renderPrompt 插值), complete?(把本 contribution 当完整 system prompt——assembly 仍跑 waterfall 解析 tools/contexts/variables 后**恢复此 section 为唯一**；>1 complete 生效 → assembly fail)}。
- **PromptContext**：{name(重复 throw), order, text(static|provider, 空文本不贡献)}——cache-safe 对应物；agent-loop 只在变化或 compaction 移除后把完整当前 snapshot 记入日志(retained history 之后)。
- **排序分配**：仓库 contributor 用 getSectionOrder()；runtime-context 用 getContextOrder()。

## 3. 作用与生命周期
plugin 注册 section/context → 每 turn assembly(带 scope/signal) → waterfall(tools/contexts/variables) → 排序渲染 → 完整 system prompt。dynamic context 变更才 append snapshot(省日志)。

## 4. 约束（红线/不可违）
- 重复 name throw；>1 complete fail。
- section 由 service 定序(勿自造 order 冲突)。
- 本环境实证：tool schema 进 system prompt 白名单(tools.md schemas()) 与这里衔接；missing output/参数泄漏等 tool 契约问题会体现在 prompt 层。

## 5. 依赖
- 被依赖 agent-loop(每 turn 组装)；依赖 tools(schemas)/scope。contributor = 各能力插件。

## 6. 规范要点（标准）
- 加能力文案(系统提示) → 注册 PromptSection(有序)或 PromptContext(动态)；勿改官方 prompt 字符串(用层序 patch 或新 section)。
- 诊断"模型看不到某工具/行为"：查 ToolProviderResult.schemas 白名单 + restriction(scope 卡)。

## 7. 关联
- 官方：system-prompt.md · 工具箱：— · 路由：—
- 代码：dsh-system-prompt/lib；agent 总线/技能类插件是其 contributor。

## 8. 待补
- renderPrompt 插值语法详情。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
