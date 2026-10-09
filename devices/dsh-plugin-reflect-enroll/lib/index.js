/**
 * index.js — ① dsh 插件形态：注册 reflect_enroll 工具
 * =============================================================================
 * 一句话：把**用户已裁定的提案**写入哲学库/规则库，并把新规则主动反馈给所有相关智能体。
 * 它是「每日反思」流水线的**唯一写库环节**，也是数据飞轮的闭环点。
 *
 * ★ 入参里**没有** "decision"（裁定只能来自用户提供的裁定文件/单条 --rule）、
 *   **没有** "target 自由文本"（枚举）、**没有** delete/force/autoDecide 之类的口子。
 *   "自动决定入册什么 / 删除条目 / 重复入册"这三件事不是被拒绝，而是**无法表达**（R006 ⑩）。
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { runPipeline } from './pipeline.js';
import { DECISIONS, TARGETS, GATE_META } from './gate.js';
import { VERSION } from './version.js';
import { log, logFile } from './log.js';

export const name = 'dsh-plugin-reflect-enroll';
export const inject = ['tools'];

const HERE = path.dirname(fileURLToPath(import.meta.url));

function makeOutput() {
  return {
    schema: {
      type: 'object',
      additionalProperties: true,
      properties: {
        ok: { type: 'boolean' },
        dryRun: { type: 'boolean' },
        date: { type: 'string' },
        root: { type: 'string' },
        results: { type: 'array' },
        feedback: { type: 'object', additionalProperties: true },
        related: { type: 'object', additionalProperties: true },
        gate: { type: 'object', additionalProperties: true },
        logFile: { type: 'string' },
        version: { type: 'string' }
      }
    }
  };
}

export function apply(ctx, config = {}) {
  // R014 自查门（apply 最前）
  try {
    runSelfCheck('reflect-enroll', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'runPipeline'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(HERE, '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  const targets = Array.isArray(config.targets) && config.targets.length
    ? config.targets.filter((t) => TARGETS.includes(t))
    : TARGETS;
  const decisions = Array.isArray(config.decisions) && config.decisions.length
    ? config.decisions.filter((d) => DECISIONS.includes(d))
    : DECISIONS;

  ctx.effect(() => ctx.tools.register(defineTool({
    name: 'reflect_enroll',
    description:
      '反思入册·反馈闭环：把**用户已裁定的提案**写入治理哲学库/规则库（或转 SOP / 只归档），' +
      '并把新规则/哲学生成反馈卡、写**本机+中央**黑板（规则变更通知卡全设备可检索）、按需推送给相关智能体（含其他设备：<device>:<agent>，走中央黑板待投递队列，离线也能收到）。' +
      '严格遵守 phi-user-sovereignty：**本工具绝不自行决定入册什么** —— 必须由人给出裁定' +
      `（裁定文件 ruling-<date>.json 或单条 rule=<提案id>=<${decisions.join('|')}>:<${targets.join('|')}>）。` +
      '结构上不存在的能力：删除任何条目、重复入册、写坏目标文件（备份前置 + .tmp 原子写 + 回读校验 + 失败自动回滚）。',
    parameters: {
      rulingFile: { type: 'string', description: '裁定文件路径（省略则读 <root>/data/reflect/ruling-<date>.json）' },
      rule: { type: 'string', description: `单条裁定，形如 P1=approve:philosophy（decision ∈ ${decisions.join('|')}，target ∈ ${targets.join('|')}）` },
      proposalFile: { type: 'string', description: '提案正本文件（省略则读 <root>/data/reflect/proposals-<date>.json）——工具绝不自行编造入册内容' },
      date: { type: 'string', description: 'YYYY-MM-DD（默认今天；决定 rulings/proposals/反馈卡/归档的文件名）' },
      dryRun: { type: 'boolean', description: 'true=只出计划，**一个字节都不写**（含备份、台账、反馈卡、黑板）' },
      notify: { type: 'boolean', description: 'true=对相关智能体推送短消息（正文≤50字「看黑板 <key>」，先落黑板再发）' },
      noBb: { type: 'boolean', description: 'true=跳过黑板写入与推送（反馈卡仍落盘）' },
      localBb: { type: 'string', description: '本机黑板地址（默认 config.bbUrl / http://127.0.0.1:8792）' },
      device: { type: 'string', description: '本机设备名（<device> 段，如 mac-mini/mbp/i9；默认 $DSH_NODE_ID → 主机名匹配设备登记表）' },
      centralBb: { type: 'string', description: '中央黑板地址（默认 http://106.53.214.108:8792；跨设备汇聚点，必须过主机白名单）' },
      root: { type: 'string', description: '协作根目录（默认 ~/dsh-collab；自测/沙箱用）' }
    },
    output: makeOutput(),
    async execute(args) {
      const res = await runPipeline({
        root: args.root,
        rulingFile: args.rulingFile,
        ruleSpec: args.rule,
        proposalFile: args.proposalFile,
        date: args.date,
        dryRun: args.dryRun === true,
        notify: args.notify === true,
        noBb: args.noBb === true,
        localBb: args.localBb || config.bbUrl,
        centralBb: args.centralBb || config.centralBb,
        device: args.device
      });
      return {
        ok: res.ok, dryRun: res.dryRun, date: res.date, root: res.root,
        results: res.results, feedback: res.feedback, related: res.related,
        gate: { decisions, targets, principle: GATE_META.principle, noAutoDecide: GATE_META.noAutoDecide, noDelete: GATE_META.noDelete },
        logFile: logFile(), version: VERSION
      };
    }
  })));

  log('plugin.applied', { input: { config: { targets, decisions } }, result: { ok: true, inject } });
}
