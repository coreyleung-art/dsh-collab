# 部件卡 · dsh-web-client（前端应用 / 会话列表 UI 数据链）

> 填卡：2026-09-04 · 依据：官方 subsystems/web-client.md + 首窗空事故实证
> 状态：learned（registry: web-client）

## 1. 一句话定位
浏览器侧 Cordis 应用：独立加载的 client 插件组装；四大基石 = Client Modules(加载图) / API Gateway(typed Host 通信) / Slots(React 组合) / Conversation(会话历史窗口)。本卡聚焦"会话列表/workspace 数据如何到 UI"（首窗空事故的关键域）。

## 2. 概念与定义
- **Browser boot**：Host 写 WebBootGraph 到 `window.__DSH_BOOT__` + 装 module-loader → bundle 注册 factory → cordis Loader 建图 → 全 roster settle 后 ui-renderer hydrate + renderSlot('root')。
- **Remote 通信**：`api-remotes` 把生成的 remote 方法挂到 `ctx.remote.<ns>`；Connection 拥有 request correlation/`/api` carrier/trust/connection generation；Gateway 管 dispatch/stream/event 转发。
- **$events 逻辑流 = generation 源**：opening `ready` 帧带 Host home，**Host listeners 全 attach 后**才建立 generation，然后 controller 才开始 baseline read。
- **ClientWorkspaceModel**（workspace 数据）：owner = 浏览器 rows/order/archived/stream-unary 竞态解决；**每 generation 完整 baseline + upsert/remove/order/archived 增量；reconnect 从新 baseline 替换 model**。
- **SessionManager**：own list baseline、live 更新、冲突排序（pulls vs later updates）。
- **无 monolithic Runtime/resync()**：Connection 暴露 generation 状态，Gateway 管 logical stream 监管，每个 Client model 定义自己的替换/resume 语义。

## 3. 作用与生命周期（首窗空事故的机制解释）
- 数据路径：Host workspace baseline/increments → ClientWorkspaceModel → ctx.workspaces.list → useWorkspaces → sidebar。
- **首窗空机制**：若 Host workspace 服务未就绪/异常(遮蔽) → workspace-controller 的 follow 无有效 baseline 或空 → Client 拿空模型；connection 不再产生新 generation → **UI 保持空不自动更新**。
- **为何 reload 无效、重建窗口有效**：reload = 同 connection 复用（不必然新 generation/新 baseline）；重建 BrowserWindow = 新 connection = 新 generation = 新 baseline（实证：S5fix4 发现 reload 无效/重建有效）。
- **为何遮蔽清理后首窗正常**：host workspace/controller 服务回到 rc.2 健康 → baseline 即时有效（今日实证：27 遮蔽清理后多次重启首窗正常）。

## 4. 约束（红线/不可违）
- 依赖 remote 服务 `remote.fileReferences`/`remote.sessionReferenceResolver` 的 UI(ui-reference) 在服务缺失时 boot pending——禁用治标，根治=服务健康(遮蔽清理)。
- client model 非 business truth——host controller 权威；client 只是 latest usable projection。
- carrier 失败可重试；business error/malformed opening/protocol violation 对所属 logical stream **terminal**。

## 5. 依赖
- client 侧依赖：api-remotes(remote 方法) → Connection($events/trust) → Host(web-server)。ui-workspace 依赖 WorkspaceController(ctx.workspaces)。
- 宿主服务依赖：workspace-controller/session-controller 依赖 workspaceRegistry/sessionPersistence（见 workspace 卡）。

## 6. 规范要点（标准）
- **首窗空诊断**：先查遮蔽(shade_count/guard-check-deps)——host 服务健康是 UI 数据链前提；数据健康后仍空 → 重建窗口(新 generation)。
- 勿用 webContents.reload() 治首窗空（无效）；要重建窗口或等 host 服务就绪。
- 排查 client 问题看 renderer console（--enable-logging=stderr 或 CLD /dom 端点读 innerText）。

## 7. 关联
- 官方文档：web-client.md、client-modules.md、api-gateway(引用)、slots.md、conversation.md
- 工具箱：T1（首窗空）· 路由：OP-restart（竞态 0.3，遮蔽清除后大降）
- 代码：dsh-client-ui-workspace/client.js（model 消费）、dsh-client-connection、dsh-workspace-controller/session-controller
- 观测：guard-eye /dom（读 UI 文本判断"暂无会话"）

## 8. 待补
- workspace-controller follow 在 workspace pending 时的确切行为（空 baseline vs error）——遮蔽清除后难复现。
- UI 是否可加"baseline 空时重试"——属 runtime restricted 区根治点。

## 9. 学-建-用 沉淀
- 2026-09-04：卡毕业——把"首窗空"从现象升到机制(ready帧/generation/baseline/遮蔽)理解；支撑 T1 处置(session_recovery_check→遮蔽→重建窗口)。
