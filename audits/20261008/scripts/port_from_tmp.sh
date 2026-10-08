#!/bin/bash
# 把本会话的审计复现件从 /tmp 移植到耐久路径（整改：验证手段不得依赖会被清理的载体）
set -u
DST="$HOME/dsh-collab/audits/20261008/scripts"
mkdir -p "$DST"
FILES="audit_rb.sh audit_writer_stat.py audit_horizon_probe.py audit_snapshot_timing_probe.py audit_consistency_probe.py audit_card_provenance.py audit_baserate_probe.py audit_tsdelta_probe.py audit_author12_verify.py audit_author12_read.py audit_idx_verify.py audit_idx_verify2.py audit_idx_verify3.py audit_pstd_f1.sh audit_dvminus1_probe.py audit_v2pure_and_dv.py audit_v2pure_fix.py"
echo "=== 移植 ==="
n=0
for f in $FILES; do
  if [ -f "/tmp/$f" ]; then
    cp "/tmp/$f" "$DST/$f"
    n=$((n+1))
    echo "  OK  $f"
  else
    echo "  MISS $f"
  fi
done
echo "共移植 $n 个"
echo
echo "=== 目标目录 ==="
ls -la "$DST"
echo
echo "=== 耐久路径下试跑（不依赖 /tmp）==="
python3 "$DST/audit_fork_offset_and_auth.py" 2>&1
