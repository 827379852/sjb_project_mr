"""
任务队列管理服务
============================================
实现用户级并发控制和排队机制

核心设计：
1. 全局用户级信号量（最大并行用户数）
2. 任务队列（FIFO，存储等待中的任务）
3. 任务状态追踪（通过 SSE 推送到前端）
4. 可配置的最大并行数（存储在数据库）
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from sqlalchemy import select


class TaskStatus(str, Enum):
    """任务状态枚举"""
    QUEUED = "queued"          # 排队中
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


@dataclass
class QueueTask:
    """队列任务"""
    task_id: str                              # 任务唯一ID（对应 study_id）
    user_id: str                              # 用户ID
    study_id: str                             # 研究ID
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.QUEUED
    queue_position: int = 0                   # 队列位置
    started_at: Optional[datetime] = None    # 开始时间
    completed_at: Optional[datetime] = None  # 完成时间
    error_message: Optional[str] = None      # 错误信息
    # SSE 事件队列（用于向前端推送状态）
    event_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class TaskQueueManager:
    """
    任务队列管理器（单例模式）

    功能：
    1. 用户级并发控制（最大并行用户数）
    2. 任务排队机制
    3. 状态推送
    """
    _instance: Optional['TaskQueueManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 默认最大并行用户数（启动时从数据库加载）
        self._max_concurrent_users = 4

        # 用户级信号量
        self._user_semaphore = asyncio.Semaphore(self._max_concurrent_users)

        # 任务队列 {task_id: QueueTask}
        self._tasks: Dict[str, QueueTask] = {}

        # 用户当前任务映射 {user_id: task_id}
        self._user_tasks: Dict[str, str] = {}

        # 排队队列（FIFO）
        self._queue: asyncio.Queue = asyncio.Queue()

        # 队列处理器
        self._processor_task: Optional[asyncio.Task] = None

        # 锁，用于保护队列操作
        self._lock = asyncio.Lock()

        logger.info(f"[TaskQueue] 初始化完成，最大并行用户数: {self._max_concurrent_users}")

    async def initialize(self):
        """从数据库加载配置"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.system_config import SystemConfig

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SystemConfig).where(SystemConfig.key == "max_concurrent_users")
                )
                config = result.scalar_one_or_none()
                if config:
                    self._max_concurrent_users = int(config.value)
                    self._user_semaphore = asyncio.Semaphore(self._max_concurrent_users)
                    logger.info(f"[TaskQueue] 从数据库加载配置，最大并行用户数: {self._max_concurrent_users}")
        except Exception as e:
            logger.warning(f"[TaskQueue] 加载配置失败，使用默认值: {e}")

    async def update_max_concurrent(self, new_max: int):
        """更新最大并行用户数"""
        async with self._lock:
            self._max_concurrent_users = new_max
            self._user_semaphore = asyncio.Semaphore(new_max)
            logger.info(f"[TaskQueue] 更新最大并行用户数: {new_max}")

    @property
    def max_concurrent_users(self) -> int:
        return self._max_concurrent_users

    async def submit_task(
        self,
        user_id: str,
        study_id: str,
    ) -> QueueTask:
        """
        提交任务到队列

        返回：
        - QueueTask: 任务对象（包含队列位置等信息）
        """
        task_id = study_id  # 使用 study_id 作为 task_id

        task = QueueTask(
            task_id=task_id,
            user_id=user_id,
            study_id=study_id,
        )

        async with self._lock:
            self._tasks[task_id] = task
            self._user_tasks[user_id] = task_id

            # 计算队列位置
            queue_size = self._queue.qsize()
            task.queue_position = queue_size + 1

            # 加入队列
            await self._queue.put(task_id)

            logger.info(f"[TaskQueue] 任务入队: task_id={task_id}, user_id={user_id}, queue_position={task.queue_position}")

        # 推送排队状态
        await task.event_queue.put({
            'type': 'queue_status',
            'task_id': task_id,
            'status': TaskStatus.QUEUED.value,
            'queue_position': task.queue_position,
            'max_concurrent': self._max_concurrent_users,
        })

        return task

    async def wait_for_slot(self, task: QueueTask):
        """
        等待获取执行槽位

        当获得槽位后，任务状态会更新为 RUNNING
        """
        # 等待信号量
        await self._user_semaphore.acquire()

        async with self._lock:
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()

            # 更新其他任务的队列位置
            await self._update_queue_positions()

        # 推送开始状态
        await task.event_queue.put({
            'type': 'queue_status',
            'task_id': task.task_id,
            'status': TaskStatus.RUNNING.value,
            'started_at': task.started_at.isoformat() if task.started_at else None,
        })

        logger.info(f"[TaskQueue] 任务开始执行: task_id={task.task_id}, user_id={task.user_id}")

    async def release_slot(self, task: QueueTask, success: bool = True, error_message: str = None):
        """
        释放执行槽位
        """
        async with self._lock:
            # 更新任务状态
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error_message = error_message

            # 清理用户任务映射
            if self._user_tasks.get(task.user_id) == task.task_id:
                del self._user_tasks[task.user_id]

        # 释放信号量
        self._user_semaphore.release()

        logger.info(f"[TaskQueue] 任务完成: task_id={task.task_id}, success={success}")

    async def _update_queue_positions(self):
        """更新所有排队任务的队列位置"""
        position = 1
        for task in self._tasks.values():
            if task.status == TaskStatus.QUEUED:
                task.queue_position = position
                position += 1
                try:
                    await task.event_queue.put({
                        'type': 'queue_status',
                        'task_id': task.task_id,
                        'status': TaskStatus.QUEUED.value,
                        'queue_position': task.queue_position,
                    })
                except Exception as e:
                    logger.warning(f"[TaskQueue] 更新队列位置失败: {e}")

    def get_task(self, task_id: str) -> Optional[QueueTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_user_task(self, user_id: str) -> Optional[QueueTask]:
        """获取用户当前任务"""
        task_id = self._user_tasks.get(user_id)
        if task_id:
            return self._tasks.get(task_id)
        return None

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        queued = sum(1 for t in self._tasks.values() if t.status == TaskStatus.QUEUED)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

        return {
            'max_concurrent': self._max_concurrent_users,
            'queued': queued,
            'running': running,
            'total_tasks': len(self._tasks),
        }

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.CANCELLED
                await task.event_queue.put({
                    'type': 'queue_status',
                    'task_id': task_id,
                    'status': TaskStatus.CANCELLED.value,
                })
                logger.info(f"[TaskQueue] 任务已取消: task_id={task_id}")
                return True
            return False

    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """清理已完成的旧任务"""
        now = datetime.now()
        to_remove = []

        for task_id, task in self._tasks.items():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                if task.completed_at:
                    age = (now - task.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]

        if to_remove:
            logger.info(f"[TaskQueue] 清理了 {len(to_remove)} 个旧任务")


# 全局单例
task_queue = TaskQueueManager()
