#!/bin/bash

# 会议纪要系统启动脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "  会议纪要系统 - 快速启动脚本"
echo "=========================================="
echo ""

# 检查是否是第一次运行
if [ ! -f "backend/.env" ]; then
    echo "首次运行检测，正在进行初始化配置..."
    echo ""
    
    # 复制环境变量示例文件
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo "✅ 已创建 backend/.env 文件"
        echo "⚠️  请编辑 backend/.env 文件，填入你的 API 密钥等配置"
        echo ""
    fi
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p backend/data/uploads
echo "✅ 目录已就绪"
echo ""

# 后端设置
echo "=========================================="
echo "  后端设置"
echo "=========================================="

cd backend

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3 -m venv venv
    echo "✅ 虚拟环境已创建"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "检查 Python 依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Python 依赖已就绪"
echo ""

# 返回项目根目录
cd ..

# 前端设置
echo "=========================================="
echo "  前端设置"
echo "=========================================="

cd frontend

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "node_modules 不存在，正在安装依赖..."
    npm install
    echo "✅ 前端依赖已安装"
fi

echo ""
echo "=========================================="
echo "  启动服务"
echo "=========================================="
echo ""
echo "📋 使用说明："
echo ""
echo "1. 后端服务需要在一个终端中运行："
echo "   cd backend && source venv/bin/activate && python -m app.main"
echo ""
echo "2. 前端服务需要在另一个终端中运行："
echo "   cd frontend && npm run dev"
echo ""
echo "3. 访问地址："
echo "   - 前端界面: http://localhost:3000"
echo "   - 后端 API: http://localhost:8001"
echo "   - API 文档: http://localhost:8001/docs"
echo ""
echo "⚠️  请确保已编辑 backend/.env 文件并填入正确的配置！"
echo ""
