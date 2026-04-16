"""
管理员 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.security import get_password_hash
from app.models.user import User, DEFAULT_CREDITS, TASK_COST_CREDITS
from app.models.credit_log import CreditLog
from app.models.system_config import SystemConfig
from app.schemas.user import UserOut, UserUpdate
from app.schemas.credit_log import CreditLogOut, CreditLogListResponse
from app.dependencies.auth import get_current_superuser

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/users", response_model=ApiResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    获取用户列表（仅超级管理员）
    """
    # 计算总数
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return ApiResponse.ok({
        "items": [UserOut.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/users/{user_id}", response_model=ApiResponse[UserOut])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    获取用户详情（仅超级管理员）
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return ApiResponse.ok(UserOut.model_validate(user))


@router.put("/users/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    更新用户信息（仅超级管理员）
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 不允许修改自己的 is_active 状态
    if user.id == current_user.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账号",
        )

    # 更新字段
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.credits is not None:
        user.credits = user_data.credits

    await db.flush()
    await db.refresh(user)

    return ApiResponse.ok(UserOut.model_validate(user))


@router.post("/users/{user_id}/reset-password", response_model=ApiResponse)
async def reset_user_password(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    重置用户密码为 123456（仅超级管理员）
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    user.hashed_password = get_password_hash("123456")
    await db.flush()

    return ApiResponse.ok({"message": "密码已重置为 123456"})


@router.post("/users/{user_id}/add-credits", response_model=ApiResponse[UserOut])
async def add_user_credits(
    user_id: str,
    amount: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    为用户增加积分（仅超级管理员）
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="增加的积分必须大于0",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    user.credits += amount
    await db.flush()
    await db.refresh(user)

    return ApiResponse.ok(UserOut.model_validate(user))


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    删除用户（仅超级管理员）
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 不允许删除其他超级管理员
    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除超级管理员",
        )

    await db.delete(user)
    await db.flush()

    return ApiResponse.ok({"message": "用户已删除"})


@router.get("/stats", response_model=ApiResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    获取系统统计信息（仅超级管理员）
    """
    # 总用户数
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    # 活跃用户数
    active_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar()

    # 总积分
    total_credits_result = await db.execute(select(func.sum(User.credits)))
    total_credits = total_credits_result.scalar() or 0

    return ApiResponse.ok({
        "total_users": total_users,
        "active_users": active_users,
        "total_credits": total_credits,
        "default_credits": DEFAULT_CREDITS,
        "task_cost_credits": TASK_COST_CREDITS,
    })


@router.get("/credit-logs", response_model=ApiResponse)
async def list_credit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str | None = Query(None, description="用户ID筛选"),
    log_type: str | None = Query(None, description="日志类型筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """
    获取积分记录列表（仅超级管理员）
    """
    # 构建查询条件
    query = select(CreditLog)
    count_query = select(func.count(CreditLog.id))

    if user_id:
        query = query.where(CreditLog.user_id == user_id)
        count_query = count_query.where(CreditLog.user_id == user_id)

    if log_type:
        query = query.where(CreditLog.log_type == log_type)
        count_query = count_query.where(CreditLog.log_type == log_type)

    # 计算总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(desc(CreditLog.created_at)).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()

    # 获取用户信息
    items = []
    for log in logs:
        user_result = await db.execute(select(User).where(User.id == log.user_id))
        user = user_result.scalar_one_or_none()
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": user.email if user else None,
            "user_name": user.name if user else None,
            "amount": log.amount,
            "balance_after": log.balance_after,
            "log_type": log.log_type,
            "description": log.description,
            "related_study_id": log.related_study_id,
            "created_at": log.created_at,
        }
        items.append(CreditLogOut(**log_dict))

    return ApiResponse.ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


# ── 系统配置管理 ─────────────────────────────────────────────────────

class SystemConfigUpdate(BaseModel):
    """系统配置更新请求"""
    value: str
    description: Optional[str] = None


class SystemConfigOut(BaseModel):
    """系统配置输出"""
    id: str
    key: str
    value: str
    description: str
    config_type: str
    updated_at: str


@router.get("/system-configs", response_model=ApiResponse)
async def list_system_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """获取所有系统配置"""
    result = await db.execute(select(SystemConfig).order_by(SystemConfig.key))
    configs = result.scalars().all()

    return ApiResponse.ok([SystemConfigOut(
        id=c.id,
        key=c.key,
        value=c.value,
        description=c.description or "",
        config_type=c.config_type,
        updated_at=c.updated_at.isoformat() if c.updated_at else "",
    ) for c in configs])


@router.put("/system-configs/{key}", response_model=ApiResponse)
async def update_system_config(
    key: str,
    data: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """更新系统配置"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()

    if not config:
        # 创建新配置
        config = SystemConfig(key=key, value=data.value, description=data.description or "")
        db.add(config)
    else:
        config.value = data.value
        if data.description is not None:
            config.description = data.description

    await db.flush()
    await db.refresh(config)

    # 如果更新的是最大并行用户数，同步更新任务队列
    if key == "max_concurrent_users":
        try:
            from app.services.task_queue import task_queue
            await task_queue.update_max_concurrent(int(data.value))
        except Exception as e:
            # 如果任务队列还未初始化，忽略错误
            pass

    return ApiResponse.ok(SystemConfigOut(
        id=config.id,
        key=config.key,
        value=config.value,
        description=config.description or "",
        config_type=config.config_type,
        updated_at=config.updated_at.isoformat() if config.updated_at else "",
    ))


# ── 队列状态查看 ─────────────────────────────────────────────────────

@router.get("/queue-status", response_model=ApiResponse)
async def get_queue_status(
    current_user: User = Depends(get_current_superuser),
):
    """获取任务队列状态"""
    try:
        from app.services.task_queue import task_queue
        return ApiResponse.ok(task_queue.get_queue_status())
    except Exception as e:
        return ApiResponse.ok({
            'max_concurrent': 4,
            'queued': 0,
            'running': 0,
            'total_tasks': 0,
            'error': str(e),
        })
