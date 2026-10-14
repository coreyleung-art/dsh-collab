# 四跑法记录模板 · 鲜花垂类「全国第一」的定义

> 建立日期 2026-09-29 · 框架 runfour.py v1.0.0
> 
> ⚠️ **四跑的价值不是走流程，是「数据跑纠正了空跑的什么判断」——如果答不出这一句，说明推演没做透**

## 一、怎么用（4 步）

```bash
runfour.py init    "鲜花垂类「全国第一」的定义" --out .           # 已生成 four.json
runfour.py fill    . --run forward  --judgments forward.json
runfour.py fill    . --run reverse  --judgments reverse.json
runfour.py fill    . --run blank    --judgments blank.json
runfour.py fill    . --run data     --judgments data.json
runfour.py fill    . --run corrections --judgments corrections.json   # ★ 核心
runfour.py fill    . --run feasibility --judgments feasibility.json
runfour.py fill    . --run honesty  --judgments honesty.json
runfour.py compare . --out COMPARISON.md   # ★ 生成对比分析
runfour.py score   . --positions positions.json
```

不给 `--judgments` 时进入交互模式（逐条问答）。

## 二、四跑定义与「每跑要回答的问题」

| 跑法 | 做什么 | 关键输出 |
|---|---|---|
| **正跑 forward** | 从现状往上推：手上有什么 → 顺着现有能力能走到哪 | 下限路径 |
| **反跑 reverse** | 从目标倒推：要达成目标，前置条件是什么、分几阶段、分水岭在哪 | 前置条件清单 |
| **空数据跑 blank** | **不代入任何真实数据**，纯抽象排序：正常情况下哪些环节最关键 | 抽象基线排序 |
| **数据跑 data** | **代入已知数据**重跑，**看纠正了什么** | 校正表 |

### 1. 正跑 forward —— 从现状往上推

关键输出：**下限路径**

要回答的问题：

- [ ] 手上有什么？（能力 / 资源 / 数据 / 关系 / 资质，逐项列）
- [ ] 顺着现有能力、不追加投入，最远能走到哪一步？（这就是下限路径）
- [ ] 哪一步会卡住？卡住的直接原因是什么？
- [ ] 下限路径的终点是什么状态？（不含任何「如果融到钱 / 如果有人给」）

填法（`four.json` → `runs.forward`）：`judgments: [{"claim":"判断","basis":"依据","conclusion":"结论"}]`

### 2. 反跑 reverse —— 从目标倒推

关键输出：**前置条件清单**

要回答的问题：

- [ ] 目标是什么？（写成可判定达成与否的一句话）
- [ ] 要达成它，前置条件有哪些？（资格 / 数据 / 战绩 / 能力 / 资本，逐条列）
- [ ] 每条前置条件「怎么验证它已具备」？（verifiable 必须可观测，不能写「感觉有了」）
- [ ] 分几个阶段？每阶段拿到什么、验证什么？
- [ ] 分水岭/守门动作在哪一关？（赢下哪一关才上台阶）

填法（`four.json` → `runs.reverse`）：`prerequisites: [{"id":"P1","name":"…","desc":"…","verifiable":"…"}], phases: [{"name":"…","goal":"…","watershed":"…"}]`

### 3. 空数据跑 blank —— 不代入任何真实数据，纯抽象排序

关键输出：**抽象基线排序**

要回答的问题：

- [ ] 先把真实数字遮住：这条业务链上，正常情况下哪些环节最关键？
- [ ] 抽象（第一性）排序的前三名是谁？为什么他们最关键（讲逻辑，不讲数字）？
- [ ] 如果只能抓一个环节，抓哪个？（key_link）
- [ ] 这个排序的依据是什么？（例：缺口量级 / 不可替代性 / 行业普遍规律）

填法（`four.json` → `runs.blank`）：`ranking: [{"rank":1,"item":"环节","why":"为什么最关键"}], key_link: "最关键的单一环节"`

### 4. 数据跑 data —— 代入已知数据重跑，看纠正了什么

关键输出：**校正表**

要回答的问题：

- [ ] 代入哪些真实数据？（每个数字标注来源：回填 / 测算 / 待考证）
- [ ] 重跑后哪几个环节的排序变了？
- [ ] 空跑以为最优的，在数据下还是最优吗？有没有被反超？
- [ ] 反超的原因是什么？（给出算式与结论）

填法（`four.json` → `runs.data`）：`calculations: [{"name":"算式一","formula":"…","result":"…","implication":"…"}]`

## 三、★ 校正表（本方法的核心产出）

填 `corrections` —— **空跑以为最优的 → 数据跑反超为 → 为什么反超 → 数据依据**：

```json
{
  "corrections": [
    {
      "blank_thought": "空跑以为最优的环节",
      "data_shows": "数据跑反超为哪个环节",
      "why": "为什么反超（机制，不是复述数字）",
      "evidence": "数据依据（标明是回填还是测算）"
    }
  ]
}
```

> 填不出校正表 = 这一轮推演没做透。空跑与数据跑得出同一个排序，说明数据没带来新信息，
> 要么数据选错，要么空跑一开始就偷看了数据。

## 四、可能性评估（只给高/中/低，**不给百分比**）

```json
{
  "feasibility": [
    {
      "scope": "口径（哪个目标/哪条路径）",
      "level": "高|中|低",
      "preconditions": [
        "达到该级别的前置条件1",
        "前置条件2"
      ]
    }
  ]
}
```

## 五、诚实红线 R1-R4（不可绕过）

| 编码 | 红线 | 说明 | 本次要回答 |
|---|---|---|---|
| R1 | 分数是判断不是测量 | 六维分数 / 可能性级别都是独立分析判断，不是测量值；可讨论、可调整，不得当客观事实引用。可能性只给「高/中/低」，不给百分比。 | 本次哪些分数 / 级别只是判断？依据是什么？ |
| R2 | 测算 ≠ 验证 | 凡模型外推 / 会议口径一律标「测算」；只有真实财务 / 订单 / 回填数据才可标「已验证」。 | 本次哪些数字是测算、哪些有真实回填？ |
| R3 | 冲突要标出、来源不明要标注 | 不同版本数字打架必须点明；无公开信源的数字标「待考证 / 需补信源」。 | 本次有无打架数字 / 无源数字？标在哪一处？ |
| R4 | 不能拿「推演出来的能行」当「真的能行」 | 推演只产出假设。必须列出待真实验证项——未验证前不得对外宣称可行。 | 本次待真实验证项有哪些？谁去验、用什么数据验？ |

在 `four.json` → `honesty` 里逐个作答（R1-R4 各一段话）。**R4 必须落到「待真实验证项」清单**：

```json
{
  "honesty": {
    "R1": "…",
    "R2": "…",
    "R3": "…",
    "R4": "…"
  },
  "verify_items": [
    {
      "item": "待验证项",
      "why": "为什么必须真实验证",
      "how": "怎么验（谁/用什么数据/什么标准）"
    }
  ]
}
```

## 六、four.json 空壳结构（这就是要填的东西）

```json
{
  "topic": "鲜花垂类「全国第一」的定义",
  "created": "2026-09-29",
  "runs": {
    "forward": {
      "judgments": [],
      "summary": ""
    },
    "reverse": {
      "prerequisites": [],
      "phases": [],
      "summary": ""
    },
    "blank": {
      "ranking": [],
      "key_link": "",
      "summary": ""
    },
    "data": {
      "calculations": [],
      "summary": ""
    }
  },
  "corrections": [],
  "feasibility": [],
  "honesty": {
    "R1": "",
    "R2": "",
    "R3": "",
    "R4": ""
  },
  "verify_items": []
}
```

---

> ⚠️ **四跑的价值不是走流程，是「数据跑纠正了空跑的什么判断」——如果答不出这一句，说明推演没做透**
