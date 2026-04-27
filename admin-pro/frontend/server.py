#!/usr/bin/env python3
"""开发服务器 - 自动禁用浏览器缓存"""
import http.server
import socketserver
import os

PORT = 5176

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        # 简化日志
        pass

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    print(f"Server started: http://localhost:{PORT}")
    print("Cache disabled")
    httpd.serve_forever()
