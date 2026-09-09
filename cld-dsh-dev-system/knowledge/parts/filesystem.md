# 部件卡 · dsh-filesystem（文件系统工具面）

> 填卡：2026-09-05 · 依据：官方 subsystems/filesystem.md
> 状态：learned（registry: filesystem）

## 1. 一句话定位
[FileSystem seam `ctx.fs`]：用户路径 → 后端 resolve 成不透明 FsTarget 的稳定身份，之后一切操作吃 target。本地/远程 backend 皆可（displayPath 可 local/workspace-rel/remote URI）。

## 2. 概念与定义
- **FsTarget**：{targetKey(不透明 Branded——消费方**不得 parse/假设是本地绝对路径**), displayPath(模型/UI 展示用)}。
- **跨能力坐标（provider 给，勿自行解释 identity）**：processPath(target)→子进程可开的 canonical 绝对路径；processPathFromHostPath(hostPath)→仅共享执行世界时；fileUrl(target)；contains(parent,child)→canonical identity 或后代。
- **Version tokens（backend 拥有）**：write/edit 的 freshness guard；policy 插件存 stale 检查用，消费方不解释。
- **Write/Edit guards**：`writeText/editText` 的 expected 可选——omit=无条件 bare 变更；`createIfAbsent`(已存在→FS_NOT_OBSERVED, 含 probe 后出现者——**发布本身 must be no-replace**) | `replaceIfVersion`(缺席或版本不匹→FS_STALE_VERSION)。union 只两 guarded intent，无 guard=omit 非第三臂。
- **Read outcome**：只读渲染分开（消费方）。Observed-file state 由 policy 插件管（谁观察到什么版本）。
- **Error taxonomy**：FS_* 稳定错误。**No timeouts on file IO**（文件 IO 无超时——策略层不给）。

## 3. 作用与生命周期
resolve(path)→targetKey；读写走 target+guard；edit=read-modify-write with version。policy 插件(approval/sandbox) 在 fs 事件(pre/post)拦。

## 4. 约束（红线/不可违）
- 勿 parse targetKey 当路径——跨 backend 通用靠 provider 坐标。
- write 有 guard 语义：createIfAbsent no-replace / replaceIfVersion 防陈旧覆盖（防"改了被旧版覆盖"）。
- 文件 IO 无超时（与网络/exec 不同）。
- 本环境实证：DSH 写工具(read 前置/观察策略)与 edit 的 old_string 唯一匹配语义 = replaceIfVersion 的界面化。

## 5. 依赖
- ctx.fs 依赖 provider(local/remote)；policy 插件依赖 approval/sandbox。被 tools(tool-fs 系) 消费。

## 6. 规范要点（标准）
- "改了文件不生效/被覆盖"诊断：查 write guard(version) 语义 + 观察策略——多 agent 同改一文件即 stale。
- 跨机路径：用 processPath/fileUrl 勿拼字符串。

## 7. 关联
- 官方：filesystem.md · 工具箱：T4 · 路由：—
- 代码：dsh-filesystem/dsh-tool-fs 系

## 8. 待补
- local backend 的 targetKey 具体形态(realpath-like)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
