# CLD 公约维护与提案通道（convention-PR）v1 · 2026-09-09 星桥
> 用户指示：公约维护不应单方面(mac-mini 星桥)掌握——端侧主桥(MBP/i9)应能提交补充意见
> 类比 Git PR：任何接入设备可提提案 → 评审 → 裁决 → 合并 → 版本 bump → 全节点通知

## 一、提案通道（端侧如何提）

### 1.1 提交方式（任一）
- **端侧守护信封**: bus/send {from:"<dev>:<桥>", target:"mac-mini", action:"convention-propose",
  payload:{pr:{...}}} → mac-mini 守护转提案区
- **端侧黑板直写**: 写 data/registry/convention-proposals/<id>.json（经守护或协调者）
- **本机角色**: 同左直接写

### 1.2 提案格式（模板必填字段）
```json
{
  "pr_id": "CP-20260909-<seq>",        // 提案号: 日期+序号
  "title": "建议修改<条款>",            // 一句话
  "clause": "<公约条款引用, 如 §3.1.1-B / G-Cxx>",
  "suggest": "<具体修改建议, 替换/新增条文文本>",
  "reason": "<理由: 实测问题/成本/边界场景>",
  "proposer": "<设备:角色, 如 mbp:mbp-bus>",  // 提出方(端侧主桥可提)
  "ts": "<ISO时间>",
  "status": "pending"                   // pending→review→merged|rejected
}
```

## 二、评审与合并流程（PR 生命周期）

```
pending(端侧提交)
  → review(星桥汇总+相关方评审, 3日窗口)
  → 裁决: merged(用户/协调者批准) | rejected(带理由) | 需修订
  → merged: 并入公约 + 版本 bump(v1.x) + notify-nodes.sh 抄送全节点
  → 变更记录入公约 §八 changelog
```

### 评审原则
- 提案须**带实测/场景理由**（无理由=纸面意见，R030 精神）
- 涉及成本/安全(如 G-Cxx 断言) → 需数据调查员/守望复核
- 用户裁决权保留：重大变更走 R008（用户批准）
- **端侧主桥提案优先响应**（它们是被约束方, 最懂落地痛点）

## 三、工具 convention-pr.py
```
python3 convention-pr.py list                    # 列出全部提案(pending/review/merged)
python3 convention-pr.py submit --from mbp:mbp-bus --clause "§3.1.1-B" --title "..." --suggest "..." --reason "..."
python3 convention-pr.py review <pr_id>          # 星桥标记 review(评审中)
python3 convention-pr.py merge <pr_id>           # 并入公约(裁决通过)
python3 convention-pr.py reject <pr_id> --reason "..."
```
- 提案库: data/registry/convention-proposals/*.json
- Lean4 断言: G-C34 proposal-channel（提案区存在+格式校验）
- G-C35 end-node-propose（端侧桥可提交——from 校验允许 mbp/mbp-bus/i9 等）

## 四、落地检查
- [ ] data/registry/convention-proposals/ 目录建
- [ ] convention-pr.py 可 submit/list/review/merge/reject
- [ ] 端侧(守护)收到 convention-propose 信封 → 落提案区
- [ ] 合并触发 notify-nodes.sh 抄送
- [ ] G-C34/C35 断言 PASS

---
*星桥 2026-09-09 · 公约 PR 机制 · 端侧共治*
