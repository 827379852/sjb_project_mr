from __future__ import annotations
"""
Agent 后端适配器抽象接口
=============================

所有 Agent 后端（agentsociety / mock / custom）都必须实现此接口。
上层业务逻辑只依赖此接口，实现后端的无缝切换。

替换后端只需：
1. 实现 AgentBackendAdapter 中的所有抽象方法
2. 在 get_agent_backend() 工厂函数中注册新实现
3. 修改 AGENT_BACKEND 环境变量
"""
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentProfile:
    """受访者 Agent 档案"""
    agent_id: str
    name: str
    profile: dict


@dataclass
class SurveyResult:
    """单个 Agent 的问卷回答结果"""
    agent_id: str
    answers: dict       # {question_id: answer_value}
    raw_dialog: list    # 原始对话记录
    sentiment: str      # positive | neutral | negative


@dataclass
class ExperimentStatus:
    """实验运行状态"""
    experiment_id: str
    status: str          # pending | running | completed | failed
    progress: int        # 0-100
    total: int
    completed: int
    input_tokens: int
    output_tokens: int
    error: str = ""


class AgentBackendAdapter(ABC):
    """Agent 后端适配器抽象基类"""

    # ── 受访者生成 ────────────────────────────────────────────────

    @abstractmethod
    async def generate_respondents(
        self,
        persona_description: str,
        demographics: dict,
        count: int,
    ) -> list[AgentProfile]:
        """
        根据受众画像描述批量生成受访者 Agent 档案。

        Args:
            persona_description: 自然语言描述的受众画像
            demographics: 结构化人口统计约束
            count: 需要生成的受访者数量

        Returns:
            生成的 AgentProfile 列表
        """
        ...

    # ── 实验生命周期 ──────────────────────────────────────────────

    @abstractmethod
    async def create_experiment(
        self,
        project_id: str,
        agents: list[AgentProfile],
        questionnaire_schema: dict,
        config: dict,
    ) -> str:
        """
        创建并注册一个调研实验。

        Returns:
            后端实验 ID (backend_experiment_id)
        """
        ...

    @abstractmethod
    async def start_experiment(self, experiment_id: str) -> bool:
        """启动实验"""
        ...

    @abstractmethod
    async def stop_experiment(self, experiment_id: str) -> bool:
        """停止/取消实验"""
        ...

    @abstractmethod
    async def get_experiment_status(self, experiment_id: str) -> ExperimentStatus:
        """获取实验当前状态"""
        ...

    # ── 数据收集 ──────────────────────────────────────────────────

    @abstractmethod
    async def collect_survey_results(
        self,
        experiment_id: str,
    ) -> list[SurveyResult]:
        """
        从已完成的实验中收集所有受访者的问卷回答。

        Returns:
            每个受访者的 SurveyResult 列表
        """
        ...

    @abstractmethod
    async def get_agent_dialog(
        self,
        experiment_id: str,
        agent_id: str,
    ) -> list[dict]:
        """获取指定 Agent 的完整对话历史"""
        ...

    # ── 辅助功能 ──────────────────────────────────────────────────

    @abstractmethod
    async def health_check(self) -> bool:
        """后端健康检查"""
        ...