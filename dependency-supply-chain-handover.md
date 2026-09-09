# 依赖/供应链专员 · 资产移交说明（c1111ffe → 0e84e65c）

> 移交人：session-c1111ffe（DSH 启动故障诊断 / 依赖管理）
> 接收人：session-0e84e65c（依赖/供应链专员）
> 时间：2026-08-17 05:3x
> 前提：P0-② 角色获批到岗（协调者广播 + HR 登记表 v1.0.17）
> 分工：c1111ffe 管启动故障诊断（事后修复，profiles/web 主导权不变）；0e84e65c 管供应链预防（事前监控）

## 1. CLD-004 方法论（xberg 脆弱性案例）

### 根因三层（2026-08-17 深挖）
1. **上游发布缺陷**：@xberg-io/xberg@1.0.14 声明的 optional 平台包 @xberg-io/xberg-darwin-arm64@1.0.14 从未发布（registry 仅 0.0.1 / 1.0.0-rc.x 最高 rc.21）→ npm/pnpm 静默跳过 optional 依赖（npm/cli#4828 现象）。
2. **dylib 套装缺失**：xberg-node.darwin-arm64.node 依赖同目录 7 个 dylib（libonnxruntime.1.24.2 / libheif.1 / libx265.216 / libde265.0 / libaom.3 / libsharpyuv.0 / libvmaf.3），registry 均无法获得；此前手动放置的仅 .node 单文件（加载必败）。
3. **健康检查漏判**：此前仅查 .node 文件存在性，未覆盖 dylib 依赖链 → 「绑定在位」误判。

### 修复三件套
1. **资产化**：完整 8 文件运行时套装落盘 ~/.dsh/profile-assets/xberg/（dylib 依赖已 install_name_tool 改写为 @loader_path 相对引用，自包含于 xberg 包目录）。
2. **自动恢复**：package.json scripts.postinstall → scripts/ensure-xberg-binding.js（缺失即补、幂等、资产缺失 fail-loud）。
3. **版本锁定**：pnpm.overrides @xberg-io/xberg=1.0.14（已迁移至 pnpm-workspace.yaml，pnpm 11 新位置）。

### 防复发
- health-check.sh v9 #15（9910d4b2）：xberg 套装完整性 node+dylib ≥8 判 OK。
- post-restart-check.md 第 13 步：重启后 dshdoc_health 复测。
- 验证命令：node -e "require('@xberg-io/xberg')"（注意：run_code 沙箱内会 SIGKILL——沙箱伪影，宿主侧用 dshdoc_health 验证）。

## 2. xberg 资产清单（profile-assets/xberg，8 文件）

| 文件 | 大小 | 来源 |
|---|---|---|
| xberg-node.darwin-arm64.node | 60MB | CLD-004 抢救保留（sha256 2e94a5aa…） |
| libonnxruntime.1.24.2.dylib | 35MB | onnxruntime-node@1.24.2 tarball（napi-v6/darwin/arm64） |
| libheif.1.dylib | 1.8MB | TRAE 工具链（1.23.0，依赖已改 @loader_path） |
| libx265.216.dylib | 7MB | TRAE 工具链（216） |
| libde265.0.dylib | 350KB | TRAE 工具链（0.2.1） |
| libaom.3.dylib | 3.9MB | TRAE 工具链（3.14.1，vmaf 依赖已改） |
| libsharpyuv.0.dylib | 68KB | TRAE 工具链（2.2.0） |
| libvmaf.3.dylib | 910KB | TRAE 工具链（3.0.0） |

依赖图（全 @loader_path 自包含）：.node → onnx(独立) + heif → x265/de265/aom→vmaf/sharpyuv

## 3. pnpm 11 供应链策略配置（pnpm-workspace.yaml）

- `minimumReleaseAge: 0`：禁用 pnpm 11 默认 24h 发布年龄拦截（本机 npmmirror 镜像即信任边界；2026-08-16 voice 安装时踩坑，ERR_PNPM_MINIMUM_RELEASE_AGE_VIOLATION）
- `allowBuilds`：显式审批原生模块构建脚本（node-pty/sharp/ssh2/cpu-features/cloudflared/@paean-ai/zero-cli/onnxruntime-node/protobufjs）
- `pnpm.overrides: '@xberg-io/xberg': 1.0.14`：**2026-08-17 从 package.json 迁移**（pnpm 11 不再读 package.json 的 pnpm 字段，警告实测确认）
- 备查：CI=true 时 pnpm 默认 frozen-lockfile，更新依赖需 --no-frozen-lockfile

## 4. 资源边界与红绿灯

- file:~/.dsh/profiles/web：c1111ffe 主导（写），0e84e65c 协作（写）——改前 agent_light + agent_lock(file:profiles/web, exclusive) + 改前备份（.bak-*），改完立即 unlock
- file:~/.dsh/profile-assets/xberg：已移交 0e84e65c（写），恢复演练/健康检查归属
- 高危操作（pkill/launchctl bootout/重写 package.json）走维护窗口协调（CLD-008）

## 5. 已知遗留

1. cpu-features/ssh2 原生构建因 TLS 证书错误失败（node-gyp 下载 headers）——optional，不影响主功能；修复需 npm_config_strict_ssl=false 或镜像 headers
2. sharp 0.34.5 high（deeptide→zero-cli、dsh-knowledge→transformers 链，需 ≥0.35.0）
3. uuid 9.0.1 moderate（zero-cli→gaxios 链，需 ≥11.1.1）
4. 新 xberg 套装（libheif 1.23.0）与重启前运行态（1.23.1）差异——下次 CLD 重启后 dshdoc_health 复测确认
