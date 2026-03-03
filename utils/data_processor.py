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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_excel_sheets(filepath: str) -> Dict[str, pd.DataFrame]:
    """
    读取Excel文件中的所有工作表

    Parameters
    ----------
    filepath : str
        Excel文件路径

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
                df = pd.read_excel(filepath, sheet_name=sheet_name)
                sheets[sheet_name] = df
                logger.info(f"成功读取工作表: {sheet_name}, 形状: {df.shape}")
            except Exception as e:
                logger.warning(f"读取工作表 {sheet_name} 失败: {str(e)}")
                continue

        return sheets

    except Exception as e:
        logger.error(f"读取Excel文件失败: {str(e)}")
        raise


def preview_sheet(filepath: str, sheet_name: str, nrows: int = 10) -> Dict[str, Any]:
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

    Returns
    -------
    Dict[str, Any]
        包含预览数据和元信息的字典
    """
    try:
        # 读取数据
        df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=nrows)

        # 读取完整数据以检测日期范围
        full_df = pd.read_excel(filepath, sheet_name=sheet_name)

        # 检测日期列
        date_columns = _detect_date_columns(full_df)

        # 获取日期范围
        date_range = None
        if date_columns:
            primary_date_col = date_columns[0]
            try:
                dates = pd.to_datetime(full_df[primary_date_col], errors='coerce')
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    date_range = {
                        'start': valid_dates.min().strftime('%Y-%m-%d'),
                        'end': valid_dates.max().strftime('%Y-%m-%d'),
                        'count': len(valid_dates)
                    }
            except Exception as e:
                logger.warning(f"获取日期范围失败: {str(e)}")

        # 构建预览信息
        preview_info = {
            'sheet_name': sheet_name,
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'shape': full_df.shape,
            'preview_data': df.to_dict('records'),
            'date_columns': date_columns,
            'date_range': date_range,
            'has_data': not df.empty
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


def get_all_sheets_info(filepath: str) -> List[Dict[str, Any]]:
    """
    获取所有工作表的信息

    Parameters
    ----------
    filepath : str
        Excel文件路径

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
                preview = preview_sheet(filepath, sheet_name, nrows=5)
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
