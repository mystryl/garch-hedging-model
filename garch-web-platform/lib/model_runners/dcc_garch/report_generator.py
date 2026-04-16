"""
DCC-GARCH 专用报告生成器

保持与 Basic GARCH 一致的视觉主题（蓝色）
添加 DCC-GARCH 特有图表：动态相关系数、套保比例与相关系数对比
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import warnings
warnings.filterwarnings('ignore')

# 先设置绘图风格
sns.set_style('whitegrid')

# 配置中文字体
from basic_garch_analyzer.font_config import setup_chinese_font
setup_chinese_font()

# 导入数据过滤函数
from basic_garch_analyzer.report_generator import filter_data_to_recent_months

# 创建全局的中文字体属性对象
import os
font_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'
if os.path.exists(font_path):
    CHINESE_FONT = fm.FontProperties(fname=font_path)
else:
    CHINESE_FONT = None


def apply_chinese_font(fig_or_ax):
    """应用中文字体到图表"""
    if CHINESE_FONT is None:
        return

    if hasattr(fig_or_ax, 'flatten') and not hasattr(fig_or_ax, 'axes'):
        axes_list = fig_or_ax.flatten()
        fig = axes_list[0].figure if len(axes_list) > 0 else None
    elif hasattr(fig_or_ax, 'figure'):
        axes_list = [fig_or_ax]
        fig = fig_or_ax.figure
    else:
        fig = fig_or_ax
        axes_list = fig.axes

    for ax in axes_list:
        if ax.get_title():
            ax.set_title(ax.get_title(), fontproperties=CHINESE_FONT)
        if ax.get_xlabel():
            ax.set_xlabel(ax.get_xlabel(), fontproperties=CHINESE_FONT)
        if ax.get_ylabel():
            ax.set_ylabel(ax.get_ylabel(), fontproperties=CHINESE_FONT)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(CHINESE_FONT)
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontproperties(CHINESE_FONT)
        for text in ax.texts:
            text.set_fontproperties(CHINESE_FONT)


def plot_price_series(data, output_path, restrict_to_recent_months=False):
    """绘制现货和期货价格走势（复用 Basic GARCH）"""
    print("\n[绘图 1/8] 价格走势图...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, cutoff_date = filter_data_to_recent_months(data, months=3)
        if cutoff_date:
            print(f"  图表仅显示: {cutoff_date.strftime('%Y-%m-%d')} 之后的数据")

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # 价格走势
    ax1 = axes[0]
    ax1.plot(data['date'], data['spot'], label='现货价格', linewidth=1.5, alpha=0.8)
    ax1.plot(data['date'], data['futures'], label='期货价格', linewidth=1.5, alpha=0.8)
    ax1.set_ylabel('价格', fontsize=11)
    ax1.set_title('现货与期货价格走势', fontsize=12, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 基差走势
    ax2 = axes[1]
    ax2.plot(data['date'], data['spread'], label='基差', color='orange', linewidth=1.5, alpha=0.8)
    ax2.axhline(y=data['spread'].mean(), color='red', linestyle='--', alpha=0.7,
                label=f'基差均值: {data["spread"].mean():.2f}')
    ax2.set_ylabel('基差', fontsize=11)
    ax2.set_xlabel('日期', fontsize=11)
    ax2.set_title('基差时变', fontsize=12, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    apply_chinese_font(axes)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_returns(data, output_path, restrict_to_recent_months=False):
    """绘制收益率分布（复用 Basic GARCH）"""
    print("[绘图 2/8] 收益率分布图...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, cutoff_date = filter_data_to_recent_months(data, months=3)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 收益率时序
    ax1 = axes[0, 0]
    ax1.plot(data['date'], data['r_s'], label='现货收益率', alpha=0.6, linewidth=0.8)
    ax1.set_ylabel('收益率', fontsize=10)
    ax1.set_title('现货收益率时序', fontsize=11, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    ax2 = axes[0, 1]
    ax2.plot(data['date'], data['r_f'], label='期货收益率', alpha=0.6, linewidth=0.8, color='orange')
    ax2.set_ylabel('收益率', fontsize=10)
    ax2.set_title('期货收益率时序', fontsize=11, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # 收益率分布
    ax3 = axes[1, 0]
    ax3.hist(data['r_s'], bins=50, alpha=0.6, density=True, edgecolor='black')
    ax3.axvline(x=data['r_s'].mean(), color='red', linestyle='--', alpha=0.8,
                label=f'均值: {data["r_s"].mean():.6f}')
    ax3.set_xlabel('收益率', fontsize=10)
    ax3.set_ylabel('密度', fontsize=10)
    ax3.set_title('现货收益率分布', fontsize=11, fontweight='bold')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3, axis='y')

    ax4 = axes[1, 1]
    ax4.hist(data['r_f'], bins=50, alpha=0.6, density=True, edgecolor='black', color='orange')
    ax4.axvline(x=data['r_f'].mean(), color='red', linestyle='--', alpha=0.8,
                label=f'均值: {data["r_f"].mean():.6f}')
    ax4.set_xlabel('收益率', fontsize=10)
    ax4.set_ylabel('密度', fontsize=10)
    ax4.set_title('期货收益率分布', fontsize=11, fontweight='bold')
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3, axis='y')

    apply_chinese_font(axes)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_dcc_correlation(data, model_results, output_path, restrict_to_recent_months=False):
    """
    绘制动态相关系数图（DCC-GARCH 特有）

    Parameters:
    -----------
    data : pd.DataFrame
        数据
    model_results : dict
        模型结果
    output_path : str
        输出文件路径
    restrict_to_recent_months : bool
        是否只显示最近三个月数据
    """
    print("[绘图 3/8] 动态相关系数图...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, cutoff_date = filter_data_to_recent_months(data, months=3)

        # 计算需要保留的元素数量（从末尾开始）
        filtered_len = len(data)

        # 创建过滤后的 model_results 副本
        model_results_filtered = {
            'rho_t': model_results['rho_t'][-filtered_len:]
        }
    else:
        model_results_filtered = model_results

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    rho_t = model_results_filtered['rho_t']

    # 动态相关系数时序
    ax1 = axes[0]
    ax1.plot(data['date'], rho_t, label='动态相关系数', linewidth=1.5, alpha=0.8, color='purple')
    ax1.axhline(y=rho_t.mean(), color='red', linestyle='--', alpha=0.8,
                label=f'均值: {rho_t.mean():.4f}')
    ax1.set_ylabel('相关系数', fontsize=11)
    ax1.set_title('DCC-GARCH 动态相关系数时变', fontsize=12, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 动态相关系数分布
    ax2 = axes[1]
    ax2.hist(rho_t, bins=50, alpha=0.6, density=True, edgecolor='black', color='purple')
    ax2.axvline(x=rho_t.mean(), color='red', linestyle='--', alpha=0.8,
                label=f'均值: {rho_t.mean():.4f}')
    ax2.axvline(x=np.median(rho_t), color='green', linestyle='--', alpha=0.8,
                label=f'中位数: {np.median(rho_t):.4f}')
    ax2.set_xlabel('相关系数', fontsize=11)
    ax2.set_ylabel('密度', fontsize=11)
    ax2.set_title('动态相关系数分布', fontsize=12, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3, axis='y')

    apply_chinese_font(axes)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_hedge_ratio_and_correlation(data, model_results, output_path, restrict_to_recent_months=False):
    """
    绘制套保比例与相关系数对比（DCC-GARCH 特有）

    Parameters:
    -----------
    data : pd.DataFrame
        数据
    model_results : dict
        模型结果
    output_path : str
        输出文件路径
    restrict_to_recent_months : bool
        是否只显示最近三个月数据
    """
    print("[绘图 4/8] 套保比例与相关系数对比...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, cutoff_date = filter_data_to_recent_months(data, months=3)

        # 计算需要保留的元素数量（从末尾开始）
        filtered_len = len(data)

        # 创建过滤后的 model_results 副本
        model_results_filtered = {
            'h_actual': model_results['h_actual'][-filtered_len:],
            'rho_t': model_results['rho_t'][-filtered_len:]
        }
    else:
        model_results_filtered = model_results

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    h_actual = model_results_filtered['h_actual']
    rho_t = model_results_filtered['rho_t']

    # 套保比例时序
    ax1 = axes[0]
    ax1.plot(data['date'], h_actual, label='套保比例（税后）', linewidth=1.5, alpha=0.8, color='#3498db')
    ax1.axhline(y=h_actual.mean(), color='red', linestyle='--', alpha=0.8,
                label=f'均值: {h_actual.mean():.4f}')
    ax1.set_ylabel('套保比例', fontsize=11)
    ax1.set_title('DCC-GARCH 套保比例时变', fontsize=12, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # 套保比例 vs 相关系数散点图
    ax2 = axes[1]
    scatter = ax2.scatter(rho_t, h_actual, alpha=0.5, s=10, c=range(len(rho_t)), cmap='viridis')
    ax2.set_xlabel('动态相关系数', fontsize=11)
    ax2.set_ylabel('套保比例', fontsize=11)
    ax2.set_title('套保比例 vs 动态相关系数', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # 添加趋势线
    z = np.polyfit(rho_t, h_actual, 1)
    p = np.poly1d(z)
    ax2.plot(rho_t, p(rho_t), "r--", alpha=0.8, linewidth=2, label=f'趋势线: y={z[0]:.2f}x+{z[1]:.2f}')
    ax2.legend(loc='best')

    plt.colorbar(scatter, ax=ax2, label='时间索引')

    apply_chinese_font(axes)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_backtest_results(data, eval_results, output_path, restrict_to_recent_months=False):
    """绘制回测结果：净值曲线（复用 Basic GARCH）"""
    print("[绘图 5/8] 净值曲线图...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, _ = filter_data_to_recent_months(data, months=3)
        # 确保评估结果与过滤后的数据对齐
        max_len = min(len(data), len(eval_results['returns_unhedged']), len(eval_results['returns_hedged']))
        eval_results_filtered = {
            'returns_unhedged': eval_results['returns_unhedged'][:max_len],
            'returns_hedged': eval_results['returns_hedged'][:max_len],
            'drawdown_series': eval_results['drawdown_series'][:max_len],
            'metrics': eval_results['metrics']
        }
    else:
        eval_results_filtered = eval_results

    fig, ax = plt.subplots(figsize=(14, 8))

    cumulative_unhedged = np.cumprod(1 + eval_results_filtered['returns_unhedged'])
    cumulative_hedged = np.cumprod(1 + eval_results_filtered['returns_hedged'])

    ax.plot(data['date'].values[:len(cumulative_unhedged)], cumulative_unhedged,
            label='未套保组合', linewidth=2, alpha=0.8, color='red')
    ax.plot(data['date'].values[:len(cumulative_hedged)], cumulative_hedged,
            label='套保组合', linewidth=2, alpha=0.8, color='green')

    ax.axhline(y=cumulative_hedged[np.argmin(eval_results_filtered['drawdown_series'])],
               color='orange', linestyle='--', alpha=0.6,
               label=f'套保组合最大回撤: {eval_results_filtered["metrics"]["max_dd_hedged"]:.2%}')

    ax.set_ylabel('净值', fontsize=11)
    ax.set_xlabel('日期', fontsize=11)
    ax.set_title('套保前后净值曲线对比', fontsize=12, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.2f}'))

    apply_chinese_font(ax)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_drawdown(data, eval_results, output_path, restrict_to_recent_months=False):
    """绘制回撤曲线（复用 Basic GARCH）"""
    print("[绘图 6/8] 回撤曲线图...")

    # 应用数据过滤（仅用于图表显示）
    if restrict_to_recent_months:
        data, _ = filter_data_to_recent_months(data, months=3)
        # 确保评估结果与过滤后的数据对齐
        max_len = min(len(data), len(eval_results['drawdown_series']))
        eval_results_filtered = {
            'drawdown_series': eval_results['drawdown_series'][:max_len],
            'metrics': eval_results['metrics']
        }
    else:
        eval_results_filtered = eval_results

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.fill_between(data['date'].values[:len(eval_results_filtered['drawdown_series'])],
                    0, eval_results_filtered['drawdown_series'],
                    alpha=0.3, color='red', label='回撤')
    ax.plot(data['date'].values[:len(eval_results_filtered['drawdown_series'])],
            eval_results_filtered['drawdown_series'],
            linewidth=1.5, color='red')

    max_dd_idx = np.argmin(eval_results_filtered['drawdown_series'])
    ax.plot(data['date'].values[max_dd_idx], eval_results_filtered['drawdown_series'][max_dd_idx],
            'v', markersize=10, color='darkred',
            label=f'最大回撤: {eval_results_filtered["metrics"]["max_dd_hedged"]:.2%}')

    ax.set_ylabel('回撤比例', fontsize=11)
    ax.set_xlabel('日期', fontsize=11)
    ax.set_title('套保组合回撤曲线', fontsize=12, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))

    apply_chinese_font(ax)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_performance_metrics(eval_results, output_path):
    """绘制性能指标对比图（复用 Basic GARCH）"""
    print("[绘图 7/8] 性能指标对比图...")

    metrics = eval_results['metrics']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 方差降低
    ax1 = axes[0, 0]
    categories = ['未套保', '套保后']
    variances = [metrics['var_unhedged'], metrics['var_hedged']]
    bars = ax1.bar(categories, variances, color=['red', 'green'], alpha=0.7, edgecolor='black')
    ax1.set_ylabel('收益率方差', fontsize=10)
    ax1.set_title('方差对比', fontsize=11, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, variances):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:.6f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 夏普比率
    ax2 = axes[0, 1]
    sharpe_values = [metrics['sharpe_unhedged'], metrics['sharpe_hedged']]
    bars = ax2.bar(categories, sharpe_values, color=['red', 'green'], alpha=0.7, edgecolor='black')
    ax2.set_ylabel('夏普比率', fontsize=10)
    ax2.set_title('夏普比率对比', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    for bar, val in zip(bars, sharpe_values):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:.4f}', ha='center', va='bottom' if val >= 0 else 'top', fontsize=10, fontweight='bold')

    # 最大回撤
    ax3 = axes[1, 0]
    max_dd_values = [metrics['max_dd_unhedged'], metrics['max_dd_hedged']]
    bars = ax3.bar(categories, max_dd_values, color=['red', 'green'], alpha=0.7, edgecolor='black')
    ax3.set_ylabel('最大回撤', fontsize=10)
    ax3.set_title('最大回撤对比', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
    for bar, val in zip(bars, max_dd_values):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:.1%}', ha='center', va='top', fontsize=10, fontweight='bold')

    # VaR 和 CVaR
    ax4 = axes[1, 1]
    var_values = [metrics['var_95_unhedged'], metrics['var_95_hedged']]
    cvar_values = [metrics['cvar_95_unhedged'], metrics['cvar_95_hedged']]
    x = np.arange(len(categories))
    width = 0.35
    bars1 = ax4.bar(x - width/2, var_values, width, label='VaR (95%)', color='orange', alpha=0.7)
    bars2 = ax4.bar(x + width/2, cvar_values, width, label='CVaR (95%)', color='purple', alpha=0.7)
    ax4.set_ylabel('数值', fontsize=10)
    ax4.set_title('风险价值对比', fontsize=11, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(categories)
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3, axis='y')

    apply_chinese_font(axes)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_summary_table(eval_results, selected, model_results, output_path):
    """绘制汇总表格（DCC-GARCH 版本）"""
    print("[绘图 8/8] 汇总表格...")

    metrics = eval_results['metrics']
    model_params = model_results['model_params']

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # 创建汇总表格数据
    table_data = [
        ['数据配置', ''],
        ['现货列名', selected.get('spot', 'N/A')],
        ['期货列名', selected.get('futures', 'N/A')],
        ['数据期间', f'{eval_results["start_date"]} 至 {eval_results["end_date"]}'],
        ['样本量', f'{len(eval_results["returns_unhedged"])} 天'],
        ['', ''],
        ['模型参数', ''],
        ['模型类型', f'DCC-GARCH({model_params["p"]},{model_params["q"]})'],
        ['分布假设', model_params.get('dist', 'norm')],
        ['税点调整', f'{eval_results.get("tax_rate", 0.13):.1%}'],
        ['', ''],
        ['套保效果', ''],
        ['方差降低比例', f'{metrics["variance_reduction"]:.2%}'],
        ['Ederington指标', f'{metrics["ederington"]:.4f}'],
        ['', ''],
        ['收益率统计', ''],
        ['传统套保收益率均值 (h=1)', f'{metrics["mean_traditional"]:.6f}'],
        ['动态套保收益率均值 (DCC)', f'{metrics["mean_hedged"]:.6f}'],
        ['传统套保收益率标准差', f'{metrics["std_traditional"]:.6f}'],
        ['动态套保收益率标准差', f'{metrics["std_hedged"]:.6f}'],
        ['', ''],
        ['风险指标', ''],
        ['传统套保夏普比率', f'{metrics["sharpe_traditional"]:.4f}'],
        ['动态套保夏普比率', f'{metrics["sharpe_hedged"]:.4f}'],
        ['传统套保最大回撤', f'{metrics["max_dd_traditional"]:.2%}'],
        ['动态套保最大回撤', f'{metrics["max_dd_hedged"]:.2%}'],
        ['', ''],
        ['风险价值', ''],
        ['传统套保 VaR(95%)', f'{metrics["var_95_traditional"]:.6f}'],
        ['动态套保 VaR(95%)', f'{metrics["var_95_hedged"]:.6f}'],
        ['传统套保 CVaR(95%)', f'{metrics["cvar_95_traditional"]:.6f}'],
        ['动态套保 CVaR(95%)', f'{metrics["cvar_95_hedged"]:.6f}'],
    ]

    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                     colWidths=[0.4, 0.6])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # 设置单元格样式（蓝色主题）
    for i in range(len(table_data)):
        if table_data[i][1] == '' and table_data[i][0] != '':
            table[(i, 0)].set_facecolor('#3498db')
            table[(i, 1)].set_facecolor('#3498db')
            table[(i, 0)].set_text_props(weight='bold', color='white')
            table[(i, 1)].set_text_props(weight='bold', color='white')
        elif table_data[i][0] == '':
            table[(i, 0)].set_facecolor('white')
            table[(i, 1)].set_facecolor('white')
        elif i % 2 == 0:
            table[(i, 0)].set_facecolor('#f0f0f0')
            table[(i, 1)].set_facecolor('#f0f0f0')

    apply_chinese_font(ax)
    for key, cell in table.get_celld().items():
        cell.set_text_props(fontproperties=CHINESE_FONT)

    # 动态生成标题
    model_name = f"DCC-GARCH({model_params['p']},{model_params['q']})"
    ax.set_title(f'{model_name} 套保策略回测报告汇总', fontsize=14, fontweight='bold', pad=20)

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def generate_html_report(data, model_results, eval_results, selected, output_path):
    """生成 HTML 报告（DCC-GARCH 版本）"""
    print("\n[生成 HTML 报告]...")

    metrics = eval_results['metrics']
    model_params = model_results['model_params']

    # 计算 DCC-GARCH 特有指标
    rho_t = model_results['rho_t']
    h_actual = model_results['h_actual']

    # 动态生成模型名称
    model_name = f"DCC-GARCH({model_params['p']},{model_params['q']})"
    dist_name = "正态分布" if model_params.get('dist') == 'norm' else "t分布"

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{model_name} 套保策略回测报告</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>{model_name} 套保策略回测报告</h1>

        <h2>📊 数据配置</h2>
        <table>
            <tr><th>项目</th><th>值</th></tr>
            <tr><td>现货列名</td><td>{selected.get('spot', 'N/A')}</td></tr>
            <tr><td>期货列名</td><td>{selected.get('futures', 'N/A')}</td></tr>
            <tr><td>数据期间</td><td>{eval_results["start_date"]} 至 {eval_results["end_date"]}</td></tr>
            <tr><td>样本量</td><td>{len(eval_results["returns_unhedged"])} 天</td></tr>
        </table>

        <h2>⚙️ 模型参数</h2>
        <table>
            <tr><th>参数</th><th>值</th></tr>
            <tr><td>模型类型</td><td>{model_name}</td></tr>
            <tr><td>分布假设</td><td>{dist_name}</td></tr>
        </table>

        <h2>🎯 核心指标</h2>
        <div class="metric">
            <div class="metric-title">套保比例均值</div>
            <div class="metric-value">{h_actual.mean():.4f}</div>
        </div>
        <div class="metric">
            <div class="metric-title">动态相关系数均值</div>
            <div class="metric-value">{rho_t.mean():.4f}</div>
        </div>
        <div class="metric">
            <div class="metric-title">方差降低比例</div>
            <div class="metric-value">{metrics["variance_reduction"]:.2%}</div>
        </div>
        <div class="metric">
            <div class="metric-title">Ederington指标</div>
            <div class="metric-value">{metrics["ederington"]:.4f}</div>
        </div>
        <div class="metric">
            <div class="metric-title">动态套保夏普比率</div>
            <div class="metric-value">{metrics["sharpe_hedged"]:.4f}</div>
        </div>
        <div class="metric">
            <div class="metric-title">动态套保最大回撤</div>
            <div class="metric-value">{metrics["max_dd_hedged"]:.2%}</div>
        </div>

        <h2>📈 详细结果</h2>
        <h3>价格走势</h3>
        <img src="figures/1_price_series.png" alt="价格走势图">

        <h3>收益率分析</h3>
        <img src="figures/2_returns.png" alt="收益率分布图">

        <h3>动态相关系数（DCC-GARCH 特有）</h3>
        <img src="figures/3_dcc_correlation.png" alt="动态相关系数图">

        <h3>套保比例与相关系数</h3>
        <img src="figures/4_hedge_ratio.png" alt="套保比例与相关系数对比">

        <h3>回测净值曲线</h3>
        <img src="figures/5_backtest_results.png" alt="净值曲线图">

        <h3>回撤分析</h3>
        <img src="figures/6_drawdown.png" alt="回撤曲线图">

        <h3>性能指标对比</h3>
        <img src="figures/7_performance_metrics.png" alt="性能指标图">

        <h3>汇总表格</h3>
        <img src="figures/8_summary_table.png" alt="汇总表格">

        <h2>📋 完整指标表</h2>
        <table>
            <tr><th>指标</th><th>传统套保 (h=1)</th><th>动态套保 (DCC)</th></tr>
            <tr><td>收益率均值</td><td>{metrics["mean_unhedged"]:.6f}</td><td>{metrics["mean_hedged"]:.6f}</td></tr>
            <tr><td>收益率标准差</td><td>{metrics["std_unhedged"]:.6f}</td><td>{metrics["std_hedged"]:.6f}</td></tr>
            <tr><td>夏普比率</td><td>{metrics["sharpe_unhedged"]:.4f}</td><td>{metrics["sharpe_hedged"]:.4f}</td></tr>
            <tr><td>最大回撤</td><td>{metrics["max_dd_unhedged"]:.2%}</td><td>{metrics["max_dd_hedged"]:.2%}</td></tr>
            <tr><td>VaR (95%)</td><td>{metrics["var_95_unhedged"]:.6f}</td><td>{metrics["var_95_hedged"]:.6f}</td></tr>
            <tr><td>CVaR (95%)</td><td>{metrics["cvar_95_unhedged"]:.6f}</td><td>{metrics["cvar_95_hedged"]:.6f}</td></tr>
        </table>

        <div style="text-align: center; margin-top: 50px; color: #7f8c8d;">
            <p>报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>{model_name} 套保策略分析系统</p>
        </div>
    </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  ✓ 已保存: {output_path}")


def generate_dcc_garch_report(data, model_results, eval_results, selected, config, output_dir='outputs', restrict_to_recent_months=False):
    """
    生成 DCC-GARCH 所有报告和图表

    Parameters:
    -----------
    data : pd.DataFrame
        数据
    model_results : dict
        模型结果
    eval_results : dict
        回测评估结果
    selected : dict
        列名配置
    config : ModelConfig
        模型配置
    output_dir : str
        输出目录
    restrict_to_recent_months : bool
        是否只显示最近三个月数据

    Returns:
    --------
    dict
        {'html_path': str}
    """
    print("\n" + "=" * 60)
    print("生成 DCC-GARCH 分析报告")
    print("=" * 60)

    os.makedirs(f'{output_dir}/figures', exist_ok=True)

    # 生成所有图表
    plot_price_series(data, f'{output_dir}/figures/1_price_series.png', restrict_to_recent_months)
    plot_returns(data, f'{output_dir}/figures/2_returns.png', restrict_to_recent_months)
    plot_dcc_correlation(data, model_results, f'{output_dir}/figures/3_dcc_correlation.png', restrict_to_recent_months)
    plot_hedge_ratio_and_correlation(data, model_results, f'{output_dir}/figures/4_hedge_ratio.png', restrict_to_recent_months)
    plot_backtest_results(data, eval_results, f'{output_dir}/figures/5_backtest_results.png', restrict_to_recent_months)
    plot_drawdown(data, eval_results, f'{output_dir}/figures/6_drawdown.png', restrict_to_recent_months)
    plot_performance_metrics(eval_results, f'{output_dir}/figures/7_performance_metrics.png')
    plot_summary_table(eval_results, selected, model_results, f'{output_dir}/figures/8_summary_table.png')

    # 生成 HTML 报告
    generate_html_report(data, model_results, eval_results, selected, f'{output_dir}/report.html')

    print("\n" + "=" * 60)
    print("✓ DCC-GARCH 报告生成完成！")
    print("=" * 60)
    print(f"\n📁 输出目录: {output_dir}")
    print(f"  - {output_dir}/report.html  ⭐ (推荐查看)")
    print(f"  - {output_dir}/figures/ (所有图表)")

    return {'html_path': f'{output_dir}/report.html'}
