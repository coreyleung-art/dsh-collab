# 部件卡 · dsh-web-server（HTTP 载体 / 路由注册表）

> 填卡：2026-09-05 · 依据：官方 subsystems/web-server.md + web.md + 实证(31888 壳端点)
> 状态：learned（registry: web-server）

## 1. 一句话定位
[dsh-host-webserver] GUI host 的浏览器 HTTP 载体：单 `node:http` 插件提供 `ctx.webServer`（命名路由注册表 + 可选 gzip + index.html transform + 一个可被认领的 fallback handler）。**非 agent-loop、非 capability seam、不识 harness 概念**——每条功能路由(含 /api bridge/插件 bundle/HMR)由别的插件注册。**只服务浏览器：Electron 走 file:// + IPC bridge 不用此 server**。

## 2. 概念与定义
- **Route**：{kind:'exact'|'prefix', path(无尾斜杠绝对路径), handler(own 全响应生命周期, 可 SSE 挂起)}。
- **匹配序固定**：exact 表 → 最长 prefix → fallback。注册序无语义(命名路由 disjoint)；fallback 单 owner, 二次注册 throw。
- **Config**：host 仅 '127.0.0.1'(默认姿态)|'0.0.0.0'(有意网络暴露)；port 0=OS 分配；compression none|gzip(默认 none, shipped web 选 gzip level1/1024B)。**载体自身无 TLS/auth/Origin**——非 loopback 绑定即暴露除非组合提供控制；dsh web 拒 --host 0.0.0.0。
- **listen 立即**：EADDRINUSE 等失败 → init 拒 → boot 报 failed fiber。
- **register(route)** 返回 disposer；重复 (kind,path) throw=composition 契约冲突。
- **collectIndexInjections/renderIndex**：IndexInjection 行 → 渲染进 root/index 响应（boot manifest）；tapIndex 逃生舱变换按注册序。
- 异常安全：handler throw → log warn + 400（或 headers 已出则 destroy socket），绝不进程退出。Disposal 用 close()+closeAllConnections()（SSE 连接不会自终）。

## 3. 作用与生命周期
shipped Web 组合：Connection 插件认领 fallback seat(dsh-host-frontend-static, SPA dist, 锁定语义: dist root/index 先鉴权再读, 非 index 资产公开, 非 GET/HEAD 405, 出 root 403, 缺文件空404, 未知扩展 octet-stream)。feature routes 由各插件注册(dsh-client-connection 注 /api bridge + /api/events.* upgrade)。

## 4. 约束（红线/不可违）
- 非 loopback 绑定无 auth=裸奔（host 白名单化：web-runtime trustedHosts 只在 /api 层）。
- 路由重复注册 throw——两插件抢同一 path = misconfig。
- CLD 壳的管理端点(31888 /dom /shot /health)是**壳自建** node:http，非本 server——改壳不涉 runtime webServer。

## 5. 依赖
- 被依赖：所有需 HTTP/WS 面的插件(connection/static/frontend)。依赖：node:http。IndexInjection 由 dsh-client-modules 应答。

## 6. 规范要点（标准）
- 诊断"web 起不来/某路由 404"：先分 壳(31888) vs dsh webServer(dsh web 端口)；路由 404 = 注册方未 init(见 client-connection /api 需 apiProxy)。
- WS 路径(/api/events.mux|host)与 HTTP(/api bridge)是不同路由表(upgrades Map vs routes)——测错路径得出错结论(实证教训)。

## 7. 关联
- 官方文档：web-server.md、web.md · 工具箱：T5 · 路由：无
- 代码：dsh-host-webserver/lib、dsh-host-frontend-static
- 知识：web-client(connection/remote)、client-connection(apiProxy 依赖) 卡

## 8. 待补
- browser-trust fence 精确实现(trustedHosts vs loopback 默认)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业；钉死"WS hang up 误判"(测错路径)教训的理论依据。
