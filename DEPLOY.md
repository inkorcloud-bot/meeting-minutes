# 部署文档

本文档详细说明如何部署会议纪要系统到生产环境。

## 目录

- [生产环境部署](#生产环境部署)
- [Docker 部署](#docker-部署)
- [Nginx 配置](#nginx-配置)
- [系统服务配置](#系统服务配置)
- [HTTPS 配置](#https-配置)
- [备份和恢复](#备份和恢复)
- [监控和日志](#监控和日志)

---

## 生产环境部署

### 1. 服务器要求

**最低配置：**
- CPU: 2 核心
- 内存: 4GB
- 硬盘: 20GB 可用空间
- 操作系统: Ubuntu 20.04+ / Debian 11+ / CentOS 8+

**推荐配置：**
- CPU: 4 核心
- 内存: 8GB
- 硬盘: 50GB+ SSD
- 操作系统: Ubuntu 22.04 LTS

### 2. 安装基础依赖

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm nginx git
```

**CentOS/RHEL:**
```bash
sudo yum install -y python3 python3-venv python3-pip nginx git
# Node.js 需要额外安装
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 3. 创建应用目录和用户

```bash
# 创建应用目录
sudo mkdir -p /opt/meeting-minutes
sudo chown -R $USER:$USER /opt/meeting-minutes

# 或者创建专用用户
sudo useradd -r -s /bin/false meeting-minutes
sudo mkdir -p /opt/meeting-minutes
sudo chown -R meeting-minutes:meeting-minutes /opt/meeting-minutes
```

### 4. 克隆或上传项目

```bash
cd /opt/meeting-minutes
git clone <your-repo-url> .
# 或者上传项目文件到这个目录
```

### 5. 后端部署

```bash
cd /opt/meeting-minutes/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

**生产环境 .env 配置示例：**
```env
# 后端配置
APP_NAME=Meeting Minutes System
DEBUG=false
SECRET_KEY=change-this-to-a-random-secret-key-in-production

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/meetings.db

# ASR 服务
ASR_API_URL=http://localhost:8000/api/v1

# 大模型配置
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=deepseek-chat

# 文件存储
UPLOAD_DIR=./data/uploads
MAX_FILE_SIZE=524288000  # 500MB
```

```bash
# 创建数据目录
mkdir -p data/uploads

# 测试运行
python -m app.main
```

### 6. 前端部署

```bash
cd /opt/meeting-minutes/frontend

# 安装依赖
npm install

# 修改 API 地址（如果需要）
# 编辑 vite.config.js 中的 proxy 配置

# 构建生产版本
npm run build
```

构建完成后，`dist` 目录包含了所有静态文件。

---

## Docker 部署

### 1. 创建后端 Dockerfile

在 `backend/Dockerfile` 创建：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data/uploads

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 运行应用
CMD ["python", "-m", "app.main"]
```

### 2. 创建前端 Dockerfile

在 `frontend/Dockerfile` 创建：

```dockerfile
# 构建阶段
FROM node:18-alpine as builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源码
COPY . .

# 构建应用
RUN npm run build

# 生产阶段
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
```

创建 `frontend/nginx.conf`：

```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;

    # 前端路由（SPA）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://backend:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # 超时设置（处理长音频）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 3. 创建 docker-compose.yml

在项目根目录创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: meeting-minutes-backend
    restart: unless-stopped
    environment:
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite+aiosqlite:///./data/meetings.db
      - ASR_API_URL=${ASR_API_URL}
      - LLM_BASE_URL=${LLM_BASE_URL}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=${LLM_MODEL}
      - UPLOAD_DIR=./data/uploads
    volumes:
      - backend-data:/app/data
    networks:
      - meeting-minutes
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: meeting-minutes-frontend
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend
    networks:
      - meeting-minutes

volumes:
  backend-data:
    driver: local

networks:
  meeting-minutes:
    driver: bridge
```

创建 `.env` 文件：

```env
SECRET_KEY=your-secret-key-here
ASR_API_URL=http://your-asr-server:8000/api/v1
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=deepseek-chat
```

### 4. 启动 Docker 容器

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v
```

---

## Nginx 配置

### 1. 基础配置（非 Docker 部署）

如果不使用 Docker，使用以下 Nginx 配置：

```nginx
upstream backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /opt/meeting-minutes/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # 长超时设置
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    # 静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        root /opt/meeting-minutes/frontend/dist;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json application/javascript;
}
```

### 2. 启用配置

```bash
# 创建配置文件
sudo nano /etc/nginx/sites-available/meeting-minutes

# 启用站点
sudo ln -s /etc/nginx/sites-available/meeting-minutes /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

---

## 系统服务配置

### 1. 创建 systemd 服务文件

创建 `/etc/systemd/system/meeting-minutes-backend.service`：

```ini
[Unit]
Description=Meeting Minutes Backend Service
After=network.target

[Service]
Type=simple
User=meeting-minutes
Group=meeting-minutes
WorkingDirectory=/opt/meeting-minutes/backend
Environment="PATH=/opt/meeting-minutes/backend/venv/bin"
ExecStart=/opt/meeting-minutes/backend/venv/bin/python -m app.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/meeting-minutes/backend/data

[Install]
WantedBy=multi-user.target
```

### 2. 启用和启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用服务
sudo systemctl enable meeting-minutes-backend

# 启动服务
sudo systemctl start meeting-minutes-backend

# 查看状态
sudo systemctl status meeting-minutes-backend

# 查看日志
sudo journalctl -u meeting-minutes-backend -f
```

---

## HTTPS 配置

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取并自动配置证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

Certbot 会自动更新 Nginx 配置。

### 手动 HTTPS 配置

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 其他配置同上...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 备份和恢复

### 1. 自动备份脚本

创建 `/opt/meeting-minutes/scripts/backup.sh`：

```bash
#!/bin/bash

BACKUP_DIR="/opt/meeting-minutes/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# 备份数据库
cp /opt/meeting-minutes/backend/data/meetings.db $BACKUP_DIR/meetings_$DATE.db

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/meeting-minutes/backend/data uploads

# 备份配置文件
cp /opt/meeting-minutes/backend/.env $BACKUP_DIR/env_$DATE

# 删除旧备份
find $BACKUP_DIR -name "*.db" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "env_*" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

```bash
# 设置可执行权限
chmod +x /opt/meeting-minutes/scripts/backup.sh
```

### 2. 添加定时任务

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /opt/meeting-minutes/scripts/backup.sh >> /opt/meeting-minutes/backups/backup.log 2>&1
```

### 3. 恢复备份

```bash
# 停止服务
sudo systemctl stop meeting-minutes-backend

# 恢复数据库
cp /path/to/backup/meetings_YYYYMMDD_HHMMSS.db /opt/meeting-minutes/backend/data/meetings.db

# 恢复上传文件
tar -xzf /path/to/backup/uploads_YYYYMMDD_HHMMSS.tar.gz -C /opt/meeting-minutes/backend/data

# 恢复配置（如果需要）
cp /path/to/backup/env_YYYYMMDD /opt/meeting-minutes/backend/.env

# 设置权限
sudo chown -R meeting-minutes:meeting-minutes /opt/meeting-minutes/backend/data

# 启动服务
sudo systemctl start meeting-minutes-backend
```

---

## 监控和日志

### 1. 日志管理

**查看后端日志：**
```bash
# systemd 日志
sudo journalctl -u meeting-minutes-backend -n 100 -f

# 应用日志（如果配置了文件日志）
tail -f /opt/meeting-minutes/backend/logs/app.log
```

**查看 Nginx 日志：**
```bash
# 访问日志
sudo tail -f /var/log/nginx/meeting-minutes-access.log

# 错误日志
sudo tail -f /var/log/nginx/meeting-minutes-error.log
```

### 2. 健康检查

可以配置监控系统（如 Prometheus + Grafana）监控：
- `/health` 端点
- 系统资源使用
- 磁盘空间
- 响应时间

### 3. 性能优化

**后端优化：**
- 使用 Gunicorn + Uvicorn workers
- 配置适当的 worker 数量
- 启用数据库连接池

**前端优化：**
- 启用 Gzip 压缩
- 配置静态资源缓存
- 使用 CDN

---

## 故障排查

### 常见问题

1. **后端无法启动**
   - 检查端口是否被占用：`sudo lsof -i :8001`
   - 查看日志：`sudo journalctl -u meeting-minutes-backend -n 50`
   - 检查虚拟环境和依赖

2. **502 Bad Gateway**
   - 确认后端服务正在运行
   - 检查 Nginx 配置中的 proxy_pass 地址
   - 查看 Nginx 错误日志

3. **文件上传失败**
   - 检查 `UPLOAD_DIR` 权限
   - 检查 Nginx `client_max_body_size` 设置
   - 检查磁盘空间

4. **处理失败**
   - 检查 ASR 服务是否可访问
   - 检查 LLM API Key 是否正确
   - 查看后端日志获取详细错误信息

---

## 安全建议

1. **定期更新系统和依赖**
2. **使用防火墙限制访问**
3. **启用 HTTPS**
4. **定期备份**
5. **使用强密码和安全的 Secret Key**
6. **限制文件上传类型和大小**
7. **监控日志和异常活动**
8. **考虑使用 WAF（Web 应用防火墙）**

---

如需更多帮助，请查看 [README.md](./README.md) 或提交 Issue。
