# 给 Agent 的素材交付规范 · Asset Delivery Standard

> 建立：2026-09-05 · 依据：CLD 品牌替换实战（图标/logo/文案）+ agent 能力边界实测
> 适用：任何"给 agent 处理的设计素材"交付（图标、logo、UI 元素、图片资产）
> 核心矛盾：**多数 agent 不能看图** → 素材必须"可机读、可决策、可自动处理"，不靠 agent 目视

---

## 一、为什么需要这份规范（实战教训）

CLD 图标替换当天暴露的问题：
| 交付物 | 问题 |
|---|---|
| JPG（无透明通道） | 当图标/logo 带背景色块；无法叠深/浅 UI；mockup 是"展示图"不是"素材" |
| 单一 1920² 大图 | 尺寸靠 agent 猜全套缩放 |
| mockup（效果预览图） | 误导：当成品用，实际是"手机壳/桌面展示" |
| 无配套文字描述 | **agent 不能看图** → 只能凭文件名猜内容（选错风险） |
| 只有 summary 缺关键字段 | 有无透明？哪张主稿？配色？→ 无法决策 |

**结论**：给 agent 素材 ≠ 给设计师素材。要额外带"机读描述"，让 agent 不靠眼睛也能判断/选用/检查。

---

## 二、理想交付 = 每类资产"三件套"

```
<asset-name>/
├── 源文件/          ← ① 矢量源/高分辨率原始（唯一真理）
├── 导出/            ← ② 透明 PNG 多尺寸（或按需生成）
└── 说明.json         ← ③ 机读描述（agent 决策依据）★ 最重要
```

---

## 三、各资产类型规格

### ① 源文件（第一优先）
- **SVG 首选**：矢量任意缩放无损；agent 可直接嵌入代码（React/SVG）/ 重导出任意尺寸
- 位图源：**≥1024×1024、透明底 PNG**
- 退路：AI/PSD/Figma 导出链接

### ② 导出 PNG 规格（一律透明底，除非明确要底色）

| 用途 | 建议尺寸 | 说明 |
|---|---|---|
| **App 图标**（macOS icns 源） | 1024×1024 透明 PNG | 给"图标本体"；圆角遮罩由系统规范或明确标注 |
| UI 内 logo（如 hero 34px/侧栏 24px） | 1024 源即可（agent 按需缩放），或给 2x(68/48) | 需透明底 |
| 深浅主题适配 | 各一版或注明主色 | agent 按环境选 |

### ③ 说明.json —— schema 建议

```json
{
  "primary": "cld-app-icon-transparent.png",
  "description": "深蓝圆角方块，白色几何 CLD 三字母，居中，无背景图案",
  "palette": { "bg": "#0E1A2B", "fg": "#FFFFFF", "accent": "#5B8DEF" },
  "transparency": "图标本体透明底；圆角为图形一部分",
  "style": "geometric|flat|gradient|3d|hand-drawn",
  "intendedUse": { "appIcon": true, "uiLogo": false, "hero": false, "favicon": false },
  "scalesToSmall": true,
  "notes": "缩到 16px 仍清晰；右上角有节点连线装饰"
}
```

字段作用：
- `primary`：哪张是主稿（agent 不用猜）
- `description/palette`：agent 的"眼睛"——判断适用场景/深浅/是否替换成功
- `intendedUse`：防止把 hero 素材当 app 图标之类的错配
- `scalesToSmall`：预判小尺寸可用性

---

## 四、AI 生图工具 prompt 模板（一次到位）

生成时直接在 prompt 要求成品格式，避免二次返工：
```
透明背景 PNG（不是 JPG）
1024×1024
主体为 [圆角方块图标本身]（不要手机壳/桌面 mockup 效果）
[深色底 + 白色几何字母]，无文字水印
```
**关键词：透明背景（最关键）、图标本体（非 mockup）、方形 1:1**。

---

## 五、Agent 侧处理 SOP（拿到素材后）

```
① 读 说明.json → 定 primary + intendedUse（不看图也能选）
② 透明底 PNG → iconset 全套(16~1024 @1x@2x) → iconutil → .icns
③ 替换 Resources/icon.icns → 深度清缓存(见下) → 完全重启
④ 验证: 文件替换成功 + 进程正常; 像素效果仍需用户目视确认(agent 不能看图)
```

**macOS 图标缓存刷新 SOP（易踩坑，实测 2026-09-05）**：
```bash
pkill -f "CLD.app/Contents/MacOS/CLD"          # 1. 完全停
rm -rf ~/Library/Caches/com.apple.iconservices.store   # 2. 删 iconservices 缓存
touch /Applications/CLD.app
lsregister -f /Applications/CLD.app            # 3. 重新登记
# 4. ★决定性: 从 Dock 移除固定项再重开(强制 Dock 重读 icns)
#    defaults export com.apple.dock → 剔 CLD 项 → import → killall Dock
open /Applications/CLD.app
# 5. 若仍旧: 删 ~/Library/Application Support/Dock/*.db 或注销/重启
```
**实测结论**：仅删 iconservices 缓存+killall Dock 不够；**Dock 固定项移除重加**是决定性一步。

---

## 六、清单（交付前自检）

- [ ] 有 SVG 或 ≥1024 透明 PNG 源
- [ ] 无 JPG mockup 混入正式素材（或单独目录标注）
- [ ] 附 说明.json（primary/description/palette/intendedUse）
- [ ] 若多版本（深浅）标注各自用途
- [ ] 若 AI 生成：确认是"图标本体"非展示图

---

## 七、当前 CLD 品牌资产缺口（2026-09-05）

| 资产 | 现状 | 缺口 |
|---|---|---|
| App 图标 | JPG mockup-dark 已转 icns 在用 | 透明底 PNG 本体版（1024²） |
| UI logo（hero/侧栏） | 代码内"蓝底 CLD 字母"占位 | 正式 SVG logo 图形 |

补齐后 agent 可重做一版"干净"图标 + 把 UI 占位换成正式 logo。

---

*规范 v1.0 · 2026-09-05 · 与《DSH可替换元素地图》《页面元素定制指南》配套*
