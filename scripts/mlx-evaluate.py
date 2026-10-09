#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mlx-evaluate.py v1.0 — 微调模型二分类准确率评估（在 ~/mlx-venv 里运行）

用法（在 venv 激活后）:
  python ~/dsh-collab/scripts/mlx-evaluate.py

逻辑：加载基座 + LoRA adapter → 对 test 集 172 条逐条推理 → 解析「沉淀/跳过」→ 算准确率
       + 输出误判样本（供分析过拟合/边界）。

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== mlx-evaluate 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · mlx-evaluate.py v1.0 — 微调模型二分类准确率评估（在 ~/mlx-venv 里运行）")
    print("  · 用法（在 venv 激活后）:")
    print("  · 逻辑：加载基座 + LoRA adapter → 对 test 集 172 条逐条推理 → 解析「沉淀/跳过」→ 算准确率")
    print("  · + 输出误判样本（供分析过拟合/边界）。")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: json, time")
    print("  · ★ 第三方: mlx_lm ⇒ 缺失时行为须明确（拒绝或降级），不得抛栈")
    print("  · 固定日志: ~/dsh-collab/logs/mlx-evaluate.log")
    return 0


import sys as _r006_sys
if __name__ == "__main__" and "--selfcheck" in _r006_sys.argv:
    _r006_sys.exit(selfcheck())

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, os, sys


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/mlx-evaluate.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

MODEL = os.path.expanduser("~/mlx-models/Qwen2.5-3B-Instruct-4bit")
ADAPTER = os.path.expanduser("~/mlx-adapters/deposit-judge")
TEST = os.path.expanduser("~/dsh-collab/token-monitor/mlx-data/test.jsonl")

SYSTEM = (
    "你是沉积判定器。判断任务摘要是否值得「沉淀复用经验」——即是否产生了可复用的产出"
    "（脚本/插件/文档/规范/知识入库/修复bug/总结SOP/复用模式）。"
    "只回答「沉淀」或「跳过」两个字，不要解释。"
)

def main():
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler

    print("加载基座 + adapter ...")
    model, tokenizer = load(MODEL, adapter_path=ADAPTER)
    print("加载完成，开始评估 test 集 ...\n")

    # 温度 0 采样（贪心，确定性输出）
    sampler = make_sampler(temp=0.0)

    rows = []
    for line in open(TEST, encoding="utf-8"):
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    correct = 0
    total = 0
    wrong = []
    for r in rows:
        # 取 user 内容 + assistant 期望
        user_text = ""
        expect = ""
        for m in r["messages"]:
            if m["role"] == "user":
                user_text = m["content"]
            elif m["role"] == "assistant":
                expect = m["content"]

        # 构造 chat 消息
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_text},
        ]
        # 用 chat template
        prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        resp = generate(model, tokenizer, prompt=prompt, max_tokens=4, sampler=sampler)
        # 解析「沉淀」/「跳过」
        pred = "沉淀" if "沉淀" in resp else ("跳过" if "跳过" in resp else "?")
        total += 1
        if pred == expect:
            correct += 1
        else:
            wrong.append((user_text[:40], expect, pred, resp[:20]))

    acc = correct / total if total else 0
    print(f"=== 评估结果 ===")
    print(f"准确率: {correct}/{total} = {acc:.1%}")
    print(f"\n误判样本（前 20 条）:")
    for u, e, p, raw in wrong[:20]:
        print(f"  期望={e:3} 预测={p:3} | {u}")
    return acc

if __name__ == "__main__":
    main()
