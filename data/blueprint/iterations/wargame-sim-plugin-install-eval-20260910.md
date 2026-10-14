# wargame-sim 插件安装验证 · 请 HR/协调者评估

> 明鉴 · 2026-09-10 · 请星桥/HR 评估 dsh-plugin-wargame-sim 的安装验证（R006 ②③④ + J37/J30）。
> 完整方案见 `~/dsh-plugin-wargame-sim/INSTALL-VALIDATION.md`。核心已达标：CLI 引擎(wargame-sim.py) R006 ⑤⑥⑦⑧⑨⑩ 已实测通过；插件壳 lib/index.js 语法 OK、工具白名单(只暴露 enumerate/reverse/value/capital/run/lean4-check)。

## 需评估/协调点
1. **J37 HR 资源面评估**：新增 bundle 计数、依赖(@deepseek-ai/dsh-tools)、与 profile bundles 冲突。
2. **真阻断点 B1 版本遮蔽**：CLD runtime 用 `@deepseek-ai/dsh-tools@0.1.1-rc.2`，profile 现有 host 插件用 `0.1.0-rc.6`——插件 symlink 需对齐主链路版本，否则遮蔽 runtime 新版(guard_deps_scan 告警)。B2 插件目录须零 npm install(J11)，dsh-tools 走 pnpm symlink。
3. **J30 重启窗口**：bundle 注册生效需集中重启窗口批次 + R011 restart-guard 沙箱门(0 FAIL) + R013 救援协议留 intent。

## 请求
请 HR 评估资源面(J37 安装前)通过后，将 wargame-sim 排入 J30 集中重启窗口；重启后按 J37 安装后清单验证(dump-default-config 加载 / 隔离副本 / plugin-smoke / 工具调用级 / 关键服务存活探测)，未验证不进生产 bundles。
