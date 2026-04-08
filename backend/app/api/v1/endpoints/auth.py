"""
认证 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import ApiResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut, Token
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
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前用户信息
    """
    return ApiResponse.ok(UserOut.model_validate(current_user))
