#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ECM-DCC-GARCH模型套保回测脚本

使用方法：
    python run_ecm_dcc_garch.py

功能：
    - 读取处理后的期现货数据
    - 运行ECM-DCC-GARCH模型（综合模型：协整+动态相关性）
    - 执行滚动回测（6周期 × 90天）
    - 生成完整的HTML/Excel/CSV报告

模型特点：
    - 结合ECM（误差修正模型）和DCC-GARCH
    - 考虑现货与期货的长期均衡关系（协整）
    - 捕捉时变相关性和波动
    - 学术界和实务界公认的最强模型

输出目录：outputs/<品种>_ECM_DCC_GARCH_<年份>/
"""

import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from model_ecm_dcc_garch import fit_ecm_dcc_garch
from basic_garch_analyzer.rolling_backtest import (
    run_rolling_backtest,
    plot_rolling_nav_curve,
    plot_rolling_drawdown,
    generate_rolling_backtest_report
)
from basic_garch_analyzer.report_generator import (
    generate_html_report,
    plot_price_series,
    plot_returns,
    plot_hedge_ratio,
    plot_performance_metrics,
    plot_summary_table
)

# ==================== 配置参数 ====================

# 数据文件路径
DATA_FILE = 'outputs/hot_coil_2021_latest.xlsx'  # 修改为您的数据文件路径

# 输出目录配置
OUTPUT_DIR = 'outputs/热卷ECM_DCC_GARCH_2021_完整回测'  # 修改为想要的输出目录名

# 数据列配置
SPOT_COL = 'spot'      # 现货价格列名
FUTURES_COL = 'futures'  # 期货价格列名

# ECM-DCC-GARCH模型参数
ECM_DCC_CONFIG = {
    'p': 1,                    # GARCH(p,q) - p参数
    'q': 1,                    # GARCH(p,q) - q参数
    'coint_window': 120,       # 协整关系滚动窗口（天）
    'tax_adjust': True,        # 是否进行税点调整
    'coupling_method': 'ect-garch'  # ECT与GARCH耦合方法
}

# 滚动回测参数
BACKTEST_CONFIG = {
    'n_periods': 6,     # 回测周期数
    'window_days': 90,  # 每个周期天数
    'seed': 42,         # 随机种子（保持结果可复现）
    'tax_rate': 0.13    # 增值税率（13%）
}

# 数据过滤参数（可选）
START_DATE = '2021-01-01'  # 起始日期（None表示使用全部数据）
END_DATE = None            # 结束日期（None表示使用全部数据）

# ==================== 主程序 ====================

def main():
    """主程序"""

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
    plt.rcParams['axes.unicode_minus'] = False

    print("=" * 60)
    print("ECM-DCC-GARCH模型套保回测")
    print("=" * 60)

    # 1. 读取数据
    print("\n[1/7] 正在读取数据...")
    print(f"数据文件: {DATA_FILE}")

    if not os.path.exists(DATA_FILE):
        print(f"❌ 错误：数据文件不存在 - {DATA_FILE}")
        print("\n请检查数据文件路径是否正确！")
        return

    data = pd.read_excel(DATA_FILE)

    # 检查日期列
    if 'date' in data.columns:
        data['date'] = pd.to_datetime(data['date'])
        if START_DATE:
            data = data[data['date'] >= START_DATE]
        if END_DATE:
            data = data[data['date'] <= END_DATE]
        # 不要设置date为index，保持为普通列

    print(f"✓ 数据加载成功")
    print(f"  - 样本量: {len(data)} 天")
    if 'date' in data.columns:
        print(f"  - 起始日期: {data['date'].iloc[0].strftime('%Y-%m-%d')}")
        print(f"  - 结束日期: {data['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # 检查数据列
    if SPOT_COL not in data.columns:
        print(f"❌ 错误：数据中缺少 '{SPOT_COL}' 列")
        print(f"  可用的列: {list(data.columns)}")
        return

    if FUTURES_COL not in data.columns:
        print(f"❌ 错误：数据中缺少 '{FUTURES_COL}' 列")
        print(f"  可用的列: {list(data.columns)}")
        return

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/figures', exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/model_results', exist_ok=True)

    # 2. ECM-DCC-GARCH模型拟合
    print("\n[2/7] 正在拟合ECM-DCC-GARCH模型...")
    print(f"  - GARCH参数: ({ECM_DCC_CONFIG['p']}, {ECM_DCC_CONFIG['q']})")
    print(f"  - 协整窗口: {ECM_DCC_CONFIG['coint_window']} 天")
    print(f"  - 税点调整: {'是' if ECM_DCC_CONFIG['tax_adjust'] else '否'}")
    print(f"  - 耦合方法: {ECM_DCC_CONFIG['coupling_method']}")

    # 准备数据（添加date列）
    data_copy = data.reset_index()
    data_copy['date'] = data_copy['date']

    try:
        model_results = fit_ecm_dcc_garch(
            data_copy,
            p=ECM_DCC_CONFIG['p'],
            q=ECM_DCC_CONFIG['q'],
            output_dir=f'{OUTPUT_DIR}/model_results',
            coint_window=ECM_DCC_CONFIG['coint_window']
        )
    except Exception as e:
        print(f"❌ 错误：模型拟合失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 显示模型结果
    gamma = model_results['ecm_params'].get('gamma', None)
    h_base = model_results['ecm_params'].get('h_ecm', None)
    rho_mean = model_results.get('dcc_params', {}).get('rho_mean', None)
    h_mean = model_results['h_actual'].mean()

    print(f"✓ 模型拟合成功")
    print(f"  - 误差修正系数 γ = {gamma:.3f} {'✓ (反向修正)' if gamma and gamma < 0 else '✗ (需要检查)'}")
    print(f"  - 基础套保比例 h = {h_base:.3f}" if h_base else "  - 基础套保比例: 未提供")
    print(f"  - 动态相关系数均值 = {rho_mean:.4f}" if rho_mean else "  - 动态相关系数: 未提供")
    print(f"  - 套保比例均值 = {h_mean:.4f}")

    # 3. 滚动回测
    print("\n[3/7] 正在进行滚动回测...")
    print(f"  - 回测周期: {BACKTEST_CONFIG['n_periods']} 个")
    print(f"  - 周期长度: {BACKTEST_CONFIG['window_days']} 天")
    print(f"  - 税率: {BACKTEST_CONFIG['tax_rate']*100}%")

    try:
        rolling_results = run_rolling_backtest(
            data=data,
            hedge_ratios=model_results['h_actual'],
            n_periods=BACKTEST_CONFIG['n_periods'],
            window_days=BACKTEST_CONFIG['window_days'],
            seed=BACKTEST_CONFIG['seed'],
            tax_rate=BACKTEST_CONFIG['tax_rate']
        )
    except Exception as e:
        print(f"❌ 错误：滚动回测失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    print(f"✓ 滚动回测完成")
    print(f"  - 平均收益率（未套保）: {rolling_results['avg_return_unhedged']*100:.2f}%")
    print(f"  - 平均收益率（套保后）: {rolling_results['avg_return_hedged']*100:.2f}%")
    print(f"  - 平均方差降低: {rolling_results['avg_variance_reduction']*100:.2f}%")

    # 4. 生成图表
    print("\n[4/7] 正在生成图表...")

    figures_dir = f'{OUTPUT_DIR}/figures'

    try:
        # 图1：价格走势
        print("  - 生成图1: 价格走势...")
        plot_price_series(
            data,
            spot_col=SPOT_COL,
            futures_col=FUTURES_COL,
            save_path=f'{figures_dir}/1_price_series.png'
        )

        # 图2：收益率分布
        print("  - 生成图2: 收益率分布...")
        plot_returns(
            data,
            spot_col=SPOT_COL,
            futures_col=FUTURES_COL,
            save_path=f'{figures_dir}/2_returns.png'
        )

        # 图3：套保比例时变
        print("  - 生成图3: 套保比例时变...")
        plot_hedge_ratio(
            model_results['h_actual'],
            save_path=f'{figures_dir}/3_hedge_ratio.png'
        )

        # 图4：波动率（ECM-DCC-GARCH跳过）
        print("  - 跳过图4: 波动率（ECM-DCC-GARCH模型输出格式不同）")

        # 图5：净值曲线（带套保比例）
        print("  - 生成图5: 净值曲线（6周期 × 双坐标轴）...")
        plot_rolling_nav_curve(
            rolling_results['periods'],
            save_path=f'{figures_dir}/5_backtest_results.png'
        )

        # 图6：回撤分析（带套保比例）
        print("  - 生成图6: 回撤分析（6周期 × 双坐标轴）...")
        plot_rolling_drawdown(
            rolling_results['periods'],
            save_path=f'{figures_dir}/6_drawdown.png'
        )

        # 图7：性能指标对比
        print("  - 生成图7: 性能指标对比...")
        eval_results = {
            'metrics': {
                'mean_unhedged': rolling_results['avg_return_unhedged'] / 252,
                'mean_hedged': rolling_results['avg_return_hedged'] / 252,
                'std_unhedged': rolling_results['all_returns_unhedged'].std(),
                'std_hedged': rolling_results['all_returns_hedged'].std(),
                'sharpe_unhedged': rolling_results['avg_sharpe_unhedged'],
                'sharpe_hedged': rolling_results['avg_sharpe_hedged'],
                'max_dd_unhedged': rolling_results['avg_max_dd_unhedged'],
                'max_dd_hedged': rolling_results['avg_max_dd_hedged'],
                'var_95_unhedged': rolling_results['all_returns_unhedged'].quantile(0.05),
                'var_95_hedged': rolling_results['all_returns_hedged'].quantile(0.05),
                'cvar_95_unhedged': rolling_results['all_returns_unhedged'][
                    rolling_results['all_returns_unhedged'] <= rolling_results['all_returns_unhedged'].quantile(0.05)
                ].mean(),
                'cvar_95_hedged': rolling_results['all_returns_hedged'][
                    rolling_results['all_returns_hedged'] <= rolling_results['all_returns_hedged'].quantile(0.05)
                ].mean(),
            }
        }
        plot_performance_metrics(
            eval_results,
            save_path=f'{figures_dir}/7_performance_metrics.png'
        )

        # 图8：汇总表格
        print("  - 生成图8: 汇总表格...")
        plot_summary_table(
            eval_results,
            save_path=f'{figures_dir}/8_summary_table.png'
        )

        print(f"✓ 图表生成完成（7张）")

    except Exception as e:
        print(f"❌ 错误：图表生成失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 5. 生成Excel和CSV报告
    print("\n[5/7] 正在生成Excel和CSV报告...")

    try:
        generate_rolling_backtest_report(
            data,
            rolling_results,
            output_dir=OUTPUT_DIR,
            generate_html=False
        )
        print(f"✓ 报告已生成: {OUTPUT_DIR}/")

    except Exception as e:
        print(f"❌ 错误：Excel/CSV报告生成失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 6. 生成HTML报告
    print("\n[6/7] 正在生成HTML报告...")

    try:
        generate_html_report(
            data=data,
            model_results=model_results,
            backtest_results=rolling_results,
            output_path=f'{OUTPUT_DIR}/report.html',
            spot_col=SPOT_COL,
            futures_col=FUTURES_COL,
            model_type='ECM-DCC-GARCH',
            ecm_params={
                'gamma': gamma,
                'h_base': h_base,
                'coint_window': ECM_DCC_CONFIG['coint_window']
            },
            dcc_params={
                'rho_mean': rho_mean,
                'rho_std': model_results.get('dcc_params', {}).get('rho_std', None)
            }
        )
        print(f"✓ HTML报告: {os.path.join(OUTPUT_DIR, 'report.html')}")

    except Exception as e:
        print(f"❌ 错误：HTML报告生成失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 7. 完成
    print("\n[7/7] 回测完成！")
    print("=" * 60)
    print(f"📊 报告位置: {OUTPUT_DIR}/")
    print(f"  - HTML报告: {os.path.join(OUTPUT_DIR, 'report.html')}")
    print(f"  - Excel报告: {os.path.join(OUTPUT_DIR, 'rolling_backtest_report.xlsx')}")
    print(f"  - CSV报告: {os.path.join(OUTPUT_DIR, 'rolling_backtest_report.csv')}")
    print(f"  - 模型结果: {os.path.join(OUTPUT_DIR, 'model_results/h_ecm_dcc_garch.csv')}")
    print(f"  - 图表文件: {figures_dir}/ (7张)")

    # 检查核心指标
    print("\n📈 核心指标:")
    print(f"  - 方差降低比例: {rolling_results['avg_variance_reduction']*100:.2f}%")
    print(f"  - Ederington有效性: {rolling_results['avg_variance_reduction']:.4f}")
    print(f"  - 套保后夏普比率: {rolling_results['avg_sharpe_hedged']:.4f}")
    print(f"  - 套保后最大回撤: {rolling_results['avg_max_dd_hedged']*100:.2f}%")

    print("\n✅ ECM-DCC-GARCH回测完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
