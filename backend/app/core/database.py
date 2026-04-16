"""
数据库初始化与连接管理
"""
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """初始化数据库表结构"""
    # 需要先导入所有模型，确保 metadata 已注册
    from app.models import user, research_project, questionnaire, respondent, research_run, study, system_config  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化超级管理员
    await _init_superuser()

    # 初始化默认系统配置
    await _init_system_configs()


async def _init_superuser() -> None:
    """初始化超级管理员账号"""
    from app.models.user import User
    from app.core.security import get_password_hash

    async with AsyncSessionLocal() as session:
        # 检查是否已存在 admin 用户
        result = await session.execute(select(User).where(User.email == "admin@qq.com"))
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            logger.info("超级管理员账号已存在")
            return

        # 创建超级管理员
        admin = User(
            email="admin@qq.com",
            name="超级管理员",
            hashed_password=get_password_hash("123456"),
            is_superuser=True,
            is_active=True,
            credits=999999,  # 超级管理员给足够的积分
        )
        session.add(admin)
        await session.commit()
        logger.info("✅ 超级管理员账号创建成功 (admin@qq.com / 123456)")


async def _init_system_configs() -> None:
    """初始化默认系统配置"""
    from app.models.system_config import SystemConfig, DEFAULT_SYSTEM_CONFIGS

    async with AsyncSessionLocal() as session:
        for config_data in DEFAULT_SYSTEM_CONFIGS:
            # 检查是否已存在
            result = await session.execute(select(SystemConfig).where(SystemConfig.key == config_data["key"]))
            existing = result.scalar_one_or_none()

            if existing:
                continue

            # 创建新配置
            config = SystemConfig(**config_data)
            session.add(config)

        await session.commit()
        logger.info("✅ 系统默认配置初始化完成")