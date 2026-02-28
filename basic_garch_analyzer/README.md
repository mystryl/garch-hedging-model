# Basic GARCH Analyzer

GARCH(1,1) 套保模型分析工具，支持命令行和 Python 库两种使用方式。

## 功能特点

- ✅ 自动数据加载和预处理
- ✅ GARCH(1,1) 模型拟合
- ✅ 动态套保比例计算
- ✅ 完整的回测评估指标
- ✅ 自动生成图表和报告
- ✅ 支持交互式列名选择
- ✅ 灵活的参数配置

## 安装依赖

```bash
pip install pandas numpy matplotlib arch openpyxl
```

## 使用方法

### 方式1: 命令行

```bash
# 基本使用
python -m basic_garch_analyzer \
    --data data.xlsx \
    --spot 现货价格 \
    --futures 期货价格

# 自定义参数
python -m basic_garch_analyzer \
    --data data.xlsx \
    --spot 现货 \
    --futures 期货 \
    --tax-rate 0.0 \
    --corr-window 60

# 交互模式
python -m basic_garch_analyzer \
    --data data.xlsx \
    --interactive
```

### 方式2: Python 库

```python
from basic_garch_analyzer import run_analysis, ModelConfig

# 使用默认配置
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格'
)

# 自定义配置
config = ModelConfig(
    corr_window=60,
    tax_rate=0.0
)
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格',
    config=config
)
```

## 输出文件

运行后会在输出目录（默认 `outputs/`）生成：

- `report.html` - HTML 格式的完整报告（推荐查看）
- `backtest_report.csv` - CSV 格式的指标表格
- `backtest_report.xlsx` - Excel 格式的多工作表报告
- `figures/` - 8 张可视化图表
- `model_results/` - 模型拟合结果数据

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--data` | Excel文件路径 | - (必需) |
| `--spot` | 现货列名 | - (非交互模式必需) |
| `--futures` | 期货列名 | - (非交互模式必需) |
| `--date-col` | 日期列名 | 自动检测 |
| `--sheet` | 工作表名/索引 | 0 |
| `--p` | GARCH p 阶数 | 1 |
| `--q` | GARCH q 阶数 | 1 |
| `--corr-window` | 相关系数窗口 | 120 |
| `--tax-rate` | 税点调整比例 | 0.13 |
| `--output-dir` | 输出目录 | outputs |
| `--interactive` | 交互式选择列 | False |

## 配置参数

```python
from basic_garch_analyzer import ModelConfig

config = ModelConfig(
    # GARCH 模型参数
    p=1,                    # GARCH p 阶数
    q=1,                    # GARCH q 阶数
    mean_model='Constant',  # 均值模型
    vol_model='GARCH',      # 波动率模型
    distribution='normal',  # 分布假设

    # 套保参数
    corr_window=120,        # 动态相关系数窗口（天）
    tax_rate=0.13,          # 税点调整比例

    # 输出配置
    output_dir='outputs',   # 输出目录
    save_intermediate=True  # 保存中间结果
)
```

## 示例

详细示例请参考 `config_example.py`
