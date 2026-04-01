"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1.endpoints import projects, questionnaires, respondents, runs, system, research_flow

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(system.router)
api_router.include_router(projects.router)
api_router.include_router(questionnaires.router)
api_router.include_router(respondents.router)
api_router.include_router(runs.router)
api_router.include_router(research_flow.router)