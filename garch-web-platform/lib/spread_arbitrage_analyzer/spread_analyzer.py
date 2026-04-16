# -*- coding: utf-8 -*-
"""
价差套利分析 — 核心分析模块

自动完成所有统计检验，无需用户设置参数：
- ADF 平稳性检验
- Johansen 协整检验
- OU 过程半衰期
- 滚动 Z-Score
- 滚动相关性
- GARCH(1,1) 拟合 → 动态阈值
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .config import SpreadConfig


@dataclass
class SpreadAnalysisResult:
    """分析结果容器"""
    # 基础统计
    spread_stats: dict = field(default_factory=dict)

    # 检验结果
    adf_test: dict = field(default_factory=dict)
    johansen_test: dict = field(default_factory=dict)
    half_life: dict = field(default_factory=dict)
    correlation: dict = field(default_factory=dict)

    # 时序指标
    zscore_series: Optional[pd.Series] = None
    rolling_corr_series: Optional[pd.Series] = None
    garch_volatility: Optional[pd.Series] = None
    dynamic_threshold_upper: Optional[pd.Series] = None
    dynamic_threshold_lower: Optional[pd.Series] = None

    # DCC 协整稳定性监控
    dcc_corr_series: Optional[pd.Series] = None       # 条件相关系数时序
    dcc_vol_a: Optional[pd.Series] = None             # 标的A条件波动率
    dcc_vol_b: Optional[pd.Series] = None             # 标的B条件波动率
    cointegration_break: dict = field(default_factory=dict)  # 瓦解预警统计
    coint_break_signals: Optional[pd.Series] = None   # 预警信号（日频bool）
    dcc_analysis_failed: bool = False                 # DCC 分析是否失败

    # 综合判断
    is_mean_reverting: bool = False
    is_cointegrated: bool = False
    tradeable: bool = False
    summary: str = ""


class SpreadAnalyzer:
    """价差分析器"""

    def __init__(self, config: SpreadConfig = None):
        self.config = config or SpreadConfig()

    def analyze(
        self,
        df: pd.DataFrame,
        price_a: str = 'price_a',
        price_b: str = 'price_b',
        spread_col: str = 'spread',
    ) -> SpreadAnalysisResult:
        """
        执行完整的价差分析

        Parameters
        ----------
        df : pd.DataFrame
            包含 date, price_a, price_b, spread 列
        price_a, price_b : str
            价格列名
        spread_col : str
            价差列名

        Returns
        -------
        SpreadAnalysisResult
        """
        result = SpreadAnalysisResult()

        # 1. 基础统计
        result.spread_stats = self._compute_spread_stats(df, spread_col)

        # 2. ADF 平稳性检验
        result.adf_test = self._adf_test(df[spread_col].values)

        # 3. Johansen 协整检验
        result.johansen_test = self._johansen_test(
            df[price_a].values, df[price_b].values
        )

        # 4. OU 过程半衰期
        result.half_life = self._estimate_half_life(df[spread_col].values)

        # 5. 滚动相关性
        result.correlation, result.rolling_corr_series = self._rolling_correlation(
            df[price_a], df[price_b]
        )

        # 6. 滚动 Z-Score
        result.zscore_series = self._rolling_zscore(df[spread_col])

        # 7. GARCH(1,1) 动态阈值
        if self.config.enable_dynamic_threshold:
            garch_result = self._garch_dynamic_threshold(df[spread_col])
            result.garch_volatility = garch_result['volatility']
            result.dynamic_threshold_upper = garch_result['upper']
            result.dynamic_threshold_lower = garch_result['lower']
            # 重索引到完整 spread 的 index（GARCH 的 series 比 spread 短，因为 pct_change 丢失首行）
            if result.dynamic_threshold_upper is not None:
                result.dynamic_threshold_upper = result.dynamic_threshold_upper.reindex(
                    df.index, method='ffill'
                )
            if result.dynamic_threshold_lower is not None:
                result.dynamic_threshold_lower = result.dynamic_threshold_lower.reindex(
                    df.index, method='ffill'
                )

        # 8. DCC-GARCH 协整稳定性监控
        if self.config.enable_dcc_stoploss:
            dcc_result = self._dcc_cointegration_monitor(df, price_a, price_b)
            result.dcc_corr_series = dcc_result['corr_series']
            result.dcc_vol_a = dcc_result['vol_a']
            result.dcc_vol_b = dcc_result['vol_b']
            result.cointegration_break = dcc_result['break_stats']
            result.coint_break_signals = dcc_result['break_signals']
            # 标记 DCC 分析是否成功（有 corr_series 但无 break_stats 说明分析失败）
            result.dcc_analysis_failed = (
                dcc_result['corr_series'] is None
                and not dcc_result['break_stats']
            )

        # 9. 综合判断
        result.is_mean_reverting = result.adf_test['p_value'] < 0.05
        result.is_cointegrated = result.johansen_test['cointegrated']
        result.tradeable = (
            result.is_mean_reverting
            and result.is_cointegrated
            and result.half_life['interpretable']
            and 5 <= result.half_life['halflife_days'] < self.config.max_holding_days
        )
        result.summary = self._generate_summary(result)

        return result

    # ========================
    # 各项检验实现
    # ========================

    @staticmethod
    def _compute_spread_stats(df: pd.DataFrame, spread_col: str) -> dict:
        """价差描述统计"""
        s = df[spread_col]
        return {
            'mean': float(s.mean()),
            'std': float(s.std()),
            'min': float(s.min()),
            'max': float(s.max()),
            'median': float(s.median()),
            'skewness': float(s.skew()),
            'kurtosis': float(s.kurtosis()),
            'n_observations': len(s),
            'acf_lag1': float(s.autocorr(lag=1)),
        }

    @staticmethod
    def _adf_test(spread: np.ndarray) -> dict:
        """
        ADF 平稳性检验

        使用 arch.unitroot.ADF（避免 statsmodels 版本兼容问题）
        """
        from arch.unitroot import ADF

        spread_clean = spread[~np.isnan(spread)]

        adf = ADF(spread_clean)
        return {
            'statistic': float(adf.stat),
            'p_value': float(adf.pvalue),
            'used_lag': int(adf.lags),
            'nobs': int(adf.nobs),
            'stationary': bool(adf.pvalue < 0.05),
            'critical_values': {
                '1%': float(adf.critical_values.get('1%', 0)),
                '5%': float(adf.critical_values.get('5%', 0)),
                '10%': float(adf.critical_values.get('10%', 0)),
            },
        }

    @staticmethod
    def _johansen_test(price_a: np.ndarray, price_b: np.ndarray) -> dict:
        """
        Johansen 协整检验

        检验两个序列是否存在长期均衡关系。
        """
        from statsmodels.tsa.vector_ar.vecm import coint_johansen

        # 清洗数据
        mask = ~(np.isnan(price_a) | np.isnan(price_b))
        data = np.column_stack([price_a[mask], price_b[mask]])

        # det_order=0: 无确定性趋势, k_ar_diff=1: 差分滞后阶数
        johansen = coint_johansen(data, det_order=0, k_ar_diff=1)

        # 迹统计量检验
        lr1 = johansen.lr1          # 迹统计量
        cvt = johansen.cvt          # 临界值表 (90%, 95%, 99%)
        # cvm = johansen.cvm         # 最大特征值临界值

        r0_reject = lr1[0] > cvt[0, 1]  # r=0 在5%水平拒绝 → 至少1个协整关系
        r1_reject = lr1[1] > cvt[1, 1]  # r<=1 在5%水平拒绝 → 2个协整关系

        return {
            'trace_stat_r0': float(lr1[0]),
            'trace_stat_r1': float(lr1[1]),
            'critical_5pct_r0': float(cvt[0, 1]),
            'critical_5pct_r1': float(cvt[1, 1]),
            'cointegrated': bool(r0_reject),
            'n_coint_relations': 2 if r1_reject else (1 if r0_reject else 0),
            'eigenvectors': johansen.evec.tolist() if hasattr(johansen, 'evec') else None,
        }

    @staticmethod
    def _estimate_half_life(spread: np.ndarray) -> dict:
        """
        OU 过程半衰期估计

        通过 OLS 回归估计: ΔS(t) = θ(μ - S(t-1)) + ε
        半衰期 = -ln(2) / ln(1 + β1)
        """
        spread_clean = spread[~np.isnan(spread)]
        y = spread_clean
        ylag = y[:-1]
        ydiff = y[1:] - ylag

        X = np.column_stack([np.ones(len(ylag)), ylag])
        # 最小二乘
        beta, residuals, rank, sv = np.linalg.lstsq(X, ydiff, rcond=None)

        beta0, beta1 = beta[0], beta[1]

        if beta1 >= 0:
            halflife = float('inf')
        elif 1 + beta1 <= 0:
            halflife = float('inf')
        else:
            halflife = -np.log(2) / np.log(1 + beta1)

        # 计算 R²
        ss_res = np.sum((ydiff - X @ beta) ** 2)
        ss_tot = np.sum((ydiff - np.mean(ydiff)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        return {
            'halflife_days': round(halflife, 1),
            'beta0': float(beta0),
            'beta1': float(beta1),
            'r_squared': float(r_squared),
            'mean_reverting': beta1 < 0,
            'interpretable': 0 < halflife < 500,
        }

    def _rolling_correlation(
        self, price_a: pd.Series, price_b: pd.Series
    ) -> tuple:
        """滚动 Pearson 相关系数"""
        window = self.config.corr_window
        rolling_corr = price_a.rolling(window).corr(price_b)

        return {
            'window': window,
            'current': float(rolling_corr.iloc[-1]) if not rolling_corr.isna().all() else None,
            'mean': float(rolling_corr.mean()),
            'min': float(rolling_corr.min()),
            'max': float(rolling_corr.max()),
            'full_sample': float(price_a.corr(price_b)),
        }, rolling_corr

    def _rolling_zscore(self, spread: pd.Series) -> pd.Series:
        """滚动 Z-Score"""
        window = self.config.zscore_window
        rolling_mean = spread.rolling(window).mean()
        rolling_std = spread.rolling(window).std()
        zscore = (spread - rolling_mean) / rolling_std
        return zscore

    def _garch_dynamic_threshold(
        self, spread: pd.Series
    ) -> dict:
        """
        GARCH(1,1) 拟合价差序列，生成动态入场/出场阈值

        思路：
        1. 用全部数据拟合 GARCH(1,1)，得到条件方差
        2. 条件标准差 = √条件方差，作为时变波动率
        3. 动态入场阈值 = entry_zscore × 条件标准差
        4. 动态出场阈值 = exit_zscore × 条件标准差
        """
        from arch import arch_model

        spread_clean = spread.dropna()
        # 价差可能过零点，pct_change 产生 inf；需清洗
        raw_ret = spread_clean.pct_change()
        raw_ret = raw_ret.replace([np.inf, -np.inf], np.nan).dropna()
        returns = raw_ret * 100  # 百分比收益率

        if len(returns) < 100:
            print("  [GARCH] 数据不足100条，跳过 GARCH 拟合")
            return {
                'volatility': None,
                'upper': None,
                'lower': None,
                'model_fitted': False,
            }

        try:
            # 拟合 GARCH(1,1)
            am = arch_model(returns, vol='Garch', p=1, q=1, dist='normal',
                          mean='Constant', rescale=False)
            res = am.fit(disp='off', show_warning=False)

            # 获取条件波动率（百分比）
            cond_vol = res.conditional_volatility / 100  # 转回小数

            # 对齐到原始 spread 的索引
            # cond_vol 比 spread 少2行（pct_change + dropna）
            vol_series = pd.Series(
                index=returns.index,
                data=cond_vol.values,
                name='garch_volatility'
            )

            # 动态阈值 = 固定阈值 × (条件波动率 / 全样本波动率)
            # 使阈值保持无量纲，与 Z-Score 直接可比
            # 注意: vol_series 已转回小数 (/100)，returns.std() 也需 /100 保持单位一致
            full_sample_std = returns.std() / 100
            if full_sample_std > 0:
                dynamic_factor = vol_series / full_sample_std
            else:
                dynamic_factor = pd.Series(1.0, index=vol_series.index)

            upper = self.config.entry_zscore * dynamic_factor
            lower = self.config.exit_zscore * dynamic_factor

            return {
                'volatility': vol_series,
                'upper': upper,
                'lower': lower,
                'model_fitted': True,
                'params': {
                    'omega': float(res.params.get('omega', 0)),
                    'alpha': float(res.params.get('alpha[1]', 0)),
                    'beta': float(res.params.get('beta[1]', 0)),
                },
            }
        except Exception as e:
            print(f"  [GARCH] 拟合失败: {e}")
            return {
                'volatility': None,
                'upper': None,
                'lower': None,
                'model_fitted': False,
                'error': str(e),
            }

    # ========================
    # 综合判断
    # ========================

    def _dcc_cointegration_monitor(
        self, df: pd.DataFrame, price_a: str, price_b: str
    ) -> Dict[str, Any]:
        """
        DCC-GARCH 协整稳定性监控

        使用动态条件相关系数 ρ_t 的持续下降作为协整关系瓦解的预警信号。
        """
        import warnings
        warnings.filterwarnings('ignore')

        empty_result = {
            'corr_series': None,
            'vol_a': None,
            'vol_b': None,
            'break_stats': {},
            'break_signals': None,
        }

        pa = df[price_a]
        pb = df[price_b]

        # 数据不足 150 条时跳过
        if len(pa) < 150:
            print("  [DCC] 数据不足150条，跳过 DCC 分析")
            return empty_result

        # 计算收益率
        ret_a = pa.pct_change()
        ret_b = pb.pct_change()
        ret_a = ret_a.replace([np.inf, -np.inf], np.nan).dropna()
        ret_b = ret_b.replace([np.inf, -np.inf], np.nan).dropna()

        # 对齐
        common_idx = ret_a.index.intersection(ret_b.index)
        ret_a = ret_a.loc[common_idx]
        ret_b = ret_b.loc[common_idx]

        # 清洗 NaN / inf
        valid = ~(ret_a.isna() | ret_b.isna() | np.isinf(ret_a) | np.isinf(ret_b))
        ret_a = ret_a[valid]
        ret_b = ret_b[valid]

        if len(ret_a) < 150:
            print("  [DCC] 清洗后数据不足150条，跳过 DCC 分析")
            return empty_result

        try:
            import mgarch
            from lib.model_dcc_garch import get_conditional_covariance

            returns_matrix = np.column_stack([ret_a.values, ret_b.values])
            dcc_model = mgarch.mgarch(dist='norm')
            dcc_model.fit(returns_matrix)
            print("  [DCC] DCC-GARCH 模型拟合成功")

            # 提取条件协方差矩阵
            H_t = get_conditional_covariance(dcc_model)

            var_a = H_t[:, 0, 0]
            var_b = H_t[:, 1, 1]
            cov_ab = H_t[:, 0, 1]

            # 计算条件相关系数
            rho_t = cov_ab / np.sqrt(var_a * var_b)
            rho_t = np.clip(rho_t, -1, 1)

            # 条件波动率
            vol_a = np.sqrt(var_a)
            vol_b = np.sqrt(var_b)

            # 对齐到 df.index
            rho_series = pd.Series(rho_t, index=ret_a.index)
            rho_series = rho_series.reindex(df.index, method='ffill')

            vol_a_series = pd.Series(vol_a, index=ret_a.index)
            vol_a_series = vol_a_series.reindex(df.index, method='ffill')

            vol_b_series = pd.Series(vol_b, index=ret_a.index)
            vol_b_series = vol_b_series.reindex(df.index, method='ffill')

            # --- 预警逻辑 ---
            # 跳过 burn-in 期，使用稳定区域计算初始 ρ
            rho_clean = rho_series.dropna()
            burnin = self.config.dcc_rho_burnin
            init_window = self.config.dcc_rho_init_window
            if len(rho_clean) < burnin + init_window:
                print(f"  [DCC] ρ_t 有效数据不足{burnin + init_window}条，跳过预警计算")
                return {
                    'corr_series': rho_series,
                    'vol_a': vol_a_series,
                    'vol_b': vol_b_series,
                    'break_stats': {},
                    'break_signals': pd.Series(False, index=df.index),
                }

            initial_rho = float(rho_clean.iloc[burnin:burnin + init_window].mean())
            current_rho = float(rho_clean.iloc[-1])
            min_rho = float(rho_clean.min())

            # 滚动均值
            roll_win = self.config.dcc_roll_window
            rho_roll = rho_clean.rolling(roll_win).mean()

            # 预警信号
            break_signal = pd.Series(False, index=rho_clean.index)

            # 条件 a: 滚动均值 < 初始 ρ 的 dcc_rho_half_ratio，且持续 >= dcc_streak_days 天
            half_ratio = self.config.dcc_rho_half_ratio
            streak_days = self.config.dcc_streak_days
            below_half = rho_roll < (initial_rho * half_ratio)
            # 计算连续天数
            streak = below_half.astype(int).groupby(
                (~below_half).cumsum()
            ).cumsum()
            cond_a = below_half & (streak >= streak_days)

            # 条件 b: ρ_t 跌破 dcc_abs_threshold
            abs_threshold = self.config.dcc_abs_threshold
            cond_b = rho_clean < abs_threshold

            break_signal = cond_a | cond_b

            # 对齐到 df.index
            break_signal = break_signal.reindex(df.index, fill_value=False)

            # 统计
            warn_count = int((break_signal.diff() == 1).sum())  # 从 False→True 的次数
            warn_days = int(break_signal.sum())

            break_stats = {
                'initial_rho': round(initial_rho, 4),
                'current_rho': round(current_rho, 4),
                'min_rho': round(min_rho, 4),
                'warn_count': warn_count,
                'warn_days': warn_days,
            }

            print(f"  [DCC] ρ_t 统计: 初始={initial_rho:.4f}, "
                  f"当前={current_rho:.4f}, 最低={min_rho:.4f}, "
                  f"预警次数={warn_count}, 预警天数={warn_days}")

            return {
                'corr_series': rho_series,
                'vol_a': vol_a_series,
                'vol_b': vol_b_series,
                'break_stats': break_stats,
                'break_signals': break_signal,
            }

        except Exception as e:
            print(f"  [DCC] DCC 分析失败: {e}")
            return empty_result

    @staticmethod
    def _generate_summary(result: SpreadAnalysisResult) -> str:
        """生成分析摘要"""
        lines = []

        # ADF
        adf = result.adf_test
        lines.append(
            f"ADF检验: 统计量={adf['statistic']:.4f}, "
            f"p值={adf['p_value']:.4f} → "
            f"{'✅ 平稳（均值回归）' if adf['stationary'] else '❌ 非平稳'}"
        )

        # Johansen
        jt = result.johansen_test
        lines.append(
            f"Johansen协整: 迹统计量={jt['trace_stat_r0']:.2f}, "
            f"临界值(5%)={jt['critical_5pct_r0']:.2f} → "
            f"{'✅ 存在协整关系' if jt['cointegrated'] else '❌ 无协整关系'}"
        )

        # 半衰期
        hl = result.half_life
        hl_str = f"{hl['halflife_days']:.1f}天" if hl['interpretable'] else "不可估计"
        lines.append(
            f"半衰期: {hl_str} → "
            f"{'✅ 合理回归速度' if hl['interpretable'] and 0 < hl['halflife_days'] < 60 else '⚠️ 回归较慢' if hl['interpretable'] else '❌'}"
        )

        # 综合判断
        if result.tradeable:
            lines.append("📊 综合判断: ✅ 价差具备套利条件")
        elif result.is_mean_reverting and result.is_cointegrated:
            lines.append("📊 综合判断: ⚠️ 价差均值回归但半衰期较长，需谨慎")
        else:
            lines.append("📊 综合判断: ❌ 价差不具备套利条件")

        return '\n'.join(lines)
