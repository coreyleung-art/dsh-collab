# 部件卡 · dsh-user-questions（用户提问接缝）

> 填卡：2026-09-05 · 依据：官方 subsystems/user-questions.md
> 状态：learned（registry: user-questions）

## 1. 一句话定位
provider-neutral 词汇：tool/permission 插件需 human 回答才能继续时用它。Agent-scoped waterfall listeners 组合可用 UI surfaces(含 relay 到 connected client)。dsh-user-questions。

## 2. 概念与定义
- **AskUserQuestionOption**：{label(用户可见=也是模型面选中值), description?(UI 帮助文本)}。
- **AskUserQuestionIntent**：可选声明已知 decision kind，tagged on kind(可扩展)；不识别 tag 的 UI 渲染 generic 列表。**intent 只改呈现不改答案字段**(遵守的 UI 也发同样 labels)。'approve' 命名肯定项(不靠顺序)。ask() 拒两个类型无法携带的断言：approve 命名非本问题选项 / intent 配无 detail 的问题。
- 用途面：exit_plan_mode 呈审(plan 卡)、permission 确认等。

## 3. 作用与生命周期
tool/permission 调 ask(question+options+intent) → waterfall listeners → UI 呈现 → human 选 → 答案回调用者(继续/重试/带反馈失败)。

## 4. 约束（红线/不可违）
- option label 是模型面值——勿放机器内部码当 label。
- intent 只影响呈现：调用方按同字段读答案(UI 不认识 tag 也兼容)。

## 5. 依赖
- 被依赖 plan(exit 呈审)/approval/permission 系；依赖 waterfall listeners(UI)。

## 6. 规范要点（标准）
- 需用户抉择(风险/二选一/确认)走本接缝(本环境 ask_user_question = 界面实例);高危配 approve intent。

## 7. 关联
- 官方：user-questions.md · 工具箱：— · 路由：—
- 代码：dsh-user-questions/lib

## 8. 待补
- waterfall listener 组合(多个 UI surface)细节。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业。
