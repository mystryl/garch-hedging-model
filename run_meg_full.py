#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
乙二醇MEG Basic GARCH模型套保回测脚本（完整数据+最近3个月报告）
"""

import pandas as pd
import os
from basic_garch_analyzer import run_analysis, ModelConfig

# 使用完整数据
DATA_FILE = 'outputs/meg_full_data.xlsx'
OUTPUT_DIR = 'outputs/乙二醇MEG_Basic_GARCH_完整回测'

SPOT_COL = 'spot'
FUTURES_COL = 'futures'

# 使用ModelConfig对象（默认配置适合全量数据）
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
    print("乙二醇MEG - Basic GARCH模型套保回测")
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
    print(f"  - HTML报告: {OUTPUT_DIR}/report.html")
    print(f"  - 图表目录: {OUTPUT_DIR}/figures/")
    print(f"  - 模型结果: {OUTPUT_DIR}/model_results/")

    if result['config'].enable_rolling_backtest:
        rr = result['rolling_results']
        print(f"\n核心结果:")
        print(f"  平均收益率（未套保）: {rr['avg_return_unhedged']:.2%}")
        print(f"  平均收益率（套保后）: {rr['avg_return_hedged']:.2%}")
        print(f"  平均方差降低: {rr['avg_variance_reduction']:.2%}")
        print(f"  平均最大回撤（套保后）: {rr['avg_max_dd_hedged']:.2%}")


if __name__ == '__main__':
    main()
