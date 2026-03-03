# GARCH模型套保分析Web平台实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 构建一个通用的GARCH模型套保分析Web平台，支持拖拽上传Excel、可视化配置、自动生成完整报告

**架构:** Flask后端 + Jinja2模板 + 原生JavaScript前端，复用现有的 basic_garch_analyzer 模块

**技术栈:**
- 后端: Flask 3.0, pandas, openpyxl
- 前端: Jinja2, 原生JS, CSS3
- 模型: 现有的 basic_garch_analyzer, model_dcc_garch, model_ecm_garch

---

## 任务概览

1. 项目结构搭建和依赖配置
2. Flask应用框架搭建
3. 文件上传功能
4. 工作表检测和预览
5. 智能列推荐和映射
6. 日期范围选择
7. 模型Wrapper封装
8. 报告生成和下载
9. 前端UI和交互
10. 测试和优化

---

## Task 1: 项目结构搭建和依赖配置

**文件:**
- 创建: `requirements_web.txt`
- 创建: `config.py`
- 创建: `static/css/style.css`
- 创建: `static/js/app.js`
- 创建: `templates/base.html`
- 创建目录: `models/`, `utils/`, `outputs/uploaded/`

**Step 1: 创建 requirements_web.txt**

```txt
Flask>=3.0.0
Werkzeug>=3.0.0
pandas>=2.0.0
openpyxl>=3.1.0
```

运行: `pip install -r requirements_web.txt`

**Step 2: 创建 config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Flask配置
SECRET_KEY = os.environ.get('SECRET_KEY', 'garch-platform-dev-key')
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000

# 文件上传配置
UPLOAD_FOLDER = BASE_DIR / 'outputs' / 'uploaded'
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# 输出配置
OUTPUT_DIR = BASE_DIR / 'outputs'

# 模型配置
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
        'coupling_method': 'ect-garch',
        'tax_rate': 0.13
    }
}
```

**Step 3: 创建目录结构**

运行:
```bash
mkdir -p static/css static/js models utils outputs/uploaded
touch models/__init__.py utils/__init__.py
```

**Step 4: 创建基础样式文件 static/css/style.css**

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background-color: #f5f5f5;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.card {
    background: white;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    text-align: center;
    color: #2c3e50;
    margin-bottom: 30px;
}

h2 {
    color: #34495e;
    margin-bottom: 16px;
    font-size: 18px;
}

/* 拖拽区域 */
.upload-area {
    border: 3px dashed #3498db;
    border-radius: 8px;
    padding: 60px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
}

.upload-area:hover, .upload-area.dragover {
    background-color: #ecf0f1;
    border-color: #2980b9;
}

/* 按钮 */
.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 16px;
    transition: background 0.3s;
}

.btn-primary {
    background-color: #3498db;
    color: white;
}

.btn-primary:hover {
    background-color: #2980b9;
}

.btn:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
}

/* 表单 */
.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
}

.form-control {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

/* 数据预览表格 */
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 16px;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #f8f9fa;
    font-weight: 600;
}

/* Loading */
.loading {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 3px solid rgba(0,0,0,0.1);
    border-radius: 50%;
    border-top-color: #3498db;
    animation: spin 1s ease-in-out infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* 隐藏元素 */
.hidden {
    display: none;
}

/* 成功/错误消息 */
.alert {
    padding: 12px 20px;
    border-radius: 4px;
    margin-bottom: 16px;
}

.alert-success {
    background-color: #d4edda;
    color: #155724;
}

.alert-error {
    background-color: #f8d7da;
    color: #721c24;
}
```

**Step 5: 提交**

运行:
```bash
git add requirements_web.txt config.py static/ models/ utils/
git commit -m "feat: Set up project structure and dependencies for web platform"
```

---

## Task 2: Flask应用框架搭建

**文件:**
- 创建: `app.py`
- 修改: `templates/base.html`

**Step 1: 创建基础Flask应用 app.py**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GARCH模型套保分析Web平台
"""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import (
    SECRET_KEY, DEBUG, HOST, PORT,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH, ALLOWED_EXTENSIONS,
    OUTPUT_DIR, MODEL_CONFIG
)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH
)

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("=" * 60)
    print("GARCH模型套保分析Web平台")
    print("=" * 60)
    print(f"请在浏览器中访问: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host=HOST, port=PORT, debug=DEBUG)
```

**Step 2: 创建基础模板 templates/base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}GARCH模型套保分析平台{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="container">
        <h1>GARCH模型套保分析平台</h1>

        {% block content %}{% endblock %}

        <footer style="text-align: center; margin-top: 50px; color: #7f8c8d; font-size: 14px;">
            <p>GARCH套保策略分析系统 v1.0</p>
        </footer>
    </div>

    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

**Step 3: 创建主页面 templates/index.html**

```html
{% extends "base.html" %}

{% block title %}首页 - GARCH模型套保分析平台{% endblock %}

{% block content %}
<!-- 步骤1: 上传文件 -->
<div class="card" id="step1">
    <h2>步骤1: 上传数据文件</h2>
    <div class="upload-area" id="uploadArea">
        <p style="font-size: 48px; margin-bottom: 16px;">📁</p>
        <p style="font-size: 18px; margin-bottom: 8px;">拖拽Excel文件到此处</p>
        <p style="color: #7f8c8d;">或点击选择文件</p>
        <input type="file" id="fileInput" accept=".xlsx,.xls" style="display: none;">
    </div>
    <div id="uploadStatus" class="hidden"></div>
</div>

<!-- 步骤1.5: 选择工作表 -->
<div class="card hidden" id="step1_5">
    <h2>步骤1.5: 选择工作表</h2>
    <div id="sheetList"></div>
    <div id="sheetPreview"></div>
</div>

<!-- 步骤2: 确认数据映射 -->
<div class="card hidden" id="step2">
    <h2>步骤2: 确认数据映射</h2>
    <div class="form-group">
        <label>日期列:</label>
        <select id="dateColumn" class="form-control"></select>
    </div>
    <div class="form-group">
        <label>现货列:</label>
        <select id="spotColumn" class="form-control"></select>
    </div>
    <div class="form-group">
        <label>期货列:</label>
        <select id="futuresColumn" class="form-control"></select>
    </div>
    <div class="form-group">
        <label>日期范围:</label>
        <div style="display: flex; gap: 16px;">
            <input type="date" id="startDate" class="form-control">
            <input type="date" id="endDate" class="form-control">
        </div>
    </div>
    <div id="dataPreview"></div>
</div>

<!-- 步骤3: 选择模型 -->
<div class="card hidden" id="step3">
    <h2>步骤3: 选择模型并生成报告</h2>
    <div id="modelList">
        {% for model_key, model_config in MODEL_CONFIG.items() %}
        <div class="model-option">
            <input type="radio" name="model" id="{{ model_key }}" value="{{ model_key }}">
            <label for="{{ model_key }}">
                <strong>{{ model_config.name }}</strong>
                <p style="color: #7f8c8d; font-size: 14px;">{{ model_config.description }}</p>
            </label>
        </div>
        {% endfor %}
    </div>
    <button id="generateBtn" class="btn btn-primary" style="margin-top: 16px;">生成报告</button>
</div>

<!-- 结果区域 -->
<div class="card hidden" id="result">
    <h2>报告生成完成！</h2>
    <div id="resultSummary"></div>
    <div style="margin-top: 16px;">
        <a id="viewReportBtn" href="#" target="_blank" class="btn btn-primary">查看报告</a>
        <a id="downloadBtn" href="#" class="btn btn-primary">下载报告</a>
    </div>
</div>
{% endblock %}
```

**Step 4: 测试启动**

运行:
```bash
python app.py
```

访问: http://localhost:5000

预期: 看到页面显示"步骤1: 上传数据文件"

**Step 5: 提交**

```bash
git add app.py templates/
git commit -m "feat: Set up Flask application and basic UI"
```

---

## Task 3: 文件上传功能

**文件:**
- 创建: `utils/data_processor.py`
- 修改: `app.py`
- 修改: `static/js/app.js`

**Step 1: 创建数据处理工具 utils/data_processor.py**

```python
import pandas as pd
from pathlib import Path


def read_excel_sheets(filepath):
    """
    读取Excel文件的所有工作表信息

    Args:
        filepath: Excel文件路径

    Returns:
        list: 工作表信息列表
            [{
                'name': 'Sheet1',
                'columns': ['date', 'spot', 'futures'],
                'ncols': 3,
                'nrows': 1246
            }]
    """
    xls = pd.ExcelFile(filepath)
    sheets_info = []

    for sheet_name in xls.sheet_names:
        # 读取0行获取列名
        df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=0)
        # 读取全部获取行数
        df_full = pd.read_excel(filepath, sheet_name=sheet_name)

        sheets_info.append({
            'name': sheet_name,
            'columns': list(df.columns),
            'ncols': len(df.columns),
            'nrows': len(df_full)
        })

    return sheets_info


def preview_sheet(filepath, sheet_name, nrows=10):
    """
    预览工作表数据

    Args:
        filepath: Excel文件路径
        sheet_name: 工作表名称
        nrows: 预览行数

    Returns:
        dict: {
            'columns': [...],
            'preview': [...],  # list of dict
            'total_rows': 1246,
            'date_range': {'min': '2021-01-05', 'max': '2026-03-02'}
        }
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name, nrows=nrows)
    df_full = pd.read_excel(filepath, sheet_name=sheet_name)

    # 尝试检测日期列并获取日期范围
    date_range = None
    for col in df_full.columns:
        if 'date' in str(col).lower() or '日期' in str(col):
            try:
                dates = pd.to_datetime(df_full[col])
                date_range = {
                    'min': dates.min().strftime('%Y-%m-%d'),
                    'max': dates.max().strftime('%Y-%m-%d')
                }
                break
            except:
                pass

    return {
        'columns': list(df.columns),
        'preview': df.to_dict('records'),
        'total_rows': len(df_full),
        'date_range': date_range
    }
```

**Step 2: 在app.py中添加上传API**

```python
from utils.data_processor import read_excel_sheets, preview_sheet

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传Excel文件并解析工作表"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '仅支持.xlsx/.xls格式'}), 400

    try:
        # 保存文件
        filename = secure_filename(file.filename)
        import uuid
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = Path(app.config['UPLOAD_FOLDER']) / unique_filename
        file.save(str(filepath))

        # 读取所有工作表
        sheets_info = read_excel_sheets(str(filepath))

        # 智能推荐工作表
        recommended_sheet = recommend_sheet(sheets_info)

        return jsonify({
            'success': True,
            'filepath': str(filepath),
            'filename': filename,
            'sheets': sheets_info,
            'recommended_sheet': recommended_sheet
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'文件解析失败: {str(e)}'}), 500


def recommend_sheet(sheets_info):
    """智能推荐工作表"""
    scores = []
    for sheet in sheets_info:
        score = 0
        cols_lower = [str(c).lower() for c in sheet['columns']]

        if any('spot' in c or '现货' in c for c in cols_lower):
            score += 10
        if any('futures' in c or '期货' in c for c in cols_lower):
            score += 10
        if any('price' in c or '价格' in c for c in cols_lower):
            score += 5
        if any('date' in c or '日期' in c for c in cols_lower):
            score += 3

        scores.append((score, sheet['name']))

    if scores:
        return max(scores)[1]
    return sheets_info[0]['name'] if sheets_info else None
```

**Step 3: 添加前端上传逻辑 static/js/app.js**

```javascript
// 全局状态
let uploadedFile = null;
let selectedSheet = null;
let columnMapping = {};

// 拖拽上传
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

uploadArea.addEventListener('click', () => fileInput.click());

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', async (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        await handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
        await handleFileUpload(e.target.files[0]);
    }
});

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            uploadedFile = result;
            displaySheets(result.sheets, result.recommended_sheet);
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('上传失败: ' + error.message);
    }
}

function showError(message) {
    const status = document.getElementById('uploadStatus');
    status.className = 'alert alert-error';
    status.textContent = message;
    status.classList.remove('hidden');
}
```

**Step 4: 测试上传功能**

运行:
```bash
python app.py
```

测试: 拖拽一个Excel文件到上传区域

预期: 看到工作表列表显示（但还没有显示逻辑，下一步实现）

**Step 5: 提交**

```bash
git add utils/ app.py static/js/app.js
git commit -m "feat: Add file upload functionality"
```

---

## Task 4: 工作表选择和预览

**文件:**
- 修改: `app.py`
- 修改: `static/js/app.js`

**Step 1: 添加工作表预览API (app.py)**

```python
@app.route('/api/preview-sheet', methods=['POST'])
def preview_sheet_api():
    """获取工作表预览"""
    data = request.get_json()
    filepath = data.get('filepath')
    sheet_name = data.get('sheet_name')

    if not filepath or not sheet_name:
        return jsonify({'success': False, 'error': '缺少参数'}), 400

    if not Path(filepath).exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 400

    try:
        preview = preview_sheet(filepath, sheet_name)

        # 智能推荐列映射
        suggested_mapping = suggest_columns(preview['columns'])

        return jsonify({
            'success': True,
            'preview': preview,
            'suggested_mapping': suggested_mapping
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'预览失败: {str(e)}'}), 500


def suggest_columns(columns):
    """智能推荐列映射"""
    mapping = {}
    for col in columns:
        col_lower = str(col).lower()

        if not mapping.get('date'):
            if 'date' in col_lower or '日期' in col_lower:
                mapping['date'] = col

        if not mapping.get('spot'):
            if 'spot' in col_lower or '现货' in col_lower:
                mapping['spot'] = col

        if not mapping.get('futures'):
            if 'futures' in col_lower or '期货' in col_lower:
                mapping['futures'] = col

    return mapping
```

**Step 2: 添加工作表显示和选择逻辑 (static/js/app.js)**

```javascript
function displaySheets(sheets, recommended) {
    const step1_5 = document.getElementById('step1_5');
    const sheetList = document.getElementById('sheetList');

    let html = '<p>检测到 ' + sheets.length + ' 个工作表:</p>';

    sheets.forEach(sheet => {
        const isRecommended = sheet.name === recommended;
        html += `
            <div class="sheet-option" style="margin-bottom: 12px;">
                <label style="display: flex; align-items: center; padding: 12px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; ${isRecommended ? 'background-color: #e3f2fd;' : ''}">
                    <input type="radio" name="sheet" value="${sheet.name}" ${isRecommended ? 'checked' : ''}>
                    <span style="margin-left: 12px;">
                        <strong>${sheet.name}</strong>
                        ${isRecommended ? ' <span style="color: #3498db;">(推荐)</span>' : ''}
                        <span style="color: #7f8c8d; margin-left: 8px;">(${sheet.nrows}行 × ${sheet.ncols}列)</span>
                    </span>
                </label>
            </div>
        `;
    });

    sheetList.innerHTML = html;

    // 绑定选择事件
    document.querySelectorAll('input[name="sheet"]').forEach(radio => {
        radio.addEventListener('change', async (e) => {
            await loadSheetPreview(e.target.value);
        });
    });

    // 自动加载推荐工作表
    const recommendedRadio = document.querySelector(`input[value="${recommended}"]`);
    if (recommendedRadio) {
        recommendedRadio.dispatchEvent(new Event('change'));
    }

    step1_5.classList.remove('hidden');
}

async function loadSheetPreview(sheetName) {
    selectedSheet = sheetName;

    try {
        const response = await fetch('/api/preview-sheet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filepath: uploadedFile.filepath,
                sheet_name: sheetName
            })
        });

        const result = await response.json();

        if (result.success) {
            displayColumnMapping(result.preview.columns, result.suggested_mapping);
            displayDataPreview(result.preview.preview);
            displayDateRange(result.preview.date_range);
            showStep2();
        } else {
            showError(result.error);
        }
    } catch (error) {
        showError('加载预览失败: ' + error.message);
    }
}

function displayColumnMapping(columns, suggested) {
    const selects = {
        date: document.getElementById('dateColumn'),
        spot: document.getElementById('spotColumn'),
        futures: document.getElementById('futuresColumn')
    };

    Object.keys(selects).forEach(key => {
        const select = selects[key];
        select.innerHTML = '<option value="">-- 请选择 --</option>';

        columns.forEach(col => {
            const option = document.createElement('option');
            option.value = col;
            option.textContent = col;

            if (suggested[key] === col) {
                option.selected = true;
                option.style.fontWeight = 'bold';
                option.textContent += ' ✨';
            }

            select.appendChild(option);
        });
    });

    columnMapping = {...suggested};
}
```

**Step 3: 测试工作表选择**

运行:
```bash
python app.py
```

测试: 上传文件 → 选择工作表

预期: 看到列映射和数据预览

**Step 4: 提交**

```bash
git add app.py static/js/app.js
git commit -m "feat: Add sheet selection and preview"
```

---

## Task 5: 数据预览和日期范围选择

**文件:**
- 修改: `static/js/app.js`

**Step 1: 添加数据预览显示函数**

```javascript
function displayDataPreview(previewData) {
    const container = document.getElementById('dataPreview');

    if (!previewData || previewData.length === 0) {
        container.innerHTML = '<p style="color: #7f8c8d;">暂无数据</p>';
        return;
    }

    const columns = Object.keys(previewData[0]);

    let html = '<h3 style="margin-top: 24px; font-size: 16px;">数据预览 (前10行):</h3>';
    html += '<table><thead><tr>';

    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });

    html += '</tr></thead><tbody>';

    previewData.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            html += `<td>${row[col] !== null ? row[col] : ''}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function displayDateRange(dateRange) {
    if (!dateRange) return;

    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');

    startDate.value = dateRange.min;
    endDate.value = dateRange.max;
}

function showStep2() {
    document.getElementById('step2').classList.remove('hidden');
    document.getElementById('step3').classList.remove('hidden');
}
```

**Step 2: 测试数据预览**

上传文件并选择工作表

预期: 看到数据表格和日期范围

**Step 3: 提交**

```bash
git add static/js/app.js
git commit -m "feat: Add data preview and date range display"
```

---

## Task 6: 模型Wrapper封装

**文件:**
- 创建: `models/basic_garch_wrapper.py`
- 创建: `models/dcc_garch_wrapper.py`
- 创建: `models/ecm_garch_wrapper.py`
- 创建: `models/__init__.py`

**Step 1: 创建Basic GARCH Wrapper**

```python
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from basic_garch_analyzer import run_analysis, ModelConfig


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config):
    """
    运行Basic GARCH模型

    Returns:
        dict: {
            'success': bool,
            'report_path': str,
            'summary': dict,
            'error': str (如果失败)
        }
    """
    try:
        # 读取数据
        df = pd.read_excel(data_path, sheet_name=sheet_name)

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 转换日期
        df['date'] = pd.to_datetime(df['date'])

        # 过滤日期范围
        df = df[
            (df['date'] >= date_range['start']) &
            (df['date'] <= date_range['end'])
        ]

        # 删除缺失值
        df = df.dropna(subset=['spot', 'futures'])

        if len(df) < 100:
            return {
                'success': False,
                'error': f'筛选后数据不足100行，当前仅{len(df)}行'
            }

        # 保存临时文件
        temp_file = Path(output_dir) / 'temp_data.xlsx'
        df.to_excel(temp_file, index=False)

        # 配置模型
        config = ModelConfig(
            enable_rolling_backtest=True,
            n_periods=6,
            window_days=90,
            backtest_seed=42,
            tax_rate=model_config.get('tax_rate', 0.13),
            output_dir=output_dir
        )

        # 运行模型
        result = run_analysis(
            excel_path=str(temp_file),
            spot_col='spot',
            futures_col='futures',
            config=config
        )

        # 删除临时文件
        temp_file.unlink()

        # 提取摘要
        summary = {
            'variance_reduction': result['rolling_results']['avg_variance_reduction'],
            'avg_return_hedged': result['rolling_results']['avg_return_hedged'],
            'avg_max_dd_hedged': result['rolling_results']['avg_max_dd_hedged']
        }

        report_path = Path(output_dir) / 'report.html'

        return {
            'success': True,
            'report_path': str(report_path),
            'summary': summary
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': f'模型运行失败: {str(e)}\n{traceback.format_exc()}'
        }
```

**Step 2: 创建DCC-GARCH Wrapper**

```python
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_dcc_garch import fit_dcc_garch
from basic_garch_analyzer.rolling_backtest import run_rolling_backtest
from basic_garch_analyzer.report_generator import (
    plot_price_series, plot_returns, plot_hedge_ratio,
    plot_performance_metrics, plot_summary_table
)


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config):
    """运行DCC-GARCH模型"""
    try:
        # 读取和准备数据
        df = pd.read_excel(data_path, sheet_name=sheet_name)
        df = df.rename(columns=column_mapping)
        df['date'] = pd.to_datetime(df['date'])

        # 过滤日期范围
        df = df[
            (df['date'] >= date_range['start']) &
            (df['date'] <= date_range['end'])
        ]
        df = df.dropna(subset=['spot', 'futures'])

        if len(df) < 100:
            return {'success': False, 'error': f'数据不足100行，当前{len(df)}行'}

        # 拟合DCC-GARCH模型
        model_results = fit_dcc_garch(
            df,
            p=model_config.get('p', 1),
            q=model_config.get('q', 1),
            dist=model_config.get('dist', 'norm'),
            output_dir=f'{output_dir}/model_results'
        )

        # 税点调整
        tax_rate = model_config.get('tax_rate', 0.13)
        tax_adj = 1 / (1 + tax_rate)
        model_results['h_actual'] = model_results['h_actual'] * tax_adj

        # 滚动回测
        rolling_results = run_rolling_backtest(
            data=df,
            hedge_ratios=model_results['h_actual'],
            n_periods=6,
            window_days=90,
            seed=42,
            tax_rate=tax_rate
        )

        # 生成报告
        from basic_garch_analyzer.report_generator import generate_rolling_backtest_report
        generate_rolling_backtest_report(
            data=df,
            results=rolling_results,
            output_dir=output_dir,
            generate_html=False
        )

        summary = {
            'variance_reduction': rolling_results['avg_variance_reduction'],
            'avg_return_hedged': rolling_results['avg_return_hedged'],
            'avg_max_dd_hedged': rolling_results['avg_max_dd_hedged']
        }

        return {
            'success': True,
            'report_path': str(Path(output_dir) / 'report.html'),
            'summary': summary
        }

    except Exception as e:
        return {'success': False, 'error': f'DCC-GARCH运行失败: {str(e)}'}
```

**Step 3: 创建ECM-GARCH Wrapper**

```python
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from model_ecm_garch import fit_ecm_garch
from basic_garch_analyzer.rolling_backtest import run_rolling_backtest
from basic_garch_analyzer.report_generator import generate_rolling_backtest_report


def run_model(data_path, sheet_name, column_mapping, date_range, output_dir, model_config):
    """运行ECM-GARCH模型"""
    try:
        # 读取和准备数据
        df = pd.read_excel(data_path, sheet_name=sheet_name)
        df = df.rename(columns=column_mapping)
        df['date'] = pd.to_datetime(df['date'])

        # 过滤日期范围
        df = df[
            (df['date'] >= date_range['start']) &
            (df['date'] <= date_range['end'])
        ]
        df = df.dropna(subset=['spot', 'futures'])

        if len(df) < 100:
            return {'success': False, 'error': f'数据不足100行，当前{len(df)}行'}

        # 拟合ECM-GARCH模型
        model_results = fit_ecm_garch(
            df,
            p=model_config.get('p', 1),
            q=model_config.get('q', 1),
            output_dir=f'{output_dir}/model_results',
            coint_window=model_config.get('coint_window', 120),
            tax_adjust=model_config.get('tax_adjust', True),
            coupling_method=model_config.get('coupling_method', 'ect-garch')
        )

        # 滚动回测
        tax_rate = model_config.get('tax_rate', 0.13)
        rolling_results = run_rolling_backtest(
            data=df,
            hedge_ratios=model_results['h_actual'],
            n_periods=6,
            window_days=90,
            seed=42,
            tax_rate=tax_rate
        )

        # 生成报告
        generate_rolling_backtest_report(
            data=df,
            results=rolling_results,
            output_dir=output_dir,
            generate_html=False
        )

        summary = {
            'variance_reduction': rolling_results['avg_variance_reduction'],
            'avg_return_hedged': rolling_results['avg_return_hedged'],
            'avg_max_dd_hedged': rolling_results['avg_max_dd_hedged']
        }

        return {
            'success': True,
            'report_path': str(Path(output_dir) / 'report.html'),
            'summary': summary
        }

    except Exception as e:
        return {'success': False, 'error': f'ECM-GARCH运行失败: {str(e)}'}
```

**Step 4: 更新 models/__init__.py**

```python
from .basic_garch_wrapper import run_model as run_basic_garch
from .dcc_garch_wrapper import run_model as run_dcc_garch
from .ecm_garch_wrapper import run_model as run_ecm_garch

MODEL_RUNNERS = {
    'basic_garch': run_basic_garch,
    'dcc_garch': run_dcc_garch,
    'ecm_garch': run_ecm_garch
}
```

**Step 5: 提交**

```bash
git add models/
git commit -m "feat: Add model wrappers for Basic/DCC/ECM GARCH"
```

---

## Task 7: 报告生成API

**文件:**
- 修改: `app.py`

**Step 1: 添加报告生成API**

```python
import shutil
from datetime import datetime
from models import MODEL_RUNNERS
from config import MODEL_CONFIG


@app.route('/api/generate', methods=['POST'])
def generate_report():
    """生成报告"""
    data = request.get_json()

    # 获取参数
    filepath = data.get('filepath')
    sheet_name = data.get('sheet_name')
    model_type = data.get('model_type')
    column_mapping = data.get('column_mapping')
    date_range = data.get('date_range')

    # 验证参数
    if not all([filepath, sheet_name, model_type, column_mapping, date_range]):
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    if model_type not in MODEL_RUNNERS:
        return jsonify({'success': False, 'error': f'不支持的模型: {model_type}'}), 400

    # 验证列映射
    required_cols = ['date', 'spot', 'futures']
    for col in required_cols:
        if col not in column_mapping or not column_mapping[col]:
            return jsonify({'success': False, 'error': f'未选择{col}列'}), 400

    # 创建输出目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = OUTPUT_DIR / f'{model_type}_{timestamp}'
    output_dir.mkdir(exist_ok=True)

    try:
        # 运行模型
        model_runner = MODEL_RUNNERS[model_type]
        result = model_runner(
            data_path=filepath,
            sheet_name=sheet_name,
            column_mapping=column_mapping,
            date_range=date_range,
            output_dir=str(output_dir),
            model_config=MODEL_CONFIG[model_type]
        )

        if not result['success']:
            return jsonify(result), 500

        # 生成下载文件名
        download_name = f'{model_type}_report_{timestamp}.zip'
        download_path = OUTPUT_DIR / download_name

        # 打包报告
        shutil.make_archive(
            str(download_path).replace('.zip', ''),
            'zip',
            root_dir=str(output_dir),
            base_dir='.'
        )

        return jsonify({
            'success': True,
            'report_path': str(result['report_path']),
            'download_url': f'/download/{download_name}',
            'summary': result['summary']
        })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'生成报告失败: {str(e)}\n{traceback.format_exc()}'
        }), 500


@app.route('/download/<filename>')
def download_report(filename):
    """下载报告"""
    filepath = OUTPUT_DIR / filename

    if not filepath.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    return send_file(filepath, as_attachment=True)
```

**Step 2: 提交**

```bash
git add app.py
git commit -m "feat: Add report generation API"
```

---

## Task 8: 前端生成报告交互

**文件:**
- 修改: `static/js/app.js`

**Step 1: 添加生成报告逻辑**

```javascript
// 生成报告按钮
const generateBtn = document.getElementById('generateBtn');
generateBtn.addEventListener('click', generateReport);

async function generateReport() {
    // 获取选中的模型
    const selectedModel = document.querySelector('input[name="model"]:checked');
    if (!selectedModel) {
        alert('请选择模型类型');
        return;
    }

    // 收集参数
    const columnMapping = {
        date: document.getElementById('dateColumn').value,
        spot: document.getElementById('spotColumn').value,
        futures: document.getElementById('futuresColumn').value
    };

    const dateRange = {
        start: document.getElementById('startDate').value,
        end: document.getElementById('endDate').value
    };

    // 验证
    if (!columnMapping.date || !columnMapping.spot || !columnMapping.futures) {
        alert('请完整选择数据列');
        return;
    }

    if (!dateRange.start || !dateRange.end) {
        alert('请选择日期范围');
        return;
    }

    // 禁用按钮，显示loading
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="loading"></span> 正在生成报告，请稍候...';

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filepath: uploadedFile.filepath,
                sheet_name: selectedSheet,
                model_type: selectedModel.value,
                column_mapping: columnMapping,
                date_range: dateRange
            })
        });

        const result = await response.json();

        if (result.success) {
            displayResult(result);
        } else {
            alert('生成报告失败: ' + result.error);
            generateBtn.disabled = false;
            generateBtn.textContent = '生成报告';
        }
    } catch (error) {
        alert('生成报告失败: ' + error.message);
        generateBtn.disabled = false;
        generateBtn.textContent = '生成报告';
    }
}

function displayResult(result) {
    const resultDiv = document.getElementById('result');
    const summaryDiv = document.getElementById('resultSummary');
    const viewBtn = document.getElementById('viewReportBtn');
    const downloadBtn = document.getElementById('downloadBtn');

    // 显示摘要
    summaryDiv.innerHTML = `
        <h3 style="margin-bottom: 16px;">核心指标</h3>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
            <div style="padding: 16px; background: #f8f9fa; border-radius: 4px;">
                <div style="color: #7f8c8d; font-size: 14px;">方差降低</div>
                <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                    ${(result.summary.variance_reduction * 100).toFixed(2)}%
                </div>
            </div>
            <div style="padding: 16px; background: #f8f9fa; border-radius: 4px;">
                <div style="color: #7f8c8d; font-size: 14px;">套保后收益率</div>
                <div style="font-size: 24px; font-weight: bold; color: #3498db;">
                    ${(result.summary.avg_return_hedged * 100).toFixed(2)}%
                </div>
            </div>
            <div style="padding: 16px; background: #f8f9fa; border-radius: 4px;">
                <div style="color: #7f8c8d; font-size: 14px;">最大回撤</div>
                <div style="font-size: 24px; font-weight: bold; color: #e74c3c;">
                    ${(result.summary.avg_max_dd_hedged * 100).toFixed(2)}%
                </div>
            </div>
        </div>
    `;

    // 设置按钮链接
    viewBtn.href = '/report?path=' + encodeURIComponent(result.report_path);
    downloadBtn.href = result.download_url;

    // 显示结果区域
    resultDiv.classList.remove('hidden');

    // 恢复生成按钮
    generateBtn.disabled = false;
    generateBtn.textContent = '生成报告';

    // 滚动到结果区域
    resultDiv.scrollIntoView({behavior: 'smooth'});
}
```

**Step 2: 添加报告查看API (app.py)**

```python
@app.route('/report')
def view_report():
    """查看HTML报告"""
    report_path = request.args.get('path')

    if not report_path or not Path(report_path).exists():
        return "报告不存在", 404

    return send_file(report_path)
```

**Step 3: 提交**

```bash
git add static/js/app.js app.py
git commit -m "feat: Add report generation interaction"
```

---

## Task 9: 测试和优化

**文件:**
- 修改: `app.py`
- 创建: `README_WEB.md`

**Step 1: 添加错误处理中间件**

```python
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'success': False, 'error': '文件过大，最大支持50MB'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500
```

**Step 2: 创建使用文档 README_WEB.md**

```markdown
# GARCH模型套保分析Web平台使用指南

## 启动服务

```bash
pip install -r requirements_web.txt
python app.py
```

访问: http://localhost:5000

## 使用流程

1. **上传Excel文件**
   - 拖拽文件到上传区域
   - 支持格式: .xlsx, .xls
   - 最大50MB

2. **选择工作表**
   - 系统自动推荐最合适的工作表
   - 可手动选择其他工作表
   - 预览前10行数据

3. **确认数据映射**
   - 检查日期列、现货列、期货列是否正确
   - 系统智能推荐并标记 ✨
   - 可手动调整

4. **选择日期范围**
   - 使用日历控件选择分析区间
   - 默认为全部数据

5. **选择模型并生成**
   - Basic GARCH: 快速，适合初步分析
   - DCC-GARCH: 捕捉时变相关性
   - ECM-GARCH: 考虑协整关系
   - 点击"生成报告"等待1-3分钟

6. **查看和下载**
   - 查看核心指标摘要
   - 在线查看完整HTML报告
   - 下载ZIP压缩包

## 技术支持

遇到问题请查看:
- 模型文档: docs/GARCH模型回测指南.md
- GitHub Issues
```

**Step 3: 完整测试**

测试场景:
1. 上传乙二醇数据 → 选择ECM-GARCH → 生成报告
2. 上传热卷数据 → 选择DCC-GARCH → 生成报告
3. 测试日期范围过滤
4. 测试错误处理（上传非Excel文件、列缺失等）

**Step 4: 提交**

```bash
git add README_WEB.md app.py
git commit -m "docs: Add usage guide and error handling"
```

---

## Task 10: 最终清理和文档

**Step 1: 清理临时文件**

```bash
find outputs/uploaded -name "temp_*.xlsx" -mtime +7 -delete
```

**Step 2: 更新主README**

**Step 3: 最终提交**

```bash
git add .
git commit -m "feat: Complete GARCH web platform implementation"
```

---

## 实现注意事项

1. **模型复用**: 所有wrapper都复用现有的模型代码，不重新实现
2. **路径处理**: 使用`pathlib.Path`处理所有文件路径
3. **错误处理**: 每个步骤都有try-except，返回统一错误格式
4. **内存管理**: 大文件处理时注意内存，及时删除临时文件
5. **测试数据**: 使用乙二醇和热卷数据进行测试

## 依赖检查清单

- [x] Flask 3.0+
- [x] pandas 2.0+
- [x] openpyxl 3.1+
- [x] 现有的 basic_garch_analyzer 模块
- [x] 现有的 model_dcc_garch, model_ecm_garch

## 成功标准

- [x] 支持拖拽上传Excel
- [x] 自动检测并推荐工作表和列
- [x] 可视化配置日期范围
- [x] 3种模型正常运行
- [x] 生成完整的HTML报告
- [x] 提供报告下载功能
- [x] 错误处理友好
- [x] 响应时间 < 3分钟
