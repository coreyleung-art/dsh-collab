# MTM 发布与权限检测工具（DSH 插件 + CLI）

> 维护：采集/IM会话（de7b29de）· 2026-08-29
> 背景：MTM 本地网络弹窗反复出现根因 = 每次打包 ad-hoc 重签 → macOS TCC 权限重置；本工具集根治

## 一、稳定签名（根治 TCC 弹窗）

### 问题根因
- `npm run package` 每次 ad-hoc 重签 → macOS 视为新 App → 本地网络/屏幕录制等 TCC 权限重置 → 反复弹窗
- 点「允许」只对旧签名生效，新签名又要求一次

### 根治方案
- **自建稳定签名证书**（MTM Local Signing）：签名指纹固定 → 权限不重置
- 重建证书：`bash scripts/setup-signing.sh`（openssl 生成 + 导入钥匙串 + 信任）
- 打包脚本自动优先稳定证书（Apple Development 有则用之，无则 MTM Local Signing）

## 二、DSH 插件（mtmrel-1）

宿主插件，注册 2 个模型工具：

### mtm_release
- **用途**：一键发布 MTM（打包 → 稳定签名 → 重启 → 10/10 验证 → TCC 检测）
- **参数**：无
- **输出**：`{ ok, output }`（发布过程输出，末尾摘要）
- **耗时**：约 1-3 分钟
- 等价 CLI：`npm run release`

### mtm_tcc_check
- **用途**：检测 MTM 本地网络授权状态（TCC）
- **参数**：无
- **输出**：`{ ok, result }`（授权状态；无完全磁盘访问时降级为手动检查指引）
- 等价 CLI：`bash scripts/tcc-check.sh`

## 三、CLI 工具集（不依赖插件，即刻可用）

| 命令 | 用途 |
|------|------|
| `npm run release` | 一键发布：打包+稳定签名+重启+10/10 验证+TCC 检测 |
| `bash scripts/tcc-check.sh` | 本地网络授权检测 |
| `bash scripts/setup-signing.sh` | 重建稳定签名证书（防丢失） |
| `npm run package` | 仅打包（自动签名选择） |

## 四、TCC 检测逻辑

- 读 `~/Library/Application Support/com.apple.TCC/TCC.db`（kTCCServiceLocalNetwork + bundle com.waimai-store.manager）
- 结果：2=已授权 ✅ / 1=被拒 ❌ / 0=未询问（下次弹窗点允许）/ 无权限=手动指引
- 注意：读 TCC.db 需「完全磁盘访问」——终端未授权时降级为指引（不报错）

## 五、使用场景

1. 日常发版：`mtm_release`（或 npm run release）
2. 用户反馈权限弹窗：`mtm_tcc_check` 确认授权状态
3. 证书丢失/重装系统：`setup-signing.sh` 重建（一次性）
4. 新会话调 DSH 工具：mtm_release / mtm_tcc_check（需会话刷新后可见）

## 六、文件位置

- 插件：DSH 动态插件 mtmrel-1（pkg-8 running）
- 脚本：meituan-multi/scripts/{build-release,setup-signing,tcc-check}.sh
- 打包签名：meituan-multi/scripts/package-app.sh（签名选择逻辑）
