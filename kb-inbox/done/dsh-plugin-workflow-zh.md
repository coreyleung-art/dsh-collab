# DSH 插件生产工作流

> 从「一个想法」到「跑在 DeepSeek Harness profile 里的插件」的完整生产线。
> 配套脚手架：`bin/create-dsh-plugin.mjs`（零依赖，Node ≥ 20）。

---

## 0. 总览

```
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│ 1.需求   │→ │ 2.脚手架  │→ │ 3.实现    │→ │ 4.构建与  │→ │ 5.集成开发    │
│ 形态决策  │  │ 生成工程  │  │ 插件代码  │  │ 冒烟测试  │  │ profile 验证  │
└─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────┬───────┘
                                                              │ 迭代
┌──────────┐  ┌──────────────┐  ┌──────────┐                  │
│ 8.维护    │← │ 7.发布与安装   │← │ 6.发布前  │←────────────────┘
│ 验收清单  │  │ npm/git 安装  │  │ 回归检查  │
└──────────┘  └──────────────┘  └──────────┘
```

核心事实（决定整个工作流的架构）：

- DSH 的 runtime 是 **Cordis**；一个插件 = 一个 npm 包，导出约定
  `name` / `inject` / `Config` / `apply`。
- 一个 **profile**（如 `web`、`headless`、自定义的 `dev`）= `$DSH_HOME/profiles/<name>/`
  目录，其中 `package.json` 的 `dsh.profile.bundles` 列出**叠加层（bundle）**，
  `cordis.patch.yml` 是用户自己的补丁层。
- **bundle** = 在 package.json 里声明了 `dsh.bundle.patch` 的包；
  `dsh plugin --profile <name> add <pkg>` 会自动把它追加进层栈，
  patch 里的 `insert` 行把插件挂进配置树。
- 配置树 = 空根 + 各 bundle patch 按序叠加 + 用户 patch 层 + `--patch` 覆盖层，
  行 id 相同的配置「后写覆盖先写」。

---

## 1. 前置条件

```bash
node >= 20        # 开发与脚手架
pnpm >= 9         # profile 插件管理（dsh plugin 是 pnpm 转发器）
dsh               # DeepSeek Harness CLI（npx 安装即全局可用）
```

确认 dsh 可用：

```bash
dsh --help
```

---

## 2. 阶段一：需求分析 → 形态选择

拿到需求先回答「这个插件面向谁、干什么」，据此选形态：

| 需求类型 | 形态 | 注入服务 | 注册点 | 触发方式 |
|---|---|---|---|---|
| 让模型获得新能力（查数据、写文件、调 API…） | **tool** | `tools` | `ctx.tools.register(defineTool(...))` | 模型自主调用 |
| 给用户一个斜杠命令（`/xxx`，不经过模型） | **command** | `commands` | `ctx.commands.register(...)` | 用户在 UI 输入 |
| 给应用其它部分提供内部 API（被别的插件注入） | **service** | 依赖方注入 | `ctx.provide(<name>, api)` | 其它插件 |
| 想「装一个包就自动接入」、或需要往配置树插多行 | **+ bundle 打包** | — | `dsh.bundle.patch` + `cordis.patch.yml` | `dsh plugin add` 自动挂载 |

决策建议：

- **默认 bundle + tool**：最容易分发、也最容易端到端验证。
- 只影响单个 profile 且由用户手动加行 → 普通行插件即可（`--no-bundle`），
  用户在自己的 `cordis.patch.yml` 里 insert 一行。
- 工具名/命令名全局唯一：工具名建议 `<插件id>_<动词>`（如 `weather_query`），
  命令名用插件 id 本身（如 `/weather`）。
- 模型可见的描述要写「做什么、何时用、注意事项」，参考内置工具
  `todo_write`、`bash` 的措辞。

---

## 3. 阶段二：脚手架生成

```bash
# 生成一个 bundle 打包的 tool 插件
node bin/create-dsh-plugin.mjs hello \
  --kind tool --bundle \
  --description "Say hello from the hello plugin" \
  --dir examples/dsh-plugin-hello
```

常用变体：

```bash
# 斜杠命令，不打包为 bundle
node bin/create-dsh-plugin.mjs weather --kind command --no-bundle

# 内部服务，带 npm scope，输出到当前目录
node bin/create-dsh-plugin.mjs notify --kind service --scope @my-org --dir .
```

生成物：

```
dsh-plugin-hello/
├── package.json          # dsh.bundle 声明 + peerDependencies
├── tsconfig.json         # NodeNext 严格模式
├── .gitignore
├── README.zh.md          # 安装/配置说明（生成即可用）
├── cordis.patch.yml      # bundle 层：1 行 insert
└── src/index.ts          # tool 形态实现
```

---

## 4. 阶段三：实现

### 4.1 插件解剖（所有形态通用）

```ts
import { Context } from '@deepseek-ai/cordis';
import z from '@deepseek-ai/schemastery';

export const name = 'plugin-hello';        // 行 id，profile 内唯一
export const inject = ['tools'];           // 依赖的服务名数组

export interface Config {                  // 配置类型（与 schema 一一对应）
  greeting: string;
}
export const Config: z<Config> = z.object({// 配置 schema（patch 行 config 校验）
  greeting: z.string().required(),
});
export function apply(ctx: Context, config: Config) {
  // 注册工具/命令/服务；返回的 dispose 由 Cordis 在卸载时调用
}
```

- `Config` 采用「interface + `z<Config>` 标注」的官方约定（schemastery 没有 `z.infer`）。
- `apply` 里通过 `ctx.inject([...], cb)` 做「服务就绪后再初始化」的延迟注册。
- 命名导出必须保持这四个名字，加载器按约定读取。

### 4.2 tool 形态要点

```ts
ctx.tools.register(defineTool({
  name: 'hello',
  description: '…模型看到的说明…',
  parameters: { who: { type: 'string', required: true, description: '…' } },
  output: {
    schema: { type: 'object', additionalProperties: false,
              properties: { message: { type: 'string', required: true } } },
    render: (_args, value) => [{ type: 'text', text: value.message }],
  },
  execute(args) { return Promise.resolve({ message: `Hi, ${args.who}!` }); },
  // 可选：timeoutMs / isConcurrencySafe / presentCall（UI 卡片）
}));
```

- `output.schema` 必须与 `execute` 返回值严格一致（`additionalProperties: false`）。
- `render` 是模型看到的纯文本投影。
- 需要会话/持久化能力时注入 `session`、`sessionProjections` 等（参考
  `@deepseek-ai/dsh-tool-todo`）。

### 4.3 command 形态要点

```ts
ctx.commands.register({
  name: 'hello',
  description: '…',
  handler({ rawInput }) { return { kind: 'success', text: `Hi, ${rawInput.trim() || 'world'}!` }; },
});
```

- 结果 `{ kind: 'success'|'error', text }`；命令不经过模型，直接执行。

### 4.4 service 形态要点

```ts
ctx.provide('notify', { send(...) {...} });   // 其它插件 inject: ['notify'] 消费
```

- 服务名在 profile 内唯一；提供方是唯一可写入该服务名的人。

### 4.5 bundle 打包（`--bundle` 时自动生成）

`package.json` 里的关键声明：

```json
"dsh": { "bundle": { "patch": "./cordis.patch.yml" } },
"exports": { "./cordis.patch.yml": "./cordis.patch.yml", … }
```

`cordis.patch.yml`（一次 insert，把插件挂进配置树）：

```yaml
- insert:
    - id: plugin-hello
      name: dsh-plugin-hello
      config:
        greeting: Hello
```

- 行 `id` 不能与 profile 内既有行冲突（冲突 = 覆盖语义，见 §0）。
- 需要插多行时，`insert` 列表可放多个行；需要改内置行为时用
  `- <行id>: { config: … }` 覆盖、`- <行id>: disabled` 禁用。

---

## 5. 阶段四：构建与冒烟测试

```bash
cd dsh-plugin-hello
pnpm install        # 仅装构建期依赖（typescript / @types/node）
pnpm build          # tsc → lib/index.js（NodeNext 严格模式）
pnpm typecheck      # 类型检查
```

冒烟测试（不启动 profile，直接验证导出形状）：

```bash
node -e "import('./lib/index.js').then(m => {
  if (typeof m.apply !== 'function' || !m.name) throw new Error('bad plugin export');
  console.log('ok:', m.name, 'inject=', m.inject);
})"
```

---

## 6. 阶段五：集成开发 profile 验证

用一个**专门的 dev profile** 跑插件，不污染 web/headless 生产 profile。

```bash
# 1) 建 dev profile 并装入插件 + headless 运行器（首次自动初始化）
dsh plugin --profile dev add "$PWD" @deepseek-ai/dsh-headless@0.1.0-rc.6

# 2) 验证组合配置里出现插件行
dsh --profile dev --dump-config | grep -A4 plugin-hello

# 3) 真实运行：让模型调用你的工具
dsh --profile dev "调用 hello 工具，原样报告输出"
```

- 第 1 步：`dsh plugin` 首次使用会以 `[dsh-base]` 初始化 dev profile，
  pnpm 装入插件后自动把带 `dsh.bundle` 的包追加进层栈
  （不带 bundle 的依赖会收到一条提示性警告）。
  **dsh 系运行时包建议固定版本**（与 `dsh --version` 一致，当前
  `0.1.0-rc.6`）：registry 上存在依赖已下架的旧 rc 版本（如
  `dsh-headless@0.0.1-rc.1`），不加版本可能拉取失败；自己的插件用
  `file:`/`link:` 路径安装则无此问题。
- 第 2 步：`--dump-config` 不启动、只合成配置树，是最快的回归手段。
- 第 3 步：headless 模式跑一次真实 agent 回路，确认工具被模型看到且可执行。
- 验证时注意：web 界面用的是 `web` profile，dev profile 是独立会话，
  不会影响线上数据。

---

## 7. 阶段六：迭代循环

```
改 src/index.ts → pnpm build → 重启目标 profile（重跑 dsh --profile dev "…"）
```

- 长驻界面（web）会热载用户 patch 层，但**新装/重建的插件包需要重启**。
- 每轮改动至少跑一遍 `--dump-config` + 一次 headless 冒烟，再进入下一轮。

---

## 8. 阶段七：发布与安装

### 8.1 本地/内部分发

```bash
# 方式 A：直接路径（dev 验证同款）
dsh plugin --profile web add /abs/path/to/dsh-plugin-hello

# 方式 B：git 仓库（install 时需放行 prepare 脚本构建）
dsh plugin --profile web add git+https://github.com/you/dsh-plugin-hello.git
```

git 方式如果 pnpm 提示 `Ignored build scripts`，在
`$DSH_HOME/profiles/<name>/pnpm-workspace.yaml` 的 `allowBuilds` 里放行
pnpm 打印的 key，再重跑。

### 8.2 npm 发布（公开分发）

```bash
cd dsh-plugin-hello
npm publish --access public     # 或 --scope 私有包
dsh plugin --profile web add @my-org/dsh-plugin-hello
```

发布前检查：

- `package.json` 的 `files` 只包含 `lib`（和 bundle 的 `cordis.patch.yml`）。
- peerDependencies 版本与目标 dsh 版本范围匹配（当前 `^0.1.0-rc.6`）。
- 升级已有依赖后重新 `add`（`update` 也会让新获得 `dsh.bundle` 声明的包自动入栈）。

---

## 9. 阶段八：发布前回归 & 维护清单

- [ ] `pnpm build` / `pnpm typecheck` 全绿
- [ ] 冒烟：导出形状正确（name/inject/Config/apply）
- [ ] 在全新 dev profile 里 `dsh plugin add` + `--dump-config` 出现插件行
- [ ] headless 真实调用一次工具/命令，输出正确
- [ ] 工具/命令名不与内置及同 profile 其它插件冲突
- [ ] 模型描述无歧义；参数 schema 与 execute 实际取值一致
- [ ] bundle patch 的行 id 不与目标 profile 冲突
- [ ] README 记录了配置项与安装方式
- [ ] 升级 dsh 版本后回归一次（peer 版本兼容）

---

## 附录 A：常见问题

| 现象 | 原因与处理 |
|---|---|
| `dsh plugin add` 后无效果 | 包没声明 `dsh.bundle`（普通依赖，只会收到警告）；或插件行被后续层覆盖 |
| 改了源码不生效 | 未重新 `pnpm build`；或 profile 未重启 |
| 工具模型看不到 | 行未进组合配置（`--dump-config` 确认）；`inject` 缺 `tools`；description 为空 |
| `Ignored build scripts` | git 插件需在 profile 的 `pnpm-workspace.yaml` `allowBuilds` 放行 |
| `cannot resolve profile bundle …` | 依赖未安装：`dsh plugin --profile <name> install` |
| 行 id 冲突 | patch 覆盖语义：后写覆盖先写，检查自己的 cordis.patch.yml |

## 附录 B：参考实现（读源码学模式）

- tool：`@deepseek-ai/dsh-tool-todo`（defineTool + sessionProjections 完整范例）
- command：`@deepseek-ai/dsh-command-goal`（命令解析 + UI 渲染）
- service：`@deepseek-ai/dsh-goal`（提供 `goals` 服务）
- bundle：`@deepseek-ai/dsh-base`（第一层 patch，最全的 insert 示范）

## 附录 C：DSH 插件市场模块（市场监控 + 一键发布）

配套插件 `market/dsh-plugin-market`：在 harness 自带 webserver 上提供
`/market` 页面与 `/market-api/*` API，监控开源 harness 插件生态并支持
把本工作流产出的插件一键发布到 GitHub / Gitee。

### 部署

```bash
# 独立预览 profile（不动 web profile，立即可用）
dsh plugin --profile market add <dsh-plugin-market 目录> @deepseek-ai/dsh-web-app@0.1.0-rc.6
dsh --profile market --port 3081          # 浏览器打开 http://127.0.0.1:3081/market

# 或装进 web profile（重启 dsh web 后生效）
dsh plugin --profile web add <dsh-plugin-market 目录>
```

### 能力

| 能力 | 说明 |
|---|---|
| 市场监控 | npm 官方包（直读本机安装清单）+ GitHub/Gitee 开源项目（公共搜索 API），自动识别形态 |
| 一键授权 | GitHub 设备码流（浏览器输码即完成，默认 gh CLI 公开 OAuth app）；Gitee 私人令牌粘贴；令牌存 `$DSH_HOME/market/tokens.json`（0600，绝不出现在 `--dump-config`） |
| 一键发布 | 校验工程（package.json + lib/index.js）→ GitHub（优先 gh CLI，回退 API + git push）/ Gitee（API + git push）→ 自动登记入市场索引；支持 dry-run 演练 |
| 安全 | 令牌不回传明文 API；发布为本地写操作，先 dry-run 再实发 |

### 与生产工作流的衔接

1. 用本工作流脚手架生成插件 → `pnpm build`
2. 市场页「发布」填工程目录（如 `examples/dsh-plugin-hello`）
3. dry-run 确认命令 → 正式发布 → 条目自动进入市场
4. 安装到目标 profile：复制卡片上的 `dsh plugin --profile web add <仓库>` 命令

> 多源并存即回答「GitHub 还是 Gitee」：两个都支持、同一索引去重展示，
> 发布时按平台选择。
