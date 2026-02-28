"""
模型3: DCC-GARCH动态套保模型
基于mgarch库实现,用于计算现货-期货的动态最小方差套保比率
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


def get_conditional_covariance(mgarch_model):
    """
    从已拟合的mgarch模型中提取完整的时变条件协方差矩阵序列

    Parameters:
    -----------
    mgarch_model : mgarch.mgarch
        已拟合的DCC-GARCH模型

    Returns:
    --------
    H_t : np.ndarray
        时变条件协方差矩阵序列,形状为(T, N, N)
        T为时间点数,N为资产数
    """
    T = mgarch_model.T
    N = mgarch_model.N
    a = mgarch_model.a
    b = mgarch_model.b
    D_t = mgarch_model.D_t
    rt = mgarch_model.rt

    # 计算无条件协方差矩阵
    Q_bar = np.cov(rt.reshape(N, T))

    # 初始化
    Q_t = np.zeros((T, N, N))
    R_t = np.zeros((T, N, N))
    H_t = np.zeros((T, N, N))

    # 第一个时间点: 使用无条件协方差作为初始值
    Q_t[0] = Q_bar

    # 计算第一个时间点的相关系数矩阵和条件协方差矩阵
    sqrt_diag_0 = np.sqrt(np.diag(Q_t[0]))
    qts_0 = np.diag(1.0 / sqrt_diag_0)
    R_t[0] = qts_0 @ Q_t[0] @ qts_0
    dts_0 = np.diag(D_t[0])
    H_t[0] = dts_0 @ R_t[0] @ dts_0

    # 迭代计算所有时间点的条件协方差矩阵
    for i in range(1, T):
        dts = np.diag(D_t[i])
        dtinv = np.linalg.inv(dts)
        et = dtinv @ rt[i].T  # 使用矩阵乘法

        # DCC更新方程
        Q_t[i] = (1 - a - b) * Q_bar + a * (et @ et.T) + b * Q_t[i-1]

        # 标准化为相关系数矩阵
        sqrt_diag = np.sqrt(np.diag(Q_t[i]))
        qts = np.diag(1.0 / sqrt_diag)
        R_t[i] = qts @ Q_t[i] @ qts

        # 条件协方差矩阵: H_t = D_t @ R_t @ D_t
        H_t[i] = dts @ R_t[i] @ dts

    return H_t


# 税点调整系数
TAX_ADJUSTMENT_FACTOR = 1.13  # 增值税等税点调整


def fit_dcc_garch(data, p=1, q=1, output_dir='outputs/model_results', dist='norm'):
    """
    拟合DCC-GARCH模型并计算套保比例（使用mgarch库）

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s 和 r_f 的收益率数据
    p : int
        GARCH模型的p阶数（当前版本固定使用GARCH(1,1)）
    q : int
        GARCH模型的q阶数（当前版本固定使用GARCH(1,1)）
    output_dir : str
        输出目录
    dist : str
        分布假设,'norm'或't'

    Returns:
    --------
    results : dict
        包含套保比例序列、动态相关系数等
    """

    print("\n" + "=" * 60)
    print("模型3: DCC-GARCH套保模型（使用mgarch库）")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 提取收益率数据
    if 'r_s' not in data.columns or 'r_f' not in data.columns:
        raise ValueError("输入数据必须包含 'r_s' 和 'r_f' 列（收益率数据）")

    r_s = data['r_s'].values
    r_f = data['r_f'].values

    T = len(r_s)
    print(f"\n样本量: {T}")

    # 准备收益率矩阵
    returns = np.column_stack([r_s, r_f])

    # 使用mgarch库拟合DCC-GARCH模型
    print("\n拟合DCC-GARCH模型...")
    import mgarch
    dcc_model = mgarch.mgarch(dist=dist)
    dcc_model.fit(returns)
    print("  ✓ DCC-GARCH模型拟合成功")

    # 提取时变条件协方差矩阵
    H_t = get_conditional_covariance(dcc_model)

    # 计算套保比率和相关系数
    var_s = H_t[:, 0, 0]  # 现货条件方差
    var_f = H_t[:, 1, 1]  # 期货条件方差
    cov_sf = H_t[:, 0, 1]  # 协方差

    # 动态相关系数
    rho_t = cov_sf / np.sqrt(var_s * var_f)

    # 套保比率
    h_t = cov_sf / var_f

    # 税点调整
    h_actual = h_t / TAX_ADJUSTMENT_FACTOR

    # 处理异常值
    h_actual = np.clip(h_actual, 0, 2)

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual.mean():.4f}")
    print(f"  标准差: {h_actual.std():.4f}")
    print(f"  最小值: {h_actual.min():.4f}")
    print(f"  最大值: {h_actual.max():.4f}")
    print(f"  中位数: {np.median(h_actual):.4f}")

    print(f"\n动态相关系数统计:")
    print(f"  均值: {rho_t.mean():.4f}")
    print(f"  标准差: {rho_t.std():.4f}")
    print(f"  最小值: {rho_t.min():.4f}")
    print(f"  最大值: {rho_t.max():.4f}")

    # 保存结果
    print("\n[保存结果]")

    # 创建输出DataFrame
    output_df = pd.DataFrame({
        'date': data['date'].values if 'date' in data.columns else range(T),
        'h_theoretical': h_t,
        'h_actual': h_actual,
        'rho_t': rho_t,
        'sigma_s': np.sqrt(var_s),
        'sigma_f': np.sqrt(var_f),
        'cov_sf': cov_sf,
        'var_f': var_f
    })

    output_path = f"{output_dir}/h_dcc_garch.csv"
    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {output_path}")

    print("\n" + "=" * 60)
    print("✓ 模型3拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'DCC-GARCH',
        'h_actual': h_actual,
        'h_theoretical': h_t,
        'hedge_ratio': pd.Series(h_actual, index=output_df.index),
        'rho_t': rho_t,
        'sigma_s': np.sqrt(var_s),
        'sigma_f': np.sqrt(var_f),
        'cov_sf': cov_sf,
        'var_f': var_f,
        'dcc_params': {
            'dist': dist
        },
        'conditional_covariance': H_t,
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("DCC-GARCH动态套保模型测试")
    print("=" * 60)

    # 生成模拟数据
    np.random.seed(42)
    n_days = 200
    dates = pd.date_range(start='2025-01-01', periods=n_days, freq='B')

    # 生成收益率数据
    r_s = np.random.normal(0, 0.02, n_days)
    r_f = np.random.normal(0, 0.018, n_days) + 0.95 * r_s  # 高度相关

    data = pd.DataFrame({
        'date': dates,
        'r_s': r_s,
        'r_f': r_f
    })

    print(f"\n样本量: {len(data)} 个交易日")

    # 拟合模型
    print("\n拟合DCC-GARCH模型...")
    results = fit_dcc_garch(data)

    print("\n✓ 测试完成!")
