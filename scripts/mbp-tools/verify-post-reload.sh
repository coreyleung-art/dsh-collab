#!/usr/bin/env bash
# verify-post-reload.sh —— 热重载后自动验收（v1.0.0，2026-10-04）
#
# 为什么必须独立进程：POST /reload 会杀掉发起者所在的 dsh 运行时（同进程组连坐，见 hazards#G36）
#   ⇒ 发起方自己写不出结论；本脚本必须用 setsid 启动（tools/spawn-detached.sh）。
#
# 判据（测试前定义）：
#   P1 壳未退出：CLD 主进程 pid 不变 且 exit-marker.json 的 startedAt 不变
#   P2 dsh 换代：dsh 运行时子进程 pid 改变
#   P3 生命周期：日志出现「触发重载 dsh」→「旧 dsh 已退出」→「新 dsh 就绪」
#   P4 无循环：触发恰好 1 次、无「已在进行中」、crash-reason.log 无新增行
#   P5 端口换代：`dsh web:` 地址变化
#   P6 插件生效：磁盘 + 运行时投递探针（POST /agent-bus/api/send ⇒ delivered）
#
# 用法： verify-post-reload.sh [延迟秒=45]
set -u
DLY=${1:-45}
EXP_VER=${2:-}   # 期望版本；省略则取当前磁盘版本
OPS="$HOME/dsh-collab/data/ops"
LOG="$OPS/post-reload-verify.log"
DSHLOG="$HOME/.cld/logs/dsh-web.log"
MARKER="$HOME/.cld/logs/exit-marker.json"
CRASH="$HOME/.cld/logs/crash-reason.log"
PLUGIN="$HOME/.dsh/profiles/web/node_modules/dsh-plugin-agent-way/package.json"
PATTERN="/Applications/CLD.app/Contents/MacOS/CLD"
MY_SESSION="session-20b800d4-98f6-4e5e-90e4-34f7b6ca61d7"
mkdir -p "$OPS"
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }
# EXIT trap（记录异常退出点；本脚本 12:23 那次在 P6 后静默死掉，教训=失败必须出声）
trap 'rc=$?; log "  ⚠️ 脚本退出（rc=$rc，行 ${LINENO} 附近）"' EXIT

app_pid() { ps -ww -axo pid=,command= | awk -v p="$PATTERN" '$2==p && NF==2 {print $1; exit}'; }
dsh_pid() { ps -ww -axo pid=,command= | awk -v p="$PATTERN" '$2==p && NF>2 {print $1; exit}'; }
bootsig() { python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("startedAt"),d.get("pid"))' "$MARKER" 2>/dev/null; }
weburl()  { grep -o 'http://127.0.0.1:[0-9]*' "$DSHLOG" 2>/dev/null | tail -1; }

log "════ 热重载后验收开始（延迟 ${DLY}s 触发）════"
B_APP="$(app_pid)"; B_DSH="$(dsh_pid)"; B_BOOT="$(bootsig)"; B_URL="$(weburl)"
B_CRASH=$(wc -l <"$CRASH" 2>/dev/null | tr -d ' '); B_VER=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$PLUGIN" 2>/dev/null)
log "  前：app=$B_APP dsh=$B_DSH boot=[$B_BOOT] url=$B_URL 插件版本=$B_VER crash行=$B_CRASH"
[ -n "$B_APP" ] && [ -n "$B_DSH" ] || { log "❌ 前置失败：识别不到 app/dsh ⇒ 中止"; exit 2; }

sleep "$DLY"
MARK=$(wc -l <"$DSHLOG" 2>/dev/null | tr -d ' ')
log "  发出 POST /reload → $(curl -s -m 10 -X POST http://127.0.0.1:31888/reload 2>&1)"

NEW=0
for i in $(seq 1 180); do
  if tail -n +"$((MARK + 1))" "$DSHLOG" 2>/dev/null | grep -q "新 dsh 就绪"; then NEW=1; break; fi
  sleep 0.5
done
A_APP="$(app_pid)"; A_DSH="$(dsh_pid)"; A_BOOT="$(bootsig)"; A_URL="$(weburl)"
NEWLOG=$(tail -n +"$((MARK + 1))" "$DSHLOG" 2>/dev/null)
N_TRIG=$(printf '%s' "$NEWLOG" | grep -c "触发重载 dsh"); N_OLD=$(printf '%s' "$NEWLOG" | grep -c "旧 dsh 已退出")
N_NEW=$(printf '%s' "$NEWLOG" | grep -c "新 dsh 就绪"); N_BUSY=$(printf '%s' "$NEWLOG" | grep -c "已在进行中")
A_CRASH=$(wc -l <"$CRASH" 2>/dev/null | tr -d ' '); A_VER=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["version"])' "$PLUGIN" 2>/dev/null)
log "  后：app=$A_APP dsh=$A_DSH boot=[$A_BOOT] url=$A_URL 插件版本=$A_VER crash行=$A_CRASH"
log "  计数：触发=$N_TRIG 旧退=$N_OLD 新就绪=$N_NEW 进行中=$N_BUSY crash新增=$(( ${A_CRASH:-0} - ${B_CRASH:-0} ))"

# P6 投递探针（用新端口）
PORT=$(printf '%s' "$A_URL" | grep -o '[0-9]*$')
PROBE="reload-probe-$(date +%s)"
DELIV="(未探测)"; TRY=0
# ★ 探测前必须等目标会话上线（reload 后会话需数秒恢复，否则必然 queued —— 12:15 / 12:23 两次实测教训）
for t in 1 2 3 4 5; do
  TRY=$t
  if [ -n "$PORT" ]; then
    R=$(curl -s -m 15 -X POST -H "Host: 127.0.0.1:$PORT" -H 'Content-Type: application/json' \
          -d "{\"to\":\"$MY_SESSION\",\"text\":\"$PROBE-t$t\"}" "http://127.0.0.1:$PORT/agent-bus/api/send" 2>&1)
    DELIV=$(printf '%s' "$R" | python3 -c 'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("status") or d)
except Exception: print("parse-fail")' 2>/dev/null || echo raw)
  fi
  printf '%s' "$DELIV" | grep -q delivered && break
  log "  P6 第 $t 次探针：$DELIV（等 10s 重试，等目标会话上线）"
  sleep 10
done
log "  P6 投递探针（to=self，共 $TRY 次）：$DELIV"

PASS=0; FAIL=0
chk() { if [ "$2" = "1" ]; then log "  ✅ $1"; PASS=$((PASS+1)); else log "  ❌ $1"; FAIL=$((FAIL+1)); fi; }
chk "P1 壳未退出（app $B_APP→${A_APP:-无}，boot 未变）" "$([ "$A_APP" = "$B_APP" ] && [ "$A_BOOT" = "$B_BOOT" ] && echo 1 || echo 0)"
chk "P2 dsh 换代（$B_DSH→${A_DSH:-无}）" "$([ -n "$A_DSH" ] && [ "$A_DSH" != "$B_DSH" ] && echo 1 || echo 0)"
chk "P3 生命周期完整（触发$N_TRIG/旧退$N_OLD/新就绪$N_NEW）" "$([ "$N_TRIG" -ge 1 ] && [ "$N_OLD" -ge 1 ] && [ "$N_NEW" -ge 1 ] && echo 1 || echo 0)"
chk "P4 无循环（触发=1 且 进行中=0 且 crash无新增）" "$([ "$N_TRIG" -eq 1 ] && [ "$N_BUSY" -eq 0 ] && [ "$A_CRASH" = "$B_CRASH" ] && echo 1 || echo 0)"
chk "P5 端口换代（$B_URL→${A_URL:-无}）" "$([ -n "$A_URL" ] && [ "$A_URL" != "$B_URL" ] && echo 1 || echo 0)"
[ -n "$EXP_VER" ] || EXP_VER="$B_VER"
PLUG_MTIME=$(stat -f %m "$PLUGIN" 2>/dev/null || echo 0)
DSH_START=$(ps -o lstart= -p "${A_DSH:-0}" 2>/dev/null | sed "s/^ *//")
DSH_EPOCH=$(date -j -f "%a %b %d %T %Y" "$DSH_START" "+%s" 2>/dev/null || echo 0)
log "  P6/P7 依据：期望版本=$EXP_VER ｜ 磁盘=$A_VER ｜ 插件 mtime=$(date -r "$PLUG_MTIME" '+%T' 2>/dev/null) ｜ dsh 启动=$DSH_START（epoch=$DSH_EPOCH）"
chk "P6 磁盘版本=$EXP_VER 且投递 delivered（实测：$DELIV）" "$([ "$A_VER" = "$EXP_VER" ] && printf '%s' "$DELIV" | grep -q delivered && echo 1 || echo 0)"
N_CG_ERR=$(printf '%s' "$NEWLOG" | grep -icE "channel-gate.*(error|cannot find|failed)|error.*channel-gate" || true)
N_CI_ERR=$(printf '%s' "$NEWLOG" | grep -icE "central-inbox.*(error|cannot find|failed)|error.*central-inbox" || true)
chk "P8 新/改插件装载无错误（channel-gate 错 $N_CG_ERR 行 / central-inbox 错 $N_CI_ERR 行）" "$([ "${N_CG_ERR:-1}" -eq 0 ] && [ "${N_CI_ERR:-1}" -eq 0 ] && echo 1 || echo 0)"
chk "P7 新 dsh 诞生晚于插件文件（⇒ 装载的是新代码）" "$([ "${DSH_EPOCH:-0}" -ge "${PLUG_MTIME:-0}" ] && echo 1 || echo 0)"

if [ "$FAIL" = "0" ]; then log "════ 判定：✅ PASS（$PASS/8）⇒ agent-way 1.5.19 已生效，/reload 通道可用 ════"
else log "════ 判定：❌ FAIL（通过 $PASS / 失败 $FAIL）════"; fi
[ "$FAIL" = "0" ] || exit 1
