#!/usr/bin/env python3
"""
UPAS API Server - 为GitHub Pages提供数据接口
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace')

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# 配置
UPAS_DIR = '/root/.openclaw/workspace/upas'
DATA_DIR = os.path.join(UPAS_DIR, 'data')

class CORSRequestHandler(BaseHTTPRequestHandler):
    """支持CORS的请求处理器"""
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{self.log_date_time_string()}] {args[0]}")
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/patterns':
            self.handle_get_patterns()
        elif path == '/api/expectancy':
            self.handle_get_expectancy()
        elif path == '/api/status':
            self.handle_get_status()
        elif path == '/':
            self.handle_index()
        else:
            self.send_error(404, 'Not Found')
    
    def handle_get_patterns(self):
        """获取形态库"""
        try:
            pattern_file = os.path.join(DATA_DIR, 'demo_patterns.json')
            
            if os.path.exists(pattern_file):
                with open(pattern_file, 'r') as f:
                    patterns = json.load(f)
            else:
                patterns = {}
            
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'patterns': patterns
            }).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_get_expectancy(self):
        """获取期望值数据库"""
        try:
            expectancy_file = os.path.join(DATA_DIR, 'demo_saved_state/expectancy_db.json')
            
            if os.path.exists(expectancy_file):
                with open(expectancy_file, 'r') as f:
                    expectancy = json.load(f)
            else:
                expectancy = {}
            
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'expectancy': expectancy
            }).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_get_status(self):
        """获取系统状态"""
        try:
            pattern_file = os.path.join(DATA_DIR, 'demo_patterns.json')
            expectancy_file = os.path.join(DATA_DIR, 'demo_saved_state/expectancy_db.json')
            
            patterns = {}
            expectancy = {}
            
            if os.path.exists(pattern_file):
                with open(pattern_file, 'r') as f:
                    patterns = json.load(f)
            
            if os.path.exists(expectancy_file):
                with open(expectancy_file, 'r') as f:
                    expectancy = json.load(f)
            
            # 计算统计信息
            best_pattern = None
            best_expectancy = 0
            
            for pid, exp in expectancy.items():
                if exp.get('expectancy', 0) > best_expectancy:
                    best_expectancy = exp.get('expectancy', 0)
                    best_pattern = pid
            
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success',
                'data': {
                    'pattern_count': len(patterns),
                    'expectancy_count': len(expectancy),
                    'best_pattern': best_pattern,
                    'best_expectancy': best_expectancy
                }
            }).encode())
            
        except Exception as e:
            self.send_error(500, str(e))
    
    def handle_index(self):
        """API首页"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>UPAS API Server</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { color: #2ecc71; font-weight: bold; }
                code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🚀 UPAS API Server</h1>
            <p>通用抽象形态系统 - 数据接口</p>
            
            <h2>可用接口</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/patterns</code>
                <p>获取形态库数据</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/expectancy</code>
                <p>获取期望值数据库</p>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <code>/api/status</code>
                <p>获取系统状态</p>
            </div>
            
            <hr>
            <p><small>UPAS v1.0 | GitHub: https://github.com/your-username/upas</small></p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())


def run_server(port=8080):
    """运行API服务器"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    
    print("=" * 60)
    print(f"UPAS API Server 已启动")
    print("=" * 60)
    print(f"访问地址: http://0.0.0.0:{port}/")
    print(f"API文档: http://0.0.0.0:{port}/")
    print("")
    print("可用接口:")
    print(f"  GET http://你的IP:{port}/api/patterns")
    print(f"  GET http://你的IP:{port}/api/expectancy")
    print(f"  GET http://你的IP:{port}/api/status")
    print("=" * 60)
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='UPAS API Server')
    parser.add_argument('--port', '-p', type=int, default=8080, help='服务器端口 (默认: 8080)')
    
    args = parser.parse_args()
    run_server(args.port)