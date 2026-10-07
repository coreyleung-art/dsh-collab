#!/bin/bash
VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）
# blackboard-deploy-068.sh — 黑板 rust-blackboard v0.6.7 → v0.6.8 受控切换
#
# 修的是什么：PUT body 非 JSON 时静默落 {} 且返回 200（accept-and-discard 丢数据）
#             v0.6.8 改为 fail loud（400）+ X-Body-Text:1 纯文本逃生门
#
# 用法：
#   ./blackboard-deploy-068.sh            # 默认演练（零变更，只打印计划）
#   ./blackboard-deploy-068.sh --go       # 真正切换（换 plist 指向 + bootout/bootstrap 重新加载）
#
# 安全设计：
#   · 默认 dry-run，必须显式 --go 才动（避免误触发共享基础设施重启）
#   · plist 先备份，健康校验失败自动回滚到 v0.6.7 并再次校验
#   · 健康判定 = 进程存活 + :8792 可读 + 已知键回读内容非空 + 启动日志版本号一致
#   · 不回显 plist 内容（内含 BLACKBOARD_TOKEN）
set -uo pipefail

GO=0
[ "${1:-}" = "--go" ] && GO=1

BB_HOME="$HOME/dsh-collab/rust-blackboard"
NEW_BIN="$BB_HOME/dist/rust-blackboard-macos-arm64-v0.6.8"
OLD_BIN="$BB_HOME/dist/rust-blackboard-macos-arm64-v0.6.7"
PLIST="$HOME/Library/LaunchAgents/com.dsh.hr.blackboard-server.plist"
LABEL="com.dsh.hr.blackboard-server"
PORT=8792
LOG="$HOME/dsh-collab/scripts/logs/blackboard-rust.log"
TS=$(date +%s)
PROBE_KEY="health/blackboard-deploy-probe"   # 只读探针，不写入

say() { printf '%s\n' "$*"; }
die() { say "❌ $*"; exit 1; }

say "=== 黑板切换 v0.6.7 → v0.6.8 ($([ $GO = 1 ] && echo '执行' || echo '演练')) ==="
say ""

# ---------- 前置检查 ----------
say "[1/6] 前置检查"
[ -f "$NEW_BIN" ] && [ -x "$NEW_BIN" ] || die "新二进制缺失或不可执行: $NEW_BIN"
[ -f "$PLIST" ] || die "plist 缺失: $PLIST"
CUR_BIN=$(grep -o '/[^<]*rust-blackboard-macos-arm64-v[0-9.]*' "$PLIST" | head -1)
[ -n "$CUR_BIN" ] || die "无法从 plist 解析当前二进制路径"
say "  新二进制   : $NEW_BIN"
say "  新 sha256  : $(shasum -a 256 "$NEW_BIN" | cut -c1-16)"
say "  当前指向   : $CUR_BIN"
say "  当前 sha256: $(shasum -a 256 "$CUR_BIN" 2>/dev/null | cut -c1-16)"
[ "$CUR_BIN" = "$OLD_BIN" ] || say "  ⚠️ plist 当前指向不是 v0.6.7，请人工确认"
plutil -lint "$PLIST" >/dev/null || die "plist 语法非法"

# ---------- 切换前快照（用于回滚后比对）----------
say ""
say "[2/6] 切换前快照"
PID_BEFORE=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | head -1)
SEQ_BEFORE=$(curl -s -m 5 "http://127.0.0.1:$PORT/clock" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("seq"))' 2>/dev/null)
KEYS_BEFORE=$(curl -s -m 5 "http://127.0.0.1:$PORT/data/" 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get("total"))' 2>/dev/null)
say "  运行 pid=$PID_BEFORE  seq=$SEQ_BEFORE  data 键数=$KEYS_BEFORE"
[ -n "$PID_BEFORE" ] || die "当前 :$PORT 无监听进程，状态异常，请先排查"
[ -n "$SEQ_BEFORE" ] || die ":8792 /clock 不可读，状态异常"

# SSE 订阅端盘点：重启会断开全部连接，必须能确认它们重新连上
# （历史教训 v0.6.1：订阅端静默失联 = 跨设备注入全断，且无人察觉）
SUBS_BEFORE=$(lsof -nP -iTCP:8803 2>/dev/null | grep -c ESTABLISHED)
say "  SSE :8803 活连接=$SUBS_BEFORE（重启将全部断开，需确认重连）"
lsof -nP -iTCP:8803 2>/dev/null | grep ESTABLISHED | awk '{print $1}' | sort | uniq -c | sed 's/^/     /'
if [ "$SUBS_BEFORE" -gt 0 ]; then
  say "     ⚠️ 有 $SUBS_BEFORE 个订阅端在线：请确认它们均有自动重连"
  say "        （bb-sub-daemon.py 有 backoff 重连；自研脚本若无重连逻辑，"
  say "         重启后会静默变聋 —— 这是本类故障里最贵的一种）"
fi

# ---------- 计划 ----------
say ""
say "[3/6] 将执行的动作"
say "  a. 备份 plist → ${PLIST}.bak-v067-$TS"
say "  b. plist 中 $CUR_BIN → $NEW_BIN"
say "  c. launchctl bootout + bootstrap（**必须重新加载**：kickstart -k 不重读 plist，改动不生效）"
say "  d. 健康校验（最多 10 次重试）：/clock + /data/ + 键回读 + 日志版本号"
say "  e. 任一校验失败 → 恢复 plist 备份 + bootout/bootstrap + 复验（自动回滚）"
say ""
say "  ⚠️ 影响面：黑板 :8792 约 1-3s 不可用；SSE 订阅端（:8803）需重连；"
say "     此刻正在写的智能体会收到连接失败（失败即失败，不会静默丢——v0.6.8 起更明确）"

if [ $GO = 0 ]; then
  say ""
  say "== 演练结束（零变更）=="
  say "确认窗口后执行：$0 --go"
  exit 0
fi

# ---------- 执行 ----------
say ""
say "[4/6] 执行切换"
cp "$PLIST" "${PLIST}.bak-v067-$TS" || die "plist 备份失败"
say "  ✅ plist 已备份"
sed -i '' "s|$CUR_BIN|$NEW_BIN|" "$PLIST" || die "plist 修改失败"
plutil -lint "$PLIST" >/dev/null || { cp "${PLIST}.bak-v067-$TS" "$PLIST"; die "plist 语法非法，已还原"; }
say "  ✅ plist 已指向 v0.6.8"
# ★ 2026-09-13 修复：kickstart -k 只重启"已加载的 job"，**不会重读磁盘上的 plist**
#   → 实测后果：plist 已指向 v0.6.8，但重启后仍跑 v0.6.7，且旧脚本打印了"✅ 切换成功"（假成功）。
#   正确做法 = bootout（卸载旧 job）+ bootstrap（按新 plist 重新加载）。
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null; sleep 1
launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null || say "  ⚠️ bootstrap 返回非零，请检查 plist"
say "  ⏳ 等待服务就绪…"

# ---------- 健康校验 ----------
say ""
say "[5/6] 健康校验"
ok=0
for i in $(seq 1 10); do
  sleep 0.7
  pid=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | head -1)
  code=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/clock" 2>/dev/null)
  if [ -n "$pid" ] && [ "$code" = "200" ]; then ok=1; break; fi
done

health_fail() {
  say "  ❌ $1"
  say ""
  say "[6/6] 自动回滚"
  cp "${PLIST}.bak-v067-$TS" "$PLIST" && say "  ✅ plist 已还原为 v0.6.7"
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null; sleep 1
  launchctl bootstrap "gui/$UID" "$PLIST" 2>/dev/null
  sleep 2
  rcode=$(curl -s -m 3 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/clock" 2>/dev/null)
  say "  回滚后 /clock = $rcode（期望 200）"
  say "  回滚备份保留: ${PLIST}.bak-v067-$TS"
  exit 1
}

[ $ok = 1 ] || health_fail "服务未在 7s 内就绪（pid=$pid /clock=$code）"
say "  ✅ 进程存活 pid=$pid，/clock=200"

TOTAL=$(curl -s -m 5 "http://127.0.0.1:$PORT/data/" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("total"))' 2>/dev/null)
[ "$TOTAL" = "$KEYS_BEFORE" ] || health_fail "data 键数变化 $KEYS_BEFORE → $TOTAL（数据丢失）"
say "  ✅ data 键数一致：$TOTAL（切换前 $KEYS_BEFORE）"

SEQ_AFTER=$(curl -s -m 5 "http://127.0.0.1:$PORT/clock" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("seq"))' 2>/dev/null)
[ -n "$SEQ_AFTER" ] && [ "$SEQ_AFTER" -ge "$SEQ_BEFORE" ] 2>/dev/null || health_fail "seq 回退 $SEQ_BEFORE → $SEQ_AFTER"
say "  ✅ seq 未回退：$SEQ_BEFORE → $SEQ_AFTER"

# 读真实键回读（挑一个已知存在的注册卡）
SAMPLE=$(curl -s -m 5 "http://127.0.0.1:$PORT/data/" | python3 -c 'import json,sys;l=json.load(sys.stdin).get("list") or [];print(l[0] if l else "")' 2>/dev/null)
if [ -n "$SAMPLE" ]; then
  LEN=$(curl -s -m 5 "http://127.0.0.1:$PORT/$SAMPLE" | python3 -c 'import json,sys;v=json.load(sys.stdin).get("value") or {};print(len(json.dumps(v,ensure_ascii=False)))' 2>/dev/null)
  say "  ✅ 抽样回读 $SAMPLE → value 长度 $LEN"
else
  say "  （无样本键）"
fi

SUBS_AFTER=$(lsof -nP -iTCP:8803 2>/dev/null | grep -c ESTABLISHED)
if [ "$SUBS_BEFORE" -gt 0 ] && [ "$SUBS_AFTER" -eq 0 ]; then
  say "  ⚠️ 订阅端尚未重连（$SUBS_BEFORE → 0）：等待 10s 再数一次（多数订阅端有 backoff）"
  sleep 10
  SUBS_AFTER=$(lsof -nP -iTCP:8803 2>/dev/null | grep -c ESTABLISHED)
fi
say "  SSE 订阅端：重启前 $SUBS_BEFORE → 重启后 $SUBS_AFTER"
if [ "$SUBS_AFTER" -lt "$SUBS_BEFORE" ]; then
  say "  ⚠️ 少于重启前：请逐个确认谁没回来（聋掉的订阅端 = 静默丢失，不可放过）"
  lsof -nP -iTCP:8803 2>/dev/null | grep ESTABLISHED | awk '{print $1}' | sort | uniq -c | sed 's/^/     /'
else
  say "  ✅ 订阅端已恢复（≥ 重启前）"
fi

# ★ 2026-09-13 加固：版本校验从"看一眼日志（软警告）"改为**硬门**——
#   判据用"运行中进程的二进制路径 sha256 == 新二进制 sha256"，比日志更硬（日志可能仍是上一轮的）。
RUN_BIN=$(ps -o command= -p "$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null | head -1)" 2>/dev/null | awk '{print $1}')
RUN_SHA=$(shasum -a 256 "$RUN_BIN" 2>/dev/null | cut -c1-16)
WANT_SHA=$(shasum -a 256 "$NEW_BIN" | cut -c1-16)
say "  运行中二进制: $RUN_BIN"
say "  其 sha256[:16]: $RUN_SHA | 期望: $WANT_SHA"
if [ "$RUN_SHA" != "$WANT_SHA" ]; then
  health_fail "运行中的二进制与目标不一致（旧 job 未重载？）—— 判为切换失败"
fi
say "  ✅ 运行版本确认：sha256 与目标逐位一致"
VER=$(tail -50 "$LOG" 2>/dev/null | grep -o 'rust-blackboard v[0-9.]*' | tail -1)
say "  启动日志版本：${VER:-未捕获}"

say ""
say "[6/6] 完成"
say "  ✅ 切换成功。回滚方式：cp ${PLIST}.bak-v067-$TS $PLIST && launchctl bootout gui/$UID/$LABEL; launchctl bootstrap gui/$UID $PLIST"
say "  验证缺陷已修复：curl -X PUT --data-binary 'raw' http://127.0.0.1:$PORT/data/ops/probe  → 期望 400"
