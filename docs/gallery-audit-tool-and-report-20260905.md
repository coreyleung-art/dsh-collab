# 系统架构管理器 · 结构审查工具 + 2026-09-05 审查报告

> 作者: 明鉴 v2 · 2026-09-05 · R006 九标准合规
> 触发: 用户发现「蓝图库 vs 蓝图详情」父子重复臃肿 → 要求全面审查架构管理器并工具化

## 一、审查工具 bb-gallery-audit.py(R006 合规)

| R006 标准 | 合规实现 |
|-----------|---------|
| ① dsh 插件形态 | 独立脚本 bb-gallery-audit.py(可入 dsh-tools 或 gallery 子命令) |
| ② TCC 自检 | `--selfcheck`: 有 error 则 exit 1 |
| ③ CLD 自适应 | 纯文件扫描, 不依赖运行服务/黑板(静态审查) |
| ④ dsh 版本自适应 | `--tool-version` → v1.0.0 |
| ⑤ 文档化 | 本文档 |
| ⑥ 版本管理 | 纳入 ~/system-graph-app/VERSION-MANIFEST(工具版本随发布) |
| ⑦ 统一日志 | `--json` 输出供落链; 无运行日志(纯扫描) |
| ⑧ 自动落链 | `--json` 结果可写黑板 notes/ 或 plan-archive |
| ⑨ CLI 治理 | `--scan [FILE]` / `--selfcheck` / `--json` / `--tool-version` |

### 审查项(7 类)
| 检查 | 含义 |
|------|------|
| H1 Tab-View 映射 | 每 tab 有 view-div, 每 view 有 tab; 死 view |
| H2 深链/空态 | tab 无 switchTab 渲染分支(深链直达可能空) |
| H3 多写冲突 | 同 view 被多 render 写(重复/覆盖) |
| H5 死代码 | 定义了未调用的 render |
| H6 内容重复 | 蓝图可点卡片多处生成(父子视图重复的根因模式) |
| H7 初始化顺序 | 引用全局 ALL 但非 init 首屏的 render(深链空态风险) |

```bash
python3 ~/dsh-collab/scripts/bb-gallery-audit.py          # 审查(默认当前源码)
python3 ~/dsh-collab/scripts/bb-gallery-audit.py --selfcheck
python3 ~/dsh-collab/scripts/bb-gallery-audit.py --json   # 落链用
```

## 二、2026-09-05 审查结论(触发案例)

### 发现并已修复
| # | 问题 | 修复 |
|---|------|------|
| P1 | **📐蓝图库 ↔ 🔍蓝图详情** 父子重复(都渲染全蓝图卡片, 直接进详情空态) | 合并为「📐 蓝图(库+详情)」左右分栏: 左列表高亮 + 右详情(流程/鱼骨/时间线/动态); 删 blueprint-detail Tab + showBpGuide |
| P2 | **🗂项目视图** 按维度重复全部蓝图卡片(与📐蓝图重复) | 改为「维度导航入口」: 维度卡 → gotoBpDim 跳📐蓝图并打开该维度首蓝图 |
| P3 | renderProjects 无 ALL 数据防御(深链空态) | 加 `if(!ALL.blueprints...)return 空态` |

### 审查确认健康(无需改)
- 17 Tab = 17 View 全映射, 无死 view/tab
- switchTab 覆盖全部 tab 渲染入口
- 无多函数写同 view 冲突
- 集成后的 renderBlueprints 含 curBp 恢复, 深链安全

### 复发预防
- 每次新增 Tab/视图 → 跑 bb-gallery-audit.py, H1/H6/H7 防同类"父子重复/空态"
- 新增"全蓝图可点卡片"前先想: 是否已有入口(📐蓝图), 避免 H6
- 已纳入 sysgraph-version release 流程前检查项

## 三、遗留观察(非阻塞)
- H7 启发式对 init 首屏 render 已排除(顺序安全); 若未来 render 改异步/移出 init 需重审
- renderRelations 误报已通过 init 排除修正
