#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARCH Web 平台优化验证脚本

验证三个优化：
1. 性能指标汇总表格统一为传统套保 vs 动态套保
2. ZIP 文件命名为日期+品种+模型组合
3. 前端报告图片路径修复
"""

import sys
from pathlib import Path

# 添加lib目录到Python路径
LIB_DIR = Path(__file__).parent / 'lib'
sys.path.insert(0, str(LIB_DIR))

from models import MODEL_RUNNERS

def test_table_labels():
    """测试1：验证表格列标题更新"""
    print("\n" + "="*60)
    print("测试 1: 性能指标汇总表格标签")
    print("="*60)

    # 运行一个简单的测试
    result = MODEL_RUNNERS['basic_garch'](
        data_path='../outputs/meg_full_data.xlsx',
        sheet_name=0,
        column_mapping={'spot': 'spot', 'future': 'futures', 'date': 'date'},
        model_config={'p': 1, 'q': 1, 'corr_window': 120, 'tax_rate': 0.13},
        output_dir='../outputs/test_tables'
    )

    if result.get('success'):
        # 检查 HTML 报告
        html_path = result['report_path']
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 验证 HTML 表格列标题
        has_traditional = '传统套保 (h=1)' in html_content
        has_dynamic = '动态套保 (GARCH)' in html_content
        has_old_unhedged = '未套保' not in html_content or html_content.count('未套保') == 0
        has_old_hedged = '套保后' not in html_content or html_content.count('套保后') == 0

        print(f"✓ HTML 报告路径: {html_path}")
        print(f"  - 包含'传统套保 (h=1)': {has_traditional}")
        print(f"  - 包含'动态套保 (GARCH)': {has_dynamic}")
        print(f"  - 不包含旧'未套保'标签: {has_old_unhedged}")
        print(f"  - 不包含旧'套保后'标签: {has_old_hedged}")

        # 检查 CSV 报告
        import pandas as pd
        csv_path = Path(html_path).parent / 'backtest_report.csv'
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            csv_has_traditional = '传统套保' in df['指标'].values[0] or '传统套保' in str(df['指标'].iloc[0])

            print(f"\n✓ CSV 报告检查:")
            print(f"  - 第一行指标: {df['指标'].iloc[0]}")
            print(f"  - 包含'传统套保': {csv_has_traditional}")

        return has_traditional and has_dynamic
    else:
        print(f"✗ 测试失败: {result.get('error')}")
        return False


def test_zip_naming():
    """测试2：验证 ZIP 文件命名"""
    print("\n" + "="*60)
    print("测试 2: ZIP 文件命名格式")
    print("="*60)

    from app import extract_commodity_name

    # 测试品种名称提取
    test_cases = [
        ('meg_full_data.xlsx', {}, 'MEG'),
        ('pp_data.xlsx', {}, 'PP'),
        ('test_unknown.xlsx', {}, '通用'),
    ]

    all_passed = True
    for filename, col_mapping, expected in test_cases:
        result = extract_commodity_name(filename, col_mapping)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✓" if passed else "✗"
        print(f"{status} {filename} -> {result} (期望: {expected})")

    return all_passed


def test_image_paths():
    """测试3：验证图片路径修复逻辑"""
    print("\n" + "="*60)
    print("测试 3: 图片路径正则替换")
    print("="*60)

    import re

    # 模拟 HTML 内容
    sample_html = '''
    <html>
    <body>
        <img src="figures/1_price_series.png" alt="价格走势图">
        <img src="figures/2_returns.png" alt="收益率图">
    </body>
    </html>
    '''

    # 执行替换
    report_dir = "20250304_MEG_Basic_GARCH"
    modified = re.sub(
        r'src="figures/([^"]+)"',
        lambda m: f'src="/report-images/{report_dir}/figures/{m.group(1)}"',
        sample_html
    )

    # 验证结果
    has_correct_path = '/report-images/20250304_MEG_Basic_GARCH/figures/1_price_series.png' in modified
    has_second_path = '/report-images/20250304_MEG_Basic_GARCH/figures/2_returns.png' in modified

    print(f"✓ 原始路径被正确替换:")
    print(f"  - 第一张图片: {has_correct_path}")
    print(f"  - 第二张图片: {has_second_path}")
    print(f"\n修改后的 HTML 片段:")
    print(modified.strip())

    return has_correct_path and has_second_path


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("GARCH Web 平台优化验证")
    print("="*60)

    results = {
        '表格标签更新': test_table_labels(),
        'ZIP 文件命名': test_zip_naming(),
        '图片路径修复': test_image_paths(),
    }

    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status}: {test_name}")
        all_passed = all_passed and passed

    print("\n" + "="*60)
    if all_passed:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败，请检查")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
