"""
ECM-GARCH 配置管理
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ECMGarchConfig:
    """
    ECM-GARCH 模型配置

    Attributes:
    -----------
    coint_window : int
        协整检验滚动窗口大小
    coupling_method : str
        ECM-GARCH耦合方式 ('ect-garch' 或其他)
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
    # 协整参数
    coint_window: int = 60

    # ECM-GARCH 耦合方法
    coupling_method: str = 'ect-garch'

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
    def from_dict(cls, config_dict: dict) -> 'ECMGarchConfig':
        """
        从字典创建配置对象

        Parameters:
        -----------
        config_dict : dict
            配置字典

        Returns:
        --------
        config : ECMGarchConfig
            配置对象
        """
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})
