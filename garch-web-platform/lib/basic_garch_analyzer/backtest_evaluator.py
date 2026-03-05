"""
回测评估模块（备份版本）
用于全样本回测（备选方案）
默认使用滚动回测模式（rolling_backtest.py）
"""
import pandas as pd
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


def evaluate_hedging_effectiveness(data, h_ratio, tax_rate=0.13):
    """
    评估套保效果

    简化版本，用于支持全样本回测（备选方案）
    推荐使用滚动回测模式（rolling_backtest.py）

    Parameters:
    -----------
    data : pd.DataFrame
        包含收益率数据
    h_ratio : np.array
        套保比例序列（动态套保）
    tax_rate : float
        税点调整比例

    Returns:
    --------
    metrics : dict
        套保效果指标
    """
    print("\n[全样本回测评估] 注意：推荐使用滚动回测模式")

    # 现货收益率
    r_s = data['r_s'].values
    r_f = data['r_f'].values

    # 对齐长度
    min_len = min(len(r_s), len(h_ratio))
    r_s = r_s[:min_len]
    r_f = r_f[:min_len]
    h_aligned = h_ratio[:min_len]

    # 传统套保（固定 h=1，即现货:期货 = 1:1）
    r_traditional = r_s / (1 + tax_rate) - 1.0 * r_f
    # 动态套保（使用 GARCH 模型的时变套保比例）
    r_hedged = r_s / (1 + tax_rate) - h_aligned * r_f

    # 计算指标
    var_traditional = np.var(r_traditional)
    var_hedged = np.var(r_hedged)
    variance_reduction = 1 - var_hedged / var_traditional

    mean_traditional = np.mean(r_traditional)
    mean_hedged = np.mean(r_hedged)

    std_traditional = np.std(r_traditional)
    std_hedged = np.std(r_hedged)

    sharpe_traditional = mean_traditional / std_traditional if std_traditional > 0 else 0
    sharpe_hedged = mean_hedged / std_hedged if std_hedged > 0 else 0

    # 累计收益率
    cumulative_traditional = np.cumprod(1 + r_traditional)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    max_dd_traditional = calculate_max_drawdown(cumulative_traditional)
    max_dd_hedged = calculate_max_drawdown(cumulative_hedged)

    total_return_traditional = cumulative_traditional[-1] - 1
    total_return_hedged = cumulative_hedged[-1] - 1

    years = len(r_traditional) / 252
    annual_return_traditional = (1 + total_return_traditional) ** (1/years) - 1
    annual_return_hedged = (1 + total_return_hedged) ** (1/years) - 1

    # 计算 VaR 和 CVaR
    var_95_traditional = calculate_var(r_traditional, confidence_level=0.95)
    var_95_hedged = calculate_var(r_hedged, confidence_level=0.95)
    cvar_95_traditional = calculate_cvar(r_traditional, confidence_level=0.95)
    cvar_95_hedged = calculate_cvar(r_hedged, confidence_level=0.95)

    # 套保效果评级
    if variance_reduction > 0.7:
        rating = "优秀 (Excellent)"
    elif variance_reduction > 0.5:
        rating = "良好 (Good)"
    elif variance_reduction > 0.3:
        rating = "一般 (Fair)"
    else:
        rating = "较差 (Poor)"

    metrics = {
        'variance_reduction': variance_reduction,
        'ederington': variance_reduction,
        'var_traditional': var_traditional,
        'var_hedged': var_hedged,
        'std_traditional': std_traditional,
        'std_hedged': std_hedged,
        'mean_traditional': mean_traditional,
        'mean_hedged': mean_hedged,
        'sharpe_traditional': sharpe_traditional,
        'sharpe_hedged': sharpe_hedged,
        'max_dd_traditional': max_dd_traditional,
        'max_dd_hedged': max_dd_hedged,
        'total_return_traditional': total_return_traditional,
        'total_return_hedged': total_return_hedged,
        'annual_return_traditional': annual_return_traditional,
        'annual_return_hedged': annual_return_hedged,
        'var_95_traditional': var_95_traditional,
        'var_95_hedged': var_95_hedged,
        'cvar_95_traditional': cvar_95_traditional,
        'cvar_95_hedged': cvar_95_hedged,
        'rating': rating,
        'cumulative_traditional': cumulative_traditional,
        'cumulative_hedged': cumulative_hedged,
        # 保持向后兼容
        'var_unhedged': var_traditional,
        'std_unhedged': std_traditional,
        'mean_unhedged': mean_traditional,
        'sharpe_unhedged': sharpe_traditional,
        'max_dd_unhedged': max_dd_traditional,
        'total_return_unhedged': total_return_traditional,
        'annual_return_unhedged': annual_return_traditional,
        'var_95_unhedged': var_95_traditional,
        'cvar_95_unhedged': cvar_95_traditional,
        'cumulative_unhedged': cumulative_traditional
    }

    return metrics
