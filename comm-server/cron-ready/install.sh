#!/bin/bash
# install.sh — 2 cron 装载（R036 门合规：先 channel_gate register 再动 launchd）
# 执行时机：launchd-daemons 配额滚动后（10-04 窗口）
set -e
for plist in com.dsh.cron.bus-triage.plist com.dsh.cron.queue-condense.plist; do
  cp "$(dirname "$0")/$plist" ~/Library/LaunchAgents/
  launchctl unload ~/Library/LaunchAgents/$plist 2>/dev/null || true
  launchctl load ~/Library/LaunchAgents/$plist
  launchctl list | grep -q "$(basename $plist .plist)" && echo "✓ $plist loaded"
done
echo "验证（语法）:"
for p in ~/Library/LaunchAgents/com.dsh.cron.bus-triage.plist ~/Library/LaunchAgents/com.dsh.cron.queue-condense.plist; do plutil -lint "$p"; done
