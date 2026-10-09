/**
 * index.js — dsh 插件形态（R006 ①）：注册 reflect_harvest 工具
 * =============================================================================
 * ④ reflect-harvest：每日反思流水线的「收牌」环节。
 *
 * 工具入参里**没有任何能削弱证据门的口子**：
 *   - 没有 `skipEvidence` / `force` / `lenient` / `allowMissingEvidence`；
 *   - `date` 只是选目录，改不了校验规则；
 *   - 插件 config 也影响不了门（apply 里 config 只读 includeItems）。
 * 即：schema 即门（R006 §4.1 Schema 门）——「把无证据条目当有效」不是被拒绝，而是**无法表达**。
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { harvest, formatSummary, DATE_RE, HarvestIOError } from './harvest.js';
import { LOG_FILE, DATA_DIR } from './out.js';
import { toolParameters } from './options.js';

export const name = 'dsh-plugin-reflect-harvest';
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
        agents_total: { type: 'integer' },
        agents_answered: { type: 'integer' },
        devices_total: { type: 'integer' },
        devices_submitted: { type: 'integer' },
        devices_pending: { type: 'integer' },
        pending_devices: { type: 'array' },
        per_device: { type: 'object', additionalProperties: true },
        version_drift: { type: 'object', additionalProperties: true },
        agents_declined: { type: 'integer' },
        files_rejected: { type: 'integer' },
        items_total: { type: 'integer' },
        items_valid: { type: 'integer' },
        items_rejected: { type: 'integer' },
        rejection_distribution: { type: 'object', additionalProperties: true },
        flags_distribution: { type: 'object', additionalProperties: true },
        clusters: { type: 'array' },
        rejected: { type: 'array' },
        summary: { type: 'string' },
        outputFile: { type: 'string' },
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
    runSelfCheck('dsh-plugin-reflect-harvest', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'harvest'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  // config 只能影响「回报多少」，**不能影响判定**（判定在 gate.js，config 到不了那里）
  const includeItems = config.includeItems !== false;

  const tool = defineTool({
    name: 'reflect_harvest',
    description:
      '每日反思流水线 · 收牌（④ · ★ 跨设备）：从**全部设备**收智能体回填 —— ' +
      '本机 <localRoot>/answers/<device>/<date>/（含老布局 answers/<date>/）+ 中央黑板 data/reflect/answers/<device>/<date>；' +
      '做五类校验（★ 证据完整性 / 必填字段 / suggestion.type 合法性 / related_rule 存在性 / declined 合法性），' +
      '按 (device,agent) 去重（黑板 > 本地）、跨设备聚类，并按**复现广度**（独立 <设备>:<智能体> 数）计数，' +
      '集群带 cross_device 标记；逐字相同且跨设备、时点接近的 lesson 判 possible_sync_duplicate 不重复计入；' +
      '输出按设备分组统计 + 版本漂移检查 + pending/not_dispatched 区分，产 harvested-<date>.json。' +
      '★ 质量门：**无证据的条目在结构上无法进入 valid 集合**（mintAdmitted 唯一入口，不过返回 null；buildValidSet 只收品牌化条目）。' +
      '本工具**只读黑板（只 GET，绝不 PUT/POST）**，没有写 RULES.md / 哲学库的能力，也不执行任何外部命令。',
    parameters: toolParameters(),
    output: makeOutput(),
    async execute(args) {
      const date = String(args.date);
      if (!DATE_RE.test(date)) {
        return { ok: false, date, error: 'BAD_DATE', message: `日期格式必须是 YYYY-MM-DD，收到 '${date}'`, version: VERSION };
      }
      try {
        const payload = await harvest(date, {
          dryRun: args.dryRun === true,
          devices: args.devices ? String(args.devices).split(',').map((x) => x.trim()).filter(Boolean) : undefined,
          localOnly: args.localOnly === true,
          allowLate: args.allowLate === true
        });
        const wantItems = args.includeItems === undefined ? includeItems : args.includeItems === true;
        const out = { ...payload, ok: true, dryRun: args.dryRun === true, logFile: LOG_FILE, version: VERSION };
        if (!wantItems) delete out.valid_items;
        out.summary = formatSummary(payload);
        out.outputFile = args.dryRun === true ? '(dry-run：未写入)' : path.join(DATA_DIR, `harvested-${date}.json`);
        return out;
      } catch (e) {
        if (e instanceof HarvestIOError) {
          return { ok: false, date, error: e.code, message: e.message, logFile: LOG_FILE, version: VERSION };
        }
        throw e;
      }
    }
  });

  ctx.effect(() => ctx.tools.register(tool));
}
