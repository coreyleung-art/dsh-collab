#!/bin/bash
# bb-page-probe.sh — SystemGraph 逐页【双平台】渲染探针
#
# 出件：明鉴 v3 · 2026-10-12
# 用途：对同一个功能页，一次性产出 iOS（模拟器 · 真 iOS WebKit）与 macOS（桌面视口）两版渲染，
#       并做机器预检（JS 报错 / 内容长度 / 横向溢出代理）。
#
# 为什么这么做（本夜教训）：
#   ★ 三个纯视觉 bug（badge 被拉伸成竖条 / 列表被空画布挤到屏幕下方 / 关系标签全空）
#     **只有看渲染截图才能发现** —— 日志与 DOM 文本检查都报"正常"。
#   ⇒ 故逐页迭代必须以【看图】为主、机器检查为辅。
#
# 用法：
#   bb-page-probe.sh <hash> [outdir]
#   例：bb-page-probe.sh philosophy /tmp/sgpages
#
# 产出：
#   <outdir>/ios-<hash>.png    iOS 模拟器截图（1206x2622）
#   <outdir>/mac-<hash>.png    macOS 桌面截图（1440x900）
#   机器预检行打到 stdout
set -uo pipefail

HASH="${1:-dash}"
OUT="${2:-/tmp/sgpages}"
BASE="http://127.0.0.1:8798"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
SIM="${SG_SIM_UDID:-D5AE0F82-CA99-44FC-A9E3-6BCECA1437C4}"   # iPhone 18 Pro

mkdir -p "$OUT"
# ★ 2026-10-12 P7 教训：必须带 cache-buster —— 否则 Safari/Chrome 可能用缓存页，
#   你会对着【旧渲染】判断「修复没生效」（本夜实测踩到一次）。
TS=$(date +%s)
URL="$BASE/?t=$TS#$HASH"
echo "════ 探针：$HASH ════  ($URL)"

# ── ① iOS（Xcode 模拟器 · 真 iOS WebKit；env(safe-area-*) 有真实值）──
if /usr/bin/xcrun simctl list devices | grep -q "$SIM"; then
  st=$(/usr/bin/xcrun simctl list devices | grep "$SIM" | sed -n 's/.*(\([A-Za-z]*\)).*/\1/p')
  [ "$st" = "Booted" ] || /usr/bin/xcrun simctl boot "$SIM" >/dev/null 2>&1
  /usr/bin/xcrun simctl openurl "$SIM" "$URL" >/dev/null 2>&1
  sleep 11
  /usr/bin/xcrun simctl io "$SIM" screenshot "$OUT/ios-$HASH.png" >/dev/null 2>&1
  echo "  iOS   : $OUT/ios-$HASH.png  $(stat -f%z "$OUT/ios-$HASH.png" 2>/dev/null || echo 失败) B"
else
  echo "  iOS   : ★ 模拟器 $SIM 不可用（跳过，如实报）"
fi

# ── ② macOS（桌面视口；同时抓 JS 报错）──
rm -rf "/tmp/probe-$HASH"; mkdir -p "/tmp/probe-$HASH"
"$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir="/tmp/probe-$HASH" \
  --window-size=1440,900 --hide-scrollbars --virtual-time-budget=11000 \
  --enable-logging=stderr --v=0 \
  --screenshot="$OUT/mac-$HASH.png" --dump-dom "$URL" \
  >"/tmp/probe-$HASH.html" 2>"/tmp/probe-$HASH.err"
echo "  macOS : $OUT/mac-$HASH.png  $(stat -f%z "$OUT/mac-$HASH.png" 2>/dev/null || echo 失败) B"

# ── ③ 机器预检（辅助，不能替代看图）──
python3 - "$HASH" "/tmp/probe-$HASH.html" "/tmp/probe-$HASH.err" <<'PY'
import re, sys
page, htmlf, errf = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    raw = open(htmlf, encoding='utf-8', errors='replace').read()
except Exception:
    raw = ''
body = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.S)     # ★ 必须先剥 script
try:
    errs = open(errf, encoding='utf-8', errors='replace').read().count('CONSOLE')
except Exception:
    errs = -1
# 目标 view 的内容长度
m = re.search(r'id="view-' + re.escape(page) + r'"[^>]*>(.*?)(?=<div[^>]*id="view-|<div class="foot"|$)', body, re.S)
seg = m.group(1) if m else ''
txt = re.sub(r'<[^>]+>', ' ', seg)
txt = re.sub(r'\s+', ' ', txt).strip()
over = [int(n) for n in re.findall(r'style="[^"]*?(?<![-\w])width:(\d+)px', body) if int(n) > 390]
print("  预检  : view 文本长度=%d · JS 报错=%s · 渲染体内 >390px 内联宽=%s · 渲染文本「加载失败」=%d"
      % (len(txt), errs, sorted(set(over)) or '无',
         # ★ 2026-10-12 修：原来用 body.count() 查原始 HTML 串 ⇒ 会命中 title/属性里的字样
         #   （实测：「列表模式」出现在按钮 title 里，导致 1440 宽也误报列表模式）。
         #   ⇒ 改为在【剥标签后的渲染文本】里查。
         re.sub(r'<[^>]+>', ' ', body).count('加载失败')))
print("          首 90 字: %s" % txt[:90])
PY
