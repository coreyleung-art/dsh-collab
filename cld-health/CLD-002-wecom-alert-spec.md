# CLD-002 看门狗 → 企微告警接入规范（外发用例 #10）

> 提供方：session-3d490920（CLD/dsh 运维排障）· 2026-08-17
> 对接方：session-92623479（外链通讯员，channel.send / wecom aibot）
> 状态：路径定稿（aibot 通道可用）后即交付接入点

## 触发条件（3 类）
1. **异常退出检测**：CLD 启动时读 exit-marker.json，发现上次运行 cleanExit!=true → 告警。
   来源：~/.cld/logs/exit-marker.json + dsh-web.log `[exit-trace] PREVIOUS CLD RUN ... DID NOT EXIT CLEANLY`。
2. **心跳丢失**：heartbeat.json（~/.cld/logs/）最后 iso 距今 >90s 且 CLD 主进程不存在 → 告警（适合外部巡检触发，如 health-check.sh）。
3. **故障恢复通知**：dsh web 服务器模式新 boot 成功（dsh-web.log 出现 `dsh web: http://127.0.0.1:<port>`）且上一轮曾异常 → 恢复通知（可选）。

## 文本模板（markdown）

### 模板 A · 异常退出
```
⚠️ CLD 异常退出检测
- 时间：{detectedAt}
- 上一运行 PID：{prevPid}
- 启动时间：{prevStartedAt}
- 最后心跳：{lastHeartbeat}（无=n/a）
- 事件：PREVIOUS CLD RUN DID NOT EXIT CLEANLY（崩溃或外部强杀？）
- 现场：~/.cld/logs/exit-marker.json · dsh-web.log
- 建议：SIGKILL 场景排查外部 pkill/内存压力；崩溃场景查看 .ips 报告
```

### 模板 B · 心跳丢失
```
⏱️ CLD 心跳丢失（>90s）
- 检测时间：{detectedAt}
- 最后心跳：{lastHeartbeatIso}
- 状态：CLD 主进程不在/心跳停滞
- 建议：检查进程与 launchd（com.cld.server）
```

### 模板 C · 故障恢复（可选）
```
✅ CLD/dsh web 已恢复
- 恢复时间：{detectedAt}
- 地址：http://127.0.0.1:{port}
```

## 接入方式
- `channel.send(channel="wecom", text=<模板填充后的 markdown>)`
- 建议限流：同类告警 10 分钟内去重（同一异常只推一次，恢复后解除）
- 触发源建议：由本会话或 health-check 巡检调用，不常驻轮询

## 字段来源
- exit-marker.json：pid / startedAt / cleanExit / exitCode / exitSignal / endedAt / reason
- heartbeat.json：pid / ts / iso
- dsh-web.log：[exit-trace] 行