# 页面元素定制指南 · Hero（新建会话首页）

> 研究：2026-09-05 · 对象：新建会话 hero 页（大鲸鱼 + 「探索未至之境 / 预览版」）
> 归属：界面层定制（与《界面层封装与模块机制.md》配套的页面级手册）

---

## 一、目标元素与官方实现位置

| 可见元素 | 用户看到 | 官方实现 | 可改性 |
|---|---|---|---|
| 大鲸鱼图形 | 鲸鱼 logo（hover 有游泳动画） | `dsh-client-ui-conversation` HeroShell：`renderSlot("conversation.hero.brand.mark", {size:34}, {fallback: FishLogo})` | ✅ **可换**（官方预留品牌 slot） |
| 标题文字 | 「探索未至之境」 | `t("hero.headline")` = locale key（zh: 探索未至之境 / en: Into the Unknown） | ⚠️ **官方锁死**（locale 防重） |
| 预览版徽章 | 「预览版」小圆角标签 | `t("hero.preview")`（zh: 预览版 / en: Preview） | ⚠️ **官方锁死**（文字）；可 CSS 隐藏/改样式 |

**代码坐标**：`dsh-runtime/.../dsh-client-ui-conversation/lib/client.js` HeroShell（~7087-7125 行）：
```
headline(grid: 34px 鱼 | auto 标题 | auto 徽章)
├─ span.fishHitbox → renderSlot("conversation.hero.brand.mark", {size, className:"…fish"})
│     fallback: <FishLogo size=34 className=fish/>   ← 无注册时才显示大鲸鱼
├─ span.headlineText → t("hero.headline")
└─ span.previewBadge → t("hero.preview")
```

---

## 二、可改性判定与改法

### 1️⃣ 可换：鲸鱼图形（官方预留品牌点）✅
- **机制**：`conversation.hero.brand.mark` 是官方留给品牌的 slot；**有插件注册即替换鲸鱼**（fallback=FishLogo 只在无人注册时出现）。
- **改法**（client 插件，dsh-plugin-my-brand 已验证注册通路）：
  ```js
  // client.js 内（__ModuleLoader__.load factory 里, apply 阶段）
  ctx.slots.inject("conversation.hero.brand.mark", () =>
    ctx.slots.register(
      { name: "conversation.hero.brand.mark", priority: -1 },  // 覆盖官方
      MyLogo,  // 自绘组件: React.createElement, 读 props.size/className
    ));
  ```
  - 组件须：读 `props.size`（宿主传 34）自适应、带 `className`（宿主传 `…fish` 以继承 swim 动画）或自管样式
  - 返回**真实 React 元素**（React.createElement），勿手写 `{type,props}`（React #31 教训）
- **状态**：my-brand 已注册此 slot（v0.5）——当前 hero 若仍见鲸鱼=注册未覆盖成功（待实测确认渲染路径），或占位组件透明。

### 2️⃣ 锁死：标题/徽章文字（官方 i18n 设计）⚠️
- **为何锁死**（实证源码）：
  1. `ctx.locale.register(ns, dict)` 对同 ns 同 locale **重复注册直接 throw**（"already has locale"）——插件无法用官方同一 namespace 覆写；
  2. `translate(ns,key)` 查找顺序 = 本 ns → 回退 `common` → 原样 key；**common 回退只在官方本 ns 无该 key 时生效**——`hero.headline` 官方已注册，故插件往 common 塞同 key **无效**。
- **结论**：官方把 UI 文案定义为 locale-owned（AGENTS.md: Client UI copy 走 typed dictionaries + t；verify-client-ui-i18n 拒硬编码）——文案不是给第三方改的。
- **想改文字的可行路径**（权衡风险）：
  | 路径 | 做法 | 风险 |
  |---|---|---|
  | 改 runtime client.js 字典 | 直接改 `"hero.headline": "我的文案"` | 🔴 红线（runtime 包），升级被覆盖，禁止 |
  | 上游提 PR | 让官方把文案做成可配置/slot | 官方不支持则无果 |
  | 接受官方文案 | 品牌表现走鱼/logo/周边 slot | 无风险 |

### 3️⃣ 官方文字 CSS 替换（✅ 已实测 2026-09-05 v0.7）
**已验证升级**：headlineText+previewBadge 可纯 CSS **原位替换文本**——官方字 `font-size:0` 腾位 + `::after` 伪元素显示自定义文案（颜色/字重/字号显式恢复，因继承会随 font-size:0 消失）。当前: 「构建智能 · 连接思想」「Build Agents Connect Minds」。
```css
body[data-dsh-my-brand] [data-phase="hero"] [class*="headlineText"],
body[data-dsh-my-brand] [data-phase="hero"] [class*="previewBadge"]
{ visibility: hidden !important; }
```
- 选择器技巧：`[class*=子串]` 匹配 scoped hash class（headlineText/previewBadge），不依赖完整 hash；`[data-phase=hero]` 限定 hero 容器；body 标记防外泄。
- 实现位置：my-brand client.js v0.6 `injectHeroTextHideCss()`（style data-plugin-css 注入）。
- 局限：visibility 隐藏视觉（文本选中/读屏仍可读=治标）；改字无官方通道。

---

## 三、研究方法（沉淀为可复用流程）

定位"某 UI 元素能否定制"的标准三步：
```
① 定位字符串 → grep runtime client 包（中文原文必命中）→ 找到 locale key 与渲染文件
② 看渲染结构 → 读组件 JSX：元素是 slot(renderSlot) 还是直接 t()/JSX
     - 经 slot → 可 shadow/注入（查 slot 名 + priority -1 覆盖）
     - 直接 t() → locale 锁死（register 防重 + common 回退仅 key 缺失）
     - 纯 CSS → 可注入 style 改观感（不可改文本）
③ 查官方契约 → locale-owned 文案（AGENTS）不可覆写；品牌点常留 slot（如 conversation.hero.brand.mark）
```
**关键判据**：`renderSlot("X", …, {fallback: <官方默认/>})` = X 是官方预留定制点，有注册即替换默认。

---

## 四、页面元素注册表（本 hero 页）

| slot/locale | 属主 | 覆盖方式 | 现状 |
|---|---|---|---|
| conversation.hero.brand.mark | 品牌 slot | 注册组件(priority -1) | my-brand 已注册(待验证生效) |
| hero.headline (locale) | 官方文案 | 不可覆写 | 官方值 |
| hero.preview (locale) | 官方文案 | 不可覆写(可 CSS 藏) | 官方值 |
| hero.chooseWorkspace (locale) | 官方文案 | 不可覆写 | aria-label |
| conversation.session / composer / view | 结构 slot | shadow 整区 | 一般不动 |

---

## 五、结论速答
- **能不能改？** 鲸鱼 ✅（slot 官方留口）；文字 ❌（i18n 防重设计）；徽章观感部分可（CSS）。
- **怎么改鲸鱼**：改 dsh-plugin-my-brand 的 MyBrandMark → 渲染自定义 logo（读 size/className），重启 profile 生效。
- **想动文字**：无干净通道——除非接受 runtime patch（红线，不做）或等官方做成可配置。

*指南 v1 · 2026-09-05 · 与 my-brand 插件、界面层文档配套*
