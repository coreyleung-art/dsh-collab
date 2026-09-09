# 会议人物身份图谱 · CLI + GUI 使用手册 v1

> 明鉴 · 2026-09-09 · R006 十项全达标 · 用户开会念名字即查身份

## 一、两组件

| 组件 | 路径 | 端口/形态 |
|---|---|---|
| CLI | ~/dsh-collab/scripts/identity-graph.py | 命令行 |
| GUI | ~/dsh-collab/scripts/identity-graph-gui.py | http://127.0.0.1:8811 |
| 图谱库 | ~/dsh-collab/data/meeting-identity-graph.json | 10 人物 + 7 组织 |

## 二、GUI 用法（推荐开会时用）

```bash
python3 ~/dsh-collab/scripts/identity-graph-gui.py   # 启动 → http://127.0.0.1:8811
```

六个页签：
1. **关系图谱** — 人物↔组织关系图(点击节点查身份)
2. **人物档案** — 全部人物卡(组织/角色/置信度)
3. **扫描识别** — 粘贴会议转写 → 自动识别在场/被谈人物(点击即查)
4. **查身份** — 输名字(支持别名)秒回身份卡
5. **组织** — 7 组织卡片
6. **登记人物** — 听到新名字当场登记(进入图谱)

## 三、CLI 用法

```bash
python3 identity-graph.py --scan <会议转写.txt>    # 动态识别谁在场/被谈
python3 identity-graph.py --identify 于总          # 查身份卡
python3 identity-graph.py --graph mermaid|json     # 关系图谱
python3 identity-graph.py --org 声通               # 查组织+成员
python3 identity-graph.py --add-person --name X --title Y --org Z --aliases "a,b"  # 登记(唯一写入口)
python3 identity-graph.py --selfcheck              # TCC
python3 identity-graph.py --lean4-check            # R006#10 约束门
```

## 四、R006 十项达标

| # | 项 | CLI | GUI |
|---|---|---|---|
| ① | CLI 形态 | ✅ | ✅(--port/--host) |
| ② | TCC | --selfcheck | --selfcheck |
| ③ | CLD 自适应 | 纯 py | 纯 stdlib |
| ④ | 版本自适应 | --tool-version v1.0.0 | --tool-version |
| ⑤ | 文档化 | 本文档 | 内嵌帮助 |
| ⑥ | 版本管理 | ✅ | ✅ |
| ⑦ | 统一日志 | GUI 日志 | 内嵌 |
| ⑧ | 自动落链 | 资产已登记 asset-map | ✅ |
| ⑨ | CLI 治理 | argparse 规范 | ✅ |
| ⑩ | Lean4 约束门 | --lean4-check PASS(写入仅限 add-person) | API 写门控(重名拒) |

## 五、图谱维护约定

- 用户开会念名字 → 用 --identify 查 或 GUI 查身份
- 新名字 → GUI "登记人物" 或 CLI --add-person（唯一写入口）
- Speaker 编号跨会议变化 → 图谱 speakers 字段稳定映射（9-05场S7=振宇 vs 09-08场S5=振宇）
- 待确认人物(Speaker4资源方/Speaker3蓝图方) → 用户念名字后登记补全

---
*identity-graph 手册 v1 · 明鉴 · 2026-09-09*
