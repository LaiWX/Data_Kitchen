from flask import Flask, jsonify, send_file, request, url_for, render_template_string
from functools import wraps
import os
from datetime import datetime
import base64

app = Flask(__name__)

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>File List</title>
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        .link a { text-decoration: none; color: #0366d6; }
        .size { color: #666; }
        .date { color: #666; }
    </style>
</head>
<body>
    <table id="list">
        <thead>
            <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Last Modified</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td class="link">
                    <a href="{{ item.url }}" title="{{ item.name }}">{{ item.name }}{% if item.is_directory %}/{% endif %}</a>
                </td>
                <td class="size">{{ item.size }}</td>
                <td class="date">{{ item.modified_date.strftime('%Y-%b-%d %H:%M') }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
'''

# 测试用户凭据
VALID_CREDENTIALS = {
    'test': 'password'
}


def check_auth(username, password):
    """验证用户名和密码"""
    return username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password


def authenticate():
    """返回401未授权响应"""
    return ('未授权访问', 401, {
        'WWW-Authenticate': 'Basic realm="Login Required"'
    })


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


def format_size(size_in_bytes):
    """格式化文件大小"""
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes/1024:.1f} KB"
    else:
        return f"{size_in_bytes/(1024*1024):.1f} MB"


def get_file_info(base_path, current_path, name):
    """获取文件信息"""
    full_path = os.path.join(current_path, name)
    stats = os.stat(full_path)
    is_dir = os.path.isdir(full_path)
    
    # 计算相对路径
    rel_path = os.path.relpath(full_path, base_path)
    
    # 构建URL时，确保使用当前请求的URL作为基础
    if is_dir:
        url = f'{request.url_root}list/{rel_path}/'
    else:
        url = f'{request.url_root}files/{rel_path}'
    
    return {
        'name': name,
        'size': "-" if is_dir else format_size(stats.st_size),
        'modified_date': datetime.fromtimestamp(stats.st_mtime),
        'url': url,
        'is_directory': is_dir
    }


@app.route('/list/')
@app.route('/list/<path:subpath>')
@requires_auth
def list_files(subpath=''):
    """列出目录内容"""
    base_path = 'test_files'  # 基础文件目录
    current_path = os.path.join(base_path, subpath) if subpath else base_path
    
    # 安全检查：确保路径在基础目录内
    if not os.path.abspath(current_path).startswith(os.path.abspath(base_path)):
        return 'Invalid path', 403
    
    try:
        # 获取目录内容
        items = []
        
        # 如果不是根目录，添加返回上级目录的项
        if subpath:
            items.append({
                'name': '..',
                'size': '-',
                'modified_date': datetime.now(),
                'url': '../',  # 使用相对路径
                'is_directory': True
            })
        
        # 获取当前目录内容
        for name in sorted(os.listdir(current_path)):
            # 跳过隐藏文件
            if name.startswith('.'):
                continue
            items.append(get_file_info(base_path, current_path, name))
        
        # 返回HTML页面
        return render_template_string(HTML_TEMPLATE, items=items)
    except Exception as e:
        return str(e), 500


@app.route('/files/<path:filepath>')
@requires_auth
def download_file(filepath):
    """下载文件"""
    try:
        file_path = os.path.join('test_files', filepath)
        # 安全检查：确保文件在允许的目录内
        if not os.path.abspath(file_path).startswith(os.path.abspath('test_files')):
            return '无效的文件路径', 403
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return str(e), 404


if __name__ == '__main__':
    # 创建测试文件目录
    os.makedirs('test_files', exist_ok=True)
    
    # 创建一些测试文件和目录
    test_structure = {
        'documents': {
            'test.txt': 'This is a test file\nWith multiple lines\nAnd some content',
            'hello.md': '# Hello World\nThis is a markdown file\n## Section 1\nSome content here\n## Section 2\nMore content',
            'large.txt': 'x' * 1024 * 1024  # 1MB file
        },
        'images': {
            'small.jpg': b'\xFF\xD8\xFF\xE0' + b'\x00' * 1024,  # 1KB fake JPEG
            'medium.png': b'\x89PNG\r\n' + b'\x00' * (1024 * 50),  # 50KB fake PNG
        },
        'nested': {
            'subfolder1': {
                'file1.txt': 'Content of file 1',
                'file2.txt': 'Content of file 2'
            },
            'subfolder2': {
                'file3.txt': 'Content of file 3'
            }
        }
    }
    
    def create_test_files(structure, base_path):
        for name, content in structure.items():
            path = os.path.join(base_path, name)
            if isinstance(content, dict):
                os.makedirs(path, exist_ok=True)
                create_test_files(content, path)
            else:
                mode = 'wb' if isinstance(content, bytes) else 'w'
                with open(path, mode) as f:
                    f.write(content)
    
    create_test_files(test_structure, 'test_files')
    
    app.run(debug=True, port=5000)
