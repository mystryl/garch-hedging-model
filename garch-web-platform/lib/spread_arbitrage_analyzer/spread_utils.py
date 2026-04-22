"""价差区间计算工具 — 将 Z-Score 阈值转换为实际价差值"""


def calculate_spread_range(spread, config, garch_result=None) -> dict:
    """计算价差区间（将 Z-Score 阈值转换为实际价差值）

    Args:
        spread: pd.Series — 价差序列
        config: SpreadArbitrageConfig — 套利配置（需 zscore_window, entry_zscore, exit_zscore）
        garch_result: dict|None — GARCH 动态阈值结果（含 'upper' Series），用于计算动态因子

    Returns:
        dict — 包含 current_spread, rolling_mean, rolling_std, current_zscore,
               dynamic_factor, long_entry_spread, short_entry_spread,
               close_lower_spread, close_upper_spread, is_dynamic
               或空 dict（数据不足时）
    """
    window = config.zscore_window
    rolling_mean = spread.rolling(window).mean().dropna()
    rolling_std = spread.rolling(window).std().dropna()

    if rolling_mean.empty or rolling_std.empty:
        return {}

    lm = float(rolling_mean.iloc[-1])
    ls = float(rolling_std.iloc[-1])
    lc = float(spread.iloc[-1])
    lz = round((lc - lm) / ls, 4) if ls > 0 else 0.0

    # GARCH 动态因子
    dynamic_factor = 1.0
    is_dynamic = False

    if garch_result and garch_result.get('volatility') is not None:
        upper_series = garch_result.get('upper')
        if upper_series is not None:
            uc = upper_series.dropna()
            if not uc.empty and config.entry_zscore > 0:
                dynamic_factor = round(float(uc.iloc[-1]) / config.entry_zscore, 4)
                is_dynamic = True

    return {
        'current_spread': round(lc, 2),
        'rolling_mean': round(lm, 2),
        'rolling_std': round(ls, 2),
        'current_zscore': lz,
        'dynamic_factor': dynamic_factor,
        'long_entry_spread': round(lm - config.entry_zscore * dynamic_factor * ls, 2),
        'short_entry_spread': round(lm + config.entry_zscore * dynamic_factor * ls, 2),
        'close_lower_spread': round(lm - config.exit_zscore * ls, 2),
        'close_upper_spread': round(lm + config.exit_zscore * ls, 2),
        'is_dynamic': is_dynamic,
    }
