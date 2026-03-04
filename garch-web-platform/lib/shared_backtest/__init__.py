"""
共享的滚动回测模块

从 Basic GARCH 的滚动回测实现中抽取通用逻辑，
供 Basic GARCH、DCC-GARCH、ECM-GARCH 三个模型复用。

主要模块：
- backtest_core: 核心回测逻辑（日期选择、单周期回测、完整回测）
- evaluator: 评估指标计算（VaR、CVaR、最大回撤等）
- plotter: 通用绘图函数（净值曲线、回撤曲线、周期对比）
"""

from .backtest_core import (
    is_delivery_month,
    is_near_delivery_month,
    select_backtest_start_dates,
    run_single_period_backtest,
    run_rolling_backtest
)

from .evaluator import (
    calculate_max_drawdown,
    calculate_var,
    calculate_cvar
)

from .plotter import (
    plot_rolling_nav_curve,
    plot_rolling_drawdown,
    plot_period_comparison
)

__all__ = [
    # 核心回测逻辑
    'is_delivery_month',
    'is_near_delivery_month',
    'select_backtest_start_dates',
    'run_single_period_backtest',
    'run_rolling_backtest',
    # 评估指标
    'calculate_max_drawdown',
    'calculate_var',
    'calculate_cvar',
    # 绘图函数
    'plot_rolling_nav_curve',
    'plot_rolling_drawdown',
    'plot_period_comparison',
]
