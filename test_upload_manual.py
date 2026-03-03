#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动测试文件上传API
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.data_processor import get_all_sheets_info, preview_sheet

def test_data_processor():
    """测试数据处理器"""

    print("=" * 60)
    print("数据处理器测试")
    print("=" * 60)

    # 测试文件
    test_file = Path(__file__).parent / '乙二醇价格 基差.xlsx'

    if not test_file.exists():
        print(f"错误: 测试文件不存在: {test_file}")
        return False

    print(f"\n测试文件: {test_file}")
    print(f"文件大小: {test_file.stat().st_size / 1024:.2f} KB\n")

    try:
        # 获取所有工作表信息
        print("正在读取工作表信息...")
        sheets_info = get_all_sheets_info(str(test_file))

        print(f"✓ 成功读取 {len(sheets_info)} 个工作表\n")

        # 显示工作表信息
        for i, sheet in enumerate(sheets_info, 1):
            print(f"工作表 {i}: {sheet.get('name')}")
            print(f"  - 行数: {sheet.get('row_count', 'N/A')}")
            print(f"  - 列数: {sheet.get('column_count', 'N/A')}")
            print(f"  - 列名: {', '.join(sheet.get('columns', []))}")

            if sheet.get('date_range'):
                dr = sheet['date_range']
                print(f"  - 日期范围: {dr.get('start')} 至 {dr.get('end')} ({dr.get('count')} 个数据点)")

            # 测试预览功能
            if sheet.get('has_data'):
                print(f"\n  预览前5行数据:")
                preview = preview_sheet(str(test_file), sheet['name'], nrows=5)
                for j, row in enumerate(preview['preview_data'], 1):
                    print(f"    行{j}: {row}")

            print()

        # 测试推荐算法
        print("\n测试工作表推荐算法:")
        recommended = recommend_sheet(sheets_info)
        print(f"✓ 推荐工作表: {recommended}")

        print("\n" + "=" * 60)
        print("测试通过 ✓")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("测试失败 ✗")
        print("=" * 60)
        return False


def recommend_sheet(sheets_info):
    """
    根据工作表信息智能推荐最佳工作表（复制自app.py）
    """
    if not sheets_info:
        return None

    # 评分系统
    scored_sheets = []

    for sheet in sheets_info:
        if 'error' in sheet or not sheet.get('has_data'):
            continue

        score = 0
        name = sheet['name'].lower()
        columns = [col.lower() for col in sheet.get('columns', [])]

        # 1. 检查工作表名称（优先级最高）
        if any(keyword in name for keyword in ['数据', 'data', '价格', 'price', '期货', '现货', 'future', 'spot']):
            score += 50

        # 2. 检查列名（包含价格、日期、期货、现货等关键词）
        price_keywords = ['价格', 'price', '收盘', 'close', '期货', 'future', '现货', 'spot']
        date_keywords = ['日期', 'date', '时间', 'time']

        for col in columns:
            if any(keyword in col for keyword in price_keywords):
                score += 15
            if any(keyword in col for keyword in date_keywords):
                score += 10

        # 3. 检查是否有日期范围
        if sheet.get('date_range'):
            score += 20

        # 4. 检查数据量（数据量适中加分）
        row_count = sheet.get('row_count', 0)
        if 100 <= row_count <= 10000:
            score += 10

        scored_sheets.append({
            'name': sheet['name'],
            'score': score
        })

        print(f"  工作表 '{sheet['name']}' 得分: {score}")

    # 返回得分最高的工作表
    if scored_sheets:
        scored_sheets.sort(key=lambda x: x['score'], reverse=True)
        return scored_sheets[0]['name']

    # 如果没有合适的工作表，返回第一个有效的
    for sheet in sheets_info:
        if sheet.get('has_data'):
            return sheet['name']

    return None


if __name__ == '__main__':
    success = test_data_processor()
    sys.exit(0 if success else 1)
