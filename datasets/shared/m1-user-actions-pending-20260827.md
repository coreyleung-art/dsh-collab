# 待用户操作清单（M1 里程碑 · 等用户回来处理）

> 记录：2026-08-27 ｜ 中枢 fa1f9150
> 说明：以下操作需要用户人工处理（系统权限/账号凭据/设备操作），已自动推进的部分见 M1 状态。

## 🔴 需要用户（按优先级）

### 1. npm 官方发布认证（可选优化，git URL 已替代）
- **现象**：`npm login` 提示 "Public registration is not allowed"（网络/账号受限）
- **现状**：已用 git URL 安装替代（`dsh plugin add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git`）——已验证可行
- **待用户**：若希望插件可从 npm 官方安装（`dsh plugin add dsh-plugin-agent-way`），需：
  - 检查 npmjs.com 账号是否可登录（可能需科学上网）
  - 或提供 npm token（publish 权限）
- **收益**：npm 官方是 dsh plugin add 默认源，安装体验最好；git URL 是过渡

### 2. MBP 重启 CLD（生效 git URL 安装）
- **现状**：MBP 已收到 git URL 安装指令（notes/mbp/install-git-url）
- **待用户**：MBP 执行安装后需重启 CLD → [agent-bus] 加载
- **阻塞**：MBP 的 osascript 远程重启被 macOS 自动化权限拒绝（-128）——需用户手动

### 3. i9 安装验证 + CLD 重启
- **现状**：i9 已收到 git URL 安装指令（notes/i9/install-git-url）
- **待用户**：i9 执行安装；若 CLD 固定组合不加载第三方插件，需确认官方入口是否生效
- **阻塞**：i9 的 taskkill 远程命令超时——需用户手动操作

### 4. 三端对称验证（M1 完成后）
- **待用户**：三端各自重启后，验证 [agent-bus] 加载 + agentBus 服务上线 + 双向注入

## 🟡 可选（不紧急）

### 5. git 全局 config 已修复（无需操作）
- 双重引号 insteadOf 污染已清理（R10 完成）
- 顺带说明：github.com/coreyleung-art/dsh-plugin-agent-way 仓库已建，源码已推送

### 6. 后续里程碑（M2+）需用户拍板
- M2：HubBridge 独立化（genebank 恢复 + 身份层 + audit 清理）
- M3：企业级（计量 + HA 云部署 + 看门狗）
- M4：多租户（门店隔离 + 订阅）
- M5：商业化（首付费订阅）
- 每个里程碑进入需用户确认（架构演进原则）

---
*本清单由中枢维护，用户回来后按 🔴 优先级处理即可。已自动完成的部分见 data/iterations/m1-* 归档。*
