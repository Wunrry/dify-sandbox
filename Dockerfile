FROM python:3.12-slim-bookworm

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装基础依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码和启动脚本
COPY app/ ./app/
COPY start.sh .

# 创建依赖目录
RUN mkdir -p /dependencies

# 设置启动脚本权限
RUN chmod +x start.sh

# 暴露端口
EXPOSE 8194

# 使用启动脚本替代直接的 uvicorn 命令
CMD ["./start.sh"]