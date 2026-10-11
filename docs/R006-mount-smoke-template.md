# R006 ① 第 5 项 · 真挂载冒烟（补课模板）

> 用户 2026-09-11 裁定：**全部 32 个插件都补**。本文件是可直接抄进 `--selfcheck` 的模板，
> 以及**三态判定**的硬性要求。纠正自 R006 v3.1.0 §2 ① 第 5 项。

## 一、要做什么（一句话）
真实 `import` 插件入口 → 用**桩 ctx** 调 `apply(ctx, config)` → **断言注册结果**。
**不是**只 `import`（那只能证"文件能加载"，不能证"能被挂载"）。

## 二、模板（ESM，放进你自己的 `--selfcheck`）
```js
// 【真挂载冒烟】—— 这一项抓的是"其它九项全绿但插件根本挂不上"
let smoke = { state: 'skipped', reason: '未执行' };
try {
  const mod = await import('./lib/index.js');
  const registered = [];
  const ctx = {
    tools: { register: (t) => { registered.push(t); return () => {}; } },
    effect: (fn) => fn(),
    on: () => () => {},
    logger: { info(){}, warn(){}, error(){}, debug(){} },
    // ⚠️ 你插件实际用到的 ctx.* 都要在这里建模，否则失败是**桩的缺口**，不是插件的问题
  };
  mod.apply(ctx, { /* 你的必需 config，或用你的默认值入口 */ });
  smoke = { state: 'pass', tools: registered.map((t) => t?.name) };
} catch (e) {
  const msg = String((e && e.message) || e);
  if (/Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(msg)) {
    smoke = { state: 'skipped', reason: msg.split('\n')[0] };   // ★ 依赖解析不到 → 如实说"跳过"
  } else {
    smoke = { state: 'fail', error: msg.split('\n').slice(0, 3).join(' '), code: e && e.code };
  }
}
// 三态分开报，绝不把 skipped 写成 pass
```

## 三、三态硬性要求
| 状态 | 含义 | 允许的表述 |
|---|---|---|
| `pass` | 挂上且注册了预期项 | ✅ 挂载通过（须列出实际注册的工具名） |
| `fail` | `apply` 抛**非依赖类**异常 | ❌ 挂不上——**这是真实缺陷**，须修 |
| `skipped` | 依赖在本目录解析不到 | ⊘ 已跳过（**如实说明**，不判通过也不判失败） |

**禁止**：把 `skipped` 报成 `pass`；用 `catch {}` 吞掉异常后仍打印"通过"。

## 四、自测要求（与 ⑩ 一致）
- **正控**：改坏一个字段（如删除必需 config）→ 必须 `fail`
- **反控**：在依赖解析不到的环境跑 → 必须 `skipped`，不得 `pass`
- 两个方向都要有，否则该自检本身是"会撒谎的检查"

## 五、盘点基线（2026-09-11）
32 个真实插件中**仅 3 个已具备**：`~/dsh-plugin-openpencil` · `dsh-plugin-reflect-collect` · `dsh-plugin-reflect-dispatch`。**其余 29 个待补**（含本标准参考实现 `dsh-plugin-cldvoice-activate`）。
**归属优先**：多数插件属其它会话，由属主补，协调者不代改。
