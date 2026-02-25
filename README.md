# 热卷现货-期货套保比例计算模型

基于条件协方差理论，为热卷上海地区现货与SHFE热卷期货构建四种动态套保比例计算模型。

## 项目概述

本项目实现了四种GARCH类套保模型：

1. **基础GARCH** - 使用二元GARCH模型估计时变协方差
2. **ECM-GARCH** - 考虑现货与期货的长期均衡关系（误差修正模型）
3. **DCC-GARCH** - 考虑动态时变相关性
4. **ECM-DCC-GARCH** - 综合模型，结合基差修正和动态相关性

### 核心公式

```
理论套保比例: h_t = Cov_t(ΔS, ΔF) / Var_t(ΔF)
实际套保比例: h_实际 = h_t / 1.13  (考虑13%增值税)
```

## 文件结构

```
GARCH 模型套保方案/
├── 基差数据.xlsx                  # 原始数据
├── main.py                       # 主程序入口 ⭐
├── requirements.txt              # 依赖库列表
├── data_preprocessing.py         # 数据预处理模块
├── eda_analysis.py               # 探索性数据分析
├── model_basic_garch.py          # 模型1: 基础GARCH
├── model_ecm_garch.py            # 模型2: ECM-GARCH
├── model_dcc_garch.py            # 模型3: DCC-GARCH
├── model_ecm_dcc_garch.py        # 模型4: ECM-DCC-GARCH
├── hedging_effectiveness.py      # 效果评估
├── generate_report.py            # 报告生成
├── outputs/                      # 输出目录
│   ├── figures/                  # 图表
│   ├── model_results/            # 各模型输出
│   ├── hedging_report.html       # 完整报告 ⭐
│   └── hedging_results.xlsx      # Excel结果
└── README.md                     # 本文件
```

## 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖库

- pandas >= 2.0.0
- numpy >= 1.24.0
- openpyxl >= 3.1.0
- arch >= 6.0.0
- statsmodels >= 0.14.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0
- plotly >= 5.18.0
- scipy >= 1.11.0
- scikit-learn >= 1.3.0
- kaleido >= 0.2.0

## 使用方法

### 快速开始

```bash
# 1. 确保基差数据.xlsx 在当前目录
# 2. 运行主程序
python main.py
```

### 分步骤运行

```python
# 数据预处理
from data_preprocessing import preprocess_data
data = preprocess_data('基差数据.xlsx')

# 探索性分析
from eda_analysis import generate_eda_report
eda_results = generate_eda_report(data)

# 拟合模型
from model_basic_garch import fit_basic_garch
h_basic = fit_basic_garch(data)

# 评估效果
from hedging_effectiveness import compare_models
comparison_df = compare_models(data, model_results)
```

## 输出说明

### 主要输出文件

1. **hedging_report.html** - 完整的分析报告，推荐首先查看
2. **hedging_results.xlsx** - Excel格式的综合结果文件
3. **outputs/figures/** - 所有可视化图表
4. **outputs/model_results/** - 四种模型的逐日套保比例

### 图表列表

- `price_series.png` - 现货与期货价格走势对比
- `returns_volatility.png` - 收益率波动图
- `basis_spread.png` - 基差时变图
- `hedge_ratio_comparison.png` - 四种模型套保比例对比
- `dynamic_correlation.png` - DCC模型动态相关系数
- `variance_reduction.png` - 套保效果对比
- `sharpe_ratio_comparison.png` - 夏普比率对比
- `max_drawdown_comparison.png` - 最大回撤对比
- `in_sample_vs_out_sample.png` - 样本内外效果对比

### 模型输出文件

- `h_basic_garch.csv` - 基础GARCH套保比例序列
- `h_ecm_garch.csv` - ECM-GARCH套保比例序列
- `h_dcc_garch.csv` - DCC-GARCH套保比例序列
- `h_ecm_dcc_garch.csv` - ECM-DCC-GARCH套保比例序列
- `rho_t.csv` - DCC动态相关系数

## 数据说明

### 数据来源

- **现货**: 热轧板卷：4.75mm：汇总价格：上海（日）
- **期货**: SHFE：热轧板卷：主力合约：收盘价（日）

### 数据格式

Excel文件 `基差数据.xlsx` 应包含以下列：
- 日期（第1列）
- 期货价格（第3列）
- 上海现货价格（第4列）

## 模型说明

### 模型1: 基础GARCH

使用单变量GARCH(1,1)模型分别估计现货和期货的条件波动率，然后计算协方差和套保比例。

**优点**: 实现简单，计算快速
**适用**: 波动聚集性明显，但相关性相对稳定的市场

### 模型2: ECM-GARCH

在GARCH模型基础上加入误差修正项，考虑现货与期货的长期均衡关系。

**优点**: 考虑基差修正机制
**适用**: 有明显基差修复规律的商品市场

### 模型3: DCC-GARCH

使用动态条件相关模型，允许现货与期货的相关性随时间变化。

**优点**: 动态相关系数自动调整套保比例
**适用**: 相关性不稳定、频繁波动的市场

### 模型4: ECM-DCC-GARCH

综合模型，结合基差修正 + 动态相关性 + 时变波动。

**优点**: 学术界和实务界公认的最强模型
**适用**: 对精度要求最高的套保场景

## 套保效果评估指标

### 方差降低比例 (Variance Reduction)

```
HE = 1 - Var(套保组合) / Var(未套保现货)
```

数值越大，套保效果越好。

### Ederington指标

与方差降低比例相同，是经典的套保效果评估指标。

### 夏普比率

```
Sharpe = E(R) / σ(R)
```

衡量单位风险下的超额收益。

### 最大回撤

衡量最坏情况下的损失程度。

## 技术细节

### GARCH(1,1)模型

```
σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
```

### DCC模型

```
Q_t = (1 - α - β)·Q̄ + α·ε_{t-1}·ε'_{t-1} + β·Q_{t-1}
R_t = Q_t^{*-1/2}·Q_t·Q_t^{*-1/2}
```

### ECM模型

```
ΔS_t = α + h·ΔF_t + γ·ect_{t-1} + ε_t
```

其中 `ect = S - β·F` 是误差修正项。

## 注意事项

1. **增值税调整**: 所有套保比例已除以1.13以考虑13%增值税
2. **异常值处理**: 套保比例被限制在[0, 2]范围内
3. **数据质量**: 请确保输入数据无缺失值和异常值
4. **计算时间**: 完整运行约需5-10分钟，取决于数据量

## 风险提示

- 历史数据不代表未来表现
- 模型假设可能不适用于所有市场环境
- 交易成本和滑点未在模型中考虑
- 极端市场条件下模型可能失效
- 增值税税率变化会影响实际套保比例

## 后续优化方向

1. 添加滚动窗口预测（rolling window）
2. 支持多品种套保（跨品种套利）
3. 实时数据接入与自动套保
4. 交易成本考虑
5. 止损策略优化

## 参考文献

1. Engle, R. F. (2002). "Dynamic Conditional Correlation: A Simple Class of Multivariate Generalized Autoregressive Conditional Heteroskedasticity Models."
2. Kroner, K. F., & Sultan, J. (1993). "Time-varying distributions and dynamic hedging with foreign currency futures."
3. Lien, D., & Tse, Y. K. (2002). "Some recent developments in futures hedging."

## 作者

Claude Code

## 许可证

MIT License

## 更新日志

- 2026-02: 初始版本发布
