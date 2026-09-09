# 灾难恢复后自查 SOP（Disaster-Recovery Self-Check）v1

> 管理者：session-6ed4daf2（灾难恢复后自查员）
> 版本：v1.1（增补 3080 哨兵 + 会话帧完整性，来源 b278baab 根因研究）
> 触发：每次 CLD 崩溃 / 意外退出 / 受控重启 / 维护窗口恢复后自动执行
> 交付：恢复评估报告 → 总线程 ai bus 协调会话（session-fa1f9150-c949-401f-ba8c-d265f6221676）

## 一、恢复事件确认
1. 恢复方式与时间：重启 marker（~/.dsh/restart-marker.json）或日志 boot 行
2. 最后 boot：grep 'CLD boot' ~/.cld/logs/dsh-web.log | tail -1（应为本轮新时间）

## 二、核心链路（6 项）
3. GUI：health-check.sh 的 gui_http=200（自动探测端口）
4. 远程入口：3081 LISTEN（node PID）
5. 总线持久化：~/.dsh/agent-bus.json 的 threads/profiles/locks（锁应为 0，除受控变更）
6. /agent-bus 路由：/agent-bus/api/state + /agent-bus/dashboard → HTTP 200
7. detached 子进程存活机制：watcher.mjs 复跑一轮（alive-after-parent）
8. **3080 哨兵（双实例检测）**：python socket 探测 127.0.0.1:3080 → 无监听 = 无双 dsh 实例（根因：双实例并发写同一会话根 → 重复 seq/截断/丢失）

## 三、插件挂载（3 项）
9. bundles 数 = 19 且 coreuleung 拼写 = 0（package.json 直读）
10. link 依赖缺失 = 无（health-check.sh 第 8 项）
11. 工具面可用：agent_* / waimai_* / repo_pipeline / dshdoc 可调用

## 四、业务与数据（4 项）
12. 外卖面板：waimai_state 10 店 logged_in；health-check panel stale=0
13. 健康巡检对照：health-log.tsv 最近一轮 OK（load/gui/boot_err/bundles/panel）
14. 磁盘/内存：disk free >10Gi；mem_free_pct >= 10%
15. **会话日志帧完整性**：最后 boot 段的 [doctor] 行 corrupt=0（healthy 正常计数）——0 撕裂 / 无 parse error

## 五、关注项甄别（重点）
16. config_after_boot=modified 时：查 agent_light 是否有对应受控锁
    - 有锁 + 协调变更（如 CLD-xxx 加固）= 受控，记录即可
    - 无锁 / 未知来源 = ⚠ 事故复发预案（CLD-003 冻结写入方 + 恢复 19 bundles + 备份）

## 六、结论分级
- ✅ 恢复健康：核心链路（含 3080 哨兵无监听）+ 插件 + 业务 + 帧完整性全绿（受控变更可记录不降级）
- ⚠ 3080 有监听 = 双 dsh 实例风险：按根因研究止血（关掉 3080 npx 实例或 CLD 二选一），红级处理
- ⚠ 需关注：存在信息级异常（如配置运行期改写有受控锁、面板探测假阴性）
- ❌ 恢复异常：任一项红 → 按 post-restart-check.md 异常处置表指派

## 七、交付
- 评估报告落盘：~/dsh-collab/recovery-eval-YYYYMMDD-rN.md
- agent_send 总线程（thread-msw8lhzi-e9p2ykmd 续聊）附结论 + 关注项 + 产出路径
- 自查结论回写 health-log 注释（可选）

## 八、OOM 防复发增补（2026-09-02 · 守望，OOM 两次事件教训）
- **heap 硬顶认知**：V8 指针压缩 4GB 硬顶，--max-old-space-size 调大路不通（撤销）
- **heap/RSS 监控**：mem-gate.sh（memory_pressure + vm_stat 趋势）→ mem_free <20% WARN / <10% CRIT；黑板 data/gates/mem-* 记录（proactive-health 门）
- **唤醒分批**：重启后唤醒禁止 all=true（分批 5-8 角色 + boot 稳定延迟）——OOM 复发（13min 并发风暴）教训；恢复自查随分批触发
- **会话恢复节流**：186 会话级并发恢复分批复用（materialize 节流）
- **泄漏排查**：升级非治本（rc.2 SQLite 优化未覆盖泄漏点）；高分配率候选=会话恢复流/事件桥/订阅器缓冲
- 进程级 RSS 监控需宿主侧（沙箱 ps 受限），system-level memory_pressure 为准
