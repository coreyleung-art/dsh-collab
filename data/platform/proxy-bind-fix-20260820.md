---
key: data/platform/proxy-bind-fix-20260820
domain: platform
author: session-582093dd
ts: 2026-08-20
---

# 反代启动竞态安全回归修复报告（2026-08-20）

## 问题
系统重启后反代（com.dsh.remote）启动时 Tailscale 应用尚未就绪，
ifconfig 查不到 100.x → 误绑 0.0.0.0:3081（LAN 暴露 + loopback 改写 = 配对门禁绕过风险）。

## 修复（~/.cld/tools/dsh-tailnet-proxy.mjs，红绿灯锁定+释放，语法校验通过）
1. 启动等待重试：waitForTailnetIp() 最多 60s（12×5s）等 Tailscale 就绪后再选绑定地址
2. 回退兜底：若仍 0.0.0.0，每 30s 复查，tailnet 出现后自动重绑到 tailnet IP

## 验证
- 当前绑定 100.120.203.20:3081（tailnet-only，PID 76361）
- GUI 端口 52074 发现正确；tailnet 200
- 全链路安全态恢复

## 遗留
- CLD 重签仍待用户终端执行（codesign verify 仍失败，Resources 内 bak 4 个）
