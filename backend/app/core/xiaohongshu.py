from playwright.sync_api import sync_playwright
import time
import random
import json
import sys
import io

# 设置标准输出编码为 UTF-8（解决 Windows 终端 emoji 乱码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace',line_buffering=True)

# 模拟真实浏览器的 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
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
    小红书爬虫主函数

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
    print(f"\n正在搜索: {keyword}，目标 {max_posts} 个帖子...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        cookies = [
    {"name": "abRequestId", "value": "dab0aa40-3aec-51f4-8a0c-f475488d2c8c", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "ets", "value": "1775634811523", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "xsecappid", "value": "xhs-pc-web", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "a1", "value": "19d6c150acdaqghpz80m9zaqq9tobheg8fwwbie7450000286325", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "webId", "value": "17c697cb144a0776b13b8b96bb759099", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "gid", "value": "yjfKSy2yj2Y4yjfKSy280i3dSf0AkxUuY86jEW4u0AAj9E28lDxdkD888JYKqJ28JiSK0KWW", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "web_session", "value": "0400698cc4323f561240e041e33b4bc7cb83b4", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "id_token", "value": "VjEAAGV8icCEyy9jCO25RtP9Vofh0E2WQtx9Drb4enNT1deI3RQlWgiyy2yVotN0/07RhjUwLCPOGRpWo2LlHDF7CqCQsekWtQLI7hNzOpsuqV+HBDRiPDyvpPuFUmS5ArjF7+L/", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "unread", "value": "{\"ub\":\"69d788e2000000002301e4ed\",\"ue\":\"69d60986000000001d01b649\",\"uc\":28}", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "acw_tc", "value": "0ad5865817757967658742590e529d193fe53d3f1ec1a2851473e022668259", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "websectiga", "value": "2a3d3ea002e7d92b5c9743590ebd24010cf3710ff3af8029153751e41a6af4a3", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "sec_poison_id", "value": "fdba7ed2-78c2-4fae-9b98-a871a47d1dc1", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "webBuild", "value": "6.5.1", "domain": ".xiaohongshu.com", "path": "/"},
    {"name": "loadts", "value": "1775798074261", "domain": ".xiaohongshu.com", "path": "/"},
]
        context.add_cookies(cookies)

        page = context.new_page()

        print(f"打开小红书...")
        try:
            page.goto("https://www.xiaohongshu.com/explore", timeout=60000)
        except Exception as e:
            print(f"访问失败: {e}")
            browser.close()
            return []

        page.wait_for_timeout(3000)

        print("输入关键词...")
        try:
            search_box = page.wait_for_selector("#search-input", timeout=10000)
            search_box.fill(keyword)
            page.keyboard.press("Enter")
            print("搜索成功")

        except Exception as e:
            print(f"搜索框操作失败: {e}")
            browser.close()
            return []

        page.wait_for_timeout(5000)
        page.screenshot(path="screenshot1.png")

        # ========== 筛选操作 ==========
        print("正在设置筛选条件...")
        try:
            # 鼠标悬停到筛选按钮（漏斗图标）展开下拉菜单
            filter_clicked = False
            filter_selectors = [
                ".filter-btn", ".filter", "[class*='filter']",
                ".sort-filter", ".search-filter", ".feeds-filter",
                "button.filter", "span.filter", "div.filter",
                "[data-v-b1556b3c]",  # 小红书可能的内部选择器
                ".search-result .filter-btn",
                ".note-list-header .filter"
            ]
            for selector in filter_selectors:
                try:
                    filter_btn = page.wait_for_selector(selector, timeout=3000)
                    if filter_btn:
                        # 先鼠标悬停，等待下拉菜单出现
                        filter_btn.hover()
                        print("  已悬停到筛选按钮")
                        page.wait_for_timeout(2000)

                        # 悬停后再点击
                        # filter_btn.click()
                        filter_clicked = True
                        # print("  已点击筛选按钮")
                        page.wait_for_timeout(2000)
                        break
                except:
                    continue
            page.screenshot(path = r'D:\temp\1.jpg')
            if not filter_clicked:
                # 尝试通过文本查找筛选按钮
                try:
                    all_buttons = page.query_selector_all("button, span, div")
                    for btn in all_buttons:
                        try:
                            btn_text = btn.inner_text()
                            if "筛选" in btn_text:
                                # 先悬停
                                btn.hover()
                                print("  已悬停到筛选按钮（通过文本匹配）")
                                page.wait_for_timeout(2000)
                                # 再点击
                                btn.click()
                                filter_clicked = True
                                print("  已点击筛选按钮（通过文本匹配）")
                                page.wait_for_timeout(2000)
                                break
                        except:
                            continue
                except:
                    pass

            if filter_clicked:
                page.wait_for_timeout(2000)

                # 1. 选择排序方式：最多点赞
                try:
                    # 直接定位包含"最多点赞"文本的元素
                    sort_option = page.get_by_text("最多点赞", exact=True).nth(1)
                    if sort_option.is_visible():
                        sort_option.click()
                        print("  已选择：最多点赞")
                        page.wait_for_timeout(1000)
                    else:
                        # 备用：尝试其他选择器
                        sort_option = page.locator("span:has-text('最多点赞')").first
                        if sort_option.is_visible():
                            sort_option.click()
                            print("  已选择：最多点赞（备用选择器）")
                            page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"  选择最多点赞失败: {e}")

                # 2. 选择时间范围：半年内
                try:
                    time_option = page.get_by_text("半年内", exact=True).nth(1)
                    if time_option.is_visible():
                        time_option.click()
                        print("  已选择：半年内")
                        page.wait_for_timeout(1000)
                    else:
                        time_option = page.locator("span:has-text('半年内')").first
                        if time_option.is_visible():
                            time_option.click()
                            print("  已选择：半年内（备用选择器）")
                            page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"  选择半年内失败: {e}")

                # 3. 选择内容类型：图文
                try:
                    type_option = page.get_by_text("图文", exact=True).nth(1)
                    if type_option.is_visible():
                        type_option.click()
                        print("  已选择：图文")
                        page.wait_for_timeout(1000)
                    else:
                        type_option = page.locator("span:has-text('图文')").first
                        if type_option.is_visible():
                            type_option.click()
                            print("  已选择：图文（备用选择器）")
                            page.wait_for_timeout(1000)
                except Exception as e:
                    print(f"  选择图文失败: {e}")

                # 确认筛选（如果有确认按钮）
                try:
                    confirm_btn = page.query_selector("button:has-text('确定'), button:has-text('确认'), .confirm-btn, [class*='confirm']")
                    if confirm_btn:
                        confirm_btn.click()
                        print("  已确认筛选条件")
                        page.wait_for_timeout(2000)
                except:
                    pass

                page.screenshot(path="screenshot2_filter.png")
                print("  筛选条件设置完成")

        except Exception as e:
            print(f"  筛选操作失败（将继续爬取）: {e}")
            page.screenshot(path="screenshot2_error.png")

        page.wait_for_timeout(2000)
        page.screenshot(path = r'D:\temp\2.jpg')
        # ========== 筛选操作结束 ==========

        # 已移除滚动加载，直接解析当前页面数据
        print("解析数据...")
        page.screenshot(path=r'D:\temp\3.jpg')
        cards = page.query_selector_all(".note-item")

        results = []
        cards_to_process = cards[:max_posts]

        for idx, card in enumerate(cards_to_process):
            try:
                title_el = (
                    card.query_selector(".title span") or
                    card.query_selector("h1") or
                    card.query_selector(".note-content .title")
                )
                title = title_el.inner_text() if title_el else ""

                author_el = (
                    card.query_selector(".author-name") or
                    card.query_selector(".name") or
                    card.query_selector(".user-nickname")
                )
                author = author_el.inner_text() if author_el else ""

                link_el = card.query_selector("a.cover, a[href*='/discovery/item/']")
                if not link_el:
                    link_el = card.query_selector("a")
                link = link_el.get_attribute("href") if link_el else ""

                if link and not link.startswith("http"):
                    link = "https://www.xiaohongshu.com" + link

                if title or author:
                    results.append({
                        "title": title.strip() if title else "无标题",
                        "author": author.strip() if author else "未知作者",
                        "link": link,
                        "content": "",
                        "comments": []
                    })
                    print(f"  已提取第 {idx+1} 个帖子: {results[-1]['title'][:30]}...")
            except Exception as e:
                print(f"  提取第 {idx+1} 个帖子失败: {e}")
                continue

        print(f"\n开始抓取前 {len(results)} 个帖子的详情和评论...")

        for idx, post in enumerate(results):
            print(f"\n正在抓取第 {idx+1}/{len(results)} 个帖子: {post['title'][:30]}...")
            try:
                detail_page = context.new_page()
                detail_page.goto(post['link'], timeout=60000)
                time.sleep(page_load_wait)

                if save_screenshots:
                    detail_page.screenshot(path=f"detail_{idx+1}.png", full_page=False)

                # ===== 抓取正文内容 =====
                content = ""
                content_selectors = [
                    "#detail-content", ".detail-content", ".note-content",
                    ".content", "#content", ".desc", "#note-desc",
                    ".note-detail-content", ".main-content"
                ]
                for selector in content_selectors:
                    el = detail_page.query_selector(selector)
                    if el:
                        content = el.inner_text()
                        if content.strip():
                            break

                if not content.strip():
                    content_container = detail_page.query_selector(".note-detail")
                    if content_container:
                        content = content_container.inner_text()
                    else:
                        all_text = detail_page.inner_text("body")
                        lines = all_text.split('\n')
                        for line in lines:
                            if len(line) > 50:
                                content = line
                                break

                post['content'] = content.strip() if content else "无法获取正文"
                print(f"  正文长度: {len(post['content'])} 字符")

                # ===== 抓取评论内容 =====
                comments = []

                # 展开评论区
                expand_selectors = [
                    ".expand-btn", ".expand-comment", "#expand-comment",
                    ".show-more-comments", ".load-more-comments",
                    ".comment-expand-btn", ".comments-btn",
                    "[class*='expand']", "[class*='more']"
                ]

                for selector in expand_selectors:
                    try:
                        expand_btn = detail_page.query_selector(selector)
                        if expand_btn:
                            expand_btn.click()
                            print(f"  已点击展开评论区按钮")
                            time.sleep(2)
                            break
                    except:
                        continue

                # 滚动到评论区
                try:
                    detail_page.evaluate("window.scrollBy(0, document.body.scrollHeight * 0.7)")
                    time.sleep(2)
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
                        comment_container = detail_page.query_selector(selector)
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
                            items = comment_container.query_selector_all(selector)
                            if items and len(items) > 0:
                                comment_items = items
                                print(f"  找到 {len(items)} 个评论项")
                                break
                        except:
                            continue

                    for comment_item in comment_items[:max_comments_per_post]:
                        try:
                            comment_text_el = (
                                comment_item.query_selector(".comment-content") or
                                comment_item.query_selector(".text") or
                                comment_item.query_selector(".content") or
                                comment_item.query_selector(".comment-text") or
                                comment_item.query_selector("p") or
                                comment_item.query_selector("span")
                            )
                            comment_text = comment_text_el.inner_text() if comment_text_el else ""

                            comment_user_el = (
                                comment_item.query_selector(".user-name") or
                                comment_item.query_selector(".nickname") or
                                comment_item.query_selector(".comment-user") or
                                comment_item.query_selector(".author") or
                                comment_item.query_selector("a.user-link") or
                                comment_item.query_selector("a")
                            )
                            comment_user = comment_user_el.inner_text() if comment_user_el else ""

                            if comment_text.strip() and len(comment_text.strip()) > 2:
                                comments.append({
                                    "user": comment_user.strip() if comment_user else "匿名用户",
                                    "text": comment_text.strip()
                                })
                        except:
                            continue

                post['comments'] = comments
                print(f"  获取到 {len(comments)} 条评论")

                detail_page.close()

                # 随机间隔，避免反爬
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)

            except Exception as e:
                print(f"  抓取帖子详情失败: {e}")
                if 'detail_page' in locals():
                    try:
                        detail_page.close()
                    except:
                        pass
                continue

        print(f"\n共找到 {len(results)} 条帖子详情")
        browser.close()
        return results


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
    print("小红书爬虫")
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
