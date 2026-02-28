#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DCC-GARCH模型套保回测脚本（6个随机周期）

使用方法：
    python run_dcc_garch_rolling.py

功能：
    - 读取处理后的期现货数据
    - 运行DCC-GARCH模型（动态条件相关多元GARCH）
    - 执行滚动回测（6周期 × 90天）
    - 生成完整的HTML/Excel/CSV报告

模型特点：
    - 捕捉现货与期货的时变相关性
    - 动态套保比例随相关性变化
    - 使用mgarch库进行DCC-GARCH建模

输出目录：outputs/<品种>_DCC_GARCH_<年份>_滚动回测/
"""

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from model_dcc_garch import fit_dcc_garch
from basic_garch_analyzer.rolling_backtest import (
    run_rolling_backtest,
    plot_rolling_nav_curve,
    plot_rolling_drawdown
)
from basic_garch_analyzer.report_generator import (
    plot_price_series,
    plot_returns,
    plot_hedge_ratio,
    plot_performance_metrics,
    plot_summary_table
)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

# ==================== 配置参数 ====================

# 数据文件路径
DATA_FILE = 'outputs/hot_coil_2021_latest.xlsx'

# 输出目录配置（新目录，不覆盖之前的）
OUTPUT_DIR = 'outputs/热卷DCC_GARCH_2021_滚动回测'

# DCC-GARCH模型参数
DCC_CONFIG = {
    'p': 1,           # GARCH(p,q) - p参数
    'q': 1,           # GARCH(p,q) - q参数
    'dist': 't'       # 分布假设（t分布或正态分布'normal'）
}

# 滚动回测参数
BACKTEST_CONFIG = {
    'n_periods': 6,     # 回测周期数
    'window_days': 90,  # 每个周期天数
    'seed': 42,         # 随机种子（保持结果可复现）
    'tax_rate': 0.13    # 增值税率（13%）
}

# ==================== 主程序 ====================

def main():
    """主程序"""

    print("=" * 60)
    print("DCC-GARCH模型套保回测（6个随机周期）")
    print("=" * 60)

    # 1. 读取数据
    print("\n[1/7] 正在读取数据...")
    print(f"数据文件: {DATA_FILE}")

    data = pd.read_excel(DATA_FILE)

    if 'date' in data.columns:
        data['date'] = pd.to_datetime(data['date'])

    print(f"✓ 数据加载成功")
    print(f"  - 样本量: {len(data)} 天")
    if 'date' in data.columns:
        print(f"  - 起始日期: {data['date'].iloc[0].strftime('%Y-%m-%d')}")
        print(f"  - 结束日期: {data['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/figures', exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/model_results', exist_ok=True)

    # 2. DCC-GARCH模型拟合
    print("\n[2/7] 正在拟合DCC-GARCH模型...")
    print(f"  - GARCH参数: ({DCC_CONFIG['p']}, {DCC_CONFIG['q']})")
    print(f"  - 分布假设: {DCC_CONFIG['dist']}")

    # DCC-GARCH需要收益率数据，计算收益率
    data_dcc = data.copy()
    data_dcc['r_s'] = np.log(data_dcc['spot'] / data_dcc['spot'].shift(1))
    data_dcc['r_f'] = np.log(data_dcc['futures'] / data_dcc['futures'].shift(1))
    data_dcc = data_dcc.dropna()
    data_dcc['date'] = data['date'].iloc[1:].reset_index(drop=True)

    model_results = fit_dcc_garch(
        data_dcc,
        p=DCC_CONFIG['p'],
        q=DCC_CONFIG['q'],
        output_dir=f'{OUTPUT_DIR}/model_results',
        dist=DCC_CONFIG['dist']
    )

    h_mean = model_results['h_actual'].mean()
    rho_mean = model_results['rho_t'].mean()

    print(f"✓ 模型拟合成功")
    print(f"  - 动态相关系数均值 = {rho_mean:.4f}")
    print(f"  - 套保比例均值 = {h_mean:.4f}")

    # 3. 滚动回测
    print("\n[3/7] 正在进行滚动回测...")
    print(f"  - 回测周期: {BACKTEST_CONFIG['n_periods']} 个")
    print(f"  - 周期长度: {BACKTEST_CONFIG['window_days']} 天")
    print(f"  - 税率: {BACKTEST_CONFIG['tax_rate']*100}%")

    # 对齐套保比例
    h_aligned_full = np.full(len(data), np.nan)
    h_aligned_full[1:] = model_results['h_actual']

    rolling_results = run_rolling_backtest(
        data=data,
        hedge_ratios=h_aligned_full,
        n_periods=BACKTEST_CONFIG['n_periods'],
        window_days=BACKTEST_CONFIG['window_days'],
        seed=BACKTEST_CONFIG['seed'],
        tax_rate=BACKTEST_CONFIG['tax_rate']
    )

    print(f"✓ 滚动回测完成")
    print(f"  - 平均收益率（未套保）: {rolling_results['avg_return_unhedged']*100:.2f}%")
    print(f"  - 平均收益率（套保后）: {rolling_results['avg_return_hedged']*100:.2f}%")
    print(f"  - 平均方差降低: {rolling_results['avg_variance_reduction']*100:.2f}%")

    # 4. 生成图表
    print("\n[4/7] 正在生成图表...")

    figures_dir = f'{OUTPUT_DIR}/figures'

    try:
        # 准备绘图所需数据
        plot_data = data.copy()
        plot_data['spread'] = plot_data['spot'] - plot_data['futures']

        # 图1：价格走势
        print("  - 生成图1: 价格走势...")
        plot_price_series(plot_data, output_path=f'{figures_dir}/1_price_series.png')

        # 图2：收益率分布
        print("  - 生成图2: 收益率分布...")
        plot_returns(data_dcc, output_path=f'{figures_dir}/2_returns.png')

        # 图3：套保比例时变
        print("  - 生成图3: 套保比例时变...")
        hedge_results = {
            'h_theoretical': pd.Series(model_results['h_theoretical'], index=data_dcc['date'].values),
            'h_actual': pd.Series(model_results['h_actual'], index=data_dcc['date'].values),
            'rolling_corr': pd.Series(model_results['rho_t'], index=data_dcc['date'].values),
            'sigma_s': pd.Series(model_results['sigma_s'], index=data_dcc['date'].values),
            'sigma_f': pd.Series(model_results['sigma_f'], index=data_dcc['date'].values)
        }
        plot_hedge_ratio(data_dcc, hedge_results, output_path=f'{figures_dir}/3_hedge_ratio.png')

        # 图4：波动率（跳过，DCC-GARCH输出格式不同）
        print("  - 跳过图4: 波动率（DCC-GARCH模型输出格式不同）")

        # 图5：净值曲线（6个周期子图）
        print("  - 生成图5: 净值曲线（6周期 × 双坐标轴）...")
        plot_rolling_nav_curve(
            rolling_results,
            output_path=f'{figures_dir}/5_backtest_results.png'
        )

        # 图6：回撤分析（6个周期子图）
        print("  - 生成图6: 回撤分析（6周期 × 双坐标轴）...")
        plot_rolling_drawdown(
            rolling_results,
            output_path=f'{figures_dir}/6_drawdown.png'
        )

        # 图7：性能指标对比
        print("  - 生成图7: 性能指标对比...")

        # 构建评估结果
        all_returns_unhedged = []
        all_returns_hedged = []

        for period_result in rolling_results['period_results']:
            cum_unhedged = period_result['cumulative_unhedged']
            cum_hedged = period_result['cumulative_hedged']
            if len(cum_unhedged) > 1:
                returns_u = np.diff(cum_unhedged) / cum_unhedged[:-1]
                returns_h = np.diff(cum_hedged) / cum_hedged[:-1]
                all_returns_unhedged.extend(returns_u.tolist())
                all_returns_hedged.extend(returns_h.tolist())

        all_returns_unhedged = np.array(all_returns_unhedged)
        all_returns_hedged = np.array(all_returns_hedged)

        eval_results = {
            'metrics': {
                'mean_unhedged': rolling_results['avg_return_unhedged'] / 252,
                'mean_hedged': rolling_results['avg_return_hedged'] / 252,
                'std_unhedged': all_returns_unhedged.std(),
                'std_hedged': all_returns_hedged.std(),
                'sharpe_unhedged': rolling_results['period_results'][0]['sharpe_unhedged'],
                'sharpe_hedged': rolling_results['period_results'][0]['sharpe_hedged'],
                'variance_reduction': rolling_results['avg_variance_reduction'],
                'ederington': rolling_results['avg_variance_reduction'],
                'max_dd_unhedged': rolling_results['period_results'][0]['max_dd_unhedged'],
                'max_dd_hedged': rolling_results['period_results'][0]['max_dd_hedged'],
                'var_95_unhedged': np.percentile(all_returns_unhedged, 5),
                'var_95_hedged': np.percentile(all_returns_hedged, 5),
                'cvar_95_unhedged': all_returns_unhedged[all_returns_unhedged <= np.percentile(all_returns_unhedged, 5)].mean(),
                'cvar_95_hedged': all_returns_hedged[all_returns_hedged <= np.percentile(all_returns_hedged, 5)].mean(),
            },
            'returns_unhedged': all_returns_unhedged,
            'returns_hedged': all_returns_hedged,
            'drawdown_series': np.concatenate([p['drawdown'] for p in rolling_results['period_results']]),
            'start_date': data['date'].iloc[0].strftime('%Y-%m-%d'),
            'end_date': data['date'].iloc[-1].strftime('%Y-%m-%d')
        }

        plot_performance_metrics(
            eval_results,
            output_path=f'{figures_dir}/7_performance_metrics.png'
        )

        # 图8：汇总表格
        print("  - 生成图8: 汇总表格...")
        model_params_for_table = {
            'model_name': 'DCC-GARCH',
            'corr_window': 120,
            'tax_rate': BACKTEST_CONFIG['tax_rate']
        }
        plot_summary_table(
            eval_results,
            {'spot': 'spot', 'futures': 'futures'},
            model_params_for_table,
            output_path=f'{figures_dir}/8_summary_table.png'
        )

        print(f"✓ 图表生成完成（7张）")

    except Exception as e:
        import traceback
        print(f"⚠️ 图表生成失败: {e}")
        traceback.print_exc()

    # 5. 生成CSV和HTML报告
    print("\n[5/7] 正在生成CSV和HTML报告...")

    try:
        # 生成CSV
        results_df = pd.DataFrame({
            'period': range(1, len(rolling_results['period_results']) + 1),
            'start_date': [p['start_date'].strftime('%Y-%m-%d') if hasattr(p['start_date'], 'strftime') else p['start_date'] for p in rolling_results['period_results']],
            'end_date': [p['end_date'].strftime('%Y-%m-%d') if hasattr(p['end_date'], 'strftime') else p['end_date'] for p in rolling_results['period_results']],
            'return_unhedged': [p['total_return_unhedged'] for p in rolling_results['period_results']],
            'return_hedged': [p['total_return_hedged'] for p in rolling_results['period_results']],
            'variance_reduction': [p['variance_reduction'] for p in rolling_results['period_results']],
            'sharpe_unhedged': [p['sharpe_unhedged'] for p in rolling_results['period_results']],
            'sharpe_hedged': [p['sharpe_hedged'] for p in rolling_results['period_results']],
            'avg_hedge_ratio': [p['avg_hedge_ratio'] for p in rolling_results['period_results']]
        })
        results_df.to_csv(f'{OUTPUT_DIR}/rolling_backtest_report.csv', index=False, encoding='utf-8-sig')
        print(f"  ✓ CSV报告: {OUTPUT_DIR}/rolling_backtest_report.csv")

        # 生成HTML报告
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DCC-GARCH模型套保回测报告</title>
    <style>
        body {{
            font-family: Arial, 'Microsoft YaHei', sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin-top: 30px;
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
        .metric {{
            display: inline-block;
            margin: 10px;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 5px;
            width: 200px;
        }}
        .metric-title {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            color: #3498db;
            font-weight: bold;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .period-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .period-card {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            background-color: #f9f9f9;
        }}
        .period-card h3 {{
            margin-top: 0;
            color: #3498db;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DCC-GARCH模型套保回测报告</h1>

        <h2>📊 数据配置</h2>
        <table>
            <tr><th>项目</th><th>值</th></tr>
            <tr><td>数据文件</td><td>{DATA_FILE}</td></tr>
            <tr><td>样本量</td><td>{len(data)} 天</td></tr>
            <tr><td>起始日期</td><td>{data['date'].iloc[0].strftime('%Y-%m-%d')}</td></tr>
            <tr><td>结束日期</td><td>{data['date'].iloc[-1].strftime('%Y-%m-%d')}</td></tr>
        </table>

        <h2>🎯 模型参数</h2>
        <table>
            <tr><th>参数</th><th>值</th></tr>
            <tr><td>模型类型</td><td>DCC-GARCH</td></tr>
            <tr><td>GARCH参数</td><td>({DCC_CONFIG['p']}, {DCC_CONFIG['q']})</td></tr>
            <tr><td>分布假设</td><td>{DCC_CONFIG['dist']}</td></tr>
            <tr><td>税率</td><td>{BACKTEST_CONFIG['tax_rate']*100}%</td></tr>
        </table>

        <h2>📈 模型结果</h2>
        <table>
            <tr><th>指标</th><th>值</th></tr>
            <tr><td>动态相关系数均值</td><td>{rho_mean:.4f}</td></tr>
            <tr><td>套保比例均值</td><td>{h_mean:.4f}</td></tr>
        </table>

        <h2>⭐ 核心指标</h2>
        <div class="metric">
            <div class="metric-title">方差降低比例</div>
            <div class="metric-value">{rolling_results['avg_variance_reduction']*100:.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-title">Ederington有效性</div>
            <div class="metric-value">{rolling_results['avg_variance_reduction']:.4f}</div>
        </div>
        <div class="metric">
            <div class="metric-title">平均收益率（未套保）</div>
            <div class="metric-value">{rolling_results['avg_return_unhedged']*100:.2f}%</div>
        </div>
        <div class="metric">
            <div class="metric-title">平均收益率（套保后）</div>
            <div class="metric-value">{rolling_results['avg_return_hedged']*100:.2f}%</div>
        </div>

        <h2>📊 图表</h2>
        <h3>价格走势</h3>
        <img src="figures/1_price_series.png" alt="价格走势图">

        <h3>收益率分布</h3>
        <img src="figures/2_returns.png" alt="收益率分布图">

        <h3>套保比例时变</h3>
        <img src="figures/3_hedge_ratio.png" alt="套保比例时变图">

        <h3>6个周期净值曲线</h3>
        <img src="figures/5_backtest_results.png" alt="6个周期净值曲线">

        <h3>6个周期回撤分析</h3>
        <img src="figures/6_drawdown.png" alt="6个周期回撤分析">

        <h2>📋 6个回测周期详细结果</h2>
        <table>
            <tr>
                <th>周期</th>
                <th>起始日期</th>
                <th>结束日期</th>
                <th>未套保收益率</th>
                <th>套保收益率</th>
                <th>方差降低</th>
                <th>平均套保比例</th>
            </tr>
"""

        for i, p in enumerate(rolling_results['period_results'], 1):
            html_content += f"""
            <tr>
                <td>{i}</td>
                <td>{p['start_date'].strftime('%Y-%m-%d')}</td>
                <td>{p['end_date'].strftime('%Y-%m-%d')}</td>
                <td>{p['total_return_unhedged']*100:.2f}%</td>
                <td>{p['total_return_hedged']*100:.2f}%</td>
                <td>{p['variance_reduction']*100:.2f}%</td>
                <td>{p['avg_hedge_ratio']:.4f}</td>
            </tr>
"""

        html_content += f"""
        </table>

        <h2>📁 下载文件</h2>
        <table>
            <tr><th>文件</th><th>说明</th></tr>
            <tr><td><a href="rolling_backtest_report.csv">rolling_backtest_report.csv</a></td><td>6个周期详细数据（CSV格式）</td></tr>
            <tr><td><a href="model_results/h_dcc_garch.csv">model_results/h_dcc_garch.csv</a></td><td>DCC-GARCH模型套保比例时序数据</td></tr>
        </table>

        <div style="text-align: center; margin-top: 50px; color: #7f8c8d;">
            <p>报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>DCC-GARCH套保策略分析系统</p>
        </div>
    </div>
</body>
</html>
"""

        with open(f'{OUTPUT_DIR}/report.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  ✓ HTML报告: {OUTPUT_DIR}/report.html")

    except Exception as e:
        import traceback
        print(f"⚠️ 报告生成失败: {e}")
        traceback.print_exc()

    # 6. 完成
    print("\n[6/6] 回测完成！")
    print("=" * 60)
    print(f"📊 报告位置: {OUTPUT_DIR}/")
    print(f"  - HTML报告: {OUTPUT_DIR}/report.html")
    print(f"  - CSV报告: {OUTPUT_DIR}/rolling_backtest_report.csv")
    print(f"  - CSV报告: {OUTPUT_DIR}/rolling_backtest_report.csv")
    print(f"  - 模型结果: {OUTPUT_DIR}/model_results/h_dcc_garch.csv")
    print(f"  - 图表文件: {figures_dir}/ (7张)")

    print("\n📈 核心指标:")
    print(f"  - 方差降低比例: {rolling_results['avg_variance_reduction']*100:.2f}%")
    print(f"  - Ederington有效性: {rolling_results['avg_variance_reduction']:.4f}")
    print(f"  - 动态相关系数: {rho_mean:.4f}")
    print(f"  - 套保比例均值: {h_mean:.4f}")

    print("\n6个回测周期:")
    for i, p in enumerate(rolling_results['period_results'], 1):
        print(f"  周期{i}: {p['start_date'].date()} → {p['end_date'].date()}, "
              f"方差降低={p['variance_reduction']*100:.2f}%, "
              f"套保收益率={p['total_return_hedged']*100:.2f}%")

    print("\n✅ DCC-GARCH回测完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
