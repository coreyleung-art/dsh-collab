#!/bin/bash
# verify-cld-release.sh — CLD 发布制品验收门（2026-10-06 星桥 · P0 · v2）
# v2（2026-10-06 裁判审查后修复）：
#   ① 假绿根治：verify_pass 定义前置（v1 中 selftest 块调用时函数未定义，
#      command not found 被 2>/dev/null 吞掉 ⇒ 负控从未真跑仍报 PASS）
#   ② 冒号边界消除：macho_list 用 file -0 批处理 + python 解析（路径含冒号不再被截断）
#   ③ selftest 负控真打印（能看到 "FAIL: zip 不存在" 才算真红）
# 判据（全部运行时取数）：stapler 票据 / spctl accepted / codesign --verify --deep --strict /
#   全 Mach-O 带 TeamIdentifier / manifest sha256 匹配 / 版本单调
# 用法：
#   verify-cld-release.sh <stapled.zip> [installed-app路径]
#   verify-cld-release.sh --selftest          # 2 条负控必须真红
# 出口：0=PASS 1=FAIL 2=用法错
set -uo pipefail

# ---------- 工具函数（先定义） ----------
# Mach-O 清单：file -0 批处理输出 "path\0: desc\n"，python 拆包；冒号/空格路径安全
macho_list() { # $1 = .app 路径 → stdout 换行分隔的 Mach-O 全路径
  find "$1/Contents" -type f -print0 | xargs -0 file -0 2>/dev/null | python3 -c '
import sys
data = sys.stdin.buffer.read()
parts = data.split(b"\x00")
out = []
for i, part in enumerate(parts):
    if i == 0:
        continue  # 第一个 chunk 是首个路径本身
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

verify_pass() { # $1=zip 路径 $2=已装件路径(可省) → 0=PASS
  local ZIP="$1" INST="${2:-/Applications/CLD.app}"
  local FAILS=0
  [ -f "$ZIP" ] || { echo "FAIL: zip 不存在: $ZIP"; return 1; }

  # 1) manifest 存在 + sha256 匹配
  if [ -f "$ZIP.manifest.json" ]; then
    local EXP SHA
    EXP=$(python3 -c "import json;print(json.load(open('$ZIP.manifest.json')).get('zip_sha256',''))" 2>/dev/null)
    SHA=$(shasum -a 256 "$ZIP" | cut -d' ' -f1)
    if [ "$EXP" = "$SHA" ]; then echo "✓ zip sha256 匹配 manifest"; else echo "✗ zip sha256 不匹配 manifest ($SHA != $EXP)"; FAILS=$((FAILS+1)); fi
  else
    echo "✗ 无 manifest 文件（发布物必须附 manifest）"; FAILS=$((FAILS+1))
  fi

  # 2) 解包做签名验收
  local T; T=$(mktemp -d)
  ditto -x -k "$ZIP" "$T" 2>/dev/null
  local APP; APP=$(find "$T" -name "*.app" -maxdepth 2 | head -1)
  if [ -z "$APP" ]; then echo "✗ zip 内无 .app"; rm -rf "$T"; return 1; fi

  xcrun stapler validate "$APP" >/dev/null 2>&1 && echo "✓ stapler 票据有效" || { echo "✗ stapler 票据无效"; FAILS=$((FAILS+1)); }
  spctl -a -vv -t exec "$APP" >/dev/null 2>&1 && echo "✓ spctl accepted" || { echo "✗ spctl 拒"; FAILS=$((FAILS+1)); }
  codesign --verify --deep --strict "$APP" >/dev/null 2>&1 && echo "✓ codesign deep strict" || { echo "✗ codesign deep strict 失败"; FAILS=$((FAILS+1)); }

  # 3) 全 Mach-O 带团队签名（捕获输出再匹配，避免 SIGPIPE 竞态）
  local N=0 BAD=0 OUT f
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    N=$((N+1))
    OUT=$(codesign -dv "$f" 2>&1 || true)
    case "$OUT" in
      *"TeamIdentifier=XS7SMKFS42"*) ;;
      *) echo "✗ 无团队签名: ${f#"$T"/}"; BAD=$((BAD+1));;
    esac
  done < <(macho_list "$APP")
  echo "Mach-O 总数 $N，无团队签名 $BAD"
  [ "$BAD" = "0" ] || FAILS=$((FAILS+1))

  # 4) 版本单调（与已装件比）
  if [ -d "$INST" ]; then
    local VNEW VOLD
    VNEW=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist" 2>/dev/null || echo 0)
    VOLD=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$INST/Contents/Info.plist" 2>/dev/null || echo 0)
    if [ "$VNEW" != "$VOLD" ]; then echo "✓ 版本变化 $VOLD → $VNEW（换装候选）"; else echo "· 版本相同 $VOLD（若为升级请检查版本号）"; fi
  fi

  rm -rf "$T"
  [ "$FAILS" = "0" ]
}

# ---------- selftest（负控必须真红） ----------
if [ "${1:-}" = "--selftest" ]; then
  # 负控 1：不存在路径必须 FAIL（FAIL 行必须真打印）
  if verify_pass "/tmp/__nonexistent__.zip"; then
    echo "NEG1-FAILED(假绿): 不存在路径未被拒"; exit 1
  fi
  # 负控 2：sha 不匹配必须 FAIL
  T=$(mktemp -d); echo x > "$T/fake.zip"
  echo '{"zip_sha256":"deadbeef"}' > "$T/fake.zip.manifest.json"
  if verify_pass "$T/fake.zip"; then
    echo "NEG2-FAILED(假绿): 篡改 sha 未被拒"; rm -rf "$T"; exit 1
  fi
  rm -rf "$T"
  echo "VERDICT: PASS (2 负控真红)"
  exit 0
fi

# ---------- 主路径 ----------
if verify_pass "${1:-}" "${2:-/Applications/CLD.app}"; then
  echo "VERDICT: PASS"
  exit 0
else
  echo "VERDICT: FAIL"
  exit 1
fi
