"""
系统健康检查 & 后端信息接口
"""
from fastapi import APIRouter
from app.core.response import ApiResponse
from app.core.config import settings
from app.adapters.factory import get_agent_backend

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check():
    """系统健康检查"""
    backend = get_agent_backend()
    backend_ok = await backend.health_check()

    return ApiResponse.ok({
        "status": "ok" if backend_ok else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "agent_backend": settings.AGENT_BACKEND,
        "backend_healthy": backend_ok,
    })


@router.get("/info", response_model=ApiResponse[dict])
async def get_info():
    """获取系统配置信息"""
    return ApiResponse.ok({
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "agent_backend": settings.AGENT_BACKEND,
        "max_agents_per_run": settings.AGENTSOCIETY_MAX_AGENTS,
    })