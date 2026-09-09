# mtm(8787) 进程内存治理方案 · Lean4 逻辑版 v1

> 设计：老登 aa528267 · 2026-09-06
> 素材：MBP 拉取资料（CLD/DSH 历史考古 M1-M6、内存崩溃实验室、资源优化 80% 报告）+ mtm 源码实测
> 原则：**不合法状态结构不可达**（不是运行时 if，是类型检查期不可能）——Lean4 纪律
> 用户约束：mtm 不做 launchd 常驻守护（常驻吃内存会拉崩 CLD 本体）

---

## 〇、Lean4 原则 → 内存治理映射

| Lean 4 概念 | mtm 内存治理对应 | 强制手段 |
|---|---|---|
| 类型即命题 | 每个内存状态迁移有精确前提，不符即拒 | chrome.js 门锁函数 |
| 全函数/穷尽匹配 | 没有"也许省也许不省"的模糊方案 | 状态机穷尽分支 |
| 构造性证明 | 不空口"应该省内存"，要实测 | 内存采样 + 断言套件 |
| 反例思维 | 先构造"什么会让它再崩"再动手 | pre-mortem 表 |
| **引用透明** | Chrome 内存行为会随版本变——改前查官方 | P0 预查门 |

## 一、目标定理（设计纲领）

```
theorem mtm_memory_governed (cfg : MTMConfig) :
  requires lifecycle_typed cfg        -- 前提① 生命周期类型锁生效
  ∧ budget_enforced cfg               -- 前提② 内存预算强制（结构层）
  ∧ lazy_materialization cfg          -- 前提③ 按需物化（尾部窗口思想）
  ∧ resident_disciplined cfg          -- 前提④ 常驻窗口 ≤ 用户授权值
  → produces (peak_mtm_mem cfg ≤ BUDGET  -- 结论 mtm 峰值内存有上界
             ∧ cld_never_oom_from_mtm)   -- 且 CLD 不会因 mtm 拉崩
```

**Lean 语义**：前提缺一 → 无法构造 `mtm_memory_governed` → "常驻吃内存方案"在类型上不存在。

## 二、现状证据（构造性：源码 + 实测）

| 事实 | 证据 | 含义 |
|---|---|---|
| 每店 = 1 独立 Chrome（profile 隔离防顶号） | lib/chrome.js launch：`--user-data-dir` + `--remote-debugging-port` | 10 店 = 10 Chrome 进程树 |
| 每 Chrome 含主进程+renderer+utility+IM 页 | launch 后 ensurePageHidden + ensureImPageHidden(美团) | 每店 ≥2 页面目标 |
| 现有护栏只在"启动前"查一次内存 | lib/chrome.js memoryPressureOk（free≥80MB 或 inactive≥1500MB） | ❌ 不防运行期累积 |
| 面板启动即拉全店 | watcher.ensureAllRunning → 全部 launch | 常驻=全量物化（M2 模式复刻） |
| 无"空闲休眠/降级"状态 | 只有 running/stopped | 无中间态 = 要么全占要么全无 |
| 用户：不做 launchd 常驻 | 2026-09-06 决策（黑板 data/ops/panel-launchd-guard-decision） | 方案必须按需 + 受控 |

**根因定位（对照 MBP 考古 M2 模式）**：mtm 的"全店常驻 Chrome" = CLD 的"多会话全量物化"同一模式——全量物化在受限环境 = OOM。CLD 用**帧索引尾部窗口**解决（768→33.9MB, 23x）；mtm 应平移该思想：**只物化活跃店窗口**。

## 三、类型锁核心设计

### 3.1 生命周期状态机（穷尽：禁止隐式态）

```lean
inductive StoreLifecycle        -- 每店生命周期（mtm 内部状态，5 态穷尽）
  | Cold      : StoreLifecycle  -- 未启动：0 进程（占 0MB）
  | Launching : StoreLifecycle  -- 拉起中：限时 25s，超时回 Cold
  | Hot       : StoreLifecycle  -- 活跃监控：受预算约束常驻
  | Warm      : StoreLifecycle  -- 低活跃：CDP 断开但 profile 保留登录态
  | Error     : StoreLifecycle  -- 异常：看门狗冷却，不回 Hot 直到人工/超时

inductive MemoryBudget          -- 预算凭证：只有预算内迁移才可构造
  | AllowHot   : Budget → Hot    -- 剩余预算 ≥ hot_cost 才允许 Hot
  | AllowWarm  : Budget → Warm   -- warm 成本低（近 0 进程）
  | Deny       : Reason → MemoryBudget  -- 预算不足：只能降级/保持

def transition (s : StoreLifecycle) (b : Budget) : Option StoreLifecycle :=
  match s with
  | Cold    => if b.room ≥ hot_cost then some Hot else some Warm
  | Warm    => if b.room ≥ hot_cost then some Hot else none
  | Hot     => if b.room < hot_cost then some Warm else none
  | Launching | Error => none   -- 非用户/看门狗驱动不可自迁
-- 类型保证：Hot 总进程的内存和 ≤ BUDGET（超 = 无法构造 transition 到 Hot）
```

**落地**：store 表加 `lifecycle` 列（cold|hot|warm|error），chrome.js 的 launch 改由 `transition` 门决定——**不是** watcher 无脑 ensureAllRunning。

### 3.2 预算参数（默认，config 可调）

| 参数 | 默认 | 依据 |
|---|---|---|
| BUDGET_TOTAL | 4GB（用户机器可调） | CLD 需留 ≥6GB，mac-mini 16-25GB |
| hot_cost/店 | 350MB（含 IM 页） | Chrome 主+renderer 实测区间（待 P0 采样校准） |
| warm_cost/店 | ~15MB | profile 保留、无进程（CDP 断开） |
| max_hot | 自动 = floor(BUDGET/hot_cost) | 结构推导而非手填 |
| 优先级 | meituan 4 店 > 其他渠道 | 预算不足时低优先降 Warm |

### 3.3 治理策略分层（对照 CLD 考古 P0-P2）

| 层 | 措施 | Lean 对应 | 预期收益 |
|---|---|---|---|
| **P0 行为治理** | ① 默认不 ensureAllRunning；面板启动只 Hot 授权店 ② `max_hot` 结构上限 ③ 用户可 `mtm launch --store X` 临时 Hot | 会话≤5 纪律平移 | 立即止血：10→4 Chrome |
| **P1 运行期护栏** | ① tick 前 vm_stat 采样：free<X 自动降 Warm 低优店 ② watcher 只 poll Hot 店 ③ Error 店冷却 60s 不回弹 | 崩溃自动重启 + 错峰 | 防运行期累积 OOM |
| **P2 惰性物化** | ① Warm 店数据 = sqlite 缓存 + 上次快照（不连 Chrome）② 需要操作/告警时才 transition→Hot ③ 历史事件尾部窗口（保留近 N 天，旧数据存档） | 帧索引尾部窗口（23x 证据） | 常驻内存 -80% 级 |

## 四、反例检查（pre-mortem：什么会让它再坏）

| 反例 | 场景 | 防线 |
|---|---|---|
| 看门狗疯拉 | Error 店 1s 后又被拉起 → 崩了拉循环 | transition Error 冷却 60s + 计数 >3 停（termination） |
| 预算竞态 | 两店同时 transition→Hot 双超 | transition 全在单线程队列（Node 单事件循环天然串行） |
| 手动 launch 绕过 | 用户 mtm launch 直调不查预算 | launch 统一走 transition 门（CLI 同入口） |
| IM 页复活 | IM 窗口看门狗把 Warm 店拉成 Hot | IM 保活仅在 Hot 店执行 |
| Chrome 后台升级 | Chrome 自更新后内存翻倍 | P0 版本预查 + hot_cost 校准任务（月度） |
| 杀掉后 profile 锁 | Warm kill 后残留锁文件 | stop 保留现有 pgrep 精确匹配 + 锁检测 |

## 五、验收（穷尽清单，全过才算证明成立）

```
M1 budget_ok:   10 店全 Hot 时结构拒绝（max_hot 生效，日志可见 Deny reason）
M2 resident_ok: 面板 idle 30min 后 4 美团店 Hot + 其余 Warm（实测进程数）
M3 peak_ok:    全天采样峰值 ≤ BUDGET_TOTAL（vm_stat + RSS 曲线）
M4 cld_ok:     CLD 进程内存不受 mtm 启动影响（基线对比 ±15%）
M5 func_ok:     新订单告警/差评观察在 Hot 店正常（回归现有采集）
M6 manual_ok:   mtm launch --store 京东店 30s 内可操作（Warm→Hot 延迟）
M7 rollback_ok: 关掉治理开关回退现行为（config governance:false）
```

## 六、落地路径（有界：3 步，每步可回滚）

1. **Step1 类型层**（改动 lib/chrome.js + lib/store.js + mtm.js）：
   - store 加 lifecycle 列；launch 前查 transition 门；watcher 只 poll Hot
   - 验证 M1/M2；回滚点=git tag memory-v1-before
2. **Step2 护栏层**（watcher.js tick 内）：
   - vm_stat 压力采样 + 自动降级 + Error 冷却
   - 验证 M3/M4/M5；回滚点=Step2 前
3. **Step3 惰性层**（数据层）：
   - Warm 店历史尾部窗口 + 事件存档
   - 验证 M6/M7 全绿 → 收尾报告

## 七、约束与保留

- **不做** launchd 常驻（用户决策，尊重）
- 面板本身（server.js Node，~150MB）可常驻或按需——由用户后续定，本方案先管 Chrome 大头
- Warm 店登录态保留依赖 profile 目录 + enable-background-mode 语义——P0 预查确认 Chrome 后台模式是否维持 cookie

---

*定理未证完之前，任何"10 店全常驻"的配置在评审中应被拒绝（unsafe 标记）。*
