#!/bin/bash
# apply-a2-port-pin.sh — A2 端口固定（★ 由【用户】执行）
#
# ★★ 为什么由用户执行，而不是 agent：
#   `~/.dsh/profiles/web/cordis.patch.yml` **在 guard 的不可写清单（红线）内**
#   （依据 guard/tools/risk-router.json:112「cordis.patch.yml 禁用插件」）。
#   `guard_check_writable` ⇒ forbidden=true；`guard_compliance` 六门中 **P2 唯一的失败门** ⇒ `safe_edit:false`。
#   ★ 该红线**没有「已授权可覆盖」开关** —— 这是**设计**（改坏它 CLD 起不来）。用户不受该红线约束。
#
# ★ 本脚本已完成的验证（agent 侧）：
#   · P1 备份 ✓  · P4 沙箱验证 ✓（--patch 叠加实测 webserver.port 变为 61044，host 保留）
#   · P0 官方预查 ✓（证据已入 gate-state.json）
#   · 行 id **实查非猜**：--dump-config 第 409 行 `- id: webserver` ✓
#
# 用法:
#   bash apply-a2-port-pin.sh              # 应用到真实 profile
#   bash apply-a2-port-pin.sh /tmp/copy.yml # 应用到指定文件（★ 供 dry-test）
set -euo pipefail

TARGET="${1:-$HOME/.dsh/profiles/web/cordis.patch.yml}"
BK_DIR="$HOME/dsh-collab/guard/backups"
BIN=/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai/dsh/lib/bin.js

echo "== A2 端口固定 =="
echo "  目标: $TARGET"

if [ ! -f "$TARGET" ]; then echo "★ 目标文件不存在"; exit 2; fi

# ① 幂等：已应用即退出（不重复追加）
if grep -qE '^- id: webserver[[:space:]]*$' "$TARGET"; then
  echo "  ✓ 已含 webserver 行 ⇒ 幂等退出（不重复追加）"
  exit 0
fi

# ② 备份
mkdir -p "$BK_DIR"
BK="$BK_DIR/cordis.patch.yml.bak-pre-port-pin-$(date +%Y%m%d-%H%M%S)"
cp "$TARGET" "$BK"
echo "  ✓ 备份 → $BK"
echo "    sha=$(shasum -a 256 "$TARGET" | cut -c1-16)"
# ★ 修（2026-10-11 干跑自捕）：此行原写成 $(( ... )) —— 那是**算术展开**，在 set -u 下
#   bash 会把 `shasum` 当变量名 ⇒ `unbound variable` ⇒ 脚本在【备份后、追加前】退出。
#   正确是 $( ... )（命令替换）。★ 正因为有 set -e，它在动文件之前就停了（真文件未受影响）。

# ③ 追加（★ restate 全部键：该行 config 共 host / port 两键）
cat >> "$TARGET" <<'PATCHEOF'

# ★ 2026-10-11 星桥第二任 · 端口固定（锚点 §10 W4.1 / §14 M2「3 次重启地址不变」/ §15 Q-B —— 同一根因）
#   CLD 以 `bin.js web --port 0` 启动 ⇒ web 端口**每次重启由 OS 重新分配**
#   （实测历史：65074/65021/63723/61044/31888/51127/60482/55348）
#   ⇒ tailscale funnel 的 `/` 代理（**写死 61044**）必然指向死地址 ⇒ HTTP 502（实测 3/3 全 502）。
#   ★ 选 61044 的理由：**funnel 当前就指向它** ⇒ **funnel 一字不用改**，502 自然消失。
#   ★★ 本文件第 5 行约定：**覆盖会整段替换该行 config** ⇒ 必须 restate 全部键。
#      该行 config 共两键（host / port）⇒ 两键都写；★ 漏 host 会落到 schema 默认值。
#   ★ 行 id `webserver` 系 --dump-config **实查**所得（非猜）：web-app bundle 以 insert 引入，
#     而 profile patch 在 bundle 之后应用 ⇒ 可按 id 覆盖。
- id: webserver
  config:
    host: 127.0.0.1
    port: 61044
PATCHEOF
echo "  ✓ 已追加 patch 条目"

# ④ 复核（★ 若复核不通过，自动回滚）
if [ -x "$(command -v node 2>/dev/null)" ] || [ -x /opt/homebrew/bin/node ]; then
  # ★ 修（2026-10-11 干跑自捕）：`--dump-config` 读的是**真 profile**，不是 $TARGET。
  #   ⇒ 拿副本跑时复核必然失败（并触发正确但误导的回滚）。故：目标==真 profile 时直接 dump；
  #     目标是副本时改用 `--patch "$TARGET"` 叠加验证 —— 两条路都验的是【改后内容】。
  REAL="$HOME/.dsh/profiles/web/cordis.patch.yml"
  if [ "$TARGET" = "$REAL" ]; then
    OUT=$(/opt/homebrew/bin/node "$BIN" --profile web --dump-config 2>&1 || true)
  else
    OUT=$(/opt/homebrew/bin/node "$BIN" --profile web --dump-config --patch "$TARGET" 2>&1 || true)
  fi
  if printf '%s' "$OUT" | grep -A6 -- '- id: webserver' | grep -q 'port: 61044'; then
    echo "  ✅ 复核通过：webserver.port = 61044"
  else
    echo "  ★ 复核未通过 ⇒ 自动回滚"
    cp "$BK" "$TARGET"
    echo "    已还原自 $BK"
    exit 1
  fi
fi

cat <<'NEXT'

▶ 下一步：**正常重启 CLD**（★ 不要走 :31888/reload —— portal 附录 B：会触发壳崩溃）

重启后核验三条（全绿才算成功）:
  lsof -nP -iTCP:61044 -sTCP:LISTEN                      # 应有 CLD 子进程在监听
  curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 https://coreymac-mini.taild3fd86.ts.net/   # 期望 200（原 502）
  node ~/dsh-plugin-drift-scan/cli.js --json | /usr/bin/python3 -c "import sys,json;d=json.load(sys.stdin);print('driftCount=',d['driftCount'],[r['check'] for r in d['rows'] if r['drift']])"   # 期望 driftCount=0

若想回滚:  cp <上面打印的备份路径> ~/.dsh/profiles/web/cordis.patch.yml  然后重启
NEXT
