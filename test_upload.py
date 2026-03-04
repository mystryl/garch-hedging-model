#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试文件上传功能
"""

import requests
import sys
from pathlib import Path

BASE_URL = 'http://localhost:5000'

def test_upload():
    """测试文件上传"""

    # 测试文件路径
    test_file = Path(__file__).parent / '乙二醇价格 基差.xlsx'

    if not test_file.exists():
        print(f"错误: 测试文件不存在: {test_file}")
        return False

    print(f"测试文件: {test_file}")
    print(f"文件大小: {test_file.stat().st_size / 1024:.2f} KB")

    # 准备上传
    url = f'{BASE_URL}/api/upload'

    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}

            print("\n正在上传文件...")
            response = requests.post(url, files=files, timeout=30)

            print(f"状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("\n上传成功!")
                print(f"文件名: {result.get('filename')}")
                print(f"文件路径: {result.get('filepath')}")
                print(f"工作表数量: {len(result.get('sheets', []))}")
                print(f"推荐工作表: {result.get('recommended_sheet')}")
                print(f"\n消息: {result.get('message')}")

                # 显示工作表信息
                sheets = result.get('sheets', [])
                if sheets:
                    print("\n工作表列表:")
                    for i, sheet in enumerate(sheets, 1):
                        print(f"  {i}. {sheet.get('name')} - {sheet.get('row_count', 'N/A')} 行 x {sheet.get('column_count', 'N/A')} 列")
                        if sheet.get('date_range'):
                            dr = sheet['date_range']
                            print(f"     日期范围: {dr.get('start')} 至 {dr.get('end')} ({dr.get('count')} 个数据点)")

                return True
            else:
                error = response.json()
                print(f"\n上传失败: {error.get('error', '未知错误')}")
                return False

    except requests.exceptions.ConnectionError:
        print("\n错误: 无法连接到服务器")
        print("请确保Flask应用正在运行: python app.py")
        return False
    except Exception as e:
        print(f"\n错误: {str(e)}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("文件上传功能测试")
    print("=" * 60)

    # 首先检查健康状态
    try:
        response = requests.get(f'{BASE_URL}/health', timeout=5)
        if response.status_code == 200:
            print("服务器运行正常 ✓")
        else:
            print("服务器响应异常")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器")
        print("请先启动Flask应用: python app.py")
        sys.exit(1)
    except Exception as e:
        print(f"健康检查失败: {str(e)}")
        sys.exit(1)

    print()

    # 执行上传测试
    success = test_upload()

    print("\n" + "=" * 60)
    if success:
        print("测试通过 ✓")
    else:
        print("测试失败 ✗")
    print("=" * 60)

    sys.exit(0 if success else 1)
