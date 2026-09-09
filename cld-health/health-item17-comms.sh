#!/usr/bin/env bash
# health-check item 17: 通讯通道卫生（CLD 节点网络公约 §1.3）
# 供守灯 health-check 纳入第 17 项 · 星桥 2026-09-09 提供探测方案
# 免 curl 401 假阴性：bus/status 带 token；守护进程数；SSE 订阅最近活动
# 退出: 0=健康 1=异常（供 health-check 集成）

TOKEN_FILE="$HOME/.dsh/bus-bridge-token"
SERVER="http://106.53.214.108:8791"
SSH_KEY="$HOME/Downloads/startbrige.pem"
SERVER_USER="ubuntu"

ok=0; warn=0

echo "── [17] 通讯通道卫生 ──"

# 17a. bus 队列零积压（R033/G-C4）
TOK=$(cat "$TOKEN_FILE" 2>/dev/null)
if [ -n "$TOK" ]; then
  Q=$(curl -s --max-time 5 -H "X-Webhook-Token: $TOK" "$SERVER/bus/status" 2>/dev/null \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['stats']['queued'])" 2>/dev/null)
  if [ "$Q" = "0" ]; then echo "  ✅ 17a bus队列零积压 (queued=0)"; ok=$((ok+1))
  else echo "  ⚠️ 17a bus队列积压 queued=$Q (R033 违反)"; warn=$((warn+1)); fi
else echo "  ⚠️ 17a token 缺失（$TOKEN_FILE）"; warn=$((warn+1)); fi

# 17b. 守护进程在跑（R033/G-C2，本机 mac-mini 守护）
D=$(ps aux | grep -c "[d]evice-daemon.py" 2>/dev/null)
if [ "$D" -ge 1 ]; then echo "  ✅ 17b 守护进程在跑 ($D)"; ok=$((ok+1))
else echo "  ❌ 17b 守护未运行 (device-daemon.py)"; warn=$((warn+1)); fi

# 17c. SSE 订阅存活（守护进程活着 + 日志含 SSE 连接记录——进程存活=连接在）
LAST_SSE=$(grep "SSE 已连接" "$HOME/.dsh/logs/device-daemon.log" 2>/dev/null | tail -1 | grep -oE "\[[0-9]{2}:[0-9]{2}:[0-9]{2}\]" | tr -d '[]')
if [ -n "$LAST_SSE" ]; then
  echo "  ✅ 17c SSE 订阅存活 (最后连接 $LAST_SSE)"; ok=$((ok+1))
else echo "  ❌ 17c 守护日志无 SSE 连接记录"; warn=$((warn+1)); fi

# 17d. 守护最近运行段无异常（查最后 20 行——旧版历史异常不计入）
ERR=$(tail -20 "$HOME/.dsh/logs/device-daemon.log" 2>/dev/null | grep -c "SSE 异常")
if [ "$ERR" -eq 0 ]; then echo "  ✅ 17d 守护当前运行无异常" ; ok=$((ok+1))
else echo "  ⚠️ 17d 守护最近异常 $ERR 次"; warn=$((warn+1)); fi

echo "── 17 结果: $ok 项健康 / $warn 项异常 ──"
[ "$warn" -eq 0 ] && exit 0 || exit 1
