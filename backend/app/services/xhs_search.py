"""
小红书批量搜索服务
============================================
支持复用浏览器实例进行多次搜索
"""
import asyncio
import random
from typing import List, Dict, Any, Optional, Callable
from loguru import logger

from app.services.browser_pool import browser_pool, random_sleep


async def search_xhs_for_persona(
    session,
    keyword: str,
    max_posts: int = 6,
    max_comments: int = 20,
    progress_callback: Optional[Callable] = None,
) -> List[Dict[str, Any]]:
    """
    在已有浏览器会话中执行搜索

    参数：
    - session: 浏览器会话
    - keyword: 搜索关键词
    - max_posts: 最大帖子数
    - max_comments: 每帖最大评论数
    - progress_callback: 进度回调函数

    返回：
    - List[Dict]: 帖子列表
    """
    page = session.page
    results = []

    try:
        logger.info(f"[XHS] 开始搜索: keyword={keyword}")

        # 在搜索框输入关键词
        try:
            search_box = await page.wait_for_selector("#search-input", timeout=10000)
            # 先清空搜索框
            await search_box.fill("")
            await asyncio.sleep(0.3)
            await search_box.fill(keyword)
            await page.keyboard.press("Enter")
            logger.info(f"[XHS] 输入关键词成功: {keyword}")
        except Exception as e:
            logger.error(f"[XHS] 搜索框操作失败: {e}")
            return []

        await random_sleep(4, 6)  # 等待搜索结果加载

        # 选择图文类型
        try:
            type_option = page.get_by_text("图文", exact=True).nth(1)
            if await type_option.is_visible():
                await type_option.click()
                await random_sleep(0.8, 1.5)
        except:
            pass

        # 筛选条件设置（最多点赞、半年内）
        try:
            filter_btn = await page.wait_for_selector(".filter", timeout=5000)
            await filter_btn.hover()
            await random_sleep(1.5, 3)

            # 选择最多点赞
            sort_option = page.get_by_text("最多点赞", exact=True).nth(1)
            await sort_option.click()
            await random_sleep(0.8, 1.5)

            # 选择半年内
            time_option = page.get_by_text("半年内", exact=True).nth(1)
            await time_option.click()
            await random_sleep(0.8, 1.5)
        except Exception as e:
            logger.warning(f"[XHS] 筛选设置失败: {e}")

        # 获取帖子卡片
        cards = await page.query_selector_all(".note-item")
        cards_to_process = cards[:max_posts]

        logger.info(f"[XHS] 找到 {len(cards)} 个帖子卡片，将处理 {len(cards_to_process)} 个")

        # 逐个获取帖子详情
        for idx, card in enumerate(cards_to_process):
            try:
                post = await _extract_post_from_card(card, page, idx, max_comments)
                if post:
                    results.append(post)
                    session.search_count += 1

                    if progress_callback:
                        await progress_callback({
                            'type': 'post_extracted',
                            'index': idx + 1,
                            'total': len(cards_to_process),
                            'title': post.get('title', '')[:30],
                        })
            except Exception as e:
                logger.error(f"[XHS] 提取帖子失败: {e}")

        logger.info(f"[XHS] 搜索完成: keyword={keyword}, 获取 {len(results)} 条帖子")

    except Exception as e:
        logger.error(f"[XHS] 搜索失败: {e}")

    return results


async def _extract_post_from_card(
    card,
    page,
    idx: int,
    max_comments: int
) -> Optional[Dict[str, Any]]:
    """从卡片提取帖子信息"""
    # 提取基本信息
    title_el = await card.query_selector(".title span") or await card.query_selector("h1")
    title = await title_el.inner_text() if title_el else ""

    author_el = await card.query_selector(".author-name") or await card.query_selector(".name")
    author = await author_el.inner_text() if author_el else ""

    link_el = await card.query_selector("a.cover, a[href*='/discovery/item/']") or await card.query_selector("a")
    link = await link_el.get_attribute("href") if link_el else ""
    if link and not link.startswith("http"):
        link = "https://www.xiaohongshu.com" + link

    # 点击卡片打开详情弹窗
    await card.click()
    await random_sleep(2, 3)

    # 提取正文
    content = ""
    try:
        popup = await page.wait_for_selector(".note-detail-mask, .note-detail", timeout=5000)
        if popup:
            content_el = await popup.query_selector("#detail-content, .detail-content, .note-content")
            if content_el:
                content = await content_el.inner_text()
    except:
        pass

    # 提取评论
    comments = []
    try:
        # 展开评论区
        expand_btn = await page.query_selector(".expand-btn, .expand-comment")
        if expand_btn:
            await expand_btn.click()
            await random_sleep(0.8, 1.5)

        # 获取评论
        comment_items = await page.query_selector_all(".comment-item, .comment")
        for comment_el in comment_items[:max_comments]:
            text_el = await comment_el.query_selector(".comment-content, .text")
            user_el = await comment_el.query_selector(".user-name, .nickname")
            if text_el:
                comments.append({
                    "user": await user_el.inner_text() if user_el else "匿名用户",
                    "text": await text_el.inner_text(),
                })
    except:
        pass

    # 关闭弹窗
    await page.keyboard.press("Escape")
    await random_sleep(0.3, 0.8)

    return {
        "title": title.strip(),
        "author": author.strip(),
        "link": link,
        "content": content.strip(),
        "comments": comments,
        "platform": "小红书",
        "is_real": True,
    }


async def batch_search_for_study(
    study_id: str,
    persona_keywords: List[Dict[str, Any]],
    max_posts: int = 6,
    max_comments: int = 20,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    为一个研究任务执行批量搜索

    参数：
    - study_id: 研究ID
    - persona_keywords: 每个人设的搜索关键词 [{persona_id, persona_name, keywords: [...]}]
    - max_posts: 每个人设最大帖子数
    - max_comments: 每帖最大评论数
    - progress_callback: 进度回调函数

    返回：
    - Dict[persona_id, List[posts]]: 每个人设的搜索结果
    """
    results = {}

    # 获取浏览器会话
    session = await browser_pool.acquire(study_id)

    try:
        for i, persona_data in enumerate(persona_keywords):
            persona_id = persona_data['persona_id']
            persona_name = persona_data.get('persona_name', f'用户{i+1}')
            keywords = persona_data.get('keywords', [])

            # 通知开始
            if progress_callback:
                await progress_callback({
                    'type': 'persona_search_start',
                    'persona_id': persona_id,
                    'persona_name': persona_name,
                    'keywords': keywords,
                    'current': i + 1,
                    'total': len(persona_keywords),
                })

            # 执行搜索
            combined_kw = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
            posts = await search_xhs_for_persona(
                session=session,
                keyword=combined_kw,
                max_posts=max_posts,
                max_comments=max_comments,
            )

            results[persona_id] = posts

            # 通知完成
            if progress_callback:
                await progress_callback({
                    'type': 'persona_search_done',
                    'persona_id': persona_id,
                    'persona_name': persona_name,
                    'posts_count': len(posts),
                })

    finally:
        # 释放会话（不关闭，等待任务完成后统一关闭）
        await browser_pool.release(study_id)

    return results


async def close_study_browser(study_id: str):
    """关闭研究的浏览器会话"""
    await browser_pool.close(study_id)
