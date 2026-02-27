# 部署文档

本文档说明如何将会议纪要系统部署到内网服务器。

前端构建产物由 FastAPI 直接托管，无需 nginx 等额外 HTTP 服务器，整个应用只需运行一个后端进程即可对外提供服务。

## 目录

- [快速部署](#快速部署)
- [Docker 部署](#docker-部署)
- [系统服务配置](#系统服务配置)
- [备份和恢复](#备份和恢复)
- [监控和日志](#监控和日志)
- [故障排查](#故障排查)

---

## 快速部署

### 1. 服务器要求

- CPU: 2 核心以上
- 内存: 4GB 以上
- 硬盘: 20GB 可用空间
- 操作系统: Ubuntu 20.04+ / Debian 11+ / CentOS 8+

### 2. 安装基础依赖

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git
```

**CentOS/RHEL:**
```bash
sudo yum install -y python3 python3-venv python3-pip git
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 3. 获取项目代码

```bash
sudo mkdir -p /opt/meeting-minutes
sudo chown -R $USER:$USER /opt/meeting-minutes
cd /opt/meeting-minutes
git clone <your-repo-url> .
```

### 4. 构建前端

```bash
cd /opt/meeting-minutes/frontend
npm install
npm run build
```

构建完成后，`frontend/dist/` 目录包含所有静态文件，FastAPI 启动时会自动检测并托管该目录。

### 5. 部署后端

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
nano .env
```

**`.env` 配置示例：**
```env
APP_NAME=会议纪要系统
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
MAX_FILE_SIZE=524288000

# 前端静态文件目录（相对于 backend/ 运行目录，默认值即可）
# FRONTEND_DIST_DIR=../frontend/dist
```

```bash
# 创建数据目录
mkdir -p data/uploads

# 启动服务（默认监听 0.0.0.0:8001）
python -m app.main
```

启动后访问 `http://<服务器IP>:8001` 即可打开前端界面。

---

## Docker 部署

使用单个 Docker 镜像同时包含前端构建和后端服务。

### 1. 创建 Dockerfile

在项目根目录创建 `Dockerfile`：

```dockerfile
# 阶段一：构建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 阶段二：后端运行环境
FROM python:3.11-slim

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# 将前端构建产物复制到后端可读取的位置
COPY --from=frontend-builder /app/frontend/dist ../frontend/dist

RUN mkdir -p data/uploads

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "app.main"]
```

### 2. 构建并运行

```bash
# 在项目根目录执行
docker build -t meeting-minutes .

docker run -d \
  --name meeting-minutes \
  --restart unless-stopped \
  -p 8001:8001 \
  -v $(pwd)/data:/app/backend/data \
  -e DEBUG=false \
  -e LLM_API_KEY=your-api-key \
  -e ASR_API_URL=http://your-asr-server:8000/api/v1 \
  meeting-minutes
```

### 3. 使用 docker-compose

在项目根目录创建 `docker-compose.yml`：

```yaml
services:
  app:
    build: .
    container_name: meeting-minutes
    restart: unless-stopped
    ports:
      - "8001:8001"
    volumes:
      - ./data:/app/backend/data
    environment:
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite+aiosqlite:///./data/meetings.db
      - ASR_API_URL=${ASR_API_URL}
      - LLM_BASE_URL=${LLM_BASE_URL}
      - LLM_API_KEY=${LLM_API_KEY}
      - LLM_MODEL=${LLM_MODEL}
      - UPLOAD_DIR=./data/uploads
```

```bash
docker-compose up -d
docker-compose logs -f
```

---

## 系统服务配置

### 1. 创建 systemd 服务

创建 `/etc/systemd/system/meeting-minutes.service`：

```ini
[Unit]
Description=Meeting Minutes Service
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

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/meeting-minutes/backend/data

[Install]
WantedBy=multi-user.target
```

### 2. 启用服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable meeting-minutes
sudo systemctl start meeting-minutes

# 查看状态
sudo systemctl status meeting-minutes

# 查看日志
sudo journalctl -u meeting-minutes -f
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

cp /opt/meeting-minutes/backend/data/meetings.db $BACKUP_DIR/meetings_$DATE.db
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz -C /opt/meeting-minutes/backend/data uploads
cp /opt/meeting-minutes/backend/.env $BACKUP_DIR/env_$DATE

find $BACKUP_DIR -name "*.db" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "env_*" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/meeting-minutes/scripts/backup.sh

# 每天凌晨 2 点自动备份
crontab -e
# 添加：0 2 * * * /opt/meeting-minutes/scripts/backup.sh >> /opt/meeting-minutes/backups/backup.log 2>&1
```

### 2. 恢复备份

```bash
sudo systemctl stop meeting-minutes

cp /path/to/backup/meetings_YYYYMMDD.db /opt/meeting-minutes/backend/data/meetings.db
tar -xzf /path/to/backup/uploads_YYYYMMDD.tar.gz -C /opt/meeting-minutes/backend/data

sudo systemctl start meeting-minutes
```

---

## 监控和日志

### 查看日志

```bash
# 实时日志
sudo journalctl -u meeting-minutes -f

# 最近 100 条
sudo journalctl -u meeting-minutes -n 100
```

### 健康检查

```bash
curl http://localhost:8001/health
# 返回 {"status":"healthy"} 表示服务正常
```

---

## 故障排查

1. **服务无法启动**
   - 检查端口占用：`sudo lsof -i :8001`
   - 确认前端已构建：`ls frontend/dist/index.html`
   - 查看日志：`sudo journalctl -u meeting-minutes -n 50`

2. **页面无法访问**
   - 确认服务正在运行：`sudo systemctl status meeting-minutes`
   - 检查防火墙：`sudo ufw status`，必要时开放 8001 端口

3. **文件上传失败**
   - 检查 `UPLOAD_DIR` 权限：`ls -la backend/data/uploads`
   - 检查磁盘空间：`df -h`

4. **处理失败**
   - 检查 ASR 服务是否可达：`curl $ASR_API_URL`
   - 确认 `LLM_API_KEY` 配置正确
   - 查看日志获取详细错误信息

---

如需更多帮助，请查看 [README.md](./README.md)。
