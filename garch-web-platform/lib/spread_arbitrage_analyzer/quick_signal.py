# -*- coding: utf-8 -*-
"""
快速信号计算器

支持所有模型类型：
- spread_arbitrage: Z-Score + 交易方向
- basic_garch: 最优套保比例 + 条件波动率
- dcc_garch: 动态相关系数 + 最优套保比例
- ecm_garch: 误差修正项 + 套保比例

跳过回测引擎和报告生成，仅运行核心模型拟合。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


class QuickSignalCalculator:
    """快速信号计算器（支持所有模型）"""

    LOOKBACK_DAYS = 30

    def calculate(self, config: dict) -> dict:
        """
        根据配置文件计算最近 30 天的信号

        Parameters
        ----------
        config : dict
            配置文件内容（从 JSON 读取）

        Returns
        -------
        dict
            包含 current, last_30_days, config_info, last_analysis 的结果字典
        """
        model_type = config.get('model_type', 'spread_arbitrage')

        if model_type == 'spread_arbitrage':
            return self._calculate_spread(config)
        elif model_type in ('basic_garch', 'dcc_garch', 'ecm_garch'):
            return self._calculate_garch(config)
        else:
            return {'success': False, 'error': f'不支持的模型类型: {model_type}'}

    # ========================
    # 价差套利模型
    # ========================

    def _calculate_spread(self, config: dict) -> dict:
        """价差套利快速信号"""
        try:
            import matplotlib
            matplotlib.use('agg')

            data_cfg = config.get('data', {})
            param_cfg = config.get('parameters', {})
            last_summary = config.get('last_analysis_summary', {})

            filepath = data_cfg.get('filepath')
            sheet_name = data_cfg.get('sheet_name')
            col_mapping = data_cfg.get('column_mapping', {})
            skip_rows = data_cfg.get('skip_rows', 0)
            date_range = data_cfg.get('date_range')

            col_a = col_mapping.get('col_a')
            col_b = col_mapping.get('col_b')
            date_col = col_mapping.get('date_col')

            if not filepath or not col_a or not col_b:
                return {'success': False, 'error': '配置文件缺少必要字段 (filepath, col_a, col_b)'}

            print(f"\n{'='*60}")
            print(f"快速信号计算 [价差套利]")
            print(f"  文件: {filepath}")
            print(f"  工作表: {sheet_name}")
            print(f"  价格A: {col_a}, 价格B: {col_b}")
            print(f"{'='*60}\n")

            # 加载数据
            print("[1/3] 加载数据...")
            from .data_loader import SpreadDataLoader
            from .config import SpreadConfig

            loader = SpreadDataLoader()
            df = loader.load(
                filepath=filepath,
                sheet_name=sheet_name,
                col_a=col_a,
                col_b=col_b,
                date_col=date_col,
                skip_rows=skip_rows,
                date_range=date_range,
            )
            total_rows = len(df)
            print(f"  数据量: {total_rows} 行")

            # 构建参数配置
            spread_config = SpreadConfig(
                entry_zscore=param_cfg.get('entry_zscore', 2.0),
                exit_zscore=param_cfg.get('exit_zscore', 0.5),
                zscore_window=param_cfg.get('zscore_window', 60),
                max_holding_days=param_cfg.get('max_holding_days', 60),
                enable_dcc_stoploss=param_cfg.get('enable_dcc_stoploss', True),
            )

            # 核心分析
            print("[2/3] 核心分析 (GARCH + DCC)...")
            zscore, garch_upper, garch_lower = self._compute_spread_signals(df, spread_config)

            # 提取最近 30 天
            print("[3/3] 生成信号...")
            last_30, current = self._extract_spread_last_n_days(
                df, zscore, garch_upper, garch_lower, spread_config
            )

            date_start = df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A'
            date_end = df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else 'N/A'

            config_info = {
                'model_type': 'spread_arbitrage',
                'model_name': '价差套利',
                'entry_zscore': spread_config.entry_zscore,
                'exit_zscore': spread_config.exit_zscore,
                'zscore_window': spread_config.zscore_window,
                'max_holding_days': spread_config.max_holding_days,
                'data_date_range': f'{date_start} ~ {date_end}',
                'total_rows': total_rows,
                'use_garch_threshold': garch_upper is not None,
                'use_dcc_stoploss': spread_config.enable_dcc_stoploss,
            }

            last_analysis = {
                'created_at': config.get('created_at', 'N/A'),
                'tradeable': last_summary.get('tradeable', False),
                'is_cointegrated': last_summary.get('is_cointegrated', False),
                'half_life': last_summary.get('half_life', 'N/A'),
                'full_correlation': last_summary.get('full_correlation', 'N/A'),
            }

            print(f"\n  当前信号: {current['signal']}")
            print(f"  Z-Score: {current['zscore']:.4f}")
            print(f"{'='*60}\n")

            return {
                'success': True,
                'model_type': 'spread_arbitrage',
                'current': current,
                'last_30_days': last_30,
                'config_info': config_info,
                'last_analysis': last_analysis,
            }

        except Exception as e:
            import traceback
            error_msg = f"快速信号计算失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {'success': False, 'error': error_msg}

    def _compute_spread_signals(self, df, config) -> tuple:
        """计算价差套利信号指标"""
        from .spread_analyzer import SpreadAnalyzer

        analyzer = SpreadAnalyzer(config)
        spread = df['spread']

        print("  计算 Z-Score...")
        zscore = analyzer._rolling_zscore(spread)

        garch_upper = None
        garch_lower = None
        if config.enable_dynamic_threshold:
            print("  GARCH(1,1) 拟合中...")
            garch_result = analyzer._garch_dynamic_threshold(spread)
            if garch_result.get('volatility') is not None:
                garch_upper = garch_result['upper']
                garch_lower = garch_result['lower']
                garch_upper = garch_upper.reindex(df.index, method='ffill')
                garch_lower = garch_lower.reindex(df.index, method='ffill')
                print("  GARCH 动态阈值计算完成")
            else:
                print("  GARCH 拟合数据不足，使用固定阈值")

        dcc_break = None
        if config.enable_dcc_stoploss:
            print("  DCC-GARCH 监控中...")
            dcc_result = analyzer._dcc_cointegration_monitor(df, 'price_a', 'price_b')
            dcc_break = dcc_result.get('break_signals')
            if dcc_break is not None:
                dcc_break = dcc_break.reindex(df.index, fill_value=False)
                print("  DCC 监控计算完成")
            else:
                print("  DCC 数据不足，跳过")

        self._dcc_break = dcc_break
        return zscore, garch_upper, garch_lower

    def _extract_spread_last_n_days(self, df, zscore, garch_upper, garch_lower, config) -> tuple:
        """提取价差套利最近 N 天"""
        n = self.LOOKBACK_DAYS
        tail_df = df.tail(n)
        dcc_break = getattr(self, '_dcc_break', None)

        rows = []
        for i in range(len(tail_df)):
            idx = tail_df.index[i]
            z = zscore.iloc[idx] if idx < len(zscore) else None

            if garch_upper is not None and idx < len(garch_upper) and not pd.isna(garch_upper.iloc[idx]):
                entry_upper = float(garch_upper.iloc[idx])
                entry_lower = -entry_upper
                exit_band = float(garch_lower.iloc[idx]) if garch_lower is not None and idx < len(garch_lower) and not pd.isna(garch_lower.iloc[idx]) else config.exit_zscore
            else:
                entry_upper = config.entry_zscore
                entry_lower = -config.entry_zscore
                exit_band = config.exit_zscore

            signal, signal_type = _determine_spread_signal(z, entry_upper, entry_lower, exit_band)

            if dcc_break is not None and idx < len(dcc_break) and dcc_break.iloc[idx]:
                if signal_type != 'close':
                    signal = 'DCC预警·建议平仓'
                    signal_type = 'dcc_warning'

            row = {
                'date': str(tail_df.iloc[i]['date']) if 'date' in tail_df.columns else '',
                'price_a': float(tail_df.iloc[i]['price_a']),
                'price_b': float(tail_df.iloc[i]['price_b']),
                'spread': float(tail_df.iloc[i]['spread']),
                'zscore': round(float(z), 4) if z is not None and not pd.isna(z) else None,
                'signal': signal,
                'signal_type': signal_type,
            }
            rows.append(row)

        return rows, rows[-1] if rows else None

    # ========================
    # GARCH 套保比例模型
    # ========================

    def _calculate_garch(self, config: dict) -> dict:
        """GARCH 套保比例快速信号（basic_garch / dcc_garch / ecm_garch）"""
        try:
            import matplotlib
            matplotlib.use('agg')

            model_type = config.get('model_type')
            data_cfg = config.get('data', {})
            param_cfg = config.get('parameters', {})
            last_summary = config.get('last_analysis_summary', {})

            filepath = data_cfg.get('filepath')
            sheet_name = data_cfg.get('sheet_name')
            col_mapping = data_cfg.get('column_mapping', {})
            skip_rows = data_cfg.get('skip_rows', 0)
            date_range = data_cfg.get('date_range')

            spot_col = col_mapping.get('spot')
            futures_col = col_mapping.get('future')
            date_col = col_mapping.get('date')

            if not filepath or not spot_col or not futures_col:
                return {'success': False, 'error': '配置文件缺少必要字段 (filepath, spot, future)'}

            MODEL_NAMES = {
                'basic_garch': 'Basic GARCH',
                'dcc_garch': 'DCC-GARCH',
                'ecm_garch': 'ECM-GARCH',
            }

            print(f"\n{'='*60}")
            print(f"快速信号计算 [{MODEL_NAMES[model_type]}]")
            print(f"  文件: {filepath}")
            print(f"  工作表: {sheet_name}")
            print(f"  现货: {spot_col}, 期货: {futures_col}")
            print(f"{'='*60}\n")

            # 1. 加载数据
            print("[1/2] 加载数据...")
            from lib.basic_garch_analyzer.data_loader import load_and_preprocess

            min_required = {
                'basic_garch': 120,
                'dcc_garch': 150,
                'ecm_garch': param_cfg.get('coint_window', 120) + 2,
            }

            data, selected = load_and_preprocess(
                file_path=filepath,
                sheet_name=sheet_name,
                date_col=date_col,
                spot_col=spot_col,
                futures_col=futures_col,
                skip_rows=skip_rows,
                output_file=None,
                interactive=False,
                min_required=min_required.get(model_type, 120),
            )
            total_rows = len(data)
            print(f"  数据量: {total_rows} 行")

            # 2. 拟合模型
            print(f"[2/2] 拟合 {MODEL_NAMES[model_type]} 模型...")
            model_results = self._fit_garch_model(model_type, data, param_cfg)

            # 3. 提取最近 30 天
            last_30, current = self._extract_garch_last_n_days(data, model_results, model_type)

            date_start = data['date'].min().strftime('%Y-%m-%d')
            date_end = data['date'].max().strftime('%Y-%m-%d')

            config_info = {
                'model_type': model_type,
                'model_name': MODEL_NAMES[model_type],
                'data_date_range': f'{date_start} ~ {date_end}',
                'total_rows': total_rows,
                'spot_col': spot_col,
                'futures_col': futures_col,
            }
            # 添加模型特有参数
            for k, v in param_cfg.items():
                config_info[k] = v

            last_analysis = {
                'created_at': config.get('created_at', 'N/A'),
            }
            if last_summary:
                last_analysis.update({k: v for k, v in last_summary.items()})

            print(f"\n  当前套保比例: {current['hedge_ratio']:.4f}")
            if 'rho' in current:
                print(f"  动态相关系数: {current['rho']:.4f}")
            if 'ect' in current:
                print(f"  误差修正项: {current['ect']:.6f}")
            print(f"{'='*60}\n")

            return {
                'success': True,
                'model_type': model_type,
                'current': current,
                'last_30_days': last_30,
                'config_info': config_info,
                'last_analysis': last_analysis,
            }

        except Exception as e:
            import traceback
            error_msg = f"快速信号计算失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return {'success': False, 'error': error_msg}

    @staticmethod
    def _fit_garch_model(model_type: str, data: pd.DataFrame, params: dict) -> dict:
        """根据模型类型调用对应的拟合函数"""
        if model_type == 'basic_garch':
            from lib.basic_garch_analyzer.basic_garch_model import fit_basic_garch
            return fit_basic_garch(
                data,
                p=params.get('p', 1),
                q=params.get('q', 1),
                corr_window=params.get('corr_window', 120),
                tax_rate=params.get('tax_rate', 0.13),
            )
        elif model_type == 'dcc_garch':
            from lib.model_runners.dcc_garch.dcc_model import fit_dcc_garch_model
            return fit_dcc_garch_model(
                data=data,
                p=params.get('p', 1),
                q=params.get('q', 1),
                dist=params.get('dist', 'norm'),
            )
        elif model_type == 'ecm_garch':
            from lib.model_runners.ecm_garch.ecm_model import fit_ecm_garch_model
            return fit_ecm_garch_model(
                data=data,
                p=params.get('p', 1),
                q=params.get('q', 1),
                coint_window=params.get('coint_window', 120),
                coupling_method=params.get('coupling_method', 'ect-garch'),
                tax_rate=params.get('tax_rate', 0.13),
            )
        else:
            raise ValueError(f'不支持的模型类型: {model_type}')

    def _extract_garch_last_n_days(
        self, data: pd.DataFrame, results: dict, model_type: str
    ) -> tuple:
        """提取 GARCH 模型最近 N 天的套保比例"""
        n = self.LOOKBACK_DAYS
        dates = data['date'].values
        spots = data['spot'].values
        futures = data['futures'].values
        spreads = data['spread'].values
        h_actual = np.array(results.get('h_actual', []))
        sigma_s = np.array(results.get('sigma_s', []))
        sigma_f = np.array(results.get('sigma_f', []))

        total = min(len(dates), len(h_actual))
        start = max(0, total - n)

        rows = []
        for i in range(start, total):
            row = {
                'date': str(dates[i]),
                'spot': round(float(spots[i]), 2),
                'futures': round(float(futures[i]), 2),
                'spread': round(float(spreads[i]), 2),
                'hedge_ratio': round(float(h_actual[i]), 6) if i < len(h_actual) else None,
                'sigma_s': round(float(sigma_s[i]), 6) if i < len(sigma_s) else None,
                'sigma_f': round(float(sigma_f[i]), 6) if i < len(sigma_f) else None,
            }

            # 模型特有字段
            if model_type == 'basic_garch':
                corr = np.array(results.get('rolling_corr', []))
                row['rolling_corr'] = round(float(corr[i]), 4) if i < len(corr) else None
            elif model_type == 'dcc_garch':
                rho = np.array(results.get('rho_t', []))
                row['rho'] = round(float(rho[i]), 4) if i < len(rho) else None
            elif model_type == 'ecm_garch':
                ect = np.array(results.get('ect', []))
                row['ect'] = round(float(ect[i]), 6) if i < len(ect) else None

            rows.append(row)

        # 当前值（最后一天）
        last = rows[-1] if rows else {}
        current = {
            'date': last.get('date', ''),
            'spot': last.get('spot'),
            'futures': last.get('futures'),
            'spread': last.get('spread'),
            'hedge_ratio': last.get('hedge_ratio'),
            'sigma_s': last.get('sigma_s'),
            'sigma_f': last.get('sigma_f'),
        }
        if model_type == 'basic_garch':
            current['rolling_corr'] = last.get('rolling_corr')
        elif model_type == 'dcc_garch':
            current['rho'] = last.get('rho')
        elif model_type == 'ecm_garch':
            current['ect'] = last.get('ect')

        return rows, current


# ========================
# 工具函数
# ========================

def _determine_spread_signal(z, entry_upper, entry_lower, exit_band) -> tuple:
    """根据 Z-Score 判断价差套利信号"""
    if z is None or pd.isna(z):
        return '数据缺失', 'none'
    if z > entry_upper:
        return '做空价差', 'short'
    elif z < entry_lower:
        return '做多价差', 'long'
    elif abs(z) < exit_band:
        return '平仓观望', 'close'
    else:
        return '持仓中', 'hold'
