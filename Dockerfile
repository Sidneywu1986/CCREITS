# REITs 数据平台 - Docker 镜像

FROM node:18-alpine

# 安装系统依赖
RUN apk add --no-cache sqlite

# 创建工作目录
WORKDIR /app

# 复制后端文件
COPY backend/package*.json ./backend/
RUN cd backend && npm install --production

COPY backend/ ./backend/

# 复制前端文件
COPY frontend/ ./frontend/

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 3001

# 启动命令
CMD ["node", "backend/server.js"]
