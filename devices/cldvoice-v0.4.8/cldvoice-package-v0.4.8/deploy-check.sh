#!/usr/bin/env bash
# deploy-check.sh — CLD-Voice v0.4.8 接收端自检 (deploy-safety-scheme §5)
# 用法: ./deploy-check.sh [--isolate]
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$HERE/plugin/dsh-plugin-cldvoice"
PASS=0; FAIL=0
ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }
no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }

echo "=== 1. 静态四段审查 ==="
# 1.1 package.json 合法
if python3 -c "import json;json.load(open('$PLUGIN/package.json'))" 2>/dev/null; then ok "package.json 合法"; else no "package.json 非法"; fi
# 1.2 cordis.patch.yml 存在
[ -f "$PLUGIN/cordis.patch.yml" ] && ok "cordis.patch.yml 存在" || no "cordis.patch.yml 缺失"
# 1.3 dsh.bundle.patch 引用存在
if python3 -c "import json,sys;d=json.load(open('$PLUGIN/package.json'));sys.exit(0 if d.get('dsh',{}).get('bundle',{}).get('patch') else 1)" 2>/dev/null; then ok "dsh.bundle.patch 已声明"; else no "dsh.bundle.patch 未声明"; fi
# 1.4 语法
for f in "$PLUGIN"/lib/*.js; do
  if node --check "$f" 2>/dev/null; then ok "语法 OK: $(basename "$f")"; else no "语法错误: $(basename "$f")"; fi
done

echo "=== 2. 依赖解析(自包含检查) ==="
if (cd "$PLUGIN" && node -e "import('./lib/index.js').then(m=>{if(typeof m.apply!=='function')process.exit(1)}).catch(e=>{console.error(e.message);process.exit(1)})") 2>/dev/null; then
  ok "host 依赖解析通过(无 Cannot find package)"
else
  echo "  ⚠️ host 依赖缺包(接收端可能需补 node_modules):"
  (cd "$PLUGIN" && node -e "import('./lib/index.js').catch(e=>console.error('    '+e.message))" 2>&1 | head -3)
  FAIL=$((FAIL+1))
fi

echo "=== 3. 后端语法 ==="
for f in "$HERE"/backend/*.py; do
  if python3 -m py_compile "$f" 2>/dev/null; then ok "语法 OK: $(basename "$f")"; else no "语法错误: $(basename "$f")"; fi
done

echo "=== 4. 后端依赖(可选, 检查 venv) ==="
if [ -x "$HOME/dsh-collab/cld-voice/backend/venv/bin/python" ]; then
  for m in websockets websocket numpy; do
    if "$HOME/dsh-collab/cld-voice/backend/venv/bin/python" -c "import $m" 2>/dev/null; then ok "py 模块 $m"; else no "py 模块缺失 $m"; fi
  done
else
  echo "  ⏭  venv 未就绪(安装后再验证: pip install -r requirements.txt)"
fi

echo "=== 5. 凭证 ==="
for k in VOLC_ASR_API_KEY GLM_API_KEY; do
  if grep -q "$k" "$HOME/.dsh/.credentials.yaml" 2>/dev/null; then ok "凭证 $k 存在"; else echo "  ⚠️  凭证 $k 未找到(语音/成稿可能不可用)"; fi
done

echo "=== 6. 隔离模拟(仅 --isolate 时) ==="
if [ "${1:-}" = "--isolate" ]; then
  TESTHOME=/tmp/dsh-test-home-cldvoice
  rm -rf "$TESTHOME"; mkdir -p "$TESTHOME/profiles/web"
  cp "$HOME/.dsh/profiles/web/package.json" "$TESTHOME/profiles/web/" 2>/dev/null || true
  ln -sfn "$PLUGIN" "$TESTHOME/profiles/web/node_modules_dsh-plugin-cldvoice" 2>/dev/null || true
  echo "  ⏭  隔离 profile 已建($TESTHOME); 请手动执行 DSH_HOME=$TESTHOME dsh --profile web --dump-config | grep cldvoice"
else
  echo "  ⏭  跳过(加 --isolate 启用)"
fi

echo
echo "================ 自检结果: PASS=$PASS FAIL=$FAIL ================"
[ "$FAIL" -eq 0 ] && echo "🎉 全部通过 — 可进行生产安装(重启 CLD 生效)" || echo "⚠️  有失败项 — 请反馈发包方(MBP)"
exit $FAIL
