# DSH 可替换元素地图 · 标准化文档

> 建立：2026-09-05 · 依据：runtime client 源码扫描 + 壳层实证（hero/标题已改）
> 用途：品牌替换(去 deepseek 化)与 UI 定制的**唯一查表**——哪些能改/在哪/怎么改/改了没
> 代码坐标基准：CLD app v0.1.1 runtime `@deepseek-ai/dsh-client-*` lib/client.js（rc.2 构建）

---

## 〇、可改判据（先判再动）

| 形态 | 判据 | 可否定制 |
|---|---|---|
| **Slot** | 源码见 `renderSlot("X", props, {fallback})` | ✅ 官方预留：注册同名牌即替换 fallback |
| **locale 文案** | 渲染处 `t("key")`，字典 `"key": "值"` | ⚠️ 官方锁死（register 防重 + common 回退仅 key 缺失）；可 CSS 隐藏 |
| **壳层(asar)** | main.js / BrowserWindow / dock | ✅ 可控（备份+gate+重签） |
| **runtime 包源码** | 直接改 dsh-* 包 | 🔴 红线：升级被覆盖 / 崩风险，禁止 |

---

## 一、A 层：壳层元素（改 app.asar main.js）——已完成 ✅

| 元素 | 位置 | 状态 | 实现 |
|---|---|---|---|
| 窗口标题(红黄绿灯旁) | BrowserWindow title | ✅ 已改 | `BRAND_TITLE` + page-title-updated preventDefault（拦 "DeepSeek Harness"） |
| 崩溃弹窗/菜单名 | APP_NAME | 用 CLD 短名 | 无需改（内部） |
| Dock 图标 | 应用图标 | ⬜ 待定 | 需 1024² 源图重建 icns（另项） |
| crashReporter productName | main.js | 已设 CLD | 无需改 |

---

## 二、B 层：Client Slot 地图（可注册 shadow 的定制点）

> 改法统一：client 插件 `ctx.slots.register({name:"X", priority:-1}, MyComp)`（priority -1 覆盖官方 fallback；组件返回 React.createElement）。

### B1 品牌位（官方 logo FishLogo 的 fallback 点——最优先替换）

| Slot | 位置 | 宿主 size | 官方 fallback | 当前状态 |
|---|---|---|---|---|
| `sidebar.brand.mark` | 侧栏顶部 logo | 24px | FishLogo | ✅ my-brand 已替换(网络节点图形 v0.9) |
| `sidebar.brand.name` | 侧栏品牌名 | — | "DSH Local Build" 文本 | ✅ my-brand 已替换(CLD+分布式智能体网络工作台 v0.15) |
| `conversation.hero.brand.mark` | hero 页大 logo | 34px | FishLogo | ✅ my-brand 已替换(网络节点图形 v0.9) |

### B2 hero 区（新建会话页）

| Slot | 用途 | 状态 |
|---|---|---|
| `conversation.hero.brand.mark` | 大 logo（B1） | ✅ |
| `conversation.hero.workspace` | 工作区选择区 | 默认在用,可 shadow |
| `conversation.hero.workspace.directoryFlow` | 目录流 | 可注入 |
| `conversation.hero.agentPreset` | agent 预设 | 可注入 |

### B3 会话视图区（一般不动,列全备查）

`conversation.session` / `conversation.session.header` / `.header.actions` / `.header.lineage` / `.header.utilities` /
`conversation.view` / `conversation.composer` / `.composer.bar` / `.composer.dock` /
`conversation.input.attachments` / `.input.dock` / `.input.left` / `.input.model` / `.input.overlay` / `.input.plan` / `.input.right` /
`conversation.message.images` / `conversation.chat.node` / `.chat.assistant-actions` / `.chat.turnTail` / `conversation.details.tool` /
`settings.general.item`(composer-enter 等) / `settings.plugin.item`

---

## 三、C 层：官方文案（locale 锁死）——处理策略:隐藏 or 接受

| key | zh | 出现区 | 状态 |
|---|---|---|---|
| `hero.headline` | 探索未至之境 | hero 标题 | ✅ 已替换「构建智能 · 连接思想」(v0.7) |
| `hero.preview` | 预览版 | hero 徽章 | ✅ 已替换「Build Agents Connect Minds」(v0.7) |
| `document.title` | DeepSeek Harness | 窗口标题 | ✅ 壳层锁定(BRAND_TITLE) |
| onboarding 文案 | DeepSeek Harness 介绍 | 设置-模型 Onboarding 对话框 | ⬜ 待定(不影响日常,如需隐藏另行) |
| settings 内 model 名 | DeepSeek-V4-Flash | 模型选择 | 是模型名非品牌,保留合理 |

**隐藏模板**（my-brand client.js 已验证）：
```css
body[data-dsh-my-brand] [data-phase="hero"] [class*="headlineText"],
body[data-dsh-my-brand] [data-phase="hero"] [class*="previewBadge"]
{ visibility: hidden !important; }
```

---

## 四、官方 logo(FishLogo) 出现点（如需全清 deepseek 图形）

`dsh-client-ui-brand-official`（官方品牌插件）/ `dsh-client-ui-sidebar` / `dsh-client-ui-conversation` / `dsh-client-ui-primitives`(定义源)。
已被 B1 slot 替换覆盖的点: 侧栏 + hero。其余(boot splash/对话框)如有再清。

---

## 五、现状核对表（2026-09-05）

| 元素 | deepseek 痕迹 | 处理 | 验证 |
|---|---|---|---|
| hero 文字 探索未至之境/预览版 | 替换标语 | ✅ v0.7 | 用户目视 构建智能·连接思想 / Build Agents Connect Minds |
| hero 大 logo | 网络节点图形 | ✅ v0.9 | 用户目视 好看 |
| 侧栏 logo | 网络节点图形 | ✅ v0.9 | 用户目视 好看 |
| 窗口标题 DeepSeek Harness | 品牌全称 | ✅ asar | osascript 实测 |
| 侧栏品牌名(sidebar.brand.name) | CLD+分布式智能体网络工作台 | ✅ v0.15 | 用户目视 合适 |
| Dock 图标 | deepseek 图 | ⬜ 待定 | — |
| onboarding 对话框 | DeepSeek 文案 | ⬜ 待定 | — |

---

## 六、改法速查

**A. 注册 slot（替换 logo/区）**：client 插件 apply 内
```js
ctx.slots.inject("sidebar.brand.mark", () =>
  ctx.slots.register({ name: "sidebar.brand.mark", priority: -1 }, MyLogo));
// MyLogo 读 props.size; 返回 React.createElement(...)
```
**B. CSS 隐藏文案**：注入 style data-plugin-css（见 §三模板）
**C. 壳层标题**：改 asar main.js BRAND_TITLE + page-title-updated 拦截（§一）

**注意**：所有 client 改动落地在插件目录(~/.dsh/plugin 或 profile symlink) → 重启 CLD 生效；asar 改动需 backup+gate+adhoc 重签。

---

## 七、研究方法（三步定位，任何"能否改"问题照此走）

```
① 找字符串 → grep runtime client 包 → 得 locale key + 文件行
② 看渲染 → renderSlot(X,{fallback})=可替换 / t("key")=锁死 / 纯CSS=可藏
③ 判归属 → slot→register shadow / locale→CSS藏 / 壳→asar / runtime→红线
```

---

*地图 v1.0 · 2026-09-05 · 与 my-brand v0.6、页面元素定制指南-Hero页.md 配套*
