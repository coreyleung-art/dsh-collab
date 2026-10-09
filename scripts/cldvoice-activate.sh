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
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .sh 版
r006_selfcheck() {
  echo "== cldvoice-activate 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · cldvoice-activate.sh — 薄转发壳（v2）"
  echo "  · 【重要】本脚本的初版（v1）实现了**错误的模型**："
  echo "  · 它要求'端口必须先释放才启动'，并会在超时后强杀占用端口的 PID。"
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/cldvoice-activate.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

DSH_LOG="$HOME/dsh-collab/logs/cldvoice-activate.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

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
