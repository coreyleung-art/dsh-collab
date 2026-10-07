#!/usr/bin/env python3
"""卡 JSON 检查器：解析 + 内容类/结构类手误。
用法：python3 card-json-check.py <file.json>
退出码 0=通过 1=有问题
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, re

def main(path, list_quotes=False):
    raw = open(path, encoding="utf-8").read()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"解析: ❌ {e.msg}: line {e.lineno} column {e.colno} (char {e.pos})")
        print("  ★ 首选怀疑：值里嵌了**未转义的 ASCII 双引号**（实测基线 9% 的卡值里含 `\"`；"
              "只差一个反斜杠就从合法变非法）⇒ 改用中文引号，或转义为 `\\\"`")
        lines = raw.split("\n")
        # ── 降级诊断（新增）：解析失败时仍尽量指出【原因】，不只给行号 ──
        print("降级诊断（解析失败时逐行找可疑形态）：")
        found = False
        for i, L in enumerate(lines, 1):
            # 形态1：整行只是一个字符串，后面直接跟 , 或 } 或行尾 ⇒ 缺 : 与 value
            if re.match(r'^\s*"(?:[^"\\]|\\.)*"\s*[,\}]\s*$', L):
                print(f"  ★ 行 {i}: 疑似【缺 `:` 与 value】—— 该行只有 key 没有值")
                print(f"     {L[:150]}")
                found = True
            # 形态2：行内 ASCII 双引号个数为奇数
            if L.count('"') % 2 == 1:
                print(f"  ★ 行 {i}: ASCII 双引号个数为奇数（{L.count(chr(34))}）—— 字符串可能未闭合")
                print(f"     {L[:150]}")
                found = True
        if not found:
            print("  （未匹配到已知可疑形态，请人工看该行前后）")
        print(f"  出错行全文: {lines[e.lineno-1][:200] if e.lineno-1 < len(lines) else '(越界)'}")
        return 1
    # 解析通过 ⇒ 找值里含 ASCII 双引号的字段
    bad = []
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for i, it in enumerate(o):
                walk(it, f"{path}[{i}]")
        elif isinstance(o, str) and '"' in o:
            bad.append((path, o[:80]))
    walk(d)
    print("解析: ✅ 合法")
    print(f"字段数 = {len(d)}")
    # ★ 判据修正（2026-09-14，实测后）：**「值里含 ASCII 双引号」是合法形状，不是缺陷。**
    #   实测基线：data/registry + notes/mac-mini 抽样 150 键 ⇒ **14 个（9%）**的值里含 `"`。
    #   ⇒ 9% 的基线意味着：把它当**报警**，它每 11 张卡就叫一次 ⇒ 噪声级（恒响的哨兵 = 没有哨兵）。
    #   ⇒ 正确的分工：**触发条件 = 解析失败**（硬、可判）；**「含引号的值」= 解析失败之后的诊断列表**
    #     （那时它极可能正是原因）。解析成功时只**计数**，要明细须显式 --list-quotes。
    print(f"信息: 值里含 ASCII 双引号 = {len(bad)} 处（**合法形状**，仅计数；9% 基线上报警会变成噪声）")
    if bad and (list_quotes or False):
        print(f"明细（--list-quotes）：")
        for p, s in bad:
            print(f"  {p} = {s!r}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--list-quotes" in sys.argv))
