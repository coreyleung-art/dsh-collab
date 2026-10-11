# CLD 热更新规划：更新包下载 + 受控提示性重启（2026-10-06 · 星桥）

> 用户需求：CLD 是否可规划为「热更新包下载 + 受控提示性重启」？参考业界解决方案。
> 结论：可行，且大部分基础设施今晚已就绪。本规划分「现状盘点 → 业界对标 → 目标架构 → 安全链 → 治理对接 → 阶段计划 → 资源评估」。

## 一、现状盘点（2026-10-06 实测）

| 组件 | 现状 | 说明 |
|---|---|---|
| 更新引擎 | ✅ 已内嵌 | CLD.app 内 Squirrel.framework（Electron 更新器）在架 |
| 换装执行 | ✅ 已有脚本 | MBP 的 swap-cld-to-notarized.py：等 CLD 退出 → 备份 → ditto 替换 → 三项复验 → 落 installed-baseline-after.json（不自动重启）；换装守护已就位 |
| 签名/公证链 | ✅ 已跑通 | Developer ID（无头可用）+ hardened runtime entitlements + notarytool + stapler；**24/24 Mach-O 全签教训**（--deep 漏 node_modules 内嵌二进制、空格路径循环 bug 均已解） |
| 回滚点 | ✅ 已有 | guard/backups/CLD.app.bak-20261006（ditto 全量 534M）+ swap 脚本的基线对照 |
| 受控重启治理 | ✅ 已有 | 重启征询协议（agent_restart_request/ack/go）+ 黑板 restart-notice 票 + hb-watchdog 语义判官（up-new/up-same/offline≤down_from） |
| 下载与提示层 | ❌ 缺失 | 本规划核心增量 |

## 二、业界对标（2026-10-06 检索）

| 方案 | 模式 | 可借鉴点 |
|---|---|---|
| Sparkle「Gentle Reminders」 | 下载后温和提示 | macOS 事实标准：后台下载 → 不打断 → 「Install and Relaunch / Later」；见 sparkle-project.org/documentation/gentle-reminders/ |
| VS Code 更新徽标 | 后台下载 + Reload 徽标 | 不弹窗，状态栏徽标提示「重启生效」；用户主导重启时机；见 microsoft/vscode PR #325942（update badge） |
| Chrome「Relaunch」气泡 | 后台下载 + 重启气泡 + 分阶段放量 | 分级提示（气泡→菜单）；staged rollout 按百分比灰度，见 support.google.com/chrome |
| electron-updater | autoDownload / autoInstallOnAppQuit / 灰度 | 退出时静默安装、delta blockmap 增量、强制更新门限 |
| K8s node drain 类比 | 排空→维护→回归 | 我们的受控重启协议 = 本域版 drain：先全端 ack、再动宿主、后健康验证 |

共同模式：**下载与安装解耦、安装与重启解耦、提示分级、可灰度、失败可回滚**。

## 三、目标架构：三层更新闭环

```
[下载层]  release channel(GitHub/Gitee Release 或静态 HTTPS)
   │ 后台静默下载更新包（delta 可选）
   │ 校验：Developer ID 签名 + 公证票据 + SHA256 manifest + 版本单调
   ▼
[暂存] ~/.dsh/updates/pending/<version>/
   │ 校验失败 → 丢弃 + 上报（不打扰用户）
   ▼
[提示层] 分级提示（用户可配置强度）
   ① 徽标级：状态栏「更新已就绪」（VS Code 式，默认）
   ② 气泡级：「重启安装更新」气泡（Chrome 式，可「稍后」）
   ③ 强制级：超过 N 天/安全修复 → 弹窗限期（可延但不可无限延）
   ▼ 用户确认 / 或下次退出自动装（autoInstallOnAppQuit）
[受控重启层]（复用现有治理）
   1. 落黑板 restart-notice 票（其他设备 hb-watchdog 免误报）
   2. 全端 agent_restart_request/ack（在线的全 ack）
   3. 会话 checkpoint flush（~/.dsh sessions 落盘）
   4. quit CLD → swap 脚本换装 → 复验（cdhash/stapler/spctl）
   5. relaunch → 启动后自检（exit-marker C1 + 挂载活体表 + health C1-C7）
   6. 失败 → 自动 ditto 回滚上一版本 + 回卡告警
```

## 四、更新包安全链（签名侧 SOP，今晚教训内化）

1. 更新制品必须走完整签名链：**全部内嵌 Mach-O 逐个签**（find -exec file + | grep Mach-O 清单，null 分隔防空格路径）→ 外层 --deep → Developer ID + hardened runtime entitlements（allow-jit/allow-unsigned-executable-memory/disable-library-validation/allow-dyld-environment-variables）→ notarytool --wait → stapler staple → spctl 验收
2. 分发只发 **stapled zip**（MBP 教训：装订前 zip 勿分发）
3. 时间戳依赖：codesign --timestamp 依赖 HTTPS timestamp.apple.com——下载层要容忍该服务劣化（重试/退避；本次 10-06 实测该端点 https 全挂即为此类风险）
4. 发布判据自动化：release-gate.py 全量 PASS（MBP 侧 159/159 范式）+ 星桥机械复核（R046 第三方在场）
5. 更新源变更 = 通道变更 → 先过 channel-gate（R036），不留私设旁路

## 五、阶段计划

| 阶段 | 内容 | 依赖 | 工作量 |
|---|---|---|---|
| P0（本周） | 更新制品签名 SOP 固化（工具化：release 脚本 + gate 脚本落 mac-mini）；0.1.1 换装收尾（MBP 制品 scp → 重启窗口换装） | MBP 归位 | 小 |
| P1 | 下载层：release channel 探测（HTTPS 优先）→ 静默下载 → 校验（签名+票据+manifest）→ 暂存；校验失败静默丢弃 | 通道经 channel-gate 登记 | 中 |
| P2 | 提示层：徽标/气泡/强制三级 + autoInstallOnAppQuit 选项 | P1 | 中 |
| P3 | 受控重启编排自动化：票→ack→flush→quit→swap→relaunch→自检→失败回滚 一条命令 | 复用现有脚本 | 中 |
| P4（可选） | delta 增量（blockmap）+ 灰度放量（staged rollout %） | P1-P3 稳定后 | 大 |

## 六、资源评估

- 新增代码：P0-P3 约 1-2 个插件/脚本（下载校验器 + 提示 UI + 编排脚本），复用 Squirrel/swap/restart 协议，**无需新服务器**（release 走 GitHub/Gitee Release 或现有 nginx）
- 风险点：时间戳服务劣化（重试退避）、更新后签名失效（P0 SOP 覆盖）、重启窗口打断会话（受控协议已覆盖）
- 与星台/外卖等 app 更新体系同构，可共用 release 通道与 gate 工具

## 七、遗留

- MBP 0.1.1 制品与脚本待 scp 到位（用户批准通道）
- 更新通道 URL 确定后过 channel-gate 登记
- P0 完成后把「更新后重签」并入 harness-updater 流程
