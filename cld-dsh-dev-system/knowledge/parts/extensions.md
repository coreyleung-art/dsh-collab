# 部件卡 · dsh-extensions（扩展子系统）

> 填卡：2026-09-05 · 依据：官方 subsystems/extensions.md
> 状态：learned（registry: extensions）

## 1. 一句话定位
让 agent **定义版本化 Cordis 包、跑其 host/browser 两半、写码前查 approved runtime metadata**——即"agent 自建插件"的扩展面(与 self-modification 包呼应)。生命周期与沙箱行为属 packages/extensions 组。

## 2. 概念与定义
- **版本化 Cordis 包**：agent 可定义/注册的扩展(manifest + host/browser halves)。
- **ctx.cordisInspect CordisInspectRegistryService**：registry + cross-page router behind 两个 model-facing inspect 工具(写码前查 runtime metadata)；register(registration)=manifest+local query handler → idempotent disposer。
- **查询**：host provider 注册后可按 manifest/query 检阅——让 agent 编插件前了解目标 API(防瞎写)。

## 3. 作用与生命周期
agent 想加能力 → inspect 查 runtime → define 包(host/browser) → 注册 → 沙箱内跑 host/browser halves → 卸载回卷。

## 4. 约束（红线/不可违）
- host/browser 两半生命周期由 packages/extensions 管；包沙箱行为遵循 sandbox。
- 写码前查 approved metadata——勿凭空猜 API。

## 5. 依赖
- 依赖 cordis(包定义)/sandbox(运行)/registry；与 guard 插件自研路径(dsh-plugin-*)同族但版本化+inspect 支撑。

## 6. 规范要点（标准）
- 造新 host 工具前先 inspect 目标 runtime(services/API)——防 dsh-tools 契约踩坑(见 tools-exec 卡)。
- 扩展注册 effect 化、disposer 回卷。

## 7. 关联
- 官方：extensions.md、cookbook/extension-cookbook.md · 工具箱：T4 · 路由：—
- 代码：dsh-extensions/dsh-plugin-* 生态

## 8. 待补
- 与 dsh-plugin-guard 自研流程的衔接(是否可走官方 inspect)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
