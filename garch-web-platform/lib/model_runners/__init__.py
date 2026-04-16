"""
模型运行器模块 - GARCH套保模型统一接口

设计原则：
- 简洁直接，类似 run_meg_full.py 的风格
- 复用原始模型代码（model_*.py）
- 复用 basic_garch_analyzer 的报告生成系统
- 统一的输入输出接口

使用方式：
    >>> from lib.model_runners.basic_garch import run_basic_garch
    >>> result = run_basic_garch(
    ...     data_path='data.xlsx',
    ...     sheet_name='Sheet1',
    ...     spot_col='现货价格',
    ...     futures_col='期货价格',
    ...     date_col='日期',
    ...     output_dir='outputs/test'
    ... )
"""

from .basic_garch import run_basic_garch
from .dcc_garch import run_dcc_garch
from .ecm_garch import run_ecm_garch
from .spread_arbitrage import run_spread_arbitrage

__all__ = ['run_basic_garch', 'run_dcc_garch', 'run_ecm_garch', 'run_spread_arbitrage']
