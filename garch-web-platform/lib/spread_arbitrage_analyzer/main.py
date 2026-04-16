#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价差套利分析 — 独立命令行入口

用法:
    python main.py --file 数据.xlsx --sheet 卷螺差 --col-a 热卷 --col-b 螺纹 --skip-rows 3
"""

import argparse
import sys
from pathlib import Path

# 确保父目录在路径中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import matplotlib
matplotlib.use('agg')

from lib.spread_arbitrage_analyzer.config import SpreadConfig
from lib.spread_arbitrage_analyzer.data_loader import SpreadDataLoader
from lib.spread_arbitrage_analyzer.spread_analyzer import SpreadAnalyzer
from lib.spread_arbitrage_analyzer.backtest_engine import SpreadBacktestEngine
from lib.spread_arbitrage_analyzer.report_generator import SpreadReportGenerator


def main():
    parser = argparse.ArgumentParser(description='价差套利分析工具')
    parser.add_argument('--file', required=True, help='Excel 数据文件路径')
    parser.add_argument('--sheet', required=True, help='工作表名称')
    parser.add_argument('--col-a', required=True, help='价格序列A列名')
    parser.add_argument('--col-b', required=True, help='价格序列B列名')
    parser.add_argument('--date-col', default=None, help='日期列名（默认自动检测）')
    parser.add_argument('--skip-rows', type=int, default=0, help='跳过前N行')
    parser.add_argument('--output', default=None, help='输出目录（默认: outputs/spread_arbitrage/）')
    parser.add_argument('--entry-zscore', type=float, default=2.0, help='入场Z-Score阈值')
    parser.add_argument('--exit-zscore', type=float, default=0.5, help='出场Z-Score阈值')
    parser.add_argument('--zscore-window', type=int, default=60, help='Z-Score滚动窗口')
    parser.add_argument('--max-holding', type=int, default=60, help='最大持仓天数')
    parser.add_argument('--rolling', action='store_true', help='启用滚动回测')
    parser.add_argument('--rolling-periods', type=int, default=6, help='滚动回测周期数')

    args = parser.parse_args()

    # 配置
    config = SpreadConfig(
        entry_zscore=args.entry_zscore,
        exit_zscore=args.exit_zscore,
        zscore_window=args.zscore_window,
        max_holding_days=args.max_holding,
        enable_rolling_backtest=args.rolling,
        rolling_periods=args.rolling_periods,
    )

    # 输出目录
    if args.output:
        output_dir = args.output
    else:
        from datetime import datetime
        base_dir = Path(__file__).parent.parent.parent.parent / 'outputs' / 'spread_arbitrage'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = str(base_dir / timestamp)

    print("=" * 60)
    print("价差套利分析工具")
    print("=" * 60)

    # 1. 加载数据
    print("\n[1/5] 加载数据...")
    loader = SpreadDataLoader()
    df = loader.load(
        filepath=args.file,
        sheet_name=args.sheet,
        col_a=args.col_a,
        col_b=args.col_b,
        date_col=args.date_col,
        skip_rows=args.skip_rows,
    )
    info = loader.get_info()
    print(f"  数据量: {info['total_rows']} 行")
    print(f"  时间范围: {info['date_range']['start']} ~ {info['date_range']['end']}")
    print(f"  {args.col_a} 均值: {info['series_a']['mean']:.2f}")
    print(f"  {args.col_b} 均值: {info['series_b']['mean']:.2f}")
    print(f"  价差均值: {info['spread']['mean']:.2f}, 标准差: {info['spread']['std']:.2f}")

    # 2. 统计分析
    print("\n[2/5] 统计分析...")
    analyzer = SpreadAnalyzer(config)
    analysis = analyzer.analyze(df)
    print(f"\n  {analysis.summary}")

    # 3. 回测
    print("\n[3/5] 回测...")
    engine = SpreadBacktestEngine(config)

    backtest = engine.run_backtest(df, analysis)

    # 4. 滚动回测（可选）
    if args.rolling:
        print("\n[4/5] 滚动回测...")
        rolling_result = engine.run_rolling_backtest(df)
        summary = rolling_result.get('summary', {})
        print(f"\n  滚动回测汇总:")
        print(f"    周期数: {summary.get('total_periods', 0)}")
        print(f"    可交易周期: {summary.get('tradeable_periods', 0)}")
        print(f"    平均夏普: {summary.get('avg_sharpe', 0):.2f}")
        print(f"    平均收益: {summary.get('avg_return', 0):.2%}")
        print(f"    平均最大回撤: {summary.get('avg_max_drawdown', 0):.2%}")
    else:
        rolling_result = None
        print("\n[4/5] 滚动回测: 跳过（使用 --rolling 启用）")

    # 5. 生成报告
    print("\n[5/5] 生成报告...")
    reporter = SpreadReportGenerator(output_dir)
    result = reporter.generate(
        df=df,
        analysis=analysis,
        backtest=backtest,
        config=config,
        series_a_name=args.col_a,
        series_b_name=args.col_b,
    )

    print(f"\n{'=' * 60}")
    print(f"报告生成完成!")
    print(f"  HTML: {result['report_path']}")
    print(f"  Excel: {result['excel_path']}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
