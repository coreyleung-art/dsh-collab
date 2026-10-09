/**
 * index.js — dsh 插件形态（R006 ①）：注册 reflect_dispatch / reflect_targets / reflect_device_status
 * =============================================================================
 * schema 即门（R006#10 门型「类型锁」）：
 *   · 工具入参里**没有** message / text / body 之类的自由文本槽 —— "发一条长通知"无法表达；
 *     通知只能由 gate.buildNotice(boardKey) 生成（模板冻结；key 必须过
 *     `data/reflect/<cards|events|answers>/<device>/<date>` 形状门）。
 *   · 也**没有** target/all/broadcast 槽：目标只能是一个明确的智能体 id。
 *   · 设备名走 DEVICE_NAME_RE（`^[a-z][a-z0-9-]{1,15}$`）：设备是**枚举式受控值**，
 *     不是任意字符串 —— 这样"把卡写到别人的设备目录"在 schema 层就已经很别扭。
 *   agent 参数在 execute 里逐个过 gate.assertTargetExists（只抛不返回布尔 → 无法静默跳过）。
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
import { runSelfCheck } from './selfcheck.js';
import { dispatch, listTargets, VERSION, LOG_FILE } from './core.js';
import { resolveLocalDevice, computePresence, keysFor, resolveDevices } from './sources.js';
import {
  GateError, NOTICE_MAX_CHARS, SUGGESTION_TYPES, GATE_META, REFLECT_ROOT_REL,
  CANDIDATE_DEVICES, DEVICE_STATUS, ALLOWED_HOSTS
} from './gate.js';

export const name = 'dsh-plugin-reflect-dispatch';
export const inject = ['tools'];

/**
 * 输出 schema 构造器。
 * ★ 被"真挂载"抓到的 bug（2026-09-10）：嵌套对象若**不显式**写 `additionalProperties`，
 *   宿主 dsh-tools 的 JSON schema 编译会直接抛 `UNSUPPORTED_SCHEMA`
 *   （`schema.properties.late.additionalProperties must be explicitly true or false`）→
 *   **apply() 阶段崩，插件根本挂不上去**。这正是 R006 §1「插件 apply 阶段 ReferenceError，
 *   启动即崩，靠外部 restart-guard 事后发现」那一类事故。
 *   这里用 obj() 统一构造，**让漏写变得不可能**，而不是靠人记得写。
 */
function obj(props) {
  return { type: 'object', additionalProperties: true, properties: props };
}
function arr() { return { type: 'array' }; }

function makeOutput() {
  return {
    schema: obj({
      ok: { type: 'boolean' },
      blocked: { type: 'boolean' },
      code: { type: 'string' },
      reason: { type: 'string' },
      plugin: { type: 'string' },
      version: { type: 'string' },
      localDevice: { type: 'string' },
      date: { type: 'string' },
      dateDashed: { type: 'string' },
      dryRun: { type: 'boolean' },
      send: { type: 'boolean' },
      late: obj({ late: { type: 'boolean' }, lateDays: { type: 'number' } }),
      devices: arr(),
      deviceEnum: obj({ method: { type: 'string' }, evidence: obj({}), limits: arr(), devices: arr() }),
      profiles: obj({ source: { type: 'string' }, file: { type: 'string' }, count: { type: 'number' } }),
      targets: arr(),
      skipped: arr(),
      unassigned: arr(),
      notices: arr(),
      redactions: arr(),
      plan: obj({ environment: { type: 'string' } }),
      ledgerPathTilde: { type: 'string' },
      ledgerReadback: obj({ ok: { type: 'boolean' }, targets: { type: 'number' }, devices: { type: 'number' }, bytes: { type: 'number' } }),
      logFile: { type: 'string' },
      gate: obj({
        noticeMaxChars: { type: 'number' }, suggestionTypes: arr(), deviceStatus: arr(),
        allowedHosts: arr(), notHappens: { type: 'string' }
      })
    })
  };
}

export function apply(ctx, config = {}) {
  // R014 自查门（apply 最前；失败不阻塞挂载）
  try {
    runSelfCheck('dsh-plugin-reflect-dispatch', {
      requiredPeers: ['@deepseek-ai/cordis', '@deepseek-ai/dsh-tools'],
      requiredSymbols: ['defineTool', 'dispatch', 'resolveDevices'],
      sourceFiles: ['lib/index.js'],
      baseDir: path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
    });
  } catch { /* 自查失败不阻塞挂载 */ }

  const defaults = {
    emitOnly: config.emitOnly !== false,
    maxEvents: Number.isFinite(config.maxEvents) ? config.maxEvents : 8,
    threshold: Number.isFinite(config.threshold) ? config.threshold : 50,
    reflectRoot: config.reflectRoot || REFLECT_ROOT_REL,
    localDevice: config.localDevice || null
  };

  const tools = [
    defineTool({
      name: 'reflect_dispatch',
      description:
        '每日反思流水线的**发牌**环节（★ 跨设备）：读各设备当天的事件流（中央黑板 data/reflect/events/<device>/<date>；' +
        'localOnly=true 时只读本机 --events），按每个智能体登记的 resources 做归属判定，为它当天**真实做过**的事件定制一张' +
        '「思考卡」（① 你的今日任务实摘 ② 5 问各带你自己的上下文 ③ 证据要求含 Φ13 双时点 ④ 回填 JSON schema ⑤ 回填去向），' +
        '落盘到 ~/dsh-collab/data/reflect/cards/<device>/[<日期>/]<短键>.md 并生成设备合并卡，' +
        'send=true 时 PUT 中央板 data/reflect/cards/<device>/<date> 并**立即回读校验**。' +
        '目标设备离线 → 状态 pending（离线待取，不是失败）；允许 T+1/T+2 补派（allowLate）。' +
        '结构约束：目标不存在 → 拒绝执行（不静默跳过）；通知正文由冻结模板生成，恒 ≤' + NOTICE_MAX_CHARS + ' 字；' +
        '卡片只能写自己的 <device> 段（跨设备写即拒绝）；落盘/写板前跑凭据脱敏；dry-run 零变更。',
      parameters: {
        eventsPath: { type: 'string', description: '本机事件流 JSON 路径（localOnly 时必填；否则作为本机设备来源）' },
        devices: { type: 'string', description: `设备列表（逗号分隔；冻结候选 ${CANDIDATE_DEVICES.join('/')}）；省略=按中央板索引→候选探测→兜底本机` },
        device: { type: 'string', description: '本机设备名（默认按主机名映射 mac-mini/mbp/i9）' },
        localOnly: { type: 'boolean', description: 'true=只处理本机（退回单设备行为）' },
        allowLate: { type: 'boolean', description: 'true=允许补派 T+1/T+2（不加则处理过去的日期会被拒绝，Φ13）' },
        assumeOnline: { type: 'string', description: '人工声明在线的设备（逗号分隔）—— 仅在确知设备在线时用；声明会记入台账' },
        agents: { type: 'string', description: '只派给这些智能体（逗号分隔的会话 id 或短键）' },
        maxEvents: { type: 'integer', description: `每个智能体最多带几条事件（默认 ${defaults.maxEvents}）` },
        send: { type: 'boolean', description: 'true=PUT 中央板派发（含回读校验）；默认 false=只落盘不发送' },
        dryRun: { type: 'boolean', description: 'true=只返回计划，零变更（不落盘/不发黑板/不写日志）' },
        date: { type: 'string', description: '覆盖日期 YYYY-MM-DD；默认取事件流 window.until' },
        threshold: { type: 'integer', description: `归属阈值（默认 ${defaults.threshold}；低于它的事件不派给该目标）` }
      },
      output: makeOutput(),
      async execute(args) {
        try {
          const res = await dispatch({
            eventsPath: args.eventsPath ? String(args.eventsPath) : undefined,
            devices: args.devices ? String(args.devices) : undefined,
            device: args.device ? String(args.device) : undefined,
            localOnly: args.localOnly === true,
            allowLate: args.allowLate === true,
            assumeOnline: args.assumeOnline ? String(args.assumeOnline) : undefined,
            agents: args.agents ? String(args.agents) : undefined,
            maxEvents: args.maxEvents,
            send: args.send === true && args.dryRun !== true,
            dryRun: args.dryRun === true,
            date: args.date ? String(args.date) : undefined,
            threshold: args.threshold
          });
          return {
            ok: res.ok, plugin: res.plugin, version: res.version, localDevice: res.localDevice,
            date: res.date, dateDashed: res.dateDashed, dryRun: res.dryRun, send: res.send, late: res.late,
            devices: res.devices, deviceEnum: res.deviceEnum, profiles: res.profiles,
            targets: res.targets, skipped: res.skipped, unassigned: res.unassigned,
            notices: res.notices, redactions: res.redactions, plan: res.plan,
            ledgerPathTilde: res.ledgerPathTilde, ledgerReadback: res.ledgerReadback,
            logFile: res.logFile,
            gate: {
              noticeMaxChars: NOTICE_MAX_CHARS, suggestionTypes: SUGGESTION_TYPES,
              deviceStatus: DEVICE_STATUS, allowedHosts: ALLOWED_HOSTS, notHappens: GATE_META.notHappens
            }
          };
        } catch (e) {
          if (e instanceof GateError) {
            // 失败即停：把门的可操作原因原样返回（不吞、不降级为 warn）
            return { ok: false, plugin: name, version: VERSION, blocked: true, code: e.code, reason: e.message, logFile: LOG_FILE };
          }
          throw e;
        }
      }
    }),
    defineTool({
      name: 'reflect_targets',
      description: '只读：列出当前可派发目标（来自 agent_profiles / agent-bus 能力登记表）及其登记的 resources 与今天的设备卡键，用于派发前确认"能不能派、依据是什么"。不产生任何变更。',
      parameters: { device: { type: 'string', description: '本机设备名（默认按主机名映射）' } },
      output: makeOutput(),
      async execute(args) {
        try {
          const r = listTargets({ device: args.device ? String(args.device) : undefined });
          return { ok: true, plugin: name, version: VERSION, localDevice: r.localDevice, profiles: { source: r.source, file: r.file, count: r.count }, targets: r.targets, logFile: LOG_FILE };
        } catch (e) {
          if (e instanceof GateError) return { ok: false, blocked: true, plugin: name, version: VERSION, code: e.code, reason: e.message };
          throw e;
        }
      }
    }),
    defineTool({
      name: 'reflect_device_status',
      description:
        '只读：跨设备状态一览 —— 解析设备集合（标注用了哪种枚举方法及其局限），逐设备探测三件套键的存在性' +
        '（200=已存在 / 404=格式合法但尚未写入 / 400=键写法非法，三者语义不同不合并），并给出在场判定' +
        '（reportedToday / 心跳 / 本机）。用于 dispat 前后确认"卡该落哪、对方是否已上线取走"。',
      parameters: { devices: { type: 'string', description: '设备列表（逗号分隔）；省略=自动解析' }, date: { type: 'string', description: '日期 YYYY-MM-DD（默认今天）' } },
      output: makeOutput(),
      async execute(args) {
        try {
          const { probeKey } = await import('./board.js');
          const localDevice = resolveLocalDevice(undefined, undefined);
          const c = new Date();
          const p = (n) => String(n).padStart(2, '0');
          const dateDashed = args.date ? String(args.date) : `${c.getFullYear()}-${p(c.getMonth() + 1)}-${p(c.getDate())}`;
          const devRes = await resolveDevices({ devices: args.devices ? String(args.devices) : undefined, localDevice, dateDashed });
          const rows = [];
          for (const d of devRes.devices) {
            const k = keysFor(d, dateDashed);
            rows.push({
              device: d, local: d === localDevice,
              events: await probeKey(k.events, d === localDevice ? 'local' : 'central'),
              cards: await probeKey(k.cards, 'central'),
              answers: await probeKey(k.answers, 'central'),
              presence: await computePresence(d, { dateDashed, localDevice })
            });
          }
          return { ok: true, plugin: name, version: VERSION, localDevice, dateDashed, deviceEnum: { method: devRes.method, limits: devRes.limits }, devices: rows, logFile: LOG_FILE };
        } catch (e) {
          if (e instanceof GateError) return { ok: false, blocked: true, plugin: name, version: VERSION, code: e.code, reason: e.message };
          throw e;
        }
      }
    })
  ];

  for (const t of tools) ctx.effect(() => ctx.tools.register(t));
}
