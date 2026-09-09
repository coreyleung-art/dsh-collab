#!/usr/bin/env bash
# =============================================================================
# ensure-hub-symlinks.sh — web profile 符号链接守护脚本（v2，白名单语义）
# =============================================================================
# 目的：
#   dsh-plugin-agent-way 经 git URL / npm 安装进 web profile 时，pnpm 可能按
#   peerDeps 把 @deepseek-ai/* 解析为 profile 独立副本，与宿主 CLD runtime
#   形成「双实例」——cordis/dsh-tools 等服务变成两个物理模块，身份、事件、
#   服务注册全部错位。
#
#   安全机制（v1.3.0 审查确认）：
#     1. nodeLinker: hoisted + autoInstallPeers: false（pnpm-workspace.yaml）
#        → peer 不被自动复制到 profile
#     2. @deepseek-ai/* 符号链接 → CLD runtime 同一物理模块
#        → 插件与宿主共享同一份 cordis/dsh-tools/...
#     3. peerDeps 在 profile 中「缺失」是安全态：插件 bundle 从 CLD runtime
#        解析（resolveBundleDir 双锚点 installAnchor 优先），向上命中 runtime
#        单实例，比 profile 副本更干净。
#
#   本脚本（幂等）：
#     - 校验/重建既有符号链接 → CLD runtime（broken 修复）
#     - 扫描 peerDeps 白名单：发现 profile 独立副本且 runtime 同版本 → 替换为
#       符号链接（消除双实例）；缺失 → 不补建（保留 runtime 单实例解析）
#     - 校验 pnpm-workspace.yaml 关键配置
#
# 用法：
#   ./ensure-hub-symlinks.sh              # 检查 + 修复（幂等）
#   ./ensure-hub-symlinks.sh --check      # 只检查不修复，异常时 exit 1
#   ./ensure-hub-symlinks.sh --verbose    # 详细输出
#
# 退出码：
#   0 = 全部正常（或修复完成）
#   1 = --check 模式下发现异常
# =============================================================================

set -u

MODE="fix"
VERBOSE=0
for arg in "$@"; do
  case "$arg" in
    --check) MODE="check" ;;
    --verbose) VERBOSE=1 ;;
    *) echo "未知参数: $arg（支持 --check / --verbose）" >&2; exit 2 ;;
  esac
done

log()  { [ "$VERBOSE" = "1" ] && echo "[info] $*"; }
warn() { echo "[warn] $*" >&2; }
fail() { echo "[FAIL] $*" >&2; }

# --- 路径推导 ---------------------------------------------------------------
# CLD runtime 双锚点（与 dsh 插件加载器 resolveBundleDir 一致）
INSTALL_ANCHOR="/Applications/CLD.app/Contents/Resources/dsh-runtime/runtime"
PROFILE_DIR="${DSH_PROFILE_DIR:-$HOME/.dsh/profiles/web}"
RUNTIME_NM="$INSTALL_ANCHOR/node_modules/@deepseek-ai"
PROFILE_NM="$PROFILE_DIR/node_modules/@deepseek-ai"

# 允许环境变量覆盖（三端路径可能不同）
RUNTIME_NM="${DSH_RUNTIME_NM:-$RUNTIME_NM}"
PROFILE_NM="${DSH_PROFILE_NM:-$PROFILE_NM}"

# dsh-plugin-agent-way v1.3.0 的 11 个 peerDeps（白名单）
PEER_DEPS="cordis dsh-tools dsh-client-runtime dsh-agent dsh-session-persistence dsh-settings dsh-system-prompt dsh-host-webserver dsh-agent-default-model dsh-agent-presets dsh-client-locale"

echo "═══ web profile 符号链接守护 ═══"
echo "  runtime  @deepseek-ai: $RUNTIME_NM"
echo "  profile @deepseek-ai:  $PROFILE_NM"
echo "  模式: $MODE"

# --- 前置校验 ---------------------------------------------------------------
[ -d "$RUNTIME_NM" ] || { fail "CLD runtime 目录不存在: $RUNTIME_NM"; exit 1; }
[ -d "$PROFILE_NM" ] || { fail "profile 目录不存在: $PROFILE_NM"; exit 1; }

# pnpm-workspace.yaml 关键配置校验
WS="$PROFILE_DIR/pnpm-workspace.yaml"
if [ -f "$WS" ]; then
  grep -q "^nodeLinker: hoisted" "$WS"   || warn "pnpm-workspace.yaml 缺少 nodeLinker: hoisted"
  grep -q "^autoInstallPeers: false" "$WS" || warn "pnpm-workspace.yaml 缺少 autoInstallPeers: false"
  log "pnpm-workspace.yaml 配置已校验: $WS"
else
  warn "未找到 $WS（自动安装 peer 可能复制独立副本）"
fi

# --- 阶段 1：校验/重建既有符号链接（不限于白名单，保留平台原有 34 个） ------
BROKEN=0; FIXED=0; OK=0
for link in "$PROFILE_NM"/*; do
  [ -L "$link" ] || continue
  name="$(basename "$link")"
  dest="$(readlink "$link")"
  if [ -e "$dest" ]; then
    OK=$((OK+1))
  else
    warn "broken 符号链接: $name → $dest"
    if [ "$MODE" = "fix" ]; then
      rm "$link"
      # 若 runtime 有同名模块则重建，否则保持删除
      if [ -d "$RUNTIME_NM/$name" ]; then
        ln -s "$RUNTIME_NM/$name" "$link"
        FIXED=$((FIXED+1))
        log "  已重建: $name → runtime"
      else
        FIXED=$((FIXED+1))
        log "  runtime 无此模块，已删除 broken 链接: $name"
      fi
    else
      BROKEN=$((BROKEN+1))
    fi
  fi
done

# --- 阶段 2：peerDeps 白名单扫描（防双实例） --------------------------------
PEER_ISSUE=0; PEER_FIXED=0; PEER_OK=0
for p in $PEER_DEPS; do
  target="$PROFILE_NM/$p"
  if [ -L "$target" ]; then
    PEER_OK=$((PEER_OK+1))
  elif [ -d "$target" ]; then
    # 独立副本 → 若 runtime 同版本则替换为符号链接；版本不同则告警保留
    rv=$(node -e "console.log(require('$RUNTIME_NM/$p/package.json').version)" 2>/dev/null || echo "?")
    pv=$(node -e "console.log(require('$target/package.json').version)" 2>/dev/null || echo "?")
    if [ "$rv" = "$pv" ] && [ "$rv" != "?" ]; then
      warn "双实例隐患: $p profile 独立副本 v$pv = runtime v$rv（应符号链接化）"
      if [ "$MODE" = "fix" ]; then
        mv "$target" "$target.pnpmcopy-bak-$(date +%s)"
        ln -s "$RUNTIME_NM/$p" "$target"
        PEER_FIXED=$((PEER_FIXED+1))
        log "  已替换为符号链接: $p"
      else
        PEER_ISSUE=$((PEER_ISSUE+1))
      fi
    else
      log "peer $p: profile 独立副本 v$pv ≠ runtime v$rv（版本差异，保留副本，需人工判断）"
    fi
  else
    # 缺失 → 安全态（插件从 CLD runtime 解析单实例），不补建
    log "peer $p: profile 缺失（安全态，走 runtime 单实例解析）"
    PEER_OK=$((PEER_OK+1))
  fi
done

# --- 汇总 -------------------------------------------------------------------
echo "═══ 结果 ═══"
echo "  既有符号链接: $OK 正常 / $FIXED 修复 / $BROKEN 异常"
echo "  peerDeps(11): $PEER_OK 安全 / $PEER_FIXED 已修复 / $PEER_ISSUE 需人工"
if [ "$MODE" = "check" ] && { [ "$BROKEN" -gt 0 ] || [ "$PEER_ISSUE" -gt 0 ]; }; then
  echo "  → 请运行本脚本（无 --check）修复" >&2
  exit 1
fi
echo "  （$INSTALL_ANCHOR 与 $PROFILE_DIR 保持同一物理模块，双实例隐患已受控）"
exit 0
