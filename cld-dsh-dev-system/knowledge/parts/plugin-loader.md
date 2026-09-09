# 部件卡 · plugin-loader（插件树加载 / bundle / patch）

> 填卡：2026-09-04 · 依据：architecture.md(Profiles/bundles) + cordis-tutorial + cookbook + 实证(遮蔽事故)
> 状态：learned（registry: plugin-loader）

## 1. 一句话定位
dsh 是 **everything-is-a-plugin**：运行中的 dsh = boot 时按有序层组合的 Cordis 插件树；无特权核心可 patch——扩展 = 在旁边挂插件，注册是 effect（插件卸载即回卷）。

## 2. 概念与定义
- **Profile**：Harness home 里的命名组合：列出 stacks 的 bundles + 外树插件 + 用户自己的 `cordis.patch.yml`。web/headless/sdk/sdk-minimal/acp 是模板。
- **Bundle**：Cordis config 行 + 其挂载代码的分发格式（dsh.bundle 指 bundle 的 patch 文件）；插进去的东西可被上层 layer patch。
- **Layer 顺序**：空 entry 表上按序应用：profile 列出的各 bundle(按序) → profile 的 cordis.patch.yml → home 级 → --patch overlay。**patch 按行 id 定位：整段替换 config 或插入新行**。
- **Entry 并发**：entries 并发 start——列表位置不保证加载序；**真顺序 = 服务依赖(inject)**（实证：遮蔽使 host 服务旧版异常，与位置无关）。
- **apply(ctx)**：插件模块 named-export apply；ctx 是注册一切的通道；注册=effect(ctx.effect)。
- **load 错误传播**：entry init 失败 → plugin tree failed（8-21 "corrupt zstd"、今天 central-inbox ReferenceError 均此类，会整树失败）。

## 3. 作用与生命周期
CLD spawn dsh → dsh-app-boot 按 profile 组合 → cordis loader 建树 → entries 并发 init（inject 定序）→ 服务 active → 热重载(web profile live patch reload) / 一次性(其他 profile)。CLD 重启 = 新 dsh 进程重演全 boot。

## 4. 约束（红线/不可违——全部实证踩过）
- **pnpm/dsh plugin add 全量重写 profile 依赖树** → 65/27 遮蔽（OP-pnpm-add prob 1.0）。
- **profile node_modules 真目录遮蔽 runtime** = host 服务跑旧版 → UI/会话/connection 异常（今日根因）。核心包：workspace/host-apiproxy/client-connection/api-remotes/agent…全在 runtime 才是正解。
- **entry 依赖 inject 服务**：client-connection 的 /api WS 在 `ctx.inject(["apiProxy"])` 内——apiProxy 未就绪则永不挂载。
- 禁插件(disabled) 可致 boot 不完整(ui-reference 教训)；禁用官方 client 插件 → fallback 文案。
- module 加载协议：host ESM named-export apply / client `__ModuleLoader__.load`。

## 5. 依赖
- dsh-app-boot(组装) → cordis(core) → cordis-plugin-loader(entry init)。entry 间靠 inject 服务依赖。
- profile 组合解析：dsh 读 profile 的 dsh.profile bundles + cordis.patch.yml。

## 6. 规范要点（标准）
- **依赖/包改动 = 改 runtime 内包解析**：`guard-check-deps` 归零是硬前提；cld-monitor shade_count 告警已接。
- 诊断 boot 失败：读最新 boot 段 entry 错误 → 判断 版本遮蔽(OP-pnpm) / 依赖服务缺失 / 语法 / YAML patch 错。
- 加 host 工具插件：defineTool + output:makeOutput + schema 显式 additionalProperties + mock-ctx 冒烟。
- 加 client 插件：__ModuleLoader__.load + exports{default} + React.createElement + priority:-1。
- dump-config 看组合后树（每行可被 patch 替换）。

## 7. 关联
- 官方文档：architecture.md、cordis-tutorial/、cookbook/extension-cookbook.md、cordis-api/
- 工具箱：T4/T5/T7 · 路由表：OP-pnpm-add/OP-disable-plugin/OP-add-plugin-host/client/OP-config-yaml
- 代码：cordis-plugin-loader/lib（Entry._init/updateError）、dsh-app-boot、dsh/lib/profile-boot
- 知识：session-persistence/workspace 卡（其服务是 loader 树的 entry）

## 8. 待补
- live patch reload 机制细节（web profile 热重载如何触发/revert）。
- entry init 并发与 inject 定序的精确语义（cordis fiber）。

## 9. 学-建-用 沉淀
- 2026-09-04：卡毕业；直接支撑今日遮蔽根因修复的理解；guard-check-deps/monitor shade 告警 = 本卡产出的防再犯工具。
