"""
数据加载模块
支持从 Excel 加载数据，自动识别列名，选择品种
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加项目根目录到路径以导入 utils
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.data_processor import _clean_metadata_rows


# 自定义异常
class DataLoadError(Exception):
    """数据加载基础异常"""
    pass


class ColumnNotFoundError(DataLoadError):
    """列不存在错误"""
    pass


class InsufficientDataError(DataLoadError):
    """数据量不足错误"""
    pass


def load_data_from_excel(file_path, sheet_name=0, skip_rows=0):
    """
    从 Excel 文件加载数据并显示可用列

    Parameters:
    -----------
    file_path : str
        Excel 文件路径
    sheet_name : str or int
        工作表名称或索引
    skip_rows : int, optional
        跳过的行数（用于处理多行标题）

    Returns:
    --------
    df : pd.DataFrame
        原始数据
    available_columns : list
        可用列名列表
    """
    print("\n" + "=" * 60)
    print("数据加载")
    print("=" * 60)

    # 读取数据（使用 header 参数指定哪一行作为列名）
    if skip_rows > 0:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=skip_rows)
        print(f"✓ 跳过前 {skip_rows} 行，使用第 {skip_rows + 1} 行作为表头")
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"✓ 使用第一行作为表头")

    print(f"\n✓ 成功读取 Excel 文件: {file_path}")
    print(f"✓ 工作表: {sheet_name}")
    print(f"  原始数据行数: {len(df)}")
    print(f"  原始数据列数: {len(df.columns)}")

    # 清理元数据行（如 "频度"、"指标描述" 等非数据行）
    df_cleaned = _clean_metadata_rows(df)
    if df_cleaned is not None:
        df = df_cleaned
        print(f"  ✓ 清理元数据后数据行数: {len(df)}")

    print(f"\n可用列名:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")

    print(f"\n数据预览 (前5行):")
    print(df.head())

    return df, list(df.columns)


def select_columns_interactive(df, available_columns):
    """
    交互式选择日期、现货、期货列

    Parameters:
    -----------
    df : pd.DataFrame
        数据框
    available_columns : list
        可用列名列表

    Returns:
    --------
    selected : dict
        选择的列名 {'date': '', 'spot': '', 'futures': ''}
    """
    print("\n" + "=" * 60)
    print("列名选择")
    print("=" * 60)

    # 自动检测日期列
    date_columns = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            date_columns.append(col)
        elif '日期' in str(col) or 'date' in str(col).lower():
            date_columns.append(col)

    if date_columns:
        print(f"\n自动检测到日期列: {date_columns}")
        date_col = date_columns[0]
    else:
        print(f"\n请手动选择日期列:")
        for i, col in enumerate(available_columns, 1):
            print(f"  {i}. {col}")
        date_idx = int(input("请输入日期列编号: ")) - 1
        date_col = available_columns[date_idx]

    # 选择现货列
    print(f"\n请选择现货价格列:")
    for i, col in enumerate(available_columns, 1):
        print(f"  {i}. {col}")
    spot_idx = int(input("请输入现货列编号: ")) - 1
    spot_col = available_columns[spot_idx]

    # 选择期货列
    print(f"\n请选择期货价格列:")
    for i, col in enumerate(available_columns, 1):
        print(f"  {i}. {col}")
    futures_idx = int(input("请输入期货列编号: ")) - 1
    futures_col = available_columns[futures_idx]

    selected = {
        'date': date_col,
        'spot': spot_col,
        'futures': futures_col
    }

    print(f"\n✓ 已选择:")
    print(f"  日期列: {date_col}")
    print(f"  现货列: {spot_col}")
    print(f"  期货列: {futures_col}")

    return selected


def select_columns_auto(df, available_columns, date_col=None, spot_col=None, futures_col=None):
    """
    自动或手动指定列名（非交互式）

    Parameters:
    -----------
    df : pd.DataFrame
        数据框
    available_columns : list
        可用列名列表
    date_col : str or None
        日期列名（None 则自动检测）
    spot_col : str or None
        现货列名
    futures_col : str or None
        期货列名

    Returns:
    --------
    selected : dict
        选择的列名
    """
    print("\n" + "=" * 60)
    print("列名配置")
    print("=" * 60)

    # 自动检测日期列
    if date_col is None:
        date_columns = []
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                date_columns.append(col)
            elif '日期' in str(col) or 'date' in str(col).lower():
                date_columns.append(col)
        date_col = date_columns[0] if date_columns else available_columns[0]

    # 验证列是否存在
    if spot_col and spot_col not in available_columns:
        raise ValueError(f"现货列 '{spot_col}' 不存在")
    if futures_col and futures_col not in available_columns:
        raise ValueError(f"期货列 '{futures_col}' 不存在")

    selected = {
        'date': date_col,
        'spot': spot_col,
        'futures': futures_col
    }

    print(f"\n列名配置:")
    print(f"  日期列: {date_col}")
    print(f"  现货列: {spot_col}")
    print(f"  期货列: {futures_col}")

    return selected


def preprocess_data(df, selected, output_file=None, min_required=120):
    """
    预处理数据：清洗、计算收益率、基差

    Parameters:
    -----------
    df : pd.DataFrame
        原始数据
    selected : dict
        选择的列名
    output_file : str or None
        输出文件路径
    min_required : int
        最小数据量要求

    Returns:
    --------
    data : pd.DataFrame
        预处理后的数据
    """
    print("\n" + "=" * 60)
    print("数据预处理")
    print("=" * 60)

    # 提取选择的列
    date_col = selected['date']
    spot_col = selected['spot']
    futures_col = selected['futures']

    data = df[[date_col, spot_col, futures_col]].copy()
    data.columns = ['date', 'spot', 'futures']

    # 转换日期格式
    data['date'] = pd.to_datetime(data['date'])

    # 转换数值列为float类型（关键修复）
    data['spot'] = pd.to_numeric(data['spot'], errors='coerce')
    data['futures'] = pd.to_numeric(data['futures'], errors='coerce')

    # 删除缺失值
    original_len = len(data)
    data = data.dropna()
    deleted_na = original_len - len(data)

    # 按日期排序
    data = data.sort_values('date').reset_index(drop=True)

    # 删除异常值（价格为负数或0）
    data = data[(data['spot'] > 0) & (data['futures'] > 0)]
    deleted_abnormal = original_len - deleted_na - len(data)

    print(f"\n数据清洗:")
    print(f"  原始数据量: {original_len}")
    print(f"  删除缺失值: {deleted_na}")
    print(f"  删除异常值: {deleted_abnormal}")
    print(f"  有效数据量: {len(data)}")
    print(f"  时间范围: {data['date'].min()} 至 {data['date'].max()}")

    # 计算对数收益率
    data['r_s'] = np.log(data['spot'] / data['spot'].shift(1))
    data['r_f'] = np.log(data['futures'] / data['futures'].shift(1))

    # 删除第一行（收益率 NaN）
    data = data.dropna()

    # 计算基差
    data['spread'] = data['spot'] - data['futures']

    print(f"\n数据统计:")
    print(f"  现货价格: dtype={data['spot'].dtype}, 均值={data['spot'].mean():.2f}, 标准差={data['spot'].std():.2f}")
    print(f"  期货价格: dtype={data['futures'].dtype}, 均值={data['futures'].mean():.2f}, 标准差={data['futures'].std():.2f}")
    print(f"  基差: 均值={data['spread'].mean():.2f}, 标准差={data['spread'].std():.2f}")
    print(f"  相关系数: {data['spot'].corr(data['futures']):.4f}")

    # 保存预处理后的数据
    if output_file:
        data.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✓ 已保存预处理数据: {output_file}")

    # 数据量验证
    if len(data) < min_required:
        raise InsufficientDataError(
            f"数据量不足: 需要 >= {min_required} 天, 实际 {len(data)} 天"
        )

    return data


def load_and_preprocess(file_path, sheet_name=None, date_col=None, spot_col=None, futures_col=None,
                        skip_rows=0, output_file=None, interactive=False, min_required=120):
    """
    完整的数据加载和预处理流程

    Parameters:
    -----------
    file_path : str
        Excel 文件路径
    sheet_name : str, int or None
        工作表名称或索引，None 表示第一个工作表
    date_col : str or None
        日期列名
    spot_col : str or None
        现货列名
    futures_col : str or None
        期货列名
    skip_rows : int, optional
        跳过的行数（用于处理多行标题）
    output_file : str or None
        输出文件路径
    interactive : bool
        是否交互式选择列名
    min_required : int
        最小数据量要求

    Returns:
    --------
    data : pd.DataFrame
        预处理后的数据
    selected : dict
        选择的列名
    """
    # 加载数据
    df, available_columns = load_data_from_excel(file_path, sheet_name=sheet_name, skip_rows=skip_rows)

    # 选择列名
    if interactive:
        selected = select_columns_interactive(df, available_columns)
    else:
        selected = select_columns_auto(df, available_columns, date_col, spot_col, futures_col)

    # 预处理
    data = preprocess_data(df, selected, output_file, min_required)

    return data, selected
