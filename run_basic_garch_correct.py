#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic GARCH模型套保回测脚本（使用正确数据路径）

使用方法：
    python run_basic_garch_correct.py
"""

import pandas as pd
import os
from basic_garch_analyzer import run_analysis, ModelConfig

# 修改数据文件路径
DATA_FILE = 'outputs/hot_coil_2021_latest.xlsx'
OUTPUT_DIR = 'outputs/热卷Basic_GARCH_2021_完整回测'

SPOT_COL = 'spot'
FUTURES_COL = 'futures'

# 使用ModelConfig对象
CONFIG = ModelConfig(
    enable_rolling_backtest=True,
    n_periods=6,
    window_days=90,
    backtest_seed=42,
    tax_rate=0.13,
    output_dir=OUTPUT_DIR
)

def main():
    """主程序"""

    print("=" * 60)
    print("Basic GARCH模型套保回测")
    print("=" * 60)

    # 1. 检查数据文件
    print("\n[1/2] 正在检查数据...")
    print(f"数据文件: {DATA_FILE}")

    if not os.path.exists(DATA_FILE):
        print(f"❌ 错误：数据文件不存在 - {DATA_FILE}")
        return

    print(f"✓ 数据文件存在")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(f'{OUTPUT_DIR}/model_results', exist_ok=True)

    # 2. 运行Basic GARCH回测
    print("\n[2/2] 正在运行Basic GARCH模型...")

    result = run_analysis(
        excel_path=DATA_FILE,
        spot_col=SPOT_COL,
        futures_col=FUTURES_COL,
        config=CONFIG
    )

    # 3. 完成
    print("\n[3/3] 回测完成！")
    print("=" * 60)
    print(f"📊 报告位置: {OUTPUT_DIR}/")

    if result['config'].enable_rolling_backtest:
        rr = result['rolling_results']
        print(f"\n核心结果:")
        print(f"  平均收益率（套保后）: {rr['avg_return_hedged']:.2%}")
        print(f"  平均方差降低: {rr['avg_variance_reduction']:.2%}")


if __name__ == '__main__':
    main()
