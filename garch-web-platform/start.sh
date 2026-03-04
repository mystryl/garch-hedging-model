#!/bin/bash
# GARCH模型套保分析Web平台启动脚本

cd "$(dirname "$0")"

# 检测 Python 命令
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误: 找不到 Python 命令"
    exit 1
fi

echo "使用 Python: $PYTHON_CMD"

# 检查依赖
if ! $PYTHON_CMD -c "import flask" 2>/dev/null; then
    echo "安装依赖中..."
    $PYTHON_CMD -m pip install -r requirements_web.txt
fi

# 停止旧的Flask进程
echo "停止旧进程..."
pkill -f "($PYTHON_CMD|python).*app.py" 2>/dev/null || true

# 等待进程完全停止
sleep 1

# 启动Flask应用
echo "启动Flask应用..."
nohup $PYTHON_CMD app.py > flask.log 2>&1 &
FLASK_PID=$!

echo "Flask应用已启动 (PID: $FLASK_PID)"
echo "请在浏览器中访问: http://localhost:5050"
echo ""
echo "查看日志: tail -f flask.log"
echo "停止应用: pkill -f \"($PYTHON_CMD|python).*app.py\""
