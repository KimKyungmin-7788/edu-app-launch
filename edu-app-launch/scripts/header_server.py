#!/usr/bin/env python3
"""vercel.json 의 headers·cleanUrls 를 그대로 적용하는 로컬 정적 서버.

배포 전에 보안 헤더(CSP 등)를 켠 상태로 앱 기능을 확인하려고 쓴다.
사용법: python3 header_server.py <앱폴더> [포트=5510]
"""
import http.server
import json
import os
import socketserver
import sys

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5510

cfg_path = os.path.join(root, 'vercel.json')
cfg = json.load(open(cfg_path, encoding='utf-8')) if os.path.exists(cfg_path) else {}
headers = [h for rule in cfg.get('headers', []) for h in rule.get('headers', [])]
clean_urls = cfg.get('cleanUrls', False)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=root, **k)

    def translate_path(self, path):
        p = super().translate_path(path)
        if clean_urls and not os.path.exists(p) and os.path.exists(p + '.html'):
            return p + '.html'
        return p

    def end_headers(self):
        for h in headers:
            self.send_header(h['key'], h['value'])
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


socketserver.TCPServer.allow_reuse_address = True
print(f'serving {root} on http://localhost:{port} with {len(headers)} headers')
with socketserver.TCPServer(('', port), Handler) as srv:
    srv.serve_forever()
