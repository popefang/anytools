#!/usr/bin/env python3
"""
简单的HTTP文件服务器
支持指定根目录，用于文件下载或直接访问
"""

import os
import sys
import argparse
import socket
import mimetypes
import chardet  # 需要先安装: pip install chardet
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote, quote, parse_qs
import json

# 添加UTF-8编码支持
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('text/plain', '.txt')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('application/xml', '.xml')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/markdown', '.md')

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """自定义HTTP请求处理器，支持目录访问和文件服务"""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """重写路径转换方法，支持自定义根目录"""
        # 解析查询参数
        if '?' in path:
            path, query = path.split('?', 1)
        else:
            query = ''
        
        # 解码URL编码的路径（使用UTF-8）
        try:
            path = unquote(path, encoding='utf-8', errors='replace')
        except:
            path = unquote(path)
        
        # 如果是根路径，返回目录列表
        if path == '/':
            return self.directory if self.directory else os.getcwd()
        
        # 处理上级目录访问
        if '..' in path:
            self.send_error(403, "访问上级目录被禁止")
            return None
        
        # 构建完整路径
        if self.directory:
            full_path = os.path.join(self.directory, path.lstrip('/'))
        else:
            full_path = os.path.join(os.getcwd(), path.lstrip('/'))
        
        # 规范化路径
        full_path = os.path.normpath(full_path)
        
        # 检查路径是否在指定目录内
        if self.directory and not full_path.startswith(os.path.abspath(self.directory)):
            self.send_error(403, "访问根目录外的文件被禁止")
            return None
        
        return full_path
    
    def do_GET(self):
        """处理GET请求"""
        # 获取请求路径
        path = self.translate_path(self.path)
        
        # 如果路径无效，直接返回
        if path is None:
            return
        
        # 检查路径是否存在
        if not os.path.exists(path):
            self.send_error(404, "文件未找到")
            return
        
        # 如果是目录，显示目录列表
        if os.path.isdir(path):
            self.send_directory_listing(path)
            return
        
        # 如果是文件，根据类型处理
        self.send_file(path)
    
    def send_directory_listing(self, path):
        """发送目录列表页面"""
        try:
            # 获取目录内容
            files = os.listdir(path)
            files.sort()
            
            # 生成HTML页面
            html = self.generate_directory_html(path, files)
            
            # 发送响应
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            
        except PermissionError:
            self.send_error(403, "权限被拒绝")
        except Exception as e:
            self.send_error(500, f"内部服务器错误: {str(e)}")
    
    def generate_directory_html(self, path, files):
        """生成目录列表HTML"""
        # 相对路径
        if self.directory:
            rel_path = os.path.relpath(path, self.directory)
            if rel_path == '.':
                rel_path = ''
        else:
            rel_path = self.path
        
        # 尝试获取IP地址
        try:
            # 获取本机IP地址
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "127.0.0.1"
        
        # 构建HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文件服务器 - {self.html_escape(os.path.basename(path) if os.path.basename(path) else '根目录')}</title>
    <style>
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4a6bff;
            padding-bottom: 10px;
        }}
        .path-info {{
            background-color: #f0f4ff;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            color: #555;
        }}
        .file-list {{
            list-style: none;
            padding: 0;
        }}
        .file-item {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
        }}
        .file-item:hover {{
            background-color: #f9f9f9;
        }}
        .file-icon {{
            margin-right: 10px;
            width: 24px;
            text-align: center;
        }}
        .file-name {{
            flex: 1;
        }}
        .file-size {{
            color: #777;
            font-size: 0.9em;
        }}
        .dir-up {{
            background-color: #e6eeff;
        }}
        .dir-up:hover {{
            background-color: #d0d9ff;
        }}
        a {{
            color: #4a6bff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .server-info {{
            color: #666;
            font-size: 0.9em;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #888;
            font-size: 0.8em;
        }}
        .action-buttons {{
            margin-left: 10px;
        }}
        .action-btn {{
            background-color: #4a6bff;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 0.8em;
            cursor: pointer;
            margin-left: 5px;
        }}
        .action-btn:hover {{
            background-color: #3a56d6;
        }}
        .encoding-info {{
            background-color: #fff8e1;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
            font-size: 0.9em;
            color: #666;
        }}
        .encoding-badge {{
            display: inline-block;
            background-color: #e8f4fd;
            color: #2196f3;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 文件服务器</h1>
            <div class="server-info">
                当前目录: {self.html_escape(path)}<br>
                IP: {local_ip}
            </div>
        </div>
        
        <div class="path-info">
            📍 路径: /{self.html_escape(rel_path if rel_path else '')}
        </div>
        
        <ul class="file-list">
            <!-- 上级目录链接 -->
            {self.generate_parent_link(path)}
"""
        
        # 添加文件列表
        for file in files:
            file_path = os.path.join(path, file)
            is_dir = os.path.isdir(file_path)
            file_size = ""
            encoding_info = ""
            
            if not is_dir:
                try:
                    size = os.path.getsize(file_path)
                    file_size = self.format_size(size)
                    
                    # 检测文件编码
                    encoding = self.detect_file_encoding(file_path)
                    if encoding and encoding.lower() != 'utf-8':
                        encoding_info = f'<span class="encoding-badge">{encoding}</span>'
                except:
                    file_size = "未知"
                    
            file_icon = "📁" if is_dir else "📄"
            
            # 相对URL路径
            if rel_path:
                file_url = f"/{rel_path}/{file}" if rel_path else f"/{file}"
            else:
                file_url = f"/{file}"
            
            # 清理URL中的双斜杠
            file_url = file_url.replace('//', '/')
            # 对URL进行UTF-8编码
            encoded_file_url = quote(file_url.encode('utf-8'))
            
            html += f"""            <li class="file-item">
                <div class="file-icon">{file_icon}</div>
                <div class="file-name">
                    <a href="{encoded_file_url}">{self.html_escape(file)}</a>{encoding_info}
                    <span class="action-buttons">
                        <button class="action-btn" onclick="viewFile('{encoded_file_url}')">查看</button>
                        <button class="action-btn" onclick="downloadFile('{encoded_file_url}')">下载</button>
                    </span>
                </div>
                <div class="file-size">{file_size}</div>
            </li>
"""
        
        html += """        </ul>
        
        <div class="encoding-info">
            ℹ️ 编码提示：服务器会自动检测文件编码并转换为UTF-8显示。如果中文显示乱码，请在浏览器中检查编码设置是否正确。
        </div>
        
        <div class="footer">
            简单HTTP文件服务器 | 按 Ctrl+C 停止
        </div>
    </div>
    
    <script>
        function viewFile(url) {
            window.open(url, '_blank');
        }
        
        function downloadFile(url) {
            // 添加download参数强制下载
            const downloadUrl = url + (url.includes('?') ? '&' : '?') + 'download=true';
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = '';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    </script>
</body>
</html>"""
        
        return html
    
    def detect_file_encoding(self, file_path, sample_size=1024):
        """检测文件编码"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(sample_size)
            
            if not raw_data:
                return None
            
            # 使用chardet检测编码
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            
            # 如果置信度太低，返回None
            if confidence < 0.5:
                return None
            
            return encoding
        except:
            return None
    
    def convert_to_utf8(self, content_bytes, detected_encoding):
        """将内容转换为UTF-8编码"""
        if detected_encoding and detected_encoding.lower() != 'utf-8':
            try:
                # 尝试用检测到的编码解码，然后编码为UTF-8
                decoded = content_bytes.decode(detected_encoding, errors='replace')
                return decoded.encode('utf-8')
            except:
                # 如果转换失败，返回原始内容
                pass
        
        # 如果已经是UTF-8或者检测失败，直接返回
        return content_bytes
    
    def generate_parent_link(self, current_path):
        """生成上级目录链接"""
        if self.directory and os.path.abspath(current_path) == os.path.abspath(self.directory):
            return ""  # 已经在根目录，不显示上级目录链接
        
        parent_path = os.path.dirname(current_path)
        
        # 计算相对路径
        if self.directory:
            rel_parent = os.path.relpath(parent_path, self.directory)
            if rel_parent == '.':
                parent_url = '/'
            else:
                parent_url = f'/{rel_parent}'
        else:
            parent_url = os.path.dirname(self.path)
            if parent_url == '/':
                parent_url = '/'
            else:
                parent_url = parent_url.rstrip('/')
        
        # 对URL进行UTF-8编码
        encoded_parent_url = quote(parent_url.encode('utf-8'))
        
        return f"""            <li class="file-item dir-up">
                <div class="file-icon">⬆️</div>
                <div class="file-name">
                    <a href="{encoded_parent_url}">返回上级目录</a>
                </div>
            </li>"""
    
    def send_file(self, file_path):
        """发送文件"""
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 获取文件名
            filename = os.path.basename(file_path)
            
            # 获取MIME类型
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # 检查是否是文本文件
            is_text_file = content_type.startswith(('text/', 'application/json', 'application/xml', 'application/javascript'))
            
            # 检查URL中是否有download参数
            query_string = self.path.split('?')[1] if '?' in self.path else ''
            download_requested = 'download=true' in query_string
            
            # 设置响应头
            self.send_response(200)
            
            # 对于非文本文件或要求下载的情况，设置为附件
            if not is_text_file or download_requested:
                # 处理中文文件名下载问题
                # 使用现代浏览器支持的UTF-8文件名编码
                try:
                    # 移除不安全的字符
                    import re
                    safe_filename = re.sub(r'[^\w\-_.()\u4e00-\u9fff]', '_', filename)
                    
                    # 同时提供两种格式的文件名，让浏览器选择
                    encoded_filename = quote(safe_filename.encode('utf-8'), safe='')
                    self.send_header("Content-Disposition", 
                                   f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{encoded_filename}")
                except:
                    # 如果失败，使用ASCII
                    ascii_filename = filename.encode('ascii', 'ignore').decode('ascii')
                    self.send_header("Content-Disposition", f'attachment; filename="{ascii_filename}"')
            else:
                # 对于查看请求，添加正确的字符集
                if is_text_file:
                    content_type = f"{content_type}; charset=utf-8"
            
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Access-Control-Allow-Origin", "*")  # 允许跨域访问
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.end_headers()
            
            # 发送文件内容
            if is_text_file and not download_requested:
                # 对于查看文本文件，读取并确保UTF-8编码
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # 检测文件编码并转换为UTF-8
                detected_encoding = self.detect_file_encoding(file_path)
                utf8_content = self.convert_to_utf8(file_content, detected_encoding)
                
                self.wfile.write(utf8_content)
            else:
                # 对于下载请求或二进制文件，直接发送原始内容
                with open(file_path, 'rb') as f:
                    # 分块发送，避免内存占用过大
                    chunk_size = 8192
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                    
        except PermissionError:
            self.send_error(403, "权限被拒绝")
        except Exception as e:
            self.send_error(500, f"内部服务器错误: {str(e)}")
    
    def do_OPTIONS(self):
        """处理OPTIONS请求，支持CORS"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
    
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def html_escape(self, text):
        """HTML转义，防止XSS攻击"""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#39;'))
    
    def log_message(self, format, *args):
        """自定义日志输出"""
        client_ip = self.client_address[0]
        # 确保日志输出使用正确的编码
        try:
            message = format % args
            print(f"[{self.log_date_time_string()}] {client_ip} - {message}")
        except:
            # 如果编码有问题，使用安全的输出
            print(f"[{self.log_date_time_string()}] {client_ip} - Request logged")
    
    def send_error(self, code, message=None):
        """重写send_error方法，使用UTF-8编码"""
        if message is None:
            message = ""
        
        # 确保消息使用UTF-8编码
        try:
            message = message.encode('utf-8', 'replace').decode('utf-8')
        except:
            message = "错误"
        
        self.send_response(code)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header('Connection', 'close')
        self.end_headers()
        
        error_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>错误 {code}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 20px; }}
        .error {{ color: #d32f2f; }}
    </style>
</head>
<body>
    <h1>错误 {code}</h1>
    <p class="error">{message}</p>
    <p><a href="/">返回首页</a></p>
</body>
</html>"""
        
        try:
            self.wfile.write(error_html.encode('utf-8'))
        except:
            pass

def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个临时socket来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="简单的HTTP文件服务器")
    parser.add_argument("-p", "--port", type=int, default=9000, help="服务器端口号 (默认: 9000)")
    parser.add_argument("-d", "--directory", type=str, default=".", help="服务器根目录 (默认: 当前目录)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定主机地址 (默认: 0.0.0.0)")
    
    args = parser.parse_args()
    
    # 获取绝对路径
    root_dir = os.path.abspath(args.directory)
    
    # 检查目录是否存在
    if not os.path.exists(root_dir):
        print(f"错误: 目录 '{root_dir}' 不存在")
        return 1
    
    if not os.path.isdir(root_dir):
        print(f"错误: '{root_dir}' 不是目录")
        return 1
    
    # 创建服务器
    try:
        # 创建自定义Handler类，传入目录参数
        handler_class = lambda *args, **kwargs: CustomHTTPRequestHandler(
            *args, directory=root_dir, **kwargs
        )
        
        server = HTTPServer((args.host, args.port), handler_class)
        
        # 获取本机IP
        local_ip = get_local_ip()
        
        print("=" * 60)
        print("🎯 简单HTTP文件服务器已启动 (UTF-8增强版)")
        print("=" * 60)
        print(f"📁 根目录: {root_dir}")
        print(f"🌐 服务器地址:")
        print(f"   本地访问: http://localhost:{args.port}")
        print(f"   网络访问: http://{local_ip}:{args.port}")
        print(f"🔧 参数设置:")
        print(f"   主机: {args.host}")
        print(f"   端口: {args.port}")
        print("📄 文件处理:")
        print(f"   - 自动检测文件编码并转换为UTF-8")
        print(f"   - 支持中文文件名")
        print(f"   - 支持跨域访问(CORS)")
        print("=" * 60)
        print("📝 安装chardet库以获得更好的编码检测:")
        print("   pip install chardet")
        print("=" * 60)
        print("🛑 按 Ctrl+C 停止服务器")
        print("=" * 60)
        
        # 启动服务器
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
        return 0
    except PermissionError:
        print(f"错误: 没有权限在端口 {args.port} 上启动服务器")
        return 1
    except OSError as e:
        if e.errno == 98:
            print(f"错误: 端口 {args.port} 已被占用")
        else:
            print(f"错误: {e}")
        return 1
    except Exception as e:
        print(f"错误: {e}")
        return 1

if __name__ == "__main__":
    # 设置标准输出编码为UTF-8
    if sys.stdout.encoding != 'UTF-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python 3.6及以下版本
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    sys.exit(main())