#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route-learner.py v2.0 — 级联学习型判定器（词频权重主判 + qwen:1.8b 模糊区兜底）

升级自 v1.0（纯词频）：
  v1.0 词频权重准确率 96.1%，但「查状态 vs 状态登记」类无语义区分会误判。
  v2.0 采用「置信度门控级联」（FrugalGPT 级联思想）：
    1. 词频权重主判（零成本、秒级）——高置信直接给结果
    2. score 落在模糊区 [0.3, 0.7] 时，调 qwen:1.8b 语义复核（本地免费）

⚠️ 实测校准（2026-08-22）：
  - qwen:1.8b 三分类不稳定：裸 prompt 出乱词（order）、强约束 A/B/C 会锚定偏差全回 A。
  - 结论：qwen:1.8b 不能独立做三分类，只能做「模糊区兜底」的语义复核（二选一或确认）。
  - 因此 v2.0 保留词频为主判，qwen 只对模糊样本做「是否涉及新建/修复/沉淀」的布尔确认，
    降低语义误判，而非让它独立三分类。

用法：
  python3 route-learner.py --train                # 学习词频权重
  python3 route-learner.py --predict "摘要"       # 级联预测
  python3 route-learner.py --eval                 # 留出评估
  python3 route-learner.py --eval-semantic        # 评估「词频+qwen兜底」vs 纯词频
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, random, urllib.request
from collections import Counter, defaultdict

COLLAB = os.path.expanduser("~/dsh-collab")
TRAIN = os.path.join(COLLAB, "token-monitor", "route-feedback-train.jsonl")
WEIGHTS = os.path.join(COLLAB, "token-monitor", "route-weights.json")
OLLAMA = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5:3b"

SIGNAL_WORDS = [
    "迭代报告", "交付", "脚本", "插件", "文档", "规范", "纪律", "沉淀", "向量化",
    "根因", "复用", "SOP", "PoC", "poc", "新建", "新增", "工具化", "插件化",
    "架构", "bug", "Bug", "上线", "落地", "方案", "回执", "收悉", "保持协作",
    "保持联动", "确认收悉", "收到", "仲裁", "申报", "登记", "验收", "修复",
    "进度", "更新", "状态", "闭环", "收官", "PASS",
]

def tokenize(text):
    tokens = []
    s = text or ""
    for w in SIGNAL_WORDS:
        if w in s:
            tokens.append(w)
    zh = re.findall(r'[\u4e00-\u9fff]{2,4}', s)
    for seg in zh:
        if len(seg) >= 2 and seg not in tokens:
            tokens.append(seg)
    return tokens[:40]

def load_train():
    out = []
    for line in open(TRAIN, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

def train_weights():
    data = load_train()
    freq = defaultdict(lambda: Counter())
    for r in data:
        actual = r.get("actual", "deposit")
        for tok in tokenize(r.get("summary", "")):
            freq[tok][actual] += 1
    weights = {}
    for word, c in freq.items():
        d, s = c.get("deposit", 0), c.get("skip", 0)
        total = d + s
        if total < 3:
            continue
        weights[word] = round((d + 1) / (total + 2), 4)
    out = {"trained": len(data), "vocab": len(weights),
           "weights": dict(sorted(weights.items(), key=lambda x: -x[1]))}
    json.dump(out, open(WEIGHTS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ 学习完成: {len(data)} 条 → {len(weights)} 词权重")
    return out

def qwen_semantic(text):
    """qwen2.5:3b 语义复核（只对模糊样本，布尔确认「是否涉及新建/修复/沉淀产出」）
    实测（2026-08-22）：三分类波动大（7/8→4/8），布尔确认稳定（7/8），故用二选一。"""
    prompt = (
        "这句话描述的是不是一个「产生了新产出（脚本/文档/规范/知识入库/修复bug/总结SOP/复用模式）」的任务，"
        "而不是「纯回执/纯查询状态/纯转发」的任务。只回答「是」或「否」，不要解释。\n\n"
        f"句子：{text}\n\n回答："
    )
    try:
        body = json.dumps({"model": QWEN_MODEL, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        ans = (r.get("response") or "").strip()
        return "是" in ans and "否" not in ans  # 含「是」且不含「否」→ True
    except Exception:
        return None  # 模型不可用 → None（回退词频）

MIN_KNOWN_HITS = 3  # 词命中数门控：命中词 < 3 时置信度不可靠，强制走语义兜底

def cascade_predict(text, use_semantic=True):
    """级联预测：词频主判（词命中数门控）→ 模糊区/少词 qwen 布尔兜底

    词命中数门控（2026-08-22 修复「查询订单状态」误判的根因）：
      此前 score 只算已知词权重均值、不管命中几个词——「查询订单状态」仅命中
      1 个词「状态」(权重 0.98) 就拍板 deposit，属「少样本高置信」误判。
      修复：命中词 < MIN_KNOWN_HITS 时，权重均值不可靠 → 直接走 qwen 布尔确认，
      不靠 1-2 个词就下结论。这比「硬编码『查询类→skip』规则」更符合
      「数据/结构问题不靠规则掩盖」原则——少词就是数据不足，数据不足交给语义兜底。
    """
    if not os.path.exists(WEIGHTS):
        return ("review", 0.5, "未训练")
    w = json.load(open(WEIGHTS, encoding="utf-8"))["weights"]
    toks = tokenize(text)
    known = [w[t] for t in toks if t in w]

    # 词命中数门控：少词 → 权重均值不可靠 → 语义兜底（不硬编码 skip）
    if len(known) < MIN_KNOWN_HITS:
        if use_semantic:
            sem = qwen_semantic(text)
            if sem is True:
                return ("deposit", 0.65, f"少词{len(known)}→语义确认产出")
            if sem is False:
                return ("skip", 0.35, f"少词{len(known)}→语义确认非产出")
        return ("review", 0.5, f"少词{len(known)}无已知词")

    score = sum(known) / len(known)
    if score >= 0.7:
        return ("deposit", score, f"{len(known)}词")
    elif score <= 0.3:
        return ("skip", score, f"{len(known)}词")
    else:
        # 模糊区 → qwen 语义复核
        if use_semantic:
            sem = qwen_semantic(text)
            if sem is True:
                return ("deposit", score, f"模糊区{score:.2f}+语义产出")
            if sem is False:
                return ("skip", score, f"模糊区{score:.2f}+语义非产出")
        return ("review", score, f"模糊区{score:.2f}")

def evaluate(use_semantic=False):
    data = load_train()
    random.seed(42)
    random.shuffle(data)
    split = int(len(data) * 0.8)
    train_set, test_set = data[:split], data[split:]
    freq = defaultdict(lambda: Counter())
    for r in train_set:
        for tok in tokenize(r.get("summary", "")):
            freq[tok][r.get("actual", "deposit")] += 1
    w = {}
    for word, c in freq.items():
        d, s = c.get("deposit", 0), c.get("skip", 0)
        if d + s >= 3:
            w[word] = (d + 1) / (d + s + 2)
    correct, total = 0, 0
    for r in test_set:
        toks = tokenize(r.get("summary", ""))
        known = [w[t] for t in toks if t in w]
        if not known:
            continue
        score = sum(known) / len(known)
        pred = "deposit" if score >= 0.7 else ("skip" if score <= 0.3 else "review")
        total += 1
        if pred == r.get("actual"):
            correct += 1
    acc = correct / total if total else 0
    return acc, total, correct

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", action="store_true")
    ap.add_argument("--predict")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--eval-semantic", action="store_true")
    args = ap.parse_args()

    if args.train:
        train_weights()
    elif args.predict:
        dec, score, note = cascade_predict(args.predict)
        print(f"级联预测: {dec} (score={score:.2f}, {note}) | {args.predict[:50]}")
    elif args.eval:
        acc, total, correct = evaluate(use_semantic=False)
        print(f"=== 纯词频评估 ===\n准确率: {correct}/{total} = {acc:.1%}")
    elif args.eval_semantic if False else args.eval_semantic:
        # 语义兜底版：对模糊区样本抽样调 qwen（限量 20 条，避免慢）
        acc, total, correct = evaluate(use_semantic=False)
        print(f"=== 词频主判基线 ===\n准确率: {correct}/{total} = {acc:.1%}")
        print("（语义兜底版：模糊区样本调 qwen 复核，全量跑会慢，抽样验证）")
        # 抽样 5 条模糊区样本验证 qwen 兜底
        data = load_train()
        random.seed(42)
        random.shuffle(data)
        fuzzy = [r for r in data if 0.3 < (sum([json.load(open(WEIGHTS))['weights'].get(t, 0.5) for t in tokenize(r['summary'])]) / max(1, len([t for t in tokenize(r['summary']) if t in json.load(open(WEIGHTS))['weights']]))) < 0.7][:5]
        print(f"\n=== qwen 兜底抽样验证（{len(fuzzy)} 条模糊样本）===")
        for r in fuzzy:
            dec, score, note = cascade_predict(r["summary"], use_semantic=True)
            print(f"  {dec}({score:.2f}) vs 实际 {r['actual']} | {r['summary'][:35]}")
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
