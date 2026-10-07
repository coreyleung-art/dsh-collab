#!/usr/bin/env bash
# 升级后验证：MBP 侧 agent-way v1.5.8 + central-inbox v0.2.2(+内容指纹) + comm-shared v1.0.1
# 依据：星桥 upgrade-notice-20261003 的验收方式（重跑自注册看版本号变化 + 行为验证）
set -uo pipefail
NM=~/.dsh/profiles/web/node_modules

echo "════════ ① 版本确认（磁盘 vs 生效）════════"
python3 - <<'PY'
import json, os
nm = os.path.expanduser("~/.dsh/profiles/web/node_modules")
for n in ("dsh-plugin-agent-way", "dsh-plugin-central-inbox", "dsh-comm-shared"):
    p = os.path.join(nm, n, "package.json")
    try:
        print("  %-30s v%s" % (n, json.load(open(p)).get("version")))
    except Exception as e:
        print("  %-30s ❌ %s" % (n, e))
PY

echo
echo "════════ ② 我的两处补丁是否在位（重启不丢）════════"
echo -n "  central-inbox 内容指纹去重键: "
grep -c "key + '#' + fp" "$NM/dsh-plugin-central-inbox/lib/route.js" 2>/dev/null
echo -n "  central-inbox contentFingerprint import: "
grep -c "contentFingerprint" "$NM/dsh-plugin-central-inbox/lib/route.js" 2>/dev/null
echo -n "  agent-way 思考链中文门(lang-zh): "
grep -c "agent-bus:lang-zh" "$NM/dsh-plugin-agent-way/lib/index.js" 2>/dev/null
echo -n "  agent-way LANG_PROMPT 定义: "
grep -c "const LANG_PROMPT" "$NM/dsh-plugin-agent-way/lib/index.js" 2>/dev/null

echo
echo "════════ ③ 它侧新增能力是否到位（核对升级收益）════════"
echo -n "  A6 第4层裸标签变体表: "
grep -c "身份变体表\|identity-variant" "$NM/dsh-plugin-agent-way/lib/index.js" 2>/dev/null
echo -n "  I7a reply_required 唤醒: "
grep -c "reply_required" "$NM/dsh-plugin-agent-way/lib/index.js" 2>/dev/null
echo -n "  route.js 可测纯逻辑(shouldInject): "
grep -c "export function shouldInject" "$NM/dsh-plugin-central-inbox/lib/route.js" 2>/dev/null
echo -n "  comm-shared identity.js 导出数: "
grep -c "^export" "$NM/dsh-comm-shared/identity.js" 2>/dev/null

echo
echo "════════ ④ 重跑自注册（星桥给的验收方式：版本号变化即生效）════════"
python3 ~/dsh-collab/tools/e2-register-services.py 2>&1 | tail -6

echo
echo "════════ ⑤ 中枢注册表实测（读侧一眼看到新版本）════════"
python3 - <<'PY'
import json, urllib.request
H = {"X-Webhook-Token": "c6b784621fc871de1077517c24165e93",
     "X-Blackboard-Token": open(__import__("os").path.expanduser("~/.dsh/blackboard-token")).read().strip()}
try:
    r = urllib.request.Request("http://xingqiao.meetfunbp.com:8792/data/discovery/agents/mbp", headers=H)
    svc = (json.load(urllib.request.urlopen(r, timeout=10)).get("value") or {}).get("services") or {}
    for k in ("agent-way", "central-inbox", "node-bridge", "dsh-tools"):
        print("  %-16s %s" % (k, svc.get(k, "(缺)")))
except Exception as e:
    print("  读取失败:", str(e)[:60])
PY

echo
echo "════════ ⑥ 守护与心跳 ════════"
for p in blackboard-events node-bridge device-daemon bb-proxy voice_service; do
  n=$(pgrep -f "$p" 2>/dev/null | wc -l | tr -d ' ')
  printf "  %-20s %s\n" "$p" "$([ "$n" -gt 0 ] && echo ✅ || echo ❌)"
done
python3 -c "
import json,urllib.request
H={'Authorization':'Bearer bb-token-20260829-macmini'}
r=urllib.request.Request('http://100.120.203.20:8792'+'/nodes/mbp/heartbeat',headers=H)
v=(json.load(urllib.request.urlopen(r,timeout=8)).get('value') or {})
print('  心跳: ver=%s health=%s'%(v.get('ver'),v.get('health')))
" 2>/dev/null

echo
echo "════════ ⑦ 行为探针（版本号之外的证据；含新旧判别力自证）════════"
# ①–⑤ 读的都是磁盘 package.json ⇒ 只能证明「包已就位」，证不了新逻辑在跑。
# 本节点跑 central-inbox 的纯函数，其中 A 用例对**新旧两种去重键公式给出相反结论**。
NODE=$(command -v node 2>/dev/null || true)
[ -z "$NODE" ] && NODE=/opt/homebrew/bin/node
if [ -x "$NODE" ]; then
  "$NODE" ~/dsh-collab/tools/probe-central-inbox-dedup.mjs 2>&1 | tail -22
else
  echo "  ⚠️ 未找到 node（试过 PATH 与 /opt/homebrew/bin/node），跳过"
fi
echo
echo "  ⚠️ 判据边界：本探针证明的是**磁盘上的新逻辑正确**；"
echo "     「宿主内存里跑的是新代码」须另由系统提示出现 agent-way:lang-zh 段证明。"
echo
echo "════════ 完成 ════════"
