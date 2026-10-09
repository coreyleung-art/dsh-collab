#!/usr/bin/env bash
# archive-logs.sh — 月度日志归档（launchd 每月 1 日 03:00）
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .sh 版
r006_selfcheck() {
  echo "== archive-logs 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · archive-logs.sh — 月度日志归档（launchd 每月 1 日 03:00）"
  echo "  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。"
  echo "  · 依据：r006-debt-assess.py 机械扫描未检出以下原语："
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

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
