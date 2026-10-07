#!/usr/bin/env bash
# test-hot-reload.sh —— POST /reload 热重载功能验收（v1.0.0，2026-10-04）
#
# 为什么需要：壳 v3 的 reloadDsh 宽限定时器误杀新 dsh ⇒ 1/3 崩溃循环（10-03 16:06:59 实测），
# 故本项目长期**禁用** POST /reload。壳已升 v4（定点移植 oldChild 捕获 + 显式 return + oldChild kill），
# 本脚本用于**解禁前的功能验收**：证明"重载能成功、且不产生崩溃循环、且应用壳不退出（无需拉起）"。
#
# 判据（★ 测试前定义，避免事后解释）：
#  P1 壳不退出：CLD 主进程 pid 不变 **且** exit-marker.json 的 startedAt 不变（未重启）
#  P2 dsh 换代：dsh 运行时子进程 pid 改变
#  P3 生命周期完整：日志出现「触发重载 dsh」→「旧 dsh 已退出」→「新 dsh 就绪」
#  P4 无循环：触发重载**恰好 1 次**、无「已在进行中」重复、无 dsh-crash 痕迹
#  P5 端口换代：`dsh web:` 地址变化（窗口 loadURL 到新地址）
# 失败即任何一条不成立 ⇒ 维持禁用。
#
# 用法： test-hot-reload.sh [延迟秒=20]     （由 nohup/detached 启动，日志 data/ops/hot-reload-test.log）
set -u
DLY=${1:-20}
OPS="$HOME/dsh-collab/data/ops"
LOG="$OPS/hot-reload-test.log"
DSHLOG="$HOME/.cld/logs/dsh-web.log"
MARKER="$HOME/.cld/logs/exit-marker.json"
CRASH="$HOME/.cld/logs/crash-reason.log"
PATTERN="/Applications/CLD.app/Contents/MacOS/CLD"
mkdir -p "$OPS"
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }

procs() { ps -ww -axo pid=,command= | awk -v p="$PATTERN" '$2==p {print $1, ($3=="" ? "APP" : "DSH")}'; }
app_pid() { ps -ww -axo pid=,command= | awk -v p="$PATTERN" '$2==p && NF==2 {print $1; exit}'; }
dsh_pid() { ps -ww -axo pid=,command= | awk -v p="$PATTERN" '$2==p && NF>2 {print $1; exit}'; }
boot_sig() { python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d.get("startedAt"),d.get("pid"))' "$MARKER" 2>/dev/null; }
web_url() { grep -o 'http://127.0.0.1:[0-9]*' "$DSHLOG" 2>/dev/null | tail -1; }

log "════ 热重载验收开始（延迟 ${DLY}s 后 POST /reload）════"
B_APP="$(app_pid)"; B_DSH="$(dsh_pid)"; B_BOOT="$(boot_sig)"; B_URL="$(web_url)"
B_CRASH_LINES=$(wc -l <"$CRASH" 2>/dev/null | tr -d ' ')
log "  重载前：app=$B_APP dsh=$B_DSH boot=[$B_BOOT] url=$B_URL"
[ -n "$B_APP" ] && [ -n "$B_DSH" ] || { log "❌ 前置失败：识别不到 app/dsh 进程 ⇒ 中止"; exit 2; }

sleep "$DLY"
TS=$(date '+%F %T')
MARK_LINE=$(wc -l <"$DSHLOG" 2>/dev/null | tr -d ' ')
log "  发出 POST /reload（本机 31888）"
RESP=$(curl -s -m 10 -X POST "http://127.0.0.1:31888/reload" 2>&1)
log "  响应: $RESP"

# 等新 dsh 就绪（最多 90s）
NEW=0
for i in $(seq 1 180); do
  if tail -n +"$((MARK_LINE + 1))" "$DSHLOG" 2>/dev/null | grep -q "新 dsh 就绪"; then NEW=1; break; fi
  sleep 0.5
done

A_APP="$(app_pid)"; A_DSH="$(dsh_pid)"; A_BOOT="$(boot_sig)"; A_URL="$(web_url)"
NEWLOG=$(tail -n +"$((MARK_LINE + 1))" "$DSHLOG" 2>/dev/null)
N_TRIG=$(printf '%s' "$NEWLOG" | grep -c "触发重载 dsh")
N_OLD=$(printf '%s' "$NEWLOG" | grep -c "旧 dsh 已退出")
N_NEW=$(printf '%s' "$NEWLOG" | grep -c "新 dsh 就绪")
N_BUSY=$(printf '%s' "$NEWLOG" | grep -c "已在进行中")
A_CRASH_LINES=$(wc -l <"$CRASH" 2>/dev/null | tr -d ' ')
DELTA_CRASH=$(( ${A_CRASH_LINES:-0} - ${B_CRASH_LINES:-0} ))
log "  重载后：app=$A_APP dsh=$A_DSH boot=[$A_BOOT] url=$A_URL"
log "  日志计数：触发=$N_TRIG 旧退=$N_OLD 新就绪=$N_NEW 进行中拒绝=$N_BUSY｜crash 新增行=$DELTA_CRASH"

PASS=0; FAIL=0
chk() { if [ "$2" = "1" ]; then log "  ✅ $1"; PASS=$((PASS+1)); else log "  ❌ $1"; FAIL=$((FAIL+1)); fi; }
chk "P1 壳未退出（app pid $B_APP→${A_APP:-无} 且 boot 未变）" "$([ "$A_APP" = "$B_APP" ] && [ "$A_BOOT" = "$B_BOOT" ] && echo 1 || echo 0)"
chk "P2 dsh 换代（$B_DSH→${A_DSH:-无}）" "$([ -n "$A_DSH" ] && [ "$A_DSH" != "$B_DSH" ] && echo 1 || echo 0)"
chk "P3 生命周期完整（触发/旧退/新就绪 各≥1）" "$([ "$N_TRIG" -ge 1 ] && [ "$N_OLD" -ge 1 ] && [ "$N_NEW" -ge 1 ] && echo 1 || echo 0)"
chk "P4 无循环（触发恰好 1 次=$N_TRIG、无进行中=$N_BUSY、无新 crash 行=$DELTA_CRASH）" \
    "$([ "$N_TRIG" -eq 1 ] && [ "$N_BUSY" -eq 0 ] && [ "$DELTA_CRASH" -eq 0 ] && echo 1 || echo 0)"
chk "P5 端口换代（$B_URL→${A_URL:-无}）" "$([ -n "$A_URL" ] && [ "$A_URL" != "$B_URL" ] && echo 1 || echo 0)"

if [ "$FAIL" = "0" ]; then log "════ 判定：✅ PASS（$PASS/5）⇒ 可解禁 POST /reload ════"
else log "════ 判定：❌ FAIL（通过 $PASS / 失败 $FAIL）⇒ 维持禁用 ════"; fi
[ "$FAIL" = "0" ] || exit 1
