"""
FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import AppException, app_exception_handler
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期钩子"""
    logger.info(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"   Agent 后端: {settings.AGENT_BACKEND}")
    await init_db()
    logger.info("✅ 数据库初始化完成")
    yield
    logger.info("👋 服务关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
## 市场调研 AI 平台 API

基于 **AgentSociety** 框架，通过 LLM Agent 模拟真实受访者进行市场调研、产品测试和用户研究。

### 核心能力
- 📋 **问卷设计**：支持单选、多选、量表、NPS、开放题等多种题型
- 👥 **受访者生成**：基于受众画像自动生成多样化 Agent 受访者
- 🤖 **AI 调研执行**：并发运行 Agent 角色扮演，完成问卷填写
- 📊 **结果分析**：自动统计分析，输出频率分布、均值、情感倾向等
- 🔄 **后端可替换**：抽象适配层设计，支持切换不同 Agent 后端

### 快速开始
1. 创建调研项目 `POST /api/v1/projects`
2. 设计问卷 `POST /api/v1/questionnaires`
3. 配置受访者 `POST /api/v1/respondent-configs`
4. 生成受访者 `POST /api/v1/respondent-configs/{id}/generate`
5. 绑定并启动调研 `POST /api/v1/runs`
6. 查看结果 `GET /api/v1/runs/{id}/analytics`
        """,
        openapi_tags=[
            {"name": "系统", "description": "健康检查与系统信息"},
            {"name": "调研项目", "description": "调研项目的增删改查"},
            {"name": "问卷设计", "description": "问卷结构设计与管理"},
            {"name": "受访者管理", "description": "受访者配置与 Agent 档案生成"},
            {"name": "调研执行", "description": "启动调研运行、监控进度、查看结果"},
        ],
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    app.add_exception_handler(AppException, app_exception_handler)

    # 注册路由
    app.include_router(api_router)

    return app


app = create_app()