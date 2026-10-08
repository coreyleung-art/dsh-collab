/- ============================================================
   自述门 · Lean4 形式化规范（self-report-gate · R-SR 自述可证性）
   业主 2026-10-09：要「类似 Lean4 逻辑结构门」——不靠上下文自证，靠机器取值
   - ★ 我只许写「命令 + 期望」，**不许写值**：切断「记忆 → 报告」这条通道
   - 五类陈述各一条断言：SR1 现场重测 / SR2 阳性对照 / SR3 撤回传播 /
                        SR4 写盘自证 / SR5 环境指纹
   - 每条断言必带事故来源（**不许凭空设计**）——见各行 source 注释
   - 本文件为规范源；运行面镜像 = scripts/self-report-gate.py（谓词 1:1）
     ⇒ 对照方式：本文件 def 名 sr1..sr5 ↔ Python ASSERTIONS 表的 5 个函数

   补逻辑（2026-10-09，**全部来自当天真实事故，非推演**）：
     · 报 `audit 46,111`（实测 24,382，且 1 小时内又涨到 25,345）⇒ SR1
     · 报 `writer 非空 = 0` 而实际存在非空值 ⇒ SR2（同源两次假否定）
     · 表述里仍用已被作者撤回的 `standard.js` 限定词 ⇒ SR3
     · 报「本轮未写盘」而磁盘上有 2 个文件 ⇒ SR4
     · 一对 `std` 读数跨了**两个**进程边界（3901→50425→35869）⇒ SR5

   编号迁移表：本文件 v1（2026-10-09 首版）**无重编号**，编号即终版。
     ★ 沿用 acceptance-gate.lean 的纪律：日后若重编号，必须在此登记新旧对照，
       并注明「互换型重编号下区间会碎裂」（裁判 2026-10-08 指出），历史卡不重写。

   约束使用对象（scope，先定对象再定工具）：
     主体 = agent 会话（首发：session-1ffded95）
     产物 = **落盘前**的自述性陈述（报告 / 板卡 / 声明 JSON）
     不管 = 业务断言（rule-judge L2）· 源码引用失效（citation-stale-check）·
            卡片否定面 lint（absence-claim-lint）· 验收「通过」裁定（R046）
   ============================================================ -/

-- 五类陈述（与 Python 的 kind 字段一一对应）
inductive Kind where
  | number    -- 数字类：声称了一个值
  | negative  -- 否定类：不存在 / 零 / 未找到
  | ref       -- 引用类：引用了某判据
  | write     -- 写盘类：我做了/我没做
  | env       -- 环境类：运行态（版本 / 在役 / 加载态）
  deriving DecidableEq, Repr

structure SelfReportClaim where
  id            : String
  kind          : Kind
  cmd           : Option String   -- 取值命令（number/negative 必填）
  reported      : Option Nat      -- 我只许写「声称值」，真值由门跑出
  positiveCtrl  : Option String   -- 否定类必填：同载体上**必然命中**的对照
  refs          : List String     -- 引用类：被引判据 id
  rereadAfterRetraction : Bool    -- 引用命中撤回清单后是否已按撤回后口径重读
  scanDirs      : List String     -- 写盘类：扫描目录
  since         : Option String   -- 写盘类：窗口起点
  expectPid     : Option String   -- 环境类：载体 pid
  expectLstart  : Option String   -- 环境类：载体 lstart（可选）

/-- 运行面注入的取值通道。★ 这五个函数由运行面提供真实现（跑命令/查进程），
    规范层只声明它们的签名 ⇒ 谓词与实现因此可逐条对照。 -/
structure Runtime where
  runCmd      : String → Nat              -- 跑命令取数字
  hits        : String → Nat              -- 跑命令取命中数
  isRetracted : String → Bool             -- 查撤回清单
  scanWindow  : List String → String → Nat -- 扫目录窗口内的新写入数
  alive       : String → Option String    -- 查进程（pid → 存在则给 lstart）

/-- SR1 现场重测：声称为 0 值必须由现场取值支撑；缺 cmd ⇒ fail-closed。
     source: 2026-10-09 audit 46,111 事件 -/
def sr1 (r : Runtime) (c : SelfReportClaim) : Bool :=
  match c.cmd, c.reported with
  | none,     _      => false              -- ★ 缺 cmd 即拒（不许凭记忆写值）
  | some _,   none   => true               -- 无声称值 ⇒ 只取值，不比对
  | some cmd, some n => r.runCmd cmd == n

/-- SR2 阳性对照：对照 0 命中 ⇒ **载体失效 ⇒ 否定不成立**（不是「没有」，是「测不到」）。
    source: 同日两次假否定（端点猜错 / 中文被 shell 吃掉） -/
def sr2 (r : Runtime) (c : SelfReportClaim) : Bool :=
  match c.cmd, c.positiveCtrl with
  | some probe, some ctrl => (r.hits ctrl) > 0 && (r.hits probe) == 0
  | _,          _         => false         -- ★ 否定类缺对照即拒

/-- SR3 撤回传播：引用命中撤回清单且未标注重读 ⇒ 拒。
    source: standard.js 更窄条件被作者撤回后仍被引用 -/
def sr3 (r : Runtime) (c : SelfReportClaim) : Bool :=
  if c.refs.any r.isRetracted then c.rereadAfterRetraction else true

/-- SR4 写盘自证：声称未写盘 ⇒ 门亲自扫 mtime；窗口内有写入即拒。
    source: 「本轮未写盘」而磁盘上有 2 个文件 -/
def sr4 (r : Runtime) (c : SelfReportClaim) : Bool :=
  match c.since with
  | none        => false                   -- ★ 无窗口即拒
  | some since  => r.scanWindow c.scanDirs since == 0

/-- SR5 环境指纹：载体不存在 ⇒ 该读数跨了进程边界 ⇒ 拒。
    source: 一对 std 读数跨两个进程边界（3901→50425→35869） -/
def sr5 (r : Runtime) (c : SelfReportClaim) : Bool :=
  match c.expectPid, c.alive c.expectPid.getD "" with
  | none,        _            => false     -- ★ 无指纹即拒
  | some _,      none         => false     -- 载体已换
  | some _,      some actual  =>
      match c.expectLstart with
      | none        => true                -- 只核存在性
      | some want   => want == actual

/-- 门：按 kind 分派；任一断言不成立即拒（fail-closed）。 -/
def gateValid (r : Runtime) (c : SelfReportClaim) : Bool :=
  match c.kind with
  | .number   => sr1 r c
  | .negative => sr2 r c
  | .ref      => sr3 r c
  | .write    => sr4 r c
  | .env      => sr5 r c

/- ───────── 定理（每条断言不成立 ⇒ 门拒） ───────── -/

/-- 定理 1：缺 cmd 的数字类自述 ⇒ 永不通过（禁止凭记忆写值） -/
theorem missing_cmd_invalid (r : Runtime) (c : SelfReportClaim)
    (h : c.cmd = none) (hk : c.kind = .number) :
    gateValid r c = false := by
  simp [gateValid, hk, sr1, h]

/-- 定理 2：阳性对照 0 命中 ⇒ 载体失效 ⇒ 否定不成立（防假否定） -/
theorem dead_carrier_negation_invalid (r : Runtime) (c : SelfReportClaim)
    (probe ctrl : String)
    (hp : c.cmd = some probe) (hc : c.positiveCtrl = some ctrl)
    (hdead : r.hits ctrl = 0) (hk : c.kind = .negative) :
    gateValid r c = false := by
  simp [gateValid, hk, sr2, hp, hc, hdead]

/-- 定理 3：引用已撤回判据且未重读 ⇒ 永不通过 -/
theorem stale_reference_invalid (r : Runtime) (c : SelfReportClaim)
    (u : String) (hu : c.refs = [u])
    (hre : r.isRetracted u = true) (hnr : c.rereadAfterRetraction = false)
    (hk : c.kind = .ref) :
    gateValid r c = false := by
  simp [gateValid, hk, sr3, hu, hre, hnr]

/-- 定理 4：窗口内有写入却说未写盘 ⇒ 永不通过 -/
theorem false_no_write_invalid (r : Runtime) (c : SelfReportClaim)
    (s : String) (hs : c.since = some s) (hn : r.scanWindow c.scanDirs s ≠ 0)
    (hk : c.kind = .write) :
    gateValid r c = false := by
  simp [gateValid, hk, sr4, hs]
  exact hn

/-- 定理 5：载体不存在（读数跨进程边界）⇒ 永不通过 -/
theorem stale_carrier_env_invalid (r : Runtime) (c : SelfReportClaim)
    (p : String) (hp : c.expectPid = some p) (hgone : r.alive p = none)
    (hk : c.kind = .env) :
    gateValid r c = false := by
  simp [gateValid, hk, sr5, hp, hgone]

/-- 定理 6（正例）：五断言各自成立 ⇒ 门通过。
    ★ 正例必须存在（否则门可能恒 false 而看起来"很严"）。 -/
theorem valid_example :
    gateValid
      { runCmd := fun _ => 5, hits := fun s => if s == "ctrl" then 3 else 0,
        isRetracted := fun _ => false,
        scanWindow := fun _ _ => 0, alive := fun _ => some "L" }
      { id := "ok", kind := .number, cmd := some "echo 5", reported := some 5,
        positiveCtrl := none, refs := [], rereadAfterRetraction := false,
        scanDirs := [], since := none, expectPid := none, expectLstart := none }
    = true := by
  simp [gateValid, sr1]
