# GARCH模型套保分析Web平台使用指南

## 简介

本平台基于Flask构建，提供三种GARCH套保模型的在线分析服务：
- **Basic GARCH**: 基础GARCH(1,1)模型，使用滚动窗口估计动态相关系数
- **DCC-GARCH**: 动态条件相关GARCH模型，捕捉时变相关性
- **ECM-GARCH**: 误差修正GARCH模型，考虑现货与期货的长期协整关系

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements_web.txt
```

**requirements_web.txt 内容：**
```
Flask==3.0.0
pandas==2.1.4
numpy==1.26.3
openpyxl==3.1.2
xlrd==2.0.1
arch==7.0.0
mgarch==1.1.0
statsmodels==0.14.1
scipy==1.11.4
matplotlib==3.8.2
seaborn==0.13.1
```

### 2. 启动服务

```bash
python app.py
```

服务启动后，终端会显示：
```
============================================================
GARCH模型套保分析Web平台
============================================================
请在浏览器中访问: http://localhost:5001
按 Ctrl+C 停止服务
============================================================
```

### 3. 访问平台

在浏览器中打开：http://localhost:5001

## 使用流程

### 步骤1: 上传数据文件

1. 拖拽Excel文件到上传区域，或点击"选择文件"按钮
2. 支持的文件格式：`.xlsx`, `.xls`
3. 文件大小限制：50MB

**数据要求：**
- 必须包含现货价格列和期货价格列
- 可选日期列
- 数据量建议：至少120个交易日（用于协整检验和参数估计）

### 步骤2: 选择工作表

1. 系统会自动分析所有工作表并推荐最佳选择（标记为⭐）
2. 从下拉菜单中选择包含数据的工作表
3. 预览区域会显示前10行数据

### 步骤3: 配置数据列

1. **现货价格列**：选择包含现货价格的列
2. **期货价格列**：选择包含期货价格的列
3. **日期列**（可选）：选择日期列，用于时间序列分析
4. **训练集比例**：滑动调整训练集比例（50%-90%）

系统会智能推荐列映射：
- 搜索关键词："现货"、"spot"、"期货"、"future"等
- 根据数据内容推断（期货价格通常高于现货）

### 步骤4: 选择模型并运行

**三种模型可选：**

#### 1. Basic GARCH
- **特点**：计算速度快，实现简单
- **适用场景**：快速分析，相关性较稳定的品种
- **方法**：单变量GARCH(1,1) + 滚动窗口相关系数
- **参数**：
  - `p=1, q=1`：GARCH阶数
  - `corr_window=120`：相关系数窗口（天）

#### 2. DCC-GARCH
- **特点**：捕捉时变相关性，更灵活
- **适用场景**：相关性波动较大的品种
- **方法**：DCC（动态条件相关）结构
- **参数**：
  - `p=1, q=1`：GARCH阶数
  - `dist='norm'`：分布假设（正态分布）

#### 3. ECM-GARCH
- **特点**：考虑长期均衡关系，理论最完善
- **适用场景**：存在协整关系的品种（如现货-期货）
- **方法**：误差修正模型 + GARCH
- **参数**：
  - `p=1, q=1`：GARCH阶数
  - `coint_window=120`：协整估计窗口（天）
  - `coupling_method='ect-garch'`：ECM-GARCH耦合方式

点击"运行模型分析"按钮，系统会：
1. 显示进度条
2. 运行选定的模型
3. 生成HTML报告和ZIP包
4. 计算套保效果指标

### 步骤5: 查看和下载结果

**结果摘要包含：**
- 套保比例均值
- 方差降低比例
- Ederington套保有效性指标
- 模型特定参数（如误差修正系数、协整系数等）

**可执行操作：**
1. **📊 查看HTML报告**：在新标签页打开完整的分析报告
2. **📥 下载ZIP包**：下载包含HTML报告、CSV数据、图表的压缩包
3. **🔄 重新分析**：返回模型选择，重新运行

## 输出文件说明

### HTML报告
包含以下内容：
- 模型配置参数
- 套保比例统计（均值、标准差、最小值、最大值）
- 套保效果评估（方差降低、夏普比率、最大回撤）
- 图表可视化（价格序列、收益率、套保比例、波动率）
- 模型特定图表（如ECM的误差修正项、DCC的动态相关系数）

### ZIP包内容
```
[model_type]_report_[timestamp].zip
├── report.html              # HTML分析报告
├── model_results/
│   └── h_[model_type].csv   # 套保比例时间序列
└── figures/                 # 图表文件
    ├── 1_price_series.png
    ├── 2_returns.png
    ├── 3_hedge_ratio.png
    └── ...
```

## 模型对比

| 模型 | 速度 | 准确性 | 理论基础 | 适用场景 |
|------|------|--------|----------|----------|
| Basic GARCH | ⭐⭐⭐ | ⭐⭐ | 简单 | 快速分析 |
| DCC-GARCH | ⭐⭐ | ⭐⭐⭐ | 较完善 | 时变相关性 |
| ECM-GARCH | ⭐ | ⭐⭐⭐⭐ | 最完善 | 协整关系 |

## 常见问题

### Q1: 文件上传失败？
**A:** 检查以下几点：
- 文件格式是否为 `.xlsx` 或 `.xls`
- 文件大小是否超过50MB
- 文件是否损坏（尝试在Excel中打开）

### Q2: 列映射推荐不准确？
**A:** 可以手动选择：
- 现货价格列：通常包含"现货"、"spot"、"华东"、"市场价"等关键词
- 期货价格列：通常包含"期货"、"future"、"主力合约"、"收盘"等关键词
- 日期列：通常包含"日期"、"date"、"时间"等关键词

### Q3: 模型运行失败？
**A:** 常见原因：
- **样本量不足**：至少需要120个交易日的数据
- **数据质量问题**：检查是否有缺失值、异常值
- **协整检验失败**（ECM-GARCH）：尝试减小协整窗口
- **收敛问题**：尝试不同的模型或参数

### Q4: 套保比例异常？
**A:** 可能的原因：
- 数据期间跨越交割月（期货价格异常）
- 现货与期货价格倒挂
- 税点调整未正确应用

### Q5: 如何选择模型？
**A:** 推荐策略：
1. **初次分析**：使用Basic GARCH快速了解数据
2. **相关性波动大**：使用DCC-GARCH捕捉时变特征
3. **理论严谨性要求高**：使用ECM-GARCH（推荐用于实际套保）

## 技术架构

```
GARCH Web Platform
├── app.py                 # Flask应用主入口
├── config.py              # 配置文件
├── models/                # 模型包装器
│   ├── __init__.py
│   ├── basic_garch_wrapper.py
│   ├── dcc_garch_wrapper.py
│   └── ecm_garch_wrapper.py
├── utils/                 # 工具函数
│   └── data_processor.py
├── templates/             # HTML模板
│   ├── base.html
│   └── index.html
├── static/                # 静态资源
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── outputs/               # 输出目录
    └── web_reports/       # Web平台生成的报告
```

## API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 主页面 |
| `/health` | GET | 健康检查 |
| `/api/upload` | POST | 上传Excel文件 |
| `/api/preview-sheet` | POST | 预览工作表数据 |
| `/api/generate` | POST | 生成分析报告 |
| `/download/<filename>` | GET | 下载ZIP包 |
| `/report?path=...` | GET | 查看HTML报告 |

## 配置说明

### config.py 配置项

```python
# Flask配置
SECRET_KEY = 'garch-platform-dev-key'  # 密钥
DEBUG = True                           # 调试模式
HOST = '0.0.0.0'                       # 监听地址
PORT = 5001                            # 监听端口

# 文件上传配置
UPLOAD_FOLDER = 'outputs/uploaded'     # 上传目录
MAX_CONTENT_LENGTH = 50MB              # 最大文件大小
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}   # 允许的扩展名

# 输出配置
OUTPUT_DIR = 'outputs'                 # 输出根目录

# 模型配置
MODEL_CONFIG = {
    'basic_garch': {
        'p': 1, 'q': 1,
        'corr_window': 120,
        'tax_rate': 0.13
    },
    'dcc_garch': {
        'p': 1, 'q': 1,
        'dist': 'norm',
        'tax_rate': 0.13
    },
    'ecm_garch': {
        'p': 1, 'q': 1,
        'coint_window': 120,
        'tax_adjust': True,
        'coupling_method': 'ect-garch',
        'tax_rate': 0.13
    }
}
```

## 性能优化建议

1. **数据预处理**：上传前清理数据，删除无关列
2. **模型选择**：初次分析使用Basic GARCH，验证后再使用复杂模型
3. **并发限制**：Web版单次运行一个任务，避免多用户同时提交
4. **缓存利用**：相同参数的重复分析会覆盖之前的输出

## 安全注意事项

⚠️ **本平台仅用于开发和测试环境**

生产环境部署需要：
1. 修改 `SECRET_KEY` 为随机密钥
2. 设置 `DEBUG = False`
3. 添加用户认证机制
4. 实施文件上传病毒扫描
5. 配置HTTPS
6. 添加请求频率限制

## 故障排查

### 端口占用
```bash
# macOS可能提示端口5001被占用
# 修改config.py中的PORT为其他值（如5002）
PORT = 5002
```

### 依赖安装失败
```bash
# 使用国内镜像加速
pip install -r requirements_web.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 中文显示问题
确保系统安装了中文字体：
- Windows: Microsoft YaHei
- macOS: PingFang SC
- Linux: WenQuanYi Micro Hei

## 更新日志

### v1.0.0 (2024-03)
- ✅ 完整的Web平台
- ✅ 三种GARCH模型支持
- ✅ 智能列映射推荐
- ✅ HTML报告生成
- ✅ ZIP包下载
- ✅ 响应式界面设计

## 反馈与支持

如有问题或建议，请通过以下方式联系：
- 项目Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 邮箱: your-email@example.com

---

**祝您使用愉快！** 🎉
