# GARCH模型套保分析Web平台

独立的Web应用，用于GARCH模型套保分析。

## 📁 项目结构

```
garch-web-platform/
├── app.py                    # Flask主应用
├── config.py                 # 配置文件
├── requirements_web.txt      # Python依赖
├── start.sh                  # 启动脚本
├── static/                   # 前端静态资源
│   ├── css/                  # 样式文件
│   └── js/                   # JavaScript文件
├── templates/                # HTML模板
├── models/                   # 模型Wrapper
│   ├── basic_garch_wrapper.py
│   ├── dcc_garch_wrapper.py
│   └── ecm_garch_wrapper.py
├── utils/                    # 工具函数
│   └── data_processor.py
└── lib/                      # 引用的库模块
    ├── basic_garch_analyzer/  # Basic GARCH分析器
    ├── model_dcc_garch.py     # DCC-GARCH模型
    └── model_ecm_garch.py     # ECM-GARCH模型
```

## 🚀 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
./start.sh
```

### 方式2: 手动启动

```bash
# 1. 安装依赖（首次运行）
pip install -r requirements_web.txt

# 2. 启动Flask应用
python app.py
```

### 方式3: 后台运行

```bash
nohup python app.py > flask.log 2>&1 &
```

## 🌐 访问地址

启动后在浏览器中打开：
```
http://localhost:6000
```

## 📊 功能特性

- ✅ 拖拽上传Excel文件
- ✅ 智能工作表和列推荐
- ✅ 可视化列映射配置
- ✅ 日期范围选择
- ✅ 3种GARCH模型（Basic/DCC/ECM）
- ✅ 自动生成HTML报告
- ✅ ZIP打包下载

## 🛠️ 管理命令

### 查看日志
```bash
tail -f flask.log
```

### 停止应用
```bash
pkill -f "python.*app.py"
```

### 检查进程
```bash
ps aux | grep "python.*app.py" | grep -v grep
```

### 修改端口

编辑 `config.py` 中的 `PORT` 值（默认6000）

## 📦 依赖说明

主要依赖：
- Flask 3.0+ - Web框架
- pandas 2.0+ - 数据处理
- openpyxl 3.1+ - Excel读写
- arch 6.0+ - GARCH模型
- mgarch 0.2+ - DCC-GARCH模型
- matplotlib - 图表生成
- numpy, scipy - 数值计算

## 📝 使用流程

1. 上传Excel数据文件
2. 选择工作表
3. 确认数据映射（日期、现货、期货列）
4. 选择日期范围
5. 选择模型类型
6. 生成报告
7. 查看或下载报告

## 🔧 配置

所有配置都在 `config.py` 文件中：
- `PORT`: Web服务端口（默认6000）
- `UPLOAD_FOLDER`: 上传文件保存路径
- `MODEL_CONFIG`: 三种模型的参数配置

## ⚠️ 注意事项

1. 此为开发版本，使用Flask开发服务器
2. 单用户本地使用，不包含认证系统
3. 模型计算可能需要1-3分钟
4. 上传文件限制50MB

## 📧 技术支持

如有问题请查看：
- 原项目文档：`docs/GARCH模型回测指南.md`
- GitHub Issues

---

**版本**: 1.0  
**更新时间**: 2025-03-03
