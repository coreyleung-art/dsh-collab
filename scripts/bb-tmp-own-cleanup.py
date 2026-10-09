#!/usr/bin/env python3
"""清理我【可确证】的 /tmp 残留（其余归属无法确证者不动 —— 只审不代改）
可确证判据：该文件是我本次会话用 write 工具亲手生成的（idx_dump.txt 是我为索引卡验证生成的导出）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""
import os, shutil, hashlib


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/bb-tmp-own-cleanup.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

SRC = "/tmp/idx_dump.txt"
DSTDIR = os.path.expanduser("~/dsh-collab/audits/20261008")
DST = os.path.join(DSTDIR, "index-card-v2-snapshot.json")

print("=== 清理确证件 ===")
if os.path.isfile(SRC):
    before = hashlib.sha256(open(SRC, "rb").read()).hexdigest()[:16]
    shutil.move(SRC, DST)
    after = hashlib.sha256(open(DST, "rb").read()).hexdigest()[:16]
    print(f"  {SRC} -> {DST}")
    print(f"  sha256(前16) 移动前={before} 移动后={after} {'✅ 同一内容' if before == after else '❌ 内容变了'}")
    print(f"  /tmp 侧仍存在? {os.path.exists(SRC)}")
else:
    print(f"  {SRC} 不存在（可能已清）")

print("\n=== 我方在 /tmp 的剩余候选（需逐一确认是否我写的）===")
# 只列我可能有份的（本次会话我 write 过的文件名）
MINE_CANDIDATES = ["idx_dump.txt", "port_from_tmp.sh", "audit_port_scripts.sh", "rb_http1270018792.json",
                   "rb_http106532141088792.json", "audit_idx_verify.py", "audit_idx_verify2.py"]
for n in MINE_CANDIDATES:
    p = os.path.join("/tmp", n)
    print(f"  {'存在' if os.path.isfile(p) else '不存在'}  {p}")

print("\n=== 判据说明 ===")
print("  ① 文件名不可作归属判据：「含 audit」≠「裁判的」（作者所列 12 件中至少 5 件首行写明与通道/R048 有关）")
print("  ② 内容也不可作归属判据：117 个 /tmp 文件含裁判 session id，但多数只是**卡内容里引用了我**")
print("  ⇒ 归属只能靠“写入时留痕”⇒ **这正是 G11 writer 字段要解决的问题在 /tmp 层的重演**")
