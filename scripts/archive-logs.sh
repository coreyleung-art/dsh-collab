#!/usr/bin/env bash
# archive-logs.sh — 月度日志归档（launchd 每月 1 日 03:00）
set -u
LOGS=~/dsh-collab/logs
MONTH=$(date +%Y-%m)
DEST="$LOGS/archive/$MONTH"
mkdir -p "$DEST"
# 移动 >30 天的 jsonl/日志（保留目录结构）
find "$LOGS"/{tools,plugins,bridge,audit} -type f \( -name "*.jsonl" -o -name "*.log" \) -mtime +30 2>/dev/null | while read f; do
  rel="${f#$LOGS/}"
  mkdir -p "$DEST/$(dirname "$rel")"
  mv "$f" "$DEST/$rel"
  echo "  📦 $rel"
done
echo "✅ 归档完成: $DEST"
