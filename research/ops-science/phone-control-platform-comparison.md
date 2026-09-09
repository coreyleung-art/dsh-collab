# 手机控制技术平台对比 · Windows(i9) vs macOS（沉淀）

> 建立：2026-08-19 · HR 驾驶舱 · 用途=市场调研端自动化（链路 B）的设备层选型
> 背景：i9=Windows 11 Pro（i9-14900KF/32G/RTX 4060 Ti），本机=macOS（M4/24G）；两端都要能控制手机

---

## 一、结论速览

| 平台 | Android 控制 | iOS 控制 | 模拟器/多开 | 远程物理机 |
|---|---|---|---|---|
| **Windows (i9)** | ✅ 完全对等（ADB/scrcpy/uiautomator2/AirTest/Appium 均跨平台） | ⚠️ 需远程 Mac 跑 WDA 或云真机（Appium 官方 non-macOS 指南） | ✅ 生态最成熟（蓝叠/雷电/夜神多开） | ✅ 向日葵 MCP 已打通 |
| **macOS** | ✅ 对等 | ✅ **唯一直接通道**（Xcode/XCUITest/WDA 仅 macOS） | ✅ Android Studio/模拟器；iOS Simulator 仅 macOS | ✅ 向日葵 MCP 已打通 |

**核心结论**：① **Android 控制两端无差别**，Windows 多开模拟器生态更成熟——竞对情报采集主力应跑 i9(Windows) Android 链路 ② **iOS 控制 macOS 是唯一直接通道**——iOS 真机自动化必须 Mac 跑 WebDriverAgent ③ 统一抽象层（Appium/AirTest）屏蔽平台差异 ④ 云真机/设备农场作弹性扩容。

## 二、Android 控制技术（跨平台，两端对等）

| 技术 | 定位 | 平台 | 备注 |
|---|---|---|---|
| ADB | 官方底层（安装/截图/输入/控件 dump） | Win/mac/Linux | 一切 Android 自动化的地基 |
| scrcpy | 投屏+反向控制（低延迟） | 跨平台 | 人肉浏览的可视化替代 |
| uiautomator2 | Python UI 自动化（控件级） | 跨平台 | 稳定、社区大 |
| AirTest | 网易 UI 自动化（图像识别为主） | 跨平台 | 适合动态界面/游戏式点击 |
| Appium | 跨平台自动化框架 | 跨平台 | 统一抽象（Android+iOS） |
| 模拟器多开 | 蓝叠/雷电/夜神（Android） | Win 生态最成熟 | 每开=一个「城市/商圈」并发采集 |

## 三、iOS 控制技术（macOS 硬优势）

| 技术 | 平台约束 | 说明 |
|---|---|---|
| XCUITest / WebDriverAgent | **仅 macOS**（需 Xcode 编译） | iOS 真机 UI 自动化的唯一原生路径 |
| Appium xcuitest driver（non-macOS hosts） | Windows 可驱动，但 WDA 须跑在 Mac | Appium 官方指南：非 Mac 主机通过远程 Mac/云跑 WDA |
| iOS Simulator | 仅 macOS | Windows 无 iOS 模拟器 |
| 云真机（AWS Device Farm / TestGrid 等） | 跨平台 API | iOS 真机按需租用，弹性扩容 |

## 四、其他技术路线

| 技术 | 说明 | 适配场景 |
|---|---|---|
| **向日葵 MCP（已有）** | AweSun 22 工具（握手/搜索/详情实测打通）=物理手机远程控制 | 现成通道；Win/Mac 均可 |
| 云手机（Android 云真机） | 红手指/阿里云手机等，API 驱动 | 多城市多商圈并发，免物理设备 |
| 设备农场 | AWS Device Farm / TestGrid | 弹性扩容/兼容性测试 |
| 企业移动管理（MDM）+ 自动化 | 大批量设备管理 | 规模化后的管理底座 |

## 五、链路 B 推荐架构（沉淀）

```
竞对情报采集（链路 B）设备层：
  主力 = i9(Windows) + Android 真机/模拟器多开（ADB + scrcpy + uiautomator2/AirTest）
  iOS  = macOS 本机跑 WDA（现有 Mac 资产）或云真机按需
  远程 = 向日葵 MCP（已有 awesun 通道，物理手机）
  扩容 = 云手机/设备农场（弹性）
  抽象 = Appium 或 AirTest 统一层（屏蔽 Win/Mac/云差异）
```

**决策依据**：竞对情报对象=美团/饿了么/京东外卖用户版 App——Android 版功能完整、模拟器多开成本低、i9 是现成 Windows 算力机 → **Android 优先**；iOS 仅在有 Android 无法覆盖的场景（如 iOS 端差异化优惠/排名差异）时按需补充。

## 六、phoneuse 项目（定位结果 · 2026-08-19 设备协调回报）

- **路径**：`E:\My vibe codding\phoneuse`（i9 Windows E 盘）
- **形态**：Python 311 MCP stdio 服务器（`python -m phoneuse.mcp.stdio_server`）——**26 个手机自动化工具**（device.screenshot / input.tap / input.swipe 等），绑定真机（--serial 序列号）
- **用途**：手机自动化测试/控制 MCP——**正是链路 B 需要的现成控制层**（智能体可直接调用 MCP 工具面，无需从 ADB 层自建）
- **数据**：截图/脚本/日志（E 盘），数据量待 cmd2 恢复后实测
- **可访问**：Tailscale 内可达 i9；MCP stdio 配置已就绪
- **沉淀结论**：链路 B 控制层优先复用 **phoneuse MCP（26 工具）+ 向日葵 MCP（远程通道）**——i9 上手机自动化底座已存在；市场调研采集 = phoneuse 工具 + 智能体大脑 + 竞对情报库

---
*来源：Appium non-macOS Hosts 官方指南、ADB/scrcpy/uiautomator2/AirTest 官方文档、AWS Device Farm 文档、TestGrid 设备农场对比（2026-08-19 检索）；向日葵 MCP 已有实测（awesun 22 工具）*