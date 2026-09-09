# 供应链基线审计报告 R1（依赖/供应链专员 session-0e84e65c）

- 时间：2026-08-17（epoch 17869153xx）
- 对象：`~/.dsh/profiles/web`（dsh-profile-web）依赖树 + `~/.dsh/profile-assets/xberg` 原生资产
- 依据：xberg 脆弱性案例（optional 平台包发布缺失）+ 9910d4b2/c1111ffe 双证据（CLD-004 加固产出）
- 工具：pnpm 11.22.0（全局 ~/.npm-global）、node v25.9.0、npm 11.12.1

---

## 一、审计方法

1. package.json / pnpm-workspace.yaml / cordis.yml 结构读取
2. pnpm-lock.yaml（lockfileVersion 9.0）与 package.json 一致性核对
3. `pnpm install --lockfile-only --frozen-lockfile --offline` 冻结校验
4. `pnpm audit --prod --registry=https://registry.npmjs.org` 安全审计
5. npm registry 数据核查（xberg 平台包发布历史、主包版本）
6. xberg 原生资产 sha256 快照 + otool 依赖链检查 + node require 实测

## 二、资产健康检查结果

### 2.1 xberg 原生绑定资产（profile-assets/xberg，8 文件）✅

| 文件 | sha256 | 状态 |
|------|--------|------|
| xberg-node.darwin-arm64.node | 2e94a5aa…a441 | ✅ 存在 |
| libonnxruntime.1.24.2.dylib | a7983030…be11 | ✅ 存在 |
| libheif.1.dylib | 6598e5f1…6cc3 | ✅ 存在 |
| libx265.216.dylib | ab9093bf…27a8 | ✅ 存在 |
| libde265.0.dylib | 3ed380b8…76aa | ✅ 存在 |
| libaom.3.dylib | 04337cce…8e9 | ✅ 存在 |
| libsharpyuv.0.dylib | 89efe3d4…ddcd | ✅ 存在 |
| libvmaf.3.dylib | 744847f5…b524 | ✅ 存在 |

- **node require 实测：通过**（extract/mapUrl/PSMMode 等 API 正常导出）
- **otool 依赖链**：@loader_path 相对引用自包含 ✅
- **⚠️ 注意**：`xberg-node.darwin-arm64.node` 首行 otool 依赖含绝对路径 `/Users/runner/work/xberg/xberg/target/aarch64-apple-darwin/release/deps/libxberg_node.dylib`，该文件**不存在**于包目录。实测 require 正常说明 NAPI 加载不依赖它（可能为编译残留元数据），但为防未来 NAPI 版本变化，建议验证 `otool -l` 中 LC_LOAD_DYLIB 实际解析行为，并考虑用 install_name_tool 改写或文档标注为已知无害项。

### 2.2 postinstall 加固脚本（CLD-004 产出）✅

`scripts/ensure-xberg-binding.js`：node_modules 重装后自动从资产目录恢复 8 文件到 `node_modules/@xberg-io/xberg/`，缺资产即 FATAL 退出。当前包目录内 8 文件已就位（Aug 17 04:43 恢复）。

### 2.3 xberg 平台包发布状态（xberg 案例核心证据）⚠️

> **当日补发事件（2026-08-17，QA 验收 #007 提示补注）**：本报告快照时平台包最高仅 `1.0.0-rc.21`（1.0.14 未发布）；同日稍后上游**补发了全部 6 平台 1.0.14**（darwin-arm64 / linux-arm64-gnu / linux-x64-gnu / linux-x64-musl / linux-arm64-musl / win32-x64-msvc，官方 registry 实测确认）。本小节描述的是**快照时点**状态；演进后状态见 upstream-watchlist.md §C（脆弱性→已解除）。

- `@xberg-io/xberg-darwin-arm64`：快照时最高发布 `1.0.0-rc.21`，**1.0.14 未发布**（1.0.0-rc.x 止步）；当日稍后补发 1.0.14
- `@xberg-io/xberg-linux-arm64-gnu`：同上限 `1.0.0-rc.21`，1.0.14 缺失；当日补发
- `@xberg-io/xberg-win32-x64-msvc`：最高 `1.0.0-rc.15`；当日补发 1.0.14
- 主包 `@xberg-io/xberg`：1.0.14 已发布（lockfile 解析 1.0.14 正确）
- **结论**：平台 optional 包缺失 = pnpm 静默跳过（npm/cli#4828 现象），CLD-004 的本地资产恢复方案是正确的加固路径。平台包已补发（当日），镜像同步后评估移除 override + postinstall 降级为纯 registry 依赖。

## 三、Lockfile 一致性 ✅

- `pnpm install --lockfile-only --frozen-lockfile --offline`：**通过**（"Lockfile passes supply-chain policies"）
- importers 段 18 个直接依赖 specifier 与 package.json 一致
- 依赖链路关键确认：`dsh-doc@0.1.1 → @xberg-io/xberg@1.0.14`（xberg 为 dsh-doc 传递依赖，overrides 锁定 1.0.14）
- `@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-web-app`：宿主内置 bundle（CLD runtime 提供，dsh-web-app 0.1.0-rc.6），不在 profile 依赖树，lockfile 无对应条目属正常

## 四、安全审计结果 ⚠️（2 漏洞待修）

| 级别 | 包 | 脆弱版本 | 修复版本 | 路径 | 备注 |
|------|-----|---------|---------|------|------|
| **high** | sharp | <0.35.0（当前 0.34.5） | ≥0.35.0 | `deeptide>@paean-ai/zero-cli>sharp`；`dsh-knowledge>@huggingface/transformers>sharp` | CVE-2026-33327/33328/35590/35591（libvips 继承漏洞） |
| **moderate** | uuid | <11.1.1（当前 9.0.1） | ≥11.1.1 | `deeptide>@paean-ai/zero-cli>google-auth-library>gaxios>uuid` 等 3 条 | GHSA-w5hq-g745-h8pq（v3/v5/v6 buffer bounds） |

修复策略（待与 c1111ffe 协作 + 维护窗口）：
- sharp：优先升级 `@paean-ai/zero-cli`（当前 0.11.25）或对 sharp 加 overrides 到 0.35.x；`dsh-knowledge` 侧跟踪 `@huggingface/transformers` 新版本
- uuid：跟踪 zero-cli 上游升级 gaxios；若无新版本则接受风险并记录（uuid 仅用于 Google 云 auth 路径，本地使用面有限）

## 五、供应链策略问题 ⚠️

### 5.1 pnpm.overrides 字段失效（重要）

- package.json 中 `"pnpm": { "overrides": { "@xberg-io/xberg": "1.0.14" } }` 是 **pnpm ≤9 的旧位置**
- pnpm 11.22.0 明确警告：`The "pnpm" field in package.json is no longer read by pnpm`，overrides 被忽略
- **影响**：xberg 1.0.14 当前仍正确解析（lockfile 固化 + dsh-doc 声明精确 1.0.14），但 override 策略**已失去兜底作用**；若未来 dsh-doc 或传递依赖要求其他版本，将无法强制锁定
- **建议**：迁移 overrides 到 `pnpm-workspace.yaml`（pnpm 11 新位置）或 package.json 根级 `"overrides"` 字段；连带把 allowBuilds 等策略一并审查

### 5.2 GitHub 直链依赖（脆弱绑定）

- `@omdsh-dev/dsh-genui`: `github:omdsh-dev/dsh-genui`（lockfile 固化为 codeload tarball 0e756efb…）——GitHub 直链虽已锁定 commit，但仍是发布供应链薄弱点（无 registry 版本、依赖 GitHub 可用性）。**建议**：跟踪上游是否发布 npm 版本，发布后切换

### 5.3 镜像信任边界

- registry 指向 npmmirror（信任边界已文档化于 pnpm-workspace.yaml）；audit endpoint 在 npmmirror 缺失（ERR_PNPM_AUDIT_ENDPOINT_NOT_EXISTS），**安全审计需显式 --registry=https://registry.npmjs.org**

## 六、健康检查结论

| 项 | 状态 |
|----|------|
| xberg 资产完整性（8 文件 + sha256） | ✅ |
| xberg require 加载 | ✅ |
| postinstall 加固脚本 | ✅ |
| lockfile 一致性 | ✅ |
| 安全漏洞 | ⚠️ 1 high + 1 moderate |
| overrides 策略 | ⚠️ pnpm 11 失效 |
| 脆弱绑定 | ⚠️ dsh-genui GitHub 直链 |

**总体：可运行、结构健康；2 个安全漏洞 + overrides 迁移为优先跟进项。**

## 六.b 上游发布跟踪（初始核查）

| 包 | runtime/profile 当前 | registry latest | next | 结论 |
|----|---------------------|----------------|------|------|
| @deepseek-ai/dsh-base | 0.1.0-rc.6 | 0.0.1-rc.1 | 0.1.0-rc.6 | ✅ 宿主内置=next 线，无滞后 |
| @deepseek-ai/dsh-web-app | 0.1.0-rc.6 | 0.0.1-rc.1 | 0.1.0-rc.6 | ✅ 同上 |
| @deepseek-ai/dsh-agent | 0.1.0-rc.6 | 0.1.0-rc.6 | — | ✅ 一致 |
| @deepseek-ai/cordis | 4.0.1 | 4.0.1 | — | ✅ 一致 |
| @linxin666/dsh-web-ui-all | 0.1.16 | 0.1.19 | — | 🔼 semver 范围内可升（^0.1.16） |
| @liustack/modlens | 3.16.7 | 3.18.1 | — | 🔼 semver 范围内可升（^3.16.7） |
| dsh-better-sidebar | 0.12.2 | 0.12.3 | — | 🔼 semver 范围内可升（^0.12.2） |
| deeptide | 0.11.8 | 0.11.8 | — | ✅ 最新 |
| dsh-doc | 0.1.1 | 0.1.1 | — | ✅ 最新 |
| dsh-knowledge | 0.1.0 | 0.1.0 | — | ✅ 最新 |
| @xberg-io/xberg | 1.0.14 | 1.0.14 | — | ✅ 主包最新 |
| @omdsh-dev/dsh-genui | github 直链 0e756efb | **E404 未 npm 化** | — | 🔴 脆弱绑定坐实：registry 无此包，GitHub 直链为唯一来源 |

> 注：可升项均在各自 semver 范围内（低风险），不属紧急；升级走维护窗口 + 红绿灯 file:profiles/web。

## 七、后续行动清单

1. [ ] 与 c1111ffe 协作：迁移 overrides 到 pnpm-workspace.yaml（红绿灯 file:profiles/web）
2. [ ] 跟踪 zero-cli / transformers 上游，评估 sharp≥0.35 升级窗口
3. [ ] 跟踪 uuid≥11.1.1（zero-cli gaxios 链）修复
4. [ ] 监控 @xberg-io/xberg-darwin-arm64 是否发布 1.0.14 平台包
5. [ ] 监控 dsh-genui npm 化发布
6. [ ] 建立上游发布跟踪机制（registry 定时核查 + 可委派 4787d717）
