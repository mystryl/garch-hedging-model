"""
Basic GARCH Analyzer 配置模块
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelConfig:
    """
    GARCH 模型配置参数

    默认值基于学术文献和实际应用经验
    """
    # GARCH 模型参数
    p: int = 1
    q: int = 1
    mean_model: str = 'Constant'
    vol_model: str = 'GARCH'
    distribution: str = 'normal'

    # 套保参数
    corr_window: int = 120  # 动态相关系数滚动窗口（约4个月交易日）
    tax_rate: float = 0.13  # 增值税率（用于调整套保比例）

    # 输出配置
    output_dir: str = 'outputs'
    save_intermediate: bool = True

    def __post_init__(self):
        """验证参数合理性"""
        if self.p < 1 or self.q < 1:
            raise ValueError(f"GARCH阶数必须 >= 1, 得到 p={self.p}, q={self.q}")

        if self.corr_window < 30:
            raise ValueError(f"相关系数窗口至少30天, 得到 {self.corr_window}")

        if not 0 <= self.tax_rate <= 1:
            raise ValueError(f"税率必须在[0,1]之间, 得到 {self.tax_rate}")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'GARCH(p,q)': f'({self.p}, {self.q})',
            '相关系数窗口': f'{self.corr_window}天',
            '税点调整': f'{self.tax_rate:.1%}',
        }


def create_config(**kwargs) -> ModelConfig:
    """
    创建配置对象的工厂函数

    Parameters:
    -----------
    **kwargs: 配置参数覆盖

    Returns:
    --------
    ModelConfig: 配置对象

    Example:
    --------
    >>> config = create_config(p=2, tax_rate=0.0)
    >>> print(config.to_dict())
    """
    return ModelConfig(**kwargs)
