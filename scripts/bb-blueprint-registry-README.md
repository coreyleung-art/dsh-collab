# 蓝图库工具族 · registry + shell + GUI 关系图谱

> 明鉴 v2 · 2026-09-01 · blueprint-platform P2 工具化落地
> 三件套纪律：文档（本 README + 各蓝图 BP-9 md）/ 代码（3 工具）/ 依赖（relations 网络）

---

## 工具族全景

| 工具 | 功能 | R006 合规 |
|------|------|-----------|
| **bb-blueprint-create.py** | 蓝图正式化（黑板 BP-9 → 本地文档 + switch 声明） | ✅ CLI/TCC/版本/落链 |
| **bb-blueprint-registry.py** | 标准化蓝图库：盘点/list/relations/deps-tree/impact/refs/show | ✅ CLI/TCC/版本/落链 |
| **bb-blueprint-shell.py** | 交互式导航：REPL/引用解析(blueprint:<id>#<stage>)/关联跳转 | ✅ CLI/TCC/版本 |
| **bb-blueprint-ui2.py** | GUI 4 视图：流程图/鱼骨图(双鱼)/时间线/**关系图谱** | —（前端） |

## registry 用法

```bash
python3 bb-blueprint-registry.py --list                # 盘点 5 蓝图
python3 bb-blueprint-registry.py --relations           # 关系网络（9 边 6 类型）
python3 bb-blueprint-registry.py --relations --bp agent-network  # 单蓝图关系
python3 bb-blueprint-registry.py --deps-tree flowernet # 依赖树（含循环检测）
python3 bb-blueprint-registry.py --impact agent-network # 影响分析（变更→3 下游）
python3 bb-blueprint-registry.py --refs flowernet      # 反向引用（3 处）
python3 bb-blueprint-registry.py --show agent-network  # 单蓝图详情
```

## shell 用法

```bash
# 交互模式
python3 bb-blueprint-shell.py --bp flowernet
# 引用解析（蓝图间跳转定位）
python3 bb-blueprint-shell.py --resolve 'blueprint:flowernet#d3-3'
python3 bb-blueprint-shell.py --resolve '@blueprint:agent-network#an1-1'
# 导航
python3 bb-blueprint-shell.py --nav flowernet d3-3
# 交互命令: ls <bp> / go <bp> / stage <id> / refs / resolve <引用> / back
```

## GUI 关系图谱

- http://127.0.0.1:8797/ → 🔗 关系图谱视图
- 5 蓝图节点（业务/技术/底座/元层着色）+ 6 类型关系边（contains/depends_on/requires/consumes/manages/references）
- 配合缩放/平移/折叠（四视图共用）

## 关系网络（9 边）

```
flowernet-platform ⊃ flowernet（技术含业务）
flowernet →依赖 flowernet-platform
agent-network →要求 flowernet-platform
blueprint-platform →消费 agent-network
blueprint-platform →管理 flowernet / flowernet-platform / aistartup
flowernet ↔引用 aistartup（视觉模型/dogfooding）
```

## 验证记录（2026-09-01）

- registry：TCC PASS + list(5)/relations(9 边)/deps-tree(循环检测)/impact(3 下游)/refs(3 处) 全通
- shell：TCC PASS + resolve(blueprint:@ 语法)/nav 全通
- GUI：关系图谱 5 节点 + 边 + 按钮（4 视图全）
- 三工具 R006 合规（--tool-version/TCC/文档化/自动落链）

## 后续

- Rust 化评估：relations 查询高频 → dsh-tools 子命令（R029 范式）
- KB 集成：blueprints 单集合（星桥裁决①）语义检索跨蓝图关联
- 影响分析增强：门禁链传播可视化

---
*蓝图库工具族 v1.0 · 2026-09-01 · 明鉴 v2*

## 🔧 蓝图登记同步 SOP（v1.0 · 2026-09-07 新增 · 必修）

> 教训来源：2026-09-07 新增 flowernet-supply/citywar 后 SystemGraph 架构管理器不显示——
> 根因：蓝图登记只写了本地(relations.md/asset-map)，未同步**黑板数据源**（SystemGraph 从黑板读）。

### 新蓝图/蓝图更新登记的 4 步（缺一不可）

| # | 步骤 | 落点 | 验证 |
|---|------|------|------|
| 1 | **本地登记** | `data/blueprint/<id>/blueprint-*.md`（BP-9 元信息）+ 本地 `relations.md` + `gallery/business-asset-map.json` | grep 蓝图 id 三处存在 |
| 2 | **黑板 relations 清单** | PUT `黑板 /data/blueprint/relations` → `blueprints` 数组加 id + 关系边（纯 dict 不带包装） | GET 回读 blueprints 含 id |
| 3 | **黑板蓝图详情** | PUT `黑板 /data/blueprint/<id>` → **结构化 dict**（id/name/version/status/mainlines/gate/dim/stages——**不是 md 文本**） | GET 回读 value 是 dict 含 mainlines |
| 4 | **SystemGraph 生效** | `bb-blueprint-gallery.py` 硬编码表 `bp_dims()`/`bp_colors()` 补新蓝图 id（主源 + dist 双份同步）→ 重启 8798 服务 | `curl :8798/api/blueprints` 显示 dim/主线数 |

### 关键坑（勿再犯）

- ⚠️ 黑板 PUT 只能放**纯数据对象**——GET 返回含 key/ts/value/version 包装，PUT 时不可整体回写（会多套一层嵌套，服务端 fetch `.get("value")` 解析错位 → 清单变空）
- ⚠️ 服务端 `get_blueprint` 只认 **dict**（md 文本解析不出 mainlines → 蓝图显示为壳 dim=?/ml=0）
- ⚠️ 改主源 `~/dsh-collab/scripts/bb-blueprint-gallery.py` 后须同步 `dist/SystemGraph.app/.../gallery/` 同版文件
- ⚠️ bp_dims/bp_colors 是硬编码表（无自动发现），新蓝图必补

### 快速验证命令

```bash
curl -s http://127.0.0.1:8798/api/blueprints | python3 -c "import sys,json;[print(b['id'],b['dim'],len(b.get('mainlines',[]))) for b in json.load(sys.stdin)]"
curl -s http://127.0.0.1:8798/api/blueprint/<新蓝图id>   # 应返回 dict 含 mainlines
```

---
*README 更新 v1.1 · 2026-09-07 · 明鉴 v3 · 蓝图登记同步 SOP*

## 💻 编写入口 CLI（2026-09-07 新增 · 全部写操作命令行化）

> 用户要求：系统架构管理器的所有编写入口加 CLI 接口——不再手工 curl/黑板 PUT/改 JSON。

| 写入口 | CLI 命令 | 说明 |
|--------|---------|------|
| **蓝图登记三写** | `python3 bb-bp-register.py --register <蓝图id>` | 本地 md → 黑板详情(dict) + relations 清单 + 硬编码表检查 + SystemGraph 验证 |
| 蓝图登记+重启服务 | `... --register <id> --sync-sysgraph` | 登记后重启 8798 + 验证生效 |
| SystemGraph 验证 | `... --verify <蓝图id>` | 检查 dim/主线非空 |
| 硬编码表检查 | `... --dims-check <id>` / `--dims-all` | 查 bp_dims/bp_colors 覆盖 |
| **资产登记** | `python3 bb-asset-relations.py --add-asset "资产名" --bp <蓝图id> --atype asset --desc "..."` | asset-map assets 数组添加 |
| 资产列表 | `... --assets [蓝图id]` | 按蓝图查资产 |
| 资产关系 | `... --add "A" "B" depends_on "说明"` | relations 层（已存在） |
| **纠错条目** | `python3 speech-fix.py --add "规范名" --variants "变体1,变体2" --type org` | speech-fix-library 新增/更新条目 |
| 纠错条目列表 | `... --entries` | 列出现有 10 条 |

### 全部写 CLI 一览

```bash
# 蓝图登记（最重要——本次教训的直接解药）
python3 bb-bp-register.py --register flowernet-xxx
python3 bb-bp-register.py --register flowernet-xxx --sync-sysgraph   # 含重启8798

# 资产与纠错
python3 bb-asset-relations.py --add-asset "资产" --bp flowernet-xxx --desc "..."
python3 speech-fix.py --add "实体名" --variants "错写1,错写2"

# 查询/验证
python3 bb-bp-register.py --verify <id> · --dims-all · --list
python3 bb-asset-relations.py --assets · --list
python3 speech-fix.py --entries
```

---
*README 更新 v1.2 · 2026-09-07 · 明鉴 v3 · 编写入口 CLI*

## 🎯 里程碑通报工具（2026-09-09 新增）

> 用户指示：主动识别里程碑和蓝图意义，按 R006 十项标准工具化，每次自动通报媒体。

| 功能 | 命令 |
|------|------|
| 里程碑识别 | `python3 bb-milestone-report.py --scan <hours>` — 扫黑板 notes/collab/ → 里程碑判定(登记/验收/打通/规则生效/修复/定稿) |
| 蓝图意义映射 | 内置语义词典(中文→蓝图id) + SystemGraph registry 查询 → 命中蓝图(维度) |
| 媒体通报 | `... --scan 3 --notify` — 新里程碑写 media/inbox/ + 黑板 notes/media/(媒体专员 54e809ed 摄取) |
| 已通报列表 | `... --list` |
| 自检 | `--selfcheck`(TCC) · `--lean4-check`(约束门: 无notify不写媒体/ack不误报) · `--tool-version` |

**约定（明鉴每次迭代完成后执行）**：
1. 里程碑达成(验收/生效/登记/打通/修复/定稿) → `bb-milestone-report.py --scan 6 --notify` 自动通报媒体
2. 时间窗口门控(黑板 ts 过滤) + 幂等(已通报跳过) → 媒体只收"本次新"的
3. R006 十项: CLI/TCC/版本/文档/落链/Lean4门 全达标

---
*README 更新 v1.3 · 2026-09-09 · 里程碑通报工具*
