# bb-blueprint2.py — 蓝图升级工具 v2

> 明鉴 v2 蓝图主编流程工具化 · 2026-08-30 · 用户指示：把蓝图升级过程插件化工具化
> 位置：`~/dsh-collab/scripts/bb-blueprint2.py`（与 bb-blueprint.py 并列，v2 扩展）

---

## 沉淀的流程（6 步全工具化）

| 步骤 | 命令 | 落点 |
|------|------|------|
| ① 变更记录 | `--refine "摘要" --stages d25-3,d3-3` | 黑板 `data/blueprint/changelog/<ts>` |
| ② 广播公告 | `--broadcast "标题"` | 黑板 `notes/collab/blueprint-change-<ts>` |
| ③ 定向提醒 | `--notify`（生成 agent_send 文案模板） | 星舵/老登/知了/守灯 |
| ④ Master 汇总 | `--master <路径>` | 本地单文件（stages+works+排期） |
| ⑤ 门禁检查 | `--gate` | 控制台（门禁链现状） |
| ⑥ 一键全流程 | `--full "摘要" --stages d25-3 --out /path` | ①②③④ 一次执行 |

## 用法

```bash
# 蓝图树（复用 bb-blueprint.py）
python3 bb-blueprint.py --list

# 单步
python3 bb-blueprint2.py --refine "变更摘要" --stages d25-3,d3-3 --version v2.3
python3 bb-blueprint2.py --broadcast "【蓝图变更公告】v2.3"
python3 bb-blueprint2.py --notify
python3 bb-blueprint2.py --master ~/dsh-collab/data/blueprint/flowernet/blueprint-master.md
python3 bb-blueprint2.py --gate

# 一键全流程（推荐日常用）
python3 bb-blueprint2.py --full "v2.3 细化：..." --stages d25-3,d4-1 --out ~/dsh-collab/data/blueprint/flowernet/blueprint-master.md
```

## 设计要点

- **R003 规范**：黑板 PUT body = 纯内容对象（不嵌套 `{"value":...}`），已实测可读
- **URL 拼接修正**：`_url()` 自动补前导斜杠（`BB + path` 缺 `/` 会 404）
- **幂等**：changelog/broadcast 以时间戳命名，重复执行不覆盖
- **与 v1 关系**：bb-blueprint.py 负责登记/更新工作 + 状态；bb-blueprint2.py 负责升级流程（变更同步+汇总+门禁）——互补不冲突

## 验证记录（2026-08-30）

- `--gate` ✅ 读到 3 条门禁 + 7 子阶段推进中
- `--master` ✅ 生成 120 行汇总文件（BP-9 元信息+子阶段表+works+排期）
- `--refine` ✅ 黑板 changelog 写入正确（R003 纯内容）
- `--broadcast` ✅ 黑板公告写入正确
- 测试数据：changelog/20260830-222634 + blueprint-change-20260830-222634（工具化验证用，可保留为样例）

## 后续（可选）

- 注册为 DSH 插件工具（cordis 工具面，blueprint-dialog/create/refine 三工具排期中）
- 与 bb-blueprint-ui.py（8797 GUI）联动：升级后自动刷新看板
- 定时门禁巡检（gate 检查每日自动跑，告警不达标）

---
*bb-blueprint2 v1.0 · 2026-08-30 · 明鉴 v2*
