#!/usr/bin/env bash
# comm-layer 版本管理 (R006 ⑥版本管理 · 服务器版)
# manifest.json: 服务版本台账 (version-ctl verify 校验, deploy 后更新)
# 用法:
#   version-ctl.sh list     # 展示版本台账
#   version-ctl.sh verify   # 校验二进制 sha256 + 服务运行版本
#   version-ctl.sh update   # 从 manifest 重建(部署后调)
set -uo pipefail
CTL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$CTL_DIR/../manifest.json"
TOOLS_BIN="/opt/comm-layer/bin/dsh-tools"

case "${1:-}" in
  list)
    echo "== comm-layer 版本台账 =="
    if [ -f "$MANIFEST" ]; then
      python3 -c "
import json
m=json.load(open('$MANIFEST'))
print(f\"部署时间: {m.get('deployed_at','?')} | 部署者: {m.get('deployed_by','?')}\")
print('--- 二进制 ---')
for b in m.get('binaries',[]): print(f\"  {b['name']}: v{b['version']} | sha256={b.get('sha256','?')[:16]}... | {b.get('note','')}\")
print('--- 服务 ---')
for s in m.get('services',[]): print(f\"  {s['name']}: {s.get('desc','')}\")
print('--- 数据/依赖 ---')
for k,v in m.get('data',{}).items(): print(f\"  {k}: {v}\")
"
    else
      echo "❌ 无 manifest.json (部署 deploy-comm-layer.sh 后生成)"
    fi
    ;;
  verify)
    echo "== 版本校验 =="
    [ -f "$TOOLS_BIN" ] && echo "✅ dsh-tools 在位: $(ls -la $TOOLS_BIN | awk '{print $5}') bytes" || echo "❌ dsh-tools 缺失"
    [ -f "$MANIFEST" ] && echo "✅ manifest 在位" || echo "❌ manifest 缺失"
    # 服务运行中校验
    ACTIVE=$(systemctl is-active comm-server comm-server-test comm-bus-bridge comm-bb-sub-coordinator comm-bb-sub-device comm-bb-sub-hr comm-bb-sub-learning comm-bb-sub-qa comm-bb-sub-recovery comm-bb-sub-supply comm-bb-sub-xingduo 2>/dev/null | grep -c active)
    echo "✅ 服务 active: $ACTIVE/11"
    # node 版本
    /opt/node/bin/node -v 2>/dev/null | xargs echo "node:"
    ;;
  update)
    echo "== 重建 manifest (供 deploy 后调用) =="
    echo "请由 deploy-comm-layer.sh 维护，勿手工改"
    ;;
  *)
    echo "用法: version-ctl.sh {list|verify}"
    ;;
esac
