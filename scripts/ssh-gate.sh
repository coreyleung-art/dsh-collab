#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# ssh-gate —— 【ssh 写操作前置门】（★ shell wrapper，覆盖裸 ssh）
#
# ★★★ 立据（D-341 / D-342 / D-343，2026-10-14）：
#   「write/edit 命中红灯会被自动拦截」—— ★★ 但那只看【本机文件工具】。
#   `ssh host sudo …` 在【远端】写 ⇒ ★★★ 拦截器结构上看不到它。
#   ⇒ ★★ 锁的覆盖面 = 本机文件工具的边界；远程 SSH 写入在它之外。
#   ⇒ 明鉴：「这是唯一一类【必须靠人记得查】的写操作 ⇒ 应**做成动作而非靠记得**」。
#
# ★★ 三条设计原则：
#   ① **只读不拦** —— ★ 否则天天误拦，★ 门就会被绕过（★ 门的价值在于不被绕过）
#   ② **写操作必过门** —— sudo/systemctl/rm/cp/mv/tee/dd/> 等落在远端改名/改状态
#   ③ **必须留逃生门** —— ★ `\ssh` 或 `command ssh` 直达；★ 否则门坏了就救不回来
#
# 用法（★ 在 ~/.zshrc 里 source 本文件即可）：
#   source ~/dsh-collab/scripts/ssh-gate.sh
#   ssh ubuntu@106.53.214.108 'cat /etc/hostname'          # ★ 只读 ⇒ 直通
#   ssh ubuntu@106.53.214.108 'sudo systemctl restart x'   # ★ 写 ⇒ 过门
#   \ssh ubuntu@106.53.214.108 'sudo rm -rf /x'            # ★ 逃生门（★ 不推荐）
#   ssh-gate-status                                        # ★ 查看本门状态
# ═══════════════════════════════════════════════════════════════════════

SSH_GATE_VER="1.0.0"
SSH_GATE_ROOT="${DSH_COLLAB_ROOT:-$HOME/dsh-collab}"
SSH_GATE_LOG="$SSH_GATE_ROOT/logs/ssh-gate.log"
SSH_GATE_BUS="${DSH_AGENT_BUS_JSON:-$HOME/.dsh/agent-bus.json}"

# ── 判据：这条远端命令是【写】还是【读】──
#   ★ 保守方向：★ **拿不准就算写**（★ 宁可多拦一次，★ 不可漏一次）
_ssh_gate_is_write() {
  local cmd="$1"
  [ -z "$cmd" ] && return 0                      # ★ 交互式 ssh ⇒ 算写（★ 你可能会在里面写给命令）
  # ★ 写动词（★ 会改远端状态）
  printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])(sudo|doas|systemctl|service|launchctl|rm|rmdir|mv|cp|install|chmod|chown|chattr|dd|mkfs|mount|umount|tee|truncate|ln|touch|mkdir|sed[[:space:]]+-i|apt|apt-get|yum|dnf|brew|pip|pip3|npm|yarn|pnpm|docker|kubectl|git[[:space:]]+(push|reset|checkout|clean)|crontab|useradd|usermod|passwd|reboot|shutdown|kill|pkill|killall)([[:space:]]|$)' && return 0
  # ★ 重定向写（★ > 与 >>，★ 排除 2>&1 之类的 fd 复制）
  printf '%s' "$cmd" | grep -qE '(^|[^0-9&])>{1,2}[^&]' && return 0
  return 1
}

# ── 查红绿灯（★ 直读 agent-bus.json，★ 与 xdom-op.sh 同源）──
_ssh_gate_light() {
  local res="$1"
  perl -e 'alarm 12; exec @ARGV' python3 - "$res" "$SSH_GATE_BUS" <<'PY'
import sys, json, io, os, datetime
res = sys.argv[1]; p = os.path.expanduser(sys.argv[2])
try:
    d = json.load(io.open(p, encoding="utf-8"))
except Exception as e:
    print("UNKNOWN\t\u72b6\u6001\u6587\u4ef6\u4e0d\u53ef\u8bfb: %s" % type(e).__name__); sys.exit(2)
locks = d.get("locks")
if not isinstance(locks, list):
    print("UNKNOWN\tlocks \u5b57\u6bb5\u7f3a\u5931"); sys.exit(2)
now = datetime.datetime.now().timestamp() * 1000
hs = []
for lk in locks:
    if not isinstance(lk, dict) or str(lk.get("resource")) != res:
        continue
    exp = lk.get("expiresAt")
    if exp and float(exp) < now:
        continue
    hs.append(lk.get("holder") or lk.get("lockId") or "?")
if hs:
    print("RED\t\u6301\u6709\u8005: %s" % ",".join(str(h)[:24] for h in hs)); sys.exit(1)
print("GREEN\tlocks \u5217\u8868\u91cc\u65e0\u672c\u8d44\u6e90\uff08\u5171 %d \u4e2a\u9501\uff09" % len(locks)); sys.exit(0)
PY
}

# ── 从 ssh 参数里抽出目标主机 ──
_ssh_gate_host() {
  local a skip=0
  for a in "$@"; do
    if [ "$skip" = "1" ]; then skip=0; continue; fi
    case "$a" in
      -i|-o|-p|-l|-F|-E|-b|-c|-D|-e|-I|-J|-L|-m|-O|-Q|-R|-S|-W|-w) skip=1; continue ;;
      -*) continue ;;
      *@*) printf '%s' "${a##*@}"; return 0 ;;
      *) printf '%s' "$a"; return 0 ;;
    esac
  done
  return 1
}

# ── 从 ssh 参数里抽出远端命令（★ 第一个非选项且非 host 的参数起）──
_ssh_gate_remote_cmd() {
  local out="" seen_host=0 skip=0 a
  for a in "$@"; do
    if [ "$skip" = "1" ]; then skip=0; continue; fi
    case "$a" in
      -i|-o|-p|-l|-F|-E|-b|-c|-D|-e|-I|-J|-L|-m|-O|-Q|-R|-S|-W|-w) skip=1; continue ;;
      -*) continue ;;
    esac
    if [ "$seen_host" = "0" ]; then seen_host=1; continue; fi
    out="$out $a"
  done
  printf '%s' "${out# }"
}

ssh() {
  local host rc verdict why rcmd res
  host="$(_ssh_gate_host "$@")" || { command ssh "$@"; return $?; }
  rcmd="$(_ssh_gate_remote_cmd "$@")"

  # ★ 无远端命令 ⇒ 交互式 ⇒ 算写
  if ! _ssh_gate_is_write "$rcmd"; then
    printf '\033[2m[ssh-gate] 只读命令 ⇒ 直通（%s）\033[0m\n' "$host" >&2
    command ssh "$@"; return $?
  fi

  res="host:$host"
  local o; o="$(_ssh_gate_light "$res")"; rc=$?
  verdict="$(printf '%s' "$o" | cut -f1)"
  why="$(printf '%s' "$o" | cut -f2)"

  case "$verdict" in
    GREEN)
      printf '\033[32m[ssh-gate] %s 绿灯 ⇒ 放行\033[0m · %s\n' "$res" "$why" >&2
      printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "PASS" "res=$res host=$host cmd=$rcmd" >> "$SSH_GATE_LOG" 2>/dev/null || true
      ;;
    RED)
      printf '\033[31m[ssh-gate] ★★ 拒绝执行：%s 已被持有\033[0m\n' "$res" >&2
      printf '  %s\n' "$why" >&2
      printf '  ⇒ 正确姿势：agent_light 查看 → 需要则 agent_lock(wait=true) 排队 → 再重试\n' >&2
      printf '  ⇒ 逃生门（★ 不推荐）：\\ssh … 或 command ssh …\n' >&2
      printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "DENY-RED" "res=$res host=$host cmd=$rcmd" >> "$SSH_GATE_LOG" 2>/dev/null || true
      return 3
      ;;
    *)
      printf '\033[31m[ssh-gate] ★★ 拒绝执行：%s 锁状态【不可判】\033[0m\n' "$res" >&2
      printf '  %s\n' "$why" >&2
      printf '  ⇒ 依纪律：【空 ≠ 无；不可判 ≠ 可以】—— 不可判不得当作绿灯\n' >&2
      printf '  ⇒ 逃生门（★ 不推荐）：\\ssh … 或 command ssh …\n' >&2
      printf '%s\t%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "DENY-UNKNOWN" "res=$res host=$host cmd=$rcmd" >> "$SSH_GATE_LOG" 2>/dev/null || true
      return 2
      ;;
  esac

  command ssh "$@"; return $?
}

ssh-gate-status() {
  printf 'ssh-gate %s\n' "$SSH_GATE_VER"
  printf '  状态文件 = %s（%s）\n' "$SSH_GATE_BUS" "$([ -r "$SSH_GATE_BUS" ] && echo 可读 || echo 不可读)"
  printf '  日志     = %s\n' "$SSH_GATE_LOG"
  printf '  逃生门   = \\ssh … 或 command ssh …\n'
  printf '  覆盖范围 = 本 shell 会话内所有 ssh（★ 含交互式）\n'
  printf '\n  最近 5 条：\n'
  tail -5 "$SSH_GATE_LOG" 2>/dev/null | sed 's/^/    /' || printf '    （无）\n'
}

ssh-gate-selftest() {
  local ok=0 tot=0 dir
  printf '== ssh-gate 自查 ==\n'
  tot=$((tot+1)); [ -r "$SSH_GATE_BUS" ] && { ok=$((ok+1)); printf '  ✅ 正控：状态文件可读\n'; } || printf '  ⚠️ 正控：状态文件不可读（★ 那会让门判 UNKNOWN）\n'
  tot=$((tot+1)); _ssh_gate_is_write "sudo systemctl restart x" && { ok=$((ok+1)); printf '  ✅ 正控：sudo … 判为写\n'; } || printf '  ❌ sudo … 未判为写\n'
  tot=$((tot+1)); _ssh_gate_is_write "cat /etc/hostname" && printf '  ❌ cat … 误判为写\n' || { ok=$((ok+1)); printf '  ✅ 负控：cat … 判为只读\n'; }
  tot=$((tot+1)); _ssh_gate_is_write "echo hi > /tmp/x" && { ok=$((ok+1)); printf '  ✅ 正控：重定向判为写\n'; } || printf '  ❌ 重定向未判为写\n'
  tot=$((tot+1)); _ssh_gate_is_write "" && { ok=$((ok+1)); printf '  ✅ 正控：空命令（交互式）判为写\n'; } || printf '  ❌ 空命令未判为写\n'
  tot=$((tot+1)); [ "$(_ssh_gate_host -i ~/.ssh/k ubuntu@1.2.3.4 'x')" = "1.2.3.4" ] && { ok=$((ok+1)); printf '  ✅ 正控：能抽出 host\n'; } || printf '  ❌ 抽 host 失败\n'
  tot=$((tot+1)); [ "$(_ssh_gate_remote_cmd -i ~/.ssh/k ubuntu@1.2.3.4 'sudo rm -rf /')" = "sudo rm -rf /" ] && { ok=$((ok+1)); printf '  ✅ 正控：能抽出远端命令\n'; } || printf '  ❌ 抽远端命令失败\n'
  printf '\n  自证：%d/%d\n' "$ok" "$tot"
  [ "$ok" = "$tot" ] && return 0 || return 1
}
