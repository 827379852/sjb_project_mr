"""
调研项目管理接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.core.database import get_db
from app.core.response import ApiResponse, PaginatedData
from app.core.exceptions import NotFoundError
from app.models.research_project import ResearchProject, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/projects", tags=["调研项目"])


@router.get("", response_model=ApiResponse[PaginatedData[ProjectOut]])
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[ProjectStatus] = Query(None, description="按状态筛选"),
    keyword: Optional[str] = Query(None, description="按名称关键词搜索"),
    db: AsyncSession = Depends(get_db),
):
    """获取调研项目列表"""
    query = select(ResearchProject).order_by(ResearchProject.created_at.desc())

    if status:
        query = query.where(ResearchProject.status == status)
    if keyword:
        query = query.where(ResearchProject.name.contains(keyword))

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()

    return ApiResponse.ok(PaginatedData.build(
        items=[ProjectOut.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    ))


@router.post("", response_model=ApiResponse[ProjectOut], status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建调研项目"""
    project = ResearchProject(**payload.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return ApiResponse.ok(ProjectOut.model_validate(project), message="项目创建成功")


@router.get("/{project_id}", response_model=ApiResponse[ProjectOut])
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """获取项目详情"""
    project = await db.get(ResearchProject, project_id)
    if not project:
        raise NotFoundError("调研项目", project_id)
    return ApiResponse.ok(ProjectOut.model_validate(project))


@router.put("/{project_id}", response_model=ApiResponse[ProjectOut])
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目信息"""
    project = await db.get(ResearchProject, project_id)
    if not project:
        raise NotFoundError("调研项目", project_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)
    return ApiResponse.ok(ProjectOut.model_validate(project))


@router.delete("/{project_id}", response_model=ApiResponse[None])
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """删除项目"""
    project = await db.get(ResearchProject, project_id)
    if not project:
        raise NotFoundError("调研项目", project_id)
    await db.delete(project)
    return ApiResponse.ok(message="项目已删除")