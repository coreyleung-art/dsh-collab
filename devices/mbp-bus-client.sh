#!/usr/bin/env bash
# mbp-bus-client.sh — MBP 资源节点总线桥客户端（v1.1 协议定稿版）
# 部署于 MBP（mbp-node agent），对接 mac-mini bus-bridge.js（端口 8791）
# 协议（92623479 实测契约）：
#   GET  /bus/receive?target=mbp-node  → {ok, task:{task_id,from,target,action,payload,created_at}} | {ok, task:null}
#   POST /bus/reply {task_id, ok, result, error} → {ok, task_id, status}
#   GET  /bus/outbox?from=mbp-node&consume=1 （可选，拉已回结果）
# 轮询 5-10s；任务超时 60s 主动 reply error；reply 失败重试 ≤3；幂等容忍
# 依赖：curl + python3（macOS 自带）
# 2026-08-17 · 设备协调 5a5368af

# ===== 配置 =====
BUS_BASE="${BUS_BASE:-http://100.120.203.20:8791}"
TOKEN_FILE="${TOKEN_FILE:-$HOME/.dsh/bus-bridge-token}"  # 凭据文件（0600，MBP 侧私有）
NODE_ID="${NODE_ID:-mbp-node}"      # 本节点 ID
POLL_INTERVAL="${POLL_INTERVAL:-5}" # 轮询间隔秒（5-10 推荐）
TASK_TIMEOUT="${TASK_TIMEOUT:-60}"  # 任务主动超时秒（60 可配）
REPLY_RETRIES=3
LOG_FILE="$HOME/.dsh/mbp-bus-client.log"
PID_FILE="$HOME/.dsh/mbp-bus-client.pid"

# ===== 工具 =====
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"; }

# 鉴权参数：启动时构建 AUTH_ARGS 数组（curl 用 "${AUTH_ARGS[@]}" 展开——避免 $(auth) 分词拆裂 header）
# header 值含空格（X-Webhook-Token: <token>），数组展开保整（$(auth) 会按空格拆成多个参数 → token 丢失）
build_auth() {
  AUTH_ARGS=()
  if [ -f "$TOKEN_FILE" ]; then
    local tk
    tk=$(cat "$TOKEN_FILE" | tr -d '\n')
    AUTH_ARGS=(-H "X-Webhook-Token: $tk")
  fi
}

# 超时执行（macOS 无 timeout：后台 + kill）
run_task() {
  local cmd="$1" outfile="/tmp/mbp-task.$$"
  bash -c "$cmd" > "$outfile" 2>&1 &
  local pid=$! waited=0
  while kill -0 $pid 2>/dev/null; do
    sleep 1; waited=$((waited+1))
    if [ $waited -ge $TASK_TIMEOUT ]; then
      kill $pid 2>/dev/null
      echo "__TIMEOUT__"
      rm -f "$outfile"; return 124
    fi
  done
  cat "$outfile"; rm -f "$outfile"
  return 0
}

# ===== 单次轮询 =====
poll_once() {
  local resp task_id action payload
  resp=$(curl -s --max-time 10 "${AUTH_ARGS[@]}" "$BUS_BASE/bus/receive?target=$NODE_ID" 2>/dev/null)
  task_id=$(echo "$resp" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    t=d.get('task')
    print(t.get('task_id','') if t else '')
except: print('')" 2>/dev/null)
  [ -z "$task_id" ] && return 0   # 空队列

  action=$(echo "$resp" | python3 -c "
import sys,json
d=json.load(sys.stdin); print(d['task'].get('action',''))" 2>/dev/null)
  payload=$(echo "$resp" | python3 -c "
import sys,json
d=json.load(sys.stdin); print(json.dumps(d['task'].get('payload',{}),ensure_ascii=False))" 2>/dev/null)
  log "收到任务 $task_id action=$action"

  # 执行：action 为 shell 命令字符串则直接跑；否则按 action 分派
  local result rc
  case "$action" in
    shell|exec|run)
      local cmd
      cmd=$(echo "$payload" | python3 -c "
import sys,json
p=json.load(sys.stdin); print(p.get('cmd','') or p.get('command',''))" 2>/dev/null)
      result=$(run_task "$cmd"); rc=$?;;
    info|status)
      result=$(run_task "uname -a; df -h / | tail -1; sysctl -n hw.memsize 2>/dev/null; sw_vers -productVersion"); rc=0;;
    *)
      # 未知 action：尝试把 payload 的 cmd 字段当命令
      local cmd2
      cmd2=$(echo "$payload" | python3 -c "
import sys,json
p=json.load(sys.stdin); print(p.get('cmd','') or p.get('command',''))" 2>/dev/null)
      if [ -n "$cmd2" ]; then result=$(run_task "$cmd2"); rc=$?;
      else result="unknown action: $action"; rc=1; fi;;
  esac

  log "任务完成 $task_id rc=$rc"
  # 回传（重试 ≤3，幂等容忍）
  local ok_str=false
  [ $rc -eq 0 ] && ok_str=true
  [ "$result" = "__TIMEOUT__" ] && { ok_str=false; result="timeout: $action 未在 ${TASK_TIMEOUT}s 内完成"; }
  # 用环境变量传 result（避免 shell 引号/换行破坏 JSON——python 内部 json.dumps 处理转义）
  local body
  body=$(RESULT="$result" TASK_ID="$task_id" OK="$ok_str" python3 -c "
import json,os
payload={'task_id':os.environ['TASK_ID'],'ok':os.environ['OK']=='true','result':os.environ['RESULT'] if os.environ['OK']=='true' else None,'error':None if os.environ['OK']=='true' else os.environ['RESULT']}
print(json.dumps(payload,ensure_ascii=False))" 2>/dev/null)
  log "reply body 生成: ${body:0:80}..."
  local i
  for i in 1 2 3; do
    local r
    r=$(curl -s --max-time 10 -X POST "$BUS_BASE/bus/reply" -H "Content-Type: application/json" "${AUTH_ARGS[@]}" -d "$body" 2>/dev/null)
    if echo "$r" | grep -q '"ok":true'; then log "回传成功 $task_id"; break; fi
    log "回传重试 $i $task_id"
    sleep 2
  done
}

# ===== 主循环 =====
start() {
  log "MBP bus-client 启动 bus=$BUS_BASE node=$NODE_ID interval=${POLL_INTERVAL}s"
  echo $$ > "$PID_FILE"
  while true; do
    poll_once
    sleep "$POLL_INTERVAL"
  done
}
stop() { [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null; rm -f "$PID_FILE"; log "已停止"; }

case "${1:-start}" in
  start) build_auth; start;;
  stop) stop;;
  once) build_auth; poll_once;;
  --version|-V) echo "mbp-bus-client v1.1.0"; exit 0;;
  --help|-h) echo "用法: $0 {start|stop|once|--version|--help}
  start   启动轮询（写 PID + 日志）
  stop    停止（kill PID）
  once    单次轮询（调试）
文档: ~/dsh-collab/devices/lessons/tool-readme/mbp-bus-client.md"; exit 0;;
  *) echo "用法: $0 {start|stop|once}"; exit 1;;
esac
