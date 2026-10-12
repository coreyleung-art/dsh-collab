# 2026-08-30-hot-reload-crash CLD 热重载崩溃（reloadDsh 正常路径缺 return → HTTP 读 undefined 崩壳）

> 级别: P1 · 日期: 2026-08-30

## 现象
POST 127.0.0.1:31888/reload 后 CLD 直接崩溃（uncaughtException TypeError: Cannot read properties of undefined (reading 'reloading')），需用户手动重开

## 根因
main.js reloadDsh() 正常路径（非 already-reloading）执行完无 return → 返回 undefined → startReloadServer HTTP 处理器 `r.reloading` 读 undefined 属性 → TypeError → 壳崩。存量 bug（v0.3.x 引入），本次触发暴露

## 修复
reloadDsh 正常路径补 `return { ok: true, reloading: true }`（治理仓库 ~/dsh-collab/cld/main.js，v0.3.2）

## 教训（→ SOP 更新点）
① 热重载/重启类生产路径，触发前必须沙箱验证（R015）——本次违反纪律直接触发未验证热重载，撞上存量 bug 崩溃 ② JS 函数所有分支必须显式 return（尤其被调用方读返回值属性的场景）③ 触发崩溃后发现：CLD 不是自动重启而是用户手动重开——不能假设 launchd 自动拉起

## SOP 更新
热重载 SOP：触发 /reload 前先 node --check main.js + 逻辑静态验证（所有 return 路径）+ 沙箱 CLD 试跑；崩溃后先查 exit-marker/crash-reason 再判断是否自动恢复
