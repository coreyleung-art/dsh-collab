#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""genebank-server.py v1.0 — GeneBank 基因库注册层服务（AI 网盘）

AI 网盘（基因库）的注册层：基因（资产）注册/查询/列表 + manifest 校验 + 操作日志。
混合命名（隐喻精神+工程命名）：gene_id（内容寻址）/ chromosome（染色体分类）/ expression（表达谱）/ heredity（遗传）。

用法:
  python3 genebank-server.py --port 8801          # 启动服务
  python3 genebank-server.py --list --chromosome datasets   # 列表（CLI）
  python3 genebank-server.py --register manifest.json        # 注册（CLI）

存储:
  ~/.genebank/registry.jsonl   # 注册日志（append-only，每行一次注册）
  ~/.genebank/genes/<id>.json  # 基因 manifest 文件
  ~/.genebank/genebank.log     # 操作日志

黑板同步: 注册/变更时写黑板 notes/genebank/<gene_id>（通知总线）

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
    print("== genebank-server 自查（TCC 能力边界）==")

    print("【① 能力清单】")
    print("  · genebank-server.py v1.0 — GeneBank 基因库注册层服务（AI 网盘）")
    print("  · AI 网盘（基因库）的注册层：基因（资产）注册/查询/列表 + manifest 校验 + 操作日志。")
    print("  · 混合命名（隐喻精神+工程命名）：gene_id（内容寻址）/ chromosome（染色体分类）/ expression（表达谱）/ heredity（遗传）。")
    print("  · python3 genebank-server.py --port 8801          # 启动服务")
    print("  · 命令/参数: port, list, chromosome, register")

    print("【② 不该发生路径清单】")
    print("  · 本工具【不执行外部命令、不删除数据、不修改权限】⇒ 无该路径")
    print("  · 不修改 r006 管辖外的其它工具文件（只读审计类行为）")

    print("【③ 依赖完整性】")
    print("  · Python %s" % _sys.version.split()[0])
    print("  · 标准库: argparse, http, time, urllib")
    print("  · ✅ 无第三方依赖（仅标准库）")
    print("  · 固定日志: ~/dsh-collab/logs/genebank-server.log")
    return 0

__version__ = '1.0.0'  # ★ R006 ⑥ 唯一版本声明处（补课生成）

import argparse, json, os, re, sys, hashlib, datetime, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# ★ R006 ⑦ 统一日志：固定路径，失败也留痕（r006-retrofit-apply 自足插入）
LOG = os.path.expanduser("~/dsh-collab/logs/genebank-server.log")


def log(msg):
    """★ R006 ⑦：固定路径日志；失败也留痕。"""
    import time as _t
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_t.strftime("%Y-%m-%dT%H:%M:%S"), msg))
    except Exception:
        pass

GB_DIR = os.path.expanduser("~/.genebank")
REGISTRY = os.path.join(GB_DIR, "registry.jsonl")
LOG_FILE = os.path.join(GB_DIR, "genebank.log")
BLACKBOARD = "http://127.0.0.1:8792"
CHROMOSOMES = ["models", "datasets", "corpora", "knowledge", "artifacts", "recipes"]

def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def log(entry):
    os.makedirs(GB_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _now(), **entry}, ensure_ascii=False) + "\n")

def validate_manifest(m):
    """校验 manifest（复用 genebank-manifest.schema.json 的必填 + 枚举）"""
    errors = []
    if not isinstance(m, dict):
        return ["manifest 必须是对象"]
    required = ["gene_id", "name", "chromosome", "body", "expression", "heredity"]
    for k in required:
        if k not in m:
            errors.append("缺必填字段: %s" % k)
    if "gene_id" in m and not re.match(r"^sha256:[a-f0-9]{64}$", m["gene_id"]):
        errors.append("gene_id 格式应为 sha256:<64位hex>")
    if "chromosome" in m and m["chromosome"] not in CHROMOSOMES:
        errors.append("chromosome 不在标准染色体 %s（自进化扩展需先声明）" % CHROMOSOMES)
    if "body" in m and not isinstance(m["body"], dict):
        errors.append("body 必须是对象")
    if "heredity" in m and not isinstance(m["heredity"], dict):
        errors.append("heredity 必须是对象")
    if "mutation" in m.get("heredity", {}) and not re.match(r"^\d+\.\d+\.\d+$", m["heredity"]["mutation"]):
        errors.append("heredity.mutation 应为语义版本 1.0.0")
    return errors

def compute_gene_id(path, content=None):
    """内容寻址：由文件内容或字符串计算 gene_id"""
    if content is not None:
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    elif path and os.path.exists(path):
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
    else:
        h = hashlib.sha256(("empty-" + _now()).encode()).hexdigest()
    return "sha256:" + h

def _bb_put(path, data):
    import http.client
    u = urllib.parse.urlparse(BLACKBOARD)
    body = json.dumps(data, ensure_ascii=False).encode()
    conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=8)
    conn.request("PUT", path, body=body, headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
    resp = conn.getresponse()
    raw = resp.read().decode("utf-8", "ignore")
    conn.close()
    return raw

def register_gene(manifest, sync_blackboard=True):
    """注册基因：校验 → 存 manifest → 记日志 → 黑板同步"""
    errors = validate_manifest(manifest)
    if errors:
        return {"ok": False, "errors": errors}
    os.makedirs(GB_DIR, exist_ok=True)
    gene_id = manifest["gene_id"]
    gpath = os.path.join(GB_DIR, "genes", gene_id.replace(":", "_") + ".json")
    os.makedirs(os.path.dirname(gpath), exist_ok=True)
    with open(gpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    entry = {"op": "register", "gene_id": gene_id, "name": manifest.get("name"),
             "chromosome": manifest.get("chromosome"), "mutation": manifest.get("heredity", {}).get("mutation"),
             "size": manifest.get("body", {}).get("size_bytes")}
    with open(REGISTRY, "a", encoding="utf-8") as f:
        f.write(json.dumps({**entry, "ts": _now()}, ensure_ascii=False) + "\n")
    log(entry)
    if sync_blackboard:
        try:
            _bb_put("/notes/genebank/%s" % gene_id.replace(":", "_")[:40],
                    {"ts": _now(), "type": "gene-register", "gene_id": gene_id,
                     "name": manifest.get("name"), "chromosome": manifest.get("chromosome"),
                     "expression": manifest.get("expression")})
        except Exception:
            pass
    return {"ok": True, "gene_id": gene_id, "path": gpath}

def list_genes(chromosome=None):
    """列表基因（从 registry 读取，可按染色体过滤）"""
    genes = []
    if os.path.exists(REGISTRY):
        for line in open(REGISTRY, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            try:
                e = json.loads(line)
            except Exception: continue
            if chromosome and e.get("chromosome") != chromosome:
                continue
            genes.append(e)
    return genes

def get_gene(gene_id):
    gpath = os.path.join(GB_DIR, "genes", gene_id.replace(":", "_") + ".json")
    if os.path.exists(gpath):
        return json.load(open(gpath, encoding="utf-8"))
    return None

class H(BaseHTTPRequestHandler):
    def _ok(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _err(self, code, msg):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_PUT(self):
        # PUT /api/v1/genes  body=manifest
        # PUT /api/v1/genes/<id>/file  body=<文件字节> → 存储基因文件（AI 网盘）
        path = self.path.rstrip("/")
        if "/file" in path:
            gid = path.split("/")[-2]
            g = get_gene(gid)
            if not g:
                self._err(404, "gene not found")
                return
            n = int(self.headers.get("Content-Length", 0))
            content = self.rfile.read(n) if n else b""
            # 存文件到 genes/<id>.bin（内容寻址）；支持断点续传（X-Offset 分片追加）
            fpath = os.path.join(GB_DIR, "genes", gid.replace(":", "_") + ".bin")
            offset = int(self.headers.get("X-Offset", 0))
            mode = "ab" if offset > 0 else "wb"
            with open(fpath, mode) as f:
                if offset == 0:
                    f.write(content)
                else:
                    # 分片：跳到 offset 写（续传）
                    cur = os.path.getsize(fpath)
                    if cur == offset:
                        f.write(content)
                    else:
                        # offset 不匹配：从文件末尾续（断点=已写长度）
                        f.write(content)
            total = os.path.getsize(fpath)
            self._ok({"ok": True, "gene_id": gid, "file_bytes": len(content),
                      "total_bytes": total, "offset": offset,
                      "file_url": "/api/v1/genes/%s/file" % gid,
                      "resumable": True})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            manifest = json.loads(self.rfile.read(n).decode("utf-8", "ignore")) if n else {}
        except Exception:
            manifest = {}
        r = register_gene(manifest)
        if r.get("ok"):
            self._ok(r)
        else:
            self._err(400, r.get("errors"))
    def do_GET(self):
        path = self.path.rstrip("/")
        if path == "/api/v1/registry":
            # 列表：?chromosome=
            import urllib.parse
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            chrom = qs.get("chromosome", [None])[0]
            self._ok({"count": len(list_genes(chrom)), "genes": list_genes(chrom)})
        elif path.startswith("/api/v1/genes/"):
            parts = path.split("/")
            # GET /api/v1/genes/<id>/file → 下载基因文件（AI 网盘，支持 Range 断点续传）
            if len(parts) >= 5 and parts[-1] == "file":
                gid = parts[-2]
                g = get_gene(gid)
                fpath = os.path.join(GB_DIR, "genes", gid.replace(":", "_") + ".bin")
                if g and os.path.exists(fpath):
                    size = os.path.getsize(fpath)
                    content = open(fpath, "rb").read()
                    # Range 支持（断点续传）
                    rng = self.headers.get("Range")
                    start = 0
                    if rng and rng.startswith("bytes="):
                        try:
                            rng_v = rng.split("=")[1].split("-")[0]
                            start = int(rng_v) if rng_v else 0
                        except ValueError:
                            start = 0
                    if start > 0:
                        content = content[start:]
                        self.send_response(206)
                        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, size-1, size))
                    else:
                        self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(content)))
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Disposition", 'attachment; filename="%s"' % g.get("name", "gene"))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                self._err(404, "gene file not found")
                return
            gid = parts[-1]
            g = get_gene(gid)
            if g:
                self._ok(g)
            else:
                self._err(404, "gene not found")
        else:
            self._err(404, "use /api/v1/registry or /api/v1/genes/<id>")
    def log_message(self, *a):
        pass

def main():
    ap = argparse.ArgumentParser(description="GeneBank 基因库注册层服务")
    ap.add_argument("--port", type=int, default=8801)
    ap.add_argument("--selfcheck", action="store_true", help="R006 02 TCC")
    ap.add_argument("--list", action="store_true", help="CLI 列表")
    ap.add_argument("--chromosome", default=None, help="按染色体过滤")
    ap.add_argument("--register", default=None, help="CLI 注册 manifest JSON 文件")
    if "--selfcheck" in __import__("sys").argv:
        return selfcheck()
    args = ap.parse_args()
    os.makedirs(GB_DIR, exist_ok=True)
    if args.register:
        m = json.load(open(args.register, encoding="utf-8"))
        print(json.dumps(register_gene(m), ensure_ascii=False, indent=1))
        return
    if args.list:
        genes = list_genes(args.chromosome)
        print("基因库 %d 个基因" % len(genes))
        for g in genes:
            print("  [%s] %s %s v%s" % (g.get("chromosome"), g.get("name"), g.get("gene_id", "")[:20], g.get("mutation")))
        return
    import urllib.parse
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), H)
    print("GeneBank 注册层服务 :%d  存储=%s" % (args.port, GB_DIR))
    srv.serve_forever()

if __name__ == "__main__":
    main()
