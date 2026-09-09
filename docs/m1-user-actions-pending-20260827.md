# 待用户操作清单（M1 里程碑 · 等用户回来处理）

> 记录：2026-08-27 ｜ 中枢 fa1f9150 ｜ 更新：2026-08-27 锁 ref 版指令已下发
> 说明：以下操作需要用户人工处理（系统权限/账号凭据/设备操作），已自动推进的部分见 M1 状态。

## 🔴 需要用户（按优先级）

### 1. npm 官方发布认证（可选优化，git URL 锁 ref 已替代）
- **现象**：`npm login` 提示 "Public registration is not allowed"（网络/账号受限）
- **现状**：已用 git URL 锁 ref 替代（`git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0`）——已验证可行，tag v1.0.0~v1.3.0 已全部推 GitHub
- **待用户**：若希望插件可从 npm 官方安装（`dsh plugin add dsh-plugin-agent-way`），需：
  - 检查 npmjs.com 账号是否可登录（可能需科学上网）
  - 或提供 npm token（publish 权限）
- **收益**：npm 官方是 dsh plugin add 默认源，安装体验最好；git URL 是过渡

### 2. MBP 重启 CLD（生效 git URL 安装）—— ✅ 已完成（2026-08-28）
- **完成经过**：MBP 执行 `dsh plugin --profile web add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0`（4.1s 拉取）→ dump-config 确认注册 → 重启报 **duplicate loader entry id: agent-bus** → 修复（删旧 `dsh-plugin-agent-bus` v1.0.0 tar.gz 物理复制版，与 v1.3.0 抢 id）→ 重启正常 → **新会话确认完整 agent 总线工具 ✅**
- **遗留**：① MBP 会话 agent_profile 档案为空，待登记角色/能力 ② MBP central-inbox SSE 配置待确认（verify-ack 未自动回报）③ MBP 节点注册 ts 未随重启刷新（verify-watch 探针误报「离线 301s」，判定瑕疵待修）

### 3. i9 安装验证 + CLD 重启
- **现状**：i9 已收到【锁 ref】安装指令（notes/i9/install-git-url-lockref，`#v1.3.0`）
- **待用户**：i9 执行安装；若 CLD 固定组合不加载第三方插件，需确认官方入口是否生效
- **阻塞**：i9 的 taskkill 远程命令超时——需用户手动操作

### 4. 三端对称验证（M1 完成后）—— MBP ✅ / i9 待确认
- **mac-mini**：✅ link 本地源，重启后 agent-bus 加载 + dump-config 确认（2026-08-28）
- **MBP**：✅ git+ #v1.3.0 安装 + 重启 + 新会话确认 agent 总线工具（2026-08-28）
- **i9**：⏳ 待确认（CLD 固定组合是否加载第三方插件；i9 已重启 + node-bridge 1.2.0）
- **验证命令**：`dsh dump-config | grep agent-way`（确认 id: agent-bus 注册）

### 5. 符号链接守护脚本三端部署（可选加固）
- **现状**：`~/dsh-collab/scripts/ensure-hub-symlinks.sh`（v2）已写好并实测（mac-mini ✅）
- **待用户**：MBP/i9 安装完成后跑一次 `ensure-hub-symlinks.sh --check`，异常则直接运行修复
- **收益**：防 pnpm 把 peerDeps 复制成 profile 独立副本（双实例隐患）

## 🟡 可选（不紧急）

### 6. git 全局 config 已修复（无需操作）
- 双重引号 insteadOf 污染已清理（R10 完成）
- 顺带说明：github.com/coreyleung-art/dsh-plugin-agent-way 仓库已建，源码+5 tag 已推送

### 7. 后续里程碑（M2+）需用户拍板
- M2：HubBridge 独立化（genebank 恢复 + 身份层 + audit 清理）
- M3：企业级（计量 + HA 云部署 + 看门狗）
- M4：多租户（门店隔离 + 订阅）
- M5：商业化（首付费订阅）
- 每个里程碑进入需用户确认（架构演进原则）

---
*本清单由中枢维护，用户回来后按 🔴 优先级处理即可。已自动完成的部分见 data/iterations/m1-* 归档。*
