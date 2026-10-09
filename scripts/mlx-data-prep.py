#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mlx-data-prep.py v1.0 — 沉积判定训练数据转 MLX 指令格式（纯规则，零 LLM）

职责：把 route-feedback-train.jsonl（{summary, actual} 平铺格式）
     转成 MLX-LM LoRA 微调所需的 train.jsonl / valid.jsonl / test.jsonl
     （messages 指令格式，二分类）。

设计（见 mlx-lora-finetune-plan-2026-08-22.md）：
  - 二分类：deposit→「沉淀」 / skip→「跳过」；review 不由模型判，由置信度阈值产出
  - 划分 8:1:1（铁律：test 训练期绝不碰）
  - 固定随机种子（可复现）

用法：
  python3 mlx-data-prep.py                    # 生成 mlx-data/{train,valid,test}.jsonl
  python3 mlx-data-prep.py --dry-run          # 只看统计不落盘
  python3 mlx-data-prep.py --balance          # 负样本过采样/正样本降采样均衡（deposit:skip 平衡）

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
    print("== mlx-data-prep 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · mlx-data-prep.py v1.0 — 沉积判定训练数据转 MLX 指令格式（纯规则，零 LLM）")
    print("  · 职责：把 route-feedback-train.jsonl（{summary, actual} 平铺格式）")
    print("  · 转成 MLX-LM LoRA 微调所需的 train.jsonl / valid.jsonl / test.jsonl")
    print("  · （messages 指令格式，二分类）。")
    print("  · 命令/参数: dry-run, balance, seed")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, collections, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/mlx-data-prep.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, random


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/mlx-data-prep.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

COLLAB = os.path.expanduser("~/dsh-collab")
SRC = os.path.join(COLLAB, "token-monitor", "route-feedback-train.jsonl")
OUT_DIR = os.path.join(COLLAB, "token-monitor", "mlx-data")

SYSTEM_PROMPT = (
    "你是沉积判定器。判断任务摘要是否值得「沉淀复用经验」——即是否产生了可复用的产出"
    "（脚本/插件/文档/规范/知识入库/修复bug/总结SOP/复用模式）。"
    "只回答「沉淀」或「跳过」两个字，不要解释。"
)

def load_src():
    out = []
    for line in open(SRC, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                r = json.loads(line)
                out.append(r)
            except Exception:
                continue
    return out

def to_messages(summary, actual):
    label = "沉淀" if actual == "deposit" else "跳过"
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": summary},
            {"role": "assistant", "content": label},
        ]
    }

def balance(data):
    """均衡：deposit 860 vs skip 292 失衡 → skip 过采样到等量（有放回）"""
    from collections import Counter
    c = Counter(r["actual"] for r in data)
    if c["deposit"] == c["skip"]:
        return data
    target = max(c["deposit"], c["skip"])
    deposit = [r for r in data if r["actual"] == "deposit"]
    skip = [r for r in data if r["actual"] == "skip"]
    # 少数类过采样
    if c["skip"] < c["deposit"]:
        extra = random.choices(skip, k=c["deposit"] - c["skip"])
        return deposit + skip + extra
    else:
        extra = random.choices(deposit, k=c["skip"] - c["deposit"])
        return deposit + skip + extra

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--balance", action="store_true", help="deposit/skip 均衡采样")
    ap.add_argument("--seed", type=int, default=42)
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()

    random.seed(args.seed)
    data = load_src()

    if args.balance:
        data = balance(data)
        print("已均衡采样（deposit/skip 等量）")

    # 洗牌 + 8:1:1 划分
    random.shuffle(data)
    n = len(data)
    n_train = int(n * 0.8)
    n_valid = int(n * 0.1)
    splits = {
        "train": data[:n_train],
        "valid": data[n_train:n_train + n_valid],
        "test": data[n_train + n_valid:],
    }

    print(f"=== MLX 数据准备（{n} 条 → 8:1:1）===")
    for name, rows in splits.items():
        from collections import Counter
        c = Counter(r["actual"] for r in rows)
        print(f"  {name:6} {len(rows):4} 条  deposit={c.get('deposit',0)} skip={c.get('skip',0)}")

    if args.dry_run:
        print("(dry-run) 未落盘")
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    for name, rows in splits.items():
        path = os.path.join(OUT_DIR, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(to_messages(r["summary"], r["actual"]), ensure_ascii=False) + "\n")
    print(f"\n✅ 已落盘: {OUT_DIR}/{{train,valid,test}}.jsonl")
    print("下一步（用户终端）:")
    print("  mlx_lm.lora --model ~/mlx-models/Qwen2.5-3B-Instruct-4bit \\")
    print(f"    --data {OUT_DIR} --train --adapter-path ~/mlx-adapters/deposit-judge")

if __name__ == "__main__":
    main()
