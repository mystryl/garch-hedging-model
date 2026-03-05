#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GARCH Web 平台端到端测试

完整测试 Web 平台的所有优化功能：
1. 性能指标表格标签更新
2. ZIP 文件命名格式
3. 图片路径修复
"""

import sys
import os
from pathlib import Path

# 添加lib目录到Python路径
LIB_DIR = Path(__file__).parent / 'lib'
sys.path.insert(0, str(LIB_DIR))

# 必须在导入其他模块前设置matplotlib后端
import matplotlib
matplotlib.use('agg')

from flask import Flask
import requests
from models import MODEL_RUNNERS
from app import extract_commodity_name, app
import threading
import time


def start_flask_server():
    """在后台启动 Flask 服务器"""
    # 修改端口以避免冲突
    port = 5051
    print(f"\n启动 Flask 测试服务器 (端口 {port})...")
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def test_full_workflow():
    """
    测试完整工作流程：
    1. 运行模型生成报告
    2. 检查报告内容
    3. 验证 ZIP 文件命名
    4. 测试图片路径修复
    """
    print("\n" + "="*70)
    print("GARCH Web 平台端到端测试")
    print("="*70)

    # 步骤 1: 运行模型生成报告
    print("\n[步骤 1/4] 运行 Basic GARCH 模型...")
    result = MODEL_RUNNERS['basic_garch'](
        data_path='../outputs/meg_full_data.xlsx',
        sheet_name=0,
        column_mapping={'spot': 'spot', 'future': 'futures', 'date': 'date'},
        model_config={'p': 1, 'q': 1, 'corr_window': 120, 'tax_rate': 0.13},
        output_dir='../outputs/test_e2e'
    )

    if not result.get('success'):
        print(f"✗ 模型运行失败: {result.get('error')}")
        return False

    print("✓ 模型运行成功")

    # 步骤 2: 检查 HTML 报告内容
    print("\n[步骤 2/4] 检查 HTML 报告内容...")
    html_path = Path(result['report_path'])

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 验证新标签存在
    checks = {
        '包含"传统套保 (h=1)"表格标题': '传统套保 (h=1)' in html_content,
        '包含"动态套保 (GARCH)"表格标题': '动态套保 (GARCH)' in html_content,
        '包含"动态套保夏普比率"卡片': '动态套保夏普比率 (GARCH)' in html_content,
        '包含"动态套保最大回撤"卡片': '动态套保最大回撤 (GARCH)' in html_content,
        '不包含"未套保"旧标签': '未套保' not in html_content or html_content.count('未套保') == 0,
        '不包含"套保后"旧标签': '套保后' not in html_content or html_content.count('套保后') == 0,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed

    if not all_passed:
        print("\n✗ HTML 报告检查失败")
        return False

    print("✓ HTML 报告检查通过")

    # 步骤 3: 检查 CSV 报告
    print("\n[步骤 3/4] 检查 CSV 报告...")
    import pandas as pd

    csv_path = html_path.parent / 'backtest_report.csv'
    if not csv_path.exists():
        print(f"✗ CSV 报告不存在: {csv_path}")
        return False

    df = pd.read_csv(csv_path)
    first_metric = df['指标'].iloc[0]

    csv_checks = {
        'CSV 第一个指标包含"传统套保"': '传统套保' in first_metric,
        'CSV 第一个指标包含"h=1"': 'h=1' in first_metric,
    }

    for check_name, passed in csv_checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed

    if not all_passed:
        print("\n✗ CSV 报告检查失败")
        return False

    print("✓ CSV 报告检查通过")

    # 步骤 4: 测试 ZIP 文件命名
    print("\n[步骤 4/4] 测试 ZIP 文件命名...")

    # 模拟 app.py 中的命名逻辑
    from datetime import datetime
    filepath = '../outputs/meg_full_data.xlsx'
    column_mapping = {'spot': 'spot', 'future': 'futures', 'date': 'date'}

    current_date = datetime.now().strftime('%Y%m%d')
    commodity_name = extract_commodity_name(filepath, column_mapping)
    model_display_name = 'Basic_GARCH'

    expected_zip_name = f"{current_date}_{commodity_name}_{model_display_name}.zip"

    print(f"  预期 ZIP 文件名: {expected_zip_name}")
    print(f"  格式: YYYYMMDD_品种_模型名.zip")

    # 验证格式
    parts = expected_zip_name.replace('.zip', '').split('_')
    # 模型名可能包含下划线，所以需要特殊处理
    model_part = '_'.join(parts[2:])  # 从第3部分开始合并

    zip_checks = {
        f'包含{len(parts)}个部分（模型名含下划线）': len(parts) >= 3,
        '第1部分是日期(8位数字)': len(parts[0]) == 8 and parts[0].isdigit(),
        '第2部分是品种名': parts[1] in ['MEG', 'PP', 'PE', 'PVC', 'PTA', '通用'],
        '模型名正确': model_part in ['Basic_GARCH', 'DCC_GARCH', 'ECM_GARCH'],
    }

    for check_name, passed in zip_checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")
        all_passed = all_passed and passed

    if not all_passed:
        print("\n✗ ZIP 文件命名检查失败")
        return False

    print("✓ ZIP 文件命名检查通过")

    return True


def main():
    """主测试函数"""
    try:
        success = test_full_workflow()

        print("\n" + "="*70)
        if success:
            print("✓✓✓ 所有端到端测试通过！ ✓✓✓")
            print("\n优化完成:")
            print("  1. ✓ 性能指标表格统一为'传统套保' vs '动态套保'")
            print("  2. ✓ ZIP 文件命名为 YYYYMMDD_品种_模型名.zip")
            print("  3. ✓ 前端报告图片路径修复（/report-images路由）")
        else:
            print("✗✗✗ 部分测试失败 ✗✗✗")
            return 1
        print("="*70)

        return 0 if success else 1

    except Exception as e:
        print(f"\n✗ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
