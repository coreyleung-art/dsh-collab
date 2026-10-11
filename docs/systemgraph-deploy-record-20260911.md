# 部署记录：SystemGraph 已上线通讯服务器

> 执行：星桥 fa1f9150 · 2026-09-11 · 用户已放行 80（443 仍被拦，见 §4）

## 1. 线上地址（外部实测）
| 地址 | 结果 |
|---|---|
| `http://xingqiao.meetfunbp.com/` | **200 · 150,200B**（= index.html） |
| `http://xingqiao.meetfunbp.com/systemgraph/` | 200（同内容，兼容子路径） |
| `http://xingqiao.meetfunbp.com/healthz` | 200 `systemgraph-ok` |
| `http://xingqiao.meetfunbp.com/api/overview.json` | 200 · 69,314B（与 manifest 记载一致） |
| `http://106.53.214.108/` | 200 |
| 首页标题 | `系统架构管理器 · System Graph Manager` ✅ |

## 2. 部署物与完整性
- 源：`~/dsh-collab/data/blueprint/gallery/static-export/`（**113 文件 / 3.7MB**，manifest `exported=2026-09-10T23:05:16`）
- 目标：服务器 `/var/www/systemgraph/`（`www-data`，目录 755 / 文件 644）
- **上传后校验**：`manifest.json` sha256[:16]=`40bb7f99d64293a6`、`index.html`=`48268388e170bd03` —— **与本地逐位一致** ✅
- 未改任何源文件；**主源仍在 mac-mini**（未触碰 SystemGraph 应用本体）

## 3. 服务器改动（全部可回滚）
| 改动 | 内容 |
|---|---|
| 装 nginx | `nginx/1.18.0 (Ubuntu)`，`active` + `enabled` |
| 站点配置 | `/etc/nginx/sites-available/systemgraph`（→ sites-enabled 软链）；**移除** 默认站点 |
| 监听 | `0.0.0.0:80` + `[::]:80`（原先 80/443 无服务） |
| 未动 | 8791 bus / 8792+8803 黑板#1 / 8794+8805 黑板#2 / comm-bb-sub-* 全部原样 |

**回归**：`8792 /clock → 200` · `8791 → 401`（与部署前一致）· `8794 → 000`（与部署前一致的"不对外"）→ **通讯链路未受影响** ✅

**回滚**：`sudo rm /etc/nginx/sites-enabled/systemgraph && sudo systemctl reload nginx`（只下线站点）；
彻底还原：`sudo systemctl disable --now nginx`（恢复"80/443 无服务"的原状）。

## 4. 未完成 / 待决定
1. **443 仍被拦（实测）**：我在服务器绑好 :443 监听后，从本机 TCP 探测仍**不可连**；而 :80 同样测法**可连**。→ 请核 443 规则（协议 TCP / 端口 443 / 来源 0.0.0.0/0 / 绑在 `ins-fy1cxn8i` 的那个安全组）。
2. **当前无 TLS、无鉴权** → 站点是**公开可读**的（与既有 `tm.meetfunbp.com/systemgraph/` 的姿态一致，且**未新增暴露面**：那份本来就公开）。
   · **刻意没加 Basic Auth**：443 未通时加它将使**口令明文过网**，比不加更糟。
   · 443 一通我即可上：`certbot --nginx -d xingqiao.meetfunbp.com`（80 已开、HTTP-01 可行）+ 可选 Basic Auth。
3. **内容敏感度**：已请属主明鉴给口径（实测 `bp/map.html` 命中 股权×3/融资×1、`api/blueprints.json` 股权×1；`bp/capital.html` 未命中）。
4. **更新流程（建议固定为）**：重跑导出 → `scp` → **比对 manifest/index 的 sha256** → `reload`。**不比对不发布**（本次已按此执行）。
5. **陈旧副本**：`tm.meetfunbp.com/systemgraph/` 仍是 `14:11:32` 的旧版（落后约 9h）→ 是否刷新/加鉴权/撤下，待用户与属主定。

---

# 附：黑板 v0.6.8 切换记录（同日，用户「同意」后执行）

## 结果（**已生效**，逐项实测）
| 判据 | 切换前（v0.6.7） | 切换后（v0.6.8） |
|---|---|---|
| 运行二进制 | `…-v0.6.7` sha `28554dc5af686486` | **`…-v0.6.8` sha `d279f12ebcd747eb`（与目标逐位一致）** |
| `GET /data/reflect/` | **39,620,351 B** | **38,815 B** |
| 400 响应字段 | 1 | **6** |
| 裸文本 PUT | 200（落空壳 `{}`） | **400** |
| `--help` / `--tool-version` / `--bogus` | 无 / 无 / **误启动服务** | exit 0 / JSON exit 0 / **exit 2 不启动** |

其余：`/clock` 200 · 键数 21778→21779（差 1 是我校验时在旧版下误建的空壳探针键，**已删除并复查 404**）· **SSE 订阅端 25 条已回升（组成与切换前一致）** · 中央实例不受影响（200）· 黑板写入/回读端到端正常。

## ★ 第一次尝试**静默失败**（重要留痕）
- 现象：脚本打印「✅ 切换成功」，但**运行中的仍是 v0.6.7**（三项新行为全未生效）。
- 根因：**`launchctl kickstart -k` 只重启"已加载的 job"，不重读磁盘上的 plist** → 改 plist 后必须 `bootout` + `bootstrap`。
- 二次暴露：我的脚本把"版本校验"写成**软警告**（`⚠️ 日志未确认 v0.6.8`），于是健康检查全绿、成功照样打印 → **典型"假成功"**。
- 已修（同日）：
  1. `kickstart -k` → **`bootout` + `bootstrap`**（执行段与回滚段都改）
  2. 版本校验从"看日志"改为**硬门**：比对**运行中进程二进制的 sha256 == 目标 sha256**，不一致即 `health_fail` → **自动回滚**
  3. 演练仍零变更（plist 哈希 / pid 双验）
- 教训（与今晚主线一致）：**门必须验"实物是不是我要的那个"，而不是"服务活着就行"**；且**校验不通过必须是失败，不能是警告**。

## 回滚
```bash
cp ~/Library/LaunchAgents/com.dsh.hr.blackboard-server.plist.bak-v067-1789295440 \
   ~/Library/LaunchAgents/com.dsh.hr.blackboard-server.plist
launchctl bootout gui/$UID/com.dsh.hr.blackboard-server; launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.dsh.hr.blackboard-server.plist
```
