#!/usr/bin/env bash
# bus-send.sh v1.0 — 跨设备 bus 信封便捷发送 (门3: 让正确通道成为顺手通道, 防退回 agent-msg 老路)
# HR 2026-09-09: 公约发布≠工具就绪——bus token 未配导致退回老通道; 本封装自动读 token, 一条命令发对通道。
# 用法:
#   bus-send.sh <target> <action> "<text>" [--from mac-mini:星桥] [--to 角色] [--notify] [--ttl 86400]
#   bus-send.sh --probe                      # 自检: token 在位 + 服务器 200
# 例: bus-send.sh i9 ask-capability "采集你的 ASR 能力清单" --from "mac-mini:星桥" --to "i9:coordinator"
set -euo pipefail
TOK_FILE="$HOME/.dsh/bus-bridge-token"
SERVER="${BUS_SERVER:-http://106.53.214.108:8791}"
FROM="mac-mini:星桥"
TO=""
NOTIFY="false"
TTL=86400

if [ "${1:-}" = "--probe" ]; then
  if [ ! -f "$TOK_FILE" ]; then echo "❌ token 文件缺失 $TOK_FILE"; exit 1; fi
  chmod 600 "$TOK_FILE" 2>/dev/null || true
  R=$(curl -s --max-time 8 -H "X-Webhook-Token: $(cat "$TOK_FILE")" "$SERVER/health" 2>/dev/null || echo '{"ok":false}')
  echo "服务器: $R"
  [ "$(echo "$R" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("ok","false"))' 2>/dev/null)" = "True" ] && echo "✅ bus/send 通道就绪" || { echo "❌ 通道不可用"; exit 1; }
  exit 0
fi
[ $# -lt 3 ] && { echo "用法: bus-send.sh <target> <action> '<text>' [--from ..] [--to 角色] [--notify] [--ttl N]"; exit 2; }
TARGET="$1"; ACTION="$2"; TEXT="$3"; shift 3
while [ $# -gt 0 ]; do case "$1" in
  --from) FROM="$2"; shift 2;;
  --to) TO="$2"; shift 2;;
  --notify) NOTIFY="true"; shift;;
  --ttl) TTL="$2"; shift 2;;
  *) shift;; esac; done

[ ! -f "$TOK_FILE" ] && { echo "❌ token 缺失(找 mac-mini 星桥申请)"; exit 1; }
PAYLOAD="{\"to\":\"${TO:-$TARGET}\",\"text\":$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$TEXT")"
[ "$NOTIFY" = "true" ] && PAYLOAD="$PAYLOAD,\"notify_only\":true"
PAYLOAD="$PAYLOAD}"
BODY="{\"from\":\"$FROM\",\"target\":\"$TARGET\",\"action\":\"$ACTION\",\"payload\":$PAYLOAD,\"ttl_sec\":$TTL}"
R=$(curl -s --max-time 10 -X POST -H "X-Webhook-Token: $(cat "$TOK_FILE")" -H "Content-Type: application/json" -d "$BODY" "$SERVER/bus/send")
echo "$R" | head -c 300; echo
echo "$R" | grep -q '"ok":true' && echo "✅ 已入队(target=$TARGET action=$ACTION)" || { echo "❌ 发送失败(见上)"; exit 1; }
