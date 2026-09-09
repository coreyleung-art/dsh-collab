#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bb-send-check.py — agent_send 发送前审查校验器（v2.2 前置门禁）

在调用 agent_send 之前运行，判断该消息应该怎么发：
  ✅ 放行（短提示/紧急/已落黑板）
  ⚠️ 建议（全文未落黑板 → 先写黑板再发短提示）

用法:
  python3 bb-send-check.py --text "要发送的消息文本"
  python3 bb-send-check.py --text "..." --to session-xxx   # 指定收件人（查其是否在黑板消费）
  python3 bb-send-check.py --text "..." --json             # JSON 输出（供脚本集成）

判定逻辑（v2.2 规则）:
  1. 短消息（≤200 字）→ 放行
  2. 含「看黑板 <key>」→ 放行（已是短提示格式）
  3. 含 urgent 标记 → 放行（紧急）
  4. 全文（>200 字）且无黑板引用 → 建议：写黑板 + 短提示
  5. 全文但提到已写黑板键（含 notes/ 或 data/ 路径）→ 提示确认黑板是否已写

输出示例:
  ✅ 放行: 短消息（120 字）
  ⚠️ 建议: 全文 500 字——请先写黑板（notes/mac-mini/xxx），再发『看黑板 notes/mac-mini/xxx』
"""
import argparse, json, sys, re

THRESHOLD = 200  # 与 agent-send-gate.py 一致

def check(text, to=None):
    """返回 (verdict, reason, advice)"""
    length = len(text)
    has_bb_ref = "看黑板" in text
    has_urgent = "urgent" in text.lower()
    has_path = bool(re.search(r"(notes/|data/|tasks/)[a-z0-9\-/]+", text))

    # 规则 1: 短消息
    if length <= THRESHOLD:
        return ("pass", f"短消息（{length} 字）", None)
    # 规则 2: 含看黑板（已是短提示格式，但 >200 字可能是带解释的短提示）
    if has_bb_ref:
        return ("pass", f"含看黑板引用（{length} 字）", None)
    # 规则 3: urgent 紧急
    if has_urgent:
        return ("pass", f"紧急标记 urgent（{length} 字）", None)
    # 规则 4: 全文且无黑板引用
    if not has_path:
        advice = f"请先写黑板（notes/mac-mini/<key> 或 data/<域>/<key>），再发『看黑板 <key>』"
        return ("warn", f"全文 {length} 字且无黑板引用", advice)
    # 规则 5: 全文但提到黑板路径
    advice = f"消息提到黑板路径，请确认内容已写入黑板；已写则改为发『看黑板 <key>』"
    return ("warn", f"全文 {length} 字（提及黑板路径，需确认已落盘）", advice)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="要发送的消息文本")
    ap.add_argument("--to", help="收件人（可选）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    verdict, reason, advice = check(args.text, args.to)
    if args.json:
        print(json.dumps({"verdict": verdict, "reason": reason, "advice": advice, "len": len(args.text)}, ensure_ascii=False))
        return

    icon = "✅" if verdict == "pass" else "⚠️"
    print(f"{icon} {reason}")
    if advice:
        print(f"   → {advice}")
    if args.to:
        print(f"   → 收件人: {args.to}")

if __name__ == "__main__":
    main()
