#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Basic GARCH 运行器
"""

import sys
from pathlib import Path

# 添加 garch-web-platform 到路径
platform_dir = Path(__file__).parent
sys.path.insert(0, str(platform_dir))

from lib.model_runners.basic_garch import run_basic_garch

def test_basic_garch():
    """测试 Basic GARCH 模型运行器"""

    print("\n" + "="*70)
    print("测试 Basic GARCH 模型运行器")
    print("="*70)

    # 测试参数
    test_params = {
        'data_path': '../outputs/meg_full_data.xlsx',
        'sheet_name': 0,  # 使用第一个工作表
        'spot_col': 'spot',
        'futures_col': 'futures',
        'date_col': None,  # 自动检测
        'skip_rows': 0,
        'output_dir': '../outputs/test_basic_garch_runner',
        'p': 1,
        'q': 1,
        'corr_window': 120,
        'tax_rate': 0.13,
        'enable_rolling_backtest': False,  # 先用简单的全样本回测
        'n_periods': 3,
        'window_days': 90,
        'backtest_seed': 42
    }

    print("\n测试参数:")
    for key, value in test_params.items():
        print(f"  {key}: {value}")

    # 运行测试
    print("\n开始测试...")
    result = run_basic_garch(**test_params)

    # 检查结果
    print("\n" + "="*70)
    print("测试结果")
    print("="*70)

    if result['success']:
        print("\n✓ 测试成功！")
        print(f"\n报告路径: {result['report_path']}")

        if result['summary']:
            print(f"\n摘要信息:")
            for key, value in result['summary'].items():
                if isinstance(value, float):
                    if key in ['variance_reduction', 'avg_return_unhedged', 'avg_return_hedged']:
                        print(f"  {key}: {value:.2%}")
                    elif 'ratio' in key or 'sharpe' in key:
                        print(f"  {key}: {value:.4f}")
                    else:
                        print(f"  {key}: {value:.4f}")
                else:
                    print(f"  {key}: {value}")

        return True
    else:
        print(f"\n✗ 测试失败！")
        print(f"\n错误信息:\n{result['error']}")
        return False


if __name__ == '__main__':
    success = test_basic_garch()
    sys.exit(0 if success else 1)
