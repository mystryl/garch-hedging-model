# Basic GARCH Analyzer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 basic_garch_analyzer 改造为独立的命令行工具和 Python 库，支持一键生成完整的套保分析报告

**Architecture:** 最小重构方案 - 添加配置模块、合并回测评估与报告生成、创建命令行入口

**Tech Stack:** Python 3.7+, pandas, numpy, matplotlib, arch (GARCH), argparse, dataclasses

---

## Task 1: 创建配置模块 (config.py)

**Files:**
- Create: `basic_garch_analyzer/config.py`

**Step 1: 创建配置文件骨架**

```python
"""
Basic GARCH Analyzer 配置模块
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelConfig:
    """
    GARCH 模型配置参数

    默认值基于学术文献和实际应用经验
    """
    # GARCH 模型参数
    p: int = 1
    q: int = 1
    mean_model: str = 'Constant'
    vol_model: str = 'GARCH'
    distribution: str = 'normal'

    # 套保参数
    corr_window: int = 120  # 动态相关系数滚动窗口（约4个月交易日）
    tax_rate: float = 0.13  # 增值税率（用于调整套保比例）

    # 输出配置
    output_dir: str = 'outputs'
    save_intermediate: bool = True

    def __post_init__(self):
        """验证参数合理性"""
        if self.p < 1 or self.q < 1:
            raise ValueError(f"GARCH阶数必须 >= 1, 得到 p={self.p}, q={self.q}")

        if self.corr_window < 30:
            raise ValueError(f"相关系数窗口至少30天, 得到 {self.corr_window}")

        if not 0 <= self.tax_rate <= 1:
            raise ValueError(f"税率必须在[0,1]之间, 得到 {self.tax_rate}")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'GARCH(p,q)': f'({self.p}, {self.q})',
            '相关系数窗口': f'{self.corr_window}天',
            '税点调整': f'{self.tax_rate:.1%}',
        }


def create_config(**kwargs) -> ModelConfig:
    """
    创建配置对象的工厂函数

    Parameters:
    -----------
    **kwargs: 配置参数覆盖

    Returns:
    --------
    ModelConfig: 配置对象

    Example:
    --------
    >>> config = create_config(p=2, tax_rate=0.0)
    >>> print(config.to_dict())
    """
    return ModelConfig(**kwargs)
```

**Step 2: 验证语法**

```bash
cd /Users/mystryl/Documents/GARCH\ 模型套保方案
python -c "from basic_garch_analyzer.config import ModelConfig; print('Import OK')"
```

Expected: `Import OK`

**Step 3: 提交**

```bash
git add basic_garch_analyzer/config.py
git commit -m "feat: 添加 ModelConfig 配置类"
```

---

## Task 2: 创建核心分析器模块 (analyzer.py)

**Files:**
- Create: `basic_garch_analyzer/analyzer.py`

**Step 1: 创建分析器骨架（合并回测评估和报告生成）**

```python
"""
核心分析器模块
合并回测评估和报告生成功能
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style('whitegrid')

# 导入现有模块的函数
from basic_garch_analyzer.backtest_evaluator import (
    calculate_max_drawdown,
    evaluate_hedging_effectiveness
)
from basic_garch_analyzer.report_generator import (
    plot_price_series,
    plot_returns,
    plot_hedge_ratio,
    plot_volatility,
    plot_backtest_results,
    plot_drawdown,
    plot_performance_metrics,
    plot_summary_table,
    generate_html_report
)


def evaluate_and_report(
    data: pd.DataFrame,
    results: dict,
    selected: dict,
    config,
    output_dir: str = 'outputs'
) -> dict:
    """
    执行回测评估并生成完整报告

    Parameters:
    -----------
    data : pd.DataFrame
        包含 date, spot, futures, r_s, r_f, spread 的数据
    results : dict
        模型拟合结果（来自 fit_basic_garch）
    selected : dict
        列名配置 {'date': str, 'spot': str, 'futures': str}
    config : ModelConfig
        模型配置对象
    output_dir : str
        输出目录路径

    Returns:
    --------
    report_info : dict
        报告信息字典
        {
            'metrics': dict,           # 评估指标
            'figures': list,           # 图表路径列表
            'html_path': str,          # HTML报告路径
            'csv_path': str,           # CSV报告路径
            'output_dir': str          # 输出目录
        }
    """
    print("\n" + "=" * 60)
    print("回测评估与报告生成")
    print("=" * 60)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)
    model_results_dir = os.path.join(output_dir, 'model_results')
    os.makedirs(model_results_dir, exist_ok=True)

    # ===== 1. 计算回测指标 =====
    print("\n[1/5] 计算回测指标...")
    metrics = evaluate_hedging_effectiveness(
        data,
        results['h_final'],
        tax_rate=config.tax_rate
    )

    # ===== 2. 准备评估结果字典（用于绘图函数）=====
    print("\n[2/5] 准备图表数据...")

    # 对齐数据长度
    min_len = min(len(data), len(results['h_final']))
    data_aligned = data.iloc[:min_len].copy()
    h_aligned = results['h_final'][:min_len]

    # 计算套保后收益率
    r_hedged = data_aligned['r_s'].values - h_aligned * data_aligned['r_f'].values
    r_unhedged = data_aligned['r_s'].values

    # 计算累计收益率
    cumulative_unhedged = np.cumprod(1 + r_unhedged)
    cumulative_hedged = np.cumprod(1 + r_hedged)

    # 计算回撤序列
    running_max_h = np.maximum.accumulate(cumulative_hedged)
    drawdown_series = (cumulative_hedged - running_max_h) / running_max_h

    eval_results = {
        'metrics': metrics,
        'returns_unhedged': r_unhedged,
        'returns_hedged': r_hedged,
        'drawdown_series': drawdown_series,
        'start_date': data_aligned['date'].min(),
        'end_date': data_aligned['date'].max(),
    }

    # ===== 3. 生成8张图表 =====
    print("\n[3/5] 生成可视化图表...")

    figure_paths = []

    # 图1: 价格走势
    path = os.path.join(figures_dir, '1_price_series.png')
    plot_price_series(data_aligned, path)
    figure_paths.append(path)

    # 图2: 收益率分布
    path = os.path.join(figures_dir, '2_returns.png')
    plot_returns(data_aligned, path)
    figure_paths.append(path)

    # 图3: 套保比例
    path = os.path.join(figures_dir, '3_hedge_ratio.png')
    plot_hedge_ratio(data_aligned, results, path)
    figure_paths.append(path)

    # 图4: 波动率与相关性
    path = os.path.join(figures_dir, '4_volatility.png')
    plot_volatility(data_aligned, results, path)
    figure_paths.append(path)

    # 图5: 回测净值曲线
    path = os.path.join(figures_dir, '5_backtest_results.png')
    plot_backtest_results(data_aligned, eval_results, path)
    figure_paths.append(path)

    # 图6: 回撤曲线
    path = os.path.join(figures_dir, '6_drawdown.png')
    plot_drawdown(data_aligned, eval_results, path)
    figure_paths.append(path)

    # 图7: 性能指标对比
    path = os.path.join(figures_dir, '7_performance_metrics.png')
    plot_performance_metrics(eval_results, path)
    figure_paths.append(path)

    # 图8: 汇总表格
    path = os.path.join(figures_dir, '8_summary_table.png')
    plot_summary_table(eval_results, selected, results, path)
    figure_paths.append(path)

    print(f"✓ 已生成 {len(figure_paths)} 张图表")

    # ===== 4. 生成 CSV/Excel 报告 =====
    print("\n[4/5] 生成表格报告...")

    # 创建报告 DataFrame
    report_data = {
        '指标': [
            '总收益率 (未套保)',
            '总收益率 (套保后)',
            '年化收益率 (未套保)',
            '年化收益率 (套保后)',
            '波动率 (未套保)',
            '波动率 (套保后)',
            '最大回撤 (未套保)',
            '最大回撤 (套保后)',
            '夏普比率 (未套保)',
            '夏普比率 (套保后)',
            'VaR 95% (未套保)',
            'VaR 95% (套保后)',
            'CVaR 95% (未套保)',
            'CVaR 95% (套保后)',
            '方差降低比例',
            'Ederington 指标',
            '套保效果评级'
        ],
        '数值': [
            f"{metrics['total_return_unhedged']:.2%}",
            f"{metrics['total_return_hedged']:.2%}",
            f"{metrics['annual_return_unhedged']:.2%}",
            f"{metrics['annual_return_hedged']:.2%}",
            f"{metrics['std_unhedged']:.4f}",
            f"{metrics['std_hedged']:.4f}",
            f"{metrics['max_dd_unhedged']:.2%}",
            f"{metrics['max_dd_hedged']:.2%}",
            f"{metrics['sharpe_unhedged']:.4f}",
            f"{metrics['sharpe_hedged']:.4f}",
            f"{metrics['var_95_unhedged']:.4f}",
            f"{metrics['var_95_hedged']:.4f}",
            f"{metrics['cvar_95_unhedged']:.4f}",
            f"{metrics['cvar_95_hedged']:.4f}",
            f"{metrics['variance_reduction']:.2%}",
            f"{metrics['ederington']:.4f}",
            metrics['rating']
        ]
    }

    report_df = pd.DataFrame(report_data)

    # 保存 CSV
    csv_path = os.path.join(output_dir, 'backtest_report.csv')
    report_df.to_csv(csv_path, index=False, encoding='utf-8-sig')

    # 保存 Excel（多工作表）
    excel_path = os.path.join(output_dir, 'backtest_report.xlsx')
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        report_df.to_excel(writer, sheet_name='回测报告', index=False)

        # 配置信息工作表
        summary_data = {
            '项目': ['数据起止日期', '样本量', '相关系数窗口', '税点调整'],
            '数值': [
                f"{data['date'].min()} 至 {data['date'].max()}",
                len(data),
                config.corr_window,
                f"{config.tax_rate:.1%}"
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='配置信息', index=False)

        # GARCH 参数工作表
        if 'params_spot' in results and 'params_futures' in results:
            spot_params = pd.DataFrame(list(results['params_spot'].items()),
                                      columns=['参数', '现货'])
            futures_params = pd.DataFrame(list(results['params_futures'].items()),
                                         columns=['参数', '期货'])
            pd.merge(spot_params, futures_params, on='参数', how='outer').to_excel(
                writer, sheet_name='GARCH参数', index=False
            )

    print(f"✓ CSV报告: {csv_path}")
    print(f"✓ Excel报告: {excel_path}")

    # ===== 5. 生成 HTML 报告 =====
    print("\n[5/5] 生成 HTML 报告...")

    html_path = os.path.join(output_dir, 'report.html')
    generate_html_report(data_aligned, eval_results, selected, results, html_path)

    print(f"✓ HTML报告: {html_path}")

    # ===== 汇总返回 =====
    print("\n" + "=" * 60)
    print("✓ 报告生成完成！")
    print("=" * 60)
    print(f"\n📁 输出目录: {output_dir}")
    print(f"  - {html_path}  ⭐ (推荐查看)")
    print(f"  - {figures_dir}/ (所有图表)")
    print(f"  - {csv_path}")
    print(f"  - {excel_path}")

    return {
        'metrics': metrics,
        'figures': figure_paths,
        'html_path': html_path,
        'csv_path': csv_path,
        'excel_path': excel_path,
        'output_dir': output_dir
    }
```

**Step 2: 验证导入**

```bash
python -c "from basic_garch_analyzer.analyzer import evaluate_and_report; print('Import OK')"
```

Expected: `Import OK` (可能会有 matplotlib 警告，忽略)

**Step 3: 提交**

```bash
git add basic_garch_analyzer/analyzer.py
git commit -m "feat: 添加核心分析器模块（合并评估+报告）"
```

---

## Task 3: 创建包初始化文件 (__init__.py)

**Files:**
- Create: `basic_garch_analyzer/__init__.py`

**Step 1: 编写包初始化代码**

```python
"""
Basic GARCH Analyzer - GARCH套保模型分析工具

支持：
- 作为Python库导入使用
- 作为命令行工具运行
- 自动生成完整的回测分析报告

Example:
--------
作为库使用:
    >>> from basic_garch_analyzer import run_analysis
    >>> result = run_analysis('data.xlsx', '现货价格', '期货价格')

命令行使用:
    $ python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格
"""
from basic_garch_analyzer.config import ModelConfig, create_config
from basic_garch_analyzer.data_loader import load_and_preprocess
from basic_garch_analyzer.basic_garch_model import fit_basic_garch, save_model_results
from basic_garch_analyzer.analyzer import evaluate_and_report

__version__ = '1.0.0'
__all__ = [
    'ModelConfig',
    'create_config',
    'load_and_preprocess',
    'fit_basic_garch',
    'save_model_results',
    'evaluate_and_report',
    'run_analysis'
]


def run_analysis(
    excel_path: str,
    spot_col: str,
    futures_col: str,
    date_col: str = None,
    config: ModelConfig = None,
    interactive: bool = False,
    **kwargs
) -> dict:
    """
    一键运行完整分析流程

    Parameters:
    -----------
    excel_path : str
        Excel 文件路径
    spot_col : str
        现货价格列名
    futures_col : str
        期货价格列名
    date_col : str, optional
        日期列名（None则自动检测）
    config : ModelConfig, optional
        模型配置对象（None则使用默认配置）
    interactive : bool
        是否交互式选择列名
    **kwargs
        其他配置参数（用于覆盖 config）

    Returns:
    --------
    result : dict
        {
            'data': DataFrame,           # 预处理后的数据
            'model_results': dict,       # 模型拟合结果
            'report_info': dict          # 报告信息
        }

    Example:
    --------
    >>> # 使用默认配置
    >>> result = run_analysis('data.xlsx', '现货', '期货')
    >>>
    >>> # 自定义配置
    >>> config = ModelConfig(tax_rate=0.0, corr_window=60)
    >>> result = run_analysis('data.xlsx', '现货', '期货', config=config)
    """
    print("\n" + "=" * 70)
    print(" " * 15 + "Basic GARCH Analyzer")
    print(" " * 10 + "套保策略回测分析系统")
    print("=" * 70)

    # 1. 准备配置
    if config is None:
        config = ModelConfig(**kwargs)
    else:
        # 合并 kwargs 覆盖
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

    print("\n📋 配置参数:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")

    # 2. 加载和预处理数据
    print("\n" + "=" * 70)
    data, selected = load_and_preprocess(
        file_path=excel_path,
        date_col=date_col,
        spot_col=spot_col,
        futures_col=futures_col,
        output_file=None,
        interactive=interactive
    )

    # 3. 拟合 GARCH 模型
    print("\n" + "=" * 70)
    model_results = fit_basic_garch(
        data,
        p=config.p,
        q=config.q,
        corr_window=config.corr_window,
        tax_rate=config.tax_rate
    )

    # 保存模型结果
    model_results_path = f"{config.output_dir}/model_results/h_basic_garch.csv"
    save_model_results(data, model_results, model_results_path)

    # 4. 评估和生成报告
    print("\n" + "=" * 70)
    report_info = evaluate_and_report(
        data=data,
        results=model_results,
        selected=selected,
        config=config,
        output_dir=config.output_dir
    )

    # 5. 输出摘要
    print("\n" + "=" * 70)
    print(" " * 20 + "分析完成")
    print("=" * 70)

    metrics = report_info['metrics']
    print(f"\n核心结果:")
    print(f"  方差降低比例: {metrics['variance_reduction']:.2%}")
    print(f"  夏普比率 (套保后): {metrics['sharpe_hedged']:.4f}")
    print(f"  最大回撤 (套保后): {metrics['max_dd_hedged']:.2%}")
    print(f"  套保效果评级: {metrics['rating']}")

    return {
        'data': data,
        'selected': selected,
        'model_results': model_results,
        'report_info': report_info,
        'config': config
    }
```

**Step 2: 验证导入**

```bash
python -c "from basic_garch_analyzer import run_analysis; print('Import OK')"
```

Expected: `Import OK`

**Step 3: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "feat: 添加包初始化和 run_analysis 一键运行函数"
```

---

## Task 4: 创建命令行入口 (main.py)

**Files:**
- Create: `basic_garch_analyzer/main.py`

**Step 1: 编写命令行入口代码**

```python
"""
Basic GARCH Analyzer 命令行入口

Usage:
    python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

    python -m basic_garch_analyzer --data data.xlsx --interactive
"""
import argparse
import sys
from pathlib import Path
from basic_garch_analyzer import run_analysis, ModelConfig


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Basic GARCH 套保策略回测分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用
  python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

  # 自定义参数
  python -m basic_garch_analyzer --data data.xlsx --spot 现货 --futures 期货 --tax-rate 0.0

  # 交互模式
  python -m basic_garch_analyzer --data data.xlsx --interactive

  # 指定工作表
  python -m basic_garch_analyzer --data data.xlsx --spot 现货 --futures 期货 --sheet "数据"
        """
    )

    # 必需参数
    parser.add_argument(
        '--data', '-d',
        required=True,
        help='Excel数据文件路径'
    )

    # 交互模式
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互式选择列名（无需指定 --spot 和 --futures）'
    )

    # 列名参数
    parser.add_argument(
        '--spot',
        help='现货价格列名'
    )
    parser.add_argument(
        '--futures',
        help='期货价格列名'
    )
    parser.add_argument(
        '--date-col',
        help='日期列名（默认自动检测）'
    )
    parser.add_argument(
        '--sheet',
        default=0,
        help='工作表名或索引（默认: 0）'
    )

    # GARCH 模型参数
    parser.add_argument(
        '--p',
        type=int,
        default=1,
        help='GARCH(p,q) 的 p 阶数（默认: 1）'
    )
    parser.add_argument(
        '--q',
        type=int,
        default=1,
        help='GARCH(p,q) 的 q 阶数（默认: 1）'
    )

    # 套保参数
    parser.add_argument(
        '--corr-window',
        type=int,
        default=120,
        help='动态相关系数滚动窗口大小，单位天（默认: 120）'
    )
    parser.add_argument(
        '--tax-rate',
        type=float,
        default=0.13,
        help='税点调整比例（默认: 0.13）'
    )

    # 输出配置
    parser.add_argument(
        '--output-dir', '-o',
        default='outputs',
        help='输出目录路径（默认: outputs）'
    )

    return parser.parse_args()


def validate_args(args):
    """验证参数"""
    # 检查文件存在性
    if not Path(args.data).exists():
        print(f"❌ 错误: 文件不存在 - {args.data}")
        sys.exit(1)

    # 交互模式不需要指定列名
    if not args.interactive:
        if not args.spot:
            print("❌ 错误: 非交互模式必须指定 --spot 参数")
            sys.exit(1)
        if not args.futures:
            print("❌ 错误: 非交互模式必须指定 --futures 参数")
            sys.exit(1)

    # 验证数值参数
    if args.p < 1 or args.q < 1:
        print(f"❌ 错误: GARCH阶数必须 >= 1")
        sys.exit(1)

    if args.corr_window < 30:
        print(f"❌ 错误: 相关系数窗口至少30天")
        sys.exit(1)

    if not 0 <= args.tax_rate <= 1:
        print(f"❌ 错误: 税率必须在[0,1]之间")
        sys.exit(1)


def main():
    """主入口函数"""
    # 解析参数
    args = parse_args()

    # 验证参数
    validate_args(args)

    # 创建配置对象
    config = ModelConfig(
        p=args.p,
        q=args.q,
        corr_window=args.corr_window,
        tax_rate=args.tax_rate,
        output_dir=args.output_dir
    )

    # 运行分析
    try:
        result = run_analysis(
            excel_path=args.data,
            spot_col=args.spot,
            futures_col=args.futures,
            date_col=args.date_col,
            config=config,
            interactive=args.interactive
        )

        # 输出报告路径
        print(f"\n" + "=" * 70)
        print("📊 报告已生成:")
        print(f"  HTML: {result['report_info']['html_path']}")
        print(f"  CSV:  {result['report_info']['csv_path']}")
        print("=" * 70)

        return 0

    except FileNotFoundError as e:
        print(f"❌ 文件错误: {e}")
        return 1
    except ValueError as e:
        print(f"❌ 数据错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
```

**Step 2: 测试帮助信息**

```bash
python -m basic_garch_analyzer --help
```

Expected: 显示完整的帮助信息

**Step 3: 提交**

```bash
git add basic_garch_analyzer/main.py
git commit -m "feat: 添加命令行入口 main.py"
```

---

## Task 5: 创建 utils 工具模块（可选）

**Files:**
- Create: `basic_garch_analyzer/utils/__init__.py`

**Step 1: 创建工具模块骨架**

```python
"""
工具函数模块
"""
from basic_garch_analyzer.utils.helpers import format_number, print_summary


def format_number(value, format_type='percent'):
    """
    格式化数字显示

    Parameters:
    -----------
    value : float
        数值
    format_type : str
        格式类型: 'percent', 'float', 'int'

    Returns:
    --------
    str : 格式化后的字符串
    """
    if format_type == 'percent':
        return f"{value:.2%}"
    elif format_type == 'float':
        return f"{value:.4f}"
    elif format_type == 'int':
        return f"{int(value)}"
    else:
        return str(value)


def print_summary(metrics, title="分析摘要"):
    """
    打印分析结果摘要

    Parameters:
    -----------
    metrics : dict
        评估指标字典
    title : str
        标题
    """
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

    key_metrics = [
        ('方差降低比例', 'variance_reduction', 'percent'),
        ('夏普比率 (套保后)', 'sharpe_hedged', 'float'),
        ('最大回撤 (套保后)', 'max_dd_hedged', 'percent'),
        ('年化收益率 (套保后)', 'annual_return_hedged', 'percent'),
    ]

    for label, key, fmt in key_metrics:
        if key in metrics:
            print(f"  {label}: {format_number(metrics[key], fmt)}")

    print("=" * 60)
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/utils/
git commit -m "feat: 添加工具函数模块"
```

---

## Task 6: 添加错误处理增强

**Files:**
- Modify: `basic_garch_analyzer/analyzer.py`
- Modify: `basic_garch_analyzer/data_loader.py`

**Step 1: 在 analyzer.py 添加错误处理**

在文件开头添加：

```python
# 自定义异常
class AnalyzerError(Exception):
    """分析器基础异常"""
    pass


class ReportGenerationError(AnalyzerError):
    """报告生成失败"""
    pass
```

在 `evaluate_and_report` 函数开头添加：

```python
# 输入验证
if data.empty:
    raise ReportGenerationError("数据为空")

if 'h_final' not in results:
    raise ReportGenerationError("模型结果中缺少套保比例")

required_columns = ['date', 'spot', 'futures', 'r_s', 'r_f', 'spread']
missing_cols = [col for col in required_columns if col not in data.columns]
if missing_cols:
    raise ReportGenerationError(f"数据缺少必需列: {missing_cols}")
```

**Step 2: 在 data_loader.py 添加错误处理**

在文件开头添加：

```python
# 自定义异常
class DataLoadError(Exception):
    """数据加载基础异常"""
    pass


class ColumnNotFoundError(DataLoadError):
    """列不存在错误"""
    pass


class InsufficientDataError(DataLoadError):
    """数据量不足错误"""
    pass
```

在 `preprocess_data` 函数末尾添加：

```python
# 数据量验证
min_required = 120  # 至少120天数据
if len(data) < min_required:
    raise InsufficientDataError(
        f"数据量不足: 需要 >= {min_required} 天, 实际 {len(data)} 天"
    )
```

**Step 3: 提交**

```bash
git add basic_garch_analyzer/analyzer.py basic_garch_analyzer/data_loader.py
git commit -m "feat: 添加错误处理和数据验证"
```

---

## Task 7: 创建示例配置文件（可选）

**Files:**
- Create: `basic_garch_analyzer/config_example.py`

**Step 1: 创建示例配置**

```python
"""
配置示例文件

演示如何创建和使用自定义配置
"""
from basic_garch_analyzer import ModelConfig

# 示例1: 默认配置
config_default = ModelConfig()

# 示例2: 无税点调整
config_no_tax = ModelConfig(tax_rate=0.0)

# 示例3: 短窗口相关系数
config_short_window = ModelConfig(corr_window=60)

# 示例4: GARCH(2,1) 模型
config_garch_21 = ModelConfig(p=2, q=1)

# 示例5: 完全自定义
config_custom = ModelConfig(
    p=1,
    q=1,
    corr_window=90,
    tax_rate=0.0,
    output_dir='my_outputs'
)

# 使用示例
if __name__ == '__main__':
    from basic_garch_analyzer import run_analysis

    # 使用自定义配置
    result = run_analysis(
        excel_path='data.xlsx',
        spot_col='现货价格',
        futures_col='期货价格',
        config=config_no_tax
    )
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/config_example.py
git commit -m "docs: 添加配置示例文件"
```

---

## Task 8: 创建使用文档

**Files:**
- Create: `basic_garch_analyzer/README.md`

**Step 1: 编写使用文档**

```markdown
# Basic GARCH Analyzer

GARCH(1,1) 套保模型分析工具，支持命令行和 Python 库两种使用方式。

## 功能特点

- ✅ 自动数据加载和预处理
- ✅ GARCH(1,1) 模型拟合
- ✅ 动态套保比例计算
- ✅ 完整的回测评估指标
- ✅ 自动生成图表和报告
- ✅ 支持交互式列名选择
- ✅ 灵活的参数配置

## 安装依赖

\`\`\`bash
pip install pandas numpy matplotlib arch openpyxl
\`\`\`

## 使用方法

### 方式1: 命令行

\`\`\`bash
# 基本使用
python -m basic_garch_analyzer \\
    --data data.xlsx \\
    --spot 现货价格 \\
    --futures 期货价格

# 自定义参数
python -m basic_garch_analyzer \\
    --data data.xlsx \\
    --spot 现货 \\
    --futures 期货 \\
    --tax-rate 0.0 \\
    --corr-window 60

# 交互模式
python -m basic_garch_analyzer \\
    --data data.xlsx \\
    --interactive
\`\`\`

### 方式2: Python 库

\`\`\`python
from basic_garch_analyzer import run_analysis, ModelConfig

# 使用默认配置
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格'
)

# 自定义配置
config = ModelConfig(
    corr_window=60,
    tax_rate=0.0
)
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格',
    config=config
)
\`\`\`

## 输出文件

运行后会在输出目录（默认 `outputs/`）生成：

- `report.html` - HTML 格式的完整报告（推荐查看）
- `backtest_report.csv` - CSV 格式的指标表格
- `backtest_report.xlsx` - Excel 格式的多工作表报告
- `figures/` - 8 张可视化图表
- `model_results/` - 模型拟合结果数据

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--data` | Excel文件路径 | - (必需) |
| `--spot` | 现货列名 | - (非交互模式必需) |
| `--futures` | 期货列名 | - (非交互模式必需) |
| `--date-col` | 日期列名 | 自动检测 |
| `--sheet` | 工作表名/索引 | 0 |
| `--p` | GARCH p 阶数 | 1 |
| `--q` | GARCH q 阶数 | 1 |
| `--corr-window` | 相关系数窗口 | 120 |
| `--tax-rate` | 税点调整比例 | 0.13 |
| `--output-dir` | 输出目录 | outputs |
| `--interactive` | 交互式选择列 | False |

## 配置参数

\`\`\`python
from basic_garch_analyzer import ModelConfig

config = ModelConfig(
    # GARCH 模型参数
    p=1,                    # GARCH p 阶数
    q=1,                    # GARCH q 阶数
    mean_model='Constant',  # 均值模型
    vol_model='GARCH',      # 波动率模型
    distribution='normal',  # 分布假设

    # 套保参数
    corr_window=120,        # 动态相关系数窗口（天）
    tax_rate=0.13,          # 税点调整比例

    # 输出配置
    output_dir='outputs',   # 输出目录
    save_intermediate=True  # 保存中间结果
)
\`\`\`

## 示例

详细示例请参考 `config_example.py`
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/README.md
git commit -m "docs: 添加使用文档"
```

---

## Task 9: 集成测试

**Files:**
- Create: `test_analyzer_integration.py` (在项目根目录)

**Step 1: 创建集成测试脚本**

```python
"""
Basic GARCH Analyzer 集成测试
测试完整分析流程
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from basic_garch_analyzer import run_analysis, ModelConfig


def test_run_analysis():
    """测试完整分析流程"""
    print("\n" + "=" * 60)
    print("集成测试: Basic GARCH Analyzer")
    print("=" * 60)

    # 测试1: 使用项目现有数据
    print("\n[测试1] 使用现有数据文件...")

    data_file = "outputs/preprocessed_data.xlsx"

    if not os.path.exists(data_file):
        print(f"⚠️  测试数据不存在: {data_file}")
        print("   请先运行主程序生成测试数据")
        return False

    try:
        result = run_analysis(
            excel_path=data_file,
            spot_col='spot',
            futures_col='futures',
            config=ModelConfig(
                output_dir='outputs/test'
            )
        )

        # 验证输出
        assert 'data' in result
        assert 'model_results' in result
        assert 'report_info' in result
        assert os.path.exists(result['report_info']['html_path'])

        print("\n✅ 测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_run_analysis()
    sys.exit(0 if success else 1)
```

**Step 2: 运行测试（如果数据存在）**

```bash
python test_analyzer_integration.py
```

**Step 3: 提交**

```bash
git add test_analyzer_integration.py
git commit -m "test: 添加集成测试脚本"
```

---

## Task 10: 最终验证和文档

**Step 1: 验证所有模块可导入**

```bash
python -c "
from basic_garch_analyzer import (
    ModelConfig,
    run_analysis,
    load_and_preprocess,
    fit_basic_garch,
    evaluate_and_report
)
print('✓ 所有模块导入成功')
"
```

**Step 2: 检查命令行帮助**

```bash
python -m basic_garch_analyzer --help
```

**Step 3: 创建 CHANGELOG**

```bash
cat > basic_garch_analyzer/CHANGELOG.md << 'EOF'
# 变更日志

## [1.0.0] - 2025-02-28

### 新增
- 添加 ModelConfig 配置类
- 添加 run_analysis 一键运行函数
- 添加命令行接口支持
- 添加完整的错误处理
- 添加交互式列名选择
- 自动生成 HTML 报告

### 功能
- 支持 GARCH(1,1) 模型拟合
- 支持动态套保比例计算
- 支持 8 种可视化图表
- 支持多格式报告输出（HTML/CSV/Excel）
EOF
```

**Step 4: 最终提交**

```bash
git add basic_garch_analyzer/CHANGELOG.md
git commit -m "docs: 添加变更日志"
```

**Step 5: 打标签（可选）**

```bash
git tag -a v1.0.0 -m "Basic GARCH Analyzer v1.0.0"
git push origin v1.0.0
```

---

## 验收标准

完成所有任务后，应该能够：

1. ✅ 作为 Python 库导入和使用
   ```python
   from basic_garch_analyzer import run_analysis
   result = run_analysis('data.xlsx', 'spot_col', 'futures_col')
   ```

2. ✅ 作为命令行工具运行
   ```bash
   python -m basic_garch_analyzer --data data.xlsx --spot 现货 --futures 期货
   ```

3. ✅ 自动生成完整报告
   - HTML 报告（包含所有图表）
   - CSV/Excel 表格报告
   - 8 张可视化图表

4. ✅ 灵活配置参数
   - 默认配置开箱即用
   - 支持配置覆盖
   - 支持交互式选择

5. ✅ 错误处理完善
   - 数据验证
   - 参数验证
   - 友好的错误提示

---

## 后续优化建议

1. 添加单元测试覆盖
2. 支持多品种批量分析
3. 添加更多可视化选项
4. 支持导出为 PDF 报告
5. 添加模型对比功能（与 ECM-GARCH、DCC-GARCH 等）
