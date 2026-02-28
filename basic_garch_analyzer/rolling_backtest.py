"""
滚动回测模块
模拟实际套保操作，随机抽取多个时间点进行60天回测
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

# 配置中文字体
try:
    from basic_garch_analyzer.font_config import setup_chinese_font, CHINESE_FONT
    setup_chinese_font()
except ImportError:
    # 回退到默认配置
    CHINESE_FONT = None

sns.set_style('whitegrid')

# 交割月常量
DELIVERY_MONTHS = [1, 5, 10]  # 1月、5月、10月为交割月份


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


def is_near_delivery_month(date: pd.Timestamp, window_days: int = 90) -> bool:
    """
    判断是否临近交割月份（交割月前window_days天内）

    Parameters:
    -----------
    date : pd.Timestamp
        日期
    window_days : int
        预警窗口天数

    Returns:
    --------
    bool : 是否临近交割月
    """
    year = date.year

    for dm in DELIVERY_MONTHS:
        # 计算当年的交割月日期
        delivery_date = pd.Timestamp(f'{year}-{dm:02d}-01')

        # 计算距离交割月的天数
        days_diff = (date - delivery_date).days

        # 如果在预警窗口内
        if -window_days <= days_diff <= window_days:
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
                               window_days: int = 60) -> Dict:
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

    # 计算套保后收益率
    r_hedged = period_data['r_s'].values - period_h * period_data['r_f'].values
    r_unhedged = period_data['r_s'].values

    # 计算累计收益率
    cumulative_unhedged = np.cumprod(1 + r_unhedged)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    # 计算回撤
    running_max = np.maximum.accumulate(cumulative_hedged)
    drawdown = (cumulative_hedged - running_max) / running_max

    # 计算指标
    total_return_unhedged = cumulative_unhedged[-1] - 1
    total_return_hedged = cumulative_hedged[-1] - 1

    annual_return_unhedged = cumulative_unhedged[-1] ** (252 / len(period_data)) - 1
    annual_return_hedged = cumulative_hedged[-1] ** (252 / len(period_data)) - 1

    std_unhedged = np.std(r_unhedged)
    std_hedged = np.std(r_hedged)

    # 计算最大回撤（复用已计算的 cumulative_unhedged）
    max_dd_unhedged = np.min(cumulative_unhedged / np.maximum.accumulate(cumulative_unhedged) - 1)
    max_dd_hedged = np.min(drawdown)

    sharpe_unhedged = np.mean(r_unhedged) / np.std(r_unhedged) if np.std(r_unhedged) > 0 else 0
    sharpe_hedged = np.mean(r_hedged) / np.std(r_hedged) if np.std(r_hedged) > 0 else 0

    # 方差降低
    variance_reduction = 1 - (std_hedged ** 2) / (std_unhedged ** 2)

    return {
        'start_date': start_date,
        'end_date': period_data.iloc[-1]['date'],
        'period_days': len(period_data),
        'total_return_unhedged': total_return_unhedged,
        'total_return_hedged': total_return_hed,
        'annual_return_unhedged': annual_return_unhedged,
        'annual_return_hedged': annual_return_hedged,
        'std_unhedged': std_unhedged,
        'std_hedged': std_hedged,
        'max_dd_unhedged': max_dd_unhedged,
        'max_dd_hedged': max_dd_hedged,
        'sharpe_unhedged': sharpe_unhedged,
        'sharpe_hedged': sharpe_hedged,
        'variance_reduction': variance_reduction,
        'cumulative_unhedged': cumulative_unhedged,
        'cumulative_hedged': cumulative_hedged,
        'drawdown': drawdown,
        'dates': period_data['date'].values
    }


def run_rolling_backtest(data: pd.DataFrame, hedge_ratios: np.ndarray,
                         n_periods: int = 5, window_days: int = 60,
                         seed: int = 42) -> Dict:
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
            data, start_date, hedge_ratios, window_days
        )

        period_results.append(result)

        print(f"  结束日期: {result['end_date'].date()}")
        print(f"  实际天数: {result['period_days']}")
        print(f"  未套保收益率: {result['total_return_unhedged']:.2%}")
        print(f"  套保收益率: {result['total_return_hedged']:.2%}")
        print(f"  方差降低: {result['variance_reduction']:.2%}")

    # 汇总统计
    print(f"\n{'='*60}")
    print("回测汇总")
    print(f"{'='*60}")

    avg_return_unhedged = np.mean([r['total_return_unhedged'] for r in period_results])
    avg_return_hedged = np.mean([r['total_return_hedged'] for r in period_results])
    avg_variance_reduction = np.mean([r['variance_reduction'] for r in period_results])
    avg_max_dd_hedged = np.mean([r['max_dd_hedged'] for r in period_results])

    print(f"平均收益率（未套保）: {avg_return_unhedged:.2%}")
    print(f"平均收益率（套保后）: {avg_return_hedged:.2%}")
    print(f"平均方差降低: {avg_variance_reduction:.2%}")
    print(f"平均最大回撤（套保后）: {avg_max_dd_hedged:.2%}")

    return {
        'period_results': period_results,
        'n_periods': len(period_results),
        'window_days': window_days,
        'avg_return_unhedged': avg_return_unhedged,
        'avg_return_hedged': avg_return_hedged,
        'avg_variance_reduction': avg_variance_reduction,
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

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def generate_rolling_backtest_report(data: pd.DataFrame, results: Dict,
                                      output_dir: str):
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
    """
    print(f"\n[生成滚动回测报告]...")

    import os
    os.makedirs(output_dir, exist_ok=True)
    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    # 1. 绘制图表
    print("\n[1/2] 生成可视化图表...")

    # 各周期净值曲线
    path = os.path.join(figures_dir, '1_periods_nav.png')
    plot_rolling_backtest_results(results, path)

    # 周期对比图
    path = os.path.join(figures_dir, '2_periods_comparison.png')
    plot_period_comparison(results, path)

    # 2. 生成Excel报告
    print("\n[2/2] 生成表格报告...")

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
            '未套保收益率': f"{r['total_return_unhedged']:.2%}",
            '套保收益率': f"{r['total_return_hedged']:.2%}",
            '收益率改善': f"{(r['total_return_hedged'] - r['total_return_unhedged']):.2%}",
            '方差降低': f"{r['variance_reduction']:.2%}",
            '最大回撤（套保后）': f"{r['max_dd_hedged']:.2%}",
            '夏普比率（套保后）': f"{r['sharpe_hedged']:.4f}"
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
                '平均收益率（未套保）',
                '平均收益率（套保后）',
                '平均方差降低',
                '平均最大回撤（套保后）',
            ],
            '数值': [
                results['n_periods'],
                results['window_days'],
                f"{results['avg_return_unhedged']:.2%}",
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

    print(f"\n✓ 滚动回测报告生成完成！")
    print(f"📁 输出目录: {output_dir}")

    return {
        'excel_path': excel_path,
        'csv_path': csv_path,
        'figures_dir': figures_dir
    }
