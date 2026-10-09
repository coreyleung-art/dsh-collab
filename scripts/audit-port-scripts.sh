#!/bin/bash
# 审计复现件整理（三件事）：
#  ① 校验「耐久副本」与 /tmp 原件是否同一内容（sha256）
#  ② 通用件移入共享目录 ~/dsh-collab/scripts/ 并改为 kebab-case（与该目录既有命名一致）
#  ③ 清空 /tmp/audit_*，避免两份分叉
set -u
ARCH="$HOME/dsh-collab/audits/20261008/scripts"
SHARED="$HOME/dsh-collab/scripts"

echo "=== ① sha256 校验：耐久副本 vs /tmp 原件 ==="
for f in audit_consistency_probe.py audit_card_provenance.py audit_horizon_probe.py audit_baserate_probe.py audit_writer_stat.py audit_rb.sh; do
  a=$( [ -f "$ARCH/$f" ] && shasum -a 256 "$ARCH/$f" | cut -c1-16 || echo "MISSING" )
  b=$( [ -f "/tmp/$f" ] && shasum -a 256 "/tmp/$f" | cut -c1-16 || echo "MISSING" )
  same=$([ "$a" = "$b" ] && echo "同一内容 ✅" || echo "内容不同 ⚠")
  printf "  %-34s arch=%s tmp=%s  %s\n" "$f" "$a" "$b" "$same"
done

echo
echo "=== ② 通用件移入共享目录并重命名（kebab-case）==="
port() {
  src="$ARCH/$1"; dst="$SHARED/$2"
  if [ -f "$src" ]; then
    if [ -f "$dst" ]; then echo "  SKIP $2（目标已存在，不覆盖）"; else cp "$src" "$dst"; echo "  OK   $1 -> $2"; fi
  else
    echo "  MISS $1"
  fi
}
port audit_consistency_probe.py   bb-cross-board-consistency.py
port audit_card_provenance.py     bb-card-provenance.py
port audit_horizon_probe.py       bb-retention-horizon.py
port audit_snapshot_timing_probe.py bb-snapshot-timing.py
port audit_baserate_probe.py      bb-baserate-probe.py
port audit_writer_stat.py         bb-writer-census.py
port audit_fork_offset_and_auth.py bb-fork-offset-and-auth.py
port audit_probe_cleanup.py       bb-probe-cleanup.py
port audit_rb.sh                  bb-readback.sh
port audit_pstd_f1.sh             pstd-f1-check.sh

echo
echo "=== ③ 清理 /tmp/audit_*（避免两份分叉）==="
ls /tmp/audit_* 2>/dev/null | wc -l | tr -d ' ' | sed 's/^/  待清理数量: /'
rm -f /tmp/audit_*.py /tmp/audit_*.sh
echo "  剩余 /tmp/audit_*: $(ls /tmp/audit_* 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "=== 验证：共享目录下的新脚本可直接运行 ==="
bash "$SHARED/bb-readback.sh" "notes/mac-mini/audit-retention-horizon-3h31m-and-seq-decoded-20261008" 2>&1 | head -6
