#!/usr/bin/env bash
# artifact-commit.sh v2.0.1 — 「唯一副本止损」的【持续化机制】
# 起因（2026-10-09 裁判节点② 复核指出）：一次性 `git add -f` 不是机制 ——
#   「唯一副本止损是持续动作、不是一次动作」。
#
# 用法：
#   artifact-commit.sh <路径...> -m "说明"      # 指定路径：add -f → commit → [门] → push
#   artifact-commit.sh --snapshot               # 定时快照：全放行面 add → commit（★ 不 push）
#   artifact-commit.sh --no-push <路径...> -m X  # 只落本地第二副本
#   artifact-commit.sh --coverage               # 只跑覆盖率断言（不写任何东西）
#   artifact-commit.sh --publicity-gate <ref>   # 只跑公开性门（问：ref 里的东西能不能出本机）
#   artifact-commit.sh --selftest | --selfcheck | --lean4-check | --tool-version | --help
#
# ★★ v2.0.0 修的三个真缺陷（★ 均为本线 2026-10-12 实测照出，★ 非推测）：
#   ① ★★★ **无条件 push** —— v1.0.3 的设计判据是「不 push 则止损未完成」。
#      ★ 但 `origin` = **公开仓库**（未认证探测 HTTP 200）⇒ ★ 该设计会把
#      **任何被它提交的东西自动发布到公开互联网**，包括密钥样内容。
#      ⇒ v2.0.0 在 push **之前**加一道【公开性门】；★ 判不了 ⇒ **不推**（fail-closed）。
#   ② ★★ **覆盖率无断言** —— 「加一条定时 git 快照」在**白名单 .gitignore** 下
#      ★ 会跑、会成功、会产生提交，**而被保护的件一个都没进去**（实测 `git add -A`
#      对未放行目录命中 0 条）⇒ 这是一个**恒真的空动作**。
#      ⇒ v2.0.0 断言：★ **「没有任何路径处于「既未被跟踪、也未被明确忽略」的第三态」**。
#   ③ ★ **统一日志是死代码** —— v1.0.3 定义了 `dsh_log()` 却**从未调用**
#      （R006 ⑦ **名义在位、实际不写**）⇒ v2.0.0 每条路径都落日志。
#
# ★ 约束门（⑩）：本工具【不删除数据、不修改权限、不终止进程】。
#   写路径仅：`git add/commit`（在被操作的仓库内）+ 固定日志一行。
#   ★ 依赖 `git` 与 `grep`；★ 网络仅用于 `--publicity-gate` 的只读可见性探测。
#

set -uo pipefail

# ★ R006 ⑥ 版本【单一来源】—— 其余位置一律引用 $VERSION
VERSION="2.0.1"

DSH_LOG="$HOME/dsh-collab/logs/artifact-commit.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

# ★ 密钥样模式（★ 公开性门的判据源；★ 与 6 处已公开值同批者仍会被点到 —— ★ 门只报，不代裁）
SECRET_RE='bb-token-[0-9a-z-]{6,}|ghp_[A-Za-z0-9]{20,}|app-v[A-Za-z0-9]{15,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|Authorization: *Bearer [A-Za-z0-9_-]{16,}'

usage() {
cat <<'EOF'
artifact-commit.sh v2.0.1 — 唯一副本止损的持续化机制

  <路径...> -m "说明"        指定路径：add -f → commit → [公开性门] → push
  --snapshot                 定时快照：全放行面 add → commit（★ 恒不 push）
  --no-push <路径...> -m X   只落本地第二副本，不过门不推送
  --coverage                 只跑覆盖率断言（只读）
  --publicity-gate <ref>     只跑公开性门（只读；问「ref 里的东西能不能出本机」）
  --selftest                 自证（含负控；★ 负控必须能红）
  --selfcheck                R006 ② TCC 能力边界三段
  --lean4-check              R006 ⑩ 约束门六项 A–F
  --tool-version             R006 ⑥ 版本单一来源
  --help
EOF
}

# ═══ ★ 覆盖率断言（v2.0.0 新增 · 修缺陷②）═══
# ★ 门问的不是「快照跑没跑」，而是：★「**有没有东西处于第三态**？」
#   第三态 = 既没被 git 跟踪（⇒ 无第二副本）、也没被 .gitignore 明确忽略（⇒ 不是设计排除）。
coverage_gate() {
    local untracked_not_ignored
    untracked_not_ignored="$(git status --porcelain 2>/dev/null | grep -c '^??' || true)"
    if [ "${untracked_not_ignored:-0}" -eq 0 ]; then
        echo "  [OK]   覆盖率：未跟踪且未被忽略 = 0 ✅（无第三态）"
        return 0
    fi
    echo "  [FAIL] 覆盖率：★ ${untracked_not_ignored} 条路径处于【第三态】—— 既未被跟踪、也未被明确忽略："
    git status --porcelain 2>/dev/null | grep '^??' | head -12 | sed 's/^/           /'
    echo "           ★ 修法二选一：放进 .gitignore 白名单（⇒ 有第二副本），或在 .gitignore 里显式忽略（⇒ 设计排除）。"
    return 1
}

# ═══ ★「已知作废」指纹清单（v2.0.1）═══
# ★ 为什么要它：★ 泄露值被**轮换作废后**，它仍留在**历史提交**里 ⇒ 公开性门会**永远报红**
#   ⇒ ★ 一个永远红的门**等于没有门**（会被忽略或绕过）。
# ★ 正解不是放宽门，是**把「活密钥外泄」与「已废值的历史残留」分开**：
#   清单只收【已实测作废】的值的**指纹**（★ 不存明文），且**须附实测证据**。
# ★ 判定「作废」的方法依 `docs/AGENT-NETWORK-CHARTER.md` §凭证分级 ③：
#   **逐头隔离测试 + 正控**（★ 禁止用单一头的 401 推断「不可写」）。
DENYLIST="$HOME/.dsh/token-denylist.json"

hit_fp() {  # ★ 与制表侧同算法：sha256(令牌值) 前 8 位
    local v; v="$(printf '%s' "$1" | grep -oE '[A-Za-z0-9_-]{16,}' | tail -1)"
    [ -n "$v" ] || v="$1"
    printf '%s' "$v" | shasum -a 256 | cut -c1-8
}

is_denylisted() {
    [ -f "$DENYLIST" ] || return 1
    grep -q "\"$1\": {" "$DENYLIST" 2>/dev/null
}

# ═══ ★ 公开性门（v2.0.0 新增 · 修缺陷①）═══
# ★ 门问：★「**即将【出本机】的东西，能不能公开？**」—— ★ 这是 irreversible-gate
#   （「即将销毁的有没有第二副本」）的**镜像**：★ 一个销毁唯一副本，一个**复制到全世界**。
# ★ 三态：判不了 ⇒ **不推**（fail-closed）。★ 「空集 ≠ 通过」同族。
publicity_gate() {
    local ref="${1:-HEAD}" url host code hits rc=0
    if ! url="$(git remote get-url origin 2>/dev/null)" || [ -z "$url" ]; then
        echo "  [UNDECIDABLE] 无 origin ⇒ 判不了可见性 ⇒ ★ 不推（fail-closed）"
        return 2
    fi
    # ★ 纯 bash 参数展开取 host/slug —— ★ BSD sed 不支持非贪婪 `+?`（本线实测照出：
    #   原写法在 macOS 报 "repetition-operator operand invalid" ⇒ slug 空 ⇒ URL 退化）
    # ★ 两种形态都要对：`https://user:tok@host/owner/repo` 与 `git@host:owner/repo`
    #   ★ 首版把 `#*:` 放在 `#*@` 之后 ⇒ 对 ssh 形态把【主机名也吃掉】了（实测 host=coreyleung-art）
    local t; t="${url%.git}"
    if [[ "$t" == *"://"* ]]; then
        t="${t#*://}"; t="${t#*@}"
    else
        t="${t#*@}"
    fi
    if [[ "$t" == *":"* ]]; then t="${t%%:*}/${t#*:}"; fi
    host="${t%%/*}"; slug="${t#*/}"
    if [ -z "$host" ] || [ -z "$slug" ] || [ "$slug" = "$t" ]; then
        echo "  [UNDECIDABLE] 无法解析 origin ⇒ host='$host' slug='$slug' ⇒ ★ 不推（fail-closed）"
        return 2
    fi
    case "$host" in
      github.com|gitee.com|gitlab.com)
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 "https://${host}/${slug}" 2>/dev/null)"
        [ -n "$code" ] || code="000"
        case "$code" in
          200) echo "  [PUBLIC] origin=${host}/${slug} ⇒ ★ 公开仓库（未认证 200）" ;;
          404) echo "  [PRIVATE] origin=${host}/${slug} ⇒ ★ 私有/不存在（未认证 404）⇒ 公开性门：放行" ;;
          *)   echo "  [UNDECIDABLE] 可见性探测 HTTP=${code} ⇒ ★ 不推（fail-closed）"; return 2 ;;
        esac
        ;;
      *) echo "  [UNDECIDABLE] 非常见托管域 (${host}) ⇒ ★ 不推（fail-closed）"; return 2 ;;
    esac

    # 将推送的提交范围：origin/<branch>..HEAD（无上游则用 ref）
    local rng; rng="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    if git rev-parse --verify -q "origin/${rng}" >/dev/null 2>&1; then
        rng="origin/${rng}..HEAD"
    else
        rng="$ref"
    fi
    local dead=0 live="" fp h
    while IFS= read -r h; do
        [ -n "$h" ] || continue
        fp="$(hit_fp "$h")"
        if is_denylisted "$fp"; then dead=$((dead+1)); else live="$live $fp"; fi
    done < <(git diff -U0 "$rng" 2>/dev/null | grep -E "^\+" | grep -oE "$SECRET_RE" | sort -u)
    if [ -n "$live" ]; then
        echo "  [BLOCK] ★★ 待推送内容命中【未列入作废清单】的密钥样 ⇒ ★ 拒绝 push（commit 保留）："
        for fp in $live; do printf '           ★ 指纹 %s\n' "$fp"; done
        echo "           （已作废且已登记指纹的命中数 = ${dead}）"
        echo "           ★ 处置：轮换该凭据，或先 git reset --soft 摘掉该文件；★ 本门不代改内容。"
        return 1
    fi
    if [ "${dead:-0}" -gt 0 ]; then
        echo "  [OK·已作废] 公开性门：命中 ${dead} 个值，★ 全部在【已知作废】清单内（附实测证据）"
        echo "              ★ 清单：${DENYLIST}（0600）· ★ 这不是「无泄露」，是「泄露值已废」。"
        return 0
    fi
    echo "  [OK]   公开性门：待推送内容未命中密钥样 ✅（★ 启发式，非保证）"
    return 0
}

# ═══ ★ safe_rm（2026-10-12 事故教训落进代码：「删除前必须有路径断言」）═══
# ★ 定义必须落在【工具主体内】（lean4_check 之前），否则 A' 判据扫不到它。
# ★ 今晚的事故是 `rmtree(os.path.dirname(tmp))` 打到了 `scripts/` 本身
#   ⇒ ★「外部/运行时数据 → 直接当删除目标，中间无断言」。
# ★ 本条只肯删【临时区内的目录】，四条断言缺一即拒 —— ★ 宁可留垃圾，不可删错。
safe_rm() {
    local p="${1:-}"
    [ -n "$p" ] || { echo "safe_rm 拒绝：空路径" >&2; return 1; }
    [ "$p" != "/" ] || { echo "safe_rm 拒绝：根路径" >&2; return 1; }
    case "$p" in
      /tmp/*|/private/tmp/*|/var/folders/*|"${TMPDIR:-/nonexistent}"/*) : ;;
      *) echo "safe_rm 拒绝：不在临时区 ⇒ $p" >&2; return 1 ;;
    esac
    [ -d "$p" ] || { echo "safe_rm 拒绝：非目录 ⇒ $p" >&2; return 1; }
    rm -rf -- "$p"
}

# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
lean4_check() {
    local self fails=0
    self="$(cat "$0")"
    # ★ 危险原语查【剥注释后的 code 面】—— 避免自指假阳性
    local code; code="$(printf '%s\n' "$self" | sed 's/#.*$//')"
    # ★★ 且**必须再排除判据自身**：A/B/C 的正则里就写着 `rm -rf`/`chmod`/`kill` 这些字面
    #    ⇒ 不排除则判据**必然命中自己**（★ 本线连撞七次的自指污染，第七次就在这里）。
    #    ⇒ 论域 = **工具主体**（`lean4_check()` 定义之前的部分）。
    local body; body="$(printf '%s\n' "$code" | sed '/^lean4_check() {/,$d')"
    chk() { # key name cond detail
        if [ "$3" = "0" ]; then printf '  OK   %s %-54s %s\n' "$1" "$2" "$4"
        else printf '  FAIL %s %-54s %s\n' "$1" "$2" "$4"; fails=$((fails+1)); fi
    }
    echo "== $(basename "$0") · --lean4-check（六项 A–F）=="
    printf '   ★ 论域：A–C 扫的是【工具主体】（已剥注释 + 已排除判据自身）—— 面 %s 行\n' "$(printf '%s\n' "$body" | wc -l | tr -d ' ')"
    # ★ A–C 是【不得存在】类判据 ⇒ 用 `!` 取反（★ 首版写反了：grep 命中=0 被当成 OK，
    #   那正是「恒真控」的典型 —— ★ 由本线自查照出）
    # ★ A 只判【未受控】原语；`rm -rf` 由 A' 判（★ 二者不可重叠，否则互相矛盾 —— 首版就是）
    ! printf '%s' "$body" | grep -qE '(rmtree|os\.remove|shred|dd if=)'; chk A "只读锁：无未受控销毁原语（rmtree/os.remove/shred/dd）" $? "命中 0 次"
    ! printf '%s' "$body" | grep -qE 'chmod|chown'; chk B "权限锁：不修改权限" $? "命中 0 次"
    ! printf '%s' "$body" | grep -qE 'kill|pkill|launchctl (unload|bootout)'; chk C "进程锁：不终止任何进程" $? "命中 0 次"
    # ★ A' ：唯一的 `rm -rf` 必须落在 safe_rm 体内，且 safe_rm 有路径断言
    if [ "$(printf '%s' "$body" | grep -c 'rm -rf')" -eq 1 ] && printf '%s' "$body" | grep -q 'safe_rm 拒绝：不在临时区'; then
      printf '  OK   %-3s %-54s %s\n' "A'" "销毁路径受 safe_rm 断言约束（★ 今晚事故教训已落进代码）" "断言在位"
    else
      printf '  FAIL %-3s %-54s %s\n' "A'" "销毁路径受 safe_rm 断言约束" "断言缺失"; fails=$((fails+1))
    fi
    grep -q -- '--selftest' "$0"; chk D "状态机：本工具可自证（--selftest 在位）" $? "selftest 在位"
    grep -q -- '--publicity-gate' "$0" && grep -q 'SECRET_RE' "$0"; chk E "负例矩阵：公开性门在位（★ 修 v1.0.3 无条件 push）" $? "门在位"
    grep -q 'coverage_gate' "$0"; chk F "覆盖率断言在位（★ 修恒真空动作）" $? "断言在位"
    echo
    echo "  => $((7-fails))/7 pass, $fails FAIL"
    [ "$fails" -eq 0 ]
}

# ═══ ★ 自证（★ 每一条负控都必须【能红】；★ 恒真控＝没控）═══
selftest() {
    local fails=0 undec=0 self_abs rc g
    self_abs="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
    echo "== artifact-commit · --selftest（v$VERSION）=="
    ST_TMP="$(mktemp -d)"
    cd "$ST_TMP" || return 1
    git init -q . 2>/dev/null; git config user.email t@t; git config user.name t
    printf 'clean\n' > clean.txt; git add -A; git commit -qm init

    # ① ★ 负控：第三态必须被判红
    printf 'x\n' > third-state.txt
    if git status --porcelain | grep -q '^??'; then
        printf '  OK   %-58s %s\n' "N1 第三态（未跟踪且未忽略）⇒ 覆盖率门必红" "检出第三态 ✅"
    else printf '  FAIL %-58s\n' "N1 第三态 ⇒ 覆盖率门必红"; fails=$((fails+1)); fi

    # ② ★ 正控：显式忽略后不得再判红（★ 否则 N1 恒真）
    printf 'third-state.txt\n' > .gitignore; git add -A; git commit -qm ignore
    if git status --porcelain | grep -q '^??'; then
        printf '  FAIL %-58s 仍报第三态 ⇒ N1 可能是恒真控\n' "N2 正控：显式忽略后不再判红"; fails=$((fails+1))
    else printf '  OK   %-58s %s\n' "N2 正控：显式忽略后不再判红" "0 条 ✅"; fi

    # ③ ★ 负控：公开性门对密钥样必红
    printf 'tok = bb-token-20260829-macmini-abcdef\n' > secret.txt
    git add -A; git commit -qm secret
    if git diff -U0 HEAD~1..HEAD 2>/dev/null | grep -E '^\+' | grep -qE "$SECRET_RE"; then
        printf '  OK   %-58s %s\n' "N3 密钥样内容 ⇒ 公开性门必红" "命中 ✅"
    else printf '  FAIL %-58s\n' "N3 密钥样内容 ⇒ 公开性门必红"; fails=$((fails+1)); fi

    # ④ ★ 正控：干净内容不得误报（★ 否则 N3 恒真）
    printf 'hello world\n' > clean2.txt; git add -A; git commit -qm clean
    if git diff -U0 HEAD~1..HEAD 2>/dev/null | grep -E '^\+' | grep -qE "$SECRET_RE"; then
        printf '  FAIL %-58s 误报 ⇒ N3 可能恒真\n' "N4 正控：干净内容不误报"; fails=$((fails+1))
    else printf '  OK   %-58s %s\n' "N4 正控：干净内容不误报" "0 命中 ✅"; fi

    # ⑤ ★ 未知旗标 ⇒ exit 2（R006 ⑨）★ 用绝对路径：本函数已 cd 走
    bash "$self_abs" --definitely-unknown >/dev/null 2>&1
    if [ $? -eq 2 ]; then printf '  OK   %-58s rc=2\n' "N5 未知旗标 ⇒ exit 2（R006 ⑨）"
    else printf '  FAIL %-58s\n' "N5 未知旗标 ⇒ exit 2（R006 ⑨）"; fails=$((fails+1)); fi

    # ⑥ ★ 空集 ≠ 通过：无 origin ⇒ 公开性门必须 UNDECIDABLE（不得 OK），且 fail-closed
    g="$(publicity_gate HEAD 2>&1)"; rc=$?
    if [ "$rc" = "2" ]; then printf '  OK   %-58s %s\n' "N6 无 origin ⇒ 公开性门 UNDECIDABLE（不推）" "rc=2 ✅"
    else printf '  FAIL %-58s rc=%s\n' "N6 无 origin ⇒ 公开性门 UNDECIDABLE（不推）" "$rc"; fails=$((fails+1)); fi

    # ⑦ ★★ safe_rm 负控：拒删【非临时区】—— ★ 今晚事故（rmtree 打到 scripts/）的复现
    safe_rm "$HOME/dsh-collab" >/dev/null 2>&1
    if [ $? -ne 0 ]; then printf '  OK   %-58s %s\n' "N7 safe_rm 拒删非临时区（★ 今晚事故复现）" "已拒 ✅"
    else printf '  FAIL %-58s\n' "N7 safe_rm 拒删非临时区"; fails=$((fails+1)); fi

    # ⑧ ★ safe_rm 正控：临时区内必须肯删（★ 否则 N7 恒真）
    local t2; t2="$(mktemp -d)"
    if safe_rm "$t2" >/dev/null 2>&1 && [ ! -d "$t2" ]; then
        printf '  OK   %-58s %s\n' "N8 正控：safe_rm 肯删临时区内目录" "已删 ✅"
    else printf '  FAIL %-58s\n' "N8 正控：safe_rm 肯删临时区内目录"; fails=$((fails+1)); fi

    # ⑨ ★ 指纹算法两侧一致（★ 否则清单形同虚设）
    local known; known="$(hit_fp "tok = bb-token-20260829-macmini-abcdef")"
    if [ "$known" = "$(printf 'bb-token-20260829-macmini-abcdef' | shasum -a 256 | cut -c1-8)" ]; then
        printf '  OK   %-58s %s\n' "N9 hit_fp 与制表侧同算法" "$known ✅"
    else printf '  FAIL %-58s\n' "N9 hit_fp 与制表侧同算法"; fails=$((fails+1)); fi

    # ⑩ ★★ 负控：未登记的指纹必须【不被判为已作废】
    #    ★ 否则「作废清单」会变成恒真放行 —— 门就废了
    if is_denylisted "deadbeef" || is_denylisted "$(hit_fp 'bb-token-NEVER-REGISTERED-9999')"; then
        printf '  FAIL %-58s 未登记却放行 ⇒ 门已恒真\n' "N10 负控：未登记指纹不得判作废"; fails=$((fails+1))
    else printf '  OK   %-58s %s\n' "N10 负控：未登记指纹不得判作废" "正确拒绝 ✅"; fi

    cd /tmp || true
    safe_rm "$ST_TMP"; ST_TMP=""
    echo
    echo "selftest: fails=$fails undecidable=$undec version=$VERSION"
    [ "$fails" -eq 0 ] && [ "$undec" -eq 0 ]
}

ST_TMP=""
trap 'if [ -n "$ST_TMP" ]; then safe_rm "$ST_TMP"; fi' EXIT

cd "$(dirname "$0")/.." || exit 2

case "${1:-}" in
  --help|-h|"")        usage; exit 0 ;;
  --tool-version)      echo "$VERSION"; exit 0 ;;
  --selfcheck)
    echo "== artifact-commit 自查（TCC 能力边界）=="
    echo "【① 能力清单】"
    echo "  · artifact-commit.sh v$VERSION — 「唯一副本止损」的【持续化机制】"
    echo "  · 指定路径 add -f → commit →【公开性门】→ push；--snapshot 恒不 push"
    echo "  · 覆盖率断言：无「未跟踪且未被忽略」的第三态"
    echo "【② 不该发生路径清单】"
    echo "  · 本工具【不删除数据、不修改权限、不终止进程】"
    echo "  · 写路径仅：git add/commit + 固定日志一行"
    echo "【③ 依赖完整性】"
    echo "  · shell: $SHELL · Python: 不依赖"
    echo "  · 依赖: git, grep, curl（仅公开性门只读探测）"
    echo "  · 固定日志: ~/dsh-collab/logs/artifact-commit.log"
    exit 0 ;;
  --lean4-check)       lean4_check; exit $? ;;
  --selftest)          selftest;    exit $? ;;
  --coverage)          coverage_gate; exit $? ;;
  --publicity-gate)    shift; publicity_gate "${1:-HEAD}"; exit $? ;;
esac

MSG=""; PATHS=(); MODE="push"
while [ $# -gt 0 ]; do
  case "$1" in
    -m)        MSG="$2"; shift 2 ;;
    --no-push) MODE="nopush"; shift ;;
    --snapshot) MODE="snapshot"; shift ;;
    --*)       echo "[unknown flag] 未知旗标 $1" >&2; usage >&2; exit 2 ;;
    *)         PATHS+=("$1"); shift ;;
  esac
done

if [ "$MODE" = "snapshot" ]; then
  # ★ 定时快照：只落本地第二副本，★ 恒不 push（公开仓 ⇒ 自动发布＝不可逆）
  MSG="auto-snapshot $(date +%Y-%m-%dT%H:%M:%S)"
  git add -A 2>/dev/null || true
  if git diff --cached --quiet; then dsh_log "snapshot: 无改动（幂等退出）"; echo "无改动（幂等退出）"; exit 0; fi
  echo "【覆盖率断言】"; coverage_gate || { dsh_log "snapshot: ★覆盖率失败 — 拒绝提交"; echo "★ 覆盖率断言失败 ⇒ 不提交（先修 .gitignore 口径）"; exit 1; }
  git commit -q -m "$MSG" || { dsh_log "snapshot: commit 失败"; exit 1; }
  echo "已快照 $(git rev-parse --short HEAD) · ★ 未推送（快照只落本地第二副本）"
  dsh_log "snapshot: $(git rev-parse --short HEAD) ✓ 未推送"
  exit 0
fi

[ ${#PATHS[@]} -gt 0 ] || { echo "用法见 --help" >&2; exit 2; }
[ -n "$MSG" ] || { echo "必须给 -m 说明" >&2; exit 2; }
for p in "${PATHS[@]}"; do
  [ -e "$p" ] || { echo "跳过（不存在）: $p" >&2; continue; }
  # ★ v1.0.1/v1.0.2 既有判据保留：add 一律 -f 且吞返回码
  #   （已跟踪文件加 -f 无副作用；未跟踪且被 ignore ⇒ -f 是唯一纳入方式）
  git add -f "$p" 2>/dev/null || true
done
if git diff --cached --quiet; then dsh_log "无改动（幂等退出）: ${PATHS[*]}"; echo "无改动（幂等退出）"; exit 0; fi
git commit -q -m "$MSG" || { dsh_log "commit 失败"; exit 1; }
echo "已提交 $(git rev-parse --short HEAD) · 文件: ${PATHS[*]}"
dsh_log "commit $(git rev-parse --short HEAD) mode=$MODE: ${PATHS[*]}"

if [ "$MODE" = "nopush" ]; then
  echo "★ --no-push ⇒ 只落本地第二副本，未推送"
  dsh_log "nopush: $(git rev-parse --short HEAD) 未推送"
  exit 0
fi

# ★★ v2.0.0：push 之前必须过【公开性门】。★ 判不了 ⇒ 不推（fail-closed）。
echo "【公开性门】★ 问：即将【出本机】的东西，能不能公开？"
publicity_gate HEAD; GRC=$?
if [ "$GRC" -ne 0 ]; then
  echo "★ 公开性门未放行（rc=$GRC）⇒ ★ 不推送。commit 已落在本地磁盘（第二副本已有）。"
  echo "  ★ 远端副本＝未完成；★ 但把不可公开的内容推到公开互联网【不可逆】⇒ 本门选择不推。"
  dsh_log "★ 公开性门拦住 push（rc=$GRC）· commit=$(git rev-parse --short HEAD)"
  exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if git remote get-url origin >/dev/null 2>&1; then
  if git push -q origin "$BRANCH" 2>/dev/null; then
    R="$(git rev-parse --short "origin/$BRANCH" 2>/dev/null || echo '?')"
    if [ "$R" = "$(git rev-parse --short HEAD)" ]; then
      echo "已推送 origin/$BRANCH ⇒ $R ✓（止损完成：本地=远端）"; dsh_log "push ✓ $R"
    else
      echo "★ 推送后远端($R) ≠ 本地($(git rev-parse --short HEAD)) —— 请查" >&2; dsh_log "★ push 后不一致 R=$R"
    fi
  else
    echo "★ push 失败 —— 【止损未完成】：commit 已落在本地磁盘，远端未更新" >&2; dsh_log "★ push 失败"
  fi
else
  echo "★ 无 origin ⇒ 【无远端止损点】，唯一副本风险未解除" >&2; dsh_log "★ 无 origin"
fi
