# convention · j44-reuse-gate（R006 ⑤ 文档化）

> 工具：`~/dsh-collab/scripts/j44-reuse-gate.py` · 版本 `1.0.0`
> 定位：**J44「资源复用纪律」的执行门** —— 建任何新工具/脚本/机制之前，先查本机 2100+ 项已有资产。
> 本文为 R006 §2⑤ 要求的「可独立复现」文档（含退出码、达标矩阵、坑、复现命令）。

---

## ① 为什么需要（有实据）

`rules-registry/RULES.md` 里的 **J44 是 `enforced` 级规则，但长期【无执行件】** ——
即「靠人记得去查」= **纸面门**（声明了门、却没有可执行工具 ⇒ 可跳过）。

**已知事故**：本机有两个 R006 补课器（`r006-retrofit.js` / `r006-retrofit-scripts.js`）与一份
273 条合规矩阵，**均已登记在 `resource-registry.md` 里，而执行 agent 仍然找不到它们**，
靠人工考古才发现，并因此**差点新建一个已存在的机制**（`sedimentation-chain-scan.py`，2026-08-22 建）。

⇒ 该事故命中的正是 R006 §2⑧ 的反例句：**「产出只在会话里说过，落盘后无人知」**。
⇒ 本器的存在意义：把「先查存量」从**人的自觉**变成**门的拒绝**。

---

## ② 用法与退出码

```bash
# 1) 建新东西之前：查本机有没有
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --intent "我要做一个静默截断检测器"

# 2) 有命中时必须显式裁决，否则门不放行
python3 ~/dsh-collab/scripts/j44-reuse-gate.py \
    --intent "我要做一个静默截断检测器" \
    --artifact silent-truncation-lint \
    --verdict reuse --note "复用对侧同名工具的能力面"

# 3) 核验某产物是否已留痕
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --check silent-truncation-lint

# 4) 列最近裁决 / 自检 / 版本 / 机器可读
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --list
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --selftest
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --version
python3 ~/dsh-collab/scripts/j44-reuse-gate.py --json ...
```

| 退出码 | 语义 |
|---|---|
| `0` | 成功（无命中；或命中但已给出合法裁决） |
| `1` | **门不通过** —— 有命中而**未给裁决**（★ 失败即停，不退化为警告） |
| `2` | 用法或 IO 错误（未知旗标、缺必填参数） |

**裁决枚举**（`--verdict`，封闭取值集）：`reuse`（复用） · `adapt`（改造） · `no-overlap`（确无重叠）

---

## ③ R006 达标矩阵（实跑口径）

| 项 | 状态 | 证据 |
|---|---|---|
| ① 形态 | ✅ | 独立 `.py` 工具（脚本族形态），可被 `--help`/`--version` 驱动 |
| ② TCC 自检 | ✅ | `--selfcheck` 输出三段（能力清单 / 不该发生路径 / 依赖完整性）+ 9 项结构核验，`rc=0` |
| ③ CLD 自适应 | ✅ | 仅标准库；注释外无内硬编码 CLD 路径 |
| ④ dsh 版本自适应 | ✅ | 无写死的 dsh 版本字面量 |
| ⑤ 文档化 | ✅ | 本文件 |
| ⑥ 版本单一来源 | ✅ | 唯一声明 `__version__`；`--version` 从中读（本批补：原 `--version` 返回 rc=2） |
| ⑦ 统一日志 | ✅ | `~/dsh-collab/logs/j44-reuse-gate.log`；★ 本批补：原日志只在部分路径写，现**唯一出口统一留痕** |
| ⑧ 自动落链 | △ | pull 有（台账 `data/j44-reuse-ledger.json`）；push 面待定 |
| ⑨ CLI 治理 | ✅ | 未知旗标 rc=2 · `--json` 机器可读 · `--help` 自解释 · `--dry-run` 由 canonical 块接管 |
| ⑩ 约束门 | ✅ | `--lean4-check` A–F 六项全绿，含**反空洞**（扫描器先在合成恶意源上自证会红） |

---

## ④ 坑（全部有实据）

| # | 坑 | 表现 | 修法 |
|---|---|---|---|
| 1 | **`--version` 无处理器** | 声明了 `__version__` 却没有 `--version` 分支 ⇒ `rc=2`，读者无法机器可读地取版本 | 本批补：`ap.add_argument("--version", action="version", version=__version__)`，**从唯一来源读** |
| 2 | **日志死件** | 定义了 `log()` 却**没有任何调用点** ⇒ 声明了固定路径却从不留痕（≠ 达标） | 在**唯一出口**（`__main__` 守卫）统一留痕，覆盖全部 return 路径，且**留痕自身失败也留痕** |
| 3 | **本块遮蔽本器实现** | canonical 块的早期守卫（`--lean4-check`）先于 `main()` 触发，**使原写在同名函数里的 log 调用永不到达** | 块**自己**补留痕 —— 否则「修工具」会把被修物的 ⑦ 从「有」打成「死」 |
| 4 | **能力面复用而非重写** | 与 `bb-dispatch-learn.py`、黑板 `data/frameworks/dispatch-kb` 能力重叠时重复造轮子 | 本器只做**门**，检索与台账复用既有件 |

---

## ⑤ 复现命令（任何人可核）

```bash
cd ~/dsh-collab/scripts
python3 j44-reuse-gate.py --version   ; echo "rc=$?"   # 期望 0，且打印 1.0.0
python3 j44-reuse-gate.py --selftest  ; echo "rc=$?"   # 期望 0
python3 j44-reuse-gate.py --selfcheck ; echo "rc=$?"   # 期望 0，三段 + N 项核验
python3 j44-reuse-gate.py --lean4-check; echo "rc=$?"  # 期望 0，A–F 六项
python3 j44-reuse-gate.py --zzz-unknown; echo "rc=$?"  # 期望 2（参数解析严格）
tail -3 ~/dsh-collab/logs/j44-reuse-gate.log           # 期望有刚跑过的 rc 记录
```

---

## ⑥ 变更记录

- **2026-10-10（U6 批次3）**：补 `--version`（⑥）；唯一出口统一留痕（⑦）；本文件（⑤）。
  期间自查出并记录坑 #2 #3。
- 更早：见 `CHANGELOG.md`（若存在）。
