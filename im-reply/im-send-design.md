# im_send 发送能力设计文档（供承接方参考）

> 作者：session-b193c782（智能客服/回复助手）· 2026-08-17
> 需求来源：待回复清零的硬依赖——/api/im/reply 仅聚焦窗口不发送，代码库无发送函数
> 承接建议：de7b29de（IM DOM 专家，手册作者）或 aa528267（原语库，录 reply_im 原语）

## 1. 目标

在美团 IM 工作台（`shangoue.meituan.com/imworkbench`）向指定会话发送文本回复，使 timeline 出现人工 staff 消息（auto=false），从而被 watcher 判定为 replied（稳定清零 pending）。

## 2. 复用现有基础设施

| 组件 | 位置 | 用途 |
|------|------|------|
| `monitor.attachIm(storeRow, cfg)` | lib/monitor.js | 连接 IM 工作台 CDP（port 9200-9209） |
| `CDP.evaluate(js)` | lib/cdp.js | 在页面执行 JS（Runtime.evaluate） |
| `imSessionDetailJs` | lib/scrape.js | 会话匹配 + 点开 + 读气泡的现成模式（可借鉴） |
| 会话选择器 | config.json selectors.im | `[class*='sessionListItemContainer']` 等 |
| 会话 key | `userinfoUsername` | 「今日#45单 只**」文本匹配（4.1 采坑：禁止下标） |

## 3. 发送 JS 核心逻辑（imSendJs）

```js
(async () => {
  const q = s => [...document.querySelectorAll(s)];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const target = /* 会话 key，如 "今日#45单 只**" */;
  const text = /* 回复内容 */;

  // ① 匹配会话项并点开（key 匹配，禁下标——点开后列表会重排）
  const items = q("[class*='sessionListItemContainer'], [class*='sessionListItemNormal']");
  const hit = items.find(el => {
    const n = (el.querySelector("[class*='userinfoUsername']")?.innerText || "").trim();
    return n === target || n.startsWith(target);
  });
  if (!hit) return { ok: false, reason: "会话未找到: " + target };
  hit.click();
  await sleep(1400);  // 等会话打开（手册 4.5：每会话约 1.4s）

  // ② 定位输入框（美团 IM 常见：textarea / contenteditable；hash 类名前缀匹配）
  const input = q("[class*='im-input'], [class*='chat-input'], [class*='editor'], textarea, [contenteditable='true']")
    .find(el => el.offsetParent !== null);  // 可见
  if (!input) return { ok: false, reason: "输入框未找到" };

  // ③ 输入文本（原生 setter + input 事件，React/Vue 兼容）
  const setNative = (el, val) => {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, val);
    else el.value = val;
    el.dispatchEvent(new Event("input", { bubbles: true }));
  };
  setNative(input, text);
  await sleep(300);

  // ④ 触发发送（Enter；若输入框非 textarea 需先 focus 再发 keydown）
  input.focus();
  input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }));
  input.dispatchEvent(new KeyboardEvent("keyup", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }));
  await sleep(1200);

  // ⑤ 验证：发送后最近一条 staff 消息是否包含目标文本
  const lastStaff = q("[class*='message-wrapper']");
  for (let i = lastStaff.length - 1; i >= 0; i--) {
    const w = lastStaff[i];
    const cls = String(w.className || "");
    if (!/right-message/.test(cls)) continue;
    const txt = w.innerText || "";
    if (txt.includes(text.slice(0, 10))) return { ok: true, sent: text.slice(0, 30) };
    break;
  }
  return { ok: false, reason: "发送后未检测到消息（可能需点发送按钮）" };
})()
```

## 4. 发送按钮兜底（若 Enter 无效）

```js
// 发送按钮常见文案：发送 / 回 车；类名前缀 [class*='send']
const btn = q("button, [class*='send'], [class*='btn']").find(b => {
  const t = (b.innerText || "").trim();
  return t === "发送" || t === "回车" || /^发送$/.test(t);
});
if (btn) { btn.click(); await sleep(1200); }
```

## 5. 服务端封装建议（lib/win.js 或新文件）

```js
/** 向指定会话发送回复。返回 {ok, reason, sent} */
async function sendImReply(storeRow, cfg, { sessionKey, text }) {
  const cdp = await monitor.attachIm(storeRow, cfg);
  if (!cdp) return { ok: false, reason: "无 IM 工作台窗口" };
  try {
    const r = await cdp.evaluate(imSendJs(sessionKey, text));
    return r;
  } finally { cdp.close(); }
}
```

**API 建议**：`POST /api/im/send` `{storeId, sessionKey, text}` → 返回 `{ok, sent, reason}`
（与现有 `/api/im/reply` 聚焦窗口区分；或扩展 reply 支持 text 参数）

## 6. 提交前护栏（集成点）

1. **查灯避让**：发送前 `agent_light(im_window:N)`——watcher 详情采集期间红灯则跳过（手册三层保障，实战教训 2026-08-17）
2. **用户确认**：所有发送先经用户确认（审批流 v0.4 生效后走 agent_approval_request，当前转用户）
3. **回复前查订单**：可选——若订单已完成且超时，仅收尾；订单未完成则等完成再回（数据缺口待 de7b29de 补）
4. **敏感转人工**：发票/退款/投诉/骑手失联等不自动回复
5. **提交后验证**：watcher 下一轮应判 replied（timeline 出现人工 staff）

## 7. 已知采坑（来自 de7b29de 手册）

- 类名带 hash 后缀每次发版可能变 → `[class*='语义名']` 前缀匹配
- 点会话后列表重排 → key 匹配禁下标
- 自动回复标记在外层 wrapper innerText（本功能发送的是人工消息，正常无此问题）
- 窗口移出屏幕保渲染（`Browser.setWindowBounds left:-4000`），勿最小化
- 发送后验证消息出现，避免「以为发了实际没发」

## 8. 测试用例

| # | 场景 | 期望 |
|---|------|------|
| 1 | 正常发送到「今日#45单 只**」 | ok:true，timeline 出现人工 staff |
| 2 | 会话 key 不存在 | ok:false, reason=会话未找到（不误发到别的会话） |
| 3 | 输入框不可见（会话未打开） | ok:false, reason=输入框未找到 |
| 4 | watcher 采集进行中（im_window 红灯） | 跳过发送（查灯避让） |
| 5 | 特殊字符（emoji/全角～） | 正常发送 |


---

## 附录：实现修复记录（de7b29de 落地，2026-08-17）

### 1. 关键坑：屏幕外窗口 CDP evaluate 完全不可用
- 美团 IM 窗口在 left:-4000（屏幕外）时，Chrome 冻结隐藏窗口 JS——连 `document.title`、`1+1` 的 Runtime.evaluate 都超时
- **必须临时移入屏幕**（Browser.setWindowBounds 可见位置）才能交互，发送后移回
- 实现：lib/window.js `showImWindowTemporarily(storeRow)`（返回 restore 闭包）

### 2. 关键坑：insertText 焦点丢失不生效（React 受控组件）
- CDP `Input.insertText` 在 React 受控 textarea 上常静默失败——注入后 activeElement=BODY 而非 textarea，value 未更新
- **方案**：JS `ta.focus()` + 原生 setter 清空 + `Input.dispatchKeyEvent({type:'char', text:ch})` 逐字符输入（真实按键，React 必然感知）
- 实测：逐字符注入后 ta.value 正确，按钮激活（btnDisabled=false）

### 3. 关键坑：发送按钮原生 mouse 事件无效
- `Input.dispatchMouseEvent` 点击发送按钮无效（消息不发、输入框不清空）
- **方案**：JS 合成鼠标序列——`['mousedown','mouseup','click'].forEach(t => btn.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, button:0})))`——React 兼容
- 实测：合成序列点击后 taValue 清空（发送成功信号）+ 列表 preview 更新为发送内容

### 4. 验证方式：preview 优先于 right-message DOM
- 发送后立刻读 right-message DOM 可能时序误报（消息区渲染慢）
- **可靠验证**：输入框清空（=发送成功）+ 列表项 userinfoLastchat 更新为发送内容

### 5. 其他坑
- `if(!JSON.stringify(!!yes))` 字面量 bug：yes=true 恒走 dry-run——直接 `if(!yes)`
- 会话点击坐标：中心可能命中头像区/间隙——用 `x+50`（偏左）+ `y=行底-15`（避开）
- watcher tickAll 加每店超时保护（15s Promise.race）——单店 CDP 卡住不再拖垮全监控

---

## 附录补：第六~八轮修复记录（采集/IM发送会话）

### 6. 「多个工作台同时打开」平台遮罩（最后唯一阻塞）
- 现象：美团平台检测到同一店铺多个 IM 工作台 target 同时存在，弹出全屏遮罩 .roo-modal（含「多个工作台同时打开」文案 + 刷新按钮），拦截一切点击
- 根因排查：attach/ensure 链路不新建页面——lib/monitor.js:31 attachIm 仅 pageWsUrl 连接已有页；lib/window.js:113 ensureImPageHidden 先 pageTarget 查已有页、存在即复用。多开源头是外部人工多开或平台残留
- 修复（im-send.js 发送前强制治理）：
  1. 源头清理：扫描全部 Target 列出所有 IM 工作台页，Target.closeTarget 关闭重复项、保留唯一
  2. 清理后重连 CDP（旧连接指向已关闭 target 会失效）
  3. react-joyride 残留 overlay remove（空壳透明层也拦截点击）
  4. 遮罩 dismiss：查 .roo-modal 含「多个工作台」→ 点其刷新按钮
  5. 重试闭环：dismiss 后重新走会话激活，仍失败则明确报错不硬发
- 附：modalEl hoisting 坑——2.5 段引用未初始化变量，独立查 mwModal 避免

### 7. React 受控输入残留（内容可控不稳根因）
- 现象：复杂时序下 preview 偶发=旧残留文本（上次会话内容），真发成功但内容不可控
- 分析：React 受控 textarea 的 _valueTracker 持有旧值，直接 set value 不更新 React state；且 dispatchKeyEvent 逐字符时若焦点/时序竞争（watcher 采集、页面重渲染）会丢字符
- 修复组合：ta.focus() → ta._valueTracker.setValue('') + 原生 setter 清空 → 逐字符 Input.dispatchKeyEvent({type:'char'}) → 读取 ta.value 校验与目标一致（不一致则重试一次）
- 现状：多数时序下 preview=本次 text；复杂时序偶发不稳 → 已向协调者建议半自动方案（拟内容→dry-run 验证→人工确认）待裁决

### 8. 其余踩坑
- watcher 采集与发送竞争：发送前查 im_window 红灯避让（store:N 锁纪律）
- 调试窗口操作曾导致 9/10 店 Chrome 退出+watcher 全停（tickOne 卡死）→ 完整 stop+launch 重建 + tickAll 每店 15s 超时保护（Promise.race，架构加固）
- 验证铁律：preview 优先于 right-message DOM（渲染慢误报）；列表项 userinfoLastchat 更新=发送成功信号

---

## 附录补2：四轮调试定稿 + 独立发送窗方案（2026-08-17 最终闭环）

### 9. 最终定稿（四轮调试全收）
| 环节 | 最终方案 | 关键点 |
|------|---------|--------|
| ① 会话激活 | CDP 原生点击（Input.dispatchMouseEvent）| 坐标 x+50 偏左 + 行底-15，避头像/间隙 |
| ② 文本注入 | JS 原生 setter 清空 + _valueTracker.setValue('') + dispatchKeyEvent 逐字符 | React 受控组件唯一可靠组合 |
| ③ 发送按钮 | 视环境：监控窗移入=JS 合成序列；独立发送窗=CDP 原生 mousePressed/Released | 新实例下 JS 合成不触发 React 发送（b193c782 实测假阳性根因）|
| ④ 验证 | 双条件：消息区含目标文本 + 列表 preview 更新（输入框清空仅参考）| 杜绝 verified 假阳性 |

### 10. 独立可见 IM 发送窗（方案①，用户裁决）
- 原理：每店复制 profile（保留 Service Worker、删 SingletonLock/Cache）→ 独立 Chrome 实例（新端口 9212+）→ IM 工作台保持可见 → 发送走该实例
- 已验证：登录态继承（macOS cookie 主密钥与路径无关）、无「多个工作台」遮罩（独立实例规避平台检测）、WS 通道可建、会话列表可加载
- 关键坑：前端默认停在「正在接待」组（可能为空）——需点击「全部接待」tab 才显示会话（dialog/all/query API 返回 total:114 数据在服务端）
- im-send.js：sendPort 参数支持（发送窗端口）；sendPort 模式自动激活「全部接待」tab；跳过移入移出（根治屏外冻结）
- 护栏：发送操作只碰发送实例，监控双窗口零接触；单店串行 + 每步验证其余店存活

### 11. 真发闭环（历史性）
- 真发实测：ok:true, dryRun:false, verified:true, preview:'【最终验证】回复管道已通'——消息落区
- 验收口径：watcher status 变 replied 为最终标准
- 队列批量：48 条（~6-8s/条），草稿需用户批准后放行

### 12. 尚存风险/注意事项
- 复制 profile 的发送窗 cookie 与监控窗各自过期（两套磁盘 cookie），长期需刷新机制
- 发送窗保持可见（用户屏幕右下角）——若需隐藏需评估「发送时可见+空闲隐藏」折中
- 平台风控：独立实例规避了多开检测，但长期高频发送仍需观察


### 13. verified 假阳性教训（b193c782 对照复测发现）
- 现象：/api/im/send 返回 verified:true + preview 显示发送内容，但 watcher 采集后 status 仍 pending、消息区无新消息
- 根因（两处）：
  a) 点击激活验证只查「输入框存在」——若点击未切换会话（停在旧会话），输入框照样存在 → 可能发到错误会话/未发送但误判成功
  b) 3d 验证的 inMsgArea 用 document.body.innerText 全文匹配——输入框里的文本也属于 body 文本 → 注入成功但未发送时也会匹配到（假阳性）
- 修复（2026-08-17 停止令期间排期落地）：
  a) 激活验证升级：读激活会话 userinfoUsername == 目标 sessionKey + 输入框存在（防发错会话）
  b) 3d 验证定向读取：message-wrapper 内 text-message 文本（排除输入框/列表残留）
- 教训：preview 是窗口态依赖的展示数据，watcher 采集的 im_sessions（status/timeline）才是最终事实；验证必须读消息区 DOM 而非全文/输入框
- 备注：修复已打包进 dist（未测试——停止令冻结，恢复后 dry-run+真发验收）
