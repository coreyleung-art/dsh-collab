#!/usr/bin/env bash
# tavily.sh — Tavily API helper（搜索/抽取），供数据调查员与子代理批量调用
# 用法:
#   tavily.sh search "查询词" [max_results] [basic|advanced] [days]
#   tavily.sh answer "问题"            # 带 AI 摘要 answer
#   tavily.sh extract "https://url"    # 抽取正文
#   tavily.sh raw search "查询词" ...  # 输出原始 JSON
# 凭据: 从 ~/.hermes/.env 读 TAVILY_API_KEY（不落盘明文）
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
DSH_LOG="$HOME/dsh-collab/logs/tavily.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

set -uo pipefail
ENVF="$HOME/.hermes/.env"
KEY=$(grep -E "^TAVILY_API_KEY=" "$ENVF" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')
[ -z "$KEY" ] && { echo "ERR: TAVILY_API_KEY 未找到"; exit 1; }

MODE="${1:-search}"; RAW=""
if [ "$MODE" = "raw" ]; then RAW=1; MODE="${2:-search}"; shift 1; fi

case "$MODE" in
  search)
    Q="${2:-}"; MAX="${3:-5}"; DEPTH="${4:-basic}"; DAYS="${5:-}"
    [ -z "$Q" ] && { echo "用法: tavily.sh search \"查询词\" [max] [basic|advanced] [days]"; exit 1; }
    BODY=$(python3 -c "
import json,sys
b={'api_key':sys.argv[1],'query':sys.argv[2],'max_results':int(sys.argv[3]),'search_depth':sys.argv[4],'include_answer':True,'include_raw_content':False}
if sys.argv[5]: b['days']=int(sys.argv[5])
print(json.dumps(b))
" "$KEY" "$Q" "$MAX" "$DEPTH" "$DAYS")
    RESP=$(curl -s --max-time 45 -X POST "https://api.tavily.com/search" -H "Content-Type: application/json" -d "$BODY")
    ;;
  answer)
    Q="${2:-}"; [ -z "$Q" ] && { echo "用法: tavily.sh answer \"问题\""; exit 1; }
    BODY=$(python3 -c "import json,sys;print(json.dumps({'api_key':sys.argv[1],'query':sys.argv[2],'max_results':5,'search_depth':'advanced','include_answer':'advanced'}))" "$KEY" "$Q")
    RESP=$(curl -s --max-time 60 -X POST "https://api.tavily.com/search" -H "Content-Type: application/json" -d "$BODY")
    ;;
  extract)
    U="${2:-}"; [ -z "$U" ] && { echo "用法: tavily.sh extract \"https://url\""; exit 1; }
    BODY=$(python3 -c "import json,sys;print(json.dumps({'api_key':sys.argv[1],'urls':[sys.argv[2]]}))" "$KEY" "$U")
    RESP=$(curl -s --max-time 60 -X POST "https://api.tavily.com/extract" -H "Content-Type: application/json" -d "$BODY")
    ;;
  *) echo "未知模式: $MODE（用 search|answer|extract）"; exit 1 ;;
esac

if [ -n "$RAW" ]; then echo "$RESP"; exit 0; fi
echo "$RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
except Exception as e:
    print('解析失败:',e); sys.exit(1)
if 'answer' in d and d.get('answer'): print('【AI摘要】', d['answer'][:600], '\n')
for r in d.get('results',[])[:10]:
    print('•', r.get('title','')[:80]); print('  ', r.get('url',''))
    c=(r.get('content') or '')[:260]
    if c: print('  ', c.replace(chr(10),' ')); print()
for it in d.get('results',[]) if 'results' in d else []:
    if 'raw_content' in it and it.get('raw_content'):
        print('【正文】', it['raw_content'][:800]); break
if not d.get('results') and 'answer' not in d:
    print('无结果 / 错误:', json.dumps(d,ensure_ascii=False)[:400])
"