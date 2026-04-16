# -*- coding: utf-8 -*-
"""
价差套利分析模块

功能：
- 两个价格序列的价差分析
- 平稳性检验 (ADF)、协整检验 (Johansen)
- OU 过程半衰期估计
- 滚动 Z-Score + GARCH 动态阈值
- 回测引擎 + 报告生成
"""

from .config import SpreadConfig
from .data_loader import SpreadDataLoader
from .spread_analyzer import SpreadAnalyzer
from .backtest_engine import SpreadBacktestEngine
from .report_generator import SpreadReportGenerator

__all__ = [
    'SpreadConfig',
    'SpreadDataLoader',
    'SpreadAnalyzer',
    'SpreadBacktestEngine',
    'SpreadReportGenerator',
]
