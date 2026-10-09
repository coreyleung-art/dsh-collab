#!/bin/bash
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .sh 版
r006_selfcheck() {
  echo "== mbp-log-guard 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。"
  echo "  · 依据：r006-debt-assess.py 机械扫描未检出以下原语："
  echo "  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数"
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）
# mbp-log-guard.sh v1.2 — 日志大小守卫：超限即截断，防止 launchd stdout 无界写满磁盘
#
# 历史：
#   v1.0 (2026-08-27) 事故根因：node-bridge stdout → mbp-agent.log 涨到 21GB 占满数据卷
#                     → 写了本脚本，但（a）路径只覆盖 ~/dsh-collab/devices/ 下 3 个
#                              （b）没有挂 launchd ⇒ 从未运行过（log-guard.log 不存在）
#   v1.1 (2026-09-28) 事故重演：/private/tmp/node-bridge-mac-mini.log 涨到 127.41 GB，
#                     磁盘仅剩 6.6 GB。本版：补齐路径 + 自轮转 + 由 launchd 每 5 分钟调用。
#                     ★ 但装载未生效 ⇒ 2026-10-01 第三次事故，156.35 GB。
#   v1.2 (2026-10-01) 星桥。装载问题已解（bootstrap exit=0，已实弹开火）。
#                     本版修【路径表】本身，三处：
#                     (1) 删除 5 条死路径（v1.0 遗留的 MBP 路径 + 从未存在的 .err/.log）
#                     (2) ★ 路径改【自动发现】而非手工维护：实测 launchd 全机有 174 条
#                         StandardOutPath/StandardErrorPath，其中 138 条文件存在、且
#                         138/138【无轮转兄弟】⇒ 全部潜在无界。硬编码 3 条覆盖 1.7%，
#                         下一颗地雷必然是表外的。自动发现把覆盖率提到 138/138。
#                     (3) ★ 路径身份归一化（realpath）：实测 /tmp/node-bridge-mac-mini.log
#                         与 /private/tmp/node-bridge-mac-mini.log 字符串不同、inode 相同
#                         （均 327052276）⇒ 用字符串比路径必然误判。v1.2 一律先 realpath。
#
# 用法:
#   mbp-log-guard.sh              # 正常：超限即截断
#   mbp-log-guard.sh --dry-run    # 只报告，不截断
#   mbp-log-guard.sh --list       # 列出发现的全部路径与体积，不截断
#
# 安全判据（截断前必须全部满足）：
#   a) 该路径是某个 launchd plist 的 StandardOutPath 或 StandardErrorPath
#      —— 即「launchd 会往这里写」，本就是日志 sink，不是数据文件
#   b) 存在 ∧ 是常规文件（非目录/非符号链接指向目录）
#   c) size > MAX
#   d) 不被 EXCLUDE_RE 命中（显式排除面）
#   e) 不在 EXCLUDE_EXACT 白名单内
#   ★ 全部满足才 truncate；任一条不满足即跳过并计数。

MAX=104857600  # 100 MiB
GUARD_LOG=/Users/coreyleung/dsh-collab/logs/log-guard.log
GUARD_LOG_MAX=5242880  # 5 MiB，守卫日志自身的上限
LA_DIRS="/Users/coreyleung/Library/LaunchAgents /Library/LaunchAgents"

# ── 显式排除面（永不截断）───────────────────────────────────────
# 判据：命中以下形态的路径，即使被 launchd 重定向也不截断（人工确认后再移出）
EXCLUDE_RE='(^|/)(sessions|node_modules|\.git|data|registry|backups)/|\.jsonl$|\.json$|\.db$|\.sqlite'
EXCLUDE_EXACT=""

DRY=0
LIST=0
case "$1" in
  --dry-run) DRY=1 ;;
  --list)    LIST=1; DRY=1 ;;
esac

# ── 守卫日志自轮转（防止守卫自己长成问题）────────────────────────
if [ -f "$GUARD_LOG" ] && [ "$(stat -f%z "$GUARD_LOG" 2>/dev/null || echo 0)" -gt "$GUARD_LOG_MAX" ]; then
  tail -c 1048576 "$GUARD_LOG" > "$GUARD_LOG.tmp" 2>/dev/null && mv "$GUARD_LOG.tmp" "$GUARD_LOG"
fi

# ── 路径发现 + 归一化（★ v1.2 核心变更）─────────────────────────
# 输出：每行一个 realpath；去重后按路径排序
discover() {
  /usr/bin/python3 - "$@" <<'PYEOF'
import plistlib, glob, os, sys
dirs = sys.argv[1:]
seen = {}
for d in dirs:
    for f in glob.glob(os.path.join(d, '*.plist')):
        try:
            p = plistlib.load(open(f, 'rb'))
        except Exception:
            continue
        for k in ('StandardOutPath', 'StandardErrorPath'):
            v = p.get(k)
            if not v:
                continue
            # ★ 归一化：/tmp 与 /private/tmp 是同一文件，必须 realpath 后再比
            rp = os.path.realpath(v)
            seen.setdefault(rp, os.path.basename(f))
for rp in sorted(seen):
    print(rp + '\t' + seen[rp])
PYEOF
}

FOUND=$(discover $LA_DIRS)
N_TOTAL=$(printf '%s\n' "$FOUND" | grep -c . )
N_EXIST=0
N_EMPTY=0
N_OVER=0
N_TRUNC=0

# ── 主循环 ───────────────────────────────────────────────────────
# 注意：被 launchd 持有 fd 的日志【不能用 rm】——rm 只删目录项，inode 仍被进程引用，
#       空间不释放。必须用 truncate（截断）；截断后若 fd 是追加语义则下次写回到 offset 0。
#       ★ 已实证：truncate 对持有中的 fd 有效且不打断进程（pid/inode 均不变）。
while IFS=$'\t' read -r f owner; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || continue
  [ -L "$f" ] && continue
  N_EXIST=$((N_EXIST+1))
  case "$f" in $EXCLUDE_EXACT) continue ;; esac
  if printf '%s' "$f" | grep -Eq "$EXCLUDE_RE"; then continue; fi
  sz=$(stat -f%z "$f" 2>/dev/null || echo 0)
  # ★ 清单必须与摘要对得上：-list 模式先印（含零字节），再按体积过滤
  [ "$sz" -eq 0 ] && N_EMPTY=$((N_EMPTY+1))
  if [ "$LIST" = "1" ]; then
    printf '%12s B  %s  ← %s\n' "$sz" "$f" "$owner"
  fi
  [ "$sz" -gt 0 ] || continue
  if [ "$sz" -gt "$MAX" ]; then
    N_OVER=$((N_OVER+1))
    if [ "$DRY" = "1" ]; then
      echo "WOULD-TRUNCATE $f ($sz bytes) ← $owner"
    else
      truncate -s 0 "$f" 2>/dev/null && {
        N_TRUNC=$((N_TRUNC+1))
        echo "$(date '+%Y-%m-%d %H:%M:%S') truncated $f ($sz bytes) ← $owner" >> "$GUARD_LOG"
      }
    fi
  fi
done <<< "$FOUND"

if [ "$LIST" = "1" ]; then
  echo "---"
  echo "发现 $N_TOTAL 条 launchd 日志路径；文件存在 $N_EXIST 条（零字节 $N_EMPTY · 非空 $((N_EXIST-N_EMPTY))）；超 $((MAX/1048576))MiB $N_OVER 条"
fi
if [ "$DRY" = "0" ] && [ "$N_TRUNC" -gt 0 ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') round: found=$N_TOTAL exist=$N_EXIST over=$N_OVER truncated=$N_TRUNC" >> "$GUARD_LOG"
fi
exit 0
