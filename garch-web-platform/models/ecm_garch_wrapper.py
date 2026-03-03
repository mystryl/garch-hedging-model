#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ECM-GARCH模型包装器
为Web平台提供统一的模型运行接口
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from model_ecm_garch import fit_ecm_garch
from utils.data_processor import read_excel_sheets


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config):
    """
    运行ECM-GARCH模型分析

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
        print("ECM-GARCH Wrapper - 开始运行模型")
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
        run_output_dir = output_path / f'ecm_garch_{timestamp}'
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

        # 4. 运行ECM-GARCH模型
        print(f"\n开始运行ECM-GARCH分析...")
        print(f"模型配置: p={model_config.get('p', 1)}, q={model_config.get('q', 1)}, "
              f"coint_window={model_config.get('coint_window', 120)}")

        model_results = fit_ecm_garch(
            data,
            p=model_config.get('p', 1),
            q=model_config.get('q', 1),
            output_dir=str(run_output_dir / 'model_results'),
            coint_window=model_config.get('coint_window', 120),
            tax_adjust=model_config.get('tax_adjust', True),
            coupling_method=model_config.get('coupling_method', 'ect-garch')
        )

        # 5. 提取摘要信息
        h_actual = model_results.get('h_actual', [])
        h_mean = float(pd.Series(h_actual).mean()) if len(h_actual) > 0 else 0.0
        h_std = float(pd.Series(h_actual).std()) if len(h_actual) > 0 else 0.0

        ecm_params = model_results.get('ecm_params', {})
        h_ecm_base = ecm_params.get('h_ecm', 0.0)
        gamma = ecm_params.get('gamma', 0.0)

        cointegration_params = model_results.get('cointegration_params', {})
        beta1_mean = cointegration_params.get('beta1_mean', 0.0)

        evaluation = model_results.get('evaluation', {})
        variance_reduction = evaluation.get('variance_reduction', 0.0)
        hedging_effectiveness = evaluation.get('hedging_effectiveness', 0.0)

        summary = {
            'model_name': 'ECM-GARCH',
            'model_params': f"ECM-GARCH({model_config.get('p', 1)},{model_config.get('q', 1)})",
            'hedge_ratio_mean': h_mean,
            'hedge_ratio_std': h_std,
            'h_ecm_base': h_ecm_base,
            'error_correction_coeff': gamma,
            'cointegration_coeff': beta1_mean,
            'variance_reduction': variance_reduction,
            'hedging_effectiveness': hedging_effectiveness,
            'ederington': hedging_effectiveness,
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
        print(f"  ECM基础套保比例: {h_ecm_base:.4f}")
        print(f"  误差修正系数: {gamma:.6f}")
        print(f"  方差降低: {variance_reduction:.2%}")

        return {
            'success': True,
            'report_path': str(report_html),
            'summary': summary,
            'error': None
        }

    except Exception as e:
        error_msg = f'ECM-GARCH模型运行失败: {str(e)}\n{traceback.format_exc()}'
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
    ect = model_results.get('ect', [])

    # 统计信息
    h_min = float(np.min(h_actual)) if len(h_actual) > 0 else 0.0
    h_max = float(np.max(h_actual)) if len(h_actual) > 0 else 0.0
    h_median = float(np.median(h_actual)) if len(h_actual) > 0 else 0.0

    ect_mean = float(np.nanmean(ect)) if len(ect) > 0 else 0.0
    ect_std = float(np.nanstd(ect)) if len(ect) > 0 else 0.0

    ecm_params = model_results.get('ecm_params', {})
    alpha = ecm_params.get('alpha', 0.0)
    gamma = ecm_params.get('gamma', 0.0)

    cointegration_params = model_results.get('cointegration_params', {})
    beta0_mean = cointegration_params.get('beta0_mean', 0.0)
    beta1_mean = cointegration_params.get('beta1_mean', 0.0)
    r_squared_mean = cointegration_params.get('r_squared_mean', 0.0)

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ECM-GARCH 套保分析报告</title>
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
            border-bottom: 3px solid #2ecc71;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
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
            background-color: #2ecc71;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .equation {{
            background-color: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
            text-align: center;
            font-size: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 ECM-GARCH 套保分析报告</h1>
        <p>生成时间: {summary['timestamp']}</p>

        <div class="summary">
            <div class="metric">
                <div class="metric-label">套保比例均值</div>
                <div class="metric-value">{summary['hedge_ratio_mean']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">误差修正系数</div>
                <div class="metric-value">{summary['error_correction_coeff']:.6f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">协整系数</div>
                <div class="metric-value">{summary['cointegration_coeff']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">方差降低</div>
                <div class="metric-value">{summary['variance_reduction']:.2%}</div>
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
            <h2>ECM方程估计结果</h2>
            <div class="equation">
                r<sub>s</sub>(t) = {alpha:.6f} + {summary['h_ecm_base']:.4f}·r<sub>f</sub>(t) + {gamma:.6f}·ect<sub>t-1</sub> + &epsilon;<sub>t</sub>
            </div>
            <table>
                <tr><th>参数</th><th>值</th><th>说明</th></tr>
                <tr><td>&alpha; (常数项)</td><td>{alpha:.6f}</td><td>截距项</td></tr>
                <tr><td>h (套保比例)</td><td>{summary['h_ecm_base']:.4f}</td><td>ECM估计的静态套保比例</td></tr>
                <tr><td>&gamma; (误差修正系数)</td><td>{gamma:.6f}</td><td>{'<span style="color: green;">✓ 负值：符合反向修正机制</span>' if gamma < 0 else '<span style="color: orange;">⚠ 正值：可能存在正向调整</span>'}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>协整关系统计</h2>
            <table>
                <tr><th>参数</th><th>均值</th><th>说明</th></tr>
                <tr><td>&beta;<sub>0</sub> (截距)</td><td>{beta0_mean:.4f}</td><td>协整方程截距</td></tr>
                <tr><td>&beta;<sub>1</sub> (斜率)</td><td>{beta1_mean:.4f}</td><td>长期均衡系数</td></tr>
                <tr><td>R² (拟合优度)</td><td>{r_squared_mean:.4f}</td><td>协整关系拟合度</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>误差修正项统计</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>均值</td><td>{ect_mean:.4f}</td></tr>
                <tr><td>标准差</td><td>{ect_std:.4f}</td></tr>
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
            <h2>套保效果评估</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>套保有效性 (HE)</td><td>{summary['hedging_effectiveness']:.4f}</td></tr>
                <tr><td>方差降低比例</td><td>{summary['variance_reduction']:.2%}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>说明</h2>
            <p>本报告基于ECM-GARCH模型，考虑现货与期货的长期均衡关系（协整关系）。</p>
            <p><strong>模型特点：</strong></p>
            <ul>
                <li><strong>误差修正机制：</strong>通过误差修正项(ECT)捕捉长期均衡偏离的短期调整</li>
                <li><strong>协整关系：</strong>使用滚动窗口估计时变协整参数，更灵活地适应市场变化</li>
                <li><strong>GARCH建模：</strong>对ECM残差拟合GARCH模型，捕捉波动率聚集效应</li>
                <li><strong>税点调整：</strong>已应用13%增值税调整，套保比例为税后实际值</li>
            </ul>
            <p><strong>ECM方程解释：</strong></p>
            <p>当误差修正系数 &gamma; < 0 时，表示当现货价格相对于期货价格偏高（ect > 0）时，下一期现货收益率会下降，向均衡回归。这是符合经济理论的反向修正机制。</p>
        </div>
    </div>
</body>
</html>
    """

    report_path = output_dir / 'report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return report_path
