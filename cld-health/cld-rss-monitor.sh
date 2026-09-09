#!/usr/bin/env bash
# cld-rss-monitor.sh — CLD 内存监控（RSS >3.2G 告警）· 3d490920 产出 2026-09-04
# 用途：监测 CLD 主进程 + dsh web 子进程（ELECTRON_RUN_AS_NODE）RSS，超阈告警。
# 用法：直接运行（告警写 ~/.cld/logs/cld-rss.log + stderr）；供 health-check.sh 以子命令调用。
#   bash cld-rss-monitor.sh          # 检查并输出
#   bash cld-rss-monitor.sh --json   # 机器可读
# 阈值：RSS > 3.2 GiB（3355443 KB）触发（OOM 实况 old space ~3.6-3.8GB，3.2G 预留告警余量）

set -u
THRESHOLD_KB=$((3 * 1024 * 1024 + 205 * 1024))  # 3.2 GiB ≈ 3355443 KB
LOG_FILE="${HOME}/.cld/logs/cld-rss.log"
JSON=0
[ "${1:-}" = "--json" ] && JSON=1

alerts=()
lines=()

check_pid() {
  # $1=label $2=pid
  local label="$1" pid="$2" rss_kb=0
  [ -z "$pid" ] && return 0
  rss_kb=$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ')
  [ -z "$rss_kb" ] && return 0
  local rss_mb=$((rss_kb / 1024))
  lines+=("$label pid=$pid rss=${rss_mb}MB")
  if [ "$rss_kb" -gt "$THRESHOLD_KB" ]; then
    local msg="[cld-rss] ALERT $label pid=$pid rss=${rss_mb}MB > 3.2GiB (threshold $((THRESHOLD_KB/1024))MB) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    alerts+=("$msg")
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
  fi
}

# CLD 主进程（无 --type 即非 helper）
main_pid=$(pgrep -f '/Applications/CLD.app/Contents/MacOS/CLD' 2>/dev/null | while read -r p; do
  if ! ps -o command= -p "$p" 2>/dev/null | grep -q -- '--type='; then echo "$p"; break; fi
done | head -1)
check_pid 'cld-main' "$main_pid"

# dsh web 子进程（bin.js + ELECTRON_RUN_AS_NODE）
dsh_pids=$(pgrep -f 'bin.js web --port' 2>/dev/null | head -3)
for p in $dsh_pids; do check_pid 'dsh-web' "$p"; done

if [ "$JSON" = "1" ]; then
  printf '{"checked_at":"%s","threshold_kb":%s,"procs":[%s],"alert":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$THRESHOLD_KB" \
    "$(IFS=,; echo "${lines[*]+${lines[*]}}" | sed 's/pid=/{"pid":/; s/ rss=/","rss_mb":/; s/MB/}/g')" \
    "$([ ${#alerts[@]} -gt 0 ] && echo true || echo false)"
else
  if [ ${#lines[@]} -gt 0 ]; then for l in "${lines[@]}"; do echo "[cld-rss] $l"; done; fi
  if [ ${#alerts[@]} -gt 0 ]; then for a in "${alerts[@]}"; do echo "$a" >&2; done; fi
fi

[ ${#alerts[@]} -gt 0 ] && exit 1 || exit 0