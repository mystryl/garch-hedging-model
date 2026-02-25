# Excel报告解释文档

## 项目状态：✅ 已完成

本项目的GARCH套保模型已成功实现并生成完整报告。此文档用于解释Excel输出文件的内容和参数设定。

---

## Excel报告结构说明

文件位置：`outputs/hedging_results.xlsx`

### 工作表1：原始数据
| 列名 | 含义 | 说明 |
|------|------|------|
| date | 日期 | 交易日 |
| spot | 现货价格 | 热卷上海现货价格（元/吨） |
| futures | 期货价格 | SHFE热卷期货主力合约收盘价（元/吨） |
| r_s | 现货收益率 | 对数收益率：ln(S_t/S_{t-1}) |
| r_f | 期货收益率 | 对数收益率：ln(F_t/F_{t-1}) |
| spread | 基差 | 现货-期货价差（元/吨） |

### 工作表2：收益率数据
仅包含收益率相关列：date, r_s, r_f, spread

### 工作表3：Basic GARCH（基础GARCH模型）
| 列名 | 含义 | 计算方式 |
|------|------|----------|
| date | 日期 | 交易日 |
| h_theoretical | 理论套保比例 | Cov_t(ΔS,ΔF) / Var_t(ΔF) |
| h_actual | 实际套保比例 | h_theoretical / 1.13（考虑13%增值税） |
| sigma_s | 现货条件波动率 | GARCH(1,1)模型估计 |
| sigma_f | 期货条件波动率 | GARCH(1,1)模型估计 |
| cov_sf | 条件协方差 | rho * sigma_s * sigma_f |
| var_f | 期货条件方差 | sigma_f² |

### 工作表4：ECM GARCH（误差修正GARCH模型）
| 列名 | 含义 | 计算方式 |
|------|------|----------|
| date | 日期 | 交易日 |
| h_theoretical | 理论套保比例 | ECM估计的时变套保比例 |
| h_actual | 实际套保比例 | h_theoretical / 1.13 |
| h_ecm_base | ECM基础套保比例 | 误差修正模型估计的h系数 |
| ect | 误差修正项 | S - (β0 + β1·F)，衡量偏离长期均衡的程度 |
| sigma_ecm | ECM残差波动率 | 残差序列的GARCH波动率 |
| sigma_f | 期货波动率 | GARCH(1,1)估计 |

### 工作表5：DCC GARCH（动态条件相关GARCH模型）
| 列名 | 含义 | 计算方式 |
|------|------|----------|
| date | 日期 | 交易日 |
| h_theoretical | 理论套保比例 | 动态相关系数调整的套保比例 |
| h_actual | 实际套保比例 | h_theoretical / 1.13 |
| rho_t | 动态相关系数 | DCC模型估计的时变相关系数 |
| sigma_s | 现货条件波动率 | GARCH(1,1)估计 |
| sigma_f | 期货条件波动率 | GARCH(1,1)估计 |
| cov_sf | 条件协方差 | rho_t * sigma_s * sigma_f |
| var_f | 期货条件方差 | sigma_f² |

### 工作表6：ECM DCC GARCH（综合模型）
| 列名 | 含义 | 计算方式 |
|------|------|----------|
| date | 日期 | 交易日 |
| h_theoretical | 理论套保比例 | 综合ECM和DCC的套保比例 |
| h_actual | 实际套保比例 | h_theoretical / 1.13 |
| h_ecm_base | ECM基础系数 | 误差修正模型的h系数 |
| rho_t | 动态相关系数 | DCC估计的时变相关性 |
| ect | 误差修正项 | 偏离长期均衡的程度 |
| sigma_ecm | ECM残差波动率 | 残差序列的GARCH波动率 |
| sigma_f | 期货波动率 | GARCH(1,1)估计 |
| vol_ratio | 波动率比率 | sigma_ecm / sigma_f |
| correlation_adjustment | 相关性调整 | abs(rho_t)，用于调整套保比例 |

### 工作表7：效果评估
| 列名 | 含义 | 计算方式 |
|------|------|----------|
| 模型 | 模型名称 | Basic GARCH, ECM-GARCH, DCC-GARCH, ECM-DCC-GARCH |
| 方差降低比例 | 套保效果 | 1 - Var(套保后)/Var(套保前)，越大越好 |
| Ederington指标 | 经典有效性指标 | 与方差降低比例相同 |
| 套保前波动率 | 未套保现货风险 | 收益率标准差 |
| 套保后波动率 | 套保组合风险 | 套保后收益率标准差 |
| 夏普比率(套保前) | 未套保收益风险比 | 均值/标准差 |
| 夏普比率(套保后) | 套保后收益风险比 | 套保组合均值/标准差 |
| 最大回撤(套保前) | 未套保最大损失 | 累计收益曲线的最大回撤 |
| 最大回撤(套保后) | 套保后最大损失 | 套保组合累计收益的最大回撤 |
| VaR_95(套保前) | 95%置信度风险值 | 未套保收益率的5%分位数 |
| VaR_95(套保后) | 95%置信度风险值 | 套保后收益率的5%分位数 |

### 工作表8：样本内外测试
| 列名 | 含义 | 说明 |
|------|------|------|
| Unnamed: 0 | 模型名称 | 行索引 |
| 样本内方差降低 | 训练集效果 | 前80%数据的套保效果 |
| 样本外方差降低 | 测试集效果 | 后20%数据的套保效果 |

**分割比例**：训练集80%，测试集20%

### 工作表9：模型参数汇总
| 列名 | 含义 | 说明 |
|------|------|------|
| 模型 | 模型名称 | 四种模型 |
| 平均套保比例 | 套保比例均值 | 时变套保比例的平均值 |
| 套保比例标准差 | 套保比例波动 | 衡量套保比例的稳定性 |
| ECM_h系数 | 期货收益率系数 | ECM模型中的ΔF_t系数 |
| ECM_误差修正系数 | 基差修正力度 | ECM模型中的γ系数，负值表示反向修正 |
| 协整_R² | 长期均衡拟合度 | 现货与期货长期关系的R² |
| DCC_α | 短期冲击参数 | DCC模型的α参数，衡量相关性对短期冲击的敏感度 |
| DCC_β | 相关性持续参数 | DCC模型的β参数，衡量相关性的持续性 |

---

## 观察窗口确定方法

### 1. **滚动统计窗口（30天）**
- **用途**：计算滚动相关系数、滚动波动率
- **位置**：`eda_analysis.py:179`，`model_basic_garch.py:96`
- **设定依据**：月度交易日（约20-22天）的近似值，平衡稳定性和敏感性
- **代码**：`window = 30`

### 2. **GARCH滚动波动窗口（30天）**
- **用途**：当GARCH拟合失败时的替代方案
- **位置**：`model_ecm_garch.py:153`, `model_ecm_dcc_garch.py:147-148`
- **设定依据**：月度交易日，提供足够的观测值估计波动率
- **代码**：`window = 30`

### 3. **平滑窗口（3-5天）**
- **用途**：对套保比例序列进行平滑处理
- **位置**：
  - ECM-GARCH: `window_smooth = 5`
  - ECM-DCC-GARCH: `window_smooth = 3`
- **设定依据**：短期平滑，避免过度平滑导致延迟
- **代码**：`rolling(window=window_smooth, center=True, min_periods=1)`

### 4. **样本内外分割（80%/20%）**
- **用途**：评估模型的样本外泛化能力
- **位置**：`hedging_effectiveness.py:113`
- **设定依据**：
  - 训练集：前80%数据（约2312个观测）
  - 测试集：后20%数据（约579个观测）
- **代码**：`train_ratio = 0.8`

### 5. **DCC参数搜索窗口**
- **用途**：网格搜索最优DCC参数
- **位置**：`model_dcc_garch.py:46-47`
- **搜索范围**：
  - α: 0.01-0.15
  - β: 0.80-0.98
  - 约束：α + β < 1

---

## 窗口选择的统计学依据

### 为什么是30天？
1. **月度周期**：约等于一个月的交易日，捕捉月度周期性
2. **统计有效性**：30个观测值提供足够的自由度估计波动率
3. **市场适应性**：足以反映市场变化，但不会过度敏感

### 为什么平滑窗口是3-5天？
1. **降低噪音**：过滤掉日度数据的随机波动
2. **保持灵敏性**：小窗口避免信号延迟
3. **中心化**：使用`center=True`确保平滑后的值对齐原始时间点

### 为什么80%/20%分割？
1. **足够训练**：80%数据提供充足样本估计模型参数
2. **有效测试**：20%数据（约579天，近2年）足以验证泛化能力
3. **行业标准**：金融计量经济学常用比例

---

## 核心参数总结

| 参数 | 值 | 用途 | 文件位置 |
|------|---|------|----------|
| GARCH阶数 | (1,1) | 波动建模 | 所有模型文件 |
| 滚动统计窗口 | 30天 | EDA分析 | eda_analysis.py |
| 滚动相关窗口 | 60天 | 基础GARCH | model_basic_garch.py |
| 波动替代窗口 | 30天 | GARCH失败时备用 | ECM/ECM-DCC模型 |
| 平滑窗口 | 3-5天 | 套保比例平滑 | ECM/ECM-DCC模型 |
| 样本分割 | 80%/20% | 效果评估 | hedging_effectiveness.py |
| 增值税率 | 13% | 套保比例调整 | 所有模型 |
| 套保范围 | [0, 2] | 异常值限制 | 所有模型 |

---

## 用户自定义参数建议

如果需要调整窗口大小，可考虑：

**短期策略**（更灵敏）：
- 滚动窗口：20天
- 平滑窗口：3天

**长期策略**（更稳定）：
- 滚动窗口：60天
- 平滑窗口：10天

**修改位置**：
- 模型文件中的`window`参数
- EDA分析中的`window`参数
- 主程序不需要修改

**数据来源**：
- 现货：热轧板卷：4.75mm：汇总价格：上海（日）
- 期货：SHFE：热轧板卷：主力合约：收盘价（日）

**核心公式**：`h_t = Cov_t(ΔS,ΔF) / Var_t(ΔF)`

其中 `h_实际 = h_t / 1.13`（考虑13%增值税）

---

## 四种模型说明

### 模型1：基础GARCH（Bivariate GARCH）
- **核心思想**：使用二元GARCH模型估计现货与期货的条件协方差和条件方差
- **适用场景**：波动聚集性明显，但相关性相对稳定的市场
- **实现方法**：使用 `arch` 包的 BGARCH 模型

### 模型2：ECM-GARCH（误差修正GARCH）
- **核心思想**：考虑现货与期货的长期均衡关系（基差修正）
- **核心公式**：`ΔS_t = α + h·ΔF_t + γ·(S_{t-1} - F_{t-1}) + ε_t`
- **适用场景**：有明显基差修复规律的商品市场
- **实现步骤**：协整检验 → 误差修正模型 → GARCH

### 模型3：DCC-GARCH（动态条件相关GARCH）
- **核心思想**：现货与期货的相关性随时间变化
- **核心特点**：动态相关系数 `ρ_t` 自动调整套保比例
- **适用场景**：相关性不稳定、频繁波动的市场
- **实现方法**：先单变量GARCH，再DCC估计动态相关性

### 模型4：ECM-DCC-GARCH（综合模型）
- **核心思想**：结合基差修正 + 动态相关性 + 时变波动
- **特点**：学术界和实务界公认的最强模型
- **适用场景**：对精度要求最高的套保场景

---

## 技术实现细节

### 依赖库

```python
# requirements.txt
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0  # 读取Excel
arch>=6.0.0      # GARCH模型
statsmodels>=0.14.0  # 统计检验、协整检验
matplotlib>=3.7.0   # 绘图
seaborn>=0.12.0     # 高级绘图
plotly>=5.18.0      # 交互式图表
scipy>=1.11.0       # 科学计算
scikit-learn>=1.3.0 # 机器学习（如需）
```

### 文件结构

```
GARCH 模型套保方案/
├── 基差数据.xlsx                  # 原始数据
├── data_preprocessing.py          # 数据预处理
├── model_basic_garch.py           # 模型1：基础GARCH
├── model_ecm_garch.py             # 模型2：ECM-GARCH
├── model_dcc_garch.py             # 模型3：DCC-GARCH
├── model_ecm_dcc_garch.py         # 模型4：ECM-DCC-GARCH
├── hedging_effectiveness.py       # 效果评估
├── generate_report.py             # 报告生成
├── main.py                        # 主程序入口
├── requirements.txt               # 依赖库
├── outputs/                       # 输出目录
│   ├── figures/                   # 图表
│   ├── hedging_report.html        # 完整报告
│   ├── hedging_results.xlsx       # Excel结果
│   └── model_results/             # 各模型输出
│       ├── h_basic_garch.csv
│       ├── h_ecm_garch.csv
│       ├── h_dcc_garch.csv
│       └── h_ecm_dcc_garch.csv
└── README.md                      # 使用说明
```

---

## 输出文件说明

### Excel文件工作表

1. **原始数据** - 包含日期、现货价格、期货价格、收益率和基差
2. **收益率数据** - 仅包含收益率相关列
3. **Basic GARCH** - 基础GARCH模型的套保比例和波动率估计
4. **ECM GARCH** - 误差修正GARCH模型的套保比例
5. **DCC GARCH** - 动态条件相关GARCH模型的套保比例
6. **ECM DCC GARCH** - 综合模型的套保比例
7. **效果评估** - 四种模型的套保效果对比
8. **样本内外测试** - 训练集和测试集的效果对比
9. **模型参数汇总** - 各模型的关键参数

### 图表文件

- `price_series.png` - 现货与期货价格走势对比
- `returns_volatility.png` - 收益率波动图
- `basis_spread.png` - 基差时变图
- `hedge_ratio_comparison.png` - 四种模型套保比例对比
- `dynamic_correlation.png` - DCC模型动态相关系数
- `variance_reduction.png` - 套保效果对比（柱状图）
- `returns_distribution.png` - 收益率分布
- `correlation_scatter.png` - 现货与期货相关性散点图
- `rolling_statistics.png` - 滚动统计量
- `sharpe_ratio_comparison.png` - 夏普比率对比
- `max_drawdown_comparison.png` - 最大回撤对比
- `in_sample_vs_out_sample.png` - 样本内外效果对比

---

## 验证与测试

### 验证清单
1. ✅ 数据加载正确，无缺失值
2. ✅ 收益率计算正确
3. ✅ 协整检验通过（p-value < 0.05）
4. ✅ GARCH模型收敛
5. ✅ 套保比例在合理范围内（0 < h < 2）
6. ✅ 税点调整正确
7. ✅ 所有图表正常生成
8. ✅ HTML报告可正常打开
9. ✅ Excel文件包含所有工作表

### 测试方法
```bash
# 安装依赖
pip install -r requirements.txt

# 运行主程序
python main.py

# 检查输出
ls outputs/
ls outputs/figures/
```

---

## 关键文件路径

- **原始数据**：`/Users/mystryl/Documents/GARCH 模型套保方案/基差数据.xlsx`
- **研究文档**：`/Users/mystryl/Documents/GARCH 模型套保方案/基于条件协方差的套保比例研究.md`
- **工作目录**：`/Users/mystryl/Documents/GARCH 模型套保方案/`
- **Excel输出**：`/Users/mystryl/Documents/GARCH 模型套保方案/outputs/hedging_results.xlsx`
- **HTML报告**：`/Users/mystryl/Documents/GARCH 模型套保方案/outputs/hedging_report.html`

---

## 使用说明

### 快速开始

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **运行完整分析**
   ```bash
   python main.py
   ```

3. **查看结果**
   - 打开 `outputs/hedging_results.xlsx` 查看完整数据
   - 打开 `outputs/hedging_report.html` 查看交互式报告
   - 查看 `outputs/figures/` 目录下的所有图表

### 自定义分析

如需修改窗口参数或模型配置，请参考本文档的"用户自定义参数建议"部分。

---

## 后续优化方向

1. 添加滚动窗口预测（rolling window）
2. 支持多品种套保（跨品种套利）
3. 实时数据接入与自动套保
4. 交易成本考虑
5. 止损策略优化

---

## 联系与支持

如有问题或建议，请联系项目维护者。

---

**文档生成日期**：2026-02-25
**项目版本**：1.0.0
**状态**：✅ 已完成
