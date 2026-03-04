"""
ECM-GARCH 模型核心实现
从 model_ecm_garch.py 迁移
"""
import pandas as pd
import numpy as np
import warnings
import os
warnings.filterwarnings('ignore')


def fit_ecm_garch(
    data,
    output_dir='outputs/model_results',
    coint_window=60,
    coupling_method='ect-garch',
    tax_adjust=True,
    config=None
):
    """
    拟合ECM-GARCH套保模型

    模型流程：
    1. 对数价格协整检验
    2. 滚动窗口协整估计（时变协整系数）
    3. ECM误差修正模型估计
    4. ECM-GARCH耦合建模（对ECM残差拟合GARCH）
    5. 套保比例计算与调整
    6. 套保有效性评估

    Parameters:
    -----------
    data : pd.DataFrame
        包含 price_s, price_f 的价格数据
    output_dir : str
        输出目录
    coint_window : int
        协整检验滚动窗口大小（默认60天）
    coupling_method : str
        ECM-GARCH耦合方式，'ect-garch'表示对ECM残差拟合GARCH并用ECT动态调整
    tax_adjust : bool
        是否启用税点调整（默认启用）
    config : ECMGarchConfig, optional
        配置对象

    Returns:
    --------
    results : dict
        包含套保比例序列、ECT序列、协整参数等
    """

    print("\n" + "=" * 60)
    print("模型: ECM-GARCH套保模型（误差修正模型+GARCH）")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # 提取价格数据
    if 'price_s' not in data.columns or 'price_f' not in data.columns:
        raise ValueError("输入数据必须包含 'price_s' 和 'price_f' 列（价格数据）")

    price_s = data['price_s'].values
    price_f = data['price_f'].values

    T = len(price_s)
    print(f"\n样本量: {T}")

    # 步骤1: 对数价格协整检验
    print("\n[1/6] 对数价格协整检验...")

    log_s = np.log(price_s)
    log_f = np.log(price_f)

    # Engle-Granger两步法
    # 第一步: 静态回归 log_s = beta0 + beta1 * log_f + epsilon
    from scipy import stats
    slope, intercept, r_value, p_value, std_err = stats.linregress(log_f, log_s)

    print(f"  静态回归结果:")
    print(f"    log_s = {intercept:.4f} + {slope:.4f} * log_f")
    print(f"    R-squared = {r_value**2:.4f}")

    # 第二步: ADF检验残差平稳性
    residuals = log_s - (intercept + slope * log_f)

    try:
        from statsmodels.tsa.stattools import adfuller
        adf_result = adfuller(residuals, maxlag=10, regression='c')
        adf_statistic = adf_result[0]
        adf_pvalue = adf_result[1]
        adf_critical_5 = adf_result[4]['5%']

        print(f"\n  ADF检验结果:")
        print(f"    ADF统计量: {adf_statistic:.4f}")
        print(f"    5%临界值: {adf_critical_5:.4f}")
        print(f"    p值: {adf_pvalue:.4f}")

        if adf_statistic < adf_critical_5:
            print(f"  ✓ 残差平稳 (p<{adf_pvalue:.4f})，存在协整关系")
        else:
            print(f"  ⚠ 残差可能非平稳，协整关系较弱")
    except ImportError:
        print(f"  ⚠ 无法导入statsmodels.tsa.stattools.adfuller,跳过ADF检验")
        print(f"  请安装: pip install statsmodels")
    except Exception as e:
        print(f"  ⚠ ADF检验失败: {e}")

    # 步骤2: 滚动窗口协整估计（时变协整系数）
    print(f"\n[2/6] 滚动窗口协整估计（窗口={coint_window}天）...")

    # 初始化时变参数序列
    beta0_series = np.full(T, np.nan)
    beta1_series = np.full(T, np.nan)
    r_squared_series = np.full(T, np.nan)

    # 滚动窗口估计
    for i in range(coint_window, T):
        window_log_s = log_s[i-coint_window:i]
        window_log_f = log_f[i-coint_window:i]

        slope, intercept, r_value, p_value, std_err = stats.linregress(
            window_log_f, window_log_s
        )

        beta0_series[i] = intercept
        beta1_series[i] = slope
        r_squared_series[i] = r_value**2

    print(f"  ✓ 滚动协整估计完成")
    print(f"    beta0: 均值={beta0_series[~np.isnan(beta0_series)].mean():.4f}, " +
          f"标准差={beta0_series[~np.isnan(beta0_series)].std():.4f}")
    print(f"    beta1: 均值={beta1_series[~np.isnan(beta1_series)].mean():.4f}, " +
          f"标准差={beta1_series[~np.isnan(beta1_series)].std():.4f}")

    # 步骤3: ECM误差修正模型估计
    print("\n[3/6] ECM误差修正模型估计...")

    # 准备ECM数据
    # 误差修正项（ECT）：协整残差（滞后1期）
    ect = pd.Series(log_s - (beta0_series + beta1_series * log_f))
    ect_lagged = ect.shift(1)  # 滞后1期

    # 对数收益率（差分）
    delta_s = np.diff(log_s, prepend=log_s[0])  # 现货收益率
    delta_f = np.diff(log_f, prepend=log_f[0])  # 期货收益率

    # 创建ECM回归DataFrame
    ecm_data = pd.DataFrame({
        'delta_s': delta_s,
        'delta_f': delta_f,
        'ect_lagged': ect_lagged
    }).dropna()  # 移除前2个NaN（ect_lagged产生1个，diff产生1个）

    # 提取有效样本
    r_spot_ecm = ecm_data['delta_s'].values
    r_futures_ecm = ecm_data['delta_f'].values
    ect_lagged_valid = ecm_data['ect_lagged'].values

    # 有效样本掩码（用于后续对齐）
    valid_mask = np.arange(len(r_spot_ecm))

    # ECM回归: delta_s = alpha + h * delta_f + gamma * ect_lagged + epsilon
    import statsmodels.api as sm
    X_ecm = sm.add_constant(np.column_stack([r_futures_ecm, ect_lagged_valid]))
    ecm_model = sm.OLS(r_spot_ecm, X_ecm)
    ecm_result = ecm_model.fit()

    alpha = ecm_result.params[0]
    h_ecm = ecm_result.params[1]
    gamma = ecm_result.params[2]

    print(f"  ✓ ECM回归结果:")
    print(f"    delta_s = {alpha:.6f} + {h_ecm:.4f} * delta_f + {gamma:.6f} * ect_lagged")
    print(f"    R-squared = {ecm_result.rsquared:.4f}")
    print(f"    gamma系数（误差修正速度）: {gamma:.6f}")

    # 解释gamma系数
    if gamma < -0.5:
        print(f"    ✓ 误差修正速度较快（|gamma| > 0.5）")
    elif gamma < -0.1:
        print(f"    ✓ 误差修正速度适中（0.1 < |gamma| < 0.5）")
    elif gamma < 0:
        print(f"    ⚠ 误差修正速度较慢（|gamma| < 0.1）")
    else:
        print(f"    ⚠ gamma为正，可能不符合误差修正模型预期")

    # 残差诊断
    print(f"\n  ECM残差诊断:")
    print(f"    JB检验正态性 p值: {ecm_result.diagnostic['jaque'][1]:.4f}")
    print(f"    Durbin-Watson统计量: {ecm_result.diagnostic['durbin_watson']:.4f}")

    try:
        from statsmodels.stats.diagnostic import het_arch
        arch_test = het_arch(ecm_result.resid)
        print(f"    ARCH效应检验 p值: {arch_test[1]:.4f}")
        if arch_test[1] < 0.05:
            print(f"    ✓ 存在显著ARCH效应，适合使用GARCH模型")
    except ImportError:
        print(f"  ⚠ 无法导入statsmodels.diagnostic.het_arch,跳过ARCH检验")
        print(f"  请安装: pip install statsmodels")
    except Exception as e:
        print(f"  ⚠ ARCH检验失败: {e}")

    # 步骤4: ECM-GARCH耦合建模
    print("\n[4/6] ECM-GARCH耦合建模...")

    # 准备ECM残差和ECT数据
    ecm_residuals = ecm_result.resid

    if coupling_method == 'ect-garch':
        # 方案A: ECT-GARCH(对ECM残差建模GARCH,用ECT动态调整套保比例)
        print("  使用ECT-GARCH模型(GARCH建模残差+ECT动态调整)...")
        print("  注: GARCH建模对象为对数收益率的ECM残差")

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
            sigma_mean = sigma_t.mean()

            # 波动率调整 + ECT调整
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
    h_t = np.full(T, np.nan)
    h_t[2:][valid_mask] = h_t_valid

    # 平滑处理
    window_smooth = 5
    h_t_smooth = pd.Series(h_t).rolling(
        window=window_smooth, center=True, min_periods=1
    ).mean().values
    h_t_smooth = np.nan_to_num(h_t_smooth, nan=h_ecm)

    # 税点调整
    if tax_adjust:
        tax_rate = 0.13  # 13%增值税
        h_actual = h_t_smooth / (1 + tax_rate)
        print(f"  ✓ 税点调整: h_actual = h_smooth / {1+tax_rate}")
    else:
        h_actual = h_t_smooth
        print(f"  未启用税点调整")

    print(f"    调整前均值: {h_t_smooth[~np.isnan(h_t_smooth)].mean():.4f}")
    print(f"    调整后均值: {h_actual[~np.isnan(h_actual)].mean():.4f}")

    # 异常值处理
    h_valid = h_actual[~np.isnan(h_actual)]
    lower_bound = np.percentile(h_valid, 1)
    upper_bound = np.percentile(h_valid, 99)

    h_actual = np.where(h_actual < lower_bound, lower_bound, h_actual)
    h_actual = np.where(h_actual > upper_bound, upper_bound, h_actual)
    h_actual = np.maximum(h_actual, 0)

    print(f"  ✓ 异常值处理完成(百分位数方法: 1%-99%分位数)")

    print(f"\n套保比例统计:")
    print(f"  均值: {h_actual.mean():.4f}")
    print(f"  标准差: {h_actual.std():.4f}")
    print(f"  最小值: {h_actual.min():.4f}")
    print(f"  最大值: {h_actual.max():.4f}")

    # 步骤6: 套保有效性评估
    print("\n[6/6] 套保有效性评估...")

    # 对齐 h_actual 到有效样本
    h_aligned = h_actual[2:][valid_mask]

    # 使用对数收益率计算套保效果
    returns_unhedged = r_spot_ecm
    returns_hedged = r_spot_ecm - h_aligned * r_futures_ecm

    var_unhedged = returns_unhedged.var()
    var_hedged = returns_hedged.var()
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

    # 处理date列
    if 'date' in data.columns:
        dates = data['date'].values
    else:
        dates = data.index.values

    output_df = pd.DataFrame({
        'date': dates,
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
    print("✓ ECM-GARCH模型拟合完成！")
    print("=" * 60)

    results = {
        'model_name': 'ECM-GARCH',
        'h_actual': h_actual,
        'h_theoretical': h_t,
        'h_ecm_base': h_ecm,
        'ect': ect,
        'beta0_series': beta0_series,
        'beta1_series': beta1_series,
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
        'garch_params': garch_result.params.to_dict() if garch_result is not None else {},
        'evaluation': evaluation_results,
        'coint_window': coint_window,
        'coupling_method': coupling_method,
        'tax_adjust': tax_adjust,
        'output_df': output_df
    }

    return results
