#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""l3-semantic-check.py — rule-judge L3 语义层检查器（本地模型软门）

用户指示（2026-09-02）：推进 rule-judge L3 原型实现。
功能：AI 提议的语义把关（软门）——事实核查 / groundedness / 策略合理性 / 独立验证模型。
定位：L1/L2 拦『错』（数字硬错误），L3 拦『蠢』（策略不合理）——软门只决定重试 or 升级人工。

R006 九标准：CLI 形态 / TCC(--selfcheck) / 文档化 / 版本管理(--tool-version) / 自动落链 / CLI 治理。

用法：
  python3 l3-semantic-check.py --proposal '{"action":"change_price","params":{...},"basis":"..."}'   # 语义检查
  python3 l3-semantic-check.py --proposal-file proposal.json        # 从文件读提议
  python3 l3-semantic-check.py --model qwen2.5:3b                   # 指定模型（默认 qwen2.5:3b）
  python3 l3-semantic-check.py --selfcheck
  python3 l3-semantic-check.py --tool-version

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-remediate.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, datetime, urllib.request, ast, os


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-batch-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/l3-semantic-check.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

VERSION = "v1.0.0"
OLLAMA = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:3b"

def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def ollama_generate(prompt, model=DEFAULT_MODEL):
    """调用 Ollama 生成（本地零成本）"""
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
            return d.get("response", "")
    except Exception as e:
        return f"__OLLAMA_ERR__: {str(e)[:100]}"

# ═══════════ L3 语义检查 ═══════════
def semantic_check(proposal, model=DEFAULT_MODEL):
    """对 AI 提议做三层语义检查（软门）"""
    action = proposal.get("action", "?")
    params = proposal.get("params", {})
    basis = proposal.get("basis", "（无依据声明）")
    prompt = f"""你是花店 AI 运营的『语义裁判』（rule-judge L3 软门）。对 AI 提议做三层语义检查，输出 JSON。

【AI 提议】
- 动作: {action}
- 参数: {json.dumps(params, ensure_ascii=False)[:500]}
- 依据: {basis}

【检查项】
1. 事实核查：提议引用的依据是否可信（价格/库存/数据是否合理范围）？
2. Groundedness：提议是否基于依据、有无编造（幻觉）？
3. 策略合理性：整体策略是否过激/愚蠢（如全场同时降价、无视产能）？

【输出格式】（严格 JSON，不要其他文字）
{{
  "semantic_valid": true/false,
  "issues": ["问题1", "问题2"],
  "suggest": "pass(放行) / retry(打回重试) / escalate(升级人工)",
  "reason": "一句话总结"
}}"""
    resp = ollama_generate(prompt, model)
    if resp.startswith("__OLLAMA_ERR__"):
        return {"semantic_valid": False, "issues": [resp], "suggest": "escalate", "reason": "L3 模型不可用，保守升级人工"}
    # 解析 JSON（容忍模型输出噪声）
    try:
        start = resp.find("{")
        end = resp.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(resp[start:end])
    except Exception:
        pass
    return {"semantic_valid": False, "issues": ["L3 输出解析失败"], "suggest": "escalate",
            "reason": f"模型返回不可解析: {resp[:200]}"}

def cmd_check(proposal_str, proposal_file, model):
    if proposal_file:
        with open(proposal_file) as f:
            proposal = json.load(f)
    else:
        proposal = json.loads(proposal_str)
    print(f"== L3 语义检查（{model}）==")
    print(f"提议: {proposal.get('action','?')} {json.dumps(proposal.get('params',{}), ensure_ascii=False)[:80]}")
    print(f"依据: {proposal.get('basis','无')[:80]}")
    print()
    result = semantic_check(proposal, model)
    print(f"结果: semantic_valid={result.get('semantic_valid')}")
    print(f"  issues: {result.get('issues', [])}")
    print(f"  suggest: {result.get('suggest')}")
    print(f"  reason: {result.get('reason','')}")
    # 落链黑板
    note = {"ts": now(), "action": proposal.get("action"), "result": result, "model": model,
            "by": "l3-semantic-check"}
    body = json.dumps(note, ensure_ascii=False).encode()
    req = urllib.request.Request("http://127.0.0.1:8792/data/blueprint/rule-judge/l3-checks",
                                 data=body, method="PUT", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            print("✅ 已落链黑板 data/blueprint/rule-judge/l3-checks")
    except Exception:
        print("⚠️ 黑板落链失败（离线？）")
    return result

def selfcheck():
    ok = True
    try:
        ast.parse(open(__file__).read())
        print("✅ 语法 OK")
    except SyntaxError as e:
        print(f"❌ 语法: {e}"); ok = False
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as r:
            d = json.loads(r.read().decode())
            print(f"✅ Ollama 在线（{len(d.get('models',[]))} 模型）")
    except Exception as e:
        print(f"❌ Ollama: {e}"); ok = False
    print("TCC:", "PASS" if ok else "FAIL")
    return ok

def main():
    ap = argparse.ArgumentParser(description="rule-judge L3 语义检查器")
    ap.add_argument("--proposal", default="", help="AI 提议 JSON 字符串")
    ap.add_argument("--proposal-file", default="", help="提议 JSON 文件")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--tool-version", action="version", version=f"l3-semantic-check {VERSION}")
    args = ap.parse_args()

    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    elif args.proposal or args.proposal_file:
        cmd_check(args.proposal, args.proposal_file, args.model)
    else:
        # 演示模式
        demo = {"action": "change_price", "params": {"sku": "红玫瑰A级", "price": 68},
                "basis": "花价日报#20260901：向日葵 ¥1.88 高位，建议提价"}
        print("（未传提议，演示模式）\n")
        cmd_check("", None, args.model) if False else None
        result = semantic_check(demo, args.model)
        print(f"== L3 语义检查演示（{args.model}）==")
        print(f"提议: {demo['action']} {demo['params']}")
        print(f"依据: {demo['basis']}")
        print(f"结果: {json.dumps(result, ensure_ascii=False)}")

if __name__ == "__main__":
    main()
