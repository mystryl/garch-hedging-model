"""
模型4: ECM-DCC-GARCH综合模型
结合基差修正 + 动态相关性 + 时变波动
学术界和实务界公认的最强模型
"""

import pandas as pd
import numpy as np
from arch import arch_model
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import warnings
warnings.filterwarnings('ignore')

# 导入DCC相关函数
from model_dcc_garch import estimate_dcc_parameters, compute_dcc_correlations


def fit_ecm_dcc_garch(data, p=1, q=1, output_dir='outputs/model_results'):
    """
    拟合ECM-DCC-GARCH模型并计算套保比例

    Parameters:
    -----------
    data : pd.DataFrame
        包含 spot, futures, r_s, r_f 的数据
    p : int
        GARCH模型的p阶数
    q : int
        GARCH模型的q阶数
    output_dir : str
        输出目录

    Returns:
    --------
    results : dict
        包含套保比例序列、ECM参数、DCC参数等
    """

    print("\n" + "=" * 60)
    print("模型4: ECM-DCC-GARCH综合模型")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 提取数据
    spot = data['spot'].values
    futures = data['futures'].values
    r_s = data['r_s'].values * 100
    r_f = data['r_f'].values * 100

    T = len(r_s)
    print(f"\n样本量: {T}")

    # ========================================
    # 第一阶段: ECM部分
    # ========================================

    print("\n[阶段1: 误差修正模型]")

    # 步骤1: 协整检验
    print("\n[1/3] 协整检验...")

    try:
        score, pvalue, _ = coint(spot, futures, trend='ct', autolag='BIC')
        print(f"  Engle-Granger协整检验统计量: {score:.4f}")
        print(f"  p值: {pvalue:.6f}")
        if pvalue < 0.05:
            print("  ✓ 在5%水平下存在协整关系")
        else:
            print("  ⚠ 在5%水平下可能不存在协整关系")
    except Exception as e:
        print(f"  ⚠ 协整检验失败: {e}")

    # 步骤2: 构建误差修正项
    print("\n[2/3] 构建误差修正项...")

    # 长期均衡关系
    X = sm.add_constant(futures)
    ecm_model = sm.OLS(spot, X).fit()

    beta0 = ecm_model.params[0]
    beta1 = ecm_model.params[1]

    print(f"  长期均衡方程: spot = {beta0:.2f} + {beta1:.4f} * futures")
    print(f"  R² = {ecm_model.rsquared:.4f}")

    # 计算误差修正项
    ect = spot - (beta0 + beta1 * futures)

    # 步骤3: 估计ECM模型
    print("\n[3/3] 估计ECM方程...")

    ect_lag = ect[:-1]
    r_s_current = r_s[1:]
    r_f_current = r_f[1:]

    X_ecm = pd.DataFrame({
        'const': 1.0,
        'delta_f': r_f_current,
        'ect_lag': ect_lag
    })

    ecm_result = sm.OLS(r_s_current, X_ecm).fit()

    alpha = ecm_result.params['const']
    h_ecm = ecm_result.params['delta_f']
    gamma = ecm_result.params['ect_lag']

    print(f"\nECM方程: ΔS_t = {alpha:.6f} + {h_ecm:.4f}·ΔF_t + {gamma:.6f}·ect_{{t-1}} + ε_t")
    print(f"  误差修正系数 γ = {gamma:.6f} ", end="")
    if gamma < 0:
        print("✓ (反向修正)")
    else:
        print("⚠ (可能异常)")

    # ECM残差（经过误差修正后的收益率）
    ecm_residuals = ecm_result.resid

    # ========================================
    # 第二阶段: DCC-GARCH部分
    # ========================================

    print("\n[阶段2: DCC-GARCH动态相关性模型]")

    # 准备数据：ECM残差 和 期货收益率
    print("\n[1/3] 拟合单变量GARCH模型...")

    # ECM残差GARCH
    print("  - 拟合ECM残差GARCH模型...")
    try:
        arch_model_ecm = arch_model(ecm_residuals, p=p, q=q, mean='Zero',
                                    vol='GARCH', dist='normal')
        result_ecm = arch_model_ecm.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_ecm.convergence_flag == 0}")

        # 条件波动率
        sigma_ecm = result_ecm.conditional_volatility / 100

        # 标准化残差
        resid_ecm = result_ecm.resid / result_ecm.conditional_volatility

    except Exception as e:
        print(f"    ⚠ ECM残差GARCH拟合失败: {e}")
        # 使用简单方法
        window = 30
        sigma_ecm = pd.Series(ecm_residuals).rolling(window=window, min_periods=1).std().values / 100
        resid_ecm = ecm_residuals / (sigma_ecm * 100)

    # 期货GARCH
    print("  - 拟合期货收益率GARCH模型...")
    try:
        arch_model_f = arch_model(r_f, p=p, q=q, mean='Constant',
                                  vol='GARCH', dist='normal')
        result_f = arch_model_f.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_f.convergence_flag == 0}")

        # 条件波动率（需要对齐长度）
        sigma_f_full = result_f.conditional_volatility / 100

        # 标准化残差
        resid_f = result_f.resid / result_f.conditional_volatility

    except Exception as e:
        print(f"    ⚠ 期货GARCH拟合失败: {e}")
        window = 30
        sigma_f_full = pd.Series(r_f).rolling(window=window, min_periods=1).std().values / 100
        resid_f = r_f / (sigma_f_full * 100)

    # 对齐长度（ECM回归少一个观测值）
    sigma_f = sigma_f_full[1:]
    resid_f_aligned = resid_f[1:]

    # 合并标准化残差
    standardized_residuals = np.column_stack([resid_ecm, resid_f_aligned])

    # 步骤2: 估计DCC参数
    print("\n[2/3] 估计DCC参数...")

    alpha_dcc, beta_dcc, Q_bar = estimate_dcc_parameters(standardized_residuals)

    print(f"  DCC参数:")
    print(f"    α = {alpha_dcc:.4f}")
    print(f"    β = {beta_dcc:.4f}")
    print(f"    α + β = {alpha_dcc + beta_dcc:.4f}")

    # 步骤3: 计算动态相关系数
    print("\n[3/3] 计算动态相关系数...")

    rho_t, R_t = compute_dcc_correlations(standardized_residuals, alpha_dcc, beta_dcc, Q_bar)

    print(f"  动态相关系数统计:")
    print(f"    均值: {rho_t.mean():.4f}")
    print(f"    标准差: {rho_t.std():.4f}")
    print(f"    范围: [{rho_t.min():.4f}, {rho_t.max():.4f}]")

    # ========================================
    # 第三阶段: 计算套保比例
    # ========================================

    print("\n[阶段3: 计算套保比例]")

    # ECM-DCC-GARCH的套保比例公式:
    # h_t = h_ecm * (sigma_ecm / sigma_f)^2 * (rho_t调整)

    # 基础套保比例（来自ECM）
    h_base = h_ecm

    # 波动率调整因子
    vol_ratio = sigma_ecm / sigma_f
    vol_adjustment = vol_ratio ** 2

    # 综合套保比例（考虑ECM和波动率）
    h_t = h_base * vol_adjustment

    # 进一步考虑动态相关系数的调整
    # 如果相关性低，应该降低套保比例
    correlation_adjustment = np.abs(rho_t)
    h_t_adjusted = h_t * correlation_adjustment

    # 税点调整
    h_actual = h_t_adjusted / 1.13

    # 平滑处理
    window_smooth = 3
    h_actual_smooth = pd.Series(h_actual).rolling(window=window_smooth, center=True, min_periods=1).mean().values
    # 确保没有NaN
    h_actual_smooth = np.nan_to_num(h_actual_smooth, nan=h_actual)

    # 处理异常值
    h_actual_final = np.clip(h_actual_smooth, 0, 2)

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual_final.mean():.4f}")
    print(f"  标准差: {h_actual_final.std():.4f}")
    print(f"  最小值: {h_actual_final.min():.4f}")
    print(f"  最大值: {h_actual_final.max():.4f}")
    print(f"  中位数: {np.median(h_actual_final):.4f}")

    # 保存结果
    print("\n[保存结果]")

    # 创建输出DataFrame
    output_df = pd.DataFrame({
        'date': data['date'].values[1:],  # ECM回归少一个观测值
        'h_theoretical': h_t_adjusted,
        'h_actual': h_actual_final,
        'h_ecm_base': h_base,
        'rho_t': rho_t,
        'ect': ect[1:],
        'sigma_ecm': sigma_ecm,
        'sigma_f': sigma_f,
        'vol_ratio': vol_ratio,
        'correlation_adjustment': correlation_adjustment
    })

    output_path = f"{output_dir}/h_ecm_dcc_garch.csv"
    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {output_path}")

    print("\n" + "=" * 60)
    print("✓ 模型4拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'ECM-DCC-GARCH',
        'h_actual': h_actual_final,
        'h_theoretical': h_t_adjusted,
        'h_ecm_base': h_base,
        'rho_t': rho_t,
        'ect': ect,
        'sigma_ecm': sigma_ecm,
        'sigma_f': sigma_f,
        'ecm_params': {
            'alpha': alpha,
            'h_ecm': h_ecm,
            'gamma': gamma
        },
        'cointegration_params': {
            'beta0': beta0,
            'beta1': beta1,
            'r_squared': ecm_model.rsquared
        },
        'dcc_params': {
            'alpha': alpha_dcc,
            'beta': beta_dcc
        },
        'garch_params': result_ecm.params.to_dict() if 'result_ecm' in locals() else {},
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试ECM-DCC-GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_ecm_dcc_garch(data)

    print("\n测试完成！")
