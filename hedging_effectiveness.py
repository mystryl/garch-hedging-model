"""
套保效果评估模块
评估四种模型的套保效果
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def calculate_hedging_effectiveness(data, h_ratio, r_s, r_f):
    """
    计算套保效果指标

    Parameters:
    -----------
    data : pd.DataFrame
        包含收益率数据
    h_ratio : np.array
        套保比例序列
    r_s : str
        现货收益率列名
    r_f : str
        期货收益率列名

    Returns:
    --------
    metrics : dict
        套保效果指标
    """

    # 未套保组合收益率（仅持有现货）
    r_unhedged = data[r_s].values

    # 套保组合收益率
    # R_hedged = r_s - h * r_f
    # 注意：需要对齐长度
    min_len = min(len(r_unhedged), len(h_ratio))
    r_unhedged = r_unhedged[:min_len]
    r_f_aligned = data[r_f].values[:min_len]
    h_aligned = h_ratio[:min_len]

    r_hedged = r_unhedged - h_aligned * r_f_aligned

    # 方差降低比例（Variance Reduction）
    var_unhedged = np.var(r_unhedged)
    var_hedged = np.var(r_hedged)
    variance_reduction = 1 - var_hedged / var_unhedged

    # Ederington有效性指标
    ederington = variance_reduction

    # 风险调整后的收益
    mean_unhedged = np.mean(r_unhedged)
    mean_hedged = np.mean(r_hedged)

    std_unhedged = np.std(r_unhedged)
    std_hedged = np.std(r_hedged)

    # 夏普比率（假设无风险利率为0）
    sharpe_unhedged = mean_unhedged / std_unhedged if std_unhedged > 0 else 0
    sharpe_hedged = mean_hedged / std_hedged if std_hedged > 0 else 0

    # 最大回撤
    def calculate_max_drawdown(returns):
        """计算最大回撤"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)

    max_dd_unhedged = calculate_max_drawdown(r_unhedged)
    max_dd_hedged = calculate_max_drawdown(r_hedged)

    # VaR (Value at Risk) at 95% confidence level
    var_95_unhedged = np.percentile(r_unhedged, 5)
    var_95_hedged = np.percentile(r_hedged, 5)

    # CVaR (Conditional VaR) at 95% confidence level
    cvar_95_unhedged = np.mean(r_unhedged[r_unhedged <= var_95_unhedged])
    cvar_95_hedged = np.mean(r_hedged[r_hedged <= var_95_hedged])

    metrics = {
        'variance_reduction': variance_reduction,
        'ederington': ederington,
        'var_unhedged': var_unhedged,
        'var_hedged': var_hedged,
        'mean_unhedged': mean_unhedged,
        'mean_hedged': mean_hedged,
        'std_unhedged': std_unhedged,
        'std_hedged': std_hedged,
        'sharpe_unhedged': sharpe_unhedged,
        'sharpe_hedged': sharpe_hedged,
        'max_dd_unhedged': max_dd_unhedged,
        'max_dd_hedged': max_dd_hedged,
        'var_95_unhedged': var_95_unhedged,
        'var_95_hedged': var_95_hedged,
        'cvar_95_unhedged': cvar_95_unhedged,
        'cvar_95_hedged': cvar_95_hedged
    }

    return metrics, r_hedged


def in_sample_out_sample_test(data, model_results, train_ratio=0.8):
    """
    样本内外测试

    Parameters:
    -----------
    data : pd.DataFrame
        完整数据
    model_results : dict
        所有模型结果
    train_ratio : float
        训练集比例

    Returns:
    --------
    results : dict
        样本内外效果对比
    """

    T = len(data)
    split_point = int(T * train_ratio)

    print(f"\n样本内外测试:")
    print(f"  训练集: 前 {split_point} 个观测 ({train_ratio*100:.0f}%)")
    print(f"  测试集: 后 {T - split_point} 个观测 ({(1-train_ratio)*100:.0f}%)")

    results = {}

    for model_name, result in model_results.items():
        h = result['h_actual']

        # 对齐长度
        min_len = min(len(h), T)
        h_train = h[:split_point][:min_len]
        h_test = h[split_point:][:min_len - split_point] if min_len > split_point else []

        # 计算样本内效果
        r_s_train = data['r_s'].values[:split_point]
        r_f_train = data['r_f'].values[:split_point]

        r_hedged_train = r_s_train - h_train * r_f_train
        var_reduction_train = 1 - np.var(r_hedged_train) / np.var(r_s_train)

        # 计算样本外效果
        if len(h_test) > 0:
            r_s_test = data['r_s'].values[split_point:split_point + len(h_test)]
            r_f_test = data['r_f'].values[split_point:split_point + len(h_test)]

            r_hedged_test = r_s_test - h_test * r_f_test
            var_reduction_test = 1 - np.var(r_hedged_test) / np.var(r_s_test)
        else:
            var_reduction_test = np.nan

        results[model_name] = {
            'in_sample': var_reduction_train,
            'out_sample': var_reduction_test
        }

        print(f"\n  {model_name}:")
        print(f"    样本内方差降低: {var_reduction_train:.2%}")
        print(f"    样本外方差降低: {var_reduction_test:.2%}")

    return results


def compare_models(data, model_results, output_dir='outputs'):
    """
    比较四种模型的套保效果

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s 和 r_f 的数据
    model_results : dict
        四种模型的结果字典
    output_dir : str
        输出目录

    Returns:
    --------
    comparison : pd.DataFrame
        模型对比表格
    """

    print("\n" + "=" * 60)
    print("套保效果评估")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 计算各模型的效果指标
    all_metrics = {}
    all_hedged_returns = {}

    for model_name, result in model_results.items():
        h = result['h_actual']
        metrics, r_hedged = calculate_hedging_effectiveness(
            data, h, 'r_s', 'r_f'
        )
        all_metrics[model_name] = metrics
        all_hedged_returns[model_name] = r_hedged

        print(f"\n{model_name}:")
        print(f"  方差降低比例: {metrics['variance_reduction']:.2%}")
        print(f"  Ederington指标: {metrics['ederington']:.4f}")
        print(f"  夏普比率 (套保后): {metrics['sharpe_hedged']:.4f}")
        print(f"  最大回撤 (套保后): {metrics['max_dd_hedged']:.2%}")

    # 创建对比表格
    comparison_data = []

    for model_name in model_results.keys():
        metrics = all_metrics[model_name]
        comparison_data.append({
            '模型': model_name,
            '方差降低比例': f"{metrics['variance_reduction']:.2%}",
            'Ederington指标': f"{metrics['ederington']:.4f}",
            '套保前波动率': f"{metrics['std_unhedged']:.6f}",
            '套保后波动率': f"{metrics['std_hedged']:.6f}",
            '夏普比率(套保前)': f"{metrics['sharpe_unhedged']:.4f}",
            '夏普比率(套保后)': f"{metrics['sharpe_hedged']:.4f}",
            '最大回撤(套保前)': f"{metrics['max_dd_unhedged']:.2%}",
            '最大回撤(套保后)': f"{metrics['max_dd_hedged']:.2%}",
            'VaR_95(套保前)': f"{metrics['var_95_unhedged']:.6f}",
            'VaR_95(套保后)': f"{metrics['var_95_hedged']:.6f}"
        })

    comparison_df = pd.DataFrame(comparison_data)

    # 保存对比表格
    csv_path = f"{output_dir}/effectiveness_report.csv"
    comparison_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已保存效果评估报告: {csv_path}")

    # 样本内外测试
    print("\n" + "=" * 60)
    ios_results = in_sample_out_sample_test(data, model_results)

    # 保存样本内外测试结果
    ios_df = pd.DataFrame(ios_results).T
    ios_df.columns = ['样本内方差降低', '样本外方差降低']
    ios_path = f"{output_dir}/in_sample_out_sample.csv"
    ios_df.to_csv(ios_path, encoding='utf-8-sig')
    print(f"\n✓ 已保存样本内外测试: {ios_path}")

    # 绘制对比图表
    plot_comparison_charts(comparison_df, all_metrics, ios_results, f"{output_dir}/figures")

    print("\n" + "=" * 60)
    print("✓ 套保效果评估完成！")
    print("=" * 60)

    return comparison_df, ios_df, all_metrics, ios_results


def plot_comparison_charts(comparison_df, all_metrics, ios_results, output_dir='outputs/figures'):
    """
    绘制效果对比图表
    """

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 图1: 方差降低比例对比
    print("\n[绘图1/4] 方差降低比例对比...")
    fig, ax = plt.subplots(figsize=(10, 6))

    models = comparison_df['模型'].values
    variance_reduction = [float(v.rstrip('%')) / 100 for v in comparison_df['方差降低比例'].values]

    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
    bars = ax.bar(models, variance_reduction, color=colors, alpha=0.7, edgecolor='black')

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1%}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_ylabel('Variance Reduction', fontsize=12)
    ax.set_title('Hedging Effectiveness Comparison (Variance Reduction)',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(variance_reduction) * 1.2)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/variance_reduction.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 图2: 夏普比率对比
    print("[绘图2/4] 夏普比率对比...")
    fig, ax = plt.subplots(figsize=(10, 6))

    sharpe_unhedged = [float(all_metrics[m]['sharpe_unhedged']) for m in models]
    sharpe_hedged = [float(all_metrics[m]['sharpe_hedged']) for m in models]

    x = np.arange(len(models))
    width = 0.35

    bars1 = ax.bar(x - width/2, sharpe_unhedged, width, label='Unhedged',
                   color='gray', alpha=0.7)
    bars2 = ax.bar(x + width/2, sharpe_hedged, width, label='Hedged',
                   color=colors, alpha=0.7)

    ax.set_ylabel('Sharpe Ratio', fontsize=12)
    ax.set_title('Sharpe Ratio Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/sharpe_ratio_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 图3: 最大回撤对比
    print("[绘图3/4] 最大回撤对比...")
    fig, ax = plt.subplots(figsize=(10, 6))

    max_dd_unhedged = [float(all_metrics[m]['max_dd_unhedged']) for m in models]
    max_dd_hedged = [float(all_metrics[m]['max_dd_hedged']) for m in models]

    bars1 = ax.bar(x - width/2, max_dd_unhedged, width, label='Unhedged',
                   color='gray', alpha=0.7)
    bars2 = ax.bar(x + width/2, max_dd_hedged, width, label='Hedged',
                   color=colors, alpha=0.7)

    ax.set_ylabel('Max Drawdown', fontsize=12)
    ax.set_title('Maximum Drawdown Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/max_drawdown_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()

    # 图4: 样本内外效果对比
    print("[绘图4/4] 样本内外效果对比...")
    fig, ax = plt.subplots(figsize=(10, 6))

    in_sample = [ios_results[m]['in_sample'] for m in models]
    out_sample = [ios_results[m]['out_sample'] for m in models]

    bars1 = ax.bar(x - width/2, in_sample, width, label='In-Sample',
                   color='steelblue', alpha=0.7)
    bars2 = ax.bar(x + width/2, out_sample, width, label='Out-of-Sample',
                   color='coral', alpha=0.7)

    ax.set_ylabel('Variance Reduction', fontsize=12)
    ax.set_title('In-Sample vs Out-of-Sample Performance',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend(loc='best')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/in_sample_vs_out_sample.png", dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  ✓ 所有图表已保存到 {output_dir}")


if __name__ == "__main__":
    # 测试效果评估模块
    from data_preprocessing import preprocess_data
    from model_basic_garch import fit_basic_garch
    from model_ecm_garch import fit_ecm_garch
    from model_dcc_garch import fit_dcc_garch
    from model_ecm_dcc_garch import fit_ecm_dcc_garch

    # 加载数据
    data = preprocess_data("基差数据.xlsx")

    # 拟合所有模型
    print("拟合所有模型...")
    h_basic = fit_basic_garch(data)
    h_ecm = fit_ecm_garch(data)
    h_dcc = fit_dcc_garch(data)
    h_ecm_dcc = fit_ecm_dcc_garch(data)

    # 模型结果字典
    model_results = {
        'Basic GARCH': h_basic,
        'ECM-GARCH': h_ecm,
        'DCC-GARCH': h_dcc,
        'ECM-DCC-GARCH': h_ecm_dcc
    }

    # 评估效果
    comparison_df, ios_df, all_metrics, ios_results = compare_models(data, model_results)

    print("\n测试完成！")
