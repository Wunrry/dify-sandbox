#!/bin/bash

# 检查并安装依赖
if [ -f "/dependencies/python-requirements.txt" ]; then
    echo "发现依赖文件，开始安装额外依赖..."
    pip install --no-cache-dir -r /dependencies/python-requirements.txt
fi

# 启动 FastAPI 应用
exec uvicorn app.main:app --host 0.0.0.0 --port 8194