#!/usr/bin/env bash
# gate-weekly-audit — 纸面门→结构门全链周度自动巡检 (2026-09-07 用户指示)
# 每周跑: gate-auditor scan-all → 与上次基线对比 → 新增纸面门候选登记 → 黑板周报
# 用法: bash gate-weekly-audit.sh [--once-only]
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
body = {'from':'gate-weekly-audit', 'date':'$DATE', 'summary':'$SUMMARY', 'new_candidates':'$PREV_NEW'}
req = urllib.request.Request('http://127.0.0.1:8792/data/ops/gate-weekly-audit-$DATE', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'}, method='PUT')
print(urllib.request.urlopen(req, timeout=6).read().decode()[:100])
" | tee -a "$LOG"
echo "[gate-weekly] 完成" | tee -a "$LOG"
