# GUI 插件结构说明（session-1e54d56d）—— 供知识库灌入

> 结构级文档：mcp-station / workflow-capture 的架构、模块、API、数据流。配 `~/dsh-collab/gui-plugins-deliverables.md`（功能级）使用。

## 1. dsh-plugin-mcp-station —— MCP 工作站

### Host（`src/index.ts`，构建产物 `lib/index.js`）
```
inject: ['tools','settings','llm','attachments','fs','skills']
apply(ctx):
├─ state: servers{}/order[]/skills{}/vision（内存，进程级）
├─ seedSkills() + importClaudeServers()（读 ~/.claude.json 的 mcpServers 导入种子）
├─ mountServer(id) ── 官方 MCP SDK:
│    StdioClientTransport(command,args,env) → Client.connect →
│    listTools() → 每个工具 tools.register({name:mcp__server__tool, parameters, output, execute})
│    （异步，状态 mounting→running/error；unmount 时 dispose + client.close）
├─ vision_analyze 工具（tools.register）:
│    fs.readBytes → attachments.saveImage → llm.stream({provider,model,content:[image,text]}) → 聚合 text-delta
│    ensureVision() 兜底：读 settings(llm-pi-ai) providers 找视觉模型
├─ DISCOVERY: registries[]（MCP 聚合站）+ picks[]（场景精选）
├─ repo pipeline:
│    connectRepo(url,targetDir,actions) → runRepoJob:
│      git clone --depth 1 → detectType(package.json/pyproject/go.mod/Cargo.toml) →
│      install(npm/pip/go) → build(npm run build 等)；runCmd 用 child_process.spawn 收集输出
├─ webServer 路由 /mcp-station/api/*:
│    state | mount | unmount | import | remove | refresh | vision | discover |
│    repo/connect | repo/list | repo/status
└─ 生命周期: ctx.on('internal/service') 等 webServer；ctx.effect 清理
```

### Client（`src/client/index.tsx`，构建产物 `lib/client.js`，__ModuleLoader__.load 格式）
```
apply(ctx):
├─ slots.register('sidebar.footer.action', SidebarEntry) —— 统一"⚡ 工具"启动器:
│    Button + Menu（官方 primitives）：MCP 工作站 / 工作流捕获 / 刷新数据
│    跨插件协作: window.dispatchEvent(new CustomEvent('workflow-capture:open'))
├─ Drawer（createPortal → document.body，fixed 左侧抽屉）:
│    仓库一键连接 / MCP 挂载 / 技能 / 多模态桥 / 发现 MCP
│    错误边界 MsErrorBoundary + 诊断徽标（window.onerror）
└─ 数据: fetch('/mcp-station/api/*')；共享 store（模块级 shared + subscribe/emit）
```

## 2. dsh-plugin-workflow-capture —— 工作流捕获器

### Host（`src/index.ts`）
```
inject: ['tools']
apply(ctx):
├─ 捕获: ctx.on('tools/result') → record(exec):
│    排除 NOISE_TOOLS（read/glob/grep/web_search 等只读探测）
│    动作 = {tool, fp(参数指纹 sha256), summary, args} 按 agent 分序列（上限 300）
├─ 挖掘: mine(agentId) —— 滑动窗口 w=3..6 统计重复子序列，count≥2 → candidates
├─ promote(key) → runbook（保存真实参数，可 {{key}} 插值）→ runbooks Map
├─ run_workflow 工具（tools.register）: 按 runbook steps 逐个 tools.execute 重放
├─ cron 调度器:
│    cronMatches(5段: 分 时 日 月 周) + nextCronTime（往后扫 24h）
│    setInterval 30s schedulerTick → 到点跑 runbook，记录 history（最近 500）
├─ 持久化 ~/.dsh/workflow-capture/: runbooks.json / tasks.json / history.json / sequence-log.json
└─ webServer 路由 /workflow-capture/api/*:
     state | promote | delete | run | tasks | tasks/toggle | tasks/delete
```

### Client（`src/client/index.tsx`）
```
apply(ctx):
├─ slots.register('sidebar.footer.action', WfEntry) —— 不渲染按钮，仅挂载监听:
│    window.addEventListener('workflow-capture:open') → 打开抽屉（由 mcp-station 启动器触发）
├─ WfDrawer（createPortal → body）:
│    候选工作流（重复≥2，一键工具化）/ 已工具化 runbook（运行/删除/结果）
│    自动化任务（选 runbook + cron 5 段 + 创建；启用/停用/删除；下次执行/上次结果）
│    执行历史
└─ fetch('/workflow-capture/api/*')
```

## 关键经验（灌库要点）
1. **官方 MCP 对接**：StdioClientTransport + Client.connect + listTools + register，比手写 JSON-RPC 稳；断线由 SDK 管理
2. **TS→esbuild 插件管线**：tsc 编 host（lib/index.js）+ esbuild 编 client（CJS bundle 包成 `window.__ModuleLoader__.load({id, factory})`）→ profile/package.json `dsh.profile.bundles` 加 link 插件 → CLD 重启扫描
3. **client 三坑**：React/host/styles 是闭包参数（非 ctx.get）；抽屉必须 createPortal 到 body（fixed 不被 sidebar transform 裁剪）；加错误边界防整树冻结
4. **无 uvx/npx 装 MCP**：npm 全局装 TS 官方服务器（/opt/homebrew/Cellar/node/*/bin）；PyPI venv 装 Python 服务器；官方 servers 已弃 Python 迁 TS
5. **cron 调度在 Host 端**（进程级 setInterval），比浏览器端可靠（关页面不失效）
