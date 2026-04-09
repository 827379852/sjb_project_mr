from __future__ import annotations
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
from sqlalchemy import select
from pydantic import BaseModel, Field
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.core.response import ApiResponse
from app.models.user import User, TASK_COST_CREDITS
from app.models.study import Study, StudyPersona, StudyInterview, ScoutResult, StudyReport
from app.dependencies.auth import get_current_active_user, get_user_by_api_key
from app.schemas.study import StudyOut, StudyDetailOut

router = APIRouter(prefix="/research-flow", tags=["研究闭环"])


# ── Pydantic 请求/响应模型 ───────────────────────────────────────────

class StudyDesignRequest(BaseModel):
    """1. 研究设计请求"""
    user_request: str = Field(..., description="用户输入的研究需求（自然语言）")
    context: str = Field("", description="补充上下文（可含附件提取文本）")


class PersonaSearchRequest(BaseModel):
    """2. 人群认知基线查询"""
    study_id: str
    persona_description: str
    max_count: int = Field(10, ge=1, le=10, description="最多生成的人设数量")


class ScoutRequest(BaseModel):
    """3. 社交媒体侦察请求"""
    study_id: str
    keywords: list[str]
    platforms: list[str] = Field(["小红书", "微博", "抖音"], description="搜索平台")
    persona_ids: list[str] = Field([], description="要更新的人设 ID 列表")


class InterviewRequest(BaseModel):
    """4. 深度访谈请求"""
    study_id: str
    persona_id: str
    question: str
    conversation_history: list[dict] = []  # [{role, content}]


class ReportRequest(BaseModel):
    """5. 报告生成请求"""
    study_id: str
    personas: list[dict]
    interview_transcripts: list[dict]   # [{persona_id, messages}]
    format: str = "markdown"            # "markdown" | "structured"


class AutoInterviewRequest(BaseModel):
    """自动访谈请求"""
    study_id: str


# ── LLM 调用工具 ─────────────────────────────────────────────────────

def _get_llm_client():
    """获取 LLM 客户端"""
    import openai
    return openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        timeout=120.0,
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
            if not chunk.choices:
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


# ── 研究管理 API ─────────────────────────────────────────────────────

@router.get("/studies", response_model=ApiResponse[list[StudyOut]])
async def list_studies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的研究列表"""
    result = await db.execute(
        select(Study)
        .where(Study.user_id == current_user.id)
        .order_by(Study.updated_at.desc())
    )
    studies = result.scalars().all()
    return ApiResponse.ok([StudyOut.model_validate(s) for s in studies])


@router.get("/studies/{study_id}", response_model=ApiResponse[StudyDetailOut])
async def get_study_detail(
    study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取研究详情"""
    study = await db.get(Study, study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    # 加载关联数据
    await db.refresh(study, ["personas", "interviews", "scout_results", "reports"])

    return ApiResponse.ok(StudyDetailOut.model_validate(study))


@router.delete("/studies/{study_id}", response_model=ApiResponse[None])
async def delete_study(
    study_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除研究"""
    study = await db.get(Study, study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    await db.delete(study)
    return ApiResponse.ok(message="研究已删除")


# ── Step 1: designStudy ─────────────────────────────────────────────

@router.post("/design-study")
async def design_study(
    request: StudyDesignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 1: 设计访谈框架，锚定研究目标。
    根据用户输入的需求，生成：
    - 明确的研究目标
    - 目标人群描述
    - 访谈框架（分阶段问题设计）
    - 初始假设列表

    返回：Server-Sent Events 流式响应
    """
    # 创建 Study 记录
    title = request.user_request[:30] + ("..." if len(request.user_request) > 30 else "")
    study = Study(
        user_id=current_user.id,
        title=title,
        user_request=request.user_request,
        status="in_progress",
        current_phase="designing",
    )
    db.add(study)
    await db.commit()  # 先提交，确保 study_id 生成
    await db.refresh(study)

    study_id = study.id

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
        has_error = False
        yield f"data: {json.dumps({'type': 'study_id', 'study_id': study_id}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'step', 'step': 'design_study', 'status': 'running'}, ensure_ascii=False)}\n\n"

        try:
            async for chunk in _llm_stream([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]):
                full_content += chunk
                yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"
        except Exception as e:
            has_error = True
            logger.error(f"研究设计失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        # 重新获取数据库 session 并更新 Study 记录
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            if not has_error:
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.design_content = full_content
                    study_to_update.current_phase = "post-design"
                    await new_db.commit()

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
async def search_personas(
    request: PersonaSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 2: 查询目标人群的已有认知基线作为初始假设。
    如果没有已有人群数据，则根据描述模拟生成。

    返回：流式生成每个人设档案
    """
    # 验证 study 所有权
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    # 检查积分（超级管理员不需要检查）
    if not current_user.is_superuser:
        if current_user.credits < TASK_COST_CREDITS:
            logger.warning(f"[积分] 用户 {current_user.email} 积分不足: 当前 {current_user.credits}, 需要 {TASK_COST_CREDITS}")
            raise HTTPException(
                status_code=402,
                detail=f"积分不足，当前积分 {current_user.credits}，需要 {TASK_COST_CREDITS} 积分"
            )
        # 扣除积分
        current_user.credits -= TASK_COST_CREDITS
        await db.flush()
        logger.info(f"[积分] 用户 {current_user.email} 扣除 {TASK_COST_CREDITS} 积分, 剩余 {current_user.credits}")
    else:
        logger.info(f"[积分] 超级管理员 {current_user.email} 跳过积分检查")

    user_id = current_user.id
    has_deducted_credits = not current_user.is_superuser  # 标记是否扣除了积分

    async def stream_generator():
        has_error = False
        task_completed = False  # 标记任务是否成功完成
        # 首先发送积分扣除事件
        if has_deducted_credits:
            yield f"data: {json.dumps({'type': 'credits_deducted', 'amount': TASK_COST_CREDITS, 'remaining': current_user.credits}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'step', 'step': 'search_personas', 'status': 'running', 'max_count': request.max_count}, ensure_ascii=False)}\n\n"

        design_context = study.design_content or ""

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

        try:
            result_json = await _llm_complete(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.85,
                json_mode=True,
            )
        except Exception as e:
            has_error = True
            logger.error(f"[积分] 人设生成失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        # 失败时返还积分
        if has_error:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as new_db:
                if has_deducted_credits:
                    user_to_refund = await new_db.get(User, user_id)
                    if user_to_refund:
                        user_to_refund.credits += TASK_COST_CREDITS
                        await new_db.commit()
                        logger.info(f"[积分] 任务失败，返还 {TASK_COST_CREDITS} 积分给用户 {user_to_refund.email}, 当前积分 {user_to_refund.credits}")
                        yield f"data: {json.dumps({'type': 'credits_refund', 'amount': TASK_COST_CREDITS, 'message': '任务失败，积分已返还'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'step', 'step': 'search_personas', 'status': 'error'}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        try:
            try:
                personas_data = json.loads(result_json).get("personas", [])
            except Exception:
                personas_data = []

            personas = []
            for i, p in enumerate(personas_data[:request.max_count]):
                persona_id = str(uuid.uuid4())
                persona = {**p, "id": persona_id, "source": "generated"}
                personas.append(persona)

                # 保存到数据库 - 使用新的 session
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as new_db:
                    db_persona = StudyPersona(
                        id=persona_id,
                        study_id=request.study_id,
                        name=p.get("name", f"用户{i+1}"),
                        age=p.get("age"),
                        occupation=p.get("occupation", ""),
                        city=p.get("city", ""),
                        background=p.get("background", ""),
                        persona_data=p,
                        source="generated",
                    )
                    new_db.add(db_persona)
                    await new_db.commit()

                yield f"data: {json.dumps({'type': 'persona', 'index': i, 'persona': persona}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.1)

            # 更新 study 状态 - 使用新的 session
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as new_db:
                study_to_update = await new_db.get(Study, request.study_id)
                if study_to_update:
                    study_to_update.current_phase = "personas"
                    await new_db.commit()

            yield f"data: {json.dumps({'type': 'step', 'step': 'search_personas', 'status': 'done', 'total': len(personas)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            task_completed = True  # 标记任务成功完成

        except asyncio.CancelledError:
            # 流式响应被取消（前端断开连接或手动中断）
            logger.warning(f"[积分] 流式响应被取消，用户 {user_id}")
            raise
        except Exception as e:
            logger.error(f"[积分] 人设保存失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            raise
        finally:
            # 如果任务未成功完成，返还积分
            if not task_completed and has_deducted_credits:
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as new_db:
                    user_to_refund = await new_db.get(User, user_id)
                    if user_to_refund:
                        user_to_refund.credits += TASK_COST_CREDITS
                        await new_db.commit()
                        logger.info(f"[积分] 任务未完成（中断），返还 {TASK_COST_CREDITS} 积分给用户 {user_to_refund.email}, 当前积分 {user_to_refund.credits}")
                        try:
                            yield f"data: {json.dumps({'type': 'credits_refund', 'amount': TASK_COST_CREDITS, 'message': '任务中断，积分已返还'}, ensure_ascii=False)}\n\n"
                        except:
                            pass  # 如果连接已断开，忽略 yield 错误

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 3: scoutTaskChat + buildPersona ────────────────────────────

@router.post("/scout-and-build")
async def scout_and_build(
    request: ScoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 3:
    - 为每个人设生成专属搜索关键词（人群特征 + 研究主题）
    - scoutTaskChat: 针对每个人设搜索社媒内容
    - buildPersona: 用该人设专属的侦察结果增强该人设

    返回：流式输出每个人的侦察结果和人设增强过程
    """
    # 验证 study 所有权
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    # 获取已有人设
    result = await db.execute(
        select(StudyPersona).where(StudyPersona.study_id == request.study_id)
    )
    existing_personas = result.scalars().all()
    research_topic = study.title or "、".join(request.keywords)

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'scout_task', 'status': 'running', 'platforms': request.platforms}, ensure_ascii=False)}\n\n"

        persona_ids_to_update = request.persona_ids or [p.id for p in existing_personas]
        all_posts = []

        # ── 辅助：获取人设描述 ────────────────────────────────────
        def get_persona_desc(persona_obj):
            return (
                f"{persona_obj.name}，{persona_obj.age or ''}岁，"
                f"{persona_obj.occupation or ''}，{(persona_obj.background or '')[:100]}"
            )

        # ── 辅助：为一个人设执行完整侦察（3步 LLM 并行）───
        async def scout_persona(
            persona_obj,
            persona_queue: asyncio.Queue,
        ):
            """
            并行执行关键词生成 → 社媒搜索 → 人设增强，
            将所有 SSE 事件推入 persona_queue。
            """
            p_id = persona_obj.id
            p_name = persona_obj.name
            p_data = persona_obj.persona_data or {}
            p_desc = get_persona_desc(persona_obj)
            research_t = research_topic

            # ① 生成专属关键词
            keyword_prompt = f"""根据以下用户画像和研究主题，生成 2-3 个精准的社交媒体搜索关键词组合。

用户画像：{p_desc}
性格/价值观：
研究主题：{research_t}

要求：
- 关键词要结合用户特征和研究主题
- 使用口语化、真实用户会搜索的表达
- 每组关键词用空格分隔

JSON 输出：
{{"keywords": ["关键词1 关键词2", "关键词3 关键词4"]}}"""

            keyword_task = _llm_complete(
                [{"role": "user", "content": keyword_prompt}],
                temperature=0.7,
                json_mode=True,
            )

            # ② 社媒搜索（依赖关键词结果）
            async def search_and_rebuild(kw_result: str):
                try:
                    kw_data = json.loads(kw_result)
                    persona_kw = kw_data.get("keywords", [])
                except Exception:
                    persona_kw = request.keywords

                await persona_queue.put((
                    'persona_scout_start',
                    {
                        'persona_id': p_id,
                        'persona_name': p_name,
                        'keywords': persona_kw,
                    }
                ))

                # 社媒内容搜索
                scout_prompt = f"""你是一位擅长网络内容分析的研究员。
请模拟从 {', '.join(request.platforms)} 平台上搜索关键词 "{', '.join(persona_kw)}" 的真实用户内容。

目标用户画像：{p_desc}

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

                # 逐条发送帖子
                for post in posts:
                    post_with_persona = {**post, "persona_id": p_id, "persona_name": p_name}
                    await persona_queue.put((
                        'post',
                        {
                            'post': post_with_persona,
                            'persona_id': p_id,
                        }
                    ))
                    await asyncio.sleep(0.03)

                # 发送洞察
                if insights:
                    await persona_queue.put((
                        'persona_insights',
                        {
                            'persona_id': p_id,
                            'persona_name': p_name,
                            'insights': insights,
                        }
                    ))

                # 人设增强
                rebuild_prompt = f"""你是一位资深用户研究员，正在用真实社交媒体数据重构用户画像。

原始人设：
{json.dumps(p_data, ensure_ascii=False, indent=2)}

该用户群体的真实社媒声音：
{json.dumps(posts, ensure_ascii=False, indent=2)}

洞察摘要：{', '.join(insights)}

任务：根据真实数据，更新/修正这个人设的：
1. 态度（是否与假设一致？）
2. 痛点（真实痛点 vs 假设痛点）
3. 语言风格（他们实际怎么说话？）
4. 新增：情绪触发点（什么让他们兴奋/担忧）

JSON 输出（在原有字段上修改，并添加 "scouted_updates" 字段说明修改原因）："""

                try:
                    updated_str = await _llm_complete(
                        [{"role": "user", "content": rebuild_prompt}],
                        temperature=0.6,
                        json_mode=True,
                    )
                    updated_persona = json.loads(updated_str)
                    updated_persona["id"] = p_id
                    updated_persona["source"] = "scouted"
                    updated_persona["scout_keywords"] = persona_kw

                    # 更新数据库
                    from app.core.database import AsyncSessionLocal
                    async with AsyncSessionLocal() as new_db:
                        persona_to_update = await new_db.get(StudyPersona, p_id)
                        if persona_to_update:
                            persona_to_update.persona_data = updated_persona
                            persona_to_update.source = "scouted"
                            await new_db.commit()

                    await persona_queue.put((
                        'updated_persona',
                        {'persona': updated_persona, 'persona_id': p_id}
                    ))
                except Exception as e:
                    logger.error(f"人设重构失败: {e}")

                # 标记完成，并携带 posts 数量
                await persona_queue.put(('persona_scout_done', {'persona_id': p_id, 'persona_name': p_name, 'posts_count': len(posts)}))
                return posts

            # 编排：先关键词 → 再搜索+增强（这两步可并行吗？不，搜索依赖关键词）
            # 但不同人设之间完全并行
            kw_result = await keyword_task
            posts = await search_and_rebuild(kw_result)
            return posts

        # ── 并行启动所有人设的侦察任务 ──────────────────────────────
        persona_queues: dict[str, asyncio.Queue] = {}
        scout_tasks: list[asyncio.Task] = []

        for persona_id in persona_ids_to_update:
            persona = next((p for p in existing_personas if p.id == persona_id), None)
            if not persona:
                continue
            q: asyncio.Queue = asyncio.Queue()
            persona_queues[persona_id] = q
            task = asyncio.create_task(scout_persona(persona, q))
            scout_tasks.append(task)

        # ── 主循环：实时收集各人设的事件并 yield ───────────────────
        pending_tasks = set(scout_tasks)
        while pending_tasks:
            for p_id, q in persona_queues.items():
                while not q.empty():
                    evt_type, evt_data = await q.get()
                    if evt_type == 'post':
                        all_posts.append(evt_data['post'])
                        yield f"data: {json.dumps({'type': 'post', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'persona_scout_start':
                        yield f"data: {json.dumps({'type': 'persona_scout_start', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'persona_insights':
                        yield f"data: {json.dumps({'type': 'persona_insights', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'updated_persona':
                        yield f"data: {json.dumps({'type': 'updated_persona', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'persona_scout_done':
                        yield f"data: {json.dumps({'type': 'persona_scout_done', **evt_data}, ensure_ascii=False)}\n\n"

            # 检查已完成的任务
            done_tasks = {t for t in pending_tasks if t.done()}
            for t in done_tasks:
                # 把该任务关联队列中剩余的事件全部读完
                for p_id, q in persona_queues.items():
                    while not q.empty():
                        evt_type, evt_data = await q.get()
                        if evt_type == 'post':
                            all_posts.append(evt_data['post'])
                            yield f"data: {json.dumps({'type': 'post', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'persona_scout_start':
                            yield f"data: {json.dumps({'type': 'persona_scout_start', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'persona_insights':
                            yield f"data: {json.dumps({'type': 'persona_insights', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'updated_persona':
                            yield f"data: {json.dumps({'type': 'updated_persona', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'persona_scout_done':
                            yield f"data: {json.dumps({'type': 'persona_scout_done', **evt_data}, ensure_ascii=False)}\n\n"
                pending_tasks.discard(t)

            if pending_tasks:
                await asyncio.sleep(0.05)  # 避免 CPU 空转

        # ── 保存整体侦察结果 ──────────────────────────────────────
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            scout_result = ScoutResult(
                study_id=request.study_id,
                keywords=request.keywords,
                platforms=request.platforms,
                posts=all_posts,
            )
            new_db.add(scout_result)
            study_to_update = await new_db.get(Study, request.study_id)
            if study_to_update:
                study_to_update.current_phase = "scouting"
            await new_db.commit()

        yield f"data: {json.dumps({'type': 'step', 'step': 'build_persona', 'status': 'done', 'total_personas': len(persona_ids_to_update)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 4: interviewChat ───────────────────────────────────────────

@router.post("/interview", response_model=ApiResponse[dict])
async def interview_chat(
    request: InterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 4: 一对一深度访谈。
    以人设身份进行对话，补充定量数据无法揭示的深层动机。
    """
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    result = await db.execute(
        select(StudyPersona).where(StudyPersona.id == request.persona_id)
    )
    persona = result.scalar_one_or_none()

    if not persona:
        raise HTTPException(status_code=404, detail=f"人设 {request.persona_id} 不存在")

    design_content = study.design_content or ""
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计的引导框架，供你理解研究目的）\n{design_content[:800]}"

    system_prompt = f"""你正在扮演一位真实的用户参与深度访谈。

## 你的背景
- 姓名：{persona.name}
- 年龄：{persona.age or '未知'}
- 职业：{persona.occupation or '未知'}
- 所在城市：{persona.city or '未知'}
- 背景：{persona.background or ''}
- 人设详情：{json.dumps(persona.persona_data, ensure_ascii=False)}

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
    for msg in request.conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.question})

    result_str = await _llm_complete(messages, temperature=0.75, json_mode=True)

    try:
        result = json.loads(result_str)
    except Exception:
        result = {"response": result_str, "emotion": "calm", "follow_up_hints": []}

    # 保存访谈记录
    interview = StudyInterview(
        study_id=request.study_id,
        persona_id=request.persona_id,
        persona_name=persona.name,
        messages=[
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": result.get("response", "")},
        ],
    )
    db.add(interview)
    await db.commit()

    return ApiResponse.ok({
        "persona_id": request.persona_id,
        "persona_name": persona.name,
        "response": result.get("response", ""),
        "emotion": result.get("emotion", "calm"),
        "follow_up_hints": result.get("follow_up_hints", []),
    })


@router.post("/interview/stream")
async def interview_chat_stream(
    request: InterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Step 4 (流式版): 深度访谈，流式输出回答。"""
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    result = await db.execute(
        select(StudyPersona).where(StudyPersona.id == request.persona_id)
    )
    persona = result.scalar_one_or_none()

    if not persona:
        raise HTTPException(status_code=404, detail=f"人设 {request.persona_id} 不存在")

    design_content = study.design_content or ""
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计，供你理解研究目的）\n{design_content[:800]}\n"

    system_prompt = f"""你正在扮演 {persona.name}（{persona.age or ''}岁，{persona.occupation or ''}）参与深度访谈。

背景：{persona.background or ''}
人设详情：{json.dumps(persona.persona_data, ensure_ascii=False)}

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
        yield f"data: {json.dumps({'type': 'persona', 'name': persona.name, 'emotion': 'thinking'}, ensure_ascii=False)}\n\n"

        async for chunk in _llm_stream(messages, temperature=0.75):
            full_response += chunk
            yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"

        # 保存访谈记录 - 使用新的 session
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            interview = StudyInterview(
                study_id=request.study_id,
                persona_id=request.persona_id,
                persona_name=persona.name,
                messages=[
                    {"role": "user", "content": request.question},
                    {"role": "assistant", "content": full_response},
                ],
            )
            new_db.add(interview)
            await new_db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 4-auto: 自动深度访谈 ─────────────────────────────────────

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
    return [q for q in questions if 5 < len(q) < 200][:12]


async def _auto_interview_persona(
    persona: StudyPersona,
    questions: list[str],
    design_content: str,
) -> dict:
    """对单个 persona 执行自动访谈，返回完整的 Q&A 记录"""
    design_section = ""
    if design_content:
        design_section = f"## 访谈框架（研究者设计）\n{design_content[:600]}\n"

    system_prompt = f"""你正在扮演 {persona.name}（{persona.age or ''}岁，{persona.occupation or ''}）参与深度访谈。

背景：{persona.background or ''}
人设详情：{json.dumps(persona.persona_data, ensure_ascii=False)}

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
        "persona_id": persona.id,
        "persona_name": persona.name,
        "qa": qa_records,
        "total_questions": len(qa_records),
    }


@router.post("/auto-interview")
async def auto_interview(
    request: AutoInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 4 (自动版): 基于访谈框架，自动对所有用户人设执行深度访谈。
    流式返回每个人的访谈进度和完整对话。
    """
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    result = await db.execute(
        select(StudyPersona).where(StudyPersona.study_id == request.study_id)
    )
    personas = result.scalars().all()

    if not personas:
        raise HTTPException(status_code=400, detail="暂无用户人设，请先生成人设")

    design_content = study.design_content or ""

    async def stream_generator():
        yield f"data: {json.dumps({'type': 'step', 'step': 'auto_interview', 'status': 'running', 'total_personas': len(personas)}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'status', 'message': '正在从研究框架中提取访谈问题...'}, ensure_ascii=False)}\n\n"

        questions = await _extract_interview_questions(design_content)
        if not questions:
            fallback = study.user_request or "用户研究"
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
        yield f"data: {json.dumps({'type': 'status', 'message': f'提取到 {len(questions)} 个访谈问题，开始对 {len(personas)} 位用户进行并行访谈...'}, ensure_ascii=False)}\n\n"

        # ── 辅助：为一个 persona 执行完整访谈，实时推送每对 QA ──────────
        async def interview_persona(
            persona: StudyPersona,
            index: int,
            total: int,
            q: asyncio.Queue,
        ):
            p_id = persona.id
            p_name = persona.name or f"用户{index + 1}"

            try:
                await q.put((
                    'interview_start',
                    {'persona_id': p_id, 'persona_name': p_name, 'index': index, 'total': total}
                ))

                result = await _auto_interview_persona(persona, questions, design_content)

                # 实时推送每一对 QA
                for j, qa in enumerate(result["qa"]):
                    await q.put((
                        'qa',
                        {
                            'persona_id': p_id,
                            'persona_name': p_name,
                            'index': j,
                            'question': qa['question'],
                            'answer': qa['answer'],
                        }
                    ))

                # 保存访谈记录到数据库
                from app.core.database import AsyncSessionLocal
                async with AsyncSessionLocal() as new_db:
                    interview = StudyInterview(
                        study_id=request.study_id,
                        persona_id=p_id,
                        persona_name=p_name,
                        messages=[
                            msg
                            for qa in result["qa"]
                            for msg in [
                                {"role": "user", "content": qa["question"]},
                                {"role": "assistant", "content": qa["answer"]},
                            ]
                        ],
                    )
                    new_db.add(interview)
                    await new_db.commit()

                await q.put((
                    'interview_done',
                    {'persona_id': p_id, 'persona_name': p_name, 'qa_count': result.get('total_questions', len(result["qa"]))}
                ))

            except Exception as e:
                logger.error(f"[AutoInterview] persona {p_id} 访谈失败: {e}")
                await q.put((
                    'interview_start',
                    {'persona_id': p_id, 'persona_name': p_name, 'index': index, 'total': total}
                ))
                await q.put((
                    'qa',
                    {'persona_id': p_id, 'persona_name': p_name, 'index': 0, 'question': '（访谈失败）', 'answer': str(e)}
                ))
                await q.put((
                    'interview_done',
                    {'persona_id': p_id, 'persona_name': p_name, 'qa_count': 0}
                ))

        # ── 并行启动所有人设的访谈任务 ──────────────────────────────
        persona_queues: dict[str, asyncio.Queue] = {}
        interview_tasks: list[asyncio.Task] = []

        for i, persona in enumerate(personas):
            q: asyncio.Queue = asyncio.Queue()
            persona_queues[persona.id] = q
            task = asyncio.create_task(interview_persona(persona, i, len(personas), q))
            interview_tasks.append(task)

        # ── 主循环：实时收集各人设的事件并 yield ───────────────────
        pending_tasks = set(interview_tasks)
        while pending_tasks:
            for p_id, q in persona_queues.items():
                while not q.empty():
                    evt_type, evt_data = await q.get()
                    if evt_type == 'interview_start':
                        yield f"data: {json.dumps({'type': 'interview_start', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'qa':
                        yield f"data: {json.dumps({'type': 'qa', **evt_data}, ensure_ascii=False)}\n\n"
                    elif evt_type == 'interview_done':
                        yield f"data: {json.dumps({'type': 'interview_done', **evt_data}, ensure_ascii=False)}\n\n"

            done_tasks = {t for t in pending_tasks if t.done()}
            for t in done_tasks:
                for p_id, q in persona_queues.items():
                    while not q.empty():
                        evt_type, evt_data = await q.get()
                        if evt_type == 'interview_start':
                            yield f"data: {json.dumps({'type': 'interview_start', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'qa':
                            yield f"data: {json.dumps({'type': 'qa', **evt_data}, ensure_ascii=False)}\n\n"
                        elif evt_type == 'interview_done':
                            yield f"data: {json.dumps({'type': 'interview_done', **evt_data}, ensure_ascii=False)}\n\n"
                pending_tasks.discard(t)

            if pending_tasks:
                await asyncio.sleep(0.05)

        # ── 更新研究状态 ────────────────────────────────────────────
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            study_to_update = await new_db.get(Study, request.study_id)
            if study_to_update:
                study_to_update.current_phase = "interviewing"
                await new_db.commit()

        yield f"data: {json.dumps({'type': 'step', 'step': 'auto_interview', 'status': 'done', 'total_personas': len(personas), 'questions_per_persona': len(questions)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── Step 5: generateReport ──────────────────────────────────────────

@router.post("/generate-report")
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Step 5: 将人设数据与访谈洞察合成可指导决策的研究报告。

    返回：流式输出报告内容（Markdown 格式）
    """
    study = await db.get(Study, request.study_id)
    if not study or study.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="研究不存在")

    personas = request.personas
    interviews = request.interview_transcripts

    # 获取数据库中的数据作为备选
    if not personas:
        result = await db.execute(
            select(StudyPersona).where(StudyPersona.study_id == request.study_id)
        )
        db_personas = result.scalars().all()
        personas = [p.persona_data for p in db_personas]

    if not interviews:
        result = await db.execute(
            select(StudyInterview).where(StudyInterview.study_id == request.study_id)
        )
        db_interviews = result.scalars().all()
        interviews = [
            {"persona_id": i.persona_id, "persona_name": i.persona_name, "messages": i.messages}
            for i in db_interviews
        ]

    scout_result = await db.execute(
        select(ScoutResult).where(ScoutResult.study_id == request.study_id)
    )
    scout_data = scout_result.scalars().first()
    scout_insights = scout_data.insights if scout_data else []

    system_prompt = """你是一位资深市场研究专家，擅长将定性研究数据转化为可指导商业决策的专业报告。

你的报告必须遵循以下结构，每个章节都要有实质性内容：

## 一、执行摘要（200字左右）
- 研究背景与目的（一句话概括）
- 3-5 条关键发现（每条带数据或用户原话支撑）
- 核心行动建议摘要

## 二、研究方法（150字左右）
- 研究方法说明：AI 模拟用户深度访谈 + 社交媒体舆情分析
- 样本概况：必须明确说明用户画像数量、覆盖的人群特征
- 研究局限性：诚实说明本研究的局限

## 三、用户画像分析（500字左右）
- 人群整体特征概述
- 逐一介绍每位用户画像（人口统计、行为特征、心理特征、核心痛点）
- 用户决策路径/购买旅程分析
- 痛点优先级排序（按严重程度）

## 四、核心发现（600字左右）
每个发现包含：
- 发现主题
- 具体描述
- 用户原话引用（带说话人名字）
- 假设验证情况（"验证"或"推翻"）

## 五、竞品与市场洞察（300字左右）
- 用户对现有产品/服务的评价
- 市场趋势判断
- 竞品优劣势对比

## 六、机会与建议（500字左右）
### 短期建议（1-3个月可执行）
- 具体行动项 + 预期效果 + 优先级

### 中长期建议（3-12个月）
- 具体行动项 + 预期效果 + 优先级

### 风险提示
- 执行风险、市场变化风险

## 七、附录
- 研究数据统计（访谈人数、问题数量等）
- 假设验证矩阵表（表格形式）

写作要求：
- 报告中必须包含所有用户画像的信息，不能遗漏任何一位受访者
- 用具体的访谈引用支撑观点（必须有引号和说话人名字）
- 区分"验证的假设"和"被推翻的假设"
- 建议要具体可行，有优先级
- 使用 Markdown 格式，适当使用表格
- 总字数 2500-3500 字"""

    # 构建完整的访谈记录（不截断）
    interview_summary = ""
    total_questions = 0
    for idx, interview in enumerate(interviews):
        name = interview.get("persona_name", f"受访者{idx+1}")
        persona_id = interview.get("persona_id", "")
        msgs = interview.get("messages", [])
        if msgs:
            qa_pairs = []
            for i in range(0, len(msgs)-1, 2):
                q = msgs[i].get("content", "") if i < len(msgs) else ""
                a = msgs[i+1].get("content", "") if i+1 < len(msgs) else ""
                if q and a:
                    qa_pairs.append(f"**问：** {q}\n**{name} 答：** {a}")
                    total_questions += 1
            interview_summary += f"\n### {name} 的访谈（共 {len(qa_pairs)} 轮问答）\n" + "\n\n".join(qa_pairs) + "\n"

    # 构建完整的用户画像数据（不截断）
    persona_details = []
    for p in personas:
        persona_info = {
            "姓名": p.get("name", "未知"),
            "年龄": p.get("age", "未知"),
            "职业": p.get("occupation", "未知"),
            "城市": p.get("city", "未知"),
            "背景": p.get("background", ""),
            "性格特征": p.get("personality", ""),
            "消费习惯": p.get("consumer_habits", ""),
            "核心痛点": p.get("pain_points", ""),
            "动机": p.get("motivations", ""),
            "数字行为": p.get("digital_behavior", ""),
            "核心价值观": p.get("core_values", []),
            "态度": p.get("attitude", ""),
        }
        persona_details.append(persona_info)

    user_prompt = f"""请基于以下完整的研究数据，生成一份专业的市场调研报告。

## 研究背景
{study.user_request or '未提供研究背景'}

## 研究设计框架
{study.design_content or '未提供研究设计'}

## 用户画像详情（共 {len(personas)} 人）
{json.dumps(persona_details, ensure_ascii=False, indent=2)}

## 社交媒体舆情洞察（共 {len(scout_insights)} 条）
{json.dumps(scout_insights, ensure_ascii=False, indent=2) if scout_insights else '本次研究暂未收集社媒数据'}

## 深度访谈记录（共 {len(interviews)} 位受访者，{total_questions} 轮问答）
{interview_summary if interview_summary else '暂无访谈数据'}

---
请严格按照上述七个章节结构，生成完整的市场调研报告（Markdown 格式）。

重要提示：
1. 报告中必须逐一介绍所有 {len(personas)} 位用户画像，不能遗漏
2. 访谈发现要涵盖所有 {len(interviews)} 位受访者的观点
3. 每个发现都要有用户原话引用支撑
4. 建议要具体可行，有优先级"""

    async def stream_generator():
        full_report = ""
        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_report', 'status': 'running'}, ensure_ascii=False)}\n\n"

        async for chunk in _llm_stream([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], temperature=0.6):
            full_report += chunk
            yield f"data: {json.dumps({'type': 'content', 'delta': chunk}, ensure_ascii=False)}\n\n"

        # 保存报告 - 使用新的 session
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_db:
            report = StudyReport(
                study_id=request.study_id,
                content=full_report,
                format=request.format,
            )
            new_db.add(report)
            study_to_update = await new_db.get(Study, request.study_id)
            if study_to_update:
                study_to_update.status = "completed"
                study_to_update.current_phase = "completed"
            await new_db.commit()

        yield f"data: {json.dumps({'type': 'step', 'step': 'generate_report', 'status': 'done'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ── 工具接口 ─────────────────────────────────────────────────────────

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

    extracted_text = ""
    if filename.endswith((".txt", ".md")):
        try:
            extracted_text = content.decode("utf-8")
        except Exception:
            extracted_text = content.decode("latin-1", errors="ignore")
    else:
        extracted_text = f"[已上传文件: {filename}，共 {len(content)} 字节。如需提取内容，请使用 PDF/TXT 格式文件。]"

    return ApiResponse.ok({
        "filename": filename,
        "size": len(content),
        "extracted_text": extracted_text[:2000],
    })


# ── 全自动研究 API（API Key 认证）────────────────────────────────────

class AutoResearchRequest(BaseModel):
    """全自动研究请求"""
    user_request: str = Field(..., description="研究需求（自然语言）")
    persona_count: int = Field(5, ge=1, le=10, description="生成的人设数量")
    platforms: list[str] = Field(["小红书", "微博", "抖音"], description="社媒侦察平台")


@router.post("/auto-research")
async def auto_research(
    request: AutoResearchRequest,
    current_user: User = Depends(get_user_by_api_key),
):
    """
    全自动市场研究 API（通过 X-API-Key 认证）

    输入研究需求，自动完成：
    1. 设计研究框架
    2. 生成用户人设
    3. 社交媒体侦察
    4. 自动深度访谈
    5. 生成研究报告

    返回：流式 SSE 响应，包含每个步骤的进度和结果
    """
    from app.core.database import AsyncSessionLocal

    # 创建 Study 记录
    title = request.user_request[:30] + ("..." if len(request.user_request) > 30 else "")
    async with AsyncSessionLocal() as db:
        study = Study(
            user_id=current_user.id,
            title=title,
            user_request=request.user_request,
            status="in_progress",
            current_phase="designing",
        )
        db.add(study)
        await db.commit()
        await db.refresh(study)
        study_id = study.id

    # 检查积分（超级管理员不需要检查）
    if not current_user.is_superuser:
        if current_user.credits < TASK_COST_CREDITS:
            raise HTTPException(
                status_code=402,
                detail=f"积分不足，当前积分 {current_user.credits}，需要 {TASK_COST_CREDITS} 积分"
            )

    user_id = current_user.id
    has_deducted_credits = False

    async def stream_generator():
        nonlocal has_deducted_credits
        task_completed = False

        # 发送开始事件
        yield f"data: {json.dumps({'type': 'study_id', 'study_id': study_id}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'step', 'step': 'auto_research', 'status': 'running', 'message': '开始全自动市场研究...'}, ensure_ascii=False)}\n\n"

        try:
            # ═══════════════════════════════════════════════════════
            # Step 1: 设计研究框架
            # ═══════════════════════════════════════════════════════
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'design', 'status': 'running', 'message': '正在设计研究框架...'}, ensure_ascii=False)}\n\n"

            design_content = ""
            design_system = """你是一位资深的定性用户研究员，擅长设计用户访谈框架。
你的任务是分析用户的研究需求，帮助他们：
1. 明确研究目标（清晰、可验证）
2. 定义目标人群
3. 设计访谈框架（分阶段，从暖场到深挖）
4. 提出初始假设（基于常识和行业知识）

请用结构化的方式输出，让研究员可以直接使用。"""

            design_user = f"""研究需求：
{request.user_request}

请帮我设计一个完整的定性用户研究方案，包括：
1. 研究目标（1-2句话）
2. 目标人群画像描述
3. 访谈框架（3-4个阶段，每阶段2-3个核心问题）
4. 初始假设（3-5个基于现有认知的假设）

用清晰的中文输出。"""

            async for chunk in _llm_stream([
                {"role": "system", "content": design_system},
                {"role": "user", "content": design_user},
            ]):
                design_content += chunk
                yield f"data: {json.dumps({'type': 'design_content', 'delta': chunk}, ensure_ascii=False)}\n\n"

            # 保存设计内容
            async with AsyncSessionLocal() as new_db:
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.design_content = design_content
                    study_to_update.current_phase = "post-design"
                    await new_db.commit()

            yield f"data: {json.dumps({'type': 'phase', 'phase': 'design', 'status': 'done'}, ensure_ascii=False)}\n\n"

            # ═══════════════════════════════════════════════════════
            # Step 2: 生成用户人设
            # ═══════════════════════════════════════════════════════
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'personas', 'status': 'running', 'message': f'正在生成 {request.persona_count} 个用户人设...'}, ensure_ascii=False)}\n\n"

            # 扣除积分
            async with AsyncSessionLocal() as new_db:
                user_to_deduct = await new_db.get(User, user_id)
                if user_to_deduct and not user_to_deduct.is_superuser:
                    if user_to_deduct.credits >= TASK_COST_CREDITS:
                        user_to_deduct.credits -= TASK_COST_CREDITS
                        await new_db.commit()
                        has_deducted_credits = True
                        yield f"data: {json.dumps({'type': 'credits_deducted', 'amount': TASK_COST_CREDITS, 'remaining': user_to_deduct.credits}, ensure_ascii=False)}\n\n"

            persona_system = """你是一位消费者洞察专家，擅长构建真实、有深度的用户画像。
请基于研究背景，生成具有代表性的目标用户画像。每个人设要：
- 有真实的生活背景和动机
- 体现出对研究主题的不同态度（支持/中立/怀疑）
- 有具体的痛点和期望
- 严格按照 JSON 格式输出"""

            persona_user = f"""研究背景：
{design_content[:500]}

目标人群描述：根据研究背景自行判断

请生成 {request.persona_count} 个用户人设，确保覆盖不同年龄、职业、态度、使用场景的关键人群。

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
      "attitude": "这类用户对该话题持什么态度（2-3句）"
    }}
  ]
}}"""

            try:
                persona_result = await _llm_complete(
                    [{"role": "system", "content": persona_system}, {"role": "user", "content": persona_user}],
                    temperature=0.85,
                    json_mode=True,
                )
                personas_data = json.loads(persona_result).get("personas", [])
            except Exception as e:
                logger.error(f"人设生成失败: {e}")
                personas_data = []

            # 保存人设到数据库
            personas = []
            for i, p in enumerate(personas_data[:request.persona_count]):
                persona_id = str(uuid.uuid4())
                persona = {**p, "id": persona_id, "source": "generated"}
                personas.append(persona)

                async with AsyncSessionLocal() as new_db:
                    db_persona = StudyPersona(
                        id=persona_id,
                        study_id=study_id,
                        name=p.get("name", f"用户{i+1}"),
                        age=p.get("age"),
                        occupation=p.get("occupation", ""),
                        city=p.get("city", ""),
                        background=p.get("background", ""),
                        persona_data=p,
                        source="generated",
                    )
                    new_db.add(db_persona)
                    await new_db.commit()

                yield f"data: {json.dumps({'type': 'persona', 'index': i, 'persona': persona}, ensure_ascii=False)}\n\n"

            async with AsyncSessionLocal() as new_db:
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.current_phase = "personas"
                    await new_db.commit()

            yield f"data: {json.dumps({'type': 'phase', 'phase': 'personas', 'status': 'done', 'count': len(personas)}, ensure_ascii=False)}\n\n"

            # ═══════════════════════════════════════════════════════
            # Step 3: 社交媒体侦察
            # ═══════════════════════════════════════════════════════
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'scout', 'status': 'running', 'message': '正在进行社交媒体侦察...'}, ensure_ascii=False)}\n\n"

            # 从研究标题提取关键词
            keywords = title.replace("...", "").split()[:3] or ["用户研究"]

            for persona in personas:
                p_id = persona["id"]
                p_name = persona.get("name", "用户")
                p_desc = f"{p_name}，{persona.get('age', '')}岁，{persona.get('occupation', '')}，{persona.get('background', '')[:100]}"

                # 生成专属关键词
                kw_prompt = f"""根据以下用户画像和研究主题，生成 2-3 个精准的社交媒体搜索关键词组合。
用户画像：{p_desc}
研究主题：{title}
JSON 输出：{{"keywords": ["关键词1 关键词2"]}}"""

                try:
                    kw_result = await _llm_complete([{"role": "user", "content": kw_prompt}], temperature=0.7, json_mode=True)
                    kw_data = json.loads(kw_result)
                    persona_kw = kw_data.get("keywords", keywords)
                except Exception:
                    persona_kw = keywords

                yield f"data: {json.dumps({'type': 'scout_start', 'persona_id': p_id, 'persona_name': p_name, 'keywords': persona_kw}, ensure_ascii=False)}\n\n"

                # 社媒内容搜索
                scout_prompt = f"""你是一位擅长网络内容分析的研究员。
请模拟从 {', '.join(request.platforms)} 平台上搜索关键词 "{', '.join(persona_kw)}" 的真实用户内容。
目标用户画像：{p_desc}
生成 5-8 条该类用户可能发布的真实帖子/评论。

JSON 格式输出：
{{
  "posts": [{{"platform": "小红书", "content": "...", "sentiment": "positive"}}],
  "insights": ["核心洞察1", "核心洞察2"]
}}"""

                try:
                    scout_result = await _llm_complete([{"role": "user", "content": scout_prompt}], temperature=0.8, json_mode=True)
                    scout_data = json.loads(scout_result)
                    posts = scout_data.get("posts", [])
                    insights = scout_data.get("insights", [])
                except Exception as e:
                    logger.error(f"社媒侦察失败: {e}")
                    posts, insights = [], []

                # 发送帖子
                for post in posts:
                    yield f"data: {json.dumps({'type': 'post', 'persona_id': p_id, 'post': {**post, 'persona_name': p_name}}, ensure_ascii=False)}\n\n"

                # 人设增强
                if posts:
                    rebuild_prompt = f"""你是一位资深用户研究员，正在用真实社交媒体数据重构用户画像。
原始人设：{json.dumps(persona, ensure_ascii=False)}
社媒声音：{json.dumps(posts, ensure_ascii=False)}
洞察：{', '.join(insights)}
任务：根据真实数据，更新这个人设的态度、痛点、语言风格，并添加 "scouted_updates" 字段说明修改原因。"""

                    try:
                        updated_result = await _llm_complete([{"role": "user", "content": rebuild_prompt}], temperature=0.6, json_mode=True)
                        updated_persona = json.loads(updated_result)
                        updated_persona["id"] = p_id
                        updated_persona["source"] = "scouted"

                        async with AsyncSessionLocal() as new_db:
                            persona_to_update = await new_db.get(StudyPersona, p_id)
                            if persona_to_update:
                                persona_to_update.persona_data = updated_persona
                                persona_to_update.source = "scouted"
                                await new_db.commit()

                        yield f"data: {json.dumps({'type': 'updated_persona', 'persona_id': p_id, 'persona': updated_persona}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.error(f"人设增强失败: {e}")

                yield f"data: {json.dumps({'type': 'scout_done', 'persona_id': p_id, 'persona_name': p_name, 'posts_count': len(posts)}, ensure_ascii=False)}\n\n"

            async with AsyncSessionLocal() as new_db:
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.current_phase = "scouting"
                    await new_db.commit()

            yield f"data: {json.dumps({'type': 'phase', 'phase': 'scout', 'status': 'done'}, ensure_ascii=False)}\n\n"

            # ═══════════════════════════════════════════════════════
            # Step 4: 自动深度访谈
            # ═══════════════════════════════════════════════════════
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'interview', 'status': 'running', 'message': '正在进行自动深度访谈...'}, ensure_ascii=False)}\n\n"

            # 提取访谈问题
            questions = await _extract_interview_questions(design_content)
            if not questions:
                questions = [
                    "你能简单介绍一下自己和你目前的生活状态吗？",
                    f"关于{title}，你目前的了解和看法是什么？",
                    "在做出相关决策时，你最看重哪些因素？",
                    "你之前有没有类似的经历？可以分享一下吗？",
                    "什么情况下你会决定尝试或购买？什么会让你犹豫？",
                ]

            yield f"data: {json.dumps({'type': 'interview_questions', 'questions': questions, 'count': len(questions)}, ensure_ascii=False)}\n\n"

            interview_transcripts = []
            for idx, persona in enumerate(personas):
                p_id = persona["id"]
                p_name = persona.get("name", "用户")

                yield f"data: {json.dumps({'type': 'interview_start', 'persona_id': p_id, 'persona_name': p_name, 'index': idx}, ensure_ascii=False)}\n\n"

                # 执行访谈
                system_prompt = f"""你正在扮演 {p_name}（{persona.get('age', '')}岁，{persona.get('occupation', '')}）参与深度访谈。
背景：{persona.get('background', '')}
人设详情：{json.dumps(persona, ensure_ascii=False)}
要求：
- 完全以第一人称，口语化中文回答
- 体现角色的真实性格、矛盾感、生活经历
- 每个问题回答 2-4 句话，有具体细节"""

                messages = [{"role": "system", "content": system_prompt}]
                qa_records = []

                for question in questions:
                    messages.append({"role": "user", "content": question})
                    try:
                        answer = await _llm_complete(messages, temperature=0.75)
                    except Exception as e:
                        answer = f"（回答失败：{str(e)}）"

                    messages.append({"role": "assistant", "content": answer})
                    qa_records.append({"question": question, "answer": answer})

                    yield f"data: {json.dumps({'type': 'qa', 'persona_id': p_id, 'question': question, 'answer': answer}, ensure_ascii=False)}\n\n"

                # 保存访谈记录
                async with AsyncSessionLocal() as new_db:
                    interview = StudyInterview(
                        study_id=study_id,
                        persona_id=p_id,
                        persona_name=p_name,
                        messages=[
                            msg
                            for qa in qa_records
                            for msg in [
                                {"role": "user", "content": qa["question"]},
                                {"role": "assistant", "content": qa["answer"]},
                            ]
                        ],
                    )
                    new_db.add(interview)
                    await new_db.commit()

                interview_transcripts.append({
                    "persona_id": p_id,
                    "persona_name": p_name,
                    "messages": messages[1:],  # 去掉 system
                })

                yield f"data: {json.dumps({'type': 'interview_done', 'persona_id': p_id, 'persona_name': p_name, 'qa_count': len(qa_records)}, ensure_ascii=False)}\n\n"

            async with AsyncSessionLocal() as new_db:
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.current_phase = "interviewing"
                    await new_db.commit()

            yield f"data: {json.dumps({'type': 'phase', 'phase': 'interview', 'status': 'done'}, ensure_ascii=False)}\n\n"

            # ═══════════════════════════════════════════════════════
            # Step 5: 生成研究报告
            # ═══════════════════════════════════════════════════════
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'report', 'status': 'running', 'message': '正在生成研究报告...'}, ensure_ascii=False)}\n\n"

            report_system = """你是一位资深市场研究专家，擅长将定性研究数据转化为可指导商业决策的专业报告。

报告结构：
## 一、执行摘要（200字）
## 二、研究方法（150字）
## 三、用户画像分析（500字）
## 四、核心发现（600字）
## 五、竞品与市场洞察（300字）
## 六、机会与建议（500字）
## 七、附录

写作要求：
- 必须包含所有用户画像信息
- 用具体的访谈引用支撑观点
- 建议要具体可行，有优先级
- 使用 Markdown 格式"""

            # 构建访谈摘要
            interview_summary = ""
            for t in interview_transcripts:
                interview_summary += f"\n### {t['persona_name']} 的访谈\n"
                msgs = t["messages"]
                for i in range(0, len(msgs)-1, 2):
                    if msgs[i]["role"] == "user" and msgs[i+1]["role"] == "assistant":
                        interview_summary += f"**问：** {msgs[i]['content']}\n**答：** {msgs[i+1]['content']}\n\n"

            report_user = f"""研究背景：{request.user_request}

研究设计：{design_content}

用户画像（共 {len(personas)} 人）：{json.dumps(personas, ensure_ascii=False, indent=2)}

深度访谈记录：{interview_summary}

请生成完整的市场调研报告（Markdown 格式，2500-3500 字）。"""

            full_report = ""
            async for chunk in _llm_stream([
                {"role": "system", "content": report_system},
                {"role": "user", "content": report_user},
            ], temperature=0.6):
                full_report += chunk
                yield f"data: {json.dumps({'type': 'report_content', 'delta': chunk}, ensure_ascii=False)}\n\n"

            # 保存报告
            async with AsyncSessionLocal() as new_db:
                report = StudyReport(
                    study_id=study_id,
                    content=full_report,
                    format="markdown",
                )
                new_db.add(report)
                study_to_update = await new_db.get(Study, study_id)
                if study_to_update:
                    study_to_update.status = "completed"
                    study_to_update.current_phase = "completed"
                await new_db.commit()

            yield f"data: {json.dumps({'type': 'phase', 'phase': 'report', 'status': 'done'}, ensure_ascii=False)}\n\n"

            # ═══════════════════════════════════════════════════════
            # 完成
            # ═══════════════════════════════════════════════════════
            task_completed = True
            yield f"data: {json.dumps({'type': 'step', 'step': 'auto_research', 'status': 'done', 'study_id': study_id, 'report_length': len(full_report)}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except asyncio.CancelledError:
            logger.warning(f"[自动研究] 流式响应被取消，用户 {user_id}")
            raise
        except Exception as e:
            logger.error(f"[自动研究] 研究失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            raise
        finally:
            # 如果任务未完成，返还积分
            if not task_completed and has_deducted_credits:
                async with AsyncSessionLocal() as new_db:
                    user_to_refund = await new_db.get(User, user_id)
                    if user_to_refund:
                        user_to_refund.credits += TASK_COST_CREDITS
                        await new_db.commit()
                        logger.info(f"[积分] 自动研究未完成，返还 {TASK_COST_CREDITS} 积分给用户 {user_to_refund.email}")
                        try:
                            yield f"data: {json.dumps({'type': 'credits_refund', 'amount': TASK_COST_CREDITS, 'message': '任务中断，积分已返还'}, ensure_ascii=False)}\n\n"
                        except:
                            pass

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
