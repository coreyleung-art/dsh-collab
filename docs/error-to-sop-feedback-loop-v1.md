# 踩坑→SOP 更新闭环机制 v1.0（Error-to-SOP Feedback Loop）

> 2026-08-29 星桥-mac-mini-协调者 · 用户指示：凡是工作过程出现错误/遗漏，都更新一次类似的工作流 SOP，避免资源浪费
> 定位：元流程（meta-process）——把「踩坑 → 沉淀 → 更新 SOP」制度化，让每次错误都转化为可复用的流程资产
> 触发词：错误 / 遗漏 / 漏了 / 失败 / 崩溃 / 回滚 / 踩坑 / 失联 / 阻塞

## 一、为什么需要（本次触发实例）

2026-08-29 连续暴露三类问题，均因「错误未及时转化为 SOP」：
1. **node-bridge v1.3.2 沙箱漏测模式** → 首版只测带 token，空 token 模式生产心跳仍空 {}（MBP 升级还遇到 identity 路径崩溃）
2. **central-inbox 注入失联** → CLD 启动后插件更新未重启，两侧收不到注入消息，直到用户发现才排查
3. **i9 消息无人感知** → 备用通道未建立时，升级期消息静默丢失

**规律**：错误本身不可怕，可怕的是「同类错误重复发生」——因为没有 SOP 沉淀。

## 二、闭环流程（五步）

```
【触发】工作过程出现错误/遗漏/失败
   ↓
【1. 记录】立即记黑板 data/pitfalls/<id>（结构：id/日期/现象/根因/影响/修复/教训）
   ↓
【2. 归档】落盘 docs/pitfalls/YYYY-MM-DD-<slug>.md（模板见下）
   ↓
【3. 更新 SOP】判断：是否有对应工作流 SOP？
   ├─ 有 → 在 SOP 增补「已知坑」章节（本次错误 + 预防检查项）
   └─ 无 → 新建 SOP（触发词→流程→验证→已知坑）
   ↓
【4. 验证】SOP 更新后，跑一遍「验证清单」确认防坑有效（沙箱先行）
   ↓
【5. 同步】推 GitHub + 端侧同步 + 落链知识库（ops-science-research）
```

## 三、踩坑档案模板（docs/pitfalls/）

```markdown
# <日期> <现象一句话>

> 记录人: <角色> · 状态: closed/active

## 现象
（发生了什么，用户/端侧观察到什么）

## 根因
（为什么发生——定位到代码/配置/流程层面）

## 影响
（谁受影响：哪端/哪个功能/多少资源浪费）

## 修复
（怎么解决的，改动哪些文件）

## 教训（→ SOP 更新点）
（一句话规律 + 应更新的 SOP 名称）

## 预防检查项
（SOP 更新后，下次执行前应检查什么）
```

## 四、SOP 增补格式（在既有 SOP 追加「已知坑」章节）

```markdown
## 已知坑（踩坑档案联动）

| 坑 | 现象 | 预防 |
|----|------|------|
| 沙箱漏测模式 | 只测一种模式，另一种生产仍坏 | 沙箱验证必须覆盖所有运行模式 |
| 插件更新不重启 | CLD 启动后改插件文件，旧代码在跑 | 改插件后必须重启 CLD 验证 |
| 升级期无备用通道 | 消息静默丢失无人感知 | 升级前确认备用通道（bb-sub/central-wake）在线 |
```

## 五、插件化/工具化评估（R006 9 项对照）

| # | 标准项 | 方案 | 状态 |
|---|--------|------|------|
| 1 | dsh 插件形态 | dsh-plugin-pitfall-log（cordis 插件：pitfall_add/pitfall_query/pitfall_list 工具） | 待建 |
| 2 | TCC 检测 | 不涉及（无 macOS 权限） | N/A |
| 3 | CLD 自适应 | adapt.js 基线跟随宿主版本 | 待建 |
| 4 | dsh 版本自适应 | 版本指纹 + probeCapabilities | 待建 |
| 5 | 文档化 | README + 工具注释 + SOP 模板 | 待建 |
| 6 | 版本管理 | git + tag + CHANGELOG + GitHub Release | 待建 |
| 7 | 日志管理 | appendFileSync 统一文件日志（~/.dsh/pitfall-log.log） | 待建 |
| 8 | 自动落链 | 黑板 data/pitfalls/ + docs/pitfalls/ + KB 向量化 | 待建 |
| 9 | CLI 治理 | pitfalls-cli.py（add/query/list/stats/export） | 待建 |

**评估结论**：可插件化（R006 9 项全部可落地），且与 i9 已有 pitfalls.json 31 条体系对齐（统一结构，两端互通）。建议纳入 dsh-plugin-health-check 或独立插件。

## 六、落地清单

- [ ] docs/pitfalls/ 目录 + 首批 3 条踩坑档案（v1.3.2 漏测 / central-inbox 失联 / 备用通道缺失）
- [ ] SOP 增补「已知坑」章节到相关文档（upgrade-standby-channel / restart-verify / 插件发布流程）
- [ ] pitfalls-cli.py 工具（add/query/list/stats/export，参考 i9 pitfall-archive.py）
- [ ] 插件化评估完成（R006 9 项）→ 用户批准后实施
- [ ] 触发机制固化：错误出现 → 自动进踩坑档案流程（本文档作为元流程引用）
