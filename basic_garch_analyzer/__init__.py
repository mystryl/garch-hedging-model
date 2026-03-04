"""
Basic GARCH Analyzer - GARCH套保模型分析工具

支持：
- 作为Python库导入使用
- 作为命令行工具运行
- 自动生成完整的滚动回测分析报告（默认）

Example:
--------
作为库使用:
    >>> from basic_garch_analyzer import run_analysis
    >>> result = run_analysis('data.xlsx', '现货价格', '期货价格')

命令行使用:
    $ python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

使用全样本回测（备选）:
    >>> from basic_garch_analyzer import run_analysis, ModelConfig
    >>> config = ModelConfig(enable_rolling_backtest=False)
    >>> result = run_analysis('data.xlsx', '现货', '期货', config=config)
"""
import numpy as np
from basic_garch_analyzer.config import ModelConfig, create_config
from basic_garch_analyzer.data_loader import load_and_preprocess
from basic_garch_analyzer.basic_garch_model import fit_basic_garch, save_model_results
from basic_garch_analyzer.analyzer import evaluate_and_report
from basic_garch_analyzer.rolling_backtest import (
    run_rolling_backtest as _run_rolling_backtest,
    generate_rolling_backtest_report
)
from basic_garch_analyzer import report_generator

__version__ = '1.1.0'
__all__ = [
    'ModelConfig',
    'create_config',
    'load_and_preprocess',
    'fit_basic_garch',
    'save_model_results',
    # 'evaluate_and_report',  # 不再导出（保留作为备份）
    'run_analysis',
    # 'run_rolling_backtest'  # 已整合到 run_analysis 中
]


def run_analysis(
    excel_path: str,
    spot_col: str,
    futures_col: str,
    date_col: str = None,
    config: ModelConfig = None,
    interactive: bool = False,
    **kwargs
) -> dict:
    """
    一键运行完整分析流程

    Parameters:
    -----------
    excel_path : str
        Excel 文件路径
    spot_col : str
        现货价格列名
    futures_col : str
        期货价格列名
    date_col : str, optional
        日期列名（None则自动检测）
    config : ModelConfig, optional
        模型配置对象（None则使用默认配置）
    interactive : bool
        是否交互式选择列名
    **kwargs
        其他配置参数（用于覆盖 config）

    Returns:
    --------
    result : dict
        {
            'data': DataFrame,           # 预处理后的数据
            'model_results': dict,       # 模型拟合结果
            'report_info': dict          # 报告信息
        }

    Example:
    --------
    >>> # 使用默认配置
    >>> result = run_analysis('data.xlsx', '现货', '期货')
    >>>
    >>> # 自定义配置
    >>> config = ModelConfig(tax_rate=0.0, corr_window=60)
    >>> result = run_analysis('data.xlsx', '现货', '期货', config=config)
    """
    print("\n" + "=" * 70)
    print(" " * 15 + "Basic GARCH Analyzer")
    print(" " * 10 + "套保策略分析系统（滚动回测模式）")
    print("=" * 70)

    # 1. 准备配置
    if config is None:
        config = ModelConfig(**kwargs)
    else:
        # 合并 kwargs 覆盖
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

    print("\n📋 配置参数:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")

    # 2. 加载和预处理数据
    print("\n" + "=" * 70)
    # 计算最小数据量要求
    min_required = max(config.window_days * 2, config.corr_window)

    # 从 kwargs 中提取 skip_rows（如果有）
    skip_rows = kwargs.get('skip_rows', 0)

    data, selected = load_and_preprocess(
        file_path=excel_path,
        date_col=date_col,
        spot_col=spot_col,
        futures_col=futures_col,
        output_file=None,
        interactive=interactive,
        min_required=min_required,
        skip_rows=skip_rows
    )

    # 3. 拟合 GARCH 模型
    print("\n" + "=" * 70)
    model_results = fit_basic_garch(
        data,
        p=config.p,
        q=config.q,
        corr_window=config.corr_window,
        tax_rate=config.tax_rate
    )

    # 保存模型结果
    model_results_path = f"{config.output_dir}/model_results/h_basic_garch.csv"
    save_model_results(data, model_results, model_results_path)

    # ===== 4. 回测评估（滚动回测或全样本）=====
    print("\n" + "=" * 70)

    if config.enable_rolling_backtest:
        # 使用滚动回测
        print("运行滚动回测...")
        rolling_results = _run_rolling_backtest(
            data,
            model_results['h_final'],
            n_periods=config.n_periods,
            window_days=config.window_days,
            seed=config.backtest_seed,
            tax_rate=config.tax_rate
        )

        # 生成完整HTML报告（混合模式）
        # 图表1-4, 7-8来自report_generator.py，图表5-6来自rolling_backtest.py
        print("\n[生成HTML兼容报告]...")

        # 确保输出目录存在
        import os
        figures_dir = f"{config.output_dir}/figures"
        os.makedirs(figures_dir, exist_ok=True)

        # 生成图表1-4（价格、收益率、套保比例、波动率）
        print("\n[生成基础图表 1-4]...")
        report_generator.plot_price_series(data, f'{figures_dir}/1_price_series.png')
        report_generator.plot_returns(data, f'{figures_dir}/2_returns.png')
        report_generator.plot_hedge_ratio(data, model_results, f'{figures_dir}/3_hedge_ratio.png')
        report_generator.plot_volatility(data, model_results, f'{figures_dir}/4_volatility.png')

        # 生成图表5-6（滚动回测净值曲线和回撤曲线）
        print("\n[生成滚动回测图表 5-6]...")
        from basic_garch_analyzer.rolling_backtest import plot_rolling_nav_curve, plot_rolling_drawdown
        plot_rolling_nav_curve(rolling_results, f'{figures_dir}/5_backtest_results.png')
        plot_rolling_drawdown(rolling_results, f'{figures_dir}/6_drawdown.png')

        # 生成图表7（性能指标对比）
        print("\n[生成性能指标图表 7-8]...")
        # 构造性能指标数据（基于滚动回测结果）
        avg_std_unhedged = np.mean([r['std_unhedged'] for r in rolling_results['period_results']])
        avg_std_hedged = np.mean([r['std_hedged'] for r in rolling_results['period_results']])
        avg_sharpe_unhedged = np.mean([r['sharpe_unhedged'] for r in rolling_results['period_results']])
        avg_sharpe_hedged = np.mean([r['sharpe_hedged'] for r in rolling_results['period_results']])
        avg_max_dd_unhedged = np.mean([r['max_dd_unhedged'] for r in rolling_results['period_results']])
        avg_max_dd_hedged = rolling_results['avg_max_dd_hedged']

        eval_results_for_plot = {
            'metrics': {
                'variance_reduction': rolling_results['avg_variance_reduction'],
                'ederington': rolling_results['avg_variance_reduction'],  # Ederington指标 = 方差降低比例
                'mean_unhedged': rolling_results['avg_return_unhedged'] / 252,  # 日均值
                'mean_hedged': rolling_results['avg_return_hedged'] / 252,
                'var_unhedged': avg_std_unhedged ** 2,
                'var_hedged': avg_std_hedged ** 2,
                'std_unhedged': avg_std_unhedged,
                'std_hedged': avg_std_hedged,
                'sharpe_unhedged': avg_sharpe_unhedged,
                'sharpe_hedged': avg_sharpe_hedged,
                'max_dd_unhedged': avg_max_dd_unhedged,
                'max_dd_hedged': avg_max_dd_hedged,
                'var_95_unhedged': avg_std_unhedged * 1.65,  # 近似VaR
                'var_95_hedged': avg_std_hedged * 1.65,
                'cvar_95_unhedged': avg_std_unhedged * 2.0,  # 近似CVaR
                'cvar_95_hedged': avg_std_hedged * 2.0,
            }
        }

        # 由于plot_performance_metrics需要eval_results中的returns数据，我们需要构造一个简化版本
        # 这里我们生成一个简化的性能指标图
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 左图：收益率对比
        ax1 = axes[0]
        returns_u = [r['total_return_unhedged'] for r in rolling_results['period_results']]
        returns_h = [r['total_return_hedged'] for r in rolling_results['period_results']]
        x = np.arange(len(returns_u))
        width = 0.35
        ax1.bar(x - width/2, returns_u, width, label='未套保', color='red', alpha=0.7)
        ax1.bar(x + width/2, returns_h, width, label='套保后', color='green', alpha=0.7)
        ax1.set_ylabel('收益率', fontproperties=report_generator.CHINESE_FONT)
        ax1.set_title('各周期收益率对比', fontproperties=report_generator.CHINESE_FONT, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([f'周期{i+1}' for i in range(len(returns_u))], fontproperties=report_generator.CHINESE_FONT)
        ax1.legend(prop=report_generator.CHINESE_FONT)
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

        # 右图：汇总指标
        ax2 = axes[1]
        ax2.axis('tight')
        ax2.axis('off')
        table_data = [
            ['指标', '平均值'],
            ['收益率（未套保）', f"{rolling_results['avg_return_unhedged']:.2%}"],
            ['收益率（套保后）', f"{rolling_results['avg_return_hedged']:.2%}"],
            ['方差降低', f"{rolling_results['avg_variance_reduction']:.2%}"],
            ['夏普比率（套保后）', f"{avg_sharpe_hedged:.4f}"],
            ['最大回撤（套保后）', f"{avg_max_dd_hedged:.2%}"],
        ]
        table = ax2.table(cellText=table_data, cellLoc='left', loc='center', colWidths=[0.6, 0.4])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        for i in range(len(table_data)):
            if i == 0:
                table[(i, 0)].set_facecolor('#3498db')
                table[(i, 1)].set_facecolor('#3498db')
                table[(i, 0)].set_text_props(weight='bold', color='white')
                table[(i, 1)].set_text_props(weight='bold', color='white')
            elif i % 2 == 0:
                table[(i, 0)].set_facecolor('#f0f0f0')
                table[(i, 1)].set_facecolor('#f0f0f0')
        for key, cell in table.get_celld().items():
            cell.set_text_props(fontproperties=report_generator.CHINESE_FONT)
        ax2.set_title('滚动回测汇总', fontproperties=report_generator.CHINESE_FONT,
                      fontsize=12, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(f'{figures_dir}/7_performance_metrics.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 已保存: {figures_dir}/7_performance_metrics.png")

        # 生成图表8（汇总表格）
        print("\n[生成汇总表格 8]...")
        report_generator.plot_summary_table(
            {'metrics': eval_results_for_plot['metrics'],
             'start_date': data['date'].min().strftime('%Y-%m-%d'),
             'end_date': data['date'].max().strftime('%Y-%m-%d'),
             'returns_unhedged': np.concatenate([r['cumulative_unhedged'] for r in rolling_results['period_results']])},
            selected,
            {'model_name': f'Basic GARCH({config.p},{config.q}) - 滚动回测',
             'corr_window': config.corr_window,
             'tax_rate': config.tax_rate},
            f'{figures_dir}/8_summary_table.png'
        )

        # 生成HTML报告
        print("\n[生成HTML报告]...")
        # 构造HTML报告需要的eval_results结构
        eval_results = {
            'metrics': {
                'variance_reduction': rolling_results['avg_variance_reduction'],
                'ederington': rolling_results['avg_variance_reduction'],
                'mean_unhedged': rolling_results['avg_return_unhedged'] / 252,  # 日均收益率
                'mean_hedged': rolling_results['avg_return_hedged'] / 252,
                'std_unhedged': avg_std_unhedged,
                'std_hedged': avg_std_hedged,
                'sharpe_unhedged': avg_sharpe_unhedged,
                'sharpe_hedged': avg_sharpe_hedged,
                'max_dd_unhedged': avg_max_dd_unhedged,
                'max_dd_hedged': avg_max_dd_hedged,
                'var_95_unhedged': avg_std_unhedged * 1.65,
                'var_95_hedged': avg_std_hedged * 1.65,
                'cvar_95_unhedged': avg_std_unhedged * 2.0,
                'cvar_95_hedged': avg_std_hedged * 2.0,
            },
            'start_date': data['date'].min().strftime('%Y-%m-%d'),
            'end_date': data['date'].max().strftime('%Y-%m-%d'),
            'returns_unhedged': np.concatenate([r['cumulative_unhedged'] for r in rolling_results['period_results']]),
        }

        # 修改HTML模板，添加滚动回测说明
        html_path = f"{config.output_dir}/report.html"
        report_generator.generate_html_report(
            data, eval_results, selected,
            {'model_name': f'Basic GARCH({config.p},{config.q}) - 滚动回测模式',
             'corr_window': config.corr_window,
             'tax_rate': config.tax_rate},
            html_path
        )

        # 在HTML报告中添加滚动回测说明
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 在标题后插入滚动回测说明
        rolling_note = '''
        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;">
            <h3 style="color: #856404; margin-top: 0;">🔄 滚动回测模式</h3>
            <p style="color: #856404; margin-bottom: 0;">
                本报告采用<strong>滚动回测</strong>模式：随机抽取{0}个时间点，每个回测{1}天，避开交割月份（1、5、10月）。
                回测结果更贴近实际套保操作，图表5-6为滚动回测结果，其他图表基于全样本数据。
            </p>
        </div>
        '''.format(config.n_periods, config.window_days)

        # 在<h1>标签后插入
        html_content = html_content.replace(
            '<h1>Basic GARCH 套保策略回测报告</h1>',
            '<h1>Basic GARCH 套保策略回测报告</h1>' + rolling_note
        )

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  ✓ 已保存: {html_path}")

        # 生成Excel报告
        print("\n[生成Excel报告]...")
        report_info = generate_rolling_backtest_report(
            data,
            rolling_results,
            config.output_dir,
            generate_html=False  # 已经生成了HTML兼容图表，这里只需要Excel
        )
    else:
        # 使用全样本回测（备选方案）
        print("运行全样本回测...")
        report_info = evaluate_and_report(
            data=data,
            results=model_results,
            selected=selected,
            config=config,
            output_dir=config.output_dir
        )
    # ==================================================

    # 5. 输出摘要
    print("\n" + "=" * 70)
    print(" " * 20 + "分析完成")
    print("=" * 70)

    if config.enable_rolling_backtest:
        print(f"\n核心结果（滚动回测）:")
        print(f"  回测周期数: {rolling_results['n_periods']}")
        print(f"  平均收益率（套保后）: {rolling_results['avg_return_hedged']:.2%}")
        print(f"  平均方差降低: {rolling_results['avg_variance_reduction']:.2%}")
        print(f"  平均最大回撤: {rolling_results['avg_max_dd_hedged']:.2%}")
    else:
        metrics = report_info['metrics']
        print(f"\n核心结果（全样本回测）:")
        print(f"  方差降低比例: {metrics['variance_reduction']:.2%}")
        print(f"  夏普比率 (套保后): {metrics['sharpe_hedged']:.4f}")
        print(f"  最大回撤（套保后）: {metrics['max_dd_hedged']:.2%}")
        print(f"  套保效果评级: {metrics['rating']}")

    return {
        'data': data,
        'selected': selected,
        'model_results': model_results,
        'rolling_results' if config.enable_rolling_backtest else 'metrics':
            rolling_results if config.enable_rolling_backtest else report_info.get('metrics'),
        'report_info': report_info,
        'config': config
    }


def run_rolling_backtest(
    excel_path: str,
    spot_col: str,
    futures_col: str,
    date_col: str = None,
    config: ModelConfig = None,
    n_periods: int = 5,
    window_days: int = 60,
    seed: int = 42,
    output_dir: str = 'outputs/rolling_backtest'
) -> dict:
    """
    运行滚动回测（模拟实际套保周期）

    随机抽取多个时间点，每个回测固定天数，避开交割月份

    Parameters:
    -----------
    excel_path : str
        Excel 文件路径
    spot_col : str
        现货价格列名
    futures_col : str
        期货价格列名
    date_col : str, optional
        日期列名
    config : ModelConfig, optional
        模型配置对象
    n_periods : int
        回测周期数（默认5个）
    window_days : int
        每个周期天数（默认60天）
    seed : int
        随机种子
    output_dir : str
        输出目录

    Returns:
    --------
    result : dict
        回测结果
    """
    print("\n" + "=" * 70)
    print(" " * 15 + "Basic GARCH Analyzer")
    print(" " * 10 + "滚动回测分析系统")
    print("=" * 70)

    # 1. 准备配置
    if config is None:
        config = ModelConfig()

    print(f"\n📋 配置参数:")
    print(f"  回测周期数: {n_periods}")
    print(f"  每个周期: {window_days} 天")
    print(f"  避开交割月: 1月、5月、10月")
    print(f"  随机种子: {seed}")

    # 2. 加载和预处理数据
    print("\n" + "=" * 70)
    data, selected = load_and_preprocess(
        file_path=excel_path,
        date_col=date_col,
        spot_col=spot_col,
        futures_col=futures_col,
        output_file=None
    )

    # 3. 拟合 GARCH 模型
    print("\n" + "=" * 70)
    model_results = fit_basic_garch(
        data,
        p=config.p,
        q=config.q,
        corr_window=config.corr_window,
        tax_rate=config.tax_rate
    )

    # 4. 运行滚动回测
    print("\n" + "=" * 70)
    rolling_results = _run_rolling_backtest(
        data,
        model_results['h_final'],
        n_periods=n_periods,
        window_days=window_days,
        seed=seed,
        tax_rate=config.tax_rate
    )

    # 5. 生成报告
    print("\n" + "=" * 70)
    report_info = generate_rolling_backtest_report(
        data,
        rolling_results,
        output_dir
    )

    # 6. 输出摘要
    print("\n" + "=" * 70)
    print(" " * 20 + "滚动回测完成")
    print("=" * 70)

    print(f"\n核心结果:")
    print(f"  回测周期数: {rolling_results['n_periods']}")
    print(f"  平均收益率（套保后）: {rolling_results['avg_return_hedged']:.2%}")
    print(f"  平均方差降低: {rolling_results['avg_variance_reduction']:.2%}")
    print(f"  平均最大回撤: {rolling_results['avg_max_dd_hedged']:.2%}")

    return {
        'data': data,
        'selected': selected,
        'model_results': model_results,
        'rolling_results': rolling_results,
        'report_info': report_info,
        'config': config
    }
