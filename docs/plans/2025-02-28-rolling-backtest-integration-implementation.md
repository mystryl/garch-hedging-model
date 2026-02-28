# 滚动回测集成实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 将滚动回测功能集成到 basic_garch_analyzer 主代码中，完全替换原来的全样本回测评估

**架构：** 方案 A - 最小改动直接替换。在 ModelConfig 中添加滚动回测参数，修改 run_analysis() 默认使用滚动回测，删除 backtest_evaluator.py

**技术栈：** Python 3.7+, pandas, numpy, dataclasses

---

## Task 1: 扩展 ModelConfig 配置类

**Files:**
- Modify: `basic_garch_analyzer/config.py`

**Step 1: 添加滚动回测参数到 ModelConfig 类**

找到 `@dataclass class ModelConfig:` 定义，在现有参数后添加：

```python
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

    # ===== 新增：滚动回测参数 =====
    enable_rolling_backtest: bool = True  # 启用滚动回测（替代全样本回测）
    n_periods: int = 5                    # 回测周期数
    window_days: int = 60                 # 每个周期天数
    backtest_seed: int = 42               # 随机种子
    # =================================

    # 输出配置
    output_dir: str = 'outputs'
    save_intermediate: bool = True
```

**Step 2: 更新 to_dict() 方法**

找到 `def to_dict(self) -> dict:` 方法，替换返回值：

```python
def to_dict(self) -> dict:
    """转换为字典格式"""
    return {
        'GARCH(p,q)': f'({self.p}, {self.q})',
        '相关系数窗口': f'{self.corr_window}天',
        '税点调整': f'{self.tax_rate:.1%}',
        '回测模式': '滚动回测' if self.enable_rolling_backtest else '全样本',
        '回测周期数': f'{self.n_periods}个' if self.enable_rolling_backtest else '-',
        '每周期': f'{self.window_days}天' if self.enable_rolling_backtest else '-',
    }
```

**Step 3: 验证语法**

```bash
cd "/Users/mystryl/Documents/GARCH 模型套保方案"
python -c "from basic_garch_analyzer.config import ModelConfig; c = ModelConfig(); print('✓ Config OK'); print(c.to_dict())"
```

Expected: 输出包含新参数的字典

**Step 4: 提交**

```bash
git add basic_garch_analyzer/config.py
git commit -m "feat(config): 添加滚动回测参数到 ModelConfig

- 添加 enable_rolling_backtest, n_periods, window_days, backtest_seed
- 默认启用滚动回测模式
- 更新 to_dict() 方法显示新参数"
```

---

## Task 2: 修改 run_analysis() 函数 - 导入部分

**Files:**
- Modify: `basic_garch_analyzer/__init__.py`

**Step 1: 添加滚动回测导入**

在文件顶部的导入区域添加：

```python
from basic_garch_analyzer.rolling_backtest import (
    run_rolling_backtest as _run_rolling_backtest,
    generate_rolling_backtest_report
)
```

确保在现有的 `from basic_garch_analyzer.analyzer import evaluate_and_report` 之后。

**Step 2: 更新版本号**

找到 `__version__ = '1.0.0'`，修改为：

```python
__version__ = '1.1.0'
```

**Step 3: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "feat(__init__): 添加滚动回试导入并升级版本到1.1.0"
```

---

## Task 3: 修改 run_analysis() 函数 - 标题和配置显示

**Files:**
- Modify: `basic_garch_analyzer/__init__.py`

**Step 1: 更新函数标题**

找到 `def run_analysis(...)` 函数内的标题打印：

```python
print("\n" + "=" * 70)
print(" " * 15 + "Basic GARCH Analyzer")
print(" " * 10 + "套保策略分析系统（滚动回测模式）")  # 添加括号内的说明
print("=" * 70)
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "docs(__init__): 更新 run_analysis 标题说明"
```

---

## Task 4: 修改 run_analysis() 函数 - 替换回测逻辑

**Files:**
- Modify: `basic_garch_analyzer/__init__.py`

**Step 1: 找到回测评估部分**

在 `run_analysis()` 函数中，找到这一段：

```python
# 4. 评估和生成报告
print("\n" + "=" * 70)
report_info = evaluate_and_report(
    data=data,
    results=model_results,
    selected=selected,
    config=config,
    output_dir=config.output_dir
)
```

**Step 2: 替换为条件分支**

将上述代码替换为：

```python
# ===== 4. 回测评估（滚动回测或全样本）=====
print("\n" + "=" * 70)

if config.enable_rolling_backtest:
    # 使用滚动回测
    print("运行滚动回测...")
    rolling_results = _run_rolling_backtest(
        data,
        model_results['h_final'],
        n_periods=config.n_periods,
        window_days=config.window_days,
        seed=config.backtest_seed,
        tax_rate=config.tax_rate
    )

    # 生成报告
    report_info = generate_rolling_backtest_report(
        data,
        rolling_results,
        config.output_dir
    )
else:
    # 使用全样本回测（备选方案）
    print("运行全样本回测...")
    report_info = evaluate_and_report(
        data=data,
        results=model_results,
        selected=selected,
        config=config,
        output_dir=config.output_dir
    )
# ==================================================
```

**Step 3: 验证语法**

```bash
python -c "from basic_garch_analyzer import run_analysis; print('✓ Import OK')"
```

Expected: `Import OK`

**Step 4: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "feat(__init__): 修改 run_analysis 使用滚动回测作为默认

- 添加 enable_rolling_backtest 条件分支
- 默认使用滚动回测模式
- 保留全样本回测作为备选（enable_rolling_backtest=False）"
```

---

## Task 5: 修改 run_analysis() 函数 - 结果摘要输出

**Files:**
- Modify: `basic_garch_analyzer/__init__.py`

**Step 1: 找到结果摘要部分**

在 `run_analysis()` 函数的结尾，找到输出摘要的代码：

```python
# 5. 输出摘要
print("\n" + "=" * 70)
print(" " * 20 + "分析完成")
print("=" * 70)

metrics = report_info['metrics']
print(f"\n核心结果:")
print(f"  方差降低比例: {metrics['variance_reduction']:.2%}")
print(f"  夏普比率 (套保后): {metrics['sharpe_hedged']:.4f}")
print(f"  最大回撤 (套保后): {metrics['max_dd_hedged']:.2%}")
print(f"  套保效果评级: {metrics['rating']}")
```

**Step 2: 替换为条件分支**

替换为：

```python
# 5. 输出摘要
print("\n" + "=" * 70)
print(" " * 20 + "分析完成")
print("=" * 70)

if config.enable_rolling_backtest:
    print(f"\n核心结果（滚动回测）:")
    print(f"  回测周期数: {rolling_results['n_periods']}")
    print(f"  平均收益率（套保后）: {rolling_results['avg_return_hedged']:.2%}")
    print(f"  平均方差降低: {rolling_results['avg_variance_reduction']:.2%}")
    print(f"  平均最大回撤: {rolling_results['avg_max_dd_hedged']:.2%}")
else:
    metrics = report_info['metrics']
    print(f"\n核心结果（全样本回测）:")
    print(f"  方差降低比例: {metrics['variance_reduction']:.2%}")
    print(f"  夏普比率 (套保后）: {metrics['sharpe_hedged']:.4f}")
    print(f"  最大回撤（套保后）: {metrics['max_dd_hedged']:.2%}")
    print(f"  套保效果评级: {metrics['rating']}")
```

**Step 3: 修改返回值**

找到 `return` 语句，修改为：

```python
return {
    'data': data,
    'selected': selected,
    'model_results': model_results,
    'rolling_results' if config.enable_rolling_backtest else 'metrics':
        rolling_results if config.enable_rolling_backtest else report_info.get('metrics'),
    'report_info': report_info,
    'config': config
}
```

**Step 4: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "feat(__init__): 根据回测模式输出不同的结果摘要"
```

---

## Task 6: 更新 __init__.py 导出列表

**Files:**
- Modify: `basic_garch_analyzer/__init__.py`

**Step 1: 修改 __all__ 列表**

找到 `__all__ = [...]` 定义，注释掉不再导出的函数：

```python
__all__ = [
    'ModelConfig',
    'create_config',
    'load_and_preprocess',
    'fit_basic_garch',
    'save_model_results',
    # 'evaluate_and_report',  # 不再导出（保留作为备份）
    'run_analysis',
    # 'run_rolling_backtest'  # 已整合到 run_analysis 中
]
```

**Step 2: 更新模块文档字符串**

找到文件顶部的文档字符串，更新为：

```python
"""
Basic GARCH Analyzer - GARCH套保模型分析工具

支持：
- 作为Python库导入使用
- 作为命令行工具运行
- 自动生成完整的滚动回测分析报告（默认）

Example:
--------
作为库使用:
    >>> from basic_garch_analyzer import run_analysis
    >>> result = run_analysis('data.xlsx', '现货价格', '期货价格')

命令行使用:
    $ python -m basic_garch_analyzer --data data.xlsx --spot 现货价格 --futures 期货价格

使用全样本回测（备选）:
    >>> from basic_garch_analyzer import run_analysis, ModelConfig
    >>> config = ModelConfig(enable_rolling_backtest=False)
    >>> result = run_analysis('data.xlsx', '现货', '期货', config=config)
"""
```

**Step 3: 提交**

```bash
git add basic_garch_analyzer/__init__.py
git commit -m "refactor(__init__): 更新导出列表和文档字符串

- 移除 evaluate_and_report 和 run_rolling_backtest 的导出
- 更新文档说明默认使用滚动回测
- 添加全样本回测的使用示例"
```

---

## Task 7: 删除 backtest_evaluator.py

**Files:**
- Delete: `basic_garch_analyzer/backtest_evaluator.py`

**Step 1: 确认文件不再被引用**

```bash
cd "/Users/mystryl/Documents/GARCH 模型套保方案"
grep -r "backtest_evaluator" basic_garch_analyzer/ --include="*.py" | grep -v "\.pyc"
```

Expected: 只有 `analyzer.py` 中的 `evaluate_and_report` 仍然使用它（作为备份）

**Step 2: 删除文件**

```bash
rm basic_garch_analyzer/backtest_evaluator.py
```

**Step 3: 验证导入仍然工作**

```bash
python -c "from basic_garch_analyzer import run_analysis; print('✓ Import OK')"
```

Expected: `Import OK`

**Step 4: 提交**

```bash
git add basic_garch_analyzer/backtest_evaluator.py
git commit -m "refactor: 删除 backtest_evaluator.py

- 全样本回测功能已被滚动回测替代
- analyzer.py 中的 evaluate_and_report 保留作为备份"
```

---

## Task 8: 为 analyzer.py 添加注释标记

**Files:**
- Modify: `basic_garch_analyzer/analyzer.py`

**Step 1: 更新模块文档字符串**

找到文件顶部的文档字符串，添加说明：

```python
"""
核心分析器模块
合并回测评估和报告生成

注意：此模块保留用于全样本回测（备选方案）
默认使用滚动回测模式（rolling_backtest.py）

要使用全样本回测:
    >>> config = ModelConfig(enable_rolling_backtest=False)
    >>> run_analysis(..., config=config)
"""
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/analyzer.py
git commit -m "docs(analyzer): 添加文档说明此模块为备选方案"
```

---

## Task 9: 更新 README.md 文档

**Files:**
- Modify: `basic_garch_analyzer/README.md`

**Step 1: 更新功能说明**

在功能特点部分，修改回测相关说明：

```markdown
## 功能特点

- ✅ 自动数据加载和预处理
- ✅ GARCH(1,1) 模型拟合
- ✅ 动态套保比例计算
- ✅ **滚动回测分析**（随机抽取多个周期，更稳健）
- ✅ 完整的回测评估指标
- ✅ 自动生成图表和报告
- ✅ 支持交互式列名选择
- ✅ 灵活的参数配置
```

**Step 2: 更新使用示例**

修改"方式1: Python 库"部分：

```markdown
### 方式1: Python 库

\`\`\`python
from basic_garch_analyzer import run_analysis, ModelConfig

# 默认使用滚动回测（5个周期，每个60天）
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格'
)

# 自定义滚动回测参数
config = ModelConfig(
    n_periods=10,           # 10个周期
    window_days=90,         # 每周期90天
    backtest_seed=123       # 自定义随机种子
)
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格',
    config=config
)

# 使用全样本回测（备选方案）
config = ModelConfig(enable_rolling_backtest=False)
result = run_analysis(
    excel_path='data.xlsx',
    spot_col='现货价格',
    futures_col='期货价格',
    config=config
)
\`\`\`
```

**Step 3: 添加输出文件说明**

添加或更新输出文件部分：

```markdown
## 输出文件

运行后会在输出目录（默认 `outputs/`）生成：

**滚动回测模式（默认）：**
- `figures/1_periods_nav.png` - 各周期净值曲线
- `figures/2_periods_comparison.png` - 周期对比图
- `rolling_backtest_report.xlsx` - Excel 格式报告
- `rolling_backtest_report.csv` - CSV 格式报告

**全样本回测模式：**
- `report.html` - HTML 格式的完整报告
- `backtest_report.csv` - CSV 格式的指标表格
- `backtest_report.xlsx` - Excel 格式的多工作表报告
- `figures/` - 8 张可视化图表
```

**Step 4: 提交**

```bash
git add basic_garch_analyzer/README.md
git commit -m "docs(readme): 更新文档说明默认使用滚动回测

- 更新功能特点说明
- 添加滚动回测参数配置示例
- 添加全样本回测使用说明
- 更新输出文件说明"
```

---

## Task 10: 更新 CHANGELOG.md

**Files:**
- Modify: `basic_garch_analyzer/CHANGELOG.md`

**Step 1: 添加新版本条目**

在文件顶部添加：

```markdown
# 变更日志

## [1.1.0] - 2025-02-28

### 重大变更
- **[BREAKING]** 默认回测模式从全样本改为滚动回测
  - `run_analysis()` 现在默认使用滚动回测（5周期×60天）
  - 输出格式和指标发生变化
  - 添加 `enable_rolling_backtest=False` 可使用全样本回测

### 新增
- 添加滚动回测参数到 ModelConfig
  - `enable_rolling_backtest`: 是否启用滚动回测（默认True）
  - `n_periods`: 回测周期数（默认5）
  - `window_days`: 每周期天数（默认60）
  - `backtest_seed`: 随机种子（默认42）

### 移除
- `backtest_evaluator.py` 已删除（功能整合到滚动回测）
- `evaluate_and_report` 不再导出（但保留作为备份）
- `run_rolling_backtest` 不再导出（已整合到 `run_analysis`）

### 文档
- 更新 README.md 说明新的默认回测模式
- 添加全样本回测使用示例

## [1.0.0] - 2025-02-28
```

**Step 2: 提交**

```bash
git add basic_garch_analyzer/CHANGELOG.md
git commit -m "docs(changelog): 添加 v1.1.0 变更日志

- 标记默认回测模式变更为 BREAKING CHANGE
- 记录新增参数和移除的功能"
```

---

## Task 11: 集成测试

**Files:**
- Create: `test_rolling_backtest_integration.py`

**Step 1: 创建集成测试脚本**

```python
"""
滚动回测集成测试
验证 run_analysis() 默认使用滚动回测
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from basic_garch_analyzer import run_analysis, ModelConfig


def test_default_rolling_backtest():
    """测试默认使用滚动回测"""
    print("\n" + "=" * 60)
    print("测试1: 默认滚动回测模式")
    print("=" * 60)

    data_file = "outputs/preprocessed_data.xlsx"

    if not os.path.exists(data_file):
        print(f"⚠️  测试数据不存在: {data_file}")
        return False

    try:
        # 使用默认配置
        result = run_analysis(
            excel_path=data_file,
            spot_col='spot',
            futures_col='futures',
            config=ModelConfig(output_dir='outputs/test_rolling')
        )

        # 验证返回值包含滚动回测结果
        assert 'rolling_results' in result
        assert 'n_periods' in result['rolling_results']
        assert result['config'].enable_rolling_backtest == True

        print("\n✅ 测试通过: 默认使用滚动回测")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_sample_backtest():
    """测试全样本回测备选方案"""
    print("\n" + "=" * 60)
    print("测试2: 全样本回测模式")
    print("=" * 60)

    data_file = "outputs/preprocessed_data.xlsx"

    if not os.path.exists(data_file):
        print(f"⚠️  测试数据不存在: {data_file}")
        return False

    try:
        # 禁用滚动回测
        result = run_analysis(
            excel_path=data_file,
            spot_col='spot',
            futures_col='futures',
            config=ModelConfig(
                enable_rolling_backtest=False,
                output_dir='outputs/test_full_sample'
            )
        )

        # 验证返回值包含全样本回测指标
        assert 'report_info' in result
        assert 'metrics' in result['report_info']
        assert result['config'].enable_rolling_backtest == False

        print("\n✅ 测试通过: 全样本回测作为备选方案")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_custom_rolling_params():
    """测试自定义滚动回测参数"""
    print("\n" + "=" * 60)
    print("测试3: 自定义滚动回测参数")
    print("=" * 60)

    data_file = "outputs/preprocessed_data.xlsx"

    if not os.path.exists(data_file):
        print(f"⚠️  测试数据不存在: {data_file}")
        return False

    try:
        # 自定义参数
        config = ModelConfig(
            n_periods=3,
            window_days=30,
            backtest_seed=999,
            output_dir='outputs/test_custom'
        )

        result = run_analysis(
            excel_path=data_file,
            spot_col='spot',
            futures_col='futures',
            config=config
        )

        # 验证参数生效
        assert result['rolling_results']['n_periods'] == 3
        assert result['config'].n_periods == 3
        assert result['config'].window_days == 30

        print("\n✅ 测试通过: 自定义参数生效")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" " * 20 + "滚动回测集成测试")
    print("=" * 70)

    results = []
    results.append(test_default_rolling_backtest())
    results.append(test_full_sample_backtest())
    results.append(test_custom_rolling_params())

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)
    print(f"通过: {sum(results)}/{len(results)}")

    sys.exit(0 if all(results) else 1)
```

**Step 2: 运行测试（如果数据存在）**

```bash
cd "/Users/mystryl/Documents/GARCH 模型套保方案"
python test_rolling_backtest_integration.py
```

**Step 3: 提交测试脚本**

```bash
git add test_rolling_backtest_integration.py
git commit -m "test: 添加滚动回测集成测试脚本

- 测试默认滚动回测模式
- 测试全样本回测备选方案
- 测试自定义参数配置"
```

---

## Task 12: 验证和文档检查

**Step 1: 最终验证清单**

```bash
cd "/Users/mystryl/Documents/GARCH 模型套保方案"

# 1. 验证所有导入正常
python -c "from basic_garch_analyzer import run_analysis, ModelConfig; print('✓ 导入成功')"

# 2. 验证配置参数
python -c "from basic_garch_analyzer import ModelConfig; c = ModelConfig(); print(c.to_dict())"

# 3. 检查文件是否存在
ls -la basic_garch_analyzer/backtest_evaluator.py 2>&1 | grep "No such file"
# Expected: "No such file or directory"

# 4. 检查 git 状态
git status
```

**Step 2: 创建迁移指南**

创建 `basic_garch_analyzer/MIGRATION.md`:

```markdown
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

### 2. 输出差异

| 项目 | 全样本回测 | 滚动回测 |
|------|-----------|---------|
| 回测周期 | 1个（全样本） | 5个（可配置） |
| 主要指标 | 方差降低、夏普比率 | 平均收益率、平均方差降低 |
| 图表数量 | 8张 | 2张 |
| 报告格式 | HTML + Excel/CSV | Excel/CSV |

### 3. 返回值差异

**v1.0.0：**
```python
result = {
    'data': DataFrame,
    'model_results': dict,
    'report_info': {
        'metrics': {...},  # 全样本指标
        ...
    }
}
```

**v1.1.0：**
```python
result = {
    'data': DataFrame,
    'model_results': dict,
    'rolling_results': {...},  # 滚动回测结果
    'report_info': {...}
}
```

## 如何保持旧行为

如果你想继续使用全样本回测：

```python
from basic_garch_analyzer import run_analysis, ModelConfig

config = ModelConfig(enable_rolling_backtest=False)
result = run_analysis('data.xlsx', 'spot', 'futures', config=config)
```

## 配置滚动回测参数

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

## 问题反馈

如有问题，请查看：
- README.md - 完整使用文档
- CHANGELOG.md - 详细变更记录
```

**Step 3: 提交迁移指南**

```bash
git add basic_garch_analyzer/MIGRATION.md
git commit -m "docs: 添加 v1.0.0 到 v1.1.0 迁移指南

- 说明默认回测模式变更
- 对比新旧版本差异
- 提供保持旧行为的方法"
```

**Step 4: 最终提交**

```bash
git log --oneline -10  # 查看最近的提交
```

---

## 验收标准

完成所有任务后，应该能够：

1. ✅ `run_analysis()` 默认使用滚动回测（5周期×60天）
2. ✅ 通过 `enable_rolling_backtest=False` 使用全样本回测
3. ✅ `ModelConfig` 包含新的滚动回测参数
4. ✅ `backtest_evaluator.py` 被删除
5. ✅ 文档完整更新（README.md, CHANGELOG.md, MIGRATION.md）
6. ✅ 集成测试通过
7. ✅ 版本号升级到 1.1.0

---

## 快速验证命令

```bash
# 完整验证流程
cd "/Users/mystryl/Documents/GARCH 模型套保方案"

# 1. 导入测试
python -c "from basic_garch_analyzer import run_analysis, ModelConfig; print('✓ 导入成功')"

# 2. 配置测试
python -c "from basic_garch_analyzer import ModelConfig; c = ModelConfig(); assert c.enable_rolling_backtest == True; assert c.n_periods == 5; print('✓ 配置正确')"

# 3. 文件检查
! ls basic_garch_analyzer/backtest_evaluator.py 2>&1 | grep "No such file" && echo "✓ 旧文件已删除" || echo "✗ 旧文件仍存在"

# 4. 版本检查
python -c "from basic_garch_analyzer import __version__; print(f'✓ 版本: {__version__}')"
```

Expected output:
```
✓ 导入成功
✓ 配置正确
✓ 旧文件已删除
✓ 版本: 1.1.0
```
