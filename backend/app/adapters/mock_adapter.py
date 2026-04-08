from __future__ import annotations
"""
Mock 后端适配器（用于开发/测试，无需 LLM 配置）
"""
import asyncio
import random
from loguru import logger

from app.adapters.base import AgentBackendAdapter, AgentProfile, SurveyResult, ExperimentStatus


MOCK_NAMES = ["张伟", "李娜", "王芳", "刘洋", "陈静", "赵磊", "周婷", "吴刚", "孙雪", "郑明"]
MOCK_OCCUPATIONS = ["产品经理", "软件工程师", "市场专员", "教师", "医生", "设计师", "销售经理", "学生", "创业者", "自由职业"]
MOCK_CITIES = ["北京", "上海", "深圳", "广州", "杭州", "成都", "武汉", "西安", "南京", "重庆"]


class MockAgentBackend(AgentBackendAdapter):
    """Mock 后端：快速返回模拟数据，用于前端开发和接口调试"""

    def __init__(self):
        self._experiments: dict[str, dict] = {}

    async def generate_respondents(self, persona_description: str, demographics: dict, count: int) -> list[AgentProfile]:
        await asyncio.sleep(0.1)  # 模拟网络延迟
        profiles = []
        for i in range(count):
            profiles.append(AgentProfile(
                agent_id=f"mock_agent_{i}",
                name=MOCK_NAMES[i % len(MOCK_NAMES)],
                profile={
                    "age": random.randint(18, 55),
                    "gender": random.choice(["male", "female"]),
                    "occupation": random.choice(MOCK_OCCUPATIONS),
                    "location": random.choice(MOCK_CITIES),
                    "income": random.choice(["5k以下", "5k-10k", "10k-20k", "20k以上"]),
                    "personality": "普通消费者",
                    "background": f"Mock受访者#{i+1}",
                }
            ))
        return profiles

    async def create_experiment(self, project_id, agents, questionnaire_schema, config) -> str:
        import uuid
        exp_id = f"mock_exp_{uuid.uuid4().hex[:8]}"
        self._experiments[exp_id] = {
            "agents": agents,
            "questionnaire": questionnaire_schema,
            "status": "pending",
            "results": [],
        }
        return exp_id

    async def start_experiment(self, experiment_id: str) -> bool:
        if experiment_id not in self._experiments:
            return False
        self._experiments[experiment_id]["status"] = "running"
        asyncio.create_task(self._mock_run(experiment_id))
        return True

    async def _mock_run(self, experiment_id: str):
        """模拟实验运行，生成随机回答"""
        await asyncio.sleep(2)
        exp = self._experiments[experiment_id]
        questionnaire = exp["questionnaire"]
        results = []

        for agent in exp["agents"]:
            answers = self._generate_mock_answers(questionnaire)
            results.append(SurveyResult(
                agent_id=agent.agent_id,
                answers=answers,
                raw_dialog=[{"role": "assistant", "content": "Mock 回答"}],
                sentiment=random.choice(["positive", "neutral", "negative"]),
            ))
            await asyncio.sleep(0.05)

        exp["results"] = results
        exp["status"] = "completed"
        logger.info(f"Mock 实验 {experiment_id} 完成")

    def _generate_mock_answers(self, questionnaire_schema: dict) -> dict:
        answers = {}
        for section in questionnaire_schema.get("sections", []):
            for q in section.get("questions", []):
                q_id = q["id"]
                q_type = q["type"]
                options = q.get("options", [])

                if q_type == "single_choice" and options:
                    answers[q_id] = random.choice(options)
                elif q_type == "multi_choice" and options:
                    answers[q_id] = random.sample(options, k=random.randint(1, min(3, len(options))))
                elif q_type in ("scale", "nps"):
                    answers[q_id] = random.randint(q.get("scale_min", 1), q.get("scale_max", 10))
                elif q_type == "text":
                    answers[q_id] = random.choice([
                        "产品整体感觉不错，使用体验流畅",
                        "功能基本满足需求，但价格偏高",
                        "界面设计需要改进，操作不太直观",
                        "非常满意，会推荐给朋友",
                    ])
                elif q_type == "ranking" and options:
                    shuffled = options.copy()
                    random.shuffle(shuffled)
                    answers[q_id] = shuffled
        return answers

    async def stop_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self._experiments:
            self._experiments[experiment_id]["status"] = "cancelled"
            return True
        return False

    async def get_experiment_status(self, experiment_id: str) -> ExperimentStatus:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return ExperimentStatus(experiment_id=experiment_id, status="not_found", progress=0, total=0, completed=0, input_tokens=0, output_tokens=0)
        total = len(exp["agents"])
        completed = len(exp["results"])
        return ExperimentStatus(
            experiment_id=experiment_id,
            status=exp["status"],
            progress=int(completed / total * 100) if total else 0,
            total=total,
            completed=completed,
            input_tokens=random.randint(1000, 5000),
            output_tokens=random.randint(500, 2000),
        )

    async def collect_survey_results(self, experiment_id: str) -> list[SurveyResult]:
        return self._experiments.get(experiment_id, {}).get("results", [])

    async def get_agent_dialog(self, experiment_id: str, agent_id: str) -> list[dict]:
        return [{"role": "assistant", "content": "Mock 对话记录"}]

    async def health_check(self) -> bool:
        return True