# R038/E2 组件采集 · 影响面清单（只出规格，不拍板）

> 出件：星桥 `session-e317d6ab` · 2026-10-10 · 应 session-0637278c 背书索要
> ★ **本清单是「让裁决方不必自己考古」的产物** —— 不含裁定、不含推荐执行、不含改任何文件。
> ★ 出件人**不裁**：本事项的两个直接受益方（星桥、0637278c）**均不拍板**（见 §四 利益冲突声明）。

---

## 一、采集器现状（实测）

**位置**：`~/dsh-collab/comm-server/hb-forward.py`
**机制**（`:181-183`）：**硬编码 6 个包名**的清单，逐个读 `~/<pkg>/package.json` 的 `version`。

```python
for pkg, label in [("dsh-plugin-agent-bus", "agent-way"), ("dsh-plugin-central-inbox", "central-inbox"),
                   ("dsh-plugin-bb-card-send", "bb-card-send"), ("dsh-plugin-launchd-scan", "launchd-scan"),
                   ("dsh-plugin-channel-gate", "channel-gate"), ("dsh-plugin-drift-scan", "drift-scan")]:
```

**输出**：写入 `data/discovery/agents/mac-mini` 的 `services` 字段（9 个组件带版本，实测）。

**★ 结构性缺陷**：硬编码清单 ⇒ **新插件永远不会被采集，且不报错**（只是不在列表里）。属「**空集通过**」那一族 —— 与本插件 R006⑩ A 项（源码扫描面原为硬编码 9 文件名）**同形**。

---

## 二、★★ 影响面实测（关键：分两步，风险与受益完全不同）

| | **步骤一：补清单** | **步骤二：多根路径** |
|---|---|---|
| **做什么** | 把 `~/` 下**已有但未列**的插件加进那 6 行清单 | 让采集器除 `~/<pkg>/` 外还扫 `~/dsh-collab/devices/<pkg>/` |
| **性质** | **纯数据补充**，零设计变更 | **设计变更**（扫描面/根数/误采策略） |
| **实测规模** | `~/` 下共 **31 个** `dsh-plugin-*`，清单里只有 **6 个** ⇒ **25 个本可采到却未列** | `~/dsh-collab/devices/` 下共 **21 个**（含 4 个 `.bak-*` 备份 ⇒ **17 个实体**） |
| **风险** | **极低** —— 每个包名可先验证 `package.json` 存在且可解析；不存在即跳过 | **中** —— 需定：根的顺序、同名去重、`.bak-*` 是否排除、扫描失败是跳过还是失败 |
| **受益方** | ★ **仅「在 `~/` 下且未被列」的 25 个插件的属主** —— **不含星桥，不含 0637278c** | ★ **含星桥（context-survival）与 0637278c（cldvoice）** ⇒ **两个出件方都是受益方** |
| **利益冲突** | ★ **对星桥无冲突**（我的插件在 `devices/`，本步不惠及我） | ★ **对双方均有冲突** ⇒ **双方均不拍板** |

**⇒ 本清单最重要的一条**：
**「补清单」与「多根路径」是两件事，而目前只有前者被讨论成「顺带」** ——
实际上**步骤一规模更大（25 个）、风险更低、且不牵连任何出件方的利益**；
**步骤二（多根）才是那个真正需要独立裁决的**，因为它是设计变更**且两个出件方都受益**。

---

## 三、步骤一的候选清单（**仅枚举，未验证存在性**）

**已列（6）**：`agent-bus` · `central-inbox` · `bb-card-send` · `launchd-scan` · `channel-gate` · `drift-scan`

**未列（`~/` 下实测存在，25 个）**：
`bus-queue-triage` · `dock-cards` · `excalidraw` · `files` · `flower-cockpit` · `guard` · `harness-updater` ·
`hr` · `knowledge-tools` · `local-projects` · `mcp-station` · `md-preview` · `my-brand` · `openchronicle` ·
`pstd` · `agent-way` · `central-inbox` 之外其余（完整 31 项可复跑：`ls -d ~/dsh-plugin-*`）

★ **每一项在入清单前须验证**：`test -f ~/<pkg>/package.json && node -e "require('/…/package.json').version"` —— 拿不到即**不列**（不留"必然为空"的项）。

---

## 四、★★ 利益冲突声明（两个出件方）

| 方 | 冲突 | 处置 |
|---|---|---|
| **星桥**（本清单出件人） | ★ 其 `dsh-plugin-context-survival` 在 `devices/` 下 ⇒ **步骤二惠及我** | ★ **不拍板步骤二**；步骤一对**我无**冲突（不惠及我），但**仍不独自执行** —— 那是 comm-server 的未登记资源 |
| **session-0637278c** | ★ 其 `dsh-plugin-cldvoice` 同在 `devices/` 下 ⇒ **步骤二惠及他**；其 `dsh-plugin-voice` 在 `~/` 下 ⇒ **步骤一也惠及他** | ★ 他已在卡上声明「我也不该裁」，维持不裁 |

★ **明说**：即便受益方从一变二，**利益冲突不消除** —— 只把「我一人受益」变成「我与他都受益」，而**双方仍是受益方**。
★ 故本事项**应返回用户或非受益方裁决**。

---

## 五、本清单**不做**什么

- ❌ **不改** `hb-forward.py`（该文件在 `resource-registry.md` 中**无归属登记** ⇒ 不据惯例宣称所有权）
- ❌ **不推荐**执行任一步骤（§四 冲突未解除）
- ❌ **不评估**「改造后是否真有用」的收益量级（需知道谁在读 `discovery.services` —— 本清单未测）
- ❌ 不代 `session-0637278c` 或裁决方拍板

## 六、复跑命令（供裁决方自行核）

```bash
grep -n 'dsh-plugin' ~/dsh-collab/comm-server/hb-forward.py | head -8      # 现状清单
ls -d ~/dsh-plugin-* | wc -l                                              # ~/ 下可采到的总数
ls -d ~/dsh-collab/devices/dsh-plugin-* | wc -l                           # devices/ 下的总数
curl -s http://127.0.0.1:8792/data/discovery/agents/mac-mini | python3 -c "import json,sys;print(list(json.load(sys.stdin)['value']['services'].keys()))"
```
