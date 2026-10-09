#!/usr/bin/env bash
# archive-logs.sh — 月度日志归档（launchd 每月 1 日 03:00）
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#

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
