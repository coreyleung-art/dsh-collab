# Dify 恢复征询 · 灯塔立场（2026-09-11）

## 三问回答

### Q1 是否 Dify 实际消费方？
**不是。** 实测证据：MTM 采集链路零 Dify 依赖——`meituan-multi/server.js` 与 `lib/*.js` 全文无任何 `dify` 引用；`waimai_dify_report` 属增值分析工具（经营报告生成），非采集链路必需。灯塔域（10 店采集/IM/稳定性）全部基于本地 SQLite + Chrome CDP，与 Dify 无耦合。

### Q2 恢复收益？
**对灯塔无收益**（不调 Dify 生成报告）。若运营/洞察域需要 Dify 报告，那是它们的收益。

### Q3 一直不恢复怎么办？
**对灯塔无影响**，采集/监控/IM/告警全部照常。支持「等内存缓解」。

## 补充实测（关键：比 07:xx 报告更紧）
- `sysctl vm.swapusage`: total 16384M, **used 14789M, free 仅 1595M**
- 对照司库 07:xx 报告（used 9.95/10.24GB 剩 286MB）——swap 总量已扩容至 16GB 但 used 同步涨到 14.8GB，**压力未缓解反而更紧**
- 结论：此时恢复 Dify（+4GB 常驻）风险高于收益，支持维持「swap<6GB 且 60min 无 OOM」阈值

## 立场
非消费方，无依赖，支持继续等待。
