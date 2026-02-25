"""
可视化与报告生成模块
生成完整的HTML报告和Excel文件
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def plot_hedge_ratio_comparison(data, model_results, output_dir='outputs/figures'):
    """
    绘制四种模型套保比例对比图
    """
    print("\n[绘图1/2] 套保比例时变对比...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()

    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
    model_names = list(model_results.keys())

    for i, (model_name, color) in enumerate(zip(model_names, colors)):
        ax = axes[i]
        result = model_results[model_name]
        h = result['h_actual']

        # 对齐日期
        dates = data['date'].values[:len(h)]

        ax.plot(dates, h, linewidth=1.5, color=color, alpha=0.8, label=model_name)
        ax.axhline(y=np.mean(h), color='red', linestyle='--',
                   linewidth=1.5, label=f"Mean: {np.mean(h):.3f}")

        ax.set_title(f'{model_name}', fontsize=12, fontweight='bold')
        ax.set_ylabel('Hedge Ratio', fontsize=10)
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)

        # 添加统计信息
        stats_text = f"Mean: {np.mean(h):.3f}\nStd: {np.std(h):.3f}\nMin: {np.min(h):.3f}\nMax: {np.max(h):.3f}"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=8, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(f"{output_dir}/hedge_ratio_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_dir}/hedge_ratio_comparison.png")


def plot_dynamic_correlation(model_results, output_dir='outputs/figures'):
    """
    绘制DCC模型的动态相关系数
    """
    print("\n[绘图2/2] 动态相关系数...")

    # 提取DCC和ECM-DCC-GARCH的动态相关系数
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # DCC-GARCH
    if 'DCC-GARCH' in model_results:
        result = model_results['DCC-GARCH']
        rho_t = result.get('rho_t', None)
        if rho_t is not None:
            axes[0].plot(rho_t, linewidth=1.5, color='steelblue', alpha=0.8)
            axes[0].axhline(y=np.mean(rho_t), color='red', linestyle='--',
                           linewidth=1.5, label=f"Mean: {np.mean(rho_t):.4f}")
            axes[0].set_title('DCC-GARCH: Dynamic Correlation Coefficient',
                             fontsize=12, fontweight='bold')
            axes[0].set_ylabel('Correlation', fontsize=11)
            axes[0].legend(loc='best')
            axes[0].grid(True, alpha=0.3)

    # ECM-DCC-GARCH
    if 'ECM-DCC-GARCH' in model_results:
        result = model_results['ECM-DCC-GARCH']
        rho_t = result.get('rho_t', None)
        if rho_t is not None:
            axes[1].plot(rho_t, linewidth=1.5, color='darkgreen', alpha=0.8)
            axes[1].axhline(y=np.mean(rho_t), color='red', linestyle='--',
                           linewidth=1.5, label=f"Mean: {np.mean(rho_t):.4f}")
            axes[1].set_title('ECM-DCC-GARCH: Dynamic Correlation Coefficient',
                             fontsize=12, fontweight='bold')
            axes[1].set_xlabel('Time', fontsize=11)
            axes[1].set_ylabel('Correlation', fontsize=11)
            axes[1].legend(loc='best')
            axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_dir}/dynamic_correlation.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 已保存: {output_dir}/dynamic_correlation.png")


def generate_html_report(data, eda_results, model_results, comparison_df,
                        ios_df, output_dir='outputs'):
    """
    生成完整的HTML报告
    """

    print("\n[生成HTML报告]")

    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>热卷现货-期货套保比例计算模型报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .metric {{
            display: inline-block;
            margin: 10px;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 5px;
            min-width: 200px;
        }}
        .metric-label {{
            font-weight: bold;
            color: #7f8c8d;
        }}
        .metric-value {{
            font-size: 24px;
            color: #2c3e50;
            margin-top: 5px;
        }}
        .star {{
            color: #f39c12;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .code-block {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }}
        .alert {{
            padding: 15px;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>热卷现货-期货套保比例计算模型报告</h1>
        <p><strong>生成时间:</strong> {generate_time}</p>
        <p><strong>数据时间范围:</strong> {date_range}</p>
        <p><strong>样本量:</strong> {sample_size} 个交易日</p>

        <h2>执行摘要 (Executive Summary)</h2>
        <p>本报告基于条件协方差理论，为热卷上海地区现货与SHFE热卷期货构建了四种动态套保比例计算模型：</p>
        <ul>
            <li><strong>模型1: 基础GARCH</strong> - 使用二元GARCH模型估计时变协方差</li>
            <li><strong>模型2: ECM-GARCH</strong> - 考虑现货与期货的长期均衡关系（误差修正模型）</li>
            <li><strong>模型3: DCC-GARCH</strong> - 考虑动态时变相关性</li>
            <li><strong>模型4: ECM-DCC-GARCH</strong> - 综合模型，结合基差修正和动态相关性</li>
        </ul>

        <h2>核心公式</h2>
        <div class="code-block">
            理论套保比例: h_t = Cov_t(ΔS, ΔF) / Var_t(ΔF)<br>
            实际套保比例: h_实际 = h_t / 1.13  (考虑13%增值税)
        </div>

        <h2>数据描述与统计特征</h2>
        <table>
            <tr>
                <th>指标</th>
                <th>现货价格 (CNY/ton)</th>
                <th>期货价格 (CNY/ton)</th>
            </tr>
            <tr>
                <td>均值</td>
                <td>{{spot_mean:.2f}}</td>
                <td>{{futures_mean:.2f}}</td>
            </tr>
            <tr>
                <td>标准差</td>
                <td>{{spot_std:.2f}}</td>
                <td>{{futures_std:.2f}}</td>
            </tr>
            <tr>
                <td>最小值</td>
                <td>{{spot_min:.2f}}</td>
                <td>{{futures_min:.2f}}</td>
            </tr>
            <tr>
                <td>最大值</td>
                <td>{{spot_max:.2f}}</td>
                <td>{{futures_max:.2f}}</td>
            </tr>
        </table>

        <h3>收益率统计</h3>
        <table>
            <tr>
                <th>指标</th>
                <th>现货收益率</th>
                <th>期货收益率</th>
            </tr>
            <tr>
                <td>均值</td>
                <td>{{r_s_mean:.6f}}</td>
                <td>{{r_f_mean:.6f}}</td>
            </tr>
            <tr>
                <td>标准差</td>
                <td>{{r_s_std:.6f}}</td>
                <td>{{r_f_std:.6f}}</td>
            </tr>
            <tr>
                <td>偏度</td>
                <td>{{r_s_skew:.4f}}</td>
                <td>{{r_f_skew:.4f}}</td>
            </tr>
            <tr>
                <td>峰度</td>
                <td>{{r_s_kurt:.4f}}</td>
                <td>{{r_f_kurt:.4f}}</td>
            </tr>
        </table>

        <h3>基差统计</h3>
        <table>
            <tr>
                <th>均值</th>
                <th>标准差</th>
                <th>最小值</th>
                <th>最大值</th>
            </tr>
            <tr>
                <td>{{spread_mean:.2f}}</td>
                <td>{{spread_std:.2f}}</td>
                <td>{{spread_min:.2f}}</td>
                <td>{{spread_max:.2f}}</td>
            </tr>
        </table>

        <h3>现货-期货相关系数</h3>
        <div class="metric">
            <div class="metric-label">Pearson相关系数</div>
            <div class="metric-value">{{correlation:.4f}}</div>
        </div>

        <h2>可视化图表</h2>

        <h3>1. 价格走势对比</h3>
        <img src="figures/price_series.png" alt="价格走势对比">

        <h3>2. 收益率波动</h3>
        <img src="figures/returns_volatility.png" alt="收益率波动">

        <h3>3. 基差时变图</h3>
        <img src="figures/basis_spread.png" alt="基差时变图">

        <h3>4. 套保比例对比</h3>
        <img src="figures/hedge_ratio_comparison.png" alt="套保比例对比">

        <h3>5. 动态相关系数</h3>
        <img src="figures/dynamic_correlation.png" alt="动态相关系数">

        <h2>套保效果对比分析</h2>
        {comparison_table}

        <h3>方差降低比例对比</h3>
        <img src="figures/variance_reduction.png" alt="方差降低比例">

        <h3>夏普比率对比</h3>
        <img src="figures/sharpe_ratio_comparison.png" alt="夏普比率对比">

        <h3>最大回撤对比</h3>
        <img src="figures/max_drawdown_comparison.png" alt="最大回撤对比">

        <h2>样本内外测试</h2>
        {ios_table}

        <h3>样本内外效果对比图</h3>
        <img src="figures/in_sample_vs_out_sample.png" alt="样本内外效果对比">

        <h2>模型选择建议</h2>
        <div class="alert">
            <strong>推荐模型:</strong> {best_model}<br>
            <strong>推荐理由:</strong> {recommendation_reason}
        </div>

        <h2>风险提示与局限性</h2>
        <ul>
            <li>历史数据不代表未来表现</li>
            <li>模型假设可能不适用于所有市场环境</li>
            <li>交易成本和滑点未在模型中考虑</li>
            <li>极端市场条件下模型可能失效</li>
            <li>增值税税率变化会影响实际套保比例</li>
        </ul>

        <h2>技术细节</h2>
        <h3>GARCH模型参数</h3>
        <p>所有模型均采用GARCH(1,1)设定：</p>
        <div class="code-block">
            σ²_t = ω + α·ε²_{{t-1}} + β·σ²_{{t-1}}
        </div>

        <h3>DCC模型参数</h3>
        <p>动态条件相关模型：</p>
        <div class="code-block">
            Q_t = (1 - α - β)·Q̄ + α·ε_{{t-1}}·ε'_{{t-1}} + β·Q_{{t-1}}<br>
            R_t = Q_t^{{*-1/2}}·Q_t·Q_t^{{*-1/2}}
        </div>

        <h2>参考文献</h2>
        <ol>
            <li>Engle, R. F. (2002). "Dynamic Conditional Correlation: A Simple Class of Multivariate Generalized Autoregressive Conditional Heteroskedasticity Models."</li>
            <li>Kroner, K. F., & Sultan, J. (1993). "Time-varying distributions and dynamic hedging with foreign currency futures."</li>
            <li>Lien, D., & Tse, Y. K. (2002). "Some recent developments in futures hedging."</li>
        </ol>

        <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d;">
            <p>本报告由 Claude Code 自动生成 | 数据来源: 上海期货交易所 (SHFE)</p>
        </footer>
    </div>
</body>
</html>
    """

    # 准备数据
    generate_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    date_range = f"{data['date'].min().strftime('%Y-%m-%d')} 至 {data['date'].max().strftime('%Y-%m-%d')}"
    sample_size = len(data)

    spot_mean = data['spot'].mean()
    spot_std = data['spot'].std()
    spot_min = data['spot'].min()
    spot_max = data['spot'].max()

    futures_mean = data['futures'].mean()
    futures_std = data['futures'].std()
    futures_min = data['futures'].min()
    futures_max = data['futures'].max()

    r_s_mean = data['r_s'].mean()
    r_s_std = data['r_s'].std()
    r_s_skew = data['r_s'].skew()
    r_s_kurt = data['r_s'].kurtosis()

    r_f_mean = data['r_f'].mean()
    r_f_std = data['r_f'].std()
    r_f_skew = data['r_f'].skew()
    r_f_kurt = data['r_f'].kurtosis()

    spread_mean = data['spread'].mean()
    spread_std = data['spread'].std()
    spread_min = data['spread'].min()
    spread_max = data['spread'].max()

    correlation = eda_results['correlation']

    # 生成对比表格HTML
    comparison_table_html = """
    <table>
        <tr>
            <th>模型</th>
            <th>方差降低比例</th>
            <th>Ederington指标</th>
            <th>夏普比率(套保后)</th>
            <th>最大回撤(套保后)</th>
        </tr>
    """

    for _, row in comparison_df.iterrows():
        comparison_table_html += f"""
        <tr>
            <td>{row['模型']}</td>
            <td>{row['方差降低比例']}</td>
            <td>{row['Ederington指标']}</td>
            <td>{row['夏普比率(套保后)']}</td>
            <td>{row['最大回撤(套保后)']}</td>
        </tr>
        """

    comparison_table_html += "</table>"

    # 生成样本内外表格HTML
    ios_table_html = """
    <table>
        <tr>
            <th>模型</th>
            <th>样本内方差降低</th>
            <th>样本外方差降低</th>
        </tr>
    """

    for model_name in ios_df.index:
        ios_table_html += f"""
        <tr>
            <td>{model_name}</td>
            <td>{ios_df.loc[model_name, '样本内方差降低']:.2%}</td>
            <td>{ios_df.loc[model_name, '样本外方差降低']:.2%}</td>
        </tr>
        """

    ios_table_html += "</table>"

    # 确定最佳模型
    best_variance_reduction = 0
    best_model = comparison_df.iloc[0]['模型']

    for _, row in comparison_df.iterrows():
        vr = float(row['方差降低比例'].rstrip('%')) / 100
        if vr > best_variance_reduction:
            best_variance_reduction = vr
            best_model = row['模型']

    recommendation_reason = f"该模型的方差降低比例最高（{best_variance_reduction:.1%}），套保效果最好。"

    # 填充HTML模板
    html_content = html_template.format(
        generate_time=generate_time,
        date_range=date_range,
        sample_size=sample_size,
        spot_mean=spot_mean,
        spot_std=spot_std,
        spot_min=spot_min,
        spot_max=spot_max,
        futures_mean=futures_mean,
        futures_std=futures_std,
        futures_min=futures_min,
        futures_max=futures_max,
        r_s_mean=r_s_mean,
        r_s_std=r_s_std,
        r_s_skew=r_s_skew,
        r_s_kurt=r_s_kurt,
        r_f_mean=r_f_mean,
        r_f_std=r_f_std,
        r_f_skew=r_f_skew,
        r_f_kurt=r_f_kurt,
        spread_mean=spread_mean,
        spread_std=spread_std,
        spread_min=spread_min,
        spread_max=spread_max,
        correlation=correlation,
        comparison_table=comparison_table_html,
        ios_table=ios_table_html,
        best_model=best_model,
        recommendation_reason=recommendation_reason
    )

    # 保存HTML文件
    output_path = f"{output_dir}/hedging_report.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  ✓ 已保存: {output_path}")


def generate_excel_report(data, model_results, comparison_df, ios_df, output_dir='outputs'):
    """
    生成Excel综合报告
    """

    print("\n[生成Excel报告]")

    output_path = f"{output_dir}/hedging_results.xlsx"

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 原始数据
        data.to_excel(writer, sheet_name='原始数据', index=False)

        # 收益率数据
        returns_data = data[['date', 'r_s', 'r_f', 'spread']].copy()
        returns_data.to_excel(writer, sheet_name='收益率数据', index=False)

        # 四种模型的套保比例
        for model_name, result in model_results.items():
            df = result.get('output_df', None)
            if df is not None:
                sheet_name = model_name.replace('-', ' ')[:31]  # Excel工作表名最长31个字符
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        # 效果评估指标
        comparison_df.to_excel(writer, sheet_name='效果评估', index=False)

        # 样本内外测试
        ios_df.to_excel(writer, sheet_name='样本内外测试')

        # 模型参数汇总
        params_data = []

        for model_name, result in model_results.items():
            row = {'模型': model_name}

            if 'ecm_params' in result:
                row['ECM_h系数'] = result['ecm_params'].get('h_ecm', '')
                row['ECM_误差修正系数'] = result['ecm_params'].get('gamma', '')

            if 'dcc_params' in result:
                row['DCC_α'] = result['dcc_params'].get('alpha', '')
                row['DCC_β'] = result['dcc_params'].get('beta', '')

            if 'cointegration_params' in result:
                row['协整_R²'] = result['cointegration_params'].get('r_squared', '')

            h = result['h_actual']
            row['平均套保比例'] = np.mean(h)
            row['套保比例标准差'] = np.std(h)

            params_data.append(row)

        params_df = pd.DataFrame(params_data)
        params_df.to_excel(writer, sheet_name='模型参数汇总', index=False)

    print(f"  ✓ 已保存: {output_path}")


def generate_comprehensive_report(data, eda_results, model_results,
                                   comparison_df, ios_df, output_dir='outputs'):
    """
    生成完整的分析报告
    """

    print("\n" + "=" * 60)
    print("生成可视化与报告")
    print("=" * 60)

    import os
    os.makedirs(f"{output_dir}/figures", exist_ok=True)

    # 1. 绘制套保比例对比图
    plot_hedge_ratio_comparison(data, model_results, f"{output_dir}/figures")

    # 2. 绘制动态相关系数图
    plot_dynamic_correlation(model_results, f"{output_dir}/figures")

    # 3. 生成HTML报告
    generate_html_report(data, eda_results, model_results,
                        comparison_df, ios_df, output_dir)

    # 4. 生成Excel报告
    generate_excel_report(data, model_results, comparison_df, ios_df, output_dir)

    print("\n" + "=" * 60)
    print("✓ 报告生成完成！")
    print("=" * 60)
    print("\n输出文件:")
    print(f"  - {output_dir}/hedging_report.html")
    print(f"  - {output_dir}/hedging_results.xlsx")
    print(f"  - {output_dir}/figures/")


if __name__ == "__main__":
    # 测试报告生成
    print("报告生成模块测试")
