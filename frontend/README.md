# 会议纪要系统 - 前端

基于 React + Ant Design 的会议纪要系统前端应用。

## 技术栈

- React 18
- React Router 6
- Ant Design 5
- Axios
- Vite
- Marked (Markdown 渲染)

## 项目结构

```
frontend/
├── src/
│   ├── api/
│   │   └── index.js          # API 接口封装
│   ├── components/           # 公共组件
│   ├── pages/
│   │   ├── Upload.jsx        # 音频上传页面
│   │   ├── MeetingList.jsx   # 会议列表页面
│   │   └── MeetingDetail.jsx # 会议详情页面
│   ├── styles/
│   │   └── index.css         # 全局样式
│   ├── App.jsx               # 根组件
│   └── main.jsx              # 应用入口
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

## 功能特性

### 上传页面 (Upload.jsx)
- ✅ 拖拽上传音频文件
- ✅ 支持格式：MP3、WAV、M4A、OGG、FLAC
- ✅ 文件大小限制：500MB
- ✅ 表单验证（标题必填）
- ✅ 音频预览播放器
- ✅ 实时上传进度显示
- ✅ 预计处理时间估算
- ✅ 上传成功后自动跳转

### 会议列表 (MeetingList.jsx)
- ✅ 会议列表展示
- ✅ 实时状态更新
- ✅ 处理进度显示
- ✅ 分页功能
- ✅ 删除会议
- ✅ 自动刷新

### 会议详情 (MeetingDetail.jsx)
- ✅ 会议基本信息展示
- ✅ 处理进度跟踪
- ✅ Markdown 格式纪要渲染
- ✅ 复制纪要功能
- ✅ 原始转录查看
- ✅ 删除会议

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## API 配置

API 基础地址在 `src/api/index.js` 中配置：

```javascript
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  // ...
});
```

开发环境下，Vite 代理配置在 `vite.config.js` 中：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## License

MIT
