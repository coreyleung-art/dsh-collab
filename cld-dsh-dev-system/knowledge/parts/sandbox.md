# 部件卡 · dsh-sandbox（进程沙箱 / 文件效应策略）

> 填卡：2026-09-05 · 依据：官方 subsystems/sandbox.md + permission-presets.md
> 状态：learned（registry: sandbox）

## 1. 一句话定位
[dsh-sandbox] 把同世界子进程 argv 包进**文件效应策略**而不把消费者耦合到平台 runner：mode 只治文件效应；providers = Linux bwrap/Landlock、macOS Seatbelt、Windows ACL restricted-token；消费者 = bash-sandbox/pwsh-sandbox。容器/microVM/远程执行是整能力 seam 的兄弟实现，非 ctx.sandbox provider。

## 2. 概念与定义
- **SandboxMode**：'read-only'(只许必需 sink 如 /dev/null；POSIX 额外给 /dev/null) | 'workspace-write'(workspace root + backend 承诺的 temp) | 'danger-full-access'(绕过)。**Network/进程可见性在此词汇外**。
- **ConfinedSandboxMode** = Exclude<SandboxMode,'danger-full-access'>——只有前两模式能发 provider；danger-full-access 消费者直接 spawn 原 argv 不调 ctx.sandbox。
- **SandboxEnforcement**：'full'(backend 治每个承诺效应) | 'partial'(旧内核 ABI/Windows ACL 边界只治子集)——**要求绝对边界者不得当 full**。
- **SandboxExecutionPolicy**：每次 capability call 完整解析并携带（含 danger-full-access 让消费者先解析再决定是否绕过）；tool call 的 workspaceRoot 从 calling session 不可变 cwd 派生；**root 先 filesystem 语义 canonicalize 再词法归一**(cwd 含 symlink/.. 时定位真实运行目录)。
- **preset 表(permission-presets.md)**：ctx.permissionPresets——current preset + 派生的 custom；切换发 permission/preset 事件。

## 3. 作用与生命周期
tool call → 解析 SandboxExecutionPolicy(mode+root) → 非 danger 则包 argv 交 provider 执行 → 报告 enforcement(full/partial)。权限预设决定 tools 的默认 mode。

## 4. 约束（红线/不可违）
- mode 三态只治文件效应，不含 network/进程——要隔离那些另走整能力 seam。
- partial enforcement 不可当 full——绝对边界要求者必须拒或显式 surface。
- 本环境实证：DSH 沙箱三模式(read-only/workspace-write/danger-full-access)与 CLI 工具 sandbox_permissions 同构；bash 工具被拒=partial/full 报告。

## 5. 依赖
- ctx.sandbox 依赖平台 provider(sandbox-local)；被依赖 shell tools。ctx.sandboxPolicy 供策略查询。

## 6. 规范要点（标准）
- 需要写 workspace 外/系统区 → 升级模式或整能力 seam，勿硬绕。
- 被 sandbox 拒的操作：改更宽模式重试一次即可(设计如此)，但拒绝后换法绕过 = 违规。

## 7. 关联
- 官方：sandbox.md、permission-presets.md · 工具箱：T4(工具执行) · 路由：—
- 代码：dsh-sandbox{,-local}/dsh-bash-sandbox

## 8. 待补
- macOS Seatbelt 在 CLD 宿主侧的应用边界(本机实际用哪个 provider)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业——三方模式与 enforcement 概念对齐自研工具行为。
