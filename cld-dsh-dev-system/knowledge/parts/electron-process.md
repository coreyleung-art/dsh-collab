# 部件卡 · electron-process（Electron 进程模型 / 内存）

> 填卡：2026-09-05 · 依据：electron-docs process-model.md + CLD OOM 实证
> 状态：learned（registry: electron-process）

## 1. 一句话定位
Electron 继承 Chromium 多进程架构：main(控制)+ renderer(每窗口/标签独立)+ utility/net/gpu 等；单页崩溃不拖垮整体。CLD 壳在此基础上再 spawn dsh 子进程(ELECTRON_RUN_AS_NODE)——层叠。

## 2. 概念与定义
- **main process**：应用入口/生命周期/原生 API(BrowserWindow/Menu/dialog/app)；owns window 管理(browser window 生命周期)。
- **renderer process**：每窗口独立(渲染 web 内容)——CLD 里跑 dsh UI。
- **preload scripts**：renderer 与 main 间受控桥(contextIsolation)。
- **utility process**：net/gpu 等 Chromium 服务。
- **memory**：Node/Chromium 堆各自独立——OOM 是单进程级(CLD 实证: dsh 子进程 JS 堆 4001MB 上限 OOM→SIGABRT)。

## 3. 作用与生命周期
app.whenReady → 建窗口(renderer) → 生命周期(activate/window-all-closed/before-quit)。CLD 壳: main spawn dsh(子进程, 独立堆) → renderer 加载 dsh web URL → dsh 崩不影响壳 UI 进程(但壳看门狗检测→弹窗/quit)。

## 4. 约束（红线/不可违）
- 每进程独立堆：不能共享 Node heap；--max-old-space-size 白名单限制(打包 Electron 无效——官方 fuse/白名单, 实证)。
- renderer 崩≠main 崩(多进程隔离价值)；dsh 子进程 OOM 需看门狗标记(exit-marker, S1)。
- 内存采样用 process 的 memoryUsage/rss + node:v8(别用被移除的 process.getHeapStatistics)。

## 5. 依赖
- main 依赖原生 API;renderer 依赖 preload/contextIsolation;CLD spawn 依赖 ELECTRON_RUN_AS_NODE。

## 6. 规范要点（标准）
- 内存诊断按进程分(ps aux 各 CLD Helper/主/dsh)：谁涨即谁的堆。
- heap 上限 4001MB 是硬顶——治本在减少单进程峰值(compaction/分流)非抬上限。

## 7. 关联
- 官方：process-model.md、memory 相关 docs · 工具箱：T2(OOM) · 路由：OP-asar-shell
- 代码：CLD app.asar main.js(S1 看门狗/S5 采样)——知识：cld-shell-watchdog 卡。

## 8. 待补
- renderer 与 utility 进程内存细分。

## 9. 学-建-用 沉淀
- 2026-09-05：卡毕业——OOM 排障按进程归因 + 硬顶认知。
