# 2026-08-29 node-bridge v1.3.2 沙箱漏测模式（带 token vs 空 token）

> 记录人: 星桥-mac-mini-协调者 · 状态: closed

## 现象
- v1.3.1 带 token 时所有写入 value 变 {}（心跳/队列/notes 全空）、register 名字丢失
- 首版修复只测带 token 路径，空 token 模式生产心跳仍空 {}（mac-mini 心跳 value:{}）

## 根因
- bb.rs request() 构造：token_hdr 自带 \r\n + 格式串再补 → header 空行提前结束，Content-Length 被吞进 body
- 修复 v1.3.2 首版：只验证带 token 模式，漏测空 token（格式串 \r\n{}\r\n 空 token 时仍产生空行）

## 影响
- 生产 mac-mini 心跳 value 空（不影响功能但误导监控）
- MBP 升级时 identity 路径 SIGABRT 崩溃循环（待 i9 实证确认是否同源）
- 额外 debug 轮次消耗

## 修复
- v1.3.2 二次修复：token_hdr 自带 \r\n，格式串只放一个 {} 占位（空 token 无空行）
- 双向沙箱验证：无 token + 带 token 均 value 完整

## 教训（→ SOP 更新点）
**沙箱验证必须覆盖所有运行模式**（带 token/空 token、有无 --identity、生产参数组合），不能只测「主路径」

## 预防检查项
- [ ] 发布前沙箱验证：列出该二进制的所有运行模式，逐一测试
- [ ] 生产参数组合（--node-id + --identity + --no-llm）必须有沙箱覆盖
