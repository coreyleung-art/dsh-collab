# central-inbox SSE 重连缺陷修复

> 1e54d56d · 2026-09-02 · 排查基于黑板 central-inbox-test + MBP bugfix 记录 + 8803 实测

## 排查结论
1. **AbortSignal.timeout(0) 缺陷**：MBP 已定位（0ms 立即 abort），mac 侧已同步修复（无 signal fetch + token headers）✅
2. **8803 实测**：hello 帧（无 key 安全丢弃）+ i9 heartbeat 高频推送（nodes/ 前缀不匹配丢弃）+ **无周期 keepalive**
3. **新发现缺陷**（本次修复）：
   - 服务端关流（done=true）不落盘 → stdout 被 CLD 丢弃，排查无痕
   - 退避指数增长无抖动 → 多实例同时重连风暴
   - 无假活检测 → TCP 断开但 reader 未感知时永久挂起

## 修复（4 项）
1. done=true 时 logLine 落盘（可观测）
2. 退避加抖动 ±20%（防风暴）
3. 假活检测：45s 无数据帧 → 强制取消重连（黑板桥无 keepalive，用数据活性判断）
4. 数据到达更新 lastDataAt + hbTimer 清理

语法验证通过（node --check）。生效：CLD 重启后加载。
