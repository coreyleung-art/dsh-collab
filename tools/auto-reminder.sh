#!/bin/bash
# auto-reminder.sh v2 —— 星桥自动提醒器（用户指令：十轮 × 每 30 分钟自我注入提醒）
# v2（2026-10-08 裁判裁定整改）：
#   ① 端口动态发现（CLD web --port 0 随机，写死 49187 在重启后空转）
#   ② 注入失败不耗轮次（探活失败→记日志退出，下周期重试）
#   ③ 计数器写后回读断言（断电不丢轮次账）
#   ④ 第 10 轮成功注入后立即 bootout（不再等第 11 轮触发）
#   ⑤ 回读断言：resp 必须含 "ok":true 才算注入成功
set -uo pipefail

MAX_ROUNDS=10
COUNT_FILE="$HOME/.dsh/auto-reminder-count"
FAIL_FILE="$HOME/.dsh/auto-reminder-fails"
DEADLINE_FILE="$HOME/.dsh/auto-reminder-deadline"
MAX_CONSEC_FAIL=5
MAX_HOURS=24
LOG="$HOME/dsh-collab/logs/auto-reminder.log"
GOALS_KEY="notes/mac-mini/pending-goals-20261008"
SELF_SESSION="session-fa1f9150-c949-401f-ba8c-d265f6221676"
TS=$(date "+%Y-%m-%d %H:%M")

log() { echo "[$TS] $*" >> "$LOG"; }

# 首次运行记录绝对时限（24h 后无论成败一律停）
[ -f "$DEADLINE_FILE" ] || { date +%s > "$DEADLINE_FILE"; sync "$DEADLINE_FILE" 2>/dev/null || sync; }  # ★ 裁判 2026-10-08 标未覆盖：首次记录时限也需 fsync（否则断电窗口内时限丢失）
DEADLINE=$(( $(cat "$DEADLINE_FILE") + MAX_HOURS*3600 ))
if [ "$(date +%s)" -ge "$DEADLINE" ]; then
  log "已达绝对时限 ${MAX_HOURS}h，bootout 卸载退出"
  launchctl bootout "gui/$(id -u)/com.dsh.auto-reminder" 2>/dev/null
  exit 0
fi

# ---- 端口动态发现：CLD 监听 127.0.0.1 的端口里，/agent-bus/api/state 答 JSON 者 ----
WEB=""
for port in $(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep CLD | grep "127.0.0.1" | awk '{print $9}' | sed 's/.*://' | sort -un); do
  if curl -s -m 5 "http://127.0.0.1:$port/agent-bus/api/state" 2>/dev/null | grep -q '"ok"'; then
    WEB="http://127.0.0.1:$port"; break
  fi
done
fail_bump() {
  local f; f=$(cat "$FAIL_FILE" 2>/dev/null | tr -dc '0-9'); [ -z "$f" ] && f=0
  f=$((f+1)); echo "$f" > "$FAIL_FILE"
  if [ "$f" -ge "$MAX_CONSEC_FAIL" ]; then
    log "连续失败 $f 次 ≥ 上限 $MAX_CONSEC_FAIL，bootout 卸载退出"
    launchctl bootout "gui/$(id -u)/com.dsh.auto-reminder" 2>/dev/null
  fi
}
if [ -z "$WEB" ]; then
  log "FAIL: 未发现 CLD web 端口，本轮不注入不耗轮次"
  fail_bump
  exit 0
fi

# ---- 读取当前轮次 ----
N=$(cat "$COUNT_FILE" 2>/dev/null | tr -dc '0-9'); [ -z "$N" ] && N=0
if [ "$N" -ge "$MAX_ROUNDS" ]; then
  log "轮次已达 $MAX_ROUNDS，卸载并退出"
  launchctl bootout "gui/$(id -u)/com.dsh.auto-reminder" 2>/dev/null
  exit 0
fi

# ---- 注入 ----
NN=$((N+1))
BODY=$(python3 -c "
import json
print(json.dumps({'to': '$SELF_SESSION', 'text': '【自动提醒 第 $NN/$MAX_ROUNDS 轮】半小时到：检查未完成目标（看黑板 $GOALS_KEY 清单 + todo），有可推进项就继续推进，本轮结束把小结写 notes/mac-mini/auto-reminder-round-$NN。'}))
")
RESP=$(curl -s -m 10 -X POST "$WEB/agent-bus/api/send" -H 'content-type: application/json' -d "$BODY")
if ! echo "$RESP" | grep -q '"ok":true'; then
  log "FAIL: 注入未成功（resp=$(echo "$RESP" | head -c 120)），不耗轮次"
  fail_bump
  exit 0
fi

# ---- 成功才计数：写后回读断言 ----
echo "$NN" > "$COUNT_FILE"
sync "$COUNT_FILE" 2>/dev/null || sync   # ★ 持久化：回读只验「写入被接受」，防断电须 fsync（裁判 v2 复核）
echo 0 > "$FAIL_FILE"
if [ "$(cat "$COUNT_FILE" | tr -dc '0-9')" != "$NN" ]; then
  log "FAIL: 计数器回读不符"
  exit 1
fi
log "round=$NN/$MAX_ROUNDS injected_ok resp=$(echo "$RESP" | head -c 100)"

# ---- 第 10 轮成功后立即卸载 ----
if [ "$NN" -ge "$MAX_ROUNDS" ]; then
  log "第 $MAX_ROUNDS 轮完成，bootout 卸载"
  launchctl bootout "gui/$(id -u)/com.dsh.auto-reminder" 2>/dev/null
fi
