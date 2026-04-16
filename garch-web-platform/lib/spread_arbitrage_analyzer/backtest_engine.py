# -*- coding: utf-8 -*-
"""
价差套利分析 — 回测引擎

信号逻辑：
- Z-Score > 入场阈值 → 做空价差（卖A买B）
- Z-Score < -入场阈值 → 做多价差（买A卖B）
- |Z-Score| < 出场阈值 → 平仓
- 持仓超过 max_holding_days → 强制平仓
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .config import SpreadConfig
from .spread_analyzer import SpreadAnalysisResult


@dataclass
class BacktestMetrics:
    """回测绩效指标"""
    total_return: float = 0.0          # 累计收益率
    annual_return: float = 0.0         # 年化收益率
    sharpe_ratio: float = 0.0          # 夏普比率（年化）
    max_drawdown: float = 0.0          # 最大回撤
    calmar_ratio: float = 0.0          # Calmar 比率
    win_rate: float = 0.0              # 胜率
    profit_loss_ratio: float = 0.0     # 盈亏比
    total_trades: int = 0              # 总交易次数
    long_trades: int = 0               # 做多次数
    short_trades: int = 0              # 做空次数
    avg_holding_days: float = 0.0      # 平均持仓天数
    max_holding_days_actual: int = 0   # 实际最大持仓天数
    daily_returns_std: float = 0.0     # 日收益率标准差
    var_95: float = 0.0                # 95% VaR
    cvar_95: float = 0.0               # 95% CVaR


@dataclass
class BacktestResult:
    """回测结果"""
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    equity_curve: Optional[pd.DataFrame] = None  # date, equity, drawdown
    trades: Optional[pd.DataFrame] = None        # 交易记录
    daily_pnl: Optional[pd.Series] = None        # 每日盈亏


class SpreadBacktestEngine:
    """价差回测引擎"""

    def __init__(self, config: SpreadConfig = None):
        self.config = config or SpreadConfig()

    def run_backtest(
        self,
        df: pd.DataFrame,
        analysis: SpreadAnalysisResult,
    ) -> BacktestResult:
        """
        运行单次回测

        Parameters
        ----------
        df : pd.DataFrame
            包含 date, price_a, price_b, spread 列
        analysis : SpreadAnalysisResult
            分析结果（包含 zscore_series）

        Returns
        -------
        BacktestResult
        """
        zscore = analysis.zscore_series
        if zscore is None:
            raise ValueError("分析结果中缺少 zscore_series")

        spread = df['spread']

        # 确定使用动态阈值还是固定阈值
        if (analysis.dynamic_threshold_upper is not None
                and analysis.dynamic_threshold_lower is not None):
            entry_upper = analysis.dynamic_threshold_upper
            entry_lower = -analysis.dynamic_threshold_upper
            exit_band = analysis.dynamic_threshold_lower
            print("  [回测] 使用 GARCH 动态阈值")
        else:
            entry_upper = pd.Series(
                self.config.entry_zscore, index=df.index
            )
            entry_lower = pd.Series(
                -self.config.entry_zscore, index=df.index
            )
            exit_band = pd.Series(
                self.config.exit_zscore, index=df.index
            )
            print("  [回测] 使用固定 Z-Score 阈值")

        # 生成信号
        dcc_break = analysis.coint_break_signals if self.config.enable_dcc_stoploss else None
        positions, exit_reasons = self._generate_signals(zscore, entry_upper, entry_lower, exit_band,
                                                         dcc_break_signals=dcc_break)

        # 计算盈亏
        equity, trades, daily_pnl = self._simulate_trades(
            df, spread, positions, exit_reasons=exit_reasons
        )

        # 计算指标
        metrics = self._compute_metrics(equity, trades, daily_pnl)

        result = BacktestResult(
            metrics=metrics,
            equity_curve=equity,
            trades=trades,
            daily_pnl=daily_pnl,
        )

        self._print_summary(metrics)
        return result

    def run_rolling_backtest(
        self,
        df: pd.DataFrame,
        analysis_fn=None,
    ) -> Dict[str, Any]:
        """
        滚动多周期回测

        Parameters
        ----------
        df : pd.DataFrame
            全量数据
        analysis_fn : callable
            分析函数，接收 (df_slice) 返回 SpreadAnalysisResult

        Returns
        -------
        dict
            滚动回测汇总结果
        """
        if analysis_fn is None:
            from .spread_analyzer import SpreadAnalyzer
            analyzer = SpreadAnalyzer(self.config)
            analysis_fn = lambda d: analyzer.analyze(d)

        total_rows = len(df)
        window = self.config.rolling_window_days
        periods = self.config.rolling_periods
        min_gap = self.config.min_gap_days

        # 计算每个周期的起始日
        if total_rows < window:
            print(f"  [滚动回测] 数据量({total_rows})不足窗口({window})，跳过")
            return {'periods': [], 'summary': '数据不足'}

        available = total_rows - window
        if available < min_gap:
            step = available
        else:
            step = max((available - min_gap) // max(periods - 1, 1), min_gap)

        start_dates = []
        for i in range(periods):
            idx = i * step
            if idx + window > total_rows:
                break
            start_dates.append(idx)

        print(f"  [滚动回测] 共 {len(start_dates)} 个周期")

        results = []
        for i, start_idx in enumerate(start_dates):
            end_idx = start_idx + window
            df_slice = df.iloc[start_idx:end_idx].copy()
            df_slice = df_slice.reset_index(drop=True)

            start_date = df.iloc[start_idx]['date'] if 'date' in df.columns else f"Day{start_idx}"
            end_date = df.iloc[end_idx - 1]['date'] if 'date' in df.columns else f"Day{end_idx-1}"

            print(f"\n  === 周期 {i+1}/{len(start_dates)}: {start_date} ~ {end_date} ===")

            try:
                analysis = analysis_fn(df_slice)
                bt_result = self.run_backtest(df_slice, analysis)

                results.append({
                    'period': i + 1,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'metrics': vars(bt_result.metrics),
                    'tradeable': analysis.tradeable,
                })
            except Exception as e:
                print(f"  [滚动回测] 周期 {i+1} 失败: {e}")
                results.append({
                    'period': i + 1,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'metrics': None,
                    'error': str(e),
                })

        # 汇总
        valid_metrics = [r['metrics'] for r in results if r['metrics'] is not None]
        if valid_metrics:
            avg_sharpe = np.mean([m['sharpe_ratio'] for m in valid_metrics])
            avg_return = np.mean([m['total_return'] for m in valid_metrics])
            avg_max_dd = np.mean([m['max_drawdown'] for m in valid_metrics])
            n_tradeable = sum(1 for r in results if r.get('tradeable', False))
        else:
            avg_sharpe = avg_return = avg_max_dd = 0
            n_tradeable = 0

        return {
            'periods': results,
            'summary': {
                'total_periods': len(results),
                'tradeable_periods': n_tradeable,
                'avg_sharpe': float(avg_sharpe),
                'avg_return': float(avg_return),
                'avg_max_drawdown': float(avg_max_dd),
            }
        }

    # ========================
    # 内部方法
    # ========================

    def _generate_signals(
        self,
        zscore: pd.Series,
        entry_upper: pd.Series,
        entry_lower: pd.Series,
        exit_band: pd.Series,
        dcc_break_signals=None,
    ) -> tuple:
        """
        生成持仓信号

        Returns
        -------
        (positions, exit_reasons)
            positions: 持仓状态 1=做多价差, -1=做空价差, 0=空仓
            exit_reasons: 平仓原因 ('dcc_warning'/'max_holding'/'zscore'/None)
        """
        n = len(zscore)
        positions = pd.Series(0, index=zscore.index, dtype=int)
        exit_reasons = pd.Series(None, index=zscore.index, dtype=object)

        current_pos = 0
        hold_days = 0

        for i in range(1, n):
            z = zscore.iloc[i]
            eu = entry_upper.iloc[i] if i < len(entry_upper) else self.config.entry_zscore
            el = entry_lower.iloc[i] if i < len(entry_lower) else -self.config.entry_zscore
            eb = exit_band.iloc[i] if i < len(exit_band) else self.config.exit_zscore

            if pd.isna(z):
                positions.iloc[i] = current_pos
                continue

            if current_pos != 0:
                hold_days += 1

            # DCC 预警止损：最高优先级（高于 max_holding_days 和 Z-Score 平仓）
            if current_pos != 0 and dcc_break_signals is not None:
                if i < len(dcc_break_signals) and dcc_break_signals.iloc[i]:
                    current_pos = 0
                    hold_days = 0
                    positions.iloc[i] = current_pos
                    exit_reasons.iloc[i] = 'dcc_warning'
                    continue

            if current_pos == 0:
                # 空仓 → 开仓
                if z > eu:
                    current_pos = -1  # 做空价差
                    hold_days = 0
                elif z < el:
                    current_pos = 1   # 做多价差
                    hold_days = 0
            elif current_pos == 1:
                # 做多 → 平仓条件
                if hold_days >= self.config.max_holding_days:
                    current_pos = 0
                    hold_days = 0
                    exit_reasons.iloc[i] = 'max_holding'
                elif z > -eb:
                    current_pos = 0
                    hold_days = 0
                    exit_reasons.iloc[i] = 'zscore'
            elif current_pos == -1:
                # 做空 → 平仓条件
                if hold_days >= self.config.max_holding_days:
                    current_pos = 0
                    hold_days = 0
                    exit_reasons.iloc[i] = 'max_holding'
                elif z < eb:
                    current_pos = 0
                    hold_days = 0
                    exit_reasons.iloc[i] = 'zscore'

            positions.iloc[i] = current_pos

        return positions, exit_reasons

    def _simulate_trades(
        self,
        df: pd.DataFrame,
        spread: pd.Series,
        positions: pd.Series,
        exit_reasons: pd.Series = None,
    ) -> tuple:
        """
        模拟交易，计算权益曲线和交易记录

        价差套利：做多价差 → 价差上涨获利，做空价差 → 价差下跌获利

        收益率计算：日 PnL = 持仓 × 价差变化（绝对值，单位：元/吨）
        归一化：daily_return = daily_pnl / avg_notional
        其中 avg_notional = mean(price_a + price_b)，代表开仓一单位价差的平均资金占用
        """
        # 每日绝对盈亏（元/吨）
        spread_change = spread.diff()
        daily_pnl_abs = positions.shift(1) * spread_change
        daily_pnl_abs.iloc[0] = 0

        # 计算名义价值（两腿价格之和的均值），用于将绝对 PnL 转为收益率
        notional = (df['price_a'] + df['price_b']).mean()
        if notional <= 0:
            notional = 1.0  # 安全兜底

        # 日收益率
        daily_pnl = (daily_pnl_abs / notional).fillna(0)

        # 交易成本
        if self.config.transaction_cost > 0:
            trade_signals = positions.diff().abs()
            daily_pnl -= trade_signals * self.config.transaction_cost

        # 累计权益曲线（从 1.0 开始）
        cumulative = (1 + daily_pnl).cumprod()
        cumulative.iloc[0] = 1.0
        cumulative = cumulative.clip(lower=0.0001)

        equity = pd.DataFrame({
            'equity': cumulative,
            'drawdown': cumulative / cumulative.cummax() - 1,
            'position': positions,
            'daily_return': daily_pnl,
        })
        if 'date' in df.columns:
            equity['date'] = df['date'].values

        # 提取交易记录
        trades = self._extract_trades(df, spread, positions, exit_reasons=exit_reasons)

        return equity, trades, daily_pnl

    @staticmethod
    def _extract_trades(
        df: pd.DataFrame,
        spread: pd.Series,
        positions: pd.Series,
        exit_reasons: pd.Series = None,
    ) -> pd.DataFrame:
        """提取交易记录"""
        trade_list = []

        entry_idx = None
        entry_spread = 0
        direction = 0

        for i in range(1, len(positions)):
            pos = positions.iloc[i]
            prev_pos = positions.iloc[i - 1]

            if pos != prev_pos:
                if prev_pos == 0 and pos != 0:
                    # 开仓
                    entry_idx = i
                    entry_spread = spread.iloc[i]
                    direction = pos
                elif prev_pos != 0 and pos == 0:
                    # 平仓
                    if entry_idx is not None:
                        exit_spread = spread.iloc[i]
                        pnl = (exit_spread - entry_spread) * direction
                        holding_days = i - entry_idx

                        # 确定平仓原因
                        reason = 'zscore'  # 默认
                        if exit_reasons is not None and i < len(exit_reasons):
                            r = exit_reasons.iloc[i]
                            if r is not None and r != 'None':
                                reason = r

                        trade_record = {
                            'entry_idx': entry_idx,
                            'exit_idx': i,
                            'direction': '做多价差' if direction == 1 else '做空价差',
                            'entry_spread': entry_spread,
                            'exit_spread': exit_spread,
                            'pnl': pnl,
                            'pnl_pct': pnl / abs(entry_spread) * 100 if entry_spread != 0 else 0,
                            'holding_days': holding_days,
                            'exit_reason': reason,
                        }
                        if 'date' in df.columns:
                            trade_record['entry_date'] = str(df.iloc[entry_idx]['date'])
                            trade_record['exit_date'] = str(df.iloc[i]['date'])

                        trade_list.append(trade_record)

                    entry_idx = None
                    direction = 0

        if trade_list:
            return pd.DataFrame(trade_list)
        return pd.DataFrame()

    @staticmethod
    def _compute_metrics(
        equity: pd.DataFrame,
        trades: pd.DataFrame,
        daily_pnl: pd.Series,
    ) -> BacktestMetrics:
        """计算绩效指标"""
        m = BacktestMetrics()

        if equity.empty:
            return m

        total_ret = equity['equity'].iloc[-1] - 1
        m.total_return = total_ret

        # 年化收益（假设252个交易日）
        n_days = len(equity)
        if n_days > 1 and total_ret > -1:
            m.annual_return = (1 + total_ret) ** (252 / n_days) - 1

        # 日收益率标准差
        m.daily_returns_std = float(daily_pnl.std())
        if m.daily_returns_std > 0:
            m.sharpe_ratio = float(daily_pnl.mean() / m.daily_returns_std * np.sqrt(252))

        # 最大回撤
        m.max_drawdown = float(equity['drawdown'].min())

        # Calmar 比率
        if m.max_drawdown != 0:
            m.calmar_ratio = m.annual_return / abs(m.max_drawdown)

        # VaR & CVaR
        if len(daily_pnl) > 10:
            m.var_95 = float(np.percentile(daily_pnl.dropna(), 5))
            tail = daily_pnl[daily_pnl <= m.var_95]
            m.cvar_95 = float(tail.mean()) if len(tail) > 0 else m.var_95

        # 交易统计
        if trades is not None and len(trades) > 0:
            m.total_trades = len(trades)
            m.long_trades = len(trades[trades['direction'] == '做多价差'])
            m.short_trades = len(trades[trades['direction'] == '做空价差'])
            m.avg_holding_days = float(trades['holding_days'].mean())
            m.max_holding_days_actual = int(trades['holding_days'].max())

            win_trades = trades[trades['pnl'] > 0]
            lose_trades = trades[trades['pnl'] <= 0]
            m.win_rate = len(win_trades) / m.total_trades

            if len(lose_trades) > 0:
                avg_win = win_trades['pnl'].mean() if len(win_trades) > 0 else 0
                avg_loss = abs(lose_trades['pnl'].mean())
                m.profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0

        return m

    @staticmethod
    def _print_summary(m: BacktestMetrics):
        """打印回测摘要"""
        print(f"\n  {'='*40}")
        print(f"  回测绩效")
        print(f"  {'='*40}")
        print(f"  累计收益: {m.total_return:.2%}")
        print(f"  年化收益: {m.annual_return:.2%}")
        print(f"  夏普比率: {m.sharpe_ratio:.2f}")
        print(f"  最大回撤: {m.max_drawdown:.2%}")
        print(f"  Calmar比率: {m.calmar_ratio:.2f}")
        print(f"  总交易数: {m.total_trades}")
        print(f"  做多/做空: {m.long_trades}/{m.short_trades}")
        print(f"  胜率: {m.win_rate:.2%}")
        print(f"  盈亏比: {m.profit_loss_ratio:.2f}")
        print(f"  平均持仓: {m.avg_holding_days:.1f} 天")
        print(f"  VaR(95%): {m.var_95:.4f}")
        print(f"  CVaR(95%): {m.cvar_95:.4f}")
        print(f"  {'='*40}\n")
