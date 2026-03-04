"""
DCC-GARCH 套保模型分析器
模块化架构
"""
from .dcc_model import fit_dcc_garch
from .rolling_backtest import run_rolling_backtest
from .config import DCCGarchConfig

__all__ = [
    'fit_dcc_garch',
    'run_rolling_backtest',
    'DCCGarchConfig',
]
