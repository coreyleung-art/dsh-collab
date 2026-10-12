# 2026-08-29-apply-phase-crash apply phase crash

> 级别: P1 · 日期: 2026-08-29

## 现象
CLD 重启后 dsh exit 1，web profile 全停摆

## 根因
central-inbox v0.1.6 引入 startAdaptGuard 调用但未导入（agent-way 私有函数）→ apply 阶段 ReferenceError

## 修复
MBP 删非法调用（git ac8e2f3）+ restart-guard ⑪ 加 apply(fakeCtx) 测试

## 教训（→ SOP 更新点）
模块能加载 ≠ apply 能执行；插件验证必须执行 apply 阶段

## SOP 更新
restart-guard-sop.md ⑪增强（import+apply 双阶段实测）
