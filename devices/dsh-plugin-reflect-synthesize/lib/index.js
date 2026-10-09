/**
 * index.js — dsh 插件形态（R006 ①）：注册 reflect_synthesize 工具
 * =============================================================================
 * ⑤ reflect-synthesize：把 harvested 的 clusters 提炼成**待用户裁定的提案**。
 *
 * ★ 本工具的入参里**没有任何能写库/入册/自定义输出路径的口子**：
 *   没有 apply / enroll / writeRules / out / target …（旗标来自冻结的 lib/options.js，
 *   --lean4-check 的 B 项用**集合运算**证明这些名字一个都不存在）。
 *   即：schema 即门（R006 §4.1 Schema 门）——「替用户改哲学库」不是被拒绝，而是**无法表达**。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { synthesize, formatSummary, DATE_RE, SynthesizeIOError } from './synthesize.js';
import { LOG_FILE, DATA_DIR } from './out.js';
import { toolParameters } from './options.js';

export const name = 'dsh-plugin-reflect-synthesize';
export const inject = ['tools'];

/** ⑥ 版本单一来源：只读 package.json（不在源码里再写一份） */
export const VERSION = (() => {
  try { return JSON.parse(fs.readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version; }
  catch { return '0.0.0-unknown'; }
})();

function makeOutput() {
  return {
    schema: {
      type: 'object',
      additionalProperties: true,
      properties: {
        ok: { type: 'boolean' },
        date: { type: 'string' },
        error: { type: 'string' },
        message: { type: 'string' },
        source_file: { type: 'string' },
        output_file: { type: 'string' },
        planned_file: { type: 'string' },
        counts: { type: 'object', additionalProperties: true },
        judgment_distribution: { type: 'object', additionalProperties: true },
        category_distribution: { type: 'object', additionalProperties: true },
        items: { type: 'array' },
        stats: { type: 'object', additionalProperties: true },
        markdown: { type: 'string' },
        summary: { type: 'string' },
        dryRun: { type: 'boolean' },
        logFile: { type: 'string' },
        version: { type: 'string' }
      }
    }
  };
}

export function apply(ctx, config = {}) {
  // R014 自查门（apply 最前；失败不阻塞挂载，但会留痕到 ~/.dsh/plugin-selfcheck/）
  try {
    runSelfCheck('dsh-plugin-reflect-synthesize', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'synthesize'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  // config 只能影响「回报多少」，**影响不了判定，更影响不了写目标**（写目标在 lib/out.js 的冻结 WRITE_SPEC 里）
  const includeMarkdown = config.includeMarkdown !== false;

  const tool = defineTool({
    name: 'reflect_synthesize',
    description:
      '每日反思流水线 · 提炼（⑤）：读 harvested-<date>.json，把 clusters 提炼成**待用户裁定**的提案 proposal-<date>.md。' +
      '四步：① 对照现有库（RULES.md 规则 + governance-philosophy.json 哲学）判定 already-application / extends-existing / ' +
      'new-dimension / conflicts / unclear；② 分类归档（拟新增哲学 · 拟新增规则 · 并入补维 · 转规范 · 归档为案例 · 需裁决冲突 · 需人工复核）；' +
      '③ ★ 按 **(cross_device, recurrence) 二元组**降序排 —— 跨设备复现优先；④ 生成「看一眼就能裁」的提案。' +
      '★ 本工具是全流水线**唯一需要判断**的环节，纪律是：规则能定的用规则，**规则定不了的一律显式标 unclear 交人工/LLM 复核，不硬猜**。' +
      '★ 本工具**没有**写 RULES.md / governance-philosophy.json 的能力（无 --apply/--enroll/--out，写目标白名单里没有那些目录），入册是 ⑦ reflect-enroll 在用户裁定之后的事。',
    parameters: toolParameters(),
    output: makeOutput(),
    async execute(args) {
      const date = String(args.date);
      if (!DATE_RE.test(date)) return { ok: false, date, error: 'BAD_DATE', message: `日期格式必须是 YYYY-MM-DD，收到 '${date}'`, version: VERSION };
      try {
        const { result, markdown } = synthesize(date, { dryRun: args.dryRun === true, version: VERSION });
        const wantMd = args.includeMarkdown === undefined ? includeMarkdown : args.includeMarkdown === true;
        const out = { ...result, ok: true, dryRun: args.dryRun === true, logFile: LOG_FILE, version: VERSION };
        if (wantMd) out.markdown = markdown;
        out.summary = formatSummary(result);
        return out;
      } catch (e) {
        if (e instanceof SynthesizeIOError) return { ok: false, date, error: e.code, message: e.message, logFile: LOG_FILE, version: VERSION };
        throw e;
      }
    }
  });

  ctx.effect(() => ctx.tools.register(tool));
}
