#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GARCH模型套保分析Web平台
"""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime

from config import (
    SECRET_KEY, DEBUG, HOST, PORT,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS,
    OUTPUT_DIR, MODEL_CONFIG
)
from utils.data_processor import read_excel_sheets, preview_sheet, get_all_sheets_info

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


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    处理文件上传
    """
    # 检查是否有文件
    if 'file' not in request.files:
        return jsonify({'error': '没有文件上传'}), 400

    file = request.files['file']

    # 检查文件名
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    # 检查文件类型
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式，请上传Excel文件 (.xlsx, .xls)'}), 400

    try:
        # 保存文件
        filename = secure_filename(file.filename)
        # 添加时间戳避免文件名冲突
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        filepath = UPLOAD_FOLDER / filename

        file.save(filepath)

        # 读取所有工作表信息
        sheets_info = get_all_sheets_info(str(filepath))

        # 推荐最佳工作表
        recommended_sheet = recommend_sheet(sheets_info)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': str(filepath),
            'sheets': sheets_info,
            'recommended_sheet': recommended_sheet,
            'message': f'成功上传文件，共找到 {len(sheets_info)} 个工作表'
        })

    except Exception as e:
        return jsonify({
            'error': f'文件处理失败: {str(e)}'
        }), 500


def recommend_sheet(sheets_info):
    """
    根据工作表信息智能推荐最佳工作表

    Parameters
    ----------
    sheets_info : List[Dict]
        工作表信息列表

    Returns
    -------
    str or None
        推荐的工作表名称
    """
    if not sheets_info:
        return None

    # 评分系统
    scored_sheets = []

    for sheet in sheets_info:
        if 'error' in sheet or not sheet.get('has_data'):
            continue

        score = 0
        name = sheet['name'].lower()
        columns = [col.lower() for col in sheet.get('columns', [])]

        # 1. 检查工作表名称（优先级最高）
        if any(keyword in name for keyword in ['数据', 'data', '价格', 'price', '期货', '现货', 'future', 'spot']):
            score += 50

        # 2. 检查列名（包含价格、日期、期货、现货等关键词）
        price_keywords = ['价格', 'price', '收盘', 'close', '期货', 'future', '现货', 'spot']
        date_keywords = ['日期', 'date', '时间', 'time']

        for col in columns:
            if any(keyword in col for keyword in price_keywords):
                score += 15
            if any(keyword in col for keyword in date_keywords):
                score += 10

        # 3. 检查是否有日期范围
        if sheet.get('date_range'):
            score += 20

        # 4. 检查数据量（数据量适中加分）
        row_count = sheet.get('row_count', 0)
        if 100 <= row_count <= 10000:
            score += 10

        scored_sheets.append({
            'name': sheet['name'],
            'score': score
        })

    # 返回得分最高的工作表
    if scored_sheets:
        scored_sheets.sort(key=lambda x: x['score'], reverse=True)
        return scored_sheets[0]['name']

    # 如果没有合适的工作表，返回第一个有效的
    for sheet in sheets_info:
        if sheet.get('has_data'):
            return sheet['name']

    return None


if __name__ == '__main__':
    print("=" * 60)
    print("GARCH模型套保分析Web平台")
    print("=" * 60)
    print(f"请在浏览器中访问: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)
