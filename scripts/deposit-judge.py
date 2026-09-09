#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deposit-judge.py v1.0 — 微调模型判定入口（MLX 融合模型，本地免费）

⛔ ARCHIVED（2026-08-22 止损归档）：微调模型学到「长度=格式」代理而非语义，
   实测 4 关键样本 3/4，比词频级联（4/4）差。不接入 route-learner，仅留档供
   未来有真实边界数据时重启。详见 research/cost-governance/mlx-lora-finetune-plan §八。

职责：加载 MLX LoRA 融合模型（deposit-judge-fused），对任务摘要做二分类「沉淀/跳过」，
      review 由「低置信」产出（不独立判）。

用法（在 ~/mlx-venv 激活后）:
  python ~/dsh-collab/scripts/deposit-judge.py "查询外卖订单状态"
  python ~/dsh-collab/scripts/deposit-judge.py --stdin    # 从 stdin 读多行批量判

输出: JSON {decision: 沉淀|跳过, summary: 摘要}

设计（见 mlx-lora-finetune-plan + decision-system-principle）:
  - 二分类（沉淀/跳过），review 由置信度阈值产出（本脚本贪心采样，暂不产出 review，
    由调用方 route-learner 决定阈值兜底）
  - 与 route-learner.py 的级联衔接：本脚本是「主判」，词频权重是「兜底」
"""
import argparse, json, sys

MODEL = "/Users/coreyleung/mlx-models/deposit-judge-fused"

SYSTEM = (
    "你是沉积判定器。判断任务摘要是否值得「沉淀复用经验」——即是否产生了可复用的产出"
    "（脚本/插件/文档/规范/知识入库/修复bug/总结SOP/复用模式）。"
    "只回答「沉淀」或「跳过」两个字，不要解释。"
)

_model = None
_tokenizer = None
_sampler = None

def _load():
    global _model, _tokenizer, _sampler
    if _model is None:
        from mlx_lm import load, generate
        from mlx_lm.sample_utils import make_sampler
        _model, _tokenizer = load(MODEL)
        _sampler = make_sampler(temp=0.0)
    return _model, _tokenizer, _sampler

def judge(summary: str) -> dict:
    model, tokenizer, sampler = _load()
    from mlx_lm import generate
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": summary},
    ]
    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    resp = generate(model, tokenizer, prompt=prompt, max_tokens=4, sampler=sampler)
    decision = "沉淀" if "沉淀" in resp else ("跳过" if "跳过" in resp else "review")
    return {"decision": decision, "summary": summary}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="单条摘要")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 读多行批量判")
    args = ap.parse_args()

    if args.stdin:
        for line in sys.stdin:
            line = line.strip()
            if line:
                r = judge(line)
                print(json.dumps(r, ensure_ascii=False))
    elif args.text:
        print(json.dumps(judge(args.text), ensure_ascii=False))
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
