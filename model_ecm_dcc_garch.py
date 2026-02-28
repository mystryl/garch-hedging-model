"""
模型4: ECM-DCC-GARCH综合模型
结合基差修正 + 动态相关性 + 时变波动
学术界和实务界公认的最强模型

实现说明:
- 使用mgarch库进行DCC-GARCH建模（最佳实践）
- 复用dcc_garch_model.py中已验证的条件协方差提取函数
- 使用标准的最小方差套保比率公式: h_t = Cov_t / Var_t
"""

import pandas as pd
import numpy as np
from arch import arch_model
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import warnings
warnings.filterwarnings('ignore')

# 导入mgarch库和修正后的DCC函数
try:
    import mgarch
except ImportError:
    raise ImportError("需要安装mgarch库: pip install mgarch")

from model_dcc_garch import get_conditional_covariance, TAX_ADJUSTMENT_FACTOR


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
    # 第二阶段: DCC-GARCH部分（使用mgarch库）
    # ========================================

    print("\n[阶段2: DCC-GARCH动态相关性模型]")

    # 准备收益率数据：ECM残差 和 期货价格差分
    print("\n[1/2] 准备收益率数据...")

    # ECM残差已经是从ECM回归得到的，对应delta_s_valid的时间点
    # delta_f_valid是同一时间点的期货价格差分
    print(f"  ECM残差样本量: {len(ecm_residuals)}")
    print(f"  期货差分样本量: {len(delta_f_valid)}")

    # 合并为双变量收益率矩阵
    returns_matrix = np.column_stack([ecm_residuals, delta_f_valid])
    print(f"  收益率矩阵形状: {returns_matrix.shape}")

    # 步骤2: 使用mgarch库拟合DCC-GARCH模型
    print("\n[2/2] 拟合DCC-GARCH模型（使用mgarch库）...")

    try:
        # 拟合DCC-GARCH模型（使用t分布更稳健）
        dcc_model = mgarch.mgarch(dist='t')
        dcc_model.fit(returns_matrix)
        print("  ✓ DCC-GARCH模型拟合成功")

        # 使用修正后的函数提取时变条件协方差矩阵
        H_t_valid = get_conditional_covariance(dcc_model)
        print(f"  条件协方差矩阵形状: {H_t_valid.shape}")

        # 提取时变方差和协方差
        var_ecm = H_t_valid[:, 0, 0]  # ECM残差的条件方差
        var_fut = H_t_valid[:, 1, 1]  # 期货差分的条件方差
        cov_ecm_fut = H_t_valid[:, 0, 1]  # 协方差

        # 计算动态相关系数
        rho_t_valid = cov_ecm_fut / np.sqrt(var_ecm * var_fut)

        print(f"  动态相关系数统计:")
        print(f"    均值: {rho_t_valid.mean():.4f}")
        print(f"    标准差: {rho_t_valid.std():.4f}")
        print(f"    范围: [{rho_t_valid.min():.4f}, {rho_t_valid.max():.4f}]")

        # 条件波动率（标准差）
        sigma_ecm_valid = np.sqrt(var_ecm)
        sigma_fut_valid = np.sqrt(var_fut)

    except Exception as e:
        print(f"  ⚠ DCC-GARCH拟合失败: {e}")
        print("  回退到简化方案: 使用固定相关系数")
        # 回退方案：使用固定值
        rho_t_valid = np.full(len(ecm_residuals), 0.5)
        var_ecm = np.full(len(ecm_residuals), ecm_residuals.var())
        var_fut = np.full(len(ecm_residuals), delta_f_valid.var())
        cov_ecm_fut = rho_t_valid * np.sqrt(var_ecm * var_fut)
        sigma_ecm_valid = np.sqrt(var_ecm)
        sigma_fut_valid = np.sqrt(var_fut)

    # 创建完整长度的序列（对齐到原始数据）
    rho_t_full = np.full(T, np.nan)
    sigma_ecm_full = np.full(T, np.nan)
    sigma_fut_full = np.full(T, np.nan)

    # valid_mask对应原始索引2到T-1
    rho_t_full[2:][valid_mask] = rho_t_valid
    sigma_ecm_full[2:][valid_mask] = sigma_ecm_valid
    sigma_fut_full[2:][valid_mask] = sigma_fut_valid

    # ========================================
    # 第三阶段: 计算套保比例
    # ========================================

    print("\n[阶段3: 计算套保比例]")

    # 使用正确的DCC-GARCH套保比率公式:
    # h_t = Cov(ECM残差, 期货差分) / Var(期货差分)
    # 这是最小方差套保比率的理论公式

    h_t_valid = cov_ecm_fut / var_fut

    print(f"  动态套保比率统计:")
    print(f"    均值: {h_t_valid.mean():.4f}")
    print(f"    标准差: {h_t_valid.std():.4f}")
    print(f"    范围: [{h_t_valid.min():.4f}, {h_t_valid.max():.4f}]")

    # 创建完整长度的序列（对齐到原始数据）
    h_t_full = np.full(T, np.nan)
    h_t_full[2:][valid_mask] = h_t_valid

    # 税点调整（使用常量）
    h_actual = h_t_full / TAX_ADJUSTMENT_FACTOR

    # 平滑处理
    window_smooth = 5
    h_actual_smooth = pd.Series(h_actual).rolling(
        window=window_smooth,
        center=True,
        min_periods=1
    ).mean().values

    # 确保没有NaN（用基础套保比例填充）
    h_actual_smooth = np.nan_to_num(h_actual_smooth, nan=h_ecm)

    # 处理异常值（使用分位数方法）
    h_valid = h_actual_smooth[~np.isnan(h_actual_smooth)]
    if len(h_valid) > 0:
        lower_bound = np.percentile(h_valid, 1)   # 1分位数作为下界
        upper_bound = np.percentile(h_valid, 99)  # 99分位数作为上界
        h_actual_final = np.clip(h_actual_smooth, lower_bound, upper_bound)
        h_actual_final = np.maximum(h_actual_final, 0)  # 确保非负
    else:
        h_actual_final = h_actual_smooth

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual_final.mean():.4f}")
    print(f"  标准差: {h_actual_final.std():.4f}")
    print(f"  最小值: {h_actual_final.min():.4f}")
    print(f"  最大值: {h_actual_final.max():.4f}")
    print(f"  中位数: {np.median(h_actual_final):.4f}")

    # 有效性评估
    print("\n[有效性评估]")

    # 对齐 h_actual 到有效样本
    h_aligned = h_actual[2:][valid_mask]

    # 计算未套保收益率
    # R_u = ΔS / S_{t-1}
    returns_unhedged = delta_s_valid / spot[1:-1][valid_mask]

    # 计算套保后组合收益率
    # R_h = (ΔS - h·ΔF) / S_{t-1}
    returns_hedged = (delta_s_valid - h_aligned * delta_f_valid) / spot[1:-1][valid_mask]

    # 计算方差
    var_unhedged = returns_unhedged.var()
    var_hedged = returns_hedged.var()

    # 套保有效性（Ederington指标）
    hedging_effectiveness = 1 - var_hedged / var_unhedged if var_unhedged != 0 else 0

    print(f"\n  Ederington套保有效性指标:")
    print(f"    HE = 1 - Var(R_h) / Var(R_u)")
    print(f"    Var(R_u) = {var_unhedged:.6f}")
    print(f"    Var(R_h) = {var_hedged:.6f}")
    print(f"    HE = {hedging_effectiveness:.4f} ({hedging_effectiveness*100:.2f}%)")

    # 有效性评估
    if hedging_effectiveness > 0.9:
        print(f"  ✓ 套保效果: 优秀 (HE > 90%)")
    elif hedging_effectiveness > 0.8:
        print(f"  ✓ 套保效果: 良好 (80% < HE < 90%)")
    elif hedging_effectiveness > 0.7:
        print(f"  ⚠ 套保效果: 一般 (70% < HE < 80%)")
    else:
        print(f"  ⚠ 套保效果: 较差 (HE < 70%)")

    # 方差减少率
    variance_reduction = (var_unhedged - var_hedged) / var_unhedged
    print(f"\n  方差减少率: {variance_reduction:.4f} ({variance_reduction*100:.2f}%)")

    # 保存评估结果
    evaluation_results = {
        'hedging_effectiveness': hedging_effectiveness,
        'variance_reduction': variance_reduction,
        'var_unhedged': var_unhedged,
        'var_hedged': var_hedged
    }

    # 保存结果
    print("\n[保存结果]")

    # 创建输出DataFrame
    output_df = pd.DataFrame({
        'date': data['date'].values,
        'h_theoretical': h_t_full,
        'h_actual': h_actual_final,
        'h_ecm_base': h_ecm,
        'rho_t': rho_t_full,
        'ect': ect,
        'beta0': beta0_series,
        'beta1': beta1_series,
        'r_squared_coint': r_squared_series,
        'sigma_ecm': sigma_ecm_full,
        'sigma_f': sigma_fut_full,
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
        'h_theoretical': h_t_full,
        'h_ecm_base': h_ecm,
        'rho_t': rho_t_valid,  # 只返回有效数据的动态相关系数
        'ect': ect,
        'beta0_series': beta0_series,
        'beta1_series': beta1_series,
        'sigma_ecm': sigma_ecm_full,
        'sigma_f': sigma_fut_full,
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
            'rho_mean': rho_t_valid.mean(),
            'rho_std': rho_t_valid.std()
        },
        'garch_params': {},  # mgarch模型参数不直接暴露
        'evaluation': evaluation_results,  # 套保有效性评估
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
