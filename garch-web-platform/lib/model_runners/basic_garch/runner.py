#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic GARCH 模型运行器

简洁的模型调用接口，设计原则：
1. 直接调用核心模型函数（来自 lib.basic_garch_analyzer）
2. 使用 utils.data_processor 进行数据预处理
3. 使用 basic_garch_analyzer.report_generator 生成报告
4. 统一的返回格式，便于 Web 平台调用

参考：run_meg_full.py 的简洁风格
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import traceback

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 添加 lib 目录到路径，使 basic_garch_analyzer 可作为顶层模块导入
lib_dir = Path(__file__).parent.parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

# 导入核心模块
from utils.data_processor import read_excel_sheets, _clean_metadata_rows
from basic_garch_analyzer.basic_garch_model import fit_basic_garch
from basic_garch_analyzer.data_loader import load_and_preprocess, DataLoadError, ColumnNotFoundError, InsufficientDataError
from basic_garch_analyzer.config import ModelConfig


def run_basic_garch(
    data_path: str,
    sheet_name: str,
    column_mapping: dict,      # 改为接受字典
    date_range: dict = None,   # 新增参数
    skip_rows: int = 0,
    output_dir: str = None,
    model_config: dict = None  # 新增参数
) -> dict:
    """
    运行 Basic GARCH 模型分析

    设计理念：类似 run_meg_full.py 的简洁调用方式

    Parameters
    ----------
    data_path : str
        Excel 数据文件路径
    sheet_name : str
        工作表名称
    column_mapping : dict
        列映射字典，包含 'spot', 'future', 'date' 键
    date_range : dict, optional
        日期范围过滤（暂未实现）
    skip_rows : int, optional
        跳过的行数，默认为 0
    output_dir : str, optional
        输出目录（None 则自动创建）
    model_config : dict, optional
        模型配置字典，包含 p, q, corr_window, tax_rate,
        enable_rolling_backtest, n_periods, window_days, backtest_seed

    Returns
    -------
    dict
        {
            'success': bool,           # 是否成功
            'report_path': str,        # HTML 报告路径
            'summary': dict,           # 摘要信息
            'error': str               # 错误信息（失败时）
        }
    """
    # ============================================================
    # 参数提取和验证
    # ============================================================
    import os

    # 从 column_mapping 提取列名
    spot_col = column_mapping.get('spot')
    futures_col = column_mapping.get('future')
    date_col = column_mapping.get('date')

    # 从 model_config 提取模型参数（提供默认值）
    p = model_config.get('p', 1) if model_config else 1
    q = model_config.get('q', 1) if model_config else 1
    corr_window = model_config.get('corr_window', 120) if model_config else 120
    tax_rate = model_config.get('tax_rate', 0.13) if model_config else 0.13
    enable_rolling_backtest = model_config.get('enable_rolling_backtest', False) if model_config else False
    n_periods = model_config.get('n_periods', 6) if model_config else 6
    window_days = model_config.get('window_days', 90) if model_config else 90
    min_gap_days = model_config.get('min_gap_days', 180) if model_config else 180
    backtest_seed = model_config.get('backtest_seed') if model_config else None

    # 验证必要参数
    if not spot_col or not futures_col:
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': f'缺少必要列参数: spot_col={spot_col}, futures_col={futures_col}'
        }

    # 验证文件存在
    if not os.path.exists(data_path):
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': f'文件不存在: {data_path}'
        }

    try:
        print("\n" + "=" * 70)
        print(" " * 20 + "Basic GARCH 模型运行器")
        print("=" * 70)

        # ============================================================
        # 步骤 1: 数据加载和预处理
        # ============================================================
        print("\n[步骤 1/4] 数据加载和预处理")
        print("-" * 70)

        # 使用 load_and_preprocess 函数（来自 basic_garch_analyzer）
        # 这个函数会处理收益率计算、数据清洗等
        config = ModelConfig(
            p=p,
            q=q,
            corr_window=corr_window,
            tax_rate=tax_rate,
            enable_rolling_backtest=enable_rolling_backtest,
            n_periods=n_periods,
            window_days=window_days,
            backtest_seed=backtest_seed,
            output_dir=output_dir or 'outputs/web_reports'
        )

        # 计算最小数据量要求
        min_required = max(window_days * 2 if enable_rolling_backtest else 0, corr_window)

        data, selected = load_and_preprocess(
            file_path=data_path,
            date_col=date_col,
            spot_col=spot_col,
            futures_col=futures_col,
            skip_rows=skip_rows,
            output_file=None,
            interactive=False,
            min_required=min_required
        )

        print(f"\n✓ 数据加载成功")
        print(f"  样本量: {len(data)}")
        print(f"  日期范围: {data['date'].min()} ~ {data['date'].max()}")
        print(f"  现货列: {selected['spot']}")
        print(f"  期货列: {selected['futures']}")

        # ============================================================
        # 步骤 2: 拟合 Basic GARCH 模型
        # ============================================================
        print("\n[步骤 2/4] 拟合 Basic GARCH 模型")
        print("-" * 70)

        model_results = fit_basic_garch(
            data,
            p=config.p,
            q=config.q,
            corr_window=config.corr_window,
            tax_rate=config.tax_rate
        )

        print("\n✓ 模型拟合完成")

        # ============================================================
        # 步骤 3: 回测评估
        # ============================================================
        print("\n[步骤 3/4] 回测评估")
        print("-" * 70)

        if enable_rolling_backtest:
            # 滚动回测
            from lib.basic_garch_analyzer.rolling_backtest import run_rolling_backtest as _run_rolling_backtest

            print("使用滚动回测模式...")
            rolling_results = _run_rolling_backtest(
                data,
                model_results['h_final'],
                n_periods=config.n_periods,
                window_days=config.window_days,
                seed=config.backtest_seed,
                tax_rate=config.tax_rate
            )

            # 生成滚动回测报告
            from lib.basic_garch_analyzer.rolling_backtest import generate_rolling_backtest_report

            report_info = generate_rolling_backtest_report(
                data,
                rolling_results,
                config.output_dir,
                generate_html=True  # 生成 HTML 报告
            )

            # 提取摘要信息
            summary = {
                'model_name': f'Basic GARCH({p},{q}) - 滚动回测',
                'model_params': f'GARCH({p},{q})',
                'hedge_ratio_mean': float(pd.Series(model_results['h_final']).mean()),
                'hedge_ratio_std': float(pd.Series(model_results['h_final']).std()),
                'avg_return_traditional': rolling_results['avg_return_traditional'],
                'avg_return_hedged': rolling_results['avg_return_hedged'],
                'variance_reduction': rolling_results['avg_variance_reduction'],
                'avg_max_dd_traditional': rolling_results['avg_max_dd_traditional'],
                'avg_max_dd_hedged': rolling_results['avg_max_dd_hedged'],
                'n_periods': rolling_results['n_periods'],
                'window_days': config.window_days
            }

        else:
            # 全样本回测
            print("使用全样本回测模式...")
            from lib.basic_garch_analyzer.backtest_evaluator import evaluate_hedging_effectiveness

            metrics = evaluate_hedging_effectiveness(
                data,
                model_results['h_final'],
                tax_rate=config.tax_rate
            )

            # 生成报告
            from lib.basic_garch_analyzer.analyzer import evaluate_and_report

            report_info = evaluate_and_report(
                data=data,
                results=model_results,
                selected=selected,
                config=config,
                output_dir=config.output_dir
            )

            # 提取摘要信息
            summary = {
                'model_name': f'Basic GARCH({p},{q}) - 全样本回测',
                'model_params': f'GARCH({p},{q})',
                'hedge_ratio_mean': float(pd.Series(model_results['h_final']).mean()),
                'hedge_ratio_std': float(pd.Series(model_results['h_final']).std()),
                'variance_reduction': metrics['variance_reduction'],
                'ederington': metrics['ederington'],
                'sharpe_hedged': metrics['sharpe_hedged'],
                'max_dd_hedged': metrics['max_dd_hedged'],
                'rating': metrics['rating']
            }

        print("\n✓ 回测评估完成")

        # ============================================================
        # 步骤 4: 完成
        # ============================================================
        print("\n[步骤 4/4] 完成")
        print("-" * 70)

        report_path = report_info.get('html_path', config.output_dir + '/report.html')

        print(f"\n✓ 分析完成！")
        print(f"  报告路径: {report_path}")
        print(f"  套保比例均值: {summary['hedge_ratio_mean']:.4f}")
        if 'variance_reduction' in summary:
            print(f"  方差降低: {summary['variance_reduction']:.2%}")

        return {
            'success': True,
            'report_path': report_path,
            'summary': summary,
            'error': None
        }

    except InsufficientDataError as e:
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': f'数据量不足: {str(e)}',
            'error_type': 'insufficient_data'
        }
    except ColumnNotFoundError as e:
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': f'列不存在: {str(e)}',
            'error_type': 'column_not_found'
        }
    except DataLoadError as e:
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': f'数据加载失败: {str(e)}',
            'error_type': 'data_load_error'
        }
    except Exception as e:
        error_msg = f'Basic GARCH 模型运行失败: {str(e)}\n{traceback.format_exc()}'
        print(f"\n✗ {error_msg}")
        return {
            'success': False,
            'report_path': None,
            'summary': None,
            'error': error_msg,
            'error_type': 'unknown'
        }


# 测试代码
if __name__ == '__main__':
    # 测试运行器（使用新的接口）
    result = run_basic_garch(
        data_path='../../outputs/meg_full_data.xlsx',
        sheet_name=0,
        column_mapping={'spot': 'spot', 'future': 'futures', 'date': 'date'},
        model_config={
            'p': 1,
            'q': 1,
            'corr_window': 120,
            'tax_rate': 0.13,
            'enable_rolling_backtest': True,
            'n_periods': 3,
            'window_days': 90
        },
        output_dir='../../outputs/test_runner'
    )

    if result['success']:
        print(f"\n✓ 测试成功！")
        print(f"  报告: {result['report_path']}")
    else:
        print(f"\n✗ 测试失败: {result['error']}")
