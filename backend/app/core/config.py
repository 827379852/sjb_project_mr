"""
应用配置模块 - 支持通过环境变量灵活配置
"""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 应用基础配置 ──────────────────────────────────────────────
    APP_NAME: str = "Market Research Platform"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"

    # ── 服务器配置 ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── 数据库配置 ────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./market_research.db"

    # ── AgentSociety 后端适配配置 ─────────────────────────────────
    # 支持 "agentsociety" | "mock" | "custom"
    AGENT_BACKEND: Literal["agentsociety", "mock", "custom"] = "agentsociety"

    # AgentSociety 本地运行配置
    AGENTSOCIETY_ENABLED: bool = True
    AGENTSOCIETY_MAP_PATH: str = ""           # 地图文件路径
    AGENTSOCIETY_DEFAULT_LLM: str = "gpt-4o-mini"
    AGENTSOCIETY_MAX_AGENTS: int = 100

    # AgentSociety 远程 API 配置（如果使用远端实例）
    AGENTSOCIETY_API_BASE_URL: str = ""
    AGENTSOCIETY_API_KEY: str = ""

    # ── LLM 配置 ──────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # ── Auth 配置 ─────────────────────────────────────────────────
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    ALGORITHM: str = "HS256"


settings = Settings()