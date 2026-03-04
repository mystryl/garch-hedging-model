#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DCC-GARCH模型包装器
为Web平台提供统一的模型运行接口
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import numpy as np

# 添加必要的目录到路径
# lib/ 目录用于导入 model_dcc_garch
# 项目根目录用于导入 utils
lib_dir = Path(__file__).parent.parent / 'lib'
project_root = Path(__file__).parent.parent

lib_dir_str = str(lib_dir)
project_root_str = str(project_root)
if lib_dir_str not in sys.path:
    sys.path.insert(0, lib_dir_str)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from lib.dcc_garch_analyzer import fit_dcc_garch, run_rolling_backtest, DCCGarchConfig
from utils.data_processor import read_excel_sheets


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config):
    """
    运行DCC-GARCH模型分析

    Parameters
    ----------
    data_path : str
        Excel文件路径
    sheet_name : str
        工作表名称
    column_mapping : dict
        列映射 {'spot': str, 'future': str, 'date': str}
    date_range : dict
        日期范围 {'start': str, 'end': str} 或 None
    output_dir : str
        输出目录
    model_config : dict
        模型配置参数

    Returns
    -------
    dict
        {
            'success': bool,
            'report_path': str,      # HTML报告路径
            'summary': dict,          # 摘要统计信息
            'error': str              # 错误信息（失败时）
        }
    """
    try:
        print("\n" + "="*60)
        print("DCC-GARCH Wrapper - 开始运行模型")
        print("="*60)

        # 1. 参数验证
        if not os.path.exists(data_path):
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': f'数据文件不存在: {data_path}'
            }

        if not column_mapping.get('spot') or not column_mapping.get('future'):
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': '缺少必要的列映射（spot/future）'
            }

        # 2. 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 使用时间戳创建子目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_output_dir = output_path / f'dcc_garch_{timestamp}'
        run_output_dir.mkdir(exist_ok=True)

        print(f"输出目录: {run_output_dir}")

        # 3. 读取和预处理数据
        print(f"\n读取工作表: {sheet_name}")
        sheets = read_excel_sheets(data_path)
        if sheet_name not in sheets:
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': f'工作表不存在: {sheet_name}'
            }

        df = sheets[sheet_name]

        # 应用列映射
        spot_col = column_mapping['spot']
        future_col = column_mapping['future']
        date_col = column_mapping.get('date')

        # 检查列是否存在
        if spot_col not in df.columns:
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': f'现货列不存在: {spot_col}'
            }
        if future_col not in df.columns:
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': f'期货列不存在: {future_col}'
            }

        # 数据预处理
        data = pd.DataFrame({
            'spot': df[spot_col].values,
            'futures': df[future_col].values
        })

        # 添加日期列
        if date_col and date_col in df.columns:
            data['date'] = pd.to_datetime(df[date_col])
        else:
            data['date'] = pd.RangeIndex(start=0, stop=len(df))

        # 计算收益率（对数收益率）
        data['r_s'] = np.log(data['spot'] / data['spot'].shift(1))
        data['r_f'] = np.log(data['futures'] / data['futures'].shift(1))

        # 删除第一行（NaN）
        data = data.dropna().reset_index(drop=True)

        print(f"有效数据量: {len(data)}")

        # 应用日期范围过滤
        if date_range and date_range.get('start') and date_range.get('end'):
            start_date = pd.to_datetime(date_range['start'])
            end_date = pd.to_datetime(date_range['end'])
            mask = (data['date'] >= start_date) & (data['date'] <= end_date)
            data = data[mask].reset_index(drop=True)
            print(f"日期范围过滤后: {len(data)} 条记录")

        # 4. 创建DCC-GARCH配置并运行模型
        print(f"\n开始运行DCC-GARCH分析...")

        # 创建配置对象
        config = DCCGarchConfig(
            p=model_config.get('p', 1),
            q=model_config.get('q', 1),
            dist=model_config.get('dist', 'norm'),
            tax_rate=model_config.get('tax_rate', 0.13),
            enable_rolling_backtest=model_config.get('enable_rolling_backtest', False),
            n_periods=model_config.get('n_periods', 6),
            window_days=model_config.get('window_days', 90),
            min_gap_days=model_config.get('min_gap_days', 180),
            backtest_seed=model_config.get('backtest_seed', None),
            output_dir=str(run_output_dir / 'model_results')
        )

        print(f"模型配置: p={config.p}, q={config.q}, dist={config.dist}")
        if config.enable_rolling_backtest:
            print(f"滚动回测: n_periods={config.n_periods}, "
                  f"window_days={config.window_days}, "
                  f"seed={'随机' if config.backtest_seed is None else config.backtest_seed}")

        # 拟合模型
        model_results = fit_dcc_garch(
            data,
            p=config.p,
            q=config.q,
            output_dir=config.output_dir,
            dist=config.dist,
            config=config
        )

        # 如果启用滚动回测，运行滚动回测
        if config.enable_rolling_backtest:
            print("\n运行滚动回测...")
            backtest_results = run_rolling_backtest(
                data=data,
                hedge_ratios=model_results['h_actual'],
                n_periods=config.n_periods,
                window_days=config.window_days,
                min_gap_days=config.min_gap_days,
                seed=config.backtest_seed,
                tax_rate=config.tax_rate,
                output_dir=str(run_output_dir)
            )
            # 将滚动回测结果合并到 model_results
            model_results['rolling_backtest'] = backtest_results

        # 5. 提取摘要信息
        h_actual = model_results.get('h_actual', [])
        h_mean = float(pd.Series(h_actual).mean()) if len(h_actual) > 0 else 0.0
        h_std = float(pd.Series(h_actual).std()) if len(h_actual) > 0 else 0.0

        rho_t = model_results.get('rho_t', [])
        rho_mean = float(pd.Series(rho_t).mean()) if len(rho_t) > 0 else 0.0

        # 计算套保效果
        r_s = data['r_s'].values
        r_f = data['r_f'].values

        var_unhedged = np.var(r_s)
        var_hedged = np.var(r_s - h_mean * r_f)
        variance_reduction = 1 - var_hedged / var_unhedged

        summary = {
            'model_name': 'DCC-GARCH',
            'model_params': f"DCC-GARCH({model_config.get('p', 1)},{model_config.get('q', 1)})",
            'hedge_ratio_mean': h_mean,
            'hedge_ratio_std': h_std,
            'correlation_mean': rho_mean,
            'variance_reduction': variance_reduction,
            'ederington': variance_reduction,
            'output_dir': str(run_output_dir),
            'timestamp': timestamp
        }

        # 6. 生成HTML报告
        report_html = _create_html_report(
            run_output_dir,
            data,
            model_results,
            summary,
            column_mapping
        )

        print(f"\n✓ 分析完成!")
        print(f"  报告路径: {report_html}")
        print(f"  套保比例均值: {h_mean:.4f}")
        print(f"  动态相关系数均值: {rho_mean:.4f}")
        print(f"  方差降低: {variance_reduction:.2%}")

        return {
            'success': True,
            'report_path': str(report_html),
            'summary': summary,
            'error': None
        }

    except Exception as e:
        error_msg = f'DCC-GARCH模型运行失败: {str(e)}\n{traceback.format_exc()}'
        print(f"\n✗ {error_msg}")
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': error_msg
        }


def _create_html_report(output_dir, data, model_results, summary, column_mapping):
    """创建HTML报告"""
    h_actual = model_results.get('h_actual', [])
    rho_t = model_results.get('rho_t', [])

    # 统计信息
    h_min = float(np.min(h_actual)) if len(h_actual) > 0 else 0.0
    h_max = float(np.max(h_actual)) if len(h_actual) > 0 else 0.0
    h_median = float(np.median(h_actual)) if len(h_actual) > 0 else 0.0

    rho_min = float(np.min(rho_t)) if len(rho_t) > 0 else 0.0
    rho_max = float(np.max(rho_t)) if len(rho_t) > 0 else 0.0

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DCC-GARCH 套保分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 8px;
        }}
        .metric-value {{
            font-size: 28px;
            font-weight: bold;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #e74c3c;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 DCC-GARCH 套保分析报告</h1>
        <p>生成时间: {summary['timestamp']}</p>

        <div class="summary">
            <div class="metric">
                <div class="metric-label">套保比例均值</div>
                <div class="metric-value">{summary['hedge_ratio_mean']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">动态相关系数均值</div>
                <div class="metric-value">{summary['correlation_mean']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">方差降低</div>
                <div class="metric-value">{summary['variance_reduction']:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Ederington有效性</div>
                <div class="metric-value">{summary['ederington']:.4f}</div>
            </div>
        </div>

        <div class="section">
            <h2>模型配置</h2>
            <table>
                <tr><th>参数</th><th>值</th></tr>
                <tr><td>模型类型</td><td>{summary['model_name']}</td></tr>
                <tr><td>模型参数</td><td>{summary['model_params']}</td></tr>
                <tr><td>现货列</td><td>{column_mapping.get('spot', 'N/A')}</td></tr>
                <tr><td>期货列</td><td>{column_mapping.get('future', 'N/A')}</td></tr>
                <tr><td>日期列</td><td>{column_mapping.get('date', '自动检测')}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>套保比例统计</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>均值</td><td>{h_mean:.4f}</td></tr>
                <tr><td>中位数</td><td>{h_median:.4f}</td></tr>
                <tr><td>标准差</td><td>{h_std:.4f}</td></tr>
                <tr><td>最小值</td><td>{h_min:.4f}</td></tr>
                <tr><td>最大值</td><td>{h_max:.4f}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>动态相关系数统计</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>均值</td><td>{summary['correlation_mean']:.4f}</td></tr>
                <tr><td>最小值</td><td>{rho_min:.4f}</td></tr>
                <tr><td>最大值</td><td>{rho_max:.4f}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>套保效果评估</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>Ederington套保有效性</td><td>{summary['ederington']:.4f}</td></tr>
                <tr><td>方差降低比例</td><td>{summary['variance_reduction']:.2%}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>说明</h2>
            <p>本报告基于DCC-GARCH模型，捕捉现货与期货收益率的时变相关性和波动性。</p>
            <p><strong>模型特点：</strong></p>
            <ul>
                <li>使用DCC（动态条件相关）结构，相关系数随时间变化</li>
                <li>每个序列单独拟合GARCH(1,1)模型</li>
                <li>税点调整：已应用13%增值税调整</li>
            </ul>
        </div>
    </div>
</body>
</html>
    """

    report_path = output_dir / 'report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return report_path
