#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""task-card-validator.py v1.0 — 任务卡 schema 校验器（纯规则零 LLM）

mac总线 → 黑板 → i9总线 的任务卡，必须过此校验才能挂黑板。
任务卡是「执行指令」不是「聊天文本」——本地模型展开可能出错，
schema 校验是生死线：action 白名单 + payload 类型 + 路径白名单 + 危险命令拦截。

用法:
  python3 task-card-validator.py --check '<json任务卡>'   # 校验单张
  python3 task-card-validator.py --stdin                   # stdin 批量
  退出码: 0=合法 1=非法（打印原因）

命名约定：mac总线（mac-mini 中枢/派单）→ i9总线（PC-i9 节点/执行）

★ 约束门（⑩）：N/A —— 本工具【不执行外部命令、不删除数据、不修改权限】。
依据：r006-debt-assess.py 机械扫描未检出以下原语：
      subprocess / os.system / eval / exec / os.remove / rmtree /
      os.chmod / os.chown / os.kill / pkill / launchctl unload / 任意写路径参数
★ 限度：此为【模式匹配】结果，可能有漏；引入上述任一原语时须更新本声明。
"""

# ═══ ★ R006 ② TCC 能力边界自检（--selfcheck）═══
#   ★ 由 r006-retrofit-apply.py 自动生成（2026-10-09）——
#   三段内容取自【本工具实际被检测到的结构】，非空模板。
def selfcheck():
    import sys as _sys, os as _os
    print("== task-card-validator 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · task-card-validator.py v1.0 — 任务卡 schema 校验器（纯规则零 LLM）")
    print("  · mac总线 → 黑板 → i9总线 的任务卡，必须过此校验才能挂黑板。")
    print("  · 任务卡是「执行指令」不是「聊天文本」——本地模型展开可能出错，")
    print("  · schema 校验是生死线：action 白名单 + payload 类型 + 路径白名单 + 危险命令拦截。")
    print("  · 命令/参数: check, stdin")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, os, time")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/task-card-validator.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, sys, re

# ===== action 白名单（i9 总线 5 类 + GeneBank 基因操作）=====
import os

# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/task-card-validator.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

ACTIONS = {"shell", "info", "ollama", "scan", "数据沉淀",
           "gene.register", "gene.query", "gene.list"}

# ===== 各 action 的 payload schema =====
SCHEMAS = {
    # GeneBank 基因操作（AI 网盘）
    "gene.register": {
        "required": ["manifest"],
        "types": {"manifest": dict},
        "manifest_required": ["gene_id", "name", "chromosome", "body", "expression", "heredity"],
        "chromosome_enum": ["models", "datasets", "corpora", "knowledge", "artifacts", "recipes"],
    },
    "gene.query": {
        "required": [],
        "types": {"gene_id": str, "chromosome": str},
    },
    "gene.list": {
        "required": [],
        "types": {"chromosome": str},
        "chromosome_enum": ["models", "datasets", "corpora", "knowledge", "artifacts", "recipes"],
    },
    "shell": {
        "required": ["cmd"],
        "types": {"cmd": str},
        "max_len": {"cmd": 2000},
    },
    "info": {
        "required": [],
        "types": {},
        "max_len": {},
    },
    "ollama": {
        "required": ["prompt"],
        "types": {"model": str, "prompt": str},
        "max_len": {"prompt": 4000},
    },
    "scan": {
        "required": ["path"],
        "types": {"path": str, "depth": int},
        "max_len": {},
        "path_whitelist": True,
    },
    "数据沉淀": {
        "required": ["path", "target"],
        "types": {"path": str, "target": str},
        "max_len": {},
        "path_whitelist": True,
    },
}

# ===== 路径白名单（i9 可访问目录，含盘符）=====
PATH_WHITELIST_PREFIXES = ["E:\\", "E:/", "E:", "D:\\", "D:/",
                           "C:\\Users\\admin", "C:/Users/admin"]
# 禁扫系统路径
PATH_BLOCKLIST = ["C:\\Windows", "C:/Windows", "C:\\Program Files",
                  "C:\\ProgramData", "C:\\Users\\admin\\AppData", "C:\\$Recycle"]

# ===== 危险命令拦截（shell action，删除类一律拦截——宁严勿松）=====
DANGEROUS_PATTERNS = [
    # 格式化/分区/磁盘级（精确匹配：format+盘符才是格式化磁盘；--format= 参数不拦）
    r"(?i)\bformat\s+[a-z]:", r"(?i)\bdiskpart\b", r"(?i)\bmkfs", r"(?i)\bdd\s+if=",
    # 关机/重启
    r"(?i)\bshutdown\b", r"(?i)\brestart\b",
    # 注册表/用户/进程（系统级）
    r"(?i)\breg\s+delete", r"(?i)\bnet\s+user", r"(?i)\bwmic\s+process\s+call\s+terminate",
    r"(?i)\bsc\s+delete", r"(?i)\bschtasks\s+/delete",
    # 删除类命令（del/erase/rm/rd/rmdir/remove-item/remove + 任何盘符/通配/递归形式）
    r"(?i)\bdel\b", r"(?i)\berase\b", r"(?i)\brm\b", r"(?i)\brd\s+/s",
    r"(?i)\brmdir\s+/s", r"(?i)\bremove-item\b", r"(?i)\bremove\s+[a-z]:",
    r"(?i)\brmdir\b", r"(?i)\bdelete\b",
    # 递归/通配删除特征（\*.*、/s 递归、盘符通配）
    r"(?i)\\\*\.\*", r"(?i)\b/s\b", r"(?i)\b/r\b",
]

def validate(card):
    """校验任务卡，返回错误列表（空=合法）"""
    errors = []
    if not isinstance(card, dict):
        return ["任务卡必须是 JSON 对象"]
    tid = card.get("task_id")
    if not tid or not isinstance(tid, str):
        errors.append("task_id 必填且为字符串")
    action = card.get("action")
    if action not in ACTIONS:
        errors.append("action 不在白名单: %s（允许 %s）" % (action, sorted(ACTIONS)))
        return errors  # action 错直接拒，不继续
    payload = card.get("payload", {}) or {}
    if not isinstance(payload, dict):
        return ["payload 必须是对象"]
    schema = SCHEMAS[action]
    for field in schema.get("required", []):
        if field not in payload:
            errors.append("%s 缺必填字段 payload.%s" % (action, field))
    for field, ftype in schema.get("types", {}).items():
        if field in payload and not isinstance(payload[field], ftype):
            errors.append("payload.%s 类型应为 %s（实为 %s）"
                          % (field, ftype.__name__, type(payload[field]).__name__))
    for field, mlen in schema.get("max_len", {}).items():
        if field in payload and len(str(payload[field])) > mlen:
            errors.append("payload.%s 超长（%d > %d）" % (field, len(str(payload[field])), mlen))
    # 路径白名单（scan/数据沉淀）
    if schema.get("path_whitelist"):
        path = str(payload.get("path", ""))
        if not any(path.startswith(p) for p in PATH_WHITELIST_PREFIXES):
            errors.append("路径不在白名单: %s（允许 E:/D:/C:\\Users\\admin 前缀）" % path)
        if any(path.startswith(p) for p in PATH_BLOCKLIST):
            errors.append("路径在禁扫名单: %s" % path)
    # 危险命令（shell）
    if action == "shell":
        cmd = str(payload.get("cmd", ""))
        for pat in DANGEROUS_PATTERNS:
            if re.search(pat, cmd):
                errors.append("命令含危险操作（命中: %s）" % pat)
    # GeneBank 基因操作校验
    if action.startswith("gene."):
        _validate_gene(card, payload, schema, errors)
    return errors

def _validate_gene(card, payload, schema, errors):
    """gene.* 操作校验：manifest 必填 + 染色体枚举"""
    # 染色体枚举（gene.list/gene.register）
    chrom_enum = schema.get("chromosome_enum", [])
    chrom = payload.get("chromosome")
    if chrom and chrom not in chrom_enum:
        errors.append("chromosome 不在标准染色体: %s（允许 %s）" % (chrom, chrom_enum))
    # manifest 校验（gene.register）
    if schema.get("manifest_required"):
        manifest = payload.get("manifest")
        if not isinstance(manifest, dict):
            errors.append("gene.register 缺 payload.manifest（对象）")
            return
        for f in schema["manifest_required"]:
            if f not in manifest:
                errors.append("manifest 缺必填字段: %s" % f)
        mchrom = manifest.get("chromosome")
        if mchrom and mchrom not in schema["chromosome_enum"]:
            errors.append("manifest.chromosome 不在标准染色体: %s（允许 %s）" % (mchrom, schema["chromosome_enum"]))
        mid = manifest.get("gene_id", "")
        if mid and not re.match(r"^sha256:[a-f0-9]{64}$", str(mid)):
            errors.append("manifest.gene_id 格式应为 sha256:<64位hex>")
        mut = manifest.get("heredity", {}).get("mutation", "")
        if mut and not re.match(r"^\d+\.\d+\.\d+$", str(mut)):
            errors.append("manifest.heredity.mutation 应为语义版本 1.0.0")

def main():
    ap = argparse.ArgumentParser(description="任务卡 schema 校验器")
    ap.add_argument("--check", help="校验单张任务卡 JSON 字符串")
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--stdin", action="store_true", help="从 stdin 批量校验（每行一张）")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    if args.check:
        try:
            card = json.loads(args.check)
        except json.JSONDecodeError as e:
            print("❌ JSON 解析失败: %s" % e)
            sys.exit(1)
        errs = validate(card)
        if errs:
            print("❌ 非法: " + "; ".join(errs))
            sys.exit(1)
        print("✅ 合法任务卡（mac总线 → i9总线）")
    elif args.stdin:
        ok = True
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError as e:
                print("❌ JSON 解析失败: %s" % e)
                ok = False
                continue
            errs = validate(card)
            if errs:
                ok = False
                print("❌ %s: %s" % (card.get("task_id", "?"), "; ".join(errs)))
            else:
                print("✅ %s: 合法" % card.get("task_id", "?"))
        sys.exit(0 if ok else 1)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
