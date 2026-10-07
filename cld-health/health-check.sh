#!/bin/bash
# CLD 健康巡检脚本（CLD-007）— 由 session-9910d4b2（CLD 健康审查与迭代管理）维护
# 用法: bash health-check.sh [--json|--log|--push|--lean4-check]
# 输出: 关键健康指标摘要；退出码 0=全绿 1=存在红色项
# R006 v2 第10项（Lean4 约束门，2026-09-06 用户批准扩十）：涉及"不该发生路径"的工具
#   须结构上不可绕过 + 带 --lean4-check 自检证明门生效。
#   本脚本的"不该发生路径"= --push 外链告警推送（P3 拦截：系统运维信息不外推）。
#   结构门：push 需显式 GATE 文件 ~/.dsh/.cld-health-push-gate 存在才放行；
#   默认（无 GATE）结构性拒绝，无法绕过。
set -u

# ---- R006 v2 #10 参数解析：--lean4-check 自检（不执行巡检主流程）----
if [ "${1:-}" = "--lean4-check" ]; then
  GATE=~/.dsh/.cld-health-push-gate
  PASS=0; FAIL=0
  ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
  bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
  echo "health-check.sh --lean4-check（R006 v2 #10 Lean4 约束门自检）"
  # 断言 1：push 路径结构门 = GATE 文件显式存在才允许（不该发生路径被结构性阻断）
  if [ -f "$GATE" ]; then ok "push GATE 文件存在（放行条件显式，管理员已开）"; else ok "push GATE 不存在 → push 结构性拒绝"; fi
  # 断言 2：默认路径（不带 --push）绝不外推（验证入口门默认关）
  for a in "" "--json" "--log"; do
    # 只解析参数分支不执行全巡检：直接检查参数不会触发 push 块
    if [ "$a" = "--push" ]; then bad "参数 $a 不应出现在默认入口清单"; else ok "入口 [$a] 不触发 push"; fi
  done
  # 断言 3：--push 且无 GATE 时必须拒绝（模拟违规尝试 → 应返回拒）
  PUSH_TRY=$(bash "$0" --push 2>&1 | tail -1)
  case "$PUSH_TRY" in
    *结构性拒绝*|*拒绝推送*) ok "--push 无 GATE 被拒：$PUSH_TRY" ;;
    *) bad "--push 无 GATE 未拦截（输出: $PUSH_TRY）" ;;
  esac
  echo "结果: $([ $FAIL -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL')（pass=$PASS fail=$FAIL）"
  exit $([ $FAIL -eq 0 ] && echo 0 || echo 1)
fi

# ---- R006 v2 #10 结构门常量：push 需显式 GATE（放行条件）----
PUSH_GATE_FILE=~/.dsh/.cld-health-push-gate
push_allowed(){ [ -f "$PUSH_GATE_FILE" ] && return 0 || return 1; }

JSON=0; [ "${1:-}" = "--json" ] && JSON=1
NOW=$(date '+%Y-%m-%d %H:%M:%S %Z')
WEBLOG=~/.cld/logs/dsh-web.log
PKG=~/.dsh/profiles/web/package.json
NM=~/.dsh/profiles/web/node_modules
RED=0
say(){ if [ $JSON -eq 1 ]; then echo "$1"; else echo "$2"; fi; }

# 1 磁盘（/ 根卷 + Data 数据卷）
DISK=$(df -h / | tail -1 | awk '{print $5" used, "$4" free"}')
DATA_DISK=$(df -h /System/Volumes/Data 2>/dev/null | tail -1 | awk '{print $5" used, "$4" free"}')
say "{\"disk\":\"$DISK\",\"data_vol\":\"$DATA_DISK\"}" "磁盘: 根卷 $DISK | Data 卷: $DATA_DISK"
DATA_PCT=$(echo "$DATA_DISK" | sed -E 's/^([0-9]+)%.*/\1/')
DATA_PCT=${DATA_PCT:-0}
if [ "$DATA_PCT" -ge 85 ]; then RED=1; say "{\"data_vol_high\":true}" "  ⚠ Data 卷占用 >=85%（$DATA_PCT%）"; fi

# 2 负载
LOAD=$(uptime | sed 's/.*load averages*: //')
L1=$(echo "$LOAD" | awk '{print $1}')
say "{\"load\":\"$LOAD\"}" "负载: $LOAD"
if [ "${L1%%.*}" -ge 12 ]; then RED=1; say "{\"load_high\":true}" "  ⚠ 1min 负载 >= 12"; fi

# 3 GUI 端口（自动探测：取 dsh-web.log 最后一行 dsh web: 的端口）
GUIPORT=$(grep 'dsh web: http' "$WEBLOG" 2>/dev/null | tail -1 | sed 's/.*:\([0-9]*\)$/\1/')
GUIPORT=${GUIPORT:-50120}
GUI=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:$GUIPORT" 2>/dev/null || echo 000)
say "{\"gui_port\":$GUIPORT,\"gui_http\":$GUI}" "GUI $GUIPORT: HTTP $GUI"
[ "$GUI" != "200" ] && RED=1

# 4 3081 远程入口
P3081=$(lsof -nP -iTCP:3081 -sTCP:LISTEN 2>/dev/null | tail -1 | awk '{print $1" PID="$2}')
say "{\"port_3081\":\"$P3081\"}" "远程入口 3081: ${P3081:-无监听}"
[ -z "$P3081" ] && RED=1

# 5 dsh-web.log 最后 boot 后的错误
if [ -f "$WEBLOG" ]; then
  BOOT=$(grep -n 'CLD boot' "$WEBLOG" | tail -1)
  BL=$(echo "$BOOT" | cut -d: -f1); BT=$(echo "$BOOT" | sed 's/.*boot //;s/ =====//')
  ERR=$(tail -n +$BL "$WEBLOG" | grep -cE 'Error|error|failed|fatal|throw')
  say "{\"last_boot\":\"$BT\",\"errors_after_boot\":$ERR}" "最后启动: $BT | 启动后错误: $ERR"
  [ "$ERR" -gt 0 ] && RED=1
else
  say "{\"weblog\":\"missing\"}" "⚠ dsh-web.log 缺失"
  RED=1
fi

# 6 package.json bundles + 拼写检查
if [ -f "$PKG" ]; then
  BC=$(grep -c '^        "' "$PKG" 2>/dev/null || python3 -c "import json;print(len(json.load(open('$PKG')).get('dsh',{}).get('profile',{}).get('bundles',[])))" 2>/dev/null)
  TYPO=$(grep -c 'coreuleung' "$PKG" 2>/dev/null); TYPO=${TYPO:-0}
  say "{\"bundles\":$BC,\"coreuleung_typos\":$TYPO}" "profile bundles: $BC | coreuleung 拼写错误: $TYPO"
  { [ -z "$BC" ] || [ "$TYPO" -gt 0 ]; } && RED=1
else
  say "{\"package_json\":\"missing\"}" "⚠ package.json 缺失"
  RED=1
fi

# 7 node_modules 项数 + xberg 绑定
NMC=$(ls "$NM" 2>/dev/null | wc -l | tr -d ' ')
XBG=$(ls "$NM"/@xberg-io/xberg/*.node 2>/dev/null | head -1)
say "{\"node_modules\":$NMC,\"xberg\":\"${XBG:-缺失}\"}" "node_modules: $NMC 项 | xberg 绑定: ${XBG:-缺失}"
[ -z "$XBG" ] && RED=1

# 8 link 依赖存在性
MISS=""
for d in dsh-plugin-agent-bus dsh-plugin-local-projects dsh-plugin-mcp-station dsh-plugin-research dsh-plugin-sandbox-policy-ui dsh-plugin-voice dsh-plugin-workflow-capture dsh-plugin-repo-pipeline dsh-plugin-workflow/market/dsh-plugin-market; do
  [ -d ~/$d ] || MISS="$MISS $d"
done
say "{\"link_deps_missing\":\"$MISS\"}" "link 依赖缺失: ${MISS:-无}"
[ -n "$MISS" ] && RED=1

# 9 基线快照对比参考（会话/配置）
PROF=$(grep -c '"agentId"' ~/.dsh/agent-bus.json 2>/dev/null || echo '?')

# 10 外卖面板采集新鲜度（CLD-009：以 lastTick 判定链路健康，而非告警时间戳）
PANEL_STALE=0
PANEL=$(curl -s --max-time 5 http://127.0.0.1:8787/api/state 2>/dev/null)
if [ -n "$PANEL" ]; then
  PINFO=$(echo "$PANEL" | python3 -c "
import json,sys,datetime
try:
    d=json.load(sys.stdin)
    stores=d.get('stores',[])
    if not stores:
        print('stores=0'); sys.exit(0)
    now=datetime.datetime.now(datetime.timezone.utc)
    worst=None; stale=0; total=len(stores)
    for s in stores:
        lt=s.get('lastTick') or ''
        try:
            t=datetime.datetime.fromisoformat(lt.replace('Z','+00:00'))
            age=(now-t).total_seconds()
        except Exception:
            age=-1
        if age<0 or age>300: stale+=1
        if worst is None or age>worst[1]: worst=(s.get('name','?'),age)
    nm,age=worst
    print(f'stores={total} stale={stale} worst={nm} age={int(age)}s')
except Exception as e:
    print(f'parse_error={e}')
")
  say "{\"panel\":\"$PINFO\"}" "面板 8787: $PINFO"
  case "$PINFO" in
    parse_error*|stores=0*) say "{\"panel_warn\":true}" "  ⚠ 面板响应异常（信息级，权威判定用 waimai_state 宿主工具）" ;;
    *) S=$(echo "$PINFO" | sed -n 's/.*stale=\([0-9]*\).*/\1/p'); [ "${S:-1}" != "0" ] && say "{\"panel_warn\":true}" "  ⚠ 存在 stale 店（信息级，权威判定用 waimai_state）" ;;
  esac
  STALE=$(echo "$PINFO" | sed -n 's/.*stale=\([0-9]*\).*/\1/p'); STALE=${STALE:-?}
else
  # 沙箱网络隔离可能对 127.0.0.1:8787 假阴性（协调者裁决 2026-08-17）→ 不判红，信息级提示
  say "{\"panel\":\"unreachable\"}" "面板 8787: 探测不可达（信息级——沙箱网络隔离可能假阴性，权威判定用 waimai_state 宿主工具）"
  STALE="?"
fi

RC=$RED
say "{\"ts\":\"$NOW\",\"healthy\":$([ $RC -eq 0 ] && echo true || echo false)}" "---"
say "" "巡检时间: $NOW | 结果: $([ $RC -eq 0 ] && echo '✅ 健康' || echo '❌ 存在异常(见上)')"

# 11 配置运行期改写检测（CLD-003 复发预警，信息级）：package.json mtime 晚于最后启动 = 运行中被改写
BOOTLINE=$(grep 'CLD boot' "$WEBLOG" 2>/dev/null | tail -1)
BOOTTS=$(echo "$BOOTLINE" | sed 's/.*boot //;s/ =====//;s/\.[0-9]*Z/Z/')
BOOTEPOCH=$(BOOTTS="$BOOTTS" python3 -c "import os,datetime; s=os.environ['BOOTTS']; print(int(datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()))" 2>/dev/null)
PKGEPOCH=$(stat -f %m "$PKG" 2>/dev/null)
if [ -n "$BOOTEPOCH" ] && [ -n "$PKGEPOCH" ]; then
  if [ "$PKGEPOCH" -gt "$BOOTEPOCH" ]; then
    say "{\"config_after_boot\":\"modified\"}" "配置检测: ⚡ package.json 在最后启动（boot ${BOOTTS}）后被改写（mtime=$(date -r $PKGEPOCH '+%m-%d %H:%M')）——需确认是否为协调变更"
  else
    say "{\"config_after_boot\":\"clean\"}" "配置检测: 无运行期改写（package.json 先于最后启动）"
  fi
else
  say "{\"config_after_boot\":\"unknown\"}" "配置检测: 无法判定"
fi

# 12 内存压力检测（CLD-011）+ swap 占用（设备协调员数据：swap 94% 近满）
MEMFREE=$(memory_pressure -Q 2>/dev/null | sed -n 's/.*free percentage: \([0-9]*\)%.*/\1/p')
if [ -n "$MEMFREE" ]; then
  say "{\"mem_free_pct\":$MEMFREE}" "内存: 空闲 $MEMFREE%"
  [ "$MEMFREE" -lt 10 ] && RED=1 && say "{\"mem_low\":true}" "  ⚠ 内存空闲 <10%"
else
  say "{\"mem_free_pct\":\"?\"}" "内存: 无法判定"
fi
SWAPINFO=$(sysctl vm.swapusage 2>/dev/null)
SWAP_USED=$(echo "$SWAPINFO" | sed -n 's/.*used = \([0-9.]*\)M.*/\1/p')
SWAP_TOTAL=$(echo "$SWAPINFO" | sed -n 's/.*total = \([0-9.]*\)M.*/\1/p')
if [ -n "$SWAP_USED" ] && [ -n "$SWAP_TOTAL" ]; then
  SWAP_PCT=$(SWAP_USED="$SWAP_USED" SWAP_TOTAL="$SWAP_TOTAL" python3 -c "import os;u=float(os.environ['SWAP_USED']);t=float(os.environ['SWAP_TOTAL']);print(int(u*100/t) if t>0 else 0)")
  say "{\"swap_pct\":$SWAP_PCT}" "swap: 占用 ${SWAP_PCT}%"
  [ "${SWAP_PCT:-0}" -ge 80 ] && say "{\"swap_high\":true}" "  ⚠ swap 占用 >=80%（近满，内存压力信号）"
else
  say "{\"swap_pct\":\"?\"}" "swap: 无法判定"
fi
# 14 会话日志帧完整性（b278baab 建议：0 撕裂/无 parse error）
ZSTDBIN=/opt/homebrew/bin/zstd
[ -x "$ZSTDBIN" ] || ZSTDBIN=$(command -v zstd 2>/dev/null || echo zstd)
TORN=0; STOTAL=0
for f in ~/.dsh/sessions/--Users-coreyleung--/*/session.jsonl.zstd; do
  [ -f "$f" ] || continue
  STOTAL=$((STOTAL+1))
  "$ZSTDBIN" -t "$f" >/dev/null 2>&1 || TORN=$((TORN+1))
done
say "{\"session_logs\":$STOTAL,\"torn\":$TORN}" "会话日志完整性: $STOTAL 个 / 撕裂 $TORN"
[ "$TORN" -gt 0 ] && RED=1 && say "{\"torn_warn\":true}" "  ⚠ 存在撕裂会话日志（帧完整性受损，需会话 doctor）"

# 15 xberg dylib 运行时套装完整性（c1111ffe 建议：防 .node 在位但 dylib 缺失漏判）
XNODE_COUNT=$(ls "$NM"/@xberg-io/xberg/ 2>/dev/null | grep -cE '.node$|dylib$')
XNODE_COUNT=${XNODE_COUNT:-0}
if [ "$XNODE_COUNT" -ge 8 ]; then
  say "{\"xberg_kit\":\"ok($XNODE_COUNT files)\"}" "xberg 套装: OK（node+dylib $XNODE_COUNT 文件）"
else
  say "{\"xberg_kit\":\"broken($XNODE_COUNT)\"}" "xberg 套装: ⚠ 不完整（$XNODE_COUNT/8，需 postinstall 恢复）"
  RED=1
fi

# 16 供应链上游检查（0e84e65c upstream-check.sh --status 一行输出，信息级）
UPC=~/dsh-collab/supply-chain/upstream-check.sh
if [ -x "$UPC" ]; then
  UPSTATUS=$( ( "$UPC" --status 2>/dev/null & UP=$!; ( sleep 15; kill $UP 2>/dev/null ) & KP=$!; wait $UP 2>/dev/null; kill $KP 2>/dev/null ) | tail -1 )
  say "{\"upstream\":\"$UPSTATUS\"}" "供应链上游: $UPSTATUS"
else
  say "{\"upstream\":\"missing\"}" "供应链上游: 脚本缺失（$UPC）"
fi

# 17 通讯通道卫生（R033/R034 生效 · CLD 节点网络公约 §1.3 · 星桥提供探测方案）
#    4 项: 队列零积压/守护进程/SSE 存活/无异常（health-item17-comms.sh，免 curl 401）
ITEM17=~/dsh-collab/cld-health/health-item17-comms.sh
if [ -x "$ITEM17" ]; then
  I17=$(bash "$ITEM17" 2>/dev/null); I17RC=$?
  # 汇总一行给巡检输出（保留子脚本详细行于 stderr 诊断）
  I17_SUM=$(echo "$I17" | grep -E '结果:' | tr -d '─')
  say "{\"comms\":\"$([ $I17RC -eq 0 ] && echo ok || echo fail)\"}" "通讯通道卫生: $I17_SUM"
  [ $I17RC -ne 0 ] && RED=1 && say "{\"comms_fail\":true}" "  ⚠ 通讯链路异常（见 health-item17-comms.sh 明细）"
else
  say "{\"comms\":\"missing\"}" "通讯通道卫生: 脚本缺失（$ITEM17）"
  RED=1
fi

# 18 磁盘最大占用者（CLD-022 防复发 · 守灯 2026-09-11 立）
#    旧巡检只报「Data 卷 ≥85%」= 报占用率，报不出「是谁在吃」⇒ 无法处置。
#    本项补：大文件枚举 + 存活时长(birthtime，非 mtime) + 轮转兄弟 + 持有者 + 增长速率/ETA。
ITEM18=~/dsh-collab/cld-health/health-item18-disk.sh
if [ -x "$ITEM18" ]; then
  I18=$(bash "$ITEM18" 2>/dev/null); I18RC=$?
  say "{\"disk_top_consumer\":\"$([ $I18RC -eq 0 ] && echo none || echo action)\"}" "$(echo "$I18" | grep -E '^  (18a|18b|18d)|^    - ' | head -4)"
  [ $I18RC -ne 0 ] && RED=1 && say "{\"disk_top_action\":true}" "  ⚠ 磁盘存在无轮转大文件（见 health-item18-disk.sh 明细）"
else
  say "{\"disk_top_consumer\":\"missing\"}" "磁盘最大占用者: 脚本缺失（$ITEM18）"
  RED=1
fi

# --log: 追加时间序列记录（趋势/基线对比用）
if [ "${1:-}" = "--log" ]; then
  LOG=~/dsh-collab/cld-health/health-log.tsv
  [ -f "$LOG" ] || printf 'ts\tload1\tgui\tboot_err\tbundles\tpanel_stale\tresult\n' > "$LOG"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$NOW" "$L1" "$GUI" "${ERR:-?}" "${BC:-?}" "$STALE" "$([ $RC -eq 0 ] && echo OK || echo FAIL)" >> "$LOG"
  # 负载联动协议（协调者 01:00 定）：连续 >=2 轮 load>=12 → 上报协调者错峰
  CONS=$(awk -F'\t' 'NR>1 {n=($2+0>=12)?n+1:0} END {print n+0}' "$LOG")
  if [ "${CONS:-0}" -ge 2 ]; then
    say "{\"load_consecutive\":$CONS}" "  ⚠ 连续 $CONS 轮负载>=12——按协议上报协调者（CLD-005 错峰）"
  fi
  say "" "已追加趋势记录 → health-log.tsv"
fi
# --push: 关键告警推送（R006 v2 #10 结构门：需 GATE 文件 ~/.dsh/.cld-health-push-gate 显式放行，
#   默认结构性拒绝——P3 拦截系统运维信息外推，无法绕过）
if [ "${1:-}" = "--push" ]; then
  if ! push_allowed; then
    echo "⛔ push 结构性拒绝（R006 v2 #10 Lean4 门）：未找到 GATE 文件 $PUSH_GATE_FILE —— P3 拦截，系统运维信息不外推。"
  else
    PUSH_MSG=""
  [ "${SWAP_PCT:-0}" -ge 80 ] && PUSH_MSG="${PUSH_MSG}swap=${SWAP_PCT}% "
  [ "${DATA_PCT:-0}" -ge 85 ] && PUSH_MSG="${PUSH_MSG}DataVol=${DATA_PCT}% "
  LOGCONS=$(awk -F'\t' 'NR>1 {n=($2+0>=12)?n+1:0} END {print n+0}' ~/dsh-collab/cld-health/health-log.tsv 2>/dev/null || echo 0)
  [ "${LOGCONS:-0}" -ge 2 ] && PUSH_MSG="${PUSH_MSG}loadConsecutive=${LOGCONS} "
  if [ -n "$PUSH_MSG" ]; then
    curl -s -X POST http://127.0.0.1:8790/send -H "Content-Type: application/json" -d "{\"text\":\"[CLD健康告警] $PUSH_MSG\"}" >/dev/null 2>&1 && echo "已推送告警: $PUSH_MSG" || echo "推送失败(webhook 不可达)"
  else
    echo "无关键告警，不推送"
  fi
  fi
fi
exit $RC
