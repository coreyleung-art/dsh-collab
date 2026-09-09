# 迭代需求 · SystemGraph 壳层「通道门 + 离线缓存 + 自动对齐」 v1

> 作者: 明鉴 v2 · 2026-09-03 · 状态: 规划(用户定案方案)
> 问题: 架构管理器外部访问依赖 mac-mini 本机(Funnel 单点); 服务宕/无网时打不开; CloudBase 静态版是旧快照
> 目标: 三级通道门自动选择 + 本地缓存离线可用 + 周期自动拉最新对齐

## 一、架构(用户定案: 三级通道门 + CloudBase 自动镜像; 双层缓存都做)

```
┌─────────────────────────────────────────────────┐
│  壳层通道门(每端: Electron mac 壳 / iOS App)      │
│  ┌─① Funnel 动态 ──→ 实时(18 Tab 全交互)         │
│  ├─② CloudBase ────→ 自动镜像(近实时静态快照)     │
│  └─③ 本地缓存 ─────→ 离线(最近一次数据)           │
│  探测健康: Funnel API→CloudBase 静态→本地 fallback │
└─────────────────────────────────────────────────┘
        ↓ 页面数据层(双层缓存都做)
┌─────────────────────────────────────────────────┐
│  j() 改造: 先读本地缓存显示 → 后台拉最新 → 更新重渲  │
│  缓存: IndexedDB/localStorage(页面层)             │
│       + 壳层落盘(每端存最近一次完整 JSON)          │
│  Service Worker: 静态资源离线可开(可选)            │
└─────────────────────────────────────────────────┘
```

## 二、数据流与对齐
- **CloudBase 自动镜像**: mac-mini 数据变更(gallery 数据 JSON/蓝图/计划档案)→ 触发导出静态快照 → 交 MBP 域 CloudBase MCP 推送(~/.cloudbase-mcp)→ tm.meetfunbp.com/systemgraph/ 更新
  - 本机无 tcb CLI/脚本 → 镜像通道 = 经星桥/MBP(其 ~/.cloudbase-mcp)
  - 每次发布/数据变更后同步一次(非每 Tab 实时, 控制成本)
- **页面数据层离线优先**: 前端 j() 读缓存 → 渲染 → 后台 fetch(经通道门选的基址)→ 有新版更新缓存+重渲
- **对齐频率**: 打开即拉 + 周期 60s 静默探测(有变更才更新)

## 三、改造点
| 层 | 改什么 | owner |
|----|--------|-------|
| gallery 前端 j() | 读缓存优先 → 后台拉 → 写缓存 → 重渲; API 基址由通道门注入 | 明鉴 |
| gallery --export | 数据快照导出(全 API→JSON), 供 CloudBase 镜像 | 明鉴 |
| Electron 壳 | 通道门: Funnel→CloudBase→本地; 本地缓存目录(userData) | 明鉴 |
| iOS 壳 | URL fallback 已有(加 CloudBase 中位); WKWebView 缓存策略已有 | 明鉴 |
| CloudBase 镜像 | 自动推送(数据变更→MBP 推)→ 经星桥/MBP 域 | 星桥/MBP |
| 看门狗 | mac-mini 服务自动恢复(launchd LaunchAgent KeepAlive) | 明鉴 |

## 四、验收
| # | 标准 |
|---|------|
| A1 | mac-mini 宕 → 壳自动切 CloudBase(页面可开, 数据近实时) |
| A2 | mac-mini+CloudBase 都不可达 → 壳用本地缓存离线展示(有"最后更新"提示) |
| A3 | 打开先显缓存(秒开) → 后台拉到新版自动更新 + 显示数据版本 |
| A4 | CloudBase 镜像与 Funnel 数据源一致(每次变更后对齐) |
| A5 | 页面数据层: 刷新/重开保留缓存(免每次全拉) |
| A6 | 看门狗: mac-mini 重启后 SystemGraph 服务自动恢复 |

## 五、里程碑
- M1 gallery 数据快照导出(--export)+ 页面 j() 缓存层(本机离线优先) 
- M2 CloudBase 镜像管线(星桥/MBP 协作: 数据变更→推 CloudBase)
- M3 壳层通道门(三端: Electron/iOS/网页注入基址)
- M4 看门狗(launchd KeepAlive) + 全链路验证

## 六、风险与取舍
- CloudBase 为静态版: 交互(通讯桥探测/实时刷新)降级为只读, 展示足够; 动态功能标"在线模式可用"
- 本地缓存一致性: 缓存带数据版本+时间戳, 拉新比对 version bump
- 成本: CloudBase 推送非高频(变更驱动); 壳探测 60s 一次成本可忽略
- R031: CloudBase 部署属 MBP 域(有 ~/.cloudbase-mcp) → 分工推送, 明鉴不代理
