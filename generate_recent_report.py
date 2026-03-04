#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成最近3个月数据的聚焦报告
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 文件路径
DATA_DIR = 'outputs/乙二醇MEG_Basic_GARCH_完整回测'
OUTPUT_DIR = 'outputs/乙二醇MEG_最近3个月_聚焦'

def load_recent_data(days=90):
    """加载最近N天的数据"""
    # 读取模型结果（包含完整数据）
    model_results = pd.read_csv(f'{DATA_DIR}/model_results/h_basic_garch.csv')
    model_results['date'] = pd.to_datetime(model_results['date'])
    df = model_results[['date', 'spot', 'futures', 'spread', 'r_s', 'r_f',
                        'h_theoretical', 'h_actual', 'h_final', 'rolling_corr']].copy()

    # 计算税后套保比例
    tax_rate = 0.13
    df['h_tax_adjusted'] = df['h_final'] / (1 + tax_rate)

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 获取最近N天
    cutoff_date = df['date'].max() - timedelta(days=days)
    recent_df = df[df['date'] >= cutoff_date].copy()

    return recent_df

def plot_recent_price_series(df, output_path):
    """绘制最近价格走势"""
    print("[绘图 1/5] 最近3个月价格走势...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 价格走势
    ax1.plot(df['date'], df['spot'], label='现货价格', linewidth=2, alpha=0.8, color='red')
    ax1.plot(df['date'], df['futures'], label='期货价格', linewidth=2, alpha=0.8, color='blue')
    ax1.set_ylabel('价格 (元/吨)', fontsize=11, fontweight='bold')
    ax1.set_title('乙二醇MEG - 最近3个月价格走势', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # 基差走势
    ax2.plot(df['date'], df['spread'], label='基差 (现货-期货)', linewidth=2, color='green')
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.fill_between(df['date'], df['spread'], 0, alpha=0.3, color='green' if df['spread'].mean() > 0 else 'red')
    ax2.set_xlabel('日期', fontsize=11, fontweight='bold')
    ax2.set_ylabel('基差 (元/吨)', fontsize=11, fontweight='bold')
    ax2.set_title('基差走势', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 格式化x轴
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def plot_recent_hedge_ratio(df, output_path):
    """绘制最近套保比例"""
    print("[绘图 2/5] 最近3个月套保比例...")

    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(df['date'], df['h_tax_adjusted'], label='税后套保比例', linewidth=2.5, color='darkblue', alpha=0.8)
    ax.axhline(y=df['h_tax_adjusted'].mean(), color='red', linestyle='--',
               linewidth=2, label=f'平均套保比例 ({df["h_tax_adjusted"].mean():.4f})')
    ax.fill_between(df['date'], df['h_tax_adjusted'], alpha=0.3, color='blue')

    ax.set_xlabel('日期', fontsize=11, fontweight='bold')
    ax.set_ylabel('套保比例', fontsize=11, fontweight='bold')
    ax.set_title('乙二醇MEG - 最近3个月套保比例时变图', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 添加统计信息文本框
    stats_text = f'均值: {df["h_tax_adjusted"].mean():.4f}\n'
    stats_text += f'标准差: {df["h_tax_adjusted"].std():.4f}\n'
    stats_text += f'最小值: {df["h_tax_adjusted"].min():.4f}\n'
    stats_text += f'最大值: {df["h_tax_adjusted"].max():.4f}'

    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def plot_recent_volatility(df, output_path):
    """绘制最近波动率"""
    print("[绘图 3/5] 最近3个月波动率...")

    fig, ax = plt.subplots(figsize=(14, 7))

    # 计算滚动标准差（20天窗口）
    if 'r_s' in df.columns:
        df['vol_s'] = df['r_s'].rolling(window=20).std() * np.sqrt(252) * 100
        df['vol_f'] = df['r_f'].rolling(window=20).std() * np.sqrt(252) * 100

        ax.plot(df['date'], df['vol_s'], label='现货波动率', linewidth=2, color='red', alpha=0.8)
        ax.plot(df['date'], df['vol_f'], label='期货波动率', linewidth=2, color='blue', alpha=0.8)
    else:
        # 如果没有收益率列，使用价格计算
        df['returns'] = df['spot'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(252) * 100
        ax.plot(df['date'], df['volatility'], label='年化波动率', linewidth=2.5, color='purple', alpha=0.8)

    ax.set_xlabel('日期', fontsize=11, fontweight='bold')
    ax.set_ylabel('年化波动率 (%)', fontsize=11, fontweight='bold')
    ax.set_title('乙二醇MEG - 最近3个月波动率走势', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def plot_recent_summary(df, output_path):
    """绘制最近汇总信息"""
    print("[绘图 4/5] 最近3个月汇总统计...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    # 1. 价格箱线图
    price_data = [df['spot'].dropna(), df['futures'].dropna()]
    bp1 = ax1.boxplot(price_data, labels=['现货', '期货'], patch_artist=True)
    for patch, color in zip(bp1['boxes'], ['red', 'blue']):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax1.set_ylabel('价格 (元/吨)', fontweight='bold')
    ax1.set_title('价格分布', fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')

    # 2. 套保比例分布
    ax2.hist(df['h_tax_adjusted'].dropna(), bins=20, color='green', alpha=0.7, edgecolor='black')
    ax2.axvline(df['h_tax_adjusted'].mean(), color='red', linestyle='--', linewidth=2, label='均值')
    ax2.set_xlabel('套保比例', fontweight='bold')
    ax2.set_ylabel('频数', fontweight='bold')
    ax2.set_title('套保比例分布', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')

    # 3. 收益率散点图（如果有）
    if 'r_s' in df.columns and 'r_f' in df.columns:
        ax3.scatter(df['r_s'], df['r_f'], alpha=0.6, s=30)
        ax3.plot([df['r_s'].min(), df['r_s'].max()],
                 [df['r_s'].min(), df['r_s'].max()], 'r--', linewidth=2, label='完全对角线')
        ax3.set_xlabel('现货收益率', fontweight='bold')
        ax3.set_ylabel('期货收益率', fontweight='bold')
        ax3.set_title(f'收益率相关性 (r={df["r_s"].corr(df["r_f"]):.4f})', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

    # 4. 基差统计
    ax4.axis('tight')
    ax4.axis('off')

    # 计算统计指标
    stats = {
        '数据时间范围': f'{df["date"].min().strftime("%Y-%m-%d")} 至 {df["date"].max().strftime("%Y-%m-%d")}',
        '交易天数': f'{len(df)} 天',
        '现货价格': f'均值 {df["spot"].mean():.2f} / 标准差 {df["spot"].std():.2f}',
        '期货价格': f'均值 {df["futures"].mean():.2f} / 标准差 {df["futures"].std():.2f}',
        '基差': f'均值 {df["spread"].mean():.2f} / 标准差 {df["spread"].std():.2f}',
        '套保比例': f'均值 {df["h_tax_adjusted"].mean():.4f} / 标准差 {df["h_tax_adjusted"].std():.4f}',
    }

    if 'r_s' in df.columns:
        stats['价格相关系数'] = f'{df["spot"].corr(df["futures"]):.4f}'
        stats['收益率相关系数'] = f'{df["r_s"].corr(df["r_f"]):.4f}'

    table_data = [[k, v] for k, v in stats.items()]
    table = ax4.table(cellText=table_data, cellLoc='left', loc='center',
                      colWidths=[0.4, 0.6])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2)

    for i in range(len(table_data)):
        if i == 0:
            for j in range(2):
                table[(i, j)].set_facecolor('#3498db')
                table[(i, j)].set_text_props(weight='bold', color='white')
        elif i % 2 == 0:
            for j in range(2):
                table[(i, j)].set_facecolor('#f0f0f0')

    ax4.set_title('数据统计汇总', fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def plot_recent_performance(output_path):
    """绘制最近回测性能总结"""
    print("[绘图 5/5] 回测性能总结...")

    # 读取回测结果
    backtest_results = pd.read_csv(f'{DATA_DIR}/rolling_backtest_report.csv')

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # 过滤最近周期的数据
    recent_results = backtest_results.tail(3) if len(backtest_results) >= 3 else backtest_results

    # 转换百分比字符串为数值
    def parse_percent(s):
        if isinstance(s, str):
            return float(s.rstrip('%')) / 100
        return s

    # 构建表格数据
    table_data = [['周期', '起始日期', '结束日期', '未套保收益率', '套保收益率', '方差降低', '夏普比率(套保)', '最大回撤(套保)']]

    for _, row in recent_results.iterrows():
        table_data.append([
            row['周期'],
            row['起始日期'],
            row['结束日期'],
            row['未套保收益率'],
            row['套保收益率'],
            row['方差降低'],
            row['夏普比率（套保后）'],
            row['最大回撤（套保后）'],
        ])

    # 添加汇总行（计算平均值）
    avg_return_u = recent_results['未套保收益率'].apply(parse_percent).mean()
    avg_return_h = recent_results['套保收益率'].apply(parse_percent).mean()
    avg_var_red = recent_results['方差降低'].apply(parse_percent).mean()
    avg_sharpe = recent_results['夏普比率（套保后）'].mean()
    avg_max_dd = recent_results['最大回撤（套保后）'].apply(parse_percent).mean()

    table_data.append([
        '平均值',
        '-',
        '-',
        f"{avg_return_u:.2%}",
        f"{avg_return_h:.2%}",
        f"{avg_var_red:.2%}",
        f"{avg_sharpe:.4f}",
        f"{avg_max_dd:.2%}",
    ])

    table = ax.table(cellText=table_data, cellLoc='center', loc='center',
                     colWidths=[0.08, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12, 0.12])
    table.auto_set_font_size(False)
    table.set_fontsize(9)

    for i in range(len(table_data)):
        for j in range(len(table_data[0])):
            if i == 0:
                table[(i, j)].set_facecolor('#3498db')
                table[(i, j)].set_text_props(weight='bold', color='white')
            elif i == len(table_data) - 1:
                table[(i, j)].set_facecolor('#e74c3c')
                table[(i, j)].set_text_props(weight='bold', color='white')
            elif i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')

    ax.set_title('乙二醇MEG - 滚动回测性能总结', fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")

def main():
    """主程序"""
    print("=" * 60)
    print("生成乙二醇MEG - 最近3个月聚焦报告")
    print("=" * 60)

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/figures', exist_ok=True)

    # 加载最近3个月数据
    print("\n[1/2] 加载最近3个月数据...")
    df = load_recent_data(days=90)
    print(f"✓ 数据量: {len(df)} 天")
    print(f"  日期范围: {df['date'].min().strftime('%Y-%m-%d')} 到 {df['date'].max().strftime('%Y-%m-%d')}")

    # 生成图表
    print("\n[2/2] 生成图表...")
    plot_recent_price_series(df, f'{OUTPUT_DIR}/figures/1_price_recent.png')
    plot_recent_hedge_ratio(df, f'{OUTPUT_DIR}/figures/2_hedge_ratio_recent.png')
    plot_recent_volatility(df, f'{OUTPUT_DIR}/figures/3_volatility_recent.png')
    plot_recent_summary(df, f'{OUTPUT_DIR}/figures/4_summary_recent.png')
    plot_recent_performance(f'{OUTPUT_DIR}/figures/5_performance_recent.png')

    print("\n" + "=" * 60)
    print("✓ 报告生成完成！")
    print(f"📁 输出目录: {OUTPUT_DIR}/figures/")
    print("=" * 60)

if __name__ == '__main__':
    main()
