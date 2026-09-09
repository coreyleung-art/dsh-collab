#!/usr/bin/env bash
# comm-layer 系统健康管理 (R006 自检 + 服务器化健康巡检)
# 检查: 服务 active / 内存 / 磁盘 / inbox 增长 / bus-queue / SSE 连通
# 用法:
#   health-ctl.sh                 # 全检, 输出摘要 (exit 0=健康 / 1=告警)
#   health-ctl.sh json            # JSON 输出 (供报告聚合)
#   health-ctl.sh --alert-board   # 异常时写中枢告警键 (timer 用)
set -uo pipefail
CTL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NOW=$(date +%s)
TS_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SERVICES="comm-server comm-server-test comm-bus-bridge comm-bb-sub-coordinator comm-bb-sub-device comm-bb-sub-hr comm-bb-sub-learning comm-bb-sub-qa comm-bb-sub-recovery comm-bb-sub-supply comm-bb-sub-xingduo"
CENTRAL_BB="http://127.0.0.1:8792"

check_active() {
  local bad=""
  local n=0
  for s in $SERVICES; do
    if systemctl is-active "$s" >/dev/null 2>&1; then n=$((n+1)); else bad="$bad $s"; fi
  done
  echo "services_active=$n/11"
  [ -n "$bad" ] && echo "services_down:$bad"
  [ -z "$bad" ]
}

check_mem() {
  local used total
  used=$(free -m | awk '/Mem/{print $3}')
  total=$(free -m | awk '/Mem/{print $2}')
  echo "mem_used_mb=$used/${total}MB"
  [ "$used" -lt 800 ]  # 1G 总, 800MB 告警线
}

check_disk() {
  local pct
  pct=$(df / | awk 'NR==2{print $5}' | tr -d '%')
  echo "disk_used_pct=${pct}%"
  [ "$pct" -lt 85 ]
}

check_inbox() {
  local lines last
  lines=$(cat /home/ubuntu/.dsh/inbox/bb/*.jsonl 2>/dev/null | wc -l)
  echo "inbox_lines=$lines"
}

check_queue() {
  local q
  q=$(ls /opt/comm-layer/bus-queue 2>/dev/null | wc -l)
  echo "bus_queue_files=$q"
  [ "$q" -lt 200 ]
}

check_sse() {
  # bb-sub SSE 订阅进程数 (应≥8)
  local n
  n=$(pgrep -fc "dsh-tools bb-sub" 2>/dev/null || echo 0)
  echo "bb_sub_procs=$n"
  [ "$n" -ge 8 ]
}

json_out() {
  python3 -c "
import json,sys
d={}
for line in sys.stdin:
    line=line.strip()
    if '=' in line:
        k,v=line.split('=',1); d[k]=v
    elif ':' in line and 'down' in line:
        d['services_down']=line.split(':',1)[1]
d['ts']='$TS_ISO'
print(json.dumps(d,ensure_ascii=False))
"
}

ALERT_BOARD=0
[ "${1:-}" = "--alert-board" ] && ALERT_BOARD=1

if [ "${1:-}" = "json" ]; then
  { check_active; check_mem; check_disk; check_inbox; check_queue; check_sse; } | json_out
  exit 0
fi

echo "== comm-layer 健康巡检 $TS_ISO =="
FAILS=""
check_active || FAILS="$FAILS services"
check_mem || FAILS="$FAILS memory"
check_disk || FAILS="$FAILS disk"
check_inbox
check_queue || FAILS="$FAILS queue"
check_sse || FAILS="$FAILS sse"

if [ -z "$FAILS" ]; then
  echo "结果: ✅ HEALTHY"
  exit 0
else
  echo "结果: ❌ 异常项:$FAILS"
  # 告警写中枢 (供 mac-mini 侧可见)
  if [ "$ALERT_BOARD" = "1" ]; then
    KEY="notes/collab/comm-health-alert-$NOW"
    BODY="{\"from\":\"comm-health-ctl\",\"alert\":\"comm-layer 异常:$FAILS\",\"ts\":$NOW}"
    curl -s -m 5 -X PUT "$CENTRAL_BB/$KEY" -H "Content-Type: application/json" -d "$BODY" >/dev/null 2>&1
    echo "  告警已写中枢: $KEY"
  fi
  exit 1
fi
