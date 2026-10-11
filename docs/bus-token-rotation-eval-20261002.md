# bus-bridge token 轮换评估（三期③ · 2026-10-02）

## 现状（实测）
- 服务器 bus-bridge 鉴权：单一 `WEBHOOK_TOKEN`（env root 600，32 字符），`authOk` 为**单 token 严格比对**。
- 客户端：我侧 `~/.dsh/bus-bridge-token`（0600）+ MBP 侧同值 token（历史分发）。
- 哈希互证：我侧与服务器 token sha256 一致（f060d1e76d180d0a）。

## 风险定级
| 风险 | 定级 | 说明 |
|---|---|---|
| token 泄露面 | 中 | 单 token 双端共享：任一端泄露即全局暴露；token 在 plist/环境中有明文历史（node-bridge plist 有明文 token 先例） |
| 无轮换 | 中 | 长期有效；泄露后无吊销路径（单 token 模式改一个=两端同步换，有窗口） |
| 服务器多端支持 | 缺口 | `authOk` 只支持单 token——「每端独立 token + 可单端吊销」（server-governance 1.3 的既定目标）未实现 |

## 轮换方案（建议）
1. **短期（低风险）**：季度手动轮换——生成新 token → 服务器 env 更新 + systemctl restart comm-bus-bridge → 两端 token 文件更新。窗口期 ~1 分钟内 bus 请求 401（device-daemon 失败计数兜底，红灯退避 60s 生效）。
2. **中期（结构）**：服务器 bus-bridge 改多 token 白名单（TOKEN → TOKENS 逗号分隔，`authOk` 改集合成员判定）→ 每端独立 token → 可单端吊销。改动=服务器代码（bus-bridge.js）+ 部署。
3. **判据**：轮换后 `GET /bus/receive` 新 token ok、旧 token 401（正负对照）；两端 bus send 全链路复测。

## 结论
优先级=中（无已发生泄露，但单点共享+无轮换是长期债）。建议随「服务器 bb-sub 升级」同批做（都要动服务器），合并为一次服务器变更窗口。
