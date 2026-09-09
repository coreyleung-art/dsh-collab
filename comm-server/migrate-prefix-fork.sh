#!/usr/bin/env bash
# comm-server 数据迁移脚本 v1（cs2-3 · agent-network v1.3）
# 用途：扫描并迁移 api/notes/* 分叉数据 → 正确 notes/* 前缀（单一事实源）
# 安全：只迁移到目标键不存在的情况；迁移后源键保留（人工确认后归档）
set -uo pipefail

BB="${BB_URL:-http://127.0.0.1:8792}"
TOKEN="${BB_TOKEN:-bb-token-20260829-macmini}"
AUTH="Authorization: Bearer $TOKEN"

echo "==> 扫描分叉键 (api/notes/...)"
KEYS=$(curl -s -m 10 -H "$AUTH" "$BB/api/notes/" | python3 -c "
import json,sys
d=json.load(sys.stdin)
lst=d.get('list',{})
print('\n'.join(lst.keys()) if isinstance(lst,dict) else '')")

COUNT=0
for SRC in $KEYS; do
  # api/notes/<rest> → notes/<rest>
  DST="notes/${SRC#api/notes/}"
  # 跳过 data/ 等非 notes 域（那些可能本来就是对的）
  [[ "$DST" == notes/data/* || "$DST" == notes/session-* ]] && continue

  # 读源
  VAL=$(curl -s -m 5 -H "$AUTH" "$BB/$SRC" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d.get('value',{}),ensure_ascii=False))" 2>/dev/null)
  [ -z "$VAL" ] || [ "$VAL" = "{}" ] && { echo "  skip $SRC (空)"; continue; }

  # 目标已存在？跳过（避免覆盖）
  if curl -s -m 5 -H "$AUTH" "$BB/$DST" | python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('value') else 1)" 2>/dev/null; then
    echo "  ⚠️ 目标已存在，跳过: $SRC → $DST"
    continue
  fi

  echo "  迁移: $SRC → $DST"
  curl -s -m 5 -X PUT -H "$AUTH" -H "Content-Type: application/json" -d "$VAL" "$BB/$DST" >/dev/null
  echo "    回读验证: $(curl -s -m 5 -H "$AUTH" "$BB/$DST" | head -c 80)"
  COUNT=$((COUNT+1))
done

echo ""
echo "完成 ✅ 迁移 $COUNT 键。源键保留在 api/notes/（人工确认后 DELETE 归档）"
echo "验证: 扫描 api/notes/ 应无 notes 域新键"
