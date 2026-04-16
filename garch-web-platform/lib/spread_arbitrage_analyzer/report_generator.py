# -*- coding: utf-8 -*-
"""
价差套利分析 — 报告生成

生成 HTML 报告 + Excel 报告，包含图表和检验结果。
"""

import os
import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from .spread_analyzer import SpreadAnalysisResult
from .backtest_engine import BacktestResult, BacktestMetrics


# 中文字体设置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Heiti SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class SpreadReportGenerator:
    """价差套利报告生成器"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir = self.output_dir / 'figures'
        self.figures_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        df: pd.DataFrame,
        analysis: SpreadAnalysisResult,
        backtest: BacktestResult,
        config=None,
        series_a_name: str = '价格A',
        series_b_name: str = '价格B',
    ) -> Dict[str, str]:
        """
        生成完整报告

        Returns
        -------
        dict
            {'report_path': str, 'excel_path': str}
        """
        dates = df['date'] if 'date' in df.columns else pd.Series(range(len(df)))

        # 生成图表
        fig_files = {}
        fig_files['spread'] = self._plot_spread(dates, df['spread'], analysis)
        fig_files['zscore'] = self._plot_zscore(dates, df['spread'], analysis)
        fig_files['equity'] = self._plot_equity(dates, backtest)
        fig_files['correlation'] = self._plot_correlation(dates, analysis)

        # DCC 相关性图表
        if analysis.dcc_corr_series is not None:
            fig_files['dcc_correlation'] = self._plot_dcc_correlation(dates, analysis)

        # 生成 HTML 报告
        html_path = self._generate_html(
            df, analysis, backtest, fig_files, series_a_name, series_b_name
        )

        # 生成 Excel 报告
        excel_path = self._generate_excel(
            df, analysis, backtest, series_a_name, series_b_name
        )

        return {
            'report_path': str(html_path),
            'excel_path': str(excel_path),
        }

    # ========================
    # 图表生成
    # ========================

    def _plot_spread(
        self, dates, spread: pd.Series, analysis: SpreadAnalysisResult
    ) -> str:
        """价差走势 + 均值 ± 阈值"""
        fig, ax = plt.subplots(figsize=(14, 5))

        # 裁剪极值：用 1%/99% 分位数限制 y 轴范围
        q01, q99 = spread.quantile(0.01), spread.quantile(0.99)
        margin = (q99 - q01) * 0.15
        ylim_low, ylim_high = q01 - margin, q99 + margin

        ax.plot(dates, spread, color='#2196F3', linewidth=0.8, label='价差')
        ax.axhline(y=analysis.spread_stats['mean'], color='#FF5722',
                    linestyle='--', linewidth=1, label=f"均值 ({analysis.spread_stats['mean']:.1f})")

        # 动态阈值或固定阈值
        if analysis.dynamic_threshold_upper is not None and not analysis.dynamic_threshold_upper.isna().all():
            mean_val = analysis.spread_stats['mean']
            upper = mean_val + analysis.dynamic_threshold_upper * spread.std()
            lower = mean_val - analysis.dynamic_threshold_upper * spread.std()
            ax.fill_between(
                dates, lower, upper,
                alpha=0.1, color='#FF9800', label='GARCH 动态区间'
            )

        ax.set_title('价差走势', fontsize=14, fontweight='bold')
        ax.set_ylabel('价差')
        ax.set_ylim(ylim_low, ylim_high)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        if hasattr(dates, 'dt'):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            fig.autofmt_xdate()

        plt.tight_layout()
        return self._save_fig(fig, 'spread_trend.png')

    def _plot_zscore(
        self, dates, spread: pd.Series, analysis: SpreadAnalysisResult
    ) -> str:
        """Z-Score 时序 + 动态入场/出场阈值"""
        fig, ax = plt.subplots(figsize=(14, 5))

        zscore = analysis.zscore_series
        if zscore is None:
            plt.close(fig)
            return ''

        has_dynamic = (
            analysis.dynamic_threshold_upper is not None
            and analysis.dynamic_threshold_lower is not None
            and not analysis.dynamic_threshold_upper.isna().all()
        )

        ax.plot(dates, zscore, color='#9C27B0', linewidth=0.8, label='Z-Score')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)

        # 裁剪极值：用 1%/99% 分位数限制 y 轴，保留 15% 边距
        zs_clean = zscore.dropna()
        if len(zs_clean) > 0:
            q01, q99 = zs_clean.quantile(0.01), zs_clean.quantile(0.99)
            margin = (q99 - q01) * 0.15
            ax.set_ylim(q01 - margin, q99 + margin)

        if has_dynamic:
            du = analysis.dynamic_threshold_upper
            dl = analysis.dynamic_threshold_lower
            ax.plot(dates, du, color='#F44336', linestyle='--', linewidth=0.8,
                    label='入场 (GARCH 动态)')
            ax.plot(dates, -du, color='#F44336', linestyle='--', linewidth=0.8)
            ax.plot(dates, dl, color='#4CAF50', linestyle=':', linewidth=0.8,
                    label='出场 (GARCH 动态)')
            ax.plot(dates, -dl, color='#4CAF50', linestyle=':', linewidth=0.8)

            # 用动态阈值填充信号区域
            ax.fill_between(dates, du, zscore, where=(zscore > du),
                            alpha=0.2, color='#F44336')
            ax.fill_between(dates, -du, zscore, where=(zscore < -du),
                            alpha=0.2, color='#2196F3')

            title = '滚动 Z-Score（GARCH 动态入场/出场阈值）'
        else:
            ax.axhline(y=2, color='#F44336', linestyle='--', linewidth=0.8,
                        label='入场 (+2)')
            ax.axhline(y=-2, color='#F44336', linestyle='--', linewidth=0.8,
                        label='入场 (-2)')
            ax.axhline(y=0.5, color='#4CAF50', linestyle=':', linewidth=0.8,
                        label='出场 (+0.5)')
            ax.axhline(y=-0.5, color='#4CAF50', linestyle=':', linewidth=0.8,
                        label='出场 (-0.5)')

            ax.fill_between(dates, 2, zscore, where=(zscore > 2),
                            alpha=0.2, color='#F44336')
            ax.fill_between(dates, -2, zscore, where=(zscore < -2),
                            alpha=0.2, color='#2196F3')

            title = '滚动 Z-Score（固定入场/出场信号）'

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_ylabel('Z-Score')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)

        if hasattr(dates, 'dt'):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            fig.autofmt_xdate()

        plt.tight_layout()
        return self._save_fig(fig, 'zscore_signals.png')

    def _plot_equity(self, dates, backtest: BacktestResult) -> str:
        """净值曲线 + 回撤"""
        fig, axes = plt.subplots(2, 1, figsize=(14, 7), height_ratios=[3, 1])

        equity = backtest.equity_curve
        if equity is None or equity.empty:
            plt.close(fig)
            return ''

        ax1 = axes[0]
        if 'date' in equity.columns:
            eq_dates = pd.to_datetime(equity['date'])
        else:
            eq_dates = range(len(equity))

        ax1.plot(eq_dates, equity['equity'], color='#4CAF50', linewidth=1, label='净值')
        ax1.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.5)
        ax1.set_title(f"回测净值曲线（累计收益: {backtest.metrics.total_return:.2%}）",
                       fontsize=14, fontweight='bold')
        ax1.set_ylabel('净值')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 回撤图
        ax2 = axes[1]
        dd = equity['drawdown']
        ax2.fill_between(eq_dates, dd, 0, color='#F44336', alpha=0.4)
        ax2.plot(eq_dates, dd, color='#F44336', linewidth=0.5)
        ax2.set_title(f"回撤（最大: {backtest.metrics.max_drawdown:.2%}）",
                       fontsize=12)
        ax2.set_ylabel('回撤')
        ax2.grid(True, alpha=0.3)

        if hasattr(eq_dates, 'dt') if not isinstance(eq_dates, range) else False:
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            fig.autofmt_xdate()

        plt.tight_layout()
        return self._save_fig(fig, 'equity_drawdown.png')

    def _plot_correlation(self, dates, analysis: SpreadAnalysisResult) -> str:
        """滚动相关性"""
        corr = analysis.rolling_corr_series
        if corr is None:
            return ''

        fig, ax = plt.subplots(figsize=(14, 4))
        ax.plot(dates, corr, color='#FF9800', linewidth=0.8)
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
        ax.axhline(y=analysis.correlation['full_sample'], color='#F44336',
                    linestyle='--', linewidth=0.8, label=f"全样本相关: {analysis.correlation['full_sample']:.3f}")
        ax.set_title(f'滚动相关性（窗口={analysis.correlation["window"]}天）',
                      fontsize=14, fontweight='bold')
        ax.set_ylabel('相关系数')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        if hasattr(dates, 'dt'):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            fig.autofmt_xdate()

        plt.tight_layout()
        return self._save_fig(fig, 'rolling_correlation.png')

    def _plot_dcc_correlation(self, dates, analysis: SpreadAnalysisResult) -> str:
        """DCC 动态条件相关系数"""
        corr = analysis.dcc_corr_series
        if corr is None:
            return ''

        fig, ax = plt.subplots(figsize=(14, 5))

        # ρ_t 线（蓝色实线）
        ax.plot(dates, corr, color='#2196F3', linewidth=0.8, label='ρ_t')

        # 水平虚线：初始 ρ 水平（灰色）
        initial_rho = analysis.cointegration_break.get('initial_rho', None)
        if initial_rho is not None:
            ax.axhline(y=initial_rho, color='gray', linestyle='--', linewidth=1,
                       label=f'初始 ρ = {initial_rho:.4f}')

        # 红色阴影区域：预警信号
        signals = analysis.coint_break_signals
        if signals is not None and signals.any():
            signal_aligned = signals.reindex(corr.index, fill_value=False)
            ax.fill_between(dates, 0, 1, where=signal_aligned,
                            alpha=0.25, color='#F44336', label='预警信号', step='mid')

        corr_clean = corr.dropna()
        y_min = max(-1, float(corr_clean.min()) - 0.05)
        y_max = min(1, float(corr_clean.max()) + 0.05)
        ax.set_ylim(y_min, y_max)
        ax.set_title('DCC 动态条件相关系数', fontsize=14, fontweight='bold')
        ax.set_ylabel('ρ_t')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        if hasattr(dates, 'dt'):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            fig.autofmt_xdate()

        plt.tight_layout()
        return self._save_fig(fig, 'dcc_correlation.png')

    # ========================
    # HTML 报告
    # ========================

    def _generate_html(
        self, df, analysis, backtest, fig_files, series_a_name, series_b_name
    ) -> Path:
        """生成 HTML 报告"""
        # 嵌入图片 base64
        images = {}
        for name, path in fig_files.items():
            if path and os.path.exists(path):
                with open(path, 'rb') as f:
                    images[name] = base64.b64encode(f.read()).decode('utf-8')

        m = backtest.metrics

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>价差套利分析报告 — {series_a_name} vs {series_b_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, 'Segoe UI', Arial, sans-serif; background: #f5f5f5; color: #333; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ font-size: 24px; color: #1a73e8; margin-bottom: 30px; padding-bottom: 15px; border-bottom: 2px solid #e8eaed; }}
        h2 {{ font-size: 18px; color: #333; margin: 30px 0 15px; padding-left: 10px; border-left: 4px solid #1a73e8; }}
        .summary-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }}
        .summary-box.pass {{ border-left: 4px solid #4CAF50; }}
        .summary-box.warn {{ border-left: 4px solid #FF9800; }}
        .summary-box.fail {{ border-left: 4px solid #F44336; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 10px 15px; text-align: left; border-bottom: 1px solid #e8eaed; }}
        th {{ background: #f8f9fa; font-weight: 600; color: #555; font-size: 13px; }}
        td {{ font-size: 14px; }}
        .metric {{ display: inline-block; width: 200px; padding: 15px; margin: 10px; background: #f8f9fa; border-radius: 8px; text-align: center; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #1a73e8; }}
        .metric .label {{ font-size: 12px; color: #888; margin-top: 5px; }}
        .positive {{ color: #4CAF50 !important; }}
        .negative {{ color: #F44336 !important; }}
        img {{ max-width: 100%; margin: 15px 0; border-radius: 4px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 8px; overflow-x: auto; font-size: 13px; }}
        .verdict {{ font-size: 16px; padding: 15px 20px; border-radius: 8px; margin: 20px 0; }}
        .verdict.good {{ background: #e8f5e9; color: #2e7d32; }}
        .verdict.bad {{ background: #ffebee; color: #c62828; }}
    </style>
</head>
<body>
<div class="container">
    <h1>📊 价差套利分析报告</h1>
    <p style="color:#888;">{series_a_name} vs {series_b_name}</p>

    <!-- 综合判断 -->
    <div class="verdict {'good' if analysis.tradeable else 'bad'}">
        {'✅ 价差具备套利条件：平稳 + 协整 + 合理半衰期' if analysis.tradeable else '❌ 价差不具备套利条件'}
    </div>

    <!-- 分析摘要 -->
    <h2>📋 分析摘要</h2>
    <pre>{analysis.summary}</pre>

    <!-- 数据概况 -->
    <h2>📈 数据概况</h2>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>数据区间</td><td>{analysis.spread_stats.get('date_range', 'N/A')}</td></tr>
        <tr><td>样本量</td><td>{analysis.spread_stats['n_observations']} 个交易日</td></tr>
        <tr><td>价差均值</td><td>{analysis.spread_stats['mean']:.2f}</td></tr>
        <tr><td>价差标准差</td><td>{analysis.spread_stats['std']:.2f}</td></tr>
        <tr><td>价差范围</td><td>[{analysis.spread_stats['min']:.2f}, {analysis.spread_stats['max']:.2f}]</td></tr>
    </table>

    <!-- 统计检验 -->
    <h2>🔬 统计检验</h2>
    <table>
        <tr><th>检验项目</th><th>统计量</th><th>临界值</th><th>结论</th></tr>
        <tr>
            <td>ADF 平稳性检验</td>
            <td>{analysis.adf_test['statistic']:.4f} (p={analysis.adf_test['p_value']:.4f})</td>
            <td>5%: {analysis.adf_test['critical_values']['5%']:.4f}</td>
            <td class="{'positive' if analysis.adf_test['stationary'] else 'negative'}">{'✅ 平稳' if analysis.adf_test['stationary'] else '❌ 非平稳'}</td>
        </tr>
        <tr>
            <td>Johansen 协整检验</td>
            <td>迹统计量={analysis.johansen_test['trace_stat_r0']:.2f}</td>
            <td>5%: {analysis.johansen_test['critical_5pct_r0']:.2f}</td>
            <td class="{'positive' if analysis.johansen_test['cointegrated'] else 'negative'}">{'✅ 存在协整' if analysis.johansen_test['cointegrated'] else '❌ 无协整'}</td>
        </tr>
        <tr>
            <td>OU 半衰期</td>
            <td>{analysis.half_life['halflife_days']:.1f} 天</td>
            <td>R²={analysis.half_life['r_squared']:.4f}</td>
            <td class="{'positive' if analysis.half_life['interpretable'] else 'negative'}">{'✅ 合理' if analysis.half_life['interpretable'] else '⚠️ 偏长/不可估计'}</td>
        </tr>
        <tr>
            <td>滚动相关性</td>
            <td>全样本: {analysis.correlation['full_sample']:.4f}</td>
            <td>均值: {analysis.correlation['mean']:.4f}</td>
            <td>—</td>
        </tr>
    </table>

    <!-- 图表 -->
    <h2>📉 价差走势</h2>
    {'<img src="data:image/png;base64,' + images.get('spread', '') + '">' if images.get('spread') else '<p>图表生成失败</p>'}

    <h2>📊 Z-Score 信号</h2>
    {'<img src="data:image/png;base64,' + images.get('zscore', '') + '">' if images.get('zscore') else '<p>图表生成失败</p>'}

    <h2>📉 滚动相关性</h2>
    {'<img src="data:image/png;base64,' + images.get('correlation', '') + '">' if images.get('correlation') else '<p>图表生成失败</p>'}

    {'<h2>📊 DCC 动态条件相关系数</h2><img src="data:image/png;base64,' + images.get('dcc_correlation', '') + '">' if images.get('dcc_correlation') else ''}

    {'<div style="background:#FFF3E0;padding:12px;border-radius:6px;border-left:4px solid #FF9800;"><strong>⚠️ DCC 分析失败</strong><br>协整稳定性监控未能成功执行，可能由于数据不足或模型不收敛。回测将不包含 DCC 预警止损。</div>' if analysis.dcc_analysis_failed else ''}

    {'<h2>🔬 协整稳定性监控</h2><table><tr><th>指标</th><th>数值</th></tr><tr><td>初始条件相关系数</td><td>' + str(analysis.cointegration_break.get("initial_rho", "N/A")) + '</td></tr><tr><td>当前条件相关系数</td><td>' + str(analysis.cointegration_break.get("current_rho", "N/A")) + '</td></tr><tr><td>最低条件相关系数</td><td>' + str(analysis.cointegration_break.get("min_rho", "N/A")) + '</td></tr><tr><td>预警触发次数</td><td>' + str(analysis.cointegration_break.get("warn_count", 0)) + '</td></tr><tr><td>累计预警天数</td><td>' + str(analysis.cointegration_break.get("warn_days", 0)) + '</td></tr><tr><td>DCC 预警止损</td><td>' + ('已启用' if analysis.cointegration_break.get("warn_count") is not None else 'N/A') + '</td></tr></table>' if analysis.cointegration_break else ''}

    <h2>💹 回测绩效</h2>
    <div style="margin: 15px 0;">
        <div class="metric"><div class="value {'positive' if m.total_return >= 0 else 'negative'}">{m.total_return:.2%}</div><div class="label">累计收益</div></div>
        <div class="metric"><div class="value {'positive' if m.annual_return >= 0 else 'negative'}">{m.annual_return:.2%}</div><div class="label">年化收益</div></div>
        <div class="metric"><div class="value">{m.sharpe_ratio:.2f}</div><div class="label">夏普比率</div></div>
        <div class="metric"><div class="value negative">{m.max_drawdown:.2%}</div><div class="label">最大回撤</div></div>
        <div class="metric"><div class="value">{m.win_rate:.1%}</div><div class="label">胜率</div></div>
        <div class="metric"><div class="value">{m.profit_loss_ratio:.2f}</div><div class="label">盈亏比</div></div>
    </div>

    <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>总交易次数</td><td>{m.total_trades}</td></tr>
        <tr><td>做多/做空</td><td>{m.long_trades} / {m.short_trades}</td></tr>
        <tr><td>平均持仓天数</td><td>{m.avg_holding_days:.1f}</td></tr>
        <tr><td>Calmar 比率</td><td>{m.calmar_ratio:.2f}</td></tr>
        <tr><td>VaR (95%)</td><td>{m.var_95:.4f}</td></tr>
        <tr><td>CVaR (95%)</td><td>{m.cvar_95:.4f}</td></tr>
    </table>

    {'<img src="data:image/png;base64,' + images.get('equity', '') + '">' if images.get('equity') else ''}

    <!-- 交易记录 -->
    <h2>📝 交易记录</h2>
    {self._trades_to_html(backtest.trades)}

</div>
</body>
</html>"""

        report_path = self.output_dir / 'spread_arbitrage_report.html'
        report_path.write_text(html, encoding='utf-8')
        return report_path

    @staticmethod
    def _trades_to_html(trades: pd.DataFrame) -> str:
        """交易记录转 HTML 表格"""
        if trades is None or trades.empty:
            return '<p>无交易记录</p>'

        cols_to_show = ['direction', 'entry_date', 'exit_date',
                        'entry_spread', 'exit_spread', 'pnl', 'holding_days', 'exit_reason']
        available_cols = [c for c in cols_to_show if c in trades.columns]

        col_names = {
            'direction': '方向', 'entry_date': '开仓日', 'exit_date': '平仓日',
            'entry_spread': '开仓价差', 'exit_spread': '平仓价差',
            'pnl': '盈亏', 'pnl_pct': '收益率%', 'holding_days': '持仓天数',
            'exit_reason': '平仓原因',
        }

        exit_reason_labels = {
            'dcc_warning': 'DCC 预警',
            'max_holding': '超期强平',
            'zscore': 'Z-Score',
        }

        html = '<table><tr>'
        for c in available_cols:
            html += f'<th>{col_names.get(c, c)}</th>'
        html += '</tr>'

        for _, row in trades.iterrows():
            pnl_class = 'positive' if row.get('pnl', 0) > 0 else 'negative'
            html += '<tr>'
            for c in available_cols:
                val = row[c]
                if c == 'pnl':
                    html += f'<td class="{pnl_class}">{val:.2f}</td>'
                elif c in ('entry_spread', 'exit_spread'):
                    html += f'<td>{val:.2f}</td>'
                elif c == 'holding_days':
                    html += f'<td>{int(val)}</td>'
                elif c == 'exit_reason':
                    label = exit_reason_labels.get(val, val)
                    if val == 'dcc_warning':
                        html += f'<td style="color:#F44336;font-weight:bold;">{label}</td>'
                    else:
                        html += f'<td>{label}</td>'
                else:
                    html += f'<td>{val}</td>'
            html += '</tr>'

        html += '</table>'
        return html

    # ========================
    # Excel 报告
    # ========================

    def _generate_excel(
        self, df, analysis, backtest, series_a_name, series_b_name
    ) -> Path:
        """生成 Excel 报告"""
        excel_path = self.output_dir / 'spread_arbitrage_report.xlsx'

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 1. 数据概览
            info_data = {
                '项目': ['价格序列A', '价格序列B', '数据区间', '样本量',
                         '价差均值', '价差标准差', '价差最小值', '价差最大值'],
                '数值': [
                    series_a_name, series_b_name,
                    f"{df['date'].min()} ~ {df['date'].max()}" if 'date' in df.columns else 'N/A',
                    analysis.spread_stats['n_observations'],
                    analysis.spread_stats['mean'],
                    analysis.spread_stats['std'],
                    analysis.spread_stats['min'],
                    analysis.spread_stats['max'],
                ]
            }
            pd.DataFrame(info_data).to_excel(writer, sheet_name='数据概览', index=False)

            # 2. 统计检验
            test_data = {
                '检验项目': ['ADF检验', 'ADF p值', 'ADF 滞后阶数',
                           'Johansen 迹统计量', 'Johansen 临界值(5%)',
                           '协整关系数量',
                           'OU 半衰期(天)', 'OU R²',
                           '全样本相关性', '滚动相关性均值'],
                '数值': [
                    analysis.adf_test['statistic'],
                    analysis.adf_test['p_value'],
                    analysis.adf_test['used_lag'],
                    analysis.johansen_test['trace_stat_r0'],
                    analysis.johansen_test['critical_5pct_r0'],
                    analysis.johansen_test['n_coint_relations'],
                    analysis.half_life['halflife_days'],
                    analysis.half_life['r_squared'],
                    analysis.correlation['full_sample'],
                    analysis.correlation['mean'],
                ]
            }
            pd.DataFrame(test_data).to_excel(writer, sheet_name='统计检验', index=False)

            # 3. 每日数据
            daily_df = df[['date', 'price_a', 'price_b', 'spread']].copy() if 'date' in df.columns else df[['price_a', 'price_b', 'spread']].copy()
            if analysis.zscore_series is not None:
                daily_df['zscore'] = analysis.zscore_series.values
            if analysis.rolling_corr_series is not None:
                daily_df['rolling_corr'] = analysis.rolling_corr_series.values
            if analysis.dynamic_threshold_upper is not None:
                daily_df['garch_entry_upper'] = analysis.dynamic_threshold_upper.values
                daily_df['garch_entry_lower'] = -analysis.dynamic_threshold_upper.values
            if analysis.dynamic_threshold_lower is not None:
                daily_df['garch_exit_upper'] = analysis.dynamic_threshold_lower.values
                daily_df['garch_exit_lower'] = -analysis.dynamic_threshold_lower.values
            daily_df.to_excel(writer, sheet_name='每日数据', index=False)

            # 4. 回测绩效
            m = backtest.metrics
            perf_data = {
                '指标': ['累计收益率', '年化收益率', '夏普比率', '最大回撤',
                        'Calmar比率', '总交易次数', '做多次数', '做空次数',
                        '胜率', '盈亏比', '平均持仓天数', 'VaR(95%)', 'CVaR(95%)'],
                '数值': [m.total_return, m.annual_return, m.sharpe_ratio,
                        m.max_drawdown, m.calmar_ratio, m.total_trades,
                        m.long_trades, m.short_trades, m.win_rate,
                        m.profit_loss_ratio, m.avg_holding_days,
                        m.var_95, m.cvar_95],
            }
            pd.DataFrame(perf_data).to_excel(writer, sheet_name='回测绩效', index=False)

            # 5. 交易记录
            if backtest.trades is not None and not backtest.trades.empty:
                backtest.trades.to_excel(writer, sheet_name='交易记录', index=False)

        return excel_path

    # ========================
    # 工具方法
    # ========================

    def _save_fig(self, fig, filename: str) -> str:
        """保存图表并返回路径"""
        filepath = self.figures_dir / filename
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return str(filepath)
