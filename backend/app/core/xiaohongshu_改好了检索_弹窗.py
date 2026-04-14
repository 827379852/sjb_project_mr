from playwright.async_api import async_playwright
import asyncio
import time
import random
import json
import sys
import io
import os
from datetime import datetime

# 设置标准输出编码为 UTF-8（解决 Windows 终端 emoji 乱码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace',line_buffering=True)

# 错误截图保存目录
ERROR_PIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pic")

# 确保截图目录存在
os.makedirs(ERROR_PIC_DIR, exist_ok=True)


def random_delay(min_sec=0.5, max_sec=2.0):
    """生成随机延迟时间（秒）"""
    return random.uniform(min_sec, max_sec)


async def random_sleep(min_sec=0.5, max_sec=2.0):
    """异步随机延迟等待"""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def save_error_screenshot(page, error_name="error"):
    """保存错误截图到指定目录"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{error_name}_{timestamp}.png"
        filepath = os.path.join(ERROR_PIC_DIR, filename)
        await page.screenshot(path=filepath, full_page=False)
        print(f"  错误截图已保存: {filepath}")
    except Exception as e:
        print(f"  保存错误截图失败: {e}")

# 模拟真实浏览器的 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]
cookies = [
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

def print_config(keyword, max_posts, scroll_times, max_comments_per_post,
                 min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless):
    """打印当前配置参数"""
    print("\n" + "=" * 50)
    print("当前配置参数：")
    print("=" * 50)
    print(f"  搜索关键词: {keyword}")
    print(f"  帖子数量: {max_posts}")
    print(f"  滚动次数: {scroll_times}")
    print(f"  每帖评论上限: {max_comments_per_post}")
    print(f"  访问间隔: {min_delay}-{max_delay}秒")
    print(f"  页面加载等待: {page_load_wait}秒")
    print(f"  保存截图: {'是' if save_screenshots else '否'}")
    print(f"  保存JSON: {'是' if save_json else '否'}")
    print(f"  无头模式: {'是' if headless else '否'}")
    print("=" * 50 + "\n")


def modify_config(keyword, max_posts, scroll_times, max_comments_per_post,
                  min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless):
    """交互式修改配置参数，返回新的参数"""
    print("\n" + "=" * 50)
    print("参数设置（直接回车使用默认值）")
    print("=" * 50)

    # 关键词
    new_keyword = input(f"搜索关键词 (默认: {keyword}): ").strip()
    if new_keyword:
        keyword = new_keyword

    # 帖子数量
    try:
        posts = input(f"抓取帖子数量 1-20 (默认: {max_posts}): ").strip()
        if posts:
            max_posts = max(1, min(20, int(posts)))
    except ValueError:
        pass

    # 滚动次数
    try:
        scroll = input(f"滚动加载次数 1-10 (默认: {scroll_times}): ").strip()
        if scroll:
            scroll_times = max(1, min(10, int(scroll)))
    except ValueError:
        pass

    # 评论数量
    try:
        comments = input(f"每帖评论上限 1-100 (默认: {max_comments_per_post}): ").strip()
        if comments:
            max_comments_per_post = max(1, min(100, int(comments)))
    except ValueError:
        pass

    # 访问间隔
    try:
        delay = input(f"访问间隔秒数 (默认: {min_delay}-{max_delay}): ").strip()
        if delay:
            parts = delay.split('-')
            if len(parts) == 2:
                min_delay = float(parts[0])
                max_delay = float(parts[1])
    except ValueError:
        pass

    # 页面加载等待
    try:
        wait = input(f"页面加载等待秒数 (默认: {page_load_wait}): ").strip()
        if wait:
            page_load_wait = int(wait)
    except ValueError:
        pass

    # 保存截图
    screenshot = input(f"保存截图 (y/n, 默认: {'y' if save_screenshots else 'n'}): ").strip().lower()
    if screenshot == 'y':
        save_screenshots = True
    elif screenshot == 'n':
        save_screenshots = False

    # 保存JSON
    json_save = input(f"保存JSON文件 (y/n, 默认: {'y' if save_json else 'n'}): ").strip().lower()
    if json_save == 'y':
        save_json = True
    elif json_save == 'n':
        save_json = False

    # 无头模式
    headless_input = input(f"无头模式 (y/n, 默认: {'y' if headless else 'n'}): ").strip().lower()
    if headless_input == 'y':
        headless = True
    elif headless_input == 'n':
        headless = False

    print_config(keyword, max_posts, scroll_times, max_comments_per_post,
                 min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless)

    return keyword, max_posts, scroll_times, max_comments_per_post, min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless


async def fetch_single_post_detail_popup(page, card, post, idx, page_load_wait, save_screenshots, max_comments_per_post):
    """
    通过点击卡片打开弹窗的方式抓取单个帖子的详情和评论
    不打开新页面，直接在弹窗中获取内容，按ESC关闭
    """
    try:
        print(f"\n[弹窗模式] 正在抓取第 {idx+1} 个帖子: {post['title'][:30]}...")

        # 点击卡片打开弹窗
        await card.click()
        await random_sleep(page_load_wait * 0.8, page_load_wait * 1.2)  # 随机延迟

        if save_screenshots:
            await page.screenshot(path=f"detail_{idx+1}.png", full_page=False)

        # ===== 抓取弹窗内容 =====
        # 弹窗的选择器
        popup_selectors = [
            ".note-detail-mask", ".note-detail", ".popup-content",
            ".modal-content", ".note-container", ".note-scroller",
            "[class*='note-detail']", "[class*='popup']", "[class*='modal']"
        ]

        popup = None
        for selector in popup_selectors:
            try:
                popup = await page.wait_for_selector(selector, timeout=5000)
                if popup:
                    print(f"  [第{idx+1}帖] 找到弹窗: {selector}")
                    break
            except:
                continue

        content = ""
        if popup:
            # 从弹窗中提取正文
            content_selectors = [
                "#detail-content", ".detail-content", ".note-content",
                ".content", "#content", ".desc", "#note-desc",
                ".note-detail-content", ".main-content", "p"
            ]
            for selector in content_selectors:
                el = await popup.query_selector(selector)
                if el:
                    content = await el.inner_text()
                    if content.strip():
                        break

        if not content.strip() and popup:
            # 备用方案：获取弹窗内所有文本
            all_text = await popup.inner_text()
            lines = all_text.split('\n')
            for line in lines:
                if len(line) > 50:
                    content = line
                    break

        post['content'] = content.strip() if content else "无法获取正文"
        print(f"  [第{idx+1}帖] 正文长度: {len(post['content'])} 字符")

        # ===== 抓取评论内容 =====
        comments = []

        if popup:
            # 展开评论区
            expand_selectors = [
                ".expand-btn", ".expand-comment", "#expand-comment",
                ".show-more-comments", ".load-more-comments",
                ".comment-expand-btn", ".comments-btn",
                "[class*='expand']", "[class*='more']"
            ]

            for selector in expand_selectors:
                try:
                    expand_btn = await popup.query_selector(selector)
                    if expand_btn:
                        await expand_btn.click()
                        print(f"  [第{idx+1}帖] 已点击展开评论区按钮")
                        await random_sleep(0.8, 1.5)  # 随机延迟
                        break
                except:
                    continue

            # 滚动弹窗内的评论区
            try:
                await popup.evaluate("el => el.scrollBy(0, el.scrollHeight * 0.7)")
                await random_sleep(0.8, 1.5)  # 随机延迟
            except:
                pass

            # 查找评论容器
            comment_selectors = [
                ".comments", "#comments", ".comment-list",
                ".note-detail-comment", ".comment-container",
                ".comment-wrapper", ".comment-content-wrapper",
                "[class*='comment']", "#comment"
            ]

            comment_container = None
            for selector in comment_selectors:
                try:
                    comment_container = await popup.query_selector(selector)
                    if comment_container:
                        break
                except:
                    continue

            if comment_container:
                comment_item_selectors = [
                    ".comment-item", ".comment", ".comment-item-v2",
                    ".floor-comment-item", ".comment-wrapper",
                    ".comment-content", "[class*='comment-item']",
                    "li", ".item"
                ]

                comment_items = []
                for selector in comment_item_selectors:
                    try:
                        items = await comment_container.query_selector_all(selector)
                        if items and len(items) > 0:
                            comment_items = items
                            print(f"  [第{idx+1}帖] 找到 {len(items)} 个评论项")
                            break
                    except:
                        continue

                for comment_item in comment_items[:max_comments_per_post]:
                    try:
                        comment_text_el = (
                            await comment_item.query_selector(".comment-content") or
                            await comment_item.query_selector(".text") or
                            await comment_item.query_selector(".content") or
                            await comment_item.query_selector(".comment-text") or
                            await comment_item.query_selector("p") or
                            await comment_item.query_selector("span")
                        )
                        comment_text = await comment_text_el.inner_text() if comment_text_el else ""

                        comment_user_el = (
                            await comment_item.query_selector(".user-name") or
                            await comment_item.query_selector(".nickname") or
                            await comment_item.query_selector(".comment-user") or
                            await comment_item.query_selector(".author") or
                            await comment_item.query_selector("a.user-link") or
                            await comment_item.query_selector("a")
                        )
                        comment_user = await comment_user_el.inner_text() if comment_user_el else ""

                        if comment_text.strip() and len(comment_text.strip()) > 2:
                            comments.append({
                                "user": comment_user.strip() if comment_user else "匿名用户",
                                "text": comment_text.strip()
                            })
                    except:
                        continue

        post['comments'] = comments
        print(f"  [第{idx+1}帖] 获取到 {len(comments)} 条评论 ✓")

        # 按 ESC 关闭弹窗
        await page.keyboard.press("Escape")
        await random_sleep(0.3, 0.8)  # 随机延迟
        print(f"  [第{idx+1}帖] 已关闭弹窗")

        return post

    except Exception as e:
        print(f"  [第{idx+1}帖] 抓取失败: {e}")
        # 保存错误截图
        await save_error_screenshot(page, f"post_{idx+1}_error")
        # 尝试按 ESC 关闭可能存在的弹窗
        try:
            await page.keyboard.press("Escape")
            await random_sleep(0.3, 0.8)
        except:
            pass
        return post


async def search_xiaohongshu_async(
    keyword="旅行",
    max_posts=5,
    scroll_times=3,
    max_comments_per_post=20,
    min_delay=2,
    max_delay=4,
    page_load_wait=3,
    save_screenshots=True,
    save_json=True,
    headless=True
):
    """
    小红书爬虫主函数（弹窗模式，不打开新页面）

    参数说明:
    ---------
    keyword : str
        搜索关键词，默认 "旅行"
    max_posts : int
        最多抓取帖子数量，默认 5（范围 1-20）
    scroll_times : int
        搜索结果滚动加载次数，默认 3（范围 1-10）
    max_comments_per_post : int
        每个帖子最多抓取评论数量，默认 20（范围 1-100）
    min_delay : float
        访问帖子最小间隔（秒），默认 2
    max_delay : float
        访问帖子最大间隔（秒），默认 4
    page_load_wait : int
        页面加载等待时间（秒），默认 3
    save_screenshots : bool
        是否保存详情页截图，默认 True
    save_json : bool
        是否返回JSON格式数据，默认 True
    headless : bool
        是否无头模式运行，默认 True

    返回:
    -----
    list : 帖子数据列表，每个帖子包含 title, author, link, content, comments
    """
    print(f"\n正在搜索: {keyword}，目标 {max_posts} 个帖子...")
    print(f"弹窗模式: 点击帖子 → 弹窗显示 → ESC关闭（不打开新页面）\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )

        await context.add_cookies(cookies)

        page = await context.new_page()

        print(f"打开小红书...")
        try:
            await page.goto("https://www.xiaohongshu.com/explore", timeout=60000)
        except Exception as e:
            print(f"访问失败: {e}")
            await save_error_screenshot(page, "open_page_error")
            await browser.close()
            return []

        await random_sleep(2, 4)  # 随机延迟

        print("输入关键词...")
        try:
            search_box = await page.wait_for_selector("#search-input", timeout=10000)
            await search_box.fill(keyword)
            await page.keyboard.press("Enter")
            print("搜索成功")

        except Exception as e:
            print(f"搜索框操作失败: {e}")
            await save_error_screenshot(page, "search_error")
            await browser.close()
            return []

        await random_sleep(4, 6)  # 随机延迟
        await page.screenshot(path="screenshot1.png")

        # 选择内容类型：图文
        try:
            type_option = page.get_by_text("图文", exact=True).nth(1)
            if await type_option.is_visible():
                await type_option.click()
                print("  已选择：图文")
                await random_sleep(0.8, 1.5)  # 随机延迟
            else:
                type_option = page.locator("span:has-text('图文')").first
                if await type_option.is_visible():
                    await type_option.click()
                    print("  已选择：图文（备用选择器）")
                    await random_sleep(0.8, 1.5)  # 随机延迟
        except Exception as e:
            print(f"  选择图文失败: {e}")
            await save_error_screenshot(page, "select_type_error")

        # ========== 筛选操作 ==========
        print("正在设置筛选条件...")
        try:
            # 鼠标悬停到筛选按钮（漏斗图标）展开下拉菜单
            filter_clicked = False
            filter_selectors = [
                 ".filter"
            ]
            for selector in filter_selectors:
                try:
                    filter_btn = await page.wait_for_selector(selector, timeout=3000)
                    if filter_btn:
                        # 先鼠标悬停，等待下拉菜单出现
                        await filter_btn.hover()
                        print("  已悬停到筛选按钮")
                        await random_sleep(1.5, 3)  # 随机延迟

                        filter_clicked = True
                        print("  已点击筛选按钮")
                        break
                except:
                    continue
            await page.screenshot(path=os.path.join(ERROR_PIC_DIR, "filter_step1.png"))


            if filter_clicked:
                # 1. 选择排序方式：最多点赞
                try:
                    # 直接定位包含"最多点赞"文本的元素
                    sort_option = page.get_by_text("最多点赞", exact=True).nth(1)
                    await sort_option.click()
                    print("  已选择：最多点赞")
                    await random_sleep(0.8, 1.5)  # 随机延迟

                except Exception as e:
                    print(f"  选择最多点赞失败: {e}")
                    await save_error_screenshot(page, "select_sort_error")

                # 2. 选择时间范围：半年内
                try:
                    time_option = page.get_by_text("半年内", exact=True).nth(1)
                    await time_option.click()
                    print("  已选择：半年内")
                    await random_sleep(0.8, 1.5)  # 随机延迟

                except Exception as e:
                    print(f"  选择半年内失败: {e}")
                    await save_error_screenshot(page, "select_time_error")



                await page.screenshot(path="screenshot2_filter.png")
                print("  筛选条件设置完成")

        except Exception as e:
            print(f"  筛选操作失败（将继续爬取）: {e}")
            await save_error_screenshot(page, "filter_error")

        await random_sleep(1, 2)  # 随机延迟
        await page.screenshot(path=os.path.join(ERROR_PIC_DIR, "filter_step2.png"))
        # ========== 筛选操作结束 ==========

        # 已移除滚动加载，直接解析当前页面数据
        print("解析数据...")
        await page.screenshot(path=os.path.join(ERROR_PIC_DIR, "parse_data.png"))
        cards = await page.query_selector_all(".note-item")

        results = []
        cards_to_process = cards[:max_posts]

        # 保存卡片元素引用，用于后续点击
        card_post_pairs = []

        for idx, card in enumerate(cards_to_process):
            try:
                title_el = (
                    await card.query_selector(".title span") or
                    await card.query_selector("h1") or
                    await card.query_selector(".note-content .title")
                )
                title = await title_el.inner_text() if title_el else ""

                author_el = (
                    await card.query_selector(".author-name") or
                    await card.query_selector(".name") or
                    await card.query_selector(".user-nickname")
                )
                author = await author_el.inner_text() if author_el else ""

                link_el = await card.query_selector("a.cover, a[href*='/discovery/item/']")
                if not link_el:
                    link_el = await card.query_selector("a")
                link = await link_el.get_attribute("href") if link_el else ""

                if link and not link.startswith("http"):
                    link = "https://www.xiaohongshu.com" + link

                if title or author:
                    post = {
                        "title": title.strip() if title else "无标题",
                        "author": author.strip() if author else "未知作者",
                        "link": link,
                        "content": "",
                        "comments": []
                    }
                    results.append(post)
                    card_post_pairs.append((card, post))
                    print(f"  已提取第 {idx+1} 个帖子: {results[-1]['title'][:30]}...")
            except Exception as e:
                print(f"  提取第 {idx+1} 个帖子失败: {e}")
                continue

        print(f"\n开始弹窗模式抓取 {len(results)} 个帖子的详情和评论...")

        # ========== 串行弹窗模式处理 ==========
        for idx, (card, post) in enumerate(card_post_pairs):
            await fetch_single_post_detail_popup(page, card, post, idx, page_load_wait, save_screenshots, max_comments_per_post)
        # ========== 弹窗模式处理结束 ==========

        print(f"\n共找到 {len(results)} 条帖子详情")
        await browser.close()
        return results


def search_xiaohongshu(
    keyword="旅行",
    max_posts=5,
    scroll_times=3,
    max_comments_per_post=20,
    min_delay=2,
    max_delay=4,
    page_load_wait=3,
    save_screenshots=True,
    save_json=True,
    headless=True
):
    """
    小红书爬虫主函数（同步包装器）

    参数说明:
    ---------
    keyword : str
        搜索关键词，默认 "旅行"
    max_posts : int
        最多抓取帖子数量，默认 5（范围 1-20）
    scroll_times : int
        搜索结果滚动加载次数，默认 3（范围 1-10）
    max_comments_per_post : int
        每个帖子最多抓取评论数量，默认 20（范围 1-100）
    min_delay : float
        访问帖子最小间隔（秒），默认 2
    max_delay : float
        访问帖子最大间隔（秒），默认 4
    page_load_wait : int
        页面加载等待时间（秒），默认 3
    save_screenshots : bool
        是否保存详情页截图，默认 True
    save_json : bool
        是否返回JSON格式数据，默认 True
    headless : bool
        是否无头模式运行，默认 True

    返回:
    -----
    list : 帖子数据列表，每个帖子包含 title, author, link, content, comments
    """
    return asyncio.run(search_xiaohongshu_async(
        keyword=keyword,
        max_posts=max_posts,
        scroll_times=scroll_times,
        max_comments_per_post=max_comments_per_post,
        min_delay=min_delay,
        max_delay=max_delay,
        page_load_wait=page_load_wait,
        save_screenshots=save_screenshots,
        save_json=save_json,
        headless=headless
    ))


def save_to_json(data, filename="xiaohongshu_data.json"):
    """保存数据到JSON文件"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n数据已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        return False


def print_results(data, keyword):
    """打印抓取结果"""
    if not data:
        return

    print("\n" + "=" * 80)
    print(f"搜索结果（关键词: {keyword}，共 {len(data)} 个帖子）：")
    print("=" * 80)

    total_comments = 0

    for i, item in enumerate(data, 1):
        total_comments += len(item['comments'])

        print(f"\n{'='*80}")
        print(f"【帖子 {i}】")
        print(f"{'='*80}")
        print(f"标题: {item['title']}")
        print(f"作者: {item['author']}")
        print(f"链接: {item['link']}")
        print(f"正文长度: {len(item['content'])} 字符")
        print(f"评论数: {len(item['comments'])} 条")

        print(f"\n--- 正文内容 ---")
        content_preview = item['content'][:500] + "..." if len(item['content']) > 500 else item['content']
        print(content_preview if content_preview else "（无正文内容）")

        print(f"\n--- 评论（共 {len(item['comments'])} 条）---")
        if item['comments']:
            for j, comment in enumerate(item['comments'], 1):
                print(f"  [{j}] {comment['user']}: {comment['text'][:100]}...")
        else:
            print("（暂无评论）")

    print("\n" + "=" * 80)
    print(f"统计：共抓取 {len(data)} 个帖子，{total_comments} 条评论")
    print("=" * 80)


# ==================== 默认参数配置 ====================
DEFAULT_KEYWORD = "女大学生 化妆品态度"
DEFAULT_MAX_POSTS = 1
DEFAULT_SCROLL_TIMES = 0
DEFAULT_MAX_COMMENTS = 20
DEFAULT_MIN_DELAY = 2
DEFAULT_MAX_DELAY = 4
DEFAULT_PAGE_LOAD_WAIT = 3
DEFAULT_SAVE_SCREENSHOTS = True
DEFAULT_SAVE_JSON = True
DEFAULT_HEADLESS = False

# ==================== 默认参数结束 ====================


if __name__ == "__main__":
    print("=" * 50)
    print("小红书爬虫（弹窗模式版）")
    print("=" * 50)

    # 初始化参数
    keyword = DEFAULT_KEYWORD
    max_posts = DEFAULT_MAX_POSTS
    scroll_times = DEFAULT_SCROLL_TIMES
    max_comments_per_post = DEFAULT_MAX_COMMENTS
    min_delay = DEFAULT_MIN_DELAY
    max_delay = DEFAULT_MAX_DELAY
    page_load_wait = DEFAULT_PAGE_LOAD_WAIT
    save_screenshots = DEFAULT_SAVE_SCREENSHOTS
    save_json = DEFAULT_SAVE_JSON
    headless = DEFAULT_HEADLESS

    # 显示默认配置
    print_config(keyword, max_posts, scroll_times, max_comments_per_post,
                 min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless)

    # 询问是否修改配置
    modify = input("是否修改配置参数？(y/n，默认n): ").strip().lower()
    if modify == 'y':
        keyword, max_posts, scroll_times, max_comments_per_post, \
        min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless = \
            modify_config(keyword, max_posts, scroll_times, max_comments_per_post,
                         min_delay, max_delay, page_load_wait, save_screenshots, save_json, headless)

    # 执行爬虫
    print("\n开始抓取...\n")
    data = search_xiaohongshu(
        keyword=keyword,
        max_posts=max_posts,
        scroll_times=scroll_times,
        max_comments_per_post=max_comments_per_post,
        min_delay=min_delay,
        max_delay=max_delay,
        page_load_wait=page_load_wait,
        save_screenshots=save_screenshots,
        save_json=save_json,
        headless=headless
    )

    if data:
        print_results(data, keyword)

        if save_json:
            output_file = f"xiaohongshu_{keyword}_data.json"
            save_to_json(data, output_file)
    else:
        print("\n没有找到相关的帖子，可能原因：")
        print("1. 网络连接问题")
        print("2. 小红书反爬机制拦截")
        print("3. 页面结构已更新，请检查选择器")
