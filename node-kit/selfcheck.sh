#!/usr/bin/env bash
# node-kit selfcheck.sh — 健康自检三项（守护/队列/心跳）
echo "══ node-kit 自检 ══"
echo "① 守护进程:"
pgrep -fl device-daemon.py || echo "   ❌ 守护未运行"
echo "② 服务器队列:"
curl -s -m 5 http://106.53.214.108:8791/bus/status 2>/dev/null | head -c 200 || echo "   服务器不可达"
echo ""
echo "③ 心跳: 查黑板 devices/<node> heartbeat 时间戳"
