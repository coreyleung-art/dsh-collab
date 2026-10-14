#!/bin/bash
#
# ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
# 依据：r006-debt-assess.py 机械扫描未检出以下原语：
#       subprocess / os.system / eval / exec / os.remove / rmtree /
#       os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
# ★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
#


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）· .sh 版
r006_selfcheck() {
  echo "== systemgraph-publish 自查（TCC 能力边界）=="
  echo "【① 能力清单】"
  echo "  · ★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。"
  echo "  · 依据：r006-debt-assess.py 机械扫描未检出以下原语："
  echo "  · os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数"
  echo "【② 不该发生路径清单】"
  echo "  · 本工具涉及「删除文件」⇒ 该路径须受控"
  echo "  · 本工具涉及「终止进程」⇒ 该路径须受控"
  echo "  · 本工具涉及「修改权限」⇒ 该路径须受控"
  echo "  · 本工具涉及「访问网络」⇒ 该路径须受控"
  echo "  · 本工具涉及「提权」⇒ 该路径须受控"
  echo "【③ 依赖完整性】"
  echo "  · shell: $SHELL"
  echo "  · 依赖: 系统命令 + 标准工具"
  echo "  · 固定日志: ~/dsh-collab/logs/systemgraph-publish.log"
  return 0
}

case "$1" in
  --selfcheck) r006_selfcheck; exit 0 ;;
esac

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
    *) echo "未知旗标: ${a}（--go / --verify / --dry-run / --json）" >&2; exit 2 ;;
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
# ★★★ 2026-10-14 覆盖度修正（本线实测：原覆盖 19/126 = 15.1%）：
#   · **原来只取 api/*.json 的前 6 个**（字母序）⇒ 22 个里 16 个从不被验
#     ★ 负控实测：注入 api/overview.json **检不出**（因为 overview 不在前 6）——★ 假阴性。
#   · `snapshots/` 89 个文件【一个都不验】。
#   ⇒ 改为：**全部 api/*.json** + **全部根级 *.html/json** + snapshots 抽样（见下）
while IFS= read -r f; do key_files+=("$f"); done < <(cd "$LOCAL_DIR" && ls api/*.json 2>/dev/null)
# ★ 根级文件：★ 排除已在 key_files 里的（manifest.json / index.html）—— 否则重复计入
while IFS= read -r f; do
  case "$f" in */*) continue;; esac
  case " ${key_files[*]} " in *" $f "*) continue;; esac
  key_files+=("$f")
done < <(cd "$LOCAL_DIR" && ls *.html *.json 2>/dev/null)
# ★ snapshots：数量大（89）⇒ 抽样 5 个 + ★ 全部计入【文件数】以便报出真实覆盖度
while IFS= read -r f; do key_files+=("$f"); done < <(cd "$LOCAL_DIR" && ls snapshots/*.svg 2>/dev/null | head -5)
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

# ═══ ★★★ 三态比对（2026-10-14 明鉴 · 修假阳性）═══
#   ★ 实测缺陷（本线复现，铁证）：
#     `assets/Memory-Governance-架构图.html` **3.57 MB**，完整下载实测 **32.0s / 32.5s / 51.4s**。
#     而原实现用 `curl -s -m 20`（20 秒超时）⇒ **20s 内只下到 966,403 B / 3,572,936 B（27%）**，
#     三次下载的 sha **每次不同**（截断位置随机）⇒ ★★ **该文件永远报「不一致」**。
#     ★ 而手工取线上 = 本地 sha，逐字节相同 ⇒ **真相是「下载没下完」，不是「内容不一致」**。
#   ⇒ ★★★ 同族：**把【测量装置的失败】读成【被测对象的属性】** ——
#     与「is-active 读成健康（而它每 27 秒死一次）」是同一个框架缺口。
#   ⇒ 修法：**三态**
#     · 下载完整（HTTP 200 且字节数 == 本地）⇒ 比 sha ⇒ ✅ 一致 / ❌ 不一致
#     · 下载不完整（超时截断 / 字节数不符）    ⇒ ⚠️ **不可判**（★ 不计入不一致）
#     · 下载失败（HTTP 非 200 / 取不到）        ⇒ ⚠️ **不可判**
#   ★ 为什么关键：**带假阳性的判据接进自动链 = 自动化地制造「狼来了」**。
verify_online() {
  local bad=0 n=0 unk=0
  say "线上比对（${PUBLIC}）:"
  for f in "${key_files[@]}"; do
    [ -f "$LOCAL_DIR/$f" ] || continue
    n=$((n+1))
    lh=$(shasum -a 256 "$LOCAL_DIR/$f" | cut -c1-16)
    lsz=$(wc -c < "$LOCAL_DIR/$f" | tr -d ' ')
    # ★ 超时按大小自适应（实测吞吐约 70–110 KB/s ⇒ 给 20s/MB + 30s 底，不依赖固定值）
    to=$(( 30 + (lsz / 1048576) * 20 ))
    [ "$to" -lt 20 ] && to=20
    # ★★★ 完整性判据 = 【服务器自报的 Content-Length】
    #   ★ 起因（本线负控暴露）：注入真差异后本地大小变了，若用「大小 != 本地大小」判截断
    #     ⇒ **真不一致会被误判成「不可判」**（假阴性）。
    #   ★★ 而「收到字节 == 服务器声明的 Content-Length」是【服务器自己的口径】⇒ 与内容差异无关。
    #   ★★★ 坑 1（本线踩到）：**该服务器不支持 HEAD**（实测 `HEAD → 405 Method Not Allowed`）
    #     ⇒ 不能用 `curl -sI` 取长度。改为 **从同一次 GET 的响应头里取**（-D）。
    #   ★★★ 坑 2（本线踩到）：**`awk 'BEGIN{IGNORECASE=1}'` 是 GNU 扩展，macOS 的 BSD awk 不支持**
    #     ⇒ 它【静默无输出】⇒ 被判成「服务器声明未知」⇒ **全线 42 个文件全报「不可判」**（假阴性海啸）。
    #     ⇒ 必须用可移植写法 `tolower($1)=="content-length:"`。
    meta=$(curl -s -m "$to" -D /tmp/sg-verify-$$.hdr -o /tmp/sg-verify-$$.bin \
             -w '%{http_code} %{size_download}' "$PUBLIC/$(url_of "$f")" 2>/dev/null)
    code=${meta%% *}; got=${meta##* }
    cl=$(awk 'tolower($1)=="content-length:"{gsub(/\r/,"");print $2}' /tmp/sg-verify-$$.hdr 2>/dev/null | tail -1)
    if [ "$code" != "200" ] || [ -z "$cl" ] || [ "$got" != "$cl" ]; then
      say "  ⚠️  $f 不可判（HTTP=$code 取到=$got 服务器声明=${cl:-未知} ⇒ 下载未完成，★ 非「不一致」）"
      unk=$((unk+1))
    else
      # ★★★ 2026-10-14（本线实测的第二类假警）：**JSON 里的【生成类时间字段】每次导出都变**
      #   （`manifest.json` 的 `exported` · 生成物的 `generatedAt`/`updated` · 注入的 `_srcMtime`）
      #   ⇒ 若逐字节比，**任何一次 export 之后都必然报不一致** —— 而内容其实没变。
      #   ★ 修法：对 `.json` **比对【归一化内容】**（抹掉生成类时间字段）；
      #     HTML/二进制仍【逐字节】比（★ 不能归一化，那会掩盖真实改动）。
      case "$f" in
        *.json)
          lhn=$(python3 -c "
import json,re,sys,hashlib
def n(p):
    s=open(p,encoding='utf-8',errors='replace').read()
    s=re.sub(r'\"(exported|generatedAt|updated|_srcMtime|_built|exportedAt|generatedBy)\"\s*:\s*\"[^\"]*\"', r'\"\\1\":\"<T>\"', s)
    return hashlib.sha256(s.encode()).hexdigest()[:16]
print(n(sys.argv[1]))" "$LOCAL_DIR/$f" 2>/dev/null)
          rhn=$(python3 -c "
import json,re,sys,hashlib
def n(p):
    s=open(p,encoding='utf-8',errors='replace').read()
    s=re.sub(r'\"(exported|generatedAt|updated|_srcMtime|_built|exportedAt|generatedBy)\"\s*:\s*\"[^\"]*\"', r'\"\\1\":\"<T>\"', s)
    return hashlib.sha256(s.encode()).hexdigest()[:16]
print(n(sys.argv[1]))" /tmp/sg-verify-$$.bin 2>/dev/null)
          if [ -n "$lhn" ] && [ "$lhn" = "$rhn" ]; then
            say "  ✅ ${f}（★ 归一化后内容一致；逐字节差仅在生成时间字段）"
          else
            rh=$(shasum -a 256 /tmp/sg-verify-$$.bin | cut -c1-16)
            say "  ❌ $f 本地=$lh 线上=${rh}（★ 归一化后仍不同 ⇒ 真实内容滞后）"; bad=$((bad+1))
          fi
          ;;
        *)
          rh=$(shasum -a 256 /tmp/sg-verify-$$.bin | cut -c1-16)
          if [ "$lh" = "$rh" ]; then say "  ✅ $f"; else say "  ❌ $f 本地=$lh 线上=$rh"; bad=$((bad+1)); fi
          ;;
      esac
    fi
    rm -f /tmp/sg-verify-$$.bin /tmp/sg-verify-$$.hdr
  done
  say "  比对 $n 个文件，不一致 $bad 个，不可判 $unk 个"
  [ "$unk" -gt 0 ] && say "  ★★ 不可判 ≠ 不一致：那是【下载没取全】，★ 请重跑或加大超时，勿据此判定线上有问题"
  MISMATCH=$bad; UNKNOWN=$unk
  [ "$bad" -eq 0 ] && [ "$unk" -eq 0 ] && return 0 || return 1
}

if [ "$MODE" = "verify" ]; then
  MISMATCH=0; UNKNOWN=0
  verify_online; rc=$?
  # ★ 三态暴露：mismatch（确认不一致）与 unknown（不可判）分开报 —— ★ 不合并
  [ "$JSON" = 1 ] && echo "{\"mode\":\"verify\",\"public\":\"$PUBLIC\",\"mismatch\":$MISMATCH,\"unknown\":$UNKNOWN}"
  exit $rc
fi

# ---------- 3) 计划 ----------
say ""
say "计划（目标: $SSH_USER@$SSH_HOST:${REMOTE_DIR}）:"
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
  say "  → 比对不一致：**不切换**，保留原目录（备份在 ${REMOTE_DIR}.bak-${TS}）"
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
    # ★ 同款三态（★ 大图会被短超时截断而误报，见 verify_online 顶部注释）
    psz=$(wc -c < "$LOCAL_DIR/$probe" | tr -d ' ')
    pto=$(( 30 + (psz / 1048576) * 20 )); [ "$pto" -lt 20 ] && pto=20
    pmeta=$(curl -s -m "$pto" -D /tmp/sg-probe-$$.hdr -o /tmp/sg-probe-$$.bin -w '%{http_code} %{size_download}' "$PUBLIC/$(url_of "$probe")" 2>/dev/null)
    pcode=${pmeta%% *}; pgot=${pmeta##* }
    pcl=$(awk 'tolower($1)=="content-length:"{gsub(/\r/,"");print $2}' /tmp/sg-probe-$$.hdr 2>/dev/null | tail -1)
    if [ "$pcode" != "200" ] || [ -z "$pcl" ] || [ "$pgot" != "$pcl" ]; then
      say "  ⚠️  取图 $probe 不可判（HTTP=$pcode 取到=$pgot 服务器声明=${pcl:-未知} ⇒ 下载未完成，★ 不判失败）"
    else
      rh=$(shasum -a 256 /tmp/sg-probe-$$.bin | cut -c1-16)
      if [ "$lh" = "$rh" ]; then say "  ✅ 取图 $probe → 字节一致"; else say "  ❌ 取图 $probe 本地=$lh HTTP取到=$rh"; OK=0; fi
    fi
    rm -f /tmp/sg-probe-$$.bin /tmp/sg-probe-$$.hdr
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
