# 系统架构管理器 · UI 架构重构 v1(分组折叠导航 + 首屏总览)

> 作者: 明鉴 v2 · 2026-09-05 · 用户定案
> 背景: UI 架构评估发现 17 Tab 平铺无分组、无层级、首屏非入口; 用户选「分组折叠导航 + 首屏总览」
> 前置: JS 已独立 bb-gallery-ui.js(本轮全部改动在该文件, 跑 bb-gallery-gate.sh 门禁)

## 一、目标架构

```
顶部一级: [🏠总览] [🧠体系] [🗺图谱] [💻载体]        ← 4 域 Tab(一级)
              ↓ 展开
域内二级: 折叠标签(横向小 Tab 或下拉), 点开即该视图
```

| 域 | 含视图(原 17 Tab) |
|----|------------------|
| 🏠 总览 | dash 总览(导览卡+统计) · assets 图库 · versions 版本历史 · projects 项目导航 |
| 🧠 体系 | philosophy 治理哲学 · original 原创 · workflow 工作流/标准 · planarchive 计划档案 |
| 🗺 图谱 | blueprints 蓝图 · agents 智能体 · relations 关系 · rules 规则 · mech 机制 |
| 💻 载体 | knowledge 知识内核 · systems 系统资产 · hardware 硬件载体 · bizmap 跨节点资产 |

## 二、关键设计
- **首屏 = 总览域 dash**(默认打开)——用户见全景+导览卡, 而非直入哲学
- **深链兼容**: #dash/#blueprints/#agents-cap/#hardware-comm 等全部仍直达(自动展开所属域并激活二级)
- **视图切换状态**: 域内二级选中高亮; 折叠交互移动端可用
- **记忆**: 记住上次所在视图(可选, localStorage)

## 三、实现方式
- 全部改 `bb-gallery-ui.js` 的 DOM 结构 + `bb-blueprint-gallery.py` 的 Tab 条 HTML
- 用**二级 view 容器复用现有 view-xxx**(不改 render 函数, 只改导航壳)
- Tab 条: 一级 4 按钮 + 二级动态渲染(点一级显示该域二级)
- 验收: bb-gallery-gate.sh 全绿 + 截图/DOM 断言

## 四、验收
| # | 标准 |
|---|------|
| A1 | 首屏=总览域 dash(数据满) |
| A2 | 4 域切换正常, 域内二级可点开对应视图 |
| A3 | 旧深链全部兼容(#blueprints 展开🗺图谱并激活蓝图) |
| A4 | 手机端(≤768)折叠可用 |
| A5 | 门禁 bb-gallery-gate.sh 全绿 |
| A6 | 无 JS 错误(DOM 断言+像素) |

## 五、风险
- view-xxx div 的 display 切换逻辑(switchTab 靠 .main.on)需保留——二级切换仍走 switchTab, 一级只是导航壳
- 改动集中在导航壳, render 函数不动 → 风险低
