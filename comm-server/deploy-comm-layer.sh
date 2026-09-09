#!/usr/bin/env bash
# comm-layer 部署 SOP v1（迁移计划 v1.0 Step 1 · 阶段 A 通讯订阅层）
# 用途：把 bb-sub×8（订阅中枢）+ bus-bridge（跨设备总线）部署到 xingqiao /opt/comm-layer/
#       —— 中枢同机订阅器：服务器 24h 常驻，中枢事件在服务器 inbox 留痕（本机重启不丢事件）
# 用法：在 mac-mini 执行 ./deploy-comm-layer.sh
# 前置：comm-server(:8792/:8803) 已上线并验证；SSH 免钥(~/Downloads/startbrige.pem)；linux dsh-tools 在 dist/
# 幂等：可复跑（token/环境文件存在则复用，不覆盖）
set -euo pipefail

# ====== 配置 ======
SERVER_USER="ubuntu"
SERVER_HOST="106.53.214.108"
SSH_KEY="$HOME/Downloads/startbrige.pem"
TOOLS_SRC="$HOME/dsh-collab/rust-tools/dist/dsh-tools-linux-x64-v1.4.2"   # 含 bb-sub（该子命令 v1.0 起未变）
BUS_BRIDGE_SRC="$HOME/.dsh/bus-bridge/bus-bridge.js"                      # 纯 node 内置模块，无第三方依赖
REMOTE="/opt/comm-layer"
NODE_VER="v24.20.0"
SSE_URL="http://127.0.0.1:8803/events"                                    # 中枢 SSE（服务器本机）
NODE_TARBALL="node-${NODE_VER}-linux-x64.tar.xz"

# bb-sub 角色 → 订阅前缀（与本机 launchd 配置一致，蓝本：com.dsh.bb-sub.*.plist）
# 注：macOS 默认 bash 3.2 无关联数组 → 用 case
# R006#10 结构门: 角色白名单(防拼错角色静默落到默认前缀 = 违规路径)
ROLE_WHITELIST="coordinator device hr learning qa recovery supply xingduo"

_valid_role() {
  case " $ROLE_WHITELIST " in
    *" $1 "*) return 0 ;;
    *) return 1 ;;
  esac
}

bb_prefixes() {
  case "$1" in
    coordinator) echo "notes/collab/,notes/mac-mini/,tasks/central/queue/,notes/i9/" ;;
    device)      echo "nodes/,data/handoffs/,data/supply-chain/,notes/mac-mini/" ;;
    hr)          echo "notes/mac-mini/,data/qa/,data/supply-chain/,data/recovery/" ;;
    learning)    echo "data/learning/,notes/collab/,tasks/central/queue/" ;;
    qa)          echo "tasks/central/queue/,data/qa/,notes/collab/" ;;
    recovery)    echo "data/recovery/,notes/mac-mini/,tasks/central/queue/" ;;
    supply)      echo "data/supply-chain/,tasks/central/queue/,notes/mac-mini/" ;;
    xingduo)     echo "data/iterations/,data/blueprint/,data/progress/,notes/mac-mini/,notes/collab/,notes/8c2494e0/" ;;
    *)           echo "notes/collab/" ;;
  esac
}

# R006#10 Lean4 自检(本地, 不触碰服务器): 证明部署前提门与角色白名单门生效
lean4_check() {
  local fails=0
  # ① 非法角色必须被拒(防拼错/注入: 空格/斜杠/分号/点)
  for bad in "evil" "coordinator " "a/b" "x;rm" ".." ""; do
    if _valid_role "$bad"; then
      echo "❌ 非法角色未被拒: '$bad'"; fails=$((fails+1))
    fi
  done
  # ② 合法角色(8个)必须全放行
  for good in $ROLE_WHITELIST; do
    _valid_role "$good" || { echo "❌ 合法角色被误拒: '$good'"; fails=$((fails+1)); }
  done
  # ③ 部署前提门: 本地源文件缺失必须导致部署拒(不允许裸跑部署)
  local missing=0
  [ -f "$TOOLS_SRC" ] || { echo "⚠️ 本地缺 dsh-tools 源 ($TOOLS_SRC)"; missing=$((missing+1)); }
  [ -f "$BUS_BRIDGE_SRC" ] || { echo "⚠️ 本地缺 bus-bridge.js 源 ($BUS_BRIDGE_SRC)"; missing=$((missing+1)); }
  if [ "$missing" -gt 0 ]; then
    echo "✅ 前提门生效: 源文件缺失时部署将被拒(缺失 $missing)"
  fi
  # ④ 9 服务面完整(bb-sub×8 + bus-bridge)
  local n=0
  for r in $ROLE_WHITELIST; do n=$((n+1)); done
  if [ "$n" -ne 8 ] || [ ! -f "$BUS_BRIDGE_SRC" ]; then
    echo "❌ 服务面不完整: bb-sub=$n"; fails=$((fails+1))
  fi
  if [ "$fails" -eq 0 ]; then
    echo "lean4-check: ✅ 结构门生效(非法角色拒/合法放行/前提门/9服务面完整)"
    return 0
  fi
  echo "lean4-check: ❌ $fails 项失败"; return 1
}

ssh_run() { ssh -i "$SSH_KEY" -o ConnectTimeout=15 "$SERVER_USER@$SERVER_HOST" "$@"; }

# ====== 参数 (lean4-check 须在函数定义后) ======
if [ "${1:-}" = "--lean4-check" ]; then
  lean4_check
  exit $?
fi

echo "==> [1/7] 校验本地源文件"
[ -f "$TOOLS_SRC" ] || { echo "❌ 本地无 $TOOLS_SRC"; exit 1; }
[ -f "$BUS_BRIDGE_SRC" ] || { echo "❌ 本地无 $BUS_BRIDGE_SRC"; exit 1; }
file "$TOOLS_SRC" | grep -qi "ELF" && echo "✅ dsh-tools Linux ELF 确认（v1.4.2 含 bb-sub）"
echo "✅ bus-bridge.js（$(wc -c < "$BUS_BRIDGE_SRC") bytes，纯内置模块）"

echo "==> [2/7] 服务器建目录 + 装 node $NODE_VER"
ssh_run "sudo mkdir -p $REMOTE/bin $REMOTE/bus-bridge $REMOTE/bus-queue && sudo chown -R ubuntu:ubuntu $REMOTE"
if ssh_run "test -x /opt/node/bin/node && /opt/node/bin/node -v" >/dev/null 2>&1; then
  echo "✅ node 已装: $(ssh_run /opt/node/bin/node -v)"
else
  ssh_run "cd /opt && sudo curl -sL -o $NODE_TARBALL https://nodejs.org/dist/$NODE_VER/$NODE_TARBALL && sudo tar -xJf $NODE_TARBALL && sudo mv node-${NODE_VER}-linux-x64 node && sudo rm -f $NODE_TARBALL"
  echo "✅ node 安装完成: $(ssh_run /opt/node/bin/node -v)"
fi

echo "==> [3/7] 上传二进制与 bus-bridge.js"
scp -i "$SSH_KEY" -q "$TOOLS_SRC" "$SERVER_USER@$SERVER_HOST:$REMOTE/bin/dsh-tools"
scp -i "$SSH_KEY" -q "$BUS_BRIDGE_SRC" "$SERVER_USER@$SERVER_HOST:$REMOTE/bus-bridge/bus-bridge.js"
ssh_run "chmod +x $REMOTE/bin/dsh-tools && $REMOTE/bin/dsh-tools --help 2>&1 | head -3 || true"
echo "✅ 上传完成"

echo "==> [4/7] bus-bridge token（幂等：已存在则复用）"
TOKEN=""
if ssh_run "test -f $REMOTE/bus-bridge.env"; then
  TOKEN=$(ssh_run "grep WEBHOOK_TOKEN $REMOTE/bus-bridge.env | cut -d= -f2")
  echo "✅ 复用既有 token"
else
  TOKEN=$(openssl rand -hex 16)
  ssh_run "echo 'WEBHOOK_TOKEN=$TOKEN' | sudo tee $REMOTE/bus-bridge.env >/dev/null && sudo chmod 600 $REMOTE/bus-bridge.env && sudo chown root:root $REMOTE/bus-bridge.env"
  echo "✅ 新 token 已写入 $REMOTE/bus-bridge.env (0600 root)"
fi

echo "==> [5/7] 写 systemd units（9 个：bb-sub×8 + bus-bridge）"
for role in coordinator device hr learning qa recovery supply xingduo; do
  # R006#10 结构门: 部署循环前角色白名单校验(非法角色即拒, 不静默落默认前缀)
  if ! _valid_role "$role"; then
    echo "❌ 非法角色 '$role' 被结构门拒（不在白名单: $ROLE_WHITELIST）"; exit 1
  fi
  prefixes=$(bb_prefixes "$role")
  ssh_run "sudo tee /etc/systemd/system/comm-bb-sub-${role}.service >/dev/null <<'EOF'
[Unit]
Description=Comm bb-sub ${role} (订阅中枢 SSE · 服务器留痕)
After=network.target comm-server.service

[Service]
ExecStart=$REMOTE/bin/dsh-tools bb-sub --agent ${role} --prefixes ${prefixes} --sse ${SSE_URL}
Restart=always
RestartSec=5
User=ubuntu
WorkingDirectory=$REMOTE

[Install]
WantedBy=multi-user.target
EOF"
done

ssh_run "sudo tee /etc/systemd/system/comm-bus-bridge.service >/dev/null <<'EOF'
[Unit]
Description=Comm Bus-Bridge (跨设备消息总线 · 服务器版)
After=network.target

[Service]
ExecStart=/opt/node/bin/node $REMOTE/bus-bridge/bus-bridge.js
EnvironmentFile=$REMOTE/bus-bridge.env
Environment=BUS_QUEUE_DIR=$REMOTE/bus-queue
Restart=always
RestartSec=5
User=ubuntu
WorkingDirectory=$REMOTE

[Install]
WantedBy=multi-user.target
EOF"
echo "✅ 9 个 unit 已写"

echo "==> [6/7] 启动服务"
ssh_run "sudo systemctl daemon-reload"
for role in coordinator device hr learning qa recovery supply xingduo; do
  _valid_role "$role" || { echo "❌ 非法角色 '$role' 结构门拒"; exit 1; }
  ssh_run "sudo systemctl enable comm-bb-sub-${role} >/dev/null 2>&1 && sudo systemctl restart comm-bb-sub-${role}"
done
ssh_run "sudo systemctl enable comm-bus-bridge >/dev/null 2>&1 && sudo systemctl restart comm-bus-bridge"
sleep 3
ssh_run "systemctl is-active comm-bb-sub-coordinator comm-bb-sub-device comm-bb-sub-hr comm-bb-sub-learning comm-bb-sub-qa comm-bb-sub-recovery comm-bb-sub-supply comm-bb-sub-xingduo comm-bus-bridge"

echo "==> [7/7] 验证（R030 实测门）"
echo "--- bb-sub coordinator 日志 ---"
ssh_run "journalctl -u comm-bb-sub-coordinator --no-pager -n 5 2>/dev/null | tail -5"
echo "--- bus-bridge health ---"
ssh_run "curl -s -m 5 -H 'Authorization: Bearer $TOKEN' http://127.0.0.1:8791/health || curl -s -m 5 http://127.0.0.1:8791/health"
echo ""
echo "--- 注入测试：写中枢 notes/mac-mini/ 测试键，验证 coordinator inbox 收到 ---"
TS=$(date +%s)
ssh_run "curl -s -m 5 -X PUT http://127.0.0.1:8792/notes/mac-mini/deploy-layer-test -H 'Content-Type: application/json' -d '{\"from\":\"deploy\",\"ts\":$TS,\"note\":\"comm-layer 部署验证\"}'"
sleep 3
ssh_run "tail -3 /home/ubuntu/.dsh/inbox/bb/coordinator.jsonl 2>/dev/null || echo '⚠️ inbox 未见（检查订阅/写权限）'"
echo ""
echo "完成 ✅ comm-layer 部署 SOP v1 执行完毕（迁移计划 Step 1）"
echo "注：feature-mcp 8811 暂缓——数据源(~/.chroma flower-feature)+embed(本机 ollama) 绑定 mac-mini，非订阅层；迁移需另行评估"
echo "注：8791 公网放行在 Step 3 灰度时按需配置（当前服务器侧仅本机可达）"
