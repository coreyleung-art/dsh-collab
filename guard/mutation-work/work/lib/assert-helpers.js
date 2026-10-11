/**
 * assert-helpers.js — 自检用例的**共用断言助手**（唯一来源）
 * =============================================================================
 * ★ 为什么必须共享：本插件的自检已**三次**因「新模块抛的是另一个错误类」而写出**恒假红**的断言
 *   （`CheckpointError` → `PairingError` → `LedgerIoError`），每次都是在复制那个 `instanceof` 判断，
 *   而复制品必然漂。第 3 次之后按**判据**修：把异常类做成参数（`errHelper(Ctor)`），
 *   新增模块只需一行 `const xerr = errHelper(XError);` —— 不存在"忘了同步"的那个复制品。
 *
 * 这些助手本身不含任何判定逻辑，只负责把「实得/期望」装成统一的三元组 `{name, ok, got, want}`，
 * 供 `runK*SelfTest()` 汇总与 digest 使用。
 */
import { canonicalJson } from './budget-selftest.js';

/** 浅相等（`Object.is`）。 */
export const eq = (name, got, want) => ({ name, ok: Object.is(got, want), got, want });

/** 深相等（规范 JSON 序列化后比字节；键序无关）。 */
export const deq = (name, got, want) => ({ name, ok: canonicalJson(got) === canonicalJson(want), got, want });

/** 条件断言；不成立时把 `detail` 作为实得值带出（便于事后定位，而不是只看到一个 false）。 */
export const okTrue = (name, cond, detail = true) => ({
  name,
  ok: cond === true,
  got: cond === true ? true : detail,
  want: true
});

/**
 * ★ 错误用例助手**工厂**：传入异常类，得到该类的 code 断言器。
 * 断言「必须抛 `Ctor` 且 `e.code === wantCode`」—— 不静默（抛错而非 clamp）是本插件的一贯口径。
 * @param {Function} Ctor 异常类（须带 `code` 字段）
 */
export const errHelper = (Ctor) => (name, fn, wantCode) => {
  try {
    fn();
    return { name, ok: false, got: '(未抛错)', want: wantCode };
  } catch (e) {
    return {
      name,
      ok: e instanceof Ctor && e.code === wantCode,
      got: e instanceof Ctor ? e.code : String(e && e.message),
      want: wantCode
    };
  }
};
