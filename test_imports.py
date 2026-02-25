"""
测试所有模块的导入和基本功能
"""

import sys

def test_imports():
    """测试所有模块导入"""
    print("测试模块导入...")

    try:
        print("  1. data_preprocessing...")
        from data_preprocessing import preprocess_data
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  2. eda_analysis...")
        from eda_analysis import generate_eda_report
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  3. model_basic_garch...")
        from model_basic_garch import fit_basic_garch
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  4. model_ecm_garch...")
        from model_ecm_garch import fit_ecm_garch
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  5. model_dcc_garch...")
        from model_dcc_garch import fit_dcc_garch
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  6. model_ecm_dcc_garch...")
        from model_ecm_dcc_garch import fit_ecm_dcc_garch
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  7. hedging_effectiveness...")
        from hedging_effectiveness import compare_models
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  8. generate_report...")
        from generate_report import generate_comprehensive_report
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    try:
        print("  9. main...")
        import main
        print("     ✓ 导入成功")
    except Exception as e:
        print(f"     ✗ 失败: {e}")
        return False

    print("\n✓ 所有模块导入成功!")
    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
