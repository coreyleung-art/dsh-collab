# 蓝图架构图管理器（Blueprint Graph Manager）· 设计 v0.1

> 明鉴 v2 · 2026-09-02 · 用户需求：适配全局的蓝图架构图管理器 app
> 已拍板：① 独立本地 Web app（127.0.0.1:8798）② 自动渲染版本快照供历史翻查

## 一、目标

一个本地 Web app，统一管理：
1. **所有蓝图**（11 份 BP-9，含子蓝图）的架构图
2. **所有智能体**（52 档案）的架构图与协作关系
3. **项目关联**（蓝图 → 项目/主线映射）
4. **版本管理**（每个蓝图的历史版本 + 每版本架构图快照翻查）

## 二、数据源

| 数据 | 来源 | 说明 |
|------|------|------|
| 蓝图 BP-9 | 黑板 `data/blueprint/<id>` | 11 蓝图全字段 |
| 关系网络 | 黑板 `data/blueprint/relations` | 11 蓝图 24 边（contains/depends_on/requires/...） |
| 版本日志 | 黑板 `data/blueprint/versionlog` | 16 entries + 各蓝图当前版本 |
| 智能体档案 | `~/.dsh/agent-bus.json` `profiles` | 52 个（role/abilities/resources） |
| 蓝图 JSON 快照 | `data/blueprint/snapshots/` | 既有 `--snapshot` 产物 |
| 架构图快照（新） | `data/blueprint/gallery/snapshots/` | 每版本渲染的 SVG 快照 |

## 三、页面结构（单页 app · 顶部 Tab）

1. **🏠 总览 Dashboard** — 统计卡（蓝图数/关系边/智能体数/快照数）+ 全局关系网络图（可点蓝图跳转）
2. **📐 蓝图库** — 左侧列表（11 蓝图卡片：版本/状态/主线数）→ 右侧详情：架构图（SVG 三主线泳道）+ 子阶段/works 表 + 关系边 + 版本历史（时间线 + 快照翻查）
3. **🤖 智能体网络** — 52 智能体网格（角色/设备/能力数/资源数）→ 点击弹详情；按设备/角色分组统计
4. **🔀 关系图谱** — 全蓝图关系网络（力导向/环形 SVG，边类型着色），可点节点
5. **🗂 项目视图** — 业务项目（flowernet/banking/aistartup/agent-network...）维度聚合：项目→蓝图→主线→进度
6. **📜 版本历史** — 全局版本日志时间线（全部蓝图 bump 记录），筛选蓝图 → 每版本对比（diff 摘要）+ 快照图翻查

## 四、后端（Python http.server，port 8798）

- `GET /` → 单页 HTML（内嵌全部视图 JS/CSS）
- `GET /api/overview` → 统计 + relations
- `GET /api/blueprints` → 11 蓝图列表（registry）
- `GET /api/blueprint/<id>` → 单蓝图全 BP-9
- `GET /api/agents` → 52 智能体档案
- `GET /api/versions` → versionlog 全部 + 过滤
- `GET /api/relations` → edges
- `GET /snapshots/<file>` → 架构图 SVG 快照静态服务

## 五、渲染管线（架构图 → SVG）

服务端把每个蓝图渲染为 **SVG 快照**（自绘，不依赖浏览器）：

- **蓝图架构图 SVG**：三泳道布局（mainlines 纵排 → stages 横排卡片 → 状态色），图例 + 门禁注记
- **关系网络 SVG**：环形/分层布局 + 着色边 + 可点击
- **智能体网络 SVG**：按资源相关性分组（暂用设备+角色分层）
- **版本快照**：每次蓝图版本变化（versionlog 新 entry）→ 自动渲染该蓝图架构图 SVG 存 `gallery/snapshots/<bp>-v<ver>-<ts>.svg`，历史翻查直接读文件

## 六、目录

```
~/dsh-collab/scripts/bb-blueprint-gallery.py   # app 主程序（服务+渲染+API）
~/dsh-collab/data/blueprint/gallery/snapshots/  # SVG 快照归档
~/dsh-collab/data/blueprint/gallery/version-map.json  # 蓝图→版本→快照文件映射
```

## 七、里程碑

- M1 骨架+数据 API 通（overview/blueprints/agents/versions）
- M2 蓝图架构图 SVG 渲染（三泳道）+ 蓝图库页
- M3 关系网络 SVG + 智能体网络页 + 项目视图
- M4 快照管线：版本 bump 自动渲染归档 + 版本历史页翻查
- M5 桌面图标/一键启动 + 联调验证

## 八、门禁

① 快照管线只在版本 bump（versionlog entry 新增）时渲染，不轮询 ② SVG 自绘零依赖（不依赖 mermaid CDN）③ 黑板数据读取失败降级为本地缓存/错误提示 ④ 端口 8798 若被占用自动 +1
