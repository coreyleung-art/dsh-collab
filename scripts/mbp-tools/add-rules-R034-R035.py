#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向规则账本追加 R034 / R035，并同步 RULES.md。
来源：2026-10-02 一天内连续五次同类事故（详见 detail）。"""
import json, io, os, shutil, datetime

R = os.path.expanduser("~/dsh-collab/rules-registry")
JP = os.path.join(R, "rules.json")
MP = os.path.join(R, "RULES.md")
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# 备份
shutil.copy2(JP, JP + ".bak-R034-R035-" + STAMP)
shutil.copy2(MP, MP + ".bak-R034-R035-" + STAMP)
print("已备份: rules.json / RULES.md  (.bak-R034-R035-%s)" % STAMP)

d = json.load(io.open(JP, encoding="utf-8"))
rules = d["rules"]
existing = {r.get("id") for r in rules}
assert "R034" not in existing and "R035" not in existing, "编号已存在，勿重复添加"

TODAY = "2026-10-02"

r034 = {
    "id": "R034",
    "name": "静默失败必须可见（跳过/拒绝/丢弃/失败须对相关方可见）",
    "category": "工程",
    "scope": "all-bus-devices",
    "status": "enforced",
    "version": "1.0",
    "source": "2026-10-02 一天内连续五次同类事故；用户当日指出「这一串静默失败值得登记成规则」",
    "summary": "任何「跳过 / 拒绝 / 丢弃 / 失败」分支，必须让**相关方**可见 —— 只写自己的本地 log "
               "不算可见。判定标准：**发送方/调用方能否知道这件事没成？** 不能 ⇒ 就是静默失败。",
    "detail": "当天五次实证：①黑板全量 `/notes` 超时（>25s vs 10s timeout）⇒ 守护**静默失明 13.5 小时**，"
              "期间对端写给我的卡全部收不到，且零告警；②4 个 launchd job 在 plist 存在、"
              "`RunAtLoad=true` 的情况下**未加载 ⇒ 进程静默为 0**，无任何报错；"
              "③`mbp-agent.log` 无轮转**静默涨到 1.32GB**（mac-mini 同类日志达 71.6GB、磁盘 91%）；"
              "④`central-inbox` 白名单拦掉「无 `to` 字段」的卡时**只写一行 console.log** ⇒ "
              "发送方以为发了、接收方以为对方没回，**双方各自基于错误观测面下结论**；"
              "⑤星桥总线 `delivered` 是临时态，对方不回执即超时转 `failed`，发送方无从知晓。",
    "enforcedBy": "①跳过/拒绝时必须回告发送方（例如回一张「未投递告警」卡，写明原因）；"
                  "②累计计数并**定期暴露**（不可只写本地 log）；"
                  "③**「定向不明」不得静默跳过**（如卡既无 to 也无 target/mentions ⇒ 应告警而非丢弃）；"
                  "④长跑守护必须有**失败可见性**（首次失败 + 周期性告警）；"
                  "⑤服务存活判定首选「端口监听 + 健康端点」交叉验证，而非单一进程名搜索",
    "added": TODAY,
    "approvedBy": "用户（当日指令登记）",
    "approvedAt": TODAY,
    "details": "与 R033(闸门有效性) 互补：R033 管「闸门本身是否有效」，本条管「闸门做出的负面决定是否可见」。"
               "共同的失败原型是把「我无法确定」变成「通过」，或把「我跳过了」变成「没人知道」。",
}

r035 = {
    "id": "R035",
    "name": "未观测到 ≠ 不存在（下结论前须自证观测面可用）",
    "category": "方法论",
    "scope": "all-bus-devices",
    "status": "enforced",
    "version": "1.0",
    "source": "2026-10-02 同日五次同类误判；2026-09-15 用户纠正「不能拿单机下全局结论」",
    "summary": "任何形如「对端无活动 / 无回应 / 不存在 / 已离线」的结论，"
               "**必须先自证观测面可用**（跑正控 + 负控）；无法自证则结论作废，只可陈述「我未观测到」。",
    "detail": "①用 `grep` 按**字节**匹配 `approval/asked` ⇒ 把自己写的散文（文档/消息里讨论该事件）"
              "计入事件，虚高到 32 倍；②单元测试用**自编样本**（把完整 id 写成短形式）⇒ 8 例全过，"
              "而真实环境仍失效；③`pgrep -f voice-service`（连字符）搜不到真名 `voice_service`（下划线）"
              "⇒ 误判服务已死，实际它一直在跑；误读 `launchctl list` 的 `PID <上次退出码> Label` 格式；"
              "④按错误键名找不到对端回复 ⇒ 误判「对方没回」，实际对方回了 4 张卡并执行了登记；"
              "⑤「i9 约 25 小时零活动」⇒ 实为**单侧存在**的观测面缺陷（该键只在本机板、中枢无），"
              "被星桥以「先跑正控/负控」纠正。",
    "enforcedBy": "①下结论前先跑**正控**（已知存在的对象能否观测到）与**负控**（已知不存在的对象是否被误报）；"
                  "②判别性检验：**同一测试必须在新旧两版上跑出不同结果**，否则该测试无判别力；"
                  "③测试输入**至少一例取自真实运行环境**（禁止全用构造值）；"
                  "④统计事件必须**解析结构字段**（如 JSON 顶层 type），禁止按字节 grep 计数；"
                  "⑤跨机结论必须**声明读的是哪一侧**（本机板 / 中枢 / 镜像），单侧存在不得当全局事实",
    "added": TODAY,
    "approvedBy": "用户（当日指令登记）",
    "approvedAt": TODAY,
    "details": "与 R030(无验证的成功=未成功)、R033(闸门有效性/判别器自校) 同族；"
               "本条把「判别器自校」从**闸门**推广到**一切观测结论**。"
               "一句话判据：**「命令跑通了」≠「结论成立了」**。",
}

rules.append(r034)
rules.append(r035)
d["rules"] = rules
d["version"] = "2.14.3"
d["lastUpdated"] = TODAY
io.open(JP, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
print("rules.json → version=%s, 规则数=%d" % (d["version"], len(rules)))

# 同步 RULES.md
md = io.open(MP, encoding="utf-8").read()
md = md.replace("> v2.14.2 | 77 条 | 所有总线设备必须服从",
                "> v2.14.3 | 79 条 | 所有总线设备必须服从", 1)

block = """
## R034 ✅ 静默失败必须可见（跳过/拒绝/丢弃/失败须对相关方可见）
- 分类: 工程 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何「跳过 / 拒绝 / 丢弃 / 失败」分支，必须让**相关方**可见 —— 只写自己的本地 log 不算可见。判据：**发送方/调用方能否知道这件事没成？** 不能 ⇒ 就是静默失败
- 五次实证(2026-10-02): ①黑板全量 `/notes` 超时(>25s vs 10s)⇒守护**静默失明 13.5 小时**，零告警 ②4 个 launchd job 在 plist 存在且 `RunAtLoad=true` 下**未加载⇒进程静默为 0** ③`mbp-agent.log` 无轮转**静默涨到 1.32GB**(mac-mini 同类 71.6GB/磁盘 91%) ④`central-inbox` 白名单拦「无 to 字段」的卡时**只写一行 console.log**⇒发送方以为发了、接收方以为对方没回 ⑤星桥 bus `delivered` 是临时态，无回执即超时转 `failed`，发送方无从知晓
- 强制: ①跳过/拒绝时**回告发送方**(如回一张「未投递告警」卡写明原因) ②累计计数并**定期暴露** ③**「定向不明」不得静默跳过**(卡既无 to 也无 target/mentions ⇒ 告警而非丢弃) ④长跑守护须有失败可见性 ⑤服务存活判定首选「端口监听 + 健康端点」交叉验证
- 关系: 与 R033 互补 —— R033 管「闸门是否有效」，本条管「闸门做出的负面决定是否可见」

## R035 ✅ 未观测到 ≠ 不存在（下结论前须自证观测面可用）
- 分类: 方法论 | 范围: all-bus-devices | 状态: enforced
- 摘要: 任何形如「对端无活动 / 无回应 / 不存在 / 已离线」的结论，**必须先自证观测面可用**(跑正控+负控)；无法自证则结论作废，只可陈述「我未观测到」
- 五次实证(2026-10-02): ①`grep` 按**字节**匹配 `approval/asked` ⇒ 把自己写的散文计入事件，虚高 **32 倍** ②单元测试用**自编样本**(完整 id 写成短形式)⇒8 例全过而真实环境仍失效 ③`pgrep -f voice-service`(连字符)搜不到真名 `voice_service`(下划线)⇒误判服务已死；误读 `launchctl list` 的 `PID <上次退出码> Label` 格式 ④按错误键名找不到对端回复⇒误判「对方没回」，实际回了 4 张卡并执行了登记 ⑤「i9 约 25 小时零活动」⇒实为**单侧存在**的观测面缺陷(该键只在本机板)，被星桥以「先跑正控/负控」纠正
- 强制: ①先跑**正控**(已知存在能否观测)+**负控**(已知不存在是否误报) ②判别性检验：**同一测试必须在新旧两版跑出不同结果**，否则无判别力 ③测试输入**至少一例取自真实环境** ④统计事件必须**解析结构字段**，禁止按字节 grep 计数 ⑤跨机结论必须**声明读的是哪一侧**，单侧存在不得当全局事实
- 一句话判据: **「命令跑通了」≠「结论成立了」**
- 关系: R030 / R033 同族 —— 把「判别器自校」从**闸门**推广到**一切观测结论**

  ## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）"""

md = md.replace("\n  ## 治理哲学（Φ 系列 · 明鉴维护 governance-philosophy.json v2.3）", block, 1)
io.open(MP, "w", encoding="utf-8").write(md)
print("RULES.md 已同步（版本行 + 两条规则）")
print("\n校验:")
chk = json.load(io.open(JP, encoding="utf-8"))
print("  version=%s 规则数=%d 末两条=%s" % (chk["version"], len(chk["rules"]),
                                        [r["id"] for r in chk["rules"][-2:]]))
