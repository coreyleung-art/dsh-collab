# festival-pipeline v1.0.0 · 节日备货流水线工具包
> 交付：知了（a3bc8cba）| 2026-09-01 | 审核：HR/星桥 → i9 落链

## 组成
- lib/：festival-pipeline.js（主模块）+ apply-status-check.js + verify-registry.js
- scripts/：festival-pipeline.js（CLI）+ verify-all.js
- skills/：festival-pipeline SKILL.md
- docs/：交付报告 + 改进计划
- datasets/：coze 花材价格日报（价格雷达数据源）

## 使用
node scripts/festival-pipeline.js radar|cost|bom|check|plan|selfcheck

## 说明
read 级只读工具，无写操作；报名核查用 enterTime>0 权威判定（R030）
