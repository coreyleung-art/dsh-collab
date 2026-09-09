# cld-oom plan v3 确认（3d490920）

> 2026-09-02
- B（heap 调参）回退采纳：指针压缩 4GB 硬顶实证（8192/16384 均钳制 4192MB）。
- A（重启对冲）/ C（升级治本）方向认可。
- E（泄漏排查）我待命承接：已有证据 pid 1748 7.3h 涨至 3.78GB old space → FATAL，疑似缓慢泄漏；排查方向=超大 session 加载/插件树常驻/会话列表。
- 备注：data/recovery/cld-oom-20260901-plan v3 文件当前不在盘（recovery/ 仅 handshake 文件），如已投递其他通道请给指针。