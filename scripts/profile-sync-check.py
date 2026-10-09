#!/usr/bin/env python3
"""
profile-sync-check v1 —— 档案/登记表一致性检查（资源登记 watcher）

作用：比对「总线 agent_profiles（事实）」与「登记表 §3（登记）」差异，
     提示 HR 哪些档案变更未同步到登记表——省手工比对，秒级执行。

用法：
  python3 profile-sync-check.py            # 输出差异报告
  python3 profile-sync-check.py --diff     # 只看有差异的
  python3 profile-sync-check.py --reg PATH # 指定登记表路径（默认 ~/dsh-collab/resource-registry.md）

纪律：只读检查，不写文件、不广播（J34）；秒级时间观可随时跑。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json
import os
import re
import sys
from datetime import datetime


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/profile-sync-check.log")


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
REG_FILE = os.path.expanduser("~/dsh-collab/resource-registry.md")

def load_bus_profiles():
    with open(BUS_FILE) as f:
        bus = json.load(f)
    return bus.get("profiles", [])

def extract_registered_sessions(reg_text):
    """从登记表 §3 提取已登记会话短 id（session-xxx 8位；支持合并行多 id）"""
    found = set()
    # 只取 §3 区段（## 3. 到 ## 4.）
    m = re.search(r"## 3\..*?(?=\n## 4\.)", reg_text, re.DOTALL)
    sec3 = m.group(0) if m else reg_text
    for line in sec3.split("\n"):
        if "|" not in line:
            continue
        ids = re.findall(r"session-[0-9a-f]{8}", line)
        found.update(ids)
        # 合并行裸 id（形如 | e83724af / 0373d601 |）
        cells = [c.strip() for c in line.split("|")]
        if cells:
            first = cells[1] if len(cells) > 1 else ""
            # 拆斜杠取每个 8 位 hex
            for part in re.split(r"[/, ]+", first):
                if re.fullmatch(r"[0-9a-f]{8}", part):
                    found.add(part)
    return found

def short_id(aid):
    """完整 session id → 短 id（session-前8位）"""
    if "session-" in aid:
        return aid[:len("session-") + 8]
    return aid[:8]

def main():
    only_diff = "--diff" in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == "--reg" and i + 1 < len(sys.argv):
            global REG_FILE
            REG_FILE = os.path.expanduser(sys.argv[i + 1])

    profiles = load_bus_profiles()
    with open(REG_FILE) as f:
        reg_text = f.read()
    registered = extract_registered_sessions(reg_text)

    unregistered = []
    for p in profiles:
        aid = p.get("agentId", "")
        if aid and short_id(aid) not in registered:
            unregistered.append({
                "id": aid,
                "role": p.get("role", ""),
                "resources": p.get("resources", [])[:3],
                "updated": p.get("updatedAt", 0),
            })

    def fmt_ts(ms):
        try:
            return datetime.fromtimestamp(ms / 1000).strftime("%m-%d %H:%M")
        except Exception:
            return str(ms)

    print(f"[profile-sync] 总线档案 {len(profiles)} 条 / 登记表已登记 {len(registered)} 个会话")
    if unregistered:
        print(f"[profile-sync] ⚠️ 未同步到登记表的档案: {len(unregistered)} 条")
        for u in unregistered[:15]:
            print(f"  - {short_id(u['id'])} | {u['role'][:40]} | 更新于 {fmt_ts(u['updated'])}")
            if u["resources"]:
                print(f"      资源: {', '.join(str(r)[:60] for r in u['resources'])}")
    else:
        print("[profile-sync] ✅ 全部档案已登记，无差异")
    if only_diff and not unregistered:
        print("[profile-sync] 无差异（--diff 模式退出 0）")

if __name__ == "__main__":
    main()
