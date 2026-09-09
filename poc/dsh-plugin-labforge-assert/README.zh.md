# dsh-plugin-labforge-assert

通用断言工具: 从 JSON 产物按路径提取指标对照 op+target 判 PASS/FAIL (labforge assert-engine 插件化)

DeepSeek Harness 插件，基于 Cordis 运行。`src/index.ts` 导出 Cordis 插件约定
的四个命名导出：`name` / `inject` / `Config` / `apply`。

## 形态

tool 形态，并以 bundle 层（`dsh.bundle` + `cordis.patch.yml`）挂入 profile。

## 开发

```bash
pnpm install        # 安装 typescript / @types/node（构建期依赖）
pnpm build          # tsc → lib/index.js
pnpm typecheck      # 仅类型检查
```

## 安装到 profile

作为 bundle 层（推荐，`dsh plugin` 会自动把它挂进 profile 的层栈）：

```bash
dsh plugin --profile <name> add <本目录路径或 npm 包名>
dsh --profile <name> --dump-config   # 验证插件行已进入组合配置
```

bundle 的 `cordis.patch.yml` 会在 profile 中插入一行：

```yaml
- insert:
    - id: labforge-assert
      name: dsh-plugin-labforge-assert
      config:
        greeting: Hello
```

普通行插件（非 bundle）：在 profile 的用户层
`$DSH_HOME/profiles/<name>/cordis.patch.yml` 里手动加一行：

```yaml
- insert:
    - id: labforge-assert
      name: dsh-plugin-labforge-assert
      config:
        greeting: Hello
```

行 `config` 即 `apply(ctx, config)` 收到的第二个参数，由 `Config` schema 校验。

## 目录结构

```
src/index.ts       插件实现（name / inject / Config / apply）
tsconfig.json      NodeNext 严格模式构建配置
cordis.patch.yml   bundle 层 patch（仅 bundle 形态）
```

## 常见问题

- **改了源码不生效**：`pnpm build` 后重启目标 profile（`dsh --profile <name>`）。
- **工具未被模型看到**：确认 `@deepseek-ai/dsh-tools` 在 profile 的依赖树里
  （dsh-base 自带），且插件行已进入组合配置。
