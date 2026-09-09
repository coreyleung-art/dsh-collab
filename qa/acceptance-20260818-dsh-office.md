# 验收报告 #018 · DSH-Office（dsh-plugin-office v0.1.0，C3 自研立项）

> 验收员：session-ffb7c3ab（QA 验收员） · 日期：2026-08-18
> 交付方：session-0e84e65c（依赖/供应链专员）· 委派：直接提交（thread-mswbfjhm）
> 判定：✅ **PASS**（变更清单 + 三功能冒烟全过）

## 1. 变更清单核验

| # | 变更 | QA 核验 | 结论 |
|---|------|---------|------|
| 1 | 新插件 dsh-plugin-office | ✅ 项目在位（cordis.patch.yml/lib/package.json/pnpm-lock/src）+ **profile 已注册**（package.json L29 link + L61 bundles）| ✅ |
| 2 | 三库依赖 | ✅ docx ^9.7.1 + exceljs ^4.4.0 + pptxgenjs ^4.0.1（纯 npm 可控，零运行时下载）| ✅ |
| 3 | 工具注册 | ✅ src/index.ts：office_write（L82）/ office_edit（L99）/ office_read（L120）+ apply service 注册（L143-147 write/edit/read）| ✅ |

## 2. 功能冒烟（QA 实测，node /opt/homebrew/bin/node）

| # | 功能 | QA 实测 | 结论 |
|---|------|---------|------|
| 1 | 模块加载 | ✅ exports：Config/apply/inject/name/office_edit/office_read/office_write | ✅ |
| 2 | office_write（docx）| ✅ `{"ok":true,"path":"/tmp/QA-smoke.docx","bytes":8587}`（与交付方 8522 接近，标题差异）| ✅ |
| 3 | office_write（xlsx）| ✅ 生成成功（Sheet S1 2 行）| ✅ |
| 4 | office_edit（xlsx 追加）| ✅ 正确格式 `{append:{row:['3','4']}}` → applied=1 + 读回 **3 行 × 2 列**（追加生效）| ✅ |
| 5 | office_read 读回核对 | ✅ summary 结构化（sheet 名/行×列/preview）| ✅ |

> ⚠️ 测试过程说明：首次冒烟 .undefined 扩展名（WriteSpec.type 为必填，测试参数缺失）与 applied=0（EditOp 格式应为 {append:{row}}，测试参数格式错误）均为**测试方式问题**，正确参数后全过——非功能缺陷

## 3. 注意项

| # | 项 | 说明 | 级别 |
|---|----|------|------|
| 1 | office_edit docx 追加为 v0.1 简化 | 注释明确「docx 追加需重建文档（v0.1 简化：报提示）」——返回 ok:false 提示，能力边界已知 | 信息 |
| 2 | node --localstorage-file warning | 模块加载时 node 环境警告（非插件问题）| 信息 |

## 4. 验收结论

**PASS。** DSH-Office（dsh-plugin-office v0.1.0）验收通过：变更清单核验（插件/三库依赖/profile 注册/三工具注册）、功能冒烟全过（office_write docx 8587B + xlsx、office_edit 追加 applied=1 读回 3 行、office_read 结构化读回）。2 项信息级注意（docx 追加 v0.1 简化边界、node warning）不阻塞。**C3 自研立项交付闭环**（调研优先制度论证 → 立项 → 开发 → 验收）。

### 4.1 崩溃修复后复验（2026-08-18，0e84e65c 修复）

- **根因修复确认**：Config 普通对象 → `z.object` schema（src/index.ts L17）+ 补 schemastery@3.18.1（package.json L26）——与崩溃事件归因（Config 非 schema）一致
- **bundles 恢复确认**：dsh-plugin-office 在 package.json 2 处（dependencies link + bundles 列表，26→27 待 CLD 重启生效）
- **功能复跑全过**：office_write docx 日报（8573B + read ok）/ **xlsx 41 列基准**（商品导出 2 行 × 41 列——aa528267 四用例基准模拟）/ edit 追加（此前已验证）——修复无回归，**#018 判定维持 PASS**
- 待办：CLD 重启后 dump-config 验证（office 实际加载）+ 挂载日志确认——重启窗口补验
- 备份：.bak-office-restore-20260818-115327（在案）
