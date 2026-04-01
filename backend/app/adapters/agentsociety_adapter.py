"""
AgentSociety 适配器实现
将 agentsociety 的能力封装为标准 AgentBackendAdapter 接口
"""
import json
import asyncio
from typing import Optional
from loguru import logger

from app.adapters.base import AgentBackendAdapter, AgentProfile, SurveyResult, ExperimentStatus
from app.core.config import settings


class AgentSocietyAdapter(AgentBackendAdapter):
    """
    agentsociety 后端适配器。

    使用 agentsociety 的 Python API 在本地运行 LLM Agent 模拟实验，
    将市场调研所需的受访者生成、问卷投放、结果收集等操作映射到
    agentsociety 的相应接口。
    """

    def __init__(self):
        self._experiments: dict[str, dict] = {}   # 内存中维护实验元数据

    # ── 受访者生成 ────────────────────────────────────────────────

    async def generate_respondents(
        self,
        persona_description: str,
        demographics: dict,
        count: int,
    ) -> list[AgentProfile]:
        """
        使用 LLM 生成多样化受访者档案。
        当 agentsociety 的 Agent 配置能力稳定后，
        可直接调用其 agent-templates API 生成。
        """
        logger.info(f"生成 {count} 位受访者 Agent，画像: {persona_description[:50]}...")

        try:
            # 尝试通过 agentsociety 内置 LLM 生成受访者
            profiles = await self._generate_via_llm(
                persona_description=persona_description,
                demographics=demographics,
                count=count,
            )
            return profiles
        except Exception as e:
            logger.warning(f"LLM 生成受访者失败，使用模板生成: {e}")
            return self._generate_template_respondents(persona_description, demographics, count)

    async def _generate_via_llm(
        self,
        persona_description: str,
        demographics: dict,
        count: int,
    ) -> list[AgentProfile]:
        """调用 LLM 批量生成受访者 JSON 档案"""
        import openai

        prompt = self._build_respondent_generation_prompt(
            persona_description, demographics, count
        )

        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )

        response = await client.chat.completions.create(
            model=settings.AGENTSOCIETY_DEFAULT_LLM,
            messages=[
                {
                    "role": "system",
                    "content": "你是一位专业的市场调研设计师，擅长创建真实、多样化的受访者画像。请严格按照 JSON 格式输出。"
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.9,
        )

        result = json.loads(response.choices[0].message.content)
        respondents_data = result.get("respondents", [])

        return [
            AgentProfile(
                agent_id=f"agent_{i}",
                name=r.get("name", f"受访者{i+1}"),
                profile=r,
            )
            for i, r in enumerate(respondents_data[:count])
        ]

    def _build_respondent_generation_prompt(
        self,
        persona_description: str,
        demographics: dict,
        count: int,
    ) -> str:
        age_range = demographics.get("age_range", [18, 65])
        gender_dist = demographics.get("gender_distribution", {})
        occupations = demographics.get("occupation_types", [])
        region = demographics.get("region", "中国")
        traits = demographics.get("custom_traits", [])

        return f"""请为一项市场调研生成 {count} 位真实、多样化的受访者画像。

## 受众描述
{persona_description}

## 人口统计约束
- 年龄范围：{age_range[0]}-{age_range[1]} 岁
- 性别分布：{json.dumps(gender_dist, ensure_ascii=False)}
- 职业类型：{', '.join(occupations) if occupations else '不限'}
- 地区：{region}
- 特征标签：{', '.join(traits) if traits else '无特殊要求'}

## 输出格式（JSON）
{{
  "respondents": [
    {{
      "name": "张某某",
      "age": 28,
      "gender": "female",
      "occupation": "产品经理",
      "company_size": "500人以上",
      "income": "15k-25k/月",
      "location": "北京",
      "education": "本科",
      "personality": "理性、追求效率、注重数据",
      "consumption_habits": "购买前会深入研究，重视口碑，偏好品质产品",
      "tech_savvy": "高",
      "background": "在互联网行业工作5年，日常使用多种数字工具，对产品体验有较高要求",
      "pain_points": ["工作与生活平衡困难", "信息过载"],
      "values": ["效率", "专业成长", "家庭"]
    }}
  ]
}}

请确保受访者具有多样性，反映真实的市场分布。"""

    def _generate_template_respondents(
        self,
        persona_description: str,
        demographics: dict,
        count: int,
    ) -> list[AgentProfile]:
        """降级方案：基于模板生成受访者"""
        templates = [
            {"name": "王小明", "age": 25, "gender": "male", "occupation": "软件工程师", "location": "深圳"},
            {"name": "李晓红", "age": 32, "gender": "female", "occupation": "市场经理", "location": "上海"},
            {"name": "张伟", "age": 28, "gender": "male", "occupation": "设计师", "location": "北京"},
            {"name": "陈静", "age": 45, "gender": "female", "occupation": "教师", "location": "成都"},
            {"name": "刘洋", "age": 38, "gender": "male", "occupation": "企业主", "location": "杭州"},
        ]

        profiles = []
        for i in range(count):
            template = templates[i % len(templates)].copy()
            template["index"] = i
            profiles.append(AgentProfile(
                agent_id=f"template_agent_{i}",
                name=template["name"],
                profile=template,
            ))
        return profiles

    # ── 实验生命周期 ──────────────────────────────────────────────

    async def create_experiment(
        self,
        project_id: str,
        agents: list[AgentProfile],
        questionnaire_schema: dict,
        config: dict,
    ) -> str:
        """
        将市场调研映射为 agentsociety 实验。
        核心思路：将问卷投放转化为 Agent 的调查任务（survey）。
        """
        import uuid
        experiment_id = f"exp_{project_id}_{uuid.uuid4().hex[:8]}"

        # 存储实验元数据（实际生产中应持久化）
        self._experiments[experiment_id] = {
            "id": experiment_id,
            "project_id": project_id,
            "agents": [{"id": a.agent_id, "name": a.name, "profile": a.profile} for a in agents],
            "questionnaire": questionnaire_schema,
            "config": config,
            "status": "pending",
            "results": [],
        }

        logger.info(f"创建实验 {experiment_id}，受访者数量: {len(agents)}")
        return experiment_id

    async def start_experiment(self, experiment_id: str) -> bool:
        """
        启动调研实验。
        使用异步任务并发执行所有 Agent 的问卷回答。
        """
        if experiment_id not in self._experiments:
            logger.error(f"实验 {experiment_id} 不存在")
            return False

        exp = self._experiments[experiment_id]
        exp["status"] = "running"

        # 异步后台执行（不阻塞 API 响应）
        asyncio.create_task(self._run_survey_experiment(experiment_id))
        logger.info(f"实验 {experiment_id} 已启动")
        return True

    async def _run_survey_experiment(self, experiment_id: str) -> None:
        """后台执行所有 Agent 的问卷回答"""
        exp = self._experiments[experiment_id]
        agents = exp["agents"]
        questionnaire = exp["questionnaire"]
        results = []

        semaphore = asyncio.Semaphore(5)  # 并发限制

        async def run_single_agent(agent_data: dict) -> Optional[SurveyResult]:
            async with semaphore:
                return await self._agent_answer_survey(agent_data, questionnaire)

        tasks = [run_single_agent(agent) for agent in agents]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, SurveyResult):
                results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Agent 回答失败: {result}")

        exp["results"] = results
        exp["status"] = "completed"
        logger.info(f"实验 {experiment_id} 完成，收集到 {len(results)} 份回答")

    async def _agent_answer_survey(
        self,
        agent_data: dict,
        questionnaire_schema: dict,
    ) -> SurveyResult:
        """让单个 Agent 角色扮演并回答问卷"""
        import openai

        profile = agent_data["profile"]
        agent_id = agent_data["id"]

        # 构建角色扮演 System Prompt
        system_prompt = f"""你是一位真实的消费者，正在参与市场调研问卷。

## 你的个人背景
- 姓名：{agent_data['name']}
- 年龄：{profile.get('age', '未知')}
- 职业：{profile.get('occupation', '未知')}
- 所在地：{profile.get('location', '未知')}
- 性格特点：{profile.get('personality', '普通消费者')}
- 消费习惯：{profile.get('consumption_habits', '正常消费')}
- 背景：{profile.get('background', '')}

## 回答要求
1. 完全以该人物身份回答，体现其个性和生活经历
2. 回答要真实、具体，有个人观点
3. 对于开放题，请给出 2-3 句话的真实感受
4. 严格按照要求的 JSON 格式输出"""

        # 构建问卷内容
        survey_prompt = self._build_survey_prompt(questionnaire_schema)

        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )

        dialog = []
        try:
            response = await client.chat.completions.create(
                model=settings.AGENTSOCIETY_DEFAULT_LLM,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": survey_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
            )

            answer_text = response.choices[0].message.content
            answers = json.loads(answer_text)

            dialog = [
                {"role": "user", "content": survey_prompt},
                {"role": "assistant", "content": answer_text},
            ]

            # 情感分析
            sentiment = await self._analyze_sentiment(answers, client)

            return SurveyResult(
                agent_id=agent_id,
                answers=answers,
                raw_dialog=dialog,
                sentiment=sentiment,
            )

        except Exception as e:
            logger.error(f"Agent {agent_id} 回答失败: {e}")
            return SurveyResult(
                agent_id=agent_id,
                answers={},
                raw_dialog=dialog,
                sentiment="neutral",
            )

    def _build_survey_prompt(self, questionnaire_schema: dict) -> str:
        """将问卷 schema 转换为自然语言提示"""
        sections = questionnaire_schema.get("sections", [])
        lines = ["请回答以下市场调研问卷，严格按照 JSON 格式输出你的答案：\n"]

        answer_format = {}

        for section in sections:
            lines.append(f"## {section.get('title', '')}")
            if section.get("description"):
                lines.append(section["description"])

            for q in section.get("questions", []):
                q_id = q["id"]
                q_type = q["type"]
                q_text = q["text"]

                if q_type == "single_choice":
                    options = q.get("options", [])
                    lines.append(f"\n{q_id}. {q_text}（单选）")
                    lines.append(f"   选项：{' | '.join(options)}")
                    answer_format[q_id] = f"从 {options} 中选一个"

                elif q_type == "multi_choice":
                    options = q.get("options", [])
                    lines.append(f"\n{q_id}. {q_text}（多选）")
                    lines.append(f"   选项：{' | '.join(options)}")
                    answer_format[q_id] = f"从 {options} 中选多个，用数组表示"

                elif q_type in ("scale", "nps"):
                    min_v = q.get("scale_min", 1)
                    max_v = q.get("scale_max", 10)
                    lines.append(f"\n{q_id}. {q_text}（{min_v}-{max_v} 分）")
                    answer_format[q_id] = f"{min_v} 到 {max_v} 之间的整数"

                elif q_type == "text":
                    lines.append(f"\n{q_id}. {q_text}（开放填写）")
                    answer_format[q_id] = "文字描述"

                elif q_type == "ranking":
                    options = q.get("options", [])
                    lines.append(f"\n{q_id}. {q_text}（排序）")
                    lines.append(f"   选项：{' | '.join(options)}")
                    answer_format[q_id] = f"将 {options} 按偏好排序，用数组表示"

        lines.append(f"\n## 输出格式\n```json\n{json.dumps(answer_format, ensure_ascii=False, indent=2)}\n```")
        return "\n".join(lines)

    async def _analyze_sentiment(self, answers: dict, client) -> str:
        """对回答进行简单情感分析"""
        try:
            text_answers = " ".join(
                str(v) for v in answers.values() if isinstance(v, str)
            )
            if not text_answers:
                return "neutral"

            resp = await client.chat.completions.create(
                model=settings.AGENTSOCIETY_DEFAULT_LLM,
                messages=[
                    {
                        "role": "user",
                        "content": f'分析以下市场调研回答的整体情感倾向，只返回一个词：positive、neutral 或 negative。\n\n回答内容：{text_answers[:500]}'
                    }
                ],
                max_tokens=10,
            )
            result = resp.choices[0].message.content.strip().lower()
            if result in ("positive", "neutral", "negative"):
                return result
            return "neutral"
        except Exception:
            return "neutral"

    async def stop_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self._experiments:
            self._experiments[experiment_id]["status"] = "cancelled"
            return True
        return False

    async def get_experiment_status(self, experiment_id: str) -> ExperimentStatus:
        if experiment_id not in self._experiments:
            return ExperimentStatus(
                experiment_id=experiment_id,
                status="not_found",
                progress=0,
                total=0,
                completed=0,
                input_tokens=0,
                output_tokens=0,
                error="实验不存在",
            )

        exp = self._experiments[experiment_id]
        total = len(exp["agents"])
        completed = len(exp["results"])
        progress = int(completed / total * 100) if total > 0 else 0

        return ExperimentStatus(
            experiment_id=experiment_id,
            status=exp["status"],
            progress=progress,
            total=total,
            completed=completed,
            input_tokens=0,   # TODO: 接入 token 计数
            output_tokens=0,
        )

    async def collect_survey_results(self, experiment_id: str) -> list[SurveyResult]:
        if experiment_id not in self._experiments:
            return []
        return self._experiments[experiment_id].get("results", [])

    async def get_agent_dialog(self, experiment_id: str, agent_id: str) -> list[dict]:
        if experiment_id not in self._experiments:
            return []
        results = self._experiments[experiment_id].get("results", [])
        for r in results:
            if r.agent_id == agent_id:
                return r.raw_dialog
        return []

    async def health_check(self) -> bool:
        return True