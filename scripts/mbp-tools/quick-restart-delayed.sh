#!/bin/sh
# quick-restart-delayed.sh —— 延迟触发 CLD 快速重启（先说完，再重启）
# 用法： sh quick-restart-delayed.sh [延迟秒=20] [倒计时秒=15]
# 机制（读 agent-way 实现得出）：POST /agent-bus/api/quick-restart {confirm:true,countdown:N}
#   → 广播 → 写 restart-marker → spawn detached 守护 `sleep N+2; open -a /Applications/CLD.app`
#   → 800ms 后宿主 process.exit(0)；**不触碰 POST /reload**
# ⚠️ **2026-10-04 更正（事故 #6）**：原文写「守护自动拉起，无需人工重开」——**已证伪**：11:42 实测守护的
#   `open` 确实拉起了实例，但该实例 1.4s 后被**陈旧单实例锁静默杀掉**（exit 0、零日志痕迹）⇒ 仍需人工重开。
#   ⇒ **优先改用 `tools/restart-with-guard.sh`**（自带读回验证 + 有界重试 + 清陈旧锁）；本脚本仅作触发用。
#   证据：`hazards/incidents/#6-20261004-relaunch-singleton.md`
DLY=${1:-20}; CD=${2:-15}
PORT=$(grep -o 'http://127.0.0.1:[0-9]*' "$HOME/.cld/logs/dsh-web.log" | tail -1 | grep -o '[0-9]*$')
LOG="$HOME/dsh-collab/data/ops/quick-restart-trigger.log"
mkdir -p "$(dirname "$LOG")"
echo "[$(date '+%F %T')] 延迟 ${DLY}s 后触发 quick-restart（port=$PORT, countdown=${CD}s）" >> "$LOG"
sleep "$DLY"
R=$(curl -s -m 10 -X POST -H "Host: 127.0.0.1:$PORT" -H 'Content-Type: application/json' \
     -d "{\"confirm\":true,\"countdown\":$CD}" "http://127.0.0.1:$PORT/agent-bus/api/quick-restart")
echo "[$(date '+%F %T')] 触发回执: $R" >> "$LOG"
echo "[$(date '+%F %T')] 宿主应已退出；守护约 ${CD}s 后 open -a CLD.app" >> "$LOG"
