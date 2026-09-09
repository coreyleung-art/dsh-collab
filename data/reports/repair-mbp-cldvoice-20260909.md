# MBP dsh-plugin-cldvoice 崩溃修复报告

> 2026-09-09 · 星桥(mac-mini)远程修复 · 接收方: mbp-ops / mbp-bus / 明鉴(插件作者)
> 现象: CLD 装 voice 插件后重启 boot 失败 —— "Timed out waiting for dsh web to announce its URL (120000ms)"

## 一、根因（三层叠加，逐层剥离）

| # | 报错 | 根因 | 位置 |
|---|------|------|------|
| ① | cannot get property "services" without inject | `inject=[]` 却在 apply 里读 `ctx.services`(Cordis 3 属性访问须声明 inject) | lib/index.js apply |
| ② | webServer.route is not a function | webserver 服务无 `.route()` API——正确为 `webServer.register({kind,path,handler})`(返回 disposer) | apply 内两处路由注册 |
| ③ | declares dsh.client but exports no "./client" bundle | package.json `dsh.client` 声明了 web client 却无对应 bundle → client-modules 抛错 → boot 中断 | package.json |

三层任一层都足以让 boot 失败(dsh web 永不 announce → 120s 超时)。

## 二、修复（已应用到 MBP 安装副本）

**文件: `~/.dsh/profiles/web/node_modules/dsh-plugin-cldvoice/lib/index.js`**
- `inject` 改为 `['webServer']`，apply 内 `const webServer = ctx.webServer;`（弃 ctx.services）
- 两处路由从 `webServer.route('POST'|'GET', path, handler)` 改写为规范形态：
  ```js
  ctx.effect(() => webServer.register({
    kind: "exact", path: "/voice/draft",
    handler: async (req, res) => { /* 原逻辑 + method 守卫 */ }
  }), "cldvoice: POST /voice/draft");
  ```
  （对照先例：`@deepseek-ai/dsh-client-connection` 的 `ctx.webServer.register` + `ctx.effect` 包裹；kind ∈ exact|prefix）
- /voice/health 同法注册

**文件: `package.json`**
- 移除 `dsh.client` 声明块（cordis.patch.yml 本就只挂 host 端 id=cldvoice，client 声明为无实现残留）
- 若将来要 client 半场(全双工 UI 注入会话)，须真正实现 `./client` bundle + exports 映射 + patch client 行

## 三、验证
- 每层修复后 node --check 语法通过
- 远程重启 MBP CLD ×3（逐层确认错误推进：services→route→client → 无错）
- 最终 boot 日志仅剩无害 TSM/IMK 提示；**用户确认 MBP CLD 可正常打开** ✅

## 四、对插件作者(mbp-bus/明鉴)的回写要求
以上仅修 MBP 安装副本——**请回写插件源仓库/发布包**，否则重装/他机部署必重现三层问题。建议修复清单：
1. `inject: ['webServer']` + `ctx.webServer`（禁 ctx.services）
2. 路由改 `webServer.register({kind:'exact',path,handler})`（无 `.route`）
3. `dsh.client` 与 bundle 二选一：实现真 client bundle 或移除声明
4. 补: handler 内 method 守卫

## 五、影响与后续
- mac-mini 无 dsh-plugin-cldvoice(用 dsh-plugin-voice)，不受影响不复发
- 语音全双工插件线归 MBP 侧；R3/R4(语音笔记/静默会议助手)按用户分工待 MBP 全栈完成后接入
- 修复记录存: ~/dsh-collab/data/reports/repair-mbp-cldvoice-20260909.md
