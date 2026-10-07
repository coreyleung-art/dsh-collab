#!/usr/bin/env bash
# health-check item 18: 磁盘最大占用者（CLD-022 防复发项）
# 背景: 2026-09-11 发现 /private/tmp/node-bridge-mac-mini.log 72.7 GiB 无轮转，
#       Data 卷 92%。旧巡检只报「占用率 ≥85%」，报不出「是谁在吃」⇒ 无法处置。
# 本项把「占用率」升级为「占用者」：大文件 + 存活时长 + 轮转兄弟 + 持有者 + 增长速率/ETA。
# 退出: 0=无行动项 1=存在需处置的大文件（供 health-check 集成）
#
# ── 设计纪律（本卡族已知教训，逐条落进实现）────────────────────────
# ① 仪器失明 ≠ 对象不存在：lsof 非零退出报「未测」，不得读作「无占用者」。
# ② **mtime ≠ 存活时长**：mtime 测「最近是否被写」，对**一直在写的漏轮转日志永远是 0h**
#    ⇒ 若用 mtime 判「无轮转」，该日志会被判成「近期有写、健康」而放行（代理代替对象）。
#    正确仪器 = birthtime（创建时刻）→ 存活时长。首版即栽在此（实测 0.0h vs 160.4h）。
# ③ 判据含第二可变项 ⇒ 必须同时核轮转兄弟（无 .1/.2/.gz/日期后缀）才算「无轮转」。
# ④ 每条结论带 (对象 · 时点 · 证据级)；声明的边界写进输出，不藏在注释里。
# ⑤ 处置只能用冒号加重定向截断（rm 对仍被持有的文件不释放空间）——提示文本不得含未转义
#    反引号：反引号在双引号内会被 shell 执行，首版即因此真跑了一次截断并生成垃圾文件。

# ── 命令预检（防「依赖不存在的命令」导致静默失败）─────────────────
#   教训（守灯 2026-09-11）：macOS **没有 GNU `timeout`**（exit 127）。凡用 `timeout` 包起来的
#   扫描**从未执行**，其空输出被读成「没有结果」⇒ 这正是「空结果 ≠ 不存在」的成因之一。
#   故本项启动前必须确认所有依赖命令**存在且可执行**，缺失则显式报「未测」，不得静默。
MISSING=""
for c in find lsof stat df du awk sed python3; do
  command -v "$c" >/dev/null 2>&1 || MISSING="$MISSING $c"
done
if [ -n "$MISSING" ]; then
  echo "── [18] 磁盘最大占用者 ──"
  echo "  ⛔ 命令预检失败：缺失$MISSING ⇒ 本项**不可用（未测）**，不得把空输出读作『无大文件』"
  echo "结果: 0/0 通过 (依赖缺失，未测)"
  exit 1
fi

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
THRESH_G=$(( ${DISK_ITEM_THRESH_GB:-1} ))          # 大文件阈值 GiB
AGE_H=$(( ${DISK_ITEM_AGE_HOURS:-24} ))            # 「无轮转迹象」= 存活时长 ≥ N 小时
TOPN=${DISK_ITEM_TOPN:-5}
SCAN_TIMEOUT=${DISK_ITEM_TIMEOUT:-25}
SAMPLE="$HOME/.dsh/.cld-health-disk-sample.json"   # 两次采样算增长速率/ETA

ROOTS=(
  /private/tmp
  "$HOME/.cld/logs"
  "$HOME/.dsh/logs"
  "$HOME/dsh-collab/logs"
  "$HOME/Library/Logs"
)
EXIST=()
for r in "${ROOTS[@]}"; do [ -d "$r" ] && EXIST+=("$r"); done

echo "── [18] 磁盘最大占用者 ──"
echo "  框架: 扫描域=[${EXIST[*]}] 阈值=${THRESH_G}GiB 存活≥${AGE_H}h ｜ 时点=$NOW ｜ 谁在测=守灯"

if [ ${#EXIST[@]} -eq 0 ]; then
  echo "  ⚠️ 18 扫描域全部不存在（口径失效，非「磁盘干净」）"
  echo "结果: 0/0 通过 (域缺失)"
  exit 1
fi

TMPF=$(mktemp); RCF=$(mktemp)
# 整组 2>/dev/null：bash 回收被 kill 的子作业时会向 stderr 打 job-status 行，
# 只重定向 wait 无法拦住它（会污染 health-check 集成输出）⇒ 必须整组重定向。
{
  ( for r in "${EXIST[@]}"; do
      find "$r" -xdev -type f -size +${THRESH_G}G -print0 2>/dev/null
    done ) > "$TMPF" &
  FPID=$!
  ( sleep "$SCAN_TIMEOUT"; kill $FPID 2>/dev/null ) & KPID=$!
  wait $FPID; echo $? > "$RCF"
  kill $KPID 2>/dev/null; wait $KPID 2>/dev/null
} 2>/dev/null
SRC=$(cat "$RCF" 2>/dev/null); SRC=${SRC:-1}; rm -f "$RCF"

BIG_N=$(tr -cd '\0' < "$TMPF" | wc -c | tr -d ' '); BIG_N=${BIG_N:-0}
if [ "$SRC" -ne 0 ] && [ "$BIG_N" -eq 0 ]; then
  echo "  ⚠️ 18a 扫描超时/中断（${SCAN_TIMEOUT}s, exit=$SRC）——大文件数为 0 属**未测**，不得读作「无大文件」"
else
  echo "  ✅ 18a 大文件枚举完成: ${BIG_N} 个 ≥${THRESH_G}GiB（${SCAN_TIMEOUT}s 上限内, exit=$SRC）"
fi

if [ "$BIG_N" -eq 0 ]; then
  echo "结果: 0 行动项 (无 ≥${THRESH_G}GiB 文件)"
  rm -f "$TMPF"; exit 0
fi

# 18b. 逐个大文件：体积 / 存活时长(birthtime) / mtime 龄 / 轮转兄弟
#      两个仪器分别输出，禁止混用（纪律②）
ROWS=$(python3 - "$TMPF" "$AGE_H" "$TOPN" <<'PY'
import os, sys, json, datetime, glob
tmpf, age_h, topn = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
paths = [p.decode('utf-8','replace') for p in open(tmpf,'rb').read().split(b'\0') if p]
now = datetime.datetime.now().timestamp()

def rot_siblings(p):
    d, b = os.path.dirname(p), os.path.basename(p)
    pats = [b + '.*', b + '-*', b + '_*', b + '.gz', b + '.old', b + '.bak']
    hits = set()
    for pat in pats:
        for q in glob.glob(os.path.join(d, pat)):
            if q != p and os.path.isfile(q):
                hits.add(os.path.basename(q))
    return sorted(hits)

rows = []
for p in paths:
    try:
        st = os.stat(p)
    except OSError:
        continue
    born = getattr(st, 'st_birthtime', None)
    alive_h = (now - born) / 3600.0 if born else None
    mtime_h = (now - st.st_mtime) / 3600.0
    sib = rot_siblings(p)
    if alive_h is None:
        verdict = "存活时长未测(birthtime 不可用)"
    elif sib:
        verdict = "有轮转兄弟(%d)" % len(sib)
    elif alive_h >= age_h:
        verdict = "无轮转迹象"
    else:
        verdict = "新文件(存活<%.0fh)" % age_h
    rows.append({"p": p, "gib": st.st_size / 2**30, "alive_h": alive_h,
                 "mtime_h": mtime_h, "sib": sib, "verdict": verdict})
rows.sort(key=lambda r: -r["gib"])
print(json.dumps({"total": len(rows), "rows": rows[:topn],
                  "sum_gib": sum(r["gib"] for r in rows)}, ensure_ascii=False))
PY
)

echo "$ROWS" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("  18b TOP%d（共 %d 个 ≥阈值文件，合计 %.1f GiB）:" % (len(d["rows"]), d["total"], d["sum_gib"]))
for r in d["rows"]:
    a = ("%7.1fh" % r["alive_h"]) if r["alive_h"] is not None else "   未测"
    print("    - %6.1f GiB 存活%s 最近写%6.2fh  %-16s %s" % (r["gib"], a, r["mtime_h"], r["verdict"], r["p"]))
'

SP=$(echo "$ROWS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["rows"][0]["p"] if d["rows"] else "")')

# 18c. 持有者核查
if [ -n "$SP" ]; then
  LSOF_OUT=$(lsof "$SP" 2>&1); LSOF_RC=$?
  if [ $LSOF_RC -ne 0 ]; then
    echo "  ⚠️ 18c 持有者: **未测**（lsof exit=$LSOF_RC: $(echo "$LSOF_OUT" | head -1)）"
    echo "         仪器失明 ⇒ 空输出不得读作「无占用者」；改用 pgrep -f <进程名> 复核"
  else
    HOLD=$(echo "$LSOF_OUT" | awk 'NR>1{print $1}' | sort -u | paste -sd, -)
    echo "  ✅ 18c 持有者: ${HOLD:-无进程持有（lsof exit=0，空结果可信）}｜lsof 进程名列宽 9 字符可能截断，勿据此断言完整进程名"
    echo "         属主定位用**进程名/路径**，不要用 PID（PID 会变，见 hazard 卡）"
  fi
fi

# 18d. 增长速率 + ETA + **卷预算闭合**（两次采样；样本缺失标未测）
#    ★ v1.1 补盲区：旧版只测「单个大文件涨得多快」，**不测「卷一共掉了多少」**
#      ⇒ 若另有写入者（本工具扫描域外），旧版看不见。实测 2026-09-11 08:2x 就发现
#      卷 60s 掉 0.05 GiB（≈72 GiB/d）而日志只占 ≈40% ⇒ 必须做**预算闭合**。
DISK_INFO=$(python3 - "$SAMPLE" "$SP" <<'PY'
import os, sys, json, time, shutil
sample, sp = sys.argv[1], sys.argv[2]
VOL = "__volume__"                      # 卷采样哨兵键（不是文件路径）
now = time.time()
prev = {}
if os.path.exists(sample):
    try: prev = json.load(open(sample))
    except Exception: prev = {}
cur = {}
for p, v in prev.items():
    if p == VOL: continue
    if p != sp and os.path.exists(p):
        cur[p] = {"size": v["size"], "ts": v["ts"]}
out = {}
old = prev.get(sp); oldv = prev.get(VOL)
if sp and os.path.exists(sp):
    cur[sp] = {"size": os.stat(sp).st_size, "ts": now}
du = shutil.disk_usage("/System/Volumes/Data")
cur[VOL] = {"free": du.free, "ts": now}
try: json.dump(cur, open(sample, "w"), ensure_ascii=False)
except Exception: pass

if old and sp and now > old["ts"] + 60:
    dt = (now - old["ts"]) / 86400.0
    rate = (os.stat(sp).st_size - old["size"]) / 2**30 / dt
    out = {"rate_gib_per_day": round(rate, 2), "window_h": round(dt * 24, 2),
           "free_gib": round(du.free / 2**30, 1)}
    if rate > 0:
        out["eta_days"] = round(du.free / 2**30 / rate, 2)
        out["eta_note"] = "仅按本文件增长外推，未计其他写入者（乐观右界）"
    # ★ 卷预算闭合
    if oldv and now > oldv["ts"] + 60:
        vol_rate = (oldv["free"] - du.free) / 2**30 / dt      # 正=卷在减少
        out["volume_drain_gib_per_day"] = round(vol_rate, 2)
        if vol_rate > 0:
            tracked = max(rate, 0.0)
            unattr = vol_rate - tracked
            out["tracked_share_pct"] = round(100 * tracked / vol_rate, 1)
            out["unattributed_gib_per_day"] = round(unattr, 2)
            out["budget_closed"] = bool(unattr <= 0.2 * vol_rate)
            if not out["budget_closed"]:
                out["budget_note"] = ("**预算未闭合**：卷消耗仅 %.0f%% 由已追踪文件解释 ⇒ "
                                      "**存在未归因写入者（在本工具扫描域外或小于阈值）**"
                                      % (100 * tracked / vol_rate))
else:
    out = {"rate_gib_per_day": None, "note": "增长速率未测（需两次采样；本次已存样本，下次运行可得）"}
print(json.dumps(out, ensure_ascii=False))
PY
)
echo "  18d 增长/生存期: $(echo "$DISK_INFO" | python3 -c 'import json,sys;d=json.load(sys.stdin);r=d.get("rate_gib_per_day");print(("速率 %.2f GiB/d（窗口 %.1fh）｜剩余 %.1f GiB ｜ETA %.2f 天（%s）"%(r,d["window_h"],d["free_gib"],d["eta_days"],d["eta_note"])) if r else "未测："+d.get("note",""))')"
echo "  18f 卷预算闭合: $(echo "$DISK_INFO" | python3 -c '
import json,sys
d=json.load(sys.stdin); v=d.get("volume_drain_gib_per_day")
if v is None: print("未测（需两次卷采样）")
else:
    print("卷消耗 %.2f GiB/d ｜ 已追踪文件解释 %.1f%% ｜ 未归因 %.2f GiB/d ⇒ %s"
          % (v, d.get("tracked_share_pct",0), d.get("unattributed_gib_per_day",0),
             "✅ 闭合" if d.get("budget_closed") else "⚠ "+d.get("budget_note","")))')"

# 18e. 处置提示（只诊断，不自动执行）
UNROT=$(echo "$ROWS" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(1 for r in d["rows"] if r["verdict"]=="无轮转迹象"))')
echo "  ℹ️ 18e 处置: TOP 中 ${UNROT} 个无轮转迹象。确认可回收后，只能用冒号加重定向（: > 文件）截断；"
echo "         ⚠ 验收看 du/df（已分配块/卷可用），**不要看 ls**（逻辑大小）—— 被持有 fd 截断后会留稀疏空洞，"
echo "           逻辑大小可跳回旧偏移（实测：逻辑 110 MB vs 实际 10 MB）。rm 的释放被推迟到持有者关闭（长驻进程=实际永不）。"
echo "         本项不自动执行，交人工裁决。"

UNCLOSED=$(echo "$DISK_INFO" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(0 if d.get("budget_closed",True) else 1)')
if [ "$UNROT" -gt 0 ] || [ "${UNCLOSED:-0}" -eq 1 ]; then
  echo "结果: $(( UNROT + UNCLOSED )) 行动项 (无轮转大文件 ${UNROT} · 卷预算未闭合 ${UNCLOSED})"
  rm -f "$TMPF"; exit 1
fi
echo "结果: 0 行动项 (大文件均有轮转或为新文件；卷预算闭合)"
rm -f "$TMPF"; exit 0
