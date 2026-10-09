import { runSelfCheck } from './selfcheck.js';
import { runPipeline, status } from './run.js';
import { STAGES } from './gate.js';

export const name = 'dsh-plugin-reflect';
export const inject = ['tools'];

export function apply(ctx, config = {}) {
  // ② R014 自查门：apply 最前调用
  const sc = runSelfCheck(ctx?.root || process.cwd());
  if (!sc.ok) throw new Error(`[reflect] selfcheck 未通过：${sc.missing.join('; ')}`);

  const stages = Object.freeze([...(config.stages || STAGES)]);
  const workdir = config.workdir || '~/dsh-collab/data/reflect';

  ctx.tools.register({
    name: 'reflect_run',
    description: '跑每日反思流水线（collect→dispatch→harvest→synthesize；enroll 需人裁不自动跑）',
    parameters: {
      type: 'object',
      properties: {
        date: { type: 'string', description: '日期 YYYY-MM-DD，默认今天' },
        upto: { type: 'string', enum: stages, description: '跑到哪个环节为止' },
        dry_run: { type: 'boolean', description: '只打印计划不执行' },
      },
    },
    async execute(args = {}) {
      const date = args.date || new Date().toISOString().slice(0, 10);
      const results = runPipeline({
        root: ctx.root || process.cwd(), date, workdir,
        upto: args.upto, dryRun: !!args.dry_run,
        autoRunEnroll: config.auto_run_enroll === true,
      });
      return { date, results };
    },
  });

  ctx.tools.register({
    name: 'reflect_status',
    description: '查看当日反思流水线进度（各环节是否完成）',
    parameters: { type: 'object', properties: { date: { type: 'string' } } },
    async execute(args = {}) {
      const date = args.date || new Date().toISOString().slice(0, 10);
      return { date, stages: status(date, workdir) };
    },
  });
}

export default { name, inject, apply };
