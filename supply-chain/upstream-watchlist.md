# 上游发布跟踪清单（依赖/供应链专员维护）

- 维护人：session-0e84e65c（依赖/供应链专员）
- 基线：2026-08-17（R1 首轮核查）
- 核查方式：`npm view <pkg> version/dist-tags --registry=https://registry.npmjs.org`（npmmirror 无 audit endpoint，核查走官方 registry）
- 变更记录：见 supply-chain-baseline-r1.md 及后续 R 系列报告

## A 类：宿主内置（CLD runtime 提供，@deepseek-ai/*）

| 包 | runtime 版本 | registry next | 状态 |
|----|-------------|---------------|------|
| @deepseek-ai/dsh-base | 0.1.0-rc.6 | 0.1.0-rc.6 | ✅ 同步 |
| @deepseek-ai/dsh-web-app | 0.1.0-rc.6 | 0.1.0-rc.6 | ✅ 同步 |
| @deepseek-ai/dsh-agent | 0.1.0-rc.6 | 0.1.0-rc.6 | ✅ 同步 |
| @deepseek-ai/dsh-tools | 0.1.0-rc.6 | — | ✅ 同步 |
| @deepseek-ai/cordis | 4.0.1 | 4.0.1 | ✅ 同步 |

> 宿主包升级随 CLD.app 发布节奏，不作为 profile 依赖维护。

## B 类：profile 直接依赖（registry 可升性）

| 包 | 当前锁定 | registry latest | 可升？ | 备注 |
|----|---------|-----------------|--------|------|
| @linxin666/dsh-web-ui-all | 0.1.16 | 0.1.19 | 🔼 ^0.1.16 范围内 | 低风险，维护窗口评估 |
| @liustack/modlens | 3.16.7 | 3.18.1 | 🔼 ^3.16.7 范围内 | 低风险，维护窗口评估 |
| dsh-better-sidebar | 0.12.2 | 0.12.3 | 🔼 ^0.12.2 范围内 | 低风险 |
| deeptide | 0.11.8 | 0.11.8 | — | ✅ 最新 |
| dsh-doc | 0.1.1 | 0.1.1 | — | ✅ 最新 |
| dsh-knowledge | 0.1.0 | 0.1.0 | — | ✅ 最新 |
| @xberg-io/xberg | 1.0.14 | 1.0.14 | — | ✅ 主包最新 |

## C 类：脆弱绑定监控（高危，定期重点核查）

| 包 | 绑定方式 | 风险 | 缓解 | 监控动作 |
|----|---------|------|------|---------|
| @omdsh-dev/dsh-genui | GitHub 直链 codeload 0e756efb | 🔴 registry E404，无 npm 版本 | lockfile 已固化 commit | 每周查 npm registry 是否发布；发布即切换 |
| @xberg-io/xberg-darwin-arm64 | optional 平台包 | 🟢→**已解除**：1.0.14 已发布（2026-08-17 官方 registry 确认 6 平台全发布） | 本地资产恢复仍保留作兜底 | 待 npmmirror 镜像同步后，评估移除 override+postinstall 降级为纯 registry 依赖 |
| @xberg-io/xberg-linux-arm64-gnu | 同上 | 🟢→已解除（同上） | 同上 | 同上 |
| @xberg-io/xberg-win32-x64-msvc | 同上 | 🟢→已解除（同上） | 同上 | 同上 |

> **2026-08-17 重大事件**：xberg 上游补发了全部平台包 1.0.14（darwin-arm64 / linux-arm64-gnu / linux-x64-gnu / linux-x64-musl / linux-arm64-musl / win32-x64-msvc 全部确认）。xberg 案例的「平台包发布缺失」脆弱性已由上游修复。本地资产恢复方案（CLD-004 postinstall）作为兜底保留；等 npmmirror 镜像同步后可在维护窗口评估移除 overrides+postinstall 简化供应链（仍需 dsh-doc 精确声明 1.0.14 验证）。

## D 类：安全漏洞跟踪

| 包 | 脆弱版本 | 当前 | 修复版本 | 路径 | 状态 |
|----|---------|------|---------|------|------|
| sharp | <0.35.0 | ~~0.34.5~~ → **0.35.3** | ≥0.35.0 | deeptide→zero-cli；dsh-knowledge→transformers | ✅ **已修复（2026-08-18 CLD-014）** |
| uuid | <11.1.1 | 9.0.1 | ≥11.1.1 | deeptide→zero-cli→gaxios | ⚠️ 待 zero-cli 上游升级，低优先级（audit 现仅此 1 moderate） |

> **2026-08-18 CLD-014 落地并验收**：pnpm-workspace.yaml **顶层** `overrides: sharp: 0.35.3`（pnpm 11 要求顶层，非嵌套 pnpm: 块——本次发现 xberg overrides 迁移时的嵌套写法同样不生效，已一并修正为顶层）。验证：sharp 0.35.3 全链生效（lockfile+node_modules+require）、audit high 消除（2→1 moderate）、frozen-lockfile/bundle 树/embedding 回归通过、**QA 验收 PASS #017**（acceptance-20260818-cld014-sharp.md）。备份 .bak-sharp-20260818-011251。

## E 类：已知遗留（c1111ffe 移交，2026-08-17）

| 项 | 说明 | 影响 | 处置 |
|----|------|------|------|
| cpu-features/ssh2 原生构建失败 | node-gyp 下载 headers TLS 证书错误 | optional，不影响主功能 | 修复需 npm_config_strict_ssl=false 或镜像 headers |
| libheif 版本差异 | 新套装 1.23.0 vs 重启前运行态 1.23.1 | 需复测确认 | 下次 CLD 重启后 dshdoc_health 复测 |
| 沙箱 SIGKILL 伪影 | run_code 沙箱内 require xberg 会 SIGKILL | 验证误导 | 宿主侧用 dshdoc_health 验证 |

> 移交文档：~/dsh-collab/dependency-supply-chain-handover.md（CLD-004 方法论三层根因 + 修复三件套 + pnpm 11 策略备查）

## 供应链策略待办（与 c1111ffe 协作）

1. pnpm 11 overrides 迁移：✅ 已完成（2026-08-17 c1111ffe 执行迁移至 pnpm-workspace.yaml，本角色验证通过）
2. dsh-genui npm 化后切换 registry 依赖
3. xberg 平台包 1.0.14 发布后简化 postinstall（待 npmmirror 同步评估）
4. sharp/uuid 升级窗口跟踪（sharp 方案已备：overrides 0.35.3）

## 操作红线（加固/重建 node_modules 时）

1. **保留全部插件条目**：package.json 的 dependencies（link:/file: 插件）+ dsh.profile.bundles 条目**必须完整保留**——尤其 dsh-plugin-voice（移除则 host 路由 /voice/inbox 失效）、dsh-plugin-waimai、dsh-plugin-repo-pipeline 等全部 link 插件。仅允许增改 overrides/版本，禁止删除任何插件注册条目（3221f810 提醒，登记表 §5 热点）。
2. **手改资产保护**：`node_modules/@linxin666/dsh-pet/` 内有手改（assets/whale/spritesheet.webp 贴图 + lib/client.js 文案，宠物 enabled:false 禁用态）——pnpm 重装/postinstall 可能覆盖还原。恢复备份在 ~/.dsh/pet-backup/（75815fa9）。重装前如需保留定制，先复制备份或告知 75815fa9 恢复。
3. **禁止 git clean -x\* on 插件工作区**（2026-08-17 根因调查新增）：repo-pipeline 等 link 插件 workspace 的 node_modules 在 .gitignore 中，仅 `git clean -xdf/-fdx`（-x 清 ignored）会删除——**严禁对任何 dsh-plugin-\* 工作区执行 -x 级 git clean**（QA 冒烟曾反复触发 node_modules 丢失，第 3 次实证）；需要纯净环境用 `npm ci`（lockfile 快速重建）替代；冒烟流程已对齐（ffb7c3ab）。
4. 改 package.json/cordis.patch.yml 前备份 .bak-*，走红绿灯 file:profiles/web + 维护窗口（CLD-008）。
5. postinstall（ensure-xberg-binding.js）必须保留——xberg 资产恢复兜底。
6. CI=true 时 pnpm 默认 frozen-lockfile，更新依赖需 --no-frozen-lockfile。
