/**
 * index.js — dsh 插件形态（R006 ①），v1.1 含跨设备层
 * =============================================================================
 * 注册工具 `reflect_collect`：采集「当日发生的事件」→ 结构化事件流 →
 * 上传中央黑板 data/reflect/events/<device>/<date>（写入后回读校验）。
 *
 * ⑩ 在工具 schema 层的体现（Schema 门 + 类型锁）：
 *   · `sources` 的 items 是 **enum = 冻结白名单**（files/board/tools/logs/git），
 *     不存在"采集别的源"这个参数值；
 *   · **没有** `outPath` / `method` / `url` / `endpoint` / `command` 之类的入参 ——
 *     本地写入目标、HTTP 方法、上传目标在参数层无法表达（由冻结白名单与冻结构造器决定）；
 *   · `device` 是唯一可传的"key 成分"，必须过 `assertDevice`（正则 + 长度），
 *     除 key 段之外它去不了任何地方；
 *   · `dryRun: true` 时**零字节落盘、零上传**（连统一日志都不写）。
 */
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { collectAll } from './collect.js';
import { log, LOG_FILE } from './log.js';
import { packageVersion } from './version.js';
import { redactPayload, uploadEvents } from './upload.js';
import {
  SOURCE_KEYS, GATE_META, SELFCHECK_DIR, SELF_DIR, LOG_FILE as GATE_LOG_FILE,
  OUT_DIR, defaultDevice, buildUploadKey, CENTRAL_ORIGIN
} from './gate.js';

export const name = 'dsh-plugin-reflect-collect';
export const inject = ['tools'];

const HERE = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

export { packageVersion };

function makeOutput() {
  return {
    schema: {
      type: 'object',
      additionalProperties: true,
      properties: {
        // ★ 嵌套 object 必须显式写 additionalProperties（dsh-tools 的 schema 编译器要求），
        //   否则 defineTool 当场抛 JsonSchemaError: UNSUPPORTED_SCHEMA。
        //   实测：本项是被"用 mock ctx 真跑 apply()"的冒烟测试抓到的（不是靠读文档猜到的）。
        ok: { type: 'boolean' },
        window: { type: 'object', additionalProperties: true },
        device: { type: 'string' },
        hostname: { type: 'string' },
        collected_at: { type: 'string' },
        counts: { type: 'object', additionalProperties: true },
        events: { type: 'array', items: { type: 'object', additionalProperties: true } },
        errors: { type: 'array', items: { type: 'object', additionalProperties: true } },
        secrets_redacted: { type: 'integer' },
        uploadKey: { type: 'string' },
        upload: { type: 'object', additionalProperties: true },
        dryRun: { type: 'boolean' },
        outPath: { type: 'string' },
        logFile: { type: 'string' },
        sources: { type: 'array' },
        version: { type: 'string' }
      }
    }
  };
}

export function apply(ctx, config = {}) {
  // R014 自查门（apply 最前，失败不阻塞挂载）
  try {
    runSelfCheck('reflect-collect', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      peerRanges: (() => { try { return JSON.parse(fs.readFileSync(path.join(HERE, 'package.json'), 'utf8')).peerDependencies || {}; } catch { return {}; } })(),
      requiredSymbols: ['defineTool', 'collectAll'],
      sourceFiles: ['lib/index.js'],
      baseDir: HERE,
      selfcheckDir: SELFCHECK_DIR
    });
  } catch { /* 自查失败不阻塞挂载；CLI --selfcheck 会完整报出 */ }

  const configuredSources = Array.isArray(config.sources) && config.sources.length
    ? config.sources.filter((s) => SOURCE_KEYS.includes(s))
    : [...SOURCE_KEYS];
  // config 里的 device 也要过门（配置不是绕过白名单的后门）
  const configuredDevice = config.device ? defaultDevice(config.device).device : null;

  const tool = defineTool({
    name: 'reflect_collect',
    description:
      '采集「当日发生的事件」，输出结构化事件流，并上传中央黑板供「每日反思」跨设备流水线使用。' +
      '五源各自独立开关：files(当日新增/修改文件) / board(当日写过的黑板卡，只 GET) / ' +
      'tools(当日新建/修改的工具) / logs(当日 error/fail/拒绝/deny 日志行) / git(当日提交)。' +
      '**本地只读**：结构上不含写入本地被采集对象的能力（只有统一日志 + data/reflect 产出 + 自己包目录可写）。' +
      `**跨设备唯一写点**：PUT ${CENTRAL_ORIGIN}/data/reflect/events/<device>/<date>，写入后必回读校验；` +
      '本地黑板永远只读。上传前做凭据形态扫描，命中即脱敏为 [REDACTED] 并计数（secrets_redacted）。' +
      '每条事件带 ts(设备本地时间) / collected_at(采集时刻) / origin_device(采集者)。' +
      '采集失败的源不会被静默跳过，会出现在 errors[] 里。dryRun=true 时零字节落盘、零上传。',
    parameters: {
      since: { type: 'string', description: '窗口起（YYYY-MM-DD[THH:mm[:ss]]，设备本地时区；默认今天 00:00:00）' },
      until: { type: 'string', description: '窗口止（同上；默认今天 23:59:59）' },
      sources: {
        type: 'array',
        items: { type: 'string', enum: [...SOURCE_KEYS] },
        description: `采集源（枚举，白名单冻结）：${SOURCE_KEYS.join(' / ')}；省略=全部`
      },
      device: { type: 'string', description: '设备名（key 段，[a-z0-9-]{1,32}）；省略=主机名别名表命中（如 mac-mini）' },
      boardUrl: { type: 'string', description: '本机黑板地址（仅允许环回；默认 http://127.0.0.1:8792）' },
      limit: { type: 'integer', description: '每个源最多产出的事件条数（0=不限；默认 0）' },
      upload: { type: 'boolean', description: 'true=上传中央黑板（默认 true）；false=不上传' },
      dryRun: { type: 'boolean', description: 'true=只采集不落盘、不上传（零变更），事件流直接返回' }
    },
    output: makeOutput(),
    async execute(args) {
      const dryRun = args.dryRun === true;
      const doUpload = args.upload !== false && !dryRun;
      const sources = Array.isArray(args.sources) && args.sources.length ? args.sources : configuredSources;
      const dev = args.device ? defaultDevice(args.device)
        : (configuredDevice ? { device: configuredDevice, via: 'config' } : defaultDevice(os.hostname()));
      const res = await collectAll({
        since: args.since, until: args.until, sources,
        boardUrl: args.boardUrl || config.boardUrl || 'http://127.0.0.1:8792',
        limit: Number.isFinite(args.limit) ? args.limit : 0,
        dryRun, device: dev.device, pluginVersion: packageVersion()
      });
      // 凭据脱敏：本地与上传共用同一份 payload（工具入口不接受 --allow-secrets）
      const red = redactPayload(res.doc, { allowSecrets: false });
      const payloadObj = { ...red.payload, secrets_redacted: red.secrets_redacted };
      const text = JSON.stringify(payloadObj, null, 1);
      const day = res.window.since.slice(0, 10);
      const up = await uploadEvents({ device: dev.device, date: day, text, dryRun: !doUpload });
      const failed = res.errors.filter((e) => e.kind === 'collect-failed').length;
      const receipt = log('collect', {
        input: { since: res.window.since, until: res.window.until, sources, device: dev.device, via: 'plugin-tool', upload: doUpload },
        judgement: `五源采集：${Object.entries(res.counts).map(([k, v]) => `${k}=${v}`).join(' ')}；上传 ${up.attempted ? (up.ok ? 'ok+回读校验通过' : 'FAIL') : 'skipped'}`,
        result: failed || (up.attempted && !up.ok) ? 'fail' : 'success',
        diagnosis: {
          errors: res.errors.length, secrets_redacted: red.secrets_redacted,
          upload: { key: up.key, putStatus: up.putStatus ?? null, readbackStatus: up.readbackStatus ?? null, verified: up.ok === true, reason: up.reason }
        }
      }, { dryRun });
      return {
        ok: failed === 0 && (!up.attempted || up.ok),
        ...payloadObj,
        uploadKey: buildUploadKey(dev.device, day),
        upload: up,
        device: dev.device,
        dryRun,
        outPath: null,
        sources: res.sources,
        logFile: LOG_FILE,
        logPersisted: receipt.persisted === true,
        version: packageVersion(),
        gate: { principle: GATE_META.principle, writeTargets: GATE_META.writeTargets, selfDir: SELF_DIR, gateLog: GATE_LOG_FILE, outDir: OUT_DIR }
      };
    }
  });

  ctx.effect(() => ctx.tools.register(tool));
}
