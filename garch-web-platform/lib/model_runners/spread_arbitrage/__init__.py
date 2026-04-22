# -*- coding: utf-8 -*-
"""
价差套利分析 — Web 平台 Model Runner

为 Flask 平台提供统一的 runner 接口，与 basic_garch / dcc_garch / ecm_garch 同级。
"""

import os
from pathlib import Path
from datetime import datetime


def run_spread_arbitrage(
    data_path: str,
    sheet_name: str,
    column_mapping: dict,
    date_range: dict = None,
    skip_rows: int = 0,
    output_dir: str = None,
    model_config: dict = None,
) -> dict:
    """
    价差套利分析 runner（平台调用入口）

    Parameters
    ----------
    data_path : str
        Excel 文件路径
    sheet_name : str
        工作表名称
    column_mapping : dict
        列映射 {'col_a': str, 'col_b': str, 'date_col': str(可选)}
    date_range : dict
        日期范围过滤
    skip_rows : int
        跳过行数
    output_dir : str
        输出目录
    model_config : dict
        模型配置（来自前端参数）

    Returns
    -------
    dict
        {'success': bool, 'report_path': str, 'summary': dict}
    """
    try:
        import matplotlib
        matplotlib.use('agg')

        from lib.spread_arbitrage_analyzer.config import SpreadConfig
        from lib.spread_arbitrage_analyzer.data_loader import SpreadDataLoader
        from lib.spread_arbitrage_analyzer.spread_utils import calculate_spread_range
        from lib.spread_arbitrage_analyzer.spread_analyzer import SpreadAnalyzer
        from lib.spread_arbitrage_analyzer.backtest_engine import SpreadBacktestEngine
        from lib.spread_arbitrage_analyzer.report_generator import SpreadReportGenerator

        # 构建 config
        mc = model_config or {}
        config = SpreadConfig(
            entry_zscore=mc.get('entry_zscore', 2.0),
            exit_zscore=mc.get('exit_zscore', 0.5),
            zscore_window=mc.get('zscore_window', 60),
            max_holding_days=mc.get('max_holding_days', 60),
            enable_rolling_backtest=mc.get('enable_rolling_backtest', False),
            rolling_periods=mc.get('rolling_periods', 6),
            rolling_window_days=mc.get('rolling_window_days', 250),
            min_gap_days=mc.get('min_gap_days', 125),
            enable_dcc_stoploss=mc.get('enable_dcc_stoploss', True),
            transaction_cost=0.0,
        )

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 提取列映射
        col_a = column_mapping.get('col_a')
        col_b = column_mapping.get('col_b')
        date_col = column_mapping.get('date_col')

        if not col_a or not col_b:
            return {'success': False, 'error': '缺少价格列映射 (col_a, col_b)'}

        print(f"\n{'='*60}")
        print(f"价差套利分析")
        print(f"  文件: {data_path}")
        print(f"  工作表: {sheet_name}")
        print(f"  价格A: {col_a}, 价格B: {col_b}")
        print(f"{'='*60}\n")

        # 1. 加载数据
        print("[1/4] 加载数据...")
        loader = SpreadDataLoader()
        df = loader.load(
            filepath=data_path,
            sheet_name=sheet_name,
            col_a=col_a,
            col_b=col_b,
            date_col=date_col,
            skip_rows=skip_rows,
            date_range=date_range,
        )
        info = loader.get_info()
        print(f"  数据量: {info['total_rows']} 行")

        # 2. 统计分析
        print("[2/4] 统计分析...")
        analyzer = SpreadAnalyzer(config)
        analysis = analyzer.analyze(df)
        print(f"  {analysis.summary}")

        # 3. 回测
        print("[3/4] 回测...")
        engine = SpreadBacktestEngine(config)
        backtest = engine.run_backtest(df, analysis)

        # 3.5 滚动回测（可选）
        if config.enable_rolling_backtest:
            print("[3.5/4] 滚动回测...")
            rolling_result = engine.run_rolling_backtest(df)
        else:
            rolling_result = None

        # 4. 生成报告
        print("[4/4] 生成报告...")
        reporter = SpreadReportGenerator(output_dir)
        report_files = reporter.generate(
            df=df,
            analysis=analysis,
            backtest=backtest,
            config=config,
            series_a_name=col_a,
            series_b_name=col_b,
        )

        # 构建返回的 summary（确保值为 Python 原生类型，兼容 JSON 序列化）
        summary = {
            'is_mean_reverting': bool(analysis.is_mean_reverting),
            'is_cointegrated': bool(analysis.is_cointegrated),
            'tradeable': bool(analysis.tradeable),
            'half_life': float(analysis.half_life['halflife_days']),
            'adf_pvalue': float(analysis.adf_test['p_value']),
            'johansen_cointegrated': bool(analysis.johansen_test['cointegrated']),
            'full_correlation': float(analysis.correlation['full_sample']),
            'total_trades': int(backtest.metrics.total_trades),
            'total_return': f"{backtest.metrics.total_return:.2%}",
            'sharpe_ratio': f"{backtest.metrics.sharpe_ratio:.2f}",
            'max_drawdown': f"{backtest.metrics.max_drawdown:.2%}",
            'win_rate': f"{backtest.metrics.win_rate:.2%}",
            'profit_loss_ratio': f"{backtest.metrics.profit_loss_ratio:.2f}",
        }
        # 计算价差区间（Z-Score → 实际价差值）
        spread_range = None
        try:
            garch_res = {
                'volatility': None,
                'upper': analysis.dynamic_threshold_upper,
            } if analysis.dynamic_threshold_upper is not None else None
            spread_range = calculate_spread_range(df['spread'], config, garch_res) or None
        except Exception as e:
            print(f"价差区间计算失败: {e}")

        return {
            'success': True,
            'report_path': report_files['report_path'],
            'excel_path': report_files.get('excel_path'),
            'summary': summary,
            'spread_range': spread_range,
        }

    except Exception as e:
        import traceback
        error_msg = f"价差套利分析失败: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return {'success': False, 'error': error_msg}
