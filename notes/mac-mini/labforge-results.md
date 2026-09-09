- [2026-09-05T06:00:30.772Z] **single-session-governance** PASS (4P/0F)
  目标: 验证单会话（非叠加场景）下帧索引治理的内存/耗时收益，并确认单会话非 OOM 崩溃源（反向证实多会话叠加才是根因）
  - ✅ R1-single-no-crash 单会话 full 不崩（反向证实 OOM 源=多会话叠加） → false
  - ✅ R2-tail-alive tail 存活且峰值 < 100MB → 22.1
  - ✅ R3-memory-gain 内存改善 >= 10x → 17.3
  - ✅ R4-time-gain 耗时改善 >= 50x → 166.4
- [2026-09-05T06:00:35.451Z] **memory-crash-oom-repro** PASS (4P/0F)
  目标: 复现历史 CLD OOM（SIGABRT）崩溃场景，并验证 P2-1 帧索引尾部窗口治理后同资源下不再崩溃
  - ✅ A1-OOM-rootcause 全量物化在受限 heap 顶下崩溃(SIGABRT) —— 复现根因 → true
  - ✅ A2-governance-alive 帧索引治理后: 崩溃 heap 顶下 tail 全部存活 → true
  - ✅ A3-memory-gain 治理后峰值内存改善 >= 10x → 22.7
  - ✅ A4-time-gain 治理后耗时改善 >= 10x → 145.7
- [2026-09-05T06:00:35.510Z] **single-session-governance** PASS (4P/0F)
  目标: 验证单会话（非叠加场景）下帧索引治理的内存/耗时收益，并确认单会话非 OOM 崩溃源（反向证实多会话叠加才是根因）
  - ✅ R1-single-no-crash 单会话 full 不崩（反向证实 OOM 源=多会话叠加） → false
  - ✅ R2-tail-alive tail 存活且峰值 < 100MB → 22.1
  - ✅ R3-memory-gain 内存改善 >= 10x → 17.3
  - ✅ R4-time-gain 耗时改善 >= 50x → 166.4
- [2026-09-05T06:00:35.569Z] **frame-index-perf-regression** PASS (3P/0F)
  目标: 把 P2-1 帧索引 POC 的结论固化为可回归实验：真实会话上尾部窗口解码较全量解码提速 >=40x 且解码量 <2%
  - ✅ P1-tail-fast 尾部窗口解码 < 50ms → 1.97
  - ✅ P2-speedup 帧索引提速 >= 40x → 2089.4
  - ✅ P3-few-frames 中枢会话(perFile[0])尾部窗口解码帧占比 <= 2% → 0.066
- [2026-09-05T06:04:02.628Z] **frame-index-perf-regression** PASS (3P/0F)
  目标: 把 P2-1 帧索引 POC 的结论固化为可回归实验：真实会话上尾部窗口解码较全量解码提速 >=40x 且解码量 <2%
  - ✅ P1-tail-fast 尾部窗口解码 < 50ms → 1.77
  - ✅ P2-speedup 帧索引提速 >= 40x → 2494.7
  - ✅ P3-few-frames 中枢会话(perFile[0])尾部窗口解码帧占比 <= 2% → 0.066
- [2026-09-05T06:04:43.134Z] **memory-crash-oom-repro** PASS (4P/0F)
  目标: 复现历史 CLD OOM（SIGABRT）崩溃场景，并验证 P2-1 帧索引尾部窗口治理后同资源下不再崩溃
  - ✅ A1-OOM-rootcause 全量物化在受限 heap 顶下崩溃(SIGABRT) —— 复现根因 → true
  - ✅ A2-governance-alive 帧索引治理后: 崩溃 heap 顶下 tail 全部存活 → true
  - ✅ A3-memory-gain 治理后峰值内存改善 >= 10x → 22.7
  - ✅ A4-time-gain 治理后耗时改善 >= 10x → 152.4
- [2026-09-05T06:05:00.759Z] **memory-crash-oom-repro** PASS (4P/0F)
  目标: 复现历史 CLD OOM（SIGABRT）崩溃场景，并验证 P2-1 帧索引尾部窗口治理后同资源下不再崩溃
  - ✅ A1-OOM-rootcause 全量物化在受限 heap 顶下崩溃(SIGABRT) —— 复现根因 → true
  - ✅ A2-governance-alive 帧索引治理后: 崩溃 heap 顶下 tail 全部存活 → true
  - ✅ A3-memory-gain 治理后峰值内存改善 >= 10x → 22.7
  - ✅ A4-time-gain 治理后耗时改善 >= 10x → 152.4
- [2026-09-05T06:05:00.821Z] **single-session-governance** PASS (4P/0F)
  目标: 验证单会话（非叠加场景）下帧索引治理的内存/耗时收益，并确认单会话非 OOM 崩溃源（反向证实多会话叠加才是根因）
  - ✅ R1-single-no-crash 单会话 full 不崩（反向证实 OOM 源=多会话叠加） → false
  - ✅ R2-tail-alive tail 存活且峰值 < 100MB → 22.1
  - ✅ R3-memory-gain 内存改善 >= 10x → 17.3
  - ✅ R4-time-gain 耗时改善 >= 50x → 166.4
- [2026-09-05T06:05:00.880Z] **frame-index-perf-regression** PASS (3P/0F)
  目标: 把 P2-1 帧索引 POC 的结论固化为可回归实验：真实会话上尾部窗口解码较全量解码提速 >=40x 且解码量 <2%
  - ✅ P1-tail-fast 尾部窗口解码 < 50ms → 1.77
  - ✅ P2-speedup 帧索引提速 >= 40x → 2494.7
  - ✅ P3-few-frames 中枢会话(perFile[0])尾部窗口解码帧占比 <= 2% → 0.066
