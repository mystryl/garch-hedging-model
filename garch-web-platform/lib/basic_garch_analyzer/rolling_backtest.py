"""
滚动回测模块
模拟实际套保操作，随机抽取多个时间点进行60天回测
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import os
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

# 先设置绘图风格
sns.set_style('whitegrid')

# 配置中文字体（必须在 set_style 之后）
from basic_garch_analyzer.font_config import setup_chinese_font
setup_chinese_font()

# 创建全局的中文字体属性对象（从字体文件路径直接加载）
font_path = '/System/Library/Fonts/Hiragino Sans GB.ttc'
if os.path.exists(font_path):
    CHINESE_FONT = fm.FontProperties(fname=font_path)
else:
    CHINESE_FONT = None

# 交割月常量
DELIVERY_MONTHS = [1, 5, 10]  # 1月、5月、10月为交割月份


def apply_chinese_font(fig_or_ax):
    """
    应用中文字体到图表的所有文本元素
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


def is_delivery_month(date: pd.Timestamp) -> bool:
    """
    判断是否为交割月份（1、5、10月）

    Parameters:
    -----------
    date : pd.Timestamp
        日期

    Returns:
    --------
    bool : 是否为交割月
    """
    return date.month in DELIVERY_MONTHS


def is_near_delivery_month(date: pd.Timestamp, window_days: int = 30) -> bool:
    """
    判断是否临近交割月份（交割月前后window_days天内）

    Parameters:
    -----------
    date : pd.Timestamp
        日期
    window_days : int
        预警窗口天数（默认30天）

    Returns:
    --------
    bool : 是否临近交割月
    """
    # 只检查是否在交割月本身
    if date.month in DELIVERY_MONTHS:
        return True

    # 检查是否在交割月前 window_days 天内
    for dm in DELIVERY_MONTHS:
        if dm > date.month:
            # 计算到下一个交割月的天数
            next_delivery = pd.Timestamp(f'{date.year}-{dm:02d}-01')
            days_diff = (next_delivery - date).days
            if 0 <= days_diff <= window_days:
                return True

    return False


def select_backtest_start_dates(data: pd.DataFrame, n_periods: int = 5,
                                 min_gap_days: int = 180,
                                 window_days: int = 60,
                                 seed: int = None) -> List[pd.Timestamp]:
    """
    随机选择回测起始日期

    规则：
    1. 避开1、5、10交割月份及其前后90天
    2. 每个起始日期间隔至少 min_gap_days
    3. 确保有足够的后续数据（至少window_days）

    Parameters:
    -----------
    data : pd.DataFrame
        数据（包含 date 列）
    n_periods : int
        选择的时间点数量
    min_gap_days : int
        起始日期之间的最小间隔天数
    window_days : int
        回测窗口天数
    seed : int
        随机种子（用于复现）

    Returns:
    --------
    selected_dates : List[pd.Timestamp]
        选中的起始日期列表
    """
    if seed is not None:
        np.random.seed(seed)

    # 获取所有可能的起始日期（使用 .copy() 避免修改原始数据）
    data_copy = data.copy()
    data_copy['month'] = data_copy['date'].dt.month
    data_copy['year'] = data_copy['date'].dt.year

    # 过滤掉临近交割月的日期
    valid_mask = ~data_copy['date'].apply(is_near_delivery_month)
    valid_data = data_copy[valid_mask].copy()

    # 确保有足够的后续数据
    max_start_idx = len(valid_data) - window_days
    valid_data = valid_data.iloc[:max_start_idx].reset_index(drop=True)

    print(f"\n[回测起始日期选择]")
    print(f"  总数据量: {len(data)}")
    print(f"  有效起始点（避开交割月）: {len(valid_data)}")

    # 随机选择起始日期
    selected_dates = []
    attempts = 0
    max_attempts = 1000

    while len(selected_dates) < n_periods and attempts < max_attempts:
        attempts += 1

        # 随机选择一个候选日期
        idx = np.random.randint(0, len(valid_data))
        candidate = valid_data.loc[idx, 'date']

        # 检查与已选日期的距离
        valid = True
        for selected in selected_dates:
            if abs((candidate - selected).days) < min_gap_days:
                valid = False
                break

        if valid:
            selected_dates.append(candidate)
            print(f"  选择起始点 #{len(selected_dates)}: {candidate.date()} "
                  f"(月份={candidate.month})")

    if len(selected_dates) < n_periods:
        print(f"  ⚠️  警告: 仅找到 {len(selected_dates)} 个有效起始点")

    return sorted(selected_dates)


def run_single_period_backtest(data: pd.DataFrame, start_date: pd.Timestamp,
                               hedge_ratios: np.ndarray,
                               window_days: int = 60,
                               tax_rate: float = 0.13) -> Dict:
    """
    运行单个60天周期的回测

    Parameters:
    -----------
    data : pd.DataFrame
        完整数据
    start_date : pd.Timestamp
        回测起始日期
    hedge_ratios : np.ndarray
        套保比例序列
    window_days : int
        回测窗口天数
    tax_rate : float
        增值税率（现货收益需要考虑增值税）

    Returns:
    --------
    result : Dict
        回测结果
    """
    # 找到起始日期在数据中的索引
    matching_rows = data[data['date'] == start_date]
    if len(matching_rows) == 0:
        raise ValueError(f"起始日期 {start_date} 不存在于数据中")
    start_idx = matching_rows.index[0]

    # 提取回测窗口数据
    end_idx = min(start_idx + window_days, len(data))
    period_data = data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

    # 对应的套保比例
    period_h = hedge_ratios[start_idx:end_idx]

    # 计算套保后收益率（考虑税点）
    # 现货收益需要除以(1+税率)，因为现货盈利需要缴纳增值税
    r_s = period_data['r_s'].values
    r_f = period_data['r_f'].values

    # 传统套保（固定 h=1，即现货:期货 = 1:1）
    r_traditional = r_s / (1 + tax_rate) - 1.0 * r_f
    # 动态套保（使用 GARCH 模型的时变套保比例）
    r_hedged = r_s / (1 + tax_rate) - period_h * r_f

    # 计算累计收益率
    cumulative_traditional = np.cumprod(1 + r_traditional)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    # 计算回撤
    running_max = np.maximum.accumulate(cumulative_hedged)
    drawdown = (cumulative_hedged - running_max) / running_max

    # 传统套保的回撤
    running_max_traditional = np.maximum.accumulate(cumulative_traditional)
    drawdown_traditional = (cumulative_traditional - running_max_traditional) / running_max_traditional

    # 计算指标
    total_return_traditional = cumulative_traditional[-1] - 1
    total_return_hedged = cumulative_hedged[-1] - 1

    annual_return_traditional = cumulative_traditional[-1] ** (252 / len(period_data)) - 1
    annual_return_hedged = cumulative_hedged[-1] ** (252 / len(period_data)) - 1

    std_traditional = np.std(r_traditional)
    std_hedged = np.std(r_hedged)

    # 计算最大回撤
    max_dd_traditional = np.min(drawdown_traditional)
    max_dd_hedged = np.min(drawdown)

    sharpe_traditional = np.mean(r_traditional) / np.std(r_traditional) if np.std(r_traditional) > 0 else 0
    sharpe_hedged = np.mean(r_hedged) / np.std(r_hedged) if np.std(r_hedged) > 0 else 0

    # 方差降低（相对于传统套保）
    variance_reduction = 1 - (std_hedged ** 2) / (std_traditional ** 2)

    # 计算该周期使用的平均套保比例
    avg_hedge_ratio = np.mean(period_h)
    median_hedge_ratio = np.median(period_h)
    std_hedge_ratio = np.std(period_h)

    return {
        'start_date': start_date,
        'end_date': period_data.iloc[-1]['date'],
        'period_days': len(period_data),
        'total_return_traditional': total_return_traditional,
        'total_return_hedged': total_return_hedged,
        'annual_return_traditional': annual_return_traditional,
        'annual_return_hedged': annual_return_hedged,
        'std_traditional': std_traditional,
        'std_hedged': std_hedged,
        'max_dd_traditional': max_dd_traditional,
        'max_dd_hedged': max_dd_hedged,
        'sharpe_traditional': sharpe_traditional,
        'sharpe_hedged': sharpe_hedged,
        'variance_reduction': variance_reduction,
        'cumulative_traditional': cumulative_traditional,
        'cumulative_hedged': cumulative_hedged,
        'drawdown': drawdown,
        'dates': period_data['date'].values,
        'avg_hedge_ratio': avg_hedge_ratio,
        'median_hedge_ratio': median_hedge_ratio,
        'std_hedge_ratio': std_hedge_ratio,
        'hedge_ratios': period_h
    }


def run_rolling_backtest(data: pd.DataFrame, hedge_ratios: np.ndarray,
                         n_periods: int = 5, window_days: int = 60,
                         seed: int = 42, tax_rate: float = 0.13) -> Dict:
    """
    运行滚动回测

    Parameters:
    -----------
    data : pd.DataFrame
        数据
    hedge_ratios : np.ndarray
        套保比例序列
    n_periods : int
        回测周期数
    window_days : int
        每个周期天数
    seed : int
        随机种子

    Returns:
    --------
    results : Dict
        回测结果汇总
    """
    print("\n" + "=" * 60)
    print("滚动回测分析")
    print("=" * 60)
    print(f"回测周期数: {n_periods}")
    print(f"每个周期: {window_days} 天")
    print(f"避开交割月: 1月、5月、10月")

    # 选择起始日期
    start_dates = select_backtest_start_dates(
        data, n_periods=n_periods, window_days=window_days, seed=seed
    )

    if len(start_dates) == 0:
        raise ValueError("无法找到有效的回测起始日期")

    # 运行每个周期的回测
    print(f"\n{'='*60}")
    print(f"开始回测 {len(start_dates)} 个周期...")
    print(f"{'='*60}")

    period_results = []

    for i, start_date in enumerate(start_dates, 1):
        print(f"\n[周期 {i}/{len(start_dates)}]")
        print(f"  起始日期: {start_date.date()}")

        result = run_single_period_backtest(
            data, start_date, hedge_ratios, window_days, tax_rate
        )

        period_results.append(result)

        print(f"  结束日期: {result['end_date'].date()}")
        print(f"  实际天数: {result['period_days']}")
        print(f"  传统套保收益率 (h=1): {result['total_return_traditional']:.2%}")
        print(f"  动态套保收益率 (GARCH): {result['total_return_hedged']:.2%}")
        print(f"  方差降低: {result['variance_reduction']:.2%}")

    # 汇总统计
    print(f"\n{'='*60}")
    print("回测汇总")
    print(f"{'='*60}")

    avg_return_traditional = np.mean([r['total_return_traditional'] for r in period_results])
    avg_return_hedged = np.mean([r['total_return_hedged'] for r in period_results])
    avg_variance_reduction = np.mean([r['variance_reduction'] for r in period_results])
    avg_max_dd_traditional = np.mean([r['max_dd_traditional'] for r in period_results])
    avg_max_dd_hedged = np.mean([r['max_dd_hedged'] for r in period_results])

    print(f"平均收益率（传统套保 h=1）: {avg_return_traditional:.2%}")
    print(f"平均收益率（动态套保 GARCH）: {avg_return_hedged:.2%}")
    print(f"平均方差降低: {avg_variance_reduction:.2%}")
    print(f"平均最大回撤（传统套保）: {avg_max_dd_traditional:.2%}")
    print(f"平均最大回撤（动态套保）: {avg_max_dd_hedged:.2%}")

    return {
        'period_results': period_results,
        'n_periods': len(period_results),
        'window_days': window_days,
        'avg_return_traditional': avg_return_traditional,
        'avg_return_hedged': avg_return_hedged,
        'avg_variance_reduction': avg_variance_reduction,
        'avg_max_dd_traditional': avg_max_dd_traditional,
        'avg_max_dd_hedged': avg_max_dd_hedged
    }


def plot_rolling_backtest_results(results: Dict, output_path: str):
    """
    绘制滚动回测结果

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("\n[绘制滚动回测图表]...")

    period_results = results['period_results']
    n_periods = len(period_results)

    # 创建子图
    fig, axes = plt.subplots(n_periods, 1, figsize=(14, 4 * n_periods))

    if n_periods == 1:
        axes = [axes]

    for i, (result, ax) in enumerate(zip(period_results, axes)):
        # 绘制净值曲线
        ax.plot(result['dates'], result['cumulative_unhedged'],
                label='未套保', linewidth=2, alpha=0.7, color='red')
        ax.plot(result['dates'], result['cumulative_hedged'],
                label='套保后', linewidth=2, alpha=0.7, color='green')

        # 标注
        title = (f"周期 {i+1}: {result['start_date'].date()} - {result['end_date'].date()} "
                f"({result['period_days']}天)\n"
                f"收益率: 未套保={result['total_return_unhedged']:.1%}, "
                f"套保={result['total_return_hedged']:.1%}, "
                f"方差降低={result['variance_reduction']:.1%}")

        ax.set_title(title, fontsize=11, fontweight='bold', fontproperties=CHINESE_FONT)
        ax.set_ylabel('净值', fontsize=10, fontproperties=CHINESE_FONT)
        ax.legend(loc='best', prop=CHINESE_FONT)
        ax.grid(True, alpha=0.3)

        # 设置x轴日期格式
        ax.tick_params(axis='x', rotation=45)

    axes[-1].set_xlabel('日期', fontsize=10, fontproperties=CHINESE_FONT)

    # 应用中文字体到所有元素
    apply_chinese_font(axes)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def plot_rolling_nav_curve(results: Dict, output_path: str):
    """
    绘制滚动回测净值曲线（兼容HTML报告格式）

    为每个周期生成独立的净值曲线图，2x3布局（最多6个周期）
    主坐标轴：净值曲线，次坐标轴：套保比例曲线

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("[绘图 5/8] 滚动回测净值曲线图...")

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

            # 绘制传统套保（h=1）和动态套保后曲线（主坐标轴）
            ax.plot(result['dates'], result['cumulative_traditional'],
                    label='传统套保 (h=1)', linewidth=2, alpha=0.7, color='red')
            ax.plot(result['dates'], result['cumulative_hedged'],
                    label='动态套保 (GARCH)', linewidth=2, alpha=0.8, color='green')

            # 绘制套保比例曲线（次坐标轴）
            ax2.plot(result['dates'], result['hedge_ratios'],
                    label='套保比例', linewidth=1.5, alpha=0.6,
                    color='blue', linestyle='--')

            # 标题包含周期信息和收益率
            title = (f"周期 {i+1}: {result['start_date'].date()} - {result['end_date'].date()}\n"
                     f"收益率: 传统套保={result['total_return_traditional']:.2%}, "
                     f"动态套保={result['total_return_hedged']:.2%}, "
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
    绘制滚动回测回撤曲线（兼容HTML报告格式）

    为每个周期生成独立的回撤曲线图，2x3布局（最多6个周期）
    主坐标轴：回撤曲线，次坐标轴：套保比例曲线

    Parameters:
    -----------
    results : Dict
        回测结果
    output_path : str
        输出文件路径
    """
    print("[绘图 6/8] 滚动回测回撤曲线图...")

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
    print("\n[绘制周期对比图]...")

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


def _generate_rolling_backtest_html(data: pd.DataFrame, results: Dict, output_path: str):
    """
    生成滚动回测HTML报告

    Parameters:
    -----------
    data : pd.DataFrame
        原始数据
    results : Dict
        滚动回测结果
    output_path : str
        HTML输出路径
    """
    print("\n[生成滚动回测 HTML 报告]...")

    period_results = results['period_results']

    # 计算数据统计
    start_date = data['date'].min().strftime('%Y-%m-%d')
    end_date = data['date'].max().strftime('%Y-%m-%d')
    total_days = len(data)

    # 生成周期汇总表格HTML
    period_rows = ""
    for i, r in enumerate(period_results, 1):
        period_rows += f"""
            <tr>
                <td>周期 {i}</td>
                <td>{r['start_date'].strftime('%Y-%m-%d')}</td>
                <td>{r['end_date'].strftime('%Y-%m-%d')}</td>
                <td>{r['period_days']}</td>
                <td>{r['total_return_traditional']:.2%}</td>
                <td>{r['total_return_hedged']:.2%}</td>
                <td>{r['variance_reduction']:.2%}</td>
                <td>{r['max_dd_hedged']:.2%}</td>
                <td>{r['sharpe_hedged']:.4f}</td>
            </tr>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Basic GARCH 滚动回测报告</title>
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
        <h1>Basic GARCH 滚动回测报告</h1>

        <h2>📊 数据配置</h2>
        <table>
            <tr><th>项目</th><th>值</th></tr>
            <tr><td>数据期间</td><td>{start_date} 至 {end_date}</td></tr>
            <tr><td>样本量</td><td>{total_days} 天</td></tr>
            <tr><td>回测周期数</td><td>{results['n_periods']}</td></tr>
            <tr><td>每个周期天数</td><td>{results['window_days']} 天</td></tr>
        </table>

        <h2>🎯 核心指标（平均）</h2>
        <div class="metric">
            <div class="metric-title">平均收益率（传统套保 h=1）</div>
            <div class="metric-value">{results['avg_return_traditional']:.2%}</div>
        </div>
        <div class="metric">
            <div class="metric-title">平均收益率（动态套保 GARCH）</div>
            <div class="metric-value">{results['avg_return_hedged']:.2%}</div>
        </div>
        <div class="metric">
            <div class="metric-title">平均方差降低</div>
            <div class="metric-value">{results['avg_variance_reduction']:.2%}</div>
        </div>
        <div class="metric">
            <div class="metric-title">平均最大回撤（动态套保）</div>
            <div class="metric-value">{results['avg_max_dd_hedged']:.2%}</div>
        </div>

        <h2>📈 回测结果</h2>
        <h3>滚动回测净值曲线</h3>
        <img src="figures/5_backtest_results.png" alt="滚动回测净值曲线图">

        <h3>滚动回测回撤曲线</h3>
        <img src="figures/6_drawdown.png" alt="滚动回测回撤曲线图">

        <h2>📋 各周期详情</h2>
        <table>
            <tr>
                <th>周期</th>
                <th>起始日期</th>
                <th>结束日期</th>
                <th>天数</th>
                <th>传统套保收益率 (h=1)</th>
                <th>动态套保收益率 (GARCH)</th>
                <th>方差降低</th>
                <th>最大回撤（动态套保）</th>
                <th>夏普比率（动态套保）</th>
            </tr>
            {period_rows}
        </table>

        <div style="text-align: center; margin-top: 50px; color: #7f8c8d;">
            <p>报告生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Basic GARCH 滚动回测分析系统</p>
        </div>
    </div>
</body>
</html>
    """

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  ✓ 已保存: {output_path}")


def generate_rolling_backtest_report(data: pd.DataFrame, results: Dict,
                                      output_dir: str, generate_html: bool = False):
    """
    生成滚动回测报告

    Parameters:
    -----------
    data : pd.DataFrame
        数据
    results : Dict
        回测结果
    output_dir : str
        输出目录
    generate_html : bool
        是否生成HTML兼容图表（用于替换全样本回测报告中的图表5和6）
    """
    print(f"\n[生成滚动回测报告]...")

    import os
    os.makedirs(output_dir, exist_ok=True)
    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    # 1. 绘制图表
    print("\n[1/3] 生成可视化图表...")

    # 如果需要生成HTML兼容图表，使用与HTML报告相同的文件名
    if generate_html:
        # 生成HTML报告兼容的图表（替换图表5和6）
        path = os.path.join(figures_dir, '5_backtest_results.png')
        plot_rolling_nav_curve(results, path)

        path = os.path.join(figures_dir, '6_drawdown.png')
        plot_rolling_drawdown(results, path)
    else:
        # 生成滚动回测专用图表
        path = os.path.join(figures_dir, '1_periods_nav.png')
        plot_rolling_backtest_results(results, path)

        path = os.path.join(figures_dir, '2_periods_comparison.png')
        plot_period_comparison(results, path)

    # 2. 生成Excel报告
    print("\n[2/3] 生成表格报告...")

    period_results = results['period_results']

    # 创建周期详情表
    period_data = []
    for i, r in enumerate(period_results, 1):
        period_data.append({
            '周期': f"周期{i}",
            '起始日期': r['start_date'].date(),
            '结束日期': r['end_date'].date(),
            '天数': r['period_days'],
            '起始月份': r['start_date'].month,
            '传统套保收益率 (h=1)': f"{r['total_return_traditional']:.2%}",
            '动态套保收益率 (GARCH)': f"{r['total_return_hedged']:.2%}",
            '收益率改善': f"{(r['total_return_hedged'] - r['total_return_traditional']):.2%}",
            '方差降低': f"{r['variance_reduction']:.2%}",
            '最大回撤（动态套保）': f"{r['max_dd_hedged']:.2%}",
            '夏普比率（动态套保）': f"{r['sharpe_hedged']:.4f}"
        })

    df_periods = pd.DataFrame(period_data)

    # 保存Excel
    excel_path = os.path.join(output_dir, 'rolling_backtest_report.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_periods.to_excel(writer, sheet_name='各周期详情', index=False)

        # 汇总表
        summary_data = {
            '指标': [
                '回测周期数',
                '每个周期天数',
                '平均收益率（传统套保 h=1）',
                '平均收益率（动态套保 GARCH）',
                '平均方差降低',
                '平均最大回撤（动态套保）',
            ],
            '数值': [
                results['n_periods'],
                results['window_days'],
                f"{results['avg_return_traditional']:.2%}",
                f"{results['avg_return_hedged']:.2%}",
                f"{results['avg_variance_reduction']:.2%}",
                f"{results['avg_max_dd_hedged']:.2%}",
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='汇总', index=False)

    print(f"  ✓ Excel报告: {excel_path}")

    # 保存CSV
    csv_path = os.path.join(output_dir, 'rolling_backtest_report.csv')
    df_periods.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ CSV报告: {csv_path}")

    # 3. 生成HTML报告（新增）
    html_path = None
    if generate_html:
        print("\n[3/3] 生成HTML报告...")
        html_path = os.path.join(output_dir, 'report.html')
        _generate_rolling_backtest_html(data, results, html_path)

    print(f"\n✓ 滚动回测报告生成完成！")
    print(f"📁 输出目录: {output_dir}")

    return {
        'excel_path': excel_path,
        'csv_path': csv_path,
        'figures_dir': figures_dir,
        'html_path': html_path  # 新增返回值
    }
