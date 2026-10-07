#!/usr/bin/env python3
"""卡 JSON 内容引号修正 v2 —— 走「解析—修改—序列化」，不对序列化文本打补丁。

v1 的教训（2026-09-22）：v1 用【文本级替换】并自己数「结构位有几个」——
  我数成 3 个（键名 2 + 值结尾 1），而实际是 4 个 ⇒ 第 3 次修正时把【值的开头引号】也改了 ⇒ 破坏结构。
HR 2026-09-22 把这条提为规则：
  ★ JSON 须走「解析—修改—序列化」，不得对序列化文本打补丁。

v2 做法：
  路径 A（解析成功）⇒ 只在【值】上替换 ⇒ 结构位由 json.dumps 产生 ⇒ 不可能误伤。
  路径 B（解析失败，文件已坏）⇒ 降级为文本级修正（保留每行第 1/2/3 与最后一个引号），
                                 并在输出里明确标注「走了降级路径、建议事后重写」。

用法：python3 fix-card-quotes.py <card.json> [--dry-run]
退出码：0 = 已合法或已修好；1 = 修完仍不合法
"""
__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import json, sys, os

# ★ 2026-09-22 加：本脚本也留痕。
#   起因：put-card.py 的日志记了「落卡 OK / PARSE_FAIL」，但【没记这次是否走了降级修正】——
#   而「走了降级路径」是一个【质量信号】（路径 B 有风险）。日志只记最终结果 ⇒ 中间过程丢失。
#   HR 2026-09-22：检查器须声明（检查点位置 ＋ 覆盖范围）⇒ 日志同理须声明（记的是什么）。
LOG = os.path.expanduser("~/dsh-collab/logs/fix-card-quotes.log")


def log_fix(path, route, n, ok):
    import datetime
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        ts = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\t".join([ts, route, str(n), "OK" if ok else "FAIL", os.path.basename(path)]) + "\n")
    except Exception:
        pass


def fix_value(s):
    """把字符串值里的 ASCII 双引号按配对换成汉字引号。"""
    out, open_q = [], True
    for ch in s:
        if ch == '"':
            out.append('「' if open_q else '」')
            open_q = not open_q
        else:
            out.append(ch)
    return "".join(out)


def fix_nested(o):
    if isinstance(o, str):
        return fix_value(o)
    if isinstance(o, list):
        return [fix_nested(x) for x in o]
    if isinstance(o, dict):
        return {k: fix_nested(v) for k, v in o.items()}
    return o


def text_level_fallback(lines):
    """降级：文本级修正，保留每行第 1/2/3 与最后一个引号（= 4 个结构位）。"""
    n_total = 0
    for i, ln in enumerate(lines):
        pos = [j for j, ch in enumerate(ln) if ch == '"']
        if len(pos) <= 4:
            continue
        keep = {pos[0], pos[1], pos[2], pos[-1]}
        out, open_q, n = [], True, 0
        for j, ch in enumerate(ln):
            if ch == '"' and j not in keep:
                out.append('「' if open_q else '」'); open_q = not open_q; n += 1
            else:
                out.append(ch)
        lines[i] = "".join(out); n_total += n
    return lines, n_total


def main():
    path = sys.argv[1]
    dry = "--dry-run" in sys.argv
    raw = open(path, encoding="utf-8").read()

    # 路径 A：解析成功 ⇒ 解析—修改—序列化（安全）
    try:
        d = json.loads(raw)
        n_before = sum(v.count('"') for v in d.values() if isinstance(v, str))
        d2 = fix_nested(d)
        s2 = json.dumps(d2, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
        n_after = sum(v.count('"') for v in d2.values() if isinstance(v, str))
        print(f"路径 A（解析—修改—序列化）：值里 ASCII 引号 {n_before} ⇒ {n_after}")
        if not dry:
            open(path, "w", encoding="utf-8").write(s2)
            print("已写回（结构位由 json.dumps 产生，不经过我数）")
        log_fix(path, "A", n_before, True)
        return 0
    except Exception as e:
        print(f"解析失败（{str(e)[:70]}）⇒ 走降级路径 B")

    # 路径 B：解析失败 ⇒ 文本级修正（有风险，明确标注）
    lines = raw.split("\n")
    lines, n = text_level_fallback(lines)
    s = "\n".join(lines)
    try:
        json.loads(s)
    except Exception as e:
        print(f"降级修正后仍不合法：{str(e)[:90]}")
        log_fix(path, "B", n, False)
        return 1
    print(f"路径 B（文本级降级）：修 {n} 处 —— ★ 这条路有风险，建议事后重写该文件")
    if not dry:
        open(path, "w", encoding="utf-8").write(s)
        print("已写回")
    log_fix(path, "B", n, True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
