#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
# pre-commit-rule-parser-check.sh —— 规则解析器隐含假设的【提交时】挂点
#
# ★ 出处：裁判 `session-1ffded95` 2026-10-10 裁决（选项 A 的【限定范围 + 非阻塞】形式）
#   原话：
#     「若 staged 变更【含】rules-registry/RULES.md
#        ⇒ 跑 rule-parser-assumption-check.py
#        ⇒ INCONSISTENT ⇒ 打印警告（★ exit 0，不阻断提交）
#      否则 ⇒ 静默退出」
#     · 限定范围：只在 RULES.md 变更时跑 ⇒ 回应「会影响所有提交者」的顾虑
#     · 非阻塞：**解析器不一致不应阻碍正常开发**（且它不是「拒绝提交」的理由 —— 修法由属主定）
#     · 同时保留 D（一行命令）作为基线 —— A 需动 git 配置，A 未落地时 D 是兜底
#     · 不选 B/C（launchd）：它们**引入新的失效面** —— 谁保证定时任务活着？递归。
#
# ★★ 判据（裁判修正的措辞）：**不追求「必然发生」（那是【性质】，不可判）；
#    选【新增依赖最少】的挂点（那是【条件】，可判）。**
#      git hook 依赖链 = `git commit`（已存在的动作）⇒ 新增 0
#      launchd 依赖链  = launchd 运行 + plist 有效 + 静默失效检测 ⇒ 新增 3
#
# ★★★ 本脚本【不自行安装】—— 安装要改 `dsh-collab/.git/hooks/`，那是【他人产物】。
#     安装方式（由属主决定）：
#       ln -sf ../../devices/dsh-plugin-rule-parser-assumption-check/pre-commit-rule-parser-check.sh \
#              ~/dsh-collab/.git/hooks/pre-commit
#     卸载：rm ~/dsh-collab/.git/hooks/pre-commit
#     ★ 若 hooks 目录已有 pre-commit（本机此前无 hook 先例），须【追加调用】而非覆盖。
#
# 退出码：★ **恒 0**（非阻塞 —— 裁判裁决）。警告写 stderr，不污染 stdout。
# ════════════════════════════════════════════════════════════════════════════
set -uo pipefail

REPO="${DSH_COLLAB_ROOT:-$HOME/dsh-collab}"
GATE="$REPO/devices/dsh-plugin-rule-parser-assumption-check/rule-parser-assumption-check.py"
WATCH="rules-registry/RULES.md"

# ── ① 限定范围：只在 RULES.md 处于 staged 变更时跑 ──
if ! git -C "$REPO" diff --cached --name-only 2>/dev/null | grep -qx "$WATCH"; then
  exit 0          # ★ 静默退出（不打扰其它提交）
fi

# ── ② 前置检查：门在不在、跑不跑得起来 ──
if [ ! -f "$GATE" ]; then
  echo "⚠ [rule-parser-assumption] 门不存在，跳过：$GATE" >&2
  exit 0          # ★ 非阻塞：门缺失不应阻碍提交（但也【不静默】）
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "⚠ [rule-parser-assumption] python3 不可用，跳过" >&2
  exit 0
fi

# ── ③ 跑门（★ 捕获退出码但【不据以阻断】）──
OUT="$(python3 "$GATE" 2>&1)"
RC=$?

if [ "$RC" -eq 1 ]; then
  # INCONSISTENT ⇒ 打印警告，★ 但 exit 0（不阻断）
  echo "" >&2
  echo "⚠ [rule-parser-assumption] 本次提交改了 $WATCH，而检测到【解析器与其输入分布的隐含假设已被打破】：" >&2
  echo "$OUT" | sed -n '/INCONSISTENT/,/^\s*$/p' | head -12 | sed 's/^/    /' >&2
  echo "    ⇒ ★ 这【不阻断】你的提交（裁判裁决：解析器不一致不应阻碍正常开发）。" >&2
  echo "    ⇒ 修哪个解析器由属主定；本门只检测不修改。" >&2
  echo "    ⇒ 完整输出：python3 $GATE" >&2
  echo "" >&2
elif [ "$RC" -eq 2 ]; then
  echo "⚠ [rule-parser-assumption] 门报用法/权威源错误（exit 2），跳过。详情：python3 $GATE" >&2
fi
# RC == 0 ⇒ 一致，无需提示

exit 0    # ★ 恒 0：非阻塞
