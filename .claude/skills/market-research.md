# Market Research Skill

自动市场研究工具 - 输入研究需求，自动生成完整的市场调研报告。

## 触发条件

TRIGGER when: 用户请求进行市场研究、用户调研、竞品分析、消费者洞察、行业分析等研究任务

## 功能

当用户说类似以下内容时，自动调用此工具：
- "给我做一个关于 xxx 的市场研究报告"
- "研究一下 xxx 的消费趋势"
- "分析 xxx 的用户需求"
- "帮我调研 xxx 市场"

## 使用方法

当触发此 skill 时，执行以下命令：

```bash
python D:/BUPT/06_市场调研/sjb_project_mr/market_research_cli.py --api-key "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8" "用户的研究需求"
```

**参数说明：**
- `--api-key`: API 密钥（已配置）
- `--persona-count`: 人设数量（可选，默认 5）
- `--output`: 保存报告到文件（可选）

**示例调用：**
```bash
# 基本用法
python D:/BUPT/06_市场调研/sjb_project_mr/market_research_cli.py --api-key "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8" "研究年轻女性对国产美妆品牌的消费态度"

# 指定人设数量
python D:/BUPT/06_市场调研/sjb_project_mr/market_research_cli.py --api-key "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8" --persona-count 3 "研究大学生对新能源汽车的购买意愿"

# 保存到文件
python D:/BUPT/06_市场调研/sjb_project_mr/market_research_cli.py --api-key "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8" -o report.md "研究白领咖啡消费习惯"
```

## 执行流程

1. **验证连接** - 测试 API Key 是否有效
2. **提交任务** - 发送研究需求
3. **等待完成** - 轮询任务状态（约 2-5 分钟）
4. **返回报告** - 输出 Markdown 格式报告

## 报告结构

生成的报告包含：
1. 执行摘要
2. 研究方法
3. 用户画像分析（5 个典型用户）
4. 核心发现
5. 竞品与市场洞察
6. 机会与建议
7. 附录（访谈记录）

## 注意事项

- 每次研究消耗 10 积分
- 研究过程约需 2-5 分钟
- 请耐心等待任务完成
- 如遇网络错误，可重试

## 示例对话

**用户：** 帮我做一个关于年轻人奶茶消费习惯的市场研究报告

**Agent：** 好的，我来为您生成关于年轻人奶茶消费习惯的市场研究报告。

[执行命令]
```bash
python D:/BUPT/06_市场调研/sjb_project_mr/market_research_cli.py --api-key "mr_live_uuCQR2LUTbOMR5MJqh7LU4EJq1ZXaoNmwLQo29lucn8" "研究年轻人的奶茶消费习惯"
```

[等待 2-5 分钟后返回报告]

研究报告已完成：

## 执行摘要
本次研究针对年轻人的奶茶消费习惯进行了深度调研...
[报告内容]
