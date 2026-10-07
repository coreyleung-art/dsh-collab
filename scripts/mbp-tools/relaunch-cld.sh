#!/usr/bin/env bash
# relaunch-cld.sh —— 受控重启后的「可靠拉起 + 闭环验证」守护（v1.0.0，2026-10-04）
#
# 背景（实测根因，非推测）：
#   agent-way 的 quick-restart 守护只做一次 `sleep countdown+2; open -a CLD.app`，
#   既不验证结果也不重试。2026-10-04 11:42 实测：守护确实在 11:42:49.240 执行了 open，
#   LaunchServices 也确实建了 job 并拉起 pid 46749 —— 但该实例 1.4s 后干净退出
#   （launchd: termination reported (0,0,0)），且 free of 任何痕迹
#   （无 exit-marker.json boot、无 dsh spawn banner、无 exit-trace）。
#   排除法（全文件无 process.exit/app.exit；其余 10 处 app.quit() 都在 traceBoot() 之后
#   或会另起进程）指向唯一路径：main.js:1041 `requestSingleInstanceLock()` 返回 false
#   ⇒ app.quit()（before-quit 只在 else 分支注册 ⇒ 完全静默）。
#   即：**"没自动拉起"的真因是拉起动作成功、新实例被陈旧单实例锁静默杀掉。**
#
# 本脚本补齐四件事（每件都对应一条判据）：
#   ① 等旧实例真正退出（不是睡固定时长就 open）；
#   ② open 之后**读回验证**：进程存活 + exit-marker.json 的 startedAt 已更新到本次（新实例）；
#   ③ 失败**重试**（陈旧锁通常是瞬态，二次 open 常可成功）；
#   ④ 确认无 CLD 进程时**清理陈旧单实例锁**（SingletonLock/Socket/Cookie）后再试；
#   全程写日志（可观察），退出码语义：0=已起来 / 1=尝试耗尽 / 2=用法错 / 3=自测失败。
#
# 用法：
#   relaunch-cld.sh                          # 等 30s、最多 3 次、每次验证 25s
#   relaunch-cld.sh --wait 60 --attempts 5 --verify 30 --since <epoch>
#   relaunch-cld.sh --selftest               # 5 个场景（含 4 个负控），mock open/pgrep，无副作用
#   relaunch-cld.sh --dry-run                # 只打印将要执行的动作，不 open/不删锁
#
# 环境覆盖（跨端复用与自测用）：
#   CLD_APP CLD_PATTERN CLD_LOG CLD_MARKER CLD_SUPPORT CLD_DSHLOG CLD_OPEN_BIN CLD_PS_BIN
set -u

APP="${CLD_APP:-/Applications/CLD.app}"
PATTERN="${CLD_PATTERN:-/Applications/CLD.app/Contents/MacOS/CLD}"
LOG="${CLD_LOG:-$HOME/dsh-collab/data/ops/relaunch-cld.log}"
MARKER="${CLD_MARKER:-$HOME/.cld/logs/exit-marker.json}"
SUPPORT="${CLD_SUPPORT:-$HOME/Library/Application Support/CLD}"
DSHLOG="${CLD_DSHLOG:-$HOME/.cld/logs/dsh-web.log}"
OPEN_BIN="${CLD_OPEN_BIN:-open}"
PS_BIN="${CLD_PS_BIN:-ps}"

# ★ 2026-10-04 12:01 实测校准：老实例退出后**数十秒内**单实例锁仍被判为"占用"（新实例秒退，
#   签名=~115ms/exit 0/零输出）。取证：我 13s 内 4 次 open 全败（115/124/126/123ms），
#   用户 +35s 手动 open 成功 ⇒ **重试窗口必须 ≥90s 且间隔 ≥5s**，否则会误判"需人工重开"。
WAIT_SEC=30; ATTEMPTS=10; VERIFY_SEC=20; SETTLE_SEC=2; RETRY_GAP=5
SINCE=""; SELFTEST=0; DRY=0
EXIT_USAGE=2

# 抄对端（插件 1.5.19）守护日志尾部，便于并列回执（SOP §7 A1–A4）
peer_guard_tail() {
  [ -f "$HOME/dsh-collab/logs/agentway-relaunch.log" ] && \
    log "  （对照·插件守护）$(tail -2 "$HOME/dsh-collab/logs/agentway-relaunch.log" | tr '\n' '|')"
}

now() { date +%s; }
log() { mkdir -p "$(dirname "$LOG")" 2>/dev/null; printf '[%s] %s\n' "$(date '+%F %T')" "$*" >>"$LOG"; }
say() { [ "$DRY" = "1" ] && echo "$*" || true; }

usage() {
  sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'
}

# 存活判据：必须用 `ps -ww` 全命令行（实测教训两条，都是"判据判别力"问题）：
#   ① macOS 上 `pgrep -f <全路径>` 匹配不到 Electron 主进程（46770/46775），只返回 helper 子进程
#      ⇒ 会把"应用在跑"误判成"已退出"（dry-run 抓到的假阴性）；
#   ② 子串匹配整个命令行会被"别人命令行里提到该路径"骗过（如 `bash -c … grep -F <路径>`）
#      ⇒ 假阳性。故用 awk 严格比较 argv0（pid 后第一个字段）是否等于 PATTERN，
#      `ps -ww` 避免命令行按终端宽度截断。
ps_out()  { "$PS_BIN" -ww -axo pid=,command= 2>/dev/null || "$PS_BIN" -A -o pid=,command= 2>/dev/null; }
is_up()   { ps_out | awk -v p="$PATTERN" '$2 == p {f=1} END{exit !f}'; }
up_pids() { ps_out | awk -v p="$PATTERN" '$2 == p {printf "%s ", $1}'; }

marker_epoch() {
  python3 -c '
import json,sys,datetime
try:
    d=json.load(open(sys.argv[1]))
    s=d.get("startedAt") or ""
    print(int(datetime.datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()) if s else 0)
except Exception:
    print(0)
' "$MARKER" 2>/dev/null || echo 0
}

fresh_boot() { [ "$(marker_epoch)" -ge "$SINCE" ] 2>/dev/null; }

last_dsh_url() { tail -80 "$DSHLOG" 2>/dev/null | grep -o 'http://127.0.0.1:[0-9]*' | tail -1; }

clean_stale_locks() {
  local f target cleaned=0
  for f in SingletonLock SingletonSocket SingletonCookie; do
    if [ -L "$SUPPORT/$f" ] || [ -e "$SUPPORT/$f" ]; then
      target="$(readlink "$SUPPORT/$f" 2>/dev/null || echo '-')"
      if [ "$DRY" = "1" ]; then say "  [dry-run] 将清理 $SUPPORT/$f（原指向 $target）"
      else
        log "清理陈旧单实例锁：$f（原指向 $target）"
        rm -f "$SUPPORT/$f"
      fi
      cleaned=1
    fi
  done
  [ "$cleaned" = "1" ] || log "未发现陈旧单实例锁文件（无需清理）"
}

# ---------------------------------------------------------------- selftest
selftest() {
  local T rc pass=0 fail=0
  T="$(mktemp -d)"; mkdir -p "$T/bin" "$T/support"
  export CLD_LOG="$T/log.txt" CLD_MARKER="$T/marker.json" CLD_SUPPORT="$T/support"
  export CLD_APP="$T/Fake.app" CLD_PATTERN="Fake.app/Contents/MacOS/Fake"
  export CLD_OPEN_BIN="$T/bin/open" CLD_PS_BIN="$T/bin/ps" CLD_DSHLOG="$T/dsh.log"
  : >"$CLD_DSHLOG"

  # mock ps：仅当 $T/up 存在时"看到"目标进程（模拟真实 ps -ww -axo pid=,command= 输出）；
  # s6 = 诱饵场景：命令行里提到目标路径但不是 argv0 ⇒ 判据必须不认
  cat >"$CLD_PS_BIN" <<EOF
#!/bin/bash
case "\$(cat "$T/scenario" 2>/dev/null)" in
  s6) echo "12345 /bin/bash -c echo $T/Fake.app/Contents/MacOS/Fake"; exit 0 ;;
esac
[ -f "$T/up" ] && echo "99999 $T/Fake.app/Contents/MacOS/Fake"
exit 0
EOF
  # mock open：按 $T/scenario 决定行为，并计数
  cat >"$CLD_OPEN_BIN" <<'EOF'
#!/bin/bash
T="$(dirname "$(dirname "$0")")"
echo x >>"$T/open_calls"
case "$(cat "$T/scenario" 2>/dev/null)" in
  s1) python3 -c "import json,datetime,sys; open(sys.argv[1],'w').write(json.dumps({'pid':99999,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}))" "$T/marker.json"; touch "$T/up"; exit 0 ;;
  s2) exit 0 ;;
  s3) python3 -c "import json,datetime,sys; open(sys.argv[1],'w').write(json.dumps({'pid':99999,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}))" "$T/marker.json"; touch "$T/up"; ( sleep 1; rm -f "$T/up" ) & exit 0 ;;
  s4) python3 -c "import json,sys; open(sys.argv[1],'w').write(json.dumps({'pid':99999,'startedAt':'2020-01-01T00:00:00Z'}))" "$T/marker.json"; touch "$T/up"; exit 0 ;;
  *) exit 0 ;;
esac
EOF
  chmod +x "$CLD_OPEN_BIN" "$CLD_PS_BIN"

  run_case() { # name scenario expect_rc expect_open_calls expect_log_grep
    local name="$1" sc="$2" erc="$3" eoc="$4" egrep="$5"
    rm -f "$T/up" "$T/open_calls" "$T/log.txt" "$T/marker.json" "$T/support"/*
    echo "$sc" >"$T/scenario"
    [ "$sc" = "s5" ] && { touch "$T/up"; python3 -c "import json,datetime,sys; open(sys.argv[1],'w').write(json.dumps({'pid':99999,'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')}))" "$T/marker.json"; }
    [ "$sc" = "s2" ] || [ "$sc" = "s4" ] && ln -sf "$(hostname)-12345" "$T/support/SingletonLock"
    CLD_APP="$T/Fake.app" CLD_PATTERN="$T/Fake.app/Contents/MacOS/Fake" \
      bash "$0" --wait 2 --attempts 3 --verify 6 >/dev/null 2>&1
    rc=$?
    local oc; oc="$([ -f "$T/open_calls" ] && wc -l <"$T/open_calls" | tr -d ' ' || echo 0)"
    local ok=1
    [ "$rc" = "$erc" ] || { echo "  ❌ $name: 退出码 $rc ≠ 期望 $erc"; ok=0; }
    [ "$oc" = "$eoc" ] || { echo "  ❌ $name: open 调用 $oc ≠ 期望 $eoc"; ok=0; }
    if [ -n "$egrep" ] && ! grep -q "$egrep" "$T/log.txt" 2>/dev/null; then
      echo "  ❌ $name: 日志缺少 /$egrep/"; ok=0
    fi
    if [ "$ok" = "1" ]; then echo "  ✅ $name"; pass=$((pass+1)); else echo "     └ 日志尾部：$(tail -3 "$T/log.txt" 2>/dev/null | tr '\n' '|')"; fail=$((fail+1)); fi
  }

  echo "══ relaunch-cld.sh --selftest（mock open/pgrep，无副作用）══"
  run_case "S1 open成功+新启动标记 ⇒ 报成功且只 open 一次"      s1 0 1 "✅ 已拉起"
  run_case "S2 永远起不来 ⇒ 重试 3 次、清陈旧锁、退出 1"          s2 1 3 "清理陈旧单实例锁"
  run_case "S3 起来了又倒（存活验证）⇒ 不算成功、重试、退出 1"   s3 1 3 "未通过验证"
  run_case "S4 进程在但启动标记陈旧 ⇒ 不算成功、退出 1（负控）"   s4 1 3 "启动标记未更新"
  run_case "S5 已被他人拉起 ⇒ 不 open、直接成功（负控）"          s5 0 0 "已有新实例"
  run_case "S6 仅命令行提及路径、非 argv0 ⇒ 不算在跑（负控）"      s6 1 3 "未检测到 CLD 进程"
  echo "  ── 结果：$pass 通过 / $fail 失败 ──"
  rm -rf "$T"
  [ "$fail" = "0" ] || return 3
  return 0
}

# ---------------------------------------------------------------- args
while [ $# -gt 0 ]; do
  case "$1" in
    --wait) WAIT_SEC="$2"; shift 2 ;;
    --attempts) ATTEMPTS="$2"; shift 2 ;;
    --verify) VERIFY_SEC="$2"; shift 2 ;;
    --since) SINCE="$2"; shift 2 ;;
    --selftest) SELFTEST=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$1" >&2; usage; exit $EXIT_USAGE ;;
  esac
done
[ -n "$SINCE" ] || SINCE="$(now)"

if [ "$SELFTEST" = "1" ]; then selftest; exit $?; fi

# ---------------------------------------------------------------- main
log "─── relaunch-cld.sh 启动（app=$APP since=$SINCE wait=${WAIT_SEC}s attempts=$ATTEMPTS verify=${VERIFY_SEC}s）───"

# 阶段 1：等旧实例退出；若已有"本次新实例"在跑则直接成功
waited=0
while [ "$waited" -lt $((WAIT_SEC * 2)) ]; do
  if ! is_up; then log "旧实例已退出（等待 ${waited} 次轮询后检测到无 CLD 进程）"; break; fi
  if fresh_boot; then
    log "✅ 已有新实例在跑（pid $(up_pids)），无需拉起 ⇒ 退出 0"
    exit 0
  fi
  sleep 0.5; waited=$((waited + 1))
done
if is_up && ! fresh_boot; then
  log "⚠️ 等待 ${WAIT_SEC}s 后旧实例仍在运行且启动标记未更新 —— 继续尝试拉起（可能被单实例锁吞掉）"
fi

# 阶段 2：open → 读回验证 → 重试
attempt=1
while [ "$attempt" -le "$ATTEMPTS" ]; do
  log "第 ${attempt}/${ATTEMPTS} 次尝试：$OPEN_BIN -a $APP"
  if [ "$DRY" = "1" ]; then say "  [dry-run] $OPEN_BIN -a $APP"; else
    "$OPEN_BIN" -a "$APP" >>"$LOG" 2>&1
    rc=$?
    [ "$rc" = "0" ] || log "  open 返回非零 rc=$rc"
  fi

  deadline=$(( $(now) + VERIFY_SEC )); reason="未检测到 CLD 进程"
  while [ "$(now)" -lt "$deadline" ]; do
    if is_up; then
      sleep "$SETTLE_SEC"
      if ! is_up; then
        reason="进程起来了但在 ${SETTLE_SEC}s 内又退出（疑似被单实例锁杀掉）"
      elif ! fresh_boot; then
        reason="进程在跑但 exit-marker.json 启动标记未更新（startedAt=$(marker_epoch) < since=$SINCE）"
      else
        log "✅ 已拉起：pid $(up_pids)| boot startedAt=$(marker_epoch) | dsh web $(last_dsh_url)"
        peer_guard_tail
        exit 0
      fi
      log "  第 ${attempt} 次：${reason}"
      break
    fi
    sleep 0.5
  done
  [ "$reason" = "未检测到 CLD 进程" ] && log "  第 ${attempt} 次：${reason}（验证 ${VERIFY_SEC}s 超时）"

  if is_up; then
    : # 有进程在跑但不满足判据：绝不动锁文件
  else
    clean_stale_locks
  fi
  attempt=$((attempt + 1))
  [ "$attempt" -le "$ATTEMPTS" ] && sleep "$RETRY_GAP"
done

log "❌ ${ATTEMPTS} 次尝试均未通过验证 —— 需要人工重开 CLD（单实例锁/上下文异常）"
peer_guard_tail
exit 1
