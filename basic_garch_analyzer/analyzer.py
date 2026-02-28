"""
核心分析器模块
合并回测评估和报告生成

注意：此模块保留用于全样本回测（备选方案）
默认使用滚动回测模式（rolling_backtest.py）

要使用全样本回测:
    >>> config = ModelConfig(enable_rolling_backtest=False)
    >>> run_analysis(..., config=config)
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# 先设置绘图风格
sns.set_style('whitegrid')

# 然后配置中文字体（必须在 set_style 之后）
from basic_garch_analyzer.font_config import setup_chinese_font
setup_chinese_font()

# 导入现有模块的函数
from basic_garch_analyzer.backtest_evaluator import (
    calculate_max_drawdown,
    evaluate_hedging_effectiveness
)
from basic_garch_analyzer.report_generator import (
    plot_price_series,
    plot_returns,
    plot_hedge_ratio,
    plot_volatility,
    plot_backtest_results,
    plot_drawdown,
    plot_performance_metrics,
    plot_summary_table,
    generate_html_report
)


# 自定义异常
class AnalyzerError(Exception):
    """分析器基础异常"""
    pass


class ReportGenerationError(AnalyzerError):
    """报告生成失败"""
    pass


def evaluate_and_report(
    data: pd.DataFrame,
    results: dict,
    selected: dict,
    config,
    output_dir: str = 'outputs'
) -> dict:
    """
    执行回测评估并生成完整报告

    Parameters:
    -----------
    data : pd.DataFrame
        包含 date, spot, futures, r_s, r_f, spread 的数据
    results : dict
        模型拟合结果（来自 fit_basic_garch）
    selected : dict
        列名配置 {'date': str, 'spot': str, 'futures': str}
    config : ModelConfig
        模型配置对象
    output_dir : str
        输出目录路径

    Returns:
    --------
    report_info : dict
        报告信息字典
        {
            'metrics': dict,           # 评估指标
            'figures': list,           # 图表路径列表
            'html_path': str,          # HTML报告路径
            'csv_path': str,           # CSV报告路径
            'output_dir': str          # 输出目录
        }
    """
    # 输入验证
    if data.empty:
        raise ReportGenerationError("数据为空")

    if 'h_final' not in results:
        raise ReportGenerationError("模型结果中缺少套保比例")

    required_columns = ['date', 'spot', 'futures', 'r_s', 'r_f', 'spread']
    missing_cols = [col for col in required_columns if col not in data.columns]
    if missing_cols:
        raise ReportGenerationError(f"数据缺少必需列: {missing_cols}")

    print("\n" + "=" * 60)
    print("回测评估与报告生成")
    print("=" * 60)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)
    model_results_dir = os.path.join(output_dir, 'model_results')
    os.makedirs(model_results_dir, exist_ok=True)

    # ===== 1. 计算回测指标 =====
    print("\n[1/5] 计算回测指标...")
    metrics = evaluate_hedging_effectiveness(
        data,
        results['h_final'],
        tax_rate=config.tax_rate
    )

    # ===== 2. 准备评估结果字典（用于绘图函数）=====
    print("\n[2/5] 准备图表数据...")

    # 对齐数据长度
    min_len = min(len(data), len(results['h_final']))
    data_aligned = data.iloc[:min_len].copy()
    h_aligned = results['h_final'][:min_len]

    # 计算套保后收益率
    r_hedged = data_aligned['r_s'].values - h_aligned * data_aligned['r_f'].values
    r_unhedged = data_aligned['r_s'].values

    # 计算累计收益率
    cumulative_unhedged = np.cumprod(1 + r_unhedged)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    # 计算回撤序列
    running_max_h = np.maximum.accumulate(cumulative_hedged)
    drawdown_series = (cumulative_hedged - running_max_h) / running_max_h

    eval_results = {
        'metrics': metrics,
        'returns_unhedged': r_unhedged,
        'returns_hedged': r_hedged,
        'drawdown_series': drawdown_series,
        'start_date': data_aligned['date'].min(),
        'end_date': data_aligned['date'].max(),
    }

    # ===== 3. 生成8张图表 =====
    print("\n[3/5] 生成可视化图表...")

    figure_paths = []

    # 图1: 价格走势
    path = os.path.join(figures_dir, '1_price_series.png')
    plot_price_series(data_aligned, path)
    figure_paths.append(path)

    # 图2: 收益率分布
    path = os.path.join(figures_dir, '2_returns.png')
    plot_returns(data_aligned, path)
    figure_paths.append(path)

    # 图3: 套保比例
    path = os.path.join(figures_dir, '3_hedge_ratio.png')
    plot_hedge_ratio(data_aligned, results, path)
    figure_paths.append(path)

    # 图4: 波动率与相关性
    path = os.path.join(figures_dir, '4_volatility.png')
    plot_volatility(data_aligned, results, path)
    figure_paths.append(path)

    # 图5: 回测净值曲线
    path = os.path.join(figures_dir, '5_backtest_results.png')
    plot_backtest_results(data_aligned, eval_results, path)
    figure_paths.append(path)

    # 图6: 回撤曲线
    path = os.path.join(figures_dir, '6_drawdown.png')
    plot_drawdown(data_aligned, eval_results, path)
    figure_paths.append(path)

    # 图7: 性能指标对比
    path = os.path.join(figures_dir, '7_performance_metrics.png')
    plot_performance_metrics(eval_results, path)
    figure_paths.append(path)

    # 图8: 汇总表格
    path = os.path.join(figures_dir, '8_summary_table.png')
    plot_summary_table(eval_results, selected, results, path)
    figure_paths.append(path)

    print(f"✓ 已生成 {len(figure_paths)} 张图表")

    # ===== 4. 生成 CSV/Excel 报告 =====
    print("\n[4/5] 生成表格报告...")

    # 创建报告 DataFrame
    report_data = {
        '指标': [
            '总收益率 (未套保)',
            '总收益率 (套保后)',
            '年化收益率 (未套保)',
            '年化收益率 (套保后)',
            '波动率 (未套保)',
            '波动率 (套保后)',
            '最大回撤 (未套保)',
            '最大回撤 (套保后)',
            '夏普比率 (未套保)',
            '夏普比率 (套保后)',
            'VaR 95% (未套保)',
            'VaR 95% (套保后)',
            'CVaR 95% (未套保)',
            'CVaR 95% (套保后)',
            '方差降低比例',
            'Ederington 指标',
            '套保效果评级'
        ],
        '数值': [
            f"{metrics['total_return_unhedged']:.2%}",
            f"{metrics['total_return_hedged']:.2%}",
            f"{metrics['annual_return_unhedged']:.2%}",
            f"{metrics['annual_return_hedged']:.2%}",
            f"{metrics['std_unhedged']:.4f}",
            f"{metrics['std_hedged']:.4f}",
            f"{metrics['max_dd_unhedged']:.2%}",
            f"{metrics['max_dd_hedged']:.2%}",
            f"{metrics['sharpe_unhedged']:.4f}",
            f"{metrics['sharpe_hedged']:.4f}",
            f"{metrics['var_95_unhedged']:.4f}",
            f"{metrics['var_95_hedged']:.4f}",
            f"{metrics['cvar_95_unhedged']:.4f}",
            f"{metrics['cvar_95_hedged']:.4f}",
            f"{metrics['variance_reduction']:.2%}",
            f"{metrics['ederington']:.4f}",
            metrics['rating']
        ]
    }

    report_df = pd.DataFrame(report_data)

    # 保存 CSV
    csv_path = os.path.join(output_dir, 'backtest_report.csv')
    report_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    # 保存 Excel（多工作表）
    excel_path = os.path.join(output_dir, 'backtest_report.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        report_df.to_excel(writer, sheet_name='回测报告', index=False)

        # 配置信息工作表
        summary_data = {
            '项目': ['数据起止日期', '样本量', '相关系数窗口', '税点调整'],
            '数值': [
                f"{data['date'].min()} 至 {data['date'].max()}",
                len(data),
                config.corr_window,
                f"{config.tax_rate:.1%}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='配置信息', index=False)

        # GARCH 参数工作表
        if 'params_spot' in results and 'params_futures' in results:
            spot_params = pd.DataFrame(list(results['params_spot'].items()),
                                      columns=['参数', '现货'])
            futures_params = pd.DataFrame(list(results['params_futures'].items()),
                                         columns=['参数', '期货'])
            pd.merge(spot_params, futures_params, on='参数', how='outer').to_excel(
                writer, sheet_name='GARCH参数', index=False
            )

    print(f"✓ CSV报告: {csv_path}")
    print(f"✓ Excel报告: {excel_path}")

    # ===== 5. 生成 HTML 报告 =====
    print("\n[5/5] 生成 HTML 报告...")

    html_path = os.path.join(output_dir, 'report.html')
    generate_html_report(data_aligned, eval_results, selected, results, html_path)

    print(f"✓ HTML报告: {html_path}")

    # ===== 汇总返回 =====
    print("\n" + "=" * 60)
    print("✓ 报告生成完成！")
    print("=" * 60)
    print(f"\n📁 输出目录: {output_dir}")
    print(f"  - {html_path}  ⭐ (推荐查看)")
    print(f"  - {figures_dir}/ (所有图表)")
    print(f"  - {csv_path}")
    print(f"  - {excel_path}")

    return {
        'metrics': metrics,
        'figures': figure_paths,
        'html_path': html_path,
        'csv_path': csv_path,
        'excel_path': excel_path,
        'output_dir': output_dir
    }
