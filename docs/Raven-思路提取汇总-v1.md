# Raven 有价值的思路提取汇总 v1

> 来源：Raven 技术报告 PDF（82 页）+ [官方文档站](https://evermind-ai.github.io/Raven/) + [HarnessBank arXiv 2607.13683](https://ar5iv.labs.arxiv.org/html/2607.13683) + [EverOS DSH 插件 README](https://github.com/EverMind-AI/plugins/tree/main/dsh)
> 配套：`Raven-借鉴分析-v2.md`（怎么用到 CLD/DSH）· `wiki/research/raven-harness-of-harnesses.md`（调研报告）
> 说明：本表**只提取思路本身**，不重复应用方案。每条注明是否为一手报告明说（📄报告）还是仅 README/文档站（📄README/📄docs）——**证据强度不同**。

---

## 零、怎么读

- **可迁移的是流程，不是配置**。论文用跨模型实验证明了这条：把一个模型的补丁生搬到另一个模型上，效果接近归零，甚至**负优化 −15.7%**。所以下表的重点在方法论，不在任何一条具体 prompt。
- **标注了三档可信度**：📄报告（有实验证据）> 📄docs（工程实现，有诚实边界声明）> 📄README（产品叙事，无实验证据）。

---

## 一、最值得带走的 6 条

| # | 思路 | 一句话 |
|---|---|---|
| 1 | **改进必须过三道门** | 有效 → 激活 → 显著，三者回答三个不同问题，**不可合并成单一分数** |
| 2 | **激活门** | 改完要证明"这段代码真的执行过"；从未触发的改动 = 惰性，不得入库 |
| 3 | **分母不可缩水** | 失败任务计 0 留在分母，不剔除。污染只报告，不缩小统计基数 |
| 4 | **测试集封存 + 机械断言** | 选择全程不碰测试集，且用断言在启动时 raise，而非靠纪律 |
| 5 | **语义基因库 (WHERE × WHY)** | 同格竞争、跨格重组；WHERE 机械推导，绝不采信自我声明 |
| 6 | **产品文档写成"证据边界"清单** | 每个能力声明附「实际含义 + 重要限制」，把"没做成什么"写成正文 |

---

## 二、验证哲学（最核心的一节）

### 1. Harness 形式化：`H = K ∪ X`　📄报告
- **机制**：`H(X_edit) = {h : Exec(h)=Exec(Apply(h0,Δpatch)), scope(Δpatch)⊆X_edit, h|K_fixed=h0|K_fixed, InterfaceValid(h)=1}`（Eq.42）
- **思路**：**允许改的位置、保护的位置、接口合法性——三者必须先声明**，否则"自我修改"无因果可言。不可变内核 `K` 装评测、记账、自进化、接口关键代码。
- **解决**：没有内核边界时，"改好了"无法归因，改动也不可回滚。

### 2. 三道门，而非一个分数　📄报告
`g_scn = g_valid × g_act × g_sig`（§3.3），另有"增益"在完整训练集阶段要求胜过**固定 vanilla 基线**。
- `g_valid`：log 协议合法；基础设施故障（沙箱崩溃/验证器超时）触发**修复重试**，不是计为 agent 失败
- `g_act`：`I[ΣᵢΣ_k active_{i,k} > 0]`——提案**在评估前固定**激活谓词，运行时确定性上报
- `g_sig`：配对差 `γᵢ = s̄ᵢ(候选) − s̄ᵢ(父代)`，`t_pair = γ̄/se ≥ 1.96`；**先对 K 次取平均，使测量单位是"任务"，样本量 n 而非 n·K**
- **思路精髓**：三门回答三个**不同**问题——"干预改造了吗 / 训练集上排第几 / 未见任务上有用吗"。合并成单一分数就失去可审计性。

### 3. 分母不可缩水　📄报告
- **原话**："Agent failures remain **scored outcomes** and cannot be removed from its `|D|·K_att` denominator"（§4.2 p26）
- **思路**：Gate-f 只**报告**污染清单，**从不缩小分母**。全训练分、归因子集、统计信用回答三个不同问题，不能互相替代。
- **解决**：把"脏数据剔掉再算"这种自欺。

### 4. 测试集封存 + 机械断言　📄报告 + 📄docs
- **原话**："Test outcomes do not revise proposals, thresholds, archive cells, or the selected harness"（p28）
- **落地**：`assert_no_test_leak` 检查任务切分不重叠，**泄漏在启动时直接 raise**（不是靠自觉）
- **配套纪律**：最终交付物**按训练分选**，绝不在候选里"挑测试分最高的"；报告 `retention = test lift ÷ train lift`
- **诚实条款**：`run --force` 可绕过守卫，但"**does not restore an honest sealed experiment**"——一旦看过测试集，建议换新工作目录与未动过的留出集

### 5. 晋级 ≠ 显著：两个独立字段　📄docs
- **机制**：`promoted`（导航用，K=3 均值 > vanilla）与 `credited_2sigma`（论文用，配对 2σ）**是两个独立字段**，晋级只读前者
- **原话**："A promoted candidate can have `credited_2sigma: false`; that is **not proof** of a statistically significant improvement."
- **思路**：**导航信号**和**信用信号**必须分开。导航可以宽松（否则搜不动），信用必须严格（否则自欺）。

### 6. 存档准入与父代选择用不同比较　📄报告
- **原话**："A candidate can outperform its parent on the **screening subset** yet fall below it on the **full training set**"（§4.3 p27）
- **思路**：让"能进档案"和"能当下一代父代"用不同标准，避免小子集噪声污染谱系。

### 7. 病理标签是假设，不是真值　📄报告
- **原话**："Pathology labels remain **hypotheses, not established causes**"（§4.3 p26）
- **思路**：WHY 只决定"**试哪个候选**"，信用完全来自门控。因此**标错标签最多浪费一个候选，永不产生坏 harness**。这是一个极优雅的失效隔离设计。
- **实证**：论文中 AppWorld 一轮把"能力上限"误诊为"知识缺口"，门控把提案拒了（目标任务 0/24→0/24，p=1.0）。

### 8. 激活门是弱证据——照抄它的诚实　📄报告 + 📄docs
- **原话**：只证明"某段被插桩的代码跑过"，**不证明它位于机制的触发条件内，也不建立因果贡献**；"an **unconditionally-placed beacon degrades Gate-b to a no-op**"
- **思路**：**主动声明自己证据的等级**。一个门控机制如果不敢说清自己证明了什么、没证明什么，就不该被信任。
- **无仪表时 fail-open**：宁可放过一个无仪表但诚实的候选，也不误杀。

### 9. 消融：没有显著性门会发生什么　📄报告
- 去掉显著性门后，**收敛后轮次中 62%–76% 是"幻影进展"**，循环只能在轮次上限（>20）停下；带完整门控的版本能在 **10 轮下限**干净退出
- 反例：**无门控的 DGM 在 Omni-MATH 上部署了比 vanilla 更差的版本（−1.1%）**——"an ungated loop can deploy a regression"
- **思路**：**噪声不只是浪费预算，它会真的把系统改坏**。

### 10. 增益必须对固定基线，不是对上一版　📄docs
- **原话**：终止信号定义为 "beating the **FIXED** vanilla"，而非"没有新科冠军"
- **思路**：跟"上一代"比会掩盖**渐进式退化**——每一代都只比前代好一点点，累计下来可能不如起点。

---

## 三、搜索与进化（防塌缩）

### 11. 语义基因库　📄报告
- **机制**：`B_r : W_edit × Y_fail → H(X_edit) ∪ {⊥}`（Eq.45）——**每个 (编辑类别 × 病理) 格只存一个 elite**
- **WHERE** `= {prompt, knowledge, runtime, config}`（Eq.45）；**注意**这与**四策略接口** `(Mem,Plan,Cap,Act; θ)`（Eq.39）是**两个正交轴**，报告 §4.3 明文 "distinct"
- **思路**：模仿 MAP-Elites 的质量多样性。**不按分数只留一个最优解**，而是按"改在哪、为什么改"分格——保住结构不同的好方案，让它们有被重组的机会
- **反面**：贪心演化会随着代数推移**塌缩成 prompt 层面的保守修补**

### 12. WHERE 机械推导，不采信自我声明　📄docs
- **原话**：`bind_where` 从**实际改动的文件**推导杠杆；自我声明的 `patch_where` "stays in the ledger for audit and **never decides the archive coordinate**"
- **思路**：**归档坐标等记账类元数据，必须从客观事实机械推导**。自我声明只留作审计。这与我们 R030「无验证不陈述」同源。

### 13. 跨格重组，但承认增益不可加　📄报告
- **原话**："The combined harness requires its own evaluation because the components may interact and **their gains need not be additive**"（§4.3 p27）
- **思路**：鼓励重组，但**重组的产物必须当作全新候选重新评估**，不能把两个组件的增益相加。

### 14. 病理→补丁匹配律：没有万能的 Harness　📄报告
- 每个模型有自己**支配性的失败模式**：27B 死于"空转回合"（verify-finalize 补丁 +15.4%），397B/Gemini 死于"粗心"（清单补丁 +13.6%/+13.5%）
- 交叉上补丁：**接近归零（+0.2, +1.2）**；数学推理上 27B "想太多"、Gemini "想太少"，**同一个旋钮要反向拧**；拧错方向是 **−15.7%**
- **思路**：**真正可迁移的是"诊断失败→结构化搜索→统计验证"这整套流程，而不是任何一条具体 Harness 或 Prompt**。

### 15. 惰性死亡反馈（inert death）　📄docs
- **机制**：`pruned_inert` 是因为**触发器从未触发**而死的候选，与"机制被判无效"是不同的死法。惰性死亡会写进 per-WHY 历史，设计提示词会**区分这两种死法**，且 WHY 权重有"温柔衰减"（`0.55^n_fail × 0.85^n_inert`）
- **思路**：**失败的候选也在教学**——"你的触发器没被触达"和"你的机制不管用"要给下一代完全不同的启示。

### 16. 伤害回放（harm replay）　📄docs
- **机制**：当候选导致某任务**回归**时，把该任务在候选下的**实际执行轨迹片段**喂给下一次候选设计
- **思路**：SOP 只要求 flip 计数，但**光有数字学不到东西**——要给出反例的真实过程。

---

## 四、编排

### 17. 从交付物反向构图　📄报告
- **原话**："The host constructs the graph by **working backward from the requested deliverable**. Each node must have an identifiable output... The host then **adds a dependency whenever producing one node's input requires another node's output**."（§3.1 p14）
- **思路**：构图方向是"**倒推**"，不是"顺推步骤"。这样每个节点都天然有可验收的产物。

### 18. 分阶段披露编排指南　📄报告
- **问题**：完整编排规则放每轮上下文 = **恒定输入成本**
- **机制**：每轮只带**短描述**；当 host 判断需要多 agent 时，工具描述指示它**先加载完整指南**，加载后 **pin 在会话上下文**；**被拒的图返回"校验错误 + 指南指针"**
- **思路**：**按需加载元规则 + 错误驱动补课**。这是一条能直接砍掉常驻 token 成本的具体手法。

### 19. 节点产物落盘 + 记忆异步　📄报告
- **原话**："**Artifact completion therefore releases dependencies, while memory recording proceeds asynchronously**"（§3.3 p19）
- **机制**：产物落 `prompt.md / out.md / transcript / memory.json`，后继**按路径读**；记忆写入**不阻塞**后继
- **思路**：**把"释放依赖"和"沉淀经验"解耦**。最省 token、最可审计的多 agent 数据流范式。

### 20. 依赖域路径传播　📄报告
- **机制**：`Paths_v = { MemPath(u) : u ∈ Anc_{G_rt}(v) }`（Eq.32）——把**传递前驱的记忆路径**追加给有能力读文件的节点
- **原话**：让接收方"**have the option to inspect relevant experience without eagerly copying all ancestor memories into its prompt**"
- **思路**：**给路径，不给内容**。需要时自己去读，不需要就不占上下文。无本地文件能力的后端**收不到无用的路径块**。

### 21. Ready 集合的两个防错集合　📄报告
- **机制**：`Ready = {v : pending ∧ v ∉ Submitted ∧ ∀u∈Dep(v), z(u)=completed ∧ u ∉ Unsettled}`
- `Submitted_jrt` 防止**等槽位的节点被重复提交**
- `Unsettled_jrt` 防止**消费者读取一个完成判定可能被推翻的调用输出**
- **思路**：这是两个非常精确的竞态防护，值得直接借用命名与语义。

### 22. 判官外置　📄报告
- **原话**："An **independent model call** therefore judges each finished node"（§3.2 p16）
- **机制**：判官读「渲染后的 prompt + 输出 + 轨迹尾部」；**负判必须给出类别与证据**；判官失败/超时则**按可用性回退视为完成**
- **诚实边界**：官方承认这是**可用性权衡，而非正确性证明**
- **思路**：**"后端返回了" ≠ "任务完成了"**。但也不要把它当成安全闸。

### 23. 异常三动作：continue / abandon / replan　📄报告
- 负判且尚有余量 → `exception`（**挂起等 host 裁决，不向上传播**）
- 上游 failed/skipped → 后继 `skipped`（**独立分支不必丢弃**）
- **replan**：校验后继图并**以新 run id 关联旧 run**；旧 run 未完成节点 skip/cancel/superseded，**已完成节点按引用保留**

### 24. 澄清请求 host 先代答，但永不代答审批　📄报告
- **机制**：worker 提问时，host 用「问题 + 会话快照 + 本会话早先答复 + 以问题为 query 的 EverOS 召回」**先自行回答**
- **约束**：**仅当用户明确说过、或召回偏好唯一确定答案时才答**；"It **never** answers a request to approve an action, such as pushing, deleting, sending, or paying"
- **思路**：subagent 反复问"要什么格式"是最常见的 token 浪费——但**代答的权限边界必须画死**。

### 25. 分层：roster → worker table → charter → playbook　📄docs
| 层 | 生命周期 | 含义 |
|---|---|---|
| Roster agent | 注册配置 | 哪个后端能执行 |
| Worker Table row | **一个 host turn** | 本任务的标签与职责 |
| Charter | **一次派发的 worker turn** | 收窄的指令/工具/检查/deadline |
| Stored Playbook | 可复用文件 | 已审阅的图与参数 |
- **Charter 只做交集**："It **intersects** the worker's existing permissions: it may narrow a tool set or deadline, **not restore a disabled tool or extend a configured deadline**"
- **思路**：**派发只能收窄、永不扩大权限**。生成式裁决代码走 **AST allowlist**，被拒的代码丢弃并告警。

### 26. 存储过程规格化的细节　📄docs
- Playbook 文件 = **两字段 frontmatter + 人类可读正文 + 恰好一个 yaml `playbook-spec` 块**
- `params` 七型：`string/integer/number/boolean/enum/path/secret`
- `fills` 补作者留空：**已填值不可改**；**显式空列表是固定选择，不是留空**
- `secret` 参数存 `0600`，**仅 carried MCP 的 env/headers 能取到**，prompt 中的引用被 withhold 并记录；官方自述"**this is a local file, not an encrypted vault**"
- **思路**：把"复用一套多步流程"变成**可审阅、可校验、可遮蔽（用户层遮蔽内置层）**的文件。

---

## 五、记忆

### 27. Markdown 权威源 + 索引可丢弃　📄报告
- **原话**："EverOS stores episodes, facts, profiles, cases, and skills as **Markdown records**. SQLite maintains operational state... a **derived index** supports lexical and vector retrieval... **The Markdown records can be used to rebuild the search index.**"（§5.5 p34）
- **思路**：**Markdown 是真相源（可读、可 diff、可重建），向量库只是缓存**。索引坏了重建即可，不丢知识。

### 28. 召回两段拼接 + 围栏　📄报告
- **机制**：`MemContext(q) = Archive(q) ++ Fence(Recall(q))`（Eq.65）
  - `Archive`：host 维护的 workspace Markdown 归档——取"与消息**词法重叠最大**的 2 个 profile 段 + **全部 Notes 段**"
  - `Recall`：向量召回，用 `Fence` 标记为**不可信上下文数据**
- **思路**：**召回内容必须被标记为"不可信历史证据"**，否则历史记录会变成注入通道。

### 29. fail-open：记忆坏掉不能拖垮对话　📄DSH插件
- **原话**：EverOS failures "are logged, but **never reject the user's DSH step or turn**"
- **思路**：记忆是**增强件**，不是关键路径。故障降级为"这一轮没有记忆"，不是"这一轮失败"。

### 30. 防递归自捕获　📄DSH插件
- **原话**："Stored fence tokens are **neutralized** before injection, which prevents a recalled item from escaping the memory block. **Plugin-generated context is never captured as direct user input**, so recalled memory does not recursively save itself."
- **思路**：这是一条**很容易踩的 bug 类**——插件注入的上下文若不排除，会被当成用户输入再存一遍，形成自我放大的回声。

### 31. user track / agent track 双轨 + 确定性 ID　📄DSH插件
- **机制**：`user` 记录属 user，`cases/skills` 属 agent；`project_id` = 工作区目录名 + **绝对路径的稳定哈希**（同名目录的两个仓库仍然隔离）；所有派生标识符**确定性且路径安全**
- **原话**："**a session describes where an experience occurred, while ownership determines the collection in which it can be recalled**"
- **思路**：**"用户偏好"和"agent 经验"是两种不同的记忆**，不能混在一个池子里召回。

### 32. 记忆写入是 off-turn 队列　📄docs
- **原话**："An answer finishing **does not mean backend indexing finished**; outages, queue limits, and shutdown can leave data **unindexed or in an uncertain in-flight state**."；"**Memory persistence is not a backup of the entire transcript.**"
- **思路**：**答案写完 ≠ 索引写完**。别在下一轮立刻依赖刚写的东西（除非有 read-after-write 屏障——Raven 确实在会话切换时做了 barrier）。

### 33. 三方分离：上下文组装 / 记忆存储 / 压缩　📄docs
- **Curator** 决定本轮上下文窗口看到什么（快路径低于压力阈值不调模型）
- **记忆后端** 决定长期留存与召回
- **Compaction** 是轮内裁剪（默认关），**不写长期记忆**
- **思路**：这三者常被混为"记忆"，但**故障表现完全不同**——"为什么它忘了"要分头排查。

---

## 六、技能

### 34. pull vs push 两种发现模式　📄docs
- **pull**（默认）：模型收到**小菜单**，用 `find_skill` 搜、`read_skill` 取全文
- **push**：跑选择/注入流水线，把选中正文放进上下文
- **原话**："Pull avoids the push path's **per-turn rewriting and gating model calls**"
- **思路**：菜单常驻很便宜，正文才贵。**默认 pull**。

### 35. RRF 两级分离　📄报告
- **原话**："**RRF determines expansion order, while calibrated scores determine final relevance**"（Eq.71–72）
- 名字分组用 **RRF**（避免比较不同源的原生分数量纲）；代表选择才用**原生分**（`rep(n) ∈ argmax score_native(h)`）
- **反直觉后果**："Rescaling a source's scores can change the injected version **without changing its name's RRF position**"
- **思路**：**排序和选代表是两件事，用两套分数**。多源融合时非常实用。

### 36. 名字分组用精确名，不做语义等价　📄报告
- **原话**："It groups exact name matches **without testing semantic equivalence**"（§6.2）
- **思路**：融合层做**精确折叠**就够了；**同义技能是另一个问题**，不要在这里偷偷解决（会误合并）。

### 37. 选择 / 资源可用 / 实际执行 是三个不同事件　📄报告
- **原话**："**Selection, resource availability, and actual execution are therefore different events.**"；跳过的安装"retains the available body with **unresolved resource references**"
- **思路**：别把"选中了"当成"能用了"当成"跑通了"。

### 38. 技能不退役　📄报告
- **原话**："**A confidence below 0.1 does not remove a skill.** EverOS writes that record as an ordinary skill, and later retrieval can return it. The pipeline **does not invoke `retire_confidence`**."（§6.3）
- **思路**：宁可让低分技能留在库里（可能哪天有用），也不自动删除。**删除是不可逆的，保留是可逆的**。

### 39. 案例（case）复制不等于独立成功　📄报告
- **原话**：同一 case 在每个参与 owner 下分别持久化，"This replication makes a shared execution available to its participants. It **does not constitute independent successes or causal credit** for each participant."（§6.3）
- **思路**：**共享执行记录 ≠ 各自的独立功劳**。做多 agent 计分时这是个大坑。

---

## 七、权限与信任边界

### 40. Permission Gate 四步决策序　📄docs
1. **内置裁决**拒绝灾难级命令（如递归删除根/家目录树）
2. **用户规则** `permissions.tools` 选 `deny/allow/ask`
3. 未匹配则用**工具默认档**
4. **当前模式**解释 `ask` 档（`ask`/`smart`/`full`）
- **思路**：**内置 deny 永远不可被用户规则覆盖**。这是"安全兜底"和"可配置"的正确分工。

### 41. shell 前缀匹配的保守解析　📄docs
- 具体模式间 **strictest-wins**：`deny > ask > allow`，与顺序无关（**不同于** OpenCode 的 last-match-wins）
- **复合命令**：每段都 allow 才 allow；一段 deny 即 deny
- **deny 会穿透包装器**：`sudo`/`env`/`bash -c`/`xargs`/`doas`/`watch`、命令替换、重定向之后、以及带路径的（`/usr/bin/curl`）都问
- **诚实边界**：它"**cannot see a command a program builds for itself**（`python -c`、脚本文件、alias）"，"This is conservative parsing, **not a proof**"
- **思路**：**说清匹配器的能力边界**，比宣称"我们拦截了危险命令"有用得多。

### 42. 委派是独立的信任边界　📄docs
- **出站 ACP 的自动批准是明说的重大边界**："it is **not per-operation human approval**"；自动选 `allow_always` > `allow_once`
- **但拒绝会下传**：命中 deny 规则的调用会回 reject option；**自研 agent 把 deny 规则渲染进自己配置**；第三方 agent 只对"它主动询问的部分"受约束
- **思路**：**host 的闸门只管自己的注册表调用**。跨进程委派要单独配策略与隔离。

### 43. 主动声明"这不是安全闸"　📄docs
- Charter："**not an OS sandbox or a fail-closed security boundary**"
- DAG `confirm: true`："**not** an unattended security gate"——"With no ask channel wired, the current implementation **logs a notice and runs unconfirmed**"
- A2A bearer token："shared operator access, **not per-user authorization or a sandbox**"
- ACP 脱敏："**redaction is not a complete secret scanner**"
- **思路**：**把"我们没有保证的东西"写进正文**。这是最有价值的一条工程文化。

---

## 八、工程与诚实

### 44. Assembly Root + Kernel 边界靠 import 契约强制　📄docs
- 所有运行时入口经 `raven/core/runtime.py:build_runtime` 组装；配置与插件贡献决定每个**运行时 Generation** 的组件
- **Kernel** = `spine/` + `contracts/` + `tracing/` + `home.py`；**内层包不得 import CLI/RPC/ACP 接口**
- **机制**：`pyproject.toml` 定义 import contracts **强制**这些边界
- **思路**：**边界不靠口头约定，靠构建时静态强制**。这对我们「插件 node_modules 遮蔽 runtime 包」（M1 遮蔽）这类问题是对症解法。

### 45. 候选改动走 git 子提交，主工作树不动　📄docs
- `commit_files_as_child`：编辑落为**父提交的真实 git 子提交**，**主工作树与 HEAD 保持不动**；`evolver refs` 锚定候选防 gc
- 评估在 `work_dir/tmp` 下的临时 worktree 做，下次启动清扫残留
- **思路**：**改动的载体是提交，不是文件**。可回滚、可对比、可审计。

### 46. 配置指纹 + resume 拒绝漂移　📄docs
- `run_meta.json` 记录**有效配置指纹**；launcher 默认拒绝配置变更或已 finalize 的运行
- **诚实条款**：`--force` 能绕过守卫，但"**does not restore an honest sealed experiment or automatically make changed measurements comparable**"
- **思路**：**实验的配置必须冻结**，否则前后数据不可比。

### 47. 错误轮不烧 patience　📄docs
- 终止条件是"连续 N 轮无人胜过固定 vanilla"，但 **errored 轮不计入 patience**（另有 `max_consecutive_errors` 作独立兜底）
- **思路**：**把"环境坏了"和"方法不行"分开计数**——否则基础设施抖动会误杀一个还在进展的搜索。

### 48. 启动前置检查（Gate0）　📄docs
- `check` 会跑 bench 的 Gate0 precheck：**死掉的后端端点在 check 时失败，而不是在冷启动中途失败**
- **思路**：**把环境故障前移到最便宜的时间点**，别花完 rollout 预算才发现端点不可达。

### 49. 把"没做成的事"写成正文　📄docs
文档站有专门的 "**honest list**" 章节，逐条登记**故意偏离**与**已实现但未接线**的部分：
- borrowing 模块存在但 orchestrator **不调用**它
- affinity anchor **缺数据源**
- zero-hit preflight **默认关闭**，实际 prune 率**未知**
- `skillForge.extraction` 配置项仍在，**live host 不消费**
- 反馈驱动的技能版本化与退役 **未实现**（配置占位符存在 ≠ 功能存在）
- **思路**：**"配置里有"不等于"功能开了"**。这类清单能直接省掉别人几小时的误判。

### 50. 未评测就写"未评测"　📄报告
- **原话**："**Group memory is disabled by default and is not evaluated in this report.** Its effect on orchestration and task performance **remains to be established**."（§3.4 p23）
- 另一处："**Lexical filtering alone cannot rule out paraphrased planning cues**, which remain a review concern."（§7.1.1 p41）
- AI4AI 结论标注"Each system ran **one campaign**"（n=1）
- **思路**：**在摘要旁边就标注它的效力边界**，而不是等别人发现。

---

## 九、反模式清单：Raven 自己承认失效或未成立的设计

这一节可能是**最省时间**的一节——直接告诉我们哪些别抄。

| 项 | 官方原话 / 事实 | 判断 |
|---|---|---|
| **Group memory（分组共享记忆）** | "**disabled by default and is not evaluated in this report**"；"Verdicts remain observational judgments by the host and **may be incorrect**" | ❌ 未成立 |
| **Curator（运行时自进化）** | 技术报告 **0 命中**；README 自述 "**experimental**: it ships with the repository rather than the installed package" | ⚠️ 无证据支撑 |
| **Persona / 数字人** | 报告 **0 命中**，仅 README 叙事，**无文件级产物形态** | ⚠️ 产品叙事 |
| **Evolver** | README 标记 "**for planned retirement**"；"registers **AppWorld only**"；"**not a full-scale multi-round run or real-benchmark sealed-test retention validation**" | ❌ 不要依赖 |
| **激活门（无条件信标）** | "an unconditionally-placed beacon **degrades Gate-b to a no-op**" | ⚠️ 易失效 |
| **A2A** | "Task storage is **in memory and is lost on restart**"；"Push notifications are **not supported**"；`CancelTask` "**not proof that every external side effect was undone**" | ❌ 不适合持久协作 |
| **DAG 的持久性** | "DAGs ... **do not provide** a durable, distributed task queue"；"history recovery is **not automatic execution resumption**" | ❌ 别当成工作流引擎 |
| **SkillHub 语料** | "a catalog safety score is **not a security guarantee**"；"**missing scores are not a hard rejection**" | ⚠️ 供应链风险 |
| **技能的反馈驱动版本化/退役** | 报告自述"**not implemented** merely because configuration placeholders exist" | ❌ 未实现 |
| **跨设备 All-Domain 网络** | §9 全部列为 **future work**（"We **envision**... We **will develop**..."） | ❌ 路线图 |
| **MAOB 评测泄漏控制** | "Lexical filtering alone **cannot rule out paraphrased planning cues**" | ⚠️ 方法论待改进 |
| **SWE-bench Verified 结论** | n=26，+5.1% 仍 **z=0.78 未过门**，官方自己标 preliminary | ⚠️ 小样本 |
| **Edge F1 vs Node F1** | 所有系统、两个 backbone 下 **Edge F1 一律低于 Node F1**——依赖预测是公认难点 | ⚠️ 未解 |
| **技能增益的部分单元** | GDPval 上"per-task reward standard deviations of **20 to 27 points**"，而单元增益仅 1.2–1.9 分，"**not statistically distinguishable from zero**" | ⚠️ 效应量淹没于噪声 |
| **成本** | "The utility in Eq.(43) contains **no implicit cost penalty**" | ⚠️ 成本须单独测 |
| **复现证据** | 源论文"does **not provide a complete per-run manifest**"——七个数字**无法仅凭论文重建** | ⚠️ 复现性缺口 |

---

## 十、一句话

Raven 经得起检验的内核是 **三个层次的设计纪律**：

1. **形式化**——把 harness 切成"不可变内核 + 可变面"，把编辑空间切成"改在哪 × 为什么改"的语义坐标；记账类元数据**机械推导**，不采信声明。
2. **结构**——从交付物反向构图、产物落盘释放依赖、记忆异步沉淀、给路径不给内容、派发只收窄权限、判官外置但不当安全闸。
3. **验证**——三道门各答一问、分母不缩水、测试集封存且**机械断言**、晋级与信用分离、增益对固定基线。

而它最有价值的**不是任何一条机制，是那套把"我们证明了什么、没证明什么"写进正文的习惯**。Curator / Persona 是产品层叙事，报告本身没有为其提供证据。

---

*提取自 2026-09-28 调研；一手材料见 `raw/research/2026-09-28-raven-harness-of-harnesses/`（13 份）。*
