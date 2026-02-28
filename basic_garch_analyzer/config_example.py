"""
配置示例文件

演示如何创建和使用自定义配置
"""
from basic_garch_analyzer import ModelConfig

# 示例1: 默认配置
config_default = ModelConfig()

# 示例2: 无税点调整
config_no_tax = ModelConfig(tax_rate=0.0)

# 示例3: 短窗口相关系数
config_short_window = ModelConfig(corr_window=60)

# 示例4: GARCH(2,1) 模型
config_garch_21 = ModelConfig(p=2, q=1)

# 示例5: 完全自定义
config_custom = ModelConfig(
    p=1,
    q=1,
    corr_window=90,
    tax_rate=0.0,
    output_dir='my_outputs'
)

# 使用示例
if __name__ == '__main__':
    from basic_garch_analyzer import run_analysis

    # 使用自定义配置
    result = run_analysis(
        excel_path='data.xlsx',
        spot_col='现货价格',
        futures_col='期货价格',
        config=config_no_tax
    )
