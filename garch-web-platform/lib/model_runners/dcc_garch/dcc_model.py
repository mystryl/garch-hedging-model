"""
DCC-GARCH 模型封装
适配 Web 平台数据格式，复用原始 model_dcc_garch.py 实现
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径以导入原始模型
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入原始 DCC-GARCH 模型
from model_dcc_garch import fit_dcc_garch as _original_fit_dcc_garch


def prepare_returns_data(data: pd.DataFrame) -> tuple:
    """
    从 Web 平台数据格式中提取收益率数据

    注意：此函数当前未被使用，保留用于未来扩展或调试

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s 和 r_f 列的收益率数据（由 data_loader 生成）

    Returns:
    --------
    r_s : np.ndarray
        现货收益率序列
    r_f : np.ndarray
        期货收益率序列
    """
    if 'r_s' not in data.columns or 'r_f' not in data.columns:
        raise ValueError("数据必须包含 'r_s' 和 'r_f' 列（收益率数据）")

    r_s = data['r_s'].values
    r_f = data['r_f'].values

    return r_s, r_f


def fit_dcc_garch_model(
    data: pd.DataFrame,
    p: int = 1,
    q: int = 1,
    dist: str = 'norm',
    output_dir: str = None
) -> dict:
    """
    Web 平台适配版本的 DCC-GARCH 模型拟合

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s, r_f, date 列的完整数据（由 load_and_preprocess 生成）
    p : int
        GARCH(p,q) 的 p 参数
    q : int
        GARCH(p,q) 的 q 参数
    dist : str
        分布假设 ('norm' 或 't')
    output_dir : str
        输出目录路径

    Returns:
    --------
    results : dict
        包含套保比例、动态相关系数等结果的标准格式字典
        {
            'h_actual': array,           # 税后套保比例
            'h_theoretical': array,      # 税前套保比例
            'rho_t': array,              # 动态相关系数
            'sigma_s': array,           # 现货条件波动率
            'sigma_f': array,           # 期货条件波动率
            'conditional_covariance': array,  # 条件协方差矩阵
            'model_params': dict         # 模型参数
        }
    """
    print("\n" + "=" * 60)
    print("DCC-GARCH 模型拟合（Web 平台适配版）")
    print("=" * 60)

    # 验证 dist 参数
    if dist not in ['norm', 't']:
        raise ValueError(f"dist 参数必须是 'norm' 或 't'，得到: {dist}")

    # 验证数据质量
    if len(data) < 150:
        raise ValueError(f"DCC-GARCH 模型需要至少150个观测值，当前数据量: {len(data)}")

    # 检查必需列
    required_cols = ['r_s', 'r_f']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"数据缺少必需列: {missing_cols}")

    # 检查 NaN 和无限值
    if data['r_s'].isna().any() or data['r_f'].isna().any():
        raise ValueError("收益率数据包含 NaN 值，请先清洗数据")

    if np.isinf(data['r_s'].values).any() or np.isinf(data['r_f'].values).any():
        raise ValueError("收益率数据包含无限值，请先清洗数据")

    # 调用原始模型的拟合函数
    # 原始模型期望包含 r_s 和 r_f 的 DataFrame
    results = _original_fit_dcc_garch(
        data=data,
        p=p,
        q=q,
        output_dir=output_dir or 'outputs/model_results',
        dist=dist
    )

    # 提取并返回标准格式的结果
    output = {
        'h_actual': results['h_actual'],
        'h_theoretical': results['h_theoretical'],
        'hedge_ratio': results['hedge_ratio'],
        'rho_t': results['rho_t'],
        'sigma_s': results['sigma_s'],
        'sigma_f': results['sigma_f'],
        'conditional_covariance': results['conditional_covariance'],
        'model_params': {
            'p': p,
            'q': q,
            'dist': dist,
            'model_name': 'DCC-GARCH'
        }
    }

    print("\n" + "=" * 60)
    print("✓ DCC-GARCH 模型拟合完成！")
    print("=" * 60)

    return output
