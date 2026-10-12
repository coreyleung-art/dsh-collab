# 2026-08-30-http-header-empty-auth 无 token 时 HTTP 头提前结束（auth 空行导致 body 解析失败）

> 级别: P1 · 日期: 2026-08-30

## 现象
MCP bb_post/bb_put 无 token（BLACKBOARD_TOKEN 空）时，黑板注册/写入的 name 参数丢失（回退默认值 device）

## 根因
auth 头为空时仍输出 '\r\n' → Host 行后出现 '\r\n\r\n'（HTTP 头结束符）→ Content-Type/Content-Length 被当 body，body 解析失败

## 修复
auth 空=空串（不输出 \r\n），格式串 Host:\r\n{}Content-Type——头间单换行合法

## 教训（→ SOP 更新点）
手工拼 HTTP 请求时，可选头为空必须输出空串而非换行——\r\n\r\n 是头结束符，多余换行会截断头部

## SOP 更新
HTTP 请求构造 SOP：可选头（如 auth）空时输出空串；验证用 od -c 检查 \r\n 数量
