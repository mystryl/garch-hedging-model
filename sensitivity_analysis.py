"""
参数敏感性分析：对比不同窗口大小的套保效果

测试不同协整窗口大小对ECM-GARCH模型的影响
"""

import pandas as pd
import numpy as np
import time
from datetime import datetime
from data_preprocessing import preprocess_data
from model_ecm_garch import fit_ecm_garch
from model_ecm_dcc_garch import fit_ecm_dcc_garch
from model_basic_garch import fit_basic_garch
import os

def calculate_effectiveness_metrics(data, h_actual):
    """
    计算套保效果指标

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s, r_f 的数据
    h_actual : np.array
        实际套保比例

    Returns:
    --------
    dict : 包含各项指标的字典
    """
    r_s = data['r_s'].values
    r_f = data['r_f'].values

    # 对齐长度
    min_len = min(len(r_s), len(h_actual))
    r_s_aligned = r_s[:min_len]
    r_f_aligned = r_f[:min_len]
    h_aligned = h_actual[:min_len]

    # 计算套保后的收益率
    r_hedged = r_s_aligned - h_aligned * r_f_aligned

    # 未套保的方差
    var_unhedged = np.var(r_s_aligned)

    # 套保后的方差
    var_hedged = np.var(r_hedged)

    # 方差降低比例
    variance_reduction = (var_unhedged - var_hedged) / var_unhedged

    # 夏普比率
    mean_hedged = np.mean(r_hedged)
    std_hedged = np.std(r_hedged)
    sharpe_ratio = mean_hedged / std_hedged if std_hedged > 0 else 0

    # 最大回撤
    cumulative = np.cumprod(1 + r_hedged)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = np.min(drawdown)

    return {
        'variance_reduction': variance_reduction,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'var_unhedged': var_unhedged,
        'var_hedged': var_hedged,
        'mean_hedged': mean_hedged,
        'std_hedged': std_hedged
    }


def run_sensitivity_analysis(data, windows=[60, 90, 120], output_dir='outputs/sensitivity_analysis'):
    """
    运行窗口大小敏感性分析

    Parameters:
    -----------
    data : pd.DataFrame
        预处理后的数据
    windows : list
        要测试的窗口大小列表
    output_dir : str
        输出目录
    """

    print("\n" + "=" * 80)
    print("参数敏感性分析：协整窗口大小对比")
    print("=" * 80)

    os.makedirs(output_dir, exist_ok=True)

    results = []

    for window in windows:
        print(f"\n{'=' * 80}")
        print(f"测试窗口大小: {window}天")
        print(f"{'=' * 80}")

        start_time = time.time()

        # 测试ECM-GARCH模型
        print(f"\n[1/2] 拟合ECM-GARCH模型 (窗口={window}天)...")
        try:
            results_ecm = fit_ecm_garch(data, coint_window=window, output_dir=f'{output_dir}/window_{window}')

            # 计算效果指标
            metrics = calculate_effectiveness_metrics(data, results_ecm['h_actual'])

            results.append({
                'model': 'ECM-GARCH',
                'window': window,
                'variance_reduction': metrics['variance_reduction'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown'],
                'var_hedged': metrics['var_hedged'],
                'h_mean': results_ecm['h_actual'].mean(),
                'h_std': results_ecm['h_actual'].std(),
                'h_min': results_ecm['h_actual'].min(),
                'h_max': results_ecm['h_actual'].max(),
                'beta0_mean': results_ecm['cointegration_params']['beta0_mean'],
                'beta0_std': results_ecm['cointegration_params']['beta0_std'],
                'beta1_mean': results_ecm['cointegration_params']['beta1_mean'],
                'beta1_std': results_ecm['cointegration_params']['beta1_std'],
                'coint_r2_mean': results_ecm['cointegration_params']['r_squared_mean']
            })

            print(f"  ✓ 方差降低: {metrics['variance_reduction']:.2%}")
            print(f"  ✓ 夏普比率: {metrics['sharpe_ratio']:.4f}")
            print(f"  ✓ 最大回撤: {metrics['max_drawdown']:.2%}")

        except Exception as e:
            print(f"  ✗ ECM-GARCH拟合失败: {e}")
            import traceback
            traceback.print_exc()

        # 测试ECM-DCC-GARCH模型
        print(f"\n[2/2] 拟合ECM-DCC-GARCH模型 (窗口={window}天)...")
        try:
            results_ecm_dcc = fit_ecm_dcc_garch(data, coint_window=window, output_dir=f'{output_dir}/window_{window}')

            # 计算效果指标
            metrics = calculate_effectiveness_metrics(data, results_ecm_dcc['h_actual'])

            results.append({
                'model': 'ECM-DCC-GARCH',
                'window': window,
                'variance_reduction': metrics['variance_reduction'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'max_drawdown': metrics['max_drawdown'],
                'var_hedged': metrics['var_hedged'],
                'h_mean': results_ecm_dcc['h_actual'].mean(),
                'h_std': results_ecm_dcc['h_actual'].std(),
                'h_min': results_ecm_dcc['h_actual'].min(),
                'h_max': results_ecm_dcc['h_actual'].max(),
                'beta0_mean': results_ecm_dcc['cointegration_params']['beta0_mean'],
                'beta0_std': results_ecm_dcc['cointegration_params']['beta0_std'],
                'beta1_mean': results_ecm_dcc['cointegration_params']['beta1_mean'],
                'beta1_std': results_ecm_dcc['cointegration_params']['beta1_std'],
                'coint_r2_mean': results_ecm_dcc['cointegration_params']['r_squared_mean']
            })

            print(f"  ✓ 方差降低: {metrics['variance_reduction']:.2%}")
            print(f"  ✓ 夏普比率: {metrics['sharpe_ratio']:.4f}")
            print(f"  ✓ 最大回撤: {metrics['max_drawdown']:.2%}")

        except Exception as e:
            print(f"  ✗ ECM-DCC-GARCH拟合失败: {e}")
            import traceback
            traceback.print_exc()

        elapsed = time.time() - start_time
        print(f"\n窗口{window}天测试完成，耗时: {elapsed:.2f}秒")

    # 保存结果
    print("\n" + "=" * 80)
    print("保存敏感性分析结果")
    print("=" * 80)

    # 创建DataFrame
    df_results = pd.DataFrame(results)

    # 保存到CSV
    csv_path = f'{output_dir}/sensitivity_analysis.csv'
    df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {csv_path}")

    # 生成对比表
    print("\n" + "=" * 80)
    print("敏感性分析结果汇总")
    print("=" * 80)

    for model_name in ['ECM-GARCH', 'ECM-DCC-GARCH']:
        print(f"\n【{model_name}】")
        print("-" * 80)

        model_data = df_results[df_results['model'] == model_name]

        if len(model_data) > 0:
            print(f"\n{'窗口':<8} {'方差降低':<12} {'夏普比率':<12} {'最大回撤':<12} {'套保比例均值':<15}")
            print("-" * 80)

            for _, row in model_data.iterrows():
                print(f"{row['window']:<8} {row['variance_reduction']:>10.2%}   "
                      f"{row['sharpe_ratio']:>10.4f}   {row['max_drawdown']:>10.2%}   "
                      f"{row['h_mean']:>13.4f}")

            # 找出最优窗口
            best_window = model_data.loc[model_data['variance_reduction'].idxmax(), 'window']
            print(f"\n  → 最优窗口: {best_window}天 (基于方差降低)")

    # 生成详细对比报告
    print("\n" + "=" * 80)
    print("协整参数时变性对比")
    print("=" * 80)

    for model_name in ['ECM-GARCH', 'ECM-DCC-GARCH']:
        print(f"\n【{model_name}】")
        print("-" * 80)

        model_data = df_results[df_results['model'] == model_name]

        if len(model_data) > 0:
            print(f"\n{'窗口':<8} {'β0均值':<12} {'β0标准差':<12} {'β1均值':<12} {'β1标准差':<12} {'R²均值':<10}")
            print("-" * 80)

            for _, row in model_data.iterrows():
                print(f"{row['window']:<8} {row['beta0_mean']:>10.2f}   "
                      f"{row['beta0_std']:>10.2f}   {row['beta1_mean']:>10.4f}   "
                      f"{row['beta1_std']:>10.4f}   {row['coint_r2_mean']:>8.4f}")

    # 推荐建议
    print("\n" + "=" * 80)
    print("推荐建议")
    print("=" * 80)

    for model_name in ['ECM-GARCH', 'ECM-DCC-GARCH']:
        model_data = df_results[df_results['model'] == model_name]

        if len(model_data) > 0:
            best_idx = model_data['variance_reduction'].idxmax()
            best_row = df_results.loc[best_idx]

            print(f"\n{model_name}:")
            print(f"  推荐窗口大小: {best_row['window']}天")
            print(f"  预期方差降低: {best_row['variance_reduction']:.2%}")
            print(f"  预期夏普比率: {best_row['sharpe_ratio']:.4f}")

            # 分析β参数稳定性
            if best_row['beta0_std'] < 500 and best_row['beta1_std'] < 0.3:
                print(f"  ✓ 协整参数稳定性良好")
            else:
                print(f"  ⚠ 协整参数波动较大，可能需要更长窗口")

    print("\n" + "=" * 80)
    print("✓ 敏感性分析完成！")
    print("=" * 80)

    return df_results


if __name__ == "__main__":
    # 加载数据
    print("加载数据...")
    data = preprocess_data("基差数据.xlsx", output_dir='outputs')

    # 运行敏感性分析
    results_df = run_sensitivity_analysis(data, windows=[60, 90, 120])

    print("\n测试完成！")
