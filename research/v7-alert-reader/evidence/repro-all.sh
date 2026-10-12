#!/bin/bash
# repro-all.sh — R2（告警读者）调研的【全部复跑命令】
# 用法: bash repro-all.sh           # 打印每条命令的原始输出与退出码
# 纪律: 只读；不对黑板做任何 PUT/POST/DELETE
EV=~/dsh-collab/research/v7-alert-reader/evidence
run(){ echo; echo "################ CMD: $*"; "$@"; echo "[exit=$?]"; }
run2(){ echo; echo "################ CMD(sh): $1"; bash -c "$1"; echo "[exit=$?]"; }

echo "===== 抓取时刻 ====="; date "+%Y-%m-%dT%H:%M:%S%z"; hostname

run2 'curl -s -m 30 "http://127.0.0.1:8792/data/ops/" -o /tmp/bb-ops.json && ls -la /tmp/bb-ops.json'
run python3 ~/dsh-collab/research/v7-alert-reader/evidence/repro-census.py

run2 'grep -c "" ~/dsh-collab/logs/drift-scan.log'
run2 'grep -c "CLEAN" ~/dsh-collab/logs/drift-scan.log'
run2 'grep -c "DRIFT" ~/dsh-collab/logs/drift-scan.log'
run2 'grep -c "\"result\"" ~/dsh-collab/logs/drift-scan.log'          # 阳性对照
run2 'grep -c "ZZZ_NONEXISTENT" ~/dsh-collab/logs/drift-scan.log'     # 阴性对照
run2 'grep -c "\"check\"" ~/dsh-collab/logs/drift-scan.log'           # 逐项记录是否存在

run python3 ~/dsh-collab/tools/beacon-check.py --net
run python3 ~/dsh-collab/tools/beacon-check.py --selftest
run python3 ~/dsh-collab/research/v7-alert-reader/evidence/negctl-alert-reader.py
run python3 ~/dsh-collab/research/v7-alert-reader/evidence/repro-readers.py

run2 'tail -20 /tmp/gate-weekly-audit.err'
run2 'tail -10 /tmp/gate-weekly-audit.log'
run2 'ls -la /tmp/gate-weekly-audit.log /tmp/gate-weekly-audit.err'
