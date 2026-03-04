"""
共享的滚动回测核心逻辑
从 Basic GARCH 的 rolling_backtest.py 抽取通用逻辑
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

# 交割月常量
DELIVERY_MONTHS = [1, 5, 10]  # 1月、5月、10月为交割月份


def is_delivery_month(date: pd.Timestamp) -> bool:
    """
    判断是否为交割月份（1、5、10月）

    Parameters:
    -----------
    date : pd.Timestamp
        日期

    Returns:
    --------
    bool : 是否为交割月
    """
    return date.month in DELIVERY_MONTHS


def is_near_delivery_month(date: pd.Timestamp, window_days: int = 30) -> bool:
    """
    判断是否临近交割月份（交割月前后window_days天内）

    Parameters:
    -----------
    date : pd.Timestamp
        日期
    window_days : int
        预警窗口天数（默认30天）

    Returns:
    --------
    bool : 是否临近交割月
    """
    # 只检查是否在交割月本身
    if date.month in DELIVERY_MONTHS:
        return True

    # 检查是否在交割月前 window_days 天内
    for dm in DELIVERY_MONTHS:
        if dm > date.month:
            # 计算到下一个交割月的天数
            next_delivery = pd.Timestamp(f'{date.year}-{dm:02d}-01')
            days_diff = (next_delivery - date).days
            if 0 <= days_diff <= window_days:
                return True

    return False


def select_backtest_start_dates(data: pd.DataFrame, n_periods: int = 5,
                                 min_gap_days: int = 180,
                                 window_days: int = 60,
                                 seed: Optional[int] = None) -> List[pd.Timestamp]:
    """
    随机选择回测起始日期

    规则：
    1. 避开1、5、10交割月份及其前后90天
    2. 每个起始日期间隔至少 min_gap_days
    3. 确保有足够的后续数据（至少window_days）

    Parameters:
    -----------
    data : pd.DataFrame
        数据（包含 date 列）
    n_periods : int
        选择的时间点数量
    min_gap_days : int
        起始日期之间的最小间隔天数
    window_days : int
        回测窗口天数
    seed : int, optional
        随机种子（用于复现）

    Returns:
    --------
    selected_dates : List[pd.Timestamp]
        选中的起始日期列表
    """
    if seed is not None:
        np.random.seed(seed)

    # 获取所有可能的起始日期（使用 .copy() 避免修改原始数据）
    data_copy = data.copy()
    data_copy['month'] = data_copy['date'].dt.month
    data_copy['year'] = data_copy['date'].dt.year

    # 过滤掉临近交割月的日期
    valid_mask = ~data_copy['date'].apply(is_near_delivery_month)
    valid_data = data_copy[valid_mask].copy()

    # 确保有足够的后续数据
    max_start_idx = len(valid_data) - window_days
    valid_data = valid_data.iloc[:max_start_idx].reset_index(drop=True)

    print(f"\n[回测起始日期选择]")
    print(f"  总数据量: {len(data)}")
    print(f"  有效起始点（避开交割月）: {len(valid_data)}")

    # 随机选择起始日期
    selected_dates = []
    attempts = 0
    max_attempts = 1000

    while len(selected_dates) < n_periods and attempts < max_attempts:
        attempts += 1

        # 随机选择一个候选日期
        idx = np.random.randint(0, len(valid_data))
        candidate = valid_data.loc[idx, 'date']

        # 检查与已选日期的距离
        valid = True
        for selected in selected_dates:
            if abs((candidate - selected).days) < min_gap_days:
                valid = False
                break

        if valid:
            selected_dates.append(candidate)
            print(f"  选择起始点 #{len(selected_dates)}: {candidate.date()} "
                  f"(月份={candidate.month})")

    if len(selected_dates) < n_periods:
        print(f"  ⚠️  警告: 仅找到 {len(selected_dates)} 个有效起始点")

    return sorted(selected_dates)


def run_single_period_backtest(data: pd.DataFrame, start_date: pd.Timestamp,
                               hedge_ratios: np.ndarray,
                               window_days: int = 60,
                               tax_rate: float = 0.13) -> Dict:
    """
    运行单个周期的回测

    Parameters:
    -----------
    data : pd.DataFrame
        完整数据
    start_date : pd.Timestamp
        回测起始日期
    hedge_ratios : np.ndarray
        套保比例序列
    window_days : int
        回测窗口天数
    tax_rate : float
        增值税率（现货收益需要考虑增值税）

    Returns:
    --------
    result : Dict
        回测结果
    """
    # 找到起始日期在数据中的索引
    matching_rows = data[data['date'] == start_date]
    if len(matching_rows) == 0:
        raise ValueError(f"起始日期 {start_date} 不存在于数据中")
    start_idx = matching_rows.index[0]

    # 提取回测窗口数据
    end_idx = min(start_idx + window_days, len(data))
    period_data = data.iloc[start_idx:end_idx].copy().reset_index(drop=True)

    # 对应的套保比例
    period_h = hedge_ratios[start_idx:end_idx]

    # 计算套保后收益率（考虑税点）
    # 现货收益需要除以(1+税率)，因为现货盈利需要缴纳增值税
    r_s = period_data['r_s'].values
    r_f = period_data['r_f'].values

    # 套保收益 = 现货收益/(1+税率) - 套保比例 * 期货收益
    r_hedged = r_s / (1 + tax_rate) - period_h * r_f
    r_unhedged = r_s

    # 计算累计收益率
    cumulative_unhedged = np.cumprod(1 + r_unhedged)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    # 计算回撤
    running_max = np.maximum.accumulate(cumulative_hedged)
    drawdown = (cumulative_hedged - running_max) / running_max

    # 计算指标
    total_return_unhedged = cumulative_unhedged[-1] - 1
    total_return_hedged = cumulative_hedged[-1] - 1

    annual_return_unhedged = cumulative_unhedged[-1] ** (252 / len(period_data)) - 1
    annual_return_hedged = cumulative_hedged[-1] ** (252 / len(period_data)) - 1

    std_unhedged = np.std(r_unhedged)
    std_hedged = np.std(r_hedged)

    # 计算最大回撤（复用已计算的 cumulative_unhedged）
    max_dd_unhedged = np.min(cumulative_unhedged / np.maximum.accumulate(cumulative_unhedged) - 1)
    max_dd_hedged = np.min(drawdown)

    sharpe_unhedged = np.mean(r_unhedged) / np.std(r_unhedged) if np.std(r_unhedged) > 0 else 0
    sharpe_hedged = np.mean(r_hedged) / np.std(r_hedged) if np.std(r_hedged) > 0 else 0

    # 方差降低
    variance_reduction = 1 - (std_hedged ** 2) / (std_unhedged ** 2)

    # 计算该周期使用的平均套保比例
    avg_hedge_ratio = np.mean(period_h)
    median_hedge_ratio = np.median(period_h)
    std_hedge_ratio = np.std(period_h)

    return {
        'start_date': start_date,
        'end_date': period_data.iloc[-1]['date'],
        'period_days': len(period_data),
        'total_return_unhedged': total_return_unhedged,
        'total_return_hedged': total_return_hedged,
        'annual_return_unhedged': annual_return_unhedged,
        'annual_return_hedged': annual_return_hedged,
        'std_unhedged': std_unhedged,
        'std_hedged': std_hedged,
        'max_dd_unhedged': max_dd_unhedged,
        'max_dd_hedged': max_dd_hedged,
        'sharpe_unhedged': sharpe_unhedged,
        'sharpe_hedged': sharpe_hedged,
        'variance_reduction': variance_reduction,
        'cumulative_unhedged': cumulative_unhedged,
        'cumulative_hedged': cumulative_hedged,
        'drawdown': drawdown,
        'dates': period_data['date'].values,
        'avg_hedge_ratio': avg_hedge_ratio,
        'median_hedge_ratio': median_hedge_ratio,
        'std_hedge_ratio': std_hedge_ratio,
        'hedge_ratios': period_h
    }


def run_rolling_backtest(data: pd.DataFrame, hedge_ratios: np.ndarray,
                         n_periods: int = 5, window_days: int = 60,
                         min_gap_days: int = 180,
                         seed: Optional[int] = None,
                         tax_rate: float = 0.13) -> Dict:
    """
    运行完整滚动回测

    Parameters:
    -----------
    data : pd.DataFrame
        数据
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

    Returns:
    --------
    results : Dict
        回测结果汇总
        {
            'period_results': [...],
            'n_periods': int,
            'window_days': int,
            'avg_return_unhedged': float,
            'avg_return_hedged': float,
            'avg_variance_reduction': float,
            'avg_max_dd_hedged': float
        }
    """
    print("\n" + "=" * 60)
    print("滚动回测分析")
    print("=" * 60)
    print(f"回测周期数: {n_periods}")
    print(f"每个周期: {window_days} 天")
    print(f"避开交割月: 1月、5月、10月")

    # 选择起始日期
    start_dates = select_backtest_start_dates(
        data, n_periods=n_periods, window_days=window_days,
        min_gap_days=min_gap_days, seed=seed
    )

    if len(start_dates) == 0:
        raise ValueError("无法找到有效的回测起始日期")

    # 运行每个周期的回测
    print(f"\n{'='*60}")
    print(f"开始回测 {len(start_dates)} 个周期...")
    print(f"{'='*60}")

    period_results = []

    for i, start_date in enumerate(start_dates, 1):
        print(f"\n[周期 {i}/{len(start_dates)}]")
        print(f"  起始日期: {start_date.date()}")

        result = run_single_period_backtest(
            data, start_date, hedge_ratios, window_days, tax_rate
        )

        period_results.append(result)

        print(f"  结束日期: {result['end_date'].date()}")
        print(f"  实际天数: {result['period_days']}")
        print(f"  未套保收益率: {result['total_return_unhedged']:.2%}")
        print(f"  套保收益率: {result['total_return_hedged']:.2%}")
        print(f"  方差降低: {result['variance_reduction']:.2%}")

    # 汇总统计
    print(f"\n{'='*60}")
    print("回测汇总")
    print(f"{'='*60}")

    avg_return_unhedged = np.mean([r['total_return_unhedged'] for r in period_results])
    avg_return_hedged = np.mean([r['total_return_hedged'] for r in period_results])
    avg_variance_reduction = np.mean([r['variance_reduction'] for r in period_results])
    avg_max_dd_hedged = np.mean([r['max_dd_hedged'] for r in period_results])

    print(f"平均收益率（未套保）: {avg_return_unhedged:.2%}")
    print(f"平均收益率（套保后）: {avg_return_hedged:.2%}")
    print(f"平均方差降低: {avg_variance_reduction:.2%}")
    print(f"平均最大回撤（套保后）: {avg_max_dd_hedged:.2%}")

    return {
        'period_results': period_results,
        'n_periods': len(period_results),
        'window_days': window_days,
        'avg_return_unhedged': avg_return_unhedged,
        'avg_return_hedged': avg_return_hedged,
        'avg_variance_reduction': avg_variance_reduction,
        'avg_max_dd_hedged': avg_max_dd_hedged
    }
