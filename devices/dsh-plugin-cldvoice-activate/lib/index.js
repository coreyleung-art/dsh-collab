/**
 * index.js — dsh 插件形态（R006 ①）：注册 cldvoice_activate 工具
 * =============================================================================
 * 工具入参只有 service（enum = 冻结白名单键），**没有任何"传 label / 传 PID / 传通配"的口子**：
 * schema 即门（R006#10）——"重启框架"这件事不是被拒绝，而是无法表达。
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { activateService, serviceState, LOG_FILE, VERSION } from './activate.js';
import { ALLOWED_KEYS, GATE_META } from './gate.js';

export const name = 'dsh-plugin-cldvoice-activate';
export const inject = ['tools'];

function makeOutput() {
  return {
    schema: {
      type: 'object',
      additionalProperties: true,
      properties: {
        ok: { type: 'boolean' },
        hot: { type: 'boolean' },
        key: { type: 'string' },
        label: { type: 'string' },
        restarted: { type: 'boolean' },
        reason: { type: 'string' },
        attempts: { type: 'array' },
        diagnosis: { type: 'object', additionalProperties: true },  // ★ 嵌套 object 必须显式声明 additionalProperties，否则 defineTool 抛 UNSUPPORTED_SCHEMA → apply() 崩 → 插件挂不上（2026-09-13 由「真挂载冒烟」抓到，此前九项全绿但整包不可挂载）
        logFile: { type: 'string' },
        version: { type: 'string' }
      }
    }
  };
}

export function apply(ctx, config = {}) {
  // R014 自查门（apply 最前）
  try {
    runSelfCheck('cldvoice-activate', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'activateService'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  const allow = Array.isArray(config.allow) && config.allow.length
    ? config.allow.filter((k) => ALLOWED_KEYS.includes(k))
    : ALLOWED_KEYS;

  const tools = [
    defineTool({
      name: 'cldvoice_activate',
      description:
        'CLD-Voice 后端激活性重启：先 SIGTERM（按服务 label，非 PID）→ 等端口释放 → 再启动（不用 kickstart -k）→ 验证端口与健康端点 → 失败重试。' +
        '严格遵守 R035「能热重启的，就不要直接杀死整个框架」：本工具**没有**重启框架/按 PID 杀进程/宽杀的能力，' +
        'service 只能是白名单键之一，且若后端文件自进程启动后未变则直接判定无需重启（热生效，刷新页面即可）。',
      parameters: {
        service: {
          type: 'string',
          required: true,
          enum: [...allow],
          description: '要激活的服务（白名单枚举，无法传入其它标签或 PID）'
        },
        dryRun: { type: 'boolean', description: 'true=只返回计划，不做任何变更' },
        force: { type: 'boolean', description: 'true=跳过热重启判定，强制执行重启验证' },
        retries: { type: 'integer', description: '总尝试次数（默认 3）' },
        portWaitSeconds: { type: 'integer', description: '等端口释放上限秒数（默认 20）' }
      },
      output: makeOutput(),
      async execute(args) {
        const res = await activateService(String(args.service), {
          dryRun: args.dryRun === true,
          force: args.force === true,
          retries: args.retries,
          portWaitSeconds: args.portWaitSeconds
        });
        return { ...res, logFile: LOG_FILE, version: VERSION, gate: { allowed: allow, principle: GATE_META.principle } };
      }
    }),
    defineTool({
      name: 'cldvoice_status',
      description: '查询 CLD-Voice 后端各服务状态（launchd pid/上次退出码/端口监听/健康端点），只读，不产生任何变更。',
      parameters: {
        service: { type: 'string', enum: [...allow], description: '省略则查全部白名单服务' }
      },
      output: makeOutput(),
      async execute(args) {
        const keys = args.service ? [String(args.service)] : allow;
        const out = [];
        for (const k of keys) out.push(await serviceState(k));
        return { ok: out.every((s) => s.health && s.health.ok), services: out, logFile: LOG_FILE, version: VERSION };
      }
    })
  ];

  for (const t of tools) ctx.effect(() => ctx.tools.register(t));
}
