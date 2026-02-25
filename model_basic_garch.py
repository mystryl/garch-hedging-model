"""
模型1: 基础GARCH套保模型
使用二元GARCH模型估计现货与期货的条件协方差和条件方差
"""

import pandas as pd
import numpy as np
from arch import arch_model
import warnings
warnings.filterwarnings('ignore')


def fit_basic_garch(data, p=1, q=1, output_dir='outputs/model_results'):
    """
    拟合基础GARCH(1,1)模型并计算套保比例

    Parameters:
    -----------
    data : pd.DataFrame
        包含 r_s (现货收益率) 和 r_f (期货收益率) 的数据
    p : int
        GARCH模型的p阶数
    q : int
        GARCH模型的q阶数
    output_dir : str
        输出目录

    Returns:
    --------
    results : dict
        包含套保比例序列、GARCH参数等
    """

    print("\n" + "=" * 60)
    print("模型1: 基础GARCH套保模型")
    print("=" * 60)

    import os
    os.makedirs(output_dir, exist_ok=True)

    # 提取收益率数据
    r_s = data['r_s'].values * 100  # 转换为百分比形式以提高数值稳定性
    r_f = data['r_f'].values * 100

    T = len(r_s)
    print(f"\n样本量: {T}")

    # 分别对现货和期货收益率拟合GARCH(1,1)模型
    print("\n[1/3] 拟合单变量GARCH(1,1)模型...")

    # 现货GARCH模型
    print("  - 拟合现货收益率GARCH模型...")
    model_s = arch_model(r_s, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    try:
        result_s = model_s.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_s.convergence_flag == 0}")
        print(f"    ω = {result_s.params['omega']:.6f}")
        print(f"    α = {result_s.params['alpha[1]']:.6f}")
        print(f"    β = {result_s.params['beta[1]']:.6f}")
    except Exception as e:
        print(f"    ✗ 拟合失败: {e}")
        # 使用更简单的设置
        model_s = arch_model(r_s, p=1, q=1, mean='Constant', vol='GARCH', dist='normal')
        result_s = model_s.fit(disp='off', show_warning=False)

    # 期货GARCH模型
    print("  - 拟合期货收益率GARCH模型...")
    model_f = arch_model(r_f, p=p, q=q, mean='Constant', vol='GARCH', dist='normal')
    try:
        result_f = model_f.fit(disp='off', update_freq=0)
        print(f"    ✓ 收敛: {result_f.convergence_flag == 0}")
        print(f"    ω = {result_f.params['omega']:.6f}")
        print(f"    α = {result_f.params['alpha[1]']:.6f}")
        print(f"    β = {result_f.params['beta[1]']:.6f}")
    except Exception as e:
        print(f"    ✗ 拟合失败: {e}")
        model_f = arch_model(r_f, p=1, q=1, mean='Constant', vol='GARCH', dist='normal')
        result_f = model_f.fit(disp='off', show_warning=False)

    # 获取条件方差和条件标准差
    sigma_s = result_s.conditional_volatility / 100  # 转回原始单位
    sigma_f = result_f.conditional_volatility / 100

    # 获取标准化残差
    resid_s = result_s.resid / 100
    resid_f = result_f.resid / 100

    # 计算相关系数（使用滚动窗口估计动态相关系数）
    print("\n[2/3] 计算动态协方差...")

    # 方法1: 使用恒定相关系数（简化方法）
    corr_const = np.corrcoef(resid_s[1:], resid_f[1:])[0, 1]
    print(f"  恒定相关系数: {corr_const:.6f}")

    # 方法2: 使用滚动窗口估计动态相关系数
    window = 60  # 60天滚动窗口
    rolling_corr = pd.Series(index=range(T), dtype=float)

    for t in range(window, T):
        rolling_corr.iloc[t] = np.corrcoef(resid_s[t-window+1:t+1], resid_f[t-window+1:t+1])[0, 1]

    # 前window个数据点使用整体相关系数填充
    rolling_corr.iloc[:window] = corr_const

    # 计算条件协方差
    cov_sf = rolling_corr.values * sigma_s * sigma_f

    # 计算条件方差（期货）
    var_f = sigma_f ** 2

    # 计算套保比例
    print("\n[3/3] 计算套保比例...")
    h_t = cov_sf / var_f  # 理论套保比例

    # 税点调整（考虑13%增值税）
    h_actual = h_t / 1.13

    # 处理异常值
    h_actual = np.clip(h_actual, 0, 2)  # 限制在[0, 2]范围内

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
        'sigma_s': sigma_s,
        'sigma_f': sigma_f,
        'cov_sf': cov_sf,
        'var_f': var_f
    })

    output_path = f"{output_dir}/h_basic_garch.csv"
    output_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  ✓ 已保存: {output_path}")

    print("\n" + "=" * 60)
    print("✓ 模型1拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'Basic GARCH',
        'h_actual': h_actual,
        'h_theoretical': h_t,
        'sigma_s': sigma_s,
        'sigma_f': sigma_f,
        'cov_sf': cov_sf,
        'var_f': var_f,
        'params_spot': result_s.params.to_dict(),
        'params_futures': result_f.params.to_dict(),
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试基础GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_basic_garch(data)

    print("\n测试完成！")
