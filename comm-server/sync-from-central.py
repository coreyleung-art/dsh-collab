#!/usr/bin/env python3
"""comm-server 同步层 v1.1 · 下行镜像（中枢 → mac-mini 读侧）
v1.1 (2026-10-02, D2 修复)：防回声按 value.from 判定（原按域排除误伤 mac-mini 入向）；
  DOWN_PREFIXES 扩展 notes/mac-mini/；新增 --warm 首跑预热（防历史键全量回灌注入风暴）。
  is_self_from 单测 8/8；正负例实测（d2-pos 镜像 ✓ / d2-neg 跳过 ✓）。
订阅中枢 SSE 8803，把 i9/MBP 写入中枢的新键镜像到本机黑板（notes/i9/, notes/mbp/, notes/collab/ 相关）
本机写中枢的键不回灌（防回声：seen 记录 + from 过滤）
"""
import json, os, sys, time, subprocess, urllib.request

CENTRAL_BB = os.environ.get("CENTRAL_BB", "http://xingqiao.meetfunbp.com:8792")
CENTRAL_SSE = os.environ.get("CENTRAL_SSE", "http://xingqiao.meetfunbp.com:8803/events")
LOCAL_BB = os.environ.get("LOCAL_BB", "http://127.0.0.1:8792")
# 下行镜像域：i9/MBP 写中枢的键 + 2026-10-02 扩展 notes/mac-mini/（D2 修复）
#   原实现只镜像 i9/mbp 域 ⇒ MBP 若只写服务器（不经 Tailscale 直连）发往 mac-mini 的卡
#   永远不会镜像到本机 ⇒ 「服务器唯一中继」在 mac-mini 入向是断的。
#   防回声不再用「域排除」（会误伤入向），改由 sync_down_once 内 is_self_from() 按 value.from 判定。
from comm_domains import down_domains_as_prefixes as _down
# ★ v1.2（2026-10-03 星桥）：+ notes/collab/ —— central-inbox 的 WATCH_PREFIXES = notes/<本机> + notes/collab，
#   SSE 无 Last-Event-ID 重放（服务器 sse.rs 未实现），断线期间漏掉的协作卡只能靠本脚本 catch-up；
#   DOWN_PREFIXES 必须覆盖 WATCH_PREFIXES 全集，否则 collab 卡断线即丢。
DOWN_PREFIXES = _down() + ("notes/mac-mini/", "notes/collab/")
SEEN_FILE = os.path.expanduser("~/.dsh/comm-sync-down-seen.json")

def log(m):
    print(f"[sync-down] {time.strftime('%H:%M:%S')} {m}", flush=True)

def load_seen():
    try: return set(json.load(open(SEEN_FILE)))
    except: return set()

def save_seen(s):
    try: json.dump(sorted(s)[-5000:], open(SEEN_FILE, "w"))
    except: pass

def bb_put_local(url, val):
    try:
        body = json.dumps(val).encode()
        req = urllib.request.Request(url, data=body, method="PUT",
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception as e:
        log(f"镜像失败 {url}: {str(e)[:50]}")
        return False

# 本机自写判定标记（from 字段子串命中 → 不镜像回，防回声；未知 → 镜像=放行）
SELF_FROM_MARKERS = (
    "session-fa1f9150", "session-a190c54c", "session-2a15e6b1", "session-164dceca",
    "mac-mini", "星桥", "明鉴", "司库", "coordinator", "bus:mac-mini",
)

def is_self_from(val):
    """按 value.from 判定是否本机自写（D2：防回声按 from 而非键域）。
    未知标签 → False（镜像=放行，漏收代价 > 回声代价，2026-10-02 与 MBP 共同结论）。"""
    if val.get("_mirror") == "mac-mini-fwd":
        return True
    frm = str(val.get("from", "") or "")
    if not frm:
        return True  # 无 from 且无镜像标记的孤儿键：保守不镜像（无法判自，避免回流污染）
    return any(m in frm for m in SELF_FROM_MARKERS)

def sync_down_once(warm=False):
    seen = load_seen()
    mirrored = 0
    # 全库 list 中枢（只取 DOWN_PREFIXES 域新键）
    try:
        with urllib.request.urlopen(CENTRAL_BB + "/notes", timeout=15) as r:
            d = json.loads(r.read())
    except Exception as e:
        log(f"中枢 list 失败: {e}")
        return 0
    lst = d.get("list", {}) if isinstance(d, dict) else {}
    for key, meta in lst.items():
        if not isinstance(meta, dict): continue
        if not any(key.startswith(p) for p in DOWN_PREFIXES): continue
        if key in seen: continue
        seen.add(key)
        # ★ 2026-10-02 --warm：只预热 seen、不镜像（部署时首跑用，防历史键全量回灌注入风暴）
        if warm: continue
        try:
            with urllib.request.urlopen(CENTRAL_BB + "/" + key, timeout=6) as r:
                v = json.loads(r.read())
            val = v.get("value", {})
            if val:
                if is_self_from(val):
                    continue  # D2：本机自写不回灌（按 from 判定，域不再作为判据）
                # 标注来源中枢，镜像本机
                val2 = dict(val)
                val2["_via"] = "comm-central"
                if bb_put_local(LOCAL_BB + "/" + key, val2):
                    mirrored += 1
                    if mirrored <= 5: log(f"镜像 {key}")
        except Exception as e:
            log(f"键 {key} 异常: {str(e)[:40]}")
    save_seen(seen)
    log(f"下行同步 {mirrored} 键（累计 {len(seen)}）")
    return mirrored

def watch():
    log(f"watch 启动: {CENTRAL_SSE}")
    while True:
        try:
            req = urllib.request.Request(CENTRAL_SSE)
            with urllib.request.urlopen(req, timeout=60) as r:
                for raw in r:
                    line = raw.decode(errors="ignore").strip()
                    if line.startswith("data: "):
                        try:
                            ev = json.loads(line[6:])
                            key = ev.get("key", "")
                            if any(key.startswith(p) for p in DOWN_PREFIXES):
                                sync_down_once()
                        except: pass
        except Exception as e:
            log(f"SSE 断: {str(e)[:50]}，3s 重连")
            time.sleep(3)

if __name__ == "__main__":
    if "--warm" in sys.argv:
        # 首跑预热：只把当前全部键记入 seen（不镜像），之后增量镜像
        sync_down_once(warm=True)
    elif "--once" in sys.argv:
        sync_down_once()
    else:
        sync_down_once()
        watch()
