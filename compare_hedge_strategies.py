#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比传统套保与GARCH动态套保的收益曲线

传统套保比例: 期货:现货 = 1:1 (税后调整 h = 1/1.13 ≈ 0.885)
GARCH套保: 动态最优套保比例
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 文件路径
DATA_DIR = 'outputs/乙二醇MEG_Basic_GARCH_完整回测'
OUTPUT_DIR = 'outputs/乙二醇MEG_套保策略对比'

def calculate_hedge_returns(df, hedge_ratio_col=None, fixed_ratio=None, tax_rate=0.13):
    """
    计算套保后的收益率

    Parameters:
    -----------
    df : DataFrame
        包含 spot, futures, r_s, r_f 的数据
    hedge_ratio_col : str
        动态套保比例列名
    fixed_ratio : float
        固定套保比例（如果使用传统套保）
    tax_rate : float
        税率

    Returns:
    --------
    returns : Series
        套保后的收益率序列
    hedge_ratios : Series
        使用的套保比例序列
    """
    if fixed_ratio is not None:
        # 传统固定比例套保
        h = fixed_ratio / (1 + tax_rate)  # 税后调整
        returns = df['r_s'] - h * df['r_f']
        hedge_ratios = pd.Series([h] * len(df), index=df.index)
    elif hedge_ratio_col is not None:
        # GARCH动态套保
        returns = df['r_s'] - df[hedge_ratio_col] * df['r_f']
        hedge_ratios = df[hedge_ratio_col]
    else:
        raise ValueError("必须指定 hedge_ratio_col 或 fixed_ratio")

    return returns, hedge_ratios

def calculate_cumulative_returns(returns):
    """计算累计收益率"""
    return (1 + returns).cumprod()

def plot_full_period_comparison(df, output_path):
    """绘制全周期收益曲线对比"""
    print("[绘图 1/3] 全周期收益曲线对比...")

    # 计算三种策略的收益率
    # 传统套保：期货:现货 = 1:1，税后调整
    returns_unhedged, _ = calculate_hedge_returns(df, fixed_ratio=0)  # 不套保
    returns_traditional, _ = calculate_hedge_returns(df, fixed_ratio=1.0)  # 传统1:1套保（函数内会做税后调整）
    returns_garch, _ = calculate_hedge_returns(df, hedge_ratio_col='h_final')  # GARCH动态

    # 计算累计收益率
    cum_unhedged = calculate_cumulative_returns(returns_unhedged)
    cum_traditional = calculate_cumulative_returns(returns_traditional)
    cum_garch = calculate_cumulative_returns(returns_garch)

    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    # 上图：累计净值曲线
    ax1 = axes[0]
    ax1.plot(df['date'], cum_unhedged, label='未套保', linewidth=2.5, color='red', alpha=0.8)
    ax1.plot(df['date'], cum_traditional, label='传统套保 (1:1)', linewidth=2.5, color='blue', alpha=0.8)
    ax1.plot(df['date'], cum_garch, label='GARCH动态套保', linewidth=2.5, color='green', alpha=0.8)

    ax1.set_ylabel('累计净值', fontsize=12, fontweight='bold')
    ax1.set_title('乙二醇MEG - 套保策略对比：全周期累计净值曲线 (2021-2026)',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=1, color='black', linestyle='--', linewidth=1, alpha=0.5)

    # 添加最终净值标注
    final_unhedged = cum_unhedged.iloc[-1]
    final_traditional = cum_traditional.iloc[-1]
    final_garch = cum_garch.iloc[-1]

    textstr = f'最终净值:\n'
    textstr += f'未套保: {final_unhedged:.4f}\n'
    textstr += f'传统套保: {final_traditional:.4f}\n'
    textstr += f'GARCH套保: {final_garch:.4f}'

    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax1.text(0.02, 0.98, textstr, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=props)

    # 下图：套保比例对比
    ax2 = axes[1]

    # 传统套保比例（1:1，税后）
    traditional_ratio = 1.0 / (1 + 0.13)  # 1:1套保，税后调整
    ax2.plot(df['date'], df['h_final'], label='GARCH动态套保比例',
             linewidth=2, color='green', alpha=0.8)
    ax2.axhline(y=traditional_ratio, label=f'传统套保比例 (1:1, 税后={traditional_ratio:.4f})',
                color='blue', linestyle='--', linewidth=2, alpha=0.8)

    ax2.set_xlabel('日期', fontsize=12, fontweight='bold')
    ax2.set_ylabel('套保比例', fontsize=12, fontweight='bold')
    ax2.set_title('套保比例对比', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=11)
    ax2.grid(True, alpha=0.3)

    # 添加统计信息
    garch_mean = df['h_final'].mean()
    garch_std = df['h_final'].std()
    textstr2 = f'GARCH套保比例统计:\n'
    textstr2 += f'均值: {garch_mean:.4f}\n'
    textstr2 += f'标准差: {garch_std:.4f}\n'
    textstr2 += f'最小值: {df["h_final"].min():.4f}\n'
    textstr2 += f'最大值: {df["h_final"].max():.4f}'

    props2 = dict(boxstyle='round', facecolor='lightblue', alpha=0.8)
    ax2.text(0.98, 0.98, textstr2, transform=ax2.transAxes, fontsize=10,
             verticalalignment='top', horizontalalignment='right', bbox=props2)

    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

    return {
        'unhedged': cum_unhedged.iloc[-1] - 1,
        'traditional': cum_traditional.iloc[-1] - 1,
        'garch': cum_garch.iloc[-1] - 1,
        'std_unhedged': returns_unhedged.std() * np.sqrt(252),
        'std_traditional': returns_traditional.std() * np.sqrt(252),
        'std_garch': returns_garch.std() * np.sqrt(252),
    }

def plot_recent_comparison(df, output_path, days=90):
    """绘制最近N天的收益曲线对比"""
    print(f"[绘图 2/3] 最近{days}天收益曲线对比...")

    # 筛选最近数据
    cutoff_date = df['date'].max() - pd.Timedelta(days=days)
    df_recent = df[df['date'] >= cutoff_date].copy().reset_index(drop=True)

    # 计算三种策略的收益率
    returns_unhedged, _ = calculate_hedge_returns(df_recent, fixed_ratio=0)
    returns_traditional, _ = calculate_hedge_returns(df_recent, fixed_ratio=1.0)  # 传统1:1套保
    returns_garch, _ = calculate_hedge_returns(df_recent, hedge_ratio_col='h_final')

    # 计算累计收益率
    cum_unhedged = calculate_cumulative_returns(returns_unhedged)
    cum_traditional = calculate_cumulative_returns(returns_traditional)
    cum_garch = calculate_cumulative_returns(returns_garch)

    # 创建图表
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))

    # 上图：累计净值曲线
    ax1 = axes[0]
    ax1.plot(df_recent['date'], cum_unhedged, label='未套保', linewidth=2.5, color='red', alpha=0.8)
    ax1.plot(df_recent['date'], cum_traditional, label='传统套保 (1:1)', linewidth=2.5, color='blue', alpha=0.8)
    ax1.plot(df_recent['date'], cum_garch, label='GARCH动态套保', linewidth=2.5, color='green', alpha=0.8)

    ax1.set_ylabel('累计净值', fontsize=12, fontweight='bold')
    ax1.set_title(f'乙二醇MEG - 套保策略对比：最近{days}天累计净值曲线',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=1, color='black', linestyle='--', linewidth=1, alpha=0.5)

    # 下图：套保比例对比
    ax2 = axes[1]
    traditional_ratio = 1.0 / (1 + 0.13)  # 1:1套保，税后
    ax2.plot(df_recent['date'], df_recent['h_final'], label='GARCH动态套保比例',
             linewidth=2, color='green', alpha=0.8)
    ax2.axhline(y=traditional_ratio, label=f'传统套保比例 (1:1, 税后={traditional_ratio:.4f})',
                color='blue', linestyle='--', linewidth=2, alpha=0.8)
    ax2.fill_between(df_recent['date'], df_recent['h_final'], traditional_ratio,
                     alpha=0.2, color='gray')

    ax2.set_xlabel('日期', fontsize=12, fontweight='bold')
    ax2.set_ylabel('套保比例', fontsize=12, fontweight='bold')
    ax2.set_title('套保比例对比（最近3个月）', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=11)
    ax2.grid(True, alpha=0.3)

    # 格式化x轴
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def plot_performance_summary(stats, output_path):
    """绘制性能指标汇总表"""
    print("[绘图 3/3] 性能指标汇总...")

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # 计算更多指标
    strategies = ['未套保', '传统套保 (1:1)', 'GARCH动态套保']
    returns = [stats['unhedged'], stats['traditional'], stats['garch']]
    vols = [stats['std_unhedged'], stats['std_traditional'], stats['std_garch']]

    # 计算夏普比率（假设无风险利率为0）
    sharpe_ratios = [r/v if v > 0 else 0 for r, v in zip(returns, vols)]

    # 方差降低比例
    var_reduction_trad = (stats['std_unhedged']**2 - stats['std_traditional']**2) / stats['std_unhedged']**2
    var_reduction_garch = (stats['std_unhedged']**2 - stats['std_garch']**2) / stats['std_unhedged']**2

    # 构建表格数据
    table_data = [
        ['策略', '累计收益率', '年化波动率', '夏普比率', '方差降低'],
    ]

    table_data.append([
        strategies[0],
        f"{stats['unhedged']:.2%}",
        f"{stats['std_unhedged']:.2%}",
        f"{sharpe_ratios[0]:.4f}",
        'N/A',
    ])

    table_data.append([
        strategies[1],
        f"{stats['traditional']:.2%}",
        f"{stats['std_traditional']:.2%}",
        f"{sharpe_ratios[1]:.4f}",
        f"{var_reduction_trad:.2%}",
    ])

    table_data.append([
        strategies[2],
        f"{stats['garch']:.2%}",
        f"{stats['std_garch']:.2%}",
        f"{sharpe_ratios[2]:.4f}",
        f"{var_reduction_garch:.2%}",
    ])

    # 添加最优策略标注
    best_return = strategies[np.argmax(returns)]
    best_sharpe = strategies[np.argmax(sharpe_ratios)]
    best_var_reduction = '传统套保' if var_reduction_trad > var_reduction_garch else 'GARCH动态套保'

    table_data.append([
        '最优策略',
        best_return,
        '-',
        best_sharpe,
        best_var_reduction,
    ])

    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.3, 0.2, 0.2, 0.15, 0.15])
    table.auto_set_font_size(False)
    table.set_fontsize(11)

    # 设置单元格样式
    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            if i == 0:
                # 表头
                table[(i, j)].set_facecolor('#3498db')
                table[(i, j)].set_text_props(weight='bold', color='white')
            elif i == len(table_data) - 1:
                # 最后一行（最优策略）
                table[(i, j)].set_facecolor('#e74c3c')
                table[(i, j)].set_text_props(weight='bold', color='white')
            elif i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')

    ax.set_title('乙二醇MEG - 套保策略性能指标汇总（全周期 2021-2026）',
                 fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def main():
    """主程序"""
    print("=" * 60)
    print("对比传统套保与GARCH动态套保")
    print("=" * 60)

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. 加载数据
    print("\n[1/4] 加载数据...")
    df = pd.read_csv(f'{DATA_DIR}/model_results/h_basic_garch.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    print(f"✓ 数据量: {len(df)} 天")
    print(f"  日期范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")

    # 2. 生成全周期对比图
    print("\n[2/4] 生成全周期对比图...")
    stats = plot_full_period_comparison(df, f'{OUTPUT_DIR}/1_full_period_comparison.png')

    # 3. 生成最近3个月对比图
    print("\n[3/4] 生成最近3个月对比图...")
    plot_recent_comparison(df, f'{OUTPUT_DIR}/2_recent_90days_comparison.png', days=90)

    # 4. 生成性能指标汇总表
    print("\n[4/4] 生成性能指标汇总...")
    plot_performance_summary(stats, f'{OUTPUT_DIR}/3_performance_summary.png')

    # 输出文字总结
    print("\n" + "=" * 60)
    print("分析完成！核心结果对比:")
    print("=" * 60)
    print(f"\n累计收益率:")
    print(f"  未套保:        {stats['unhedged']:.2%}")
    print(f"  传统套保(1:1): {stats['traditional']:.2%}")
    print(f"  GARCH动态套保: {stats['garch']:.2%}")

    print(f"\n年化波动率:")
    print(f"  未套保:        {stats['std_unhedged']:.2%}")
    print(f"  传统套保(1:1): {stats['std_traditional']:.2%}")
    print(f"  GARCH动态套保: {stats['std_garch']:.2%}")

    var_red_trad = (stats['std_unhedged']**2 - stats['std_traditional']**2) / stats['std_unhedged']**2
    var_red_garch = (stats['std_unhedged']**2 - stats['std_garch']**2) / stats['std_unhedged']**2
    print(f"\n方差降低:")
    print(f"  传统套保(1:1): {var_red_trad:.2%}")
    print(f"  GARCH动态套保: {var_red_garch:.2%}")

    print(f"\n📁 输出目录: {OUTPUT_DIR}/")
    print("=" * 60)

if __name__ == '__main__':
    main()
