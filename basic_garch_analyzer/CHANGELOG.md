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

### 文档
- 更新 README.md 说明新的默认回测模式
- 添加全样本回测使用示例
- 添加 MIGRATION.md 迁移指南

## [1.0.0] - 2025-02-28

### 初始版本
- Basic GARCH 套保模型分析工具
- 全样本回测评估
- 完整的可视化和报告生成
