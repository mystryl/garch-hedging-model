#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic GARCH模型套保回测脚本

使用方法：
    python run_basic_garch.py

功能：
    - 读取处理后的期现货数据
    - 运行Basic GARCH(1,1)模型
    - 执行滚动回测（6周期 × 90天）
    - 生成完整的HTML/Excel/CSV报告

输出目录：outputs/<品种>_Basic_GARCH_<年份>/
"""

import pandas as pd
import os
from basic_garch_analyzer import run_basic_garch_analyzer

# ==================== 配置参数 ====================

# 数据文件路径
DATA_FILE = 'data/hot_coil_2021_latest.xlsx'  # 修改为您的数据文件路径

# 输出目录配置
OUTPUT_DIR = 'outputs/热卷Basic_GARCH_2021'  # 修改为想要的输出目录名

# 数据列配置
SPOT_COL = 'spot'      # 现货价格列名
FUTURES_COL = 'futures'  # 期货价格列名

# 回测参数配置
CONFIG = {
    'enable_rolling_backtest': True,  # 启用滚动回测
    'n_periods': 6,                   # 回测周期数
    'window_days': 90,                # 每个周期天数
    'backtest_seed': 42,              # 随机种子（保持结果可复现）
    'tax_rate': 0.13                  # 增值税率（13%）
}

# 数据过滤参数（可选）
START_DATE = '2021-01-01'  # 起始日期（None表示使用全部数据）
END_DATE = None            # 结束日期（None表示使用全部数据）

# ==================== 主程序 ====================

def main():
    """主程序"""

    print("=" * 60)
    print("Basic GARCH模型套保回测")
    print("=" * 60)

    # 1. 读取数据
    print("\n[1/4] 正在读取数据...")
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
        data.set_index('date', inplace=True)

    print(f"✓ 数据加载成功")
    print(f"  - 样本量: {len(data)} 天")
    print(f"  - 起始日期: {data.index[0].strftime('%Y-%m-%d')}")
    print(f"  - 结束日期: {data.index[-1].strftime('%Y-%m-%d')}")

    # 检查数据列
    if SPOT_COL not in data.columns:
        print(f"❌ 错误：数据中缺少 '{SPOT_COL}' 列")
        print(f"  可用的列: {list(data.columns)}")
        return

    if FUTURES_COL not in data.columns:
        print(f"❌ 错误：数据中缺少 '{FUTURES_COL}' 列")
        print(f"  可用的列: {list(data.columns)}")
        return

    # 2. 运行Basic GARCH回测
    print("\n[2/4] 正在运行Basic GARCH模型...")
    print(f"  - 模型类型: Basic GARCH(1,1)")
    print(f"  - 回测周期: {CONFIG['n_periods']} 个")
    print(f"  - 周期长度: {CONFIG['window_days']} 天")
    print(f"  - 税率: {CONFIG['tax_rate']*100}%")

    try:
        run_basic_garch_analyzer(
            data=data,
            output_dir=OUTPUT_DIR,
            spot_col=SPOT_COL,
            futures_col=FUTURES_COL,
            config=CONFIG
        )
    except Exception as e:
        print(f"❌ 错误：回测运行失败")
        print(f"  错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # 3. 检查输出文件
    print("\n[3/4] 正在检查输出文件...")

    expected_files = [
        'report.html',
        'rolling_backtest_report.xlsx',
        'rolling_backtest_report.csv'
    ]

    all_exist = True
    for filename in expected_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(filepath):
            print(f"  ✓ {filename}")
        else:
            print(f"  ✗ {filename} (未生成)")
            all_exist = False

    figures_dir = os.path.join(OUTPUT_DIR, 'figures')
    if os.path.exists(figures_dir):
        figures = [f for f in os.listdir(figures_dir) if f.endswith('.png')]
        print(f"  ✓ 图表文件: {len(figures)} 张")

    # 4. 完成
    print("\n[4/4] 回测完成！")
    print("=" * 60)
    print(f"📊 报告位置: {OUTPUT_DIR}/")
    print(f"  - HTML报告: {os.path.join(OUTPUT_DIR, 'report.html')}")
    print(f"  - Excel报告: {os.path.join(OUTPUT_DIR, 'rolling_backtest_report.xlsx')}")
    print(f"  - CSV报告: {os.path.join(OUTPUT_DIR, 'rolling_backtest_report.csv')}")

    if all_exist:
        print("\n✅ 所有文件生成成功！")
    else:
        print("\n⚠️  部分文件未生成，请检查错误信息")

    print("=" * 60)


if __name__ == '__main__':
    main()
