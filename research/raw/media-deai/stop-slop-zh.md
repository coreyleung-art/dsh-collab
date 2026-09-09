# stop-slop-zh

中文 AI 味清理 Codex Skill。

它不是把中文一律改成口语，也不是把文章改得更“网感”。它的目标更窄：在不改事实、不乱降格、不替作者过度发挥的前提下，去掉中文 AI 写作里最常见的套话、八股结构、金句收尾、名词化动词、抽象主语和证据越界。

适合处理公众号文章、知乎回答、产品文案、工作邮件、报告摘要、学术摘要、正式材料、创投分析和众筹表现分析。

## 它解决什么问题

中文 AI 味通常不只来自几个词，而是来自整篇文章的写法：

- 总分总八股：`首先 / 其次 / 综上所述`
- 排比三件套：`不仅是...更是...`、`是...是...更是...`
- 名词化动词：`进行优化`、`实现突破`、`提供保障`
- 抽象主语：`时代呼唤`、`科技赋能`、`市场选择`
- 金句收尾：`这就是...的力量`、`未来可期`
- 假亲切：`家人们`、`宝子们`、`谁懂啊`
- 证据越界：众筹金额被写成市场验证，理论推演被写成最终证明

这个 Skill 的重点不是“润色”，而是让文本回到具体的人、具体的事实、具体的证据边界里。

## 快速例子

改写前：

> 这一辉煌的众筹战绩成功验证了早期极客用户的买单意愿，并以极低的初期获客成本完成了品牌曝光。

改写后：

> Nimbus Sleepbuds 先后在两个海外众筹平台上线，合计获得 4,800 多名支持者和 48.2 万美元认购。这说明它在早期极客用户中有一定吸引力，也获得了初期曝光。它还不能证明大众市场需求、交付能力或主流渠道获客成本。

这段改写保留了数据，删掉了宣传腔，也没有把众筹金额推导成“市场已经验证”。

## 使用方法一：在 Codex / Vibe Coding 场景中使用

把本仓库复制到 Codex 的 Skills 目录。

Windows PowerShell：

```powershell
git clone https://github.com/y10reo/stop-slop-zh.git
Copy-Item -Recurse .\stop-slop-zh "$env:USERPROFILE\.codex\skills\stop-slop-zh"
```

macOS / Linux：

```bash
git clone https://github.com/y10reo/stop-slop-zh.git
cp -R stop-slop-zh ~/.codex/skills/stop-slop-zh
```

在 Codex 里调用：

```text
使用 $stop-slop-zh 改写这段中文文本，去掉 AI 味，保留原意、事实和场景语气。
```

也可以直接指定任务：

```text
使用 $stop-slop-zh 检查这段产品文案有没有证据越界和宣传腔。
```

## 使用方法二：在 ChatGPT 官网创建自定义 GPT

如果不使用 Codex，也可以在 ChatGPT 官网创建一个自定义 GPT 来复用这套规则。

### Instructions 放 Skill 本体

在 GPT 的 `Instructions` 中直接粘贴 `SKILL.md` 的全文。

也可以先用下面这段精简版试跑，确认风格后再替换为完整 `SKILL.md`：

```text
你是 stop-slop-zh，一个专门清理中文 AI 写作痕迹的编辑。

你的任务不是把中文改得更口语，而是在保留原意、事实、语气、场景和证据边界的前提下，去掉中文 AI 写作里常见的套话、总分总八股、排比三件套、名词化动词、抽象主语、金句收尾、假亲切和过度宣传。

处理文本时先判断场景：文章、知乎回答、小红书/抖音文案、产品文案、工作邮件、报告摘要、学术摘要、公文式材料、创投尽调、众筹分析、法律条款等。

改写时必须保留事实、数字、引用、专有名词和作者立场。不要替作者新增没有依据的结论。尤其注意证据边界：众筹金额只能说明早期支持者愿意付费，不能证明大众市场需求、产品有效、留存或盈利能力；理论推演只能提示风险，不能代替实测结论。

输出时优先给改写后的文本。必要时再用简短要点说明改动了哪些问题。
```

### Knowledge 放 reference

在 GPT 的 `Knowledge` 上传参考文件和测试案例：

```text
references/claim-boundaries.md
references/phrases.md
references/structures.md
references/scenarios.md
references/examples.md
examples/hardware-startup-due-diligence.md
```

推荐分工：

- `Instructions`：放 `SKILL.md` 本体
- `Knowledge`：放 `references/` 和 `examples/`，用于检索细分场景、禁用表达、结构模式、证据边界和案例

这样 GPT 平时按 Skill 的主流程执行，遇到复杂场景时再从 Knowledge 里检索细则。

### GPT 开场提示示例

```text
请用 stop-slop-zh 的标准改写这段中文，去掉 AI 味，保留事实、语气和场景。
```

```text
请检查这段报告有没有证据越界、宣传腔和总分总八股，先指出问题，再给一版改写。
```

## 文件结构

```text
stop-slop-zh/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── examples/
│   └── hardware-startup-due-diligence.md
└── references/
    ├── claim-boundaries.md
    ├── examples.md
    ├── phrases.md
    ├── scenarios.md
    └── structures.md
```

## 测试案例

`examples/hardware-startup-due-diligence.md` 来自一次真实压力测试。测试文本是一份中文创投课程报告，混合了产品分析、众筹解读、尽职调查、投资结论和法律条款。示例中的基金名和项目名均已替换为虚构名称。

这个案例暴露出的关键问题是“证据边界”：很多中文 AI 文本会把有限证据写成过度结论，比如把众筹金额写成市场验证，把理论模型写成最终证明，把法律条款写成风险被彻底封锁。

## 设计原则

- 主规则要短，详细规则放 `references/`
- 先判断场景，再决定改写力度
- 结构优先，词表其次
- 保留正式材料的必要语气，不强行口语化
- 清理 AI 味的同时，避免替作者说过头的话

## 借鉴来源

- hardikpandya/stop-slop
- a Chinese adaptation of humanizer-style AI writing cleanup rules

## License

MIT
