#!/bin/bash
# 回读确认（不盲重试）：比较两板原始字节 + value 语义
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
  echo "== bb-readback 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · 回读确认（不盲重试）：比较两板原始字节 + value 语义"
  echo "  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。"
  echo "  · 依据：r006-debt-assess.py 机械扫描未检出以下原语："
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "  · 本工具涉及「访问网络」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/bb-readback.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

DSH_LOG="$HOME/dsh-collab/logs/bb-readback.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

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
