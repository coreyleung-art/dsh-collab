# 全部蓝图依赖关系 + 前置顺序评估报告

> 明鉴 v2 · 2026-09-01T14:36:53 · 10 蓝图

## 依赖分析
- 19 条关系边 · 无环（拓扑排序通过）
- 双向引用 2 组：flowernet↔platform（层级包含非真环）/ flowernet↔aistartup（互引非阻塞）

## 前置顺序（拓扑）
1. blueprint-platform（方法论）→ 2. flowernet-platform（技术底座）→ 3. flowernet（业务主线）→ 4. flowernet-erp（数据底座）→ 5. miniapp → 6. website → 7. agent-network（底座）→ 8. rule-judge（验证）→ 9. aistartup → 10. banking

## 前置链
- 核心链：方法论→技术底座→业务主线→数据底座→终端
- 治理链：platform#P1→agent-network→rule-judge→消费验证
- 独立线：aistartup / banking（references 非阻塞）

## 风险
1. flowernet↔platform 双向需文档化层级语义
2. agent-network 依赖 banking（脱敏）——banking 停滞阻塞其工作
3. rule-judge 是 4 蓝图 consumers 依赖——落后拖累验证

## 建议
前置优先级：① blueprint-platform → ② flowernet-platform → ③ flowernet+erp → ④ agent-network+rule-judge → ⑤ 终端/独立线并行
