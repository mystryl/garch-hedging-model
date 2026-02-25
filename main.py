"""
热卷现货-期货套保比例计算模型
主程序入口

基于条件协方差理论，为热卷上海地区现货与SHFE热卷期货
构建四种动态套保比例计算模型

作者: Claude Code
日期: 2026
"""

import sys
import time
from datetime import datetime

# 导入所有模块
from data_preprocessing import preprocess_data
from eda_analysis import generate_eda_report
from model_basic_garch import fit_basic_garch
from model_ecm_garch import fit_ecm_garch
from model_dcc_garch import fit_dcc_garch
from model_ecm_dcc_garch import fit_ecm_dcc_garch
from hedging_effectiveness import compare_models
from generate_report import generate_comprehensive_report


def print_banner():
    """打印程序横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║       热卷现货-期货套保比例计算模型                        ║
║       Hedge Ratio Calculation Model                        ║
║                                                           ║
║       基于 GARCH 方法的动态套保策略                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主程序"""

    print_banner()

    # 记录开始时间
    start_time = time.time()

    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    try:
        # ========================================
        # 步骤1: 数据预处理
        # ========================================
        print("\n[步骤 1/5] 数据预处理")
        print("-"*60)

        data = preprocess_data('基差数据.xlsx', output_dir='outputs')

        # ========================================
        # 步骤2: 探索性数据分析
        # ========================================
        print("\n[步骤 2/5] 探索性数据分析（EDA）")
        print("-"*60)

        eda_results = generate_eda_report(data, output_dir='outputs')

        # ========================================
        # 步骤3: 拟合四种模型
        # ========================================
        print("\n[步骤 3/5] 拟合四种套保模型")
        print("-"*60)

        print("\n正在拟合模型1: 基础GARCH...")
        h_basic = fit_basic_garch(data, output_dir='outputs/model_results')

        print("\n正在拟合模型2: ECM-GARCH...")
        h_ecm = fit_ecm_garch(data, output_dir='outputs/model_results')

        print("\n正在拟合模型3: DCC-GARCH...")
        h_dcc = fit_dcc_garch(data, output_dir='outputs/model_results')

        print("\n正在拟合模型4: ECM-DCC-GARCH...")
        h_ecm_dcc = fit_ecm_dcc_garch(data, output_dir='outputs/model_results')

        # 整理模型结果
        model_results = {
            'Basic GARCH': h_basic,
            'ECM-GARCH': h_ecm,
            'DCC-GARCH': h_dcc,
            'ECM-DCC-GARCH': h_ecm_dcc
        }

        # ========================================
        # 步骤4: 评估套保效果
        # ========================================
        print("\n[步骤 4/5] 评估套保效果")
        print("-"*60)

        comparison_df, ios_df, all_metrics, ios_results = compare_models(
            data, model_results, output_dir='outputs'
        )

        # ========================================
        # 步骤5: 生成完整报告
        # ========================================
        print("\n[步骤 5/5] 生成完整报告")
        print("-"*60)

        generate_comprehensive_report(
            data, eda_results, model_results,
            comparison_df, ios_df, output_dir='outputs'
        )

        # ========================================
        # 完成
        # ========================================
        end_time = time.time()
        elapsed_time = end_time - start_time

        print("\n" + "="*60)
        print("✓ 所有步骤完成！")
        print("="*60)
        print(f"\n总耗时: {elapsed_time:.2f} 秒")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "="*60)
        print("输出文件清单")
        print("="*60)

        print("\n📊 数据文件:")
        print("  - outputs/preprocessed_data.csv")
        print("  - outputs/preprocessed_data.xlsx")

        print("\n📈 模型结果:")
        print("  - outputs/model_results/h_basic_garch.csv")
        print("  - outputs/model_results/h_ecm_garch.csv")
        print("  - outputs/model_results/h_dcc_garch.csv")
        print("  - outputs/model_results/h_ecm_dcc_garch.csv")
        print("  - outputs/model_results/rho_t.csv")

        print("\n📉 效果评估:")
        print("  - outputs/effectiveness_report.csv")
        print("  - outputs/in_sample_out_sample.csv")

        print("\n📑 完整报告:")
        print("  - outputs/hedging_report.html  ⭐ (推荐查看)")
        print("  - outputs/hedging_results.xlsx")

        print("\n🖼️  图表文件:")
        print("  - outputs/figures/ (包含所有可视化图表)")

        print("\n" + "="*60)
        print("推荐操作:")
        print("="*60)
        print("1. 用浏览器打开: outputs/hedging_report.html")
        print("2. 用Excel查看: outputs/hedging_results.xlsx")
        print("3. 查看模型结果: outputs/model_results/")

        print("\n" + "="*60)
        print("感谢使用！")
        print("="*60)

        return 0

    except Exception as e:
        print(f"\n✗ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
