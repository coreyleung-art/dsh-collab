#!/usr/bin/env bash
# cldvoice-activate.sh — 薄转发壳（v2）
# =============================================================================
# 【重要】本脚本的初版（v1）实现了**错误的模型**：
#   它要求"端口必须先释放才启动"，并会在超时后强杀占用端口的 PID。
#   2026-09-10 由插件自己的日志证明该模型不成立 —— 这两个服务是 KeepAlive=true，
#   SIGTERM 后 launchd 会立刻自动拉起，端口**从未空过**，于是 v1 对 voice-service
#   连续 3 次判"端口未释放"并**报假失败**（服务其实一直健康），对 cld-voice 则第 1 次
#   真失败、第 2 次才成功。根因：把"端口释放"当成了前置条件，它只是症状。
#
# 正确实现（热重启优先 + 原子重启 kickstart -k + 只验就绪 + 重试 + 自愈复核）已固化为插件：
#   ~/dsh-collab/devices/dsh-plugin-cldvoice-activate   （R006 十项达标，含 --lean4-check 自证）
#
# 保留本文件只为兼容既有调用路径：它**不再自带任何逻辑**，只转发到单一实现。
# 依据 RULES.md R035：能热重启的，就不要直接杀死整个框架。
# =============================================================================
set -uo pipefail
CLI="$HOME/dsh-collab/devices/dsh-plugin-cldvoice-activate/cli.js"
export PATH="/opt/homebrew/bin:$PATH"
if [ ! -f "$CLI" ]; then
  echo "找不到实现：$CLI（插件包缺失或被移动）" >&2
  exit 2
fi
if ! command -v node >/dev/null 2>&1; then
  echo "PATH 中无 node（本脚本需要 node 运行插件 CLI）" >&2
  exit 2
fi
exec node "$CLI" "$@"
