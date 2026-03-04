"""
共享的绘图函数
从 Basic GARCH 的 rolling_backtest.py 抽取通用绘图逻辑
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from typing import Dict

# 配置中文字体
font_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'
if os.path.exists(font_path):
    CHINESE_FONT = fm.FontProperties(fname=font_path)
else:
    CHINESE_FONT = None


def apply_chinese_font(fig_or_ax):
    """
    应用中文字体到图表的所有文本元素

    Parameters:
    -----------
    fig_or_ax : matplotlib.figure.Figure or matplotlib.axes.Axes or np.ndarray
        图表对象
    """
    if CHINESE_FONT is None:
        return

    # 如果传入的是 numpy ndarray (axes 数组)
    if hasattr(fig_or_ax, 'flatten') and not hasattr(fig_or_ax, 'axes'):
        axes_list = fig_or_ax.flatten()
        fig = axes_list[0].figure if len(axes_list) > 0 else None
    # 如果传入的是 Axes
    elif hasattr(fig_or_ax, 'figure'):
        axes_list = [fig_or_ax]
        fig = fig_or_ax.figure
    # 如果传入的是 Figure
    else:
        fig = fig_or_ax
        axes_list = fig.axes

    # 应用字体到所有文本元素
    for ax in axes_list:
        # 标题和标签
        if ax.get_title():
            ax.set_title(ax.get_title(), fontproperties=CHINESE_FONT)
        if ax.get_xlabel():
            ax.set_xlabel(ax.get_xlabel(), fontproperties=CHINESE_FONT)
        if ax.get_ylabel():
            ax.set_ylabel(ax.get_ylabel(), fontproperties=CHINESE_FONT)

        # 刻度标签
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(CHINESE_FONT)

        # 图例
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontproperties(CHINESE_FONT)

        # 注释文本
        for text in ax.texts:
            text.set_fontproperties(CHINESE_FONT)


def plot_rolling_nav_curve(results: Dict, output_path: str):
    """
    绘制滚动回测净值曲线（2x3布局）

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("[绘图] 滚动回测净值曲线图...")

    period_results = results['period_results']
    n_periods = len(period_results)

    # 计算子图布局（2行3列）
    ncols = min(3, n_periods)
    nrows = (n_periods + ncols - 1) // ncols

    # 创建图形
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 5 * nrows))
    fig.suptitle('滚动回测：各周期套保前后净值曲线与套保比例', fontsize=14, fontweight='bold', fontproperties=CHINESE_FONT, y=0.995)

    # 如果只有一行，确保axes是2D数组
    if nrows == 1:
        axes = axes.reshape(1, -1)

    # 为每个周期绘制独立的净值曲线
    for i in range(nrows * ncols):
        row = i // ncols
        col = i % ncols
        ax = axes[row, col]

        if i < n_periods:
            result = period_results[i]

            # 创建次坐标轴（用于套保比例）
            ax2 = ax.twinx()

            # 绘制未套保和套保后曲线（主坐标轴）
            ax.plot(result['dates'], result['cumulative_unhedged'],
                    label='未套保', linewidth=2, alpha=0.7, color='red')
            ax.plot(result['dates'], result['cumulative_hedged'],
                    label='套保后', linewidth=2, alpha=0.8, color='green')

            # 绘制套保比例曲线（次坐标轴）
            ax2.plot(result['dates'], result['hedge_ratios'],
                    label='套保比例', linewidth=1.5, alpha=0.6,
                    color='blue', linestyle='--')

            # 标题包含周期信息和收益率
            title = (f"周期 {i+1}: {result['start_date'].date()} - {result['end_date'].date()}\n"
                     f"收益率: 未套保={result['total_return_unhedged']:.2%}, "
                     f"套保={result['total_return_hedged']:.2%}, "
                     f"方差降低={result['variance_reduction']:.1%}")
            ax.set_title(title, fontsize=9, fontweight='bold', fontproperties=CHINESE_FONT)

            # 主坐标轴（净值）
            ax.set_ylabel('净值', fontsize=9, fontproperties=CHINESE_FONT, color='black')
            ax.tick_params(axis='y', labelsize=8, labelcolor='black')
            ax.grid(True, alpha=0.3)

            # 次坐标轴（套保比例）
            ax2.set_ylabel('套保比例', fontsize=9, fontproperties=CHINESE_FONT, color='blue')
            ax2.tick_params(axis='y', labelsize=8, labelcolor='blue')
            ax2.set_ylim(0, max(1.0, np.max(result['hedge_ratios']) * 1.1))

            # 合并图例（主坐标轴和次坐标轴）
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                    loc='best', prop=CHINESE_FONT, fontsize=7)

            # 设置x轴日期格式
            ax.tick_params(axis='x', rotation=45, labelsize=8)
            ax2.tick_params(axis='x', rotation=45, labelsize=8)

            # 应用中文字体
            apply_chinese_font(ax)
        else:
            # 隐藏多余的子图
            ax.axis('off')

    # 添加总x轴标签（只有最后一行）
    for col in range(ncols):
        axes[nrows-1, col].set_xlabel('日期', fontsize=10, fontproperties=CHINESE_FONT)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_rolling_drawdown(results: Dict, output_path: str):
    """
    绘制滚动回测回撤曲线（2x3布局）

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("[绘图] 滚动回测回撤曲线图...")

    period_results = results['period_results']
    n_periods = len(period_results)

    # 计算子图布局（2行3列）
    ncols = min(3, n_periods)
    nrows = (n_periods + ncols - 1) // ncols

    # 创建图形
    fig, axes = plt.subplots(nrows, ncols, figsize=(18, 4 * nrows))
    fig.suptitle('滚动回测：各周期套保组合回撤曲线与套保比例', fontsize=14, fontweight='bold', fontproperties=CHINESE_FONT, y=0.995)

    # 如果只有一行，确保axes是2D数组
    if nrows == 1:
        axes = axes.reshape(1, -1)

    # 为每个周期绘制独立的回撤曲线
    for i in range(nrows * ncols):
        row = i // ncols
        col = i % ncols
        ax = axes[row, col]

        if i < n_periods:
            result = period_results[i]

            # 创建次坐标轴（用于套保比例）
            ax2 = ax.twinx()

            # 绘制回撤曲线（主坐标轴）
            ax.plot(result['dates'], result['drawdown'],
                    linewidth=2, color='orange', alpha=0.8, label='回撤')

            # 填充回撤区域
            ax.fill_between(result['dates'], 0, result['drawdown'],
                            alpha=0.3, color='orange')

            # 标注最大回撤点
            max_dd_idx = np.argmin(result['drawdown'])
            max_dd_date = result['dates'][max_dd_idx]
            max_dd_value = result['drawdown'][max_dd_idx]

            ax.plot(max_dd_date, max_dd_value,
                    'v', markersize=10, color='darkred',
                    label=f'最大回撤: {max_dd_value:.2%}')

            # 绘制套保比例曲线（次坐标轴）
            ax2.plot(result['dates'], result['hedge_ratios'],
                    label='套保比例', linewidth=1.5, alpha=0.6,
                    color='blue', linestyle='--')

            # 标题
            title = f"周期 {i+1}: {result['start_date'].date()} - {result['end_date'].date()}"
            ax.set_title(title, fontsize=9, fontweight='bold', fontproperties=CHINESE_FONT)

            # 主坐标轴（回撤）
            ax.set_ylabel('回撤比例', fontsize=9, fontproperties=CHINESE_FONT, color='black')
            ax.tick_params(axis='y', labelsize=8, labelcolor='black')
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1%}'))
            ax.grid(True, alpha=0.3)

            # 次坐标轴（套保比例）
            ax2.set_ylabel('套保比例', fontsize=9, fontproperties=CHINESE_FONT, color='blue')
            ax2.tick_params(axis='y', labelsize=8, labelcolor='blue')
            ax2.set_ylim(0, max(1.0, np.max(result['hedge_ratios']) * 1.1))

            # 合并图例（主坐标轴和次坐标轴）
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2,
                    loc='best', prop=CHINESE_FONT, fontsize=7)

            # 设置x轴日期格式
            ax.tick_params(axis='x', rotation=45, labelsize=8)
            ax2.tick_params(axis='x', rotation=45, labelsize=8)

            # 应用中文字体
            apply_chinese_font(ax)
        else:
            # 隐藏多余的子图
            ax.axis('off')

    # 添加总x轴标签（只有最后一行）
    for col in range(ncols):
        axes[nrows-1, col].set_xlabel('日期', fontsize=10, fontproperties=CHINESE_FONT)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_period_comparison(results: Dict, output_path: str):
    """
    绘制各周期对比图

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("\n[绘图] 周期对比图...")

    period_results = results['period_results']

    # 提取数据
    periods = [f"周期{i+1}\n{r['start_date'].month}/{r['start_date'].day}"
               for i, r in enumerate(period_results)]

    returns_unhedged = [r['total_return_unhedged'] for r in period_results]
    returns_hedged = [r['total_return_hedged'] for r in period_results]
    variance_reduction = [r['variance_reduction'] for r in period_results]
    max_dd_hedged = [r['max_dd_hedged'] for r in period_results]

    # 创建子图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. 收益率对比
    ax1 = axes[0, 0]
    x = np.arange(len(periods))
    width = 0.35
    bars1 = ax1.bar(x - width/2, returns_unhedged, width, label='未套保',
                   color='red', alpha=0.7, edgecolor='black')
    bars2 = ax1.bar(x + width/2, returns_hedged, width, label='套保后',
                   color='green', alpha=0.7, edgecolor='black')
    ax1.set_ylabel('收益率', fontproperties=CHINESE_FONT)
    ax1.set_title('各周期收益率对比', fontproperties=CHINESE_FONT, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(periods)
    ax1.legend(prop=CHINESE_FONT)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    # 添加数值标签
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1%}', ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=8)

    # 2. 方差降低
    ax2 = axes[0, 1]
    bars = ax2.bar(periods, variance_reduction, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.set_ylabel('方差降低比例', fontproperties=CHINESE_FONT)
    ax2.set_title('各周期方差降低', fontproperties=CHINESE_FONT, fontweight='bold')
    ax2.set_xticklabels(periods)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=np.mean(variance_reduction), color='red', linestyle='--',
               label=f'平均: {np.mean(variance_reduction):.1%}')
    ax2.legend(prop=CHINESE_FONT)

    for bar, val in zip(bars, variance_reduction):
        ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:.1%}', ha='center', va='bottom', fontsize=9)

    # 3. 最大回撤
    ax3 = axes[1, 0]
    bars = ax3.bar(periods, [v * 100 for v in max_dd_hedged],
                  color='orange', alpha=0.7, edgecolor='black')
    ax3.set_ylabel('最大回撤 (%)', fontproperties=CHINESE_FONT)
    ax3.set_title('各周期最大回撤（套保后）', fontproperties=CHINESE_FONT, fontweight='bold')
    ax3.set_xticklabels(periods)
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.axhline(y=np.mean(max_dd_hedged) * 100, color='red', linestyle='--',
               label=f'平均: {np.mean(max_dd_hedged):.1%}%')
    ax3.legend(prop=CHINESE_FONT)

    for bar, val in zip(bars, max_dd_hedged):
        ax3.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val:.1%}', ha='center', va='top', fontsize=9)

    # 4. 汇总表格
    ax4 = axes[1, 1]
    ax4.axis('tight')
    ax4.axis('off')

    table_data = [
        ['指标', '平均值'],
        ['平均收益率（未套保）', f"{results['avg_return_unhedged']:.2%}"],
        ['平均收益率（套保后）', f"{results['avg_return_hedged']:.2%}"],
        ['平均方差降低', f"{results['avg_variance_reduction']:.2%}"],
        ['平均最大回撤（套保后）', f"{results['avg_max_dd_hedged']:.2%}"],
        ['', ''],
        ['回测周期数', f"{results['n_periods']}"],
        ['每个周期天数', f"{results['window_days']}"],
    ]

    table = ax4.table(cellText=table_data, cellLoc='left', loc='center',
                     colWidths=[0.6, 0.4])

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    # 设置单元格样式
    for i in range(len(table_data)):
        if table_data[i][1] == '':
            table[(i, 0)].set_facecolor('white')
            table[(i, 1)].set_facecolor('white')
        elif i == 0:
            table[(i, 0)].set_facecolor('#3498db')
            table[(i, 1)].set_facecolor('#3498db')
            table[(i, 0)].set_text_props(weight='bold', color='white')
            table[(i, 1)].set_text_props(weight='bold', color='white')
        elif i % 2 == 0:
            table[(i, 0)].set_facecolor('#f0f0f0')
            table[(i, 1)].set_facecolor('#f0f0f0')

    for key, cell in table.get_celld().items():
        cell.set_text_props(fontproperties=CHINESE_FONT)

    ax4.set_title('回测汇总', fontproperties=CHINESE_FONT,
                  fontsize=12, fontweight='bold', pad=20)

    # 应用中文字体到所有子图
    apply_chinese_font(axes)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")
