# GARCH模型套保分析Web平台设计文档

**日期**: 2025-03-02
**作者**: Claude & User
**状态**: 设计阶段

## 1. 项目概述

### 1.1 目标
构建一个通用的GARCH模型套保分析Web平台，支持拖拽上传Excel数据、可视化配置、自动生成完整报告。

### 1.2 使用场景
- **用户**: 个人本地工具，单用户使用
- **部署**: 本地运行 (localhost:5000)
- **数据源**: Excel文件（支持多工作表）
- **模型**: Basic GARCH、DCC-GARCH、ECM-GARCH

### 1.3 核心价值
- ✅ 避免每次编写Python脚本
- ✅ 可视化配置，降低使用门槛
- ✅ 支持不同品种数据快速分析
- ✅ 自动生成HTML/Excel报告

## 2. 系统架构

### 2.1 技术栈
- **后端**: Flask + Python 3.11
- **前端**: Jinja2模板 + 原生JavaScript + CSS
- **数据处理**: pandas, openpyxl
- **模型**: 复用现有 `basic_garch_analyzer` 模块

### 2.2 目录结构
```
garch-web-platform/
├── app.py                    # Flask主应用
├── config.py                 # 配置文件
├── requirements_web.txt      # Web相关依赖
├── static/                   # 静态资源
│   ├── css/
│   │   └── style.css        # 样式文件
│   └── js/
│       └── app.js           # 前端交互逻辑
├── templates/
│   └── index.html           # 主页面（Jinja2模板）
├── models/                   # 模型调用模块
│   ├── __init__.py
│   ├── basic_garch_wrapper.py
│   ├── dcc_garch_wrapper.py
│   └── ecm_garch_wrapper.py
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── data_processor.py     # 数据处理
│   └── sheet_selector.py     # 工作表推荐
└── outputs/                  # 输出目录
    ├── uploaded/             # 临时上传文件
    ├── basic_garch/
    ├── dcc_garch/
    └── ecm_garch/
```

### 2.3 工作流程
```
用户上传Excel
    ↓
检测工作表 → 智能推荐
    ↓
用户选择工作表 → 预览数据
    ↓
智能推荐列映射 → 用户确认/修改
    ↓
选择日期范围（日历控件）
    ↓
选择模型类型
    ↓
生成报告（同步等待）
    ↓
显示HTML报告 + 提供下载
```

## 3. 后端设计

### 3.1 核心API

#### 3.1.1 文件上传
```
POST /api/upload
功能: 上传Excel文件并解析所有工作表
请求: multipart/form-data {file}
响应:
{
  "success": true,
  "filepath": "/path/to/file.xlsx",
  "sheets": [
    {
      "name": "Sheet1",
      "columns": ["date", "spot", "futures"],
      "ncols": 3
    }
  ],
  "recommended_sheet": "Sheet1"
}
```

#### 3.1.2 工作表预览
```
POST /api/preview-sheet
功能: 获取指定工作表的数据预览
请求: {filepath, sheet_name}
响应:
{
  "success": true,
  "columns": ["date", "spot", "futures"],
  "preview": [...],  // 前10行数据
  "total_rows": 1246,
  "date_range": {
    "min": "2021-01-05",
    "max": "2026-03-02"
  },
  "suggested_mapping": {
    "date": "date",
    "spot": "spot",
    "futures": "futures"
  }
}
```

#### 3.1.3 生成报告
```
POST /api/generate
功能: 运行模型并生成报告
请求: {
  filepath: "/path/to/file.xlsx",
  sheet_name: "Sheet1",
  model_type: "ecm_garch",
  column_mapping: {
    date: "date",
    spot: "spot",
    futures: "futures"
  },
  date_range: {
    start: "2021-01-05",
    end: "2026-03-02"
  }
}
响应:
{
  "success": true,
  "report_path": "outputs/ecm_garch/report.html",
  "summary": {
    "variance_reduction": 0.8424,
    "avg_return_hedged": 0.022,
    "model_params": {...}
  },
  "download_url": "/download/ecm_garch_report.zip"
}
```

#### 3.1.4 下载报告
```
GET /download/<filename>
功能: 下载生成的报告文件
```

### 3.2 模型Wrapper接口

所有模型wrapper实现统一接口：
```python
def run_model(data_path, sheet_name, column_mapping,
              date_range, output_dir, model_config):
    """
    统一的模型调用接口

    Args:
        data_path: Excel文件路径
        sheet_name: 工作表名称
        column_mapping: 列映射字典
        date_range: {start, end}
        output_dir: 输出目录
        model_config: 模型参数配置

    Returns:
        {
            'success': bool,
            'report_path': str,
            'summary': dict,
            'error': str (如果失败)
        }
    """
```

### 3.3 错误处理

统一错误响应格式：
```python
{
  'success': False,
  'error': '错误描述',
  'error_type': 'FILE_FORMAT' | 'DATA_INVALID' |
                'MODEL_ERROR' | 'DATE_RANGE_INVALID'
}
```

关键错误场景：
1. 文件格式错误 → "仅支持.xlsx/.xls格式"
2. 列名缺失 → "未找到期货价格列"
3. 日期范围无效 → "起始日期不能大于结束日期"
4. 数据不足 → "筛选后数据少于100行"
5. 模型失败 → "模型拟合失败，请尝试其他模型"

## 4. 前端设计

### 4.1 页面布局

#### 4.1.1 整体结构
```
┌─────────────────────────────────────────────┐
│         GARCH模型套保分析平台                │
├─────────────────────────────────────────────┤
│                                             │
│  步骤1: 上传数据                             │
│  [拖拽区域]                                  │
│                                             │
│  步骤1.5: 选择工作表                         │
│  [工作表列表 + 预览]                         │
│                                             │
│  步骤2: 确认数据映射                         │
│  [列选择器 + 日期范围 + 数据预览]           │
│                                             │
│  步骤3: 选择模型并生成                       │
│  [模型选择 + 生成按钮]                       │
│                                             │
│  结果区域                                    │
│  [报告摘要 + 查看报告 + 下载]                │
└─────────────────────────────────────────────┘
```

#### 4.1.2 交互流程
1. **拖拽上传**
   - 监听 `dragover`, `drop` 事件
   - FormData上传到 `/api/upload`
   - 显示上传进度

2. **工作表选择**
   - 单选按钮组
   - 高亮推荐工作表
   - 实时预览数据

3. **列映射**
   - `<select>` 下拉框
   - 智能推荐并标记
   - 手动调整

4. **日期范围**
   - `<input type="date">` 原生控件
   - 默认值：数据最小/最大日期
   - 实时显示筛选后数据量

5. **模型选择**
   - 单选按钮 + 模型描述
   - Basic GARCH（快速）
   - DCC-GARCH（动态相关）
   - ECM-GARCH（误差修正）

6. **生成报告**
   - 点击后显示loading动画
   - 同步等待（1-3分钟）
   - 完成后显示结果

### 4.2 关键JavaScript模块

#### 4.2.1 文件上传
```javascript
function handleFileDrop(file) {
  // 验证文件格式
  // FormData上传
  // 处理响应，显示工作表列表
}
```

#### 4.2.2 工作表选择
```javascript
function selectSheet(sheetName) {
  // 调用 /api/preview-sheet
  // 显示列名和数据预览
  // 智能推荐列映射
}
```

#### 4.2.3 列映射验证
```javascript
function validateMapping() {
  // 确保date、spot、futures都已选择
  // 检查是否有重复列
}
```

#### 4.2.4 生成报告
```javascript
async function generateReport() {
  // 收集所有参数
  // 显示loading
  // 调用 /api/generate
  // 处理结果
}
```

### 4.3 样式设计

- **配色**: 蓝色主题（#3498db）+ 白色背景
- **卡片**: 圆角、阴影、悬停效果
- **表格**: 斑马纹、固定表头
- **响应式**: 最大宽度1200px，居中显示
- **动画**: loading旋转、淡入淡出

## 5. 数据处理

### 5.1 智能列推荐算法

```python
def recommend_columns(columns):
    """
    智能推荐列映射
    优先级: 精确匹配 > 中文匹配 > 关键词匹配
    """
    mapping = {}
    for col in columns:
        col_lower = col.lower()

        # 日期列
        if not mapping.get('date'):
            if 'date' in col_lower or '日期' in col_lower:
                mapping['date'] = col

        # 现货列
        if not mapping.get('spot'):
            if 'spot' in col_lower or '现货' in col_lower:
                mapping['spot'] = col

        # 期货列
        if not mapping.get('futures'):
            if 'futures' in col_lower or '期货' in col_lower:
                mapping['futures'] = col

    return mapping
```

### 5.2 智能工作表推荐

```python
def recommend_sheet(sheets_info):
    """
    根据列名推荐工作表
    评分: spot+futures > price > 列数最多
    """
    scores = []
    for sheet in sheets_info:
        score = 0
        cols_lower = [c.lower() for c in sheet['columns']]

        if any('spot' in c or '现货' in c for c in cols_lower):
            score += 10
        if any('futures' in c or '期货' in c for c in cols_lower):
            score += 10
        if any('price' in c or '价格' in c for c in cols_lower):
            score += 5
        if any('date' in c or '日期' in c for c in cols_lower):
            score += 3

        scores.append((score, sheet['name']))

    return max(scores)[1] if scores else sheets_info[0]['name']
```

### 5.3 数据过滤流程

```python
def filter_data(df, column_mapping, date_range):
    """
    1. 重命名列 → 统一命名
    2. 转换日期类型
    3. 过滤日期范围
    4. 删除缺失值
    5. 验证数据量（至少100行）
    """
    # 重命名
    df = df.rename(columns=column_mapping)

    # 日期转换
    df['date'] = pd.to_datetime(df['date'])

    # 日期过滤
    df = df[
        (df['date'] >= date_range['start']) &
        (df['date'] <= date_range['end'])
    ]

    # 删除缺失值
    df = df.dropna(subset=['spot', 'futures'])

    # 验证
    if len(df) < 100:
        raise ValueError("筛选后数据不足100行")

    return df
```

## 6. 配置管理

### 6.1 模型配置
```python
MODEL_CONFIG = {
    'basic_garch': {
        'name': 'Basic GARCH',
        'description': '基础GARCH模型，快速计算',
        'p': 1, 'q': 1,
        'corr_window': 120,
        'tax_rate': 0.13
    },
    'dcc_garch': {
        'name': 'DCC-GARCH',
        'description': '动态条件相关GARCH，捕捉时变相关性',
        'p': 1, 'q': 1,
        'dist': 'norm',
        'tax_rate': 0.13
    },
    'ecm_garch': {
        'name': 'ECM-GARCH',
        'description': '误差修正GARCH，考虑协整关系',
        'p': 1, 'q': 1,
        'coint_window': 120,
        'tax_adjust': True,
        'tax_rate': 0.13
    }
}
```

### 6.2 文件上传限制
- 最大文件: 50MB
- 允许格式: .xlsx, .xls
- 临时保存: `outputs/uploaded/temp_*.xlsx`

### 6.3 输出管理
- 每次生成创建独立目录: `outputs/<模型名>_<日期时间>/`
- 自动清理7天前的临时上传文件

## 7. 部署和运行

### 7.1 依赖安装
```bash
pip install flask werkzeug
```

### 7.2 启动服务
```bash
python app.py
# 访问 http://localhost:5000
```

### 7.3 使用示例
```
1. 打开 http://localhost:5000
2. 拖拽 "乙二醇价格 基差.xlsx"
3. 选择工作表 "数据"
4. 确认列映射
5. 选择日期范围: 2021-01-05 ~ 2026-03-02
6. 选择模型: ECM-GARCH
7. 点击"生成报告"
8. 等待2分钟
9. 查看HTML报告并下载
```

## 8. 技术约束和假设

### 8.1 约束
- 单用户本地使用，无需认证
- 同步处理模型计算（1-3分钟）
- 不保存历史记录
- 每次重新上传文件

### 8.2 假设
- 数据文件格式规范（有明确的列名）
- 用户具备基本的金融知识
- 本地机器性能足够运行GARCH模型
- 浏览器支持HTML5（拖拽、date控件）

## 9. 未来扩展

### 9.1 可能的改进
- 异步任务队列（支持多任务并发）
- 历史记录管理
- 参数调优界面
- 批量处理多个文件
- 导出为独立可执行文件（参考ERP项目）

### 9.2 技术升级路径
- 添加数据库（SQLite）存储配置
- 前后端分离（RESTful API）
- Docker容器化部署

## 10. 成功标准

- ✅ 支持拖拽上传Excel
- ✅ 自动检测并推荐工作表和列
- ✅ 可视化配置日期范围
- ✅ 3种模型正常运行
- ✅ 生成完整的HTML报告
- ✅ 提供报告下载功能
- ✅ 错误处理友好
- ✅ 响应时间 < 3分钟
