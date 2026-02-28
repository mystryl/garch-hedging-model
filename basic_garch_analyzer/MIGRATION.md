# 迁移指南：从 v1.0.0 到 v1.1.0

## 重大变更

v1.1.0 版本中，`run_analysis()` 的默认回测模式从**全样本回测**改为**滚动回测**。

## 主要变化

### 1. 默认回测模式

**v1.0.0（旧版本）：**
```python
result = run_analysis('data.xlsx', 'spot', 'futures')
# 使用全样本回测，评估整个数据集
```

**v1.1.0（新版本）：**
```python
result = run_analysis('data.xlsx', 'spot', 'futures')
# 使用滚动回测，随机抽取5个周期，每周期60天
```

### 2. 如何保持旧行为

如果你想继续使用全样本回测：

```python
from basic_garch_analyzer import run_analysis, ModelConfig

config = ModelConfig(enable_rolling_backtest=False)
result = run_analysis('data.xlsx', 'spot', 'futures', config=config)
```

### 3. 配置滚动回测参数

```python
from basic_garch_analyzer import run_analysis, ModelConfig

config = ModelConfig(
    n_periods=10,        # 10个周期
    window_days=90,      # 每周期90天
    backtest_seed=123    # 自定义随机种子
)
result = run_analysis('data.xlsx', 'spot', 'futures', config=config)
```

## 优势

滚动回测相比全样本回测：
- ✅ 模拟实际套保周期（固定期限）
- ✅ 多周期平均，结果更稳健
- ✅ 避开交割月份，更贴近实际
- ✅ 计算更快（只使用部分数据）
