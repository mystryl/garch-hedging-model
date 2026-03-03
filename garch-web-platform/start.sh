#!/bin/bash
# GARCH模型套保分析Web平台启动脚本

cd "$(dirname "$0")"

# 检查依赖
if ! python -c "import flask" 2>/dev/null; then
    echo "安装依赖中..."
    pip install -r requirements_web.txt
fi

# 停止旧的Flask进程
echo "停止旧进程..."
pkill -f "python.*app.py" 2>/dev/null || true

# 启动Flask应用
echo "启动Flask应用..."
nohup python app.py > flask.log 2>&1 &
FLASK_PID=$!

echo "Flask应用已启动 (PID: $FLASK_PID)"
echo "请在浏览器中访问: http://localhost:6000"
echo ""
echo "查看日志: tail -f flask.log"
echo "停止应用: pkill -f \"python.*app.py\""
