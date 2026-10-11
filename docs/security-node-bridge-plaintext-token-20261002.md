# 安全处置建议 · node-bridge plist 明文凭据

> 2026-10-02 · mac-mini · 星桥（session-fa1f9150）
> **状态**：仅建议，**未动手**（涉及凭据处理与部署，需用户批准；且密钥可能需轮换）。

## 事实
- **全 plist 凭据审计（2026-10-02 第 4 轮）发现两处**明文凭据：
  1. `com.dsh.node-bridge.mac-mini.plist` —— `ANTHROPIC_AUTH_TOKEN`（node-bridge 的 llm_loop 用）；
  2. `com.external-link.wecom-inbox.plist` —— 疑似企微/外链接口的凭据键（**本轮新发现，未细查值**）。
  （8 个 bb-sub plist 审计**干净**。）
- `~/Library/LaunchAgents/com.dsh.node-bridge.mac-mini.plist` 内含**明文** `ANTHROPIC_AUTH_TOKEN`
  （node-bridge 的 `llm_loop` 调用 LLM 用）。
- 该 plist 属用户私有（`~/Library/LaunchAgents`），非 world-readable，但：
  - 今天读取 plist 时该值已进入会话日志（工具输出）；
  - launchd 配置、备份（`guard/backups/…plist.bak-good-*` 9 份）都会携带它。
- 官方防御规则（`docs/defensive-patterns.zh.md`）：「绝不将环境变量或可预测路径暴露给不可信输出」，
  凭据应放 0700 私有目录 / 0600 文件 / Keychain。

## 建议处置（按代价排序）

| 步骤 | 动作 | 风险 |
|---|---|---|
| 1 | **轮换该密钥**（它已出现在会话日志与备份里，应视为泄露） | 需在 DeepSeek 控制台重发 + 更新两处（plist 与任何其它使用点） |
| 2 | 把 token 移到 `~/.dsh/credentials/node-bridge-llm.env`（**0600**），plist 里只留一个**包装脚本**：脚本 `source` 该文件再 exec node-bridge；或改用 launchd `EnvironmentVariables` 之外的机制 | 低（需短暂重启 node-bridge；它有 60s 心跳自恢复） |
| 3 | 清理含密钥的**备份**：`guard/backups/…com.dsh.node-bridge.mac-mini.plist.bak-good-*`（换完密钥后这些备份里的旧值即失效，可归档或删除） | 低 |
| 4 | 审计其它 plist（8 个 bb-sub 等）是否同样携带明文凭据 —— **待查** | 只读 |

## 不做的理由（当前）
- 涉及凭据生命周期，超出本轮目标（通信架构资源治理）的操作权限边界；
- node-bridge 在三台设备的跨设备通道上，改它的启动配置需要与轮换步骤配合，否则会让旧密钥"看起来还在用"。

## 下一步（等用户一句话）
「按建议做」= 执行步骤 1→4；「只做 2-3」= 不轮换，仅移出 plist + 清备份。
