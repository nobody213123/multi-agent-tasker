"""
=================================================================
  数据解析 Agent
  职责：利用大模型从网页 HTML 中提取核心业务数据
        （价格、数值、百分比、关键指标等）
  输入：原始 HTML
  输出：结构化的数据字典
=================================================================
"""
import json
import sys

from config import DASHSCOPE_API_KEY, LLM_MODEL, LLM_TEMPERATURE


def _get_llm():
    """初始化阿里云百炼大模型"""
    if not DASHSCOPE_API_KEY:
        print("  ❌ 错误: 未设置 DASHSCOPE_API_KEY 环境变量")
        sys.exit(1)
    try:
        from langchain_community.chat_models import ChatTongyi
        return ChatTongyi(
            model=LLM_MODEL,
            api_key=DASHSCOPE_API_KEY,
            temperature=LLM_TEMPERATURE,
        )
    except ImportError as e:
        print(f"  ❌ 缺少依赖: {e}")
        print("  💡 请运行: pip install langchain langchain-community dashscope")
        sys.exit(1)


# 解析 Agent 的系统提示词
PARSER_SYSTEM_PROMPT = """你是一个专业的网页数据解析专家。

你的任务是从页面渲染后的可见文本中提取所有重要的业务数据。

你需要提取的数据包括但不限于：
1. 价格、金额类数字（注意 ¥ 符号后的数字）
2. 百分比、涨跌幅（如 +2.35%、-0.96%）
3. 关键指标、统计数值（如饰品指数、今日最高/最低）
4. 标题、分类名称、饰品名称
5. 任何看起来像是核心业务数据的字段

注意：
- 只提取你确信是有效数据的内容
- 数值尽量保持原始格式（保留 ¥、% 等符号）
- 忽略导航菜单、登录注册提示、页脚等无关内容
- 如果页面无法访问或没有有效数据，返回 {"error": "未找到有效数据"}

请严格按 JSON 格式返回结果，不要包含其他文字。"""


class ParserAgent:
    """解析 Agent：从 HTML 中提取结构化数据"""

    def run(self, html: str) -> dict:
        """
        执行解析任务

        参数:
            html: 原始网页 HTML 字符串

        返回:
            解析后的数据字典，如 {"价格": "xxx", "涨跌幅": "xxx"}
            解析失败时返回 {"error": "解析失败"}
        """
        print(f"\n{'='*50}")
        print(f"  📊【解析 Agent】正在提取页面数据...")
        print(f"{'='*50}")

        if not html:
            print("  ⚠️  页面文本为空，跳过解析")
            return {"error": "页面文本为空，无法解析"}

        # 截取前 6000 字符（可见文本密度高，此长度足够）
        truncated = html[:6000]

        llm = _get_llm()
        try:
            from langchain.schema import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=PARSER_SYSTEM_PROMPT),
                HumanMessage(content=f"请解析以下页面文本并返回 JSON 格式的数据：\n\n{truncated}"),
            ]

            response = llm.invoke(messages)
            content = response.content.strip()

            # 清理可能的 markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            parsed = json.loads(content)
            print(f"  ✅ 解析成功，提取到 {len(parsed)} 个字段")
            for key, value in parsed.items():
                print(f"     • {key}: {value}")
            return parsed

        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON 解析失败: {e}")
            print(f"  📄 原始响应:\n{content}")
            return {"error": f"JSON 解析失败: {e}"}
        except Exception as e:
            print(f"  ❌ 大模型调用异常: {e}")
            return {"error": f"解析异常: {e}"}
