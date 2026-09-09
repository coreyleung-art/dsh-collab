# 恢复评估报告 R2（2026-08-18 崩溃修复后）

> 自查员：session-6ed4daf2 · 依据 SOP：~/dsh-collab/disaster-recovery-selfcheck.md v1.1
> 触发：6 插件连环出错崩溃 → 用户执行修复（5 修 3 移出）→ 协调者委派标准自查

## 恢复事件
- 根因：批量装 6 未验证插件连环出错（async apply / schema required 滥用 / CJS 冲突 / 缺构建 / Config 非 schema）
- 修复：hr/gov/bus-bridge 已修加载；gate/office/flower-cockpit 移出待复验
- 最后 boot：2026-08-18T02:56:06Z · 启动后错误 = 0 · GUI 58139 HTTP 200

## 自查结果（SOP v1.1）

| 维度 | 项 | 结果 | 证据 |
|------|----|------|------|
| 核心链路 | GUI | ✅ 200 | 127.0.0.1:58139 |
| 核心链路 | 3080 哨兵 | ✅ 无监听 | 无双 dsh 实例 |
| 核心链路 | 3081 | ✅ LISTEN | 100.120.203.20:3081 PID 57718 |
| 核心链路 | detached 存活 | ✅ 5/5 轮 | stress.mjs 复跑 |
| 核心链路 | 服务端口 | ✅ | 8787 面板 / 8910 MCP / 8091 论坛(Tailscale) |
| 插件挂载 | bundles | ✅ 26 基线 | gov/read-url/openpencil/ui-spec/external-link-policy/bus-bridge/hr 在列；gate/flower-cockpit/office 移出 |
| 插件挂载 | R3 路由 | ✅ 200 | /external-link-policy/stats（补挂载闭环） |
| 业务数据 | 外卖面板 | ✅ 10 店 logged_in | waimai_state + 8787 LISTEN |
| 业务数据 | 帧完整性 | ✅ corrupt=0 | doctor healthy=116 fixed=0 |
| 总线 | 持久化 | ✅ 411 线程 / 45 档案 | 运行时 0 锁（文件统计 1 为持久化滞后） |
| 资源 | 磁盘/内存 | ✅ 15Gi free / mem 35% | 均达标 |

## 关注项
- ❌ **gov 工具 schema 缺陷**：已加载（26 bundles）但工具调用报 value.data.* 未声明（additionalProperties:false）——转供应链/QA 修复；建议工具调用级验证纳入冒烟（四段探测抓不到此类）
- ⚠️ bus.status 原生工具面：归属 e0c391f7 会话验证（本会话仅见 external-link MCP 侧）

## 结论
**✅ 恢复健康** —— 崩溃修复后 26 bundles 基线运行正常，核心链路/业务/帧完整全绿；遗留 gov 工具结构缺陷与 bus-mcp 工具面归属验证两项跟踪。

## 遗留
- gov 工具 schema 修复后复验（工具调用级）
- gate/office/flower-cockpit 重新验证后恢复入列（供应链/QA 跟踪）
- bus.status 原生工具冒烟（e0c391f7）
