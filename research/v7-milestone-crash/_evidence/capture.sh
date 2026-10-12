#!/usr/bin/env bash
# capture.sh — v7 里程碑与崩溃复发 调研基线捕获（只读；不改任何既有文件）
# 用法: bash research/v7-milestone-crash/_evidence/capture.sh 2>&1 | tee out.txt
# 纪律: 每条先打【命令逐字】，再打【未编辑输出】，再打【exit=N】
set -u
cd "$HOME/dsh-collab" || exit 9
R() { echo "----- [$1] $2"; }
EX() { echo "exit=$?"; }

echo "############ capture 时刻 ############"
R T0 'date "+%Y-%m-%dT%H:%M:%S%z"'; date "+%Y-%m-%dT%H:%M:%S%z"; EX

echo
echo "############ 一 · M0 · C4 自启动注入 ############"
R M0-a "grep -n 'C4 自启动注入' docs/execution-audit-anchor-v5-20261010.md"
grep -n 'C4 自启动注入' docs/execution-audit-anchor-v5-20261010.md; EX
R M0-b "ls -d ~/.dsh/.agent-presets/*/ | wc -l"
ls -d ~/.dsh/.agent-presets/*/ 2>/dev/null | wc -l; EX
R M0-c "grep -rl 'continuity-index' ~/.dsh/.agent-presets/ | wc -l"
grep -rl 'continuity-index' ~/.dsh/.agent-presets/ 2>/dev/null | wc -l; EX
R M0-d "wc -l docs/resume-prompt-starbridge-v3.md"
wc -l docs/resume-prompt-starbridge-v3.md; EX

echo
echo "############ 二 · M1 · compaction/体积/事件数/verifier ############"
R M1-a "ls -l tools/sandbox-script.py tools/infopack-check.py tools/review-gate.py tools/official-ref-gate.py tools/gcr-gate.py tools/node-claim-gate.py tools/self-destruct-gate.py"
ls -l tools/sandbox-script.py tools/infopack-check.py tools/review-gate.py tools/official-ref-gate.py tools/gcr-gate.py tools/node-claim-gate.py tools/self-destruct-gate.py 2>&1; EX
R M1-b "du -sm ~/.dsh/sessions/--Users-coreyleung--/* | sort -rn | head -3"
du -sm ~/.dsh/sessions/--Users-coreyleung--/* 2>/dev/null | sort -rn | head -3; EX
R M1-c "grep -c EnableCompaction ~/.dsh/settings.yaml (未命中即为 0)"
grep -c 'EnableCompaction\|compaction' ~/.dsh/settings.yaml 2>/dev/null; EX
R M1-d "grep -n 'compaction' ~/.dsh/profiles/web/node_modules/dsh-plugin-context-survival/cordis.patch.yml"
grep -n 'compaction\|enableGuard' ~/.dsh/profiles/web/node_modules/dsh-plugin-context-survival/cordis.patch.yml 2>&1; EX

echo
echo "############ 三 · M2 · 真积压 / 端口固定 ############"
R M2-a "agent-bus.json 全量终态分布"
python3 - <<'PY'
import json,os,collections
p=os.path.expanduser('~/.dsh/agent-bus.json')
d=json.load(open(p))
th=d.get('threads') or []
c=collections.Counter(); n=0
for t in th:
    for m in (t.get('messages') or []):
        c[m.get('status')]+=1; n+=1
print("threads:",len(th),"messages:",n)
print("status:",c.most_common())
print("size_bytes:",os.path.getsize(p))
PY
EX
R M2-b "web 端口（现测） + CLD_PORT"
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E '^CLD' ; echo "--- CLD_PORT:"; launchctl getenv CLD_PORT; echo "(空=未设)"; EX
R M2-c "grep CLD_PORT / 历史端口记录"
grep -c 'port 0' ~/.cld/logs/dsh-web.log 2>/dev/null; EX

echo
echo "############ 四 · M3 · 订阅唤醒 / 载体 / 黑板 GC ############"
R M3-a "subscriptions.json 首订阅者"
python3 -c "
import json;d=json.load(open('subscriptions.json'))
es=d.get('event_subscriptions',[])
print('event_subscriptions 数:',len(es))
print('首订阅者:',es[0]['agent'] if es else None)
print('topics:',es[0]['topics'] if es else None)
print('updated:',d.get('updated'))"
EX
R M3-b "grep -c fa1f9150 ~/.dsh/agent-role-map.json"
grep -c 'fa1f9150' ~/.dsh/agent-role-map.json; EX
R M3-c "python3 scripts/event-bus.py --status | head -3"
python3 scripts/event-bus.py --status 2>&1 | head -3; EX
R M3-d "黑板 DELETE 计数（命名空间列举）"
curl -s --max-time 8 http://127.0.0.1:8792/data/ | python3 -c "
import sys,json
d=json.load(sys.stdin); print('data/ 键数:',len(d.get('list',{})))"; EX

echo
echo "############ 五 · 25 类坑 / G-CR 门 ############"
R M4-a "P1–P25 逐条 id（§7.1–7.7）"
grep -oE '^\| \*?\*?P[0-9]+' docs/distributed-agent-network-governance-plan-v6.1-20261011.md | grep -oE 'P[0-9]+' | sort -u -V | tr '\n' ' '; echo; EX
R M4-b "P 类 id 计数"
grep -oE '^\| \*?\*?P[0-9]+' docs/distributed-agent-network-governance-plan-v6.1-20261011.md | grep -oE 'P[0-9]+' | sort -u -V | wc -l; EX
R M4-c "python3 tools/gcr-gate.py（★ 完整输出见下）"
python3 tools/gcr-gate.py > /tmp/_gcr.log 2>&1; _rc=$?
cat /tmp/_gcr.log; echo "exit=$_rc"; EX
R M4-d "grep -c G-CR18 tools/gcr-gate.py"
grep -c 'G-CR18' tools/gcr-gate.py; EX
R M4-e "gcr-gate 里 N-A 条数"
python3 tools/gcr-gate.py 2>&1 | grep -c '^⚠️'; EX
R M4-f "gcr-gate 汇总行"
python3 tools/gcr-gate.py 2>&1 | grep '汇总'; EX

echo
echo "############ 六 · 已有回归语料（本仓先例）############"
R M5-a "python3 tools/incident-regression.py（★ 见下方汇总）"
# ★ 首版在此处写成 `python3 … | tail -20; EX` —— 管道把 $? 换成了 tail 的 0，
#   真值 1 被显示成「exit=0」⇒ **本脚本自己复现了 INC-04**（退出码经管道被静默替换）。
#   修法：先落文件、再取退出码、最后打印。
python3 tools/incident-regression.py > /tmp/_inc.log 2>&1; _rc=$?
tail -20 /tmp/_inc.log; echo "exit=$_rc"   # ★ 真实退出码（不经管道）
R M5-b "INC 用例条数"
python3 -c "
import re
s=open('tools/incident-regression.py',encoding='utf-8').read()
print(len(re.findall(r'\"id\":\s*\"INC-\d+\"',s)))"; EX
R M5-c "python3 scripts/pitfalls-cli.py list（★ 取真实退出码，不经管道）"
python3 scripts/pitfalls-cli.py list > /tmp/_pf.log 2>&1; _rc=$?
tail -6 /tmp/_pf.log; echo "exit=$_rc"; EX
R M5-d "踩坑档案条数"
python3 -c "
import json;d=json.load(open('docs/pitfalls/pitfalls.json'))
print('items:',len(d.get('items',[])),'pitfalls:',len(d.get('pitfalls',[])),'version:',d.get('version'))"; EX

echo
echo "############ 七 · P26 ############"
R P26-a "cordis.patch.yml enableGuard"
grep -n 'enableGuard' ~/.dsh/profiles/web/node_modules/dsh-plugin-context-survival/cordis.patch.yml; EX
R P26-b "package.json 与 lib/index.js 的自述（文档面）"
grep -n '开关仍关\|enableGuard: false\|enableGuard=false' devices/dsh-plugin-context-survival/package.json devices/dsh-plugin-context-survival/lib/index.js 2>/dev/null | head -5; EX
R P26-c "csx_status.guard（活体读数）—— 见调用工具 csx_status 的输出"

echo
echo "############ 八 · P27 ############"
R P27-a "python3 tools/beacon-check.py --net"
python3 tools/beacon-check.py --net 2>&1; EX
R P27-b "beacon-check --net 的退出码（单测）"
python3 tools/beacon-check.py --net >/dev/null 2>&1; echo "raw_exit=$?"; EX

echo
echo "############ 九 · P28 ############"
R P28-a "channel_gate 台账 vs status：两来源"
echo "--- logs/channel-changes.jsonl 条数 / 各通道最新 ---"
python3 - <<'PY'
import json,collections,os
p=os.path.expanduser('~/dsh-collab/logs/channel-changes.jsonl')
rows=[json.loads(l) for l in open(p,encoding='utf-8',errors='replace') if l.strip()]
print("jsonl 总条数:",len(rows))
print("按通道:",collections.Counter(r['channel'] for r in rows).most_common())
last={}
for r in rows:
    if r['channel'] not in last or r['at']>last[r['channel']]: last[r['channel']]=r['at']
for k,v in sorted(last.items()): print(f"  {k:20s} 最新 {v}")
PY
EX
R P28-b "logs/channel-gate-state.json"
cat logs/channel-gate-state.json 2>&1; echo; EX
R P28-c "channel_gate status 自报 changes24h（见调用工具输出）"
R P28-d "reply_required 读端命中数"
grep -rn 'reply_required' ~/dsh-plugin-agent-bus/lib/index.js 2>/dev/null | wc -l; EX
R P28-e "awaiting 消费者：plist 命中数"
grep -rl 'awaiting' ~/Library/LaunchAgents/ 2>/dev/null | wc -l; EX

echo
echo "############ 十 · P29 ############"
R P29-a "假绿一 C7 分母（现测）"
D=~/.dsh/profiles/web/node_modules/@deepseek-ai
echo "总=$(ls "$D" 2>/dev/null|wc -l) 跳过1=$(ls "$D" 2>/dev/null|grep -cE '\.(bak|pnpmcopy)') 跳过2软链=$(find "$D" -maxdepth 1 -type l 2>/dev/null|wc -l)"; EX
R P29-b "假绿二 drift cron 两个 fd"
grep -o 'PUT 200' /tmp/drift-scan-cron.log 2>/dev/null | wc -l
grep -o '401' /tmp/drift-scan-cron.err.log 2>/dev/null | wc -l
stat -f '%N mtime=%Sm' -t '%F %T' /tmp/drift-scan-cron.log /tmp/drift-scan-cron.err.log 2>&1; EX
R P29-c "假绿三 计数器（★ 用 -o 勿用 -c）"
grep -oh '自动重启 [0-9]/[0-9]' ~/dsh-collab/logs/node-bridge.log* 2>/dev/null | sort | uniq -c; EX
R P29-d "假绿三 扫过的面（行数）"
wc -l ~/dsh-collab/logs/node-bridge.log* 2>/dev/null; EX
R P29-e "假绿四 /health 空壳 vs 真健康数据"
for p in health stats version; do printf '%-8s -> ' "$p"; curl -s --max-time 5 "http://127.0.0.1:8792/$p" | head -c 80; echo; done
curl -s --max-time 8 http://127.0.0.1:8792/data/ | python3 -c "
import sys,json;d=json.load(sys.stdin);ks=list(d.get('list',{}))
print('data/ 键数:',len(ks))
print('含 health 的键:',len([k for k in ks if 'health' in k.lower()]))
print(\"endswith('/health'):\",len([k for k in ks if k.endswith('/health')]))"; EX
R P29-f "假绿五 检查项穷举"
grep -n 'out.checks\.' ~/dsh-plugin-guard/lib/index.js 2>/dev/null; EX
R P29-g "假绿五 C8_comm/C9 是否新增"
grep -c 'C8_comm\|C9_' ~/dsh-plugin-guard/lib/index.js; EX

echo
echo "############ 十一 · 现测漂移/健康 ############"
R X-a "drift_scan --json"
/opt/homebrew/bin/node ~/dsh-plugin-drift-scan/cli.js --json 2>&1; EX
R X-b "双板 drift-alert 到达率"
for u in http://127.0.0.1:8792 http://106.53.214.108:8792; do
  printf "%s -> " "$u"
  curl -s --max-time 10 "$u/data/ops/drift-alert/" | python3 -c "import sys,json;print('total=',json.load(sys.stdin).get('total'))" 2>&1 || echo unreachable
done; EX
R X-c "bb-card-send 双板到达率"
python3 - <<'PY'
import json,collections,os
p=os.path.expanduser('~/dsh-collab/logs/bb-card-send.log')
rows=[json.loads(l) for l in open(p,encoding='utf-8',errors='replace') if l.strip()]
s=[r for r in rows if r.get('action')=='send' and 'result' in r]
print("分母:",len(s))
print(collections.Counter(r.get('result') for r in s).most_common())
if s:
    m=sum(1 for r in s if r.get('boardsMatch') is True)
    print(f"双板到达且一致率 = {m}/{len(s)} = {m/len(s)*100:.2f}%")
else:
    print("分母为 0 ⇒ 不可判（不得报 OK）")
PY
EX
R X-d "launchctl 失败终态 com.dsh.*"
launchctl list 2>/dev/null | awk '$1=="-" && $2!=0 {print}' | grep 'com.dsh' ; echo "--- exit-非0 的 com.dsh:"; launchctl list 2>/dev/null | awk '$2!="0" && $1!="PID" && $3 ~ /^com\.dsh/ {print $2, $3}'; EX
R X-e "会话目录体积"
du -sm ~/.dsh/sessions/--Users-coreyleung-- 2>/dev/null; EX

echo
echo "############ 十一 · P26 复发谓词（全量会话扫描，报扫过的面）############"
R P26-d "全量会话 JSONL 扫两个签名"
python3 - <<'EOF'
import zstandard, os, io, glob
base=os.path.expanduser('~/.dsh/sessions')
sigs=["CONTEXT_WINDOW_EXCEEDED","summary is not smaller than the shadowed content"]
hits={s:set() for s in sigs}
skipped=[]; errs=[]; lines=0
files=glob.glob(base+'/*/*/session.jsonl*')
print("扫描面: 会话文件数 =",len(files), "（上限 60MB/文件）")
for p in files:
    sz=os.path.getsize(p)
    if sz>60*1024*1024: skipped.append((p,sz)); continue
    try:
        dctx=zstandard.ZstdDecompressor()
        with open(p,'rb') as fh, dctx.stream_reader(fh) as r:
            t=io.TextIOWrapper(r,encoding='utf-8',errors='replace')
            for line in t:
                lines+=1
                for s in sigs:
                    if s in line: hits[s].add(p)
    except Exception as e: errs.append((p,str(e)[:50]))
print("扫过的行数:",lines)
for s in sigs:
    print(f"  {s!r}: 涉及会话 {len(hits[s])}")
print("  ★ 未扫的面（>60MB 被跳过，必须报，不得当 0）:",len(skipped))
for p,sz in skipped: print("     ",os.path.basename(os.path.dirname(p)),round(sz/1048576,1),"MB")
print("  读取错误:",len(errs))
EOF
EX

echo
echo "############ 十二 · M2③ 端口固定的真规模 ############"
R P-a "dsh-web.log 内出现过的本机端口集合大小"
grep -oE 'http://127\.0\.0\.1:[0-9]+' ~/.cld/logs/dsh-web.log 2>/dev/null | sort -u | wc -l; EX
R P-b "并集里非 31888 的个数（31888=reload 端口，固定）"
grep -oE 'http://127\.0\.0\.1:[0-9]+' ~/.cld/logs/dsh-web.log 2>/dev/null | sort -u | grep -vc ':31888$'; EX
R P-c "该日志文件自身的 mtime/size（扫过的面）"
stat -f 'mtime=%Sm size=%z' -t '%F %T' ~/.cld/logs/dsh-web.log; EX
R P-d "CLD_PORT 是否设置"
launchctl getenv CLD_PORT; echo "(空行=未设置)"; EX

echo
echo "############ capture 完成 ############"
date "+%Y-%m-%dT%H:%M:%S%z"
