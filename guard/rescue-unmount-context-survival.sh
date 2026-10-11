#!/usr/bin/env bash
# ============================================================================
# 救援件：卸载 dsh-plugin-context-survival
# ----------------------------------------------------------------------------
# 用途：若挂载该插件后 CLD 起不来（插件树 fail-fast ⇒ 无法打开任何会话，
#       也就无法叫 agent 来修），用户在**终端**直接执行本脚本即可回滚。
#
# 用法：
#   bash ~/dsh-collab/guard/rescue-unmount-context-survival.sh --dry-run   # 只打印将做什么
#   bash ~/dsh-collab/guard/rescue-unmount-context-survival.sh             # 真正执行
#
# ★ 没有 --dry-run 就会**真的卸载**。先跑 --dry-run 看清楚再决定。
#
# 做三件事：恢复挂载前的 profile 备份 + 删掉 profile 侧的包名链接
#           + 删掉插件目录下的 peer 链接目录。
# 不重启任何东西；执行完由用户自行启动 CLD。可反复执行（幂等）。
# ============================================================================
set -e

DRY=""
case "${1:-}" in
  --dry-run|-n) DRY=1 ;;
  "") ;;
  -h|--help) echo "用法：bash $0 [--dry-run]"; exit 0 ;;
  *) echo "未知参数：$1（仅支持 --dry-run / -n）" >&2; exit 2 ;;
esac

PROFILE="$HOME/.dsh/profiles/web/package.json"
BACKUP_DIR="$HOME/dsh-collab/guard/backups"
PROFILE_LINK="$HOME/.dsh/profiles/web/node_modules/dsh-plugin-context-survival"
PLUGIN_NM="$HOME/dsh-collab/devices/dsh-plugin-context-survival/node_modules"

# ★ 意外中止必须**出声**：这道 trap 专治「脚本静默停在中途、用户以为跑完了」。
trap 'rc=$?; echo "★★ 脚本意外中止（exit $rc）—— 上方最后一条输出即失败点，请人工检查。" >&2' ERR

if [ -n "$DRY" ]; then
  echo "== 救援卸载：dsh-plugin-context-survival（★ DRY-RUN：不会改动任何文件）=="
else
  echo "== 救援卸载：dsh-plugin-context-survival =="
fi

echo "[1/6] 在 $BACKUP_DIR 查找最新的 profile 备份…"
LATEST="$(ls -t "$BACKUP_DIR"/profile-package.json.before-mount-* 2>/dev/null | head -1 || true)"
if [ -z "$LATEST" ]; then
  echo "★★ 错误：找不到任何备份（$BACKUP_DIR/profile-package.json.before-mount-*）" >&2
  echo "★★ 无法自动恢复，未做任何改动。请人工检查 $PROFILE" >&2
  exit 1
fi
echo "      使用备份：$LATEST"

echo "[2/6] 恢复 profile…"
if [ -n "$DRY" ]; then
  echo "      [dry-run] 将执行：cp '$LATEST' '$PROFILE'"
else
  cp "$LATEST" "$PROFILE"
  echo "      已写入：$PROFILE"
fi

echo "[3/6] 校验 JSON…"
# dry-run 时 profile 尚未改动 ⇒ 校验**备份文件**（这才是有意义的预检）
if [ -n "$DRY" ]; then
  CHECK="$LATEST"
  echo "      [dry-run] 校验备份文件本身（当前 profile 未被改动）"
else
  CHECK="$PROFILE"
fi
if ! PROFILE="$CHECK" node -e "JSON.parse(require('fs').readFileSync(process.env.PROFILE,'utf8'))"; then
  echo "★★ 错误：$CHECK 不是合法 JSON —— 已停下，未做其它改动。" >&2
  echo "★★ 请人工检查 $PROFILE" >&2
  exit 1
fi
echo "      JSON OK"

echo "[4/6] 删除 profile 侧的包名链接…"
if [ -n "$DRY" ]; then
  echo "      [dry-run] 将执行：rm -f '$PROFILE_LINK'"
elif rm -f "$PROFILE_LINK"; then
  echo "      已删除：$PROFILE_LINK"
else
  echo "      ★★ 删除失败（rm 返回非零）：$PROFILE_LINK —— 请人工检查权限。" >&2
fi

echo "[5/6] 删除插件目录下的 peer 链接目录（本次由挂载任务新建）…"
# ★ 失败不静默、也不中止：让 [6/6] 如实报出真实状态（此前这一步静默吞掉过 fail）
if [ -n "$DRY" ]; then
  echo "      [dry-run] 将执行：rm -rf '$PLUGIN_NM'"
elif rm -rf "$PLUGIN_NM"; then
  echo "      已删除：$PLUGIN_NM"
else
  echo "      ★★ 删除失败（rm 返回非零）：$PLUGIN_NM" >&2
  echo "      ★★ 常见原因：权限不足 / 目录内有文件被占用。请人工检查。" >&2
fi

echo "[6/6] 确认卸载结果…"
if [ -n "$DRY" ]; then
  echo "      [dry-run] 未改动任何文件；以下是【当前】状态（不是卸载后的状态）"
fi
COUNT="$(grep -c "context-survival" "$PROFILE" || true)"
echo "      profile 中 context-survival 出现次数：${COUNT:-0}（期望 0）"
if [ -e "$PROFILE_LINK" ]; then
  echo "      profile 侧链接：仍存在 ★（应已删除）"
else
  echo "      profile 侧链接：已移除 ✅"
fi
if [ -e "$PLUGIN_NM" ]; then
  echo "      插件 peer 目录：仍存在 ★（应已删除）"
else
  echo "      插件 peer 目录：已移除 ✅"
fi

if [ -n "$DRY" ]; then
  echo "【dry-run 结束：未做任何改动。去掉 --dry-run 才会真正卸载】"
else
  echo "【已卸载 dsh-plugin-context-survival，CLD 应可正常启动】"
fi
