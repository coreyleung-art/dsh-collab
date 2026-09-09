---
name: dsh-plugin-production
version: 1.0.0
description: "DeepSeek Harness 插件生产工作流：需求分析→脚手架→实现→构建→dev profile 集成验证→发布。当用户要开发/创建/生产/迭代 DSH（DeepSeek Harness）插件、为 profile 添加能力（工具/命令/服务/bundle 层）时使用。"
---

# DSH 插件生产工作流

把「一个插件想法」变成「跑在 DeepSeek Harness profile 里的插件」。
DSH 运行时是 Cordis：插件 = 一个 npm 包，导出 `name` / `inject` / `Config` / `apply`。

## 关键事实

- profile = `$DSH_HOME/profiles/<name>/`；`dsh.profile.bundles` 列叠加层，
  `cordis.patch.yml` 是用户补丁层。
- bundle = package.json 声明 `dsh.bundle.patch` 的包；
  `dsh plugin --profile <name> add <pkg>` 自动把它追加进层栈。
- patch 是 YAML 数组：`- insert: [{id, name, config}]` 插行、
  `- <id>: {config}` 覆盖、`- <id>: disabled` 禁用；行 id 后写覆盖先写。

## 形态选择

| 需求 | 形态 | 注入 | 注册点 |
|---|---|---|---|
| 模型新能力 | tool | `tools` | `ctx.tools.register(defineTool({name, description, parameters, output, execute}))` |
| 用户斜杠命令 | command | `commands` | `ctx.commands.register({name, description, handler})` |
| 内部 API | service | 依赖方注入 | `ctx.provide(name, api)` |
| 装包即自动挂载 | + bundle | — | `dsh.bundle.patch` + `cordis.patch.yml` |

默认建议：bundle + tool。

## 执行步骤

### 1. 脚手架（有 `~/dsh-plugin-workflow` 时优先）

```bash
node ~/dsh-plugin-workflow/bin/create-dsh-plugin.mjs <name> \
  --kind tool|command|service [--bundle|--no-bundle] \
  --description "<一句话>" --dir <输出目录>
```

无脚手架时手工创建：`src/index.ts` + `package.json` + `tsconfig.json`
（NodeNext 严格模式），包结构见「模板速写」。

### 2. 实现（四个命名导出）

```ts
import { Context } from '@deepseek-ai/cordis';
import z from '@deepseek-ai/schemastery';

export const name = 'plugin-hello';      // 行 id，profile 内唯一
export const inject = ['tools'];         // 依赖服务
export interface Config { greeting: string; }
export const Config: z<Config> = z.object({ greeting: z.string().required() });
export function apply(ctx: Context, config: Config) {
  // 注册工具/命令/服务
}
```

注意：Config 用「interface + `z<Config>` 标注」约定（schemastery 无 `z.infer`）。

tool 用 `defineTool`（`@deepseek-ai/dsh-tools`）：`output.schema` 必须与
`execute` 返回值一致；`output.render` 是模型看到的纯文本。
command 用 `ctx.commands.register`：handler 返回 `{kind:'success'|'error', text}`。
service 用 `ctx.provide(name, api)`。
bundle 需在 package.json 加 `"dsh": {"bundle": {"patch": "./cordis.patch.yml"}}`，
patch 至少一条 `insert` 把插件行挂进配置树。

### 3. 构建 + 冒烟

```bash
pnpm install && pnpm build && pnpm typecheck
node -e "import('./lib/index.js').then(m=>{if(typeof m.apply!=='function')throw Error('bad');console.log('ok',m.name)})"
```

### 4. 集成验证（专用 dev profile）

```bash
dsh plugin --profile dev add "$PWD" @deepseek-ai/dsh-headless@0.1.0-rc.6
dsh --profile dev --dump-config | grep -A4 <插件id>
dsh --profile dev "<触发插件工具/命令的 prompt>"
```

注意：dsh 系运行时包建议固定版本（与 `dsh --version` 一致），registry 上
可能有依赖已下架的旧 rc 版本。

`--dump-config` 是快速回归；headless 跑一次真实回路确认模型能看到并执行。

### 5. 迭代

改 `src/index.ts` → `pnpm build` → 重跑 headless 验证。重启才生效。

### 6. 发布

`npm publish` 或 git spec：`dsh plugin --profile <name> add <spec>`。
git 方式若 pnpm 拦截构建脚本，在 profile 的 `pnpm-workspace.yaml`
`allowBuilds` 放行后重跑。发布前跑一遍 §9 回归清单
（见 `~/dsh-plugin-workflow/docs/workflow.zh.md`）。

### 7. 市场模块（可选，一键发布到 GitHub/Gitee）

`~/dsh-plugin-workflow/market/dsh-plugin-market`：harness webserver 上的
`/market` 页面 + `/market-api/*` API。监控 npm 官方包 + GitHub/Gitee 开源
项目；GitHub 一键授权（设备码流）/ Gitee 令牌；发布插件工程（dry-run 演练
→ 建仓 push → 自动入索引）。部署：

```bash
dsh plugin --profile market add ~/dsh-plugin-workflow/market/dsh-plugin-market @deepseek-ai/dsh-web-app@0.1.0-rc.6
dsh --profile market --port 3081   # 打开 http://127.0.0.1:3081/market
```

## 模板速写（无脚手架时用）

package.json 关键字段：

```json
{
  "name": "dsh-plugin-hello",
  "type": "module",
  "main": "lib/index.js",
  "types": "lib/index.d.ts",
  "exports": { ".": {"types": "./lib/index.d.ts", "default": "./lib/index.js"},
               "./cordis.patch.yml": "./cordis.patch.yml" },
  "files": ["lib", "cordis.patch.yml"],
  "dsh": { "bundle": { "patch": "./cordis.patch.yml" } },
  "peerDependencies": { "@deepseek-ai/cordis": "^4.0.1",
                        "@deepseek-ai/dsh-tools": "^0.1.0-rc.6" },
  "dependencies": { "@deepseek-ai/schemastery": "^3.18.1" }
}
```

cordis.patch.yml：

```yaml
- insert:
    - id: plugin-hello
      name: dsh-plugin-hello
      config:
        greeting: Hello
```

## 常见问题

- `add` 后无效果：包没声明 `dsh.bundle`（会收到警告），或行被后层覆盖。
- 模型看不到工具：`--dump-config` 确认行已入树；`inject` 缺 `tools`；description 为空。
- 工具/命令名全局唯一：工具建议 `<插件id>_<动词>`，命令用插件 id。
- 参考实现：tool 看 `@deepseek-ai/dsh-tool-todo`，command 看
  `@deepseek-ai/dsh-command-goal`，bundle 看 `@deepseek-ai/dsh-base`。
