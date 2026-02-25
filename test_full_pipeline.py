"""
完整流程测试脚本
测试数据预处理到报告生成的完整流程
"""

import os
import sys
import traceback


def test_data_preprocessing():
    """测试数据预处理"""
    print("\n" + "="*60)
    print("测试 1/7: 数据预处理")
    print("="*60)

    try:
        from data_preprocessing import preprocess_data

        if not os.path.exists('基差数据.xlsx'):
            print("  ⚠ 未找到数据文件，跳过测试")
            return None

        data = preprocess_data('基差数据.xlsx', output_dir='outputs')

        # 验证数据
        assert 'date' in data.columns, "缺少date列"
        assert 'spot' in data.columns, "缺少spot列"
        assert 'futures' in data.columns, "缺少futures列"
        assert 'r_s' in data.columns, "缺少r_s列"
        assert 'r_f' in data.columns, "缺少r_f列"
        assert 'spread' in data.columns, "缺少spread列"

        assert len(data) > 0, "数据为空"
        assert data['r_s'].notna().all(), "r_s包含NaN"
        assert data['r_f'].notna().all(), "r_f包含NaN"

        print(f"  ✓ 数据预处理成功，共 {len(data)} 行")
        return data

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_eda_analysis(data):
    """测试探索性数据分析"""
    print("\n" + "="*60)
    print("测试 2/7: 探索性数据分析")
    print("="*60)

    if data is None:
        print("  ⚠ 跳过（无数据）")
        return None

    try:
        from eda_analysis import generate_eda_report

        eda_results = generate_eda_report(data, output_dir='outputs')

        assert eda_results is not None, "EDA结果为空"
        assert 'correlation' in eda_results, "缺少correlation"

        print("  ✓ EDA分析成功")
        return eda_results

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_basic_garch(data):
    """测试基础GARCH模型"""
    print("\n" + "="*60)
    print("测试 3/7: 基础GARCH模型")
    print("="*60)

    if data is None:
        print("  ⚠ 跳过（无数据）")
        return None

    try:
        from model_basic_garch import fit_basic_garch

        result = fit_basic_garch(data, output_dir='outputs/model_results')

        assert 'h_actual' in result, "缺少h_actual"
        assert len(result['h_actual']) > 0, "h_actual为空"
        assert result['h_actual'].min() >= 0, "套保比例有负值"
        assert result['h_actual'].max() <= 2, "套保比例超过2"

        print(f"  ✓ 基础GARCH模型成功")
        print(f"     套保比例范围: [{result['h_actual'].min():.3f}, {result['h_actual'].max():.3f}]")
        return result

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_ecm_garch(data):
    """测试ECM-GARCH模型"""
    print("\n" + "="*60)
    print("测试 4/7: ECM-GARCH模型")
    print("="*60)

    if data is None:
        print("  ⚠ 跳过（无数据）")
        return None

    try:
        from model_ecm_garch import fit_ecm_garch

        result = fit_ecm_garch(data, output_dir='outputs/model_results')

        assert 'h_actual' in result, "缺少h_actual"
        assert 'ecm_params' in result, "缺少ecm_params"

        print(f"  ✓ ECM-GARCH模型成功")
        return result

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_dcc_garch(data):
    """测试DCC-GARCH模型"""
    print("\n" + "="*60)
    print("测试 5/7: DCC-GARCH模型")
    print("="*60)

    if data is None:
        print("  ⚠ 跳过（无数据）")
        return None

    try:
        from model_dcc_garch import fit_dcc_garch

        result = fit_dcc_garch(data, output_dir='outputs/model_results')

        assert 'h_actual' in result, "缺少h_actual"
        assert 'rho_t' in result, "缺少rho_t"

        print(f"  ✓ DCC-GARCH模型成功")
        return result

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_ecm_dcc_garch(data):
    """测试ECM-DCC-GARCH模型"""
    print("\n" + "="*60)
    print("测试 6/7: ECM-DCC-GARCH模型")
    print("="*60)

    if data is None:
        print("  ⚠ 跳过（无数据）")
        return None

    try:
        from model_ecm_dcc_garch import fit_ecm_dcc_garch

        result = fit_ecm_dcc_garch(data, output_dir='outputs/model_results')

        assert 'h_actual' in result, "缺少h_actual"
        assert 'ecm_params' in result, "缺少ecm_params"
        assert 'dcc_params' in result, "缺少dcc_params"

        print(f"  ✓ ECM-DCC-GARCH模型成功")
        return result

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def test_model_evaluation(data, model_results):
    """测试模型评估"""
    print("\n" + "="*60)
    print("测试 7/7: 模型效果评估")
    print("="*60)

    if data is None or model_results is None:
        print("  ⚠ 跳过（无数据或模型结果）")
        return None

    try:
        from hedging_effectiveness import compare_models

        comparison_df, ios_df, all_metrics, ios_results = compare_models(
            data, model_results, output_dir='outputs'
        )

        assert comparison_df is not None, "comparison_df为空"

        print("  ✓ 模型评估成功")
        return comparison_df

    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        return None


def main():
    """主测试函数"""

    print("="*60)
    print("完整流程测试")
    print("="*60)

    # 运行所有测试
    data = test_data_preprocessing()
    eda_results = test_eda_analysis(data)

    if data is not None:
        h_basic = test_basic_garch(data)
        h_ecm = test_ecm_garch(data)
        h_dcc = test_dcc_garch(data)
        h_ecm_dcc = test_ecm_dcc_garch(data)

        model_results = {
            'Basic GARCH': h_basic,
            'ECM-GARCH': h_ecm,
            'DCC-GARCH': h_dcc,
            'ECM-DCC-GARCH': h_ecm_dcc
        }

        test_model_evaluation(data, model_results)

    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

    # 检查输出文件
    print("\n输出文件检查:")
    output_files = [
        'outputs/preprocessed_data.csv',
        'outputs/model_results/h_basic_garch.csv',
        'outputs/model_results/h_ecm_garch.csv',
        'outputs/model_results/h_dcc_garch.csv',
        'outputs/model_results/h_ecm_dcc_garch.csv',
    ]

    for f in output_files:
        if os.path.exists(f):
            size = os.path.getsize(f)
            print(f"  ✓ {f} ({size} bytes)")
        else:
            print(f"  ✗ {f} (不存在)")


if __name__ == "__main__":
    main()
