#!/usr/bin/env bash
# artifact-commit.sh v1.0.2 — 「唯一副本止损」的【持续化机制】
# 起因（2026-10-09 裁判节点② 复核指出）：一次性 `git add -f` 不是机制 ——
#   「唯一副本止损是持续动作、不是一次动作」。
# 用法：artifact-commit.sh <路径...> -m "说明"
#   白名单外路径自动 -f；无改动则静默退出 0（幂等）；已跟踪文件直接 add。
set -uo pipefail    # ★ v1.0.2：去掉 -e —— git add 遇 ignored 路径返回 1，会让脚本在 commit 前退出（实测根因）
cd "$(dirname "$0")/.."
MSG=""; PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in -m) MSG="$2"; shift 2;; *) PATHS+=("$1"); shift;; esac
done
[ ${#PATHS[@]} -gt 0 ] || { echo "用法: artifact-commit.sh <路径...> -m 说明" >&2; exit 2; }
[ -n "$MSG" ] || { echo "必须给 -m 说明" >&2; exit 2; }
changed=0
for p in "${PATHS[@]}"; do
  [ -e "$p" ] || { echo "跳过（不存在）: $p" >&2; continue; }
  # ★ v1.0.1 修：原判据用 `git ls-files --error-unmatch`，对【已跟踪但被 .gitignore 覆盖】
  #   的路径会误判 ⇒ `git add` 报 ignored 而失败（实测：research/ 白名单外）。
  #   正解：直接问 git「这个路径是否被忽略」⇒ 被忽略就 -f。
  # ★ v1.0.2：add 一律 -f 且【吞掉返回码】—— 已跟踪文件加 -f 无副作用；
  #   未跟踪且被 ignore ⇒ -f 是唯一能纳入的方式；git 的 ignored 提示只是警告。
  git add -f "$p" 2>/dev/null || true
  changed=1
done
if git diff --cached --quiet; then echo "无改动（幂等退出）"; exit 0; fi
git commit -q -m "$MSG"
echo "已提交 $(git rev-parse --short HEAD) · 文件: ${PATHS[*]}"
