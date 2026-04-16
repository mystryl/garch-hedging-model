# -*- coding: utf-8 -*-
"""
价差套利分析 — 配置参数
"""

from dataclasses import dataclass, field


@dataclass
class SpreadConfig:
    """价差套利分析配置"""

    # ========================
    # 滚动窗口参数
    # ========================
    zscore_window: int = 60          # Z-Score 滚动窗口（交易日）
    corr_window: int = 60            # 滚动相关性窗口
    garch_window: int = 250          # GARCH 拟合用数据长度（不足则用全部）

    # ========================
    # 回测参数
    # ========================
    entry_zscore: float = 2.0        # 入场 Z-Score 阈值
    exit_zscore: float = 0.5         # 出场 Z-Score 阈值（回归到）
    max_holding_days: int = 60       # 最大持仓天数
    enable_dynamic_threshold: bool = True  # 启用 GARCH 动态阈值

    # ========================
    # 滚动回测参数
    # ========================
    enable_rolling_backtest: bool = False
    rolling_periods: int = 6         # 滚动回测周期数
    rolling_window_days: int = 250   # 每周期回测窗口
    min_gap_days: int = 125          # 相邻周期最小间隔
    backtest_seed: int = None        # 随机种子

    # ========================
    # DCC-GARCH 协整稳定性监控
    # ========================
    enable_dcc_stoploss: bool = True  # 启用 DCC 预警止损
    dcc_rho_burnin: int = 20          # burn-in 期（跳过前 N 个时间步）
    dcc_rho_init_window: int = 60     # 初始 ρ 计算窗口
    dcc_roll_window: int = 20         # ρ_t 滚动均值窗口
    dcc_rho_half_ratio: float = 0.5   # 条件 a: 跌破初始 ρ 的此比例
    dcc_streak_days: int = 5          # 条件 a: 持续天数
    dcc_abs_threshold: float = 0.3    # 条件 b: ρ_t 绝对阈值

    # ========================
    # 交易参数
    # ========================
    transaction_cost: float = 0.0    # 交易成本比例

    def __post_init__(self):
        """参数合理性校验"""
        assert self.zscore_window >= 20, "Z-Score 窗口至少 20 个交易日"
        assert self.entry_zscore > self.exit_zscore, "入场阈值必须大于出场阈值"
        assert self.max_holding_days > 0, "最大持仓天数必须为正"
