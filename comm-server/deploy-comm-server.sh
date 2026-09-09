#!/usr/bin/env bash
# comm-server 部署 SOP v1（cs2-1 · agent-network v1.3 蓝图）
# 用途：把 rust-blackboard 通讯中枢部署到 24h 在线 Linux 服务器
# 用法：在 mac-mini 上执行，填入 SERVER_USER/SERVER_HOST 后运行
# 前置：mac-mini 已有 rust-blackboard-linux-x64-v0.6.0 产物
# 可复跑：幂等（重复执行安全）
set -euo pipefail

# ====== 配置（部署前填写）======
SERVER_USER="${1:-root}"
SERVER_HOST="${2:?用法: $0 <user> <host> [port]}"
SERVER_PORT="${3:-22}"
SSH_KEY="${4:-$HOME/.ssh/id_ed25519}"
BB_VERSION="v0.6.0"
BB_BINARY="$HOME/dsh-collab/rust-blackboard/dist/rust-blackboard-linux-x64-$BB_VERSION"
REMOTE_DIR="/opt/comm-server"
DATA_DIR="/var/lib/comm-server"
SERVICE_PORT=8792
SSE_PORT=8803
TOKEN="bb-token-20260904-comm-server"   # ← 部署后应轮换为随机值并下发三端

echo "==> [1/5] 校验本地二进制"
[ -f "$BB_BINARY" ] || { echo "❌ 本地无 $BB_BINARY"; ls "$HOME/dsh-collab/rust-blackboard/dist/" | grep linux; exit 1; }
file "$BB_BINARY" | grep -qi "ELF" && echo "✅ Linux ELF 确认" || { echo "⚠️ 非 ELF，确认版本"; }

echo "==> [2/5] 上传二进制到服务器"
ssh -i "$SSH_KEY" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "mkdir -p $REMOTE_DIR $DATA_DIR"
scp -i "$SSH_KEY" -P "$SERVER_PORT" "$BB_BINARY" "$SERVER_USER@$SERVER_HOST:$REMOTE_DIR/rust-blackboard-linux-x64-$BB_VERSION"
ssh -i "$SSH_KEY" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "chmod +x $REMOTE_DIR/rust-blackboard-linux-x64-$BB_VERSION"

echo "==> [3/5] 写 systemd 服务"
ssh -i "$SSH_KEY" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "cat > /etc/systemd/system/comm-server.service <<'EOF'
[Unit]
Description=Comm-Server Blackboard (hub-spoke 通讯中枢)
After=network.target

[Service]
ExecStart=$REMOTE_DIR/rust-blackboard-linux-x64-$BB_VERSION --port $SERVICE_PORT --sse-port $SSE_PORT --data-dir $DATA_DIR --token $TOKEN
Restart=always
RestartSec=5
User=$SERVER_USER
WorkingDirectory=$REMOTE_DIR

[Install]
WantedBy=multi-user.target
EOF"

echo "==> [4/5] 启动服务"
ssh -i "$SSH_KEY" -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "systemctl daemon-reload && systemctl enable comm-server && systemctl restart comm-server && sleep 2 && systemctl status comm-server --no-pager | head -8"

echo "==> [5/5] 本地验证远端可达"
sleep 2
REMOTE_URL="http://$SERVER_HOST:$SERVICE_PORT"
if curl -s -m 5 -H "Authorization: Bearer $TOKEN" "$REMOTE_URL/health" >/dev/null 2>&1; then
  echo "✅ comm-server 已上线: $REMOTE_URL（health OK）"
  echo "   验证写入: curl -X PUT $REMOTE_URL/nodes/mac-mini/hb-daemon -d '{\"ts\":$(date +%s)}'"
else
  echo "⚠️ health 未通——检查: 防火墙(ufw allow $SERVICE_PORT/$SSE_PORT) / 云安全组放行 / TOKEN"
fi

echo ""
echo "完成 ✅ comm-server 部署 SOP v1 执行完毕"
echo "下一步（cs3）：三端接入——mac-mini/i9/MBP 各自把 BB 端点指到 $REMOTE_URL"
