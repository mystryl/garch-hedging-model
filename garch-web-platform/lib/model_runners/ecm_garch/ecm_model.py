#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ECM-GARCH 模型封装
适配 Web 平台数据格式，封装原始 model_ecm_garch.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入原始 ECM-GARCH 模型
from model_ecm_garch import fit_ecm_garch


def fit_ecm_garch_model(
    data: pd.DataFrame,
    p: int = 1,
    q: int = 1,
    coint_window: int = 120,
    coupling_method: str = 'ect-garch',
    tax_rate: float = 0.13,
    output_dir: str = None
) -> dict:
    """
    拟合 ECM-GARCH 模型（Web 平台适配版本）

    Parameters
    ----------
    data : pd.DataFrame
        包含以下列的数据框：
        - spot: 现货价格
        - futures: 期货价格
        - r_s: 现货收益率
        - r_f: 期货收益率
        - date: 日期（可选）
    p : int
        GARCH 模型的 p 阶数
    q : int
        GARCH 模型的 q 阶数
    coint_window : int
        协整估计滚动窗口大小
    coupling_method : str
        ECM-GARCH 耦合方式 ('ect-garch' 或 'static')
    tax_rate : float
        税点调整比例（默认 0.13）
    output_dir : str
        输出目录

    Returns
    -------
    dict
        模型结果字典，包含：
        - h_actual: 税后套保比例序列
        - h_theoretical: 税前套保比例序列
        - h_ecm_base: ECM 基础套保比例
        - ect: 误差修正项序列
        - beta0_series: 时变协整参数 beta0
        - beta1_series: 时变协整参数 beta1
        - ecm_params: ECM 参数 (alpha, h_ecm, gamma)
        - cointegration_params: 协整参数统计
        - garch_params: GARCH 参数
        - model_params: 模型参数字典
    """
    print("\n[ECM-GARCH 模型封装] 调用原始模型...")

    # 验证数据列
    required_cols = ['spot', 'futures', 'r_s', 'r_f']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"数据缺少必要列: {missing_cols}")

    # 验证样本量
    min_required = coint_window + 2
    if len(data) < min_required:
        raise ValueError(
            f"样本量不足: 当前 {len(data)}，至少需要 {min_required} "
            f"(协整窗口 {coint_window} + 2)"
        )

    # 调用原始模型
    results = fit_ecm_garch(
        data=data,
        p=p,
        q=q,
        output_dir=output_dir or 'outputs/ecm_garch_results',
        coint_window=coint_window,
        tax_adjust=True,  # 强制启用税点调整
        coupling_method=coupling_method
    )

    # 添加模型参数到结果
    results['model_params'] = {
        'p': p,
        'q': q,
        'coint_window': coint_window,
        'coupling_method': coupling_method,
        'tax_rate': tax_rate
    }

    print("\n✓ ECM-GARCH 模型拟合完成")
    print(f"  套保比例均值: {results['h_actual'].mean():.4f}")
    print(f"  误差修正系数: {results['ecm_params']['gamma']:.6f}")
    print(f"  协整系数 β1 均值: {results['cointegration_params']['beta1_mean']:.4f}")

    return results
