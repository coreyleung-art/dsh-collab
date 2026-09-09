# 插件安装记录 R1 —— DSH web profile 社区插件加载（2026-08-16）

> 会话：插件运维（session-eb5ee9cc-7662-4b7d-8ccb-70ebab06a80d）
> 目标 profile：`web`（`~/.dsh/profiles/web/`）
> 状态更新：**2026-08-16 受控重启后已在当前实例（127.0.0.1:51960 / PID 31110）实测生效**（见「重启后验证」）

## 安装清单（5 项，全部验证通过，待重启生效）

| 社区插件 | 安装包/来源 | 安装方式 | 状态 |
|---|---|---|---|
| modlens（视觉识图桥梁） | `@liustack/modlens@3.16.7` | npm | ✅ 已挂载 `modlens` 层（cordis.patch.yml insert） |
| dsh-web-ui 全家桶 | `@linxin666/dsh-web-ui-all@0.1.16` | npm | ✅ 11 个子包全部挂载（任务看板/Git图谱/手机远程/实时统计/SSH/图像理解/宠物/皮肤中心/梁神/WebUI设置/AionUI面板） |
| deeptide（DeepTide CLI） | `deeptide@0.11.8` | npm | ⚠️ **非 dsh bundle**，仅普通依赖，无 harness 层 |
| dsh-genui（内联交互 UI） | `@omdsh-dev/dsh-genui@0.8.3` | git（官方推荐，未发布 npm） | ✅ 已挂载 `genui` 层 |
| dsh-better-sidebar（侧边栏工作台） | `dsh-better-sidebar@0.12.2` | npm | ✅ 已挂载 `better-sidebar` 层 |

## 验证结果
- `dsh --profile web --dump-config` 组合成功（exit 0），无重复 loader id
- 各 bundle 入口 `require()` 冒烟测试通过（lib/index.js / cordis.patch.yml）
- `@linxin666/*` 12 个子包在 `nodeLinker: hoisted` 下全部解析
- `node-pty`（better-sidebar 终端原生绑定）已批准构建并 `pnpm rebuild` 成功

## 环境备注（供后续运维取用）
- 本机原 PATH 无 node/pnpm → 已由 sysops 会话解决：node v25.9.0（homebrew）、pnpm 11.22.0（`~/.npm-global/bin`），PATH 已写入 `~/.zshrc` + `~/.zprofile`
- profile `pnpm-workspace.yaml` 已有：`minimumReleaseAge: 0` + `allowBuilds`（含 `@paean-ai/zero-cli`、`cloudflared`、`cpu-features`、`ssh2`、`node-pty` 等）——`@linxin666/*` pnpm 11 静默降级风险已覆盖
- 临时 shim（`/tmp/dsh-bin`，CLD 内嵌 Node）已不再需要，可清理

## ✅ 重启后验证（已完成）
- 受控重启已完成，当前实例 51960/PID 31110 实测：
  - 服务端工具：`ssh_list` → `{"hosts":[]}`（dsh-ssh）、`validate_dsh_ui` → ✅（dsh-genui）均为真实可调用
  - 客户端资产：`/plugins/<pkg>/client.js` 全部 200 且非空（web-ui-all 2574B / dsh-ssh 783503B / task-board 130682B / better-sidebar 414750B / genui 121389B / modlens 31341B）
  - 配置层：`--dump-config` 含 4 个 bundle 层 + 12 子包
- 旧实例（63866/23609，23:49 boot）已被受控重启替换；协调者侧 404 疑为旧实例/路径差异，当前实例裸 client.js 即 200
- deeptide 无 UI 入口（CLI 工具，profile 内 `node_modules/.bin/deeptide|tide` 可用）