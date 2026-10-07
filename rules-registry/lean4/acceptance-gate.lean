/- ============================================================
   验收门 · Lean4 形式化规范（acceptance-gate）
   老板 2026-10-04 22:5x 指令：自审无效、第三方必须在场
   - 提出判据方 ≠ 裁定方；执行方 ≠ 裁定方
   - 裁定必须显式声明「只审了 X 面」
   - 自我更正同样走本门（correctionValid）
   - 本文件为规范源；运行面镜像 = tools/acceptance-gate.py（谓词 1:1）
   ============================================================ -/

abbrev Party := String

structure AcceptanceClaim where
  proposer       : Party   -- 提出判据方
  executor       : Party   -- 执行方
  adjudicator    : Party   -- 裁定方
  surfaceDeclared: Bool    -- 是否显式声明裁定面（只审了 X 面）
  surfaceMeasured: Bool    -- 裁定面是否由实测划定（v1.1.4：面附实测边界，未测项显式列举）
  verdictPass    : Bool    -- 裁定结论（true=通过；裁定必须显式存在）

/- 第三方在场：裁定方既不是提出方也不是执行方 -/
def thirdPartyPresent (c : AcceptanceClaim) : Prop :=
  c.adjudicator ≠ c.proposer ∧ c.adjudicator ≠ c.executor

/- 验收门：第三方在场 ∧ 已声明裁定面 ∧ 裁定面由实测划定 -/
def valid (c : AcceptanceClaim) : Prop :=
  thirdPartyPresent c ∧ c.surfaceDeclared = true ∧ c.surfaceMeasured = true

/- 自我更正（自审式修复）同样受本门约束 -/
def correctionValid := valid

/- 定理 1：自审无效 —— 提出方即裁定方 ⇒ 永不 valid -/
theorem proposer_as_judge_invalid (c : AcceptanceClaim)
    (h : c.adjudicator = c.proposer) :
    ¬ valid c := by
  intro hv
  exact hv.1.1 h

/- 定理 2：执行方即裁定方 ⇒ 永不 valid -/
theorem executor_as_judge_invalid (c : AcceptanceClaim)
    (h : c.adjudicator = c.executor) :
    ¬ valid c := by
  intro hv
  exact hv.1.2 h

/- 定理 3：三方合一（提出=执行=裁定）⇒ 永不 valid -/
theorem self_adjudication_invalid (c : AcceptanceClaim)
    (h : c.adjudicator = c.proposer) :
    ¬ valid c := by
  intro hv
  exact hv.1.1 h

/- 定理 4：未声明裁定面 ⇒ 永不 valid（宁要有限裁定，不要全称裁定） -/
theorem undeclared_surface_invalid (c : AcceptanceClaim)
    (h : c.surfaceDeclared = false) :
    ¬ valid c := by
  intro hv
  have absurd : true = false := h.symm.trans hv.2.1
  cases absurd

/- 定理 6（v1.1.4）：裁定面未经实测划定 ⇒ 永不 valid（范围必须由实测划定，不能由假设划定） -/
theorem unmeasured_surface_invalid (c : AcceptanceClaim)
    (h : c.surfaceMeasured = false) :
    ¬ valid c := by
  intro hv
  have absurd : true = false := h.symm.trans hv.2.2
  cases absurd

/- 定理 5（正例）：三方分明且声明面且面由实测划定 ⇒ valid -/
example :
    valid { proposer := "i9", executor := "i9",
            adjudicator := "xq", surfaceDeclared := true,
            surfaceMeasured := true, verdictPass := true } := by
  constructor
  · constructor <;> native_decide
  · rfl
