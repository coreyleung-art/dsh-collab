#!/bin/bash
# cld-reopen-correct-path.sh — 极简：等 CLD 退出 → 从 /Applications 重开（**不含 mv/换装**）
#
# ★ 为什么需要它（2026-10-10 实测）：
#   换装脚本在 mv 备份与 open 之间与用户手动开 CLD 发生**竞态** ⇒
#   结果运行的是【备份路径里的旧 app】（audio-input=0）⇒ 麦克风仍不可用。
#   ⇒ 本脚本**只做一件事**：确保退出后从**规范路径**重开。
#
# ★ 与换装脚本的判据差异（吸取教训）：
#   只匹配**主进程**（不匹配 crashpad / Helper / dsh）—— 避免上一版那样永远等不到退出。
set -uo pipefail
DST="/Applications/CLD.app"
LOG="$HOME/dsh-collab/logs/cld-reopen-$(date +%Y%m%d-%H%M%S).log"
WAIT_MAX="${CLD_WAIT_MAX:-1800}"
log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

alive(){ ps -axo command= | grep -qE "^/Applications/CLD\.app/Contents/MacOS/CLD( --expose-internals .*)?$"; }

log "=== cld-reopen 启动（pid=$$）==="
log "目标: $DST"
[ -d "$DST" ] || { log "❌ 目标不存在"; log "=== RESULT=FAIL ==="; exit 1; }
N=$(codesign -d --entitlements - "$DST" 2>/dev/null | grep -c "audio-input")
log "前置校验: audio-input=$N $([ "$N" -ge 1 ] && echo '✅' || echo '（注意：为 0 时换装未成功）')"

log "等待 CLD 退出（最多 ${WAIT_MAX}s）…"
w=0
while [ "$w" -lt "$WAIT_MAX" ] && alive; do sleep 3; w=$((w+3)); done
if alive; then
  log "⏱ 超时：CLD 仍在运行，未做任何变更"
  log "=== RESULT=TIMEOUT_NO_CHANGE ==="; exit 0
fi
log "✓ CLD 已退出（等待 ${w}s）"
sleep 3
log "从规范路径打开：$DST"
if open "$DST"; then
  sleep 6
  if alive; then
    log "✓ 已重开"
    # ★ 关键：核验新进程的映像路径确实是 /Applications（不是备份路径）
    P=$(ps -axo pid=,command= | grep -E "^ *[0-9]+ /Applications/CLD\.app/Contents/MacOS/CLD$" | awk '{print $1}' | head -1)
    IMG=$(lsof -p "$P" 2>/dev/null | awk '$4=="txt"{print $NF; exit}')
    log "新进程 pid=$P"
    log "映像路径: $IMG"
    case "$IMG" in
      /Applications/CLD.app/*) log "✅ 映像来自 /Applications（正确）"; log "=== RESULT=OK ===" ;;
      *) log "❌ 映像来自别处：$IMG"; log "=== RESULT=WRONG_PATH ===" ;;
    esac
  else
    log "⚠️ 未检测到进程"; log "=== RESULT=NOT_STARTED ==="
  fi
else
  log "❌ open 失败"; log "=== RESULT=FAIL ==="
fi
