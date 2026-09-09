# MBP 端 SystemGraph 资产吸收归罗盘 · 协调安排 v1

> 明鉴 v2 · 2026-09-06 · 用户指示「MBP 端 SystemGraph 相关全吸收回罗盘」
> 黑板: notes/session-f38244df/absorb-mbp-sg-to-luopan · 状态: 已落盘待相关方确认

## 一、意图
SystemGraph v1.4.0 三端(mac-mini/iPad/iPhone)已就绪。MBP 上所有与系统架构管理器相关的
资产/部署/维护收敛回本机, 由罗盘(设备协调中枢 session-5a5368af)统一登记管理。
MBP 不再独立维护 SystemGraph 副本——主源/版本/数据主权在 mac-mini。

## 二、吸收清单
| # | MBP 侧项 | 处置 | 归属 |
|---|---------|------|------|
| 1 | /Applications/SystemGraph.app(MBP 装副本) | 登记为"远端安装副本"(device-assets) | 罗盘 |
| 2 | 黑板 notes/mbp/ SystemGraph 相关(plan-archive-reply/cloudbase-mirror/sg-v140-install-task) | 归档收口至本机 | 明鉴/罗盘 |
| 3 | MBP plan-archive 11 项回报 | ✅ 已并入 plan-archive.json(68项) | 明鉴 |
| 4 | CloudBase 推送通道(~/.cloudbase-mcp) | 保留(数据镜像用, 跨设备部署能力) | 老登域 |
| 5 | 远端优先加载链 | MBP 若装 app 则走 Funnel→本地, 数据仍本机 | 壳机制 |

## 三、分工
- **罗盘**: device-assets 登记 MBP 安装副本; task-env-map 记部署关系; 只保留"安装副本"认知
- **老登/MBP 域**: 确认安装或不装(由罗盘统一管); CloudBase 通道保留
- **明鉴(mac-mini)**: 主源维护/版本/数据/蓝图/工具(不变)

## 四、为什么这样分(用户判断)
- SystemGraph 主服务/数据/工具全在 mac-mini; MBP 只是展示副本(远端优先壳)
- 吸收回罗盘 = 设备资产认知统一(罗盘管设备), 避免 MBP 独立维护产生版本漂移
- R031: 主源本地执行, MBP 不代理

## 五、验证
- [ ] 罗盘 device-assets 含 MBP SystemGraph 条目
- [ ] 黑板 mbp 域 SystemGraph 相关收口标记
- [ ] MBP 若装 v1.4.0 走远端优先(数据本机)
