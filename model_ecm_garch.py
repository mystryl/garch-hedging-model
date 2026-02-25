"""
模型2: ECM-GARCH套保模型
考虑现货与期货的长期均衡关系（误差修正模型）
"""

import pandas as pd
import numpy as np
from arch import arch_model
from statsmodels.tsa.stattools import coint
import statsmodels.api as sm
import warnings
warnings.filterwarnings('ignore')


def fit_ecm_garch(data, p=1, q=1, output_dir='outputs/model_results'):
    """
    拟合ECM-GARCH模型并计算套保比例

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
        包含套保比例序列、ECM参数、GARCH参数等
    """

    print("\n" + "=" * 60)
    print("模型2: ECM-GARCH套保模型")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 提取数据
    spot = data['spot'].values
    futures = data['futures'].values
    r_s = data['r_s'].values * 100  # 转换为百分比
    r_f = data['r_f'].values * 100

    T = len(r_s)
    print(f"\n样本量: {T}")

    # 步骤1: 协整检验
    print("\n[1/5] 协整检验...")

    try:
        # 使用Engle-Granger两步法
        score, pvalue, _ = coint(spot, futures, trend='ct', autolag='BIC')
        print(f"  Engle-Granger协整检验统计量: {score:.4f}")
        print(f"  p值: {pvalue:.6f}")

        if pvalue < 0.05:
            print("  ✓ 在5%水平下存在协整关系")
        else:
            print("  ⚠ 在5%水平下可能不存在协整关系，但继续进行ECM分析")
    except Exception as e:
        print(f"  ⚠ 协整检验失败: {e}")

    # 步骤2: 构建误差修正项
    print("\n[2/5] 构建误差修正项...")

    # 长期均衡关系: spot = β0 + β1 * futures + ε
    # 使用OLS回归估计协整向量
    X = sm.add_constant(futures)
    ecm_model = sm.OLS(spot, X).fit()

    beta0 = ecm_model.params[0]
    beta1 = ecm_model.params[1]

    print(f"  长期均衡方程: spot = {beta0:.2f} + {beta1:.4f} * futures")
    print(f"  R² = {ecm_model.rsquared:.4f}")

    # 计算误差修正项（基差的长期均衡偏离）
    ect = spot - (beta0 + beta1 * futures)

    print(f"\n误差修正项统计:")
    print(f"  均值: {ect.mean():.2f}")
    print(f"  标准差: {ect.std():.2f}")

    # 步骤3: 估计ECM模型
    print("\n[3/5] 估计误差修正模型...")

    # ECM方程: ΔS_t = α + h·ΔF_t + γ·ect_{t-1} + ε_t
    # 准备数据（滞后一期）
    ect_lag = ect[:-1]
    r_s_current = r_s[1:]
    r_f_current = r_f[1:]

    # 构建ECM回归矩阵
    X_ecm = pd.DataFrame({
        'const': 1.0,
        'delta_f': r_f_current,
        'ect_lag': ect_lag
    })

    # OLS回归
    ecm_result = sm.OLS(r_s_current, X_ecm).fit()

    alpha = ecm_result.params['const']
    h_ecm = ecm_result.params['delta_f']
    gamma = ecm_result.params['ect_lag']

    print(f"\nECM方程估计结果:")
    print(f"  ΔS_t = {alpha:.6f} + {h_ecm:.4f}·ΔF_t + {gamma:.6f}·ect_{{t-1}} + ε_t")
    print(f"  标准误差:")
    print(f"    α: {ecm_result.bse['const']:.6f}")
    print(f"    h: {ecm_result.bse['delta_f']:.6f}")
    print(f"    γ: {ecm_result.bse['ect_lag']:.6f}")
    print(f"  t统计量:")
    print(f"    h: {ecm_result.tvalues['delta_f']:.4f}")
    print(f"    γ: {ecm_result.tvalues['ect_lag']:.4f}")
    print(f"  R² = {ecm_result.rsquared:.4f}")
    print(f"  Adjusted R² = {ecm_result.rsquared_adj:.4f}")

    # 解释γ系数
    if gamma < 0:
        print(f"\n  误差修正系数 γ = {gamma:.6f} < 0，符合反向修正机制 ✓")
    else:
        print(f"\n  ⚠ 误差修正系数 γ = {gamma:.6f}，可能存在正向调整")

    # 获取ECM残差
    ecm_residuals = ecm_result.resid

    # 步骤4: 对ECM残差拟合GARCH模型
    print("\n[4/5] 对ECM残差拟合GARCH模型...")

    try:
        arch_model_ecm = arch_model(ecm_residuals, p=p, q=q, mean='Zero',
                                    vol='GARCH', dist='normal')
        garch_result = arch_model_ecm.fit(disp='off', update_freq=0)

        print(f"  ✓ GARCH拟合收敛: {garch_result.convergence_flag == 0}")
        print(f"  ω = {garch_result.params['omega']:.8f}")
        print(f"  α = {garch_result.params['alpha[1]']:.6f}")
        print(f"  β = {garch_result.params['beta[1]']:.6f}")

        # 获取条件波动率
        conditional_vol = garch_result.conditional_volatility / 100  # 转回原始单位

    except Exception as e:
        print(f"  ⚠ GARCH拟合失败: {e}")
        print(f"  使用简单标准差作为波动率估计")
        # 使用滚动标准差作为替代
        window = 30
        cond_vol_series = pd.Series(ecm_residuals).rolling(window=window, min_periods=1).std()
        conditional_vol = cond_vol_series.values / 100

    # 步骤5: 计算套保比例
    print("\n[5/5] 计算套保比例...")

    # ECM-GARCH的套保比例由两部分组成：
    # 1. ECM部分: h_ecm（来自误差修正模型）
    # 2. 时变调整: 基于条件波动率的动态调整

    # 获取期货的条件波动率（用GARCH估计）
    try:
        arch_model_f = arch_model(r_f, p=p, q=q, mean='Constant',
                                  vol='GARCH', dist='normal')
        garch_f = arch_model_f.fit(disp='off', update_freq=0)
        sigma_f = garch_f.conditional_volatility / 100
    except:
        # 使用滚动标准差
        window = 30
        sigma_f = pd.Series(r_f).rolling(window=window).std().values / 100
        sigma_f[:window] = r_f[:window].std() / 100

    # 动态套保比例
    # 基本思路: h_t = h_ecm * (sigma_ecm / sigma_f)^2
    # 其中sigma_ecm来自ECM残差的GARCH模型

    # 对齐长度（ECM回归少一个观测值）
    sigma_f_aligned = sigma_f[1:]

    # 时变套保比例
    h_t = h_ecm * (conditional_vol / sigma_f_aligned)**2
    h_t = np.nan_to_num(h_t, nan=h_ecm)  # 处理NaN值

    # 平滑处理（使用移动平均）
    window_smooth = 5
    h_t_smooth = pd.Series(h_t).rolling(window=window_smooth, center=True, min_periods=1).mean().values
    # 确保没有NaN
    h_t_smooth = np.nan_to_num(h_t_smooth, nan=h_t)

    # 税点调整
    h_actual = h_t_smooth / 1.13

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

    # 创建输出DataFrame（对齐日期）
    output_df = pd.DataFrame({
        'date': data['date'].values[1:],  # ECM回归少一个观测值
        'h_theoretical': h_t,
        'h_actual': h_actual,
        'h_ecm_base': h_ecm,
        'ect': ect[1:],
        'sigma_ecm': conditional_vol,
        'sigma_f': sigma_f_aligned
    })

    output_path = f"{output_dir}/h_ecm_garch.csv"
    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {output_path}")

    print("\n" + "=" * 60)
    print("✓ 模型2拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'ECM-GARCH',
        'h_actual': h_actual,
        'h_theoretical': h_t,
        'h_ecm_base': h_ecm,
        'ect': ect,
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
        'garch_params': garch_result.params.to_dict() if 'garch_result' in locals() else {},
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试ECM-GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_ecm_garch(data)

    print("\n测试完成！")
