# 总线微调专用 Prompt —— HR 驾驶舱模式（preset 微调指令）

> 用途：交给 Agent Bus / DSH 框架（或支持 preset 微调的模型），按此规范生成/注册「HR 驾驶舱模式」preset。
> 版本：v1.0.207 · 2026-08-18 · 微调完成后用「角色 Prompt」激活新会话。
> 原理：preset = preset.yml（注册元数据）+ agent.cordis.yml（persona + 工具面组合）+ 可选 mjs 增强。

---

## 任务

在 `~/.dsh/.agent-presets/` 下创建（或覆盖）preset 目录 `resource-manager`，组成「HR 驾驶舱模式」专用 preset，供多智能体协作网络的资源管理者（HR）角色使用。

## 一、preset.yml（注册元数据）

```yaml
name: HR 驾驶舱模式
description: 专职资源管理者（HR Cockpit）：多智能体网络资源中枢——档案登记、能力匹配、冲突仲裁、锁审计、token/算力成本管理、冲突治理、模式评估、异步审批队列。基于梁神模式微调（保留两阶段锚定 + 模型回退 + 持久 shell），persona 注入 HR 驾驶舱 6 仪表 + 8 硬性纪律。绝不碰代码开发与 GUI 插件开发。
order: 6
```

## 二、agent.cordis.yml（组合文件）

### 2.1 工具面（必须完整保留 liangshen 的 18 节点，缺一不可）

| 节点 id | 来源 | 作用 |
|---|---|---|
| persona | @deepseek-ai/dsh-persona | 角色身份（内容见第三节角色 Prompt） |
| model-fallback | ./model-fallback.mjs | 模型回退（复制 liangshen 同名文件） |
| tool-bootstrap | ./tool-bootstrap.mjs | 两阶段锚定（复制 liangshen 同名文件） |
| agent-instructions | @deepseek-ai/dsh-agent-instructions | 工作区指令 |
| persistent-shell | cordis:group（terminals 隔离） | 持久 bash（PTY + terminal-bash + persistent-bash 三子行） |
| str-replace-editor | @deepseek-ai/dsh-tool-str-replace-editor | 阶段一编辑器（继承宿主沙箱） |
| tool-fs | @deepseek-ai/dsh-tool-fs | 文件工具 |
| tool-fs-search | @deepseek-ai/dsh-tool-fs-search | 文件搜索 |
| tool-jobs | @deepseek-ai/dsh-tool-jobs | 后台任务 |
| skill-filesystem | @deepseek-ai/dsh-skill-filesystem | 技能（本地根发现） |
| tool-skill | @deepseek-ai/dsh-tool-skill | 技能目录 |
| tool-goal | @deepseek-ai/dsh-tool-goal | 目标工具 |
| planning | cordis:group（planMode 隔离） | 计划模式（含 plan-mode 子行） |
| compaction | cordis:group（compaction 隔离） | 上下文压缩（compaction-basic 子行） |
| delegation | cordis:group（workflowEngine 隔离） | 子代理委派（subagent/fork/workflow/ralph 8 子行） |
| tool-ask-user | @deepseek-ai/dsh-tool-ask-user | 用户提问 |
| tool-todo | @deepseek-ai/dsh-tool-todo | 待办工具（allowParallelInProgress: true） |
| tool-web | @deepseek-ai/dsh-tool-web | 网页（fetch: false, searchTimeoutMs: 60000） |

### 2.2 增强文件（复制自 liangshen）

- `model-fallback.mjs`（1448B）——主模型失败自动切备用
- `tool-bootstrap.mjs`（15113B）——两阶段锚定（anchorGate + 4 步兜底 + promoteAfterFirstResponse + bootstrapMaxTokens 1024 + deferredSources: [agent-instructions, skill-catalog] + promotedPresentation: code）

### 2.3 NOTICE（来源声明）

```
agent.cordis.yml 改编自 DeepSeek Harness 内置 Minimal 与 Standard preset + liangshen（梁神模式）preset（MIT）。
tool-bootstrap.mjs / model-fallback.mjs 来自 ~/.dsh/.agent-presets/liangshen/（dsh-liangshen 插件维护，MIT）。
配套插件：dsh-plugin-hr（~/dsh-plugin-hr/，侧边栏资源看板 + dock 面板）。
原始 DeepSeek 版权和 MIT 许可声明见开源仓库。
```

## 三、微调校验清单（完成后逐项核对）

- [ ] `~/.dsh/.agent-presets/resource-manager/` 含 5 文件：preset.yml / agent.cordis.yml / model-fallback.mjs / tool-bootstrap.mjs / NOTICE
- [ ] agent.cordis.yml 节点数 = 18（与 liangshen 完全一致，`grep -c "^- id:"` 验证）
- [ ] persona 内容 = 第三节「角色 Prompt」全文（含 6 仪表 + 8 纪律 + 5 工具 + 权威文档）
- [ ] preset.yml order=6（与 liangshen 4 / librarian 5 / waimai-ops 并列，出现在新建会话选择器）
- [ ] 两阶段锚定生效：新会话首轮只见 bash + str_replace_editor，晋升后全工具
- [ ] 配套插件 dsh-plugin-hr 已挂载 profiles/web（link 依赖 + node_modules 软链 + cordis.patch.yml 注入）

## 四、激活方式（微调完成后）

1. **推荐**：新建会话 → 选择器选「HR 驾驶舱模式」（order=6）→ persona 自动注入
2. **等价通道**：新建空会话（无产出）→ AgentPresets.recompose(agentCtx, 'resource-manager') 运行时切换
3. 会话启动后按 `~/dsh-collab/hr-handover-protocol.md` 7 步清单领回 HR 角色（拉线程/读文档/接管登记表/更新档案/旧会话归档/协调者确认）

---

*微调规范 v1.0.207 · 完成后用角色 Prompt 激活新会话*
