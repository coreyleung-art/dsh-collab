#!/bin/bash
# mbp-log-guard.sh v1.0 — 日志大小守卫：超限即截断，防止 launchd stdout 无界写满磁盘
# 2026-08-27 事故根因：node-bridge stdout → mbp-agent.log 涨到 21GB 占满数据卷
MAX=104857600  # 100MB
GUARD_LOG=/Users/coreyleung/dsh-collab/logs/log-guard.log
for f in /Users/coreyleung/dsh-collab/devices/mbp-agent.log \
         /Users/coreyleung/dsh-collab/devices/mbp-agent.err \
         /Users/coreyleung/dsh-collab/devices/node-bridge.log; do
  if [ -f "$f" ]; then
    sz=$(stat -f%z "$f" 2>/dev/null || echo 0)
    if [ "$sz" -gt "$MAX" ]; then
      truncate -s 0 "$f" 2>/dev/null
      echo "$(date '+%Y-%m-%d %H:%M:%S') truncated $f ($sz bytes)" >> "$GUARD_LOG"
    fi
  fi
done
