# dsh 官方文档 + 社区类似插件调研报告

> 作者：mac-mini 中枢 ｜ 2026-08-27
> 目的：①dsh 本身官方文档调研（我们引用了哪些方面、官方文档在哪）②社区有没有类似 agent-bus 的工具/插件

---

## 一、dsh 官方文档调研

### 1. 官方文档入口

| 入口 | 地址 | 说明 |
|------|------|------|
| 官网 | [deepseek.com/harness](https://www.deepseek.com/harness/en/) | 「Everything is a Plugin」开发者预览页 |
| GitHub 仓库 | [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) | 开源，MIT，master 分支 |
| 官方文档目录 | [docs/](https://github.com/deepseek-ai/deepseek-harness/tree/master/docs) | 20+ 篇，**中英双语**（.md + .zh.md） |
| Cordis 论文 | A Programming Paradigm for Spatiotemporal Composability | Cordis 内核设计论文 |
| Discord | DeepSeek Harness Discord 社区 | 社区支持 |

### 2. 官方文档结构（docs/ 目录）

```
docs/
├── architecture.md          架构总览
├── capability-seams.md      能力缝 + 核心服务图谱（ctx.* 服务全览）
├── cordis-primer.md         Cordis 入门
├── cordis-api/              Cordis API 参考
├── cordis-tutorial/         Cordis 教程
├── development.md           开发指南
├── agent-lifecycle.md       Agent 生命周期
├── tool-catalog.md          工具目录
├── tool-execution-pipeline.md 工具执行管线
├── config-catalog.md        配置目录
├── event-producer-consumer.md 事件生产消费
├── defensive-patterns.md    防御模式
├── testing.md               测试
├── api-gateway.md           API 网关
├── persistence-catalog.md   持久化目录
├── module-graph.md          模块图
├── graph-atlas.md           图谱
├── postmortem/              事故复盘
├── user/develop/basic/      开发教程（tool.md / plugin 基础）
├── cookbook/                菜谱
└── subsystems/              子系统
```

### 3. 我们 agent-bus 引用的官方文档方面（对照）

| 官方文档 | 我们引用的方面 | 对应源码 |
|---------|--------------|---------|
| user/develop/basic/tool.md | defineTool 工具定义（官方教程与我们用法一致） | dsh-tools |
| cordis-primer / cordis-api | 约定式插件定义 + ctx 生命周期 | cordis |
| capability-seams.md | agents/sessions/tools/webServer 等核心服务 | dsh-agent 等 |
| agent-lifecycle.md | followup 注入（消息如何进会话上下文） | dsh-agent |
| development.md | profile 层插件加载 | dsh-app-boot |

**重要认知**：官方文档在 GitHub master 分支（本地 CLD runtime 的 node_modules 是打包副本，无 README；官方文档是 .md 文件在仓库 docs/ 下）。

---

## 二、社区类似工具/插件调研

### 1. 直接类似（多智能体协作/消息总线）

| 项目 | 定位 | 与我们 agent-bus 对比 |
|------|------|---------------------|
| [dsh-agent-bus](https://www.npmjs.com/package/dsh-agent-bus)（MistyBridge） | **同名**！多智能体编排：会话间分配任务/审查结果/DAG 工作流 | **撞名**。定位：任务编排（DAG）；我们：跨会话消息总线+互斥+档案。依赖 zod + 10 peerDeps |
| [dsh-agent-teams](https://github.com/NanmiCoder/dsh-agent-teams)（@nanmicoder） | AgentTeams：队长+成员+依赖任务+直接消息+Web UI（任务 DAG） | 定位：临时组队协作（subagent 承载）；我们：常驻总线+跨设备。v0.1.13 |
| [dsh-team](https://github.com/huxint/dsh-team)（huxint） | Agent teams：常驻队友+成员邮箱+共享任务+虚拟工作区+2.5D 办公室 UI | 定位：可视化团队协作（ctx.subagents 承载）；我们：宿主级消息总线。v0.2.7 |
| [ruflo](https://github.com/ruvnet/ruflo) | Agent meta-harness：多玩家 swarm 编排 | 更上层（swarm 级），非 dsh 专用 |

### 2. DSH 插件生态基础设施

| 项目 | 用途 |
|------|------|
| dsh-plugin / dsh-plugin-marketplace / dsh-plugins-store | 插件市场（GitHub dsh-plugin topic 聚合） |
| dsh-plugin-studio / dsh-plugin-console / @1e0zj/dsh-plugin-mall | 插件管理/一键安装 |
| create-dsh-plugin | 插件脚手架（秒建插件） |
| dsh-plugin-guide | 插件开发知识库 |

### 3. 官方能力 vs 我们的差异化

**官方提供**（dsh 内置）：
- `ctx.subagents`（子代理——官方多智能体基础）
- workflow（官方工作流编排）
- sessions/agents 服务（会话与智能体注册表）

**社区插件覆盖**（subagent 之上的组队协作）：
- dsh-team / dsh-agent-teams：临时团队 + 任务 DAG + 可视化

**我们 agent-bus 的差异化**（社区没有的）：
1. **宿主级常驻消息总线**（不依赖 subagent 生命周期，独立于会话）
2. **红绿灯互斥锁**（同源资源并发控制——社区无此能力）
3. **能力登记档案**（agent_profile——谁会什么/资源归谁）
4. **跨设备注入**（黑板协议 + central-inbox——社区插件全是单机）
5. **治理**（v2.3 最短提示门禁/审批/受控重启/审计）

---

## 三、结论与建议

### 撞名问题（重要）
npm 已有 `dsh-agent-bus`（MistyBridge，v0.1.1，任务编排定位）——**我们的包名冲突**。建议：
- 方案A：改名（如 `dsh-plugin-agent-bus` 或 `@coreyleung-art/dsh-agent-bus`）
- 方案B：发布到 npm 时用 scoped 名避免覆盖

### 我们的独特价值（社区空白）
社区插件聚焦「临时组队协作」（subagent 之上）；我们做的是**「宿主级常驻通信基建」**（总线+锁+档案+跨设备）——这是社区没有的层次。适合独立发展。

### 建议动作
1. 改名避冲突（scoped 发布）
2. 读官方 `capability-seams.md` 确认我们的服务如何融入官方服务图谱（是否可作为独立 seam）
3. 参考 dsh-team/dsh-agent-teams 的 UI（2.5D 办公室/任务 DAG）补我们面板
4. 用 create-dsh-plugin 规范工程结构（若需要对齐社区标准）

---

*调研时间 2026-08-27 · 来源：deepseek.com/harness / GitHub deepseek-harness docs / npm registry / GitHub dsh-plugin topic*
