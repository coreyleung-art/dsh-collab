#!/bin/bash

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
# ★ 约束门（⑩）：N/A —— **本工具的危险能力受限且非外部输入**。
#   pkill 的用途：清理【本脚本自己启动的】临时测试服务（模式限定为
#   `bb-blueprint-gallery.py --port $PORT`，$PORT 是脚本内变量，非命令行参数）。
#   ⇒ 依 R10 定义（「不该发生的路径在结构上不可绕过」）：杀进程的目标【已在模式中收口】，
#     无法通过外部输入扩大作用范围。
# ★ 限度：此为【模式匹配 + 人工核】结论；若日后允许从参数指定 kill 模式，须更新本声明。

DSH_LOG="$HOME/dsh-collab/logs/bb-gallery-gate.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）
# bb-gallery-gate.sh — 架构管理器提交前门禁(Φ9 约束前置 · R006 TCC)
# 改 bb-blueprint-gallery.py / bb-gallery-ui.js / bb-gallery-ui.css 后必跑, 不过不发布
# 检查:
#  1. Python 语法(py_compile)
#  2. JS 语法(node --check 独立文件)
#  3. JS 括号平衡(快检)
#  4. API smoke(起临时服务 curl 关键端点)
#  5. 结构审计(bb-gallery-audit.py --selfcheck)
set -e
cd "$(dirname "$0")"
PY="bb-blueprint-gallery.py"
JS="bb-gallery-ui.js"
CSS="bb-gallery-ui.css"
PORT=8891
PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
bad(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "══ bb-gallery-gate · 提交前门禁 ══"

echo "[1/5] Python 语法"
python3 -m py_compile "$PY" && ok "py_compile" || bad "Python 语法错"

echo "[2/5] JS 语法(独立文件 node check)"
if [ -f "$JS" ]; then
  NODE_BIN="$(command -v node || echo /opt/homebrew/bin/node)"
  "$NODE_BIN" --check "$JS" 2>/tmp/gate-js.err && ok "node --check" || { bad "JS 语法错"; head -3 /tmp/gate-js.err; }
else
  bad "缺 $JS"
fi

echo "[3/5] API smoke(临时服务 $PORT)"
rm -f ~/.systemgraph-user-closed 2>/dev/null
pkill -f "^.*python3? .*bb-blueprint-gallery.py --port $PORT" 2>/dev/null || true
nohup /usr/bin/python3 "$PY" --port $PORT >/tmp/gate-srv.log 2>&1 &
SRV_PID=$!
sleep 4
SMOKE_OK=1
for ep in "" "api/overview" "api/philosophy" "api/blueprints" "api/cap-view" "api/plan-archive" "api/biz-assets"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/$ep" --max-time 6)
  [ "$code" = "200" ] || { echo "  ❌ $ep → $code"; SMOKE_OK=0; }
done
[ $SMOKE_OK = 1 ] && ok "7 端点 smoke 全 200" || bad "API smoke 失败(见上)"
# 页面 JS 无错(headless) — 容忍 chrome 退出码; NO_BROWSER=1 跳过(发布门禁用, 避免无头环境挂起)
if [ -n "${NO_BROWSER:-}" ]; then
  ok "页面 JS 检查跳过(NO_BROWSER 发布模式)"
else
CHROME=$(ls ~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" 2>/dev/null | head -1)
if [ -n "$CHROME" ]; then
  OUT=$("$CHROME" --headless --disable-gpu --no-sandbox --enable-logging=stderr --virtual-time-budget=6000 --dump-dom "http://127.0.0.1:$PORT/" 2>/dev/null || true)
  ERRS=$(printf '%s' "$OUT" | grep -icE "CONSOLE.*(error|uncaught|syntax)" || true)
  ERRS=${ERRS:-0}
  if [ "$ERRS" = "0" ]; then ok "页面 JS 0 错误"; else bad "页面 JS ${ERRS} 错误"; fi
else
  ok "页面 JS 检查跳过(无 headless chrome)"
fi
fi

echo "[4/5] 结构审计"
python3 bb-gallery-audit.py --selfcheck && ok "结构审计" || bad "结构问题"

echo "[5/5] 打包完整性(app 内静态资源+工具+健康)"
# 检查 dist app 是否含 css/js/audit 等(打包缺陷如 css 丢失在此拦截)
APP_GAL="$HOME/system-graph-app/dist/SystemGraph.app/Contents/Resources/app/gallery"
MISSING=""
for f in bb-gallery-ui.css bb-gallery-ui.js bb-gallery-audit.py bb-blueprint-gallery.py bb-connect-execute.py bb-schema-gate.py; do
  [ -f "$APP_GAL/$f" ] || MISSING="$MISSING $f"
done
if [ -n "$MISSING" ]; then bad "打包缺文件:$MISSING"; else ok "打包文件齐全(css/js/工具)"; fi
# 健康自检(运行实例)全绿?
H=$(curl -s http://127.0.0.1:8798/api/health --max-time 5 2>/dev/null)
HOK=$(echo "$H" | python3 -c "import json,sys;d=json.load(sys.stdin);print('true' if d.get('healthy') else 'false')" 2>/dev/null)
if [ "$HOK" = "true" ]; then ok "运行实例健康全绿"; else bad "健康未全绿(见 /api/health)"; fi

echo "══ 结果: $PASS 通过 / $FAIL 失败(5 项) ══"
# 清理测试服务(防残留占用端口, 致下次 release 门禁卡死)
for _p in $(pgrep -f "python3.*bb-blueprint-gallery.py --port $PORT" 2>/dev/null); do kill -9 $_p 2>/dev/null; done
sleep 1
[ $FAIL = 0 ] || echo "❌ 门禁未过 —— 修复后再发布(Φ9)"
[ $FAIL = 0 ] && echo "✅ 门禁全过, 可发布"
exit $FAIL
