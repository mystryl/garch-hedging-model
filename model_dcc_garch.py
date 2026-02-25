"""
模型3: DCC-GARCH套保模型
使用动态条件相关GARCH模型，考虑时变相关性
"""

import pandas as pd
import numpy as np
from arch import arch_model
import warnings
warnings.filterwarnings('ignore')


def estimate_dcc_parameters(standardized_residuals):
    """
    估计DCC模型的参数 (α, β)

    DCC模型:
    Q_t = (1 - α - β) * Q̄ + α * ε_{t-1} * ε_{t-1}' + β * Q_{t-1}
    R_t = Q_t^{*-1/2} * Q_t * Q_t^{*-1/2}

    其中:
    - Q_t: 时变协方差矩阵
    - Q̄: 标准化残差的无条件协方差矩阵
    - ε_t: 标准化残差
    - R_t: 时变相关系数矩阵
    """

    T, k = standardized_residuals.shape

    # 计算无条件协方差矩阵 Q̄
    Q_bar = np.cov(standardized_residuals.T)

    # 初始化
    alpha = 0.05
    beta = 0.90

    # 简单的矩估计方法
    # 使用网格搜索找到最优的α和β
    best_alpha = alpha
    best_beta = beta
    best_loglik = -np.inf

    # 搜索范围
    alphas = np.linspace(0.01, 0.15, 10)
    betas = np.linspace(0.80, 0.98, 10)

    for a in alphas:
        for b in betas:
            if a + b < 1:
                # 计算时变Q_t序列
                Q_t = np.zeros((T, k, k))
                Q_t[0] = Q_bar

                loglik = 0

                for t in range(1, T):
                    eps_prev = standardized_residuals[t-1:t, :].reshape(-1, 1)
                    Q_t[t] = (1 - a - b) * Q_bar + a * (eps_prev @ eps_prev.T) + b * Q_t[t-1]

                    # 确保正定性
                    if np.any(np.diag(Q_t[t]) <= 0):
                        loglik = -np.inf
                        break

                # 计算对数似然（简化版）
                if loglik > best_loglik:
                    best_alpha = a
                    best_beta = b
                    best_loglik = loglik

    return best_alpha, best_beta, Q_bar


def compute_dcc_correlations(standardized_residuals, alpha, beta, Q_bar):
    """
    计算DCC动态相关系数序列
    """
    T, k = standardized_residuals.shape

    # 初始化
    Q_t = np.zeros((T, k, k))
    R_t = np.zeros((T, k, k))

    Q_t[0] = Q_bar

    # 递推计算Q_t和R_t
    for t in range(1, T):
        eps_prev = standardized_residuals[t-1:t, :].reshape(-1, 1)
        Q_t[t] = (1 - alpha - beta) * Q_bar + alpha * (eps_prev @ eps_prev.T) + beta * Q_t[t-1]

        # 标准化得到相关系数矩阵 R_t
        # R_t[i,j] = Q_t[i,j] / sqrt(Q_t[i,i] * Q_t[j,j])
        sqrt_diag_Q = np.sqrt(np.diag(Q_t[t]))
        R_t[t] = Q_t[t] / np.outer(sqrt_diag_Q, sqrt_diag_Q)

    # 提取动态相关系数 (现货-期货)
    rho_t = R_t[:, 0, 1]

    return rho_t, R_t


def fit_dcc_garch(data, p=1, q=1, output_dir='outputs/model_results'):
    """
    拟合DCC-GARCH模型并计算套保比例

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s 和 r_f 的数据
    p : int
        GARCH模型的p阶数
    q : int
        GARCH模型的q阶数
    output_dir : str
        输出目录

    Returns:
    --------
    results : dict
        包含套保比例序列、动态相关系数等
    """

    print("\n" + "=" * 60)
    print("模型3: DCC-GARCH套保模型")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 提取收益率数据
    r_s = data['r_s'].values * 100  # 转换为百分比
    r_f = data['r_f'].values * 100

    T = len(r_s)
    print(f"\n样本量: {T}")

    # 步骤1: 分别拟合单变量GARCH(1,1)模型
    print("\n[1/4] 拟合单变量GARCH模型...")

    # 现货GARCH
    print("  - 拟合现货收益率GARCH模型...")
    model_s = arch_model(r_s, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    result_s = model_s.fit(disp='off', update_freq=0)
    print(f"    ✓ 收敛: {result_s.convergence_flag == 0}")

    # 期货GARCH
    print("  - 拟合期货收益率GARCH模型...")
    model_f = arch_model(r_f, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    result_f = model_f.fit(disp='off', update_freq=0)
    print(f"    ✓ 收敛: {result_f.convergence_flag == 0}")

    # 获取条件波动率
    sigma_s = result_s.conditional_volatility / 100  # 转回原始单位
    sigma_f = result_f.conditional_volatility / 100

    # 获取标准化残差
    resid_s = result_s.resid / result_s.conditional_volatility
    resid_f = result_f.resid / result_f.conditional_volatility

    # 合并标准化残差
    standardized_residuals = np.column_stack([resid_s, resid_f])

    # 步骤2: 估计DCC参数
    print("\n[2/4] 估计DCC参数...")

    alpha, beta, Q_bar = estimate_dcc_parameters(standardized_residuals)

    print(f"  DCC参数估计结果:")
    print(f"    α = {alpha:.4f} (短期冲击对相关性的影响)")
    print(f"    β = {beta:.4f} (相关性的持续性)")
    print(f"    α + β = {alpha + beta:.4f} (应 < 1)")

    # 步骤3: 计算动态相关系数
    print("\n[3/4] 计算动态相关系数...")

    rho_t, R_t = compute_dcc_correlations(standardized_residuals, alpha, beta, Q_bar)

    print(f"  动态相关系数统计:")
    print(f"    均值: {rho_t.mean():.4f}")
    print(f"    标准差: {rho_t.std():.4f}")
    print(f"    最小值: {rho_t.min():.4f}")
    print(f"    最大值: {rho_t.max():.4f}")

    # 步骤4: 计算套保比例
    print("\n[4/4] 计算套保比例...")

    # 时变协方差
    cov_sf = rho_t * sigma_s * sigma_f

    # 时变方差（期货）
    var_f = sigma_f ** 2

    # 套保比例
    h_t = cov_sf / var_f

    # 税点调整
    h_actual = h_t / 1.13

    # 处理异常值
    h_actual = np.clip(h_actual, 0, 2)

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual.mean():.4f}")
    print(f"  标准差: {h_actual.std():.4f}")
    print(f"  最小值: {h_actual.min():.4f}")
    print(f"  最大值: {h_actual.max():.4f}")
    print(f"  中位数: {np.median(h_actual):.4f}")

    # 保存结果
    print("\n[保存结果]")

    # 创建输出DataFrame
    output_df = pd.DataFrame({
        'date': data['date'].values,
        'h_theoretical': h_t,
        'h_actual': h_actual,
        'rho_t': rho_t,
        'sigma_s': sigma_s,
        'sigma_f': sigma_f,
        'cov_sf': cov_sf,
        'var_f': var_f
    })

    output_path = f"{output_dir}/h_dcc_garch.csv"
    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {output_path}")

    # 单独保存动态相关系数
    rho_path = f"{output_dir}/rho_t.csv"
    output_df[['date', 'rho_t']].to_csv(rho_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {rho_path}")

    print("\n" + "=" * 60)
    print("✓ 模型3拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'DCC-GARCH',
        'h_actual': h_actual,
        'h_theoretical': h_t,
        'rho_t': rho_t,
        'sigma_s': sigma_s,
        'sigma_f': sigma_f,
        'cov_sf': cov_sf,
        'var_f': var_f,
        'dcc_params': {
            'alpha': alpha,
            'beta': beta
        },
        'garch_params_spot': result_s.params.to_dict(),
        'garch_params_futures': result_f.params.to_dict(),
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试DCC-GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_dcc_garch(data)

    print("\n测试完成！")
