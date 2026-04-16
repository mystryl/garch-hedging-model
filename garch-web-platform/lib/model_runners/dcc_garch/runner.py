#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DCC-GARCH 模型运行器

实现标准接口，完全对应 basic_garch/runner.py 的结构
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import traceback
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 添加 lib 目录到路径
lib_dir = Path(__file__).parent.parent.parent
if str(lib_dir) not in sys.path:
    sys.path.insert(0, str(lib_dir))

# 导入核心模块
from basic_garch_analyzer.data_loader import load_and_preprocess, DataLoadError, ColumnNotFoundError, InsufficientDataError
from basic_garch_analyzer.config import ModelConfig
from .dcc_model import fit_dcc_garch_model
from .report_generator import generate_dcc_garch_report


def run_dcc_garch(
    data_path: str,
    sheet_name: str,
    column_mapping: dict,
    date_range: dict = None,
    skip_rows: int = 0,
    output_dir: str = None,
    model_config: dict = None
) -> dict:
    """
    运行 DCC-GARCH 模型分析

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
        模型配置字典，包含 p, q, dist, tax_rate,
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

    # 从 column_mapping 提取列名
    spot_col = column_mapping.get('spot')
    futures_col = column_mapping.get('future')
    date_col = column_mapping.get('date')

    # 从 model_config 提取模型参数（提供默认值）
    p = model_config.get('p', 1) if model_config else 1
    q = model_config.get('q', 1) if model_config else 1
    dist = model_config.get('dist', 'norm') if model_config else 'norm'
    tax_rate = model_config.get('tax_rate', 0.13) if model_config else 0.13
    enable_rolling_backtest = model_config.get('enable_rolling_backtest', False) if model_config else False
    n_periods = model_config.get('n_periods', 6) if model_config else 6
    window_days = model_config.get('window_days', 90) if model_config else 90
    min_gap_days = model_config.get('min_gap_days', 180) if model_config else 180
    backtest_seed = model_config.get('backtest_seed') if model_config else None
    restrict_to_recent_months = model_config.get('restrict_to_recent_months', False) if model_config else False

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
        print(" " * 20 + "DCC-GARCH 模型运行器")
        print("=" * 70)

        # 验证 dist 参数
        if dist not in ['norm', 't']:
            return {
                'success': False,
                'report_path': None,
                'summary': None,
                'error': f'无效的分布假设: {dist}，必须是 "norm" 或 "t"'
            }

        # ============================================================
        # 步骤 1: 数据加载和预处理
        # ============================================================
        print("\n[步骤 1/4] 数据加载和预处理")
        print("-" * 70)

        # 使用 load_and_preprocess 函数（来自 basic_garch_analyzer）
        # 注意：ModelConfig 不支持 dist 参数，我们在后续直接使用 dist
        config = ModelConfig(
            p=p,
            q=q,
            tax_rate=tax_rate,
            enable_rolling_backtest=enable_rolling_backtest,
            n_periods=n_periods,
            window_days=window_days,
            backtest_seed=backtest_seed,
            output_dir=output_dir or 'outputs/web_reports'
        )

        # DCC-GARCH 需要至少 150 天的数据
        min_required = max(window_days * 2 if enable_rolling_backtest else 0, 150)

        data, selected = load_and_preprocess(
            file_path=data_path,
            sheet_name=sheet_name,
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
        # 步骤 2: 拟合 DCC-GARCH 模型
        # ============================================================
        print("\n[步骤 2/4] 拟合 DCC-GARCH 模型")
        print("-" * 70)

        model_results = fit_dcc_garch_model(
            data=data,
            p=config.p,
            q=config.q,
            dist=dist,
            output_dir=config.output_dir
        )

        print("\n✓ 模型拟合完成")

        # 保存每日套保比例数据（与 Basic GARCH 保持一致）
        h_csv_path = os.path.join(config.output_dir, 'h_dcc_garch.csv')
        daily_h_df = pd.DataFrame({
            'date': data['date'].values,
            'spot': data['spot'].values,
            'futures': data['futures'].values,
            'spread': data['spread'].values,
            'h_theoretical': model_results['h_theoretical'],
            'h_actual': model_results['h_actual'],
            'hedge_ratio': model_results['hedge_ratio'],
            'rho_t': model_results['rho_t'],
            'sigma_s': model_results['sigma_s'],
            'sigma_f': model_results['sigma_f']
        })
        daily_h_df.to_csv(h_csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ 已保存每日套保比例: {h_csv_path}")

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
                model_results['h_actual'],
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
                'model_name': f'DCC-GARCH({p},{q}) - 滚动回测',
                'model_params': f'DCC-GARCH({p},{q}), dist={dist}',
                'hedge_ratio_mean': float(pd.Series(model_results['h_actual']).mean()),
                'hedge_ratio_std': float(pd.Series(model_results['h_actual']).std()),
                'correlation_mean': float(pd.Series(model_results['rho_t']).mean()),
                'correlation_std': float(pd.Series(model_results['rho_t']).std()),
                'avg_return_traditional': rolling_results['avg_return_traditional'],
                'avg_return_hedged': rolling_results['avg_return_hedged'],
                'variance_reduction': rolling_results['avg_variance_reduction'],
                'avg_max_dd_traditional': rolling_results['avg_max_dd_traditional'],
                'avg_max_dd_hedged': rolling_results['avg_max_dd_hedged'],
                'n_periods': rolling_results['n_periods'],
                'window_days': config.window_days,
                'dist': dist
            }

        else:
            # 全样本回测
            print("使用全样本回测模式...")
            from lib.basic_garch_analyzer.backtest_evaluator import evaluate_hedging_effectiveness

            # 计算回测指标
            metrics = evaluate_hedging_effectiveness(
                data,
                model_results['h_actual'],
                tax_rate=config.tax_rate
            )

            # 准备评估结果字典（用于绘图函数）
            print("\n准备图表数据...")
            import numpy as np

            # 对齐数据长度
            min_len = min(len(data), len(model_results['h_actual']))
            data_aligned = data.iloc[:min_len].copy()
            h_aligned = model_results['h_actual'][:min_len]

            # 计算套保后收益率（考虑税点调整）
            r_hedged = data_aligned['r_s'].values / (1 + config.tax_rate) - h_aligned * data_aligned['r_f'].values
            r_unhedged = data_aligned['r_s'].values / (1 + config.tax_rate) - 1.0 * data_aligned['r_f'].values

            # 计算累计收益率
            cumulative_hedged = np.cumprod(1 + r_hedged)
            cumulative_unhedged = np.cumprod(1 + r_unhedged)

            # 计算回撤序列
            running_max_h = np.maximum.accumulate(cumulative_hedged)
            drawdown_series = (cumulative_hedged - running_max_h) / running_max_h

            # 构建评估结果字典
            eval_results = {
                'metrics': metrics,
                'returns_unhedged': r_unhedged,
                'returns_hedged': r_hedged,
                'drawdown_series': drawdown_series,
                'start_date': data_aligned['date'].min(),
                'end_date': data_aligned['date'].max(),
            }

            # 生成报告
            report_info = generate_dcc_garch_report(
                data=data_aligned,
                model_results=model_results,
                eval_results=eval_results,
                selected=selected,
                config=config,
                output_dir=config.output_dir,
                restrict_to_recent_months=restrict_to_recent_months
            )

            # 提取摘要信息
            summary = {
                'model_name': f'DCC-GARCH({p},{q}) - 全样本回测',
                'model_params': f'DCC-GARCH({p},{q}), dist={dist}',
                'hedge_ratio_mean': float(pd.Series(model_results['h_actual']).mean()),
                'hedge_ratio_std': float(pd.Series(model_results['h_actual']).std()),
                'correlation_mean': float(pd.Series(model_results['rho_t']).mean()),
                'correlation_std': float(pd.Series(model_results['rho_t']).std()),
                'variance_reduction': metrics['variance_reduction'],
                'ederington': metrics['ederington'],
                'sharpe_hedged': metrics['sharpe_hedged'],
                'max_dd_hedged': metrics['max_dd_hedged'],
                'rating': metrics['rating'],
                'dist': dist
            }

        print("\n✓ 回测评估完成")

        # ============================================================
        # 步骤 4: 完成
        # ============================================================
        print("\n[步骤 4/4] 完成")
        print("-" * 70)

        report_path = report_info.get('html_path', config.output_dir + '/report.html')
        csv_path = report_info.get('csv_path')
        excel_path = report_info.get('excel_path')

        print(f"\n✓ 分析完成！")
        print(f"  报告路径: {report_path}")
        if csv_path:
            print(f"  CSV报告: {csv_path}")
        if excel_path:
            print(f"  Excel报告: {excel_path}")
        print(f"  套保比例均值: {summary['hedge_ratio_mean']:.4f}")
        print(f"  动态相关系数均值: {summary['correlation_mean']:.4f}")
        if 'variance_reduction' in summary:
            print(f"  方差降低: {summary['variance_reduction']:.2%}")

        return {
            'success': True,
            'report_path': report_path,
            'csv_path': csv_path,
            'excel_path': excel_path,
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
        error_msg = f'DCC-GARCH 模型运行失败: {str(e)}\n{traceback.format_exc()}'
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
    # 测试运行器
    result = run_dcc_garch(
        data_path='../../outputs/meg_full_data.xlsx',
        sheet_name=0,
        column_mapping={'spot': 'spot', 'future': 'futures', 'date': 'date'},
        model_config={
            'p': 1,
            'q': 1,
            'dist': 'norm',
            'tax_rate': 0.13
        },
        output_dir='../../outputs/test_dcc_garch'
    )

    if result['success']:
        print(f"\n✓ 测试成功！")
        print(f"  报告: {result['report_path']}")
    else:
        print(f"\n✗ 测试失败: {result['error']}")
