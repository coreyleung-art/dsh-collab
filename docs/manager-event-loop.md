# 管理器 GUI 操作 → 明鉴 回合感知闭环

## 机制
GUI 操作(建边/推进/merged/重要动作) → /api/manager-event → 黑板 notes/mac-mini/manager-actions/<ts>
明鉴每回合开头: `python3 ~/dsh-collab/scripts/bb-mgr-events.py --check`
- 新事件才显示(🔔=important), 已读不重复(seen 文件 ~/.dsh/inbox/mgr-events.seen)

## 明鉴纪律
- 每轮用户对话开始, 先跑 bb-mgr-events.py --check 感知管理器操作
- 遇 important 事件 → 主动确认/跟进(如新确认的连接是否要通知两端)

## 端到端
管理器操作(用户) → 黑板事件键 → (inbox-watch 落盘 + bb-mgr-events) → 明鉴感知 → 对齐/跟进
