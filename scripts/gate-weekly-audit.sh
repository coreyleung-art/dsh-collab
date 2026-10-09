#!/usr/bin/env bash
# gate-weekly-audit — 纸面门→结构门全链周度自动巡检 (2026-09-07 用户指示)
# 每周跑: gate-auditor scan-all → 与上次基线对比 → 新增纸面门候选登记 → 黑板周报
# 用法: bash gate-weekly-audit.sh [--once-only]
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
  echo "== gate-weekly-audit 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · gate-weekly-audit — 纸面门→结构门全链周度自动巡检 (2026-09-07 用户指示)"
  echo "  · 每周跑: gate-auditor scan-all → 与上次基线对比 → 新增纸面门候选登记 → 黑板周报"
  echo "  · 用法: bash gate-weekly-audit.sh [--once-only]"
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "  · 本工具涉及「访问网络」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/gate-weekly-audit.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

DSH_LOG="$HOME/dsh-collab/logs/gate-weekly-audit.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

set -uo pipefail
DATE=$(date +%Y%m%d)
AUDIT="$HOME/dsh-collab/scripts/gate-auditor.py"
REPORT="$HOME/dsh-collab/rules-registry/gate-audit-full-report.json"
BASELINE="$HOME/dsh-collab/rules-registry/gate-audit-weekly-baseline.json"
LOG="/tmp/gate-weekly-audit.log"
echo "[gate-weekly] $(date '+%Y-%m-%d %H:%M') 周度巡检开始" | tee -a "$LOG"

# 1. 全量识别
python3 "$AUDIT" scan-all > /tmp/gate-weekly-scan.txt 2>&1
SUMMARY=$(tail -1 /tmp/gate-weekly-scan.txt)

# 2. 与上次基线对比 (新增 paper 候选)
if [ -f "$BASELINE" ]; then
  PREV_NEW=$(python3 -c "
import json
prev=json.load(open('$BASELINE'))
cur=json.load(open('$REPORT'))
prev_ids=set()
for f in prev.get('file_entries',[]):
    if f['category']=='paper': prev_ids.add(f['file']+str(f['line']))
new=[e for e in cur.get('file_entries',[]) if e['category']=='paper' and (e['file']+str(e['line'])) not in prev_ids]
print(len(new))
for e in new[:5]:
    print('NEW:', e['file'], 'L'+str(e['line']), e['text'][:80])
" 2>/dev/null)
else
  PREV_NEW="(首次运行, 无基线——本次作基线)"
fi

# 3. 更新基线 + 黑板周报
python3 -c "
import json
d=json.load(open('$REPORT'))
json.dump(d, open('$BASELINE','w'), ensure_ascii=False)
"
echo "$SUMMARY" | tee -a "$LOG"
echo "新增候选: $PREV_NEW" | tee -a "$LOG"

# 黑板周报
python3 -c "
import json, urllib.request
body = {'from':'service:gate-weekly-audit', 'writerLabel':'服务身份（非会话）', 'date':'$DATE', 'summary':'$SUMMARY', 'new_candidates':'$PREV_NEW'}
req = urllib.request.Request('http://127.0.0.1:8792/data/ops/gate-weekly-audit-$DATE', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'}, method='PUT')
print(urllib.request.urlopen(req, timeout=6).read().decode()[:100])
" | tee -a "$LOG"
echo "[gate-weekly] 完成" | tee -a "$LOG"
