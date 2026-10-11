#!/bin/bash
# cld-mic-test-precheck.sh — 麦克风测试【前置正控】：先验被测对象正确，再判成败
#
# ★ 为什么需要（2026-10-10 实测事故的反例判据）：
#   换装完成后，用户测试麦克风仍失败 —— 根因**不是修复失败**，而是
#   **测在了「备份路径下的旧实例」上**（tccd responsible 显示旧路径）。
#   ⇒ 教训：**麦克风测试的判据必须分两步** ——
#       ① **正控**：被测的 CLD 实例，其**映像路径 = /Applications/CLD.app**（否则测的不是新版）
#       ② **才判成败**：说话有没有反应 / TCC 是否放行
#   ★ 无第①步时，「失败」无法区分「修复无效」与「测错对象」（本次正是后者）。
#
# ★ 判据要点（两条都是今晚踩出来的）：
#   · **必须用 `lsof` 的映像路径判实例**，**不可用 `ps` 的 argv** ——
#     app 目录被 `mv` 后 argv 仍显示旧路径，而映像已在新位置（**argv 会被 mv 欺骗**）。
#   · 本脚本**只读**，不改任何东西（不改 app、不重启、不动 TCC）。
#
# 用法：
#   bash tools/cld-mic-test-precheck.sh          # 人读版
#   bash tools/cld-mic-test-precheck.sh --quiet  # 仅输出判定与退出码
#
# 退出码：0 = 正控通过（可测）· 1 = 正控失败（测了也白测）· 2 = 无实例
set -uo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1
say() { [ "$QUIET" = 1 ] || printf '%s\n' "$*"; }

EXPECT_PATH="/Applications/CLD.app"
EXPECT_SIG="com.apple.security.device.audio-input"

say "★ CLD 麦克风测试 · 前置正控（只读）"
say "★ 扫描时点：$(date '+%Y-%m-%d %H:%M:%S%z')"
say ""

# ═══ ① 枚举「真正的 CLD 主进程」（用映像路径，不用 argv）═══
#   主进程 = 映像为 <某 app>/Contents/MacOS/CLD 者；再排除其 dsh 子进程（argv 含 --expose-internals）
declare -a PIDS PATHS
#   ★ 取映像路径用 `ps -o comm=` —— 它直接给**完整可执行路径**，且不受 `lsof` 多行 txt 段干扰
#     （v1.0.0 用 `lsof | awk '$4=="txt"{print $NF; exit}'` ⇒ 对 Helper 取到的是**加载的库**而非主映像，
#      实测导致「未枚举到 Helper」的假阴性；由 `session-0d4aec63` 建议补 Helper 时才暴露）
for p in $(ps -axo pid=,command= | awk '/CLD\.app\/Contents\/MacOS\/CLD/ && !/--expose-internals/ {print $1}'); do
  img=$(ps -p "$p" -o comm= 2>/dev/null)
  case "$img" in
    */Contents/MacOS/CLD) PIDS+=("$p"); PATHS+=("$img") ;;
  esac
done

if [ "${#PIDS[@]}" -eq 0 ]; then
  say "  ✗ 未找到 CLD 主进程（映像路径匹配）⇒ 无可测对象"
  say "  ⇒ 请先打开 CLD，再重跑本预检。"
  say "  === PRECHECK=NO_INSTANCE ==="
  exit 2
fi

say "  找到 ${#PIDS[@]} 个 CLD 主进程："
GOOD=0
BAD=0
for i in "${!PIDS[@]}"; do
  pid="${PIDS[$i]}"; img="${PATHS[$i]}"
  ent=$(codesign -d --entitlements - "$img" 2>/dev/null | grep -c "$EXPECT_SIG")
  case "$img" in
    "$EXPECT_PATH"/Contents/MacOS/CLD)
      say "    ✅ pid=$pid  映像=$img  audio-input=$ent"
      GOOD=$((GOOD+1)) ;;
    *)
      say "    ❌ pid=$pid  映像=$img  ← ★ **不是 $EXPECT_PATH**（陈旧/备份实例）audio-input=$ent"
      BAD=$((BAD+1)) ;;
  esac
done

say ""

# ═══ ② 线上 app 自身的 entitlement（判断"该有"标准）═══
APP_ENT=$(codesign -d --entitlements - "$EXPECT_PATH" 2>/dev/null | grep -c "$EXPECT_SIG")
say "  线上 $EXPECT_PATH 的 audio-input = $APP_ENT $([ "$APP_ENT" -ge 1 ] && echo '✅' || echo '✗（app 本体缺键）')"

# ═══ ②b ★ Helper 映像枚举（v1.0.1 补 · 由 session-0d4aec63 指出）═══
#   ★ 为何必须补：**实际发起麦克风请求的往往是 CLD Helper** ——
#     实测：03:03 那次 tccd 判决的 `accessing` 正是 `CLD Helper`
#     ⇒ 只验主进程而不验 Helper ⇒ **漏掉真正会被 tccd 判定的对象**。
declare -a HPIDS HPATHS
for p in $(ps -axo pid=,command= | awk '/CLD\.app\/Contents\/Frameworks\// {print $1}'); do
  img=$(ps -p "$p" -o comm= 2>/dev/null)
  case "$img" in
    */CLD.app/Contents/*) HPIDS+=("$p"); HPATHS+=("$img") ;;
  esac
done
say ""
if [ "${#HPIDS[@]}" -eq 0 ]; then
  say "  ⚠ 未枚举到 CLD Helper 子进程（可能尚未拉起；麦克风请求通常由它们发起）"
else
  say "  找到 ${#HPIDS[@]} 个 CLD 框架内子进程（主进程之外）："
  HBAD=0
  for i in "${!HPIDS[@]}"; do
    pid="${HPIDS[$i]}"; img="${HPATHS[$i]}"
    name=$(printf '%s' "$img" | sed -n 's|.*/CLD.app/Contents/[^/]*/||p' | sed 's|/Contents/MacOS/.*||')
    case "$img" in
      "$EXPECT_PATH"/Contents/*)
        say "    ✅ pid=$pid  $(basename "${img%/Contents/MacOS/*}" 2>/dev/null || echo helper)" ;;
      *)
        say "    ❌ pid=$pid  映像=$img  ← ★ **不在 $EXPECT_PATH 内**（陈旧实例的 Helper —— **会被 tccd 判定**）"
        HBAD=$((HBAD+1)) ;;
    esac
  done
  if [ "$HBAD" -gt 0 ]; then
    say "  ⇒ ★ **有 $HBAD 个 Helper 映像不在 $EXPECT_PATH 内** ⇒ 它们发起的麦克风请求**不会**反映新版签名"
  fi
fi

# ═══ ②c ★ 世代判据（v1.0.2 补 · 由 session-0d4aec63 建议）═══
#   ★ 为何必须补：**路径判据不编码「世代」** —— `/Applications/CLD.app` 这个路径
#     今天可能是新签名版、明天可能被换回旧版 ⇒ **路径相同 ≠ 版本相同**。
#   ★ 它给的判据：**主实例 = 1 且 `lstart` ≥ 换装 `RESULT` 时刻**。
#   ★ 实现要点（自测抓到）：**世代锚必须取「含 RESULT=OK 的那条日志」**，
#     **不能取 ls -t 的最新日志** —— 实测最新那条是「被前置门拦住」的实例（无 RESULT=OK）。
GEN_EPOCH=""
GEN_SRC=""
for f in $(ls -t "$HOME/dsh-collab/logs"/cld-mic-apply-*.log 2>/dev/null); do
  if grep -q "RESULT=OK" "$f" 2>/dev/null; then
    # 取该文件里 RESULT=OK 那一行的时间戳
    line=$(grep -m1 "RESULT=OK" "$f")
    ts=$(printf '%s' "$line" | sed -n 's/^\[\([0-9-]\{10\} [0-9:]\{8\}\)\].*/\1/p')
    if [ -n "$ts" ]; then
      GEN_SRC="$f"
      GEN_EPOCH=$(date -j -f "%Y-%m-%d %H:%M:%S" "$ts" "+%s" 2>/dev/null || echo "")
      GEN_HUMAN="$ts"
    fi
    break
  fi
done

say ""
if [ -z "$GEN_EPOCH" ]; then
  say "  ⚠ **世代锚缺失** —— 未找到含 RESULT=OK 的换装日志 ⇒ 世代判据**无法评估**（非通过）"
else
  say "  世代锚（换装 RESULT=OK）: $GEN_HUMAN"
  say "     来源: $(basename "$GEN_SRC")"
  say ""
  say "  ★ 世代判据逐实例："
  GENBAD=0
  for i in "${!PIDS[@]}"; do
    pid="${PIDS[$i]}"
    ls_epoch=$(ps -p "$pid" -o lstart= 2>/dev/null | xargs -I{} date -j -f "%a %b %d %T %Y" "{}" "+%s" 2>/dev/null || echo "")
    if [ -z "$ls_epoch" ]; then
      say "    ⚠ pid=$pid 无法取 lstart ⇒ 世代**无法判定**"
      GENBAD=$((GENBAD+1)); continue
    fi
    if [ "$ls_epoch" -ge "$GEN_EPOCH" ]; then
      say "    ✅ pid=$pid lstart=$(ps -p $pid -o lstart= | xargs) ⇒ **晚于**换装 RESULT（世代正确）"
    else
      say "    ❌ pid=$pid lstart 早于换装 RESULT ⇒ ★ **疑似旧世代实例**（可能被换回旧版）"
      GENBAD=$((GENBAD+1))
    fi
  done
  [ "${#PIDS[@]}" -ne 1 ] && { say "    ❌ **主实例数 = ${#PIDS[@]}**（应为 1）⇒ 多实例会各自独立授权，结果不可归因"; GENBAD=$((GENBAD+1)); }
fi

# ═══ ③ 判定 ═══
say ""
if [ "$BAD" -gt 0 ] || [ "${HBAD:-0}" -gt 0 ] || [ "${GENBAD:-0}" -gt 0 ]; then
  say "══ 正控：❌ **失败** —— 主进程越界 $BAD · Helper 越界 ${HBAD:-0} · 世代/唯一性 ${GENBAD:-0} ══"
  say "   ⇒ ★ **此刻测麦克风会测到这些陈旧实例上**，其结果**不能归因于新版签名**。"
  say "   ⇒ 处置（**不在本脚本内执行**）：先让用户完全退出 CLD，再从 $EXPECT_PATH 重开；"
  say "     或用 tools/cld-restart-to-correct-app.sh（幂等）切换。"
  say "  === PRECHECK=FAIL_STALE_INSTANCE ==="
  exit 1
fi
if [ "$APP_ENT" -lt 1 ]; then
  say "══ 正控：❌ **失败** —— 线上 app 缺 $EXPECT_SIG ══"
  say "   ⇒ 说明换装未生效（或 app 被回滚）⇒ **先修 app，再测**。"
  say "  === PRECHECK=FAIL_APP_ENTITLEMENT ==="
  exit 1
fi
say "══ 正控：✅ **通过** —— 主实例 1 个 · lstart 晚于换装 RESULT（世代正确） · 主进程 + ${#HPIDS[@]} 子进程映像全在 $EXPECT_PATH 内 · app 含 audio-input ══"
say "   ⇒ **现在可以点 ●说话 测试**；TCC 判决的 responsible/accessing 应指向 $EXPECT_PATH 内的进程。"
say "   ⇒ 测后取证："
say "      log show --last 5m --predicate 'process == \"tccd\"' | grep -i microphone"
say "  === PRECHECK=PASS ==="
exit 0
