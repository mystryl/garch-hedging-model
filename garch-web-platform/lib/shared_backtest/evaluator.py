"""
回测评估指标计算
从 Basic GARCH 的 backtest_evaluator.py 抽取通用指标计算函数
"""
import numpy as np


def calculate_max_drawdown(cumulative_returns):
    """
    计算最大回撤

    Parameters:
    -----------
    cumulative_returns : np.array
        累计收益率序列

    Returns:
    --------
    max_dd : float
        最大回撤
    """
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns - running_max) / running_max
    max_dd = np.min(drawdown)
    return max_dd


def calculate_var(returns, confidence_level=0.95):
    """
    计算历史模拟法的 VaR (Value at Risk)

    Parameters:
    -----------
    returns : np.array
        收益率序列
    confidence_level : float
        置信水平（默认95%）

    Returns:
    --------
    var : float
        VaR 值（负数表示损失）
    """
    return -np.percentile(returns, (1 - confidence_level) * 100)


def calculate_cvar(returns, confidence_level=0.95):
    """
    计算条件风险价值 CVaR (Conditional Value at Risk)
    也称为 Expected Shortfall (ES)

    Parameters:
    -----------
    returns : np.array
        收益率序列
    confidence_level : float
        置信水平（默认95%）

    Returns:
    --------
    cvar : float
        CVaR 值（负数表示损失）
    """
    var = calculate_var(returns, confidence_level)
    # 计算超过 VaR 阈值的平均损失
    return -np.mean(returns[returns <= var])
