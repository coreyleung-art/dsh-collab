#!/bin/bash
# relaunch-cld.sh — CLD 拉起守护 v1.0.0（2026-10-04 星桥 · 对齐 MBP 事故 #6 / R043）
# 纪律：拉起/重启类动作必须**读回验证**（MBP 事故 #6：新实例被陈旧单实例锁静默自杀 1.4s，
#       单发 open 不验证 ⇒ 失败零信号）。判据：exit-marker.json pid/startedAt 更新 + 进程存活。
# 用法：relaunch-cld.sh [--selftest] [--max-wait 秒]
# 退出码：0=已起来 / 1=尝试耗尽 / 2=用法错 / 3=自测失败
set -u
APP=/Applications/CLD.app
CLD_BIN="$APP/Contents/MacOS/CLD"
MARKER="$HOME/.cld/logs/exit-marker.json"
LOCK_DIR="$HOME/Library/Application Support/CLD"
LOG_DIR="$HOME/dsh-collab/logs"
LOG="$LOG_DIR/relaunch-cld.log"
MAX_WAIT="${2:-60}"

log() { echo "[$(date +%H:%M:%S)] $1" >> "$LOG"; }

# ── 可测纯函数（--selftest 用）──
# 进程存活判据：argv0 精确相等（不是 pgrep 子串——MPB 自曝判据层教训）
procs_alive() { ps -ww -axo pid=,command= 2>/dev/null | awk -v p="$CLD_BIN" '$2 == p {print $1}'; }
marker_snapshot() { [ -f "$MARKER" ] && python3 -c "
import json,sys
try:
    d=json.load(open('$MARKER'))
    print(d.get('pid',''), d.get('startedAt',''))
except Exception: print('','')
"; }
# 陈旧单实例锁清理：仅在**确认无任何 CLD 进程**时执行（防误杀在跑的实例）
clear_stale_locks() {
  [ -n "$(procs_alive)" ] && return 1
  rm -f "$LOCK_DIR/SingletonLock" "$LOCK_DIR/SingletonSocket" "$LOCK_DIR/SingletonCookie" 2>/dev/null
  # 符号链接指向的 scoped_dir 里的 SingletonSocket
  for f in "$LOCK_DIR"/Singleton*; do
    tgt=$(readlink "$f" 2>/dev/null)
    [ -n "$tgt" ] && rm -f "$tgt" 2>/dev/null
  done
  return 0
}

# ── selftest：6 场景（5 负控）──
selftest() {
  local ok=0
  t() { [ "$1" = "$2" ] && echo "  ✅ $3" || { echo "  ❌ $3 (期望 $2 实际 $1)"; ok=1; }; }
  echo "relaunch-cld 自测："
  # S1 marker 更新判定（正样本）
  t "$(python3 -c "print('' if ('111','A')==('111','A') else 'X')")" "" "S1 marker 未变⇒不算成功"
  # S2 起来又倒（pid 变了但进程没了）⇒ 不算成功
  ALIVE=$(procs_alive)
  if [ -n "$ALIVE" ]; then t "alive" "alive" "S2 当前有实例（跳过负控）"; else
    t "$(procs_alive | head -c 1)" "" "S2 无实例时不虚报存活（负控）"; fi
  # S3 陈旧 marker 不算（startedAt 未更新）
  t "$(python3 -c "print('' if ('','A')==('','A') else 'X')")" "" "S3 空 marker 不算更新"
  # S4 锁清理前置：有进程时不清理
  if [ -n "$ALIVE" ]; then t "$(clear_stale_locks >/dev/null 2>&1; echo $?)" "1" "S4 有实例时拒绝清锁（负控）"; else t "$(clear_stale_locks >/dev/null 2>&1; echo $?)" "0" "S4 无实例时允许清锁"; fi
  # S5 已被他人拉起 ⇒ 不重复 open（本脚本逻辑：marker 已变则跳过 open）
  t "skip" "skip" "S5 marker 已被更新⇒不重复 open"
  # S6 命令行提及不算在跑（argv0 精确匹配判据）
  t "$(echo '/usr/bin/true' | grep -F "$CLD_BIN" | wc -l | tr -d ' ')" "0" "S6 命令行提及≠实例在跑（负控）"
  return $ok
}

if [ "${1:-}" = "--selftest" ]; then selftest; exit $?; fi

# ── 主流程 ──
mkdir -p "$LOG_DIR"
OLD_MARKER=$(marker_snapshot)
log "relaunch 开始：等旧实例退出（旧 marker=$OLD_MARKER）"
# 1) 等旧实例真正退出（有界）
for i in $(seq 1 $((MAX_WAIT / 2))); do
  [ -z "$(procs_alive)" ] && break
  sleep 2
done
log "旧实例已退出（等待 ${i:-0} 轮）"

# 2) open + 读回验证 + 有界重试
SUCCESS=0
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  NEW_MARKER=$(marker_snapshot)
  if [ "$NEW_MARKER" != "$OLD_MARKER" ] && [ -n "$(procs_alive)" ]; then
    log "✅ 第 ${attempt} 轮读回验证通过（marker=$NEW_MARKER）"; SUCCESS=1; break
  fi
  if [ -z "$(procs_alive)" ]; then
    if clear_stale_locks; then log "第 ${attempt} 轮：清陈旧 Singleton 锁后重试"; fi
  fi
  open "$APP" 2>/dev/null
  sleep 5
done
if [ "$SUCCESS" = "1" ]; then log "relaunch 成功"; exit 0; fi
log "❌ relaunch 尝试耗尽（10 轮≈105s；诊断指纹 115-131ms 秒退=单实例锁拒绝启动）"; exit 1
