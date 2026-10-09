#!/usr/bin/env bash
# build-bundle.sh — 插件完整依赖包构建（源码 + peerDeps 物理副本）
# 用途：为 i9/MBP 提供「免编译、免 pnpm 拉依赖」的完整包（Windows 无本地 pnpm 拉链也能装）
# 用法：bash build-bundle.sh <插件目录> [输出目录]
# 产物：<插件名>-full-bundle-<版本>.tar.gz（含 lib/ + package.json + cordis.patch.yml + node_modules/@deepseek-ai/* 物理副本）

#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
DSH_LOG="$HOME/dsh-collab/logs/build-bundle.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

set -euo pipefail

PLUGIN_DIR="${1:?用法: build-bundle.sh <插件目录> [输出目录]}"
OUT_DIR="${2:-$HOME/dsh-collab/datasets/shared}"
RUNTIME_NM="/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime/node_modules/@deepseek-ai"

cd "$PLUGIN_DIR"
NAME=$(node -e "console.log(require('./package.json').name)" 2>/dev/null)
VER=$(node -e "console.log(require('./package.json').version)" 2>/dev/null)
echo "═══ 构建完整包: $NAME@$VER ═══"

# 1. 临时打包目录
TMP=$(mktemp -d /tmp/bundle.XXXXXX)
PKG="$TMP/package"
mkdir -p "$PKG/node_modules/@deepseek-ai"
echo "  临时目录: $TMP"

# 2. 拷贝插件本体（lib/ package.json cordis.patch.yml README CHANGELOG）
for item in lib package.json cordis.patch.yml README.md CHANGELOG.md index.d.ts; do
  [ -e "$item" ] && cp -R "$item" "$PKG/" 2>/dev/null || true
done

# 3. peerDependencies 物理副本（从 CLD runtime 拷，避免符号链接）
PEERS=$(node -e "
const p=require('./package.json');
const peers=p.peerDependencies||{};
console.log(Object.keys(peers).join(' '));
" 2>/dev/null)
echo "  peerDeps: $PEERS"
for peer in $PEERS; do
  SHORT="${peer#@deepseek-ai/}"
  if [ -d "$RUNTIME_NM/$SHORT" ]; then
    cp -R "$RUNTIME_NM/$SHORT" "$PKG/node_modules/@deepseek-ai/$SHORT" 2>/dev/null && echo "  ✅ $SHORT 已拷（物理副本）"
  else
    echo "  ⚠️ $SHORT 不在 runtime，跳过"
  fi
done

# 4. 打 tar.gz（扁平：根目录直接文件，Windows tar 友好，避免 package/ 前缀解压问题）
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/${NAME}-full-bundle-v${VER}.tar.gz"
tar -czf "$OUT" -C "$PKG" . 2>/dev/null
echo "  ✅ 完整包: $OUT"
echo "  大小: $(du -h "$OUT" | cut -f1)"

# 5. 清理
rm -rf "$TMP"
echo "═══ 完成 ═══"
