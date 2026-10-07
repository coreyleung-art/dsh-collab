#!/bin/sh
# restart-with-guard.sh —— 受控重启 CLD，并把"可靠拉起"交给自带验证的守护（v1.0.0，2026-10-04）
#
# 为什么不用插件自带守护：agent-way 的 quick-restart 守护只做一次
#   `sleep countdown+2; open -a CLD.app`，不验证、不重试。实测（10-04 11:42）它确实拉起了
#   pid 46749，但该实例 1.4s 后被 Chromium 单实例锁静默杀掉（launchd termination (0,0,0)、
#   零痕迹）⇒ 用户看到"关闭了但没自动拉起"。本脚本改用 relaunch-cld.sh：
#   等旧实例真退出 → open → 读回验证（进程 argv0 + exit-marker 启动标记）→ 重试 → 清陈旧锁。
#
# 用法： sh restart-with-guard.sh [countdown=5] [守护等待秒=45]
#   说明：countdown = 停机时长（插件机制里 delayMs=(countdown+2)*1000）
# 结果看： ~/dsh-collab/data/ops/relaunch-cld.log（✅ 已拉起 / ❌ 需人工重开）
#         ~/dsh-collab/data/ops/quick-restart-trigger.log（触发回执）
CD=${1:-5}; WAIT=${2:-60}
TOOLS="$HOME/dsh-collab/tools"
OPS="$HOME/dsh-collab/data/ops"
TL="$OPS/quick-restart-trigger.log"
GL="$OPS/relaunch-cld.log"
mkdir -p "$OPS"

PORT=$(grep -o 'http://127.0.0.1:[0-9]*' "$HOME/.cld/logs/dsh-web.log" 2>/dev/null | tail -1 | grep -o '[0-9]*$')
if [ -z "$PORT" ]; then
  echo "[$(date '+%F %T')] ❌ 找不到 dsh web 端口（读 ~/.cld/logs/dsh-web.log 失败），中止" >> "$TL"
  exit 2
fi
NOW=$(date +%s)

# ① 起自带验证的守护（python3 start_new_session=True = setsid，等价插件的 detached+unref；
#    插件守护已被实测证明能熬过宿主退出。注意：本机 bash 工具环境里 `node` 不在 PATH，
#    故不用 node —— 避免"spawn 失败但静默"这一类风险）
GPID=$(GUARD="$TOOLS/relaunch-cld.sh" GUARD_ARGS="--wait $WAIT --attempts 10 --verify 20 --since $NOW" \
  python3 -c '
import os,shlex,subprocess
args=shlex.split(os.environ.get("GUARD_ARGS",""))
p=subprocess.Popen([os.environ["GUARD"],*args],
                   stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL,start_new_session=True)
print(p.pid)' 2>/dev/null)
echo "[$(date '+%F %T')] 守护已起：relaunch-cld.sh pid=${GPID:-起失败}（wait=${WAIT}s attempts=10 verify=20 since=$NOW）" >> "$TL"
if [ -z "$GPID" ]; then
  echo "[$(date '+%F %T')] ❌ 守护启动失败，取消本次重启（避免无人拉起）" >> "$TL"
  exit 3
fi

# ①b ★读回验证（R043）：守护必须真的跑起来并写出「含本次 since=」的启动行；
#     实测过一次 spawn 后探针未执行且不可复现 ⇒ 不看 pid 回显就触发重启 = 赌博。
#     用 `since=$NOW` 做内容锚点（唯一、不依赖时间解析）。
sleep 2
if tail -20 "$GL" 2>/dev/null | grep -q "since=$NOW"; then
  echo "[$(date '+%F %T')] ✅ 守护读回验证通过（日志含 since=$NOW 启动行）" >> "$TL"
else
  echo "[$(date '+%F %T')] ❌ 守护读回验证失败：$GL 中无 since=$NOW 启动行（spawn 未真正执行）" >> "$TL"
  echo "[$(date '+%F %T')] ⇒ **取消本次重启**（无人拉起风险 > 重启收益）" >> "$TL"
  exit 3
fi

finally_done=1
if [ "${SWG_DRY:-0}" = "1" ]; then
  echo "[$(date '+%F %T')] 🧪 预演模式（SWG_DRY=1）：守护已验证就绪，**不触发重启**；守护 pid=$GPID（收尾请 kill）" >> "$TL"
  echo "$GPID"
  exit 0
fi

# ② 触发 quick-restart
R=$(curl -s -m 10 -X POST -H "Host: 127.0.0.1:$PORT" -H 'Content-Type: application/json' \
     -d "{\"confirm\":true,\"countdown\":$CD}" "http://127.0.0.1:$PORT/agent-bus/api/quick-restart")
echo "[$(date '+%F %T')] 触发回执: $R" >> "$TL"
echo "[$(date '+%F %T')] 停机约 ${CD}s；自带验证守护负责拉起（失败会重试并清陈旧锁）" >> "$TL"
