#!/bin/bash

echo "正在启动百度云工具..."

# 检查是否已安装 Python
if ! command -v python3 &> /dev/null; then
    echo "错误：未安装 Python，请先安装 Python 3.8 或更高版本"
    echo "您可以使用以下命令安装："
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-venv"
    echo "CentOS/RHEL: sudo yum install python3 python3-venv"
    exit 1
fi

# 检查环境变量
if [ ! -d "venv" ]; then
    echo "首次运行，正在创建 Python 虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 启动后端服务
echo "启动后端服务..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &

# 等待服务启动
echo "等待服务启动..."
sleep 3

# 获取本机IP地址
IP_ADDRESS=$(hostname -I | awk '{print $1}')

# 打开浏览器（如果可能）
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8000" &
elif command -v gnome-open &> /dev/null; then
    gnome-open "http://localhost:8000" &
fi

echo ""
echo "百度云工具已启动！"
echo "请访问：http://localhost:8000"
echo "或者：http://$IP_ADDRESS:8000"
echo ""
echo "提示："
echo "1. 查看日志：tail -f app.log"
echo "2. 停止服务：pkill -f 'uvicorn app.main:app'"
echo "" 