"""
Basic GARCH 套保模型
基于单变量 GARCH(1,1) 模型估计时变套保比例
"""

import pandas as pd
import numpy as np
from arch import arch_model
import warnings
warnings.filterwarnings('ignore')


def fit_basic_garch(data, p=1, q=1, corr_window=120, tax_rate=0.13):
    """
    拟合基础 GARCH(1,1) 模型并计算套保比例

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s (现货收益率) 和 r_f (期货收益率) 的数据
    p : int
        GARCH 模型的 p 阶数
    q : int
        GARCH 模型的 q 阶数
    corr_window : int
        动态相关系数滚动窗口大小（默认120天）
    tax_rate : float
        税点调整比例（默认0.13，即13%增值税）

    Returns:
    --------
    results : dict
        包含套保比例序列、GARCH 参数等
    """

    print("\n" + "=" * 60)
    print("Basic GARCH 模型拟合")
    print("=" * 60)

    # 提取收益率数据
    r_s = data['r_s'].values * 100  # 转换为百分比形式以提高数值稳定性
    r_f = data['r_f'].values * 100

    T = len(r_s)
    print(f"\n样本量: {T}")
    print(f"相关系数窗口: {corr_window} 天")
    print(f"税点调整: {tax_rate:.1%}")

    # 步骤1: 拟合单变量 GARCH(1,1) 模型
    print("\n[步骤 1/3] 拟合单变量 GARCH(1,1) 模型...")

    # 现货 GARCH 模型
    print("  - 拟合现货收益率 GARCH 模型...")
    model_s = arch_model(r_s, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    try:
        result_s = model_s.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_s.convergence_flag == 0}")
        print(f"    ω = {result_s.params['omega']:.6f}")
        print(f"    α = {result_s.params['alpha[1]']:.6f}")
        print(f"    β = {result_s.params['beta[1]']:.6f}")
        print(f"    α + β = {result_s.params['alpha[1]'] + result_s.params['beta[1]']:.4f}")
    except Exception as e:
        print(f"    ✗ 拟合失败: {e}")
        raise

    # 期货 GARCH 模型
    print("  - 拟合期货收益率 GARCH 模型...")
    model_f = arch_model(r_f, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    try:
        result_f = model_f.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_f.convergence_flag == 0}")
        print(f"    ω = {result_f.params['omega']:.6f}")
        print(f"    α = {result_f.params['alpha[1]']:.6f}")
        print(f"    β = {result_f.params['beta[1]']:.6f}")
        print(f"    α + β = {result_f.params['alpha[1]'] + result_f.params['beta[1]']:.4f}")
    except Exception as e:
        print(f"    ✗ 拟合失败: {e}")
        raise

    # 获取条件方差和条件标准差
    sigma_s = result_s.conditional_volatility / 100  # 转回原始单位
    sigma_f = result_f.conditional_volatility / 100

    # 获取标准化残差
    resid_s = result_s.resid / 100
    resid_f = result_f.resid / 100

    # 步骤2: 计算动态相关系数
    print("\n[步骤 2/3] 计算动态相关系数...")

    # 方法1: 使用恒定相关系数
    corr_const = np.corrcoef(resid_s[1:], resid_f[1:])[0, 1]
    print(f"  恒定相关系数: {corr_const:.6f}")

    # 方法2: 使用滚动窗口估计动态相关系数
    rolling_corr = pd.Series(index=range(T), dtype=float)

    for t in range(corr_window, T):
        rolling_corr.iloc[t] = np.corrcoef(
            resid_s[t-corr_window+1:t+1],
            resid_f[t-corr_window+1:t+1]
        )[0, 1]

    # 前 corr_window 个数据点使用整体相关系数填充
    rolling_corr.iloc[:corr_window] = corr_const

    print(f"  动态相关系数统计:")
    print(f"    均值: {rolling_corr.mean():.4f}")
    print(f"    标准差: {rolling_corr.std():.4f}")
    print(f"    最小值: {rolling_corr.min():.4f}")
    print(f"    最大值: {rolling_corr.max():.4f}")

    # 计算条件协方差
    cov_sf = rolling_corr.values * sigma_s * sigma_f

    # 计算条件方差（期货）
    var_f = sigma_f ** 2

    # 步骤3: 计算套保比例
    print("\n[步骤 3/3] 计算套保比例...")

    # 理论套保比例: h_t = Cov(r_s, r_f) / Var(r_f)
    h_t = cov_sf / var_f

    # 税点调整: h_actual = h_t / (1 + tax_rate)
    h_actual = h_t / (1 + tax_rate)

    print(f"  税点调整系数: 1 / (1 + {tax_rate}) = {1/(1+tax_rate):.4f}")
    print(f"  调整前均值: {h_t.mean():.4f}")
    print(f"  调整后均值: {h_actual.mean():.4f}")

    # 处理异常值（3σ原则）
    h_mean = h_actual.mean()
    h_std = h_actual.std()
    lower_bound = h_mean - 3 * h_std
    upper_bound = h_mean + 3 * h_std

    h_final = np.clip(h_actual, lower_bound, upper_bound)
    h_final = np.maximum(h_final, 0)  # 确保非负

    print(f"\n套保比例统计 (处理后):")
    print(f"  均值: {h_final.mean():.4f}")
    print(f"  标准差: {h_final.std():.4f}")
    print(f"  最小值: {h_final.min():.4f}")
    print(f"  最大值: {h_final.max():.4f}")
    print(f"  中位数: {np.median(h_final):.4f}")

    print("\n" + "=" * 60)
    print("✓ 模型拟合完成！")
    print("=" * 60)

    # 返回结果
    results = {
        'model_name': 'Basic GARCH',
        'h_theoretical': h_t,
        'h_actual': h_actual,
        'h_final': h_final,
        'sigma_s': sigma_s,
        'sigma_f': sigma_f,
        'cov_sf': cov_sf,
        'var_f': var_f,
        'rolling_corr': rolling_corr.values,
        'params_spot': result_s.params.to_dict(),
        'params_futures': result_f.params.to_dict(),
        'corr_window': corr_window,
        'tax_rate': tax_rate
    }

    return results


def save_model_results(data, results, output_path):
    """
    保存模型结果到 CSV

    Parameters:
    -----------
    data : pd.DataFrame
        原始数据
    results : dict
        模型结果
    output_path : str
        输出文件路径
    """
    print("\n" + "=" * 60)
    print("保存模型结果")
    print("=" * 60)

    # 创建输出 DataFrame
    output_df = pd.DataFrame({
        'date': data['date'].values,
        'spot': data['spot'].values,
        'futures': data['futures'].values,
        'spread': data['spread'].values,
        'r_s': data['r_s'].values,
        'r_f': data['r_f'].values,
        'h_theoretical': results['h_theoretical'],
        'h_actual': results['h_actual'],
        'h_final': results['h_final'],
        'sigma_s': results['sigma_s'],
        'sigma_f': results['sigma_f'],
        'cov_sf': results['cov_sf'],
        'rolling_corr': results['rolling_corr']
    })

    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已保存模型结果: {output_path}")
    print(f"  数据行数: {len(output_df)}")
    print(f"  数据列数: {len(output_df.columns)}")

    return output_df
