"""
认证 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, generate_api_key
from app.models.credit_log import CreditLog
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
from app.schemas.credit_log import CreditLogOut
from app.dependencies.auth import get_current_active_user

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[UserOut])
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    用户注册
    """
    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册",
        )

    # 创建新用户
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        name=user_data.name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return ApiResponse.ok(UserOut.model_validate(user))


@router.post("/login", response_model=ApiResponse[Token])
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录，返回 JWT Token
    """
    # 查找用户
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 创建访问令牌
    access_token = create_access_token(data={"sub": user.id})

    return ApiResponse.ok(Token(access_token=access_token))


@router.get("/me", response_model=ApiResponse[UserOut])
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前用户信息
    """
    # 如果用户没有 api_key，自动生成一个
    if not current_user.api_key:
        current_user.api_key = generate_api_key()
        await db.commit()
        await db.refresh(current_user)

    return ApiResponse.ok(UserOut.model_validate(current_user))


@router.post("/reset-api-key", response_model=ApiResponse[dict])
async def reset_api_key(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    重置 API Key

    警告：重置后旧的 API Key 将立即失效
    """
    new_api_key = generate_api_key()
    current_user.api_key = new_api_key
    await db.commit()
    await db.refresh(current_user)

    return ApiResponse.ok({
        "api_key": new_api_key,
        "message": "API Key 已重置，旧 Key 已失效"
    })


@router.get("/credit-logs", response_model=ApiResponse)
async def get_my_credit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前用户的积分记录
    """
    # 构建查询条件
    query = select(CreditLog).where(CreditLog.user_id == current_user.id)
    count_query = select(func.count(CreditLog.id)).where(CreditLog.user_id == current_user.id)

    # 计算总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(desc(CreditLog.created_at)).offset(offset).limit(page_size)
    )
    logs = result.scalars().all()

    # 构建返回数据
    items = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "user_id": log.user_id,
            "user_email": current_user.email,
            "user_name": current_user.name,
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
