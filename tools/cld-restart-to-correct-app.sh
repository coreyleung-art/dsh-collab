#!/bin/bash
# cld-restart-to-correct-app.sh — 把 CLD 切到 /Applications 的正确版本
#
# ★ 判据修正（2026-10-10 实测教训）：
#   判断「CLD 是否在运行」**不能用 `ps` 的 argv** —— 若 app 目录被 `mv` 过，
#   argv 仍显示旧路径而映像已在新位置 ⇒ **argv 会被 mv 欺骗**（实测假阴性）。
#   ⇒ 本脚本用 **lsof 的 txt 段（真实映像路径）**判存活。
#
# ★ 启动方式：必须 detached（本脚本会先 kill CLD，而 CLD 一死其子进程全灭）。
#   用 `setsid` 或 launchd；**不用 submit**（上次它把 job 反复重启 ⇒ 每 10 秒抢焦点）。
set -uo pipefail
DST="/Applications/CLD.app"
LOG="$HOME/dsh-collab/logs/cld-restart-$(date +%Y%m%d-%H%M%S).log"
log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG"; }

# 真实映像 pids（只认 /Applications 或 backups 下的 CLD 主可执行）
real_pids(){ for p in $(ps -axo pid=,command= | awk '/CLD\.app\/Contents\/MacOS\/CLD$/ && !/--expose-internals/ {print $1}'); do
  img=$(lsof -p "$p" 2>/dev/null | awk '$4=="txt"{print $NF; exit}')
  case "$img" in */Contents/MacOS/CLD) echo "$p|$img";; esac
done; }

# ★★ 为何本脚本【不含】`launchctl remove <自身>`（2026-10-10 实测事故 + 门拦验证）：
#   · 事故：初版在开头写 `launchctl remove <本脚本的 label>` 想取消保活 ⇒
#     **launchd 连同该 job 的子进程一起杀掉** ⇒ 脚本什么都没做就死了（日志未生成、CLD 未变）。
#   · ★ 该形态现已被 **`tools/self-destruct-gate.py`（自指破坏门）** 覆盖，实测：
#       对含该行的版本 ⇒ `REJECT`（L23 原语目标字面等于自身标识）；对本版本 ⇒ `PASS`。
#   · **正解**：① **取消 job 的动作移到【外部】**（入口门：不由 job 自己触发）；
#             ② 脚本内改用**幂等性**防反复骚扰（第二次跑检测到已是正确版本即 NO_ACTION_NEEDED，
#                **不执行任何 open**）⇒ 即使被保活重启也不会抢焦点。
#   · ★ 另注：判断 app 版本**必须用 lsof 的映像路径**，不能用 `ps` 的 argv ——
#     实测 app 目录被 mv 后 argv 仍显示旧路径而映像已在新位置（**argv 会被 mv 欺骗**）。

log "=== cld-restart 启动（pid=$$）==="
log "目标: $DST （audio-input=$(codesign -d --entitlements - "$DST" 2>/dev/null | grep -c audio-input)）"
log "当前实例（pid|映像）:"
real_pids | sed 's/^/    /'

WRONG=$(real_pids | grep -c "backups" || true)
if [ "$WRONG" -eq 0 ]; then
  log "✓ 无错误实例 ⇒ 无需重启"
  log "=== RESULT=NO_ACTION_NEEDED ==="; exit 0
fi

log "→ 终止错误实例（备份路径下的）…"
real_pids | grep backups | cut -d'|' -f1 | while read pid; do
  log "   kill $pid"
  kill "$pid" 2>/dev/null
done
sleep 6
# 优雅退出失败则强杀
for i in 1 2 3; do
  LEFT=$(real_pids | grep -c backups || true)
  [ "$LEFT" -eq 0 ] && break
  log "   仍有 $LEFT 个，等待 4s…"; sleep 4
done
real_pids | grep backups | cut -d'|' -f1 | while read pid; do log "   kill -9 $pid"; kill -9 "$pid" 2>/dev/null; done
sleep 4

log "→ 从规范路径打开: $DST"
open "$DST" || { log "❌ open 失败"; log "=== RESULT=FAIL ==="; exit 1; }
sleep 8

log "→ 核验映像路径（★ 用 lsof，不用 ps）:"
OK=0
for line in $(real_pids); do
  pid=${line%%|*}; img=${line##*|}
  log "   pid=$pid  映像=$img"
  case "$img" in /Applications/CLD.app/*) OK=1;; esac
done
if [ "$OK" = 1 ]; then log "✅ 映像已来自 /Applications"; log "=== RESULT=OK ==="
else log "❌ 仍未切到 /Applications"; log "=== RESULT=WRONG_PATH ==="; fi
