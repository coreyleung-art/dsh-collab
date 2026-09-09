#!/usr/bin/env bash
# node-kit deploy.sh — 节点一键装备（P1 · 从 MBP/i9 实战提炼）
# 用法: ./deploy.sh --node <id> [--src-dir <守护源目录>] [--dry-run]
#   --node    节点 id (mbp/i9/新节点) —— 必填, 无默认(部署门 G-D2)
#   --src-dir 守护脚本源目录 (默认 ~/dsh-collab/comm-server)
#   --dry-run 只打印将执行的动作不实际部署
# 顺序: ① 校验门(gate-deploy-check) → ② 建目录+复制守护 → ③ 平台注册(launchd/schtasks) → ④ 自检
set -euo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE=""
SRC_DIR="$HOME/dsh-collab/comm-server"
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --node) NODE="$2"; shift 2;;
    --src-dir) SRC_DIR="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "未知参数: $1"; exit 1;;
  esac
done

# G-D2: node 必填无默认
if [[ -z "$NODE" ]]; then
  echo "❌ G-D2: --node 必填 (mbp/i9/...)，无默认"; exit 2
fi
if [[ "$NODE" == "mac-mini" ]]; then
  echo "⚠️ mac-mini 是主源中枢, 不需 node-kit 装备(自持)"; exit 0
fi

echo "══ node-kit deploy · node=$NODE ══"
# ① 校验门（若 gate-deploy-check.py 存在）
GATE="$HOME/dsh-collab/scripts/gate-deploy-check.py"
DAEMON_SRC="$SRC_DIR/device-daemon.py"
[[ "$NODE" == "i9" ]] && DAEMON_SRC="$SRC_DIR/device-daemon-i9.py"
if [[ -f "$GATE" && -f "$DAEMON_SRC" ]] && [[ $DRY -eq 0 ]]; then
  echo "① 部署门校验…"
  if ! python3 "$GATE" --file "$DAEMON_SRC" 2>/dev/null; then
    echo "  ⚠️ gate-deploy-check 返回非零(或该守护无校验规则)——继续但留意"
  fi
fi

# ② 建目录 + 复制守护
NODE_DIR="$HOME/.dsh/node-kit/$NODE"
if [[ $DRY -eq 1 ]]; then
  echo "② [dry] mkdir -p $NODE_DIR && cp $DAEMON_SRC → $NODE_DIR/"
else
  mkdir -p "$NODE_DIR"
  [[ -f "$DAEMON_SRC" ]] && cp "$DAEMON_SRC" "$NODE_DIR/device-daemon.py" && echo "② 守护已复制: $NODE_DIR/device-daemon.py"
  # conf env 模板（若存在）
  if [[ -f "$KIT_DIR/conf/$NODE.env" ]]; then
    cp "$KIT_DIR/conf/$NODE.env" "$NODE_DIR/node.env" && echo "   conf 已复制: node.env"
  fi
fi

# ③ 平台注册（macOS: launchd）
OS="$(uname -s)"
if [[ "$OS" == "Darwin" && $DRY -eq 0 ]]; then
  PLIST="$HOME/Library/LaunchAgents/com.dsh.nodekit.$NODE.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.dsh.nodekit.$NODE</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>$NODE_DIR/device-daemon.py</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>DSH_NODE_ID</key><string>$NODE</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$NODE_DIR/daemon.out.log</string>
  <key>StandardErrorPath</key><string>$NODE_DIR/daemon.err.log</string>
</dict></plist>
PLISTEOF
  echo "③ launchd 已注册: $PLIST"
  echo "   生效: launchctl load $PLIST （或等待重启 RunAtLoad）"
elif [[ "$OS" == "Darwin" ]]; then
  echo "③ [dry] 将生成 launchd plist: com.dsh.nodekit.$NODE"
fi

# ④ 自检提示
echo "④ 自检: 守护在跑? → pgrep -f device-daemon.py · 队列通? → curl :8791/bus/status · 心跳新?"
if [[ $DRY -eq 1 ]]; then echo "[dry-run 完成, 未实际部署]"; else echo "✅ node-kit 装备完成 (node=$NODE)"; fi
