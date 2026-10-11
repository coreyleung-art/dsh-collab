# mac-mini 内存治理 + 资源优化报告（2026-09-11）

> 执行: HR 司库(资源中枢) · 触发: 用户指令「做一次 mac 本机内存治理 + 资源优化」
> 方法: 实测盘点 → 根因定位 → 安全项执行 → 大项列决策

═══════════════════════════════════════

## 一、内存/CPU 治理（已执行）

### 发现 1: runaway 服务烧 3 核（根因）
- **blackboard-mcp(8810) PID 1120: 291-300% CPU 持续 6 天 8 小时**, 零连接
- 根因链:
  1. launchd plist `ProgramArguments` **累积 4 个二进制路径**(v0.8.4/0.8.2/0.8.1/0.8.0)——每次升级追加而非替换
  2. 服务内 queue-watch 每 5 分钟触发一轮 condense
  3. **二进制 bug**: `now_ms() - last_condense > 600`——注释「>10min」但代码是 **600 毫秒**(应为 600000), 每轮必触发
  4. condense 调 ollama(bge-m3 聚类 + qwen 归纳)→ ollama 98% CPU
  5. **condense 不排空队列** → 队列持续 red → 无限循环

### 处置
| 动作 | 结果 |
|---|---|
| 修复 plist(4 路径→1) | ✓ 配置干净 |
| 停止服务(launchctl bootout) | ✓ 300% CPU → 0 |
| 卸载 ollama 空闲模型(J35) | ✓ 释放 2.83GB(qwen2.5:3b + bge-m3) |

### 效果
| 指标 | 治理前 | 治理后 |
|---|---|---|
| 总 CPU | ~400%+ | **218%** |
| blackboard-mcp CPU | 291.8% | **0%**(服务已停) |
| ollama CPU | 98% | 0.5% |
| 全系统 RSS | 16.1 GB | **13.2 GB** |

## 二、磁盘资源优化（已执行 + 待决）

### 背景: 磁盘告急
- **/System/Volumes/Data: 429GB used / 460GB = 99% 满, 仅剩 6.4GB**

### 已执行(释放 ~1.5GB)
| 项 | 释放 |
|---|---|
| ollama server-1.log(旧轮转) | 197MB |
| 更新器缓存(coze/notion) | 636MB |
| Homebrew 缓存 + downloads | ~700MB |
| 合计 | **~1.5GB** → 空闲 6.4→7.9GB |

### 待决大项(需用户批准)
| 项 | 大小 | 说明 | 风险 |
|---|---|---|---|
| **Docker.raw** | **50GB** | Docker 守护未运行, 数据休眠 | 删除=丢所有 Docker 数据(Dify 等) |
| **iOS DeviceSupport** | 16GB | 3 版本(iPad 18.3.1/iPhone 26.6/26.6.1) | Xcode 可自动重下(慢); 明鉴 iOS 部署相关 |
| **CoreSimulator** | 11GB | 模拟器设备 | 删除不可用模拟器安全 |
| **Coze Drive 归档分片** | **14.5GB** | drive-part-aa~ad(拆分 tar) | ~/Coze/Drive 已解包(104,957 文件/15GB)疑冗余 |
| Xcode DerivedData | 410MB | 构建缓存 | 安全 |
| flower-102cls-yolo.zip | 781MB | 源 zip(dataset 已解 3.2GB) | 安全 |
| CLD Setup 0.3.2.exe | 137MB | 安装包 | 可重下 |

### ⚠️ 禁删(已标记)
- **MTM profiles 7.4GB**(~/Library/Caches/外卖门店多平台管理/profiles/)——**13 个店铺登录会话目录(s2-s14, 各~1GB)**, 删=所有店铺掉登录

## 三、遗留问题(需协作修复)

1. **agent-bus.json 1170 条 queued 死信**(16.5MB)——CPU 风暴燃料; TOP: 星舵 456/cld-monitor 157/明鉴 59
   - 死目标 90 组 572 条 + 陈旧活目标(e7bfeea8 退役/f38244df 明鉴v2)
2. **queue-drain 工具坏了**——返回 null(读不到 bus), 无法正规清队列
3. **queue-watch 二进制 bug**(600ms vs 600000ms)——需 Rust 重编译(星桥/知了)
4. **若重启 MCP 服务会再风暴**(队列未清 + bug 未修)——建议保持停止直到修复

## 四、建议后续

| 优先 | 动作 | 负责 |
|---|---|---|
| P0 | 用户裁决 Docker.raw 50GB / Coze 分片 14.5GB 去留 | 用户 |
| P0 | 修复 queue-drain 工具 + queue-watch 600ms bug | 星桥/知了(Rust) |
| P1 | 清 agent-bus.json 死信队列(host 侧或工具修复后) | 星桥+HR |
| P1 | iOS DeviceSupport 旧版本清理(明鉴确认后) | 明鉴+HR |
| P2 | 磁盘常态监控(阈值告警) | HR |

---
*报告 v1.0 · HR 司库 · 2026-09-11*
