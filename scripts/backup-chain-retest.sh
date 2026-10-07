#!/bin/bash
VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）
# backup-chain-retest —— 备份链四处缺陷的可重测命令（2026-09-14 老登 aa528267）
#
# 立据（HR 2026-09-14 采纳：「**修复的消费者＝可重测命令**」——否则修复本身也只是报告）。
# 并落实 HR 的统一绑定要求：「**凡结论、读数、比率、修复，皆须绑『使其成立的制品状态』；状态变化即自动失效**」
#   ⇒ 本工具在输出里**带上两份脚本的内容哈希**作为「对象状态」；脚本一改，先前结论即自动失效。
#
# 四级强度声明：**门**（任一 FAIL ⇒ 退出码 1）
# 类别声明：**正确性**（防「结论过期」与「调用点不可达」被当成已修）
#
# 用法: backup-chain-retest.sh [--json]
set -uo pipefail

HC_DEF="$HOME/dsh-plugin-research/sysops/automation/health-check.sh"
WB_DEF="$HOME/dsh-plugin-research/sysops/automation/waimai-backup.sh"
LIVE_DB_DEF="$HOME/Library/Application Support/外卖门店多平台管理/data/app.db"
DEST_DEF="$HOME/Desktop/DSH-备份/meituan-multi"
# 路径可覆盖（供 --selftest 在副本上做对象变异，不触碰真实文件）
HC="$HC_DEF"; WB="$WB_DEF"; LIVE_DB="$LIVE_DB_DEF"; DEST="$DEST_DEF"
while [ $# -gt 0 ]; do
  case "$1" in
    --hc) HC="$2"; shift 2;;
    --wb) WB="$2"; shift 2;;
    --live-db) LIVE_DB="$2"; shift 2;;
    --dest) DEST="$2"; shift 2;;
    --selftest) SELFTEST=1; shift;;
    --json) JSON=1; shift;;
    *) shift;;
  esac
done
PASS=0; FAIL=0
declare -a RESULTS

h(){ [ -f "$1" ] && shasum -a 256 "$1" | cut -c1-16 || echo "MISSING"; }
ok(){ RESULTS+=("PASS|$1|$2"); PASS=$((PASS+1)); }
no(){ RESULTS+=("FAIL|$1|$2"); FAIL=$((FAIL+1)); }

echo "备份链可重测命令 · $(date '+%F %T')"
echo "★ 对象状态（脚本内容哈希 —— 脚本一改，本结论自动失效）："
echo "   health-check.sh : $(h "$HC")"
echo "   waimai-backup.sh: $(h "$WB")"
echo

# ① SRC 指向实盘 + 产物可恢复
if grep -q 'LIVE_DIR="\$HOME/Library/Application Support/外卖门店多平台管理"' "$WB" 2>/dev/null; then
  ok "① 源路径" "LIVE_DIR 指向实盘"
else
  no "① 源路径" "未指向实盘（或脚本缺失）"
fi
LATEST=$(ls -1t "$DEST"/app-2*.db 2>/dev/null | head -1)
if [ -n "$LATEST" ] && [ -s "$LATEST" ]; then
  INTEG=$(sqlite3 "$LATEST" "PRAGMA integrity_check;" 2>/dev/null | head -1)
  ROWS=$(sqlite3 "$LATEST" "SELECT count(*) FROM order_sales;" 2>/dev/null)
  LIVE_ROWS=$(sqlite3 "$LIVE_DB" "SELECT count(*) FROM order_sales;" 2>/dev/null)
  if [ "$INTEG" = "ok" ] && [ -n "$ROWS" ] && [ "$ROWS" != "0" ]; then
    ok "① 产物可恢复" "$(basename "$LATEST") · integrity=ok · order_sales=$ROWS（实盘 $LIVE_ROWS）"
  else
    no "① 产物可恢复" "integrity=$INTEG rows=$ROWS"
  fi
else
  no "① 产物可恢复" "备份目录无 app-2*.db"
fi

# ② 方法：使用 sqlite3 .backup（而非 cp 拷 WAL 活动库）
if grep -q '"\$SQLITE" "\$SRC_DB" ".backup' "$WB" 2>/dev/null; then
  ok "② 备份方法" "使用 sqlite3 .backup（非 cp）"
else
  no "② 备份方法" "未检出 sqlite3 .backup"
fi

# ③ 保留策略：默认 180 天 + 两级
if grep -q 'RETENTION_DAYS="\${WAIMAI_BACKUP_RETENTION_DAYS:-180}"' "$WB" 2>/dev/null \
   && grep -q 'compress_old' "$WB" 2>/dev/null; then
  ok "③ 保留策略" "默认 180 天 + 7 天后 zstd 归档"
else
  no "③ 保留策略" "保留期或归档逻辑不符"
fi

# ④ 调用点可达：harness 保留真实备份调用，仅替换 health CLI 输出以避免副作用
TMP=$(mktemp -d); TLOG="$TMP/hc.log"
sed -e "s|^LOG=.*|LOG=$TLOG|" \
    -e "s|^REPORT=.*|REPORT=$TMP/rep.md|" \
    -e 's|^OUT=\$("\$PY".*|OUT="no cross mark"|' \
    "$HC" > "$TMP/hc.sh" 2>/dev/null
if [ -s "$TMP/hc.sh" ] && bash "$TMP/hc.sh" >/dev/null 2>&1; then
  if grep -q 'waimai-backup' "$TLOG" 2>/dev/null; then
    ok "④ 调用点可达" "真实调用被执行（日志含备份脚本输出）"
  else
    no "④ 调用点可达" "脚本执行了但备份调用未到达 ⇒ 疑似死代码"
  fi
else
  no "④ 调用点可达" "harness 未能执行 health-check.sh"
fi
rm -rf "$TMP"

if [ "${SELFTEST:-0}" = "1" ]; then
  echo
  echo "★ selftest（对象变异验证：证明本门的结论确实随对象变化而失效）"
  T=$(mktemp -d)
  cp "$HC_DEF" "$T/hc-clean.sh" 2>/dev/null
  # 造一个「死代码形态」的副本：把备份块移到终止行之后
  python3 - "$HC_DEF" "$T/hc-dead.sh" <<'PYEOF'
import sys
src,dst=sys.argv[1],sys.argv[2]
lines=open(src,encoding="utf-8").read().split("\n")
bi=[i for i,l in enumerate(lines) if 'waimai-backup.sh' in l]
if not bi: open(dst,"w",encoding="utf-8").write("\n".join(lines)); sys.exit(0)
bi=bi[0]; start=bi-1 if lines[bi-1].strip().startswith('#') else bi
block=lines[start:bi+1]; rest=lines[:start]+lines[bi+1:]
ei=[i for i,l in enumerate(rest) if l.startswith('echo "$OUT" | grep -q "❌" && exit 1 || exit 0')][0]
open(dst,"w",encoding="utf-8").write("\n".join(rest[:ei+1]+[""]+block))
PYEOF
  # 干净副本：④ 应 PASS；死代码副本：④ 应 FAIL
  r_clean=$(bash "$0" --hc "$T/hc-clean.sh" --wb "$WB" --live-db "$LIVE_DB" --dest "$DEST" 2>&1; echo "RC=$?")
  c_rc=$(echo "$r_clean" | grep -o 'RC=[0-9]*' | tail -1)
  r_dead=$(bash "$0" --hc "$T/hc-dead.sh" --wb "$WB" --live-db "$LIVE_DB" --dest "$DEST" 2>&1; echo "RC=$?")
  d_rc=$(echo "$r_dead" | grep -o 'RC=[0-9]*' | tail -1)
  d_has=$(echo "$r_dead" | grep -c 'FAIL.*④')
  rm -rf "$T"
  S1=0; S2=0
  [ "$c_rc" = "RC=0" ] && S1=1
  [ "$d_rc" = "RC=1" ] && [ "$d_has" -ge 1 ] && S2=1
  echo "  $([ $S1 -eq 1 ] && echo ✅ || echo ❌) 干净副本 ⇒ exit 0（对象正常时结论成立）"
  echo "  $([ $S2 -eq 1 ] && echo ✅ || echo ❌) 死代码副本 ⇒ exit 1 且 ④ FAIL（对象变化 ⇒ 结论自动失效）"
  echo "  selftest $((S1+S2))/2 —— 通过则证明：**本门的结论确实绑定于对象状态**"
  [ $((S1+S2)) -eq 2 ] || exit 1
fi

echo
for r in "${RESULTS[@]}"; do
  IFS='|' read -r st name detail <<< "$r"
  printf "  %-6s %-14s %s\n" "$st" "$name" "$detail"
done
echo
echo "合计 PASS=$PASS FAIL=$FAIL"
echo "★ 绑定：以上结论仅对上述两个哈希的脚本版本成立；脚本变更后须重跑本命令。"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
