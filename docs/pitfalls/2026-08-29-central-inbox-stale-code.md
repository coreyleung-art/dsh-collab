# 2026-08-29 central-inbox 注入失联（插件更新未重启）

> 记录人: 星桥-mac-mini-协调者 · 状态: closed（待重启验证）

## 现象
- 两侧（MBP/i9）都收不到中枢注入消息
- i9 04:11 回传插件登记，中枢直到用户提问才查到（无人感知）

## 根因
- CLD 02:35 启动 → central-inbox lib/index.js 03:38 被修改（插件化对齐）→ CLD 未重启 → 旧代码在跑且 SSE 连接失效
- 无 central-inbox.log（插件未运行）+ CLD 无 8803 SSE 连接（lsof 实证）

## 影响
- 跨设备注入链路中断：i9/MBP 消息无法自动唤醒中枢
- 「漏信息」根因——用户提问才发现

## 修复
- 重启 CLD 加载新插件代码（待执行）
- 备用通道机制（upgrade-standby-channel-protocol-v1）：bb-sub 缓存 + central-wake 触发 + upgrade-replay 回放

## 教训（→ SOP 更新点）
**改插件文件后必须重启宿主验证**；**升级/维护期必须依赖备用通道**（L0-L2 守护层），不依赖 CLD 内插件

## 预防检查项
- [ ] 改插件后：重启 CLD + 验证 central-inbox.log 出现 + lsof 8803 有 CLD 连接
- [ ] 维护/升级前：确认 bb-sub.coordinator + central-wake 在线（备用通道就绪）
