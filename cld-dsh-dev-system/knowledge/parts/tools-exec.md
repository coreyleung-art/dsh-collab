# 部件卡 · dsh-tools（工具定义 / schema DSL / 执行管线）

> 填卡：2026-09-05 · 依据：官方 subsystems/tools.md 全文 + dsh-plugin-guard 开发实证
> 状态：learned（registry: tools-exec）

## 1. 一句话定位
工具注册表 + 调度管线：`ToolDefinition` = ToolSchema(模型可见) + **mandatory canonical output 声明** + execute + 可选 finalizeContent/UI presenters；`ctx.tools` ToolRuntime；执行走 extensible waterfalls + monotonic policy。

## 2. 概念与定义
- **ToolDefinition**：name/description/parameters(模型面) + **output: ToolOutputDefinition(mandatory)** + execute + finalizeContent?/timeoutMs?/isConcurrencySafe?/presentCall?/presentResult?。
- **schemas() 白名单**：output/execute/finalizeContent/timeoutMs/isConcurrencySafe/presentCall/presentResult **绝不 leak 进模型请求**。
- **ToolOutputDefinition**：{schema(raw JSON Schema, 对每个成功 canonical value 强制), render(args,value)→ContentBlock[](纯投影), presentationMeta?}。
- **execute 契约**：返回**唯一 canonical lossless-JSON value**；async 须 observe/forward `exec.signal` 并到 quiescence 才 settle；registry 保留调用方取消（signal 替换），**无法硬杀同进程代码**。
- **defineTool**：校验并 narrow args、从 output.schema 推断 body 返回、给两个 output projector 定型——一方的工具不手写校验。
- **finalizeContent**：同步 last-mile 变换；execution 启动时快照、每个 normalized outcome 恰调一次(含绕过 post-execute 的 pipeline 失败)；必须 total 不 throw；返回 undefined=保留。
- **schema DSL(ValueSchemaSpec)**：string/number/integer/boolean/null/array/object/author-only json/exact-one oneOf；scalar enum/const 须匹配类型；**object 节点显式 additionalProperties: true|false**；parameter 定义是隐式开放 object map，required 逐属性 `required:true` 附上。
- **ToolRestriction**：scope 的 live filter（继承过滤，见 scope 卡）。
- **Waterfalls**：tools/pre-execute → tools/execute → tools/post-execute → (ptc-dispatch-log)；monotonic policy（approval/permission gate 挂 pre/post）。

## 3. 作用与生命周期
注册：apply(ctx) 里 ctx.tools.register(tool)（effect，卸载回卷）。调度：loop 收模型 tool_call → 校验/waterfall/execute → canonical value → render → ContentBlock 进会话。presentCall/presentResult 供 UI 直播+回放（须纯、只依赖 args/result）。

## 4. 约束（红线/不可违——全被 guard 插件实证踩过）
- **缺 output → "reading 'render'" 崩加载**（dsh-plugin-guard v0.1 教训）——output 是 mandatory。
- **schema object 缺 additionalProperties 显式 → JsonSchemaError**（v0.2 冒烟当场抓出）。
- required 用逐属性 `required:true`（勿用 zod .required() 内联——gov schema 教训）。
- schemas() 白名单防 metadata leak——output 等勿进 parameters。
- execute 可 async（框架 await，见 lib/types/index.js 942 行实证）。

## 5. 依赖
- ctx.tools 依赖 scope(注册归属)；执行依赖 approval/sandbox policy(pre/post waterfall)；present 依赖 UI 词汇。被依赖：agent-loop(调度)、模型。

## 6. 规范要点（标准）
- 新 host 工具插件模板：defineTool + output:makeOutput() + object 参数加 additionalProperties + mock-ctx 冒烟注册 + 真执行冒烟。（dsh-plugin-guard 全套流程即标准）
- guard_check_writable 等门禁工具 = pre-execute policy 的 agent 面实现。

## 7. 关联
- 官方文档：tools.md · 工具箱：T4（插件报错）· 路由：OP-add-plugin-host
- 代码：dsh-tools/lib（types/index.js 870-1129 waterfall/execute）、dsh-tool-*
- 产物：dsh-plugin-guard（9 工具 = 本卡标准的活实例）

## 8. 待补
- timeoutMs 合作式超时与 exec.signal 转发的完整契约（tool-call-timeout-policy）。
- parallel group(isConcurrencySafe) 的实际使用案例。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业——把 guard 插件开发中踩的 render/schema 坑从"报错"升到"契约"理解；模板标准已固化在 dsh-plugin-guard。
