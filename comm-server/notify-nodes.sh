#!/usr/bin/env bash
# notify-nodes.sh — 服务器公共文本更新 → 抄送接入设备(notes/<node>/)
# 用户 2026-09-09: 更新服务器相关公共文本须抄送接入设备(mbp/i9)
# 用法: ./notify-nodes.sh "<文档键>" "<变更摘要>" [--dry-run]
DOC_KEY="${1:?需文档键}"
SUMMARY="${2:?需变更摘要}"
TOK_FILE="$HOME/.dsh/bus-bridge-token"
SERVER="http://106.53.214.108:8791"
TS=$(date +%s%3N)

for dev in mbp i9; do
  # v1.3 (i9 CP-005 反馈): payload.to 用角色形式 $dev:coordinator(端侧过滤可读),
  # 裸设备名(i9) 会被端侧 msg-filter 判 dest-not-i9-readable 拦截
  body="{\"from\":\"server:coordinator\",\"target\":\"$dev\",\"action\":\"doc-update\",\"payload\":{\"to\":\"$dev:coordinator\",\"text\":\"[文档更新] $DOC_KEY — $SUMMARY (全文留原文档, 本通知供知悉)\"},\"ttl_sec\":86400}"
  if [ "$4" = "--dry-run" ]; then echo "[dry-run] 将通知 $dev: $SUMMARY"; continue; fi
  R=$(curl -s --max-time 8 -X POST -H "X-Webhook-Token: $(cat $TOK_FILE)" -H "Content-Type: application/json" -d "$body" "$SERVER/bus/send" 2>/dev/null)
  echo "$dev: $(echo $R | head -c 80)"
done
