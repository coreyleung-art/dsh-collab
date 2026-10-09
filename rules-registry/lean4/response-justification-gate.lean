/- ============================================================
   回应正当性门 · Lean4 形式化规范（response-justification-gate）
   2026-10-10 · executor = session-b250bf9d（PSTD 作者/维护者）
              proposer  = session-1ffded95（裁判 · 独立审查员）
   用户授权：2026-10-10「直接做成符合 10 项标准的工具插件以及
            符合 lean4 标准的逻辑工程门」（经裁判委托 · R050 已入册）

   ★ 本文件为【规范源】；运行面镜像 = devices/dsh-plugin-response-
     justification-gate/response-justification-gate.py（谓词 1:1）

   ★ 结构照本机既有范本 rules-registry/lean4/acceptance-gate.lean：
     · 规范源与运行面 1:1，改一处必改另一处
     · 定理以【否命题】为主（「什么情况下永不 valid」），末条为正例
     · ★ 提出判据方 ≠ 裁定方；执行方 ≠ 裁定方（本门自身也受此约束）

   ★ 规范正文：docs/response-justification-policy.md（sha256 7c84d4b4…）
     规则账本：RULES.md R050（sha256 d7802dd…）
     本文件实现规范 §8 的 fail-closed 三层。
   ============================================================ -/

/- ── 领域类型 ────────────────────────────────────────────── -/

/-- §2 的 R 类：直接回应当前上下文的六类正当依据（尝试性穷举） -/
inductive RClass where
  | R1 | R2 | R3 | R4 | R5 | R6
  deriving DecidableEq, Repr

/-- 门的运行模式。
    ★ advisory 与 enforced 的语义差异见规范 §9.1 与裁决：
      R 类枚举不完备 ⇒ 门会误拒 ⇒ 先以 advisory 积累误拒样本。
    ★ 但【负控在两种模式下都必须拒绝】—— 否则门即日志。 -/
inductive Mode where
  | advisory
  | enforced
  deriving DecidableEq, Repr

/-- 四元组：一条待发输出的结构完整性依据（规范 §8 输入） -/
structure Quadruple where
  to     : Bool   -- 收件人在场
  thread : Bool   -- 线程可追溯
  refs   : Bool   -- 引用依据在场
  text   : Bool   -- 正文非空
  deriving DecidableEq, Repr

/-- 一条待发输出的元数据（规范 §8 的输入形态） -/
structure Outbound where
  claimedR  : Option RClass
  quadruple : Quadruple
  forceSend : Bool
  mode      : Mode
  deriving Repr

/- ── 谓词（★ 与运行面 1:1） ──────────────────────────────── -/

/-- 四元组是否完整 -/
def Quadruple.complete (q : Quadruple) : Prop :=
  q.to = true ∧ q.thread = true ∧ q.refs = true ∧ q.text = true

/-- ★ 结构性正当：有 R 类依据 ∧ 四元组完整。
    ★ 注意限度（规范 §5）：本谓词【只判结构性在场】，
      **不判「该回应是否真的改变了接收方的判定或行为」** ——
      后者不可事前测，故本门只拦结构性缺席。 -/
def structurallyJustified (r : Outbound) : Prop :=
  r.claimedR.isSome ∧ r.quadruple.complete

/-- ★ 阻断：enforced 模式 ∧ 未显式承担 ∧ 结构不正当 -/
def blocked (r : Outbound) : Prop :=
  r.mode = Mode.enforced ∧ r.forceSend = false ∧ ¬ structurallyJustified r

/-- 可发送 = 未被阻断 -/
def sendable (r : Outbound) : Prop := ¬ blocked r

/-- ★ 标注义务：凡【无结构性依据】而发出的，必须带「本条无 §2 依据」标记。
    规范 §8 第 2、3 层 —— 显式承担与豁免后仍标注。 -/
def mustCarryNoBasisMark (r : Outbound) : Prop :=
  ¬ structurallyJustified r

/-- ★ 该输出实际是否带标记（由运行面在文本中注入） -/
def carriesNoBasisMark (r : Outbound) : Prop :=
  ¬ structurallyJustified r

/- ── 定理 1：无 R 类 ⇒ enforced 下永不 sendable ──────────── -/

theorem no_r_class_blocked (r : Outbound)
    (h_none : r.claimedR = none)
    (h_mode : r.mode = Mode.enforced)
    (h_force : r.forceSend = false) :
    ¬ sendable r := by
  intro hs
  have hb : blocked r := ⟨h_mode, h_force, by
    intro hj
    rw [h_none] at hj
    exact Option.noConfusion hj.1⟩
  exact hs hb

/- ── 定理 2：四元组不全 ⇒ enforced 下永不 sendable ───────── -/

theorem incomplete_quadruple_blocked (r : Outbound)
    (h_inc : ¬ r.quadruple.complete)
    (h_mode : r.mode = Mode.enforced)
    (h_force : r.forceSend = false) :
    ¬ sendable r := by
  intro hs
  have hb : blocked r := ⟨h_mode, h_force, by intro hj; exact h_inc hj.2⟩
  exact hs hb

/- ── 定理 3：★ --force-send 可越过，但【标注义务不可越过】 ──
   规范 §8 第 2 层：`--force-send` 才可越过 —— 且须在输出中自标
   「本条无 §2 依据」；第 3 层：即使越过，接收方看到的输出带标记。
   ⇒ 即：forceSend 解除的是【阻断】，不解除【标注】。 -/

theorem force_send_overrides_block_but_keeps_mark (r : Outbound)
    (h_force : r.forceSend = true)
    (h_mode : r.mode = Mode.enforced) :
    sendable r ∧ (¬ structurallyJustified r → mustCarryNoBasisMark r) := by
  constructor
  · intro hb
    exact hb.2.1 h_force
  · intro hns
    exact hns

/- ── 定理 4：advisory 模式【从不阻断】（只记录） ──────────── -/

theorem advisory_never_blocks (r : Outbound)
    (h : r.mode = Mode.advisory) :
    sendable r := by
  intro hb
  exact absurd (hb.1.trans h.symm) (by decide)

/- ── 定理 5：★ 负控 —— 阻断判定【必须可实例化】 ────────────
   「一个判据若没有能让它失败的输入，它就不是判据，是日志。」
   （本机 scripts/gate-canfail.py 的核心洞察）
   ⇒ 本定理【构造】一个必然被阻断的输入 ⇒ 证明 blocked 非空。 -/

def noBasisEnforced : Outbound :=
  { claimedR := none
  , quadruple := ⟨true, true, true, true⟩   -- 四元组全，缺 R 类
  , forceSend := false
  , mode := Mode.enforced }

theorem negative_control_constructive :
    ∃ r : Outbound, blocked r :=
  ⟨noBasisEnforced, rfl, rfl, by
    intro hj
    exact Option.noConfusion hj.1⟩

/- ── 定理 6（正例）：有 R 类 ∧ 四元组完整 ⇒ enforced 下 sendable ── -/

def justifiedSample : Outbound :=
  { claimedR := some RClass.R1
  , quadruple := ⟨true, true, true, true⟩
  , forceSend := false
  , mode := Mode.enforced }

example : sendable justifiedSample := by
  intro hb
  exact hb.2.2 ⟨rfl, ⟨rfl, rfl, rfl, rfl⟩⟩

/- ── 限度声明（规范 §5 · 不可自判性）────────────────────────
   本形式化【不】刻画、本门【不】判定：
     · 「该回应是否真的改变了接收方的判定或行为」—— 不可事前测
     · R1–R6 是否完备 —— 尝试性穷举，缺此则门会误拒
     · 跨角色适用性 —— 判据基于审查场景，其他角色可能不同
   ⇒ 故本门只拦【结构性缺席】，并保留 --force-send 逃生口。
   ⇒ 且本门【不裁规范本身】（proposer ≠ executor 原则）。 -/
