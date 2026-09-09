# 2026-08-29 跨设备投递错通道（agent_send/notes-mac-mini 误用）

> 记录人: 星桥-mac-mini-协调者 · 状态: closed

## 现象
- 给 MBP 的信息（CLD 分发/升级指令）用 agent_send 发送 → 全部 queued（targetLive:false）
- 写黑板用 notes/mac-mini/（中枢自己的收件箱）→ MBP 收不到
- 用户发现：MBP 实际没收到 send

## 根因
1. **agent_send 是同宿主通道**（mac-mini 内部跨会话），对远程设备（MBP/i9）无效——R002 通道边界
2. **黑板定向应写 notes/<目标node>/**（MBP 监听 notes/mbp/），我误写 notes/mac-mini/（中枢收件）

## 影响
- MBP 未收到 CLD v0.3.1 分发 + node-bridge v1.3.2 升级指令（延迟）
- 用户需指出才发现

## 修复
- 重发到正确通道：notes/mbp/（MBP bridge 监听）+ 验证
- 教训固化：跨设备定向必须 notes/<目标node>/，agent_send 仅同宿主

## 教训（→ SOP 更新点）
**跨设备投递三查**：① 目标是远程设备？→ 用黑板 notes/（非 agent_send）② 写 notes/<目标node>/（非自己收件箱）③ 投后验证目标 bridge 能落盘

## 预防检查项
- [ ] agent_send 前确认目标是同宿主会话（非远程设备）
- [ ] 黑板定向键用 notes/<目标node>/<topic>
- [ ] 投递后检查目标节点心跳/落盘确认
