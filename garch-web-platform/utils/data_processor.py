#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据处理器模块
用于读取和处理Excel文件
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _convert_nan_to_none(obj):
    """
    递归将NaN和Inf转换为None，确保JSON可序列化

    Parameters
    ----------
    obj : Any
        要转换的对象

    Returns
    -------
    Any
        转换后的对象
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _convert_nan_to_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_nan_to_none(item) for item in obj]
    else:
        return obj


def _clean_metadata_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    清理数据框中的元数据行（如"频度"、"指标描述"等）

    Parameters
    ----------
    df : pd.DataFrame
        原始数据框

    Returns
    -------
    pd.DataFrame
        清理后的数据框
    """
    if df.empty:
        return df

    # 定义需要过滤的关键词
    filter_keywords = ['频度', '指标描述', '单位', '数据来源', '钢联数据']

    # 检查第一列是否包含这些关键词
    if len(df.columns) > 0:
        first_col = df.iloc[:, 0].astype(str)
        # 过滤掉包含关键词的行
        mask = ~first_col.str.contains('|'.join(filter_keywords), na=False)
        df_cleaned = df[mask].copy()
        df_cleaned = df_cleaned.reset_index(drop=True)

        if len(df_cleaned) < len(df):
            logger.info(f"清理了 {len(df) - len(df_cleaned)} 行元数据")
            return df_cleaned

    return df


def read_excel_sheets(filepath: str, skip_rows: int = 0) -> Dict[str, pd.DataFrame]:
    """
    读取Excel文件中的所有工作表

    Parameters
    ----------
    filepath : str
        Excel文件路径
    skip_rows : int, optional
        跳过的行数，默认为0（不跳过）

    Returns
    -------
    Dict[str, pd.DataFrame]
        字典，键为工作表名称，值为对应的数据框
    """
    try:
        # 读取所有工作表
        excel_file = pd.ExcelFile(filepath)
        sheets = {}

        for sheet_name in excel_file.sheet_names:
            try:
                if skip_rows > 0:
                    # 跳过前N行：使用第skip_rows行作为表头
                    # header参数指定哪一行作为列名（0-indexed）
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=skip_rows)
                    logger.info(f"工作表 {sheet_name}: 跳过前{skip_rows}行，使用第{skip_rows + 1}行作为表头")
                else:
                    # 不跳过：第一行作为表头
                    df = pd.read_excel(filepath, sheet_name=sheet_name, header=0)
                    logger.info(f"工作表 {sheet_name}: 使用第一行作为表头")

                # 清理元数据行
                df = _clean_metadata_rows(df)

                sheets[sheet_name] = df
                logger.info(f"成功读取工作表: {sheet_name}, 形状: {df.shape}")
            except Exception as e:
                logger.warning(f"读取工作表 {sheet_name} 失败: {str(e)}")
                continue

        return sheets

    except Exception as e:
        logger.error(f"读取Excel文件失败: {str(e)}")
        raise


def preview_sheet(filepath: str, sheet_name: str, nrows: int = 10, skip_rows: int = 0) -> Dict[str, Any]:
    """
    预览工作表数据，包括数据概览和日期范围检测

    Parameters
    ----------
    filepath : str
        Excel文件路径
    sheet_name : str
        工作表名称
    nrows : int, optional
        预览行数，默认为10
    skip_rows : int, optional
        跳过的行数，默认为0

    Returns
    -------
    Dict[str, Any]
        包含预览数据和元信息的字典
    """
    try:
        if skip_rows > 0:
            # 跳过前N行：使用header参数指定列名行
            df = pd.read_excel(filepath, sheet_name=sheet_name, header=skip_rows, nrows=nrows * 2)
            full_df = pd.read_excel(filepath, sheet_name=sheet_name, header=skip_rows)
            logger.info(f"预览工作表 {sheet_name}: 跳过前{skip_rows}行")
        else:
            # 不跳过：正常读取
            df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=nrows)
            full_df = pd.read_excel(filepath, sheet_name=sheet_name)
            logger.info(f"预览工作表 {sheet_name}: 使用第一行作为表头")

        # 清理元数据行
        df = _clean_metadata_rows(df)
        full_df = _clean_metadata_rows(full_df)

        # 预览数据只显示前nrows行
        df = df.head(nrows)

        # 检测日期列（用于 date_range 和返回给前端）
        date_columns = _detect_date_columns(full_df)

        # 格式化第一列为 yyyy/mm/dd 格式（仅对预览数据）
        # 假设第一列始终是日期列
        if len(df.columns) > 0:
            first_col = df.columns[0]
            df[first_col] = pd.to_datetime(df[first_col], errors='coerce').dt.strftime('%Y/%m/%d')
            # 将 NaT（无效日期）转换为 None
            df[first_col] = df[first_col].replace('NaT', None)

        # 获取日期范围（格式：yyyy/mm/dd）
        date_range = None
        if date_columns:
            primary_date_col = date_columns[0]
            try:
                dates = pd.to_datetime(full_df[primary_date_col], errors='coerce')
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    date_range = {
                        'start': valid_dates.min().strftime('%Y/%m/%d'),
                        'end': valid_dates.max().strftime('%Y/%m/%d'),
                        'count': len(valid_dates)
                    }
            except Exception as e:
                logger.warning(f"获取日期范围失败: {str(e)}")

        # 构建预览信息（列名统一转 str，防止 datetime 等类型混入）
        df.columns = [str(c) for c in df.columns]
        full_df.columns = [str(c) for c in full_df.columns]
        preview_info = {
            'sheet_name': sheet_name,
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'shape': full_df.shape,
            'preview_data': _convert_nan_to_none(df.to_dict('records')),
            'date_columns': date_columns,
            'date_range': date_range,
            'has_data': not df.empty,
            'skipped_rows': skip_rows
        }

        return preview_info

    except Exception as e:
        logger.error(f"预览工作表失败: {str(e)}")
        raise


def _detect_date_columns(df: pd.DataFrame) -> List[str]:
    """
    检测数据框中的日期列

    Parameters
    ----------
    df : pd.DataFrame
        数据框

    Returns
    -------
    List[str]
        日期列名称列表
    """
    date_columns = []

    for col in df.columns:
        # 尝试转换为日期
        try:
            # 跳过NaN值进行测试
            sample = df[col].dropna().head(100)
            if sample.empty:
                continue

            # 尝试解析为日期
            dates = pd.to_datetime(sample, errors='coerce')

            # 如果超过80%的值可以解析为日期，则认为是日期列
            valid_ratio = dates.notna().sum() / len(sample)
            if valid_ratio > 0.8:
                date_columns.append(col)
        except Exception:
            continue

    return date_columns


def get_all_sheets_info(filepath: str, skip_rows: int = 0) -> List[Dict[str, Any]]:
    """
    获取所有工作表的信息

    Parameters
    ----------
    filepath : str
        Excel文件路径
    skip_rows : int, optional
        跳过的行数，默认为0

    Returns
    -------
    List[Dict[str, Any]]
        工作表信息列表
    """
    try:
        excel_file = pd.ExcelFile(filepath)
        sheets_info = []

        for sheet_name in excel_file.sheet_names:
            try:
                preview = preview_sheet(filepath, sheet_name, nrows=5, skip_rows=skip_rows)
                sheets_info.append({
                    'name': sheet_name,
                    'row_count': preview['shape'][0],
                    'column_count': preview['shape'][1],
                    'columns': preview['columns'],
                    'has_data': preview['has_data'],
                    'date_range': preview['date_range']
                })
            except Exception as e:
                logger.warning(f"获取工作表 {sheet_name} 信息失败: {str(e)}")
                sheets_info.append({
                    'name': sheet_name,
                    'error': str(e)
                })

        return sheets_info

    except Exception as e:
        logger.error(f"获取工作表信息失败: {str(e)}")
        raise


def validate_required_columns(df: pd.DataFrame, required_cols: List[str]) -> Tuple[bool, List[str]]:
    """
    验证数据框是否包含必需的列

    Parameters
    ----------
    df : pd.DataFrame
        数据框
    required_cols : List[str]
        必需的列名列表

    Returns
    -------
    Tuple[bool, List[str]]
        (是否包含所有列, 缺失的列列表)
    """
    df_columns = [col.strip() for col in df.columns]
    missing_cols = [col for col in required_cols if col not in df_columns]
    return len(missing_cols) == 0, missing_cols


if __name__ == '__main__':
    # 测试代码
    test_file = Path(__file__).parent.parent / '乙二醇价格 基差.xlsx'
    if test_file.exists():
        print(f"测试文件: {test_file}")
        sheets = read_excel_sheets(str(test_file))
        print(f"找到 {len(sheets)} 个工作表")

        info = get_all_sheets_info(str(test_file))
        for sheet_info in info:
            print(f"\n工作表: {sheet_info['name']}")
            print(f"  行数: {sheet_info.get('row_count', 'N/A')}")
            print(f"  列数: {sheet_info.get('column_count', 'N/A')}")
            print(f"  日期范围: {sheet_info.get('date_range', 'N/A')}")
