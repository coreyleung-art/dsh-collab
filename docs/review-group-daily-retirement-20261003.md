# review-group.daily 退役清理记录（2026-10-03 · 用户裁决）

> 裁决：沉淀清理记录 → 删 plist（用户 2026-10-03 现场决策）

## 事实
- plist：~/Library/LaunchAgents/com.dsh.waimai.review-group.daily.plist（741B，2026-08-22 装载）
- 引用脚本：~/dsh-collab/scripts/daily-review-group.py —— **已不存在**
- 归档脚本：~/dsh-collab/scripts/archived-daily-review-group.py（v1.0.0，功能=读 aa528267 每日 10:00 差评数据 → 零 LLM 聚合 → 企微群回发；chat_id wrObL9WAAAmpV27LFG0NMGX4dZHAXngQ）
- launchd-scan（08:26Z）：plist loaded、runAtLoad=false、onetime——**指向空文件，触发即静默失败**

## 处置
1. 本记录落盘（✓ 本文档）+ 黑板 data/ops/review-group-daily-retirement-20261003
2. launchctl bootout + 删除 plist 文件（经 channel-gate launchd-daemons 登记）
3. 归档脚本保留（历史参考，不删）

## 关联
- 差评分析现役通道：waimai_review_daily / daily-bad-review（meituan-multi，无 LLM 聚合发群需求）
- 门：R036 通道变更治理门
