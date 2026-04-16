# -*- coding: utf-8 -*-
"""
价差套利分析 — 数据加载与预处理

复用平台现有数据清洗逻辑，接收两个价格列。
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


class SpreadDataLoader:
    """价差数据加载器"""

    def __init__(self):
        self.raw_df: Optional[pd.DataFrame] = None
        self.df: Optional[pd.DataFrame] = None
        self.series_a_name: str = ""
        self.series_b_name: str = ""
        self.date_col: str = ""

    def load(
        self,
        filepath: str,
        sheet_name: str,
        col_a: str,
        col_b: str,
        date_col: str = None,
        skip_rows: int = 0,
        date_range: dict = None,
    ) -> pd.DataFrame:
        """
        加载并预处理数据

        Parameters
        ----------
        filepath : str
            Excel 文件路径
        sheet_name : str
            工作表名称
        col_a : str
            价格序列 A 列名
        col_b : str
            价格序列 B 列名
        date_col : str, optional
            日期列名，默认自动检测
        skip_rows : int
            跳过的行数（跳过表头前元数据）
        date_range : dict, optional
            日期范围过滤 {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}

        Returns
        -------
        pd.DataFrame
            包含 date, price_a, price_b, spread 列的 DataFrame
        """
        self.series_a_name = col_a
        self.series_b_name = col_b

        # 读取 Excel
        read_kwargs = {'sheet_name': sheet_name}
        if skip_rows > 0:
            read_kwargs['header'] = skip_rows

        self.raw_df = pd.read_excel(filepath, **read_kwargs)

        # 清洗元数据行（复用平台逻辑）
        self.raw_df = self._clean_metadata_rows(self.raw_df)
        if self.raw_df is None:
            raise ValueError("数据清洗后为空，请检查文件格式")

        # 自动检测日期列
        if date_col is None:
            date_col = self._detect_date_column(self.raw_df)
        self.date_col = date_col

        # 解析日期
        if date_col and date_col in self.raw_df.columns:
            self.raw_df[date_col] = pd.to_datetime(
                self.raw_df[date_col], errors='coerce'
            )
            self.raw_df = self.raw_df.dropna(subset=[date_col])
            self.raw_df = self.raw_df.sort_values(date_col).reset_index(drop=True)

        # 提取两列价格
        if col_a not in self.raw_df.columns:
            raise ValueError(f"列 '{col_a}' 不存在，可用列: {list(self.raw_df.columns)}")
        if col_b not in self.raw_df.columns:
            raise ValueError(f"列 '{col_b}' 不存在，可用列: {list(self.raw_df.columns)}")

        # 构建分析用 DataFrame
        result = pd.DataFrame()
        if date_col:
            result['date'] = self.raw_df[date_col]
        result['price_a'] = pd.to_numeric(self.raw_df[col_a], errors='coerce')
        result['price_b'] = pd.to_numeric(self.raw_df[col_b], errors='coerce')

        # 删除缺失值
        before_len = len(result)
        result = result.dropna()
        after_len = len(result)
        if after_len < before_len:
            print(f"  [数据清洗] 删除 {before_len - after_len} 行含缺失值的数据")

        if len(result) < 100:
            raise ValueError(
                f"有效数据仅 {len(result)} 行，至少需要 100 个交易日"
            )

        # 日期范围过滤
        if date_range and date_col and 'date' in result.columns:
            start = date_range.get('start')
            end = date_range.get('end')
            if start:
                result = result[result['date'] >= pd.Timestamp(start)]
            if end:
                result = result[result['date'] <= pd.Timestamp(end)]

        # 计算价差
        result['spread'] = result['price_a'] - result['price_b']
        result['log_spread'] = np.log(result['spread'] / result['spread'].shift(1))
        result['spread_return'] = result['spread'].pct_change()

        # 最终清洗
        result = result.dropna().reset_index(drop=True)

        self.df = result
        return result

    def get_info(self) -> dict:
        """返回数据摘要信息"""
        if self.df is None:
            return {}

        df = self.df
        return {
            'total_rows': len(df),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A',
                'end': df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A',
            },
            'series_a': {
                'name': self.series_a_name,
                'mean': float(df['price_a'].mean()),
                'std': float(df['price_a'].std()),
            },
            'series_b': {
                'name': self.series_b_name,
                'mean': float(df['price_b'].mean()),
                'std': float(df['price_b'].std()),
            },
            'spread': {
                'mean': float(df['spread'].mean()),
                'std': float(df['spread'].std()),
                'min': float(df['spread'].min()),
                'max': float(df['spread'].max()),
            },
        }

    # ========================
    # 内部方法
    # ========================

    @staticmethod
    def _clean_metadata_rows(df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗 Excel 中的元数据行

        处理钢联数据等常见格式：
        - 表头后可能有「频度」「指标描述」等元数据行
        - 需要找到第一行包含实际数值/日期数据的行，删除其前面的所有行
        """
        if df is None or df.empty:
            return None

        # 删除全空行
        df = df.dropna(how='all').reset_index(drop=True)

        # 删除 Unnamed 列（Unnamed: 0 等）
        unnamed_cols = [c for c in df.columns if str(c).startswith('Unnamed')]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)

        if df.empty:
            return None

        # 检测数据行的起始位置：逐行判断，找到第一个"数值/日期行"
        # 一行是数据行 = 至少有一列能解析为数字或日期
        data_start = 0
        for idx in range(len(df)):
            row = df.iloc[idx]
            has_numeric_or_date = False
            for val in row.values:
                if pd.isna(val):
                    continue
                # 尝试解析为数字
                try:
                    float(val)
                    has_numeric_or_date = True
                    break
                except (ValueError, TypeError):
                    pass
                # 尝试解析为日期
                try:
                    pd.to_datetime(val)
                    has_numeric_or_date = True
                    break
                except (ValueError, TypeError):
                    pass

            if has_numeric_or_date:
                # 还需要确认这行不是纯文字的元数据描述
                # 钢联数据的"频度"行第一列是"频度"（文字），后面的值是"日"（文字）
                # 但"指标描述"行后面的值是长文字描述
                # 真正的数据行第一列是日期(datetime)，后面是数字
                first_val = row.iloc[0]
                try:
                    pd.to_datetime(first_val)
                    data_start = idx
                    break
                except (ValueError, TypeError):
                    # 第一列不是日期，继续看
                    # 如果这一行有多个数字列，也认为是数据行
                    num_count = 0
                    for v in row.values:
                        try:
                            float(v)
                            num_count += 1
                        except (ValueError, TypeError):
                            pass
                    if num_count >= 2:
                        data_start = idx
                        break
                    continue

        if data_start > 0:
            df = df.iloc[data_start:].reset_index(drop=True)

        return df

    @staticmethod
    def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
        """自动检测日期列"""
        for col in df.columns:
            try:
                sample = df[col].dropna().head(20)
                if sample.empty:
                    continue
                dates = pd.to_datetime(sample, errors='coerce')
                valid_ratio = dates.notna().sum() / len(sample)
                if valid_ratio >= 0.8:
                    return col
            except Exception:
                continue
        return None
