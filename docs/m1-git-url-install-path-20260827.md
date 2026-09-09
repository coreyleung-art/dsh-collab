# M1 里程碑 · git URL 安装路径（替代 npm 官方）

> 记录：2026-08-27 ｜ 中枢 fa1f9150 ｜ FlowerNet 蓝图 M1
> 背景：npm login 提示 "Public registration is not allowed"（网络/账号受限）→ 找到替代路径

---

## 一、问题

npm 官方发布阻塞：
- `npm login` → "Public registration is not allowed"（npmjs 账号/网络受限）
- 无 token / keychain / 环境变量
- GitHub Packages 不适合（需 scoped 名，会破坏 bundle 注册）

## 二、替代路径：git URL 安装（已验证可行 ✅）

### 核心机制
```
dsh plugin add <arg> → 转发 pnpm → pnpm add <arg>
pnpm 原生支持 git URL 源：git+https://github.com/<user>/<repo>.git
→ 从 GitHub 拉取包（无需 npm 认证）
```

### 验证结果（2026-08-27 实测）
| 步骤 | 结果 |
|------|------|
| `pnpm add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git` | ✅ 拉到 1.3.0 + 81 传递依赖 |
| 包结构 | ✅ lib/cordis.patch.yml/README/CHANGELOG + peerDeps 11 |
| 模拟安装（临时 profile + bundles） | ✅ dump-config 正确加载 `dsh-plugin-agent-way`（id: agent-bus）|
| peerDeps 11 宿主解析 | ✅ 全部在 CLD runtime（宿主自带）|

### 使用命令
```bash
dsh plugin --profile web add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git
```

## 三、与其他路径对比

| 路径 | 需认证 | 可行性 | 说明 |
|------|--------|--------|------|
| npm 官方发布 | ✅ 需 token | ⏸ 阻塞 | dsh plugin add 默认源，最优但需认证 |
| **git URL 安装** | ❌ 无需 | ✅ **已验证** | pnpm 原生支持，过渡方案 |
| GitHub Packages | ✅ gh token | ❌ 不适合 | 需 scoped 名破坏 bundle 注册 |
| 本地 link/file | ❌ | ✅ | 仅本机，不通用 |

## 四、风险与缓解

| 风险 | 缓解 |
|------|------|
| git URL 安装的是源码（无构建产物）| 我们的插件是纯 JS（lib/），无需构建——源码即产物 |
| git 分支漂移（main 更新）| 版本锁定：可加 commit/tag（git+...#v1.3.0）|
| 依赖解析差异 | peerDeps 11 全宿主自带 + pnpm 解析 81 传递依赖已验证 |
| 非标准（社区用 npm）| 过渡方案；npm 官方认证解决后切换 |

## 五、结论

git URL 安装是 M1 里程碑的**可行完成路径**（无需 npm 认证），已验证：
1. pnpm 从 git 拉取成功
2. 包结构完整
3. dump-config 正确加载（模拟新设备）

**待优化**：npm 官方发布（用户提供 token 后切换，体验最佳）。

---

## 六、补强项落地（2026-08-27 子代理审查后）

### 6.1 tag 推送修复（锁 ref 前提）

发现：**本地 5 个 tag（v1.0.0~v1.3.0）从未推送**——之前 `git push -u origin main` 只推了分支。
- 直接原因：GitHub 主站 `github.com:443` 被墙（HTTP 000 超时），git push（走主站）失败
- `api.github.com` 与 `codeload.github.com` 正常（200/301）
- **解决**：gh CLI（keyring 已登录）REST API 逐个创建 ref：
  ```bash
  gh api repos/coreyleung-art/dsh-plugin-agent-way/git/refs \
    -f ref="refs/tags/v1.3.0" -f sha="12ccad1..."   # 5 个 tag 全部推送
  ```
- SSH 不可用：`~/.ssh/id_ed25519.pub` 是 openchronicle 的 deploy key，无权推本仓库

### 6.2 锁 ref 安装验证（补强项①）

```
pnpm add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0
```
- ✅ 精确拉到 `dsh-plugin-agent-way 1.3.0`（40.6s，81 传递依赖）
- ✅ peerDeps 11 个完整（cordis/dsh-tools/dsh-client-runtime/...）
- ✅ 关键文件齐全（lib/README.md/cordis.patch.yml/package.json）
- **推荐安装命令**（MBP/i9 已通过黑板下发）：
  ```bash
  dsh plugin --profile web add git+https://github.com/coreyleung-art/dsh-plugin-agent-way.git#v1.3.0
  ```

### 6.3 符号链接守护脚本（补强项③）

`~/dsh-collab/scripts/ensure-hub-symlinks.sh`（v2 白名单语义）：
- **阶段 1**：校验/重建既有符号链接 → CLD runtime（broken 修复，保留平台 34 个）
- **阶段 2**：peerDeps 白名单扫描——发现 profile 独立副本且 runtime 同版本 → 自动替换为符号链接（消除双实例）；缺失 → 视为安全态不补建
- **配置校验**：`nodeLinker: hoisted` + `autoInstallPeers: false`
- 实测：`--check` exit 0（34 符号链接正常 + 11 peerDeps 安全）；模拟双实例 → 自动修复 ✅；幂等 ✅
- 三端可用：`DSH_PROFILE_DIR` / `DSH_RUNTIME_NM` 环境变量覆盖路径

### 6.4 adapt 指纹盲区澄清（补强项⑤ → 实测修正）

子代理审查结论「cordis/dsh MISSING（指纹盲区）」**在真实 mac-mini 环境不成立**：
- `readHostVersion()` 第一优先走 CLD runtime **显式锚点**（`/Applications/CLD.app/.../runtime/node_modules` 文件直读），**不依赖 profile 解析链**
- 实测 `collectFingerprint()`：6 个 KEY_PACKAGES 全部读到版本（dsh@0.1.0-rc.6 / cordis@4.0.1 / ...），**missing: 0**
- **真实盲区边界**：仅当 CLD 升级改变 runtime 路径、且环境变量 `DSH_RUNTIME_NODE_MODULES` 未设时，回退 require 解析链才可能 MISSING
- **加固建议**（可选）：在 CLD 启动环境显式设 `DSH_RUNTIME_NODE_MODULES` 指向 runtime node_modules，使指纹采集锚点不随 CLD 升级漂移

### 6.5 双实例形态核查（补强项②真实环境）

| 模块 | profile 形态 | runtime | 判定 |
|------|-------------|---------|------|
| 34 个平台模块 | 符号链接 → runtime | 全有效（broken 0）| ✅ 安全 |
| 6 个 peerDeps（cordis 除外）| 符号链接 | 同物理模块 | ✅ 安全 |
| 5 个 peerDeps（cordis/system-prompt/host-webserver/agent-presets/client-locale）| **缺失** | runtime 有（cordis@4.0.1 等）| ✅ 安全态（Node 解析链向上命中 runtime 单实例）|
| dsh-client-ui-layout | 独立副本 | 同版本 0.1.0-rc.6 | ⚠️ 非 peerDep（平台自身 UI 模块），同版本无实际冲突，记录在案 |

**结论**：web profile 当前无活跃双实例。guard 脚本 + 锁 ref + pnpm 配置三件套防未来安装引入。

### 6.6 审查补强项闭环对照（子代理 2e816f32 报告复核）

| 审查建议 | 状态 | 落地 |
|---------|------|------|
| (a) git ref 锁 #v1.3.0 | ✅ 完成 | tag v1.0.0~v1.3.0 已推 GitHub（REST API），`git+...#v1.3.0` 实测精确拉 1.3.0 |
| (b) 切 git+ 后真实 boot 复验（dump-config 不 import 模块） | ⏳ 待用户 | mac-mini 当前 **link: 本地源（开发态）**，非 git+ 产物——git+ 安装后真实 boot 需 MBP/i9 重启 CLD 后回报（已下发指令）|
| (c) 保留并脚本化符号链接 + autoInstallPeers:false | ✅ 完成 | `ensure-hub-symlinks.sh` v2（幂等，34 符号链接 + 11 peerDeps 白名单 + pnpm 配置校验）|
| (d) 临时 profile 81 传递依赖 ≠ web profile 真实路径 | ✅ 确认 | 临时目录（git URL 产物）仅作安装可行性证明；运行证明来自 mac link 本地源 + 34 符号链接体系；两条解析路径并存：mac link（开发）/ MBP-i9 git+（生产）|
| (e) adapt 指纹盲区（cordis/dsh MISSING）记录在案 | ✅ 澄清修正 | 实测 `collectFingerprint()` missing=0（第一锚点 CLD runtime 文件直读，不依赖 profile 解析链）；盲区仅限 CLD 升级换路径 + 未设 `DSH_RUNTIME_NODE_MODULES` 场景 |
| (f) MBP/i9 现场验证 | ⏳ 待用户 | 锁 ref 指令已下发（notes/mbp|i9/install-git-url-lockref），待重启后回报 deploy-result |

**口径核对**：审查称「35 个 @deepseek-ai 符号链接」，实测 **34 个**（可能将 dsh-client-ui-layout 独立副本或边界计入）；顶层另有 18 个 `dsh-plugin-*` → 本地源码。34 为当前真值，guard 脚本以此为准。

**审查关键结论对照**：
- peerDeps 无硬遗漏（timer soft 依赖有 setInterval 兜底）✅
- git URL 有条件接受（双实例防护前提已脚本化）✅
- bundle 加载实测确认（dump-config 渲染 bundle 层 + 本会话 19 工具运行实证）✅

---
*关联：M1 里程碑 / 可靠性审计 #1 / FlowerNet 主蓝图 v4.0 P2-3 / 子代理审查 2e816f32*
