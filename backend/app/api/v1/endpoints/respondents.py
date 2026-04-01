"""
受访者管理接口
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.response import ApiResponse, PaginatedData
from app.core.exceptions import NotFoundError
from app.models.respondent import RespondentConfig, Respondent
from app.schemas.respondent import (
    RespondentConfigCreate, RespondentConfigUpdate, RespondentConfigOut, RespondentOut
)
from app.adapters.factory import get_agent_backend

router = APIRouter(prefix="/respondent-configs", tags=["受访者管理"])


# ── 受访者配置 ─────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse[PaginatedData[RespondentConfigOut]])
async def list_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取受访者配置列表"""
    query = select(RespondentConfig).order_by(RespondentConfig.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    items = (await db.execute(query.offset((page-1)*page_size).limit(page_size))).scalars().all()

    return ApiResponse.ok(PaginatedData.build(
        items=[RespondentConfigOut.model_validate(c) for c in items],
        total=total, page=page, page_size=page_size,
    ))


@router.post("", response_model=ApiResponse[RespondentConfigOut], status_code=201)
async def create_config(payload: RespondentConfigCreate, db: AsyncSession = Depends(get_db)):
    """创建受访者配置"""
    data = payload.model_dump()
    if hasattr(data.get("demographics"), "model_dump"):
        data["demographics"] = data["demographics"].model_dump()

    config = RespondentConfig(**data)
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return ApiResponse.ok(RespondentConfigOut.model_validate(config))


@router.get("/{config_id}", response_model=ApiResponse[RespondentConfigOut])
async def get_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """获取受访者配置详情"""
    config = await db.get(RespondentConfig, config_id)
    if not config:
        raise NotFoundError("受访者配置", config_id)
    return ApiResponse.ok(RespondentConfigOut.model_validate(config))


@router.put("/{config_id}", response_model=ApiResponse[RespondentConfigOut])
async def update_config(
    config_id: str,
    payload: RespondentConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新受访者配置"""
    config = await db.get(RespondentConfig, config_id)
    if not config:
        raise NotFoundError("受访者配置", config_id)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(config, field, value.model_dump() if hasattr(value, "model_dump") else value)

    await db.flush()
    await db.refresh(config)
    return ApiResponse.ok(RespondentConfigOut.model_validate(config))


@router.delete("/{config_id}", response_model=ApiResponse[None])
async def delete_config(config_id: str, db: AsyncSession = Depends(get_db)):
    """删除受访者配置"""
    config = await db.get(RespondentConfig, config_id)
    if not config:
        raise NotFoundError("受访者配置", config_id)
    await db.delete(config)
    return ApiResponse.ok(message="配置已删除")


# ── 受访者 Agent 生成与管理 ────────────────────────────────────────

@router.post("/{config_id}/generate", response_model=ApiResponse[list[RespondentOut]])
async def generate_respondents(
    config_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    根据配置生成受访者 Agent 档案（调用 LLM 生成多样化人物设定）。
    如已存在受访者，先清除再重新生成。
    """
    config = await db.get(RespondentConfig, config_id)
    if not config:
        raise NotFoundError("受访者配置", config_id)

    # 清除旧受访者
    old_respondents = (await db.execute(
        select(Respondent).where(Respondent.config_id == config_id)
    )).scalars().all()
    for r in old_respondents:
        await db.delete(r)

    # 通过 Agent 后端生成受访者
    backend = get_agent_backend()
    profiles = await backend.generate_respondents(
        persona_description=config.persona_description,
        demographics=config.demographics or {},
        count=config.count,
    )

    # 持久化到数据库
    respondents = []
    for p in profiles:
        r = Respondent(
            config_id=config_id,
            name=p.name,
            profile=p.profile,
            agent_backend_id=p.agent_id,
        )
        db.add(r)
        respondents.append(r)

    await db.flush()
    for r in respondents:
        await db.refresh(r)

    return ApiResponse.ok(
        [RespondentOut.model_validate(r) for r in respondents],
        message=f"成功生成 {len(respondents)} 位受访者"
    )


@router.get("/{config_id}/respondents", response_model=ApiResponse[list[RespondentOut]])
async def list_respondents(config_id: str, db: AsyncSession = Depends(get_db)):
    """获取配置下所有受访者列表"""
    config = await db.get(RespondentConfig, config_id)
    if not config:
        raise NotFoundError("受访者配置", config_id)

    respondents = (await db.execute(
        select(Respondent).where(Respondent.config_id == config_id)
    )).scalars().all()

    return ApiResponse.ok([RespondentOut.model_validate(r) for r in respondents])