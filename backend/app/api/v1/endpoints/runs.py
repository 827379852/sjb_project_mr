"""
调研运行控制与结果接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.core.response import ApiResponse, PaginatedData
from app.core.exceptions import NotFoundError, AppException, AgentBackendError
from app.models.research_project import ResearchProject, ProjectStatus
from app.models.questionnaire import Questionnaire
from app.models.respondent import RespondentConfig, Respondent
from app.models.research_run import ResearchRun, SurveyResponse, RunStatus
from app.schemas.run import RunCreate, RunOut, SurveyResponseOut, RunAnalyticsOut, QuestionStats
from app.adapters.factory import get_agent_backend
from loguru import logger

router = APIRouter(prefix="/runs", tags=["调研执行"])


# ── 运行控制 ───────────────────────────────────────────────────────

@router.post("", response_model=ApiResponse[RunOut], status_code=201)
async def start_run(
    payload: RunCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    启动一次调研运行。
    流程：
    1. 验证项目、问卷、受访者配置均已就绪
    2. 获取受访者 Agent 列表（如未生成则先生成）
    3. 调用 Agent 后端创建并启动实验
    4. 返回运行记录（异步执行，前端轮询进度）
    """
    # 1. 校验项目
    project = await db.get(ResearchProject, payload.project_id)
    if not project:
        raise NotFoundError("调研项目", payload.project_id)
    if not project.questionnaire_id:
        raise AppException("项目未配置问卷，请先绑定问卷", code=400)
    if not project.respondent_config_id:
        raise AppException("项目未配置受访者，请先设置受访者配置", code=400)

    # 2. 加载问卷
    questionnaire = await db.get(Questionnaire, project.questionnaire_id)
    if not questionnaire:
        raise NotFoundError("问卷", project.questionnaire_id)

    # 3. 加载受访者
    respondent_config = await db.get(RespondentConfig, project.respondent_config_id)
    if not respondent_config:
        raise NotFoundError("受访者配置", project.respondent_config_id)

    respondents = (await db.execute(
        select(Respondent).where(Respondent.config_id == respondent_config.id)
    )).scalars().all()

    if not respondents:
        raise AppException("受访者列表为空，请先生成受访者档案（调用 /respondent-configs/{id}/generate）", code=400)

    count = payload.override_respondent_count or len(respondents)
    selected_respondents = list(respondents)[:count]

    # 4. 创建运行记录
    run = ResearchRun(
        project_id=project.id,
        status=RunStatus.INITIALIZING,
        total_respondents=len(selected_respondents),
        run_config_snapshot={
            "questionnaire_id": questionnaire.id,
            "questionnaire_name": questionnaire.name,
            "respondent_config_id": respondent_config.id,
            "respondent_count": len(selected_respondents),
        },
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # 5. 更新项目状态
    project.status = ProjectStatus.RUNNING
    project.last_run_id = run.id

    # 6. 调用 Agent 后端启动实验（后台异步执行）
    try:
        backend = get_agent_backend()

        from app.adapters.base import AgentProfile
        agent_profiles = [
            AgentProfile(
                agent_id=r.agent_backend_id or r.id,
                name=r.name,
                profile=r.profile or {},
            )
            for r in selected_respondents
        ]

        experiment_id = await backend.create_experiment(
            project_id=project.id,
            agents=agent_profiles,
            questionnaire_schema=questionnaire.schema,
            config={},
        )

        run.backend_experiment_id = experiment_id
        run.status = RunStatus.RUNNING

        await backend.start_experiment(experiment_id)

        # 后台监控任务（在实际生产中推荐使用 Celery / APScheduler）
        import asyncio
        asyncio.create_task(_monitor_run(run.id, experiment_id))

    except Exception as e:
        run.status = RunStatus.FAILED
        run.error_message = str(e)
        logger.error(f"启动实验失败: {e}")

    await db.flush()
    await db.refresh(run)
    return ApiResponse.ok(RunOut.model_validate(run), message="调研已启动")


@router.get("/{run_id}", response_model=ApiResponse[RunOut])
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """获取运行详情与当前进度"""
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise NotFoundError("运行记录", run_id)

    # 同步后端状态
    if run.status in (RunStatus.RUNNING, RunStatus.ANALYZING) and run.backend_experiment_id:
        try:
            backend = get_agent_backend()
            status = await backend.get_experiment_status(run.backend_experiment_id)
            run.progress = status.progress
            run.completed_respondents = status.completed
            run.input_tokens = status.input_tokens
            run.output_tokens = status.output_tokens

            if status.status == "completed" and run.status != RunStatus.COMPLETED:
                # 直接在本次请求内同步写入结果（简单实现，生产用后台任务）
                await _collect_results(run.id, run.backend_experiment_id, db)
            elif status.status in ("failed", "cancelled"):
                run.status = RunStatus.FAILED
                run.error_message = status.error
        except Exception as e:
            logger.warning(f"同步运行状态失败: {e}")

    return ApiResponse.ok(RunOut.model_validate(run))


@router.post("/{run_id}/cancel", response_model=ApiResponse[RunOut])
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db)):
    """取消正在进行的调研"""
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise NotFoundError("运行记录", run_id)
    if run.status not in (RunStatus.RUNNING, RunStatus.INITIALIZING):
        raise AppException(f"运行状态为 {run.status}，无法取消", code=400)

    backend = get_agent_backend()
    if run.backend_experiment_id:
        await backend.stop_experiment(run.backend_experiment_id)

    run.status = RunStatus.CANCELLED
    await db.flush()
    await db.refresh(run)
    return ApiResponse.ok(RunOut.model_validate(run), message="调研已取消")


@router.get("", response_model=ApiResponse[PaginatedData[RunOut]])
async def list_runs(
    project_id: Optional[str] = Query(None, description="按项目 ID 筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取运行记录列表"""
    query = select(ResearchRun).order_by(ResearchRun.created_at.desc())
    if project_id:
        query = query.where(ResearchRun.project_id == project_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    items = (await db.execute(query.offset((page-1)*page_size).limit(page_size))).scalars().all()

    return ApiResponse.ok(PaginatedData.build(
        items=[RunOut.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size,
    ))


# ── 调研结果 ───────────────────────────────────────────────────────

@router.get("/{run_id}/responses", response_model=ApiResponse[PaginatedData[SurveyResponseOut]])
async def list_responses(
    run_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """获取所有受访者的问卷回答"""
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise NotFoundError("运行记录", run_id)

    query = select(SurveyResponse).where(SurveyResponse.run_id == run_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    items = (await db.execute(query.offset((page-1)*page_size).limit(page_size))).scalars().all()

    return ApiResponse.ok(PaginatedData.build(
        items=[SurveyResponseOut.model_validate(r) for r in items],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/{run_id}/analytics", response_model=ApiResponse[RunAnalyticsOut])
async def get_analytics(run_id: str, db: AsyncSession = Depends(get_db)):
    """
    获取调研结果统计分析。
    包括各题目频率分布、量表均值、开放题主题、情感分布、关键洞察等。
    """
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise NotFoundError("运行记录", run_id)
    if run.status not in (RunStatus.COMPLETED, RunStatus.ANALYZING):
        raise AppException(f"调研尚未完成（当前状态：{run.status}），暂无分析结果", code=400)

    # 获取问卷 schema
    project = await db.get(ResearchProject, run.project_id)
    questionnaire = await db.get(Questionnaire, project.questionnaire_id)

    # 获取所有回答
    responses = (await db.execute(
        select(SurveyResponse).where(SurveyResponse.run_id == run_id)
    )).scalars().all()

    analytics = await _build_analytics(run, questionnaire, responses)
    return ApiResponse.ok(analytics)


@router.get("/{run_id}/responses/{respondent_id}/dialog", response_model=ApiResponse[list])
async def get_agent_dialog(
    run_id: str,
    respondent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取指定受访者的完整对话记录"""
    response = (await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.run_id == run_id,
            SurveyResponse.respondent_id == respondent_id,
        )
    )).scalar_one_or_none()

    if not response:
        raise NotFoundError("问卷回答", respondent_id)
    return ApiResponse.ok(response.raw_dialog)


# ── 辅助函数 ───────────────────────────────────────────────────────

async def _monitor_run(run_id: str, experiment_id: str) -> None:
    """后台监控实验完成，收集结果写入数据库"""
    import asyncio
    from app.core.database import AsyncSessionLocal

    backend = get_agent_backend()
    max_retries = 120  # 最多等待 10 分钟

    for _ in range(max_retries):
        await asyncio.sleep(5)
        try:
            status = await backend.get_experiment_status(experiment_id)
            if status.status in ("completed", "failed", "cancelled"):
                break
        except Exception as e:
            logger.warning(f"监控实验 {experiment_id} 失败: {e}")

    # 收集结果
    async with AsyncSessionLocal() as db:
        await _collect_results(run_id, experiment_id, db)
        await db.commit()


async def _collect_results(run_id: str, experiment_id: str, db: AsyncSession) -> None:
    """从 Agent 后端收集问卷结果并写入数据库"""
    run = await db.get(ResearchRun, run_id)
    if not run:
        return

    backend = get_agent_backend()
    results = await backend.collect_survey_results(experiment_id)

    # 加载受访者映射
    project = await db.get(ResearchProject, run.project_id)
    respondent_config = await db.get(RespondentConfig, project.respondent_config_id)
    respondents = (await db.execute(
        select(Respondent).where(Respondent.config_id == respondent_config.id)
    )).scalars().all()

    agent_to_respondent = {r.agent_backend_id or r.id: r.id for r in respondents}

    for result in results:
        respondent_id = agent_to_respondent.get(result.agent_id, result.agent_id)
        survey_resp = SurveyResponse(
            run_id=run_id,
            respondent_id=respondent_id,
            questionnaire_id=project.questionnaire_id,
            answers=result.answers,
            raw_dialog=result.raw_dialog,
            sentiment=result.sentiment,
        )
        db.add(survey_resp)

    run.status = RunStatus.COMPLETED
    run.completed_respondents = len(results)
    run.progress = 100
    run.completed_at = datetime.utcnow()

    # 更新项目状态
    project.status = ProjectStatus.COMPLETED
    await db.flush()


async def _build_analytics(run: ResearchRun, questionnaire: Questionnaire, responses: list[SurveyResponse]) -> RunAnalyticsOut:
    """计算统计分析结果"""
    from collections import Counter
    import statistics

    schema = questionnaire.schema or {}
    all_questions = []
    for section in schema.get("sections", []):
        all_questions.extend(section.get("questions", []))

    question_stats = []
    for q in all_questions:
        q_id = q["id"]
        q_type = q["type"]
        q_text = q["text"]

        all_answers = [r.answers.get(q_id) for r in responses if r.answers.get(q_id) is not None]
        total = len(all_answers)

        stat = QuestionStats(
            question_id=q_id,
            question_text=q_text,
            question_type=q_type,
            total_responses=total,
        )

        if q_type == "single_choice" and all_answers:
            counter = Counter(all_answers)
            stat.option_distribution = dict(counter)
            stat.option_percentage = {k: round(v/total*100, 1) for k, v in counter.items()}

        elif q_type == "multi_choice" and all_answers:
            flat = [item for sublist in all_answers for item in (sublist if isinstance(sublist, list) else [sublist])]
            counter = Counter(flat)
            stat.option_distribution = dict(counter)
            stat.option_percentage = {k: round(v/len(all_answers)*100, 1) for k, v in counter.items()}

        elif q_type in ("scale", "nps") and all_answers:
            nums = [float(a) for a in all_answers if isinstance(a, (int, float))]
            if nums:
                stat.mean = round(statistics.mean(nums), 2)
                stat.median = statistics.median(nums)
                stat.std_dev = round(statistics.stdev(nums), 2) if len(nums) > 1 else 0.0

        elif q_type == "text" and all_answers:
            # 简单关键词提取（生产环境可接入 NLP）
            stat.themes = [{"theme": "待分析", "count": total}]

        question_stats.append(stat)

    # 情感分布
    sentiment_counter = Counter(r.sentiment for r in responses)

    return RunAnalyticsOut(
        run_id=run.id,
        project_id=run.project_id,
        total_respondents=len(responses),
        completed_at=run.completed_at,
        question_stats=question_stats,
        overall_sentiment=dict(sentiment_counter),
        key_insights=[
            f"共收集 {len(responses)} 份有效问卷",
            f"正面评价占比 {round(sentiment_counter.get('positive', 0)/max(len(responses), 1)*100, 1)}%",
        ],
        summary_report=f"## 调研摘要\n\n共 {len(responses)} 位受访者完成问卷。",
        demographic_breakdown={},
    )