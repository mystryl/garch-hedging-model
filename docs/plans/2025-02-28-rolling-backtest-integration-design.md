# 滚动回测集成设计文档

**日期:** 2025-02-28
**状态:** 已批准
**方案:** 方案 A - 最小改动直接替换

---

## 1. 概述

将 `rolling_backtest.py` 的滚动回测功能集成到主代码中，完全替换原来的全样本回测评估。

**核心变更：**
- `run_analysis()` 默认使用滚动回测而非全样本回测
- 删除 `backtest_evaluator.py`
- 在 `ModelConfig` 中添加滚动回测参数

---

## 2. 架构变更

### 2.1 修改前架构

```
run_analysis()
  ├── fit_basic_garch()              # GARCH模型拟合
  └── evaluate_and_report()          # 全样本回测 ← 旧方式
       └── backtest_evaluator.py     # 评估模块（将被删除）
```

### 2.2 修改后架构

```
run_analysis()
  ├── fit_basic_garch()              # GARCH模型拟合
  └── [if enable_rolling_backtest]
       └── run_rolling_backtest()    # 滚动回测 ← 新默认方式
            └── rolling_backtest.py
  └── [else]
       └── evaluate_and_report()     # 全样本回测（备选）
```

---

## 3. 详细设计

### 3.1 ModelConfig 扩展

**文件：** `basic_garch_analyzer/config.py`

**新增参数：**

```python
@dataclass
class ModelConfig:
    # ... 现有参数 ...

    # 滚动回测参数
    enable_rolling_backtest: bool = True  # 启用滚动回测
    n_periods: int = 5                    # 回测周期数
    window_days: int = 60                 # 每个周期天数
    backtest_seed: int = 42               # 随机种子
```

**to_dict() 更新：**

```python
def to_dict(self) -> dict:
    return {
        'GARCH(p,q)': f'({self.p}, {self.q})',
        '相关系数窗口': f'{self.corr_window}天',
        '税点调整': f'{self.tax_rate:.1%}',
        '回测模式': '滚动回测' if self.enable_rolling_backtest else '全样本',
        '回测周期数': f'{self.n_periods}个' if self.enable_rolling_backtest else '-',
        '每周期': f'{self.window_days}天' if self.enable_rolling_backtest else '-',
    }
```

---

### 3.2 run_analysis() 函数修改

**文件：** `basic_garch_analyzer/__init__.py`

**关键修改点：**

```python
def run_analysis(...) -> dict:
    # 1-3. 数据加载、模型拟合（不变）
    data, selected = load_and_preprocess(...)
    model_results = fit_basic_garch(...)

    # 4. 回测评估（修改）
    if config.enable_rolling_backtest:
        # 使用滚动回测
        rolling_results = _run_rolling_backtest(
            data,
            model_results['h_final'],
            n_periods=config.n_periods,
            window_days=config.window_days,
            seed=config.backtest_seed,
            tax_rate=config.tax_rate
        )
        report_info = generate_rolling_backtest_report(
            data, rolling_results, config.output_dir
        )
    else:
        # 全样本回测（备选）
        report_info = evaluate_and_report(...)

    # 5. 返回结果
    return {
        'data': data,
        'model_results': model_results,
        'rolling_results' if config.enable_rolling_backtest else 'metrics': ...,
        'report_info': report_info,
    }
```

---

### 3.3 文件操作

#### 删除文件

```bash
rm basic_garch_analyzer/backtest_evaluator.py
```

#### 更新 `__init__.py` 导出

```python
__version__ = '1.1.0'  # 版本升级

__all__ = [
    'ModelConfig',
    'create_config',
    'load_and_preprocess',
    'fit_basic_garch',
    'save_model_results',
    # 'evaluate_and_report',  # 不再导出
    'run_analysis',
    # 'run_rolling_backtest'  # 不再需要独立函数
]
```

#### 保留文件

- `analyzer.py` - 保留但不导出（备份）
- `rolling_backtest.py` - 保持不变
- `config.py` - 修改
- `__init__.py` - 修改

---

## 4. 数据流变更

### 4.1 修改前

```
Excel 数据
  ↓
load_and_preprocess()
  ↓
fit_basic_garch() → h_final
  ↓
evaluate_and_report() ← 全样本回测
  ↓
报告（8张图表 + HTML）
```

### 4.2 修改后

```
Excel 数据
  ↓
load_and_preprocess()
  ↓
fit_basic_garch() → h_final
  ↓
[if enable_rolling_backtest=True]
  ↓
run_rolling_backtest() ← 滚动回测
  ↓
报告（2张图表 + Excel/CSV）
```

---

## 5. 兼容性处理

### 5.1 向后兼容

虽然默认使用滚动回测，但通过 `enable_rolling_backtest=False` 仍可使用全样本回测：

```python
# 使用全样本回测
result = run_analysis(
    'data.xlsx', '现货', '期货',
    config=ModelConfig(enable_rolling_backtest=False)
)
```

### 5.2 API 兼容性

**签名不变：** `run_analysis()` 的参数签名保持不变

**返回值变化：**
- 新增 `'rolling_results'` 字段（当启用滚动回测时）
- `'report_info'` 内容结构变化

---

## 6. 输出差异

| 项目 | 全样本回测（旧） | 滚动回测（新） |
|------|-----------------|---------------|
| 回测周期数 | 1个（全样本） | 5个（可配置） |
| 图表数量 | 8张 | 2张 |
| 指标类型 | 单一时间点 | 多周期平均 |
| 报告格式 | HTML + CSV + Excel | Excel + CSV + 图表 |
| 主要指标 | 方差降低、夏普比率 | 平均收益率、方差降低 |

---

## 7. 迁移影响

### 7.1 用户影响

**对现有用户：**
- 默认行为改变（从全样本 → 滚动回测）
- 输出格式和内容变化
- 需要重新理解报告含义

**缓解措施：**
- 文档更新说明新默认行为
- 提供 `enable_rolling_backtest=False` 选项

### 7.2 性能影响

| 方面 | 全样本回测 | 滚动回测（5周期×60天） |
|------|-----------|---------------------|
| 计算时间 | 基准 | 更快（仅使用300天 vs 全样本） |
| 内存占用 | 全样本数据 | 固定窗口，更小 |
| 结果稳定性 | 单次结果 | 多周期平均，更稳健 |

---

## 8. 测试计划

### 8.1 单元测试

- [ ] ModelConfig 新参数验证
- [ ] run_analysis() with enable_rolling_backtest=True
- [ ] run_analysis() with enable_rolling_backtest=False

### 8.2 集成测试

- [ ] 完整流程测试（使用示例数据）
- [ ] 报告生成验证
- [ ] 参数覆盖测试

### 8.3 回归测试

- [ ] 确保现有功能未破坏
- [ ] 对比全样本回测结果（备选模式）

---

## 9. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 用户不适应新报告 | 高 | 文档说明，保留备选模式 |
| 输出格式变化导致脚本失败 | 中 | 保持返回值结构一致性 |
| 删除 backtest_evaluator.py 导致依赖问题 | 低 | 该文件未被外部直接依赖 |

---

## 10. 实施优先级

1. **高优先级**（必须）
   - 修改 ModelConfig
   - 修改 run_analysis()
   - 删除 backtest_evaluator.py
   - 更新 __init__.py

2. **中优先级**（建议）
   - 更新文档（README.md）
   - 添加迁移指南
   - 更新 CHANGELOG.md

3. **低优先级**（可选）
   - 添加单元测试
   - 性能基准测试

---

## 11. 后续优化建议

1. **统一报告格式**：考虑让滚动回测也生成 HTML 报告
2. **参数调优**：研究最佳的 n_periods 和 window_days 设置
3. **结果对比**：提供全样本 vs 滚动回测的对比功能
4. **可视化增强**：添加更多滚动回测专属图表

---

## 12. 验收标准

完成迁移后，应该能够：

1. ✅ `run_analysis()` 默认使用滚动回测
2. ✅ 通过 `enable_rolling_backtest=False` 使用全样本回测
3. ✅ 生成正确的滚动回测报告
4. ✅ `backtest_evaluator.py` 被删除
5. ✅ 所有测试通过
6. ✅ 文档更新完整
