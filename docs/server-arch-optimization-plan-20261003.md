# 服务器架构优化计划（阶段三·⑥ · 2026-10-03 用户指示）

> 依据：业界基准调研（Mercure SSE 重放 / Redis AOF 持久化 / token 轮换三原则 / systemd 护栏）+ 服务器专项复审实测。
> 状态：A 待协调窗口 · B 执行中 · C 评估中

## A. 黑板写端鉴权启用（token=on flip）

现状（复审实测）：8792 写端 token=off，无 token PUT → 200（公网匿名可写任意键，含注入键）。

| 步骤 | 内容 | 状态 |
|---|---|---|
| A0 | 板端多端白名单（BLACKBOARD_TOKENS 集合，v0.6.12 已部署） | ✅ 完成 |
| A1 | 我侧全部合法写方加认证头（hb-fwd/sync-up/central-wake/bb-card-send；bus-bridge 板写=服务器回环豁免无需改） | ✅ 完成 |
| A2 | 通知 MBP 侧写方同步加头（自生成 token + 哈希互证） | ✅ 已发卡（board-write-auth-flip-coordination） |
| A3 | 服务器 comm-server 单元加 `Environment=BLACKBOARD_TOKEN=<既有 token>`（先不重启） | 待 |
| A4 | 两端就绪后 flip（重启 comm-server） | 待 |
| A5 | 正负验收：无头 PUT 401 / 带 token 200 / i9 豁免路径（nodes/i9、notes/i9、tasks?node=i9）仍 200 / MBP 写实测 | 待 |
| 回滚 | 摘除 Environment 行重启即回 token=off | — |

## B. token 异常审计（bus-bridge 用量计数 + 突变告警）

依据：业界第三原则（Corsair/Zylos：用量突变→告警）。

| 步骤 | 内容 | 状态 |
|---|---|---|
| B1 | bus-bridge.js：按 token 计数（sha256 前8位）+ 10 分钟窗口落盘 token-usage.jsonl | ✅ 已部署（active） |
| B2 | 突变告警：>10x 且 ≥20 次 ⇒ stderr + jsonl spike 标记 + 黑板卡 data/ops/token-anomaly-<ts>（回环写） | ✅ 已部署（active） |
| B3 | 验收：正常流量零告警；模拟突增出告警（控制变量） | 待 |

## C.（增强）systemd 沙箱项评估

| 项 | 评估 | 状态 |
|---|---|---|
| RestrictSUIDSGID | 全部 comm 单元无 setuid 需求 → 可加 | ✅ 已加（10 单元 drop-in） |
| PrivateTmp | 无共享 /tmp 需求 → 可加 | ✅ 已加 |
| ProtectSystem/ProtectHome | bus-bridge 需写 /opt/comm-layer → ProtectSystem=full 可加（读只读） | 评估中 |

## 验收总则

每步：实测证据 + 回滚点 + 变更门登记（配额满则协调者裁决留痕，如 2026-10-03 前例）。
