"""
管理员 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.security import get_password_hash
from app.models.user import User, DEFAULT_CREDITS, TASK_COST_CREDITS
from app.schemas.user import UserOut, UserUpdate
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
