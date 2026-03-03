#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GARCH模型套保分析Web平台
"""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import (
    SECRET_KEY, DEBUG, HOST, PORT,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS,
    OUTPUT_DIR, MODEL_CONFIG
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH
)

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("=" * 60)
    print("GARCH模型套保分析Web平台")
    print("=" * 60)
    print(f"请在浏览器中访问: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)
