# 模型运行脚本使用指南

## 可用的运行脚本

### 🎯 快速开始

#### 1. 快速验证所有模型
```bash
python verify_models.py
```
**说明：** 快速测试所有模型是否正常工作（使用模拟数据）

---

## 📊 完整回测脚本

### 模型1：ECM-GARCH
**脚本：** `run_ecm_garch.py`

**特点：**
- 考虑现货与期货的长期均衡关系（协整）
- 误差修正机制（ECT）
- 时变协整参数估计

**运行：**
```bash
python run_ecm_garch.py
```

**输出：** `outputs/热卷ECM_GARCH_2021/`

---

### 模型2：DCC-GARCH ✨
**脚本：** `run_dcc_garch.py`

**特点：**
- 使用mgarch库实现DCC-GARCH
- 捕捉现货-期货的时变相关性
- 动态最小方差套保比率

**运行：**
```bash
python run_dcc_garch.py
```

**输出：** `outputs/热卷DCC_GARCH_2021/`

**关键配置：**
```python
DCC_CONFIG = {
    'p': 1,              # GARCH(p,q)
    'q': 1,
    'dist': 't'          # 分布: 'norm' 或 't'
}
```

---

### 模型3：ECM-DCC-GARCH ✨
**脚本：** `run_ecm_dcc_garch.py`

**特点：**
- 综合模型：协整 + DCC-GARCH
- 考虑长期均衡关系
- 捕捉时变相关性和波动
- **学术界和实务界公认的最强模型**

**运行：**
```bash
python run_ecm_dcc_garch.py
```

**输出：** `outputs/热卷ECM_DCC_GARCH_2021/`

**关键配置：**
```python
ECM_DCC_CONFIG = {
    'p': 1,
    'q': 1,
    'coint_window': 120,     # 协整窗口（天）
    'tax_adjust': True,
    'coupling_method': 'ect-garch'
}
```

---

## ⚙️ 通用配置

所有脚本都包含以下可配置参数：

### 数据配置
```python
DATA_FILE = 'data/hot_coil_2021_latest.xlsx'  # 数据文件路径
OUTPUT_DIR = 'outputs/热卷XXX_GARCH_2021'      # 输出目录
SPOT_COL = 'spot'                               # 现货价格列名
FUTURES_COL = 'futures'                         # 期货价格列名
START_DATE = '2021-01-01'                       # 起始日期
END_DATE = None                                 # 结束日期
```

### 回测配置
```python
BACKTEST_CONFIG = {
    'n_periods': 6,      # 回测周期数
    'window_days': 90,   # 每个周期天数
    'seed': 42,          # 随机种子
    'tax_rate': 0.13     # 增值税率（13%）
}
```

---

## 📁 输出文件结构

运行任一脚本后，将生成：

```
outputs/<品种>_<模型>_<年份>/
├── report.html                      # HTML可视化报告
├── rolling_backtest_report.xlsx    # Excel详细报告
├── rolling_backtest_report.csv     # CSV数据报告
├── model_results/
│   └── h_<模型>.csv                 # 套保比例时序数据
└── figures/
    ├── 1_price_series.png          # 价格走势
    ├── 2_returns.png               # 收益率分布
    ├── 3_hedge_ratio.png           # 套保比例时变
    ├── 5_backtest_results.png      # 净值曲线
    ├── 6_drawdown.png              # 回撤分析
    ├── 7_performance_metrics.png   # 性能指标
    └── 8_summary_table.png         # 汇总表格
```

---

## 🔧 修改配置

### 方法1：直接编辑脚本
打开对应的 `run_*.py` 文件，修改配置部分

### 方法2：命令行参数（未来支持）
```bash
# 计划中...
python run_dcc_garch.py --data data/your_data.xlsx --output outputs/your_output
```

---

## 📈 模型选择建议

| 场景 | 推荐模型 | 理由 |
|------|----------|------|
| **快速验证** | DCC-GARCH | 简单高效，计算快速 |
| **考虑长期均衡** | ECM-GARCH | 捕捉协整关系 |
| **追求最佳性能** | ECM-DCC-GARCH | 综合考虑所有因素 |
| **学术研究** | ECM-DCC-GARCH | 理论最完善 |

---

## 🚀 运行流程

每个脚本执行以下步骤：

1. **数据读取** - 加载并检查数据
2. **模型拟合** - 估计模型参数和套保比例
3. **滚动回测** - 6周期 × 90天滚动回测
4. **图表生成** - 生成7张可视化图表
5. **报告生成** - HTML/Excel/CSV报告
6. **输出摘要** - 核心指标汇总

---

## ❓ 常见问题

### Q1: 数据文件格式要求？
**A:** 需要包含以下列：
- `date`: 日期（可选）
- `spot`: 现货价格
- `futures`: 期货价格

### Q2: 样本量要求？
**A:**
- DCC-GARCH: 至少60个观测值（建议120+）
- ECM-DCC-GARCH: 至少 coint_window + 2 个观测值（默认122+）

### Q3: 如何调整协整窗口？
**A:** 修改 `ECM_DCC_CONFIG['coint_window']`：
- 小样本（<200天）：60-90天
- 中等样本（200-500天）：90-120天
- 大样本（>500天）：120-180天

### Q4: 运行时间？
**A:**
- verify_models.py: ~30秒
- 完整回测脚本: ~2-5分钟（取决于数据量）

### Q5: 内存要求？
**A:** 建议4GB+可用内存

---

## 📞 技术支持

### 查看测试结果
```bash
python verify_models.py
```

### 检查模型输出
查看 `outputs/<模型>/model_results/` 目录

### 验证报告
打开 `outputs/<模型>/report.html` 查看可视化报告

---

## 🎓 模型理论

### DCC-GARCH
- Engle (2002): "Dynamic Conditional Correlation"
- 捕捉时变相关性
- 动态最小方差套保

### ECM-GARCH
- Johansen (1991): 协整理论
- 误差修正模型
- 长期均衡关系

### ECM-DCC-GARCH
- 综合以上两种方法
- 考虑协整 + 时变相关性
- 理论最优

---

## ✅ 验证状态

| 模型 | 状态 | 脚本 | 测试日期 |
|------|------|------|----------|
| ECM-GARCH | ✅ 可用 | run_ecm_garch.py | - |
| DCC-GARCH | ✅ 可用 | run_dcc_garch.py | 2026-03-01 |
| ECM-DCC-GARCH | ✅ 可用 | run_ecm_dcc_garch.py | 2026-03-01 |

---

## 📝 更新日志

### 2026-03-01
- ✅ 创建 run_dcc_garch.py
- ✅ 创建 run_ecm_dcc_garch.py
- ✅ 创建 verify_models.py
- ✅ 所有模型测试通过
- ✅ 使用mgarch库（最佳实践）
- ✅ 修复所有已知bug
