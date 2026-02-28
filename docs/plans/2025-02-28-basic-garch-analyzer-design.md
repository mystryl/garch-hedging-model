# Basic GARCH Analyzer 设计文档

**日期:** 2025-02-28
**状态:** 已批准
**方案:** 方案 A - 最小重构

---

## 1. 概述

将 `basic_garch_analyzer` 目录改造成独立的分析工具，支持：
- 作为 Python 库导入使用
- 作为命令行工具运行
- 自动生成完整的回测分析报告
- 灵活配置模型参数
- 适配多品种数据（通过 Excel 列选择）

---

## 2. 文件结构

```
basic_garch_analyzer/
├── __init__.py             # 包初始化文件，导出主要接口
├── config.py               # 默认配置参数（ModelConfig 类）
├── data_loader.py          # 数据加载（保持不变）
├── basic_garch_model.py    # GARCH模型拟合（保持不变）
├── analyzer.py             # 核心分析器（合并评估+报告）
├── main.py                 # 命令行主入口
└── utils/
    └── __init__.py         # 工具函数（可选）
```

---

## 3. 核心模块设计

### 3.1 config.py - 默认配置

```python
from dataclasses import dataclass

@dataclass
class ModelConfig:
    # GARCH 模型参数
    p: int = 1
    q: int = 1
    mean_model: str = 'Constant'
    vol_model: str = 'GARCH'
    distribution: str = 'normal'

    # 套保参数
    corr_window: int = 120
    tax_rate: float = 0.13

    # 输出配置
    output_dir: str = 'outputs'
    save_intermediate: bool = True
```

### 3.2 analyzer.py - 核心分析器

**主要函数：**

```python
def evaluate_and_report(
    data: pd.DataFrame,
    results: dict,
    selected: dict,
    config: ModelConfig,
    output_dir: str = 'outputs'
) -> dict:
    """
    执行回测评估并生成完整报告

    Returns:
        report_info: {
            'metrics': {...},
            'figures': [...],
            'html_path': str,
            'csv_path': str
        }
    """
```

**内部流程：**
1. 计算回测指标（方差降低、夏普比率、最大回撤等）
2. 准备图表数据
3. 生成8张图表（复用 report_generator.py 的函数）
4. 生成 CSV/Excel 报告
5. 生成 HTML 报告

### 3.3 main.py - 命令行入口

**命令行参数：**

| 参数 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `--data` | Excel文件路径 | - | ✅ |
| `--spot` | 现货列名 | - | ✅ |
| `--futures` | 期货列名 | - | ✅ |
| `--sheet` | 工作表名/索引 | 0 | ❌ |
| `--date-col` | 日期列名 | auto | ❌ |
| `--p` | GARCH p | 1 | ❌ |
| `--q` | GARCH q | 1 | ❌ |
| `--corr-window` | 相关系数窗口 | 120 | ❌ |
| `--tax-rate` | 税点调整比例 | 0.13 | ❌ |
| `--output-dir` | 输出目录 | outputs | ❌ |
| `--interactive` | 交互式选择列 | False | ❌ |

**使用示例：**

```bash
# 基本使用
python -m basic_garch_analyzer \
    --data data.xlsx \
    --spot 现货价格 \
    --futures 期货价格

# 自定义参数
python -m basic_garch_analyzer \
    --data data.xlsx \
    --spot 现货价格 \
    --futures 期货价格 \
    --tax-rate 0.0 \
    --corr-window 60

# 交互模式
python -m basic_garch_analyzer \
    --data data.xlsx \
    --interactive
```

### 3.4 __init__.py - 包初始化

```python
from basic_garch_analyzer.config import ModelConfig
from basic_garch_analyzer.data_loader import load_and_preprocess
from basic_garch_analyzer.basic_garch_model import fit_basic_garch
from basic_garch_analyzer.analyzer import evaluate_and_report

def run_analysis(excel_path, spot_col, futures_col, config=None, **kwargs):
    """
    一键运行完整分析流程

    Returns:
        report_info: 分析结果信息
    """
    # 实现完整流程
```

---

## 4. 数据流

```
Excel 文件
    │
    ▼
data_loader.py (load_data + preprocess)
    │
    ▼
basic_garch_model.py (fit_basic_garch)
    │
    ▼
analyzer.py (evaluate_and_report)
    │
    ├── 生成8张图表
    ├── 生成CSV/Excel
    └── 生成HTML报告
    │
    ▼
输出文件
```

---

## 5. 作为库使用

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

---

## 6. 错误处理

**自定义异常类：**

```python
class ValidationError(Exception): pass
class DataLoadError(Exception): pass
class ColumnNotFoundError(DataLoadError): pass
class ModelFitError(Exception): pass
class ReportGenerationError(Exception): pass
```

**验证点：**
- 文件存在性
- 列名存在性
- 数据量充足性（≥120天）
- 模型收敛性
- 参数合理性（α+β < 1）

---

## 7. 输出文件结构

```
outputs/
├── report.html
├── backtest_report.csv
├── backtest_report.xlsx
├── figures/
│   ├── 1_price_series.png
│   ├── 2_returns.png
│   ├── 3_hedge_ratio.png
│   ├── 4_volatility.png
│   ├── 5_backtest_results.png
│   ├── 6_drawdown.png
│   ├── 7_performance_metrics.png
│   └── 8_summary_table.png
└── model_results/
    └── h_basic_garch.csv
```

---

## 8. 实施优先级

1. **高优先级**
   - config.py
   - main.py（命令行入口）
   - analyzer.py（合并评估+报告）

2. **中优先级**
   - __init__.py（包初始化）
   - 错误处理完善

3. **低优先级**
   - tests/（单元测试）
   - utils/（工具函数）

---

## 9. 设计决策记录

| 决策 | 选择理由 |
|------|----------|
| 选择方案A（最小重构） | 改动最小，快速实现，代码复用率高 |
| 合并评估+报告 | 简化数据流，避免接口不匹配问题 |
| 默认值+可选配置 | 平衡灵活性和易用性 |
| 单次分析一对品种 | 明确需求，避免过度设计 |
| dataclass 配置 | Python 3.7+ 原生支持，类型友好 |
