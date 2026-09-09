#!/bin/bash
# 蓝图架构图管理器 · 一键启动（幂等：已在跑则只开浏览器）
PORT=${PORT:-8798}
URL="http://127.0.0.1:$PORT"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/tmp/bb-gallery.log

# 已在运行？直接开浏览器
if curl -s -o /dev/null --max-time 2 "$URL/api/overview"; then
  echo "✅ 已在运行: $URL"
  open "$URL"
  exit 0
fi

# 启动
cd "$SCRIPT_DIR/.."
nohup python3 scripts/bb-blueprint-gallery.py --port $PORT > "$LOG" 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if curl -s -o /dev/null --max-time 2 "$URL/api/overview"; then
    echo "✅ 已启动: $URL  (日志: $LOG)"
    open "$URL"
    exit 0
  fi
done
echo "❌ 启动失败，日志:"; tail -20 "$LOG"
exit 1
