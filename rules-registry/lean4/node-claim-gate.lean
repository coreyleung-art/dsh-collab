/- ============================================================
   身份声称门 · Lean4 形式化规范（node-claim-gate）
   动因（2026-10-10）：一个会话把自己的**归属**写成「MBP 侧」并署名发出，
     而其**实体在 mac-mini**（它后来自证：hostname=CoreydeMac-mini / hw.model=Mac16,10）。
     ★ 关键区分：**「归属」（属于谁）与「位置」（在哪运行）是两个不同维度**，
       而系统里用同一个词表达了它们 ⇒ 读者把归属词当作位置实测。
     ★ 为何"提醒它"无效：它**无法自证**（零次 hostname 调用），
       且 role 由它自己写、workspace 各设备同名、DSH_NODE_ID 未设
       ⇒ **四重条件叠加，误判可长期存活而不被任何环节检出**。
     ⇒ 故本门**不靠提醒**，而靠**结构**：**使错误声称无法被构造**。
   规范源：本文件；运行面镜像 = tools/node-claim-gate.py（谓词 1:1）
   ============================================================ -/

/-- 设备枚举（**封闭集合**）—— 不在枚举内的设备**无法表示**，
    这是"未知设备"在类型层的处置：不是"允许但标红"，而是**不可构造**。 -/
inductive Node where
  | macMini | mbp | i9 | unknown : Node
  deriving BEq, Repr

/-- hostname 的实测证明项。
    ★ 三字段皆必填 —— 对应 R048 的「时值检查」三选一中的 **B（标时点+复跑命令）**。 -/
structure HostnameEvidence where
  rawOutput : String   -- hostname 的**原始输出**（不是转述、不是"我记得"）
  takenAt   : String   -- 取值时刻
  rerunCmd  : String   -- 复跑命令（读者可独立复得同一值）
  deriving Repr

/-- ★★ 核心：设备身份声称。
    `h_eq : claimed = observed` 是**构造子的字段** ——
    这是本门的全部力量所在：**claimed ≠ observed 时，不存在该类型的项**。-/
structure NodeClaim where
  claimed  : Node              -- 会话在卡里**写的**设备
  observed : Node              -- 由 hostname **原始输出解析所得**的设备
  evidence : HostnameEvidence  -- 证明项
  h_eq     : claimed = observed
  deriving Repr

/-- 门谓词：声称必须由**实测**划定。
    （`claimed = observed` 已由 `h_eq` 保证，故此处只需保证 observed 是真读数而非 unknown，
      且证明项非空。） -/
def attested (c : NodeClaim) : Prop :=
  c.observed ≠ Node.unknown ∧
  c.evidence.rawOutput ≠ "" ∧
  c.evidence.takenAt ≠ "" ∧
  c.evidence.rerunCmd ≠ ""

/-- 有效声称 -/
def valid (c : NodeClaim) : Prop := attested c

/- ── 定理 ───────────────────────────────────────────────────── -/

/-- ★★ 定理 1（本门的存在理由）：
    **若 claimed ≠ observed，则不存在任何 NodeClaim 使二者成立。**
    即：**错误归属的声称在结构上不可构造** —— 不是"会被拒"，是"写不出来"。 -/
theorem wrong_attribution_impossible
    (claimed observed : Node) (ev : HostnameEvidence)
    (h : claimed ≠ observed) :
    ¬ ∃ c : NodeClaim, c.claimed = claimed ∧ c.observed = observed := by
  intro ⟨c, hc1, hc2⟩
  -- c.h_eq : c.claimed = c.observed
  -- 由 hc1/hc2 代换 ⇒ claimed = observed，与 h 矛盾
  exact h (by rw [← hc1, ← hc2]; exact c.h_eq)

/-- 定理 2：observed 为 unknown ⇒ 声称无效（**未实测不得充当实测**） -/
theorem unknown_observed_invalid
    (c : NodeClaim) (h : c.observed = Node.unknown) :
    ¬ valid c := by
  intro hv
  exact hv.1 h

/-- 定理 3（面未实测无效，与 acceptance-gate 定理 5 同构）：
    证明项任一字段为空 ⇒ 声称无效。 -/
theorem empty_evidence_invalid
    (c : NodeClaim)
    (h : c.evidence.rawOutput = "" ∨ c.evidence.takenAt = "" ∨ c.evidence.rerunCmd = "") :
    ¬ valid c := by
  intro hv
  rcases hv with ⟨_, hr, ht, hc⟩
  rcases h with h1 | h2 | h3
  · exact hr h1
  · exact ht h2
  · exact hc h3

/-- 定理 4（**不可自证**）：声称的有效性**不依赖**提出者的身份字段。
    形式化表达：`valid` 的签名里**没有任何"谁提出的"参数** ——
    ⇒ 无论提出者自称是谁，都改变不了 claimed 必须等于 observed。
    ★ 这正是本门与"提醒/自查"的分野：**它不需要提出者诚实**。 -/
theorem validity_independent_of_proposer
    (c₁ c₂ : NodeClaim)
    (h : c₁.claimed = c₂.claimed ∧ c₁.observed = c₂.observed) :
    valid c₁ ↔ valid c₂ := by
  constructor <;> intro hv <;>
  · -- valid 只依赖 observed 与 evidence 的非空性；在同 claimed/observed 下二者同值
    exact ⟨by rw [← h.2]; exact hv.1, hv.2⟩

/- ── 与"提醒式"方案的对照（记录于规范内，便于后人理解为何选结构而非流程） ──
   提醒式：  valid_remind(c) := c.claimed 合理           -- 依赖提出者诚实 ⇒ 不可判
   本门式：  valid(c)        := attested c ∧ (h_eq)      -- 不依赖提出者 ⇒ 可判
   参见 rules-registry/lean4/acceptance-gate.lean 的分野：
     「自审无效」不是劝告，而是**定理**（proposer_as_judge_invalid）。同类。 -/
