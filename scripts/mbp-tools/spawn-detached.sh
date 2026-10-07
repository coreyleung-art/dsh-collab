#!/usr/bin/env bash
# spawn-detached.sh —— 可靠地起一个「独立会话」后台进程（v1.0.0，2026-10-04）
#
# 为什么需要（Φ8 两次法则：同一操作出现两次就工具化）：
#   本项目**两次**实测 `nohup ... &` 起的子进程**静默没执行**（无输出、无日志、无痕迹）：
#     ① 11:59 的 detached 探针：pid 已回显，但 4 秒后日志仍为空（不可复现）；
#     ② 12:09 的热重载验收脚本：写下 1 行就消失，25 秒后该发的 POST 从未发出
#        （主进程/dsh/端口全未变 ⇒ 确证"没执行"，不是"执行失败"）。
#   而用 `python3 start_new_session=True`（等价 setsid）起的子进程**两次都稳定执行**
#   （12:00:35 的守护跑了 4 次 open；12:02:17 的守护正常收尾）。
#   ⇒ 根因：`nohup` 只挡 SIGHUP；工具调用结束时若发生**进程组级清理**，同组子进程会被连带杀死。
#      setsid 让子进程进入新会话/新进程组 ⇒ 不受调用方进程组清理影响。
#
# 用法：
#   spawn-detached.sh <脚本路径> [参数...]
#   输出：子进程 pid（stdout 一行）；失败时输出 "ERR: ..." 并 exit 3
#   环境变量：
#     SPAWN_LOG=<path>   子进程 stdout/stderr 落盘（默认 /dev/null）
#     SPAWN_VERIFY=<秒>  起后等待 N 秒，回读「子进程是否仍存活」并打印 VERIFY 行
#                        （★ 判据在调用方：R043 要求"发起动作后读回验证目标自身状态"，
#                          本工具只能证明"起来了"，证明"做成了"要靠被调脚本自己的日志/产物）
#
# 例：
#   PID=$(spawn-detached.sh ~/dsh-collab/tools/test-hot-reload.sh 40)
#   SPAWN_VERIFY=3 spawn-detached.sh ~/dsh-collab/tools/relaunch-cld.sh --wait 60
set -u
[ $# -ge 1 ] || { echo "用法: spawn-detached.sh <脚本路径> [参数...]" >&2; exit 2; }
SCRIPT="$1"; shift
[ -f "$SCRIPT" ] || { echo "ERR: 脚本不存在 $SCRIPT" >&2; exit 2; }
[ -x "$SCRIPT" ] || chmod +x "$SCRIPT" 2>/dev/null

SPAWN_LOG="${SPAWN_LOG:-/dev/null}"
PID=$(SCRIPT="$SCRIPT" ARGS_JSON="$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1:]))' "$@")" \
      SPAWN_LOG="$SPAWN_LOG" python3 - <<'PY' 2>/dev/null
import json, os, subprocess, sys
script = os.environ["SCRIPT"]
args = json.loads(os.environ["ARGS_JSON"])
log = os.environ.get("SPAWN_LOG") or "/dev/null"
out = open(log, "ab") if log != "/dev/null" else subprocess.DEVNULL
try:
    p = subprocess.Popen([script, *args], stdin=subprocess.DEVNULL, stdout=out,
                         stderr=subprocess.STDOUT, start_new_session=True)
except Exception as e:
    print("ERR: %s" % e); sys.exit(1)
print(p.pid)
PY
)
case "$PID" in
  ERR:*|"") echo "${PID:-ERR: spawn 未返回 pid}" >&2; exit 3 ;;
esac
echo "$PID"

if [ "${SPAWN_VERIFY:-0}" != "0" ]; then
  sleep "$SPAWN_VERIFY"
  if ps -p "$PID" -o pid= >/dev/null 2>&1; then
    echo "VERIFY ok: pid $PID 存活（${SPAWN_VERIFY}s 后）"
  else
    echo "VERIFY gone: pid $PID 已不存在（可能已正常结束，或未真正启动 —— 请用被调脚本自身的日志判定）"
  fi
fi
