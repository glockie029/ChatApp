#!/bin/bash

# 💡 ChatApp 一键启动脚本 (适用于重构后的模块化版本)
echo "🚀 开始启动 ChatApp (Modular Version)..."

# 获取脚本所在目录的绝对路径
ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 1. 启动后端 API 服务 (在根目录下直接启动 main:app)
echo "⏳ 正在启动后端 (Uvicorn)..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 2. 启动前端静态资源服务
echo "⏳ 正在启动前端 (Python HTTP Server)..."
cd "$ROOT_DIR/frontend" || { echo "❌ 找不到 frontend 目录"; exit 1; }
python3 -m http.server --bind 0.0.0.0 8081 &
FRONTEND_PID=$!

# 3. 打印成功消息与指引
echo ""
echo "=================================================="
echo "🌟 服务已全部启动成功！"
echo "👉 前端访问地址 (在此聊天): http://127.0.0.1:8081"
echo "👉 后端 API 地址 (Swagger): http://127.0.0.1:8000/docs"
echo "🛑 请保持此终端窗口打开。按下 [Ctrl + C] 即可一键关闭前后端服务。"
echo "=================================================="
echo ""

# 4. 捕获 Ctrl+C (SIGINT) 信号，实现一键安全关闭前后端进程
cleanup() {
    echo ""
    echo "🛑 收到停止信号，正在关闭服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "👋 服务已安全关闭"
    exit 0
}

trap cleanup SIGINT SIGTERM

# 保持主进程挂起，等待停止信号并输出后台进程的日志
wait
