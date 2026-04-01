"""
定性用户研究闭环 API
============================================
"假设→验证→重构→深化→产出" 的完整研究流程:

1. designStudy      - 设计访谈框架，锚定研究目标
2. searchPersonas   - 查询/生成目标人群认知基线
3. scoutTaskChat    - 采集社交媒体真实用户声音
   buildPersona     - 据此重构人设验证/推翻初始假设
4. interviewChat    - 一对一深度访谈补充深层动机
5. generateReport   - 合成研究报告
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.core.response import ApiResponse

router = APIRouter(prefix="/research-flow", tags=["研究闭环"])


# ── Pydantic 请求/响应模型 ───────────────────────────────────────────

class StudyDesignRequest(BaseModel):
    """1. 研究设计请求"""
    user_request: str = Field(..., description="用户输入的研究需求（自然语言）")
    context: str = Field("", description="补充上下文（可含附件提取文本）")


class StudyDesignResult(BaseModel):
    """研究设计结果"""
    study_id: str
    research_goal: str
    target_persona_description: str
    interview_framework: list[dict]   # [{phase, objective, questions}]
    hypotheses: list[str]             # 初始假设列表
    created_at: str


class PersonaSearchRequest(BaseModel):
    """2. 人群认知基线查询"""
    study_id: str
    persona_description: str
    max_count: int = Field(10, ge=1, le=10, description="最多生成的人设数量")


class PersonaProfile(BaseModel):
    """人设档案"""
    id: str
    name: str
    age: int
    occupation: str
    background: str
    core_values: list[str]
    pain_points: list[str]
    attitude_hypotheses: dict   # {topic: attitude}
    source: str = "generated"  # "generated" | "scouted"


class ScoutRequest(BaseModel):
    """3. 社交媒体侦察请求"""
    study_id: str
    keywords: list[str]
    platforms: list[str] = Field(["小红书", "微博", "抖音"], description="搜索平台")
    persona_ids: list[str] = Field([], description="要更新的人设 ID 列表")


class ScoutResult(BaseModel):
    """侦察结果"""
    posts: list[dict]           # [{platform, content, sentiment, keywords}]
    insights: list[str]         # 提炼的洞察
    updated_personas: list[PersonaProfile]


class InterviewRequest(BaseModel):
    """4. 深度访谈请求"""
    study_id: str
    persona_id: str
    question: str
    conversation_history: list[dict] = []  # [{role, content}]


class InterviewResponse(BaseModel):
    """访谈回应"""
    persona_id: str
    persona_name: str
    response: str
    emotion: str          # calm | excited | hesitant | conflicted
    follow_up_hints: list[str]


class ReportRequest(BaseModel):
    """5. 报告生成请求"""
    study_id: str
    personas: list[dict]
    interview_transcripts: list[dict]   # [{persona_id, messages}]
    format: str = "markdown"            # "markdown" | "structured"


# ── 内存存储（生产环境应持久化到数据库）───────────────────────────────

_studies: dict[str, dict] = {}


def _get_llm_client():
    """获取 LLM 客户端"""
    import openai
    return openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        timeout=120.0,          # 流式响应需要较长超时
        max_retries=2,
    )


async def _llm_stream(messages: list[dict], temperature: float = 0.7) -> AsyncGenerator[str, None]:
    """流式调用 LLM"""
    client = _get_llm_client()
    try:
        stream = await client.chat.completions.create(
            model=settings.AGENTSOCIETY_DEFAULT_LLM,
            messages=messages,
            stream=True,
            temperature=temperature,
        )
        async for chunk in stream:
            if not chunk.choices:   # 最后的 [DONE] chunk choices 为空，跳过
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        logger.error(f"LLM 流式调用失败: {e}")
        yield f"[ERROR] {str(e)}"


async def _llm_complete(messages: list[dict], temperature: float = 0.7, json_mode: bool = False) -> str:
    """同步调用 LLM"""
    client = _get_llm_client()
    kwargs = dict(
        model=settings.AGENTSOCIETY_DEFAULT_LLM,
        messages=messages,
        temperature=temperature,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


# ── Step 1: designStudy ─────────────────────────────────────────────

@router.post("/design-study")
async def design_study(request: StudyDesignRequest):
    """
    Step 1: 设计访谈框架，锚定研究目标。
    根据用户输入的需求，生成：
    - 明确的研究目标
    - 目标人群描述
    - 访谈框架（分阶段问题设计）
    - 初始假设列表
    
    返回：Server-Sent Events 流式响应
    """
    study_id = str(uuid.uuid4())[:8]
    
    system_prompt = """你是一位资深的定性用户研究员，擅长设计用户访谈框架。
你的任务是分析用户的研究需求，帮助他们：
1. 明确研究目标（清晰、可验证）
2. 定义目标人群
3. 设计访谈框架（分阶段，从暖场到深挖）
4. 提出初始假设（基于常识和行业知识）

请用结构化的方式输出，让研究员可以直接使用。"""

    user_prompt = f"""研究需求：
{request.user_request}

{f'补充上下文：{request.context}' if request.context else ''}

请帮我设计一个完整的定性用户研究方案，包括：
1. 研究目标（1-2句话）
2. 目标人群画像描述
3. 访谈框架（3-4个阶段，每阶段2-3个核心问题）
4. 初始假设（3-5个基于现有认知的假设）

用清晰的中文输出。"""

    async def stream_generator():
        full_content = ""
        yield f"data: {json.dumps({'type': 'study_id', 'study_id': study_id}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'step', 'step': 'design_study', 'status': 'running'}, ensure_ascii=False)}\n\n"
        
        async for chunk in _llm_stream([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]):
            full_content += chunk
            yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"
        
        # 解析并存储研究设计
        _studies[study_id] = {
            "id": study_id,
            "user_request": request.user_request,
            "design_content": full_content,
            "personas": [],
            "scout_results": [],
            "interviews": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        yield f"data: {json.dumps({'type': 'step', 'step': 'design_study', 'status': 'done', 'study_id': study_id}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── Step 2: searchPersonas ──────────────────────────────────────────

@router.post("/search-personas")
async def search_personas(request: PersonaSearchRequest):
    """
    Step 2: 查询目标人群的已有认知基线作为初始假设。
    如果没有已有人群数据，则根据描述模拟生成。
    
    返回：流式生成每个人设档案
    """
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'search_personas', 'status': 'running', 'max_count': request.max_count}, ensure_ascii=False)}\n\n"
        
        study = _studies.get(request.study_id, {})
        design_context = study.get("design_content", "")
        
        system_prompt = """你是一位消费者洞察专家，擅长构建真实、有深度的用户画像。
请基于研究背景，生成具有代表性的目标用户画像。每个人设要：
- 有真实的生活背景和动机
- 体现出对研究主题的不同态度（支持/中立/怀疑）
- 有具体的痛点和期望
- 严格按照 JSON 格式输出"""

        user_prompt = f"""研究背景：
{design_context[:500] if design_context else request.persona_description}

目标人群描述：{request.persona_description}

请根据研究主题的需要，决定合适的人设数量来充分覆盖目标人群的多样性。
- 数量范围：1 到 {request.max_count} 个
- 原则：确保覆盖不同年龄、职业、态度（支持/中立/怀疑）、使用场景的关键人群
- 避免为了凑数而生成相似的人设，每个人设必须有独特的视角和代表性

输出 JSON 格式：
{{
  "personas": [
    {{
      "name": "张小明",
      "age": 28,
      "occupation": "互联网产品经理",
      "city": "北京",
      "background": "...",
      "core_values": ["效率", "性价比"],
      "pain_points": ["..."],
      "attitude": "这类用户对该话题持什么态度（2-3句）",
      "hypotheses": {{
        "product_attitude": "对产品的预判",
        "purchase_intent": "购买意愿预判"
      }}
    }}
  ]
}}"""

        result_json = await _llm_complete(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.85,
            json_mode=True,
        )
        
        try:
            personas_data = json.loads(result_json).get("personas", [])
        except Exception:
            personas_data = []
        
        personas = []
        for i, p in enumerate(personas_data[:request.max_count]):
            persona_id = f"persona_{request.study_id}_{i}"
            persona = {**p, "id": persona_id, "source": "generated"}
            personas.append(persona)
            yield f"data: {json.dumps({'type': 'persona', 'index': i, 'persona': persona}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1)
        
        # 存储到 study
        if request.study_id in _studies:
            _studies[request.study_id]["personas"] = personas
        
        yield f"data: {json.dumps({'type': 'step', 'step': 'search_personas', 'status': 'done', 'total': len(personas)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 3: scoutTaskChat + buildPersona ────────────────────────────

@router.post("/scout-and-build")
async def scout_and_build(request: ScoutRequest):
    """
    Step 3:
    - 为每个人设生成专属搜索关键词（人群特征 + 研究主题）
    - scoutTaskChat: 针对每个人设搜索社媒内容
    - buildPersona: 用该人设专属的侦察结果增强该人设

    返回：流式输出每个人的侦察结果和人设增强过程
    """
    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'scout_task', 'status': 'running', 'platforms': request.platforms}, ensure_ascii=False)}\n\n"

        study = _studies.get(request.study_id, {})
        existing_personas = study.get("personas", [])
        research_topic = study.get("title", "") or "、".join(request.keywords)

        # 如果没指定人设，则对所有人设执行
        persona_ids_to_update = request.persona_ids or [p["id"] for p in existing_personas]

        all_posts = []  # 收集所有帖子用于展示

        for persona_id in persona_ids_to_update:
            persona = next((p for p in existing_personas if p["id"] == persona_id), None)
            if not persona:
                continue

            # 为该人设生成专属搜索关键词
            persona_desc = f"{persona.get('name', '')}，{persona.get('age', '')}岁，{persona.get('occupation', '')}，{persona.get('background', '')[:100]}"
            persona_traits = ", ".join(persona.get("core_values", [])[:3]) if persona.get("core_values") else ""

            keyword_prompt = f"""根据以下用户画像和研究主题，生成 2-3 个精准的社交媒体搜索关键词组合。

用户画像：{persona_desc}
性格/价值观：{persona_traits}
研究主题：{research_topic}

要求：
- 关键词要结合用户特征和研究主题
- 使用口语化、真实用户会搜索的表达
- 每组关键词用空格分隔

JSON 输出：
{{"keywords": ["关键词1 关键词2", "关键词3 关键词4"]}}"""

            keyword_str = await _llm_complete(
                [{"role": "user", "content": keyword_prompt}],
                temperature=0.7,
                json_mode=True,
            )

            try:
                keyword_data = json.loads(keyword_str)
                persona_keywords = keyword_data.get("keywords", [])
            except Exception:
                persona_keywords = request.keywords  # 降级用默认关键词

            # 推送该人设开始侦察
            yield f"data: {json.dumps({'type': 'persona_scout_start', 'persona_id': persona_id, 'persona_name': persona.get('name', ''), 'keywords': persona_keywords}, ensure_ascii=False)}\n\n"

            # 为该人设搜索社媒内容
            scout_prompt = f"""你是一位擅长网络内容分析的研究员。
请模拟从 {', '.join(request.platforms)} 平台上搜索关键词 "{', '.join(persona_keywords)}" 的真实用户内容。

目标用户画像：{persona_desc}

生成 5-8 条该类用户可能发布的真实帖子/评论，要求：
- 语气、视角要符合该用户画像特征
- 包含不同情感（正面/负面/中立）
- 有具体细节（价格、功能、使用场景、个人经历）
- 真实感强，像真实用户发的

JSON 格式输出：
{{
  "posts": [
    {{
      "platform": "小红书",
      "content": "...",
      "sentiment": "positive|negative|neutral",
      "key_points": ["关键点1", "关键点2"]
    }}
  ],
  "insights": ["关于该用户群体的核心洞察1", "核心洞察2"]
}}"""

            scout_result_str = await _llm_complete(
                [{"role": "user", "content": scout_prompt}],
                temperature=0.8,
                json_mode=True,
            )

            try:
                scout_data = json.loads(scout_result_str)
                posts = scout_data.get("posts", [])
                insights = scout_data.get("insights", [])
            except Exception:
                posts, insights = [], []

            # 推送该人设的侦察帖子（带 persona_id 标识）
            for i, post in enumerate(posts):
                post_with_persona = {**post, "persona_id": persona_id, "persona_name": persona.get("name", "")}
                yield f"data: {json.dumps({'type': 'post', 'index': len(all_posts) + i, 'post': post_with_persona, 'persona_id': persona_id}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.03)
            all_posts.extend(posts)

            # 推送该人设的洞察
            yield f"data: {json.dumps({'type': 'persona_insights', 'persona_id': persona_id, 'persona_name': persona.get('name', ''), 'insights': insights}, ensure_ascii=False)}\n\n"

            # 用该人设专属的侦察结果增强该人设
            rebuild_prompt = f"""你是一位资深用户研究员，正在用真实社交媒体数据重构用户画像。

原始人设：
{json.dumps(persona, ensure_ascii=False, indent=2)}

该用户群体的真实社媒声音：
{json.dumps(posts, ensure_ascii=False, indent=2)}

洞察摘要：{', '.join(insights)}

任务：根据真实数据，更新/修正这个人设的：
1. 态度（是否与假设一致？）
2. 痛点（真实痛点 vs 假设痛点）
3. 语言风格（他们实际怎么说话？）
4. 新增：情绪触发点（什么让他们兴奋/担忧）

JSON 输出（在原有字段上修改，并添加 "scouted_updates" 字段说明修改原因）："""

            updated_str = await _llm_complete(
                [{"role": "user", "content": rebuild_prompt}],
                temperature=0.6,
                json_mode=True,
            )

            try:
                updated_persona = json.loads(updated_str)
                updated_persona["id"] = persona_id
                updated_persona["source"] = "scouted"
                updated_persona["scout_keywords"] = persona_keywords

                # 更新存储
                if request.study_id in _studies:
                    for i, p in enumerate(_studies[request.study_id]["personas"]):
                        if p["id"] == persona_id:
                            _studies[request.study_id]["personas"][i] = updated_persona

                yield f"data: {json.dumps({'type': 'updated_persona', 'persona': updated_persona, 'persona_id': persona_id}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"人设重构失败: {e}")

            yield f"data: {json.dumps({'type': 'persona_scout_done', 'persona_id': persona_id, 'persona_name': persona.get('name', '')}, ensure_ascii=False)}\n\n"

        # 存储整体侦察结果
        if request.study_id in _studies:
            _studies[request.study_id]["scout_results"] = {
                "posts": all_posts,
                "keywords": request.keywords,
                "platforms": request.platforms,
            }

        yield f"data: {json.dumps({'type': 'step', 'step': 'build_persona', 'status': 'done', 'total_personas': len(persona_ids_to_update)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 4: interviewChat ───────────────────────────────────────────

@router.post("/interview", response_model=ApiResponse[dict])
async def interview_chat(request: InterviewRequest):
    """
    Step 4: 一对一深度访谈。
    以人设身份进行对话，补充定量数据无法揭示的深层动机。
    
    支持多轮对话，传入 conversation_history 保持上下文。
    """
    study = _studies.get(request.study_id, {})
    personas = study.get("personas", [])
    persona = next((p for p in personas if p["id"] == request.persona_id), None)
    
    if not persona:
        raise HTTPException(status_code=404, detail=f"人设 {request.persona_id} 不存在")
    
    # 获取访谈框架（来自 Step 1）
    design_content = study.get("design_content", "")
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计的引导框架，供你理解研究目的）\n{design_content[:800]}"

    # 构建人设系统提示
    system_prompt = f"""你正在扮演一位真实的用户参与深度访谈。

## 你的背景
- 姓名：{persona.get('name', '用户')}
- 年龄：{persona.get('age', '未知')}
- 职业：{persona.get('occupation', '未知')}
- 所在城市：{persona.get('city', '未知')}
- 背景：{persona.get('background', '')}
- 核心价值观：{', '.join(persona.get('core_values', []))}
- 主要痛点：{', '.join(persona.get('pain_points', []))}
- 对话题的态度：{persona.get('attitude', '')}

{design_section}

## 访谈要求
1. 完全以第一人称回答，不要跳出角色
2. 回答要真实、有个人色彩，可以包含犹豫、矛盾的情绪
3. 分享具体的个人经历（可以虚构但要符合角色背景）
4. 对于不确定的问题，可以表达不确定性
5. 回答长度：2-4句话，自然口语化
6. 最后附加：emotion（calm/excited/hesitant/conflicted）和 1-2 个研究员可能感兴趣的 follow_up 方向

JSON 格式输出：
{{
  "response": "访谈回答（口语化中文）",
  "emotion": "calm|excited|hesitant|conflicted",
  "follow_up_hints": ["可追问的方向1", "可追问的方向2"]
}}"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # 加入历史对话
    for msg in request.conversation_history[-10:]:  # 最多保留最近 10 轮
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": request.question})
    
    result_str = await _llm_complete(messages, temperature=0.75, json_mode=True)
    
    try:
        result = json.loads(result_str)
    except Exception:
        result = {"response": result_str, "emotion": "calm", "follow_up_hints": []}
    
    # 保存访谈记录
    if request.study_id in _studies:
        interviews = _studies[request.study_id].setdefault("interviews", [])
        interview_entry = next((i for i in interviews if i["persona_id"] == request.persona_id), None)
        if not interview_entry:
            interview_entry = {
                "persona_id": request.persona_id,
                "persona_name": persona.get("name", ""),
                "messages": [],
            }
            interviews.append(interview_entry)
        
        interview_entry["messages"].append({"role": "user", "content": request.question})
        interview_entry["messages"].append({"role": "assistant", "content": result.get("response", "")})
    
    return ApiResponse.ok({
        "persona_id": request.persona_id,
        "persona_name": persona.get("name", ""),
        "response": result.get("response", ""),
        "emotion": result.get("emotion", "calm"),
        "follow_up_hints": result.get("follow_up_hints", []),
    })


@router.post("/interview/stream")
async def interview_chat_stream(request: InterviewRequest):
    """
    Step 4 (流式版): 深度访谈，流式输出回答。
    """
    study = _studies.get(request.study_id, {})
    personas = study.get("personas", [])
    persona = next((p for p in personas if p["id"] == request.persona_id), None)
    
    if not persona:
        raise HTTPException(status_code=404, detail=f"人设 {request.persona_id} 不存在")
    
    # 获取访谈框架（来自 Step 1）
    design_content = study.get("design_content", "")
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计，供你理解研究目的）\n{design_content[:800]}\n"
    
    system_prompt = f"""你正在扮演 {persona.get('name', '用户')}（{persona.get('age', '')}岁，{persona.get('occupation', '')}）参与深度访谈。

背景：{persona.get('background', '')}
态度：{persona.get('attitude', '')}
痛点：{', '.join(persona.get('pain_points', []))}

{design_section}要求：
- 完全以第一人称，口语化中文回答
- 体现角色的真实性格和矛盾感
- 2-4句话，不需要格式化"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.conversation_history[-8:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.question})
    
    async def stream_generator():
        full_response = ""
        yield f"data: {json.dumps({'type': 'persona', 'name': persona.get('name', ''), 'emotion': 'thinking'}, ensure_ascii=False)}\n\n"
        
        async for chunk in _llm_stream(messages, temperature=0.75):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"
        
        # 存储访谈记录
        if request.study_id in _studies:
            interviews = _studies[request.study_id].setdefault("interviews", [])
            interview_entry = next((i for i in interviews if i["persona_id"] == request.persona_id), None)
            if not interview_entry:
                interview_entry = {"persona_id": request.persona_id, "persona_name": persona.get("name", ""), "messages": []}
                interviews.append(interview_entry)
            interview_entry["messages"].append({"role": "user", "content": request.question})
            interview_entry["messages"].append({"role": "assistant", "content": full_response})
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 4-auto: 自动深度访谈 ─────────────────────────────────────

class AutoInterviewRequest(BaseModel):
    """自动访谈请求"""
    study_id: str


async def _extract_interview_questions(design_content: str) -> list[str]:
    """从 Step 1 的设计框架中提取访谈问题"""
    if not design_content:
        return []

    extract_prompt = f"""从以下用户研究方案中，提取所有访谈问题（包括各阶段的问题）。
只输出问题列表，每行一个问题，不要编号、不要其他文字。

研究方案：
{design_content}

请直接列出所有访谈问题："""

    result = await _llm_complete(
        [{"role": "user", "content": extract_prompt}],
        temperature=0.3,
    )

    questions = [q.strip() for q in result.strip().split("\n") if q.strip()]
    # 过滤掉太短或太长的行，保留合理的问题
    return [q for q in questions if 5 < len(q) < 200][:12]


async def _auto_interview_persona(
    persona: dict,
    questions: list[str],
    design_content: str,
) -> dict:
    """对单个 persona 执行自动访谈，返回完整的 Q&A 记录"""
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计）\n{design_content[:600]}\n"

    system_prompt = f"""你正在扮演 {persona.get('name', '用户')}（{persona.get('age', '')}岁，{persona.get('occupation', '')}）参与深度访谈。

背景：{persona.get('background', '')}
态度：{persona.get('attitude', '')}
痛点：{', '.join(persona.get('pain_points', []))}
核心价值观：{', '.join(persona.get('core_values', []))}

{design_section}要求：
- 完全以第一人称，口语化中文回答
- 体现角色的真实性格、矛盾感、生活经历
- 每个问题回答 2-4 句话，有具体细节
- 如果是追问，参考之前的回答保持一致性
- 不需要格式化，直接说话"""

    qa_records = []
    messages = [{"role": "system", "content": system_prompt}]

    for question in questions:
        messages.append({"role": "user", "content": question})

        try:
            answer = await _llm_complete(messages, temperature=0.75)
        except Exception as e:
            answer = f"（回答失败：{str(e)}）"

        messages.append({"role": "assistant", "content": answer})
        qa_records.append({
            "question": question,
            "answer": answer,
        })

    # 最终追加：让 persona 总结自己的核心态度
    summary_q = "最后，用一两句话总结一下你对这个话题的整体态度和最核心的顾虑。"
    messages.append({"role": "user", "content": summary_q})
    try:
        summary = await _llm_complete(messages, temperature=0.7)
    except Exception:
        summary = ""
    qa_records.append({
        "question": summary_q,
        "answer": summary,
    })

    return {
        "persona_id": persona["id"],
        "persona_name": persona.get("name", ""),
        "qa": qa_records,
        "total_questions": len(qa_records),
    }


@router.post("/auto-interview")
async def auto_interview(request: AutoInterviewRequest):
    """
    Step 4 (自动版): 基于访谈框架，自动对所有用户人设执行深度访谈。
    流式返回每个人的访谈进度和完整对话。
    """
    study = _studies.get(request.study_id)
    if not study:
        raise HTTPException(status_code=404, detail="研究不存在")

    personas = study.get("personas", [])
    if not personas:
        raise HTTPException(status_code=400, detail="暂无用户人设，请先生成人设")

    design_content = study.get("design_content", "")

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'auto_interview', 'status': 'running', 'total_personas': len(personas)}, ensure_ascii=False)}\n\n"

        # 1) 从设计框架中提取访谈问题
        yield f"data: {json.dumps({'type': 'status', 'message': '正在从研究框架中提取访谈问题...'}, ensure_ascii=False)}\n\n"

        questions = await _extract_interview_questions(design_content)
        if not questions:
            # 兜底：基于 user_request 生成通用访谈问题
            fallback = study.get("user_request", "用户研究")
            questions = [
                "你能简单介绍一下自己和你目前的生活状态吗？",
                f"关于{fallback}，你目前的了解和看法是什么？",
                "在做出相关决策时，你最看重哪些因素？",
                "你之前有没有类似的经历？可以分享一下吗？",
                "什么情况下你会决定尝试或购买？什么会让你犹豫？",
                "你觉得现有的解决方案有哪些不足？",
                "如果有一个完美的方案，你希望它是什么样的？",
                "用一两句话总结一下你的核心态度和最顾虑的点。",
            ]

        yield f"data: {json.dumps({'type': 'questions', 'questions': questions, 'count': len(questions)}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'message': f'提取到 {len(questions)} 个访谈问题，开始对 {len(personas)} 位用户进行访谈...'}, ensure_ascii=False)}\n\n"

        # 2) 并发对所有人设执行访谈（限制并发 3 个）
        semaphore = asyncio.Semaphore(3)

        async def interview_one(persona: dict) -> dict:
            async with semaphore:
                return await _auto_interview_persona(persona, questions, design_content)

        # 为了流式输出，逐个执行（而不是全部并发后再输出）
        for i, persona in enumerate(personas):
            name = persona.get("name", f"用户{i+1}")
            yield f"data: {json.dumps({'type': 'interview_start', 'persona_id': persona['id'], 'persona_name': name, 'index': i, 'total': len(personas)}, ensure_ascii=False)}\n\n"

            try:
                result = await interview_one(persona)
            except Exception as e:
                result = {
                    "persona_id": persona["id"],
                    "persona_name": name,
                    "qa": [{"question": "（访谈失败）", "answer": str(e)}],
                    "total_questions": 0,
                }

            # 逐条推送 Q&A
            for j, qa in enumerate(result["qa"]):
                qa_event = json.dumps({
                    'type': 'qa',
                    'persona_id': persona['id'],
                    'persona_name': name,
                    'index': j,
                    'question': qa['question'],
                    'answer': qa['answer'],
                }, ensure_ascii=False)
                yield f"data: {qa_event}\n\n"

            # 保存访谈记录到 study
            if request.study_id in _studies:
                interviews = _studies[request.study_id].setdefault("interviews", [])
                interviews.append({
                    "persona_id": persona["id"],
                    "persona_name": name,
                    "messages": [
                        msg
                        for qa in result["qa"]
                        for msg in [
                            {"role": "user", "content": qa["question"]},
                            {"role": "assistant", "content": qa["answer"]},
                        ]
                    ],
                })

            yield f"data: {json.dumps({'type': 'interview_done', 'persona_id': persona['id'], 'persona_name': name, 'qa_count': result['total_questions']}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'step', 'step': 'auto_interview', 'status': 'done', 'total_personas': len(personas), 'questions_per_persona': len(questions)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 5: generateReport ──────────────────────────────────────────

@router.post("/generate-report")
async def generate_report(request: ReportRequest):
    """
    Step 5: 将人设数据与访谈洞察合成可指导决策的研究报告。
    
    返回：流式输出报告内容（Markdown 格式）
    """
    study = _studies.get(request.study_id, {})
    
    personas = request.personas or study.get("personas", [])
    interviews = request.interview_transcripts or study.get("interviews", [])
    scout_results = study.get("scout_results", {})
    design_content = study.get("design_content", "")
    user_request = study.get("user_request", "")
    
    system_prompt = """你是一位资深定性研究员，擅长将访谈数据转化为可指导决策的洞察报告。
报告要：
- 有清晰的结构（执行摘要 → 用户画像 → 核心发现 → 机会洞察 → 建议）
- 用具体的访谈引用支撑观点（要有引号和说话人）
- 区分"验证的假设"和"被推翻的假设"
- 提出 3-5 个具体可行的产品/策略建议
- 用 Markdown 格式"""

    # 整理访谈摘要
    interview_summary = ""
    for interview in interviews[:5]:
        name = interview.get("persona_name", "")
        msgs = interview.get("messages", [])
        if msgs:
            qa_pairs = []
            for i in range(0, len(msgs)-1, 2):
                q = msgs[i].get("content", "") if i < len(msgs) else ""
                a = msgs[i+1].get("content", "") if i+1 < len(msgs) else ""
                if q and a:
                    qa_pairs.append(f"Q: {q[:80]}\nA（{name}）: {a[:150]}")
            interview_summary += f"\n### {name} 的访谈\n" + "\n\n".join(qa_pairs[:3]) + "\n"

    user_prompt = f"""请基于以下研究数据，生成一份专业的定性用户研究报告。

## 研究背景
{user_request}

## 研究设计
{design_content[:300] if design_content else '无'}

## 用户画像摘要（{len(personas)} 人）
{json.dumps([{k: v for k, v in p.items() if k in ['name', 'age', 'occupation', 'attitude', 'pain_points']} for p in personas[:5]], ensure_ascii=False, indent=2)}

## 社交媒体洞察
{json.dumps(scout_results.get('insights', []), ensure_ascii=False) if scout_results else '无'}

## 访谈记录摘要
{interview_summary if interview_summary else '暂无访谈数据'}

---
请生成完整的研究报告（Markdown 格式，约 800-1200 字）。"""

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_report', 'status': 'running'}, ensure_ascii=False)}\n\n"
        
        async for chunk in _llm_stream([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.6):
            yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"
        
        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_report', 'status': 'done'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── 工具接口 ─────────────────────────────────────────────────────────

@router.get("/study/{study_id}", response_model=ApiResponse[dict])
async def get_study(study_id: str):
    """获取研究状态（人设、侦察结果、访谈记录）"""
    study = _studies.get(study_id)
    if not study:
        raise HTTPException(status_code=404, detail="研究不存在")
    return ApiResponse.ok(study)


@router.post("/upload-context")
async def upload_context(
    file: UploadFile = File(...),
    study_id: str = Form(default=""),
):
    """
    上传附件（PDF/文档/图片），提取文本作为研究背景。
    返回提取的文本内容。
    """
    content = await file.read()
    filename = file.filename or ""
    
    # 简单文本提取（生产环境可接入 OCR/PDF 解析）
    extracted_text = ""
    if filename.endswith((".txt", ".md")):
        try:
            extracted_text = content.decode("utf-8")
        except Exception:
            extracted_text = content.decode("latin-1", errors="ignore")
    else:
        # 对于非文本文件，返回占位提示
        extracted_text = f"[已上传文件: {filename}，共 {len(content)} 字节。如需提取内容，请使用 PDF/TXT 格式文件。]"
    
    return ApiResponse.ok({
        "filename": filename,
        "size": len(content),
        "extracted_text": extracted_text[:2000],  # 限制长度
    })