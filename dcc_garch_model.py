"""
DCC-GARCH动态套保模型
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

    # 第一个时间点
    Q_t[0] = np.matmul(rt[0].T/2, rt[0]/2)

    # 迭代计算所有时间点的条件协方差矩阵
    for i in range(1, T):
        dts = np.diag(D_t[i])
        dtinv = np.linalg.inv(dts)
        et = dtinv * rt[i].T

        # DCC更新方程
        Q_t[i] = (1 - a - b) * Q_bar + a * (et * et.T) + b * Q_t[i-1]

        # 标准化为相关系数矩阵
        qts = np.linalg.inv(np.sqrt(np.diag(np.diag(Q_t[i]))))
        R_t[i] = np.matmul(qts, np.matmul(Q_t[i], qts))

        # 条件协方差矩阵: H_t = D_t @ R_t @ D_t
        H_t[i] = np.matmul(dts, np.matmul(R_t[i], dts))

    return H_t


def fit_dcc_garch_hedge_ratio(data, window=None, dist='norm'):
    """
    使用DCC-GARCH模型计算动态套保比率

    Parameters:
    -----------
    data : pd.DataFrame
        包含'spot'和'futures'列的价格数据
    window : int or None
        滚动窗口大小。如果为None,使用全部数据
    dist : str
        分布假设,'norm'或't'

    Returns:
    --------
    results : dict
        包含套保比率、协方差等结果
    """
    import mgarch

    # 数据预处理
    data = data.copy()
    T_original = len(data[['spot', 'futures']].dropna())  # 原始价格数据量
    data = data[['spot', 'futures']].dropna()

    # 计算对数收益率
    data['r_spot'] = np.log(data['spot'] / data['spot'].shift(1))
    data['r_futures'] = np.log(data['futures'] / data['futures'].shift(1))
    data = data.dropna()

    T = len(data)  # 收益率数据量
    if T < 60:
        raise ValueError(f"收益率样本量不足({T}个),至少需要60个观测值(原始价格数据至少需要{61}个,建议提供{120}个以上)")
    if T_original > 120 and window is None:
        print(f"警告: 样本量({T_original}个)超过120,建议使用滚动窗口")

    # 提取收益率矩阵
    returns = data[['r_spot', 'r_futures']].values

    # 拟合DCC-GARCH模型
    model = mgarch.mgarch(dist=dist)
    model.fit(returns)

    # 提取时变条件协方差矩阵
    H_t = get_conditional_covariance(model)

    # 计算套保比率: h_t = Cov(ΔS, ΔF) / Var(ΔF)
    var_futures = H_t[:, 1, 1]  # 期货条件方差
    cov_spot_futures = H_t[:, 0, 1]  # 现货-期货条件协方差

    hedge_ratio_raw = cov_spot_futures / var_futures
    hedge_ratio_adjusted = hedge_ratio_raw / 1.13  # 税点调整

    # 对齐到原始数据索引(从第二个数据开始,因为有滞后)
    hedge_ratio_series = pd.Series(
        hedge_ratio_adjusted[1:],
        index=data.index[1:]
    )

    return {
        'hedge_ratio': hedge_ratio_series,
        'conditional_covariance': H_t[1:],  # 去掉第一个NaN
        'conditional_variance_spot': H_t[:, 0, 0][1:],
        'conditional_variance_futures': var_futures[1:],
        'model': model,
        'data': data
    }


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("DCC-GARCH动态套保模型测试")
    print("=" * 60)

    # 生成模拟数据(61个交易日,计算收益率后得到60个有效观测值)
    np.random.seed(42)
    dates = pd.date_range(start='2025-01-01', periods=61, freq='B')
    spot_price = 68000 + np.cumsum(np.random.normal(50, 200, 61))
    futures_price = 67800 + np.cumsum(np.random.normal(48, 190, 61))

    data = pd.DataFrame({
        'spot': spot_price,
        'futures': futures_price
    }, index=dates)

    print(f"\n原始样本量: {len(data)} 个交易日")
    print("计算收益率后有效样本量: 60个")

    # 拟合模型
    print("\n拟合DCC-GARCH模型...")
    results = fit_dcc_garch_hedge_ratio(data)

    # 输出结果
    print("\n=== 套保比率统计 ===")
    hr = results['hedge_ratio']
    print(f"均值: {hr.mean():.4f}")
    print(f"标准差: {hr.std():.4f}")
    print(f"最小值: {hr.min():.4f}")
    print(f"最大值: {hr.max():.4f}")

    print("\n最后10个交易日套保比率:")
    print(hr.tail(10).to_frame('套保比率'))

    print("\n✓ 测试完成!")
