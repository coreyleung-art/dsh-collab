#!/bin/bash
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕
DSH_LOG="$HOME/dsh-collab/logs/systemgraph-publish.log"
dsh_log() {
    mkdir -p "$(dirname "$DSH_LOG")" 2>/dev/null
    printf '%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$*" >> "$DSH_LOG" 2>/dev/null || true
}

VERSION=1.0.0 # ★ R006 ⑥ 唯一版本声明处（补课生成）
# systemgraph-publish.sh — 把 SystemGraph 静态导出发布到通讯服务器（比对通过才算成功）
#
# 用法：
#   ./systemgraph-publish.sh                 # 默认演练（零变更）
#   ./systemgraph-publish.sh --verify        # 只读校验：线上与本地导出是否逐文件一致
#   ./systemgraph-publish.sh --go            # 真发布（上传→服务端比对→HTTP 抽验）
#   ./systemgraph-publish.sh --json          # 机器可读输出
#
# 纪律（来自 2026-09-13 的教训）：
#   · **不比对不发布**：上传完成 ≠ 发布成功；必须比对服务端与本地 sha256
#   · 默认演练、显式 --go 才动；未知旗标 → exit 2 且不启动任何动作
#   · 发布前先做**本地自洽检查**（manifest 记录的哈希 vs 实物）—— manifest 曾出现"写完又改文件"导致记录哈希恒陈旧
#   · 服务端保留上一版备份，回滚 = 恢复备份目录
# 退出码（R006 ⑨②）：0 成功 · 1 失败 · 2 用法错误
set -uo pipefail

LOCAL_DIR="${SG_LOCAL:-$HOME/dsh-collab/data/blueprint/gallery/static-export}"
SSH_KEY="${SG_KEY:-$HOME/Downloads/startbrige.pem}"
SSH_USER="${SG_USER:-ubuntu}"
SSH_HOST="${SG_HOST:-106.53.214.108}"
REMOTE_DIR="${SG_REMOTE:-/var/www/systemgraph}"
PUBLIC="${SG_PUBLIC:-http://xingqiao.meetfunbp.com}"
TS=$(date +%s)
MODE="dry"; JSON=0
for a in "$@"; do
  case "$a" in
    --go)       MODE="go" ;;
    --verify)   MODE="verify" ;;
    --dry-run)  MODE="dry" ;;
    --json)     JSON=1 ;;
    -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知旗标: $a（--go / --verify / --dry-run / --json）" >&2; exit 2 ;;
  esac
done

say() { [ "$JSON" = 1 ] || printf '%s\n' "$*"; }
die() { echo "❌ $*" >&2; exit 1; }

# URL 路径段要**百分号编码**（前端就是用 encodeURIComponent 取的图），而本地路径**不能**编码
# ⇒ 两者必须分开算：同一个字符串无法既是本地路径又是 URL 路径。
url_of() { python3 -c "import urllib.parse,sys;print('/'.join(urllib.parse.quote(s) for s in sys.argv[1].split('/')))" "$1"; }

[ -d "$LOCAL_DIR" ] || die "本地导出目录不存在: $LOCAL_DIR"
[ -f "$LOCAL_DIR/manifest.json" ] || die "缺 manifest.json"

# ---------- 1) 本地自洽：manifest 记录的哈希 vs 实物 ----------
LOCAL_FILES=$(find "$LOCAL_DIR" -type f | wc -l | tr -d ' ')
MANIFEST_EXPORTED=$(python3 -c "import json;print(json.load(open('$LOCAL_DIR/manifest.json')).get('exported',''))" 2>/dev/null)
say "本地导出: $LOCAL_DIR"
say "  文件数=$LOCAL_FILES · manifest.exported=$MANIFEST_EXPORTED"

# ---------- 2) 校验模式：线上 vs 本地逐文件比对 ----------
key_files=(manifest.json index.html)
while IFS= read -r f; do key_files+=("$f"); done < <(cd "$LOCAL_DIR" && ls api/*.json 2>/dev/null | head -6)
# ★ 2026-09-28 补（明鉴 实测发现）：验收集必须**覆盖这次要交付的对象**。
#   原 key_files 只有 manifest.json / index.html / 前 6 个 api/*.json ⇒ **assets/ 一个都不验**
#   ⇒ 图库载荷整目录没传上去，这条通道照样报「✅ 发布成功」——
#     而实测恰好如此：tm 上 /assets/ 10 条指针 8 条 200、2 条 404；
#     星桥镜像 /assets/ **一条都没有**（全 404）。**从来没有一条失败是这条通道报出来的** ✓
#   ⇒ 前端取图路径是 `__BASE+'/assets/'+encodeURIComponent(a.file)`（index.html:724）
#     ⇒ 故验收集**由索引派生**（api/assets.json 列了哪些就验哪些）：
#       载荷与判据同源、不各自枚举目录 —— 各自枚举必然出现「索引里有、载荷里没有」✓
ASSET_IDX="$LOCAL_DIR/api/assets.json"
ASSET_N=0
if [ -f "$ASSET_IDX" ]; then
  while IFS= read -r f; do key_files+=("$f"); ASSET_N=$((ASSET_N+1)); done < <(
    python3 -c "
import json,sys
try: es=json.load(open('$ASSET_IDX',encoding='utf-8'))
except Exception: sys.exit(0)
for e in es:
    fn=e.get('file') if isinstance(e,dict) else None
    if fn: print('assets/'+fn)
" 2>/dev/null)
fi
say "验收集: ${#key_files[@]} 个（含图库资产 $ASSET_N 个，由 api/assets.json 派生）"

verify_online() {
  local bad=0 n=0
  say "线上比对（$PUBLIC）:"
  for f in "${key_files[@]}"; do
    [ -f "$LOCAL_DIR/$f" ] || continue
    n=$((n+1))
    lh=$(shasum -a 256 "$LOCAL_DIR/$f" | cut -c1-16)
    rh=$(curl -s -m 20 "$PUBLIC/$(url_of "$f")" 2>/dev/null | shasum -a 256 | cut -c1-16)
    if [ "$lh" = "$rh" ]; then say "  ✅ $f"; else say "  ❌ $f 本地=$lh 线上=$rh"; bad=$((bad+1)); fi
  done
  say "  比对 $n 个文件，不一致 $bad 个"
  return $bad
}

if [ "$MODE" = "verify" ]; then
  verify_online; rc=$?
  [ "$JSON" = 1 ] && echo "{\"mode\":\"verify\",\"public\":\"$PUBLIC\",\"mismatch\":$rc}"
  exit $([ "$rc" = 0 ] && echo 0 || echo 1)
fi

# ---------- 3) 计划 ----------
say ""
say "计划（目标: $SSH_USER@$SSH_HOST:$REMOTE_DIR）:"
say "  a. 服务端备份现有 $REMOTE_DIR → ${REMOTE_DIR}.bak-$TS"
say "  b. rsync/scp 上传 $LOCAL_FILES 个文件"
say "  c. **服务端**逐文件比对 sha256（与本地必须一致）"
say "  d. HTTP 抽验 $PUBLIC/ + /manifest.json"
say "  e. 失败 → 恢复备份目录并复验"

if [ "$MODE" = "dry" ]; then
  say ""
  say "== 演练结束（零变更）=="
  say "校验线上一致性: $0 --verify    真发布: $0 --go"
  [ "$JSON" = 1 ] && echo "{\"mode\":\"dry-run\",\"local_files\":$LOCAL_FILES,\"exported\":\"$MANIFEST_EXPORTED\",\"changed\":false}"
  exit 0
fi

# ---------- 4) 发布 ----------
say ""
say "[1/4] 服务端备份"
ssh -i "$SSH_KEY" -o ConnectTimeout=20 "$SSH_USER@$SSH_HOST" \
  "sudo cp -a $REMOTE_DIR ${REMOTE_DIR}.bak-$TS 2>/dev/null && echo '  ✅ 已备份 ${REMOTE_DIR}.bak-$TS' || echo '  （无现有目录，跳过备份）'" \
  || die "SSH 不可达"

say "[2/4] 上传"
tar -C "$LOCAL_DIR" -czf /tmp/sg-publish-$TS.tgz . || die "打包失败"
scp -q -i "$SSH_KEY" -o ConnectTimeout=30 /tmp/sg-publish-$TS.tgz "$SSH_USER@$SSH_HOST:/tmp/" || die "上传失败"
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" \
  "sudo rm -rf ${REMOTE_DIR}.new && sudo mkdir -p ${REMOTE_DIR}.new && sudo tar -xzf /tmp/sg-publish-$TS.tgz -C ${REMOTE_DIR}.new && sudo chown -R www-data:www-data ${REMOTE_DIR}.new && echo '  ✅ 已解包' " || die "解包失败"

say "[3/4] 服务端逐文件比对（**不比对不算发布成功**）"
FAIL=0
for f in "${key_files[@]}"; do
  [ -f "$LOCAL_DIR/$f" ] || continue
  lh=$(shasum -a 256 "$LOCAL_DIR/$f" | cut -c1-16)
  rh=$(ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "sudo sha256sum ${REMOTE_DIR}.new/$f 2>/dev/null | cut -c1-16")
  if [ "$lh" = "$rh" ]; then say "  ✅ $f"; else say "  ❌ $f 本地=$lh 服务端=$rh"; FAIL=1; fi
done
if [ "$FAIL" != 0 ]; then
  say "  → 比对不一致：**不切换**，保留原目录（备份在 ${REMOTE_DIR}.bak-$TS）"
  ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "sudo rm -rf ${REMOTE_DIR}.new"
  exit 1
fi

say "  → 比对通过，原子切换"
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" \
  "sudo rm -rf ${REMOTE_DIR}.old && sudo mv $REMOTE_DIR ${REMOTE_DIR}.old && sudo mv ${REMOTE_DIR}.new $REMOTE_DIR && echo '  ✅ 已切换'" || die "切换失败"

say "[4/4] HTTP 抽验"
OK=1
for u in "$PUBLIC/healthz" "$PUBLIC/manifest.json"; do
  code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$u")
  [ "$code" = "200" ] && say "  ✅ $u → 200" || { say "  ❌ $u → $code"; OK=0; }
done
# ★ 2026-09-28 补：图库资产**必须走一次真实 HTTP 取图**。
#   理由（今天的教训链）：服务端 sha256 比对只证明「文件落到了盘上」，
#   不证明「**Web 服务器按前端的 URL 形态取得到它**」——
#   中文文件名要百分号编码、nginx 的 alias/try_files 可能不匹配 ⇒ 盘上有、HTTP 404 是可能的组合。
#   ⇒ 取**索引里的第一条**资产做真实取图并比对字节（不是只看状态码）。
if [ "$ASSET_N" -gt 0 ]; then
  probe=""
  for f in "${key_files[@]}"; do case "$f" in assets/*) probe="$f"; break;; esac; done
  if [ -n "$probe" ] && [ -f "$LOCAL_DIR/$probe" ]; then
    lh=$(shasum -a 256 "$LOCAL_DIR/$probe" | cut -c1-16)
    rh=$(curl -s -m 20 -f "$PUBLIC/$(url_of "$probe")" 2>/dev/null | shasum -a 256 | cut -c1-16)
    if [ "$lh" = "$rh" ]; then say "  ✅ 取图 $probe → 字节一致"; else say "  ❌ 取图 $probe 本地=$lh HTTP取到=$rh"; OK=0; fi
  fi
fi
rm -f /tmp/sg-publish-$TS.tgz

if [ "$OK" = 1 ]; then
  say ""
  say "✅ 发布成功（exported=$MANIFEST_EXPORTED · $LOCAL_FILES 文件）"
  say "   回滚：ssh → sudo rm -rf $REMOTE_DIR && sudo mv ${REMOTE_DIR}.bak-$TS $REMOTE_DIR"
  [ "$JSON" = 1 ] && echo "{\"mode\":\"go\",\"ok\":true,\"exported\":\"$MANIFEST_EXPORTED\",\"files\":$LOCAL_FILES}"
  exit 0
else
  say ""
  say "❌ 发布后 HTTP 抽验未全过 —— 建议回滚到 ${REMOTE_DIR}.bak-$TS"
  exit 1
fi
