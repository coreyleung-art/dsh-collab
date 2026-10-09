#!/bin/bash
# 回读确认（不盲重试）：比较两板原始字节 + value 语义
set -u
K="$1"
echo "READBACK_AT=$(date '+%Y-%m-%dT%H:%M:%S%z')  KEY=$K"
for BASE in "http://127.0.0.1:8792" "http://106.53.214.108:8792"; do
  TAG=$(echo "$BASE" | tr -d ':/.' )
  OUT=/tmp/rb_$TAG.json
  code=$(curl -s -m 25 -o "$OUT" -w '%{http_code}' "$BASE/$K")
  echo "  $BASE http=$code bytes=$(wc -c <"$OUT" | tr -d ' ') sha=$(shasum -a 256 "$OUT" | cut -c1-16)"
done
L=/tmp/rb_http1270018792.json; C=/tmp/rb_http106532141088792.json
if [ -f "$L" ] && [ -f "$C" ]; then
  echo "  byte_identical = $([ "$(shasum -a 256 $L|cut -d' ' -f1)" = "$(shasum -a 256 $C|cut -d' ' -f1)" ] && echo True || echo False)"
fi
python3 - "$L" "$C" <<'PY'
import json,sys,hashlib
try:
    a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
except Exception as e:
    print("  PARSE_FAIL", e); raise SystemExit
print("  local  ts=",a.get('ts'),"version=",a.get('version'))
print("  centrl ts=",b.get('ts'),"version=",b.get('version'))
va,vb=a.get('value'),b.get('value')
sa=hashlib.sha256(json.dumps(va,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
sb=hashlib.sha256(json.dumps(vb,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
print("  value_semantic_equal =", sa==sb, "| sha:", sa, sb)
# 保留顺序的原始串比较（排除顺序类假设）
print("  value_raw_equal      =", json.dumps(va,ensure_ascii=False)==json.dumps(vb,ensure_ascii=False))
if isinstance(va,dict):
    print("  from =", va.get('from'), "| from_label =", va.get('from_label'))
    print("  subject =", str(va.get('subject'))[:70])
    print("  keys =", len(va.keys()))
PY
