/**
 * gate.js — R006 ⑩ 结构门：约束前置 · 不可绕过
 * =============================================================================
 * 本工具有四条"不该发生路径"，全部在**结构上**封死（不是"检查后放行"）：
 *
 *   P1 自动决定入册什么 → **没有那个入口**：唯一入口是"用户裁定"（裁定文件 / --rule CLI）。
 *                          decision 与 target 都是**冻结枚举**；本模块不导出任何"生成裁定"的函数，
 *                          也不存在 autoDecide / force / 默认裁定 这类开关。
 *   P2 删除任何条目     → **没有那个能力**：源码内零删除原语（unlink/rm/rmdir/truncate…），
 *                          唯一的写形态是"读取 → 追加 → 原子覆盖"；写入后断言条目数**严格 +N**。
 *   P3 重复入册         → **幂等门**：已入册台账（data/reflect/enrolled.json）+ 编号唯一性查重，命中即拒。
 *   P4 写坏目标文件     → **原子写 + 回读校验 + 自动回滚**：备份前置（回读验证可解析）→ .tmp 写入
 *                          → 校验可解析 → rename 覆盖 → 回读校验 → 任一环失败即从备份回滚。
 *
 * 另：本工具**零 shell 出站**（不 import child_process，无 exec/spawn 调用点）；
 *     唯一对外通道是黑板 HTTP，且目标主机必须在冻结出站白名单内（assertBbHost）。
 *
 * 说明（如实标注，不冒充）：下面的源码扫描是「去注释/字符串/正则字面量后的结构扫描」，
 * 不是完整 AST —— 本包零外部依赖，宿主内没有可用的解析器。命名与输出都按此标注。
 */

import pathMod from 'node:path';

export class GateError extends Error {
  constructor(code, message) {
    super(message);
    this.name = 'GateError';
    this.code = code;
  }
}

/* ══════════════════════════ 冻结枚举（类型锁 / schema 门） ══════════════════════════ */

/** 用户裁定结果：只有这四种。没有 'auto'/'force'/'yes' —— 工具不能自己拍板。 */
export const DECISIONS = Object.freeze(['approve', 'reject', 'modify', 'defer']);

/** 入册目标：只有这四种。没有 'delete'/'drop'/'all' —— 工具不能删。 */
export const TARGETS = Object.freeze(['philosophy', 'rule', 'spec', 'archive']);

/** 会写"治理库"的两个目标（其余两个只写 SOP / 案例归档区，不碰治理库）。 */
export const LIBRARY_TARGETS = Object.freeze(['philosophy', 'rule']);

/** 哲学条目可选状态（枚举，不接受自由字符串）。 */
export const PHILOSOPHY_STATUS = Object.freeze(['active', 'draft']);

/** 规则状态（枚举）。 */
export const RULE_STATUS = Object.freeze(['enforced', 'draft']);

/** 新哲学必填字段（R006/规格：id/name/core/origin/doc/order/status）。 */
export const PHILOSOPHY_REQUIRED_FIELDS = Object.freeze(['id', 'name', 'core', 'origin', 'doc', 'order', 'status']);

/** 新规则必填字段（rules.json schema 对齐）。 */
export const RULE_REQUIRED_FIELDS = Object.freeze([
  'id', 'name', 'category', 'scope', 'status', 'version', 'summary', 'detail', 'enforcedBy', 'added', 'approvedBy'
]);

/** 出站白名单（冻结）：黑板只允许这两个来源。113 之外的任何主机 → GateError。 */
export const ALLOWED_BB_HOSTS = Object.freeze(['127.0.0.1', 'localhost', '::1', '106.53.214.108']);

/** 出站协议白名单（冻结）：只允许 http（黑板是明文内网通道）。 */
export const ALLOWED_BB_SCHEMES = Object.freeze(['http:']);

/** 哲学/规则的 id 形态（冻结正则，防注入与越界命名）。 */
export const PHILOSOPHY_ID_RE = /^phi-[a-z0-9][a-z0-9-]{1,48}$/;
export const RULE_ID_RE = /^(R[0-9]{3}|R-ERR[0-9]+|J[0-9]{1,3})$/;
export const SLUG_RE = /^[a-z0-9][a-z0-9-]{1,63}$/;

/**
 * 危险原语（删除/终止类）。本模块**只用于"证明源码里没有它们"**，
 * 不导出任何能执行它们的包装 —— 有那个检查 ≠ 有那个能力。
 */
export const DANGEROUS_PRIMITIVES = Object.freeze([
  'unlink', 'unlinkSync', 'rmdir', 'rmdirSync', 'rm', 'rmSync', 'truncate', 'truncateSync',
  'killall', 'pkill', 'taskkill'
]);

/** 允许被本工具执行的外部命令：**空集**（本工具不需要任何外部命令）。 */
export const ALLOWED_COMMANDS = Object.freeze([]);

/* ------------- 跨设备层（v1.1）：写入命名空间门 + 凭据门 ------------- */

/**
 * 允许写入的黑板 key 前缀（冻结）。跨设备后**只写自己命名空间下的 key**：
 *   · data/reflect/  —— 自己的反思域（全卡、事件、派卡）
 *   · data/registry/ —— 自己的登记卡（规则变更通知，供全设备检索）
 *   · notes/         —— **仅**限"短指引"待投递队列（≤50 字，不含正文）
 */
export const ALLOWED_WRITE_PREFIXES = Object.freeze(['data/reflect/', 'data/registry/', 'notes/']);

/** 卡片正文类 key 的允许前缀（更严：正文只能落在自己的两个 data 域）。 */
export const CARD_PREFIXES = Object.freeze(['data/reflect/', 'data/registry/']);

/** 短指引待投递队列的前缀（离线设备上线后自取）。 */
export const POINTER_PREFIX = 'notes/';

/** 短指引正文长度上限（总线 v2.4 / R033：内容>50字走黑板，只发最短指引）。 */
export const MAX_POINTER_CHARS = 50;

/**
 * 凭据形态（冻结）：用于**落盘前 / 上黑板前**的扫描与脱敏（Φ12 形态④ 凭据跨设备扩散）。
 * ★ 刻意**不**含"泛化长十六进制/base64"：那会把正常 sha256/uid 一起打码 —— 门太宽会砍掉自己人（R006 坑#1）。
 *   只认有辨识度的前缀形态 + 赋值/Authorization 形态。
 */
export const CREDENTIAL_PATTERNS = Object.freeze([
  { kind: 'openai-key', re: /\bsk-[A-Za-z0-9_-]{16,}/ },
  { kind: 'github-token', re: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}/ },
  { kind: 'github-pat', re: /\bgithub_pat_[A-Za-z0-9_]{20,}/ },
  { kind: 'slack-token', re: /\bxox[baprs]-[A-Za-z0-9-]{10,}/ },
  { kind: 'aws-akid', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { kind: 'google-api-key', re: /\bAIza[0-9A-Za-z_-]{20,}/ },
  { kind: 'dify-app-key', re: /\bapp-[a-z0-9]{16,}\b/ },
  { kind: 'private-key-block', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { kind: 'bearer-header', re: /\bBearer\s+[A-Za-z0-9_\-.=]{16,}/ },
  { kind: 'assigned-secret', re: /\b(?:password|passwd|secret|token|api[_-]?key|apikey|access[_-]?key)\s*[:=]\s*["']?[A-Za-z0-9_\-.\/+]{12,}/i, globalFlag: true },
  { kind: 'bb-writer-token', re: /\bX-Writer\b\s*[:=]\s*\S{8,}/i }
]);

/** 扫描凭据形态：返回 [{kind, line, sample(截断打码)}] */
export function scanCredentials(text) {
  const hits = [];
  String(text).split('\n').forEach((line, idx) => {
    for (const p of CREDENTIAL_PATTERNS) {
      const re = new RegExp(p.re.source, p.re.flags.replace('g', ''));
      if (re.test(line)) hits.push({ kind: p.kind, line: idx + 1, sample: (line.match(re) || [''])[0].slice(0, 6) + '…' });
    }
  });
  return hits;
}

/** 脱敏：把命中的凭据形态替换为 «REDACTED:kind»（**不拒绝发布**，但留痕并上报）。 */
export function redactCredentials(text) {
  let out = String(text);
  const hits = [];
  for (const p of CREDENTIAL_PATTERNS) {
    const re = new RegExp(p.re.source, p.re.flags.includes('g') ? p.re.flags : p.re.flags + 'g');
    out = out.replace(re, (m) => { hits.push({ kind: p.kind, sample: `${m.slice(0, 6)}…（${m.length} 字符）` }); return `«REDACTED:${p.kind}»`; });
  }
  return { text: out, hits };
}

/** 递归脱敏（黑板 value 用）：所有字符串字段先过 redactCredentials。 */
export function redactDeep(v) {
  if (typeof v === 'string') return redactCredentials(v).text;
  if (Array.isArray(v)) return v.map(redactDeep);
  if (v && typeof v === 'object') {
    const o = {};
    for (const [k, x] of Object.entries(v)) o[k] = redactDeep(x);
    return o;
  }
  return v;
}

/* ------------- R003 补充（2026-09-11 通告）：400/404 语义 + 空壳键 ------------- */

/**
 * 黑板 HTTP 响应的语义分类（纯函数，便于负例实测）。
 * 依据 R003 补充通告（`data/registry/r003-key-syntax-notice-20260911`，HR 司库 2026-09-11）：
 *   · **400 = 写法非法（键错）** —— "你以为写了，其实被拒"
 *   · **404 = 格式合法但不存在（内容缺失）**
 *   · **空壳键**（键存在但 value={}）—— **纯状态码校验会漏**，必须验内容
 *   · 因此：**写入必须回读确认**（回读 200 **且** value 非空 **且** 内容命中标记）
 * kind：ok | bad-key | not-found | empty-shell | marker-missing | error
 */
export function classifyBbReadback({ status = 0, body = '', marker = null, expected = undefined, transportError = null } = {}) {
  const text = String(body || '');
  let parsed = null;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = null; }
  const err = parsed && typeof parsed === 'object' ? String(parsed.error || '') : '';
  if (transportError) return { kind: 'error', landed: false, semantics: `传输失败：${transportError}` };
  if (status === 400 || /bad key/i.test(err)) {
    return { kind: 'bad-key', landed: false, semantics: '400 = 写法非法（键错）—— 你以为写了，其实被拒（首段须纯小写字母 [a-z]+）' };
  }
  if (status === 404 || /not found/i.test(err)) {
    return { kind: 'not-found', landed: false, semantics: '404 = 格式合法但不存在（内容缺失）' };
  }
  if (status !== 200) return { kind: 'error', landed: false, semantics: `HTTP ${status}（非 200/400/404）` };
  const v = parsed && typeof parsed === 'object' ? parsed.value : undefined;
  const emptyShell = v === undefined || v === null || (typeof v === 'object' && !Array.isArray(v) && Object.keys(v).length === 0);
  if (emptyShell) {
    return { kind: 'empty-shell', landed: false, semantics: '键存在但 value 为空（空壳键）—— 纯状态码校验会漏，必须验内容' };
  }
  if (marker && !text.includes(marker)) {
    return { kind: 'marker-missing', landed: false, semantics: `回读 200 但内容未命中标记（marker='${marker}'）—— 视为未落地` };
  }
  // ★ 内容深比对（对齐 bb-write.py v1.0.2 的 sort_keys 规范化深比对）：
  //   只靠"标记字符串命中"会被**截断**或**并发覆盖**骗过（标记还在，其余字段已变）。
  if (expected !== undefined) {
    const mismatch = diffWrittenVsReadback(expected, v);
    if (mismatch.length) {
      return { kind: 'mismatch', landed: false, semantics: `回读 200 但内容与写入不符（字段: ${mismatch.join(',')}）—— 疑似截断/被并发覆盖（标记命中不够）` };
    }
  }
  return { kind: 'ok', landed: true, semantics: '回读 200 + value 非空 + 内容深比对一致（真落地）' };
}

/** 规范化序列化（键排序）—— 黑板服务端会重排嵌套对象键序，直接 str 比对会假阳性。 */
export function canonicalJson(x) {
  const canon = (v) => {
    if (Array.isArray(v)) return v.map(canon);
    if (v && typeof v === 'object') {
      const o = {};
      for (const key of Object.keys(v).sort()) o[key] = canon(v[key]);
      return o;
    }
    return v;
  };
  try { return JSON.stringify(canon(x)); } catch { return String(x); }
}

/** 逐字段深比对「写入值 vs 回读值」，返回不一致的顶层字段（防截断/被并发覆盖）。 */
export function diffWrittenVsReadback(written, readbackValue) {
  const a = written && typeof written === 'object' ? written : {};
  const b = readbackValue && typeof readbackValue === 'object' ? readbackValue : {};
  const mismatch = [];
  for (const k of Object.keys(a)) {
    if (!(k in b) || canonicalJson(a[k]) !== canonicalJson(b[k])) mismatch.push(k);
  }
  return mismatch;
}

/** 断言「真的落地」：非 landed（400/404/空壳/标记未命中/传输失败）→ 抛 GateError（失败即停）。 */
export function assertLanded(cls, { key = '' } = {}) {
  if (!cls || cls.kind !== 'ok' || !cls.landed) {
    throw new GateError('BB_WRITE_NOT_LANDED', `拒绝：黑板写入未落地（${key}）—— ${cls ? cls.semantics : '无分类结果'}`);
  }
  return true;
}

/** 递归脱敏并**统计**命中的凭据（黑板 value 用；返回 {value, hits}）。 */
export function redactDeepCounted(v) {
  const hits = [];
  const walk = (x) => {
    if (typeof x === 'string') { const r = redactCredentials(x); hits.push(...r.hits); return r.text; }
    if (Array.isArray(x)) return x.map(walk);
    if (x && typeof x === 'object') { const o = {}; for (const [k, y] of Object.entries(x)) o[k] = walk(y); return o; }
    return x;
  };
  return { value: walk(v), hits };
}

/**
 * 凭据门（fail-closed，纵深防御）：脱敏之后**再断言一次**，只要还残留凭据形态就**拒绝写**。
 * 顺序是"先脱敏再断言"，所以正常情况下永远通过；一旦脱敏逻辑漏了某种形态，
 * 这里会**挡住写入**而不是把凭据发出去（这正是"失败即停"）。
 */
export function assertNoCredentials(text, { where = '输出' } = {}) {
  const hits = scanCredentials(text);
  if (hits.length) {
    throw new GateError('CREDENTIAL_LEAK',
      `拒绝：${where} 仍含凭据形态（${hits.map((h) => `${h.kind}@L${h.line}`).join(', ')}）。` +
      `本工具在落盘与上黑板前强制脱敏 + 复检，复检不通过即拒绝写入（凭据不许跨设备扩散）。`);
  }
  return true;
}

/**
 * 写入 key 门（跨设备安全约束）：key 语法 + 命名空间白名单 + 指针正文长度。
 * 语法依据（2026-09-10 实测）：黑板 key 首段命名空间**必须是纯小写字母 [a-z]+**；
 * `cld-health/...` 这类会被黑板判 400 bad key —— 所以先在本机拦下，别把 400 当成功。
 */
/**
 * key 规范校验（**与 scripts/bb-write.py v1.0.2 的 validate_key 逐条比对过**，差异见 docs/README §⑨ 一致性矩阵）。
 * 规范（2026-09-11 与 bb-write.py 对账后确定）：
 *   ① 允许前导 `/`（归一化后处理）
 *   ② **至少两段**，且**每段非空** —— 单段是黑板的"命名空间列举"端点（GET 返回 {list,total}），写它等于写错对象；
 *      尾斜杠/空段（`data/reflect/`、`data//key`）同样拒
 *   ③ 首段必须**纯小写字母** [a-z]+ —— 否则黑板返回 **400 bad key（不是 404！）**
 *   ④ 任何段不得含空白（空格会被 URL 处理破坏）
 */
export function inspectWriteKey(key) {
  const raw = String(key || '');
  if (!raw) return { ok: false, why: 'key 为空' };
  if (/\s/.test(raw)) return { ok: false, why: `key 含空白字符：'${raw}'（空白会被 URL 处理破坏）` };
  const k = raw.replace(/^\/+/, '').replace(/\/+$/, (m) => (raw.endsWith('/') ? '/' : ''));   // 仅归一化前导斜杠，保留尾斜杠以便报错
  const segs = k.split('/');
  if (segs.length < 2) {
    return { ok: false, why: `key 需至少两段（如 data/<域>/<键>）：'${raw}' —— **单段是黑板的"命名空间列举"端点**（GET 返回 {list,total}），写它等于写错对象` };
  }
  if (segs.some((x) => x.length === 0)) {
    return { ok: false, why: `key 含空段（尾斜杠或双斜杠）：'${raw}' —— 指向的是命名空间端点而非具体键` };
  }
  if (!/^[a-z]+$/.test(segs[0])) {
    return { ok: false, why: `★ key 写法非法：首段须纯小写字母 [a-z]+，当前首段='${segs[0]}' → 将返回 **400 bad key（不是 404！）**。合法示例：data/<域>/<键> / notes/<节点>/<键>` };
  }
  if (segs.some((s) => s === '.' || s === '..')) {
    return { ok: false, why: `key 含点段（. 或 ..）：'${raw}' —— 黑板会做**路径归一化**：实测 GET /data/nonexistent/.. → **200 但 body 是 {list,total} 命名空间列举**（与尾斜杠同一个坑：回读判据必然假通过）` };
  }
  // ★ 实测字符类（2026-09-11 · 只读 GET 真黑板 · 对 20195 个真实键**零误伤**）：
  //   %  &  ;  +  =  :  与非 ASCII  → 黑板 **400 bad key**（本地校验器若放过 = "校验通过但服务端 400"）
  //   允许：字母数字 . - _ ? #（`?`/`#` 实测 404 = 语法合法，会被当作键名字面量）
  const badCh = /[%&;+=:]/.exec(k);
  if (badCh) {
    return { ok: false, why: `key 含黑板判为 400 的字符 '${badCh[0]}'：'${raw}' —— 实测 GET /data/nonexistent/a${badCh[0]}b → **400 bad key**（本地校验通过 ≠ 远端接受）` };
  }
  const nonAscii = [...k].find((c) => c.charCodeAt(0) > 127);
  if (nonAscii) {
    return { ok: false, why: `key 含非 ASCII 字符 '${nonAscii}'：'${raw}' —— 实测 GET /data/nonexistent/键名 → **400 bad key**` };
  }
  return { ok: true, why: '语法合法', normalized: segs.join('/'), segmentCount: segs.length };
}

export function assertWriteKey(key, { kind = 'card', text = null } = {}) {
  const k = String(key || '');
  const insp = inspectWriteKey(k);
  if (!insp.ok) throw new GateError('BAD_BB_KEY', `拒绝：${insp.why}`);
  const allowed = kind === 'pointer' ? [POINTER_PREFIX] : CARD_PREFIXES;
  if (!allowed.some((p) => insp.normalized.startsWith(p))) {
    throw new GateError('KEY_OUT_OF_NAMESPACE',
      `拒绝：${kind === 'pointer' ? '短指引' : '卡片正文'} key '${k}' 不在允许前缀 [${allowed.join(', ')}] 内 —— 本工具只写自己命名空间下的 key，不越权写别人目录。`);
  }
  if (kind === 'pointer') {
    if (typeof text !== 'string' || text.length === 0) throw new GateError('POINTER_EMPTY', `拒绝：短指引正文为空: ${k}`);
    if (text.length > MAX_POINTER_CHARS) {
      throw new GateError('POINTER_TOO_LONG',
        `拒绝：短指引 ${text.length} 字 > ${MAX_POINTER_CHARS} 字上限（总线 v2.4 / R033：内容>50字走黑板，只发最短指引）。请把正文落黑板，再发「看黑板 <key>」。`);
    }
  }
  return k;
}

/* ══════════════════════════ 纯校验器（负例矩阵实测的对象） ══════════════════════════ */

/** 裁定结果必须是冻结枚举之一（大小写敏感、不接受空白）。 */
export function assertDecision(v) {
  if (typeof v !== 'string' || !DECISIONS.includes(v)) {
    throw new GateError('BAD_DECISION',
      `拒绝：裁定结果 '${v}' 不是合法值。只接受 ${DECISIONS.join(' / ')}——` +
      `本工具**不能自己拍板**（phi-user-sovereignty：执行需人类确认），所以不存在 'auto'/'force' 这种取值。`);
  }
  return v;
}

/** 入册目标必须是冻结枚举之一。 */
export function assertTarget(v) {
  if (typeof v !== 'string' || !TARGETS.includes(v)) {
    throw new GateError('BAD_TARGET',
      `拒绝：入册目标 '${v}' 不是合法值。只接受 ${TARGETS.join(' / ')}——` +
      `本工具**没有删除能力**，"delete"/"drop"/"all" 这类目标在语法上不存在。`);
  }
  return v;
}

/** slug（SOP 文件名 / 哲学 id 片段）：封闭字符集，杜绝路径穿越与扩展名注入。 */
export function assertSlug(v, what = 'slug') {
  if (typeof v !== 'string' || !SLUG_RE.test(v)) {
    throw new GateError('BAD_SLUG',
      `拒绝：${what} '${v}' 非法。只允许 ^[a-z0-9][a-z0-9-]{1,63}$（纯小写字母数字连字符，禁止 / . \\ .. 空格）。`);
  }
  return v;
}

/** 路径必须落在 root 之内（防 ../ 逃逸到库外文件）。 */
export function assertInsideRoot(root, abs) {
  const { resolve, sep } = pathMod;
  const r = resolve(root);
  const a = resolve(abs);
  if (a !== r && !a.startsWith(r.endsWith(sep) ? r : r + sep)) {
    throw new GateError('PATH_ESCAPE', `拒绝：路径 '${a}' 逃出 root '${r}' —— 本工具只写 root 内的目标文件。`);
  }
  return a;
}

/** 编号唯一性：新 id 不得已存在于库中（编号冲突即拒）。 */
export function assertIdUnique(existingIds, id) {
  if (existingIds.includes(id)) {
    throw new GateError('ID_CONFLICT',
      `拒绝：编号 '${id}' 已存在于目标库（现有编号 ${existingIds.length} 个）。` +
      `本工具不覆盖、不删除已有条目——请人手动处理或换一个编号。`);
  }
  return id;
}

/** 幂等门：同一 proposal_id 已入册即拒（防重复追加）。 */
export function assertNotEnrolled(ledgerEntries, proposalId) {
  const hit = (ledgerEntries || []).find((e) => e.proposal_id === proposalId && e.outcome === 'enrolled');
  if (hit) {
    throw new GateError('DUPLICATE_ENROLL',
      `拒绝：提案 '${proposalId}' 已于 ${hit.ts} 入册（target=${hit.target}, ref=${hit.ref}）。` +
      `同一提案不允许重复入册——如需变更请由人手动修订（本工具无删除/覆盖能力）。`);
  }
  return proposalId;
}

/**
 * 出站主机门（冻结白名单）：返回规范化 URL；非白名单主机 → GateError。
 * 这是"唯一对外通道"的约束——本工具不发消息、不跑命令，只写黑板。
 */
export function assertBbHost(raw) {
  let u;
  try { u = new URL(String(raw)); }
  catch { throw new GateError('BAD_BB_URL', `拒绝：黑板地址 '${raw}' 不是合法 URL。`); }
  if (!ALLOWED_BB_SCHEMES.includes(u.protocol)) {
    throw new GateError('BAD_BB_SCHEME', `拒绝：黑板协议 '${u.protocol}' 不在白名单 [${ALLOWED_BB_SCHEMES.join(', ')}]。`);
  }
  const host = u.hostname.replace(/^\[|\]$/g, '');
  if (!ALLOWED_BB_HOSTS.includes(host)) {
    throw new GateError('BB_HOST_FORBIDDEN',
      `拒绝：出站主机 '${host}' 不在冻结白名单 [${ALLOWED_BB_HOSTS.join(', ')}]。` +
      `本工具只写本地/中枢黑板，不接受任意外发目标。`);
  }
  return u;
}

/* ══════════════════════════ 源码结构扫描（去字面量） ══════════════════════════ */

/**
 * 去注释 / 字符串 / 模板 / 正则字面量（**行号与偏移保持不变**，字面量被空格替换）。
 * 为什么必须去掉：R006 坑#2 —— 直接扫原文会把"检测用的正则/帮助文本"当成危险调用（假阳性）。
 * 所以被检查的对象是"代码里真的调用了什么"，不是文档怎么说。
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

/**
 * A 项扫描：源码内是否存在删除/终止类原语。
 * 注意边界符 `[^\w$]`（允许 `.` 前缀）—— 因为 fs.rmSync/fs.unlinkSync 这类是合法要抓的目标；
 * 本工具源码里不出现 `.exec(` 之类的同名方法（scanExecSites 用更严的边界，见下）。
 */
export function scanDangerousPrimitives({ sources }) {
  const hits = [];
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    code.split('\n').forEach((line, idx) => {
      for (const name of DANGEROUS_PRIMITIVES) {
        if (new RegExp(`(^|[^\\w$])${name}\\s*\\(`).test(line)) hits.push({ file, line: idx + 1, callee: name });
      }
      if (/process\s*\.\s*kill\s*\(/.test(line)) hits.push({ file, line: idx + 1, callee: 'process.kill' });
    });
  }
  return hits;
}

/**
 * F 项扫描①：枚举全部外部命令执行点（exec/execFile/spawn/…）并**回原文读实参**。
 * 步骤（R006 坑#3 的解法）：在去字面量的代码上定位调用点 → 回到原文同偏移处读第一个实参。
 * 边界用 `(?<![\w.$])`：把正则/自定义对象的 `.exec(` 排除（否则会把自己的检测正则当靶子）。
 */
export function scanExecSites({ sources }) {
  const sites = [];
  const callRe = /(?<![\w.$])(execFileSync|execFile|execSync|exec|spawnSync|spawn)\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw); // 与原文等长 → 偏移可对齐
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
 * F 项扫描②：枚举对外 HTTP 调用点（本工具唯一的出站通道）。
 * 同样"去字面量定位 + 回原文读实参"，并回报**所在函数**，
 * 以便断言"所有出站都必须经过 bbPut 且 bbPut 内先过 assertBbHost"。
 */
export function scanOutboundSites({ sources }) {
  const sites = [];
  const re = /(^|[^\w$])(https?)\s*\.\s*request\s*\(|(?<![\w.$])fetch\s*\(/g;
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripLiterals(raw);
    const ranges = functionRanges(code);
    let m;
    while ((m = re.exec(code)) !== null) {
      const line = code.slice(0, m.index).split('\n').length;
      const fn = ranges.find((r) => m.index >= r.start && m.index < r.end);
      sites.push({ file, line, callee: m[2] ? `${m[2]}.request` : 'fetch', fn: fn ? fn.name : null });
    }
  }
  return sites;
}

/**
 * 只去注释（**保留字符串字面量**）。用途：检查 import/require 的模块说明符
 * （说明符是字符串，必须保留），同时不把注释里提到的模块名当靶子（R006 坑#2）。
 */
export function stripComments(src) {
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
      out += src.slice(i, j); i = j; continue;   // ★ 字符串原样保留
    }
    out += c; i++;
  }
  return out;
}

/**
 * 检查是否 **import/require** 了某个模块（按说明符子串匹配）。
 * 只匹配"模块说明符"，不匹配注释或普通文档字符串 —— 因此本工具在文档里写
 * "不 import child_process" 不会被自己判成违规（R006 坑#2 的第二次踩点）。
 */
export function scanModuleRefs({ sources, needle }) {
  const hits = [];
  const re = new RegExp(`(?:^|[^\\w$.])(?:import|require|from)\\s*\\(?[^\\n;]*?['"\`][^'"\`]*${needle}[^'"\`]*['"\`]`, 'g');
  for (const [file, raw] of Object.entries(sources)) {
    const code = stripComments(raw);
    code.split('\n').forEach((line, idx) => { if (re.test(line)) { re.lastIndex = 0; hits.push({ file, line: idx + 1 }); } re.lastIndex = 0; });
  }
  return hits;
}

/** 用大括号配对（在去字面量的代码上计数 → 字符串/注释里的括号不会干扰）求函数体范围。 */
export function functionRanges(code) {
  const out = [];
  const re = /(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/g;
  let m;
  while ((m = re.exec(code)) !== null) {
    // ① 先跨过**参数表**（参数默认值里可能有 {}，例如 ({a = 1} = {})），
    //    否则会把参数里的花括号当成函数体（本工具真踩过：出站点 fn 解析成 null）
    let p = code.indexOf('(', m.index);
    let pdepth = 0, q = p;
    for (; q < code.length; q++) {
      if (code[q] === '(') pdepth++;
      else if (code[q] === ')') { pdepth--; if (pdepth === 0) { q++; break; } }
    }
    const i = code.indexOf('{', q);
    if (i < 0) continue;
    let depth = 0;
    for (let j = i; j < code.length; j++) {
      if (code[j] === '{') depth++;
      else if (code[j] === '}') { depth--; if (depth === 0) { out.push({ name: m[1], start: m.index, end: j + 1 }); break; } }
    }
  }
  return out;
}

/** 断言：某个函数体内确实调用了守卫（默认 assertBbHost）。 */
export function functionCallsFn(raw, fnName, guardName) {
  const ranges = functionRanges(stripLiterals(raw));
  const r = ranges.find((x) => x.name === fnName);
  if (!r) return false;
  return stripLiterals(raw.slice(r.start, r.end)).includes(`${guardName}(`);
}

/* ══════════════════════════ 负例 / 正例矩阵（lean4-check B、C 实测对象） ══════════════════════════ */

/** 负例：逐条实测，全部必须被拒（code===null 表示"竟然放过了"= 门失效）。 */
export function gateNegativeCases() {
  const cases = [];
  const rec = (label, fn) => {
    try { fn(); cases.push({ label, code: null }); }
    catch (e) { cases.push({ label, code: e.code || 'ERROR' }); }
  };
  for (const d of ['auto', 'yes', 'force', 'ok', 'APPROVE', 'approve ', '', '   ', '全部', 'null']) {
    rec(`decision=${JSON.stringify(d)}`, () => assertDecision(d));
  }
  for (const t of ['delete', 'drop', 'remove', 'all', '*', 'philosophies', 'PHILOSOPHY', 'philosophy ', '', 'null']) {
    rec(`target=${JSON.stringify(t)}`, () => assertTarget(t));
  }
  for (const s of ['../evil', 'a/b', '..', '.', 'x.md', '', '  ', 'x y', 'X', '-lead', '__proto__']) {
    rec(`slug=${JSON.stringify(s)}`, () => assertSlug(s));
  }
  for (const u of ['http://evil.example.com', 'ftp://127.0.0.1', 'https://127.0.0.1:8792',
    'http://127.0.0.1.evil.com', 'file:///etc/passwd', 'http://10.0.0.9:8792', '']) {
    rec(`bbUrl=${JSON.stringify(u)}`, () => assertBbHost(u));
  }
  rec('重复编号 phi-user-sovereignty', () => assertIdUnique(['phi-user-sovereignty', 'phi-027'], 'phi-user-sovereignty'));
  rec('重复编号 R006', () => assertIdUnique(['R001', 'R006'], 'R006'));
  rec('重复入册 P1', () => assertNotEnrolled([{ proposal_id: 'P1', outcome: 'enrolled', ts: '2026-09-10', target: 'philosophy', ref: 'phi-x' }], 'P1'));
  rec('路径逃逸 root', () => assertInsideRoot('/tmp/root', '/tmp/root/../etc/passwd'));
  rec('路径逃逸 绝对路径', () => assertInsideRoot('/tmp/root', '/etc/passwd'));
  // 跨设备层 v1.1：写入命名空间门
  rec('卡片正文写进 notes/（越权）', () => assertWriteKey('notes/mbp/reflect-feedback-full', { kind: 'card' }));
  rec('卡片正文写进别人 data 域', () => assertWriteKey('data/other-domain/x', { kind: 'card' }));
  rec('key 首段含连字符（黑板会 400）', () => assertWriteKey('cld-health/x', { kind: 'card' }));
  rec('key 首段含大写', () => assertWriteKey('Data/reflect/x', { kind: 'card' }));
  rec('短指引写进 data/（越权）', () => assertWriteKey('data/reflect/feedback/x', { kind: 'pointer', text: '看黑板 x' }));
  rec('短指引正文为空', () => assertWriteKey('notes/mbp/x', { kind: 'pointer', text: '' }));
  rec('短指引正文 >50 字', () => assertWriteKey('notes/mbp/x', { kind: 'pointer', text: '看黑板 '.repeat(30) }));
  // 凭据门（fail-closed）：脱敏后仍残留凭据形态 → 必须拒绝写入
  rec('残留凭据 sk- 形态 → 拒绝写入', () => assertNoCredentials(`apikey = sk-${'A'.repeat(24)}`, { where: '反馈卡' }));
  rec('残留凭据 ghp_ 形态 → 拒绝写入', () => assertNoCredentials(`token: ghp_${'b'.repeat(24)}`));
  rec('残留凭据 X-Writer 形态 → 拒绝写入', () => assertNoCredentials('X-Writer: xxxxxxxx-token-value'));
  rec('残留凭据 password= 形态 → 拒绝写入', () => assertNoCredentials('password=SuperSecret123456'));
  // CLI 入口：--rule 的枚举在解析期就拒绝（用法错误，不是门拒绝）
  rec('--rule target 非法 =repository → 用法错误', () => assertRuleSpec('P4=approve:repository'));
  rec('--rule decision 非法 =auto → 用法错误', () => assertRuleSpec('P4=auto:philosophy'));
  rec('--rule 缺 target → 用法错误', () => assertRuleSpec('P4=approve'));
  // R003 补充：400/404/空壳键/标记未命中 都必须判为「未落地」
  rec('回读 400（bad key）→ 未落地', () => assertLanded(classifyBbReadback({ status: 400, body: '{"error":"bad key"}', marker: 'x' }), { key: 'k' }));
  rec('回读 404（not found）→ 未落地', () => assertLanded(classifyBbReadback({ status: 404, body: '{"error":"not found"}', marker: 'x' }, ), { key: 'k' }));
  rec('回读 200 但 value={} 空壳键 → 未落地', () => assertLanded(classifyBbReadback({ status: 200, body: '{"value":{},"version":1}', marker: 'x' }), { key: 'k' }));
  rec('回读 200 但无 value 字段 → 未落地', () => assertLanded(classifyBbReadback({ status: 200, body: '{"version":1}', marker: 'x' }), { key: 'k' }));
  rec('回读 200 内容未命中标记 → 未落地', () => assertLanded(classifyBbReadback({ status: 200, body: '{"value":{"other":1}}', marker: 'missing-marker' }), { key: 'k' }));
  rec('回读传输失败 → 未落地', () => assertLanded(classifyBbReadback({ transportError: 'timeout' }), { key: 'k' }));
  // 与 bb-write.py validate_key 对齐：单段 / 尾斜杠 / 空末段 / 含空白 都必须拒
  rec('单段 key（命名空间列举端点）→ 拒绝', () => assertWriteKey('data', { kind: 'card' }));
  rec('单段 key（notes）→ 拒绝', () => assertWriteKey('notes', { kind: 'card' }));
  rec('尾斜杠无末段 key → 拒绝', () => assertWriteKey('data/reflect/', { kind: 'card' }));
  rec('key 含空白 → 拒绝', () => assertWriteKey('data/reflect/my key', { kind: 'card' }));
  // 实测字符类（真黑板 400 / 路径归一化），2026-09-11 对 20195 真实键零误伤
  for (const ch of ['%', '&', ';', '+', '=', ':']) {
    rec(`key 含 '${ch}'（实测 400）→ 拒绝`, () => assertWriteKey(`data/dom/a${ch}b`, { kind: 'card' }));
  }
  rec('key 含中文（实测 400）→ 拒绝', () => assertWriteKey('data/nonexistent/键名', { kind: 'card' }));
  rec('key 含 .. 段（路径归一化→列举）→ 拒绝', () => assertWriteKey('data/nonexistent/..', { kind: 'card' }));
  rec('key 含 . 段 → 拒绝', () => assertWriteKey('data/./key', { kind: 'card' }));
  // 版本单调性门（明鉴 2026-09-11 降级事故的机器化）
  rec('version 低于 changelog 记录（2.4→1.4 降级）→ 拒绝', () => {
    if (!assertVersionMonotonic({ version: '1.4', changelog: [{ version: '2.1' }, { version: '2.0' }] })) throw new Error('应拒');
  });
  rec('version 低于 versionHistory 记录 → 拒绝', () => {
    if (!assertVersionMonotonic({ version: '1.6', versionHistory: [{ version: '2.4' }] })) throw new Error('应拒');
  });
  rec('回读内容被截断（标记仍命中）→ 未落地', () => assertLanded(classifyBbReadback({
    status: 200, marker: 'data/reflect/feedback/2026-09-10',
    body: JSON.stringify({ value: { key: 'data/reflect/feedback/2026-09-10', text: '被截断' } }),
    expected: { key: 'data/reflect/feedback/2026-09-10', text: '完整内容'.repeat(50) }
  }), { key: 'k' }));
  return cases;
}

/** --rule 语法的枚举校验（CLI 入口门）：非法值在解析期即拒（用法错误）。 */
export function assertRuleSpec(spec) {
  const m = /^([A-Za-z0-9_-]+)=([a-zA-Z-]+):([a-zA-Z-]+)$/.exec(String(spec || '').trim());
  if (!m) throw new GateError('BAD_RULE_SPEC', `用法错误：--rule 格式应为 <提案id>=<decision>:<target>，收到 '${spec}'`);
  if (!DECISIONS.includes(m[2])) throw new GateError('BAD_RULE_SPEC_DECISION', `用法错误：decision '${m[2]}' 非法`);
  if (!TARGETS.includes(m[3])) throw new GateError('BAD_RULE_SPEC_TARGET', `用法错误：target '${m[3]}' 非法`);
  return { proposal_id: m[1], decision: m[2], target: m[3] };
}

/** 正例：合法输入必须全部通过（防"门太宽把功能也砍了" —— R006 坑#1）。 */
export function gatePositiveCases() {
  const cases = [];
  const rec = (label, fn) => {
    try { cases.push({ label, ok: true, got: String(fn()) }); }
    catch (e) { cases.push({ label, ok: false, err: e.message }); }
  };
  for (const d of DECISIONS) rec(`decision=${d}`, () => assertDecision(d));
  for (const t of TARGETS) rec(`target=${t}`, () => assertTarget(t));
  rec('slug=reflect-enroll-demo', () => assertSlug('reflect-enroll-demo'));
  rec('id 唯一 phi-new-one', () => assertIdUnique(['phi-user-sovereignty'], 'phi-new-one'));
  rec('未入册提案 P9', () => assertNotEnrolled([{ proposal_id: 'P1', outcome: 'enrolled' }], 'P9'));
  rec('拒绝过但未入册可重审 P2', () => assertNotEnrolled([{ proposal_id: 'P2', outcome: 'rejected' }], 'P2'));
  rec('bbUrl 本地黑板', () => assertBbHost('http://127.0.0.1:8792').host);
  rec('bbUrl 中枢黑板', () => assertBbHost('http://106.53.214.108:8792').host);
  rec('root 内路径', () => assertInsideRoot('/tmp/root', '/tmp/root/data/x.json'));
  // 跨设备层 v1.1 正例：合法 key 与"不该误伤"的普通文本
  rec('--rule 合法语法 P1=approve:philosophy', () => assertRuleSpec('P1=approve:philosophy').target);
  rec('回读 200 且内容命中标记 → 真落地', () => assertLanded(classifyBbReadback({ status: 200, body: '{"value":{"key":"data/registry/reflect-feedback-2026-09-10"}}', marker: 'data/registry/reflect-feedback-2026-09-10' })).toString());
  rec('真实键形态 data/reflect/a.b-c_d 通过', () => assertWriteKey('data/reflect/a.b-c_d', { kind: 'card' }));
  rec('key 含 ? / # 通过（实测 404=语法合法，作字面量）', () => assertWriteKey('data/reflect/a?b#c', { kind: 'card' }));
  rec('合法三段 key 通过（notes/<节点>/<键>）', () => assertWriteKey('notes/mac-mini/reflect-feedback-2026-09-10', { kind: 'pointer', text: '看黑板 data/registry/reflect-feedback-2026-09-10' }));
  rec('键序不同但内容相同 → 不算不符（防假阳性）', () => {
    const m = diffWrittenVsReadback({ a: 1, b: { x: 1, y: 2 } }, { b: { y: 2, x: 1 }, a: 1 });
    if (m.length) throw new Error('假阳性: ' + m.join(','));
    return 'same';
  });
  rec('version 2.5 ≥ changelog 最高 2.1 → 放行', () => {
    const r = assertVersionMonotonic({ version: '2.5', changelog: [{ version: '2.1' }, { version: '2.0' }] });
    if (!r.ok) throw new Error('应放行');
    return 'current=' + r.current + ' maxSeen=' + r.maxSeen;
  });
  rec('无旁证版本 → 放行（不误伤）', () => assertVersionMonotonic({ version: '1.0' }).ok.toString());
  rec('不可解析版本 → 跳过不误伤', () => assertVersionMonotonic({ version: 'vNext' }).ok.toString());
  rec('400/404 语义可区分', () => classifyBbReadback({ status: 400, body: '{"error":"bad key"}' }).semantics.slice(0,3) + '|' + classifyBbReadback({ status: 404, body: '{"error":"not found"}' }).semantics.slice(0,3));
  rec('全卡 key data/reflect/feedback/<date>', () => assertWriteKey('data/reflect/feedback/2026-09-10'));
  rec('通知卡 key data/registry/reflect-feedback-<date>', () => assertWriteKey('data/registry/reflect-feedback-2026-09-10'));
  rec('短指引 key notes/<device>/… 44 字', () => assertWriteKey('notes/mbp/reflect-feedback-2026-09-10', { kind: 'pointer', text: '看黑板 data/registry/reflect-feedback-2026-09-10' }));
  rec('普通 sha256/uuid 不被当凭据（防门太宽）', () => {
    const clean = 'sha256=e66801d5172cb040e9d46415aa8a7bf5f4fcf2bf686581fe9bdba14bfa964a0b uuid=9f1c2d3e-4a5b-6c7d-8e9f-0a1b2c3d4e5f';
    const n = scanCredentials(clean).length;
    if (n) throw new Error(`误伤 ${n} 处`);
    return redactCredentials(clean).text === clean ? 'clean' : 'CHANGED';
  });
  rec('凭据形态全部能被识别并脱敏（5 种）', () => {
    const samples = [`sk-${'A'.repeat(24)}`, `ghp_${'b'.repeat(24)}`, `AKIA${'C'.repeat(16)}`, 'X-Writer: xxxxxxxx-token-value', 'password=SuperSecret123456'];
    const missed = samples.filter((s) => scanCredentials(s).length === 0);
    if (missed.length) throw new Error(`漏检 ${missed.length}/${samples.length}`);
    const still = samples.filter((s) => scanCredentials(redactCredentials(s).text).length > 0);
    if (still.length) throw new Error(`脱敏后仍残留 ${still.length}`);
    return `${samples.length}/${samples.length} 识别并脱敏`;
  });
  return cases;
}

/* ══════════════════════════ 版本单调性门（防"降级固化"） ══════════════════════════ */

/** 解析版本为可比较数（支持 2.4 / 2.14.0 / 1.6）。无法解析返回 null。 */
export function parseVersion(v) {
  const m = /^(\d+)\.(\d+)(?:\.(\d+))?$/.exec(String(v == null ? '' : v).trim());
  if (!m) return null;
  return { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3] || 0), raw: String(v).trim() };
}
export function compareVersion(a, b) {
  const A = parseVersion(a), B = parseVersion(b);
  if (!A || !B) return null;
  if (A.major !== B.major) return A.major < B.major ? -1 : 1;
  if (A.minor !== B.minor) return A.minor < B.minor ? -1 : 1;
  if (A.patch !== B.patch) return A.patch < B.patch ? -1 : 1;
  return 0;
}

/**
 * 版本单调性门：**当前 version 不得低于同一文件内已记录过的任何版本**。
 * 为什么需要（实证 · 明鉴 2026-09-11）：该库入册 Φ12/Φ13 时 version 被**从 2.4 写成 1.4**
 *   （根因：没读原值，凭"11+2=13 条"自造版本号）。单一实现里没人发现"基准本身错了"；
 *   而本工具 `bumpMinor(obj.version)` 会**从错误基准继续加**（1.4 → 1.5）把降级**固化**。
 * 信号来自**同文件内的旁证**：changelog[].version / versionHistory[].version / audit.previousVersions。
 * ★ 只拒绝、不自动修复：版本是治理决定，修复归人（phi-user-sovereignty）。
 */
export function assertVersionMonotonic(obj, { relFile = '', source = 'philosophy' } = {}) {
  const cur = parseVersion(obj && obj.version);
  if (!cur) return { ok: true, note: `version '${obj && obj.version}' 不可解析为 x.y[.z]，跳过单调性检查` };
  const seen = [];
  for (const c of obj.changelog || []) if (c && c.version) seen.push({ v: c.version, from: 'changelog' });
  for (const h of obj.versionHistory || []) if (h && h.version) seen.push({ v: h.version, from: 'versionHistory' });
  if (obj.audit && obj.audit.previousVersions) for (const v of obj.audit.previousVersions) seen.push({ v, from: 'audit.previousVersions' });
  let max = null;
  for (const s of seen) if (parseVersion(s.v) && (!max || compareVersion(s.v, max.v) > 0)) max = s;
  if (max && compareVersion(obj.version, max.v) < 0) {
    throw new GateError('VERSION_REGRESSION',
      `拒绝：${relFile} 当前 version='${obj.version}' **低于同文件内已记录过的 '${max.v}'（来自 ${max.from}）** —— ` +
      `基准本身已被写错（降级），继续入册会把降级固化（例如 1.4 → 1.5）。` +
      `本工具**只拒绝、不自动修复**：版本是治理决定，请人确认正确基准并手动修正后再入册。`);
  }
  return { ok: true, current: cur.raw, maxSeen: max ? max.v : null, sources: [...new Set(seen.map((x) => x.from))] };
}

export const GATE_META = Object.freeze({
  decisions: DECISIONS,
  targets: TARGETS,
  libraryTargets: LIBRARY_TARGETS,
  bbHosts: ALLOWED_BB_HOSTS,
  allowedCommands: ALLOWED_COMMANDS,
  writePrefixes: ALLOWED_WRITE_PREFIXES,
  cardPrefixes: CARD_PREFIXES,
  maxPointerChars: MAX_POINTER_CHARS,
  credentialKinds: CREDENTIAL_PATTERNS.map((p) => p.kind),
  principle: 'phi-user-sovereignty 用户主权·确认后执行 + R006⑩ 约束前置·不可绕过',
  noAutoDecide: '裁定只能来自用户（裁定文件 / --rule）；本模块无任何生成裁定的函数',
  noDelete: '源码零删除原语；写形态只有"读取→追加→原子覆盖"；写入后断言条目数严格 +N',
  bbProtocol: 'R003 补充：key 首段 [a-z]+；400=键错 / 404=不存在；写入必回读且 value 非空（空壳键不算落地）',
  crossDevice: '跨设备：只写自己命名空间（data/reflect/ · data/registry/ · notes/ 仅短指引≤50字）；落盘/上黑板前先跑凭据扫描脱敏'
});
