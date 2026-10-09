/**
 * smoke.js — R006 v3.1.0 ① 第 5 项：真挂载冒烟
 * =============================================================================
 * 抓的是「其它九项全绿但插件根本挂不上」。
 *
 * 做法：真实 import 插件入口 → 用**桩 ctx** 调 apply(ctx, config) → **断言注册结果**。
 * **不是**只 import（那只能证"文件能加载"，不能证"能被挂载"）。
 *
 * 三态（绝不把 skipped 写成 pass）：
 *   pass    —— 挂上且注册了预期项（须列出实际注册的工具名）
 *   fail    —— apply 抛**非依赖类**异常（这是真实缺陷，须修）
 *   skipped —— 依赖在本目录解析不到（如实说明，不判通过也不判失败）
 *
 * ★ 桩必须建模本插件实际用到的 ctx.*：ctx.root + ctx.tools（编排插件读 ctx.root 定位子插件目录）
 *   否则失败是**桩的缺口**，不是插件的问题。
 */

const inSmoke = { v: false };

export async function mountSmoke({ baseDir, indexRel = 'lib/index.js', config = {}, ctxExtra = {} } = {}) {
  // 防递归：apply() 内部会调 runSelfCheck()，若它也调本函数会无限递归
  if (inSmoke.v) return { state: 'skipped', reason: '已在冒烟中（防 apply → selfCheck → 冒烟 递归）' };
  inSmoke.v = true;
  try {
    const path = await import('node:path');
    const { pathToFileURL } = await import('node:url');
    const abs = path.default.join(baseDir, indexRel);

    let mod;
    try {
      mod = await import(pathToFileURL(abs).href);
    } catch (e) {
      const msg = String((e && e.message) || e);
      // ★ 依赖解析不到 → 如实说「跳过」
      if (/Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module/.test(msg)) {
        return { state: 'skipped', reason: msg.split('\n')[0] };
      }
      return { state: 'fail', stage: 'import', error: msg.split('\n')[0], code: (e && e.code) || null };
    }

    if (typeof mod.apply !== 'function') {
      return { state: 'fail', stage: 'shape', error: `${indexRel} 未导出 apply(ctx, config)（R006 ① 要求）` };
    }

    // ★ 桩 ctx：必须能记录副作用（注册了 0 个工具 / effect 抛错 都要被看见，不能被 catch 吞掉）
    const registered = [];
    const effects = [];
    const effectErrors = [];
    const ctx = {
      root: baseDir,                                   // reflect 编排插件用 ctx.root
      tools: { register(tool) { registered.push(tool); return () => {}; } },
      effect(fn) { effects.push(fn); try { return fn(); } catch (e) { effectErrors.push(String((e && e.message) || e)); return undefined; } },
      on() { return () => {}; },
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      ...ctxExtra,
    };

    try {
      await mod.apply(ctx, config);
    } catch (e) {
      const msg = String((e && e.message) || e);
      // ★ 星桥执行原则①：peer 解析不到 / apply 的自查门因依赖未过 → **判 skipped，不判 fail**
      //   否则会把「无宿主环境」误判成「插件挂不上」（实测 8/32 属此类误判）
      if (/Cannot find package|ERR_MODULE_NOT_FOUND|Cannot find module|selfcheck 未通过|peer/.test(msg)) {
        return { state: 'skipped', reason: `apply 因依赖/自查未过而拒绝挂载：${msg.split('\n')[0]}`, registered: registered.map((t) => t && t.name) };
      }
      return { state: 'fail', stage: 'apply', error: msg.split('\n').slice(0, 3).join(' '), code: (e && e.code) || null };
    }

    // ★ 断言：至少注册了 1 个工具（「注册了 0 个」= 挂上了但没干活）
    if (registered.length === 0) {
      return { state: 'fail', stage: 'assert', error: 'apply() 成功但注册了 0 个工具 —— 挂上了却没干活' };
    }
    if (effectErrors.length) {
      return { state: 'fail', stage: 'effect', error: `ctx.effect 内抛错：${effectErrors.join('; ')}`, registered: registered.map((t) => t && t.name) };
    }
    return { state: 'pass', tools: registered.map((t) => (t && t.name) || '(未命名)'), effects: effects.length };
  } finally {
    inSmoke.v = false;
  }
}

export function smokeRunning() { return inSmoke.v; }
