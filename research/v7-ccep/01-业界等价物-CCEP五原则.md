# 01 · CCEP 五原则的业界等价物

> **调研代理**：R-M3（v7 计划 · M3 协议族模块）
> **现测时刻**：2026-10-12T20:04:34+08:00（+08:00）
> **检索工具**：`web_search`（7 轮）+ `read_url` / `read_url_batch`（实际读取 19 页，2 页超时失败）
> **纪律**：★ **不编造 URL**；★ 未读成功的如实标注；★ **未搜到 ≠ 不存在**；★ 不得把「本机已有」写成「业界最新」。

---

## 〇、一句话结论

**五条原则里，没有一条在业界有「完全等价物」——因为它们的取证对象是「通讯通道本身」，而业界全部等价物作用在「应用 / 流量 / 制品 / 配置」层。**

★ **其中原则 2「自举」的语义最独特**：业界**未搜到**以「新版本必须经旧通道投递」为硬约束的成文标准。
★ **原则 5 在「单机进程级」有一个近乎完全等价的先例**：nginx 配置失败即回滚并沿用旧配置。

### 逐条评级（★ 本线判定，非引用）

| # | CCEP 原则 | 最接近的业界对应物 | ★ 等价程度 |
|---|---|---|---|
| 1 | 永续通讯 | K8s PDB / nginx 平滑升级 / HTTP2 GOAWAY | **部分等价** |
| 2 | 通道自举 | TUF / Uptane / Android A/B / Omaha | **★ 仅半条等价**（自举那半无对应物） |
| 3 | 验证先行 | readiness probe / server-side dry-run / CI 门禁 | **部分等价** |
| 4 | 沙箱先行 | Istio mirroring / Kayenta 金丝雀 / Netflix ChAP | **仅形似～部分等价** |
| 5 | 可回滚 | kubectl rollout undo / Argo CD rollback / 不可变基础设施 / Parallel Change | **应用层部分等价；通道层仅 nginx 一例近乎完全等价** |

---

## 一、原则 1 · 永续通讯 ↔ 零停机部署族

**原则原文**（`docs/CCEP-continuity-protocol-v1.md:10`）：
> 跨设备通道（黑板/SSE/注入）升级过程中，任何时刻至少有一条可用通道——绝不出现「全部断掉需要人工重连」。

### 业界对应物

1. **Kubernetes Deployment 滚动更新**（`maxUnavailable` / `maxSurge`）——声明式地以受控速率用新 ReplicaSet 替换旧的，保证期间有 Pod 持续服务。
   来源：<https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>（官方文档，已读取）
2. **PodDisruptionBudget（PDB）**——限制自愿中断期间同时不可用的 Pod 数。官方示例原文：无状态前端「不希望服务容量下降超过 10%」，用 `minAvailable: 90%`。
   来源：<https://kubernetes.io/docs/tasks/run-application/configure-pdb/>（官方文档，已读取）
3. **nginx 热升级 + graceful shutdown**——`HUP` 重读配置：新 worker 起来后，旧 worker 关闭监听套接字但**继续服务老客户端**，全部服务完才退出；`USR2` 支持不停机换可执行文件。
   来源：<https://nginx.org/en/docs/control.html>（官方文档，已读取）
4. **RFC 9113 HTTP/2 GOAWAY**（连接优雅排空）。
   来源：<https://www.rfc-editor.org/rfc/rfc9113.html>（IETF 标准，已读取）
   旁证：<https://datatracker.ietf.org/doc/html/draft-ietf-webtrans-http3-06>（已读取）

### ★ 等价程度：部分等价

- **差异**：PDB 的设计前提**就是允许一部分不可用**（官方原文即 `minAvailable: 90%`）；CCEP 禁止的是「**全部**断掉」这一状态。
- nginx 平滑升级是**单机单通道内的进程级并存**，不涉及跨设备多异构通道。
- GOAWAY 是「单连接优雅退休」，与「多通道冗余」不同层级。
- ★ **反向证据**：**共识协议方向相反**——Raft 类系统丢 quorum 即**停止服务**（宁停不乱），与 CCEP「永不整体断开」是相反取向。

### CCEP 独有的部分

把「**通道面自身**」（黑板 HTTP / SSE / 注入三条异构通道）作为被保护对象，并**禁止「全部断掉需人工重连」这一状态存在**。
业界可用性预算是「**允许按比例降级**」；CCEP 要求的是「**至少一条**」——★ 这比全绿弱，但比按比例降级强。

---

## 二、原则 2 · 通道自举 ↔ self-update / A-B 分区

**原则原文**（`:11`）：
> 新版本必须通过旧通道投递（genebank/黑板 notes/playbook 提示词），端侧在旧通道上收到完整迭代信息并验证，才切换。

### 业界对应物

1. **The Update Framework (TUF) 规范 v1.0.34**——客户端在安装前必须对元数据（Root/Timestamp/Snapshot/Targets）与目标文件做阈值签名、**防回滚**、防混同验证。
   来源：<https://theupdateframework.github.io/specification/v1.0.34/index.html>（规范原文，已读取）；项目主页 <https://theupdateframework.io/>（CNCF 毕业项目，已读取）
2. **Uptane Standard v1.1.0**（IEEE-ISTO 6100.1.0.0）——车端安全 OTA 标准，规定 Primary/Secondary ECU 在安装镜像前的元数据验证流程。
   来源：<https://uptane.org/papers/uptane-standard.1.1.0.html>（标准原文，已读取）
3. **Android / ChromeOS A/B 无缝更新**（`update_engine`）——由**正在运行的旧系统**把新镜像写入另一分区，切换前执行校验。
   来源：<https://android.googlesource.com/platform/system/update_engine/+/c081f4174a0aceda3f823d6bebcb1c8053d22c79/>（AOSP 源码树，已读取）
4. **Omaha 协议 v3.1**（Chromium 更新器）——旧客户端发起「更新检查 → 下载 → 安装」三阶段会话，自行决定安装时机。
   来源：<https://chromium.googlesource.com/experimental/chromium/src/+/refs/tags/89.0.4380.6/docs/updater/protocol_3_1.md>（协议文档，已读取）

### ★★ 等价程度：只有半条等价

- **对应上的那半条 = 「旧版本侧执行验证」**：TUF/Uptane 明确把验证责任放在**已安装的客户端**（即旧版本）；A/B 更新由**运行中的旧系统**写对侧分区 —— 与 CCEP「端侧在旧通道上收到完整迭代信息并验证，才切换」同构。
- **对不上的那半条 = 「走旧通道」**：上述机制的更新**走的是一条与被升级对象解耦的稳定外部通道**（更新服务器 / OTA 服务器 / 另一分区），**不要求「用旧通道搬运新版本」**。
- CCEP 要求新迭代信息经**将被替换的那条通道本身**投递 —— ★ **这是自举（bootstrap）语义**，它使「通道自身的升级」必须由通道自己完成。

### CCEP 独有的部分

把「**通道协议升级**」也纳入被投递内容，并对投递完整性做**端侧**验证。业界规范普遍**假设控制通道版本稳定**，故未搜到以「必须走旧通道」为硬约束的成文标准。

---

## 三、原则 3 · 验证先行 ↔ CI 门禁 / readiness

**原则原文**（`:12`）：
> 任何通道变更，本地完全准备妥当（编译+测试+隔离验证）后，才投递。

### 业界对应物

1. **Kubernetes readiness probe**——容器就绪才被纳入 Service 端点接流量；另有 startup / liveness 探针区分「启动完成」与「存活」。
   来源：<https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/>（官方文档，已读取）
2. **server-side dry-run + `kubectl diff`**——K8s 官方博文原文指出本地 dry-run「不与服务端通信、不经过 validating admission controller」，故引入服务端 dry-run 做真实预校验。
   来源：<https://kubernetes.io/blog/2019/01/14/apiserver-dry-run-and-kubectl-diff/>（K8s 官方博客，已读取）
3. **GitHub required status checks**（分支保护）——未通过指定状态检查即无法合并，是 CI 门禁的成文形态。
   来源：<https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>（官方文档，已读取）
4. **Argo Rollouts**——官方文档明列原生 Deployment 滚动更新的不足：无法查询外部指标、无法自动中止与回滚。
   来源：<https://argo-rollouts.readthedocs.io/en/stable/>（官方文档，已读取）
5. **可重现构建**（「同一源码得同一产物」）——★ 这只是验证得以成立的**前提**，不是验证动作本身。
   来源：<https://glossary.openssf.org/reproducible-build/>（OpenSSF 术语表，已读取）

### ★ 等价程度：部分等价

- **关键差异在被验证对象**：readiness probe 是**运行中**的持续检查（不是投递前的一次性完整验证）；CI 门禁 / dry-run 验证的是**应用制品与配置的可应用性**。
- CCEP 原则 3 的被验证对象是**通道变更本身**，且要求「编译 + 测试 + 隔离验证」三件事在**投递之前**全部于本地完成。

### CCEP 独有的部分

**把「通信通道」当作需要过 CI 的制品。** 业界几乎没有把通道 / 传输层变更纳入构建与测试门禁的通用规范 —— K8s 侧的通道即 API server，其升级被视为**平台运维事件**而非制品门禁。

---

## 四、原则 4 · 沙箱先行 ↔ shadow / canary

**原则原文**（`:13`）：
> 任何重启和测试之前，先跑安全沙箱验证，测试没问题不报错才跑正式生产重启（沙箱验证 → 生产切换两步分离，防重蹈崩溃）。

### 业界对应物

1. **Istio traffic mirroring / shadowing**——官方原文："Mirroring sends a copy of live traffic to a mirrored service. The mirrored traffic happens **out of band of the critical request path**."
   来源：<https://istio.io/latest/docs/tasks/traffic-management/mirroring/>（官方文档，已读取）
2. **Spinnaker / Kayenta 自动化金丝雀分析**——官方定义："a change is **partially rolled out**, then evaluated against the current deployment (baseline)…"
   来源：<https://spinnaker.io/docs/guides/user/canary/canary-overview/>（官方文档，已读取）
3. **Netflix ChAP**——自动生成并执行混沌实验，对照 baseline 与 canary 指标判断系统健康。
   来源：<https://arxiv.org/abs/1905.04648>（arXiv 原始论文，已读取）

### ★ 等价程度：仅形似～部分等价

- shadow / canary / ChAP **都是生产内分流**：验证发生在**生产环境**、与真实流量**共享资源**，风险已被部分暴露（canary 判据本身就是「新的不比旧的差」，而非「先在沙箱里完全过一遍」）。
- CCEP 要求**物理分离的两步**：先沙箱（离线/隔离）验证，通过后才做生产切换 —— **顺序上不允许并行**。

### CCEP 独有的部分

① 把「**重启**」这一动作**显式纳入**「任何重启/测试前先跑沙箱」的适用范围。业界最接近的是 K8s 用 PDB 限制驱逐并发，但 PDB 是**限制影响面**，不是「先在沙箱里演练这次重启」。
② 要求沙箱与生产的**严格两步分离**，而业界主流（Istio mirroring、Kayenta）默认**在生产内**验证。

★ **关于 staging**：未取得一手权威定义（搜索结果中 staging 的解释性内容多为厂商博客，如 <https://statsig.com/perspectives/staging-environment-ci-cd-best-practices-tech>，**来源等级：博文**），★ 故**不将其列为权威对应物**。

---

## 五、原则 5 · 可回滚 ↔ rollback / GitOps revert

**原则原文**（`:14`）：
> 每次切换保留旧版本/旧配置快照，失败可秒级回滚（重启+环境变量）。

### 业界对应物

1. **`kubectl rollout undo`**——"Roll back to a previous rollout"，支持 `--to-revision` 指定历史 revision。
   来源：<https://kubernetes.io/docs/reference/kubectl/generated/kubectl_rollout/kubectl_rollout_undo/>（官方文档，已读取）
2. **`argocd app rollback`**——declarative GitOps 场景下按 History ID 回退。
   来源：<https://argo-cd.readthedocs.io/en/stable/user-guide/commands/argocd_app_rollback/>（官方文档，已读取）
3. **Immutable infrastructure（HashiCorp Well-Architected）**——"infrastructure that, once deployed, is **never modified—only replaced**"，并明确「通过重新部署上一版制品而非修复当前环境来实现回滚」。
   来源：<https://developer.hashicorp.com/well-architected-framework/define-and-automate-processes/define/immutable-infrastructure>（官方文档，已读取）
4. **Parallel Change（expand–contract，Martin Fowler）**——把破坏性变更拆成 expand / migrate / contract 三阶段，使任一阶段都可安全回退。
   来源：<https://martinfowler.com/bliki/ParallelChange.html>（Fowler 原文，已读取）

### ★★ 等价程度：应用层部分等价；★ 通道层有 nginx 一例近乎完全等价

- K8s `rollout undo` / Argo CD rollback 回退的是**应用制品与配置仓库 commit**；immutable infrastructure 回退的是**机器镜像**；Parallel Change 回退安全的是**接口/DB schema**。
- ★ **四者都不处理「回退通信通道本身」。**
- ★ **唯一接近「通道级自动回滚」的成文例子是 nginx**：官方文档原文——master 进程收到 `HUP` 时先做语法检查，*"If this fails, it **rolls back changes** and continues to work with old configuration"*。
  来源：<https://nginx.org/en/docs/control.html>（已读取）
  ⇒ ★ **这在「同一通道、单机进程级」上几乎就是 CCEP 原则 5 的原型。**

### CCEP 独有的部分

快照对象是**通道的旧版本 + 旧配置**，且要求「**秒级**」切回；同时要求**跨设备**（MBP / mac-mini / 中央实例）。★ 业界**没有**面向「多异构通道切换」的快照—回滚规范。

---

## 六、★★ 阴性证据（搜过什么、没搜到什么）

> ★ **规则**：以下「未搜到」仅表示**本轮检索**未命中 ⇒ ★ **未搜到 ≠ 不存在**。

| # | 搜过的关键词 / 面 | ★ 结果 |
|---|---|---|
| 1 | `zero downtime deployment blue-green canary` · `"at least one channel" redundant control plane` · `fallback out-of-band management channel BMC IPMI` · `graceful degradation multiple transport fallback SSE websocket long polling` · `SO_REUSEPORT` | ★ **未找到**把「任何时刻至少一条通道可用」写成**不变量（invariant）**的规范或论文；返回多为专利文本与弱相关 PDF。<br>★ `SO_REUSEPORT` **仅搜到 nginx-devel 邮件列表**（<https://mailman.nginx.org/pipermail/nginx-devel/2019-February/011856.html>，**来源等级：邮件列表**）；`socket(7)` man page（<https://manpages.debian.org/stretch/manpages/socket.7.en.html>，已读取）在本次截断范围内**未出现**该选项段落 ⇒ ★ **未据此断言** |
| 2 | `self-update` · `TUF` · `Uptane` · `Android A/B` · `ChromeOS` · `Omaha` · `"update over the old channel"` · `in-band vs out-of-band update` · `hot upgrade self-bootstrapping` | ★ **未找到**以「新版本必须经旧通道投递」为**硬约束**的标准。★ 该短语只命中专利（in-band 下载升级包）与 RFC 5776（in-band 密钥链切换），**均弱对应** |
| 3 | `progressive delivery` · `pre-flight check` · `readiness probe` · `pre-deployment validation` · `CI gate` · `reproducible builds` | ★ **未找到**「对**通道变更**做编译+测试+隔离验证」的对应规范。preflight 结果多指向具体产品文档，**非通用规范** |
| 4 | `staging environment` · `shadow traffic` · `dark launch` · `dry-run` · `canary analysis Kayenta/Spinnaker` · `Netflix ChAP` | ★ **未找到** staging 的一手权威定义（只有博文）；★ 也**未找到**把「**重启**」列为须沙箱前置动作的规范 |
| 5 | `rollback` · `GitOps revert` · `Argo CD/Flux` · `immutable infrastructure` · `database migration rollback` · `blue-green switch back` | ★ **未找到**面向「**多异构通道**」的快照与回滚规范；只有**应用 / 镜像 / 配置 / DB schema** 四个层面的回滚 |

### ★ 未能读取（如实标）

- <https://source.android.com/docs/core/ota> —— **Timeout 15s，未能读取**
- <https://source.android.com/devices/tech/ota/virtual_ab> —— **Timeout 15s，未能读取**
  ⇒ ★ A/B 更新的结论**改由 AOSP 源码树 README（第 12 号来源）支撑**，非该两页。

---

## 七、★ 本件的限制

1. ★ 本件**只做「有无对应物」的对表**，★ **不主张 ZCEP/CCEP 的正确性**、★ **不主张本机在遵守**（那在 `02`/`03`）。
2. ★ 「等价程度」栏是**本线判定**，★ **非引用业界权威的评级** —— 不得升格为「业界公认 CCEP 部分等价」。
3. ★ 检索轮次有限（7 轮），★ 覆盖面受此限；★ **阴性证据已逐条列明**供后续复核扩大搜索面。

---

*R-M3 · v7 CCEP 调研 · 01/07 · ★ 本件不主张任何 CCEP 原则已被遵守或未被遵守。*
