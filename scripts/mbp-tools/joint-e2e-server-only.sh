#!/usr/bin/env bash
# 联合验收：只连服务器端到端（断 Tailscale 直连，仅保留公网中枢连通）
# ★ 自恢复保障：trap EXIT 无条件恢复 Tailscale；每步验证；结束打印状态。
# 用户指示：「如果长期没通就切回来旧通道」⇒ 本脚本测完即恢复旧通道（Tailscale 直连）。
set -uo pipefail
TS=/Applications/Tailscale.app/Contents/MacOS/tailscale
TOK=c6b784621fc871de1077517c24165e93
BBTOK=$(cat ~/.dsh/blackboard-token 2>/dev/null || echo "")   # ★ 2026-10-03 flip 新头
BB_CENTRAL=http://xingqiao.meetfunbp.com:8792
BB_TAIL=http://100.120.203.20:8792
R(){ printf '\n=== %s ===\n' "$1"; }

recover(){
  R "恢复旧通道（Tailscale up）"
  "$TS" up >/dev/null 2>&1
  for i in 1 2 3 4 5; do
    st=$("$TS" status 2>/dev/null | grep -c "coreymac-mini.*active" || true)
    [ "$st" != "0" ] && { echo "  ✅ 已恢复：mac-mini active"; break; }
    echo "  等待恢复… ($i)"; sleep 4
  done
  "$TS" status 2>/dev/null | grep coreymac-mini | sed 's/^/  /'
  echo -n "  黑板(mac-mini)可达性: "
  curl -s -m 8 -o /dev/null -w "HTTP=%{http_code}\n" -H "Authorization: Bearer bb-token-20260829-macmini" "$BB_TAIL/nodes/mbp/heartbeat" || echo "不可达"
}
trap recover EXIT

R "① 断 Tailscale 直连"
"$TS" down >/dev/null 2>&1; echo "  tailscale down 已执行"
sleep 3
"$TS" status 2>&1 | head -3 | sed 's/^/  /'

R "② 验证：mac-mini 不可达 / 中枢可达（=「只连服务器」）"
echo -n "  mac-mini 本地板($BB_TAIL): "
curl -s -m 6 -o /dev/null -w "HTTP=%{http_code}\n" -H "Authorization: Bearer bb-token-20260829-macmini" "$BB_TAIL/nodes/mbp/heartbeat" 2>&1 || echo "不可达 ✅（预期）"
echo -n "  星桥中枢($BB_CENTRAL):    "
curl -s -m 6 -o /dev/null -w "HTTP=%{http_code} %{time_total}s\n" -H "X-Webhook-Token: $TOK" -H "X-Blackboard-Token: $BBTOK" "$BB_CENTRAL/data/discovery/agents/mbp" 2>&1 || echo "不可达 ❌"

R "③ 我→它：3 条（bus 信封 ×2 + 中枢黑板双写 ×1）计时"
python3 - <<'PY'
import json,urllib.request,time,subprocess,os
TOK="c6b784621fc871de1077517c24165e93"
BBTOK=$(cat ~/.dsh/blackboard-token 2>/dev/null || echo "")   # ★ flip 新头
CENTRAL="http://xingqiao.meetfunbp.com:8792"
res=[]
# (a) bus 信封 ×2
for i in (1,2):
    t=time.time()
    try:
        out=subprocess.run(["python3",os.path.expanduser("~/dsh-collab/comm-server/xq-send.py"),
                            "mac-mini","notice","-"],input="[joint-e2e] MBP→mac-mini 第%d条 (只连服务器)"%i,
                          capture_output=True,text=True,timeout=25,env=dict(os.environ,BUS_FROM="mbp"))
        ok='"ok":true' in (out.stdout or '')
        res.append(("bus#%d"%i, ok, time.time()-t, (out.stdout or out.stderr).strip()[:60]))
    except Exception as e:
        res.append(("bus#%d"%i, False, time.time()-t, str(e)[:50]))
# (b) 中枢黑板双写（只连服务器时只能写中枢）
for i in (3,):
    t=time.time()
    k="notes/mac-mini/mbp-joint-e2e-serveronly-%d"%int(time.time())
    try:
        r=urllib.request.Request(CENTRAL+"/"+k,
          data=json.dumps({"type":"joint-e2e","from":"session-20b800d4","to":"session-fa1f9150",
            "title":"[joint-e2e] MBP→mac-mini 第%d条（只连服务器·中枢写）"%i,
            "sent_at_epoch_ms":int(t*1000)},ensure_ascii=False).encode(),
          method="PUT",headers={"X-Webhook-Token":TOK,"Content-Type":"application/json","X-Blackboard-Token":open(__import__("os").path.expanduser("~/.dsh/blackboard-token")).read().strip()})
        d=json.load(urllib.request.urlopen(r,timeout=20))
        res.append(("central-put#%d"%i, True, time.time()-t, "ver=%s key=%s"%(d.get("version"),d.get("key"))))
    except Exception as e:
        res.append(("central-put#%d"%i, False, time.time()-t, str(e)[:50]))
for name,ok,el,info in res:
    print("  %-14s %s  %.2fs  %s"%(name,"✅" if ok else "❌",el,info))
PY

R "④ 它→我：中枢黑板回执（8803 SSE 为 mac-mini 侧，断连后我不可订阅）"
echo "  ⇒ 我侧此时只能靠【中枢黑板】收它对端回复；8803 SSE 不可达（属预期）"
echo -n "  8803 SSE 可达性: "
curl -s -m 6 -o /dev/null -w "HTTP=%{http_code}\n" "http://100.120.203.20:8803/events" 2>&1 || echo "不可达 ✅（预期）"

R "⑤ 我的守护表现（R034：失败必须可见）"
tail -3 ~/dsh-collab/logs/blackboard-events.launchd.log 2>/dev/null | sed 's/^/  /'
echo "  近10行失败告警: $(tail -10 ~/dsh-collab/logs/blackboard-events.launchd.log 2>/dev/null | grep -c '读取失败')"
echo "  ⇒ 期望：出现「⚠️ 黑板读取失败」告警（证明失败可见，非静默）"

R "⑥ 即将恢复（trap 触发）"
