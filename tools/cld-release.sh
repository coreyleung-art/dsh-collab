#!/bin/bash
# cld-release.sh — CLD（Electron 宿主）发布签名流水线 P0 固化版（2026-10-06 星桥）
# 设计要点（今晚实测教训内化）：
#   ① 全部内嵌 Mach-O 逐个签（--deep 会漏 Resources/node_modules 下的二进制）
#   ② 路径安全：传递段 null 分隔 + file -0 拆包解析（空格/冒号路径完整保留，v2 裁判审查后升级）
#   ③ 时间戳依赖 HTTPS timestamp.apple.com —— 劣化时 codesign --timestamp 会挂，
#      本脚本先探测，挂了就拒绝执行（fail-loud），不做半签名
#   ④ 版本/计数全部运行时读，不写死会变的值（章程 v24）
# 用法：
#   cld-release.sh                 # 对 /Applications/CLD.app 全流程
#   cld-release.sh <app路径>       # 对任意 app 全流程
#   cld-release.sh --dry-run [app] # 只预检（不签名不公证不写盘）
set -euo pipefail

DRY=0
APP="/Applications/CLD.app"
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    *) APP="$a" ;;
  esac
done

IDENT="Developer ID Application: Zhenyu Liang (XS7SMKFS42)"
ISSUER=$(cat ~/.dsh/appstoreconnect/issuer-id.txt)
API_KEY=VA9RR5747M
# 2026-10-10: entitlements 由 /tmp 临时文件改为版本化单一来源。
#   教训：原 heredoc 只写 4 个 cs.* 键 → 缺 com.apple.security.device.audio-input →
#   hardened runtime 下 tccd 对麦克风"Policy disallows prompt"静默拒绝 →
#   CLD 内任何 getUserMedia（dsh-plugin-cldvoice 悬浮球）听不到用户声音。
ENTITLEMENTS="$HOME/dsh-collab/tools/CLD-entitlements.plist"
OUTDIR="$HOME/CLD-releases"

# Mach-O 清单（file -0 批处理 + python 拆包；空格/冒号路径安全，无 cut 截断边界）
macho_list() {
  find "$1/Contents" -type f -print0 | xargs -0 file -0 2>/dev/null | python3 -c '
import sys
data = sys.stdin.buffer.read()
parts = data.split(b"\x00")
out = []
for i, part in enumerate(parts):
    if i == 0:
        continue
    # 文件 i 的路径 = parts[i-1] 尾段，描述 = parts[i] 首段（含末文件）
    lines = part.rsplit(b"\n", 1)
    desc = lines[0]
    prev_tail = parts[i-1].rsplit(b"\n", 1)[-1]
    if b"Mach-O" in desc and prev_tail:
        out.append(prev_tail)
if out:
    sys.stdout.write("\n".join(x.decode("utf-8", "replace") for x in out) + "\n")
'
}

# ---------- 预检 ----------
[ -d "$APP" ] || { echo "FAIL: app 不存在: $APP"; exit 2; }
BUNDLE=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP/Contents/Info.plist" 2>/dev/null || echo "?")
VER=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist" 2>/dev/null || echo "?")
echo "== 预检: $APP (bundle=$BUNDLE version=$VER)"

# 内嵌 Mach-O 全量清单（声明与实际同源 v33：传递段为 null 分隔 find -print0|xargs -0，
#   解析段为 file -0 输出按 \0 拆包——路径含空格/冒号均完整保留）
BINS=$(macho_list "$APP")
COUNT=$(printf '%s\n' "$BINS" | grep -c . || true)
echo "Mach-O 清单: $COUNT 个"

if [ "$DRY" = "1" ]; then
  echo "DRY-RUN: 输入预检通过，未做任何修改。全量执行将：逐个签 $COUNT 个 Mach-O → 外层 --deep → 公证 → 装订 → spctl → 打 stapled zip"
  exit 0
fi

# ---------- 时间戳服务探活（fail-loud；真探测） ----------
# 2026-10-10 修正：原用 curl GET https://timestamp.apple.com/ts01 探活 → 该端点只收 POST(TSQ)，
#   GET 必然失败 ⇒ 探测恒假阴（实测 curl=000 但 codesign --timestamp 正常拿到时间戳）。
#   改为真签一次临时二进制：探活结果与后续签名行为同源。
TS_PROBE=$(mktemp /tmp/cld-ts-probe.XXXXXX)
cp /bin/ls "$TS_PROBE"
if ! codesign --force --options runtime --timestamp --sign "$IDENT" "$TS_PROBE" >/dev/null 2>&1; then
  rm -f "$TS_PROBE"; echo "FAIL: 时间戳服务不可用（codesign --timestamp 实签失败），拒绝执行。网络恢复后重跑。"; exit 3
fi
rm -f "$TS_PROBE"
echo "== 时间戳服务可达（实签探测通过）"

# ---------- entitlements 前置校验（fail-loud，防麦克风静默失效回归） ----------
[ -f "$ENTITLEMENTS" ] || { echo "FAIL: 缺少 entitlements 文件: $ENTITLEMENTS"; exit 4; }
/usr/libexec/PlistBuddy -c 'Print :com.apple.security.device.audio-input' "$ENTITLEMENTS" >/dev/null 2>&1 \
  || { echo "FAIL: $ENTITLEMENTS 缺 com.apple.security.device.audio-input —— 缺它 hardened runtime 会静默拒绝麦克风（CLD 内语音插件全部失效）"; exit 4; }
echo "== entitlements 校验通过（含麦克风授权）"

# ---------- 1/5 逐个签内嵌二进制 ----------
echo "== 1/5 逐个签内嵌 Mach-O"
while IFS= read -r f; do
  [ -n "$f" ] && codesign --force --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" --sign "$IDENT" "$f"
done <<< "$BINS"

# ---------- 2/5 外层深签 ----------
echo "== 2/5 外层 --deep"
codesign --force --deep --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" --sign "$IDENT" "$APP"
codesign --verify --deep --strict "$APP" && echo "VERIFY-OK"

# ---------- 3/5 公证 ----------
echo "== 3/5 公证"
mkdir -p "$OUTDIR"
ZIP="/tmp/$(basename "$APP")-notarize.zip"
rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"
xcrun notarytool submit "$ZIP" --key "$HOME/.dsh/appstoreconnect/AuthKey_$API_KEY.p8" \
  --key-id "$API_KEY" --issuer "$ISSUER" --wait 2>&1 | tail -3

# ---------- 4/5 装订 + 验收 ----------
echo "== 4/5 装订 + spctl"
xcrun stapler staple "$APP"
spctl -a -vv -t exec "$APP" 2>&1 | tail -1

# ---------- 5/5 制品 + manifest ----------
echo "== 5/5 stapled 分发 zip + manifest"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$OUTDIR/$(basename "$APP" .app)-$VER-$STAMP-stapled.zip"
rm -f "$OUT"
ditto -c -k --keepParent "$APP" "$OUT"
CDHASH=$(codesign -dvvv "$APP" 2>&1 | grep -oE 'sha256=[0-9a-f]{40,}' | head -1 | cut -d= -f2)
SHA=$(shasum -a 256 "$OUT" | cut -d' ' -f1)
cat > "$OUT.manifest.json" << EOF
{"app":"$APP","bundle":"$BUNDLE","version":"$VER","zip":"$OUT",
 "zip_sha256":"$SHA","cdhash_sha256":"$CDHASH","macho_count":$COUNT,
 "identity":"$IDENT","built_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF
echo "OUT=$OUT"
echo "RELEASE-DONE"
