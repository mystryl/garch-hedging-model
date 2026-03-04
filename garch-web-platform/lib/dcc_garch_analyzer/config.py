"""
DCC-GARCH 配置管理
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DCCGarchConfig:
    """
    DCC-GARCH 模型配置

    Attributes:
    -----------
    p : int
        GARCH(p,q) 中的 p 参数
    q : int
        GARCH(p,q) 中的 q 参数
    dist : str
        分布假设 ('norm' 或 't')
    tax_rate : float
        税率调整（默认 0.13，对应 TAX_ADJUSTMENT_FACTOR = 1.13）
    enable_rolling_backtest : bool
        是否启用滚动回测
    n_periods : int
        滚动回测周期数
    window_days : int
        每个回测周期天数
    min_gap_days : int
        回测起始日期最小间隔
    backtest_seed : Optional[int]
        随机种子（None 表示不固定）
    output_dir : str
        输出目录
    """
    # GARCH 参数
    p: int = 1
    q: int = 1
    dist: str = 'norm'

    # 税率参数
    tax_rate: float = 0.13

    # 滚动回测参数
    enable_rolling_backtest: bool = False
    n_periods: int = 6
    window_days: int = 90
    min_gap_days: int = 180
    backtest_seed: Optional[int] = None

    # 输出配置
    output_dir: str = 'outputs'

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'DCCGarchConfig':
        """
        从字典创建配置对象

        Parameters:
        -----------
        config_dict : dict
            配置字典

        Returns:
        --------
        config : DCCGarchConfig
            配置对象
        """
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})
