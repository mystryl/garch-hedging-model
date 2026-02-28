"""
工具函数模块
"""


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
