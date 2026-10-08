#!/bin/bash
# PSTD 1.0.4 生效判据 F1/F2/F3 复测（先测触发条件 F2，再谈 F1）
set -u
echo "MEASURED_AT=$(date '+%Y-%m-%dT%H:%M:%S%z') epoch=$(date +%s)"
echo "--- [1] 本机 boot 时刻 ---"
sysctl -n kern.boottime
echo "--- [2] 承载 dsh runtime 的进程（锚点：CLD 主进程 + dsh web 子进程）---"
ps -eo pid,ppid,lstart,command 2>/dev/null | grep -E "CLD\.app|dsh/lib/bin\.js" | grep -v grep
echo "--- [3] 被审文件 mtime / size ---"
stat -f '%Sm %z %N' -t '%Y-%m-%dT%H:%M:%S' "$HOME/dsh-plugin-pstd/lib/review.js" "$HOME/dsh-plugin-pstd/package.json" 2>&1
echo "--- [4] 磁盘版本声明（F3 的一半）---"
python3 -c "import json,os;p=os.path.expanduser('~/dsh-plugin-pstd/package.json');d=json.load(open(p));print('version =',d.get('version'));print('name =',d.get('name'));print('mtime_via_json_read_ok')" 2>&1
echo "--- [5] 判据触发条件判定 ---"
python3 - <<'PY'
import subprocess,os,datetime,re
boot=subprocess.run(['sysctl','-n','kern.boottime'],capture_output=True,text=True).stdout
m=re.search(r'sec = (\d+)',boot)
bootsec=int(m.group(1)) if m else 0
mt=os.path.getmtime(os.path.expanduser('~/dsh-plugin-pstd/lib/review.js'))
print('boot_sec   =',bootsec, datetime.datetime.fromtimestamp(bootsec).strftime('%Y-%m-%dT%H:%M:%S'))
print('review_mtime=',int(mt), datetime.datetime.fromtimestamp(mt).strftime('%Y-%m-%dT%H:%M:%S'))
print('F2_triggers(boot > mtime) =', bootsec>mt)
if bootsec>mt:
    print('=> F1 适用：此时若 std != PSTD/1.0.4 则为异常（非“未生效”）')
else:
    print('=> F1 **不适用**：未见晚于 review.js mtime 的重启，std=1.0.3 属“改动未加载”的预期态')
PY
