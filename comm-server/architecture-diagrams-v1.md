# 星桥系统架构图（2026-09-06 · 双轨制实况）

> 维护：星桥 fa1f9150 · 版本 v1.0 · 同步对象：明鉴（SystemGraph 蓝图）

## 一、星桥全局架构（双轨制）

```
👤 用户端
├── 📱 星台 App（iPhone/iPad/macOS）——经 Funnel 公网
└── 🖥 CLD GUI（星桥对话窗）

☁️ 通讯中枢 xingqiao.meetfunbp.com（Ubuntu 22.04 · 2026-09-06 上线）
├── Prod 黑板 :8792/:8803（跨设备事实源/镜像）rust-blackboard v0.6.0
└── Test 黑板 :8794/:8805（隔离测试区，升级验证）

💻 mac-mini 本机（主·8ms 低延迟）
├── 本机黑板 :8792/:8803（rust-blackboard v0.6.7）
├── 星台桥 :8820（sb-mobile-bridge，launchd）
├── central-inbox（SSE 8803 → 会话注入）
├── 同步层×3（launchd）
│   ├── sync-to-central.py（上行同步 5min）
│   ├── sync-from-central.py（下行同步 5min）
│   └── hb-forward.py（心跳镜像 30s）
├── CLD 宿主 → ⭐星桥（协调者）→ 角色 Agent×30（明鉴/老登/知了/驿使/灯塔/守灯/守灯塔/守望/文汇/司库/拾光/回声/罗盘…）

💻 MacBook Pro
├── node-bridge v1.4.0（连本机黑板 100.120.203.20:8792，低延迟）
└── MBP Agent（mbp-bus）——旧通道保留=降级备灾

🖥 PC-i9 Windows
├── i9 executor（轮询 notes/i9/ 域）
└── i9 协调会话——本地通道主用 + 可直写中枢

关键链路：
1. 星台→星桥：App → Funnel /sb → 桥 → mobile-inbox → central-inbox → 星桥会话 → 回复 latest-main → App 轮询
2. 双轨同步：本机 ↔ 中枢（上行/下行 5min + 心跳 30s 镜像）
3. 跨设备：MBP/i9 本地通道主 + 中枢镜像（中枢挂→本机照常，R031 通讯永续）
4. 星台↔i9 建联：target=i9 → sb-dialog-task → i9 消费 → starbridge-reply-latest → 星台（推进中）
```

## 二、星台架构（App 全链路）

```
📱 星台 App（SwiftUI）
├── 输入区：🎤语音模式切换 / 📷相册选图 / ⌨文本
├── 消息列表：气泡/图片/智能体名候选弹窗
├── 左滑抽屉：设备内 Agent 切换（v9.7）
├── ChatModel：消息/轮询/持久化（每目标独立 chat-history.json）
└── SpeechManager：语音识别

🔗 星台桥 :8820（零依赖 Node）
├── /api/chat     消息 + target 跨设备路由
├── /api/upload   图片 base64 → uploads/
├── /api/correct  语音 LLM 纠错 → ollama qwen2.5:3b
├── /api/reply    读回复（latest-main/mbp/i9 分键）
├── /api/devices  设备 + Agent 清单
└── /api/queue    真实排队（10min 窗口+死信清理）

🌐 Funnel：coreymac-mini.taild3fd86.ts.net/sb（公网可达）

📋 黑板层
├── mobile-inbox/      星台发消息
├── mobile-reply/      latest-main / latest-mbp / (i9→starbridge-reply-latest)
├── uploads/           图片存储 + 静态服务
└── sb-dialog-task     i9 跨设备路由

🤖 会话处理
├── central-inbox（SSE 注入）
├── ⭐星桥会话（协调者）
└── 定向 Agent（i9/MBP/角色，central-inbox v2 定向注入）

🧠 后端模型
├── ollama qwen2.5:3b（语音纠错）
└── LM Studio glm-4.6v（图片视觉理解）
```

## 三、Lean4 治理要点（Φ9 约束前置）
- 服务器：Prod/Test 类型化隔离（数据目录永不复用）
- 约束层：访问（密钥-only）/ token / 变更门（无验证成功=未成功 R030）
- 双轨不变量：本机主 + 中枢镜像；旧通道保留=降级备灾；通讯永续（R031 P3）
- 多门店预留：notes/store-<id>/ 命名空间

## 附：治理文档引用
- ~/dsh-collab/comm-server/server-governance-v1.md
- ~/dsh-collab/comm-server/dual-track-plan-v1.md
- ~/dsh-collab/ops/comm-server-architecture-r032.md
