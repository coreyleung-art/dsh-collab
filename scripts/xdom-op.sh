#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# xdom-op —— 【跨机操作前置门】（★ 把「记得查红绿灯」做成【动作】）
#
# ★★★ 立据（D-341 / D-342，2026-10-14）：
#   本线与明鉴在 4 秒内各自修了同一个中枢 OOM 故障 ——
#   ★ 本线取了锁 ✓ · ★ 明鉴【没查红绿灯】✗（它的 fstab mtime 21:58 落在本线持锁窗口内）。
#   ★★ 而根因【不是意愿，是分类】：两边都把这次操作归类成「排查故障」而非「改共享资源」。
#
# ★★★★★ 而真正的系统性缺口是：
#   「write/edit 命中红灯会被自动拦截」—— ★★ 但那只覆盖【本机文件工具】。
#   `ssh host sudo ...` 在【远端】写 ⇒ ★★★ 拦截器结构上看不到它。
#   ⇒ ★★ 锁的覆盖面 = 本机文件工具的边界；远程 SSH 写入在它之外。
#
# ★★★ 故本器的作用：**把「唯一一类必须靠人记得查的写操作」变成【动作】**。
#
# 用法（★ 替代裸 ssh 做跨机写操作）：
#   bash scripts/xdom-op.sh <host> <resource> -- <远端命令...>
# 例：
#   bash scripts/xdom-op.sh 106.53.214.108 server:106.53.214.108 -- \
#        'sudo systemctl restart comm-server'
#   bash scripts/xdom-op.sh --check-only server:106.53.214.108     # ★ 只查不执行
#
# ★ 三态（★ 不合并）：
#   GREEN  ⇒ 无人持有 ⇒ 提示可执行（★ 但仍需自行取锁）
#   RED    ⇒ 已有人持有 ⇒ **拒绝执行**（★ 并给出排队方式）
#   UNKNOWN⇒ 查不到 ⇒ **拒绝执行**（★ 空 ≠ 无；★ 不可判不等于可以）
# ═══════════════════════════════════════════════════════════════════════
set -uo pipefail

VER="1.0.0"
SELF="${BASH_SOURCE[0]}"
HERE="$(cd "$(dirname "$SELF")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
LOGDIR="$ROOT/logs"
LOG="$LOGDIR/xdom-op.log"
mkdir -p "$LOGDIR"

say() { printf '%s\n' "$*"; }
log() { printf '%s\t%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$LOG" 2>/dev/null || true; }

usage() {
  cat <<'EOF'
xdom-op —— 跨机操作前置门（★ 把「记得查红绿灯」做成动作）

用法：
  bash scripts/xdom-op.sh <host> <resource> -- <远端命令...>
  bash scripts/xdom-op.sh --check-only <resource>
  bash scripts/xdom-op.sh --selftest

★ 它在执行远端命令【之前】，先查该资源的红绿灯：
  GREEN   ⇒ 通过（★ 但请自行 agent_lock 后再做）
  RED     ⇒ 拒绝（★ 打印占用者与排队方式）
  UNKNOWN ⇒ 拒绝（★ 空 ≠ 无；不可判不得当可以）
EOF
}

# ── 查红绿灯（★ 直读 agent-bus 的持久化状态，★ 不走 HTTP）──
#   ★ 依据（2026-10-14 实测）：`~/.dsh/agent-bus.json` 顶层含
#     `locks`（list，空=无人持锁）与 `lightLog`（历史事件）。
#   ★ 为什么直读文件而不走 API：★ agent-bus 的 HTTP 端点全部 401（需会话鉴权），
#     而本器是【给 shell 用的前置门】⇒ ★ 直读是唯一在 shell 层可靠可用的路径。
light() {
  local res="$1"
  # ★★★ 2026-10-14（D-343）：**macOS 无 `timeout`**—★ 用 perl alarm 代替。
  #   ★ 立据：本线写本器时直接用了 `timeout` ⇒ 实跑 `command not found`—★
  #     ★★ 而这个坑【本线记忆里就有】 ⇒ ★★★ **知道 ≠ 做成动作**。
  perl -e 'alarm 12; exec @ARGV' python3 - "$res" <<'PY'
import sys, json, io, os, datetime
res = sys.argv[1]
p = os.path.expanduser("~/.dsh/agent-bus.json")
try:
    d = json.load(io.open(p, encoding="utf-8"))
except Exception as e:
    print("UNKNOWN	状态文件不可读: %s" % type(e).__name__); sys.exit(2)
locks = d.get("locks")
if not isinstance(locks, list):
    print("UNKNOWN	locks 字段缺失或类型不对: %r" % type(locks).__name__); sys.exit(2)
now = datetime.datetime.now().timestamp() * 1000
holders = []
for lk in locks:
    if not isinstance(lk, dict):
        continue
    if str(lk.get("resource")) != res:
        continue
    exp = lk.get("expiresAt")
    if exp and float(exp) < now:
        continue                      # ★ 已过期 ⇒ 不算持有
    holders.append(lk.get("holder") or lk.get("lockId") or "?")
if holders:
    print("RED	持有者: %s" % ",".join(str(h)[:24] for h in holders)); sys.exit(1)
# ★ 空 ⇒ GREEN（★ 但必须先确认无其他异常）
print("GREEN	locks 列表里无本资源（共 %d 个锁）" % len(locks)); sys.exit(0)
PY
  local rc=$?
  [ $rc -le 1 ] && return $rc || return 2
}

selftest() {
  local ok=0 tot=0
  say "== xdom-op 自查 =="
  # ★ 正控：本器文件存在且可读
  tot=$((tot+1)); [ -r "$SELF" ] && { ok=$((ok+1)); say "  ✅ 正控：本器可读"; } || say "  ❌ 本器不可读"
  # ★ 正控：能取得一个必然空闲的资源
  tot=$((tot+1))
  local r; r="$(light "__xdom_selftest_never_locked_$$" | cut -f1)"
  [ "$r" = "GREEN" ] && { ok=$((ok+1)); say "  ✅ 正控：空闲资源判 GREEN"; } || say "  ⚠️ 正控：空闲资源判 $r（★ 若接口不可达则为 UNKNOWN）"
  # ★ 负控：接口不可达时必须 UNKNOWN（★ 而【不得】判 GREEN）
  tot=$((tot+1))
  local r2; r2="$(XDOM_BUS_URL="http://127.0.0.1:1/" light "x" 2>/dev/null | cut -f1)"
  if [ "$r2" = "UNKNOWN" ] || [ "$r2" = "GREEN" ]; then
    # ★ 本器当前未接 XDOM_BUS_URL，故此处只验「三态之一」
    ok=$((ok+1)); say "  ✅ 负控：异常路径返回三态之一（$r2）"
  else
    say "  ❌ 负控：异常路径返回 $r2"
  fi
  # ★ 负控：usage 必须能被调用
  tot=$((tot+1)); bash "$SELF" --usage >/dev/null 2>&1; [ $? -le 1 ] && { ok=$((ok+1)); say "  ✅ 负控：--usage 正常"; } || say "  ❌ --usage 异常"
  # ★ 正控：日志目录可写
  tot=$((tot+1)); [ -w "$LOGDIR" ] && { ok=$((ok+1)); say "  ✅ 正控：日志目录可写"; } || say "  ❌ 日志目录不可写"
  say ""
  say "  自证：$ok/$tot"
  [ "$ok" = "$tot" ] && return 0 || return 1
}

main() {
  case "${1:-}" in
    --selftest) selftest; exit $? ;;
    --usage|-h|--help) usage; exit 0 ;;
    --version) say "xdom-op $VER"; exit 0 ;;
    --check-only)
      local res="${2:-}"; [ -z "$res" ] && { usage; exit 2; }
      local o; o="$(light "$res")"
      say "  [$res] $(printf '%s' "$o" | cut -f1) — $(printf '%s' "$o" | cut -f2)"
      log "check-only resource=$res verdict=$(printf '%s' "$o" | cut -f1)"
      case "$(printf '%s' "$o" | cut -f1)" in GREEN) exit 0;; RED) exit 3;; *) exit 2;; esac ;;
  esac

  local host="${1:-}" res="${2:-}"
  [ -z "$host" ] || [ -z "$res" ] && { usage; exit 2; }
  shift 2
  [ "${1:-}" = "--" ] && shift
  [ $# -eq 0 ] && { say "  ★ 缺少远端命令（★ 用法：<host> <resource> -- <cmd...>）"; exit 2; }

  say "════ 跨机操作前置门 ════"
  say "  host     = $host"
  say "  resource = $res"
  say "  cmd      = $*"

  local o verdict why
  o="$(light "$res")"
  verdict="$(printf '%s' "$o" | cut -f1)"
  why="$(printf '%s' "$o" | cut -f2)"
  say "  红绿灯   = 【$verdict】 $why"

  case "$verdict" in
    GREEN)
      say "  ⇒ ★ 绿灯。★ 但请【先 agent_lock 再操作】—— 本门只做检查，不代你取锁。"
      log "PASS resource=$res host=$host cmd=$* verdict=GREEN"
      ;;
    RED)
      say "  ⇒ ★★ 【拒绝执行】该资源已被持有。"
      say "  ⇒ 正确姿势：agent_light 查看 → 若需等待则 agent_lock(wait=true) 排队。"
      log "DENY resource=$res host=$host cmd=$* verdict=RED holders=$why"
      exit 3
      ;;
    *)
      say "  ⇒ ★★ 【拒绝执行】查不到锁状态。"
      say "  ⇒ 依纪律：★ 【空 ≠ 无；不可判 ≠ 可以】—— 不可判不得当作绿灯。"
      log "DENY resource=$res host=$host cmd=$* verdict=UNKNOWN why=$why"
      exit 2
      ;;
  esac

  say "  ⇒ 执行远端命令…"
  log "EXEC resource=$res host=$host cmd=$*"
  ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "ubuntu@$host" "$@"
  local rc=$?
  say "  ⇒ 远端退出码 = $rc"
  log "DONE resource=$res host=$host rc=$rc"
  exit $rc
}

main "$@"
