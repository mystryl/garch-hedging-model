"""
Basic GARCH Analyzer 集成测试
测试完整分析流程
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from basic_garch_analyzer import run_analysis, ModelConfig


def test_run_analysis():
    """测试完整分析流程"""
    print("\n" + "=" * 60)
    print("集成测试: Basic GARCH Analyzer")
    print("=" * 60)

    # 测试1: 使用项目现有数据
    print("\n[测试1] 使用现有数据文件...")

    data_file = "outputs/preprocessed_data.xlsx"

    if not os.path.exists(data_file):
        print(f"⚠️  测试数据不存在: {data_file}")
        print("   请先运行主程序生成测试数据")
        return False

    try:
        result = run_analysis(
            excel_path=data_file,
            spot_col='spot',
            futures_col='futures',
            config=ModelConfig(
                output_dir='outputs/test'
            )
        )

        # 验证输出
        assert 'data' in result
        assert 'model_results' in result
        assert 'report_info' in result
        assert os.path.exists(result['report_info']['html_path'])

        print("\n✅ 测试通过!")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_run_analysis()
    sys.exit(0 if success else 1)
