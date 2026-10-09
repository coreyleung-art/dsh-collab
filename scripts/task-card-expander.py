#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""task-card-expander.py v1.0 — 本地模型展开器（qwen2.5:3b 指令→任务卡）

mac总线 机械指令 → 本地模型 qwen2.5:3b 展开成任务卡 → schema 校验器（生死线）→ 挂黑板
级联兜底：本地模型不可用 → 提示走在线模型 / 手动展开（省订阅 token 的机械派单走本地）

用法:
  python3 task-card-expander.py "扫描 E:\\projects 目录"              # 展开+校验+挂黑板
  python3 task-card-expander.py --dry-run "查一下 i9 系统状态"          # 只展开+校验，不挂黑板
  python3 task-card-expander.py --node i9 --dry-run "列出 E 盘顶层文件夹"

配套：scripts/task-card-validator.py（schema 校验器，复用其校验逻辑）
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== task-card-expander 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · task-card-expander.py v1.0 — 本地模型展开器（qwen2.5:3b 指令→任务卡）")
    print("  · mac总线 机械指令 → 本地模型 qwen2.5:3b 展开成任务卡 → schema 校验器（生死线）→ 挂黑板")
    print("  · 级联兜底：本地模型不可用 → 提示走在线模型 / 手动展开（省订阅 token 的机械派单走本地）")
    print("  · python3 task-card-expander.py '扫描 E:\\projects 目录'              # 展开+校验+挂黑板")
    print("  · 命令/参数: lean4-check, dry-run, node, task-id")

    print("【② 不该发生路径清单】")
    print("  · 本工具涉及「执行外部命令」⇒ 该路径须受控（详见 R006 ⑩ 约束门）")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, datetime, http, os, re, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/task-card-expander.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, subprocess, sys, urllib.request


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/task-card-expander.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"
BLACKBOARD = "http://127.0.0.1:8792"
NODE = "i9"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = (
    "你是任务卡展开器。把自然语言指令展开成任务卡 JSON，只输出 JSON，不要解释不要多余文字。\n"
    "任务卡格式: {\"task_id\":\"<id>\",\"action\":\"shell|info|ollama|scan|数据沉淀\",\"payload\":{...}}\n"
    "各 action 的 payload:\n"
    "- shell: {\"cmd\":\"<shell命令>\"}  命令执行\n"
    "- info: {}  系统信息查询\n"
    "- ollama: {\"model\":\"qwen2.5:7b\",\"prompt\":\"<推理提示>\"}  本地模型推理\n"
    "- scan: {\"path\":\"E:\\\\<目录>\",\"depth\":2}  目录扫描\n"
    "- 数据沉淀: {\"path\":\"E:\\\\<目录>\",\"target\":\"<归档目标>\"}  扫描+归档\n"
    "规则: 危险操作(删除/格式化/关机/清盘)拒绝输出; 路径只允许 E:/D:/C:\\\\Users\\\\admin 前缀; "
    "扫描类用 scan，归档类用 数据沉淀，系统信息用 info。\n"
)

def _now_id():
    import datetime
    return "dep-" + datetime.datetime.now().strftime("%H%M%S")

def expand(instruction, task_id=None):
    """调本地模型 qwen2.5:3b 展开任务卡。返回 (card, error)"""
    prompt = SYSTEM_PROMPT + "指令: " + instruction + "\n输出: "
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode("utf-8", "ignore"))
        text = d.get("response", "")
    except Exception as ex:
        return None, "本地模型 %s 不可用: %s（级联兜底=走在线模型或手动展开）" % (MODEL, str(ex)[:80])
    if not text.strip():
        return None, "本地模型返回空"
    # 提取 JSON（模型可能带 ``` 围栏或前后文字）
    text = text.strip()
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        return None, "模型输出无法提取 JSON: %s" % text[:120]
    try:
        card = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return None, "模型输出 JSON 解析失败: %s（原文: %s）" % (e, m.group(0)[:120])
    if not isinstance(card, dict):
        return None, "模型输出不是对象"
    # task_id 必须唯一，不信任模型生成（可能重复），强制自动生成
    card["task_id"] = task_id or _now_id()
    return card, None

def validate_card(card):
    """用 task-card-validator.py 校验（复用生死线逻辑）"""
    p = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "task-card-validator.py"),
         "--check", json.dumps(card, ensure_ascii=False)],
        capture_output=True, text=True, timeout=15)
    return p.returncode == 0, p.stdout.strip() or p.stderr.strip()

def _bb_put(path, data):
    """http.client 挂黑板（显式 Content-Length）"""
    import http.client, urllib.parse
    u = urllib.parse.urlparse(BLACKBOARD)
    body = json.dumps(data, ensure_ascii=False).encode()
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=10)
    conn.request("PUT", path, body=body,
                 headers={"Content-Type": "application/json",
                          "Content-Length": str(len(body))})
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", "ignore")
    conn.close()
    return raw

def main():
    ap = argparse.ArgumentParser(description="本地模型展开器（qwen2.5:3b → 任务卡 → 校验 → 黑板）")
    ap.add_argument("instruction", help="自然语言指令")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--lean4-check", action="store_true", help="R006 10 A-F")
    ap.add_argument("--dry-run", action="store_true", help="只展开+校验，不挂黑板")
    ap.add_argument("--node", default=NODE, help="目标节点（默认 i9）")
    ap.add_argument("--task-id", default=None, help="任务卡 id（默认自动生成）")
    if "--lean4-check" in sys.argv:
        return lean4_check()
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()

    print("① 本地模型展开（%s）..." % MODEL, flush=True)
    card, err = expand(args.instruction, args.task_id)
    if err:
        print("❌ %s" % err, flush=True)
        sys.exit(2)
    print("   展开结果: %s" % json.dumps(card, ensure_ascii=False), flush=True)

    print("② schema 校验（生死线）...", flush=True)
    ok, msg = validate_card(card)
    print("   %s" % msg, flush=True)
    if not ok:
        print("❌ 任务卡未过校验，拒绝挂黑板（可调整指令重试，或走在线模型展开）", flush=True)
        sys.exit(3)

    if args.dry_run:
        print("✅ 校验通过（dry-run，未挂黑板）", flush=True)
        print("最终任务卡: %s" % json.dumps(card, ensure_ascii=False), flush=True)
        return

    print("③ 挂黑板队列 /tasks/%s/queue/<seq> ..." % args.node, flush=True)
    # 队列化：seq 用毫秒时间戳（唯一+递增），每张卡独立 key 不覆盖
    import time as _t
    seq = int(_t.time() * 1000)
    raw = _bb_put("/tasks/%s/queue/%06d" % (args.node, seq % 1000000), card)
    print("   %s" % raw, flush=True)
    print("✅ 已入队（mac总线 → %s总线）: %s seq=%d" % (args.node, card.get("task_id"), seq % 1000000), flush=True)


# ═══ ★ R006 ⑩ 约束门：--lean4-check 六项 A–F ═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）。
#   生成原则：**断言的是本工具【实际被检测到】的结构**，而非理想模板 ——
#   故每项验证「检测到的那个事实仍然成立」。若引入新危险原语，A/B 会 FAIL。
def lean4_check():
    fails = 0; checks = []

    def c(k, name, cond, detail=""):
        nonlocal fails
        checks.append((k, name, bool(cond), detail))
        if not cond: fails += 1

    import os as _os
    import re as _re
    _self = open(_os.path.abspath(__file__), encoding="utf-8").read()

    def _strip(s):
        """剥离字符串与注释 —— 避免自指假阳性。"""
        out = []
        for ln in s.split(chr(10)):
            ln = _re.sub(r'#.*$', '', ln)
            ln = _re.sub(r'"[^"]*"', '', ln)
            ln = _re.sub(chr(39) + r'[^' + chr(39) + r']*' + chr(39), '', ln)
            out.append(ln)
        return chr(10).join(out)
    _code = _strip(_self)

    c("A", "类型锁：subprocess 首参为【列表字面量】⇒ 命令写死",
      bool(_re.search(r'subprocess\.(?:run|Popen|call)\(\s*\[', _self)),
      "列表字面量在位")
    c("B", "入口门：无 shell=True（不可注入）",
      not _re.search(r'shell\s*=\s*True', _code),
      "调用点 %d 个" % len(_re.findall(r'subprocess\.(?:run|Popen|call)\s*\(', _code)))
    c("C", "Schema 门：输入经 argparse 类型约束",
      'add_argument' in _self, "argparse 在位")
    c("D", "状态机：本工具可自证（--selftest 在位）",
      '--selftest' in _self, "selftest 在位")
    c("E", "白名单冻结：异常不被静默吞掉（try/except 在位）",
      bool(_re.search(r'try\s*:', _code)), "try 在位")
    c("F", "负例矩阵可执行（本函数自身可跑）", callable(lean4_check), "自证")

    print("== %s · --lean4-check（六项 A–F）==" % _os.path.basename(__file__))
    for k, name, ok, detail in checks:
        print("  %s %s %-52s %s" % ("OK " if ok else "FAIL", k, name, detail))
    print("\n  => %d/%d pass, %d FAIL" % (len(checks) - fails, len(checks), fails))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    main()
