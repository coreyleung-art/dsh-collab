/**
 * gate.js — R006#10 结构门：约束前置 · 不可绕过
 * =============================================================================
 * 本工具负责「每日反思」流水线的**发牌**环节：按每个智能体当天真实做过的事件，
 * 定制一张思考卡并派发。它的"不该发生路径"是下面这一条，其余都由它派生：
 *
 * ★ **假装派发了** —— 卡写进了盘（或根本没写），却对外声称"已派发"。
 *
 * 门不是"检查后放行"，而是让这些路径**在结构上不存在**（R006 §4.1 四种门型全用上）：
 *
 * | # | 不该发生的路径 | 门型 | 结构机制 |
 * |---|---|---|---|
 * | 1 | 假装派发（写了卡但没送达 / 送达没验） | **入口门** | 发送路径 = PUT 黑板 → **立即 GET 回读逐字节比对**（R003 要求）；任一不符 → READBACK_MISMATCH 中止，绝不报成功 |
 * | 2 | 派给不存在的目标、静默跳过 | **入口门** | assertTargetExists 是 **void-or-throw**：它**没有**可被 `continue` 消费的布尔返回值；`--agents` 里任何一个未知 id 都使整次派发失败（不是跳过） |
 * | 3 | 发送超 50 字的总线正文 | **类型锁** | 通知只能由 buildNotice() 生成：模板冻结、三个受控槽（短键/日期/前缀），CLI 与工具**都没有** `--message` 之类自由文本入参；assertNotice 再校验一次（≤50 且必须含黑板键） |
 * | 4 | dry-run 改盘 | **入口门** | dry-run 在解析/校验之后、**任何写操作之前**返回；连统一日志都不落盘（打印 `[dry-run][log-not-written]`）|
 * | 5 | 越界写盘（把卡写到别处） | **类型锁** | 所有写路径 path.resolve 后必须落在 `<home>/dsh-collab/data/reflect/` 前缀内，否则 REFLECT_PATH_OUTSIDE_ROOT（含 `../` 穿越）|
 * | 6 | 执行外部命令 / 连非黑板主机 | **类型锁** | ALLOWED_COMMANDS 冻结为空 + 源码不含 child_process 导入（**正面缺席证明**，不是空集通过）；出站主机冻结为 127.0.0.1:8792 且**无环境变量入口** |
 * | 7 | 广播 / 通配目标 | **类型锁** | TARGET_TOKENS_FORBIDDEN（`*`/`all`/`全部`…）命中即 TARGET_FORBIDDEN，不允许"发给大家" |
 * | 8 | 事件流非法 / 空事件流 | **Schema 门** | assertEventsDoc：结构非法或 events 为空 → EVENTS_INVALID（**没有事件就没有定制，宁可拒绝也不产出套话卡**）|
 * | 9 | 回填类型越界 | **类型锁** | SUGGESTION_TYPES 冻结四选一（新增/修订/转规范/无需动作）|
 * | 10 | 跳步派发（没生成卡就发送 / 没回读就记账） | **状态机** | DispatchStateMachine：planned→carded→board_written→readback_ok→recorded，非法迁移抛 ILLEGAL_TRANSITION |
 * | 11 | **跨设备污染**：A 设备的卡写进 B 设备的目录 | **类型锁** | assertDeviceSegment / assertDeviceInPath：key 与落盘路径里的 `<device>` 段必须**正好等于**卡片自己的 device；且 device 必须在本次解析出的设备集合内（设计文档 §10.5）|
 * | 12 | **凭据跨设备扩散**（Φ12 形态④） | **类型锁** | scrubCredentials：落盘与写黑板前对**最终文本**再扫一次凭据形态，命中即替换为 `[REDACTED:<kind>]`，只报告形态与条数、**不回显原文**；lean4-check C 有 7 类样本 + 假阳性检查 |
 * | 13 | 把"离线待取"记成失败，或把补派记成当天 | **类型锁** | DEVICE_STATUS 冻结枚举（`pending` 是合法终态，不是 `failed`）；assertNotLate：处理过去的日期必须显式 `--allow-late`，否则拒绝（Φ13 证据有时点）|
 *
 * 因此"能否绕过"不靠纪律，而靠：**没有那个入口 + 没有那个能力 + 有那个证明 + 失败即停**。
 */

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ══════════════════════ 冻结常量（类型锁的载体） ══════════════════════ */

/** 总线 v2.4 运行时门禁阈值（与 scripts/agent-send-gate.py THRESHOLD 对齐）。 */
export const NOTICE_MAX_CHARS = 50;

/** 回填建议的冻结四选一（schema 即门）。 */
export const SUGGESTION_TYPES = Object.freeze(['新增', '修订', '转规范', '无需动作']);

/** 本工具可执行的外部命令集合：**空**。配套 lean4-check F 的"正面缺席证明"。 */
export const ALLOWED_COMMANDS = Object.freeze([]);

/**
 * 唯一允许的出站主机（两块黑板）。运行期**没有**环境变量可以覆盖它。
 * 跨设备层（v1.1）把出口从 1 个扩到 2 个：本机黑板 + 中央黑板（设计文档 §10.2「黑板即协议」）。
 * 注意这仍是**封闭白名单**：加第三个主机必须改这个冻结常量（= 改代码），不能靠参数。
 */
export const BOARD_TARGETS = Object.freeze({
  local: 'http://127.0.0.1:8792',
  central: 'http://106.53.214.108:8792'
});
export const ALLOWED_HOSTS = Object.freeze(Object.values(BOARD_TARGETS).map((u) => u.replace(/^http:\/\//, '')));
export const TARGET_NAMES = Object.freeze(Object.keys(BOARD_TARGETS));

export function assertTargetName(name) {
  const n = String(name ?? '');
  if (!TARGET_NAMES.includes(n)) {
    throw new GateError('BB_TARGET_UNKNOWN', `未知黑板目标 "${n}"：只接受 ${TARGET_NAMES.join(' / ')}（封闭白名单）`);
  }
  return n;
}

/* ---------- 跨设备（v1.1）：设备名与"跨设备写门" ---------- */

/**
 * 设备名：小写字母开头，后接小写字母/数字/连字符，总长 2-16。
 * 16 上限不是随意定的：通知正文必须 ≤50 字，而通知里要带
 * `data/reflect/cards/<device>/<date>`（19 + device + 1 + 10 + 「看黑板 」），
 * device > 16 就装不进 50 字预算 → 宁可在这里拒绝，也不在发送时静默截断。
 */
export const DEVICE_NAME_RE = /^[a-z][a-z0-9-]{1,15}$/;
/**
 * 冻结候选设备。**来源是对齐，不是我猜的**：
 * 兄弟组件 `reflect-harvest` 的 `device_layer.devices` 实产（harvested-2026-09-10.json）为
 * `["mac-mini","mbp","lab-mbp","i9"]` —— 本工具直接采用同一集合，避免两套设备名分裂
 * （设计文档 §10.5「设备间版本漂移/认知分裂」）。`--devices` 可扩展。
 * ★ 注意这里**没有 iphone**：设计文档 §10.1 的实况是 iPhone 无 DSH/无 agent，属"只采不发"，
 *   派卡给它没有意义；但 `--devices iphone` 仍然合法（DEVICE_NAME_RE 通过）——只是默认集合不含它。
 */
export const CANDIDATE_DEVICES = Object.freeze(['mac-mini', 'mbp', 'lab-mbp', 'i9']);

export function assertDeviceName(d) {
  const s = String(d ?? '').trim();
  if (!s) throw new GateError('DEVICE_EMPTY', '设备名为空：拒绝（每条事件/每张卡都必须能回答"哪台设备"）');
  if (s.length > 16) {
    throw new GateError('DEVICE_NAME_TOO_LONG',
      `设备名 "${s}" 长 ${s.length} > 16：通知正文（含 data/reflect/cards/<device>/<date>）会超过 ${NOTICE_MAX_CHARS} 字总线门禁。请用更短的设备名。`);
  }
  if (!DEVICE_NAME_RE.test(s)) {
    throw new GateError('DEVICE_NAME_INVALID',
      `设备名 "${s}" 非法：要求 ^[a-z][a-z0-9-]{1,15}$（小写字母开头；不用大写/下划线/点/斜杠 —— 段位语法是硬的）`);
  }
  return s;
}

/** 卡片路径/键的形状：data/reflect/{cards|events|answers}/<device>/<...> */
export const REFLECT_KEY_RE = /^data\/reflect\/(cards|events|answers)\/([a-z][a-z0-9-]{1,15})\/(.+)$/;

/**
 * ★ 跨设备写门：一张卡的 key 里 <device> 段必须**正好等于**这张卡自己的 device。
 * 这是"不跨设备写别人的目录"从纪律变成结构约束的地方：
 *   · 段位不匹配 → REFLECT_CROSS_DEVICE_WRITE
 *   · device 不在本次解析出的设备集合里 → DEVICE_UNKNOWN
 *   · 形状不对（少一层/多一层/命名空间错）→ REFLECT_KEY_SHAPE
 */
export function assertDeviceSegment(key, device, allowedDevices) {
  const k = assertBoardKey(key);
  const m = k.match(REFLECT_KEY_RE);
  if (!m) {
    throw new GateError('REFLECT_KEY_SHAPE',
      `键形状非法: "${k}"。要求 data/reflect/<cards|events|answers>/<device>/<...>`);
  }
  const seg = m[2];
  if (seg !== device) {
    throw new GateError('REFLECT_CROSS_DEVICE_WRITE',
      `拒绝跨设备写：键里的设备段是 "${seg}"，但这张卡属于 "${device}"。` +
      '本工具只写"这张卡自己的 <device> 段"，绝不把 A 设备的卡写进 B 设备的目录。');
  }
  if (Array.isArray(allowedDevices) && !allowedDevices.includes(device)) {
    throw new GateError('DEVICE_UNKNOWN',
      `拒绝：设备 "${device}" 不在本次解析出的设备集合 [${allowedDevices.join(', ')}] 内（不在集合里就不写它的目录）。`);
  }
  return { device: seg, kind: m[1], tail: m[3] };
}

/**
 * 本地落盘路径的设备段检查（与键同一条纪律，只是换成文件路径）。
 * 路径形状：`<home>/dsh-collab/data/reflect/<cards|events|answers>/<device>/<...>`
 * ★ 首跑修正（2026-09-10，被 lean4-check C 抓到）：初版取了 relative 的第 0 段，
 *   而那一段是 **kind**（cards），不是 device —— 于是**所有**合法路径都被判成跨设备写。
 *   这就是 R006 §6 坑 1「门太宽会砍掉自己人」的现场复现；现在按段位取第 1 段并显式校验形状。
 */
export function assertDeviceInPath(absPath, device, home) {
  const p = assertWithinReflectRoot(absPath, home);
  const rel = p.slice(`${home}/dsh-collab/${REFLECT_ROOT_REL}/`.length);
  const segs = rel.split('/');
  if (segs.length < 3 || !['cards', 'events', 'answers'].includes(segs[0])) {
    throw new GateError('REFLECT_PATH_SHAPE',
      `落盘路径形状非法：${p}（要求 <cards|events|answers>/<device>/<...>）`);
  }
  const seg = segs[1];
  if (seg !== device) {
    throw new GateError('REFLECT_CROSS_DEVICE_WRITE',
      `拒绝跨设备落盘：${p} 的设备段是 "${seg}"，但这张卡属于 "${device}"。`);
  }
  return p;
}

/* ---------- 派发状态（类型锁） ---------- */

/**
 * 派发状态枚举。**`pending` 不是 `failed`** —— 设计文档 §10.4：
 * 设备离线时卡落在中央黑板即为投递完成（该设备上线自取），
 * 把"离线待取"记成失败会诱发无意义的重试与告警。
 */
export const DEVICE_STATUS = Object.freeze(['delivered', 'pending', 'local', 'failed']);

export function resolveStatus(s) {
  const v = String(s ?? '');
  if (!DEVICE_STATUS.includes(v)) {
    throw new GateError('STATUS_INVALID', `派发状态非法: "${v}"，只接受冻结枚举 ${DEVICE_STATUS.join(' / ')}`);
  }
  return v;
}

/* ---------- 补派（--allow-late） ---------- */

/** 本地日期（YYYYMMDD）。 */
export function localDateCompact(d = new Date()) {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`;
}

/**
 * 迟到门：处理"过去的日期"必须显式 --allow-late（设计文档 §10.4 的 T+1/T+2 补填）。
 * 不通过时**拒绝**（而不是静默按今天处理 —— 那会把补派写成当天，证据时点就错了，Φ13）。
 */
export function assertNotLate(dateCompact, todayCompact, allowLate) {
  const d = String(dateCompact), t = String(todayCompact);
  if (!/^\d{8}$/.test(d) || !/^\d{8}$/.test(t)) {
    throw new GateError('DATE_INVALID', `日期必须是 8 位 YYYYMMDD：date=${d} today=${t}`);
  }
  if (d >= t) return { late: false, lateDays: 0 };
  const days = (Date.parse(`${t.slice(0, 4)}-${t.slice(4, 6)}-${t.slice(6, 8)}T00:00:00Z`) -
                Date.parse(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}T00:00:00Z`)) / 86400000;
  if (!allowLate) {
    throw new GateError('LATE_DISPATCH_NOT_ALLOWED',
      `日期 ${d} 早于今天 ${t}（T-${days}）：补派必须显式 --allow-late。` +
      '否则会把补派记成当天，证据时点就错了（Φ13 证据有时点）。');
  }
  return { late: true, lateDays: days };
}

/* ---------- ★ 凭据脱敏（Φ12 引用即复制 · device_gates「落盘端 scrub」） ---------- */

/**
 * 凭据形态清单。**命中即替换，且只报告形态与条数，不回显原文**（Φ12：副本一旦产生不可回收）。
 * 顺序敏感：先长结构（PEM / 连接串）后短前缀（sk- / ghp_）。
 */
export const SECRET_PATTERNS = Object.freeze([
  { kind: 'pem-private-key', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g },
  { kind: 'conn-string', re: /\b(?:mongodb|postgres|postgresql|mysql|redis|amqp):\/\/[^\s:@/]+:[^\s@/]+@[^\s]+/gi },
  { kind: 'bearer', re: /\bBearer\s+[A-Za-z0-9._~+/=-]{16,}/gi },
  { kind: 'jwt', re: /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{6,}/g },
  { kind: 'openai-key', re: /\bsk-[A-Za-z0-9_-]{16,}/g },
  { kind: 'github-token', re: /\bgh[pousr]_[A-Za-z0-9]{20,}/g },
  { kind: 'aws-access-key', re: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g },
  // ★ 幂等守卫 `(?!\[REDACTED:)`：没有它，第二轮会把上一轮写下的
  //   `token=[REDACTED:github-token]` 当成"token=某个值"再替换一次 →
  //   脱敏不幂等（首跑时被 lean4-check C 抓到：openai-key/github-token/kv-secret 三类都失败）。
  { kind: 'env-secret-assign', re: /\b[A-Z][A-Z0-9_]{2,}_(?:TOKEN|SECRET|KEY|PASSWORD|PASSWD)\s*=\s*(?!\[REDACTED:)[^\s"']{6,}/g },
  { kind: 'kv-secret', re: /\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|appsecret)\b(\s*[:=]\s*)["']?(?!\[REDACTED:)[^\s"',;)\]}]{6,}/gi }
]);

/**
 * 脱敏：幂等（跑两次结果相同 —— 已替换的 [REDACTED:*] 不再被二次命中）。
 * @returns {{text:string, hits:Array<{kind:string,count:number}>, total:number}}
 */
export function scrubCredentials(input) {
  let text = String(input ?? '');
  const hits = [];
  for (const { kind, re } of SECRET_PATTERNS) {
    const rx = new RegExp(re.source, re.flags);
    let n = 0;
    text = text.replace(rx, (...args) => {
      n++;
      const m = args[0];
      if (kind === 'env-secret-assign') return `${m.split('=')[0]}=[REDACTED:${kind}]`;
      if (kind === 'kv-secret') {
        // 保留"键名 + 分隔符"，只替换值 → 可读性保住，凭据不留
        const name = args[1], sep = args[2];
        return `${name}${sep}[REDACTED:${kind}]`;
      }
      return `[REDACTED:${kind}]`;
    });
    if (n) hits.push({ kind, count: n });
  }
  return { text, hits, total: hits.reduce((a, h) => a + h.count, 0) };
}

/** 脱敏自证（lean4-check C 会跑它）：含凭据样本必须被替换、原文不再出现、且幂等；普通技术文本不得被改。 */
export function scrubSelfTest() {
  const samples = [
    { kind: 'openai-key', text: 'api_key: sk-abcdefghijklmnopqrstuvwxyz012345', leak: 'sk-abcdefghijklmnopqrstuvwxyz012345' },
    { kind: 'bearer', text: 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef', leak: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef' },
    { kind: 'github-token', text: 'token=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', leak: 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' },
    { kind: 'env-secret-assign', text: 'GITEE_TOKEN=abcdef1234567890abcdef', leak: 'abcdef1234567890abcdef' },
    { kind: 'kv-secret', text: 'password: hunter2secret', leak: 'hunter2secret' },
    { kind: 'conn-string', text: 'mongodb://user:pa55word@db.example.com:27017/x', leak: 'pa55word' },
    { kind: 'pem-private-key', text: '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----', leak: 'MIIEowIBAAKCAQEA' }
  ];
  const out = samples.map((s) => {
    const r = scrubCredentials(s.text);
    return {
      kind: s.kind,
      redacted: r.total > 0 && r.text.includes('[REDACTED:'),
      leaked: r.text.includes(s.leak),
      idempotent: scrubCredentials(r.text).text === r.text
    };
  });
  // 假阳性检查：普通技术文本不得被改（门太宽会砍掉自己人）
  const benign = '归属判定 score 100 via 路径精确；指令 exit=2；键 notes/x；R026 HMAC 双层锁；token 概念解释';
  const benignUntouched = scrubCredentials(benign).text === benign;
  return { samples: out, benignUntouched, ok: out.every((o) => o.redacted && !o.leaked && o.idempotent) && benignUntouched };
}


/** 目标名里的通配/广播词：命中即拒绝，"发给大家"这条路没有入口。 */
export const TARGET_TOKENS_FORBIDDEN = Object.freeze([
  '*', 'all', 'everyone', 'everybody', '@all', '@everyone', 'broadcast', '全部', '所有人', '全体'
]);

/** 卡片落盘的根前缀（相对 ~/dsh-collab/）。所有写路径必须落在这下面。 */
export const REFLECT_ROOT_REL = 'data/reflect';

/** 派发状态机：只允许这一条链上的迁移。 */
export const DISPATCH_STATES = Object.freeze(['planned', 'carded', 'board_written', 'readback_ok', 'recorded']);
export const DISPATCH_TRANSITIONS = Object.freeze({
  planned: Object.freeze(['carded']),
  // carded → recorded 是 --emit-only（只落盘不发送）的合法终态；
  // 但 readback_ok **只能**从 board_written 到达 —— "没写黑板却声称回读通过"无法表达。
  carded: Object.freeze(['board_written', 'recorded']),
  board_written: Object.freeze(['readback_ok']),
  readback_ok: Object.freeze(['recorded']),
  recorded: Object.freeze([])
});

/* ══════════════════════ 工具：计数与规范化 ══════════════════════ */

/** 与 agent-send-gate.py 的 len() 同口径：**码点**计数（不是字节、不是 UTF-16 单元）。 */
export function charCount(text) {
  return [...String(text)].length;
}

/**
 * 黑板键合法性（实测 2026-09-10 首段规则；2026-09-11 与 bb-write.py 交叉验证后收紧）。
 *   ① 首段命名空间必须是**纯小写字母** `[a-z]+`（`cld-health`/`mac-mini`/`ABC` → 400 bad key）
 *   ② 后续段只允许 `[A-Za-z0-9._-]`（空格/`: `/#/非 ASCII → 400，或在客户端就崩）
 *   ③ **至少两段**（`data` 单段 → 黑板 400 bad key）
 * ★ 第 ③ 条是交叉验证抓出来的：我原来的正则末尾是 `(...)*`，于是**单段键 `data` 被判合法**，
 *   而实测 `PUT /data` → **400**。这正是"写前校验说 OK、实际写入被拒"的伪装陷阱——
 *   和 bb-write.py 在"后续段"上留的口子是同一类。现在两侧都按上面三条收口。
 *   （单段形式只用于"按命名空间列举"的 GET，那条路径走 board.listKeys 的 rawRequest，不经过此门。）
 */
export const BB_KEY_RE = /^[a-z]+\/[A-Za-z0-9._-]+(\/[A-Za-z0-9._-]+)*$/;

export function assertBoardKey(key) {
  const k = String(key ?? '').replace(/^\/+/, '');
  if (!k) throw new GateError('BB_KEY_EMPTY', '黑板键为空：拒绝写入无名键');
  if (!k.includes('/')) {
    throw new GateError('BB_KEY_NOT_A_KEY',
      `"${k}" 只有一段：那是**命名空间**，不是键（实测 PUT /${k} → 400 bad key）。` +
      '写法要求：至少两段，如 data/<域>/<键> / notes/<节点>/<键>。');
  }
  if (!BB_KEY_RE.test(k)) {
    throw new GateError('BB_KEY_INVALID',
      `黑板键非法: "${k}"。要求：首段纯小写字母 [a-z]+；后续段只含 [A-Za-z0-9._-]；至少两段。` +
      '（空格 / : / # / 非 ASCII → 400 bad key 或客户端直接报错 —— 实测 2026-09-11）');
  }
  return k;
}

/** 智能体短键：去掉 session- 前缀取前 8 字符。目的是让黑板键 + 通知一起挤进 50 字以内。 */
export function shortKey(agentId) {
  const s = String(agentId ?? '').trim().replace(/^session-/, '');
  const out = s.slice(0, 8);
  if (!/^[a-z0-9]{4,}$/.test(out)) {
    throw new GateError('AGENT_KEY_INVALID', `无法从 "${agentId}" 派生短键（要求去 session- 前缀后前 8 字符为 [a-z0-9]）`);
  }
  return out;
}

/** 目标存在索引。 */
export function makeIndex(agents) {
  const byShort = new Map();
  const byFull = new Map();
  for (const a of agents || []) {
    const full = String(a.agentId);
    let sk;
    try { sk = shortKey(full); } catch { continue; }   // 无法派生短键的档案不进索引（不静默冒充）
    const rec = { agentId: full, shortKey: sk, role: a.role || '', abilities: a.abilities || [], resources: a.resources || [], source: a.source || 'profile' };
    if (byShort.has(sk) && byShort.get(sk).agentId !== full) {
      throw new GateError('AGENT_KEY_COLLISION',
        `短键冲突: "${sk}" 同时来自 ${byShort.get(sk).agentId} 与 ${full} —— 黑板键会撞车，拒绝继续（请改用完整 id 体系）`);
    }
    byShort.set(sk, rec);
    byFull.set(full, rec);
  }
  return {
    size: byShort.size,
    list: () => [...byShort.values()],
    get: (k) => byShort.get(String(k)) || byFull.get(String(k)) || null,
    has: (k) => byShort.has(String(k)) || byFull.has(String(k)),
    byShort,
    byFull
  };
}

/* ══════════════════════ 类型锁：通知 + 三件套 key（唯一构造入口） ══════════════════════ */

/** 设计文档 §10.2 的 key 三件套（跨设备层的协议面）。日期用 `YYYY-MM-DD`（§10.2 示例）。 */
export function cardKeyFor(device, dateDashed) {
  return `data/reflect/cards/${assertDeviceName(device)}/${assertDateDashed(dateDashed)}`;
}
export function eventsKeyFor(device, dateDashed) {
  return `data/reflect/events/${assertDeviceName(device)}/${assertDateDashed(dateDashed)}`;
}
export function answersKeyFor(device, dateDashed) {
  return `data/reflect/answers/${assertDeviceName(device)}/${assertDateDashed(dateDashed)}`;
}

export function assertDateDashed(d) {
  const s = String(d ?? '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    throw new GateError('DATE_INVALID', `日期必须是 YYYY-MM-DD（黑板键日期段），收到 "${s}"`);
  }
  return s;
}

/**
 * 通知文本的**唯一**构造入口。
 * 模板冻结，只接受一个**受控槽**：`boardKey` —— 而 boardKey 只能由 cardKeyFor() 造出来
 * （device 必须过 DEVICE_NAME_RE、日期必须 8+2 位数字格式）。
 * ★ 这里没有 text / message / body 之类的自由文本参数 —— "发一条 200 字的通知"无法表达。
 */
export function buildNotice(boardKey) {
  const key = String(boardKey ?? '').trim();
  if (!key) throw new GateError('NOTICE_KEY_EMPTY', 'buildNotice: 黑板键为空（通知必须指向一个键）');
  const m = key.match(REFLECT_KEY_RE);
  if (!m) {
    throw new GateError('NOTICE_KEY_SHAPE',
      `buildNotice: 键 "${key}" 形状非法（要求 data/reflect/<cards|events|answers>/<device>/<date>）—— 拒绝构造通知。`);
  }
  assertDeviceName(m[2]);
  const text = `看黑板 ${key}`;
  assertNotice(text, { expectKey: key });
  return { text, chars: charCount(text), boardKey: key, device: m[2], kind: m[1] };
}

/**
 * 通知门：① 码点数 ≤50（v2.4 门禁）② 必须含黑板键（该门禁的"黑板路径豁免"正则
 * `(notes/|data/|tasks/)[a-z0-9\-/]+` 也要命中）。两条都不满足即拒绝发送。
 */
export function assertNotice(text, opts = {}) {
  const t = String(text ?? '');
  const n = charCount(t);
  if (n === 0) throw new GateError('NOTICE_EMPTY', '通知为空：拒绝发送空正文');
  if (n > NOTICE_MAX_CHARS) {
    throw new GateError('NOTICE_TOO_LONG',
      `通知 ${n} 字 > 上限 ${NOTICE_MAX_CHARS} 字（总线 v2.4 门禁）。` +
      `正确做法：长内容写黑板，正文只发「看黑板 <key>」。本工具的通知由 buildNotice 生成，不接受自由文本。`);
  }
  if (!/(notes|data|tasks)\/[a-z0-9\-/]+/.test(t)) {
    throw new GateError('NOTICE_NO_BOARD_KEY',
      `通知里没有黑板键引用: "${t}"。总线门禁要求正文必须指向黑板键（"看黑板 <key>"）。`);
  }
  if (opts.expectKey && !t.includes(opts.expectKey)) {
    throw new GateError('NOTICE_KEY_MISMATCH', `通知未包含期望的黑板键 "${opts.expectKey}"：拒绝发送（避免指向错键）`);
  }
  return { ok: true, chars: n, boardKeyMatched: (t.match(/(notes|data|tasks)\/[a-z0-9\-/]+/) || [])[0] };
}

/* ══════════════════════ 入口门：目标存在性（void-or-throw） ══════════════════════ */

/**
 * ★ 关键设计：本函数**只返回 void 或抛 GateError**。
 * 它刻意不返回 boolean —— 因为返回 boolean 就会有人写 `if (!exists) continue;`，
 * 那就成了"静默跳过"，也就成了"假装派发"。这里没有可供 continue 的返回值。
 */
export function assertTargetExists(agentKey, index) {
  const k = String(agentKey ?? '').trim();
  if (!k) throw new GateError('TARGET_EMPTY', '目标为空：拒绝派发（不接受空目标）');
  const low = k.toLowerCase();
  for (const tok of TARGET_TOKENS_FORBIDDEN) {
    if (tok === '*' ? k.includes('*') : low === tok || low.includes(tok)) {
      throw new GateError('TARGET_FORBIDDEN',
        `拒绝：目标 "${k}" 命中通配/广播词「${tok}」。本工具**只能一对一派卡**（每张卡按个人当天事件定制，广播与定制互斥）。`);
    }
  }
  const hit = index.get(k);
  if (!hit) {
    throw new GateError('TARGET_NOT_FOUND',
      `拒绝：目标 "${k}" 不在能力登记表（agent_profiles）中，无法验证其存在。` +
      `本工具**不会静默跳过**不存在的目标 —— 请先在档案里登记，或从 --agents 里去掉它。` +
      `当前可派目标 ${index.size} 个：${index.list().map((a) => a.shortKey).join(', ')}`);
  }
  return hit;
}

/** `--agents` 过滤器：任何一个未知 id 都让整次派发失败（失败即停，而非部分成功）。 */
export function resolveAgentFilter(input, index) {
  if (input === undefined || input === null || input === '') return index.list();
  const raw = Array.isArray(input) ? input : String(input).split(',');
  const wanted = raw.map((s) => String(s).trim()).filter(Boolean);
  if (!wanted.length) throw new GateError('TARGET_EMPTY', '--agents 给了空列表：拒绝（要么不给，要么给有效 id）');
  const out = [];
  const missing = [];
  for (const w of wanted) {
    try { out.push(assertTargetExists(w, index)); }
    catch (e) { missing.push(`${w} → [${e.code}]`); }
  }
  if (missing.length) {
    throw new GateError('AGENT_UNKNOWN',
      `--agents 里有 ${missing.length} 个目标无法验证存在：${missing.join('; ')}。` +
      `失败即停：不做"已知的照发、未知的跳过"。`);
  }
  return out;
}

/* ══════════════════════ 写盘门 ══════════════════════ */

export function reflectRootAbs(home) {
  return `${home}/dsh-collab/${REFLECT_ROOT_REL}`;
}

/**
 * 所有写路径必须先过此门：resolve 之后必须落在 <home>/dsh-collab/data/reflect/ 前缀内。
 * 覆盖 `../` 穿越、绝对路径越界、符号链接式绕写（resolve 归一化后再比前缀）。
 */
export function assertWithinReflectRoot(absPath, home) {
  const root = reflectRootAbs(home);
  const p = String(absPath ?? '');
  if (!p) throw new GateError('REFLECT_PATH_EMPTY', '写路径为空：拒绝');
  const rp = p.includes('\0') ? null : absPathResolve(p);
  if (!rp) throw new GateError('REFLECT_PATH_OUTSIDE_ROOT', `写路径含非法字符: ${JSON.stringify(p)}`);
  if (rp !== root && !rp.startsWith(root + '/')) {
    throw new GateError('REFLECT_PATH_OUTSIDE_ROOT',
      `拒绝越界写：${rp} 不在 ${root}/ 之下。本工具只允许写 data/reflect/（卡 / 派发记录 / 索引）。`);
  }
  return rp;
}

function absPathResolve(p) {
  // 与 path.resolve 等价、但不 import（保持门模块零依赖，便于被 lean4-check 单独加载）
  const segs = p.split('/');
  const stack = [];
  for (const s of segs) {
    if (s === '' || s === '.') continue;
    if (s === '..') { if (!stack.length) return null; stack.pop(); continue; }
    stack.push(s);
  }
  return '/' + stack.join('/');
}

/* ══════════════════════ Schema 门：事件流文档 ══════════════════════ */

/**
 * 上游 reflect-collect 的产出格式门。
 * ★ events 为空 → 直接拒绝：没有事件就没有"定制"，此时生成的卡必然是套话卡。
 */
/**
 * Schema 门：事件流文档。
 * `allowEmpty:true` 用于**跨设备**场景：某台设备当天真的 0 事件是可以接受的
 * （如实记为 no-events），但**所有**设备都没有事件时，调用方必须在最后仍拒绝生成
 * （否则就退化成"发统一问卷"）。默认（单设备路径）allowEmpty=false，空流直接拒绝。
 */
export function assertEventsDoc(doc, opts = {}) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    throw new GateError('EVENTS_INVALID', '事件流文档必须是 JSON 对象（{window, counts, events}）');
  }
  if (!Array.isArray(doc.events)) {
    throw new GateError('EVENTS_INVALID', 'events 必须是数组（上游 reflect-collect 产出格式）');
  }
  if (doc.events.length === 0 && !opts.allowEmpty) {
    throw new GateError('EVENTS_EMPTY',
      '事件流为空：没有当天真实事件就没有"定制卡"，此时只能产出套话 —— 拒绝生成。' +
      '（本工具宁可 exit 1，也不发统一问卷。）');
  }
  const seen = new Set();
  doc.events.forEach((e, i) => {
    if (!e || typeof e !== 'object' || Array.isArray(e)) {
      throw new GateError('EVENTS_INVALID', `events[${i}] 不是对象`);
    }
    if (typeof e.id !== 'string' || !e.id.trim()) {
      throw new GateError('EVENTS_INVALID', `events[${i}].id 缺失：没有 id 就无法在卡里点名引用（event_ref）`);
    }
    if (seen.has(e.id)) throw new GateError('EVENTS_INVALID', `事件 id 重复: ${e.id}（回填的 event_ref 会指向两条事件）`);
    seen.add(e.id);
    if (typeof e.source !== 'string' || !e.source.trim()) {
      throw new GateError('EVENTS_INVALID', `events[${i}].source 缺失（files/board/tools/logs/git…）`);
    }
    if (!e.path && !e.key && !e.desc) {
      throw new GateError('EVENTS_INVALID', `events[${i}] 既无 path、也无 key、也无 desc：无法归属，也无法在卡里陈述事实`);
    }
  });
  return doc;
}

export function resolveSuggestionType(input) {
  const t = String(input ?? '').trim();
  if (!SUGGESTION_TYPES.includes(t)) {
    throw new GateError('SUGGESTION_INVALID',
      `建议类型非法: "${t}"。只接受冻结四选一：${SUGGESTION_TYPES.join(' / ')}`);
  }
  return t;
}

/* ══════════════════════ 回读门（R003） ══════════════════════ */

/**
 * 空壳键判定（R003 补充通告 2026-09-11 · 第 ③ 条「空壳键变体」）。
 * 实测背景：键**存在**（HTTP 200、有 ts/version）但 `value` 是 `{}` ——
 * **纯状态码校验会漏**：`status===200` 为真，于是"该设备当天上报过事件""回读成功"这类断言全被满足，
 * 而内容其实是空的。凡是用 `status` 代替"内容非空"的地方都是这个漏点。
 * 口径：`null/undefined`、空对象 `{}`、空数组 `[]`、纯空白字符串 → 空壳。
 */
export function isEmptyShell(v) {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string') return v.trim() === '';
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === 'object') return Object.keys(v).length === 0;
  return false;
}

/**
 * 规范化 JSON（递归排序键）。
 * ★ 首跑实测（2026-09-10，跨设备 PUT 中央板时被自己的门抓到）：
 *   黑板**会重排 JSON 键序**再落盘 → 直接用 JSON.stringify 比字符会长度相同但顺序不同，
 *   于是把一次**成功**的写入判成 READBACK_MISMATCH —— 正是 R006 §6 坑 4「假失败」。
 *   回读比对要做**语义比对**（键序无关），而不是字符比对；字节数只作为附注。
 */
export function canonicalJson(value) {
  const seen = new WeakSet();
  const norm = (v) => {
    if (v === null || typeof v !== 'object') return v;
    if (seen.has(v)) return '[circular]';
    seen.add(v);
    if (Array.isArray(v)) return v.map(norm);
    const out = {};
    for (const k of Object.keys(v).sort()) out[k] = norm(v[k]);
    return out;
  };
  return JSON.stringify(norm(value));
}

/**
 * 写黑板后必须回读比对（R003：写入后立即回读验证 value 非空；
 * 实测 2026-09-10 已有 4 次"报告指向不存在的落盘物"——写入返回非 200 被当成成功）。
 * 比对口径：**规范化 JSON 语义相等**（键序无关），不是字符相等。
 */
export function assertReadback(expectValue, gotValue, boardKey) {
  if (gotValue === null || gotValue === undefined) {
    throw new GateError('READBACK_EMPTY',
      `回读为空：${boardKey} 写入后读不到内容（400=写法非法 / 404=不存在，二者都不得当成功）。派发判定为**失败**。`);
  }
  if (isEmptyShell(gotValue)) {
    // R003 补充通告第 ③ 条：光看状态码会漏——键在、ts 在、version 在，value 却是空壳
    throw new GateError('READBACK_EMPTY_SHELL',
      `回读是**空壳**：${boardKey} 的 HTTP 是 200（键确实存在），但 value=${JSON.stringify(gotValue)} 内容为空。` +
      '按 R003 补充通告（2026-09-11 第 ③ 条）：**纯状态码校验会漏空壳键**，必须验内容 —— 派发判定为**失败**。');
  }
  const a = canonicalJson(expectValue);
  const b = canonicalJson(gotValue);
  if (a !== b) {
    throw new GateError('READBACK_MISMATCH',
      `回读不一致（语义比对，键序无关）：${boardKey} 写入后读回的 JSON 与写入内容不等 —— 不报成功。` +
      `expect=${a.slice(0, 120)} got=${b.slice(0, 120)}`);
  }
  return { ok: true, chars: a.length, note: '规范化 JSON 语义相等（黑板会重排键序，故不做字符比对）' };
}

export function assertCardOnDisk(absPath, content) {
  if (!absPath) throw new GateError('CARD_PATH_EMPTY', '卡片路径为空：拒绝发送');
  return { ok: true, path: absPath, bytes: charCount(content) };
}

/* ══════════════════════ 状态机门 ══════════════════════ */

export function makeDispatchStateMachine(label = 'target') {
  let state = 'planned';
  const trail = [{ state, ts: new Date().toISOString() }];
  return {
    get state() { return state; },
    get trail() { return trail.slice(); },
    can(next) { return (DISPATCH_TRANSITIONS[state] || []).includes(next); },
    to(next) {
      if (!DISPATCH_STATES.includes(next)) {
        throw new GateError('ILLEGAL_TRANSITION', `${label}: 未知状态 "${next}"`);
      }
      if (!this.can(next)) {
        throw new GateError('ILLEGAL_TRANSITION',
          `${label}: 非法迁移 ${state} → ${next}。只允许 ${state} → [${(DISPATCH_TRANSITIONS[state] || []).join(', ') || '终态'}]。` +
          `（例：没 carded 就不能 board_written —— 没有卡就没有可派发的东西）`);
      }
      state = next;
      trail.push({ state, ts: new Date().toISOString() });
      return state;
    }
  };
}

/* ══════════════════════ 源码扫描（lean4-check 的证明工具） ══════════════════════ */

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（行号与长度保持不变）。
 * 为什么必须去掉：扫描器会把自己的检测正则与帮助文本当靶子（假阳性）。
 * 如实标注：这是**源码结构扫描，非完整 AST**（本包零外部依赖、宿主内无可用解析器）。
 */
export function stripLiterals(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  const pushBlank = (s) => { for (const ch of s) out += (ch === '\n' ? '\n' : ' '); };
  while (i < n) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') { let j = i; while (j < n && src[j] !== '\n') j++; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '/' && d === '*') { let j = src.indexOf('*/', i + 2); j = j < 0 ? n : j + 2; pushBlank(src.slice(i, j)); i = j; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) { j++; break; } j++; }
      pushBlank(src.slice(i, j)); i = j; continue;
    }
    if (c === '/') {
      const lineEnd = src.indexOf('\n', i); const stop = lineEnd < 0 ? n : lineEnd;
      const prev = out.replace(/\s+$/, '').slice(-1);
      const regexPos = prev === '' || '(,=:[!&|?{};'.includes(prev);
      if (regexPos) {
        let j = i + 1, closed = false;
        while (j < stop) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === '/') { closed = true; j++; break; } j++; }
        if (closed) { pushBlank(src.slice(i, j)); i = j; continue; }
      }
    }
    out += c; i++;
  }
  return out;
}

/** 危险原语：宽杀 / 任意命令执行 / 破坏性文件操作（命中即 lean4-check A 失败）。 */
export const FORBIDDEN_PRIMITIVES = Object.freeze([
  'killall', 'pkill', 'taskkill', 'execSync', 'execFileSync', 'spawnSync', 'fork(',
  'rmSync', 'rmdirSync', 'unlinkSync', 'truncateSync', 'chmodSync', 'writeFileSyncAtomic'
]);

export function scanForbiddenPrimitives({ sources }) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, idx) => {
      for (const name of FORBIDDEN_PRIMITIVES) {
        const re = name.endsWith('(')
          ? new RegExp(`(^|[^\\w.$])${name.replace('(', '')}\\s*\\(`)
          : new RegExp(`(^|[^\\w.$])${name}\\b`);
        if (re.test(line)) hits.push({ file, line: idx + 1, callee: name });
      }
      if (/process\s*\.\s*kill\s*\(\s*-/.test(line)) hits.push({ file, line: idx + 1, callee: 'process.kill(-N)' });
      if (/(?:from|import\s*\()\s*['"]node:child_process['"]/.test(line)) hits.push({ file, line: idx + 1, callee: 'child_process' });
    });
  }
  return hits;
}

/**
 * 正向证明 ①：枚举全部外部命令执行点（exec/execFile/spawn/fork）的第一个实参。
 * 步骤：去字面量定位调用点 → 回原文同一偏移读实参（否则会"空集通过"，R006 §6 坑 3）。
 */
export function scanExecSites({ sources }) {
  const sites = [];
  const callRe = /(?<![\w.$])(pExecFile|execFileSync|execFile|execSync|exec|spawnSync|spawn|fork)\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);           // 与原文等长 → 索引可对齐
    let m;
    while ((m = callRe.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const after = raw.slice(m.index + m[0].length);
      const lit = after.match(/^\s*'([^']*)'/) || after.match(/^\s*"([^"]*)"/) || after.match(/^\s*`([^`]*)`/);
      sites.push({ file, line, callee: m[1], cmd: lit ? lit[1] : null, literal: !!lit });
    }
  }
  return sites;
}

/**
 * 正向证明 ②：源码里是否存在 child_process 导入。
 * 这一条是为了把 F 从"空集通过"变成"**正面缺席证明**"：
 * 当 scanExecSites 返回 0 个点时，我们不是断言 `[] ⊆ 允许`（空洞通过），
 * 而是断言"源码根本不具备产生执行点的能力"。
 */
export function scanChildProcessImports({ sources }) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, idx) => {
      if (/child_process/.test(line)) {
        const l = line.trim();
        if (l.startsWith('import') || l.includes('require(')) hits.push({ file, line: idx + 1, snippet: l.slice(0, 80) });
      }
    });
  }
  return hits;
}

/** 正向证明 ③：枚举源码里出现的全部出站主机字面量，必须 ⊆ ALLOWED_HOSTS。 */
export function scanOutboundHosts({ sources }) {
  const hosts = new Set();
  const byFile = {};
  for (const [file, raw] of Object.entries(sources)) {
    // host 必须写在字面量里 → 这里要在**原文**上扫（与 scanExecSites 相反）
    const re = /https?:\/\/([^\s/'"`)\]]+)/g;
    let m;
    while ((m = re.exec(raw)) !== null) {
      hosts.add(m[1]);
      (byFile[file] = byFile[file] || []).push(m[1]);
    }
  }
  return { hosts: [...hosts], byFile };
}

/* ══════════════════════ 负例 / 正例矩阵（lean4-check B / C） ══════════════════════ */

/** hermetic 夹具索引：让 B/C 可离线复跑，不依赖当天档案内容。 */
export function fixtureIndex() {
  return makeIndex([
    { agentId: 'session-aaaaaaaa-1111-2222-3333-444444444444', role: '夹具甲', resources: ['file:/tmp/fx/a.md'] },
    { agentId: 'session-bbbbbbbb-1111-2222-3333-444444444444', role: '夹具乙', resources: ['store:8'] }
  ]);
}

/** 负例矩阵：全部必须被拒（code===null 表示"竟然放过了"）。 */
export function gateNegativeCases(index = fixtureIndex()) {
  const cases = [];
  const t = (name, fn) => {
    try { fn(); cases.push({ name, code: null }); }
    catch (e) { cases.push({ name, code: e.code || 'ERROR', msg: String(e.message).slice(0, 90) }); }
  };

  t('不存在的目标', () => assertTargetExists('deadbeef', index));
  t('空目标', () => assertTargetExists('', index));
  t('通配 *', () => assertTargetExists('*', index));
  t('广播 all', () => assertTargetExists('all', index));
  t('广播 全部', () => assertTargetExists('全部', index));
  t('--agents 混入未知 id', () => resolveAgentFilter(['aaaaaaaa', 'ghost-99'], index));
  t('--agents 空列表', () => resolveAgentFilter([], index));
  t('通知超 50 字', () => assertNotice('这是一条明显超过五十个字的通知正文用来验证总线门禁是否真的生效请不要把它发出去啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊'));
  t('通知无黑板键', () => assertNotice('今天辛苦了'));
  t('buildNotice 键形状非法（自由文本当键）', () => buildNotice('今天发一张卡给大家'));
  t('buildNotice 设备名超 16 字（通知装不进 50 字）', () => buildNotice(`data/reflect/cards/${'x'.repeat(20)}/2026-09-10`));
  t('黑板键首段非纯小写字母', () => assertBoardKey('notes-1/aaaaaaaa/reflect-card-20260910'));
  t('黑板键含大写', () => assertBoardKey('Notes/aaaaaaaa/x'));
  t('黑板键为空', () => assertBoardKey(''));
  t('★ 单段键 data（实测 board=400，交叉验证抓出）', () => assertBoardKey('data'));
  t('键含空格（board=400 / 客户端报错）', () => assertBoardKey('data/x/y z'));
  t('键含冒号（board=400）', () => assertBoardKey('data/x/a:b'));
  t('键含井号（board=400）', () => assertBoardKey('data/x/a#b'));
  t('键含非 ASCII（board=400）', () => assertBoardKey('data/x/中文'));
  t('键含空段 data//x', () => assertBoardKey('data//x'));
  t('键含尾斜杠 data/x/', () => assertBoardKey('data/x/'));
  // ---- 跨设备层新增负例 ----
  t('设备名为空', () => assertDeviceName(''));
  t('设备名含大写', () => assertDeviceName('MBP'));
  t('设备名含下划线', () => assertDeviceName('mac_mini'));
  t('设备名含点/斜杠（路径穿越式）', () => assertDeviceName('../etc'));
  t('设备名超 16 字', () => assertDeviceName('mac-mini-with-a-very-long-name'));
  t('跨设备写：mbp 的卡写进 mac-mini 段', () => assertDeviceSegment('data/reflect/cards/mac-mini/2026-09-10', 'mbp', ['mac-mini', 'mbp']));
  t('跨设备写：设备不在允许集合内', () => assertDeviceSegment('data/reflect/cards/iphone/2026-09-10', 'iphone', ['mac-mini', 'mbp']));
  t('reflect 键形状非法（少一层）', () => assertDeviceSegment('data/reflect/cards/2026-09-10', 'mac-mini', ['mac-mini']));
  t('reflect 键命名空间非法（写 registry 冒充卡）', () => assertDeviceSegment('data/registry/mac-mini/2026-09-10', 'mac-mini', ['mac-mini']));
  t('未知黑板目标名', () => assertTargetName('somewhere-else'));
  t('派发状态越界（"pending" 以外的自由文本）', () => resolveStatus('大概是成功了吧'));
  t('补派未加 --allow-late', () => assertNotLate('20260908', '20260910', false));
  t('写盘越界（/tmp）', () => assertWithinReflectRoot('/tmp/evil.md', '/Users/x'));
  t('写盘穿越（../..）', () => assertWithinReflectRoot('/Users/x/dsh-collab/data/reflect/../../../../tmp/evil.md', '/Users/x'));
  t('写盘路径含 NUL', () => assertWithinReflectRoot('/Users/x/dsh-collab/data/reflect/a\0b.md', '/Users/x'));
  t('落盘设备段不匹配', () => assertDeviceInPath('/Users/x/dsh-collab/data/reflect/cards/mbp/a.md', 'mac-mini', '/Users/x'));
  t('事件流非对象', () => assertEventsDoc([]));
  t('事件流 events 非数组', () => assertEventsDoc({ events: 'nope' }));
  t('事件流为空', () => assertEventsDoc({ events: [] }));
  t('事件缺 id', () => assertEventsDoc({ events: [{ source: 'files', path: '/a' }] }));
  t('事件 id 重复', () => assertEventsDoc({ events: [{ id: 'E1', source: 'files', path: '/a' }, { id: 'E1', source: 'files', path: '/b' }] }));
  t('事件无 path/key/desc', () => assertEventsDoc({ events: [{ id: 'E1', source: 'files' }] }));
  t('建议类型越界', () => resolveSuggestionType('随便'));
  t('回读为空（404/400 当成功）', () => assertReadback({ a: 1 }, null, 'notes/x/y'));
  t('★ 回读是空壳 {}（R003 通告第③条：纯状态码校验会漏）', () => assertReadback({ a: 1 }, {}, 'data/reflect/cards/mac-mini/2026-09-10'));
  t('回读是空数组 []', () => assertReadback({ a: 1 }, [], 'notes/x/y'));
  t('回读是空白串', () => assertReadback({ a: 1 }, '   ', 'notes/x/y'));
  t('回读内容不一致', () => assertReadback({ a: 1 }, { a: 2 }, 'notes/x/y'));
  t('状态机跳步 planned→board_written', () => makeDispatchStateMachine('t').to('board_written'));
  t('状态机未知状态', () => makeDispatchStateMachine('t').to('teleported'));

  return cases;
}

/** 正例：合法输入必须能通过（防"门太宽把功能也拦了"）。 */
export function gatePositiveCases(index = fixtureIndex()) {
  const out = [];
  const p = (name, fn, expect) => {
    try { const v = fn(); out.push({ name, ok: true, got: typeof v === 'object' ? JSON.stringify(v).slice(0, 70) : String(v).slice(0, 70), expect }); }
    catch (e) { out.push({ name, ok: false, err: `[${e.code}] ${e.message}`, expect }); }
  };

  p('夹具甲短键可解析', () => assertTargetExists('aaaaaaaa', index).agentId, 'session-aaaaaaaa-…');
  p('完整 id 亦可解析', () => assertTargetExists('session-aaaaaaaa-1111-2222-3333-444444444444', index).shortKey, 'aaaaaaaa');
  p('夹具乙短键可解析', () => assertTargetExists('bbbbbbbb', index).shortKey, 'bbbbbbbb');
  p('--agents 有效列表', () => resolveAgentFilter(['aaaaaaaa', 'bbbbbbbb'], index).length, '2');
  p('正常通知生成（设备级卡键）', () => { const n = buildNotice(cardKeyFor('mac-mini', '2026-09-10')); return `${n.chars}字 ${n.text}`; }, '≤50 字且含黑板键');
  p('合法黑板键', () => assertBoardKey('data/reflect/cards/mac-mini/2026-09-10'), '合法');
  p('合法键：后续段含大写/数字/-/_/.', () => assertBoardKey('data/reflect/A-1_x.json'), '合法');
  p('合法键：首段斜杠会被归一', () => assertBoardKey('/data/reflect/x'), '合法');
  p('合法写盘路径', () => assertWithinReflectRoot('/Users/x/dsh-collab/data/reflect/cards/mac-mini/20260910/a.md', '/Users/x'), '在根内');
  p('合法事件流', () => assertEventsDoc({ events: [{ id: 'E1', source: 'files', path: '/a/b.md', desc: 'x' }] }).events.length, '1');
  p('冻结的四种建议类型', () => SUGGESTION_TYPES.map(resolveSuggestionType).join(','), SUGGESTION_TYPES.join(','));
  p('回读一致', () => assertReadback({ a: 1 }, { a: 1 }, 'data/reflect/cards/mac-mini/2026-09-10').ok, 'true');
  p('状态机完整链', () => { const m = makeDispatchStateMachine('t'); ['carded', 'board_written', 'readback_ok', 'recorded'].forEach((s) => m.to(s)); return m.state; }, 'recorded');
  p('冻结常量已冻结', () => [Object.isFrozen(ALLOWED_COMMANDS), Object.isFrozen(ALLOWED_HOSTS), Object.isFrozen(SUGGESTION_TYPES), Object.isFrozen(DISPATCH_STATES), Object.isFrozen(BOARD_TARGETS), Object.isFrozen(CANDIDATE_DEVICES), Object.isFrozen(DEVICE_STATUS), Object.isFrozen(SECRET_PATTERNS)].every(Boolean), 'true');
  // ---- 跨设备层新增正例 ----
  p('四台候选设备名均合法', () => CANDIDATE_DEVICES.map(assertDeviceName).join(','), CANDIDATE_DEVICES.join(','));
  p('设备段匹配（mbp 的卡写 mbp 段）', () => assertDeviceSegment('data/reflect/cards/mbp/2026-09-10', 'mbp', ['mac-mini', 'mbp']).device, 'mbp');
  p('三件套 key 可构造', () => [cardKeyFor('mac-mini', '2026-09-10'), eventsKeyFor('mac-mini', '2026-09-10'), answersKeyFor('mac-mini', '2026-09-10')].join(' | '), 'cards/events/answers');
  p('落盘设备段匹配', () => assertDeviceInPath('/Users/x/dsh-collab/data/reflect/cards/mac-mini/20260910/a.md', 'mac-mini', '/Users/x'), '匹配');
  p('补派已加 --allow-late', () => { const r = assertNotLate('20260908', '20260910', true); return `late=${r.late} lateDays=${r.lateDays}`; }, 'late=true lateDays=2');
  p('当天不算迟到', () => JSON.stringify(assertNotLate('20260910', '20260910', false)), '{"late":false,...}');
  p('四种派发状态均合法', () => DEVICE_STATUS.map(resolveStatus).join(','), DEVICE_STATUS.join(','));
  p('★ 凭据脱敏自证（7 类样本 + 假阳性检查）', () => { const r = scrubSelfTest(); if (!r.ok) throw new Error(JSON.stringify(r)); return `${r.samples.length}/7 类被脱敏、原文未残留、幂等；普通技术文本未被误改=${r.benignUntouched}`; }, '全部通过');
  p('★ 空壳判定口径（{} / [] / 空白 / null 为空壳；非空对象不是）', () => {
    const cases = [[{}, true], [[], true], ['   ', true], [null, true], [undefined, true], [{ a: 1 }, false], ['x', false], [0, false], [false, false]];
    const bad = cases.filter(([v, want]) => isEmptyShell(v) !== want);
    if (bad.length) throw new Error(`口径不符: ${JSON.stringify(bad)}`);
    return `${cases.length}/${cases.length} 条符合（内容口径，非状态码口径）`;
  }, '全部符合');

  return out;
}

export const GATE_META = Object.freeze({
  principle: 'R006#10：没有那个入口 + 没有那个能力 + 有那个证明 + 失败即停',
  notHappens: '假装派发了（写了卡但没送达 / 送达没验 / 目标不存在时静默跳过）· 跨设备污染（A 设备的卡写进 B 设备段）· 凭据跨设备扩散 · 把"离线待取"记成失败',
  doorTypes: Object.freeze(['入口门', '类型锁', 'Schema 门', '状态机']),
  noticeMaxChars: NOTICE_MAX_CHARS,
  suggestionTypes: SUGGESTION_TYPES,
  allowedCommands: ALLOWED_COMMANDS,
  allowedHosts: ALLOWED_HOSTS,
  boardTargets: BOARD_TARGETS,
  candidateDevices: CANDIDATE_DEVICES,
  deviceStatus: DEVICE_STATUS,
  secretKinds: Object.freeze(SECRET_PATTERNS.map((p) => p.kind)),
  reflectRootRel: REFLECT_ROOT_REL
});
