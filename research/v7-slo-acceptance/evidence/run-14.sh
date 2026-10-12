#!/bin/bash
# v7-SLO 14 指标复跑取证器
# 用法: bash run-14.sh            # 全部跑一遍，逐条落盘 stdout+stderr+exit
#       bash run-14.sh S3 S12     # 只跑指定几条
# ★ 退出码取自【命令本体】(PIPESTATUS[0]/直跑)，不取管道末端 —— 本机已犯过「tail 的 rc 冒充命令的 rc」。
# 产出: 同目录 out/S<编号>.{txt,rc}
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/out"
mkdir -p "$OUT"
REPO="$HOME/dsh-collab"
WANT="${*:-S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14}"

run() {                      # run <编号> <标题> <命令...>
  local id="$1"; local title="$2"; shift 2
  echo "=== $id · $title ===" >&2
  {
    echo "# $id · $title"
    echo "# 命令: $*"
    echo "# 时刻: $(date "+%Y-%m-%dT%H:%M:%S%z")"
    echo "# --- 未编辑原始输出 ---"
    "$@" 2>&1
    local rc=$?
    echo "# --- end ---"
    echo "$rc" > "$OUT/$id.rc"
    return $rc
  } | tee "$OUT/$id.txt" >/dev/null
  printf "  %s rc=%s\n" "$id" "$(cat "$OUT/$id.rc")" >&2
}

for id in $WANT; do
case "$id" in
S1) run S1 "信标新鲜度（索引 updated_at 是否落后 / 是否落在未来）" \
      python3 "$HERE/probe-beacon-freshness.py"
    run S1b "信标新鲜度 · 支撑门（索引内部自洽）" \
      python3 "$REPO/tools/beacon-check.py" --net ;;
S2) run S2 "自检覆盖（G-CR18 四条判据）" \
      python3 "$REPO/tools/beacon-cover-check.py" --strict ;;
S3) run S3 "官方校对留证（24h 时效）" \
      python3 "$REPO/tools/official-ref-gate.py" --target "session persistence" ;;
S4) run S4 "闭环率（closed_with_evidence 占比 + verifier 在位）" \
      python3 "$HERE/probe-closure-rate.py" ;;
S5) run S5 "审查覆盖（review-tracker 独立审查登记数）" \
      python3 "$REPO/tools/review-gate.py" ;;
S6) run S6 "崩溃复发（G-CR 门全绿）" \
      python3 "$REPO/tools/gcr-gate.py" ;;
S7) run S7 "单会话体积 / 事件数" \
      python3 "$HERE/probe-session-volume.py" ;;
S8) run S8 "会话目录体积" \
      bash -c 'du -sh ~/.dsh/sessions | awk "{print \$1}" | sed "s/^/会话目录: /"' ;;
S9) run S9 "inbox 文件数 / 体积" \
      bash -c 'printf "文件数: "; ls ~/.dsh/inbox | wc -l; printf "体积: "; du -sh ~/.dsh/inbox | awk "{print \$1}"' ;;
S10) run S10 "bus 单文件体积" \
      bash -c 'ls -l ~/.dsh/agent-bus.json | awk "{printf \"字节: %s (%.1f MiB)\n\", \$5, \$5/1048576}"' ;;
S11) run S11 "黑板数据体积 / snapshot / DELETE 次数" \
      python3 "$HERE/probe-board-volume.py" ;;
S12) run S12 "真积压（event-bus pending）" \
      python3 "$REPO/scripts/event-bus.py" --status ;;
S13) run S13 "机制激活可观测（持久化激活计数器条数）" \
      python3 "$HERE/probe-activation-counters.py" ;;
S14) run S14 "端口稳定性（在役监听端口清单）" \
      bash -c 'lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk "NR>1{print \$1, \$9}" | sort -u' ;;
esac
done

echo "=== 汇总 ===" >&2
for id in $WANT; do
  [ -f "$OUT/$id.rc" ] && printf "%-4s rc=%s\n" "$id" "$(cat "$OUT/$id.rc")" >&2
done
