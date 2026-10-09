#!/usr/bin/env python3
"""
bus-capture v1 —— 协作记忆自动捕捉管道（OpenChronicle 机制复用）

原理：复用 OpenChronicle 的事件捕捉/聚合/去重机制到「总线事件」：
  总线事件（消息/锁/档案） → 捕捉缓冲 → 分级过滤 → 纪要 → 三轨落档

用法：
  python3 bus-capture.py --snapshot          # 立即执行一次捕捉（默认）
  python3 bus-capture.py --check             # 检查上次捕捉状态（不执行）
  python3 bus-capture.py --since HOURS       # 只捕捉最近 N 小时（默认 24）
  python3 bus-capture.py --buffer 30         # 缓冲保留天数（默认 30）

输出：
  捕捉缓冲：~/.dsh/capture/events-YYYYMMDD.jsonl（原始事件，滚动保留 30 天）
  分级标注：同文件内每条事件打 tag（value: high/med/low · target: forum/research/registry/none）
  纪要草稿：~/.dsh/capture/summaries/YYYYMMDD-thread-<id>.md（线程级纪要，供摄取角色审核落档）

纪律遵守：
  - J34 广播约束：本工具只做捕捉/标注，不广播、不打扰
  - J35 本地模型互斥：纪要生成前检查 LM Studio/Ollama 是否已在跑，不重复开
  - 秒级时间观：本工具可随时执行，秒级完成
  - 硬件守卫：内存空闲 <2GB 时降级（跳过纪要生成，只做捕捉标注）
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import sys
import time
import glob
from datetime import datetime, timedelta


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bus-capture.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

BUS_FILE = os.path.expanduser("~/.dsh/agent-bus.json")
CAPTURE_DIR = os.path.expanduser("~/.dsh/capture")
SUMMARY_DIR = os.path.join(CAPTURE_DIR, "summaries")
BUFFER_DAYS = 30  # 缓冲保留期（用户确认 30 天）
VALUE_TAGS = {"high": "可复用知识", "med": "共识/决策", "low": "一次性/噪声"}

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def load_bus():
    """加载总线数据"""
    if not os.path.exists(BUS_FILE):
        print(f"[bus-capture] 总线文件不存在: {BUS_FILE}")
        return None
    with open(BUS_FILE) as f:
        return json.load(f)

def collect_events(bus, since_hours=24):
    """收集总线事件（消息/锁/档案变更）"""
    events = []
    cutoff = time.time() - since_hours * 3600
    for t in bus.get("threads", []):
        tid = t.get("id", "unknown")
        for m in t.get("messages", []):
            ts = m.get("time", 0) / 1000 if m.get("time") else 0
            if ts < cutoff:
                continue
            events.append({
                "type": "message",
                "time": ts,
                "thread": tid,
                "from": m.get("from", ""),
                "to": m.get("to", ""),
                "kind": m.get("kind", "normal"),
                "text": (m.get("text", "") or "")[:500],
                "tag": classify_message(m),
            })
    for lk in bus.get("locks", []):
        events.append({
            "type": "lock",
            "time": time.time(),
            "thread": "system",
            "from": lk.get("holder", ""),
            "text": f"锁: {lk.get('resource','')}",
            "tag": {"value": "low", "target": "registry"},
        })
    return events

SENSITIVE_PATTERNS = [
    # 凭据/密钥
    r"sk-[a-zA-Z0-9]{20,}", r"api[_-]?key\s*[:=]\s*\S+", r"token\s*[:=]\s*\S+",
    r"password\s*[:=]\s*\S+", r"passwd\s*[:=]\s*\S+", r"secret\s*[:=]\s*\S+",
    r"Bearer\s+[a-zA-Z0-9._-]{20,}",
    # 手机号/身份证/银行卡
    r"1[3-9]\d{9}", r"\d{17}[\dXx]", r"\d{16,19}",
    # 薪酬/成本敏感
    r"薪酬\s*[:：]\s*\S+", r"工资\s*[:：]\s*\S+", r"月薪\s*[:：]\s*\S+",
    # 客户隐私
    r"客户电话\s*[:：]\s*\S+", r"客户地址\s*[:：]\s*\S+",
]

def is_sensitive(text):
    """敏感检测：命中任一模式即拒绝落档（外链纪律：客户隐私/凭据/薪酬不落盘）"""
    import re
    for pat in SENSITIVE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False

def classify_message(m):
    """分级过滤：按内容特征打标（非删减，保留原始事件）"""
    text = (m.get("text", "") or "").lower()
    kind = m.get("kind", "")
    # 广播 → 制度/重大事件
    if kind == "broadcast":
        return {"value": "high", "target": "forum"}
    # 归档确认/回执 → 低价值（不落档，原始保留）
    if any(k in text for k in ["确认收悉", "收悉", "收到", "🤝", "归档确认", "回执"]):
        return {"value": "low", "target": "none"}
    # 含结论/决策/共识词 → 共识/决策
    if any(k in text for k in ["决策", "裁定", "拍板", "裁决", "结论", "决议", "批准", "确认执行"]):
        return {"value": "med", "target": "forum"}
    # 含调研/报告/文档/资源/登记 → 可复用知识
    if any(k in text for k in ["调研", "报告", "文档", "资源", "登记", "规范", "设计", "架构"]):
        return {"value": "high", "target": "research"}
    # 含资源/锁/端口/服务 → 登记表
    if any(k in text for k in ["资源", "锁", "端口", "服务", "登记表", "档案"]):
        return {"value": "med", "target": "registry"}
    return {"value": "med", "target": "forum"}

def write_buffer(events, date_str):
    """写捕捉缓冲（append，滚动保留 BUFFER_DAYS）"""
    os.makedirs(CAPTURE_DIR, exist_ok=True)
    path = os.path.join(CAPTURE_DIR, f"events-{date_str}.jsonl")
    with open(path, "a") as f:
        for e in events:
            e["captured_at"] = now_iso()
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # 滚动清理过期缓冲
    cutoff = datetime.now() - timedelta(days=BUFFER_DAYS)
    for old in glob.glob(os.path.join(CAPTURE_DIR, "events-*.jsonl")):
        try:
            d = datetime.strptime(os.path.basename(old).replace("events-", "").replace(".jsonl", ""), "%Y%m%d")
            if d < cutoff:
                os.remove(old)
                print(f"[bus-capture] 清理过期缓冲: {old}")
        except ValueError:
            pass
    return path

def check_hardware():
    """硬件守卫：内存空闲水位检查（macOS）"""
    try:
        out = os.popen("memory_pressure -Q 2>/dev/null | grep -o '[0-9]*%' | head -1").read().strip().replace("%", "")
        if out and int(out) < 10:
            return False  # 空闲 <10%（约 2.4GB）→ 降级
    except Exception:
        pass
    return True

def check_model_conflict():
    """J35 纪律：检查 LM Studio / Ollama 是否已在跑（不重复开）"""
    import subprocess
    try:
        r = subprocess.run(["pgrep", "-fl", "lmstudio|ollama"], capture_output=True, text=True, timeout=5)
        procs = r.stdout.strip().split("\n") if r.stdout.strip() else []
        return procs
    except Exception:
        return []

def main():
    global BUFFER_DAYS
    since_hours = 24
    do_summary = True
    for arg in sys.argv[1:]:
        if arg == "--check":
            print(f"[bus-capture] 状态: 缓冲目录={CAPTURE_DIR}, 保留期={BUFFER_DAYS}天")
            files = glob.glob(os.path.join(CAPTURE_DIR, "events-*.jsonl"))
            print(f"[bus-capture] 现有缓冲文件: {len(files)} 个")
            return
        if arg.startswith("--since"):
            since_hours = int(arg.split("=")[1])
        if arg.startswith("--buffer"):
            BUFFER_DAYS = int(arg.split("=")[1])

    bus = load_bus()
    if not bus:
        return

    events = collect_events(bus, since_hours)
    if not events:
        print("[bus-capture] 最近无事件，跳过")
        return

    date_str = datetime.now().strftime("%Y%m%d")
    path = write_buffer(events, date_str)

    # 统计
    from collections import Counter
    by_target = Counter(e["tag"]["target"] for e in events)
    by_value = Counter(e["tag"]["value"] for e in events)
    print(f"[bus-capture] 捕捉 {len(events)} 条事件 → {path}")
    print(f"[bus-capture] 落档目标分布: {dict(by_target)}")
    print(f"[bus-capture] 价值分布: {dict(by_value)}")

    # 纪要生成（硬件守卫 + 模型互斥纪律）
    if do_summary and check_hardware():
        procs = check_model_conflict()
        if len(procs) > 1:
            print(f"[bus-capture] 检测到本地模型进程在跑 ({len(procs)}), 遵守 J35 不重复开，纪要延后")
        else:
            # 线程级纪要草稿（纯结构化摘要，供摄取角色审核）
            os.makedirs(SUMMARY_DIR, exist_ok=True)
            threads_seen = {}
            for e in events:
                if e["type"] == "message":
                    threads_seen.setdefault(e["thread"], []).append(e)
            for tid, msgs in list(threads_seen.items())[:10]:
                # 只对高价值线程生成纪要草稿
                if any(m["tag"]["value"] != "low" for m in msgs):
                    spath = os.path.join(SUMMARY_DIR, f"{date_str}-{tid[:8]}.md")
                    with open(spath, "w") as f:
                        f.write(f"# 线程纪要草稿 · {tid[:8]} · {date_str}\n\n")
                        f.write(f"> 来源：bus-capture 自动捕捉 · 待摄取角色审核落档\n\n")
                        f.write("## 事件摘要\n\n")
                        for m in msgs[:20]:
                            tag = m["tag"]
                            f.write(f"- [{tag['value']}/{tag['target']}] {m['from'][-8:]}→{m['to'][-8:]}: {m['text'][:120]}\n")
                        f.write(f"\n## 落档建议\n\n")
                        f.write(f"- 论坛帖: 共识/决策 {sum(1 for m in msgs if m['tag']['target']=='forum')} 条\n")
                        f.write(f"- research: 可复用知识 {sum(1 for m in msgs if m['tag']['target']=='research')} 条\n")
                        f.write(f"- 登记表: 资源相关 {sum(1 for m in msgs if m['tag']['target']=='registry')} 条\n")
                    print(f"[bus-capture] 纪要草稿: {spath}")
    else:
        print("[bus-capture] 硬件水位低或模型互斥，跳过纪要生成（仅捕捉标注）")

    # 群聊自动归档：高价值论坛帖自动 POST 到论坛（J36 沉淀三轨）
    # 门槛：仅归档「明确决策/共识/制度」线程（含决策词），避免普通协作线程刷论坛
    DECISION_KW = ["决策", "裁定", "拍板", "裁决", "结论", "决议", "批准", "确认执行",
                   "规范", "制度", "立项", "登记", "上线", "落地", "闭环"]
    forum_posts = [e for e in events if e["tag"]["target"] == "forum" and e["tag"]["value"] != "low"]
    if forum_posts and "--no-post" not in sys.argv:
        # 去重：已归档线程记录文件（防 15min 定时重复发帖刷屏）
        archive_mark = os.path.join(CAPTURE_DIR, "archived-threads.txt")
        archived = set()
        if os.path.exists(archive_mark):
            with open(archive_mark) as f:
                archived = set(l.strip() for l in f if l.strip())
        posted = 0
        # 按线程聚合论坛帖（每线程最多 1 帖，避免刷屏；仅决策/共识类线程）
        seen_threads = set()
        for e in forum_posts:
            tid = e.get("thread", "")
            if tid in seen_threads or tid in archived:
                continue
            seen_threads.add(tid)
            # 提取关键消息拼帖内容（敏感内容拦截：客户隐私/凭据/薪酬不落盘）
            content_lines = []
            for m2 in [x for x in events if x.get("thread") == tid and x["tag"]["target"] == "forum"][:5]:
                if is_sensitive(m2.get("text", "")):
                    continue  # 敏感消息跳过不落档
                content_lines.append(f"{m2['from'][-8:]}→{m2['to'][-8:]}: {m2['text'][:200]}")
            if not content_lines:
                continue
            # 决策词门槛：线程内容须含决策/共识/制度信号才落论坛（防普通协作刷屏）
            joined = " ".join(m.get("text", "") for m in events if m.get("thread") == tid)
            if not any(kw in joined for kw in DECISION_KW):
                continue
            # 来源会话名（线程首条消息发送者短 id）
            src = ""
            for m0 in events:
                if m0.get("thread") == tid and m0.get("from"):
                    src = m0["from"][-8:]
                    break
            post = {
                "board": "network",
                "title": f"[自动归档][{src}] 线程 {tid[:8]} · 协作纪要 {date_str}",
                "content": "bus-capture 自动沉淀（J36）· 已过敏感检测\n\n" + "\n".join(content_lines),
                "author": "bus-capture",
                "tags": ["auto-archive"],
            }
            try:
                import urllib.request
                req = urllib.request.Request(
                    "http://100.120.203.20:8091/api/post",
                    data=json.dumps(post).encode(),
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=5)
                r = json.loads(resp.read())
                if r.get("ok") or r.get("id"):
                    posted += 1
                    with open(archive_mark, "a") as f:
                        f.write(tid + "\n")
                    print(f"[bus-capture] 论坛自动归档: {tid[:8]} → id={r.get('id')}")
            except Exception as ex:
                print(f"[bus-capture] 论坛归档失败（{tid[:8]}）: {ex}")
        print(f"[bus-capture] 论坛自动归档完成: {posted} 帖（去重标记 {len(archived)} 线程已归档）")

if __name__ == "__main__":
    main()
