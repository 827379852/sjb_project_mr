"""
适配器工厂 - 根据配置选择 Agent 后端实现
"""
from functools import lru_cache
from app.adapters.base import AgentBackendAdapter
from app.core.config import settings


@lru_cache(maxsize=1)
def get_agent_backend() -> AgentBackendAdapter:
    """
    工厂函数：根据 AGENT_BACKEND 环境变量返回对应的适配器实例。

    支持的后端：
    - "agentsociety" : 使用 agentsociety 框架（默认）
    - "mock"         : Mock 后端，无需 LLM，适合开发测试
    - "custom"       : 自定义后端（在此扩展）
    """
    backend = settings.AGENT_BACKEND

    if backend == "agentsociety":
        from app.adapters.agentsociety_adapter import AgentSocietyAdapter
        return AgentSocietyAdapter()

    elif backend == "mock":
        from app.adapters.mock_adapter import MockAgentBackend
        return MockAgentBackend()

    elif backend == "custom":
        # 扩展点：在此引入自定义适配器
        raise NotImplementedError("请实现自定义 Agent 后端适配器并在此注册")

    else:
        raise ValueError(f"不支持的 AGENT_BACKEND: {backend}")