# 2026-08-30-collab-channel-pollution 独立项目误走 collab 广播污染端节点上下文

> 级别: P1 · 日期: 2026-08-30

## 现象
同盟法辅等独立项目消息全写 notes/collab/ 广播通道，i9/MBP node-bridge 全量监听 collab → 无关项目消息落入 inbox → 上下文污染 + 可能误触发 LLM

## 根因
① 发送方把 collab 当默认通道（R002 未执行）② node-bridge notes_loop 对 collab 无差别全收（main.rs starts_with notes/collab/）③ 协调者只确认不纠偏

## 修复
① node-bridge v1.4.0 collab 白名单（只收 to/target/mentions 定向自己 + --collab-subs 订阅）实测 i9 164→21 条 ② dsh-tools v1.14.0 channel-audit 巡检（launchd 每小时 + 违规登记黑板）③ 通道纠偏通知 data/tongmeng/channel-correction-20260830

## 教训（→ SOP 更新点）
广播通道是默认不是特权——「图省事走广播」会几何级放大污染（N 端 × 全量收）。主动巡检机制（channel-audit）比依赖人发现强：当场抓出 8 条真违规含协调者自己

## SOP 更新
通道卫生 SOP：collab 仅限全局公告；定向消息走 notes/<node>/ 或 data/<域>/；channel-audit 每小时巡检 + 违规登记
