# 9/6 二次掉线根因修正 · 灯塔（2026-09-09）

- 老登实测: 8787 现由 Electron 壳占用 → 9/6 二次掉线根因 = 壳与 node 抢端口（非 watcher bug）
- 灯塔确认: 当前 8787 = Electron(5639)，与实测一致
- 认知定调: 一次只允许一个形态占 8787（壳 或 node 直跑），混启即抖
- 补档: docs/runtime-form-and-release.md 第七节（延伸根因 + 防复发：改码/重启前先 lsof 看形态，壳形态用 release-dev.sh 统一）
