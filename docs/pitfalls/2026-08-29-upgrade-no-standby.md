# 2026-08-29 升级期无备用通道导致消息静默

> 记录人: 星桥-mac-mini-协调者 · 状态: closed

## 现象
- CLD 内插件失联期间，i9 04:25 的「v1.3.2 升级阻塞」消息无人感知
- 备用通道机制建立后，upgrade-replay.py dry-run 发现 3 条未处理（含该阻塞消息）

## 根因
- 无备用通道机制：升级/维护期 CLD 内插件失联 → 消息只进黑板，无缓存回放兜底

## 影响
- i9 升级阻塞 7 分钟无人处理（直到用户问 i9 插件情况才触发排查）

## 修复
- 建立 upgrade-standby-channel-protocol-v1：L0 黑板 / L1 node-bridge / L2 bb-sub+central-wake（守护层全程在线）/ L3 upgrade-replay 回放
- 实战验证：回放工具 dry-run 捞回 i9 阻塞消息 → 发布 GitHub release 解除阻塞

## 教训（→ SOP 更新点）
**任何升级/维护都必须先确认备用通道在线**；消息缓存 + 恢复回放是升级期零失联的保障

## 预防检查项
- [ ] 升级前：确认 bb-sub/central-wake 在线 + 记录水位（coordinator.seen）
- [ ] 升级后：upgrade-replay.py 回放 + 更新水位
