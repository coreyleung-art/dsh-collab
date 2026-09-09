# GUI 插件交付物（session-1e54d56d · GUI 插件开发）—— 协作成果落盘

> 落盘时间：2026-08-16 · 遵循 dsh-collab 约定 v1 · 同源操作遵循红绿灯协议

## 交付物清单

### 1. dsh-plugin-mcp-station —— MCP 工作站
- **路径**：`~/dsh-plugin-mcp-station/`（源码 `src/`，构建产物 `lib/`）
- **功能**：
  - MCP 服务器挂载/卸载（官方 MCP SDK，stdio），工具自动注册进 agent 工具集（`mcp__<server>__<tool>`）
  - `vision_analyze` 多模态桥：图像 → 独立视觉模型（LM Studio / llm-pi-ai provider），无需手动切换模型
  - 仓库一键连接：GitHub/Gitee URL → 克隆 + 识别类型（node/python/go/rust）+ 装依赖 + 构建验证
  - MCP 发现目录（聚合站 + 场景精选）
  - 侧边栏"⚡ 工具"启动器（菜单：工作站 / 工作流 / 刷新）
- **API**：`/mcp-station/api/state|mount|unmount|import|remove|refresh|vision|repo/connect|repo/list|repo/status|discover`

### 2. dsh-plugin-workflow-capture —— 工作流捕获器
- **路径**：`~/dsh-plugin-workflow-capture/`（源码 `src/`，构建产物 `lib/`）
- **功能**：
  - 监听 `tools/result` 事件，捕获工具调用序列（排除只读探测类）
  - 滑动窗口挖掘重复 ≥2 次的子序列 → 候选工作流
  - 一键"工具化" → runbook（保存真实参数，`{{key}}` 插值）
  - `run_workflow` 工具：agent 可直接重放 runbook
  - Host 端 cron 调度器（5 段 cron，进程级定时，关浏览器也执行）+ 执行历史
- **数据**：`~/.dsh/workflow-capture/`（runbooks.json / tasks.json / history.json / sequence-log.json）
- **API**：`/workflow-capture/api/state|promote|delete|run|tasks|tasks/toggle|tasks/delete`

### 3. MCP 生态（已挂载验证）
- obsidian-server / chroma-server（用户自建脚本，`~/.claude/mcp-servers/`）
- filesystem / memory（官方 TS 版，npm 安装于 `/opt/homebrew/Cellar/node/25.9.0_2/bin/`）
- obsidian-rag（PyPI venv `~/.claude/mcp-servers-venv/`，LM Studio 嵌入 `text-embedding-nomic-embed-text-v1.5`）
- 配置源：`~/.claude.json` 的 `mcpServers`（工作站启动时自动导入）

## 经验沉淀（可检索）
- 无 uvx/npx 环境的 MCP 安装路径：npm 全局装 TS 官方服务器；PyPI venv 装 Python 服务器
- 官方 modelcontextprotocol/servers 已从 Python 迁移到 TypeScript；sqlite/brave-search 已移除
- 本地插件管线：TS → tsc + esbuild（`__ModuleLoader__.load` 包装）→ profile bundles（`~/.dsh/profiles/web/package.json` dsh.profile.bundles + symlink）

## 环境依赖
- node/npm：`/opt/homebrew/bin`（Cellar node 25.9.0_2）
- python3.13：`/opt/homebrew/bin/python3.13`
- 无 uvx / 无 npx（PATH）/ 无 docker
