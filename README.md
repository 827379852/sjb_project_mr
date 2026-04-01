# 市场调研 AI 平台

基于 **AgentSociety** 框架的 AI 市场调研平台，通过 LLM Agent 模拟真实受访者，支持产品测试、用户研究等多种调研场景。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端（待开发）                          │
│                 React / Agent-Native UI                  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP REST API
┌───────────────────────▼─────────────────────────────────┐
│               FastAPI 后端 (Python)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  API v1     │  │  Business    │  │    Database    │  │
│  │  Endpoints  │→ │  Services    │→ │    SQLite/PG   │  │
│  └─────────────┘  └──────┬───────┘  └────────────────┘  │
│                          │                               │
│                 ┌────────▼────────┐                      │
│                 │  Adapter Layer  │  ← 核心扩展点         │
│                 └────────┬────────┘                      │
└──────────────────────────┼──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ AgentSociety │  │ Mock Backend │  │ Custom/Cloud │
│   Adapter    │  │  (开发测试)   │  │  (可扩展)    │
└──────────────┘  └──────────────┘  └──────────────┘
        │
        ▼
┌──────────────────┐
│  AgentSociety    │
│  Framework       │
│  (LLM + Ray)     │
└──────────────────┘
```

## 项目结构

```
market-research-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API 路由层
│   │   │   ├── projects.py      # 调研项目接口
│   │   │   ├── questionnaires.py # 问卷设计接口
│   │   │   ├── respondents.py   # 受访者管理接口
│   │   │   ├── runs.py          # 调研执行接口
│   │   │   └── system.py        # 健康检查
│   │   ├── adapters/            # ⭐ Agent 后端适配层
│   │   │   ├── base.py          # 抽象接口定义
│   │   │   ├── agentsociety_adapter.py  # AgentSociety 实现
│   │   │   ├── mock_adapter.py  # Mock 实现（开发测试）
│   │   │   └── factory.py       # 工厂函数
│   │   ├── core/                # 核心配置
│   │   │   ├── config.py        # 环境变量配置
│   │   │   ├── database.py      # 数据库连接
│   │   │   ├── response.py      # 统一响应格式
│   │   │   └── exceptions.py    # 异常处理
│   │   ├── models/              # ORM 数据模型
│   │   └── schemas/             # Pydantic 请求/响应模型
│   ├── .env.example             # 环境变量示例
│   ├── requirements.txt
│   └── run.py                   # 启动入口
└── docs/
    └── API_DESIGN.md            # 接口设计规范
```

## 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

**快速体验（无需 LLM API Key）**：
```bash
# 使用 Mock 后端，无需 OpenAI Key
AGENT_BACKEND=mock
```

**正式使用（接入真实 LLM）**：
```bash
AGENT_BACKEND=agentsociety
OPENAI_API_KEY=sk-your-key-here
```

### 3. 启动服务

```bash
cd backend
python run.py
```

服务启动后访问：
- **API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/api/v1/health

## 核心工作流

```
1. POST /api/v1/projects              # 创建调研项目
2. POST /api/v1/questionnaires        # 设计调研问卷
3. POST /api/v1/respondent-configs    # 配置目标受众
4. POST /api/v1/respondent-configs/{id}/generate  # 🤖 LLM 生成受访者
5. PUT  /api/v1/projects/{id}         # 绑定问卷和受访者
6. POST /api/v1/runs                  # 🚀 启动调研
7. GET  /api/v1/runs/{id}             # 轮询进度
8. GET  /api/v1/runs/{id}/analytics   # 📊 查看分析结果
```

## 扩展后端

替换 Agent 后端只需 3 步：

1. 继承 `app.adapters.base.AgentBackendAdapter`，实现接口
2. 在 `app/adapters/factory.py` 中注册
3. 修改 `AGENT_BACKEND` 环境变量

## 📚 文档

| 文档 | 说明 | 面向对象 |
|------|------|---------|
| [API_DESIGN.md](docs/API_DESIGN.md) | 接口设计规范（架构、题型、错误码） | 全员 |
| **[API_REFERENCE.md](docs/API_REFERENCE.md)** | **完整 API 集成参考（请求/响应示例、工作流）** | **前端/集成开发者** |
| **[ADAPTER_DEVELOPER_GUIDE.md](docs/ADAPTER_DEVELOPER_GUIDE.md)** | **适配器开发指南（替换 Agent 后端的完整教程）** | **后端/Agent 开发者** |

## 技术栈

- **后端框架**：FastAPI + Uvicorn
- **数据库**：SQLite (开发) / PostgreSQL (生产)
- **Agent 框架**：AgentSociety (清华 FIB Lab)
- **LLM**：OpenAI GPT-4o-mini（可替换）
- **异步**：asyncio + Ray (AgentSociety 分布式)