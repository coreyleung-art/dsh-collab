// c1-selftest.mjs —— C1 负控自检（v3：真实格式 + 裁判 T9 两形态 + fail-closed）
// 用法: /opt/homebrew/bin/node c1-selftest.mjs     退出码 0=全过 1=有用例失败
//
// 设计纪律（承席位#4 自设判据）：
//   · 每例必须有期望值，且**必须有用例会红**（否则「仪器已证明会红」不成立）；
//   · 新旧判据同场对照 —— 差额即修复效应量；
//   · 不可判定必须显式表达（status="unjudgeable"），**不得并入通过**；
//   · fixture 用**真实日志行**（不自造格式）。

import { judgeC1, judgeC1_old } from "./c1-judge.mjs";

// ── 真实行（取自 ~/.cld/logs/dsh-web.log）──
const REAL_CLEAN = '[exit-trace] previous CLD run (pid 3399, started 2026-10-03T13:59:48.050Z) exited cleanly at 2026-10-03T20:00:01.439Z (reason process-exit, code 0, signal null)';
const REAL_UNCLEAN = '[exit-trace] PREVIOUS CLD RUN (pid 12492, started 2026-10-06T20:00:15.120Z) DID NOT EXIT CLEANLY — no clean-exit record (crash or external kill?); last heartbeat 2026-10-07T19:30:49.887Z; marker: {"version":1,"pid":12492,"startedAt":"2026-10-06T20:00:15.120Z","cleanExit":false,"note":"boot","uptime_sec":0}';
const REAL_KILLED = '[exit-trace] PREVIOUS CLD RUN (pid 78256, started 2026-10-05T20:05:15.571Z) DID NOT EXIT CLEANLY — no clean-exit record (crash or external kill?); marker: {"version":1,"pid":78256,"cleanExit":false,"exitCode":0,"exitSignal":null,"reason":"dsh-crash-after-child","uptime_sec":196}';

// ── 裁判 T9 新假绿两形态（构造的对手用例）──
const T9a = '[exit-trace] previous CLD run (pid 9001, started 2026-10-07T10:00:00.000Z) exited cleanly at 2026-10-07T11:00:00.000Z; marker: {"version":1,"pid":9001,"cleanExit":false,"reason":"dsh-crash","endedAt":"2026-10-07T11:00:00.000Z"}';
const T9b = '[exit-trace] previous CLD run (pid 9002, started 2026-10-07T10:00:00.000Z) exited cleanly at 2026-10-07T11:00:00.000Z (reason dsh-crash, code 0, signal null)';
const MIXED = '[exit-trace] PREVIOUS CLD RUN (pid 9003, started 2026-10-07T10:00:00.000Z) DID NOT EXIT CLEANLY; marker: {"version":1,"pid":9003,"cleanExit":true,"endedAt":"2026-10-07T11:00:00.000Z"}';

const LIVE = { pid: 676, startedAt: "2026-10-07T19:32:30.973Z", cleanExit: false, note: "boot", uptime_sec: 2 };

const CASES = [
  { n: 1,  name: "真实干净行（两源同向）",                 live: LIVE, log: ["noise", REAL_CLEAN],  expect: { ok: true,  status: "clean" } },
  { n: 2,  name: "真实未干净行 pid12492 ★反控",            live: LIVE, log: [REAL_UNCLEAN],         expect: { ok: false, status: "unclean", pid: 12492 } },
  { n: 3,  name: "真实被 kill 行 pid78256 ★反控",          live: LIVE, log: [REAL_KILLED],          expect: { ok: false, status: "unclean", pid: 78256 } },
  { n: 4,  name: "★T9a 文案 clean + marker reason=dsh-crash（旧漏此形）", live: LIVE, log: [T9a], expect: { ok: false, status: "unclean", conflict: true } },
  { n: 5,  name: "★T9b 文案 clean + 结构尾 reason=dsh-crash",             live: LIVE, log: [T9b], expect: { ok: false, status: "unclean", conflict: true } },
  { n: 6,  name: "★两源冲突（文案 unclean + marker cleanExit=true）",     live: LIVE, log: [MIXED], expect: { ok: false, status: "unclean", conflict: true } },
  { n: 7,  name: "日志无 PREVIOUS 行 ⇒ 不可判定",           live: LIVE, log: [],                     expect: { ok: false, status: "unjudgeable" } },
  { n: 8,  name: "空 marker {} ⇒ 不可判定（旧报 true/clean）", live: {}, log: [],                     expect: { ok: false, status: "unjudgeable" } },
  { n: 9,  name: "完全无 marker 且无日志 ⇒ 不可判定",        live: null, log: [],                     expect: { ok: false, status: "unjudgeable" } },
];

let pass = 0, fail = 0;
console.log("── C1 负控自检 v3（真实格式 + T9 两形态；新旧判据对照）──");
console.log("用例 期望       新判据     status       冲突 attribution  ｜ 旧判据   旧marker   结果");
const results = [];
for (const c of CASES) {
  const got = judgeC1(c.live, c.log);
  const old = judgeC1_old(c.live);
  results.push({ c, got, old });
  const okMatch = got.ok === c.expect.ok && got.status === c.expect.status
    && (c.expect.pid === undefined || got.attribution?.pid === c.expect.pid)
    && (c.expect.conflict === undefined || got.conflict === c.expect.conflict);
  if (okMatch) pass += 1; else fail += 1;
  console.log(
    `${String(c.n).padEnd(4)} ${String(c.expect.ok).padEnd(10)} ${String(got.ok).padEnd(9)} ${got.status.padEnd(13)} ` +
    `${String(got.conflict).padEnd(5)} ${String(got.attribution?.pid ?? "—").padEnd(11)} ｜ ${String(old.ok).padEnd(8)} ${String(old.marker).padEnd(10)} ${okMatch ? "✅" : "❌ " + c.name}`
  );
}

// ── 判据级结论（比逐例更重要）──
const red = results.filter((r) => r.got.ok === false).length;
const oldRed = results.filter((r) => r.old.ok === false).length;
const fabricate = results.filter((r) => r.got.marker === "clean" && r.got.status !== "clean").length;
const unjudge = results.filter((r) => r.got.status === "unjudgeable").length;
const t9 = results.filter((r) => [4, 5, 6].includes(r.c.n) && r.got.status === "unclean").length;

console.log("\n── 判据级结论 ──");
console.log(`① 会红的用例：新 ${red}/${CASES.length} ｜ 旧 ${oldRed}/${CASES.length} ⇒ 判别力成立`);
console.log(`② 伪造 "clean" 次数：新 ${fabricate}（必须 0）｜ 旧 ${results.filter((r) => r.old.marker === "clean").length}`);
console.log(`③ 不可判定例数：${unjudge}（显式表达，未并入通过）`);
console.log(`④ **T9 两形态 + 源冲突：${t9}/3 判红**（新假绿已封）`);
console.log(`\n结果: ${fail === 0 ? "✅ PASS" : "❌ FAIL"}  pass=${pass} fail=${fail}`);
process.exit(fail === 0 ? 0 : 1);
