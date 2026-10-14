# 运维坑归档 · MTM 双运行形态致「改代码不生效」（灯塔 2026-09-09）

## 坑
- MTM 双形态（Electron 壳读 dist 副本 / node 直跑读项目根），改项目根代码不自动生效
- restart-panel.sh 只重载 node，8787 被 Electron 占则失效（watcher 走 reused 读旧码）

## 固化
- scripts/release-dev.sh（快路径）：同步项目根→dist + 杀占8787者 + 重启Electron壳 + 等10/10
- npm run release-dev / --dry 预览 / 自动备份回滚点
- 正式发布仍走 npm run release

## 文档
- docs/runtime-form-and-release.md（P0 必读：形态判定/路径选择/踩坑查表）
- memory-governance-lean4-review 已追加第七节

## 实例
- 修复 watcher.js biz_page_guard 误拉推广充值页（guard_exempt_urls 豁免）
