@echo off
echo 正在启动百度云工具...

:: 检查是否已安装 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未安装 Python，请先安装 Python 3.8 或更高版本
    echo 您可以从 https://www.python.org/downloads/ 下载安装
    pause
    exit /b 1
)

:: 检查环境变量
if not exist "venv" (
    echo 首次运行，正在创建 Python 虚拟环境...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: 启动后端服务
start cmd /k "title 百度云工具 && venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: 等待服务启动
echo 等待服务启动...
timeout /t 3 /nobreak >nul

:: 打开浏览器
start http://localhost:8000

echo.
echo 百度云工具已启动！
echo 如果浏览器没有自动打开，请手动访问：http://localhost:8000
echo.
echo 提示：关闭命令行窗口即可停止服务
echo. 