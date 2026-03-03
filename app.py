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
        original_filename = secure_filename(file.filename)
        # 添加时间戳避免文件名冲突
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(original_filename)
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


@app.route('/api/preview-sheet', methods=['POST'])
def preview_sheet_endpoint():
    """
    预览选定工作表的详细数据
    """
    data = request.get_json()

    if not data or 'filepath' not in data or 'sheet_name' not in data:
        return jsonify({'error': '缺少必要参数'}), 400

    filepath = data['filepath']
    sheet_name = data['sheet_name']

    try:
        # 获取工作表预览数据
        preview_data = preview_sheet(filepath, sheet_name, nrows=10)

        # 智能推荐列映射
        suggested_columns = suggest_columns(preview_data)

        return jsonify({
            'success': True,
            'preview': preview_data,
            'suggested_columns': suggested_columns
        })

    except Exception as e:
        return jsonify({
            'error': f'预览工作表失败: {str(e)}'
        }), 500


def suggest_columns(preview_data):
    """
    根据预览数据智能推荐列映射

    Parameters
    ----------
    preview_data : Dict
        预览数据

    Returns
    -------
    Dict
        推荐的列映射
    """
    columns = preview_data.get('columns', [])
    preview_rows = preview_data.get('preview_data', [])
    suggested = {
        'spot': None,
        'future': None,
        'date': None
    }

    # 列名转小写便于匹配
    columns_lower = [col.lower() for col in columns]

    # 推荐日期列
    date_columns = preview_data.get('date_columns', [])
    if date_columns:
        suggested['date'] = date_columns[0]

    # 推荐现货价格列
    spot_keywords = ['现货', 'spot', ' spot ', '现货价格', '市场价', '华东']
    for idx, col_lower in enumerate(columns_lower):
        if any(keyword in col_lower for keyword in spot_keywords):
            suggested['spot'] = columns[idx]
            break

    # 推荐期货价格列
    future_keywords = ['期货', 'future', ' future ', '期货价格', '收盘', 'close', '主力合约', '期货价格指数']
    for idx, col_lower in enumerate(columns_lower):
        if any(keyword in col_lower for keyword in future_keywords):
            suggested['future'] = columns[idx]
            break

    # 如果没有找到，检查预览数据中的内容来推断
    if not suggested['spot'] or not suggested['future'] and preview_rows:
        # 跳过前几行元数据，找到实际数据行
        data_start_idx = 0
        for idx, row in enumerate(preview_rows):
            # 检查是否包含数值数据
            for col in columns:
                val = row.get(col)
                if isinstance(val, (int, float)) and val > 0:
                    data_start_idx = idx
                    break
            if data_start_idx > 0:
                break

        # 如果找到了数据行，分析列内容
        if data_start_idx < len(preview_rows):
            data_row = preview_rows[data_start_idx]

            # 为每列打分
            column_scores = {}
            column_values = {}
            for col in columns:
                score = 0
                val = data_row.get(col)
                column_values[col] = val

                # 数值加分
                if isinstance(val, (int, float)):
                    score += 10

                # 检查列名
                col_lower = col.lower()
                if 'unnamed' in col_lower:
                    # Unnamed列可能是数据列
                    score += 5
                elif any(kw in col_lower for kw in ['价格', 'price', '收盘', 'close']):
                    score += 20

                column_scores[col] = score

            # 选择得分最高的两列作为现货和期货
            sorted_columns = sorted(column_scores.items(), key=lambda x: x[1], reverse=True)

            if len(sorted_columns) >= 2:
                # 获取两列的值来判断哪个是期货（期货通常价格更高）
                col1, col2 = sorted_columns[0][0], sorted_columns[1][0]
                val1 = column_values.get(col1)
                val2 = column_values.get(col2)

                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    # 期货价格通常高于现货
                    if val1 > val2:
                        suggested['future'] = col1
                        suggested['spot'] = col2
                    else:
                        suggested['future'] = col2
                        suggested['spot'] = col1
                else:
                    # 如果无法判断，按顺序分配
                    suggested['future'] = col1
                    suggested['spot'] = col2
            elif len(sorted_columns) >= 1 and not suggested['spot']:
                suggested['spot'] = sorted_columns[0][0]

    return suggested


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
