# 百度云工具

一个用于分析百度网盘数据的工具，可以帮助你可视化查看文件夹大小分布、快速浏览文件结构、分析存储空间占用等。

## 运行环境要求

- Python 3.8 或更高版本
- Windows 操作系统

## 快速开始

1. 下载并解压本工具
2. 双击运行 `start.bat`
3. 等待程序自动安装依赖并启动
4. 浏览器会自动打开工具页面

## 使用方法

1. 找到百度网盘的缓存数据库文件：
   - 在百度网盘快捷方式上右键，选择"打开文件位置"
   - 找到并进入类似这样的目录：`C:\Users\[用户名]\AppData\Roaming\baidu\BaiduYunGuanjia\users`
   - 找到 `BaiduYunCacheFileV0.db` 文件

2. 使用工具：
   - 点击"上传数据库"按钮，选择找到的数据库文件
   - 等待文件分析完成
   - 使用左侧文件树浏览目录结构
   - 使用右侧标签页查看文件分析结果

## 注意事项

- 首次运行时会自动安装必要的依赖，可能需要等待一段时间
- 如果浏览器没有自动打开，请手动访问：http://localhost:8000
- 关闭命令行窗口即可停止服务
- 确保数据库文件不在使用中（百度网盘客户端已关闭）

## 常见问题

1. 如果提示未安装 Python：
   - 访问 https://www.python.org/downloads/ 下载安装 Python 3.8 或更高版本
   - 安装时勾选"Add Python to PATH"选项

2. 如果启动失败：
   - 检查 Python 是否正确安装
   - 检查是否有其他程序占用了 8000 端口
   - 尝试以管理员身份运行 start.bat

通过以下命令启动项目：
# 启动前端开发服务器
npm run dev

# 在另一个终端启动后端服务器
cd ../../backend
uvicorn app.main:app --reload
主要文件结构：
frontend/
  ├── src/
  │   ├── views/
  │   │   └── HomeView.vue      # 主页面组件
  │   ├── types/
  │   │   └── index.ts          # TypeScript 类型定义
  │   ├── router/
  │   │   └── index.ts          # 路由配置
  │   ├── App.vue               # 根组件
  │   └── main.ts               # 入口文件
  ├── package.json              # 项目配置和依赖
  ├── tsconfig.json            # TypeScript 配置
  └── vite.config.ts           # Vite 配置

backend/
├── run.py                 # 入口文件
├── requirements.txt       # 依赖文件
└── app/
    ├── __init__.py       # 使app成为包
    ├── main.py           # FastAPI应用
    ├── api/
    │   ├── __init__.py
    │   └── endpoints.py
    ├── core/
    │   ├── __init__.py
    │   └── config.py
    ├── db/
    │   ├── __init__.py
    │   └── database.py
    ├── models/
    │   └── __init__.py
    └── schemas/
        └── __init__.py