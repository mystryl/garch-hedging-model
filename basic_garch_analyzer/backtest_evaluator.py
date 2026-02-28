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
        套保比例序列
    tax_rate : float
        税点调整比例
    
    Returns:
    --------
    metrics : dict
        套保效果指标
    """
    print("\n[全样本回测评估] 注意：推荐使用滚动回测模式")
    
    # 未套保组合收益率
    r_unhedged = data['r_s'].values
    
    # 对齐长度
    min_len = min(len(r_unhedged), len(h_ratio))
    r_unhedged = r_unhedged[:min_len]
    r_f_aligned = data['r_f'].values[:min_len]
    h_aligned = h_ratio[:min_len]
    
    # 套保组合收益率
    r_hedged = r_unhedged - h_aligned * r_f_aligned
    
    # 计算指标
    var_unhedged = np.var(r_unhedged)
    var_hedged = np.var(r_hedged)
    variance_reduction = 1 - var_hedged / var_unhedged
    
    mean_unhedged = np.mean(r_unhedged)
    mean_hedged = np.mean(r_hedged)
    
    std_unhedged = np.std(r_unhedged)
    std_hedged = np.std(r_hedged)
    
    sharpe_unhedged = mean_unhedged / std_unhedged if std_unhedged > 0 else 0
    sharpe_hedged = mean_hedged / std_hedged if std_hedged > 0 else 0
    
    # 累计收益率
    cumulative_unhedged = np.cumprod(1 + r_unhedged)
    cumulative_hedged = np.cumprod(1 + r_hedged)
    
    max_dd_unhedged = calculate_max_drawdown(cumulative_unhedged)
    max_dd_hedged = calculate_max_drawdown(cumulative_hedged)
    
    total_return_unhedged = cumulative_unhedged[-1] - 1
    total_return_hedged = cumulative_hedged[-1] - 1
    
    years = len(r_unhedged) / 252
    annual_return_unhedged = (1 + total_return_unhedged) ** (1/years) - 1
    annual_return_hedged = (1 + total_return_hedged) ** (1/years) - 1
    
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
        'var_unhedged': var_unhedged,
        'var_hedged': var_hedged,
        'std_unhedged': std_unhedged,
        'std_hedged': std_hedged,
        'mean_unhedged': mean_unhedged,
        'mean_hedged': mean_hedged,
        'sharpe_unhedged': sharpe_unhedged,
        'sharpe_hedged': sharpe_hedged,
        'max_dd_unhedged': max_dd_unhedged,
        'max_dd_hedged': max_dd_hedged,
        'total_return_unhedged': total_return_unhedged,
        'total_return_hedged': total_return_hedged,
        'annual_return_unhedged': annual_return_unhedged,
        'annual_return_hedged': annual_return_hedged,
        'rating': rating,
        'cumulative_unhedged': cumulative_unhedged,
        'cumulative_hedged': cumulative_hedged
    }
    
    return metrics
