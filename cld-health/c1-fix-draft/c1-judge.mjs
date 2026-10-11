// c1-judge.mjs —— C1 判据纯函数（守灯 · G9 修复提案 v3）
//
// v3：把「第二证据源」做成**多源表决列表**（文案 / 结构尾 / 内嵌 marker 三者皆可存在），
//     从而覆盖裁判 T9 的**两种**假绿形态：
//       T9a 文案 clean + 内嵌 marker reason=dsh-crash
//       T9b 文案 clean + 结构尾 reason=dsh-crash（code 0, signal null）
//     v2 用「尾优先、二者取其一」会漏掉 T9a（尾存在时就不再读 marker）⇒ 已改为逐个源都评。
//
// 真实日志两形态（实测，非自造）：
//   干净：`[exit-trace] previous CLD run (pid 3399, started 2026-10-03T13:59:48.050Z) exited cleanly at 2026-10-03T20:00:01.439Z (reason process-exit, code 0, signal null)`
//   未净：`[exit-trace] PREVIOUS CLD RUN (pid 12492, started 2026-10-06T20:00:15.120Z) DID NOT EXIT CLEANLY — …; marker: {…}`
//   ★ v1 只认大写形态 ⇒ 对「上次干净退出」会**假红**（判成 unjudgeable）。故正则大小写不敏感。
//
// 聚合规则（fail-closed）：
//   任一源 unclean ⇒ unclean ｜ 全部可得源 clean ⇒ clean ｜ 否则 ⇒ unjudgeable（**不得读作 clean**）

export function judgeC1_old(em) {
  return em
    ? { ok: em.cleanExit !== false || em.reason !== "dsh-crash", marker: em.reason || "clean", cleanExit: em.cleanExit }
    : { ok: false, error: "无 exit-marker（CLD 未跑过？）" };
}

const PREV_ANY_RE = /\[exit-trace\]\s+previous CLD run\s*\(pid\s+(\d+),\s*started\s+([^)]+)\)\s*([\s\S]*)$/i;
// ★ 放宽：括号尾**可选** —— 若要求必须带 `(reason…,code…,signal…)`，则形如
//   `exited cleanly at <ts>; marker:{…}` 的变体会不被认作 clean 文案 ⇒ **两源冲突检测不到**。
//   本用例（T9a）即由负控自检抓出该过严写法 ⇒ 按「检索须容忍装饰/变体」放宽。
const CLEAN_RE = /exited cleanly at\s+([0-9T:\-.Z]+)/i;
const UNCLEAN_RE = /did not exit cleanly/i;
const MARKER_RE = /marker:\s*(\{[\s\S]*?\})\s*$/i;
const TAIL_RE = /\(reason\s+([^,)]+),\s*code\s+(-?\d+),\s*signal\s+([^)]+)\)/i;

/** 收集所有**可得**证据源 → [{name, verdict, why}] */
function collectSources(tail) {
  const src = [];
  // 源 A：结论文案
  if (UNCLEAN_RE.test(tail)) src.push({ name: "prose", verdict: "unclean", why: "文案: DID NOT EXIT CLEANLY" });
  else if (CLEAN_RE.test(tail)) src.push({ name: "prose", verdict: "clean", why: "文案: exited cleanly" });

  // 源 B：干净行的结构尾 (reason …, code …, signal …)
  const t = tail.match(TAIL_RE);
  if (t) {
    const [, reason, code, signal] = t;
    const bad = Number(code) !== 0 || signal.trim() !== "null" || /dsh-crash/i.test(reason);
    src.push({ name: "tail", verdict: bad ? "unclean" : "clean",
               why: `tail: reason=${reason}, code=${code}, signal=${signal}` });
  }

  // 源 C：内嵌 marker JSON（**独立于 B 评估**——T9a 就藏在这里）
  const mj = (tail.match(MARKER_RE) || [])[1];
  if (mj) {
    try {
      const m = JSON.parse(mj);
      const reason = String(m.reason ?? "");
      const bad = /dsh-crash/i.test(reason)
               || (m.exitCode != null && Number(m.exitCode) !== 0)
               || (m.exitSignal != null && m.exitSignal !== null);
      if (bad) src.push({ name: "marker", verdict: "unclean", why: `marker: reason=${reason || "null"}, code=${m.exitCode ?? "null"}, signal=${m.exitSignal ?? "null"}` });
      else if (m.cleanExit === true && m.endedAt) src.push({ name: "marker", verdict: "clean", why: `marker: cleanExit=true, endedAt=${m.endedAt}` });
      else src.push({ name: "marker", verdict: "unknown", why: `marker: cleanExit=${m.cleanExit}, endedAt=${m.endedAt ?? "null"}（无 clean-exit 记录）` });
    } catch {
      src.push({ name: "marker", verdict: "unknown", why: "marker JSON 解析失败" });
    }
  }
  return src;
}

/**
 * C1 判据 v3（多源表决 · fail-closed）
 * @param {object|null} liveMarker 当前 exit-marker.json（描述当前运行）
 * @param {string[]}    logLines   dsh-web.log 尾部若干行
 */
export function judgeC1(liveMarker, logLines = []) {
  let prev = null;
  for (let i = logLines.length - 1; i >= 0; i -= 1) {
    const m = String(logLines[i] || "").match(PREV_ANY_RE);
    if (m) { prev = { pid: Number(m[1]), startedAt: m[2], tail: m[3] || "" }; break; }
  }
  if (!prev) {
    return { ok: false, status: "unjudgeable", marker: null, attribution: null, conflict: false,
             evidence: "日志无 [exit-trace] previous CLD run 行（不可判定；**不得读作 clean**）", sources: [] };
  }

  const sources = collectSources(prev.tail);
  const anyUnclean = sources.some((s) => s.verdict === "unclean");
  const allClean = sources.length > 0 && sources.every((s) => s.verdict === "clean");
  const conflict = anyUnclean && sources.some((s) => s.verdict === "clean");

  let status, ok;
  if (anyUnclean) { status = "unclean"; ok = false; }       // ★ fail-closed
  else if (allClean) { status = "clean"; ok = true; }       // 全部可得源同向才绿
  else { status = "unjudgeable"; ok = false; }              // 缺源/未定 ⇒ 不判干净

  const mj = (prev.tail.match(MARKER_RE) || [])[1];
  let reasonField = null;
  if (mj) { try { reasonField = JSON.parse(mj).reason ?? null; } catch { reasonField = null; } }

  return {
    ok, status,
    marker: reasonField,                                     // 如实；**绝不默认 "clean"**
    attribution: { pid: prev.pid, startedAt: prev.startedAt },
    conflict,
    evidence: sources.length ? sources.map((s) => `${s.name}=${s.verdict}(${s.why})`).join(" ｜ ") : "无可用证据源",
    sources,
  };
}
