# 企业微信机器人 Webhook 配置模板（供 aa528267 等会话复用）

## 获取 webhook
企业微信 → 群 → 右上角 → 群机器人 → 添加 → 复制 webhook URL：
`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<KEY>`

## 推送脚本（Python）
```python
import json, urllib.request
WEBHOOK = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=<KEY>"
def push(text: str):
    data = json.dumps({"msgtype": "text", "text": {"content": text}}).encode()
    req = urllib.request.Request(WEBHOOK, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status
# 告警示例
push("⚠️ 外卖面板 8787 掉线已自动拉起（时间戳）")
```

## 告警接入点建议
- 面板看门狗（com.sysops.waimai.watchdog）恢复失败时推送
- 每日经营日报/异常检查结果定时推送
- 可配合 sysops health 的 ❌ 状态触发
