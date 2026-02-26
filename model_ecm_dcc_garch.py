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


def fit_ecm_dcc_garch(data, p=1, q=1, output_dir='outputs/model_results', coint_window=120):
    """
    拟合ECM-DCC-GARCH模型并计算套保比例（使用滚动窗口协整估计）

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
    coint_window : int
        协整估计滚动窗口大小（默认120天，约4个月交易日）

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

    # 使用价格差分(而非对数收益率)以统一量纲
    # ΔS(t) = S(t) - S(t-1), ΔF(t) = F(t) - F(t-1)
    delta_s = np.diff(spot)  # 长度为T-1
    delta_f = np.diff(futures)  # 长度为T-1

    T = len(spot)
    print(f"\n样本量: {T}")
    print(f"价格差分样本量: {len(delta_s)}")
    print(f"协整估计窗口: {coint_window}天")

    # ========================================
    # 第一阶段: ECM部分（滚动窗口协整）
    # ========================================

    print("\n[阶段1: 误差修正模型]")

    # 步骤1: 滚动窗口协整检验
    print("\n[1/3] 滚动窗口协整检验...")

    # 首先使用全部数据进行协整检验（作为整体参考）
    try:
        score, pvalue, _ = coint(spot, futures, trend='ct', autolag='BIC')
        print(f"  全样本协整检验统计量: {score:.4f}, p值: {pvalue:.6f}")
        if pvalue < 0.05:
            print("  ✓ 全样本在5%水平下存在协整关系")
        else:
            print("  ⚠ 全样本在5%水平下可能不存在协整关系")
    except Exception as e:
        print(f"  ⚠ 全样本协整检验失败: {e}")

    # 使用滚动窗口估计时变协整关系
    print(f"\n  使用{coint_window}天滚动窗口估计时变协整关系...")

    ect = np.full(T, np.nan)
    beta0_series = np.full(T, np.nan)
    beta1_series = np.full(T, np.nan)
    r_squared_series = np.full(T, np.nan)

    # 对每个时间点t，使用过去coint_window天的数据估计均衡
    # 修正时序逻辑: 使用t-1时刻及之前的数据估计参数,避免未来信息泄露
    valid_count = 0
    for t in range(coint_window + 1, T):  # 从coint_window+1开始
        # 使用t-coint_window-1到t-1的数据(不包含t)
        spot_window = spot[t-coint_window-1:t-1]
        futures_window = futures[t-coint_window-1:t-1]

        # 估计协整向量
        X = sm.add_constant(futures_window)
        ecm_model = sm.OLS(spot_window, X).fit()

        beta0_series[t] = ecm_model.params[0]
        beta1_series[t] = ecm_model.params[1]
        r_squared_series[t] = ecm_model.rsquared

        # 计算时刻t的误差修正项(参数基于历史数据)
        ect[t] = spot[t] - (ecm_model.params[0] + ecm_model.params[1] * futures[t])
        valid_count += 1

    print(f"  ✓ 有效估计点数: {valid_count} (从第{coint_window+1}天开始,避免未来信息泄露)")

    # 统计时变协整参数
    print(f"\n  时变协整参数统计:")
    print(f"    β0: 均值={beta0_series[~np.isnan(beta0_series)].mean():.4f}, " +
          f"标准差={beta0_series[~np.isnan(beta0_series)].std():.4f}")
    print(f"    β1: 均值={beta1_series[~np.isnan(beta1_series)].mean():.4f}, " +
          f"标准差={beta1_series[~np.isnan(beta1_series)].std():.4f}")
    print(f"    R²: 均值={r_squared_series[~np.isnan(r_squared_series)].mean():.4f}")

    # 步骤2: 误差修正项统计
    print("\n[2/3] 误差修正项统计...")

    ect_valid = ect[~np.isnan(ect)]
    print(f"  误差修正项统计 (基于{coint_window}天滚动窗口):")
    print(f"    均值: {ect_valid.mean():.2f}")
    print(f"    标准差: {ect_valid.std():.2f}")
    print(f"    最小值: {ect_valid.min():.2f}")
    print(f"    最大值: {ect_valid.max():.2f}")

    # 步骤3: 估计ECM模型
    print("\n[3/3] 估计ECM方程...")

    # ECM方程: ΔS_t = α + h·ΔF_t + γ·ect_{t-1} + ε_t
    # 注意: 现在使用价格差分(单位: 元),与ect量纲一致
    # 准备数据(滞后一期)
    ect_lag = ect[:-1]  # ect[0:T-1]

    # delta_s和delta_f都已经是对数差分,直接使用
    # ect_lag需要与delta_s/delta_f对齐: ect_lag对应t-1时刻
    # 所以应该用delta_s[1:]和delta_f[1:]来匹配ect_lag
    delta_s_aligned = delta_s[1:]  # t=2,...,T, 长度T-2
    delta_f_aligned = delta_f[1:]  # t=2,...,T, 长度T-2
    ect_aligned = ect[1:-1]  # ect[1:T-1], 长度T-2

    # 只使用有效数据(ect不为NaN)
    valid_mask = ~np.isnan(ect_aligned)
    ect_lag_valid = ect_aligned[valid_mask]
    delta_s_valid = delta_s_aligned[valid_mask]
    delta_f_valid = delta_f_aligned[valid_mask]

    print(f"  有效ECM观测点数: {len(delta_s_valid)} (需要滞后一期)")

    X_ecm = pd.DataFrame({
        'const': 1.0,
        'delta_f': delta_f_valid,
        'ect_lag': ect_lag_valid
    })

    # OLS回归(被解释变量是价格差分,单位: 元)
    ecm_result = sm.OLS(delta_s_valid, X_ecm).fit()

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
        sigma_ecm_valid = result_ecm.conditional_volatility / 100

        # 标准化残差
        resid_ecm = result_ecm.resid / result_ecm.conditional_volatility

        # 创建完整长度的sigma_ecm序列
        sigma_ecm_full = np.full(T-1, np.nan)  # 滞后一期，所以是T-1
        sigma_ecm_full[valid_mask] = sigma_ecm_valid
        sigma_ecm = sigma_ecm_full

    except Exception as e:
        print(f"    ⚠ ECM残差GARCH拟合失败: {e}")
        # 使用简单方法
        window = 30
        sigma_ecm_valid = pd.Series(ecm_residuals).rolling(window=window, min_periods=1).std().values / 100
        resid_ecm = ecm_residuals / (sigma_ecm_valid * 100)

        # 创建完整长度的sigma_ecm序列
        sigma_ecm_full = np.full(T-1, np.nan)
        sigma_ecm_full[valid_mask] = sigma_ecm_valid
        sigma_ecm = sigma_ecm_full

    # 期货GARCH (注意: 这里使用价格差分delta_f,而非对数收益率r_f)
    print("  - 拟合期货价格差分GARCH模型...")
    try:
        arch_model_f = arch_model(delta_f, p=p, q=q, mean='Constant',
                                  vol='GARCH', dist='normal')
        result_f = arch_model_f.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_f.convergence_flag == 0}")

        # 条件波动率（需要对齐长度）
        sigma_f_full = result_f.conditional_volatility

        # 标准化残差
        resid_f = result_f.resid / result_f.conditional_volatility

    except Exception as e:
        print(f"    ⚠ 期货GARCH拟合失败: {e}")
        window = 30
        sigma_f_full = pd.Series(delta_f).rolling(window=window, min_periods=1).std().values
        resid_f = delta_f / sigma_f_full

    # 对齐长度（ECM回归少一个观测值，且需要与valid_mask对齐）
    sigma_f_aligned = sigma_f_full[1:]  # 去掉第一期
    resid_f_valid = resid_f[1:][valid_mask]  # 只保留有效数据

    # resid_ecm也对应valid_mask
    resid_ecm_valid = resid_ecm

    # 合并标准化残差（只使用有效数据）
    standardized_residuals = np.column_stack([resid_ecm_valid, resid_f_valid])

    # 步骤2: 估计DCC参数
    print("\n[2/3] 估计DCC参数...")

    alpha_dcc, beta_dcc, Q_bar = estimate_dcc_parameters(standardized_residuals)

    print(f"  DCC参数:")
    print(f"    α = {alpha_dcc:.4f}")
    print(f"    β = {beta_dcc:.4f}")
    print(f"    α + β = {alpha_dcc + beta_dcc:.4f}")

    # 步骤3: 计算动态相关系数
    print("\n[3/3] 计算动态相关系数...")

    rho_t_valid, R_t = compute_dcc_correlations(standardized_residuals, alpha_dcc, beta_dcc, Q_bar)

    print(f"  动态相关系数统计:")
    print(f"    均值: {rho_t_valid.mean():.4f}")
    print(f"    标准差: {rho_t_valid.std():.4f}")
    print(f"    范围: [{rho_t_valid.min():.4f}, {rho_t_valid.max():.4f}]")

    # 创建完整长度的rho_t序列
    rho_t_full = np.full(T-1, np.nan)  # 滞后一期
    rho_t_full[valid_mask] = rho_t_valid
    rho_t = rho_t_full

    # ========================================
    # 第三阶段: 计算套保比例
    # ========================================

    print("\n[阶段3: 计算套保比例]")

    # ECM-DCC-GARCH的套保比例公式:
    # h_t = h_ecm * (sigma_ecm / sigma_f)^2 * (rho_t调整)

    # 基础套保比例（来自ECM）
    h_base = h_ecm

    # 波动率调整因子（只对有效数据计算）
    sigma_ecm_valid = sigma_ecm[valid_mask]
    sigma_f_valid = sigma_f_aligned[valid_mask]

    vol_ratio = sigma_ecm_valid / sigma_f_valid
    vol_adjustment = vol_ratio ** 2

    # 综合套保比例（考虑ECM和波动率）
    h_t_valid = h_base * vol_adjustment

    # 进一步考虑动态相关系数的调整
    # 如果相关性低，应该降低套保比例
    correlation_adjustment = np.abs(rho_t_valid)
    h_t_adjusted_valid = h_t_valid * correlation_adjustment

    # 创建完整长度的序列
    h_t_adjusted = np.full(T-1, np.nan)
    h_t_adjusted[valid_mask] = h_t_adjusted_valid

    # 税点调整
    h_actual = h_t_adjusted / 1.13

    # 平滑处理
    window_smooth = 3
    h_actual_smooth = pd.Series(h_actual).rolling(window=window_smooth, center=True, min_periods=1).mean().values
    # 确保没有NaN（用基础套保比例填充）
    h_actual_smooth = np.nan_to_num(h_actual_smooth, nan=h_base)

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
        'ect': ect[1:],  # 对应t-1期的误差修正项
        'beta0': beta0_series[1:],  # 时变协整参数
        'beta1': beta1_series[1:],  # 时变协整参数
        'r_squared_coint': r_squared_series[1:],  # 时变协整R²
        'sigma_ecm': sigma_ecm,
        'sigma_f': sigma_f_aligned,
        'vol_ratio': np.full(T-1, np.nan),  # 占位，实际只在valid_mask计算
        'correlation_adjustment': np.full(T-1, np.nan)  # 占位
    })

    # 填充有效数据的vol_ratio和correlation_adjustment
    output_df.loc[valid_mask, 'vol_ratio'] = vol_ratio
    output_df.loc[valid_mask, 'correlation_adjustment'] = correlation_adjustment

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
        'beta0_series': beta0_series,  # 时变协整参数
        'beta1_series': beta1_series,  # 时变协整参数
        'sigma_ecm': sigma_ecm,
        'sigma_f': sigma_f_aligned,
        'ecm_params': {
            'alpha': alpha,
            'h_ecm': h_ecm,
            'gamma': gamma
        },
        'cointegration_params': {
            'beta0_mean': beta0_series[~np.isnan(beta0_series)].mean(),
            'beta1_mean': beta1_series[~np.isnan(beta1_series)].mean(),
            'beta0_std': beta0_series[~np.isnan(beta0_series)].std(),
            'beta1_std': beta1_series[~np.isnan(beta1_series)].std(),
            'r_squared_mean': r_squared_series[~np.isnan(r_squared_series)].mean()
        },
        'dcc_params': {
            'alpha': alpha_dcc,
            'beta': beta_dcc
        },
        'garch_params': result_ecm.params.to_dict() if 'result_ecm' in locals() else {},
        'coint_window': coint_window,
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试ECM-DCC-GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_ecm_dcc_garch(data)

    print("\n测试完成！")
