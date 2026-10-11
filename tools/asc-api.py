#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""asc-api.py — App Store Connect API 助手（JWT ES256 裸 r||s 签名，单一来源 kid/issuer）
用法: asc-api.py <GET路径>  例: asc-api.py /v1/apps?limit=5
凭证: ~/.dsh/appstoreconnect/{AuthKey_<kid>.p8, issuer-id.txt}（0600）
"""
import json, time, base64, sys, urllib.request, os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

DIR = os.path.expanduser("~/.dsh/appstoreconnect")
KID = "VA9RR5747M"   # 活跃 key（团队级；旧 LP2687299T 建议控制台吊销）

def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b'=').decode()
def make_jwt():
    key = serialization.load_pem_private_key(
        open(f"{DIR}/AuthKey_{KID}.p8", "rb").read(), password=None)
    iss = open(f"{DIR}/issuer-id.txt").read().strip()
    header = {"alg": "ES256", "kid": KID, "typ": "JWT"}
    payload = {"iss": iss, "iat": int(time.time())-60, "exp": int(time.time())+600, "aud": "appstoreconnect-v1"}
    seg = b64u(json.dumps(header, separators=(',', ':')).encode()) + "." + b64u(json.dumps(payload, separators=(',', ':')).encode())
    r, s = utils.decode_dss_signature(key.sign(seg.encode(), ec.ECDSA(hashes.SHA256())))
    return seg + "." + b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))

def main():
    args = sys.argv[1:]
    method = "GET"
    if args and args[0] in ("GET", "POST", "PATCH", "DELETE"):
        method = args.pop(0)
    path = args[0] if args else "/v1/apps?limit=5"
    body = args[1].encode() if len(args) > 1 else None
    req = urllib.request.Request("https://api.appstoreconnect.apple.com" + path,
                                 data=body, method=method,
                                 headers={"Authorization": "Bearer " + make_jwt(),
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(r.status)
            raw = r.read()
            if raw:
                print(json.dumps(json.loads(raw), ensure_ascii=False, indent=1)[:2000])
    except urllib.error.HTTPError as e:
        print(e.code); print(e.read()[:300])

if __name__ == "__main__":
    main()
