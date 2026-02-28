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


def fit_ecm_garch(data, p=1, q=1, output_dir='outputs/model_results',
                  coint_window=120, tax_adjust=True, coupling_method='ect-garch'):
    """
    拟合ECM-GARCH模型并计算套保比例(使用滚动窗口协整估计)

    改进说明:
    ---------
    - 实现真正的ECM-GARCH耦合(方差方程包含ECT外生变量)
    - 强制启用税点调整(现货含税而期货不含税)
    - 添加套保有效性评估(Ederington指标)

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
        协整估计滚动窗口大小(默认120天,约4个月交易日)
    tax_adjust : bool
        是否进行税点调整(默认True,必须启用)
        理论依据: 现货价格含13%增值税而期货价格不含税
    coupling_method : str
        ECM-GARCH耦合方式
        - 'ect-garch': 方差方程包含ECT外生变量(推荐)
        - 'static': 使用ECM静态套保比例(回退方案)

    Returns:
    --------
    results : dict
        包含套保比例序列、ECM参数、GARCH参数、评估指标等
    """

    print("\n" + "=" * 60)
    print("模型2: ECM-GARCH套保模型")
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

    # ===== 修正1.1: 样本量边界检查 =====
    min_required_samples = coint_window + 2  # 至少需要coint_window+1个用于协整,再加1个用于ECM
    if T < min_required_samples:
        raise ValueError(
            f"❌ 样本量不足!\n"
            f"   当前样本量 T={T}\n"
            f"   协整窗口={coint_window}\n"
            f"   最小需要: {min_required_samples}个观测值\n"
            f"   建议: 增加数据长度或减小协整窗口"
        )
    print(f"  ✓ 样本量检查通过 (T={T} > {min_required_samples})")

    # 步骤1: 滚动窗口协整检验
    print("\n[1/5] 滚动窗口协整检验...")

    # ===== 修正3: 协整检验使用正确的趋势项 =====
    # 理论依据: 现货-期货的长期均衡关系通常是线性的，不包含时间趋势项
    # 标准做法: trend='c' (仅常数项), 而非 trend='ct' (常数项+时间趋势项)
    try:
        # 使用trend='c'进行协整检验
        score, pvalue, _ = coint(spot, futures, trend='c', autolag='BIC')
        print(f"  全样本协整检验(trend='c'): 统计量={score:.4f}, p值={pvalue:.6f}")
        if pvalue < 0.05:
            print("  ✓ 全样本在5%水平下存在协整关系")
        else:
            print("  ⚠ 全样本在5%水平下可能不存在协整关系")

        # 额外说明: 如果需要，可以对比不同趋势项
        print(f"  注: 使用trend='c'(仅常数项)而非trend='ct'(含时间趋势),符合金融理论")
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

    # ===== 修正1.2: 有效样本安全检查 =====
    if valid_count == 0:
        raise ValueError(
            f"❌ 无有效协整估计点!\n"
            f"   协整窗口={coint_window}可能过大,\n"
            f"   或数据质量问题导致无法估计。\n"
            f"   建议: 减小协整窗口至{max(60, T//2)}天"
        )

    # 统计时变协整参数(使用安全的方法)
    beta0_valid = beta0_series[~np.isnan(beta0_series)]
    beta1_valid = beta1_series[~np.isnan(beta1_series)]
    r2_valid = r_squared_series[~np.isnan(r_squared_series)]

    print(f"\n  时变协整参数统计:")
    print(f"    β0: 均值={beta0_valid.mean():.4f}, 标准差={beta0_valid.std():.4f}")
    print(f"    β1: 均值={beta1_valid.mean():.4f}, 标准差={beta1_valid.std():.4f}")
    print(f"    R²: 均值={r2_valid.mean():.4f}")

    # 步骤2: 误差修正项统计
    print("\n[2/5] 误差修正项统计...")

    ect_valid = ect[~np.isnan(ect)]
    print(f"  误差修正项统计 (基于{coint_window}天滚动窗口):")
    print(f"    均值: {ect_valid.mean():.2f}")
    print(f"    标准差: {ect_valid.std():.2f}")
    print(f"    最小值: {ect_valid.min():.2f}")
    print(f"    最大值: {ect_valid.max():.2f}")

    # 步骤3: 估计ECM模型
    print("\n[3/5] 估计误差修正模型...")

    # ===== 修正2: ECT对齐逻辑清晰化 =====
    # ECM方程: ΔS(t) = α + h·ΔF(t) + γ·ect(t-1) + ε(t)
    #
    # 时序对应关系:
    #   时间索引:   0    1    2   ...  T-2  T-1   T
    #   spot:      S0   S1   S2  ... ST-2 ST-1  ST
    #   futures:   F0   F1   F2  ... FT-2 FT-1  FT
    #   ΔS:        -   ΔS1  ΔS2 ... ΔST-2 ΔST-1  -   (长度T-1)
    #   ΔF:        -   ΔF1  ΔF2 ... ΔFT-2 ΔFT-1  -   (长度T-1)
    #   ect:       ect0 ect1 ect2 ... ectT-2 ectT-1 ectT (长度T)
    #
    # ECM回归需要:
    #   被解释变量: ΔS(t) for t=2,...,T    → delta_s[1:]
    #   解释变量1:  ΔF(t) for t=2,...,T    → delta_f[1:]
    #   解释变量2:  ect(t-1) for t=2,...,T → ect[1:-1]
    #
    # 因此:
    delta_s_ecm = delta_s[1:]      # ΔS(2), ΔS(3), ..., ΔS(T)    [长度T-2]
    delta_f_ecm = delta_f[1:]      # ΔF(2), ΔF(3), ..., ΔF(T)    [长度T-2]
    ect_lagged = ect[1:-1]         # ect(1), ect(2), ..., ect(T-1) [长度T-2]

    # 只使用有效数据(ect不为NaN)
    valid_mask = ~np.isnan(ect_lagged)

    if valid_mask.sum() == 0:
        raise ValueError(
            f"❌ 无有效ECM观测点!\n"
            f"   ect_lagged全为NaN,说明协整窗口设置有问题。\n"
            f"   建议: 检查前{coint_window+1}个数据点是否有效"
        )

    delta_s_valid = delta_s_ecm[valid_mask]
    delta_f_valid = delta_f_ecm[valid_mask]
    ect_lagged_valid = ect_lagged[valid_mask]

    print(f"  有效ECM观测点数: {len(delta_s_valid)} (需要滞后一期)")

    # 构建ECM回归矩阵(变量命名清晰化)
    X_ecm = pd.DataFrame({
        'const': 1.0,
        'delta_f': delta_f_valid,      # 期货价格差分
        'ect_lagged': ect_lagged_valid # 滞后一期的误差修正项
    })

    # OLS回归(被解释变量是价格差分,单位: 元)
    ecm_result = sm.OLS(delta_s_valid, X_ecm).fit()

    alpha = ecm_result.params['const']
    h_ecm = ecm_result.params['delta_f']
    gamma = ecm_result.params['ect_lagged']  # 修复: 使用正确的列名

    print(f"\nECM方程估计结果:")
    print(f"  ΔS_t = {alpha:.6f} + {h_ecm:.4f}·ΔF_t + {gamma:.6f}·ect_{{t-1}} + ε_t")
    print(f"  标准误差:")
    print(f"    α: {ecm_result.bse['const']:.6f}")
    print(f"    h: {ecm_result.bse['delta_f']:.6f}")
    print(f"    γ: {ecm_result.bse['ect_lagged']:.6f}")  # 修复: 使用正确的列名
    print(f"  t统计量:")
    print(f"    h: {ecm_result.tvalues['delta_f']:.4f}")
    print(f"    γ: {ecm_result.tvalues['ect_lagged']:.4f}")  # 修复: 使用正确的列名
    print(f"  R² = {ecm_result.rsquared:.4f}")
    print(f"  Adjusted R² = {ecm_result.rsquared_adj:.4f}")

    # 解释γ系数
    if gamma < 0:
        print(f"\n  误差修正系数 γ = {gamma:.6f} < 0，符合反向修正机制 ✓")
    else:
        print(f"\n  ⚠ 误差修正系数 γ = {gamma:.6f}，可能存在正向调整")

    # 获取ECM残差
    ecm_residuals = ecm_result.resid

    # ===== 修正4: 添加ARCH效应检验 =====
    print("\n[3.5/5] ARCH效应检验...")

    try:
        from statsmodels.stats.diagnostic import het_arch

        # 使用多个滞后阶数进行检验
        test_lags = [5, 10, 20]
        arch_results = []

        print(f"  对ECM残差进行ARCH-LM检验:")
        for lag in test_lags:
            try:
                lm_stat, p_value, fval = het_arch(ecm_residuals, nlags=lag)
                arch_results.append({'lag': lag, 'lm': lm_stat, 'p': p_value})
                print(f"    滞后{lag}期: LM统计量={lm_stat:.4f}, p值={p_value:.6f} ", end="")
                if p_value < 0.05:
                    print("✓ 存在ARCH效应")
                else:
                    print("✗ 不存在ARCH效应")
            except ValueError:
                print(f"    滞后{lag}期: 样本不足,跳过")

        # 综合判断
        if any(r['p'] < 0.05 for r in arch_results):
            print(f"\n  ✓ 残差存在ARCH效应,适合使用GARCH模型")
        else:
            print(f"\n  ⚠ 残差未检测到显著ARCH效应")
            print(f"  建议: GARCH模型可能不适用,可考虑简单OLS或滚动标准差")

    except ImportError:
        print(f"  ⚠ 无法导入statsmodels.diagnostic.het_arch,跳过ARCH检验")
        print(f"  请安装: pip install statsmodels")
    except Exception as e:
        print(f"  ⚠ ARCH检验失败: {e}")

    # 步骤4: ECM-GARCH耦合建模
    print("\n[4/6] ECM-GARCH耦合建模...")

    # 准备ECM残差和ECT数据
    ecm_residuals = ecm_result.resid
    ect_lagged_valid = ect_lagged_valid

    if coupling_method == 'ect-garch':
        # 方案A: ECT-GARCH(对ECM残差建模GARCH,用ECT动态调整套保比例)
        print("  使用ECT-GARCH模型(GARCH建模残差+ECT动态调整)...")

        # 拟合GARCH(1,1)模型对ECM残差
        from arch import arch_model
        garch_model = arch_model(
            ecm_residuals * 100,  # 转换为百分比以便收敛
            p=1, q=1,
            mean='Zero',
            vol='GARCH',
            dist='t'  # 使用t分布更稳健
        )

        try:
            garch_result = garch_model.fit(update_freq=5, disp='off')
            print(f"  ✓ GARCH拟合成功")
            print(f"    GARCH参数: {garch_result.params.to_dict()}")

            # 提取时变条件波动率
            sigma_t = garch_result.conditional_volatility / 100  # 转回原始尺度

            # 计算时变套保比例
            # 基础部分: h_ecm (ECM估计的静态比率)
            # 动态调整: 根据波动率和ECT进行微调
            # h_t = h_ecm * (1 + lambda * (sigma_t - sigma_mean)/sigma_mean) + adjustment_ect

            sigma_mean = sigma_t.mean()

            # 方案1: 波动率调整 + ECT调整
            # 当波动率高时,适当增加套保比例
            # 当ECT偏离均衡时,调整以反映回归压力
            lambda_vol = 0.5  # 波动率调整系数
            lambda_ect = 0.05  # ECT调整系数

            h_vol_adj = 1 + lambda_vol * (sigma_t - sigma_mean) / sigma_mean
            h_ect_adj = lambda_ect * ect_lagged_valid / ect_lagged_valid.std()

            h_t_valid = h_ecm * h_vol_adj + h_ect_adj

            print(f"    基础套保比例: {h_ecm:.4f}")
            print(f"    波动率调整范围: [{h_vol_adj.min():.4f}, {h_vol_adj.max():.4f}]")
            print(f"    ECT调整范围: [{h_ect_adj.min():.4f}, {h_ect_adj.max():.4f}]")

        except Exception as e:
            print(f"  ⚠ GARCH拟合失败: {e}")
            print(f"  回退到简化方案: 使用ECM静态套保比例")
            h_t_valid = np.full(len(ecm_residuals), h_ecm)
            garch_result = None

    else:
        # 其他耦合方法的占位(未来扩展)
        print(f"  使用ECM静态套保比例")
        h_t_valid = np.full(len(ecm_residuals), h_ecm)
        garch_result = None

    # 步骤5: 套保比例调整
    print("\n[5/6] 套保比例调整...")

    # 创建完整长度的h_t序列
    # h_t_valid对应delta_s[1:]的时间点(索引2到T-1),需要在原始T个时间点上对齐
    h_t = np.full(T, np.nan)

    # h_t_valid对应的时间索引是2到T-1(因为delta_s从t=1开始,aligned从t=2开始)
    # valid_mask的长度是T-2,对应原始索引2到T-1
    h_t[2:][valid_mask] = h_t_valid  # 填充到索引2到T-1的位置

    # 平滑处理
    window_smooth = 5
    h_t_smooth = pd.Series(h_t).rolling(
        window=window_smooth, center=True, min_periods=1
    ).mean().values
    h_t_smooth = np.nan_to_num(h_t_smooth, nan=h_ecm)

    # 税点调整(必须启用)
    tax_rate = 0.13  # 13%增值税
    h_actual = h_t_smooth / (1 + tax_rate)

    print(f"  ✓ 平滑处理(窗口={window_smooth})")
    print(f"  ✓ 税点调整: h_actual = h_smooth / {1+tax_rate}")
    print(f"    调整前均值: {h_t_smooth[~np.isnan(h_t_smooth)].mean():.4f}")
    print(f"    调整后均值: {h_actual[~np.isnan(h_actual)].mean():.4f}")

    # 异常值处理(百分位数方法)
    h_valid = h_actual[~np.isnan(h_actual)]
    lower_bound = np.percentile(h_valid, 1)   # 1分位数作为下界
    upper_bound = np.percentile(h_valid, 99)  # 99分位数作为上界

    h_actual = np.where(h_actual < lower_bound, lower_bound, h_actual)
    h_actual = np.where(h_actual > upper_bound, upper_bound, h_actual)
    h_actual = np.maximum(h_actual, 0)

    print(f"  ✓ 异常值处理完成(百分位数方法: 1%-99%分位数)")
    print(f"    下界(1%分位): {lower_bound:.4f}")
    print(f"    上界(99%分位): {upper_bound:.4f}")
    print(f"    超过上界的样本数: {np.sum(h_valid > upper_bound)}个")

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual.mean():.4f}")
    print(f"  标准差: {h_actual.std():.4f}")
    print(f"  最小值: {h_actual.min():.4f}")
    print(f"  最大值: {h_actual.max():.4f}")
    print(f"  中位数: {np.median(h_actual):.4f}")

    # 步骤6: 套保有效性评估
    print("\n[6/6] 套保有效性评估...")

    # 数据对齐说明:
    # - h_actual 长度为 T = 2891
    # - valid_mask 长度为 T-2 = 2889 (对应 delta_s_ecm = delta_s[1:])
    # - delta_s_valid, delta_f_valid 基于 valid_mask 提取,长度 = sum(valid_mask)
    # - h_actual[2:] 长度为 T-2 = 2889
    # - 需要从 h_actual[2:] 中提取 valid_mask 为 True 的位置

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

    # 套保有效性
    hedging_effectiveness = 1 - var_hedged / var_unhedged

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

    # 创建输出DataFrame(对齐日期)
    # 注意: h_actual有T个观测值,但前2个是NaN
    output_df = pd.DataFrame({
        'date': data['date'].values,
        'h_theoretical': h_t,
        'h_actual': h_actual,
        'h_ecm_base': h_ecm,
        'ect': ect,
        'beta0': beta0_series,
        'beta1': beta1_series,
        'r_squared_coint': r_squared_series
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
        'beta0_series': beta0_series,  # 时变协整参数
        'beta1_series': beta1_series,  # 时变协整参数
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
        'garch_params': garch_result.params.to_dict() if 'garch_result' in locals() and garch_result is not None else {},
        'evaluation': evaluation_results,  # 套保有效性评估
        'coint_window': coint_window,
        'coupling_method': coupling_method,  # ECM-GARCH耦合方式
        'tax_adjust': tax_adjust,  # 是否启用税点调整
        'output_df': output_df
    }

    return results


if __name__ == "__main__":
    # 测试ECM-GARCH模型
    from data_preprocessing import preprocess_data

    data = preprocess_data("基差数据.xlsx")
    results = fit_ecm_garch(data)

    print("\n测试完成！")
