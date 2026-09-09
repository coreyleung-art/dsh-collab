# DSH/CLD 修复规范 · Lean 4 逻辑版 · v2

> 建立：2026-09-04 · 升级：2026-09-04（v2 新增 P0 官方预查门）
> mbp-ops · 用定理证明器的纪律替代"自觉"
> 动机：用户批评"建立了规则却没锁住自己"——本文档把规则变成类型检查器：不满足前提的操作 = 编译错误，物理拒绝执行。
> v2 动机：多轮故障的共因是**凭旧认知修，没先核对官方最新行为**（NODE_OPTIONS 白名单、Electron fuse、pnpm overrides 语义）。修前必须查官方标准，且由机器强制。

---

## 〇、Lean 4 原则 → 运维公理映射

| Lean 4 概念 | 运维对应 | 强制手段 |
|---|---|---|
| 类型即命题（Prop as Type） | 每个操作有精确前提/后置，类型不符即拒 | 门锁脚本（guard-gate） |
| 全函数（total function） | 没有"可能成功也可能坏"的模糊操作 | 穷尽验证清单 |
| 穷尽模式匹配 | 验证无遗漏分支（不能只看 boot 过） | check-list 全项必过 |
| 构造性证明 | 不空口"应该没问题"，要实测证据 | 每步留证据（日志/输出） |
| 终止性检查 | 修复迭代有界：N 次不收敛必回滚 | fix-loop bound |
| unsafe 标记 | 未验证的快速修复必须标 unsafe + 补证 | 报告带 unsafe 字段 |
| 反例思维 | 先构造"什么会让它再坏"，再动手 | pre-mortem 检查 |
| **引用透明/先验前提** | **假设会过时——改前必须先查当前官方标准** | **guard-doc-check（P0 门）** |

---

## 一、核心定理：一次安全的修改

```
theorem safe_edit (target : Path) (change : Change) :
  requires official_verified target     -- 前提⓪ 已查最新官方标准(≤24h)
  ∧ backup_exists target               -- 前提① 已备份
  ∧ not (forbidden target)             -- 前提② 不在红线
  ∧ sandbox_verified change            -- 前提③ 沙箱验证过
  → produces (boot_ok ∧ sessions_ok ∧ history_ok)  -- 结论
```

**Lean 语义**：前提不满足 → 无法构造 `safe_edit` → 操作**不存在**（不是"警告"而是"类型错误"）。

### 门锁实现（guard-gate v2）
```bash
guard-doc-check "<主题>"               # P0 官方预查：查本地官方镜像(~tech-research) + 留证
guard-gate <target> <operation>        # 前提不满足直接 exit 1，禁止继续
```
等价于 Lean 的 `#check`——类型不对根本编译不过。P0 证据写入 gate-state.json，guard-gate 校验同领域 ≤24h 记录，无则拒。

---

## 二、六大前提（不满足 = 拒绝执行）

### P0 · official_verified（官方标准预查 —— v2 新增）
```
必须: 受限区操作前 24h 内跑过 guard-doc-check <主题>，且证据有效
      证据有效 = 同领域命中官方文档(本地镜像 ~/tech-research/) 或 --web 补官方来源
      镜像 >14 天未更新 → 必须 --web 补证（官方标准可能已变）
违反后果: 凭旧认知修 → 修错方向（例: NODE_OPTIONS 改堆上限已证明无效但仍有人想再试）
```
**Lean 形式**：`official_verified : target → Prop`——safe_edit 的第一个参数，**先于一切**。铁律："先查官方，再谈修"。诊断 >15 分钟无定论也必须停下来查。
**实证锚点**：Electron 打包后 `NODE_OPTIONS` 白名单只放行 2 项（官方 fuse 行为）→ 我们绕了 2 天才确认；pnpm overrides 会重写全家依赖 → 65 遮蔽包事故。这些都在官方文档里写着，查了就不会白绕。

### P1 · backup_exists（备份存在）
```
必须: guard backup <target> 成功，且备份文件可解析（非 0 字节）
违反后果: 无回滚点 —— pnpm 事故教训（当时没备份差点无法恢复）
```
**Lean 形式**：`backup_exists : target → Prop`，作为 safe_edit 第一个参数。

### P2 · not_forbidden（非红线）
```
必须: guard check-writable <target> exit 0
红线: Electron Framework / dsh-tools/lib / .pnpm / auto-index / 运行时 asar
违反后果: 直接崩壳/API 漂移（gov schema 教训）
```

### P3 · version_coherent（版本一致）
```
必须（依赖/包改动时）: guard version-check <pkg>
        profile 版本 == runtime 版本（rc.2），无遮蔽
违反后果: 遮蔽 → 连环崩（本次 65 遮蔽包基线）
```

### P4 · sandbox_verified（沙箱验证）
```
必须: 在 /tmp 副本打补丁 → 语法/解析通过 → 才落真
       至少: node --check / JSON.parse / YAML 可解析
违反后果: 语法错直接崩 boot（曾 ERR_MODULE_NOT_FOUND ×24）
```

### P5 · bounded（有界）
```
必须: 同一次故障修复 ≤ 3 次尝试；第 3 次仍不收敛 → 回滚到 .bak-good
违反后果: 无限试错 → 越修越乱（今天 pnpm 连环修 5 个错）
```
**Lean 形式**：递归有 termination 证明——`fix_attempts : Nat`，到界必须走回滚分支。

---

## 三、结论验证：穷尽检查清单（无遗漏分支）

每次修改后，**全部**通过才算 `safe_edit` 成立：

```
C1 boot_ok:     dump-config EXIT 0
C2 web_ok:      web HTTP 200
C3 data_ok:     doctor healthy == 基线（191）不降
C4 session_ok:  会话列表可见（非空）
C5 history_ok:  点会话 → 历史可加载（无 .parse/undefined 错）
C6 renderer_ok: --enable-logging 无新增 error（除已知 modlens 警告）
C7 version_ok:  guard-deps-scan 无新增遮蔽
```

**Lean 语义**：这是 match 的穷尽分支——任一分支失败 = 证明不完整 = 操作不算成功，必须回滚或补证。

---

## 四、高频问题工具箱（实证 playbook 导航）

**故障处置一律先查 T 编号，再套本规范**：
→ 文档：`docs/高频问题处理工具箱.md`（T1 会话空 / T2 OOM SIGABRT / T3 内存暴涨 / T4 插件报错 / T5 web 起不来 / T6 React 崩溃 / T7 连环错遮蔽 / T8 崩溃无痕 / T9 未知问题先查官方）
→ 路由：`guard-risk <操作|症状>` —— 机械查「做了什么→会坏成什么样(概率)」+ 症状处置路由

每条 T 都内置：判定命令 → 标准处置（含 P0 预查示例）→ C1-C7 验收 → 回滚点。
工具箱本身也受本规范约束：新增故障条目 = 新增 lemma，需带实证。

### 飞轮条款（v2.2 · 越修越好的闭环 · 2026-09-04）

**动机**：用户指出"越修越坏"源于同一坑反复踩、修完不沉淀。本条款把"新问题"变成**必走沉淀流程**的输入，让每次修复都回写知识库（正向飞轮）。

**遇到任何未归类问题（症状/报错不在路由表 symptoms 命中）→ 飞轮五步，禁止直接试修**：
```
① 归大类: 是 OP-* 哪个操作引起? 还是全新症状?
② 查路由: guard-risk <关键词> 确认无既有条目（新问题 exit 2 会强制提示）
③ 处置:   按工具箱最近邻条目处置（不完全匹配也用其通用处置 + C1-C7）
④ 验证:   C1-C7 全过才算完（否则回滚重证）
⑤ 沉淀:   更新 risk-router.json(新 operation/symptom + 概率) + 工具箱(新/更新 T)
          + 经验沉淀-日期.md + 报告留痕 —— 不沉淀 = 白修，下次重踩
⑥ 入库:   报告/沉淀自动进 repair-knowledge（send-repair-report.py 钩子已接入
          guard-recall ingest）——以后 guard-recall search "<症状>" 秒级复用经验
```
**修复前先检索历史**：任何问题动手前先 `guard-recall search "<症状关键词>" -k 3` ——若历史命中，直接复用上次处置，不再交第二次学费（效率铁律）。
**沉淀义务（定理形式）**：
```
theorem learn_from_fix (fix : Fix) (new_issue : Issue) :
  → record_new_route new_issue     -- 路由表新增/更新
  ∧ update_toolbox new_issue       -- 工具箱条目
  ∧ log_experience new_issue       -- 经验沉淀
  ∧ report_trace fix               -- 报告留痕
```
**反模式（违反 = 飞轮停转）**：不归大类直接试修 / 修好不沉淀 / 数据健康时动 session 文件 / 把重启当修复。

---

## 五、unsafe 标记（应急通道，带义务）

### unsafe 使用条件
仅当**服务宕机需立即恢复**（如 CLD 起不来）——可跳过 P0/P3/P4 快速修。

### unsafe 义务
```
每次 unsafe 操作必须:
  1. 报告带 "unsafe: true" + 原因
  2. 24h 内补做 P0/P3/P4（官方预查 + 版本核对 + 沙箱验证）
  3. 记入 risk log —— 未补证的 unsafe 视为未完成
```
**Lean 形式**：`unsafe` 是 axiom——可用但不可信，最终证明（safe_edit）不能依赖 axiom。
**v2 强化**：跳过 P0 的 unsafe 尤其要补——宕机恢复后第一件事就是查官方确认临时修法与官方一致。

---

## 六、反例思维（pre-mortem，动手前必答）

每次修改前，回答（写入操作记录）：
```
Q0 我对这个系统的理解基于哪份官方文档？它是最新的吗？（P0 锚点）
Q1 什么会让这次修改把 CLD 搞崩？（类型错/依赖缺/路径错）
Q2 什么会让会话消失/历史读不了？（版本遮蔽/服务 pending）
Q3 怎么知道改坏了？（C1-C7 哪一项先报警）
Q4 回滚点在哪？（.bak-good-* 路径）
```

---

## 七、操作流程（编译检查器视角）

```
输入: (target, change)
── 类型检查 ──────────────────────────────
⓪ guard-doc-check "<主题>"      → P0 证明（官方预查 ≤24h，机器留证）
① guard backup target          → P1 证明
② guard check-writable target  → P2 证明
③ 若依赖: version-check        → P3 证明
④ 沙箱副本验证                  → P4 证明
⑤ pre-mortem 五问(Q0-Q4)       → 反例检查
── 求值（执行）────────────────────────────
⑥ 落真修改
── 穷尽验证 ─────────────────────────────
⑦ C1-C7 全部通过 → safe_edit 成立 ✅
   任一失败 → 回滚 .bak-good → 重新证明
── 记录 ─────────────────────────────────
⑧ 报告（含 unsafe 标记 + 证据 + 工具箱条目引用）
```

---

## 八、铁律（违反 = 直接违规）

0. **先查官方，再谈修**（P0）——旧认知会过时，机器强制 ≤24h 预查
1. **无备份不改**（P1）——pnpm 事故最大教训
2. **无门禁不碰底层**（P2）
3. **改依赖必查版本**（P3）——65 遮蔽包教训
4. **沙箱不过不落真**（P4）
5. **3 次不收敛必回滚**（P5）——不无限试错
6. **C1-C7 不全过不算成功**——boot 过 ≠ 会话/历史正常
7. **unsafe 必补证**——axiom 不能进最终证明

---

## 九、本文档自身也是 Lean 对象

- 本文档 = 规范库（类似 Lean 的 Mathlib）
- 每次事故 = 新增一个 theorem/lemma（沉淀到 docs/经验沉淀 或 高频问题处理工具箱）
- guard-gate = 编译器（把本文档前提机械执行）
- guard-doc-check = P0 证明义务的机器执行者（查官方 + 留证 + 防过时）
- 本 agent 档案 = 依赖声明（声明了就必须遵守）

---

## 十、主动学习条款（v2.3 · 不等问题才学 · 2026-09-04）

**动机**：被动修复 = 每次都交"第一次学费"；主动学习 = 把学费变成预存的定理库。官方文档在持续更新（deepseek-harness master 每日推送），知识会过时。

### 学-建-用 循环（Lean 形式）
```
theorem learn_loop (part : Part) :
  → guard-knowledge learn part          -- 登记学习中
  ∧ read_official part                  -- 读官方文档(tech-research 镜像/上游源)
  ∧ build_card part                     -- 部件卡毕业(9节: 概念/约束/依赖/规范/关联)
  ∧ plant_standard part                 -- 沉淀标准/工具(可机器化则建工具)
  ∧ associate part                      -- 关联: 工具箱T# ↔ 路由OP ↔ 规范 ↔ 文档链接
  → guard-knowledge mark part learned   -- 登记毕业
```
**节奏**：每轮 ≤1 P0 或 ≤2 P1/P2 部件；优先级 = 路由表实证出事频率（P0 先学）。
**入口**：`guard-knowledge status/next/learn/check/mark`（机械管理进度与毕业校验）。
**知识库**：`cld-dsh-dev-system/knowledge/{registry.json, parts/*.md, INDEX.md, 学习计划.md}`。

### 官方追踪义务（doc-sync）
```
必须（定期/修复前）: doc-sync  → 文档 HEAD + npm 上游版本对比
命中更新: ① 记录 ② 若涉及知识库部件 → guard-knowledge show <id> 复审 ③ 评估影响(风险路由)
镜像过期: tech-research 镜像 >14 天 → guard-doc-check 会要求 --web 补证（P0 联动）
```

### 学-建-用 的反模式
- 只读不卡（读了不沉淀 = 白读）
- 卡不全就 mark learned（毕业需 check 通过：卡9节+标准+关联+沉淀）
- 有更新不复审（知识过时 = 新的踩坑源）
- 优先级乱序（学冷门不学出事域 = 效率低）

---

*规范 v2.0-lean · 2026-09-04 · guard-gate v2 + guard-doc-check 已实现（P0-P5 机械执行）*
