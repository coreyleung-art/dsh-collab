# 2026-08-29 central-inbox apply 阶段崩溃（模块加载≠apply 执行）

> 记录人: 星桥-mac-mini-协调者 · 状态: closed（MBP 修复 + restart-guard 盲区补上）

## 现象
- CLD 重启后 dsh exit 1 崩溃，web profile 全部插件停摆
- 根因：central-inbox lib/index.js:32 调用 startAdaptGuard(ctx,"central-inbox")，该函数是 agent-way 内部 adapt.js 私有函数未导出，central-inbox 未导入 → apply 阶段 ReferenceError → profile boot 中止

## 根因（两层）
1. 代码层：v0.1.6 引入 startAdaptGuard 调用但未导入（我引入的 bug）
2. 检测层：restart-guard 模块加载实测只 import() 不执行 apply()——崩溃发生在 apply 阶段时检测不到（盲区）

## 影响
- CLD 无法启动（P1），MBP 远程修复恢复（git ac8e2f3 删非法调用）

## 修复
- MBP：删除 startAdaptGuard 调用行（备份 index.js.bak-startadaptguard）
- restart-guard：⑪ 增强为 import + apply(fakeCtx) 执行测试 + 3s 超时

## 教训（→ SOP 更新点）
**模块能加载 ≠ apply 能执行**——插件验证必须执行 apply 阶段（用 fakeCtx 模拟 cordis 上下文）

## 预防检查项
- [ ] restart-guard ⑪ 必须包含 apply(fakeCtx) 执行（已实现）
- [ ] 新增插件/改插件后：跑 restart-guard 确认 APPLY_OK
- [ ] 引用其他插件内部函数前确认已导出/已导入
