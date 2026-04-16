#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GARCH模型套保分析Web平台
"""

import os
import sys
from pathlib import Path

# ============================================================
# 重要：在导入任何使用 matplotlib 的模块之前设置后端
# ============================================================
import matplotlib
matplotlib.use('agg')  # 使用非交互式后端，避免多线程问题

# 添加lib目录到Python路径，以便导入模块
LIB_DIR = Path(__file__).parent / 'lib'
sys.path.insert(0, str(LIB_DIR))

import json
import zipfile
import traceback
from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
from datetime import datetime

from config import (
    SECRET_KEY, DEBUG, HOST, PORT,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS,
    OUTPUT_DIR, MODEL_CONFIG
)
from utils.data_processor import read_excel_sheets, preview_sheet, get_all_sheets_info
from models import MODEL_RUNNERS

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


def extract_commodity_name(filepath: str, column_mapping: dict) -> str:
    """
    从文件路径或列映射中提取品种名称

    优先级：
    1. 文件名（如 meg_full_data.xlsx → MEG）
    2. 现货列名（如 现货价格 → 通用）

    Args:
        filepath: 上传文件的路径
        column_mapping: 列名映射字典

    Returns:
        品种名称，如 'MEG', 'PP', 'PE', 'PVC', 'PTA'，无法识别返回 '通用'
    """
    import re
    from pathlib import Path

    # 尝试从文件名提取
    filename = Path(filepath).stem
    # 匹配常见品种名称模式
    commodity_patterns = {
        r'meg': 'MEG',
        r'pp': 'PP',
        r'pe': 'PE',
        r'pvc': 'PVC',
        r'pta': 'PTA',
    }

    for pattern, name in commodity_patterns.items():
        if pattern in filename.lower():
            return name

    # 如果无法识别，返回 "通用"
    return '通用'


def calculate_cleaning_stats(filepath: str, sheet_name: str, skip_rows: int = 0) -> dict:
    """
    计算数据清洗统计信息

    Parameters
    ----------
    filepath : str
        Excel 文件路径
    sheet_name : str
        工作表名称
    skip_rows : int, optional
        跳过的行数，默认为 0

    Returns
    -------
    dict
        清洗统计信息
    """
    from utils.data_processor import _clean_metadata_rows
    import pandas as pd

    # 读取原始数据
    if skip_rows > 0:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=skip_rows)
    else:
        df = pd.read_excel(filepath, sheet_name=sheet_name)

    original_rows = len(df)

    # 清理元数据行
    df_cleaned = _clean_metadata_rows(df)
    if df_cleaned is not None:
        df = df_cleaned

    # 检测日期范围
    date_range = {'start': 'N/A', 'end': 'N/A'}
    for col in df.columns:
        try:
            sample = df[col].dropna().head(100)
            if sample.empty:
                continue
            dates = pd.to_datetime(sample, errors='coerce')
            valid_ratio = dates.notna().sum() / len(sample)
            if valid_ratio > 0.8:
                valid_dates = pd.to_datetime(df[col], errors='coerce').dropna()
                if not valid_dates.empty:
                    date_range = {
                        'start': valid_dates.min().strftime('%Y-%m-%d'),
                        'end': valid_dates.max().strftime('%Y-%m-%d')
                    }
                break
        except Exception:
            continue

    return {
        'original_rows': original_rows,
        'final_rows': len(df),
        'date_range': date_range,
        'skipped_rows': skip_rows
    }


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')




@app.route('/spread')
def spread_arbitrage():
    """价差套利分析页面"""
    return render_template('spread.html')


@app.route('/quick-signal')
def quick_signal_page():
    """快速信号页面"""
    return render_template('quick_signal.html')

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

    # 获取跳过行数的参数
    skip_rows = int(request.form.get('skip_rows', '0'))

    try:
        # 保存文件
        original_filename = secure_filename(file.filename)
        # 添加时间戳避免文件名冲突
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(original_filename)
        filename = f"{name}_{timestamp}{ext}"
        filepath = UPLOAD_FOLDER / filename

        file.save(filepath)

        # 读取所有工作表信息（传递skip_rows参数）
        sheets_info = get_all_sheets_info(str(filepath), skip_rows=skip_rows)

        # 推荐最佳工作表
        recommended_sheet = recommend_sheet(sheets_info)

        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': str(filepath),
            'sheets': sheets_info,
            'recommended_sheet': recommended_sheet,
            'skip_rows': skip_rows,
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
    skip_rows = data.get('skip_rows', 0)

    try:
        # 获取工作表预览数据（传递skip_rows参数）
        preview_data = preview_sheet(filepath, sheet_name, nrows=10, skip_rows=skip_rows)

        # === 新增：计算数据清洗统计 ===
        cleaning_stats = calculate_cleaning_stats(filepath, sheet_name, skip_rows)

        # 智能推荐列映射
        suggested_columns = suggest_columns(preview_data)

        return jsonify({
            'success': True,
            'preview': preview_data,
            'suggested_columns': suggested_columns,
            'cleaning_stats': cleaning_stats  # 新增
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

    # 列名转小写便于匹配（防御非字符串列名如 datetime）
    columns = [str(c) for c in columns]
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


@app.route('/api/generate', methods=['POST'])
def generate_report():
    """
    生成模型分析报告
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    # 提取参数
    filepath = data.get('filepath')
    sheet_name = data.get('sheet_name')
    column_mapping = data.get('column_mapping')
    date_range = data.get('date_range')
    model_type = data.get('model_type')
    skip_rows = data.get('skip_rows', 0)  # 获取跳过行数参数，默认为0

    # 提取滚动回测参数（新增）
    enable_rolling_backtest = data.get('enable_rolling_backtest', False)
    n_periods = data.get('n_periods', 6)
    window_days = data.get('window_days', 90)
    min_gap_days = data.get('min_gap_days', 180)
    backtest_seed = data.get('backtest_seed', None)  # None 或整数
    restrict_to_recent_months = data.get('restrict_to_recent_months', False)  # 新增

    # 提取 DCC-GARCH 特有参数
    dist = data.get('dist', 'norm')  # 分布假设，默认为正态分布

    # 提取 ECM-GARCH 特有参数
    coint_window = data.get('coint_window', 120)  # 协整窗口，默认120天
    coupling_method = data.get('coupling_method', 'ect-garch')  # 耦合方式，默认ect-garch

    # 参数验证
    if not filepath:
        return jsonify({'error': '缺少文件路径'}), 400
    if not sheet_name:
        return jsonify({'error': '缺少工作表名称'}), 400
    if model_type == 'spread_arbitrage':
        if not column_mapping or not column_mapping.get('col_a') or not column_mapping.get('col_b'):
            return jsonify({'error': '缺少价格列映射 (col_a, col_b)'}), 400
    else:
        if not column_mapping or not column_mapping.get('spot') or not column_mapping.get('future'):
            return jsonify({'error': '缺少必要的列映射'}), 400
    if not model_type:
        return jsonify({'error': '未选择模型类型'}), 400
    if model_type not in MODEL_RUNNERS:
        return jsonify({'error': f'不支持的模型类型: {model_type}'}), 400

    # 检查文件是否存在
    if not os.path.exists(filepath):
        return jsonify({'error': f'文件不存在: {filepath}'}), 404

    try:
        # 获取模型配置（先取默认值，再用前端参数覆盖）
        model_config = MODEL_CONFIG.get(model_type, {}).copy()

        # 合并前端传来的 model_config（entry_zscore, enable_dcc_stoploss 等）
        frontend_mc = data.get('model_config')
        if frontend_mc and isinstance(frontend_mc, dict):
            model_config.update(frontend_mc)

        # 合并滚动回测配置到 model_config（新增）
        model_config.update({
            'enable_rolling_backtest': enable_rolling_backtest,
            'n_periods': n_periods,
            'window_days': window_days,
            'min_gap_days': min_gap_days,
            'backtest_seed': backtest_seed,
            'restrict_to_recent_months': restrict_to_recent_months  # 新增
        })

        # 添加 DCC-GARCH 特有参数
        if model_type == 'dcc_garch' and dist:
            model_config['dist'] = dist
            print(f"  DCC-GARCH 分布假设: {dist}")

        # 添加 ECM-GARCH 特有参数
        if model_type == 'ecm_garch':
            model_config['coint_window'] = coint_window
            model_config['coupling_method'] = coupling_method
            print(f"  ECM-GARCH 协整窗口: {coint_window}")
            print(f"  ECM-GARCH 耦合方式: {coupling_method}")

        # 打印配置信息
        if enable_rolling_backtest:
            print(f"\n[滚动回测配置]")
            print(f"  启用: 是")
            print(f"  周期数: {n_periods}")
            print(f"  每周期天数: {window_days}")
            print(f"  最小间隔: {min_gap_days}")
            print(f"  随机种子: {backtest_seed if backtest_seed is not None else '随机'}")
            print(f"{'='*60}\n")

        # 调用模型运行器
        print(f"\n{'='*60}")
        print(f"开始生成报告: {model_type}")
        print(f"文件: {filepath}")
        print(f"工作表: {sheet_name}")
        print(f"列映射: {column_mapping}")
        print(f"{'='*60}\n")

        # 创建带时间戳的输出目录，隔离不同运行的输出文件
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_output_dir = str(OUTPUT_DIR / 'web_reports' / timestamp)

        # 确保目录存在
        os.makedirs(model_output_dir, exist_ok=True)

        print(f"输出目录: {model_output_dir}")

        model_runner = MODEL_RUNNERS[model_type]
        result = model_runner(
            data_path=filepath,
            sheet_name=sheet_name,
            column_mapping=column_mapping,
            date_range=date_range,
            skip_rows=skip_rows,
            output_dir=model_output_dir,  # 使用带时间戳的目录
            model_config=model_config
        )

        if not result.get('success'):
            return jsonify({
                'error': result.get('error', '模型运行失败')
            }), 500

        # 创建ZIP包（包含HTML报告和模型结果）
        report_path = Path(result['report_path'])
        output_dir = report_path.parent

        # ZIP文件名：YYYYMMDD_品种_模型名.zip
        current_date = datetime.now().strftime('%Y%m%d')
        commodity_name = extract_commodity_name(filepath, column_mapping)

        # 模型名称映射
        MODEL_NAME_MAP = {
            'basic_garch': 'Basic_GARCH',
            'dcc_garch': 'DCC_GARCH',
            'ecm_garch': 'ECM_GARCH',
            'spread_arbitrage': 'SpreadArbitrage'
        }
        model_display_name = MODEL_NAME_MAP.get(model_type, model_type.upper())

        # 组合文件名：YYYYMMDD_HHMMSS_品种_模型名.zip（使用时间戳确保唯一性）
        zip_filename = f"{timestamp}_{commodity_name}_{model_display_name}.zip"
        zip_path = OUTPUT_DIR / 'web_reports' / zip_filename

        # 创建ZIP文件
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. 添加HTML报告
            if report_path.exists():
                zipf.write(report_path, report_path.name)

            # 2. 添加每日详细数据CSV（在 output_dir 根目录）
            #    - h_dcc_garch.csv (DCC-GARCH)
            #    - h_ecm_garch.csv (ECM-GARCH)
            for csv_file in output_dir.glob('h_*.csv'):
                zipf.write(csv_file, csv_file.name)

            # 3. 添加汇总报告CSV和Excel（在 output_dir 根目录）
            #    - backtest_report.csv/xlsx
            #    - rolling_backtest_report.csv/xlsx
            for report_file in output_dir.glob('*_report.csv'):
                zipf.write(report_file, report_file.name)
            for report_file in output_dir.glob('*_report.xlsx'):
                zipf.write(report_file, report_file.name)

            # 4. 添加模型结果子目录CSV（如果存在）
            #    - model_results/h_basic_garch.csv
            model_results_dir = output_dir / 'model_results'
            if model_results_dir.exists():
                for csv_file in model_results_dir.glob('*.csv'):
                    zipf.write(csv_file, f"model_results/{csv_file.name}")

            # 5. 添加图表（如果存在）
            figures_dir = output_dir / 'figures'
            if figures_dir.exists():
                for fig_file in figures_dir.glob('*.png'):
                    zipf.write(fig_file, f"figures/{fig_file.name}")

        # 6. 导出配置文件（用于快速信号，所有模型通用）
        config_download_url = None

        # 确定导出的参数字段（不同模型有不同的可配参数）
        if model_type == 'spread_arbitrage':
            param_keys = ('entry_zscore', 'exit_zscore', 'zscore_window',
                          'max_holding_days', 'enable_dcc_stoploss')
        elif model_type == 'basic_garch':
            param_keys = ('p', 'q', 'corr_window', 'tax_rate')
        elif model_type == 'dcc_garch':
            param_keys = ('p', 'q', 'dist', 'tax_rate')
        elif model_type == 'ecm_garch':
            param_keys = ('p', 'q', 'coint_window', 'coupling_method', 'tax_rate')
        else:
            param_keys = ()

        if param_keys:
            config_export = {
                'version': '1.0',
                'created_at': timestamp,
                'model_type': model_type,
                'data': {
                    'filepath': str(Path(filepath).absolute()),
                    'sheet_name': sheet_name,
                    'column_mapping': column_mapping,
                    'skip_rows': skip_rows,
                    'date_range': date_range,
                },
                'parameters': {
                    k: model_config[k] for k in param_keys if k in model_config
                },
                'last_analysis_summary': result.get('summary', {}),
            }
            # 保存到输出目录（供单独下载）
            configs_dir = OUTPUT_DIR / 'configs'
            os.makedirs(configs_dir, exist_ok=True)
            config_standalone_path = configs_dir / f'{timestamp}_analysis_config.json'
            with open(config_standalone_path, 'w', encoding='utf-8') as f:
                json.dump(config_export, f, indent=2, ensure_ascii=False)
            config_download_url = f'/download-config/{timestamp}_analysis_config.json'
            # 同时加入 ZIP
            with zipfile.ZipFile(zip_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(config_standalone_path, 'analysis_config.json')

        # 返回结果
        response_data = {
            'success': True,
            'report_path': str(report_path.relative_to(OUTPUT_DIR)),
            'download_url': f'/download/{zip_filename}',
            'view_url': f'/report?path={report_path.relative_to(OUTPUT_DIR)}',
            'summary': result.get('summary', {}),
            'message': f'{MODEL_CONFIG[model_type]["name"]}模型分析完成'
        }
        if config_download_url:
            response_data['config_download_url'] = config_download_url
        return jsonify(response_data)

    except Exception as e:
        error_msg = f'生成报告失败: {str(e)}\n{traceback.format_exc()}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """
    下载生成的报告文件
    """
    try:
        # 安全验证：防止路径遍历攻击
        # 注意：文件名是系统生成的（已安全），不需要 secure_filename() 过滤中文
        if '..' in filename or filename.startswith('/') or '\\' in filename:
            return jsonify({'error': '非法文件名'}), 400

        file_path = (OUTPUT_DIR / 'web_reports' / filename).resolve()
        allowed_dir = (OUTPUT_DIR / 'web_reports').resolve()

        # 确保解析后的路径仍在允许的目录内
        if not str(file_path).startswith(str(allowed_dir)):
            return jsonify({'error': '非法文件路径'}), 403

        if not file_path.exists():
            return jsonify({'error': f'文件不存在: {filename}'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


@app.route('/download-config/<filename>')
def download_config_file(filename):
    """
    下载快速信号配置文件
    """
    try:
        if '..' in filename or filename.startswith('/') or '\\' in filename:
            return jsonify({'error': '非法文件名'}), 400

        file_path = (OUTPUT_DIR / 'configs' / filename).resolve()
        allowed_dir = (OUTPUT_DIR / 'configs').resolve()

        if not str(file_path).startswith(str(allowed_dir)):
            return jsonify({'error': '非法文件路径'}), 403

        if not file_path.exists():
            return jsonify({'error': f'配置文件不存在: {filename}'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name='analysis_config.json',
            mimetype='application/json'
        )

    except Exception as e:
        return jsonify({'error': f'下载失败: {str(e)}'}), 500


@app.route('/report')
def view_report():
    """
    查看HTML报告（动态修正图片路径）
    """
    report_path = request.args.get('path')

    if not report_path:
        return '<h1>错误：缺少报告路径参数</h1>', 400

    try:
        # 安全验证：防止路径遍历攻击
        if '..' in report_path or report_path.startswith('/'):
            return '<h1>错误：非法路径</h1>', 400

        file_path = (OUTPUT_DIR / report_path).resolve()
        allowed_dir = OUTPUT_DIR.resolve()

        # 确保解析后的路径仍在输出目录内
        if not str(file_path).startswith(str(allowed_dir)):
            return '<h1>错误：非法路径</h1>', 403

        if not file_path.exists():
            return f'<h1>错误：报告文件不存在</h1><p>路径: {report_path}</p>', 404

        # 只允许查看 HTML 文件
        if not file_path.suffix.lower() == '.html':
            return '<h1>错误：仅支持查看 HTML 文件</h1>', 400

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # === 动态修正图片路径 ===
        # 提取报告所在目录（需要保留相对路径结构，如 web_reports/20260306_105718）
        report_dir = file_path.parent.relative_to(OUTPUT_DIR)

        # 将图片路径从 figures/xxx.png 改为相对于根目录的路径
        # 使用正则表达式替换
        import re
        content = re.sub(
            r'src="figures/([^"]+)"',
            lambda m: f'src="/report-images/{report_dir}/figures/{m.group(1)}"',
            content
        )

        return content

    except Exception as e:
        return f'<h1>错误：无法读取报告</h1><p>{str(e)}</p>', 500


@app.route('/report-images/<path:filename>')
def serve_report_images(filename):
    """
    提供报告图片的静态文件服务

    路径格式：/report-images/YYYYMMDD_品种_模型/figures/xxx.png
    """
    try:
        # 安全验证
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': '非法路径'}), 400

        # 构建完整路径
        file_path = (OUTPUT_DIR / filename).resolve()
        allowed_dir = OUTPUT_DIR.resolve()

        # 路径安全检查
        if not str(file_path).startswith(str(allowed_dir)):
            return jsonify({'error': '非法路径'}), 403

        if not file_path.exists():
            return jsonify({'error': f'图片不存在: {filename}'}), 404

        return send_file(file_path)

    except Exception as e:
        return jsonify({'error': f'图片加载失败: {str(e)}'}), 500


@app.route('/api/quick-signal', methods=['POST'])
def quick_signal_api():
    """
    快速信号 API — 接收配置文件，返回最近 30 天信号
    """
    # 支持两种方式：上传文件 或 JSON body
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        try:
            config = json.load(file)
        except Exception as e:
            return jsonify({'error': f'配置文件格式错误: {str(e)}'}), 400
    else:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        config = data.get('config') or data

    # 校验配置
    if not config.get('data', {}).get('filepath'):
        return jsonify({'error': '配置文件缺少 data.filepath'}), 400
    model_type = config.get('model_type', '')
    if model_type not in ('spread_arbitrage', 'basic_garch', 'dcc_garch', 'ecm_garch'):
        return jsonify({'error': f'不支持的模型类型: {model_type}'}), 400

    try:
        from lib.spread_arbitrage_analyzer.quick_signal import QuickSignalCalculator

        calculator = QuickSignalCalculator()
        result = calculator.calculate(config)

        if not result.get('success'):
            return jsonify({'error': result.get('error', '计算失败')}), 500

        return jsonify(result)

    except Exception as e:
        error_msg = f'快速信号计算失败: {str(e)}\n{traceback.format_exc()}'
        print(error_msg)
        return jsonify({'error': error_msg}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """处理文件过大错误"""
    return jsonify({
        'error': f'文件过大，请上传小于{MAX_CONTENT_LENGTH // (1024*1024)}MB的文件'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    """处理服务器内部错误"""
    return jsonify({
        'error': '服务器内部错误，请稍后重试'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("GARCH模型套保分析Web平台")
    print("=" * 60)
    print(f"请在浏览器中访问: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)
