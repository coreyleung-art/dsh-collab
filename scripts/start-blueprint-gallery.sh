#!/bin/bash
# 蓝图架构图管理器 · 一键启动（幂等：已在跑则只开浏览器）
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .sh 版
r006_selfcheck() {
  echo "== start-blueprint-gallery 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · 蓝图架构图管理器 · 一键启动（幂等：已在跑则只开浏览器）"
  echo "  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。"
  echo "  · 依据：r006-debt-assess.py 机械扫描未检出以下原语："
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "  · 本工具涉及「访问网络」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/start-blueprint-gallery.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

DSH_LOG="$HOME/dsh-collab/logs/start-blueprint-gallery.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

PORT=${PORT:-8798}
URL="http://127.0.0.1:$PORT"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG=/tmp/bb-gallery.log

# 已在运行？直接开浏览器
if curl -s -o /dev/null --max-time 2 "$URL/api/overview"; then
  echo "✅ 已在运行: $URL"
  open "$URL"
  exit 0
fi

# 启动
cd "$SCRIPT_DIR/.."
nohup python3 scripts/bb-blueprint-gallery.py --port $PORT > "$LOG" 2>&1 &
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  if curl -s -o /dev/null --max-time 2 "$URL/api/overview"; then
    echo "✅ 已启动: $URL  (日志: $LOG)"
    open "$URL"
    exit 0
  fi
done
echo "❌ 启动失败，日志:"; tail -20 "$LOG"
exit 1
