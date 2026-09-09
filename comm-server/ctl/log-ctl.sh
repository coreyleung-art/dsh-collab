#!/usr/bin/env bash
# comm-layer 日志管理入口 (R006 ⑦统一日志 · 服务器版)
# 用法:
#   log-ctl.sh list                  # 列出全部服务
#   log-ctl.sh tail [service] [行数] # 实时跟踪(默认 coordinator)
#   log-ctl.sh err [service] [行数]  # 过滤错误/异常
#   log-ctl.sh since <服务> <分钟>   # 最近 N 分钟日志
#   log-ctl.sh size                  # journald 磁盘占用
set -uo pipefail
SERVICES="comm-server comm-server-test comm-bus-bridge comm-bb-sub-coordinator comm-bb-sub-device comm-bb-sub-hr comm-bb-sub-learning comm-bb-sub-qa comm-bb-sub-recovery comm-bb-sub-supply comm-bb-sub-xingduo"

case "${1:-}" in
  list)
    echo "== comm-layer 服务清单 =="
    for s in $SERVICES; do echo "  $s"; done
    ;;
  tail)
    SVC="${2:-comm-bb-sub-coordinator}"; N="${3:-15}"
    echo "== $SVC 最近 $N 行 =="
    sudo journalctl -u "$SVC" --no-pager -n "$N" 2>/dev/null || echo "❌ 服务不存在: $SVC"
    ;;
  err)
    SVC="${2:-comm-bb-sub-coordinator}"; N="${3:-10}"
    echo "== $SVC 错误过滤(最近 $N 条) =="
    sudo journalctl -u "$SVC" --no-pager -n 200 2>/dev/null | grep -iE "error|fail|panic|❌|异常|拒绝|denied|unable" | tail -"$N" || echo "无错误匹配"
    ;;
  since)
    SVC="${2:-comm-bb-sub-coordinator}"; MIN="${3:-10}"
    echo "== $SVC 最近 ${MIN} 分钟 =="
    sudo journalctl -u "$SVC" --since "${MIN} min ago" --no-pager 2>/dev/null | tail -30
    ;;
  size)
    echo "== journald 磁盘占用 =="
    journalctl --disk-usage 2>/dev/null
    ;;
  *)
    echo "用法: log-ctl.sh {list|tail|err|since|size} [service] [行数/分钟]"
    echo "服务: comm-server / comm-server-test / comm-bus-bridge / comm-bb-sub-{coordinator,device,hr,learning,qa,recovery,supply,xingduo}"
    ;;
esac
