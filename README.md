# 会议纪要自动化系统

基于 FireRedASR2S 和大模型的会议纪要自动化系统，实现音频上传、语音识别、智能摘要生成的完整流程。

## 功能特性

- 🎤 **音频上传** - 支持 MP3、WAV、M4A、OGG、FLAC 等常见音频格式
- 📝 **ASR 转录** - 基于 FireRedASR2S 的高精度语音识别
- 🤖 **AI 摘要生成** - 基于大模型的智能会议内容总结
- 📋 **结构化纪要** - 自动提取会议议题、决议、行动项
- 📊 **会议管理** - 会议列表、详情查看、进度追踪
- 💾 **数据持久化** - SQLite 数据库存储，无需额外服务
- ⚡ **异步处理** - 后台任务处理，实时进度反馈

## 技术栈

### 后端
- **FastAPI** - 高性能异步 Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **SQLite** - 轻量级数据库
- **httpx** - 异步 HTTP 客户端
- **openai** - OpenAI 兼容 API 客户端

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - Vue 3 组件库
- **Axios** - HTTP 请求库

### 外部服务
- **FireRedASR2S** - 语音识别服务
- **OpenAI 兼容 API** - 大模型服务（DeepSeek、智谱等）

## 项目结构

```
meeting-minutes/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── core/           # 核心配置和客户端
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── tasks/          # 异步任务
│   │   └── main.py         # 应用入口
│   ├── requirements.txt    # Python 依赖
│   └── .env.example        # 环境变量示例
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── api/            # API 封装
│   │   └── App.vue
│   └── package.json
└── README.md               # 本文档
```

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 16+
- FireRedASR2S 服务（可访问）
- OpenAI 兼容 API Key

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd meeting-minutes
```

2. **后端配置**
```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

3. **前端配置**
```bash
cd frontend

# 安装依赖
npm install
```

### 配置说明

编辑 `backend/.env` 文件：

```env
# 后端配置
APP_NAME=Meeting Minutes System
DEBUG=true
SECRET_KEY=your-secret-key-here

# 数据库
DATABASE_URL=sqlite:///./meetings.db

# ASR 服务
ASR_API_URL=http://localhost:8000/api/v1

# 大模型配置
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=deepseek-chat

# 文件存储
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=524288000  # 500MB
```

## 后端部署

### 依赖安装

```bash
cd backend
pip install -r requirements.txt
```

### 环境配置

1. 复制环境变量示例文件
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入实际配置

### 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务启动后，访问 http://localhost:8000/docs 查看 API 文档。

## 前端部署

### 依赖安装

```bash
cd frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:5173 查看应用。

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

## API 文档

### 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **文档地址**: http://localhost:8000/docs

### 主要接口

#### 1. 上传音频

```http
POST /api/v1/meetings/upload
Content-Type: multipart/form-data

Request:
- audio: 文件
- title: 会议标题
- date: 会议日期（可选）
- participants: 参会人员（可选）

Response:
{
  "code": 0,
  "data": {
    "meeting_id": "uuid",
    "status": "uploaded"
  }
}
```

#### 2. 查询状态

```http
GET /api/v1/meetings/{meeting_id}/status

Response:
{
  "code": 0,
  "data": {
    "meeting_id": "uuid",
    "status": "processing",
    "progress": 45,
    "current_step": "transcribing",
    "error": null
  }
}
```

#### 3. 获取会议详情

```http
GET /api/v1/meetings/{meeting_id}

Response:
{
  "code": 0,
  "data": {
    "id": "uuid",
    "title": "会议标题",
    "status": "completed",
    "transcript": "原始转录文本",
    "summary": "生成的纪要（Markdown）",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

#### 4. 会议列表

```http
GET /api/v1/meetings?page=1&page_size=10

Response:
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 10
  }
}
```

## 使用说明

### 1. 上传会议音频

1. 访问前端页面
2. 点击"上传音频"按钮
3. 填写会议标题、日期、参会人员等信息
4. 选择音频文件并上传
5. 系统会自动开始处理

### 2. 查看处理进度

- 上传后会自动跳转到进度页面
- 实时显示当前处理步骤和进度百分比
- 状态包括：上传成功 → 处理中 → 转录中 → 摘要生成中 → 完成

### 3. 查看会议纪要

- 处理完成后，点击"查看详情"
- 可以看到完整的会议纪要，包括：
  - 会议基本信息
  - 会议议题
  - 关键讨论点
  - 会议决议
  - 行动项表格
  - 会议总结

### 4. 管理会议

- 在会议列表页面可以查看所有历史会议
- 支持按时间、状态筛选
- 点击任意会议可查看详情

## 常见问题

### ASR 服务无法访问

请检查：
1. FireRedASR2S 服务是否已启动
2. `.env` 中的 `ASR_API_URL` 是否正确
3. 网络连接是否正常

### 大模型 API 调用失败

请检查：
1. API Key 是否正确
2. Base URL 是否配置正确
3. 账户是否有足够的额度

### 音频文件上传失败

请检查：
1. 文件大小是否超过 500MB
2. 文件格式是否支持（MP3、WAV、M4A、OGG、FLAC）
3. `UPLOAD_DIR` 目录是否有写入权限

## 开发计划

- [ ] 支持纪要导出为 PDF/Word
- [ ] 实时流式转录（WebSocket）
- [ ] 多语言支持
- [ ] 会议录像处理（视频 + 音频）
- [ ] 智能问答（基于会议内容）
- [ ] 说话人分离

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
