#!/usr/bin/env python3
"""
role-scan v1 —— 专业角色需求扫描（数据驱动）

作用：按秒级时间观即时扫描「专业角色需求信号」，替代「每周评估」的被动等待：
  ① 重复调研信号：research/ 下同一主题多文件（多会话各自跑 = 缺专业线）
  ② 超时/积压信号：总线消息里高频「超时/积压/待回复」
  ③ 工具缺口信号：消息里高频「缺/没有/做不了/不会」

用法：
  python3 role-scan.py                # 全量扫描（默认最近 48h 消息 + research/ 目录）
  python3 role-scan.py --hours=24     # 指定窗口
  python3 role-scan.py --research=PATH # 指定 research 目录（默认 ~/dsh-collab/research）

纪律：只读分析，不写文件、不广播（J34）；秒级时间观可随时跑。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/role-scan.log")


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
RESEARCH_DIR = os.path.expanduser("~/dsh-collab/research")

def load_bus():
    with open(BUS_FILE) as f:
        return json.load(f)

def scan_messages(bus, hours=48):
    """扫描最近消息，找角色需求信号"""
    cutoff = time.time() - hours * 3600
    texts = []
    for t in bus.get("threads", []):
        for m in t.get("messages", []):
            ts = m.get("time", 0) / 1000 if m.get("time") else 0
            if ts >= cutoff:
                texts.append(m.get("text", "") or "")
    return texts

def scan_research_duplicates():
    """扫描 research/ 目录找重复主题（多会话各自调研）"""
    if not os.path.isdir(RESEARCH_DIR):
        return []
    files = []
    for root, _, fnames in os.walk(RESEARCH_DIR):
        for fn in fnames:
            if fn.endswith(".md"):
                files.append(os.path.join(root, fn))
    # 按文件名主题粗分（去掉日期前缀）
    topics = Counter()
    for f in files:
        base = os.path.basename(f).lower()
        # 去掉日期前缀如 2026-08-17-
        base = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", base)
        base = re.sub(r"\.md$", "", base)
        # 取主词（第一段，去版本/序号）
        base = re.split(r"[-_v\d.]+", base)[0] if base else base
        if len(base) > 2:
            topics[base] += 1
    # 同一主词 ≥2 个文件 = 潜在重复调研
    return [(t, c) for t, c in topics.items() if c >= 2]

def main():
    hours = 48
    for arg in sys.argv[1:]:
        if arg.startswith("--hours="):
            hours = int(arg.split("=")[1])

    bus = load_bus()
    texts = scan_messages(bus, hours)

    # 信号 1：重复调研
    dup = scan_research_duplicates()

    # 信号 2：超时/积压
    timeout_kw = ["超时", "积压", "待回复", "排队", "未回", "过载"]
    timeout_hits = [t for t in texts if any(k in t for k in timeout_kw)]

    # 信号 3：工具缺口
    gap_kw = ["缺", "没有这个", "做不了", "不会", "无法", "不支持", "需要工具"]
    gap_hits = [t for t in texts if any(k in t for k in gap_kw)]

    # 信号 4：角色提案（已有提案池线索）
    propose_kw = ["新增角色", "新角色", "专职", "专员", "建议新增", "角色提案"]
    propose_hits = [t for t in texts if any(k in t for k in propose_kw)]

    print(f"[role-scan] 扫描最近 {hours}h 消息 {len(texts)} 条 + research/ 目录")
    print()
    print("【信号 1 · 重复调研】")
    if dup:
        for t, c in sorted(dup, key=lambda x: -x[1])[:10]:
            print(f"  ⚠️ 主题「{t}」有 {c} 份文件（疑似多会话各自调研 → 缺专业线）")
    else:
        print("  ✅ 无重复主题")
    print()
    print(f"【信号 2 · 超时/积压】命中 {len(timeout_hits)} 条")
    for t in timeout_hits[:5]:
        print(f"  - {t[:100]}")
    print()
    print(f"【信号 3 · 工具缺口】命中 {len(gap_hits)} 条")
    for t in gap_hits[:5]:
        print(f"  - {t[:100]}")
    print()
    print(f"【信号 4 · 角色提案】命中 {len(propose_hits)} 条")
    for t in propose_hits[:5]:
        print(f"  - {t[:100]}")
    print()
    total_sig = len(dup) + len(timeout_hits) + len(gap_hits) + len(propose_hits)
    if total_sig >= 3:
        print(f"[role-scan] ⚠️ 需求信号较强（{total_sig}）→ 建议 HR 评估新增/调整专业角色")
    else:
        print(f"[role-scan] 需求信号平稳（{total_sig}）→ 现有角色覆盖足够")

if __name__ == "__main__":
    main()
