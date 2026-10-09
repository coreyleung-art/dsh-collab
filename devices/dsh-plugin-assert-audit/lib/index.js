/**
 * index.js — dsh 插件形态（R006 ①）：注册 assert_audit 工具
 *
 * 入参设计即门（⑩ Schema 门）：
 *   · verdict 是**输出**，不是输入 —— 调用方无法指定判定
 *   · runner 只能是 ['python3','node'] 的成员
 *   · mutants 的每次替换在实现内做**锚点唯一性**校验（≠1 即判不可判）
 * 嵌套 object 一律显式声明 additionalProperties（2026-09-13 UNSUPPORTED_SCHEMA 教训）
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { audit } from './audit.js';
import { ALLOWED_COMMANDS, VERDICT_VALUES, GATE_META } from './gate.js';

export const name = 'dsh-plugin-assert-audit';
export const inject = ['tools'];
const VERSION = '1.0.0';

function outSchema() {
  return {
    schema: {
      type: 'object',
      additionalProperties: false,
      properties: {
        ok: { type: 'boolean' },
        assertions: { type: 'integer' },
        vacuity: { type: 'array', items: { type: 'object', additionalProperties: true } },
        predicates: { type: 'array', items: { type: 'object', additionalProperties: true } },
        mutation: { type: 'object', additionalProperties: true },
        gate: { type: 'object', additionalProperties: true },
        notes: { type: 'array', items: { type: 'string' } },
      },
    },
  };
}

export function apply(ctx, config = {}) {
  try {
    runSelfCheck('assert-audit', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'audit'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..'),
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  const runners = Array.isArray(config.allowedRunners) && config.allowedRunners.length
    ? config.allowedRunners.filter((r) => ALLOWED_COMMANDS.includes(r))
    : [...ALLOWED_COMMANDS];

  const tools = [
    defineTool({
      name: 'assert_audit',
      description:
        '审计一个断言套件：枚举断言 → 检测恒真/探针型/弱比较 → 检查「同谓词多调用点只覆盖一个」→ 跑变异测试并给出三态判定（CAUGHT/SURVIVED/INCONCLUSIVE）。'
        + '结构性保证：变异体自身崩溃或语法错一律判 INCONCLUSIVE，绝不冒充 CAUGHT 或 SURVIVED；锚点出现次数不为 1 时拒绝替换；只读被测源，只写 os.tmpdir()。'
        + `判定闭集：${VERDICT_VALUES.join(' / ')}。`,
      parameters: {
        // ★ 形态对齐参考实现：parameters 直接就是 properties 表（不包 {type:'object',properties}）
        //   初版包了一层 → defineTool 抛「parameters.type must be a value schema object」→ apply() 崩
        //   ⇒ 由 ①第5项 真挂载冒烟抓到（这正是该项存在的理由）
        sourcePath: { type: 'string', required: true, description: '被测实现源码路径（只读）' },
        testSourcePath: { type: 'string', required: true, description: '断言套件源码路径（只读）' },
        tokens: { type: 'array', items: { type: 'string' }, description: '额外的谓词片段，用于多调用点覆盖检查' },
        runArgs: { type: 'array', items: { type: 'string' }, description: '运行套件的参数，如 ["selftest"]' },
        runner: { type: 'string', enum: [...runners], description: '执行器（白名单内）' },
        mutants: {
          type: 'array',
          description: '变异体列表；锚点必须在源文件中恰好出现 1 次',
          items: {
            type: 'object',
            additionalProperties: false,                              // ★ 嵌套 object 必须显式声明（2026-09-13 UNSUPPORTED_SCHEMA 教训）
            properties: {
              name: { type: 'string' },
              old: { type: 'string' },
              new: { type: 'string' },
            },
          },
        },
      },
      output: outSchema(),
      async execute(args) {
        const r = audit({
          sourcePath: args.sourcePath,
          testSourcePath: args.testSourcePath,
          tokens: args.tokens || [],
          mutants: args.mutants || [],
          runArgs: args.runArgs || [],
          runner: args.runner || 'python3',
        });
        return {
          ok: (r.mutation ? r.mutation.tally.SURVIVED === 0 && r.mutation.consistent : true)
              && r.vacuity.length === 0,
          assertions: r.assertions.length,
          vacuity: r.vacuity,
          predicates: r.predicates.filter((p) => p.verdict !== 'OK'),
          mutation: r.mutation,
          gate: GATE_META,
          notes: [`判定闭集：${VERDICT_VALUES.join('/')}`, 'INCONCLUSIVE 不折算为任何一侧'],
        };
      },
    }),
  ];

  for (const t of tools) ctx.tools.register(t);
  return () => { /* ctx.effect 回收：本插件无定时器/监听，注册随 Fiber 释放 */ };
}

export { VERSION };
