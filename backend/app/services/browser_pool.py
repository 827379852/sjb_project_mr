"""
浏览器实例池管理
============================================
实现浏览器实例复用，支持同一任务的批量搜索

核心设计：
1. 任务级浏览器实例绑定
2. 同一任务的所有人设搜索复用同一浏览器实例
3. 任务完成后自动清理浏览器实例
"""
import asyncio
import random
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


# 模拟真实浏览器的 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# 小红书 Cookies（从 xiaohongshu.py 同步）
XHS_COOKIES = [
    {"name": "acw_tc", "value": "0a00d10f17761761536045405e65be0a790c340a202c453896f77b66e39daa", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "abRequestId", "value": "a88d8cf4-c910-52a4-bd24-b2de48b97d9c", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "ets", "value": "1776176154974", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "webBuild", "value": "6.6.0", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "xsecappid", "value": "xhs-pc-web", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "loadts", "value": "1776176155032", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "a1", "value": "19d8c59499ez8o6ac4zgpf8m1ot8rm4gp7tcmz7oc30000128223", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "webId", "value": "526b8c3c55abedd3e9b727f274300c97", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "websectiga", "value": "29098a4cf41f76ee3f8db19051aaa60c0fc7c5e305572fec762da32d457d76ae", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "sec_poison_id", "value": "862a096e-11f9-433a-891e-71d1fc1e60c1", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "gid", "value": "yjfYS2j24fUdyjfYS2j4jWuWjduYlK0S4ukU9lSiY6yl9Sq8YF64k6888yJYJJq88qS0KqqY", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "web_session", "value": "040069b8d61ce6d434a64c04eb3b4b34426867", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "id_token", "value": "VjEAACrKREWNPNxu3884viqtiL2Y2Yw/EFZaVayceRLcV9D4PDwkancPXHtk+PNsxvEpE8xXLbcCT5fzGifPvbis/4QA+mrWSv28VzBXFs1vt+6VXt+TNBPacTeDcUj4VADPPk0E", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "unread", "value": "{\"ub\":\"69dcbe9b000000001f007287\",\"ue\":\"69ccdead00000000230226e8\",\"uc\":33}", "domain": ".xiaohongshu.com", "path": "/"}
]


async def random_sleep(min_sec: float = 0.5, max_sec: float = 2.0):
    """异步随机延迟"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


@dataclass
class BrowserSession:
    """浏览器会话"""
    study_id: str                              # 关联的研究ID
    browser: Any                               # 浏览器实例 (Browser)
    context: Any                               # 浏览器上下文 (BrowserContext)
    page: Any                                  # 当前页面 (Page)
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    search_count: int = 0                      # 搜索次数
    is_busy: bool = False                      # 是否正在使用


class BrowserPool:
    """
    浏览器实例池（单例模式）

    功能：
    1. 任务级浏览器实例管理
    2. 同一任务复用浏览器实例
    3. 自动清理过期实例
    """
    _instance: Optional['BrowserPool'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 浏览器会话映射 {study_id: BrowserSession}
        self._sessions: Dict[str, BrowserSession] = {}

        # Playwright 实例
        self._playwright = None

        # 会话超时时间（秒）
        self._session_timeout = 1800  # 30分钟

        # 锁
        self._lock = asyncio.Lock()

        logger.info("[BrowserPool] 初始化完成")

    async def _ensure_playwright(self):
        """确保 Playwright 实例存在"""
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            logger.info("[BrowserPool] Playwright 实例已创建")

    async def acquire(self, study_id: str) -> BrowserSession:
        """
        获取或创建浏览器会话

        参数：
        - study_id: 研究ID（用于绑定会话）

        返回：
        - BrowserSession: 浏览器会话
        """
        async with self._lock:
            await self._ensure_playwright()

            # 检查是否已有会话
            session = self._sessions.get(study_id)
            if session and not session.is_busy:
                session.last_used = datetime.now()
                session.is_busy = True
                logger.info(f"[BrowserPool] 复用浏览器会话: study_id={study_id}, search_count={session.search_count}")
                return session

            # 创建新会话
            browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--no-sandbox',
                ]
            )

            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800},
                locale='zh-CN',
            )

            # 添加 Cookies
            await context.add_cookies(XHS_COOKIES)

            page = await context.new_page()

            # 打开小红书首页
            try:
                await page.goto("https://www.xiaohongshu.com/explore", timeout=60000)
                await random_sleep(2, 4)
            except Exception as e:
                logger.warning(f"[BrowserPool] 打开小红书首页失败: {e}")
                # 继续尝试使用

            session = BrowserSession(
                study_id=study_id,
                browser=browser,
                context=context,
                page=page,
                is_busy=True,
            )

            self._sessions[study_id] = session
            logger.info(f"[BrowserPool] 创建新浏览器会话: study_id={study_id}")

            return session

    async def release(self, study_id: str):
        """
        释放浏览器会话（标记为可用，但不关闭）
        """
        async with self._lock:
            session = self._sessions.get(study_id)
            if session:
                session.is_busy = False
                session.last_used = datetime.now()
                logger.info(f"[BrowserPool] 释放浏览器会话: study_id={study_id}")

    async def close(self, study_id: str):
        """
        关闭并清理浏览器会话
        """
        async with self._lock:
            session = self._sessions.get(study_id)
            if session:
                try:
                    await session.browser.close()
                except Exception as e:
                    logger.warning(f"[BrowserPool] 关闭浏览器异常: {e}")

                del self._sessions[study_id]
                logger.info(f"[BrowserPool] 关闭浏览器会话: study_id={study_id}")

    async def cleanup_expired(self):
        """清理过期的浏览器会话"""
        async with self._lock:
            now = datetime.now()
            expired = []

            for study_id, session in self._sessions.items():
                if not session.is_busy:
                    elapsed = (now - session.last_used).total_seconds()
                    if elapsed > self._session_timeout:
                        expired.append(study_id)

            for study_id in expired:
                session = self._sessions.get(study_id)
                if session:
                    try:
                        await session.browser.close()
                    except:
                        pass
                    del self._sessions[study_id]
                    logger.info(f"[BrowserPool] 清理过期会话: study_id={study_id}")

    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return {
            'active_sessions': len(self._sessions),
            'sessions': [
                {
                    'study_id': s.study_id,
                    'search_count': s.search_count,
                    'is_busy': s.is_busy,
                    'created_at': s.created_at.isoformat(),
                    'last_used': s.last_used.isoformat(),
                }
                for s in self._sessions.values()
            ]
        }


# 全局单例
browser_pool = BrowserPool()
