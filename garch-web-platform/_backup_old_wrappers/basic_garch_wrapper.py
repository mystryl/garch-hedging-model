#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic GARCH模型包装器
为Web平台提供统一的模型运行接口
"""

import os
import sys
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# 添加项目根目录到路径（basic_garch_analyzer 位于 worktree 根目录）
# __file__ = models/basic_garch_wrapper.py
# parent = models/, parent.parent = garch-web-platform/, parent.parent.parent = worktree root
worktree_root = Path(__file__).parent.parent.parent
worktree_root_str = str(worktree_root)
if worktree_root_str not in sys.path:
    sys.path.insert(0, worktree_root_str)

from basic_garch_analyzer import run_analysis
from basic_garch_analyzer.config import ModelConfig
from utils.data_processor import read_excel_sheets


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config, skip_rows=0):
    """
    运行Basic GARCH模型分析

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
    skip_rows : int, optional
        跳过的行数，默认为0

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
        print("Basic GARCH Wrapper - 开始运行模型")
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
        run_output_dir = output_path / f'basic_garch_{timestamp}'
        run_output_dir.mkdir(exist_ok=True)

        print(f"输出目录: {run_output_dir}")

        # 3. 创建模型配置
        config = ModelConfig(
            p=model_config.get('p', 1),
            q=model_config.get('q', 1),
            corr_window=model_config.get('corr_window', 120),
            tax_rate=model_config.get('tax_rate', 0.13),
            enable_rolling_backtest=model_config.get('enable_rolling_backtest', False),
            n_periods=model_config.get('n_periods', 6),
            window_days=model_config.get('window_days', 90),
            min_gap_days=model_config.get('min_gap_days', 180),
            backtest_seed=model_config.get('backtest_seed', None),  # None=随机
            output_dir=str(run_output_dir)
        )

        print(f"模型配置: p={config.p}, q={config.q}, "
              f"corr_window={config.corr_window}, tax_rate={config.tax_rate}")
        if config.enable_rolling_backtest:
            print(f"滚动回测: n_periods={config.n_periods}, "
                  f"window_days={config.window_days}, "
                  f"min_gap_days={config.min_gap_days}, "
                  f"seed={'随机' if config.backtest_seed is None else config.backtest_seed}")

        # 4. 预加载数据并验证列名
        print("\n预加载数据...")
        print(f"跳过行数: {skip_rows}")

        # 使用统一的数据加载方法（会自动清理元数据行）
        sheets = read_excel_sheets(data_path, skip_rows=skip_rows)

        # 验证工作表存在
        if sheet_name not in sheets:
            # 尝试使用第一个工作表
            sheet_name = list(sheets.keys())[0]
            print(f"⚠ 工作表不存在，使用第一个工作表: {sheet_name}")

        df = sheets[sheet_name]

        # 验证列存在
        spot_col = column_mapping['spot']
        future_col = column_mapping['future']
        date_col = column_mapping.get('date')

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

        # 5. 运行分析
        print("\n开始运行Basic GARCH分析...")
        result = run_analysis(
            excel_path=data_path,
            spot_col=spot_col,
            futures_col=future_col,
            date_col=date_col,
            skip_rows=skip_rows,
            config=config,
            interactive=False
        )

        # 5.1 生成图表
        print("\n生成图表...")
        from basic_garch_analyzer import report_generator

        # 创建图表目录
        figures_dir = run_output_dir / 'figures'
        figures_dir.mkdir(exist_ok=True)

        # 获取数据和模型结果
        data = result.get('data')
        model_results = result.get('model_results')

        # 生成基础图表
        if data is not None and model_results is not None:
            try:
                report_generator.plot_price_series(data, str(figures_dir / '1_price_series.png'))
                report_generator.plot_returns(data, str(figures_dir / '2_returns.png'))
                report_generator.plot_hedge_ratio(data, model_results, str(figures_dir / '3_hedge_ratio.png'))
                report_generator.plot_volatility(data, model_results, str(figures_dir / '4_volatility.png'))
                print(f"✓ 图表已保存到: {figures_dir}")
            except Exception as e:
                print(f"⚠ 图表生成部分失败: {e}")

        # 5.2 提取摘要信息
        model_results = result.get('model_results', {})
        metrics = result.get('metrics', {})

        h_final = model_results.get('h_final', [])
        h_mean = float(pd.Series(h_final).mean()) if len(h_final) > 0 else 0.0
        h_std = float(pd.Series(h_final).std()) if len(h_final) > 0 else 0.0

        summary = {
            'model_name': 'Basic GARCH',
            'model_params': f'GARCH({config.p},{config.q})',
            'hedge_ratio_mean': h_mean,
            'hedge_ratio_std': h_std,
            'variance_reduction': metrics.get('variance_reduction', 0.0),
            'ederington': metrics.get('ederington', 0.0),
            'sharpe_hedged': metrics.get('sharpe_hedged', 0.0),
            'max_dd_hedged': metrics.get('max_dd_hedged', 0.0),
            'output_dir': str(run_output_dir),
            'timestamp': timestamp
        }

        # 6. 查找HTML报告
        report_html = run_output_dir / 'report.html'
        if not report_html.exists():
            # 如果没有生成HTML报告，创建一个简单的
            report_html = _create_simple_report(
                run_output_dir,
                result,
                summary,
                column_mapping
            )

        print(f"\n✓ 分析完成!")
        print(f"  报告路径: {report_html}")
        print(f"  套保比例均值: {h_mean:.4f}")
        print(f"  方差降低: {summary['variance_reduction']:.2%}")

        return {
            'success': True,
            'report_path': str(report_html),
            'summary': summary,
            'error': None
        }

    except Exception as e:
        error_msg = f'Basic GARCH模型运行失败: {str(e)}\n{traceback.format_exc()}'
        print(f"\n✗ {error_msg}")
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': error_msg
        }


def _create_simple_report(output_dir, result, summary, column_mapping):
    """
    创建简单的HTML报告（当run_analysis未生成报告时）
    """
    from jinja2 import Template

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Basic GARCH 套保分析报告</title>
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
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Basic GARCH 套保分析报告</h1>
        <p>生成时间: {summary['timestamp']}</p>

        <div class="summary">
            <div class="metric">
                <div class="metric-label">套保比例均值</div>
                <div class="metric-value">{summary['hedge_ratio_mean']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">方差降低</div>
                <div class="metric-value">{summary['variance_reduction']:.2%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">夏普比率 (套保后)</div>
                <div class="metric-value">{summary['sharpe_hedged']:.4f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">最大回撤 (套保后)</div>
                <div class="metric-value">{summary['max_dd_hedged']:.2%}</div>
            </div>
        </div>

        <div class="section">
            <h2>📈 数据可视化</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                <div>
                    <h3>价格走势</h3>
                    <img src="figures/1_price_series.png" alt="价格走势图" style="width: 100%; border-radius: 8px;">
                </div>
                <div>
                    <h3>收益率</h3>
                    <img src="figures/2_returns.png" alt="收益率图" style="width: 100%; border-radius: 8px;">
                </div>
                <div>
                    <h3>动态套保比例</h3>
                    <img src="figures/3_hedge_ratio.png" alt="套保比例图" style="width: 100%; border-radius: 8px;">
                </div>
                <div>
                    <h3>波动率</h3>
                    <img src="figures/4_volatility.png" alt="波动率图" style="width: 100%; border-radius: 8px;">
                </div>
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
            <h2>套保效果评估</h2>
            <table>
                <tr><th>指标</th><th>值</th></tr>
                <tr><td>Ederington套保有效性</td><td>{summary['ederington']:.4f}</td></tr>
                <tr><td>方差降低比例</td><td>{summary['variance_reduction']:.2%}</td></tr>
                <tr><td>套保比例标准差</td><td>{summary['hedge_ratio_std']:.4f}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>说明</h2>
            <p>本报告基于Basic GARCH(1,1)模型，使用滚动窗口估计动态相关系数，计算最优套保比例。</p>
            <p><strong>税点调整：</strong>已应用13%增值税调整，套保比例为税后实际值。</p>
        </div>
    </div>
</body>
</html>
    """

    report_path = output_dir / 'report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return report_path
