"""
探索性数据分析（EDA）模块
功能：数据描述性统计、可视化、平稳性检验、协整检验
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.tsa.stattools import adfuller, coint
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 设置绘图风格
sns.set_style("whitegrid")
sns.set_palette("husl")


def plot_price_series(data, output_dir='outputs/figures'):
    """
    绘制价格走势图（现货 vs 期货）
    """
    print("\n[绘图1/6] 价格走势对比图...")
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(data['date'], data['spot'], label='Spot Price (Shanghai)', linewidth=1.5, alpha=0.8)
    ax.plot(data['date'], data['futures'], label='Futures Price (SHFE)', linewidth=1.5, alpha=0.8)

    ax.set_title('Hot Rolled Coil: Spot vs Futures Price', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Price (CNY/ton)', fontsize=12)
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/price_series.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def plot_returns_volatility(data, output_dir='outputs/figures'):
    """
    绘制收益率波动图
    """
    print("\n[绘图2/6] 收益率波动图...")
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # 现货收益率
    axes[0].plot(data['date'], data['r_s'], linewidth=1, alpha=0.7, color='steelblue')
    axes[0].axhline(y=0, color='red', linestyle='--', linewidth=0.8)
    axes[0].set_title('Spot Returns', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Return', fontsize=11)
    axes[0].grid(True, alpha=0.3)

    # 期货收益率
    axes[1].plot(data['date'], data['r_f'], linewidth=1, alpha=0.7, color='darkorange')
    axes[1].axhline(y=0, color='red', linestyle='--', linewidth=0.8)
    axes[1].set_title('Futures Returns', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Date', fontsize=11)
    axes[1].set_ylabel('Return', fontsize=11)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/returns_volatility.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def plot_basis_spread(data, output_dir='outputs/figures'):
    """
    绘制基差时变图
    """
    print("\n[绘图3/6] 基差时变图...")
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(data['date'], data['spread'], linewidth=1.5, color='purple', alpha=0.7)
    ax.axhline(y=data['spread'].mean(), color='red', linestyle='--',
               linewidth=1.5, label=f"Mean Spread: {data['spread'].mean():.2f}")
    ax.fill_between(data['date'], data['spread'].mean() - data['spread'].std(),
                    data['spread'].mean() + data['spread'].std(), alpha=0.2, color='gray',
                    label=f"±1 Std Dev: {data['spread'].std():.2f}")

    ax.set_title('Basis Spread (Spot - Futures)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Spread (CNY/ton)', fontsize=12)
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/basis_spread.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def plot_distribution_analysis(data, output_dir='outputs/figures'):
    """
    绘制收益率分布分析图
    """
    print("\n[绘图4/6] 收益率分布分析图...")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 现货收益率直方图
    axes[0, 0].hist(data['r_s'], bins=50, color='steelblue', alpha=0.7, edgecolor='black')
    axes[0, 0].axvline(data['r_s'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
    axes[0, 0].set_title('Spot Returns Distribution', fontsize=11, fontweight='bold')
    axes[0, 0].set_xlabel('Return', fontsize=10)
    axes[0, 0].set_ylabel('Frequency', fontsize=10)
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # 期货收益率直方图
    axes[0, 1].hist(data['r_f'], bins=50, color='darkorange', alpha=0.7, edgecolor='black')
    axes[0, 1].axvline(data['r_f'].mean(), color='red', linestyle='--', linewidth=2, label='Mean')
    axes[0, 1].set_title('Futures Returns Distribution', fontsize=11, fontweight='bold')
    axes[0, 1].set_xlabel('Return', fontsize=10)
    axes[0, 1].set_ylabel('Frequency', fontsize=10)
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Q-Q图：现货收益率
    stats.probplot(data['r_s'], dist="norm", plot=axes[1, 0])
    axes[1, 0].set_title('Q-Q Plot: Spot Returns', fontsize=11, fontweight='bold')
    axes[1, 0].grid(True, alpha=0.3)

    # Q-Q图：期货收益率
    stats.probplot(data['r_f'], dist="norm", plot=axes[1, 1])
    axes[1, 1].set_title('Q-Q Plot: Futures Returns', fontsize=11, fontweight='bold')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/returns_distribution.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def plot_correlation_scatter(data, output_dir='outputs/figures'):
    """
    绘制现货与期货收益率散点图
    """
    print("\n[绘图5/6] 收益率相关性散点图...")
    fig, ax = plt.subplots(figsize=(10, 8))

    scatter = ax.scatter(data['r_f'], data['r_s'], alpha=0.5, s=30, c=range(len(data)),
                         cmap='viridis')

    # 添加拟合线
    z = np.polyfit(data['r_f'], data['r_s'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(data['r_f'].min(), data['r_f'].max(), 100)
    ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.8, label='Trend Line')

    # 计算相关系数
    corr = data[['r_s', 'r_f']].corr().iloc[0, 1]

    ax.set_xlabel('Futures Returns', fontsize=12)
    ax.set_ylabel('Spot Returns', fontsize=12)
    ax.set_title(f'Spot vs Futures Returns (Correlation: {corr:.4f})',
                 fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.colorbar(scatter, ax=ax, label='Observation Index')
    plt.tight_layout()
    output_path = f"{output_dir}/correlation_scatter.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def plot_rolling_statistics(data, window=30, output_dir='outputs/figures'):
    """
    绘制滚动统计量图
    """
    print("\n[绘图6/6] 滚动统计量图...")
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # 滚动相关系数
    rolling_corr = data['r_s'].rolling(window=window).corr(data['r_f'])
    axes[0].plot(data['date'], rolling_corr, linewidth=1.5, color='darkgreen')
    axes[0].axhline(y=rolling_corr.mean(), color='red', linestyle='--', linewidth=1.5,
                    label=f"Mean: {rolling_corr.mean():.4f}")
    axes[0].set_title(f'Rolling Correlation (Window={window} days)', fontsize=12, fontweight='bold')
    axes[0].set_ylabel('Correlation', fontsize=11)
    axes[0].legend(loc='best', fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # 滚动波动率（现货）
    rolling_vol_s = data['r_s'].rolling(window=window).std() * np.sqrt(252)
    axes[1].plot(data['date'], rolling_vol_s, linewidth=1.5, color='steelblue')
    axes[1].set_title(f'Rolling Volatility: Spot (Annualized, Window={window} days)',
                      fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Volatility', fontsize=11)
    axes[1].grid(True, alpha=0.3)

    # 滚动波动率（期货）
    rolling_vol_f = data['r_f'].rolling(window=window).std() * np.sqrt(252)
    axes[2].plot(data['date'], rolling_vol_f, linewidth=1.5, color='darkorange')
    axes[2].set_title(f'Rolling Volatility: Futures (Annualized, Window={window} days)',
                      fontsize=12, fontweight='bold')
    axes[2].set_xlabel('Date', fontsize=11)
    axes[2].set_ylabel('Volatility', fontsize=11)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = f"{output_dir}/rolling_statistics.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✓ 已保存: {output_path}")


def descriptive_statistics(data):
    """
    计算描述性统计
    """
    print("\n" + "=" * 60)
    print("描述性统计分析")
    print("=" * 60)

    # 收益率统计
    returns_stats = pd.DataFrame({
        'Spot Returns': data['r_s'].describe(),
        'Futures Returns': data['r_f'].describe()
    })

    # 添加偏度和峰度
    returns_stats.loc['skewness'] = [data['r_s'].skew(), data['r_f'].skew()]
    returns_stats.loc['kurtosis'] = [data['r_s'].kurtosis(), data['r_f'].kurtosis()]

    print("\n收益率统计:")
    print(returns_stats.to_string())

    # 相关系数
    corr = data[['r_s', 'r_f']].corr().iloc[0, 1]
    print(f"\n现货-期货相关系数: {corr:.6f}")

    # 基差统计
    print("\n基差统计:")
    print(f"  均值: {data['spread'].mean():.2f}")
    print(f"  标准差: {data['spread'].std():.2f}")
    print(f"  最小值: {data['spread'].min():.2f}")
    print(f"  最大值: {data['spread'].max():.2f}")

    return returns_stats


def adf_test(series, title):
    """
    ADF平稳性检验
    """
    print(f"\nADF检验: {title}")
    print("-" * 50)

    result = adfuller(series.dropna(), regression='ct', autolag='BIC')

    print(f"  ADF统计量: {result[0]:.6f}")
    print(f"  p值: {result[1]:.6f}")
    print(f"  临界值 (1%): {result[4]['1%']:.6f}")
    print(f"  临界值 (5%): {result[4]['5%']:.6f}")
    print(f"  临界值 (10%): {result[4]['10%']:.6f}")

    if result[1] < 0.05:
        print(f"  结论: 在5%显著性水平下拒绝原假设，序列是平稳的 ✓")
    else:
        print(f"  结论: 在5%显著性水平下无法拒绝原假设，序列可能非平稳 ✗")

    return result


def johansen_cointegration_test(data, det_order=-1, k_ar_diff=1):
    """
    协整检验 (使用Engle-Granger方法)
    """
    print("\n" + "=" * 60)
    print("协整检验 (Engle-Granger方法)")
    print("=" * 60)

    # 使用价格序列进行协整检验
    spot = data['spot'].values
    futures = data['futures'].values

    try:
        score, pvalue, crit_value = coint(spot, futures, trend='ct', autolag='BIC')

        print(f"\nEngle-Granger协整检验:")
        print("-" * 50)
        print(f"  检验统计量: {score:.4f}")
        print(f"  p值: {pvalue:.6f}")
        print(f"  临界值 (1%): {crit_value[0]:.4f}")
        print(f"  临界值 (5%): {crit_value[1]:.4f}")
        print(f"  临界值 (10%): {crit_value[2]:.4f}")

        if pvalue < 0.05:
            print(f"\n  结论: 在5%显著性水平下拒绝原假设，存在协整关系 ✓")
        else:
            print(f"\n  结论: 在5%显著性水平下无法拒绝原假设，可能不存在协整关系 ✗")

        # 计算协整向量（通过OLS回归）
        import statsmodels.api as sm
        X = sm.add_constant(futures)
        model = sm.OLS(spot, X).fit()
        beta0 = model.params[0]
        beta1 = model.params[1]

        print(f"\n协整方程（长期均衡关系）:")
        print(f"  spot = {beta0:.2f} + {beta1:.4f} * futures")
        print(f"  R² = {model.rsquared:.4f}")

        result = {
            'test_statistic': score,
            'pvalue': pvalue,
            'cointegration_vector': [beta0, beta1],
            'r_squared': model.rsquared
        }

        return result

    except Exception as e:
        print(f"协整检验失败: {e}")
        return None


def generate_eda_report(data, output_dir='outputs'):
    """
    生成完整的EDA报告
    """
    print("\n" + "=" * 60)
    print("步骤2: 探索性数据分析（EDA）")
    print("=" * 60)

    import os
    os.makedirs(f"{output_dir}/figures", exist_ok=True)

    # 1. 描述性统计
    desc_stats = descriptive_statistics(data)

    # 2. ADF平稳性检验
    print("\n" + "=" * 60)
    print("平稳性检验")
    print("=" * 60)

    adf_test(data['r_s'], "现货收益率")
    adf_test(data['r_f'], "期货收益率")
    adf_test(data['spread'], "基差")

    # 3. Johansen协整检验
    johansen_result = johansen_cointegration_test(data)

    # 4. 生成所有图表
    print("\n" + "=" * 60)
    print("生成可视化图表")
    print("=" * 60)

    plot_price_series(data, f"{output_dir}/figures")
    plot_returns_volatility(data, f"{output_dir}/figures")
    plot_basis_spread(data, f"{output_dir}/figures")
    plot_distribution_analysis(data, f"{output_dir}/figures")
    plot_correlation_scatter(data, f"{output_dir}/figures")
    plot_rolling_statistics(data, window=30, output_dir=f"{output_dir}/figures")

    print("\n" + "=" * 60)
    print("✓ EDA分析完成！")
    print("=" * 60)

    # 返回汇总结果
    results = {
        'descriptive_stats': desc_stats,
        'correlation': data[['r_s', 'r_f']].corr().iloc[0, 1],
        'johansen_result': johansen_result
    }

    return results


if __name__ == "__main__":
    # 测试EDA分析
    from data_preprocessing import preprocess_data

    # 数据预处理
    data = preprocess_data("基差数据.xlsx")

    # EDA分析
    eda_results = generate_eda_report(data)
    print("\nEDA分析完成！")
