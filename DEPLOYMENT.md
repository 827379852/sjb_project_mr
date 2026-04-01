# 市场调研 AI 平台 - Vercel 部署指南

## 部署前准备

### 1. Vercel 账户
如果还没有，请先注册: https://vercel.com

### 2. 连接 Git 仓库
- 将项目推送到 GitHub/GitLab/Bitbucket
- 在 Vercel Dashboard 中链接仓库

### 3. 环境变量配置

在 Vercel 项目设置中，添加以下环境变量：

```
APP_ENV=production
DEBUG=false
SECRET_KEY=<生成一个强密钥>

AGENT_BACKEND=agentsociety
OPENAI_API_KEY=sk-<你的 API Key>
OPENAI_API_BASE=https://api.openai.com/v1
AGENTSOCIETY_DEFAULT_LLM=gpt-4o-mini

DATABASE_URL=sqlite+aiosqlite:///./market_research.db
```

**注意**：Vercel Serverless 函数有限制，SQLite 数据库不会持久化。建议：
- 开发/测试：使用本地 SQLite
- 生产：改用 PostgreSQL 等云数据库

### 4. 部署方式（选择其一）

#### A. GitHub 集成部署（推荐）
1. 推送代码到 GitHub
2. 在 Vercel Dashboard 点击 "New Project"
3. 连接 GitHub 仓库
4. 自动识别 vercel.json 配置
5. 配置环境变量
6. 点击 "Deploy"

#### B. CLI 部署
```bash
npm i -g vercel
vercel login
cd market-research-platform
vercel --prod
```

## 部署架构

```
前端 (Frontend)
├── 静态 HTML/CSS/JS
└── Vercel Static Hosting

后端 (Backend)
├── FastAPI 应用
├── api/index.py (ASGI 入口)
└── Vercel Serverless Functions

API 路由
├── /api/v1/* → backend/api/index.py
└── /* → frontend/index.html
```

## 关键配置文件

### vercel.json
- 定义构建和路由规则
- Python 运行时版本：3.11

### backend/api/index.py
- Vercel Serverless 入口
- 导出 FastAPI app 对象

### backend/requirements.txt
- Python 依赖列表
- Vercel 自动安装

### .vercelignore
- 排除不需要部署的文件

## 部署后

1. **访问应用**
   - Vercel 会自动分配域名，如 `xxx.vercel.app`
   - 前端自动识别生产环境，API 使用相对路径 `/api/v1`

2. **查看日志**
   - Vercel Dashboard → Function Logs
   - 查看后端错误信息

3. **自定义域名**
   - Vercel Dashboard → Settings → Domains
   - 连接你自己的域名

## 注意事项

### 冷启动
- Vercel Serverless 首次请求会有 1-3 秒冷启动延迟
- 后续请求更快

### 数据持久化
- SQLite 数据库（`market_research.db`）存储在短期文件系统
- 容器重启后数据丢失
- **建议迁移到 PostgreSQL/MongoDB 等云数据库**

### 超时限制
- Vercel 免费：12 秒超时
- 付费：900 秒超时
- 长时间 LLM 调用可能需要调整

### CORS
- 后端已配置 CORS，允许跨域请求
- 生产环境建议更新 `ALLOWED_ORIGINS` 只允许特定域名

## 本地测试（部署前）

```bash
# 后端
cd backend
pip install -r requirements.txt
python run.py

# 前端（新终端）
cd frontend
python -m http.server 3000

# 访问 http://localhost:3000
```

## 问题排查

1. **502 Bad Gateway**
   - 检查环境变量是否正确
   - 查看函数日志

2. **CORS 错误**
   - 检查后端 CORS 配置
   - 确保 ALLOWED_ORIGINS 包含生产域名

3. **API 超时**
   - LLM 调用超过 Vercel 限制
   - 考虑使用任务队列（如 Bull、Celery）

## 升级建议

- [ ] 数据库迁移到 PostgreSQL
- [ ] 添加 Redis 缓存
- [ ] 分离后端到独立服务
- [ ] 添加 CDN 加速前端
- [ ] 配置 GitHub Actions CI/CD

## 联系支持
- 文档：docs/
- 问题反馈：[GitHub Issues]