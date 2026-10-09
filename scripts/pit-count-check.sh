#!/bin/bash
# 自包含：核对「头部声明的坑计数」与「实际条数」是否一致
# 设计要点（来自实测教训）：
#   ① 按【行索引】定位两端（## 5 · 已知坑 → ## 6 ·），**不靠字面锚点**（避开「关键词未命中≠不存在」陷阱）
#   ② 同时给出【最大编号】（必要不充分：编号连续时它=条数，若别节编号更大则失效）
#   ③ 打印【过宽计数】并标为陷阱：`^[0-9]+\. \*\*` 会把各节所有编号列表项都算进来 ⇒ 不可与坑条数对账
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
  echo "== pit-count-check 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · 自包含：核对「头部声明的坑计数」与「实际条数」是否一致"
  echo "  · 设计要点（来自实测教训）："
  echo "  · ① 按【行索引】定位两端（## 5 · 已知坑 → ## 6 ·），**不靠字面锚点**（避开「关键词未命中≠不存在」陷阱）"
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/pit-count-check.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

DSH_LOG="$HOME/dsh-collab/logs/pit-count-check.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

H="$HOME/dsh-collab/docs/audit-reviewer-handover-v1.md"
R="$HOME/dsh-plugin-pstd/docs/README.md"
python3 - "$H" "$R" <<'PY'
import re,sys
def scoped(p,a,b):
    L=open(p,encoding='utf-8').read().split('\n'); s=e=None
    for i,l in enumerate(L):
        if s is None and l.startswith(a): s=i
        elif s is not None and l.startswith(b): e=i; break
    seg=L[s:e] if s is not None else []
    return len([x for x in seg if re.match(r'^\d+\. \*\*', x)])
def maxno(p):
    ns=[int(m.group(1)) for m in re.finditer(r'^(\d+)\. \*\*', open(p,encoding='utf-8').read(), re.M)]
    return max(ns) if ns else 0
def wide(p):
    return len(re.findall(r'^\d+\. \*\*', open(p,encoding='utf-8').read(), re.M))
H,R=sys.argv[1],sys.argv[2]
pkg,own=scoped(R,'## 坑（都踩过）','## 实测记录'),scoped(H,'## 5 · 已知坑','## 6 ·')
m=re.search(r'包内 `[^`]+` (\d+) 条 / 本处 (\d+) 条', open(H,encoding='utf-8').read())
print("  声明 = %s   实测（作用域内）= (%d, %d)   ⇒ %s"%(m.groups(),pkg,own,
      "✅ 一致" if (int(m.group(1)),int(m.group(2)))==(pkg,own) else "❌ 不一致"))
print("  最大编号：包内 = %d · 本处 = %d   （必要不充分：仅当编号连续且别节编号更小时才等于条数）"%(maxno(R),maxno(H)))
print("  ⚠ 过宽计数（**陷阱，勿用于对账**）：包内 = %d · 本处 = %d —— 它把各节所有编号列表项都算进来（判据清单/复现命令/变更记录等）"%(wide(R),wide(H)))
PY
