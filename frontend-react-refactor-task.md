# Meeting Minutes 前端 React 重构任务书

## 项目概述

将现有的 Vue 3 + Element Plus 前端项目重构为 **React + TypeScript + Ant Design** 项目，保持所有功能不变。

**核心要求：**
- ✅ 全面使用 TypeScript
- ✅ 严格类型检查，避免使用 `any` 类型
- ✅ 类型安全优先，防止运行时错误

---

## 当前技术栈

| 层级 | 技术 |
|------|------|
| 框架 | Vue 3 |
| UI 库 | Element Plus |
| 路由 | Vue Router 4 |
| HTTP | Axios (已替换为原生 fetch) |
| 构建工具 | Vite |

---

## 目标技术栈

| 层级 | 技术 |
|------|------|
| 框架 | React 18+ |
| 语言 | TypeScript 5+ (严格模式) |
| UI 库 | Ant Design 5+ |
| 路由 | React Router v6 |
| HTTP | 原生 fetch (保持现有 API 封装逻辑，完全 TypeScript 化) |
| 状态管理 | React Context API (轻量级) |
| Markdown 渲染 | react-markdown |
| 构建工具 | Vite |
| 类型检查 | tsconfig.json strict: true, noImplicitAny: true |

---

## 项目功能清单

### 1. 页面路由
| 路径 | 组件 | 功能 |
|------|------|------|
| `/` | 重定向 | 重定向到 `/meetings` |
| `/upload` | UploadPage | 上传会议音频 |
| `/meetings` | MeetingListPage | 会议列表 |
| `/meetings/:id` | MeetingDetailPage | 会议详情/纪要 |

### 2. 核心功能
- ✅ 音频文件上传（支持进度显示）
- ✅ 会议列表展示（状态过滤）
- ✅ 会议详情查看
- ✅ 会议纪要 Markdown 渲染
- ✅ 实时状态轮询（处理中 → 完成）
- ✅ 重新生成纪要（SSE 流式输出）
- ✅ 删除会议
- ✅ 统一错误处理和用户提示

---

## 重构任务分解

### 阶段一：项目初始化
- [ ] 创建新的 React + TypeScript 项目结构（`frontend-react/` 或重写现有 `frontend/`）
- [ ] 安装依赖：React、React DOM、@types/react、@types/react-dom、React Router、Ant Design、react-markdown、@types/react-markdown
- [ ] 配置 Vite + React + TypeScript 插件
- [ ] 配置 `tsconfig.json`（strict: true, noImplicitAny: true, noUnusedLocals: true 等）
- [ ] 配置路径别名、环境变量（TypeScript 类型化）
- [ ] 迁移 `.env.example` 并添加类型定义 `env.d.ts`
- [ ] 定义项目类型文件 `src/types/index.ts`（Meeting、API 响应等核心类型）

### 阶段二：基础架构
- [ ] 迁移并 TypeScript 化 API 层（`src/api/index.js` → `src/api/index.ts`）
  - 保持现有逻辑，完全 TypeScript 化
  - 为所有函数、参数、返回值添加类型定义
  - 定义 API 响应类型接口
  - 保留 `ApiError`、`NetworkError`、错误处理（类型化）
- [ ] 配置 Ant Design 主题（可选）
- [ ] 设置 React Router 路由结构（类型化路由参数）
- [ ] 创建基础布局组件（Layout、Header、Sidebar 等，TypeScript 化）

### 阶段三：组件迁移

#### 3.1 上传页面 (`/upload`)
- [ ] 迁移 `Upload.vue` → `UploadPage.tsx`
- [ ] 使用 Ant Design `Upload` / `Form` 组件（类型化表单字段）
- [ ] 实现上传进度条（类型化进度状态）
- [ ] 表单验证（标题必填，TypeScript 化验证规则）

#### 3.2 会议列表页面 (`/meetings`)
- [ ] 迁移 `MeetingList.vue` → `MeetingListPage.tsx`
- [ ] 使用 Ant Design `Table`、`Tag`、`Button` 组件（类型化表格列、数据）
- [ ] 实现状态过滤下拉框（类型化状态枚举）
- [ ] 实现删除确认对话框（类型化对话框状态）
- [ ] 表格操作列（查看、删除，类型化回调函数）

#### 3.3 会议详情页面 (`/meetings/:id`)
- [ ] 迁移 `MeetingDetail.vue` → `MeetingDetailPage.tsx`
- [ ] 使用 Ant Design `Card`、`Descriptions`、`Spin`、`Alert`（类型化 props）
- [ ] 集成 `react-markdown` 渲染纪要（类型化内容）
- [ ] 实现状态轮询（处理中时，类型化轮询状态）
- [ ] 实现重新生成纪要功能（SSE 流式渲染，类型化 onChunk 回调）
- [ ] 实现删除功能（类型化确认状态）

### 阶段四： polish & 测试
- [ ] 统一 Loading / Error 状态处理
- [ ] 响应式适配
- [ ] 端到端功能测试
- [ ] 代码整理与注释

---

## 目录结构建议

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example
├── env.d.ts                  # 环境变量类型定义
└── src/
    ├── main.tsx               # 入口
    ├── App.tsx                # 根组件
    ├── types/
    │   └── index.ts           # 全局类型定义（Meeting、API 响应等）
    ├── router/
    │   └── index.tsx          # 路由配置（类型化）
    ├── api/
    │   └── index.ts           # API 层（完全 TypeScript 化）
    ├── components/            # 通用组件（.tsx）
    ├── pages/
    │   ├── UploadPage.tsx
    │   ├── MeetingListPage.tsx
    │   └── MeetingDetailPage.tsx
    ├── layouts/
    │   └── MainLayout.tsx
    └── styles/
        └── index.css
```

---

## 后端兼容处理（单页应用路由）

**后端已具备 SPA 路由支持**，无需修改：
- FastAPI 已有 `/{full_path:path}` 回退路由，所有未匹配路径返回 `index.html`
- 兼容 React Router 的 BrowserHistory 模式
- 前端构建产物仍输出到 `dist/` 目录，后端配置不变

**前端需确认：**
- 使用 `createBrowserRouter`（BrowserHistory）而非 HashRouter
- 生产环境构建的资源路径正确

---

## 注意事项

### TypeScript 严格要求
1. **零 `any` 容忍**：禁止使用 `any` 类型，必须定义明确的接口/类型
2. **严格模式**：`tsconfig.json` 启用 `strict: true`、`noImplicitAny: true`、`noUnusedLocals: true`、`noUnusedParameters: true`
3. **类型定义优先**：先定义 `src/types/index.ts` 中的核心类型，再实现逻辑
4. **Props 类型化**：所有组件 Props 必须定义接口，使用 `React.FC<Props>` 或函数参数类型注解
5. **API 响应类型化**：为所有 API 响应定义接口，避免运行时意外字段访问

### 其他
1. **API 层保持逻辑不变**：现有 API 封装逻辑已经很完善，仅做 TypeScript 化改造
2. **渐进式迁移**：可先保留 Vue 版本，新建 `frontend-react` 目录开发，验证后再替换
3. **SSE 流式输出**：注意 `regenerateMeetingSummary` 的 onChunk 回调在 React 中的状态更新（类型化）
4. **Ant Design 组件对应关系**：
   - Element Plus `el-table` → Ant Design `Table`
   - Element Plus `el-upload` → Ant Design `Upload`
   - Element Plus `el-message` → Ant Design `message`
   - Element Plus `el-dialog` → Ant Design `Modal`
5. **路由语法变化**：Vue Router `useRouter` / `useRoute` → React Router `useNavigate` / `useParams`（类型化 params）

---

## 验收标准

- [ ] 所有页面可正常访问（刷新页面不 404）
- [ ] 上传功能正常（进度条、成功/失败提示）
- [ ] 会议列表展示正常（状态过滤、删除）
- [ ] 会议详情展示正常（Markdown 渲染、状态轮询）
- [ ] 重新生成纪要功能正常（流式输出）
- [ ] 错误处理友好（网络错误、API 错误提示）
- [ ] **TypeScript 类型检查通过**：`tsc --noEmit` 无错误
- [ ] **零 `any` 类型**：代码中不出现 `any`（`eslint` 或 `tsc` 验证）
- [ ] 构建成功 `npm run build`
- [ ] SPA 路由正常：直接访问 `/meetings`、`/upload`、`/meetings/:id` 等路径可正常加载（刷新不 404）

