# agent-bus · 官方文档关联清单

> 说明：DSH/CLD 的官方文档以**源码内 JSDoc 注释 + 包内类型定义（.d.ts）** 形态存在于
> `/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/`。
> 本文档列出 agent-bus 开发中**实际引用**的官方文档方面（按依赖的官方 API 逐项映射）。

---

## 一、直接引用的官方包（import/依赖）

| 官方包 | 版本 | agent-bus 引用方式 | 引用的官方 API 文档 |
|--------|------|-------------------|---------------------|
| @deepseek-ai/dsh-tools | 0.1.0-rc.6 | `import { defineTool }` | **defineTool 工具定义 API**（name/description/schema/execute/timeoutMs/output 渲染） |
| @deepseek-ai/cordis | 4.0.1 | peer 依赖（宿主提供） | **插件定义**（约定式 `export name/inject/apply`）、**ctx 生命周期**（provide/inject/effect/on） |
| @deepseek-ai/dsh-client-runtime | 0.1.0-rc.6 | peer 依赖（client 注入） | client 运行时（client.js 注入） |

## 二、间接引用的官方包（通过宿主服务）

| 官方包 | agent-bus 使用的宿主服务 | 引用的官方 API 文档 |
|--------|------------------------|---------------------|
| dsh-agent | `ctx.get('agents')` → `agents.get(to).followup()` | **agents 服务 + followup 注入 API**（跨会话消息注入核心） |
| dsh-session | 会话事件模型（followup 的 source.kind=agent-bus） | **会话事件结构**（消息 content/source 格式） |
| dsh-tools | `ctx.get('tools')` → `ctx.tools.register()` | **工具注册服务**（register 工具定义到宿主） |
| dsh-app-boot | profile 加载（插件如何被宿主加载） | **loadProfile / resolveBundleDir / initProfile / PROFILE_TEMPLATES**（profile 层组合机制） |
| dsh-tool-cordis | 动态插件环境（i9 侧评估用） | **cordis_define / cordis_run / isolate realm**（动态插件定义与运行） |
| dsh-web-app / dsh-headless | profile 模板（web 组合含 agents 服务） | **PROFILE_TEMPLATES**（web = [dsh-base, dsh-web-app]） |

## 三、按「官方文档方面」归类（agent-bus 实际用了什么）

### 1. 插件开发规范（官方：dsh-tool-cordis + cordis）
- 插件定义形态：**约定式** `export const name / export const inject / export function apply(ctx)`
- 教训引用：cordis 4.x 移除 `definePlugin`（官方文档注明）→ 必须用约定式
- 工具定义：`defineTool({ name, description, schema, execute })`（dsh-tools JSDoc）

### 2. ctx 生命周期与服务注册（官方：cordis）
- `ctx.get('service')`：读取可选服务（agent-bus 用 `ctx.get('agents'/'tools'/'webServer'/'systemPrompt'/...)`）
- `ctx.provide('agentBus', {...})`：注册服务供其他插件注入（central-inbox 依赖）
- `ctx.effect(disposer)`：副作用生命周期（工具注册的清理）
- `ctx.on(event)`：事件监听

### 3. agents 服务与消息注入（官方：dsh-agent）
- `agents.get(sessionId)` → 获取目标会话 agent 对象
- `agent.followup({ id, role, source, content })` → **注入消息到目标会话上下文**（下轮自动看到）
- source.kind = 'agent-bus'（标记注入来源，官方事件溯源）

### 4. profile 层插件加载（官方：dsh-app-boot）
- 插件必须：①双锚点可解析（installAnchor/profileDir）②profile `dsh.profile.bundles` 列出 ③声明 `dsh.bundle.patch`
- 首次使用自动初始化（loadProfile → initProfile → PROFILE_TEMPLATES）
- 官方安装入口：`dsh plugin --profile web add <pkg>`（转 pnpm）

### 5. 工具注册（官方：dsh-tools）
- `ctx.tools.register(defineTool({...}))` 注册 19 个 agent_* 工具
- 工具 schema 校验（官方 JsonSchema）

### 6. webServer API（官方：dsh-host-webserver）
- `ws.register({kind:'prefix', path, handler})`（注：官方是 ws.register 不是 webServer.get）
- agent-bus 面板 `/agent-bus/api/*` 注册

### 7. 系统提示词注入（官方：dsh-system-prompt）
- `ctx.get('systemPrompt')` → 注入 REPORT_PROMPT（迭代报告纪律）+ 红绿灯前置

## 四、i9 侧引用的官方文档方面（架构评估）

| 方面 | 官方文档来源 | 结论 |
|------|-------------|------|
| CLD 壳启动参数 | app.asar（spawnDsh: `dshArgs=[--expose-internals, bin.js, web, --port, 0]`） | 所有 CLD 应带 web profile |
| headless agents 能力 | dsh-headless（inject=[agentDefaultModel, agents, sessions] + agent.followup） | headless 也有注入能力 |
| 动态插件限制 | dsh-tool-cordis（Builtin 仅 ctx/harness/console/...） | 会话级动态插件无 fetch/fs |
| 官方插件入口 | dsh bin.js（program.command('plugin')） | `dsh plugin --profile web add` 可解 i9 |

## 五、官方文档形态说明

DSH/CLD 的官方文档**不是独立 .md 文件**，而是以：
1. **源码 JSDoc 注释**（如 dsh-tools defineTool、dsh-app-boot loadProfile 的完整注释）
2. **包内 .d.ts 类型定义**（dsh-llm/dsh-session 的 lib/types/）
3. **打包产物注释**（cordis lib/index.js 顶部区域注释）
4. **app.asar 壳代码注释**（CLD 壳的 spawnDsh/profile 逻辑）

这 4 种形态共同构成 agent-bus 引用的「官方文档」。本机知识库已沉淀 3 篇机制条目：
- 「CLD 插件加载机制：profile 层组合」
- 「CLD 插件加载完整机制与 bundles 注册」
- 「agent-bus 原理」

---

*本清单由 agent-bus v1.0.0 源码 + runtime 官方包逐项核对生成（2026-08-27）。*
