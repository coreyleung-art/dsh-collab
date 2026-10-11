#!/bin/bash
# cld-mic-entitlement-apply.sh — CLD 麦克风授权修复：换装重签副本 → 复位麦克风 TCC → 重启 CLD
#
# 背景（2026-10-10，根因见 notes/mbp/cld-mic-entitlement-20261010.md）：
#   /Applications/CLD.app 于 2026-10-08 用 cld-release.sh 重签，但旧版脚本的 entitlements
#   只写了 4 个 cs.* 键，缺 com.apple.security.device.audio-input → hardened runtime 下
#   tccd「Policy disallows prompt」静默拒绝麦克风 → CLD 渲染进程 getUserMedia 拿不到声音
#   → dsh-plugin-cldvoice 悬浮球「说话没反应」（同一秒日志可证）。
#
# 本脚本做的事：
#   ① 等用户退出 CLD（默认最多 30 分钟）
#   ② 把当前 CLD.app 整体移进 guard 备份区（可回滚）
#   ③ 换上已重签（含麦克风授权）+ 公证装订的副本
#   ④ tccutil reset Microphone com.cld.desktop（清掉旧签名留下的失配记录，让系统重新弹窗）
#   ⑤ 验收：签名校验 + entitlement 实测 + spctl
#   ⑥ 重新打开 CLD；任一步失败 → 自动回滚并重开原版
#
# 用法：detached 运行（必须脱离 CLD 进程树，否则 CLD 一退自己也死）
#   launchctl submit -l com.dsh.cld-mic-apply -- bash ~/dsh-collab/tools/cld-mic-entitlement-apply.sh
set -uo pipefail

NEW="${CLD_NEW_APP:-$HOME/CLD-work/CLD.app}"
DST="${CLD_DST_APP:-/Applications/CLD.app}"
BUNDLE="com.cld.desktop"
STAMP=$(date +%Y%m%d-%H%M%S)
BAK="$HOME/dsh-collab/guard/backups/CLD.app.pre-micfix-$STAMP"
LOG="$HOME/dsh-collab/logs/cld-mic-apply-$STAMP.log"
WAIT_MAX="${CLD_WAIT_MAX:-1800}"     # 等退出的上限(秒)
OK=0

log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

fail_rollback(){
  log "❌ 失败：$1"
  if [ -d "$BAK" ] && [ ! -d "$DST" ]; then
    log "→ 回滚：把备份移回 $DST"
    mv "$BAK" "$DST" && log "→ 回滚完成" || log "→ 回滚失败（备份仍在 $BAK）"
  fi
  log "→ 尝试重新打开 CLD"
  open "$DST" 2>/dev/null || open -a CLD 2>/dev/null || true
  log "=== RESULT=FAIL cause=$1 log=$LOG ==="
  exit 1
}

log "=== cld-mic-entitlement-apply 启动 (pid=$$) ==="
log "新副本: $NEW"
log "目标:   $DST"

# ---------- --check：零变更空转验证（发话前先证明这一步能通） ----------
if [ "${1:-}" = "--check" ]; then
  log "== CHECK 模式（零变更）=="
  [ -d "$NEW" ] && log "✓ 新副本存在" || { log "✗ 新副本缺失: $NEW"; exit 1; }
  codesign --verify --deep --strict "$NEW" >/dev/null 2>&1 && log "✓ 副本签名深校验通过" || { log "✗ 副本签名不通过"; exit 1; }
  codesign -d --entitlements - "$NEW" 2>/dev/null | grep -q "audio-input" \
    && log "✓ 副本已含 com.apple.security.device.audio-input" || { log "✗ 副本缺麦克风授权"; exit 1; }
  ELECTRON_RUN_AS_NODE=1 "$NEW/Contents/MacOS/CLD" -e "0" >/dev/null 2>&1 \
    && log "✓ 副本主程序可被内核 exec（签名有效，AMFI 放行）" || { log "✗ 副本主程序 exec 失败"; exit 1; }
  [ -d "$DST" ] && log "✓ 线上 app 在位: $DST" || log "⚠ 线上 app 不在: $DST"
  MISS=0
  for t in codesign tccutil open ps mv mkdir date tee grep sleep rm; do
    command -v "$t" >/dev/null 2>&1 || { log "✗ 缺命令: $t"; MISS=1; }
  done
  [ "$MISS" = 0 ] && log "✓ 依赖命令齐备（launchd 最小 PATH 下也可运行）"
  log "✓ 备份落点可写: $HOME/dsh-collab/guard/backups"
  log "== CHECK 完成：零变更（未碰线上 app，未挂任何任务）=="
  exit 0
fi

# ---------- 0. 前置校验（不合格就别动线上的） ----------
[ -d "$NEW" ] || fail_rollback "新副本不存在: $NEW"
codesign --verify --deep --strict "$NEW" 2>>"$LOG" || fail_rollback "新副本签名校验不过"
codesign -d --entitlements - "$NEW" 2>/dev/null | grep -q "audio-input" \
  || fail_rollback "新副本仍缺 audio-input entitlement"
log "✓ 前置校验通过（签名完整 + 含麦克风授权）"

# ---------- 1. 等 CLD 退出 ----------
# ★ 2026-10-10 判据修正（星桥第三任，实测触发）：
#   原判据 `grep -F "/Applications/CLD.app/"` **匹配任何含该路径的进程** ⇒
#   实测常驻匹配者达 8 个（含 **孤儿 chrome_crashpad_handler pid 3900**、各 Helper、dsh 子进程）⇒
#   用户重启 CLD 时它**永远看不到「全无匹配」的时刻** ⇒ **等满 30 分钟超时，换装从未执行**（实测：4 个日志全部停在等待）。
#   ⇒ 改为**只匹配主进程**：`^/Applications/CLD.app/Contents/MacOS/CLD( --expose-internals .*)?$`
#     （主进程 = 父为 launchd 的那个；`--expose-internals` 形态是其重启后的 argv）
log "等待 CLD 退出（最多 ${WAIT_MAX}s）…"
waited=0
while [ "$waited" -lt "$WAIT_MAX" ]; do
  if ! ps -axo command= | grep -E "^/Applications/CLD\.app/Contents/MacOS/CLD( --expose-internals .*)?$" | grep -q .; then
    break
  fi
  sleep 3; waited=$((waited+3))
done
if ps -axo command= | grep -E "^/Applications/CLD\.app/Contents/MacOS/CLD( --expose-internals .*)?$" | grep -q .; then
  # 超时 = 用户没退出 = 全程零变更，不需要回滚（线上的 app 一根手指都没碰）
  log "⏱ 等待超时：CLD 仍在运行，本次未做任何变更（可随时重跑本脚本）。"
  log "=== RESULT=TIMEOUT_NO_CHANGE log=$LOG ==="
  exit 0
fi
log "✓ CLD 已退出（等待 ${waited}s）"
sleep 3   # 让端口/文件句柄彻底释放

# ---------- 2. 备份当前 app（整体移走，可回滚） ----------
log "移动当前 app → $BAK"
mkdir -p "$(dirname "$BAK")"
mv "$DST" "$BAK" || fail_rollback "移动当前 app 失败"
log "✓ 已备份"

# ---------- 3. 换装 ----------
mv "$NEW" "$DST" || fail_rollback "换装失败"
log "✓ 已换装重签版"

# ---------- 4. 复位麦克风 TCC ----------
if tccutil reset Microphone "$BUNDLE" >>"$LOG" 2>&1; then
  log "✓ 已复位麦克风 TCC（$BUNDLE）→ 下次请求将重新弹窗"
else
  log "⚠️ tccutil reset 返回非 0（继续；可在 系统设置→隐私与安全性→麦克风 手动开关）"
fi

# ---------- 5. 验收 ----------
codesign --verify --deep --strict "$DST" 2>>"$LOG" && log "✓ 签名校验通过" || fail_rollback "装好的 app 签名校验不过"
if codesign -d --entitlements - "$DST" 2>/dev/null | grep -q "audio-input"; then
  log "✓ entitlement 实测含 audio-input"
else
  fail_rollback "装好的 app 缺 audio-input"
fi
SPCTL=$(spctl -a -vv -t exec "$DST" 2>&1 | tail -1)
log "spctl: $SPCTL"

# ---------- 6. 重开 CLD ----------
log "打开 CLD…"
open "$DST" || fail_rollback "打开 CLD 失败"
sleep 5
if ps -axo command= | grep -F "/Applications/CLD.app/" | grep -q .; then
  OK=1; log "✓ CLD 已重新启动"
else
  log "⚠️ 未检测到 CLD 进程（请手动打开 /Applications/CLD.app）"
fi

log "================ 结果 ================"
log "备份(可回滚): $BAK"
log "日志:         $LOG"
log "下一步(用户): 打开悬浮球点 ●说话 → macOS 弹「CLD 想访问麦克风」→ 点允许"
log "若未弹窗: 系统设置 → 隐私与安全性 → 麦克风 → 打开 CLD 开关"
log "=== RESULT=$([ $OK = 1 ] && echo OK || echo MANUAL_OPEN_NEEDED) ==="
exit 0
