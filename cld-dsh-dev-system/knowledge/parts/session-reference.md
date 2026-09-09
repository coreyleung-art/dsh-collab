# 部件卡 · dsh-session-reference（文件/跨会话引用）

> 填卡：2026-09-05 · 依据：官方 subsystems/session-reference.md + ui-reference 恢复实证
> 状态：learned（registry: session-reference）

## 1. 一句话定位
Host-backed **文件发现 + 结构化跨会话引用请求 + prepared message 上下文**：file-reference 契约(path-only 补全/grammar) + session-reference 契约(canonical URI/current-surface 投影/tag-safe JSON与byte保留/稳定错误/不受信模型 prompt)。Host adapters 用这些类型而非把 UI mention 语法传进 agent core。

## 2. 概念与定义
- **FileReferenceCandidate**：{path, kind:'file'|'directory'}——path-only 发现结果；addressed agent 供 working-directory scope；providers 定排名/命名空间访问**不读文件内容**；dir 保持补全打开。
- **SessionReferenceInput**：{sessionId(权威), label?(展示元数据带进 snapshot)}。
- **SessionReferenceCandidate**：host-facing 发现输出；label 用最新 session title；filter 搜 label+sessionId+cwd，**绝不搜 transcript 文本**。
- **Services**：ctx.fileReferences(FileReferenceService seam) / ctx.sessionFileReferences / ctx.sessionReferenceResolver。

## 3. 作用与生命周期
UI(ui-reference) mention @文件/@会话 → remote.fileReferences.list / remote.sessionReferenceResolver.candidates（client.js 实证）→ host 服务按 cwd/元数据给候选 → 选中 → prepared message context 注入。**ui-reference client 依赖这两个 remote——host 服务健康是前提**（27 遮蔽时 host 服务旧版异常 → boot pending → 曾禁用 ui-reference；遮蔽清零 + 恢复后正常，2026-09-05 实证）。

## 4. 约束（红线/不可违）
- remote.fileReferences/sessionReferenceResolver 缺失/异常 → 依赖 UI(ui-reference) boot pending——**根治=host 服务健康，禁用是治标**。
- candidates 过滤不搜 transcript（只 label/id/cwd）——搜不到内容不奇怪。
- path-only 发现不读文件内容（安全边界）。

## 5. 依赖
- ctx.fileReferences 依赖 addressed agent 的 cwd scope；被 ui-reference 等 client 经 remote 消费。

## 6. 规范要点（标准）
- ui-reference 出问题先查 host file-reference/session-reference 服务（遮蔽/健康），再查 UI 层。
- 恢复被禁插件走门锁：条件(runtime在位/遮蔽清零)→备份→沙箱→gate→重启→guard-eye 验证（实证流程）。

## 7. 关联
- 官方文档：session-reference.md · 工具箱：T5(禁插件boot) · 路由：OP-disable-plugin
- 代码：dsh-file-reference{,-local}/dsh-session-reference/dsh-client-ui-reference
- 知识：plugin-loader(遮蔽=host旧版)/web-client(remote数据链) 卡

## 8. 待补
- file-reference-local vs remote 提供者边界(local fs vs 跨机)。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业——补全 ui-reference 恢复决策的理论依据(它依赖什么/为何曾 pending/恢复条件)。
