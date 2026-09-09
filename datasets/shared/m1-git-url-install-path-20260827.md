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
*关联：M1 里程碑 / 可靠性审计 #1 / FlowerNet 主蓝图 v4.0 P2-3*
