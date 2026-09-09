---
title: "repo-pipeline CI 加固增量（4e32062）"
source_type: collaboration
source_url: "session-dcac2308 交付增量"
ingested: 2026-08-17
tags: [llm-wiki-raw, repo-pipeline, ci]
---

# repo-pipeline CI 加固增量 · 提交 4e32062 · 2026-08-16

**背景**：6ed4daf2 冒烟发现插件 tsc not found → 根因 = 链接包场景（插件以 link: 装入 profile 时父项目不安装链接包 devDeps）+ 临时 npm install 遗留真实 node_modules。

**变更①**：node CI 模板（templates.ts + CLI 脚本）Install 后新增 Build 步骤 `npm run build --if-present`——devDeps 若有遗漏会直接暴露为构建失败（防遗漏固化）。

**变更②**：清理插件目录真实 node_modules——链接包本地 node_modules 会遮蔽宿主注入的 @deepseek-ai peer deps，导致 cordis inject 失效（运行时隐患）；插件目录应保持零 node_modules，冒烟验证用 npm ci+临时目录或仓库 CI。

**验证**：本地 tsc 构建通过；4e32062 已推送双仓，CI 自动跑 Build 步骤。

**关联陷阱**：链接包 devDeps 缺失 + 本地 node_modules 遮蔽 peer deps（与 xberg 重装覆盖陷阱同属「插件目录状态污染」类）。
