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
