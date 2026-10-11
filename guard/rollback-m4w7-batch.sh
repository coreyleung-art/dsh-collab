#!/bin/bash
# rollback-m4w7-batch.sh — M4/W7 批次属主件改动的**一键回滚**
#
# ★ 出件：2026-10-11 · 星桥第二任（mac-mini）· 目的：**重启前审查**发现 10 个被改文件里
#   有 3 个【无备份回滚点】（非 git 仓库），本脚本把这 3 个的**精确反向编辑**写下来，
#   使每一个被改文件都有**可执行**的回滚路径。
#
# 用法:
#   bash rollback-m4w7-batch.sh --dry-run     # 只打印计划，不改任何文件（默认）
#   bash rollback-m4w7-batch.sh --apply       # 真正执行回滚
#
# ★ 诚实声明：
#   · 有备份的 7 个文件走 `cp <backup> <target>`（**逐字节还原**）。
#   · ★ 无备份的 3 个文件走**反向编辑**（两者内容等价但**非逐字节**：注释块不会被还原）。
#     ⇒ 本脚本对那 3 个的还原是【**等价还原**，不是【字节还原】】—— ★ 不得读作逐字节一致。
set -u
APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1
BK="$HOME/dsh-collab/guard/backups"
say() { printf "  %s\n" "$*"; }
do_cp() {  # $1=backup文件 $2=目标
  if [ ! -f "$1" ]; then say "★ 缺备份：$1"; return 1; fi
  if [ "$APPLY" = "1" ]; then cp "$1" "$2" && say "✓ 已还原 $2"; else say "[dry] cp $(basename "$1") → $2"; fi
}
do_rev() {  # $1=文件 $2=old $3=new
  if [ ! -f "$1" ]; then say "★ 缺文件：$1"; return 1; fi
  if grep -qF "$3" "$1"; then
    if [ "$APPLY" = "1" ]; then
      /usr/bin/sed -i '' "s|$(printf '%s' "$3" | sed 's/[&/\]/\\&/g')|$(printf '%s' "$2" | sed 's/[&/\]/\\&/g')|g" "$1" && say "✓ 已反向编辑 $1"
    else say "[dry] 反向编辑 $1：\"$3\" → \"$2\""; fi
  else say "—  $1 未含 \"$3\"（可能已回滚或版本不同）"; fi
}

echo "== M4/W7 批次一键回滚（APPLY=$APPLY）=="
echo
echo "── A. 有备份的 7 个文件（逐字节还原）──"
do_cp "$BK/Users__coreyleung__dsh-plugin-agent-bus__lib__index.js.bak-good-2026-10-10-20-3" "$HOME/dsh-plugin-agent-bus/lib/index.js"
do_cp "$BK/dsh-plugin-agent-bus__lib_selfcheck.js.bak-good-2026-10-11-gitHEAD" "$HOME/dsh-plugin-agent-bus/lib/selfcheck.js"
do_cp "$BK/dsh-plugin-agent-bus__package.json.bak-good-2026-10-11-gitHEAD" "$HOME/dsh-plugin-agent-bus/package.json"
do_cp "$BK/Users__coreyleung__dsh-plugin-launchd-scan__lib__core.js.bak-good-2026-10-10-20-3" "$HOME/dsh-plugin-launchd-scan/lib/core.js"
do_cp "$BK/Users__coreyleung__dsh-plugin-guard__lib__index.js.bak-good-2026-10-10-20-3" "$HOME/dsh-plugin-guard/lib/index.js"
do_cp "$BK/Users__coreyleung__dsh-plugin-bus-queue-triage__cli.js.bak-good-2026-10-10-20-3" "$HOME/dsh-plugin-bus-queue-triage/cli.js"
say "（guard/package.json：存在 2026-10-08 的旧备份，但**不用它**—— 那会一并回退 3 天内的其它字段；"
say "  改用 §B 的**精确反向编辑**只回退版本号，风险更小）"
echo
echo "── B. ★ 无备份的 3 个文件（【等价】反向编辑，非字节还原）──"
do_rev "$HOME/dsh-plugin-launchd-scan/package.json" '"version": "1.0.0"' '"version": "1.0.1"'
do_rev "$HOME/dsh-plugin-bus-queue-triage/package.json" '"version": "1.0.0"' '"version": "1.0.1"'
do_rev "$HOME/dsh-plugin-bus-queue-triage/lib/core.js" "const VERSION = '1.0.0';" "const VERSION = '1.0.1';"
do_rev "$HOME/dsh-plugin-guard/package.json" '"version": "0.1.1"' '"version": "0.1.2"'
echo
echo "── C. 回滚后核验（三条）──"
say "node --check 四个 lib 文件"
say "node ~/dsh-plugin-agent-bus/cli.js --selfcheck        # 期望 exit 0（旧版也应 PASS）"
say "python3 ~/dsh-collab/scripts/verify-m4w7-batch-fixes.py --status   # 期望四件全 FAIL（= 已回滚）"
echo
if [ "$APPLY" != "1" ]; then echo "★ 本次为 dry-run，未改任何文件。加 --apply 才执行。"; fi
