# 文件上传功能测试文档

## 已实现的功能

### 1. 后端组件

#### `utils/data_processor.py`
- ✅ `read_excel_sheets(filepath)` - 读取Excel所有工作表
- ✅ `preview_sheet(filepath, sheet_name, nrows=10)` - 预览工作表数据
- ✅ `get_all_sheets_info(filepath)` - 获取所有工作表信息
- ✅ `_detect_date_columns(df)` - 自动检测日期列
- ✅ `validate_required_columns(df, required_cols)` - 验证必需列

#### `app.py`
- ✅ 导入数据处理器模块
- ✅ `/api/upload` POST端点 - 处理文件上传
- ✅ `recommend_sheet(sheets_info)` - 智能推荐最佳工作表
- ✅ 文件保存到 `outputs/uploaded/` 目录
- ✅ 文件名添加时间戳避免冲突
- ✅ 错误处理和验证

### 2. 前端组件

#### `static/js/app.js`
- ✅ 全局状态变量 (uploadedFile, selectedSheet, columnMapping)
- ✅ 拖拽上传事件处理
- ✅ 点击上传处理
- ✅ 文件类型验证 (.xlsx, .xls)
- ✅ 文件大小验证 (最大50MB)
- ✅ `handleFileUpload()` - 异步文件上传
- ✅ `showError()` - 错误消息显示
- ✅ `showSuccess()` - 成功消息显示
- ✅ `showInfo()` - 信息消息显示
- ✅ 上传进度指示器
- ✅ 全局API对象 `window.GARCHApp`

#### `templates/index.html`
- ✅ 更新元素ID以匹配JavaScript
- ✅ 添加上传进度样式
- ✅ 添加错误/消息样式
- ✅ 拖拽区域样式

## 测试步骤

### 手动测试

1. **启动Flask应用**
   ```bash
   cd "/Users/mystryl/Documents/GARCH 模型套保方案"
   python app.py
   ```

2. **在浏览器中访问**
   ```
   http://localhost:5000
   ```

3. **测试文件上传**

   方式1: 拖拽上传
   - 将Excel文件拖拽到上传区域
   - 观察上传进度
   - 查看控制台输出

   方式2: 点击上传
   - 点击"选择文件"按钮
   - 选择Excel文件
   - 观察上传进度

4. **验证预期行为**
   - ✅ 文件成功上传到 `outputs/uploaded/`
   - ✅ API返回工作表信息
   - ✅ 推荐工作表正确显示
   - ✅ 控制台显示详细信息
   - ✅ 错误处理正常工作

### 自动化测试

运行数据处理器测试:
```bash
python test_upload_manual.py
```

预期输出:
```
============================================================
数据处理器测试
============================================================

测试文件: /Users/mystryl/Documents/GARCH 模型套保方案/乙二醇价格 基差.xlsx
文件大小: 72.32 KB

正在读取工作表信息...
✓ 成功读取 1 个工作表

工作表 1: 导出数据
  - 行数: 1289
  - 列数: 3
  - 列名: 钢联数据, Unnamed: 1, Unnamed: 2
  - 日期范围: 2021-01-04 至 2026-03-02 (1286 个数据点)

测试工作表推荐算法:
  工作表 '导出数据' 得分: 80
✓ 推荐工作表: 导出数据

============================================================
测试通过 ✓
============================================================
```

## API测试

### 测试 `/api/upload` 端点

```bash
# 使用curl测试
curl -X POST \
  -F "file=@乙二醇价格\ 基差.xlsx" \
  http://localhost:5000/api/upload
```

预期响应:
```json
{
  "success": true,
  "filename": "乙二醇价格 基差_20260303_093000.xlsx",
  "filepath": "/path/to/outputs/uploaded/乙二醇价格 基差_20260303_093000.xlsx",
  "sheets": [
    {
      "name": "导出数据",
      "row_count": 1289,
      "column_count": 3,
      "columns": ["钢联数据", "Unnamed: 1", "Unnamed: 2"],
      "has_data": true,
      "date_range": {
        "start": "2021-01-04",
        "end": "2026-03-02",
        "count": 1286
      }
    }
  ],
  "recommended_sheet": "导出数据",
  "message": "成功上传文件，共找到 1 个工作表"
}
```

## 测试用例

### 正常情况
- ✅ 上传有效的.xlsx文件
- ✅ 上传有效的.xls文件
- ✅ 上传包含多个工作表的Excel文件
- ✅ 上传包含日期列的数据
- ✅ 上传大文件（接近50MB）

### 错误情况
- ✅ 上传非Excel文件（.pdf, .txt等）
- ✅ 上传超过50MB的文件
- ✅ 上传空文件
- ✅ 上传损坏的Excel文件

## 验证检查清单

### 后端验证
- [x] `utils/data_processor.py` 创建并测试
- [x] `app.py` 添加upload端点
- [x] `recommend_sheet()` 函数实现
- [x] 文件保存到正确目录
- [x] 错误处理完善

### 前端验证
- [x] `app.js` 实现拖拽上传
- [x] 文件类型和大小验证
- [x] 异步上传请求
- [x] 错误消息显示
- [x] 成功消息显示
- [x] 全局状态管理

### 集成验证
- [x] 前后端连接正常
- [x] 数据格式一致
- [x] 错误处理完整
- [x] 用户体验流畅

## 已知限制

1. **displaySheets函数**: 该函数将在Task 4中实现
2. **当前测试**: 使用alert显示结果，Task 4后将使用UI组件
3. **列映射**: Task 5中实现
4. **模型运行**: Task 6+中实现

## 下一步

参考实施计划:
- Task 4: 工作表检测和预览
- Task 5: 数据预览和日期范围
- Task 6+: 模型集成和报告生成

## 文件变更总结

### 新增文件
- `utils/data_processor.py` - 数据处理器模块
- `test_upload_manual.py` - 测试脚本
- `TESTING_UPLOAD.md` - 本文档

### 修改文件
- `app.py` - 添加upload端点和recommend_sheet函数
- `static/js/app.js` - 实现完整的前端上传逻辑
- `templates/index.html` - 更新元素ID和样式

### 创建目录
- `outputs/uploaded/` - 上传文件存储目录
