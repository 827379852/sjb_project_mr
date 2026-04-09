#!/usr/bin/env python3
"""
自动研究 API 测试脚本
======================
测试异步研究接口：提交任务 -> 轮询状态 -> 获取报告
"""

import requests
import time
import sys

# 配置
API_BASE = "http://localhost:8000/api/v1/research-flow"
API_KEY = "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8"  # 替换为你的 API Key

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


def test_connection():
    """测试 API 连接"""
    print("\n" + "=" * 50)
    print("📡 测试 API 连接...")
    print("=" * 50)

    try:
        response = requests.get(f"{API_BASE}/auto-research/test", headers=HEADERS)
        result = response.json()

        if result.get("code") == 0:  # code=0 表示成功
            data = result.get("data", {})
            print(f"✅ API 连接正常")
            print(f"   用户: {data['user']['name']} ({data['user']['email']})")
            print(f"   积分: {data['user']['credits']}")
            print(f"   所需积分: {data['credits_required']}")
            print(f"   可执行研究: {'是' if data['can_research'] else '否（积分不足）'}")
            return data.get("can_research", False)
        else:
            print(f"❌ 测试失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False


def submit_task(user_request: str, persona_count: int = 3):
    """提交研究任务"""
    print("\n" + "=" * 50)
    print("🚀 提交研究任务...")
    print("=" * 50)

    payload = {
        "user_request": user_request,
        "persona_count": persona_count,
        "platforms": ["小红书", "微博", "抖音"]
    }

    print(f"📝 研究需求: {user_request}")
    print(f"👥 人设数量: {persona_count}")

    try:
        response = requests.post(
            f"{API_BASE}/auto-research/submit",
            headers=HEADERS,
            json=payload
        )
        result = response.json()

        if result.get("code") == 0:  # code=0 表示成功
            data = result.get("data", {})
            task_id = data.get("task_id")
            print(f"✅ 任务已提交")
            print(f"   Task ID: {task_id}")
            return task_id
        else:
            print(f"❌ 提交失败: {result}")
            return None
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return None


def poll_status(task_id: str, interval: int = 5, max_wait: int = 600):
    """轮询任务状态"""
    print("\n" + "=" * 50)
    print("⏳ 等待任务完成...")
    print("=" * 50)

    waited = 0
    while waited < max_wait:
        try:
            response = requests.get(
                f"{API_BASE}/auto-research/status/{task_id}",
                headers=HEADERS
            )
            result = response.json()

            if result.get("code") == 0:  # code=0 表示成功
                data = result.get("data", {})
                status = data.get("status")

                if status == "completed":
                    print(f"\n✅ 任务完成!")
                    print(f"   标题: {data.get('title')}")
                    print(f"   报告长度: {len(data.get('report', ''))} 字符")
                    return data.get("report")

                elif status == "failed":
                    print(f"\n❌ 任务失败: {data.get('error')}")
                    return None

                elif status == "in_progress":
                    phase = data.get("current_phase", "unknown")
                    print(f"   [{waited}s] 执行中... 当前阶段: {phase}")

                else:
                    print(f"   [{waited}s] 等待执行...")

        except Exception as e:
            print(f"   [{waited}s] 查询错误: {e}")

        time.sleep(interval)
        waited += interval

    print(f"\n⏰ 超时：等待超过 {max_wait} 秒")
    return None


def save_report(report: str, task_id: str):
    """保存报告"""
    filename = f"report_{task_id[:8]}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"📄 报告已保存: {filename}")


def main():
    print("\n" + "=" * 50)
    print("🔬 自动研究 API 测试脚本")
    print("=" * 50)

    # 1. 测试连接
    can_research = test_connection()
    if not can_research:
        print("\n⚠️ 无法执行研究，请检查积分或权限")
        return

    # 2. 提交任务
    user_request = sys.argv[1] if len(sys.argv) > 1 else "我想研究年轻女性对国产美妆品牌的消费态度"
    task_id = submit_task(user_request)
    if not task_id:
        return

    # 3. 轮询状态
    report = poll_status(task_id)

    # 4. 保存报告
    if report:
        save_report(report, task_id)
        print("\n" + "=" * 50)
        print("✨ 测试完成!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ 测试失败，未能获取报告")
        print("=" * 50)


if __name__ == "__main__":
    main()
