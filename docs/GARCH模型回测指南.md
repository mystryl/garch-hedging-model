# GARCH套保模型回测指南

> 本指南详细说明如何使用Basic GARCH和ECM-GARCH两种模型生成套保策略回测报告。

---

## 目录

1. [概述](#概述)
2. [环境准备](#环境准备)
3. [数据准备](#数据准备)
4. [Basic GARCH模型回测](#basic-garch模型回测)
5. [ECM-GARCH模型回测](#ecm-garch模型回测)
6. [两种模型对比](#两种模型对比)
7. [输出文件说明](#输出文件说明)
8. [常见问题](#常见问题)

---

## 概述

本项目支持两种GARCH套保模型：

| 模型 | 特点 | 适用场景 |
|------|------|----------|
| **Basic GARCH** | 基础GARCH(1,1)模型，基于时变相关性和波动率估计套保比例 | 一般套保场景 |
| **ECM-GARCH** | 误差修正模型GARCH，考虑现货与期货的长期均衡关系（协整关系） | 需要捕捉长期均衡调整的场景 |

两种模型均支持：
- **滚动回测模式**（默认）：6个周期 × 90天/周期
- **双坐标轴图表**：净值/回撤曲线 + 套保比例曲线
- **完整报告输出**：HTML + Excel + CSV

---

## 环境准备

### 安装依赖

```bash
pip install numpy pandas matplotlib arch scipy openpyxl
```

### 项目结构

```
GARCH 模型套保方案/
├── model_ecm_garch.py              # ECM-GARCH模型
├── basic_garch_analyzer/           # Basic GARCH模型
│   ├── __init__.py
│   ├── config.py                   # 配置文件
│   ├── rolling_backtest.py         # 滚动回测模块
│   └── report_generator.py         # 报告生成器
├── data/                           # 数据目录
└── outputs/                        # 输出目录
```

---

## 数据准备

### 数据格式要求

准备Excel文件（`.xlsx`格式），包含以下列：

| 列名 | 说明 | 示例 |
|------|------|------|
| date | 日期（YYYY-MM-DD） | 2021-01-05 |
| spot | 现货价格 | 4500.25 |
| futures | 期货价格 | 4600.50 |

### 数据处理示例

```python
import pandas as pd

# 读取原始数据
df = pd.read_excel('data/热卷_2021.xlsx', sheet_name='热卷基差', header=None)

# 跳过表头（根据实际情况调整）
df = df.iloc[3:].reset_index(drop=True)

# 重命名列
df.columns = ['date', 'col1', 'futures', 'spot']

# 选择需要的列
data = df[['date', 'spot', 'futures']].copy()

# 转换日期格式
data['date'] = pd.to_datetime(data['date'])

# 过滤日期范围（例如：2021年以后）
data = data[data['date'] >= '2021-01-01']

# 保存处理后的数据
data.to_excel('data/processed_hot_coil_2021.xlsx', index=False)
```

---

## Basic GARCH模型回测

### 方法一：使用命令行脚本

创建脚本 `run_basic_garch.py`：

```python
from basic_garch_analyzer import run_basic_garch_analyzer
import pandas as pd

# 1. 读取数据
data = pd.read_excel('data/processed_hot_coil_2021.xlsx')
data.set_index('date', inplace=True)

# 2. 运行Basic GARCH回测
run_basic_garch_analyzer(
    data=data,
    output_dir='outputs/热卷Basic_GARCH_2021',
    spot_col='spot',
    futures_col='futures',
    config={
        'enable_rolling_backtest': True,  # 启用滚动回测
        'n_periods': 6,                   # 6个周期
        'window_days': 90,                # 每周期90天
        'backtest_seed': 42,              # 随机种子
        'tax_rate': 0.13                  # 增值税率13%
    }
)

print("Basic GARCH回测完成！")
print(f"报告位置: outputs/热卷Basic_GARCH_2021/")
```

运行脚本：

```bash
python run_basic_garch.py
```

### 方法二：手动调用各模块

```python
from basic_garch_analyzer.rolling_backtest import run_rolling_backtest, plot_rolling_nav_curve, plot_rolling_drawdown
from basic_garch_analyzer.report_generator import generate_html_report
import pandas as pd
import os

# 1. 读取数据
data = pd.read_excel('data/processed_hot_coil_2021.xlsx')
data.set_index('date', inplace=True)

# 2. 配置参数
output_dir = 'outputs/热卷Basic_GARCH_2021'
os.makedirs(output_dir, exist_ok=True)
os.makedirs(f'{output_dir}/figures', exist_ok=True)

# 3. 滚动回测
rolling_results = run_rolling_backtest(
    data=data,
    hedge_ratio=None,  # Basic GARCH会自动计算
    n_periods=6,
    window_days=90,
    seed=42,
    tax_rate=0.13,
    spot_col='spot',
    futures_col='futures'
)

# 4. 生成图表
# 图5：净值曲线（带套保比例）
plot_rolling_nav_curve(
    rolling_results['periods'],
    save_path=f'{output_dir}/figures/5_backtest_results.png'
)

# 图6：回撤分析（带套保比例）
plot_rolling_drawdown(
    rolling_results['periods'],
    save_path=f'{output_dir}/figures/6_drawdown.png'
)

# 5. 生成HTML报告
generate_html_report(
    data=data,
    model_results={'h_actual': rolling_results['all_hedge_ratios']},
    backtest_results=rolling_results,
    output_path=f'{output_dir}/report.html',
    spot_col='spot',
    futures_col='futures',
    model_type='Basic GARCH'
)

print("回测完成！")
```

---

## ECM-GARCH模型回测

### 创建ECM-GARCH回测脚本

创建脚本 `run_ecm_garch.py`：

```python
from model_ecm_garch import fit_ecm_garch
from basic_garch_analyzer.rolling_backtest import run_rolling_backtest, plot_rolling_nav_curve, plot_rolling_drawdown
from basic_garch_analyzer.report_generator import generate_html_report
import pandas as pd
import os
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 1. 读取数据
data = pd.read_excel('data/processed_hot_coil_2021.xlsx')
data.set_index('date', inplace=True)

# 2. ECM-GARCH模型拟合
print("正在拟合ECM-GARCH模型...")
model_results = fit_ecm_garch(
    data,
    p=1, q=1,                    # GARCH(1,1)
    output_dir='outputs/热卷ECM_GARCH_2021/model_results',
    coint_window=120,            # 协整关系滚动窗口
    tax_adjust=True,             # 税点调整
    coupling_method='ect-garch'  # ECT与GARCH耦合方法
)

print(f"误差修正系数 γ = {model_results['gamma']:.3f}")
print(f"基础套保比例 h = {model_results['h_base']:.3f}")
print(f"税点调整后套保比例均值 = {model_results['h_actual'].mean():.3f}")

# 3. 滚动回测
print("正在进行滚动回测...")
rolling_results = run_rolling_backtest(
    data=data,
    hedge_ratio=model_results['h_actual'],  # 使用ECM-GARCH计算的套保比例
    n_periods=6,
    window_days=90,
    seed=42,
    tax_rate=0.13,
    spot_col='spot',
    futures_col='futures'
)

# 4. 生成图表
print("正在生成图表...")
os.makedirs('outputs/热卷ECM_GARCH_2021/figures', exist_ok=True)

# 图1：价格走势
from basic_garch_analyzer.report_generator import plot_price_series
plot_price_series(
    data,
    spot_col='spot',
    futures_col='futures',
    save_path='outputs/热卷ECM_GARCH_2021/figures/1_price_series.png'
)

# 图2：收益率分布
from basic_garch_analyzer.report_generator import plot_returns
plot_returns(
    data,
    spot_col='spot',
    futures_col='futures',
    save_path='outputs/热卷ECM_GARCH_2021/figures/2_returns.png'
)

# 图3：套保比例时变
from basic_garch_analyzer.report_generator import plot_hedge_ratio
plot_hedge_ratio(
    model_results['h_actual'],
    save_path='outputs/热卷ECM_GARCH_2021/figures/3_hedge_ratio.png'
)

# 图4：波动率（ECM-GARCH跳过，因为输出格式不同）
print("注意：图4（波动率）在ECM-GARCH模式下跳过")

# 图5：净值曲线（带套保比例）
plot_rolling_nav_curve(
    rolling_results['periods'],
    save_path='outputs/热卷ECM_GARCH_2021/figures/5_backtest_results.png'
)

# 图6：回撤分析（带套保比例）
plot_rolling_drawdown(
    rolling_results['periods'],
    save_path='outputs/热卷ECM_GARCH_2021/figures/6_drawdown.png'
)

# 图7：性能指标
from basic_garch_analyzer.report_generator import plot_performance_metrics
eval_results = {
    'metrics': {
        'mean_unhedged': rolling_results['avg_return_unhedged'] / 252,
        'mean_hedged': rolling_results['avg_return_hedged'] / 252,
        'std_unhedged': rolling_results['all_returns_unhedged'].std(),
        'std_hedged': rolling_results['all_returns_hedged'].std(),
        'sharpe_unhedged': rolling_results['avg_sharpe_unhedged'],
        'sharpe_hedged': rolling_results['avg_sharpe_hedged'],
        'max_dd_unhedged': rolling_results['avg_max_dd_unhedged'],
        'max_dd_hedged': rolling_results['avg_max_dd_hedged'],
        'var_95_unhedged': rolling_results['all_returns_unhedged'].quantile(0.05),
        'var_95_hedged': rolling_results['all_returns_hedged'].quantile(0.05),
        'cvar_95_unhedged': rolling_results['all_returns_unhedged'][rolling_results['all_returns_unhedged'] <= rolling_results['all_returns_unhedged'].quantile(0.05)].mean(),
        'cvar_95_hedged': rolling_results['all_returns_hedged'][rolling_results['all_returns_hedged'] <= rolling_results['all_returns_hedged'].quantile(0.05)].mean(),
    }
}
plot_performance_metrics(
    eval_results,
    save_path='outputs/热卷ECM_GARCH_2021/figures/7_performance_metrics.png'
)

# 图8：汇总表格
from basic_garch_analyzer.report_generator import plot_summary_table
plot_summary_table(
    eval_results,
    save_path='outputs/热卷ECM_GARCH_2021/figures/8_summary_table.png'
)

# 5. 生成Excel报告
print("正在生成Excel报告...")
from basic_garch_analyzer.rolling_backtest import save_rolling_backtest_report
save_rolling_backtest_report(
    rolling_results,
    excel_path='outputs/热卷ECM_GARCH_2021/rolling_backtest_report.xlsx',
    csv_path='outputs/热卷ECM_GARCH_2021/rolling_backtest_report.csv'
)

# 6. 生成HTML报告
print("正在生成HTML报告...")
generate_html_report(
    data=data,
    model_results=model_results,
    backtest_results=rolling_results,
    output_path='outputs/热卷ECM_GARCH_2021/report.html',
    spot_col='spot',
    futures_col='futures',
    model_type='ECM-GARCH',
    ecm_params={
        'gamma': model_results['gamma'],
        'h_base': model_results['h_base'],
        'coint_window': 120
    }
)

print("\nECM-GARCH回测完成！")
print(f"报告位置: outputs/热卷ECM_GARCH_2021/")
```

运行脚本：

```bash
python run_ecm_garch.py
```

---

## 两种模型对比

### 模型差异

| 特性 | Basic GARCH | ECM-GARCH |
|------|-------------|-----------|
| **理论基础** | 时变相关性 | 协整关系 + 误差修正 |
| **套保比例计算** | h = Cov(r_s, r_f) / Var(r_f) | h = 基础比例 + ECT调整 |
| **长期均衡** | 不考虑 | 考虑（协整关系） |
| **误差修正** | 无 | γ × ECT（γ < 0为反向修正） |
| **适用场景** | 短期套保 | 中长期套保，强调均衡回归 |

### 性能指标对比（热卷2021后数据示例）

| 指标 | Basic GARCH | ECM-GARCH |
|------|-------------|-----------|
| 方差降低比例 | 84.24% | 72.11% |
| Ederington有效性 | 0.8424 | 0.7211 |
| 套保后夏普比率 | 0.0225 | 0.0067 |
| 套保后最大回撤 | -3.50% | -4.53% |

### 如何选择模型

- **选择Basic GARCH**：
  - 更关注短期波动率对冲
  - 需要更高的方差降低效果
  - 数据长度较短（< 2年）

- **选择ECM-GARCH**：
  - 强调现货期货长期均衡关系
  - 希望捕捉均衡回归的套保机会
  - 数据长度足够（≥ 2年，协整检验需要）

---

## 输出文件说明

### 文件结构

```
outputs/<模型名称>_<品种>_<年份>/
├── report.html                           # HTML交互式报告
├── rolling_backtest_report.xlsx          # Excel详细报告
├── rolling_backtest_report.csv           # CSV数据报告
├── figures/                              # 图表目录
│   ├── 1_price_series.png                # 价格走势
│   ├── 2_returns.png                     # 收益率分布
│   ├── 3_hedge_ratio.png                 # 套保比例时变
│   ├── 4_volatility.png                  # 波动率（Basic GARCH only）
│   ├── 5_backtest_results.png            # 6周期净值曲线
│   ├── 6_drawdown.png                    # 6周期回撤分析
│   ├── 7_performance_metrics.png         # 性能指标对比
│   └── 8_summary_table.png               # 汇总表格
└── model_results/                        # 模型结果（ECM-GARCH only）
    └── h_ecm_garch.csv                   # 套保比例时间序列
```

### HTML报告内容

- **核心指标卡片**：方差降低、Ederington、夏普比率、最大回撤
- **数据配置表**：现货/期货列名、数据期间、样本量
- **8张详细图表**：可视化展示回测结果
- **完整指标表**：未套保 vs 套保后各项指标对比

### Excel报告内容

**Summary工作表**：
- 6个周期的汇总统计（平均值）
- 样本内外表现对比

**Rolling Backtest工作表**：
- 每个周期的详细数据：
  - 起始/结束日期
  - 未套保收益率
  - 套保收益率
  - 收益率改善
  - 方差降低
  - 最大回撤
  - 夏普比率

---

## 常见问题

### Q1: 如何修改滚动回测参数？

编辑 `basic_garch_analyzer/config.py`：

```python
# 滚动回测参数
enable_rolling_backtest: bool = True
n_periods: int = 6              # 修改周期数（建议4-8）
window_days: int = 90           # 修改每周期天数（建议60-120）
backtest_seed: int = 42         # 随机种子（保持结果可复现）
```

或在运行时传入：

```python
run_rolling_backtest(
    data,
    n_periods=8,      # 8个周期
    window_days=60,   # 每周期60天
    seed=123
)
```

### Q2: 如何调整税率？

```python
run_rolling_backtest(
    data,
    tax_rate=0.13  # 13%增值税（根据实际情况调整）
)
```

或修改配置：

```python
# config.py
tax_rate: float = 0.13  # 税率（0.13 = 13%）
```

### Q3: 为什么ECM-GARCH缺少图4（波动率）？

ECM-GARCH模型的输出格式与Basic GARCH不同：
- Basic GARCH：输出 `sigma_s`, `sigma_f`（波动率序列）
- ECM-GARCH：输出 `h_actual`（套保比例序列），不包含波动率

因此图4在ECM-GARCH模式下会被跳过。

### Q4: 如何避免交割月份？

滚动回测默认避开1月、5月、10月（热卷主力合约交割月）。如需修改：

编辑 `basic_garch_analyzer/rolling_backtest.py` 中的 `avoid_delivery_months` 参数：

```python
def run_rolling_backtest(
    ...
    avoid_delivery_months=[1, 5, 10],  # 根据品种修改
    ...
):
```

### Q5: 套保比例如何计算？

**Basic GARCH**：
```python
h = Cov(r_s, r_f) / Var(r_f)
h_actual = h / (1 + tax_rate)  # 税点调整
```

**ECM-GARCH**：
```python
# 第一步：估计协整关系
spot_t = α + β × futures_t + ε_t

# 第二步：计算误差修正项
ECT_t = spot_t - α - β × futures_t

# 第三步：套保比例
h_t = h_base + γ × ECT_t
h_actual = h_t / (1 + tax_rate)
```

其中：
- `h_base` = 基础套保比例（基于协整关系）
- `γ` = 误差修正系数（γ < 0 表示反向修正）
- `ECT` = 误差修正项（偏离长期均衡的程度）

### Q6: 如何评估套保效果？

主要关注以下指标：

1. **方差降低比例**：
   - > 80%：优秀
   - 60-80%：良好
   - < 60%：一般

2. **Ederington有效性**：
   - > 0.8：优秀
   - 0.6-0.8：良好
   - < 0.6：一般

3. **夏普比率**：
   - 套保后 > 未套保：改善
   - 越高越好

4. **最大回撤**：
   - 套保后 < 未套保：风险降低
   - 绝对值越小越好

### Q7: 内存不足怎么办？

如果数据量很大导致内存不足：

```python
# 减少滚动窗口
model_results = fit_ecm_garch(
    data,
    coint_window=60,  # 从120减少到60
    ...
)

# 或减少回测周期
rolling_results = run_rolling_backtest(
    data,
    n_periods=4,  # 从6减少到4
    ...
)
```

### Q8: 如何批量运行多个品种？

创建批量脚本：

```python
import pandas as pd

# 配置品种列表
configs = [
    {'name': '热卷', 'file': 'data/hot_coil.xlsx'},
    {'name': '中板', 'file': 'data/medium_plate.xlsx'},
    {'name': '乙二醇', 'file': 'data/eg.xlsx'}
]

for config in configs:
    print(f"正在处理 {config['name']}...")

    # 读取数据
    data = pd.read_excel(config['file'])
    data.set_index('date', inplace=True)

    # 运行回测
    run_basic_garch_analyzer(
        data=data,
        output_dir=f'outputs/{config["name"]}_Basic_GARCH',
        spot_col='spot',
        futures_col='futures'
    )

    print(f"{config['name']} 完成！\n")
```

---

## 附录：完整示例代码

### 示例1：Basic GARCH完整流程

```python
from basic_garch_analyzer import run_basic_garch_analyzer
import pandas as pd

# 1. 数据准备
data = pd.read_excel('data/热卷_2021.xlsx')
data['date'] = pd.to_datetime(data['date'])
data = data[data['date'] >= '2021-01-01']
data.set_index('date', inplace=True)

# 2. 运行回测
run_basic_garch_analyzer(
    data=data,
    output_dir='outputs/热卷Basic_2021',
    spot_col='spot',
    futures_col='futures',
    config={
        'enable_rolling_backtest': True,
        'n_periods': 6,
        'window_days': 90,
        'tax_rate': 0.13
    }
)
```

### 示例2：ECM-GARCH完整流程

```python
from model_ecm_garch import fit_ecm_garch
from basic_garch_analyzer.rolling_backtest import (
    run_rolling_backtest,
    plot_rolling_nav_curve,
    plot_rolling_drawdown,
    save_rolling_backtest_report
)
from basic_garch_analyzer.report_generator import (
    generate_html_report,
    plot_price_series,
    plot_returns,
    plot_hedge_ratio,
    plot_performance_metrics,
    plot_summary_table
)
import pandas as pd
import os

# 1. 数据准备
data = pd.read_excel('data/热卷_2021.xlsx')
data['date'] = pd.to_datetime(data['date'])
data = data[data['date'] >= '2021-01-01']
data.set_index('date', inplace=True)

output_dir = 'outputs/热卷ECM_2021'
os.makedirs(output_dir, exist_ok=True)

# 2. 模型拟合
model_results = fit_ecm_garch(
    data,
    p=1, q=1,
    output_dir=f'{output_dir}/model_results',
    coint_window=120,
    tax_adjust=True
)

# 3. 滚动回测
rolling_results = run_rolling_backtest(
    data=data,
    hedge_ratio=model_results['h_actual'],
    n_periods=6,
    window_days=90,
    seed=42
)

# 4. 生成图表
figures_dir = f'{output_dir}/figures'
os.makedirs(figures_dir, exist_ok=True)

plot_price_series(data, 'spot', 'futures',
    save_path=f'{figures_dir}/1_price_series.png')
plot_returns(data, 'spot', 'futures',
    save_path=f'{figures_dir}/2_returns.png')
plot_hedge_ratio(model_results['h_actual'],
    save_path=f'{figures_dir}/3_hedge_ratio.png')
plot_rolling_nav_curve(rolling_results['periods'],
    save_path=f'{figures_dir}/5_backtest_results.png')
plot_rolling_drawdown(rolling_results['periods'],
    save_path=f'{figures_dir}/6_drawdown.png')

# 5. 生成报告
save_rolling_backtest_report(
    rolling_results,
    excel_path=f'{output_dir}/rolling_backtest_report.xlsx',
    csv_path=f'{output_dir}/rolling_backtest_report.csv'
)

generate_html_report(
    data=data,
    model_results=model_results,
    backtest_results=rolling_results,
    output_path=f'{output_dir}/report.html',
    spot_col='spot',
    futures_col='futures',
    model_type='ECM-GARCH'
)
```

---

## 联系与支持

如有问题或建议，请联系项目负责人或提交Issue。

**最后更新**: 2026-02-28
