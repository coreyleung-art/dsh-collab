# DSH 插件开发常见坑（实测沉淀）

> GUI 插件开发 1e54d56d · 2026-08-27 起累积 · 每次踩坑即补充

## 坑 1：cordis 插件导出方式（export default vs 命名导出）

**症状**：bundle 注册成功但 host/client apply 从未执行（零加载痕迹）。

**根因**：DSH cordis 插件机制要求**命名导出**：
- host: `export function apply(ctx, config)` + `export const name` + `export const inject = ['webServer']`
- client: `export { apply, inject }`（inject 声明依赖 slot）
- 用 `export default plugin`（对象含 name/version/apply）不生效——apply 从未被调用。

**修复**：改为命名导出；client 需 `ctx.slots.inject('sidebar.footer.action', () => ctx.slots.register({name, id, order, label}, Component))` 注册入口。

## 坑 2：webServer API 注册方式（webServer.get vs ws.register）

**症状**：host apply 有执行痕迹但 API 路由不生效（/api/xxx 返回 SPA 兜底 HTML 200）。

**根因**：DSH webServer 只有 `ws.register({kind: 'prefix', path, handler})` 接口，**没有 `.get(path, handler)`**。用 `typeof webServer.get === 'function'` 判断为 false → if 块静默跳过 → 路由未注册。

**修复**（对照 mcp-station 实证）：
```ts
const ws = ctx.get('webServer', false);
ws.register({
  kind: 'prefix',
  path: PREFIX,  // 如 '/flower-cockpit'
  handler: async (req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const p = url.pathname;
    if (p === PREFIX + '/api/state' && req.method === 'GET') { json(res, 200, {...}); return; }
    // ... 各路由分派
    json(res, 404, { ok: false, error: 'not found: ' + p });
  },
});
```
- 必须加 `hostAllowed(req)` 防护（127.0.0.1/localhost/内网）
- 加 `logger.info('[name] host ready')` 痕迹，避免静默失败

## 坑 3：ESM vs CJS（type:module 冲突）

**症状**：lib/*.js 是 ESM（import/export）但宿主 require 失败。

**根因**：DSH 静态插件管线（tsc+esbuild）产出 CJS；package.json 若带 `"type": "module"` 且 lib 文件是 ESM 语法会加载失败。

**修复**：package.json 去 type:module（默认 CJS）；源码经 tsc 编译为 CJS（require/exports）；client 用 esbuild --format=cjs + __ModuleLoader__.load 包装。

## 坑 4：cordis.patch.yml 格式（insert vs patch.add）

**症状**：bundle 注册了但插件不生效。

**根因**：profile bundle 机制消费 `- insert: - id/name/config` 格式（对照 mcp-station）；写成 `patch: - add: - path: plugins` 不匹配。

**修复**：统一用：
```yaml
- insert:
    - id: my-plugin
      name: dsh-plugin-my-plugin
      config: {}
```

## 坑 5：client 构建产物 exports（esbuild 版本差异）

**症状**：client.js 无 `exports.apply`（esbuild 0.28 不自动生成 __export）。

**修复**：ModuleLoader 包装后手动追加：
```js
exports.apply = typeof apply !== 'undefined' ? apply : undefined;
exports.inject = typeof inject !== 'undefined' ? inject : undefined;
```

## 验证清单（每次接入新插件）

1. host/client 命名导出确认（apply/name/inject）
2. webServer 用 ws.register（非 .get）
3. package.json 无 type:module + dsh.bundle.patch 指向
4. cordis.patch.yml 用 - insert: 格式
5. lib 产物 CJS（require/exports）+ ModuleLoader 包装
6. symlink 解析 + bundles 顺序（依赖在前）
