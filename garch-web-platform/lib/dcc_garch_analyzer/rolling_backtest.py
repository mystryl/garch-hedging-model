"""
DCC-GARCH 滚动回测模块
复用共享回测核心逻辑
"""
import pandas as pd
import numpy as np
import os
from typing import Dict

from lib.shared_backtest.backtest_core import run_rolling_backtest as shared_run_backtest
from lib.shared_backtest.plotter import (
    plot_rolling_nav_curve,
    plot_rolling_drawdown,
    plot_period_comparison
)


def run_rolling_backtest(
    data: pd.DataFrame,
    hedge_ratios: np.ndarray,
    n_periods: int = 6,
    window_days: int = 90,
    min_gap_days: int = 180,
    seed: int = None,
    tax_rate: float = 0.13,
    output_dir: str = 'outputs'
) -> Dict:
    """
    运行 DCC-GARCH 滚动回测

    调用共享模块的核心回测逻辑

    Parameters:
    -----------
    data : pd.DataFrame
        数据（必须包含 date, r_s, r_f 列）
    hedge_ratios : np.ndarray
        套保比例序列
    n_periods : int
        回测周期数
    window_days : int
        每个周期天数
    min_gap_days : int
        起始日期之间的最小间隔天数
    seed : int, optional
        随机种子（None 表示不固定）
    tax_rate : float
        税率
    output_dir : str
        输出目录

    Returns:
    --------
    results : Dict
        滚动回测结果
    """
    print("\n[DCC-GARCH 滚动回测]")

    # 调用共享模块的核心回测逻辑
    results = shared_run_backtest(
        data=data,
        hedge_ratios=hedge_ratios,
        n_periods=n_periods,
        window_days=window_days,
        min_gap_days=min_gap_days,
        seed=seed,
        tax_rate=tax_rate
    )

    # 生成图表（复用共享绘图函数）
    generate_charts(results, output_dir)

    return results


def generate_charts(results: Dict, output_dir: str):
    """
    生成滚动回测图表

    使用共享绘图函数生成标准的滚动回测图表

    Parameters:
    -----------
    results : Dict
        回测结果
    output_dir : str
        输出目录
    """
    print("\n[生成 DCC-GARCH 滚动回测图表]...")

    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)

    # 使用共享绘图函数
    plot_rolling_nav_curve(results, os.path.join(figures_dir, '5_backtest_results.png'))
    plot_rolling_drawdown(results, os.path.join(figures_dir, '6_drawdown.png'))
    plot_period_comparison(results, os.path.join(figures_dir, '7_period_comparison.png'))

    print(f"  ✓ 图表已保存到: {figures_dir}")
