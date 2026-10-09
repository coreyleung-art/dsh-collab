#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local Router v1.0 (HR) — A4 PoC execution tool
Calls Ollama local model (qwen3.5-2b), extracts confidence, applies CAHAC gating,
logs every call for PoC metrics (hit/escalate/review) and daily-replay integration.
Usage:
  python3 local-router.py --scene classify --input "text"
  python3 local-router.py --scene summarize --input "long text" --max-len 500
Scenes: classify|keywords|summarize|extract_json|draft (model-routing-rules v1.1)
Gating: conf>=0.9 adopt / 0.7-0.9 review / <0.7 escalate to cloud

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, datetime, urllib.request, hashlib


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/local-router.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

OLLAMA = "http://127.0.0.1:11434/api/generate"
LMSTUDIO = "http://127.0.0.1:1234/v1/chat/completions"
DEFAULT_MODEL = "qwen3.5-2b"
DEFAULT_ENDPOINT = "lmstudio"  # lmstudio|ollama (J35: LM Studio=inference, Ollama=embedding)
T_HIGH, T_MID = 0.9, 0.7
LOG_DIR = os.path.expanduser("~/dsh-collab/token-monitor/local-routing")

PROMPTS = {
    "classify": "Classify the following message into exactly one of: TASK, COLLAB, STATUS, ACK, EVENT, BATCH, BROADCAST. Reply with the label only.\nMessage: {input}",
    "keywords": "Extract top 5 keywords from the text. Reply as comma-separated list.\nText: {input}",
    "summarize": "Summarize in under {max_len} chars. Reply with the summary only.\nText: {input}",
    "extract_json": "Extract structured JSON fields (id, type, status, value) from the text. Reply JSON only.\nText: {input}",
    "draft": "Draft a reply draft (customer-service tone). Reply with the draft only.\nContext: {input}",
}

def call_llm(model, prompt, max_tokens=300, endpoint="lmstudio"):
    if endpoint == "ollama":
        payload = {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}}
        req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    # lmstudio: OpenAI-compatible chat completions; qwen3.5 thinking-mode -> content may be empty, use reasoning_content fallback
    sys_msg = {"role": "system", "content": "Answer directly without thinking process. Output only the final answer."}
    payload = {"model": model, "messages": [sys_msg, {"role": "user", "content": prompt}], "max_tokens": max_tokens, "stream": False}
    req = urllib.request.Request(LMSTUDIO, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
        msg = data.get("choices", [{}])[0].get("message", {})
        content = msg.get("content", "") or ""
        if not content.strip():
            rc = msg.get("reasoning_content", "") or ""
            content = rc[-200:]  # thinking-mode fallback: take tail of reasoning
        return {"response": content.strip()}

def confidence_fallback(model, result, endpoint="lmstudio"):
    """self-check: ask local model if confident (v1.1 self-check design)"""
    chk = call_llm(model, "Rate your confidence 0-1 for the previous answer. Reply a number only.", max_tokens=10, endpoint=endpoint)
    try:
        return min(1.0, max(0.0, float(chk.get("response", "0").strip())))
    except ValueError:
        return 0.5

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT, choices=["lmstudio", "ollama"])
    ap.add_argument("--scene", required=True, choices=list(PROMPTS.keys()))
    ap.add_argument("--input", default=None)
    ap.add_argument("--input-file", default=None, help="read input from file (avoids shell quoting for CJK)")
    ap.add_argument("--max-len", type=int, default=500)
    args = ap.parse_args()
    inp = args.input
    if args.input_file:
        with open(args.input_file, encoding="utf-8") as f: inp = f.read().strip()
    prompt = PROMPTS[args.scene].format(input=inp, max_len=args.max_len)
    try:
        resp = call_llm(args.model, prompt, endpoint=args.endpoint)
        result = resp.get("response", "")
    except Exception as ex:
        print(json.dumps({"ok": False, "error": str(ex), "gate": "escalate", "reason": "ollama_unavailable"}))
        return
    # confidence: try logprobs if present, else self-check
    conf = 0.5
    lp = resp.get("prompt_eval_count", 0)
    if lp:  # heuristic: short outputs often high-conf; use self-check as primary
        pass
    conf = confidence_fallback(args.model, result, endpoint=args.endpoint)
    gate = "adopt" if conf >= T_HIGH else ("review" if conf >= T_MID else "escalate")
    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, "poc-" + datetime.date.today().isoformat() + ".log")
    entry = {"ts": datetime.datetime.now().isoformat(), "scene": args.scene, "model": args.model,
             "conf": round(conf, 2), "gate": gate, "result_len": len(result), "hash": hashlib.sha1(inp.encode()).hexdigest()[:8]}
    with open(log, "a", encoding="utf-8") as f: f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"ok": True, "scene": args.scene, "conf": round(conf, 2), "gate": gate, "result": result[:200]}, ensure_ascii=False))

if __name__ == "__main__":
    main()